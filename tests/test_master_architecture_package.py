import json
import pytest
from scripts.package_master_architecture import REQUIRED, build, package

@pytest.fixture
def master(tmp_path):
    root = tmp_path / 'master'
    for name in REQUIRED:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{}' if path.suffix == '.json' else '# Synthetic', encoding='utf-8')
    return root

def test_deterministic_and_preserves_snapshot(master, tmp_path):
    assert build(master) == build(master)
    out = tmp_path / 'snapshot'
    package(master, out)
    original = (out / 'AXXEL_MASTER_ARCHITECTURE_V2_UPDATED.zip').read_bytes()
    with pytest.raises(FileExistsError):
        package(master, out)
    assert (out / 'AXXEL_MASTER_ARCHITECTURE_V2_UPDATED.zip').read_bytes() == original

def test_missing_master_denied(master):
    (master / 'README.md').unlink()
    with pytest.raises(ValueError, match='MISSING_MASTER'):
        build(master)

def test_invalid_json_denied(master):
    (master / '13_STATE/AXXEL_STATE.json').write_text('{')
    with pytest.raises(json.JSONDecodeError):
        build(master)

def test_missing_reference_denied(master):
    (master / 'README.md').write_text('`00_START_HERE/MISSING.md`')
    with pytest.raises(ValueError, match='MISSING_CRITICAL_REFERENCE'):
        build(master)

def test_output_inside_master_denied(master):
    with pytest.raises(ValueError, match='OUTPUT_MUST_BE_OUTSIDE_SOURCE'):
        package(master, master / 'output')
