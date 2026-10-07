#!/usr/bin/env python3
"""DEMO de punta a punta para el BLI Legal Tech Hackathon.

    escrito --> dike constancia --emit-commitment --sign --> verificación por un tercero
                                                         --> la abstención

El demo termina en la ABSTENCIÓN, no en el hash: dos citas que Diké se negó a
certificar, con su motivo, y la comprobación de que no entraron al commitment
firmado. Ese es el producto.

    python docs/hackathon/demo_bli_e2e.py              # salida en una carpeta temporal
    python docs/hackathon/demo_bli_e2e.py --out DIR    # DIR nueva o vacía

Qué usa de verdad y qué no:

* El motor es el real: `dike constancia` contra el corpus instalado. Sin corpus
  el demo falla; no simula nada.
* La llave es SINTÉTICA y desechable. Se crea dentro de la carpeta de salida y
  el demo dice cuál usó. No es la clave publicada en KEYS.md, y este script no
  busca ni toca ninguna llave real.
* Nada se escribe bajo `docs/`.

Cada paso COMPRUEBA lo que muestra. Si algo no cuadra, sale 1.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPO = BASE.parent.parent
ESCRITO = BASE / "escrito_demo.md"
VERIFICADOR = BASE / "verificar_tercero.py"
KEYS = BASE / "KEYS.md"
PY = sys.executable

#: Lo que el escrito de demostración trae a propósito.
ESPERADO = {"total_citas": 6, "citas_verificadas": 4, "citas_fallidas": 2}

ANCHO = 72


class DemoFallido(Exception):
    pass


def exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise DemoFallido(mensaje)


def titulo(texto: str) -> None:
    print("\n" + texto)


def linea(texto: str = "") -> None:
    print("      " + texto if texto else "")


def _entorno(llave: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # La llave se pasa explícita: el demo no hereda ninguna del entorno.
    env["LEXO_CONTENT_SIGNING_KEY_PATH"] = str(llave)
    env.pop("LEXO_CUSTODY_SIGNING_KEY_PATH", None)
    return env


def _receta_openssl() -> str | None:
    """La receta sin Python, extraída de KEYS.md. No se copia aquí: si el
    documento cambia, el demo ejecuta lo que el documento diga."""
    bloques = re.findall(r"^```bash\n(.*?)^```", KEYS.read_text(encoding="utf-8"), flags=re.DOTALL | re.MULTILINE)
    recetas = [b for b in bloques if "openssl pkeyutl" in b]
    return recetas[0] if len(recetas) == 1 else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Demo de Diké: verificación de citas y commitment firmado.")
    ap.add_argument("--out", default=None, help="carpeta de salida, nueva o vacía (por defecto, una temporal)")
    args = ap.parse_args()

    if args.out:
        out = Path(args.out).expanduser().resolve()
        exigir(not out.exists() or (out.is_dir() and not any(out.iterdir())),
               f"--out {out} ya tiene contenido: el demo no sobrescribe nada")
        out.mkdir(parents=True, exist_ok=True)
    else:
        out = Path(tempfile.mkdtemp(prefix="dike-demo-"))
    exigir(BASE not in out.parents and out != BASE, "la salida del demo no puede quedar bajo docs/hackathon")
    kit = out / "kit"

    print("=" * ANCHO)
    print("DEMO — Diké: verifica antes de que firmes, y se niega a certificar")
    print("       lo que no puede probar")
    print("=" * ANCHO)
    linea(f"salida: {out}")

    # ── 1. El escrito ──
    titulo("[1/5] Un escrito con seis citas (sintético, partes ficticias)")
    escrito = out / "escrito_demo.md"
    shutil.copyfile(ESCRITO, escrito)
    for parrafo in escrito.read_text(encoding="utf-8").split("\n\n"):
        if re.match(r"(PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO)\.-", parrafo):
            linea(parrafo[: ANCHO - 9] + ("…" if len(parrafo) > ANCHO - 9 else ""))

    # ── La llave sintética (explícita) ──
    sys.path.insert(0, str(REPO))
    from lexo_cli.content_signing import generar_content_key  # noqa: E402

    llave, key_id = generar_content_key(out / "llave-sintetica" / "content-signing-key.pem")

    # ── 2. La constancia real, con commitment firmado ──
    titulo("[2/5] dike constancia --emit-commitment --sign (motor real, corpus local)")
    linea(f"llave SINTÉTICA de este demo: {llave.relative_to(out)}  (key_id {key_id})")
    linea("no es la clave publicada en KEYS.md")
    r = subprocess.run(
        [PY, "-m", "lexo_cli", "constancia", str(escrito), "--origen", "demanda laboral (demo)",
         "--json", "--emit-commitment", str(kit), "--sign"],
        capture_output=True, text=True, timeout=600, cwd=str(out), env=_entorno(llave),
    )
    linea(f"exit {r.returncode}")
    exigir(r.returncode == 1,
           f"se esperaba exit 1 (hay citas sin verificar) y salió {r.returncode}:\n{r.stderr[-800:]}")
    constancia = json.loads(r.stdout)
    meta = constancia["meta"]
    for campo, valor in ESPERADO.items():
        exigir(meta[campo] == valor, f"{campo}: se esperaba {valor}, la constancia dice {meta[campo]}")
    linea(f"citas en el escrito : {meta['total_citas']}")
    linea(f"verificadas         : {meta['citas_verificadas']}")
    linea(f"NO verificadas      : {meta['citas_fallidas']}")
    linea(f"corpus (pack_hash)  : {meta['pack_hash']}")

    # ── 3. Qué quedó en el commitment ──
    titulo("[3/5] El commitment que se firmó: lo que lleva y lo que no")
    c_path, s_path, p_path = kit / "commitment.json", kit / "commitment.sig.json", kit / "content-signing-key.pub"
    for f in (c_path, s_path, p_path):
        exigir(f.is_file(), f"no se escribió {f.name}")
    texto_c = c_path.read_text(encoding="utf-8")
    commitment = json.loads(texto_c)
    sobre = json.loads(s_path.read_text(encoding="utf-8"))
    linea(f"claves publicadas: {', '.join(sorted(commitment))}")
    for norma in commitment["normas_verificadas"]:
        linea(f"· {norma['gid']:<22} {norma['vigencia_legible']}")
    exigir(len(commitment["normas_verificadas"]) == ESPERADO["citas_verificadas"], "el commitment no trae las 4 verificadas")

    rechazadas = [d for d in constancia["detalles"] if d["estado"] != "VERIFICADA"]
    ausentes = {
        "ruta del escrito": str(escrito),
        "carpeta de salida": str(out),
        "origen anotado": "demanda laboral (demo)",
        **{f"cita rechazada «{d['cita_raw']}»": d["cita_raw"] for d in rechazadas},
        "art. 9999": "9999",
    }
    for que, cadena in ausentes.items():
        exigir(cadena not in texto_c, f"FUGA: {que} está en el commitment")
    # Los campos se buscan como CLAVES, a cualquier profundidad: el aviso del
    # propio commitment nombra `document_sha256` para decir que lo omitió.
    campos_ausentes = ("documento", "origen", "cita_raw", "problemas", "detalles",
                       "document_sha256", "document_bytes")

    def claves(nodo) -> set[str]:
        if isinstance(nodo, dict):
            return set(nodo) | {k for v in nodo.values() for k in claves(v)}
        if isinstance(nodo, list):
            return {k for v in nodo for k in claves(v)}
        return set()

    presentes = claves(commitment) & set(campos_ausentes)
    exigir(not presentes, f"FUGA: el commitment trae los campos {sorted(presentes)}")
    linea("comprobado que NO lleva: la ruta del escrito, el origen anotado, las dos citas")
    linea("  rechazadas, ni los campos " + ", ".join(campos_ausentes))
    exigir(sobre["key_id"] == key_id and sobre["role"] == "content-integrity", "el sobre no es de la llave del demo")
    linea(f"firma: Ed25519, rol {sobre['role']}, key_id {sobre['key_id']}")

    # ── 4. Un tercero lo verifica, por dos caminos ──
    titulo("[4/5] Verificación por un TERCERO, sin código de Diké")
    v = subprocess.run(
        [PY, str(VERIFICADOR), c_path.name, s_path.name, p_path.name],
        capture_output=True, text=True, cwd=str(kit),
    )
    exigir(v.returncode == 0 and "RESULTADO: VERIFICADO" in v.stdout, f"el verificador de tercero no verificó:\n{v.stdout[-600:]}")
    pasos = sum(1 for l in v.stdout.splitlines() if l.strip() in ("=> OK", "=> VÁLIDA"))
    linea(f"camino 1 (verificar_tercero.py)             {pasos} comprobaciones, RESULTADO: VERIFICADO")

    receta = _receta_openssl()
    faltan = [h for h in ("bash", "jq", "openssl", "sha256sum", "basenc") if shutil.which(h) is None]
    if receta is None or faltan:
        linea("camino 2 (jq + OpenSSL)  OMITIDO: " + ("falta " + ", ".join(faltan) if faltan else "no se halló la receta en KEYS.md"))
    else:
        o = subprocess.run(["bash", "-c", receta], capture_output=True, text=True, cwd=str(kit))
        exigir(o.returncode == 0 and "Signature Verified Successfully" in o.stdout + o.stderr,
               f"la receta OpenSSL de KEYS.md no verificó:\n{o.stdout}{o.stderr}")
        linea("camino 2 (jq + OpenSSL, receta de KEYS.md)  " + (o.stdout + o.stderr).strip().splitlines()[-1])

    # ── 5. Control negativo ──
    titulo("[5/5] Control negativo: se altera un número del commitment")
    alterado = out / "alterado"
    shutil.copytree(kit, alterado)
    falso = dict(commitment, citas_verificadas=commitment["citas_verificadas"] + 2, citas_fallidas=0)
    (alterado / "commitment.json").write_text(
        json.dumps(falso, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    linea("citas_verificadas 4 -> 6, citas_fallidas 2 -> 0  (como si todo hubiera pasado)")
    n = subprocess.run(
        [PY, str(VERIFICADOR), "commitment.json", "commitment.sig.json", "content-signing-key.pub"],
        capture_output=True, text=True, cwd=str(alterado),
    )
    linea(f"exit {n.returncode}")
    for l in n.stdout.splitlines():
        if "=>" in l and "OK" not in l:
            linea(l.strip())
    exigir(n.returncode == 1, f"el control negativo debía salir 1 y salió {n.returncode}")
    exigir("NO COINCIDE" in n.stdout, "el control negativo falló por un motivo que no es el hash")

    # ── Final: la abstención ──
    print("\n" + "=" * ANCHO)
    print("LO QUE DIKÉ SE NEGÓ A CERTIFICAR")
    print("=" * ANCHO)
    exigir(len(rechazadas) == ESPERADO["citas_fallidas"], "no hay dos citas rechazadas")
    motivos = {
        "AMBIGUOUS": "no dice de qué cuerpo legal es; ese número existe en más de un código",
        "UNRESOLVABLE": "esa norma no está en el corpus: no hay texto ni vigencia que verificar",
    }
    for d in rechazadas:
        print(f"  ✕ «{d['cita_raw']}»")
        print(f"      {d['resolucion']}: {motivos.get(d['resolucion'], 'no se pudo verificar')}")
    print()
    print(f"  Ninguna de las dos está en el commitment firmado. De ellas solo viaja")
    print(f"  un número: citas_fallidas = {commitment['citas_fallidas']}.")
    print(f"  Y las {commitment['citas_verificadas']} que sí pasaron prueban que la norma existe, es citable y")
    print("  está vigente. No que diga lo que el escrito le atribuye: eso no lo")
    print("  verifica Diké, y el commitment lo declara en su campo `alcance`.")
    print("=" * ANCHO)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DemoFallido as exc:
        print(f"\nDEMO FALLIDO: {exc}")
        sys.exit(1)
