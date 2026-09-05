"""Executable DESIGN model only. No MT5, network, real clock, or capture entry point.

The durable store is simulated in memory; it is NOT proof of OS/fsync durability.
Production integration must independently pass these scenarios before a new T0.
"""
from copy import deepcopy
from hashlib import sha256
import json


class InjectedCrash(RuntimeError):
    pass


def digest(value):
    return sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class Contract:
    def __init__(self, durable=None):
        self.d = durable if durable is not None else {
            'events': [], 'batches': [], 'checkpoint': 0, 'cursor': 0,
            'parent': None, 'next_parent': 1, 'next_request': 1,
            'utc_gaps': [], 'utc_open': None, 'last_utc': 0,
        }
        self.reconcile()

    def event(self, kind, at, **fields):
        self.d['events'].append(dict(kind=kind, at=at, **fields))

    def gap(self, reason, at):
        if self.d['parent'] is None:
            self.d['parent'] = f"P{self.d['next_parent']}"
            self.d['next_parent'] += 1
            self.event('PARENT_OPEN', at, parent=self.d['parent'], reason=reason)
        self.event('RECOVERY_CHILD', at, parent=self.d['parent'], reason=reason)

    def observe(self, at, *, utc_valid, host_event=None):
        if host_event:
            self.event('HOST_OBSERVATION', at, evidence=host_event)
            self.gap('HOST_INTERRUPTION', at)
        if not utc_valid and self.d['utc_open'] is None:
            self.d['utc_open'] = at
            self.event('UTC_LOST', at)
        if utc_valid and self.d['utc_open'] is not None:
            self.d['utc_gaps'].append((self.d['utc_open'], at))
            self.d['utc_open'] = None
            self.event('UTC_RESUMED_NO_RETROACTIVE_VALIDATION', at)
        if utc_valid:
            self.d['last_utc'] = at

    def heartbeat(self, at, *, pid, birth, phase, boot):
        self.event('HEARTBEAT', at, pid=pid, process_birth=birth, phase=phase,
                   boot=boot, cursor=self.d['cursor'], checkpoint=self.d['checkpoint'],
                   parent=self.d['parent'])

    def supervision(self, now, last_heartbeat, *, alive, identity_verified=True):
        if not identity_verified:
            return 'STOP_REVIEW_IDENTITY'
        if alive and now - last_heartbeat > 30:
            self.gap('WORKER_HEARTBEAT_ABSENT_UNKNOWN_CAUSE', last_heartbeat)
            self.observe(last_heartbeat, utc_valid=False)
            return 'OBSERVE_NO_KILL_NO_SECOND_WORKER'
        return 'CONTINUE_SAME_WORKER' if alive else 'RECONCILE_BEFORE_RESTART'

    def temporally_eligible(self, start, end, utc_valid):
        if not utc_valid or self.d['utc_open'] is not None:
            return False
        return not any(start < b and end > a for a, b in self.d['utc_gaps'])

    def capture(self, now, rows, *, utc_valid=True, crash=None,
                disk_free=10 * 1024**3, identity_verified=True):
        if not identity_verified or disk_free < 5 * 1024**3:
            raise PermissionError('HARD_STOP_NO_SOURCE_REQUEST')
        lag = now - self.d['cursor']
        if lag < 0:
            raise PermissionError('CLOCK_REGRESSION')
        if lag > 120:
            self.gap('LAG_EXCEEDED', now)
            # No observations during the stall: current UTC cannot certify that gap.
            if self.d['last_utc'] < now:
                self.observe(self.d['last_utc'], utc_valid=False)
        self.observe(now, utc_valid=utc_valid)
        start = max(0, self.d['cursor'] - 2)
        end = min(now, start + 60)
        rid = self.d['next_request']
        self.d['next_request'] += 1
        recovered = self.d['parent'] is not None
        b = dict(id=rid, start=start, end=end, rows=deepcopy(rows), parent=self.d['parent'],
                 recovered=recovered, eligible=False, marks={}, committed=False)
        self.d['batches'].append(b)
        b['marks']['request'] = now
        b['marks']['raw'] = now + .001
        if crash == 'raw':
            raise InjectedCrash('RAW_PRESERVED_NO_COMMIT')
        # Each clock here is a synthetic completion observation, not filesystem mtime.
        b['marks']['descriptor'] = now + .002
        b['eligible'] = self.temporally_eligible(start, end, utc_valid)
        b['marks']['manifest'] = now + .003
        b['raw_digest'] = digest(rows)
        b['sequence'] = sum(x['committed'] for x in self.d['batches']) + 1
        b['previous'] = next((x['digest'] for x in reversed(self.d['batches'][:-1]) if x['committed']), None)
        b['digest'] = digest({k: b[k] for k in ('id','start','end','raw_digest','sequence','previous','recovered','parent','eligible')})
        b['marks']['commit'] = now + .004
        b['committed'] = True
        if crash == 'commit':
            raise InjectedCrash('COMMIT_DURABLE_CHECKPOINT_STALE')
        self.d['checkpoint'] = b['sequence']
        self.d['cursor'] = end
        b['marks']['checkpoint'] = now + .005
        if crash == 'checkpoint':
            raise InjectedCrash('CHECKPOINT_DURABLE_DERIVED_MISSING')
        b['marks']['derived'] = now + .006
        if recovered:
            self.event('RECOVERY_BATCH_COMMITTED', now, parent=b['parent'], batch=rid)
        if now - end <= 30 and self.d['parent'] is not None:
            self.event('PARENT_CLOSE', now, parent=self.d['parent'])
            self.d['parent'] = None
        return b

    def reconcile(self):
        previous, seq = None, 0
        for b in self.d['batches']:
            if not b['committed']:
                self.gap('ORPHAN_RAW_PRESERVED', b['marks']['raw'])
                continue
            seq += 1
            core = {k: b[k] for k in ('id','start','end','raw_digest','sequence','previous','recovered','parent','eligible')}
            if (b['sequence'] != seq or b['previous'] != previous or digest(b['rows']) != b['raw_digest']
                    or digest(core) != b['digest']):
                raise PermissionError('CHAIN_INTEGRITY_STOP')
            previous = b['digest']
            if self.d['checkpoint'] < seq:
                self.d['checkpoint'], self.d['cursor'] = seq, b['end']
                self.event('CHECKPOINT_RECONSTRUCTED_FROM_COMMIT', b['marks']['commit'], batch=b['id'])
            # Recovery has its own event time; never backdate a missing stage timestamp.
            if 'derived' not in b['marks']:
                self.event('DERIVED_REBUILD_REQUIRED', b['marks']['commit'], batch=b['id'])
        if self.d['checkpoint'] > seq:
            raise PermissionError('CHECKPOINT_AHEAD_OF_COMMIT')

    def authorize(self, *, track='B', purpose='AUDIT', partition='FORWARD_EXECUTION', environment='DEMO'):
        return (track, purpose, partition, environment) == ('B', 'AUDIT', 'FORWARD_EXECUTION', 'DEMO')
