"""Copia de trabajo del perfil para probar cambios sin tocar el árbol real.

La usan la batería de mutación y el ensayo de «clon limpio» del demo. Arma una
raíz temporal donde `lexo_cli/` y `docs/hackathon/` son COPIAS reales (se pueden
mutar) y el resto del perfil son enlaces simbólicos (no se copian 16 GB).

Por qué `lexo_cli` no puede ser un enlace: con un enlace, `Path(__file__).resolve()`
salta al árbol real y la copia mutada nunca se ejecuta.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

#: Lo que se copia de verdad. Todo lo demás del primer nivel se enlaza.
_COPIAS = ("lexo_cli", "docs")
_OMITIR = {".git", "cache", "__pycache__", ".pytest_cache"}


def _ignorar(_dir: str, nombres: list[str]) -> set[str]:
    return {n for n in nombres if n == "__pycache__" or n.endswith(".pyc")}


def crear(raiz: Path, *, origen: Path = REPO) -> Path:
    """Crea la copia en `raiz` (que no debe existir) y la devuelve."""
    raiz = Path(raiz)
    raiz.mkdir(parents=True)
    for entrada in sorted(origen.iterdir()):
        if entrada.name in _OMITIR:
            continue
        destino = raiz / entrada.name
        if entrada.name == "lexo_cli":
            shutil.copytree(entrada, destino, ignore=_ignorar, symlinks=True)
        elif entrada.name == "docs":
            # docs/hackathon se copia; el resto de docs/ se enlaza.
            destino.mkdir()
            for sub in sorted(entrada.iterdir()):
                if sub.name == "hackathon":
                    shutil.copytree(
                        sub, destino / sub.name, symlinks=True,
                        ignore=lambda d, ns: _ignorar(d, ns) | ({"scratch"} & set(ns)),
                    )
                else:
                    os.symlink(sub, destino / sub.name)
        else:
            os.symlink(entrada, destino)
    return raiz


def entorno(raiz: Path, tmp: Path) -> dict[str, str]:
    """Entorno hermético para correr pytest o el CLI dentro de la copia."""
    tmp.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(raiz),
        "TMPDIR": str(tmp),
        "DIKE_ROOTS_CACHE_DIR": str(tmp / "roots_cache"),
    })
    # La llave real nunca entra a un ensayo.
    env.pop("LEXO_CONTENT_SIGNING_KEY_PATH", None)
    env.pop("LEXO_CUSTODY_SIGNING_KEY_PATH", None)
    return env
