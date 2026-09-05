"""Integrated V2 tests: only injected arrays and local temporary storage."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace

import numpy as np
import pytest

from src.data.engine import DataEngine
from src.data.track_b_forward_capture import CaptureDenied
from src.data.track_b_forward_capture_v2 import TrackBForwardCaptureV2, WindowsHostObserver, encoded, digest, read

ROOT=Path(__file__).resolve().parents[2]
ORIGIN=datetime(2035,1,1,tzinfo=timezone.utc)  # synthetic control time, never operational T0
ROWS=np.array([(123,1.,2.),(123,2.,3.),(123,1.,2.)],dtype=[('time_msc','<i8'),('bid','<f8'),('ask','<f8')])


class FakeClock:
    def __init__(self):self.seconds=0
    def now(self):return ORIGIN+timedelta(seconds=self.seconds)
    def monotonic(self):return self.seconds
    def advance(self,n):self.seconds+=n


class Reference:
    def __init__(self,clock):self.clock=clock;self.available=True;self.age=0
    def measure(self):
        return {'available':self.available,'measured_at':(self.clock.now()-timedelta(seconds=self.age)).isoformat(),
                'uncertainty_milliseconds':5,'source_disagreement_milliseconds':1,'samples_count':1}


class Source:
    synthetic_only=True
    def __init__(self):self.calls=0;self.responses=[];self.entered=threading.Event();self.release=None;self.sessions=0
    def open(self):
        self.sessions+=1
        return {'server':'XMGlobal-MT5 6','account_mode':'DEMO','broker':'XM Synthetic',
                'account_fingerprint_sha256':'fixture-account','session_id':str(self.sessions)}
    def close(self):pass
    def reconnect(self):return self.open()
    def symbol_specification(self):return {'name':'GOLD','digits':2,'point':.01,'fixture':True}
    def copy_ticks(self,start,end):
        self.calls+=1;self.entered.set()
        if self.release is not None:self.release.wait(20)
        value=self.responses.pop(0) if self.responses else ROWS.copy()
        if isinstance(value,Exception):raise value
        return value


class Observer:
    def __init__(self):self.events=[]
    def poll(self,after_record_id=0):
        return [e for e in self.events if e.get('EventRecordID',0)>after_record_id]


@pytest.fixture
def setup(tmp_path):
    clock=FakeClock();source=Source();ref=Reference(clock);obs=Observer()
    w=DataEngine(ROOT).track_b_forward_capture_v2(storage_root=tmp_path/'tb2',source=source,
        utc_reference=ref,synthetic_origin=ORIGIN,clock=clock,observer=obs,
        disk_usage=lambda _:SimpleNamespace(free=20*1024**3))
    w.open(background=False)
    yield w,source,clock,ref,obs
    if w.opened:w.close()


def reopened(w,source,clock,ref,obs):
    return DataEngine(ROOT).track_b_forward_capture_v2(storage_root=w.base,source=source,
        utc_reference=ref,synthetic_origin=ORIGIN,clock=clock,observer=obs,
        disk_usage=lambda _:SimpleNamespace(free=20*1024**3))


def descriptor(w,result):return read(w.base/'batches'/result['batch_id']/'descriptor.json')


def test_inert_factory_and_market_start_denied():
    w=DataEngine(ROOT).track_b_forward_capture_v2()
    with pytest.raises(CaptureDenied,match='MARKET_CAPTURE'):w.start_market_capture()
    with pytest.raises(CaptureDenied,match='SYNTHETIC'):w.open()
    assert w.base is None


def test_three_hour_backlog_full_recovery_single_episode(setup):
    w,s,c,ref,obs=setup
    # Backlog exists at startup; no-progress watchdog must NOT be weakened to
    # permit a live worker that has already exceeded its 15-minute stop budget.
    w.close();c.advance(10800);w=reopened(w,s,c,ref,obs).open(background=False)
    flags=[];parents=[]
    while (c.now()-w.cursor).total_seconds()>30:
        result=w.capture_once();d=descriptor(w,result)
        flags.append(d['recovered_after_gap']);parents.append(d['parent'])
        assert result['status'] in ('RECOVERING','NORMAL')
        if datetime.fromisoformat(d['request']['from'])<ORIGIN+timedelta(seconds=10800):
            assert not d['temporal_eligible']
        c.advance(1)
    assert len(flags)>180 and all(flags) and len(set(parents))==1
    assert sum(e['kind']=='PARENT_OPEN' for e in w.events)==1
    assert sum(e['kind']=='PARENT_CLOSE' for e in w.events)==1
    assert not w.capture_once()['recovered_after_gap']
    assert s.sessions==2
    assert not any('BACKPRESSURE_STOP_REQUIRED' in str(e) for e in w.events)
    w.close()


def test_restart_during_recovery_keeps_parent(setup):
    w,s,c,ref,obs=setup;c.advance(600);a=w.capture_once();parent=w.parent;w.close()
    other=reopened(w,s,c,ref,obs).open(background=False)
    try:
        b=other.capture_once();assert descriptor(other,b)['parent']==parent
        assert b['recovered_after_gap']
        assert sum(e['kind']=='PARENT_OPEN' for e in other.events)==1
    finally:other.close()


@pytest.mark.parametrize('kind',['SLEEP','RESUME'])
def test_host_events_observed_without_utc_substitution(setup,kind):
    w,s,c,ref,obs=setup;c.advance(60);ref.available=False
    obs.events=[{'status':'OBSERVED','kind':kind,'provider':'fixture-Windows','EventRecordID':1,
                 'event_time':c.now().isoformat(),'raw_xml':'<synthetic/>'}]
    w.observe_host();w.observe_host()
    assert sum(e['kind']=='HOST_EVENT' for e in w.events)==1
    b=w.capture_once();assert b['recovered_after_gap'] and not b['temporal_eligible']


def test_worker_pause_heartbeat_missing_unknown_cause(setup):
    w,s,c,ref,obs=setup;c.advance(31);w.heartbeat_once()
    assert any(e['kind']=='RECOVERY_CHILD' and e['detail'].get('cause')=='UNKNOWN' for e in w.events)
    assert not any(e['kind']=='HOST_EVENT' for e in w.events)
    h=[e for e in w.events if e['kind']=='HEARTBEAT'][-1]['detail']
    assert {'pid','process_creation_time','worker_instance_id','boot_id','phase','cursor',
        'last_committed_sequence','last_progress','local_wall','monotonic','utc_state','disk_state'}<=h.keys()


@pytest.mark.parametrize('bad',['missing','stale'])
def test_utc_fail_closed_no_retroactive_repair(setup,bad):
    w,s,c,ref,obs=setup;c.advance(30)
    if bad=='missing':ref.available=False
    else:ref.age=6
    b=w.capture_once();before=(w.base/'batches'/b['batch_id']/'descriptor.json').read_bytes()
    assert not b['temporal_eligible']
    ref.available=True;ref.age=0;c.advance(1);w.sample_utc()
    assert (w.base/'batches'/b['batch_id']/'descriptor.json').read_bytes()==before
    assert not w.temporal_ok(ORIGIN,ORIGIN+timedelta(seconds=30))


def test_reconnect_retries_children(setup):
    w,s,c,ref,obs=setup;s.responses=[None,None,None];c.advance(30)
    b=w.capture_once()
    assert s.sessions==2 and b['recovered_after_gap']
    assert sum(e['kind']=='PARENT_OPEN' for e in w.events)==1
    assert any(e['kind']=='RECONNECT' and e['parent']==w.parent for e in w.events)
    assert len(list((w.base/'batches'/b['batch_id']).glob('attempt-*.json')))==3


def test_repeated_timestamps_duplicate_responses_preserved(setup):
    w,s,c,ref,obs=setup;c.advance(30);a=w.capture_once();c.advance(30);b=w.capture_once()
    for result in (a,b):
        arr=np.load(w.base/'batches'/result['batch_id']/'attempt-1.npy',allow_pickle=False)
        assert arr.dtype==ROWS.dtype and np.array_equal(arr,ROWS)
        df=w.read_derived(result['batch_id'],{'track':'B','partition':'FORWARD_EXECUTION','purpose':'FORWARD_CAPTURE_AUDIT','environment':'DEMO'})
        assert len(df)==3 and list(df.response_index)==[0,1,2]


@pytest.mark.parametrize('point',['after_raw','after_commit','after_checkpoint'])
def test_fault_reconciliation(setup,point):
    w,s,c,ref,obs=setup;c.advance(30)
    def fault(p):
        if p==point:raise RuntimeError('injected-'+point)
    w.fault=fault
    with pytest.raises(RuntimeError,match='injected'):w.capture_once()
    originals={p:p.read_bytes() for p in w.base.rglob('*') if p.is_file() and p.name!='instance.lock'}
    w.close();other=reopened(w,s,c,ref,obs).open(background=False)
    try:
        if point=='after_raw':
            assert other.sequence==0 and other.cursor==ORIGIN
            assert len(list((w.base/'staging').glob('TB2-*')))==1
        else:
            assert other.sequence==1 and other.cursor==ORIGIN+timedelta(seconds=30)
            assert len(list((w.base/'derived').glob('*.parquet')))==1
        assert all(p.read_bytes()==b for p,b in originals.items())
        other.capture_once()
    finally:other.close()


def test_missing_checkpoint_reconstructed(setup):
    w,s,c,ref,obs=setup;c.advance(30);w.capture_once()
    cp=w.base/'journal/000000001.json';before=cp.read_bytes();cp.unlink() # synthetic fault injection
    w.reconcile();assert cp.read_bytes()==before


def test_checkpoint_without_commit_denied(setup):
    w,s,c,ref,obs=setup
    w.publish(w.base/'journal/000000001.json',encoded({'sequence':1}))
    with pytest.raises(CaptureDenied,match='CHECKPOINT_WITHOUT'):w.reconcile()


@pytest.mark.parametrize('fault',['raw','fork','commit'])
def test_corruption_blocks_before_recovery(setup,fault):
    w,s,c,ref,obs=setup;c.advance(30);b=w.capture_once();p=w.base/'batches'/b['batch_id']
    if fault=='raw':(p/'attempt-1.npy').write_bytes(b'corrupted fixture')
    elif fault=='commit':(p/'COMMIT.json').write_bytes(encoded({'hash':'wrong'}))
    else:
        import shutil
        other=w.base/'batches/TB2-fork';shutil.copytree(p,other)
        m=read(other/'manifest.json');m['batch']='TB2-fork';(other/'manifest.json').write_bytes(encoded(m))
        co={'schema':'TB2-COMMIT','manifest_hash':digest((other/'manifest.json').read_bytes()),'batch':'TB2-fork'}
        co['hash']=digest(encoded(co));(other/'COMMIT.json').write_bytes(encoded(co))
    with pytest.raises(CaptureDenied):w.reconcile()


def test_stage_receipts_fsync_order(setup):
    w,s,c,ref,obs=setup;c.advance(30);w.capture_once()
    receipts=[e['detail'] for e in w.events if e['kind']=='STAGE_RECEIPT']
    stages=[d['stage'] for d in receipts]
    assert set(stages)=={'request','raw','descriptor','manifest','commit','checkpoint','derived'}
    assert stages.index('raw')<stages.index('descriptor')<stages.index('manifest')<stages.index('commit')<stages.index('checkpoint')<stages.index('derived')
    for d in receipts:
        assert set(d['start'])==set(d['end'])=={'local_wall','monotonic','boot_id','utc_reference'}
        assert d['start']['monotonic']<=d['end']['monotonic']


def test_second_worker_denied(setup):
    w,s,c,ref,obs=setup;other=reopened(w,s,c,ref,obs)
    with pytest.raises(CaptureDenied,match='SECOND_WORKER'):other.open(background=False)


def test_disk_threshold_before_source(setup):
    w,s,c,ref,obs=setup;w.disk=lambda _:SimpleNamespace(free=1)
    with pytest.raises(CaptureDenied,match='DISK_THRESHOLD'):w.capture_once()
    assert s.calls==0


def test_storage_failure_no_checkpoint(setup):
    w,s,c,ref,obs=setup;c.advance(30);publish=w.publish
    def fail(path,payload):
        if path.suffix=='.npy':raise OSError('injected disk write failure')
        return publish(path,payload)
    w.publish=fail
    with pytest.raises(CaptureDenied,match='STORAGE_FAILURE'):w.capture_once()
    assert w.sequence==0 and list((w.base/'staging').glob('TB2-*'))


def test_api_blocked_heartbeat_and_single_inflight(setup):
    w,s,c,ref,obs=setup;s.release=threading.Event();c.advance(30)
    errors=[]
    def run():
        try:w.capture_once()
        except Exception as exc:errors.append(exc)
    t=threading.Thread(target=run);t.start();assert s.entered.wait(2)
    with pytest.raises(CaptureDenied,match='IN_FLIGHT'):w.capture_once()
    with pytest.raises(CaptureDenied,match='IN_FLIGHT'):w.close()
    try:
        c.advance(5);w.heartbeat_once()
        assert [e for e in w.events if e['kind']=='HEARTBEAT'][-1]['detail']['phase']=='WAITING_API'
    finally:
        s.release.set();t.join(5)
    assert not errors and not t.is_alive()


def test_revocation_denies_capture(setup):
    w,s,c,ref,obs=setup;w.revoke('fixture')
    with pytest.raises(CaptureDenied,match='REVOKED'):w.capture_once()
    assert s.calls==0


@pytest.mark.parametrize('field,value',[('track','A'),('purpose','research'),('partition','VALIDATION'),('partition','LOCKED_OOS')])
def test_scope_denied_before_payload_io(setup,field,value):
    w,s,c,ref,obs=setup
    request={'track':'B','partition':'FORWARD_EXECUTION','purpose':'FORWARD_CAPTURE_AUDIT','environment':'DEMO'};request[field]=value
    w.reconcile=lambda:pytest.fail('payload IO attempted')
    with pytest.raises(CaptureDenied,match='BEFORE_IO'):w.read_derived('TB2-missing',request)


def test_windows_observer_readonly():
    events=WindowsHostObserver().poll()
    assert isinstance(events,list)
    for e in events:
        assert e['status'] in ('NOT_OBSERVABLE','OBSERVED')
        if e['status']=='OBSERVED':assert {'provider','EventRecordID','raw_xml','event_time'}<=e.keys()


def test_no_progress_fifteen_minutes_stops_unchanged(setup):
    w,s,c,ref,obs=setup;c.advance(900)
    with pytest.raises(CaptureDenied,match='STOP_REVIEW'):w.capture_once()
    assert s.calls==0 and (w.base/'STOP_REVIEW.json').exists()


def test_maximum_recovery_lag_six_hours(setup):
    w,s,c,ref,obs=setup;w.close();c.advance(21601)
    other=reopened(w,s,c,ref,obs).open(background=False)
    try:
        with pytest.raises(CaptureDenied,match='STOP_REVIEW'):other.capture_once()
        assert s.calls==0
    finally:other.close()


def test_fsync_precedes_exclusive_publication(setup,monkeypatch):
    w,s,c,ref,obs=setup;operations=[];sync=os.fsync;link=os.link
    def fsync(fd):
        result=sync(fd);operations.append('fsync');return result
    def publish(a,b):
        assert operations and operations[-1]=='fsync'
        operations.append('link');return link(a,b)
    monkeypatch.setattr(os,'fsync',fsync);monkeypatch.setattr(os,'link',publish)
    c.advance(30);w.capture_once()
    assert operations.count('link')>10


def test_background_heartbeat_durable_while_binding_blocked(tmp_path):
    from src.data.track_b_forward_capture_v2 import Clock
    clock=Clock();source=Source();source.release=threading.Event();origin=clock.now()
    w=DataEngine(ROOT).track_b_forward_capture_v2(storage_root=tmp_path/'background',source=source,
        utc_reference=Reference(clock),synthetic_origin=origin,clock=clock,observer=Observer())
    w.open(background=True);errors=[]
    def capture():
        try:w.capture_once()
        except Exception as exc:errors.append(exc)
    thread=threading.Thread(target=capture);thread.start();assert source.entered.wait(3)
    try:
        before=sum(e['kind']=='HEARTBEAT' for e in w.events)
        deadline=time.monotonic()+9
        while time.monotonic()<deadline and sum(e['kind']=='HEARTBEAT' for e in w.events)==before:time.sleep(.1)
        hb=[e for e in w.events if e['kind']=='HEARTBEAT'][-1]
        assert sum(e['kind']=='HEARTBEAT' for e in w.events)>before
        assert hb['detail']['phase']=='WAITING_API'
        assert read(w.base/'events'/f"{hb['sequence']:09d}.json")==hb
    finally:
        source.release.set();thread.join(10);w.close()
    assert not errors


def test_revoked_during_api_preserves_raw_but_denies_temporal(setup):
    w,s,c,ref,obs=setup;s.release=threading.Event();c.advance(30);results=[]
    t=threading.Thread(target=lambda:results.append(w.capture_once()));t.start();assert s.entered.wait(2)
    w.revoke('inflight fixture');s.release.set();t.join(5)
    assert results and not results[0]['temporal_eligible']
    assert (w.base/'batches'/results[0]['batch_id']/'attempt-1.npy').exists()


def test_changed_config_denied(tmp_path):
    c=json.loads((ROOT/'config/track_b_xm_forward_capture_v2.json').read_text());c['backpressure']['normal_lag_seconds']=60
    p=tmp_path/'config.json';p.write_text(json.dumps(c))
    with pytest.raises(CaptureDenied,match='FROZEN_PARAMETER'):DataEngine(ROOT).track_b_forward_capture_v2(p)


@pytest.mark.parametrize('point',['after_raw','after_commit','after_checkpoint'])
def test_windows_real_process_lock_crash_and_reconciliation(tmp_path,point):
    if os.name!='nt':pytest.skip('Windows process test')
    base=tmp_path/'process-tb2';ready=tmp_path/'ready'
    helper=Path(__file__).with_name('track_b_v2_process_fixture.py')
    p=subprocess.Popen([sys.executable,str(helper),str(base),str(ready),point],cwd=ROOT,
        creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        deadline=time.monotonic()+15
        while not ready.exists() and time.monotonic()<deadline and p.poll() is None:time.sleep(.1)
        assert ready.exists(),p.communicate(timeout=1)
        c=FakeClock();s=Source();ref=Reference(c)
        w=TrackBForwardCaptureV2(ROOT,'config/track_b_xm_forward_capture_v2.json',storage_root=base,
            source=s,utc_reference=ref,synthetic_origin=ORIGIN,clock=c,observer=Observer())
        with pytest.raises(CaptureDenied,match='SECOND_WORKER'):w.open(background=False)
        p.kill();p.wait(timeout=5)  # only the exact synthetic child created by this test
        w=TrackBForwardCaptureV2(ROOT,'config/track_b_xm_forward_capture_v2.json',storage_root=base,
            source=s,utc_reference=ref,synthetic_origin=ORIGIN,clock=c,observer=Observer())
        w.open(background=False)
        try:
            expected=0 if point=='after_raw' else 1
            assert w.sequence==expected and len(list((base/'journal').glob('*.json')))==expected
            assert len(list((base/'derived').glob('*.parquet')))==expected
            assert w.parent is not None
            assert sum(e['kind']=='PARENT_OPEN' for e in w.events)==1
            if point=='after_raw':assert list((base/'staging').glob('TB2-*'))
            assert any(e['kind']=='RESTART_GRANTED' for e in w.events)
        finally:w.close()
    finally:
        if p.poll() is None:p.kill();p.wait(timeout=5)


def test_prior_live_pid_cannot_be_restarted(setup):
    w,s,c,ref,obs=setup
    owner={**w.owner,'worker_instance_id':'unclosed-synthetic-instance'}
    w.event('INSTANCE_OPEN',owner=owner);w.close()
    other=reopened(w,s,c,ref,obs)
    with pytest.raises(CaptureDenied,match='PRIOR_PROCESS_STILL_ALIVE'):other.open(background=False)


def test_restart_budget_three_per_three_hundred_seconds(setup,monkeypatch):
    w,s,c,ref,obs=setup
    # Synthetic dead-owner evidence; kernel lock remains real. This tests budget,
    # while the separate child-process cases test actual death/release/reconcile.
    for i in range(3):w.event('RESTART_GRANTED',prior_owner={'pid':99999999},verified_dead=True)
    owner={**w.owner,'pid':99999999,'worker_instance_id':'dead-instance'}
    w.event('INSTANCE_OPEN',owner=owner);w.close()
    other=reopened(w,s,c,ref,obs)
    with pytest.raises(CaptureDenied,match='RESTART_BUDGET_EXHAUSTED'):other.open(background=False)


def test_corruption_blocks_next_request(setup):
    w,s,c,ref,obs=setup;c.advance(30);result=w.capture_once();before=s.calls
    (w.base/'batches'/result['batch_id']/'attempt-1.npy').write_bytes(b'synthetic corruption')
    with pytest.raises(CaptureDenied,match='HASH_INCONSISTENT'):w.capture_once()
    assert s.calls==before


def test_monitor_missing_heartbeat_durable_signal_no_live_restart(setup):
    w,s,c,ref,obs=setup;c.advance(31)
    assert w.inspect_health()=={'status':'ALIVE_NO_RESTART','heartbeat_missing':True,'restart':False}
    w.inspect_health()
    assert len(list((w.base/'signals').glob('*.json')))==1
    w.heartbeat_once()
    assert any(e['kind']=='MONITOR_SIGNAL_JOINED' and e['parent']==w.parent for e in w.events)


def test_derived_published_without_receipt_verified_from_raw(setup):
    w,s,c,ref,obs=setup;c.advance(30)
    original=w.receipt
    def fail(stage,started,artifact):
        if stage=='derived':raise RuntimeError('after-derived-link-before-receipt')
        original(stage,started,artifact)
    w.receipt=fail
    with pytest.raises(RuntimeError,match='after-derived'):w.capture_once()
    w.receipt=original
    paths=list((w.base/'derived').glob('*.parquet'));assert len(paths)==1
    before=paths[0].read_bytes();w.reconcile();assert paths[0].read_bytes()==before
    assert any(e['kind']=='DERIVED_RECEIPT_MISSING' for e in w.events)


def test_stage_stamp_does_not_claim_stale_utc(setup):
    w,s,c,ref,obs=setup;assert w.stamp()['utc_reference'] is not None
    c.advance(6);assert w.stamp()['utc_reference'] is None
