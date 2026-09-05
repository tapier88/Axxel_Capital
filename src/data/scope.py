"""FOUNDATION_SCOPE_READINESS_V1: pure metadata gates owned by DataEngine.

SHADOW only. The engine owner supplies trusted, already resident fixture metadata;
consumers supply requests/IDs, never manifests, paths, clocks or permissions.
There is no disk catalogue, provider integration, or production certificate issuer.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re
from threading import RLock

POLICY = 'FOUNDATION_SCOPE_READINESS_V1'
VERSION = 'AXXEL-SCOPE-1'
# No capability implies another. Purposes are bound to the capability, not a
# Cartesian product of whatever names a caller places in a request.
CAPABILITIES = {
    'RESEARCH_PRICE': ('A', 'DISCOVERY'),
    'RESEARCH_FEATURES': ('A', 'FEATURES'),
    'RESEARCH_LABELS': ('A', 'LABELS'),
    'RESEARCH_ML': ('A', 'ML'),
    'RESEARCH_WALK_FORWARD': ('A', 'WALK_FORWARD'),
    'RESEARCH_BACKTEST_PRICE': ('A', 'BACKTEST_PRICE'),
    'XM_FORWARD_QUOTES': ('B', 'EXECUTION_OBSERVATION'),
    'XM_SYMBOL_TERMS': ('B', 'EXECUTION_TERMS'),
    'XM_OBSERVED_FEES': ('B', 'EXECUTION_FEES'),
    'XM_EXECUTION_FILLS': ('B', 'EXECUTION_FILLS'),
}
# Canonical fields supported by this deliberately small SHADOW contract.
# New semantics require an explicit policy version, never an inferred grant.
PRICE_FIELDS = {'timestamp_utc', 'open', 'high', 'low', 'close', 'tick_volume', 'real_volume'}
CAPABILITY_FIELDS = {c: PRICE_FIELDS for c, (track, _) in CAPABILITIES.items() if track == 'A'}
CAPABILITY_FIELDS.update({
    'XM_FORWARD_QUOTES': {'bid', 'ask', 'spread', 'ticks', 'server_time', 'utc_reference'},
    'XM_SYMBOL_TERMS': {'symbol_specification', 'digits', 'point', 'contract_size', 'trading_sessions', 'swap', 'server_time', 'utc_reference'},
    'XM_OBSERVED_FEES': {'commission', 'fees', 'server_time', 'utc_reference'},
    'XM_EXECUTION_FILLS': {'fills', 'slippage', 'server_time', 'utc_reference'},
})
KINDS = {'dataset', 'features', 'labels', 'cache', 'experiences', 'model'}
OPERATIONS = {'select', 'union', 'concat', 'copy', 'rename', 'cache',
              'features', 'labels', 'experiences', 'model'}
REQUEST_KEYS = {'certificate_id', 'capability', 'instrument', 'period', 'fields',
                'environment', 'purpose', 'consumer', 'partition'}
MANIFEST_KEYS = {'schema_version', 'policy_version', 'certificate_id', 'revision',
                 'status', 'track', 'capabilities', 'instrument', 'period',
                 'fields', 'environment', 'purposes', 'consumers', 'partition',
                 'provenance_references', 'validity', 'revocation_status',
                 'parents', 'derivation', 'artifact'}


class ScopeDenied(PermissionError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__('DENY: ' + reason)


def deny(reason):
    raise ScopeDenied(reason)


def names(value):
    if (not isinstance(value, list) or not value or
            any(not isinstance(x, str) or not x or x.strip() != x for x in value) or
            len(set(value)) != len(value)):
        deny('INVALID_NAME_SET')
    return set(value)


def instant(value):
    if not isinstance(value, str):
        deny('INVALID_TIME')
    try:
        t = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        deny('INVALID_TIME')
    if t.tzinfo is None or t.utcoffset() is None:
        deny('NAIVE_TIME')
    return t.astimezone(timezone.utc)


def interval(value):
    if not isinstance(value, dict) or set(value) != {'from', 'to_exclusive'}:
        deny('INVALID_INTERVAL')
    start, end = instant(value['from']), instant(value['to_exclusive'])
    if start >= end:
        deny('EMPTY_OR_REVERSED_INTERVAL')
    return start, end


def contained(inner, outer):
    a, b = interval(inner); c, d = interval(outer)
    return c <= a and b <= d


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'SC1-[A-Za-z0-9_-]{1,80}', value):
        deny('UNKNOWN_CERTIFICATE')


def validate_manifest(m, dev_period, forward_floor):
    """No filesystem access, payload hashing, lazy callbacks or path resolution."""
    if not isinstance(m, dict) or set(m) != MANIFEST_KEYS:
        deny('MISSING_OR_UNKNOWN_MANIFEST_FIELD')
    if m['schema_version'] != VERSION or m['policy_version'] != POLICY:
        deny('UNKNOWN_MANIFEST_VERSION')
    identifier(m['certificate_id'])
    if type(m['revision']) is not int or m['revision'] != 1:
        deny('INVALID_REVISION')
    if m['status'] != 'SHADOW_ELIGIBLE':
        deny('NOT_SHADOW_ELIGIBLE')
    caps = names(m['capabilities'])
    if caps - CAPABILITIES.keys():
        deny('UNKNOWN_CAPABILITY')
    if m['track'] not in {'A', 'B'} or any(CAPABILITIES[c][0] != m['track'] for c in caps):
        deny('CROSS_TRACK')
    if m['partition'] != ('DEV' if m['track'] == 'A' else 'FORWARD_EXECUTION'):
        deny('PARTITION_DENIED')
    interval(m['period']); interval(m['validity'])
    if m['track'] == 'A' and not contained(m['period'], dev_period):
        deny('PARTITION_DENIED')
    if m['track'] == 'B' and (forward_floor is None or interval(m['period'])[0] < instant(forward_floor)):
        deny('FORWARD_CANNOT_RELABEL_HISTORICAL_PARTITIONS')
    for k in ('fields', 'consumers', 'provenance_references'):
        names(m[k])
    if not names(m['fields']) <= set.union(*(CAPABILITY_FIELDS[c] for c in caps)):
        deny('FIELD_SEMANTICS_NOT_CERTIFIED')
    if names(m['purposes']) != {CAPABILITIES[c][1] for c in caps}:
        deny('CAPABILITY_PURPOSE_MISMATCH')
    if (not isinstance(m['instrument'], dict) or
            set(m['instrument']) != {'symbol', 'definition_id'} or
            any(not isinstance(v, str) or not v for v in m['instrument'].values())):
        deny('INVALID_INSTRUMENT')
    if m['environment'] not in {'RESEARCH', 'PAPER', 'DEMO', 'LIVE'}:
        deny('INVALID_ENVIRONMENT')
    if (m['track'] == 'A') != (m['environment'] == 'RESEARCH'):
        deny('CROSS_TRACK_ENVIRONMENT')
    if m['revocation_status'] not in {'ACTIVE', 'REVOKED'}:
        deny('INVALID_REVOCATION_STATUS')
    if not isinstance(m['parents'], list) or len(m['parents']) > 32:
        deny('INVALID_PARENTS')
    seen = set()
    for p in m['parents']:
        if not isinstance(p, dict) or set(p) != {'certificate_id', 'revision'}:
            deny('INVALID_PARENT_REFERENCE')
        identifier(p['certificate_id'])
        if type(p['revision']) is not int or p['revision'] != 1 or p['certificate_id'] in seen:
            deny('INVALID_PARENT_REFERENCE')
        seen.add(p['certificate_id'])
    if m['parents']:
        if m['derivation'] not in OPERATIONS:
            deny('UNKNOWN_DERIVATION')
    elif m['derivation'] != 'SYNTHETIC_FIXTURE':
        deny('ROOTS_ARE_TRUSTED_FIXTURES_ONLY')
    if not m['parents'] and any(not r.startswith('fixture:') for r in m['provenance_references']):
        deny('ROOTS_ARE_TRUSTED_FIXTURES_ONLY')
    a = m['artifact']
    if not isinstance(a, dict) or set(a) != {'path', 'sha256', 'period', 'fields', 'kind'}:
        deny('INVALID_ARTIFACT')
    # String comparison only: never stat/resolve an attacker-supplied path.
    if a['path'] != f"data/engine/shadow/{m['certificate_id']}/artifact.parquet":
        deny('ARTIFACT_PATH_DENIED')
    if a['kind'] not in KINDS or (a['kind'] != 'dataset' and not m['parents']):
        deny('DERIVED_ARTIFACT_REQUIRES_PARENTS')
    if not isinstance(a['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', a['sha256']):
        deny('INVALID_ARTIFACT_DIGEST')
    if not contained(a['period'], m['period']) or not names(a['fields']) <= names(m['fields']):
        deny('ARTIFACT_EXCEEDS_SCOPE')


def assert_narrower(child, parent):
    for k in ('track', 'partition', 'instrument', 'environment'):
        if child[k] != parent[k]:
            deny('PARENT_SCOPE_MISMATCH')
    for k in ('capabilities', 'fields', 'purposes', 'consumers'):
        if not names(child[k]) <= names(parent[k]):
            deny('DERIVATION_EXPANDS_' + k.upper())
    for k in ('period', 'validity'):
        if not contained(child[k], parent[k]):
            deny('DERIVATION_EXPANDS_' + k.upper())
    if not names(parent['provenance_references']) <= names(child['provenance_references']):
        deny('PARENT_PROVENANCE_LOST')


class ScopeShadow:
    """An engine-local, resident control context, NOT a catalogue or issuer.

    Configure once by the trusted application/test owner. Consumer requests may
    never configure this context. Only fixture roots are admitted in this version.
    All operations share one lock so revocation cannot race a cache/payload read.
    """
    def __init__(self, manifests, *, consumer, environment, dev_period, forward_floor=None, clock=None):
        self.lock = RLock()
        self.consumer, self.environment = consumer, environment
        self.dev_period = deepcopy(dev_period)
        self.forward_floor = forward_floor
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._manifests = {}
        self._revoked = set()
        self._cache = {}
        if not isinstance(manifests, list) or len(manifests) > 256:
            deny('INVALID_METADATA_SET')
        # Admission is schema checking of preloaded metadata, never reading an ID.
        for m in deepcopy(manifests):
            validate_manifest(m, self.dev_period, self.forward_floor)
            cid = m['certificate_id']
            if cid in self._manifests:
                deny('DUPLICATE_CERTIFICATE')
            self._manifests[cid] = m
        for cid in self._manifests:
            self._graph(cid, check_time=False)

    def _graph(self, cid, *, check_time=True, stack=(), visited=None):
        identifier(cid)
        if cid not in self._manifests:
            deny('UNKNOWN_CERTIFICATE')
        if cid in stack or len(stack) >= 32:
            deny('INVALID_PARENT_GRAPH')
        visited = {} if visited is None else visited
        if cid in visited:
            return visited[cid]
        m = self._manifests[cid]
        validate_manifest(m, self.dev_period, self.forward_floor)
        if check_time:
            if cid in self._revoked or m['revocation_status'] == 'REVOKED':
                deny('REVOKED_CERTIFICATE')
            now = self.clock()
            if not isinstance(now, datetime) or now.tzinfo is None:
                deny('INVALID_CLOCK')
            start, end = interval(m['validity'])
            if now < start:
                deny('NOT_YET_VALID')
            if now >= end:
                deny('EXPIRED_CERTIFICATE')
        for ref in m['parents']:
            parent = self._graph(ref['certificate_id'], check_time=check_time,
                                 stack=(*stack, cid), visited=visited)
            if ref['revision'] != parent['revision']:
                deny('INVALID_PARENT_REVISION')
            assert_narrower(m, parent)
        visited[cid] = m
        return m

    def _authorize(self, request, *, physical=False):
        if not isinstance(request, dict) or set(request) != REQUEST_KEYS:
            deny('MISSING_OR_UNKNOWN_REQUEST_FIELD')
        r = request
        if r['capability'] not in CAPABILITIES:
            deny('UNKNOWN_CAPABILITY')
        if r['consumer'] != self.consumer or r['environment'] != self.environment:
            deny('PRINCIPAL_MISMATCH')
        if r['partition'] not in {'DEV', 'FORWARD_EXECUTION'}:
            deny('PARTITION_DENIED')
        requested = names(r['fields']); interval(r['period'])
        if not requested <= CAPABILITY_FIELDS[r['capability']]:
            deny('CAPABILITY_FIELD_DENIED')
        ancestors = {}
        m = self._graph(r['certificate_id'], visited=ancestors)
        for node in ancestors.values():
            if r['capability'] not in node['capabilities']:
                deny('CAPABILITY_NOT_CERTIFIED')
            if r['purpose'] != CAPABILITIES[r['capability']][1] or r['purpose'] not in node['purposes']:
                deny('PURPOSE_DENIED')
            if r['consumer'] not in node['consumers']:
                deny('CONSUMER_DENIED')
            for k in ('instrument', 'environment', 'partition'):
                if r[k] != node[k]:
                    deny(k.upper() + '_DENIED')
            if not requested <= names(node['fields']):
                deny('FIELD_NOT_CERTIFIED')
            if not contained(r['period'], node['period']):
                deny('PERIOD_DENIED')
        if physical:
            a = m['artifact']
            # No read-then-filter: this minimal reader admits a whole, pre-scoped
            # physical fragment, not a wider file with a proposed row predicate.
            if interval(r['period']) != interval(a['period']):
                deny('PHYSICAL_PERIOD_REQUIRES_EXACT_FRAGMENT')
            if not requested <= names(a['fields']):
                deny('FIELD_NOT_IN_ARTIFACT')
            for node in ancestors.values():
                if not names(a['fields']) <= names(node['fields']) or not contained(a['period'], node['period']):
                    deny('PHYSICAL_ARTIFACT_EXCEEDS_PARENT')
        return deepcopy(m)

    def authorize(self, request, *, physical=False):
        with self.lock:
            try:
                m = self._authorize(request, physical=physical)
                return {'decision': 'ALLOW', 'reason': 'FULL_SCOPE_VALIDATED',
                        'certificate_id': m['certificate_id'], 'policy_version': POLICY,
                        'mode': 'SHADOW'}
            except (ScopeDenied, TypeError, ValueError, KeyError, AttributeError) as e:
                return {'decision': 'DENY', 'reason': getattr(e, 'reason', 'MALFORMED_REQUEST'),
                        'policy_version': POLICY, 'mode': 'SHADOW'}

    def revoke(self, cid):
        with self.lock:
            identifier(cid)
            if cid not in self._manifests:
                deny('UNKNOWN_CERTIFICATE')
            self._revoked.add(cid)
            self._cache.clear()

    def derive(self, cid, parent_ids, operation, artifact):
        """Only narrowing; no root admission, promotion, transform or payload I/O."""
        with self.lock:
            identifier(cid)
            if cid in self._manifests:
                deny('DUPLICATE_CERTIFICATE')
            if operation not in OPERATIONS or not isinstance(parent_ids, list) or not parent_ids:
                deny('INVALID_DERIVATION')
            if len(parent_ids) != len(set(parent_ids)) or len(parent_ids) > 32:
                deny('INVALID_PARENTS')
            parents = [self._graph(p) for p in parent_ids]
            child = deepcopy(parents[0])
            for p in parents:
                if self.consumer not in p['consumers'] or self.environment != p['environment']:
                    deny('PRINCIPAL_MISMATCH')
                if any(p[k] != child[k] for k in ('track', 'partition', 'instrument', 'environment')):
                    deny('CROSS_TRACK_OR_CONTEXT_JOIN')
            for k in ('capabilities', 'fields', 'purposes', 'consumers'):
                child[k] = sorted(set.intersection(*(names(p[k]) for p in parents)))
                if not child[k]:
                    deny('EMPTY_PERMISSION_INTERSECTION')
            child['purposes'] = sorted({CAPABILITIES[c][1] for c in child['capabilities']})
            for k in ('period', 'validity'):
                start = max(interval(p[k])[0] for p in parents)
                end = min(interval(p[k])[1] for p in parents)
                if start >= end:
                    deny('EMPTY_PERMISSION_INTERSECTION')
                child[k] = {'from': start.isoformat(), 'to_exclusive': end.isoformat()}
            child.update(certificate_id=cid, revision=1, revocation_status='ACTIVE',
                         parents=[{'certificate_id': p['certificate_id'], 'revision': p['revision']} for p in parents],
                         derivation=operation, artifact=deepcopy(artifact),
                         provenance_references=sorted(set.union(*(names(p['provenance_references']) for p in parents))))
            validate_manifest(child, self.dev_period, self.forward_floor)
            for p in parents:
                assert_narrower(child, p)
            self._manifests[cid] = child
            return deepcopy(child)
