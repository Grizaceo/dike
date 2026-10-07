"""Real engine, private plugin data, no productive home, no signing."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).parents[2]


@pytest.fixture(scope='module')
def real(tmp_path_factory):
    spec = importlib.util.spec_from_file_location('native_real', ROOT / 'hermes-plugin/__init__.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    data = tmp_path_factory.mktemp('native-data')
    m._carpeta_de_datos = lambda: data
    before = {k for k in sys.modules if k == 'lexo_cli' or k.startswith('lexo_cli.')}
    text = (ROOT / 'docs/hackathon/escrito_demo.md').read_text()
    first = json.loads(m.verificar_citas({'texto': text}))
    second = json.loads(m.verificar_citas({'texto': text}))
    after = {k for k in sys.modules if k == 'lexo_cli' or k.startswith('lexo_cli.')}
    assert before == after
    return m, data, first, second


def test_demo_real_cold_and_warm(real):
    for result in real[2:]:
        assert 'error' not in result, result
        assert result['meta']['pack_hash'] == 'ea28fa1c0f9af6c1'
        assert result['meta']['total_citas'] == 6
        assert result['meta']['citas_verificadas'] == 4
        assert result['meta']['citas_fallidas'] == 2
        assert result['todo_verificado'] is False
        assert result['problemas']


def test_installed_tamper_fails_closed(real):
    m, data, _, _ = real
    files = list((data / 'generations').glob('*/users/**/*'))
    victim = next(p for p in files if p.is_file() and p.suffix == '.json')
    original = victim.read_bytes()
    try:
        victim.write_bytes(original + b' ')
        result = json.loads(m.verificar_citas({'texto': 'artículo 161 del Código del Trabajo'}))
        assert 'integrity mismatch' in result.get('error', '')
        assert result['todo_verificado'] is False
    finally:
        victim.write_bytes(original)


def test_generated_copy_identical():
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/generar_hermes_plugin.py'), '--check'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
