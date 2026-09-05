"""SHADOW policy proof with synthetic bytes only; no repository dataset I/O."""
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import json

import pandas as pd
import pytest

from src.data.engine import DataEngine
from src.data.scope import POLICY, VERSION, ScopeDenied, CAPABILITIES
from src.utils.hashing import file_hash


DEV = {'from': '2015-01-01T00:00:00Z', 'to_exclusive': '2020-01-01T00:00:00Z'}
PERIOD = {'from': '2016-01-04T12:00:00Z', 'to_exclusive': '2016-01-04T12:02:00Z'}
VALIDITY = {'from': '2026-09-01T00:00:00Z', 'to_exclusive': '2026-10-01T00:00:00Z'}
NOW = datetime(2026, 9, 4, tzinfo=timezone.utc)


def artifact(cid, period=PERIOD, fields=None, kind='dataset'):
    return dict(path=f'data/engine/shadow/{cid}/artifact.parquet', sha256='0' * 64,
                period=deepcopy(period), fields=fields or ['close'], kind=kind)


def manifest(cid='SC1-a', *, track='A', fields=None, capabilities=None):
    caps = capabilities or (['RESEARCH_PRICE'] if track == 'A' else ['XM_FORWARD_QUOTES'])
    period = PERIOD if track == 'A' else {
        'from': '2026-09-04T12:00:00Z', 'to_exclusive': '2026-09-04T12:02:00Z'}
    fields = fields or (['close'] if track == 'A' else ['bid', 'ask'])
    return dict(schema_version=VERSION, policy_version=POLICY, certificate_id=cid,
                revision=1, status='SHADOW_ELIGIBLE', track=track, capabilities=caps,
                instrument={'symbol': 'XAUUSD', 'definition_id': 'fixture:synthetic-gold'},
                period=deepcopy(period), fields=fields, environment='RESEARCH' if track == 'A' else 'DEMO',
                purposes=sorted({CAPABILITIES[c][1] for c in caps}), consumers=['fixture-reader'],
                partition='DEV' if track == 'A' else 'FORWARD_EXECUTION',
                provenance_references=[f'fixture:{cid}'], validity=deepcopy(VALIDITY),
                revocation_status='ACTIVE', parents=[], derivation='SYNTHETIC_FIXTURE',
                artifact=artifact(cid, period, fields))


def request(m):
    cap = m['capabilities'][0]
    return {k: deepcopy(m[k]) for k in ('certificate_id', 'instrument', 'period', 'fields', 'environment', 'partition')} | {
        'capability': cap, 'purpose': CAPABILITIES[cap][1], 'consumer': 'fixture-reader'}


def engine_at(root):
    (root / 'config').mkdir(parents=True, exist_ok=True)
    policy = dict(frozen=True, created_before_outcome_analysis=True, DEV=DEV,
                  VALIDATION={'from': DEV['to_exclusive'], 'to_exclusive': '2023-01-01T00:00:00Z'},
                  LOCKED_OOS={'from': '2023-01-01T00:00:00Z', 'to_exclusive': '2025-01-01T00:00:00Z'})
    (root / 'config/partitions_gold_m1_v2.json').write_text(json.dumps(policy))
    return DataEngine(root)


def write_fixture(engine, m):
    """Trusted test producer creates and hashes synthetic bytes before admission."""
    path = engine.root / m['artifact']['path']
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({f: [1.0, 2.0] for f in m['artifact']['fields']}).to_parquet(path, index=False)
    m['artifact']['sha256'] = file_hash(path)


def configure(engine, manifests, *, environment='RESEARCH', clock=None):
    engine.configure_scope_shadow(manifests, consumer='fixture-reader', environment=environment,
                                  clock=clock or (lambda: NOW))


@pytest.fixture
def ready(tmp_path):
    engine, m = engine_at(tmp_path), manifest()
    write_fixture(engine, m)
    configure(engine, [m])
    return engine, m, request(m)


def assert_denied_without_io(engine, r):
    cache = MagicMock()
    if engine._scope_shadow is not None:
        engine._scope_shadow._cache = cache
    # Tripwires cover path resolution, payload/hash, metadata and cache lookup.
    with patch.object(engine, '_path', side_effect=AssertionError('path before auth')) as paths, \
         patch('src.data.engine.file_hash', side_effect=AssertionError('hash before auth')) as hashes, \
         patch('src.data.engine.pq.read_table', side_effect=AssertionError('payload before auth')) as reads, \
         patch('src.data.engine.read_json', side_effect=AssertionError('manifest before auth')) as metadata, \
         patch('pathlib.Path.resolve', side_effect=AssertionError('resolve before auth')) as resolves:
        assert engine.authorize_scope_shadow(r)['decision'] == 'DENY'
        with pytest.raises(ScopeDenied):
            engine.read_scope_shadow(r)
        for spy in (paths, hashes, reads, metadata, resolves):
            spy.assert_not_called()
        assert cache.mock_calls == []


def test_allow_and_cache_reauthorize_before_access(ready):
    engine, m, r = ready
    assert engine.authorize_scope_shadow(r)['decision'] == 'ALLOW'
    with patch('src.data.engine.file_hash', wraps=file_hash) as hashes:
        first = engine.read_scope_shadow(r)
        assert first['close'].tolist() == [1.0, 2.0]
        assert hashes.call_count == 2
        first.loc[0, 'close'] = 999
        assert engine.read_scope_shadow(r)['close'].tolist() == [1.0, 2.0]
        assert hashes.call_count == 2


@pytest.mark.parametrize('field,value', [
    ('capability', 'UNKNOWN'), ('capability', 'RESEARCH_ML'),
    ('fields', ['open']), ('fields', ['spread']), ('fields', []),
    ('period', {'from': '2014-12-31T23:59:00Z', 'to_exclusive': PERIOD['to_exclusive']}),
    ('period', {'from': PERIOD['from'], 'to_exclusive': '2016-01-04T12:01:00Z'}),
    ('instrument', {'symbol': 'EURUSD', 'definition_id': 'fixture:synthetic-gold'}),
    ('instrument', {'symbol': 'XAUUSD', 'definition_id': 'another-contract'}),
    ('environment', 'LIVE'), ('purpose', 'ML'), ('consumer', 'rogue'),
    ('certificate_id', 'SC1-unknown'), ('certificate_id', '../raw'),
    ('certificate_id', 'DE1-' + '0' * 64),
    ('partition', 'VALIDATION'), ('partition', 'LOCKED_OOS'), ('partition', 'RAW'),
    ('partition', 'FORWARD_EXECUTION'), ('capability', []), ('period', None),
    ('period', {'from': '2016-01-04T12:00:00', 'to_exclusive': PERIOD['to_exclusive']}),
])
def test_request_denials_are_pre_io(ready, field, value):
    engine, _, r = ready
    r[field] = value
    assert_denied_without_io(engine, r)


@pytest.mark.parametrize('extra', ['raw_fallback', 'path', 'cache_id', 'filter', 'where', 'manifest', 'now', 'parent_override'])
def test_no_fallback_cache_or_filter_after_read_arguments(ready, extra):
    engine, _, r = ready
    r[extra] = True
    assert_denied_without_io(engine, r)


def test_missing_request_field_and_unconfigured_deny(ready, tmp_path):
    engine, _, r = ready
    del r['fields']
    assert_denied_without_io(engine, r)
    assert_denied_without_io(engine_at(tmp_path / 'unconfigured'), r)


@pytest.mark.parametrize('change', ['revoked', 'expired', 'future'])
def test_inactive_certificates(ready, tmp_path, change):
    _, m, r = ready
    engine = engine_at(tmp_path / change)
    if change == 'revoked':
        m['revocation_status'] = 'REVOKED'
    elif change == 'expired':
        m['validity']['to_exclusive'] = NOW.isoformat()
    else:
        m['validity']['from'] = '2026-09-05T00:00:00Z'
    configure(engine, [m])
    assert_denied_without_io(engine, r)


@pytest.mark.parametrize('change', ['missing', 'version', 'capability', 'raw_path', 'track', 'holdout', 'origin', 'legacy'])
def test_invalid_manifest_never_admitted(tmp_path, change):
    engine, m = engine_at(tmp_path), manifest()
    if change == 'missing': del m['provenance_references']
    if change == 'version': m['schema_version'] = 'future'
    if change == 'capability': m['capabilities'] = ['UNKNOWN']
    if change == 'raw_path': m['artifact']['path'] = 'data/engine/raw/secret.parquet'
    if change == 'track': m['capabilities'] = ['XM_FORWARD_QUOTES']
    if change == 'holdout': m['period'] = dict(from_='2023')
    if change == 'origin': m['provenance_references'] = ['provider:unverified']
    if change == 'legacy': m = dict(dataset_id='DE1-' + 'a' * 64, status='EXPLORATORY_ONLY')
    with patch.object(engine, '_path', side_effect=AssertionError('no paths')), \
         patch('src.data.engine.file_hash', side_effect=AssertionError('no hashes')):
        with pytest.raises(ScopeDenied): configure(engine, [m])
    assert engine._scope_shadow is None


@pytest.mark.parametrize('capability', [c for c, (track, _) in CAPABILITIES.items() if track == 'A'])
def test_each_research_capability_is_explicit_metadata_only(tmp_path, capability):
    engine, m = engine_at(tmp_path), manifest(capabilities=[capability])
    configure(engine, [m])
    assert engine.authorize_scope_shadow(request(m))['decision'] == 'ALLOW'
    # This test only evaluates policy: it never runs Discovery, ML or backtests.


def test_track_b_quotes_do_not_grant_research_or_fees(tmp_path):
    engine, m = engine_at(tmp_path), manifest(track='B')
    write_fixture(engine, m)
    configure(engine, [m], environment='DEMO')
    assert engine.read_scope_shadow(request(m)).columns.tolist() == ['bid', 'ask']
    for cap, field in [('RESEARCH_PRICE', 'close'), ('XM_OBSERVED_FEES', 'fees'), ('XM_EXECUTION_FILLS', 'fills')]:
        r = request(m); r.update(capability=cap, purpose=CAPABILITIES[cap][1], fields=[field])
        assert_denied_without_io(engine, r)


@pytest.mark.parametrize('year', [2016, 2020, 2023, 2024])
def test_track_b_cannot_relabel_existing_partitions(tmp_path, year):
    engine, m = engine_at(tmp_path), manifest(track='B')
    m['period'] = {'from': f'{year}-01-01T00:00:00Z', 'to_exclusive': f'{year}-01-02T00:00:00Z'}
    m['artifact']['period'] = deepcopy(m['period'])
    with pytest.raises(ScopeDenied): configure(engine, [m], environment='DEMO')


def test_a_cannot_certify_xm_cost_fields(tmp_path):
    engine, m = engine_at(tmp_path), manifest(fields=['close', 'spread', 'fees'])
    with pytest.raises(ScopeDenied, match='FIELD_SEMANTICS'): configure(engine, [m])


@pytest.mark.parametrize('operation', ['union', 'concat', 'copy', 'rename', 'cache', 'features', 'labels', 'experiences', 'model', 'select'])
def test_derivatives_intersect_every_dimension(tmp_path, operation):
    engine = engine_at(tmp_path)
    a = manifest('SC1-a', fields=['open', 'close'], capabilities=['RESEARCH_PRICE', 'RESEARCH_ML'])
    b = manifest('SC1-b')
    a['period']['from'] = '2016-01-04T11:00:00Z'
    a['consumers'].append('other-reader')
    a['validity']['from'] = '2026-08-01T00:00:00Z'
    configure(engine, [a, b])
    kind = operation if operation in {'cache', 'features', 'labels', 'experiences', 'model'} else 'dataset'
    child = engine.derive_scope_shadow('SC1-child', ['SC1-a', 'SC1-b'], operation, artifact('SC1-child', kind=kind))
    for k in ('fields', 'capabilities', 'purposes', 'consumers'):
        assert set(child[k]) == set(a[k]) & set(b[k])
    assert child['period']['from'] == '2016-01-04T12:00:00+00:00'
    assert child['validity']['from'] == '2026-09-01T00:00:00+00:00'
    assert set(child['provenance_references']) == {'fixture:SC1-a', 'fixture:SC1-b'}
    assert engine.authorize_scope_shadow(request(child))['decision'] == 'ALLOW'
    r = request(child); r['fields'] = ['open']
    assert_denied_without_io(engine, r)


def test_parent_revocation_blocks_cached_grandchild_and_new_derivation(tmp_path):
    engine, a = engine_at(tmp_path), manifest()
    configure(engine, [a])
    child = engine.derive_scope_shadow('SC1-child', ['SC1-a'], 'copy', artifact('SC1-child'))
    grand_artifact = artifact('SC1-grand')
    temp = dict(artifact=grand_artifact)
    write_fixture(engine, temp)
    grand = engine.derive_scope_shadow('SC1-grand', ['SC1-child'], 'cache', grand_artifact)
    assert len(engine.read_scope_shadow(request(grand))) == 2
    engine.revoke_scope_shadow('SC1-a')
    assert_denied_without_io(engine, request(grand))
    with pytest.raises(ScopeDenied, match='REVOKED'):
        engine.derive_scope_shadow('SC1-new', ['SC1-child'], 'rename', artifact('SC1-new'))
    with pytest.raises(ScopeDenied, match='ALREADY_CONFIGURED'): configure(engine, [a])


def test_parent_expiry_rechecked_on_cache_hit(tmp_path):
    clock = [NOW]
    engine, m = engine_at(tmp_path), manifest()
    write_fixture(engine, m)
    configure(engine, [m], clock=lambda: clock[0])
    engine.read_scope_shadow(request(m))
    clock[0] = datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert_denied_without_io(engine, request(m))


@pytest.mark.parametrize('change', ['unknown', 'revision', 'cycle', 'expanded_fields', 'expanded_period', 'expanded_consumers'])
def test_invalid_parent_or_widened_manifest_denied_at_admission(tmp_path, change):
    engine, a, b = engine_at(tmp_path), manifest(), manifest('SC1-b')
    b.update(parents=[{'certificate_id': 'SC1-a', 'revision': 1}], derivation='copy',
             provenance_references=['fixture:SC1-a', 'fixture:SC1-b'])
    if change == 'unknown': b['parents'][0]['certificate_id'] = 'SC1-missing'
    if change == 'revision': b['parents'][0]['revision'] = 2
    if change == 'cycle': b['parents'][0]['certificate_id'] = 'SC1-b'
    if change == 'expanded_fields': b['fields'].append('open')
    if change == 'expanded_period': b['period']['from'] = '2016-01-04T11:00:00Z'
    if change == 'expanded_consumers': b['consumers'].append('other')
    with pytest.raises(ScopeDenied): configure(engine, [a, b])


def test_cross_track_join_denied_and_no_new_id_bypass(tmp_path):
    engine, a, b = engine_at(tmp_path), manifest(), manifest('SC1-b', track='B')
    configure(engine, [a, b])
    with pytest.raises(ScopeDenied):
        engine.derive_scope_shadow('SC1-join', ['SC1-a', 'SC1-b'], 'union', artifact('SC1-join'))
    r = request(a); r['certificate_id'] = 'SC1-join'
    assert_denied_without_io(engine, r)


def test_trusted_manifest_and_derived_return_cannot_be_mutated_by_consumer(ready):
    engine, m, r = ready
    m['fields'].append('open')
    child = engine.derive_scope_shadow('SC1-child', ['SC1-a'], 'rename', artifact('SC1-child'))
    child['fields'].append('open')
    r = request(child)
    assert_denied_without_io(engine, r)


def test_tamper_and_missing_payload_fail_without_fallback(ready):
    engine, m, r = ready
    path = engine.root / m['artifact']['path']
    path.write_bytes(b'altered fixture')
    with patch('src.data.engine.pq.read_table', side_effect=AssertionError('no payload after failed hash')):
        with pytest.raises(ScopeDenied, match='INTEGRITY'): engine.read_scope_shadow(r)
    path.unlink()
    with pytest.raises(ScopeDenied, match='UNAVAILABLE'): engine.read_scope_shadow(r)


def test_resolved_path_redirect_cannot_read_raw(ready):
    engine, _, r = ready
    with patch.object(engine, '_path', return_value=engine.root / 'data/engine/raw/secret'), \
         patch('src.data.engine.file_hash', side_effect=AssertionError('no hash of redirected path')):
        with pytest.raises(ScopeDenied, match='REDIRECTION'): engine.read_scope_shadow(r)


@pytest.mark.parametrize('source', ['XM_LEGACY', 'HISTDATA'])
def test_exploratory_status_is_not_promoted(tmp_path, source):
    engine, m = engine_at(tmp_path), manifest()
    m.update(status='EXPLORATORY_ONLY', provenance_references=[f'fixture:{source}'])
    before = deepcopy(m)
    with pytest.raises(ScopeDenied, match='NOT_SHADOW_ELIGIBLE'): configure(engine, [m])
    assert m == before


def test_scoped_id_cannot_enter_v1_reader(ready):
    engine, m, _ = ready
    with patch('src.data.engine.read_json', side_effect=AssertionError('no old-contract metadata read')):
        with pytest.raises(PermissionError): engine.query(m['certificate_id'])
