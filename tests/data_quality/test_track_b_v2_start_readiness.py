"""Negative start checks only. K--N are never executed or simulated as effects."""
import ast
import json
from pathlib import Path
import socket

import pytest

from src.data.engine import DataEngine
from src.data.track_b_forward_capture import CaptureDenied

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('missing', [None, *'ABCDEFGHIJ'])
def test_readiness_claims_cannot_enable_current_market_entry(monkeypatch, tmp_path, missing):
    def forbidden(*args, **kwargs):
        raise AssertionError('Network must not be reached by the denied start')
    monkeypatch.setattr(socket, 'socket', forbidden)
    # Untrusted claims (including a purported human token) cannot grant authority.
    monkeypatch.setenv('TRACK_B_START_AUTHORIZED', 'true')
    worker = DataEngine(ROOT).track_b_forward_capture_v2()
    worker.readiness_claims = {stage: True for stage in 'ABCDEFGHIJ' if stage != missing}
    with pytest.raises(CaptureDenied, match='MARKET_CAPTURE'):
        worker.start_market_capture()
    assert worker.base is None and worker.origin is None and not worker.opened
    assert not list(tmp_path.iterdir())


def test_no_t0_or_market_effect_is_implemented_in_start_method():
    tree = ast.parse((ROOT / 'src/data/track_b_forward_capture_v2.py').read_text(encoding='utf-8-sig'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'TrackBForwardCaptureV2')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'start_market_capture')
    assert len(method.body) == 1 and isinstance(method.body[0], ast.Raise)
    calls = [n.func for n in ast.walk(method) if isinstance(n, ast.Call)]
    assert len(calls) == 1 and isinstance(calls[0], ast.Name) and calls[0].id == 'CaptureDenied'


def test_frozen_start_restrictions_are_unchanged():
    config = json.loads((ROOT / 'config/track_b_xm_forward_capture_v2.json').read_bytes())
    assert config['activation_authorized'] is False and config['t0'] is None
    assert config['market_capture'] == 'NOT_AUTHORIZED'
    assert config['storage_v2']['exact_root'] is None
    assert config['scope']['orders_authorized'] is False
    assert config['scope']['fills_authorized'] is False
    assert config['scope']['research_authorized'] is False
