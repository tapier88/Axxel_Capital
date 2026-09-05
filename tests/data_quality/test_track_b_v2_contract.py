"""Synthetic acceptance scenarios for the proposed design, NOT an active V2 worker."""
from copy import deepcopy
import pytest
from tests.data_quality.track_b_v2_contract_model import Contract, InjectedCrash

ROWS = [{'time_msc': 123, 'bid': 1}, {'time_msc': 123, 'bid': 2}, {'time_msc': 123, 'bid': 1}]


def test_host_suspend_preserves_observed_evidence_and_utc_gap():
    c = Contract()
    c.observe(20, utc_valid=False, host_event={'record_id': 42, 'state': 'SUSPEND'})
    c.observe(10820, utc_valid=True, host_event={'record_id': 43, 'state': 'RESUME'})
    b = c.capture(10820, ROWS)
    assert b['recovered'] and not b['eligible']
    assert len([e for e in c.d['events'] if e['kind'] == 'PARENT_OPEN']) == 1
    assert c.d['utc_gaps'] == [(20, 10820)]


def test_worker_paused_heartbeat_absence_does_not_invent_host_cause():
    c = Contract()
    c.heartbeat(10, pid=12, birth=1, phase='WAITING_API', boot='synthetic-boot')
    assert c.supervision(50, 10, alive=True) == 'OBSERVE_NO_KILL_NO_SECOND_WORKER'
    assert c.d['utc_open'] == 10
    assert not any(e['kind'] == 'HOST_OBSERVATION' for e in c.d['events'])
    assert c.d['events'][0]['phase'] == 'WAITING_API'


def test_hours_backlog_full_recovery_single_parent_persistent_label():
    c = Contract()
    now, recovered = 10800, []
    while now - c.d['cursor'] > 30:
        b = c.capture(now, ROWS)
        recovered.append(b)
        assert b['recovered']
        assert not b['eligible']
        assert c.supervision(now, now, alive=True) == 'CONTINUE_SAME_WORKER'
        now += 1
    assert len(recovered) > 180
    assert len({b['parent'] for b in recovered}) == 1
    assert len([e for e in c.d['events'] if e['kind'] == 'PARENT_OPEN']) == 1
    assert len([e for e in c.d['events'] if e['kind'] == 'PARENT_CLOSE']) == 1
    assert not c.capture(now, ROWS)['recovered']


def test_restart_during_backlog_keeps_parent_and_cursor():
    c = Contract()
    first = c.capture(7200, ROWS)
    d = Contract(deepcopy(c.d))
    second = d.capture(7201, ROWS)
    assert second['parent'] == first['parent'] and second['recovered']
    assert second['start'] == first['end'] - 2
    assert len([e for e in d.d['events'] if e['kind'] == 'PARENT_OPEN']) == 1


def test_utc_absent_never_validated_retrospectively():
    c = Contract()
    c.observe(0, utc_valid=False)
    first = c.capture(30, ROWS, utc_valid=False)
    c.observe(600, utc_valid=True)
    assert not first['eligible']
    assert not c.capture(600, ROWS)['eligible']
    assert not c.temporally_eligible(0, 599, True)
    assert c.temporally_eligible(600, 610, True)


def test_reconnect_is_child_not_parent_per_window():
    c = Contract()
    c.gap('DISCONNECT', 10)
    c.gap('RECONNECT_NEW_SESSION_SNAPSHOT_REQUIRED', 12)
    b = c.capture(300, ROWS)
    assert b['recovered'] and b['parent'] == 'P1'
    assert len([e for e in c.d['events'] if e['kind'] == 'PARENT_OPEN']) == 1


def test_repeated_timestamps_and_overlap_preserved():
    c = Contract()
    a, b = c.capture(30, ROWS), c.capture(60, ROWS)
    assert a['rows'] == b['rows'] == ROWS
    assert len(a['rows'] + b['rows']) == 6
    assert b['start'] == a['end'] - 2


def test_crash_raw_before_commit_preserves_orphan_no_cursor_advance():
    c = Contract()
    with pytest.raises(InjectedCrash):
        c.capture(30, ROWS, crash='raw')
    assert c.d['cursor'] == c.d['checkpoint'] == 0
    d = Contract(deepcopy(c.d))
    b = d.capture(60, ROWS)
    assert b['start'] == 0 and b['recovered']
    assert d.d['batches'][0]['rows'] == ROWS and not d.d['batches'][0]['committed']


@pytest.mark.parametrize('crash', ['commit', 'checkpoint'])
def test_restart_after_commit_and_checkpoint_recovery(crash):
    c = Contract()
    with pytest.raises(InjectedCrash):
        c.capture(30, ROWS, crash=crash)
    original = deepcopy(c.d['batches'][0])
    d = Contract(deepcopy(c.d))
    assert d.d['checkpoint'] == 1 and d.d['cursor'] == 30
    assert d.d['batches'][0] == original
    assert 'derived' not in original['marks']
    b = d.capture(60, ROWS)
    assert b['sequence'] == 2 and b['start'] == 28


def test_seven_stage_timestamps_are_separate_and_ordered():
    b = Contract().capture(30, ROWS)
    assert list(b['marks']) == ['request','raw','descriptor','manifest','commit','checkpoint','derived']
    assert list(b['marks'].values()) == sorted(set(b['marks'].values()))


@pytest.mark.parametrize('override', [dict(track='A'),dict(purpose='RESEARCH'),dict(purpose='ORDERS'),
    dict(purpose='FILLS'),dict(partition='VALIDATION'),dict(partition='LOCKED_OOS'),dict(environment='LIVE')])
def test_scope_denied(override):
    assert not Contract().authorize(**override)


@pytest.mark.parametrize('failure', [dict(disk_free=1),dict(identity_verified=False)])
def test_hard_limits_still_stop_before_request(failure):
    c = Contract()
    with pytest.raises(PermissionError):
        c.capture(7200, ROWS, **failure)
    assert c.d['batches'] == []


def test_corrupt_committed_raw_blocks_recovery():
    c = Contract()
    c.capture(30, ROWS)
    c.d['batches'][0]['rows'][0]['bid'] = 999
    with pytest.raises(PermissionError, match='INTEGRITY'):
        Contract(deepcopy(c.d))
