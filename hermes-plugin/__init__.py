"""Diké para Hermes: adaptador delgado sobre el motor de verificación de citas.

Native community adapter under review; not a public release.
The verifier runs in a subprocess. No signing or engine import in Hermes.

El motor no se importa en el proceso de Hermes. Corre como subproceso, por el
mismo contrato que usa cualquier otro consumidor: `dike constancia <archivo>
--json`, con sus códigos de salida (0: todo verificado; 1: hay citas que no se
pudieron verificar; 2: error). Así el motor sigue siendo el mismo con Hermes o
sin él, y sus módulos (`lexo_cli`, `shared`, `dike_id`) no se mezclan con los
de Hermes.

El subproceso recibe un entorno mínimo y un HOME de datos del plugin: no se
le pasan las variables de credenciales del agente. Esto no es un sandbox ni
impide técnicamente acceder a otros archivos. El corpus se instala, la primera
vez, en la carpeta de datos del plugin.
"""

from __future__ import annotations

import hashlib
import fcntl
from datetime import date, datetime
import json
import stat
import re
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent
_MOTOR = _RAIZ / "motor"
_CORPUS = _RAIZ / "corpus"
_USUARIO = "hermes"
_NOMBRE_CORPUS = "chile-base"
_LIMITE_TEXTO = 400_000

ESQUEMA = {
    "name": "dike_verificar_citas",
    "description": (
        "Verifica las citas de normas chilenas de un escrito jurídico contra un corpus local "
        "identificado por hash. Úsala SIEMPRE antes de afirmar que una cita legal es correcta, "
        "existe o está vigente. Devuelve, cita por cita, si se pudo verificar; las que no, vienen "
        "con el motivo (AMBIGUOUS, UNRESOLVABLE, …). Una cita no verificada NO se puede dar por "
        "buena: hay que decírselo al usuario tal cual. Comprueba identidad, citabilidad y estado "
        "de vigencia registrado en el corpus; no consulta cambios posteriores en vivo ni "
        "verifica que la norma diga lo que el escrito le atribuye. Usa archivos temporales "
        "y datos persistidos del plugin; no es una operación libre de escrituras."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "texto": {"type": "string", "description": "El texto del escrito, o el pasaje con las citas."},
            "ruta": {"type": "string", "description": "Ruta de un archivo .md o .txt con el escrito (alternativa a `texto`)."},
        },
    },
}


def _carpeta_de_datos() -> Path:
    try:
        from plugins.plugin_storage import plugin_data_dir
        return Path(plugin_data_dir("dike"))
    except Exception:
        base = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes")) / "plugin-data" / "dike"
        base.mkdir(parents=True, exist_ok=True)
        return base


def _paquetes_del_anfitrion() -> list:
    """Las carpetas de paquetes instalados del proceso que carga el plugin.

    Hermes no corre desde un entorno con lanzador propio: activa sus dependencias
    agregándolas a `sys.path`. El subproceso usa el mismo intérprete y necesita
    esas mismas carpetas para encontrar pydantic, yaml y las demás. Solo viajan
    las carpetas de paquetes instalados, no el código de Hermes.
    """
    return [p for p in sys.path if p and ("site-packages" in p or "dist-packages" in p)]


def _entorno(datos: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "LC_ALL", "TZ")}
    env.update({
        "PYTHONPATH": os.pathsep.join([str(_MOTOR), *_paquetes_del_anfitrion()]),
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": str(datos / "home"),
        "LEXO_CONFIG": str(datos / "config.yaml"),
        "DIKE_USER": _USUARIO,
        "DIKE_USERS_ROOT": str(datos / "users"),
        "DIKE_ROOTS_CACHE_DIR": str(datos / "roots_cache"),
    })
    return env


def _dike(argumentos: list, datos: Path, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "lexo_cli", *argumentos],
        env=_entorno(datos), cwd=str(datos), capture_output=True, text=True, timeout=timeout,
    )


def _asegurar_corpus(datos: Path) -> dict:
    """Validate package and installed generation; publish only complete installs."""
    datos.mkdir(parents=True, exist_ok=True)
    entries = [line.split() for line in (_CORPUS / 'SHA256SUMS').read_text().splitlines() if line.strip()]
    if len(entries) != 1 or len(entries[0]) != 2:
        raise ValueError('invalid corpus checksum manifest')
    esperado, nombre = entries[0]
    if Path(nombre).name != nombre or not re.fullmatch(r'[0-9a-f]{64}', esperado):
        raise ValueError('invalid corpus package name or digest')
    paquete = _CORPUS / nombre
    if hashlib.sha256(paquete.read_bytes()).hexdigest() != esperado:
        raise ValueError('corpus package checksum mismatch')
    generation = datos / 'generations' / esperado
    generation.parent.mkdir(parents=True, exist_ok=True)
    with (datos / 'install.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        marker = generation / 'installed.json'
        if generation.exists():
            record = json.loads(marker.read_text())
            if record.get('package_sha256') != esperado:
                raise ValueError('installed generation mismatch')
            actual = {str(p.relative_to(generation)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (generation / 'users').rglob('*') if p.is_file()}
            if actual != record.get('files'):
                raise ValueError('installed corpus integrity mismatch')
            return {'generation': str(generation)}
        with tempfile.TemporaryDirectory(dir=generation.parent, prefix='staging-') as tmp:
            stage = Path(tmp) / 'generation'
            stage.mkdir()
            (stage / 'home').mkdir()
            (stage / 'config.yaml').write_text('starter:\n  user: hermes\n')
            unpack = Path(tmp) / 'unpack'
            unpack.mkdir()
            with tarfile.open(paquete) as tar:
                tar.extractall(unpack, filter='data')
            result = _dike(['starter', '--user', _USUARIO, 'install', str(unpack / _NOMBRE_CORPUS),
                            '--name', _NOMBRE_CORPUS, '--json'], stage)
            if result.returncode != 0 or not isinstance(json.loads(result.stdout), dict):
                raise ValueError('corpus installation failed')
            # Starter STATE carries a local absolute snapshot locator. Relocate
            # that locator before publishing; sealed snapshot content is untouched.
            for state_file in (stage / 'users').glob('*/starter/*/STATE.json'):
                state = json.loads(state_file.read_text())
                snapshot = Path(state['snapshot'])
                state['snapshot'] = str(generation / snapshot.relative_to(stage))
                state_file.write_text(json.dumps(state, indent=2))
            files = {str(p.relative_to(stage)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (stage / 'users').rglob('*') if p.is_file()}
            if not files:
                raise ValueError('corpus installation produced no data')
            (stage / 'installed.json').write_text(json.dumps({'package_sha256': esperado, 'files': files}))
            stage.rename(generation)
        return {'generation': str(generation)}


def _validar_constancia(c, code):
    if not isinstance(c, dict) or code not in (0, 1):
        raise ValueError('invalid constancia envelope or exit code')
    for key, kind in [('meta', dict), ('detalles', list), ('problemas', list),
                      ('alcance', str), ('citation_disclosure', dict)]:
        if not isinstance(c.get(key), kind):
            raise ValueError(f'invalid constancia field: {key}')
    if not c['alcance'].strip() or any(not isinstance(p, str) for p in c['problemas']):
        raise ValueError('invalid scope or problems')
    meta = c['meta']
    counts = [meta.get(k) for k in ('total_citas', 'citas_verificadas', 'citas_fallidas')]
    if any(type(n) is not int or n < 0 for n in counts):
        raise ValueError('invalid citation counts')
    total, verified, failed = counts
    if total != verified + failed or total != len(c['detalles']):
        raise ValueError('inconsistent citation counts')
    if meta.get('pack_hash') != 'ea28fa1c0f9af6c1':
        raise ValueError('unexpected corpus pack_hash')
    date.fromisoformat(meta['as_of'])
    datetime.fromisoformat(meta['fecha_constancia'])
    for d in c['detalles']:
        if not isinstance(d, dict) or d.get('estado') not in ('VERIFICADA', 'FALLO'):
            raise ValueError('invalid citation detail')
        if not isinstance(d.get('cita_raw'), str) or not d['cita_raw'].strip():
            raise ValueError('missing citation text')
        if d['estado'] == 'VERIFICADA':
            for key in ('gid', 'fuente_url', 'fecha_recuperacion'):
                if not isinstance(d.get(key), str) or not d[key].strip():
                    raise ValueError(f'missing verified evidence: {key}')
            if not isinstance(d.get('texto_hash'), str) or not re.fullmatch(r'[0-9a-f]{64}', d['texto_hash']):
                raise ValueError('missing verified text hash')
    if verified != sum(d['estado'] == 'VERIFICADA' for d in c['detalles']):
        raise ValueError('details disagree with counts')
    if c.get('veredicto') not in ('TODAS_VERIFICADAS', 'CON_PROBLEMAS'):
        raise ValueError('invalid verdict')
    all_verified = c['veredicto'] == 'TODAS_VERIFICADAS'
    if code != (0 if all_verified else 1) or (all_verified and (failed or not total)):
        raise ValueError('verdict contradicts counts or exit code')
    return c


def _texto_input(args):
    if not isinstance(args, dict) or set(args) - {'texto', 'ruta'}:
        raise ValueError('invalid input fields')
    if ('texto' in args) == ('ruta' in args):
        raise ValueError('provide exactly one of texto or ruta')
    value = args.get('texto') if 'texto' in args else args.get('ruta')
    if not isinstance(value, str) or not value.strip():
        raise ValueError('input must be a nonempty string')
    if 'ruta' in args:
        path = Path(value).expanduser().absolute()
        if path.suffix.lower() not in ('.md', '.txt') or any(p.is_symlink() for p in [path, *path.parents]):
            raise ValueError('only regular .md/.txt files without symlinks are accepted')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > _LIMITE_TEXTO:
                raise ValueError('not a regular file or file too large')
            value = stream.read(_LIMITE_TEXTO + 1).decode('utf-8')
    if not value.strip() or len(value.encode('utf-8')) > _LIMITE_TEXTO:
        raise ValueError('empty input or input exceeds 400000 UTF-8 bytes')
    return value


def verificar_citas(args: dict, **kwargs) -> str:
    try:
        texto = _texto_input(args)
        datos = _carpeta_de_datos()
        installed = _asegurar_corpus(datos)
        runtime = Path(installed.get('generation', datos))
        with tempfile.TemporaryDirectory(dir=datos) as tmp:
            archivo = Path(tmp) / 'escrito.md'
            archivo.write_text(texto, encoding='utf-8')
            result = _dike(['constancia', str(archivo), '--json'], runtime)
        c = _validar_constancia(json.loads(result.stdout), result.returncode)
        # Preserve the engine envelope, including disclosure and reasons.
        return json.dumps({**c, 'todo_verificado': c['veredicto'] == 'TODAS_VERIFICADAS',
                           'certificacion_sustantiva': False}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({'error': f'{type(exc).__name__}: {exc}', 'todo_verificado': False}, ensure_ascii=False)


def _comando(raw):
    return verificar_citas({'texto': raw})


def register(ctx):
    ctx.register_tool(name='dike_verificar_citas', toolset='dike', schema=ESQUEMA, handler=verificar_citas)
    ctx.register_command('dike-verificar', _comando, 'Verifica citas contra el corpus local; no firma.')
    carpeta = _RAIZ / 'skills'
    if carpeta.is_dir():
        for hija in sorted(carpeta.iterdir()):
            if (hija / 'SKILL.md').is_file():
                ctx.register_skill(hija.name, hija / 'SKILL.md')
