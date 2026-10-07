#!/usr/bin/env python3
"""Corre los dos caminos de KEYS.md con las herramientas de otras distribuciones.

`KEYS.md` dice en qué sistemas está probada su receta. Esto es lo que lo mide:
escribe en disco la batería del kit (`lexo_cli/tests/_kit_commitment.py`, un
caso por carpeta, con su veredicto esperado) más el kit real publicado, y en
un contenedor de cada distribución instala lo que el documento pide (`jq`,
OpenSSL, Python con `cryptography`) y ejecuta el camino 1 y el camino 2 sobre
cada caso, tal como están escritos.

    python scripts/hackathon/probar_en_contenedores.py
    python scripts/hackathon/probar_en_contenedores.py --imagenes debian:12-slim

Sale 0 si en todas las imágenes los dos caminos dan el veredicto esperado en
todos los casos; 1 si alguno no; 2 si no se pudo probar (sin docker, sin red
para instalar los paquetes).

Necesita docker y red (descarga la imagen y los paquetes). No es parte de la
suite: se corre a mano antes de exportar el kit, y cada vez que cambie la
receta. Las llaves de la batería son sintéticas; el kit real se copia tal cual
y solo se lee.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

IMAGENES = ("debian:12-slim", "ubuntu:22.04", "ubuntu:24.04")
CUATRO = ("commitment.json", "commitment.sig.json", "content-signing-key.pub", "verificar_tercero.py")

EN_EL_CONTENEDOR = r"""#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null 2>&1 \
  && apt-get install -y -qq --no-install-recommends jq openssl python3 python3-cryptography >/dev/null 2>&1 \
  || { echo "NO SE PUDO INSTALAR"; exit 9; }
. /etc/os-release
echo "$PRETTY_NAME | $(jq --version) | $(openssl version | cut -d' ' -f1-2) | $(sha256sum --version | head -1) | $(sed --version | head -1) | bash $BASH_VERSION | python $(python3 -c 'import sys, cryptography; print(sys.version.split()[0], "cryptography", cryptography.__version__)')"
total=0; mal=0
for d in /bateria/casos/*/; do
  caso=$(basename "$d"); esperado=$(cat "$d/ESPERADO"); total=$((total+1))
  w=$(mktemp -d); cp "$d"/commitment.json "$d"/commitment.sig.json "$d"/content-signing-key.pub "$d"/verificar_tercero.py "$w"/
  (cd "$w" && bash /bateria/camino1.sh >/dev/null 2>&1); c1=$?
  (cd "$w" && bash /bateria/camino2.sh >/dev/null 2>&1); c2=$?
  v1=no; [ $c1 = 0 ] && v1=verifica; v2=no; [ $c2 = 0 ] && v2=verifica
  if [ "$v1" != "$esperado" ] || [ "$v2" != "$esperado" ]; then
    mal=$((mal+1)); echo "  MAL $caso: esperado=$esperado camino1=$v1($c1) camino2=$v2($c2)"
  fi
  rm -rf "$w"
done
echo "  $total casos; no coinciden con lo esperado: $mal"
[ "$mal" = 0 ]
"""


def escribir_bateria(raiz: Path) -> int:
    """Un caso por carpeta, con `ESPERADO` («verifica» o «no»). Devuelve cuántos."""
    from lexo_cli.tests._kit_commitment import CARPETA_KIT, CASOS, Kit, debe_verificar

    (raiz / "casos").mkdir(parents=True)
    keys = (CARPETA_KIT / "KEYS.md").read_text(encoding="utf-8")
    bloques = re.findall(r"^```bash\n(.*?)^```", keys, flags=re.DOTALL | re.MULTILINE)
    camino1 = [b for b in bloques if "verificar_tercero.py" in b and "openssl" not in b]
    camino2 = [b for b in bloques if "openssl pkeyutl" in b]
    if len(camino1) != 1 or len(camino2) != 1:
        raise RuntimeError("KEYS.md no trae exactamente un bloque por cada camino")
    (raiz / "camino1.sh").write_text(camino1[0], encoding="utf-8")
    (raiz / "camino2.sh").write_text(camino2[0], encoding="utf-8")
    (raiz / "correr.sh").write_text(EN_EL_CONTENEDOR, encoding="utf-8")

    for i, caso in enumerate(sorted(CASOS)):
        k = Kit(raiz / "tmp" / f"k{i:03d}")
        CASOS[caso](k)
        d = raiz / "casos" / caso
        d.mkdir()
        for n in CUATRO:
            shutil.copyfile(k.raiz / n, d / n)
        (d / "ESPERADO").write_text("verifica\n" if debe_verificar(caso) else "no\n", encoding="utf-8")
    # El kit real publicado, si está completo: el ejemplo firmado con la llave real.
    if all((CARPETA_KIT / n).is_file() for n in CUATRO):
        real = raiz / "casos" / "00_kit_real_publicado"
        real.mkdir()
        for n in CUATRO:
            shutil.copyfile(CARPETA_KIT / n, real / n)
        (real / "ESPERADO").write_text("verifica\n", encoding="utf-8")
    shutil.rmtree(raiz / "tmp")
    return len(list((raiz / "casos").iterdir()))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--imagenes", nargs="+", default=list(IMAGENES))
    args = ap.parse_args()
    sys.dont_write_bytecode = True  # ni un .pyc nuevo en el perfil por correr este guion

    if shutil.which("docker") is None:
        print("falta docker: no se puede probar en otras distribuciones")
        return 2
    with tempfile.TemporaryDirectory(prefix="probar-en-contenedores-") as tmp:
        bateria = Path(tmp) / "bateria"
        print(f"{escribir_bateria(bateria)} casos escritos")
        peor = 0
        for imagen in args.imagenes:
            print(f"=== {imagen}")
            r = subprocess.run(
                ["docker", "run", "--rm", "-v", f"{bateria}:/bateria:ro", imagen, "bash", "/bateria/correr.sh"],
                capture_output=True, text=True, timeout=1200,
            )
            print((r.stdout + r.stderr).rstrip())
            if r.returncode == 9 or "NO SE PUDO INSTALAR" in r.stdout or (r.returncode != 0 and "casos;" not in r.stdout):
                peor = max(peor, 2)
            elif r.returncode != 0:
                peor = max(peor, 1)
    return peor


if __name__ == "__main__":
    sys.exit(main())
