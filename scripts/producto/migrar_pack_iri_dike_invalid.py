"""Migra un pack starter sellado de la base `https://lexo.cl/` a `https://dike.invalid/` (ARCH-004).

`lexo.cl` es de un tercero. Este guion no reconstruye nada desde BCN: toma el
snapshot sellado tal cual y cambia solo la base de los IRI propios. Después
recalcula lo que depende de los bytes (MANIFEST, SNAPSHOT) y se niega a
entregar el resultado si:

- queda un solo byte `lexo.cl` en el pack;
- cambió el texto, el `textSha256` o el `eId` de algún artículo, o cambió el
  número de archivos;
- el validador, en modo estricto (`legado="rechazar"`), encuentra un error.

Uso:
    python scripts/producto/migrar_pack_iri_dike_invalid.py \\
        --desde <chile-base-….tar.gz | carpeta del pack> --hacia <carpeta nueva> [--tar <archivo .tar.gz>]

`--tar` empaqueta el resultado de forma determinista (orden por nombre, dueño
0:0, fecha fija, gzip sin marca de tiempo), igual que el tarball anterior.
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "lexo_cli" / "_vendor" / "tools"))

from starter_graph.iris import BASE, BASE_LEGADA  # noqa: E402
from starter_graph.update import snapshot_hash  # noqa: E402
from starter_graph.utils import canonical_json_bytes, distributable_files, sha256_bytes, sha256_file  # noqa: E402
from starter_graph.validate import export_turtle, validate_package  # noqa: E402

FECHA = "2026-10-14"
MTIME = 1791936000  # 2026-10-14T00:00:00Z: fecha fija de los miembros del tar


class Rechazo(Exception):
    pass


def _cambiar(valor):
    if isinstance(valor, str):
        return BASE + valor[len(BASE_LEGADA):] if valor.startswith(BASE_LEGADA) else valor.replace(BASE_LEGADA, BASE)
    if isinstance(valor, list):
        return [_cambiar(v) for v in valor]
    if isinstance(valor, dict):
        return {(_cambiar(k) if isinstance(k, str) else k): _cambiar(v) for k, v in valor.items()}
    return valor


def _raiz(carpeta: Path) -> Path:
    candidatos = [p.parent for p in carpeta.rglob("pack.json")]
    if len(candidatos) != 1:
        raise Rechazo(f"se esperaba un solo pack.json bajo {carpeta}, hay {len(candidatos)}")
    return candidatos[0]


def _articulos(raiz: Path) -> dict[str, tuple]:
    out = {}
    for p in sorted((raiz / "articulos").glob("*.json")):
        a = json.loads(p.read_bytes())
        out[p.name] = (a.get("text"), a.get("textSha256"), a.get("eId"))
    return out


def migrar(origen: Path, destino: Path) -> dict:
    if destino.exists():
        raise Rechazo(f"{destino} ya existe: no se sobrescribe")
    snap_origen = origen / "SNAPSHOT.json"
    snapshot_origen = json.loads(snap_origen.read_bytes()).get("snapshotHash") if snap_origen.is_file() else None
    shutil.copytree(origen, destino)

    cambiados = 0
    for p in sorted(destino.rglob("*")):
        if not p.is_file() or p.name in ("MANIFEST.json", "SNAPSHOT.json"):
            continue
        b = p.read_bytes()
        if BASE_LEGADA.encode() not in b and b"lexo.cl" not in b:
            continue
        if p.suffix in (".json", ".jsonld"):
            valor = json.loads(b)
            if canonical_json_bytes(valor) != b:
                raise Rechazo(f"{p.relative_to(destino)} no está en forma canónica: no se reescribe a ciegas")
            nuevo = canonical_json_bytes(_cambiar(valor))
        else:
            nuevo = b.replace(BASE_LEGADA.encode(), BASE.encode())
        p.write_bytes(nuevo)
        cambiados += 1

    # El informe de construcción anota la migración (es parte del árbol hasheado).
    informe_p = destino / "BUILD_REPORT.json"
    informe = json.loads(informe_p.read_bytes())
    # Sin nombrar el dominio anterior: el pack no lleva ni un byte de él. El
    # snapshot de origen basta para rastrearlo.
    informe["iriBaseMigration"] = {
        "to": BASE, "on": FECHA, "sourceSnapshotHash": snapshot_origen,
        "reason": "ARCH-004: la base anterior era un dominio de un tercero; cambian solo los IRI propios, no los textos ni sus hashes",
    }
    informe_p.write_bytes(canonical_json_bytes(informe))

    # El Turtle exportado se regenera con el exportador del propio motor y se
    # exige que coincida con el reemplazo: así se sabe que no hubo orden distinto.
    ttl = destino / "exports" / "graph.ttl"
    if ttl.is_file():
        with tempfile.TemporaryDirectory() as tmp:
            regenerado = Path(tmp) / "graph.ttl"
            export_turtle(destino, regenerado)
            if regenerado.read_bytes() != ttl.read_bytes():
                raise Rechazo("exports/graph.ttl regenerado no coincide con el migrado")

    # MANIFEST: la lista de archivos y su hash de núcleo, lo demás igual.
    man_p = destino / "MANIFEST.json"
    man = _cambiar(json.loads(man_p.read_bytes()))
    man["files"] = [{"path": p.relative_to(destino).as_posix(), "bytes": p.stat().st_size, "sha256": sha256_file(p)}
                    for p in distributable_files(destino)]
    nucleo = {k: v for k, v in man.items() if k != "manifestCoreSha256"}
    man["manifestCoreSha256"] = sha256_bytes(canonical_json_bytes(nucleo))
    man_p.write_bytes(canonical_json_bytes(man))

    snap_p = destino / "SNAPSHOT.json"
    nuevo_hash = snapshot_hash(destino)
    if snap_p.is_file():
        snap = json.loads(snap_p.read_bytes())
        snap["snapshotHash"] = nuevo_hash
        snap_p.write_bytes(canonical_json_bytes(snap))

    # Controles: nada de lexo.cl, los artículos intactos, el validador estricto.
    restos = [p.relative_to(destino).as_posix() for p in destino.rglob("*") if p.is_file() and b"lexo.cl" in p.read_bytes()]
    if restos:
        raise Rechazo(f"quedan {len(restos)} archivos con lexo.cl, por ejemplo {restos[:3]}")
    if _articulos(origen) != _articulos(destino):
        raise Rechazo("cambió el texto, el textSha256 o el eId de algún artículo")
    n_origen = sum(1 for p in origen.rglob("*") if p.is_file())
    n_destino = sum(1 for p in destino.rglob("*") if p.is_file())
    if n_origen != n_destino:
        raise Rechazo(f"cambió el número de archivos: {n_origen} → {n_destino}")
    reporte = validate_package(destino, legado="rechazar")
    if not reporte.ok:
        raise Rechazo("el validador estricto rechaza el pack: " + "; ".join(reporte.errors[:5]))
    return {
        "archivos_reescritos": cambiados, "archivos": n_destino, "articulos": len(_articulos(destino)),
        "snapshot_origen": snapshot_origen, "snapshot_nuevo": nuevo_hash, "advertencias": list(reporte.warnings),
    }


def empaquetar(carpeta: Path, salida: Path) -> str:
    """tar.gz determinista de `carpeta` (su nombre queda como raíz del archivo)."""
    crudo = io.BytesIO()
    with tarfile.open(fileobj=crudo, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for p in [carpeta, *sorted(carpeta.rglob("*"))]:
            info = tar.gettarinfo(str(p), arcname=p.relative_to(carpeta.parent).as_posix())
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = MTIME
            info.mode = 0o755 if p.is_dir() else 0o644
            if p.is_file():
                with p.open("rb") as f:
                    tar.addfile(info, f)
            else:
                tar.addfile(info)
    with salida.open("wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0, compresslevel=9) as gz:
        gz.write(crudo.getvalue())
    return sha256_file(salida)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--desde", type=Path, required=True)
    ap.add_argument("--hacia", type=Path, required=True)
    ap.add_argument("--tar", type=Path)
    a = ap.parse_args()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            if a.desde.is_file():
                with tarfile.open(a.desde) as t:
                    t.extractall(tmp, filter="data")
                origen = _raiz(Path(tmp))
            else:
                origen = _raiz(a.desde)
            a.hacia.mkdir(parents=True, exist_ok=True)
            destino = a.hacia / origen.name
            resultado = migrar(origen, destino)
        if a.tar:
            resultado["tar_sha256"] = empaquetar(destino, a.tar)
            resultado["tar"] = str(a.tar)
    except Rechazo as exc:
        print(f"NO SE MIGRA: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
