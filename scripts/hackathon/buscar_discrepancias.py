#!/usr/bin/env python3
"""Busca, con alteraciones al azar, una entrada en que los verificadores discrepen.

`KEYS.md` dice que sus dos caminos dan el mismo veredicto. La batería de casos
(`lexo_cli/tests/_kit_commitment.py`) prueba las entradas que a alguien se le
ocurrieron; este guion prueba las que no. Arma un kit sintético con una llave
desechable, altera al azar uno de sus tres archivos y compara el veredicto de:

  · la biblioteca de Diké (`verificar_archivos` + `leer_clave_publica`),
  · `verificar_tercero.py`,
  · la receta de `jq` + OpenSSL de `KEYS.md`, ejecutada tal como está escrita.

    python scripts/hackathon/buscar_discrepancias.py                    # 2000 casos
    python scripts/hackathon/buscar_discrepancias.py --casos 5000 --semilla 7
    python scripts/hackathon/buscar_discrepancias.py --jq ~/bin/jq-1.6  # con otro jq

Sale 0 si no encuentra ninguna, 1 si encuentra alguna (imprime la alteración
exacta y deja el archivo en la carpeta de trabajo) y 2 si el arnés está mal.

El 2026-10-06 encontró dos que la batería no traía: un byte nulo después del
objeto JSON, que un `jq` anterior a 1.8 tolera, y un carácter suelto dentro del
PEM de la clave pública, que `cryptography` ignora y OpenSSL no.

No toca el árbol real ni ninguna llave real: todo ocurre en la carpeta de trabajo.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

ARCHIVOS = ("commitment.json", "commitment.sig.json", "content-signing-key.pub")
#: Con qué frecuencia se altera cada archivo. La clave pesa más de lo que mide.
PESOS = (35, 40, 25)

#: Lo que se inserta o se pone en lugar de un byte. Elegido para caer en las
#: costuras: espacios raros, escapes, formas de escribir un número, comillas,
#: bytes que no son UTF-8, y trozos de JSON.
TROZOS = [
    b"\n", b"\r", b"\t", b" ", b"\x00", b"\\u0000", b"\\n", b"\\t", b"0", b"1", b"+", b"-", b".", b"e0", b"E0",
    b'"', b"\\", b",", b":", b"{", b"}", b"[", b"]", b"null", b"true", b"false", b"\xef\xbb\xbf", b"\x7f",
    b"\x0b", b"\x0c", b"\x1f", b"\x01", b"\xc2\xa0", b"\xe2\x80\xa8", b"\xc3\xa9", b"\\u00e9", b"//x\n",
    b"/*x*/", b"NaN", b"Infinity", b"'", b"#", b"\xff", b"\xed\xa0\x80", b"\\ud800", b"0x1", b"1.0", b"-0",
    b"00", b"A", b"a", b"f", b"F", b"{}", b"[]", b'""', b'"x":1,', b'"signature":"",', b"=", b"-----",
]
#: Un segundo documento, antes o después del bueno.
DOCUMENTOS = [b"{}", b"[]", b"null", b'""', b"1", b'{"signature":""}', b'{"signature":"","key_id":""}', b"\n\n", b" "]


class Resultado:
    """Cuántas alteraciones se probaron, cuántas siguen verificando por los
    tres, y las que discrepan: (archivo, alteración, veredictos)."""

    def __init__(self) -> None:
        self.casos = 0
        self.verifican = 0
        self.discrepan: list[tuple[str, str, dict]] = []


def _receta_de_keys_md(keys: Path) -> str:
    bloques = re.findall(r"^```bash\n(.*?)^```", keys.read_text(encoding="utf-8"), flags=re.DOTALL | re.MULTILINE)
    receta = [b for b in bloques if "openssl pkeyutl" in b]
    if len(receta) != 1:
        raise RuntimeError("KEYS.md no trae exactamente una receta de jq + OpenSSL")
    return receta[0]


def _verificador_de_tercero(ruta: Path):
    spec = importlib.util.spec_from_file_location("verificar_tercero_bajo_prueba", ruta)
    mod = importlib.util.module_from_spec(spec)
    # Sin dejar un .pyc junto al verificador que se publica.
    escribia, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = escribia
    return mod


class Comparador:
    """Los tres verificadores sobre una misma carpeta."""

    def __init__(self, trabajo: Path, *, receta: str | None = None, jq: Path | None = None):
        from lexo_cli.tests._kit_commitment import CARPETA_KIT, VERIFICADOR, Kit

        self.trabajo = trabajo
        trabajo.mkdir(parents=True, exist_ok=True)
        self.kit = Kit(trabajo / "kit")
        self.base = {n: (self.kit.raiz / n).read_bytes() for n in ARCHIVOS}
        self.caso = trabajo / "caso"
        self.caso.mkdir()
        self.guion = trabajo / "receta.sh"
        self.guion.write_text(receta if receta is not None else _receta_de_keys_md(CARPETA_KIT / "KEYS.md"), encoding="utf-8")
        self.tercero_mod = _verificador_de_tercero(VERIFICADOR)
        self.env = dict(os.environ)
        if jq is not None:
            # Una carpeta con ese `jq` y nada más, delante en el PATH.
            delante = trabajo / "bin"
            delante.mkdir()
            os.symlink(Path(jq).resolve(), delante / "jq")
            self.env["PATH"] = f"{delante}{os.pathsep}{self.env['PATH']}"

    def poner(self, cambios: dict[str, bytes] | None = None) -> None:
        for nombre, datos in self.base.items():
            (self.caso / nombre).write_bytes((cambios or {}).get(nombre, datos))

    def veredictos(self) -> dict[str, bool | str]:
        """¿Verifica? por cada verificador. Una cadena es una excepción no prevista."""
        from lexo_cli.content_signing import (
            ContentSigningError,
            DuplicateKeyError,
            leer_clave_publica,
            verificar_archivos,
        )

        c, s, k = (self.caso / n for n in ARCHIVOS)
        try:
            api: bool | str = verificar_archivos(c, s, leer_clave_publica(k)) is True
        except (ContentSigningError, DuplicateKeyError, ValueError):
            api = False
        except Exception as exc:  # no previsto: es un hallazgo en sí mismo
            api = f"excepción {type(exc).__name__}"
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                tercero: bool | str = self.tercero_mod.main(str(c), str(s), str(k)) == 0
        except Exception as exc:
            tercero = f"excepción {type(exc).__name__}"
        r = subprocess.run(["bash", str(self.guion)], cwd=self.caso, capture_output=True, timeout=120, env=self.env)
        return {"biblioteca": api, "verificar_tercero.py": tercero, "receta": r.returncode == 0}


def discrepan(veredictos: dict[str, bool | str]) -> bool:
    """True si no dicen todos lo mismo, o si alguno cayó con una excepción no prevista."""
    return len(set(veredictos.values())) != 1 or any(isinstance(v, str) for v in veredictos.values())


def alterar(rng: random.Random, base: dict[str, bytes]) -> tuple[str, bytes, str]:
    """Una alteración al azar de uno de los tres archivos."""
    nombre = rng.choices(ARCHIVOS, PESOS)[0]
    b = base[nombre]
    op = rng.choice(["ins", "ins", "ins", "del", "rep", "dupl", "caja", "doc_antes", "doc_despues", "trunc"])
    if op == "ins":
        i, t = rng.randrange(len(b) + 1), rng.choice(TROZOS)
        return nombre, b[:i] + t + b[i:], f"inserta {t!r} en {i}"
    if op == "del":
        i, k = rng.randrange(len(b)), rng.choice([1, 1, 1, 2, 5])
        return nombre, b[:i] + b[i + k:], f"quita {b[i:i + k]!r} en {i}"
    if op == "rep":
        i, t = rng.randrange(len(b)), rng.choice(TROZOS)
        return nombre, b[:i] + t + b[i + 1:], f"cambia {b[i:i + 1]!r} por {t!r} en {i}"
    if op == "dupl":
        lineas = b.split(b"\n")
        i = rng.randrange(len(lineas))
        lineas.insert(i, lineas[i])
        return nombre, b"\n".join(lineas), f"repite la línea {i}"
    if op == "caja":
        letras = [i for i, c in enumerate(b) if chr(c) in "abcdefABCDEF"]
        i = rng.choice(letras)
        return nombre, b[:i] + bytes([b[i] ^ 0x20]) + b[i + 1:], f"cambia de caja {b[i:i + 1]!r} en {i}"
    if op == "doc_antes":
        t = rng.choice(DOCUMENTOS)
        return nombre, t + b"\n" + b, f"antepone {t!r}"
    if op == "doc_despues":
        t = rng.choice(DOCUMENTOS)
        return nombre, b + t + b"\n", f"agrega al final {t!r}"
    i = rng.randrange(len(b))
    return nombre, b[:i], f"trunca en {i}"


def buscar(trabajo: Path, *, casos: int, semilla: int, receta: str | None = None, jq: Path | None = None) -> Resultado:
    comparador = Comparador(trabajo, receta=receta, jq=jq)
    comparador.poner()
    control = comparador.veredictos()
    if set(control.values()) != {True}:
        raise RuntimeError(f"el kit sin alterar no verifica por los tres: {control}")

    rng = random.Random(semilla)
    res = Resultado()
    for _ in range(casos):
        nombre, datos, descripcion = alterar(rng, comparador.base)
        comparador.poner({nombre: datos})
        v = comparador.veredictos()
        res.casos += 1
        res.verifican += set(v.values()) == {True}
        if discrepan(v):
            res.discrepan.append((nombre, descripcion, v))
            (trabajo / f"discrepa_{len(res.discrepan):03d}_{nombre}").write_bytes(datos)
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--casos", type=int, default=2000)
    ap.add_argument("--semilla", type=int, default=1)
    ap.add_argument("--jq", default=None, help="ruta a otro binario de jq (por defecto, el del PATH)")
    ap.add_argument("--tmp", default=None, help="carpeta de trabajo nueva (por defecto, una temporal)")
    args = ap.parse_args()
    sys.dont_write_bytecode = True  # ni un .pyc nuevo en el perfil por correr este guion

    faltan = [h for h in ("bash", "jq", "openssl", "sha256sum", "basenc") if shutil.which(h) is None]
    if faltan and not (faltan == ["jq"] and args.jq):
        print(f"no se puede ejecutar la receta: falta {', '.join(faltan)}")
        return 2
    trabajo = Path(args.tmp) if args.tmp else Path(tempfile.mkdtemp(prefix="buscar-discrepancias-"))
    if args.tmp and trabajo.exists() and any(trabajo.iterdir()):
        print(f"{trabajo} no está vacía: la búsqueda quiere una carpeta nueva")
        return 2
    try:
        res = buscar(trabajo, casos=args.casos, semilla=args.semilla, jq=Path(args.jq) if args.jq else None)
    except RuntimeError as exc:
        print(f"el arnés está mal: {exc}")
        return 2

    version = subprocess.run([args.jq or "jq", "--version"], capture_output=True, text=True).stdout.strip()
    print(f"{version}, semilla {args.semilla}: {res.casos} alteraciones; "
          f"{res.verifican} siguen verificando por los tres; DISCREPAN: {len(res.discrepan)}")
    for nombre, descripcion, v in res.discrepan:
        print(f"  {nombre}: {descripcion}  ->  {v}")
    if res.discrepan:
        print(f"los archivos alterados quedaron en {trabajo}")
        return 1
    if not args.tmp:
        shutil.rmtree(trabajo, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
