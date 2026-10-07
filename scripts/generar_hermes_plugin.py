"""Build-time only: vendor the unchanged engine and corpus beside plugin.yaml."""
from pathlib import Path
import argparse
import shutil

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'hermes-plugin'
SOURCES = {'lexo_cli': ROOT / 'lexo_cli', 'shared': ROOT / 'shared',
           'dike_id': ROOT / 'packages/dike-id/python/src/dike_id'}


def expected_files():
    files = {}
    for name, source in SOURCES.items():
        for path in source.rglob('*'):
            rel = path.relative_to(source)
            if path.is_file() and not any(p in ('tests', '__pycache__', '.pytest_cache') for p in rel.parts) and path.suffix != '.pyc':
                files[Path('motor') / name / rel] = path
    for path in (ROOT / 'corpus').iterdir():
        if path.is_file():
            files[Path('corpus') / path.name] = path
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    expected = expected_files()
    actual = {p.relative_to(PLUGIN) for folder in ('motor', 'corpus')
              if (PLUGIN / folder).exists() for p in (PLUGIN / folder).rglob('*') if p.is_file()}
    if args.check:
        drift = actual != set(expected) or any(not (PLUGIN / rel).is_file() or (PLUGIN / rel).read_bytes() != src.read_bytes() for rel, src in expected.items())
        print('DRIFT' if drift else f'IDENTICAL: {len(expected)} files')
        return int(drift)
    for stale in actual - set(expected):
        (PLUGIN / stale).unlink()
    for rel, source in expected.items():
        target = PLUGIN / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    print(f'GENERATED: {len(expected)} files')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
