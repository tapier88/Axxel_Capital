"""Versioned acquisition worker within Data Engine; market activation remains denied.

The implemented custody path runs only with injected synthetic sources in local temp
storage. No MT5 import, real quote call, T0 registration, or research capability exists.
Durability means observed flush/fsync + exclusive publication, not power-loss/WORM proof.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import psutil

from src.data.track_b_forward_capture import CaptureDenied


def iso(t):
    if t.tzinfo is None:
        raise CaptureDenied('AWARE_CLOCK_REQUIRED')
    return t.astimezone(timezone.utc).isoformat()


def dt(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def encoded(v):
    return (json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(b):
    return hashlib.sha256(b).hexdigest()


def read(p):
    return json.loads(p.read_bytes())


def process_identity(pid):
    try:
        p = psutil.Process(pid)
        return {'pid': pid, 'process_creation_time': p.create_time()} if p.is_running() else None
    except psutil.NoSuchProcess:
        return None
    except psutil.AccessDenied as exc:
        raise CaptureDenied('PROCESS_IDENTITY_UNKNOWN') from exc


class Clock:
    def now(self):
        return datetime.now(timezone.utc)

    def monotonic(self):
        return time.monotonic()


class InstanceLock:
    """Kernel-held byte lock; owner metadata is evidence, never a stale-lock override."""
    def __init__(self, path):
        self.path, self.handle = path, None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        f = self.path.open('a+b')
        if self.path.stat().st_size == 0:
            f.write(b'0'); f.flush(); os.fsync(f.fileno())
        f.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            f.close()
            raise CaptureDenied('SECOND_WORKER_DENIED') from exc
        self.handle = f

    def close(self):
        if self.handle:
            self.handle.close()
            self.handle = None


class WindowsHostObserver:
    """Read-only Windows event query, bounded in duration and paginated by RecordID."""
    def poll(self, after_record_id=0):
        if os.name != 'nt':
            return [{'status': 'NOT_OBSERVABLE', 'reason': 'NOT_WINDOWS'}]
        query = ("*[System[(Provider[@Name='Microsoft-Windows-Kernel-Power'] or "
                 "Provider[@Name='Microsoft-Windows-Power-Troubleshooter']) and "
                 "(EventID=42 or EventID=107 or EventID=1) and "
                 f"EventRecordID>{int(after_record_id)}]]")
        try:
            result = subprocess.run(['wevtutil', 'qe', 'System', '/q:' + query,
                '/rd:false', '/f:xml', '/c:128'], capture_output=True, timeout=3,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if result.returncode:
                return [{'status': 'NOT_OBSERVABLE', 'reason': result.stderr.decode(errors='replace')}]
            raw = result.stdout.decode('utf-8-sig')
            if not raw.strip():
                return []
            root = ET.fromstring(raw if raw.lstrip().startswith('<Events') else '<Events>' + raw + '</Events>')
            ns = {'e': 'http://schemas.microsoft.com/win/2004/08/events/event'}
            items = []
            for e in root:
                sys = e.find('e:System', ns)
                event_id = int(sys.find('e:EventID', ns).text)
                items.append({'status': 'OBSERVED', 'kind': 'SLEEP' if event_id == 42 else 'RESUME',
                    'provider': sys.find('e:Provider', ns).attrib['Name'],
                    'EventRecordID': int(sys.find('e:EventRecordID', ns).text),
                    'event_time': sys.find('e:TimeCreated', ns).attrib['SystemTime'],
                    'raw_xml': ET.tostring(e, encoding='unicode')})
            return items
        except (OSError, subprocess.TimeoutExpired, ET.ParseError, ValueError, AttributeError) as exc:
            return [{'status': 'NOT_OBSERVABLE', 'reason': repr(exc)}]


class TrackBForwardCaptureV2:
    def __init__(self, project_root, config_path, *, storage_root=None, source=None,
                 utc_reference=None, synthetic_origin=None, clock=None, observer=None,
                 disk_usage=None, fault=None):
        self.project = Path(project_root).resolve()
        cp = Path(config_path)
        self.config_path = cp if cp.is_absolute() else self.project / cp
        self.config_bytes = self.config_path.read_bytes()
        self.config = json.loads(self.config_bytes)
        self.config_hash = digest(self.config_bytes)
        self._validate_config()
        self.base = Path(storage_root).resolve() if storage_root else None
        self.source, self.utc = source, utc_reference
        self.origin = synthetic_origin
        self.clock, self.observer = clock or Clock(), observer or WindowsHostObserver()
        self.disk = disk_usage or shutil.disk_usage
        self.fault = fault or (lambda _: None)
        self.boot = f'{socket.gethostname()}:{psutil.boot_time()}'
        self.owner = {**process_identity(os.getpid()), 'boot_id': self.boot,
                      'worker_instance_id': uuid.uuid4().hex}
        self.phase, self.failure = 'NOT_STARTED', None
        self.mutex, self.inflight = threading.RLock(), threading.Lock()
        self.stop_event, self.threads = threading.Event(), []
        self.events, self.parent, self.sequence, self.head = [], None, 0, None
        self.cursor, self.last_valid, self.utc_open = self.origin, None, None
        self.utc_gaps, self.latest_reference = [], None
        self.last_progress = self.clock.monotonic()
        self.last_progress_wall = iso(self.clock.now())
        self.last_heartbeat = None
        self.last_spec, self.last_spec_time = None, None
        self.lock, self.connection = None, None
        self.opened = False

    def _validate_config(self):
        c = self.config
        if (c.get('schema_version') != 'AXXEL-TRACK-B-CAPTURE-CONFIG-2' or
            c.get('config_id') != 'TRACK_B_XM_FORWARD_CAPTURE_V2' or
            c.get('status') != 'FROZEN_IMPLEMENTATION_ONLY' or
            c.get('activation_authorized') is not False or c.get('t0') is not None):
            raise CaptureDenied('V2_CONFIG_OR_ACTIVATION_DENIED')
        # Frozen numbers are admission requirements, not test tunables.
        expected = {'polling': {'cadence_seconds':30,'maximum_request_span_seconds':60,'overlap_milliseconds':2000},
            'batch':{'maximum_records':100000}, 'symbol_specification':{'snapshot_cadence_seconds':900},
            'backpressure':{'maximum_tolerated_lag_seconds':120,'normal_lag_seconds':30,
                'disk_minimum_free_bytes':5*1024**3,'recovery_minimum_delay_seconds':1,
                'recovery_maximum_lag_seconds':21600,'no_durable_progress_stop_seconds':900},
            'heartbeat':{'cadence_seconds':5,'absence_threshold_seconds':30},
            'host_observation':{'cadence_seconds':5},
            'supervisor':{'maximum_restarts':3,'restart_window_seconds':300},
            'retry':{'maximum_attempts':3,'backoff_seconds':[1,2,4]},
            'utc_reference':{'refresh_cadence_seconds':5,'required_responses':1,
                'maximum_uncertainty_milliseconds':250,'maximum_source_disagreement_milliseconds':100}}
        for section, fields in expected.items():
            if any(c.get(section, {}).get(k) != v for k,v in fields.items()):
                raise CaptureDenied('FROZEN_PARAMETER_MISMATCH:' + section)
        scope = c['scope']
        if (scope['track'],scope['partition'],scope['server'],scope['symbol'],scope['environment'],scope['mode']) != (
                'B','FORWARD_EXECUTION','XMGlobal-MT5 6','GOLD','DEMO','READ_ONLY'):
            raise CaptureDenied('SCOPE_DENIED')
        if any(scope[k] is not False for k in ('orders_authorized','fills_authorized','research_authorized','slippage_observed')):
            raise CaptureDenied('CAPABILITY_EXPANSION_DENIED')
        if c['retention']['minimum_days'] < 30 or c['polling']['claim_tick_completeness']:
            raise CaptureDenied('RETENTION_OR_COMPLETENESS_DENIED')

    def start_market_capture(self):
        raise CaptureDenied('MARKET_CAPTURE_NOT_AUTHORIZED_NO_T0')

    def stamp(self):
        now=self.clock.now(); reference=self.latest_reference
        if reference is not None and not 0 <= (now-dt(reference['measured_at'])).total_seconds() <= 5:
            reference=None
        return {'local_wall':iso(now), 'monotonic':self.clock.monotonic(),
                'boot_id':self.boot, 'utc_reference':reference}

    def publish(self, path, payload):
        """Keep interrupted temporary objects; never overwrite sealed objects."""
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name('.partial-' + uuid.uuid4().hex)
        with temp.open('xb') as f:
            f.write(payload); f.flush(); os.fsync(f.fileno())
        try:
            os.link(temp, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise CaptureDenied('IMMUTABLE_CONFLICT:' + path.name)
        # Completed duplicate link only; crash leftovers remain preserved.
        temp.unlink()

    def event(self, kind, **detail):
        with self.mutex:
            e = {'sequence':len(self.events)+1,'kind':kind,'stamp':self.stamp(),
                 'parent':self.parent,'detail':detail,
                 'previous':self.events[-1]['hash'] if self.events else None}
            e['hash'] = digest(encoded(e))
            self.publish(self.base/'events'/f"{e['sequence']:09d}.json", encoded(e))
            self.events.append(e)
            return e

    def gap(self, reason, **detail):
        with self.mutex:
            if self.parent is None:
                self.parent = 'EP2-' + uuid.uuid4().hex
                self.event('PARENT_OPEN', reason=reason)
            self.event('RECOVERY_CHILD', reason=reason, **detail)
            if self.phase != 'WAITING_API':
                self.phase = 'RECOVERING'

    def _load_events(self):
        self.events, self.parent, self.utc_gaps, self.utc_open = [], None, [], None
        for p in sorted((self.base/'events').glob('[0-9]*.json')):
            e = read(p); core = {k:v for k,v in e.items() if k!='hash'}
            if e['sequence'] != len(self.events)+1 or e['previous'] != (self.events[-1]['hash'] if self.events else None) or digest(encoded(core)) != e['hash']:
                raise CaptureDenied('EVENT_LEDGER_INTEGRITY')
            self.events.append(e)
            if e['kind']=='PARENT_OPEN':
                if self.parent is not None:
                    raise CaptureDenied('EPISODE_FORK')
                self.parent=e['parent']
            if e['kind']=='PARENT_CLOSE':
                if e['parent']!=self.parent: raise CaptureDenied('EPISODE_CLOSE_MISMATCH')
                self.parent=None
            if e['kind']=='UTC_LOST': self.utc_open=dt(e['detail']['start'])
            if e['kind']=='UTC_RESUMED':
                if self.utc_open is None: raise CaptureDenied('UTC_LEDGER_INTEGRITY')
                self.utc_gaps.append((self.utc_open, dt(e['detail']['end']))); self.utc_open=None

    def utc_lost(self, reason, start=None):
        with self.mutex:
            self.latest_reference=None
            if self.utc_open is None:
                self.utc_open = start or self.last_valid or self.origin
                self.event('UTC_LOST', start=iso(self.utc_open), reason=reason,
                           retrospective_validation=False)

    def sample_utc(self):
        try:
            sample = self.utc.measure()
            age = (self.clock.now()-dt(sample['measured_at'])).total_seconds()
            valid = (sample.get('available') is True and 0 <= age <= 5 and
                sample['uncertainty_milliseconds'] <= 250 and
                sample['source_disagreement_milliseconds'] <= 100 and
                sample.get('samples_count',0) >= 1)
        except Exception:
            sample, valid = None, False
        with self.mutex:
            now = self.clock.now()
            if not valid:
                self.utc_lost('MISSING_STALE_OR_OUT_OF_TOLERANCE')
                return None
            if self.last_valid and (now-self.last_valid).total_seconds()>5:
                self.utc_lost('UNOBSERVED_INTERVAL', self.last_valid)
            if self.utc_open is not None:
                self.event('UTC_RESUMED', end=iso(now), retrospective_validation=False)
                self.utc_gaps.append((self.utc_open,now)); self.utc_open=None
            self.latest_reference=sample; self.last_valid=now
            return sample

    def temporal_ok(self, start, end):
        return (self.utc_open is None and self.latest_reference is not None and
                not any(start < b and end > a for a,b in self.utc_gaps))

    def _identity(self, connection):
        if (connection.get('server')!='XMGlobal-MT5 6' or connection.get('account_mode')!='DEMO' or
            'XM' not in connection.get('broker','') or not connection.get('account_fingerprint_sha256')):
            raise CaptureDenied('IDENTITY_DENIED')
        return {k:connection[k] for k in ('server','account_mode','broker','account_fingerprint_sha256')}

    def open(self, *, background=True):
        # Default constructor is inert; injection is a trusted test-host boundary.
        if (self.base is None or self.origin is None or self.source is None or
                getattr(self.source,'synthetic_only',False) is not True or self.utc is None):
            raise CaptureDenied('SYNTHETIC_DEPENDENCIES_REQUIRED_MARKET_DENIED')
        temp = Path(tempfile.gettempdir()).resolve()
        if not self.base.is_relative_to(temp) or self.base==temp or 'onedrive' in str(self.base).casefold():
            raise CaptureDenied('SYNTHETIC_LOCAL_TEMP_STORAGE_REQUIRED')
        iso(self.origin)
        self.base.mkdir(parents=True,exist_ok=True)
        self.lock=InstanceLock(self.base/'instance.lock'); self.lock.acquire()
        try:
            if (self.base/'REVOKED.json').exists(): raise CaptureDenied('SCOPE_REVOKED')
            if (self.base/'STOP_REVIEW.json').exists(): raise CaptureDenied('STOP_REVIEW')
            self._load_events()
            last_owner=next((e for e in reversed(self.events) if e['kind']=='INSTANCE_OPEN'),None)
            if last_owner:
                prior=last_owner['detail']['owner']
                closed=any(e['kind']=='INSTANCE_CLOSE' and e['detail']['instance']==prior['worker_instance_id'] for e in self.events)
                observed=process_identity(prior['pid'])
                if not closed and observed and observed['process_creation_time']==prior['process_creation_time']:
                    raise CaptureDenied('PRIOR_PROCESS_STILL_ALIVE')
                recent=[e for e in self.events if e['kind']=='RESTART_GRANTED' and
                        (self.clock.now()-dt(e['stamp']['local_wall'])).total_seconds()<=300]
                if not closed and len(recent)>=3: raise CaptureDenied('RESTART_BUDGET_EXHAUSTED')
            self.connection=self.source.open()
            binding={'schema':'TB2-SYNTHETIC-IDENTITY','config_hash':self.config_hash,
                     'identity':self._identity(self.connection),'synthetic_origin':iso(self.origin)}
            self.publish(self.base/'identity.json',encoded(binding))
            self.reconcile()
            if last_owner:
                self.gap('RESTART_RECONCILED', prior_owner=last_owner['detail']['owner'])
                self.utc_lost('RESTART_UNOBSERVED_INTERVAL',self.cursor)
                if closed:
                    self.event('INSTANCE_REOPEN_AFTER_CLOSE', prior_owner=last_owner['detail']['owner'])
                else:
                    self.event('RESTART_GRANTED', prior_owner=last_owner['detail']['owner'], verified_dead=True)
            self.event('INSTANCE_OPEN',owner=self.owner)
            self.opened=True
            self.phase='RECOVERING' if self.parent else 'NORMAL'
            self.sample_utc(); self.heartbeat_once()
            if background:
                for fn,name in ((self.heartbeat_once,'heartbeat'),(self.observe_host,'host-observer')):
                    t=threading.Thread(target=self._background,args=(fn,),name='TB2-'+name,daemon=True)
                    t.start(); self.threads.append(t)
            return self
        except BaseException:
            if self.connection: self.source.close(); self.connection=None
            self.lock.close()
            raise

    def _background(self, fn):
        while not self.stop_event.wait(5):
            try: fn()
            except Exception as exc:
                self.failure=repr(exc); self.stop_event.set()

    def heartbeat_once(self):
        seen={e['detail'].get('signal') for e in self.events if e['kind']=='MONITOR_SIGNAL_JOINED'}
        for path in (self.base/'signals').glob('*.json'):
            if path.name not in seen:
                signal=read(path)
                self.gap('HEARTBEAT_MISSING',cause='UNKNOWN')
                self.utc_lost('HEARTBEAT_MISSING',dt(signal['last_observed']))
                self.event('MONITOR_SIGNAL_JOINED',signal=path.name,sha256=digest(path.read_bytes()))
        with self.mutex:
            now=self.clock.now()
            if self.last_heartbeat and (now-self.last_heartbeat).total_seconds()>30:
                self.gap('HEARTBEAT_MISSING',cause='UNKNOWN')
                self.utc_lost('HEARTBEAT_MISSING',self.last_valid or self.last_heartbeat)
            self.last_heartbeat=now
        self.sample_utc()
        self.event('HEARTBEAT',**self.owner,phase=self.phase,cursor=iso(self.cursor),
            last_committed_sequence=self.sequence,last_progress=self.last_progress_wall,
            disk_state={'free_bytes':self.disk(self.base).free},utc_state=self.latest_reference,
            local_wall=iso(now),monotonic=self.clock.monotonic())
        if self.clock.monotonic()-self.last_progress>=900:
            self.stop_review('NO_DURABLE_PROGRESS')

    def observe_host(self):
        ids=[e['detail']['observation'].get('EventRecordID',0) for e in self.events if e['kind']=='HOST_EVENT']
        for obs in self.observer.poll(max(ids,default=0)):
            self.event('HOST_EVENT',observation=obs,boot_identity=self.boot)
            # Historical records preserved, not projected onto current collection.
            if obs.get('status')=='OBSERVED' and dt(obs['event_time'])>=self.origin:
                self.gap('HOST_'+obs['kind'],EventRecordID=obs['EventRecordID'])
                self.utc_lost('HOST_INTERRUPTION',self.last_valid or self.cursor)

    def stop_review(self, reason):
        self.phase='STOP_REVIEW'; self.failure=reason
        self.event('STOP_REVIEW',reason=reason)
        self.publish(self.base/'STOP_REVIEW.json',encoded({'reason':reason}))
        self.stop_event.set()

    def revoke(self, reason):
        self.publish(self.base/'REVOKED.json',encoded({'reason':reason,'stamp':self.stamp()}))
        self.event('SCOPE_REVOKED',reason=reason)

    def _check(self):
        if not self.opened: raise CaptureDenied('WORKER_NOT_OPEN')
        if self.failure or (self.base/'STOP_REVIEW.json').exists(): raise CaptureDenied('STOP_REVIEW')
        if (self.base/'REVOKED.json').exists(): raise CaptureDenied('SCOPE_REVOKED')
        if self.config_path.read_bytes()!=self.config_bytes: raise CaptureDenied('CONFIG_CHANGED')
        if self.disk(self.base).free<5*1024**3:
            self.stop_review('DISK_THRESHOLD'); raise CaptureDenied('DISK_THRESHOLD')

    def receipt(self, stage, started, artifact):
        self.event('STAGE_RECEIPT',stage=stage,start=started,end=self.stamp(),
                   artifact=artifact.relative_to(self.base).as_posix(),sha256=digest(artifact.read_bytes()))

    def write_stage(self, stage, path, payload):
        started=self.stamp(); self.publish(path,payload); self.receipt(stage,started,path)

    def capture_once(self):
        if not self.inflight.acquire(blocking=False): raise CaptureDenied('REQUEST_ALREADY_IN_FLIGHT')
        try:
            self._check()
            self.reconcile()
            return self._capture()
        except CaptureDenied:
            raise
        except OSError as exc:
            self.failure='STORAGE_OR_OS_FAILURE'; raise CaptureDenied('STORAGE_FAILURE') from exc
        finally: self.inflight.release()

    def _capture(self):
        self._check()
        now=self.clock.now(); lag=(now-self.cursor).total_seconds()
        if lag<0: raise CaptureDenied('CLOCK_REGRESSION')
        if lag>120: self.gap('BACKLOG_EXCEEDED',lag_seconds=lag)
        if lag>21600 or self.clock.monotonic()-self.last_progress>=900:
            self.stop_review('RECOVERY_BUDGET_EXHAUSTED'); raise CaptureDenied('STOP_REVIEW')
        start=max(self.origin,self.cursor-timedelta(seconds=2)); end=min(now,start+timedelta(seconds=60))
        batch='TB2-'+uuid.uuid4().hex; stage=self.base/'staging'/batch; stage.mkdir(parents=True)
        request={'batch':batch,'from':iso(start),'to':iso(end),'symbol':'GOLD','flags':'COPY_TICKS_ALL',
                 'track':'B','partition':'FORWARD_EXECUTION','environment':'DEMO','synthetic':True}
        self.publish(stage/'request.json',encoded(request))
        if self.last_spec_time is None or (now-self.last_spec_time).total_seconds()>=900:
            spec=self.source.symbol_specification()
            if spec.get('name')!='GOLD': raise CaptureDenied('SYMBOL_SPECIFICATION_IDENTITY_DENIED')
            spec_hash=digest(encoded(spec))
            if self.last_spec is not None and digest(encoded(self.last_spec))!=spec_hash:
                self.event('SYMBOL_SPECIFICATION_CHANGE',new_hash=spec_hash,effective_from='UNKNOWN')
            self.publish(stage/'specification.json',encoded({'observed':self.stamp(),'original':spec,
                'interval_id':'SPEC2-'+spec_hash,'retroactive':False}))
            self.last_spec_time=now; self.last_spec=spec
        attempts=[]; array=None; before=None; after=None
        for attempt in range(1,4):
            before=self.sample_utc(); began=self.stamp(); self.phase='WAITING_API'
            try:
                value=self.source.copy_ticks(start,end)
                error=None if value is not None else 'NONE_RESPONSE'
            except Exception as exc:
                value=None; error=repr(exc)
            self.phase='RECOVERING' if self.parent else 'NORMAL'
            call_end=self.stamp()
            # RAW before descriptor, UTC sampling, derived conversion, or retries.
            raw=stage/f'attempt-{attempt}.npy' if error is None else stage/f'attempt-{attempt}.json'
            if error is None:
                array=np.asarray(value); buf=io.BytesIO(); np.save(buf,array,allow_pickle=False)
                self.write_stage('raw',raw,buf.getvalue())
            else: self.write_stage('raw',raw,encoded({'response':None,'error':error}))
            self.event('STAGE_RECEIPT',stage='request',start=began,end=call_end,
                       artifact=(stage/'request.json').relative_to(self.base).as_posix(),
                       sha256=digest((stage/'request.json').read_bytes()),attempt=attempt)
            elapsed_ms=(call_end['monotonic']-began['monotonic'])*1000
            if elapsed_ms>self.config['timeouts']['mt5_call_observation_threshold_milliseconds']:
                self.event('API_TIMEOUT_THRESHOLD_EXCEEDED',batch=batch,elapsed_milliseconds=elapsed_ms,
                           cancellable=False)
            self.fault('after_raw')
            after=self.sample_utc()
            if (self.clock.now()-self.cursor).total_seconds()>120:
                self.gap('BACKLOG_AFTER_API_RETURN',batch=batch)
            attempts.append({'attempt':attempt,'raw':raw.name,'error':error,'call_start':began,'call_end':call_end})
            if error is None and len(array)==0:self.event('EMPTY_RESPONSE',batch=batch,attempt=attempt)
            if error is None: break
            self.gap('API_ERROR',batch=batch,attempt=attempt,error=error)
            if attempt<3: time.sleep(self.config['retry']['backoff_seconds'][attempt-1])
        with self.mutex:
            if array is not None:
                response_hash=digest(raw.read_bytes())
                previous=[e for e in self.events if e['kind']=='RESPONSE_HASH']
                if previous and previous[-1]['detail']['sha256']==response_hash:
                    self.event('DUPLICATE_RESPONSE',batch=batch,sha256=response_hash)
                self.event('RESPONSE_HASH',batch=batch,sha256=response_hash)
            recovered=self.parent is not None
            temporal=bool(before and after and self.temporal_ok(start,end) and not self.failure and
                          not (self.base/'REVOKED.json').exists())
            desc={'schema':'AXXEL-TRACK-B-RAW-2','config_hash':self.config_hash,'request':request,
                  'attempts':attempts,'recovery_active':recovered,'recovered_after_gap':recovered,
                  'parent':self.parent,'temporal_eligible':temporal,'research_eligible':False,
                  'tick_completeness':False,'identity':self._identity(self.connection),
                  'rows':0 if array is None else len(array),
                  'dtype':None if array is None else array.dtype.descr,
                  'shape':None if array is None else list(array.shape),
                  'strides':None if array is None else list(array.strides)}
            self.write_stage('descriptor',stage/'descriptor.json',encoded(desc))
            artifacts={p.name:digest(p.read_bytes()) for p in stage.iterdir() if p.is_file() and not p.name.startswith('.partial')}
            manifest={'schema':'TB2-MANIFEST','batch':batch,'sequence':self.sequence+1,'previous':self.head,
                      'artifacts':artifacts,'cursor':iso(end if array is not None else self.cursor),
                      'parent':self.parent,'recovered_after_gap':recovered,'config_hash':self.config_hash}
            self.write_stage('manifest',stage/'manifest.json',encoded(manifest))
            commit={'schema':'TB2-COMMIT','manifest_hash':digest((stage/'manifest.json').read_bytes()),'batch':batch}
            commit['hash']=digest(encoded(commit))
            began=self.stamp(); self.publish(stage/'COMMIT.json',encoded(commit))
            final=self.base/'batches'/batch; final.parent.mkdir(parents=True,exist_ok=True)
            os.rename(stage,final)
            self.event('COMMIT_RELOCATION',from_path=stage.relative_to(self.base).as_posix(),
                       to_path=final.relative_to(self.base).as_posix(),commit_hash=commit['hash'])
            self.receipt('commit',began,final/'COMMIT.json')
            self.fault('after_commit')
            self._checkpoint(manifest,commit)
            self.fault('after_checkpoint')
            self._derived(final,desc,array)
            self.reconcile()
            if recovered: self.event('RECOVERY_BATCH_COMMITTED',batch=batch,sequence=self.sequence)
            if self.parent and array is not None and (self.clock.now()-self.cursor).total_seconds()<=30:
                self.event('PARENT_CLOSE',after_sequence=self.sequence,reason='DURABLE_RECONCILED_NORMAL_LAG')
                self.parent=None
            self.last_progress=self.clock.monotonic(); self.last_progress_wall=iso(self.clock.now())
        if array is None:
            self.gap('RECONNECT_REQUIRED',batch=batch)
            current=self.source.reconnect()
            if self._identity(current)!=self._identity(self.connection):
                self.stop_review('IDENTITY_CHANGED'); raise CaptureDenied('IDENTITY_CHANGED')
            self.connection=current; self.last_spec_time=None
            self.event('RECONNECT',identity=self._identity(current))
        if array is not None and len(array)>100000:
            self.stop_review('ROW_LIMIT_EXCEEDED_RAW_PRESERVED'); raise CaptureDenied('ROW_LIMIT')
        self.phase='RECOVERING' if self.parent else 'NORMAL'
        return {'batch_id':batch,'status':self.phase,'recovered_after_gap':recovered,'temporal_eligible':temporal}

    def _checkpoint(self,m,c):
        p=self.base/'journal'/f"{m['sequence']:09d}.json"
        data={'sequence':m['sequence'],'batch':m['batch'],'commit_hash':c['hash'],'cursor':m['cursor']}
        if p.exists():
            if read(p)!=data: raise CaptureDenied('CHECKPOINT_CONFLICT')
        else:self.write_stage('checkpoint',p,encoded(data))
        self.sequence=m['sequence']; self.head=c['hash']; self.cursor=dt(m['cursor'])

    def _derived(self, final, desc, array=None):
        p=self.base/'derived'/(final.name+'.parquet')
        if p.exists():
            receipts=[e for e in self.events if e['kind']=='STAGE_RECEIPT' and e['detail'].get('stage')=='derived' and e['detail']['artifact']==p.relative_to(self.base).as_posix()]
            if receipts and digest(p.read_bytes())!=receipts[-1]['detail']['sha256']:
                raise CaptureDenied('DERIVED_INTEGRITY')
            if receipts:return
            self.event('DERIVED_RECEIPT_MISSING',batch=final.name,completion_time='UNKNOWN')
            # Reproduce from verified RAW below before accepting an object whose
            # publication survived a crash but whose completion receipt did not.
        if array is None:
            a=desc['attempts'][-1]
            array=np.load(final/a['raw'],allow_pickle=False) if a['error'] is None else None
        frame=pd.DataFrame.from_records(array) if array is not None else pd.DataFrame()
        frame.insert(0,'response_index',np.arange(len(frame)))
        frame.insert(0,'batch_id',final.name)
        frame['recovered_after_gap']=desc['recovered_after_gap']
        if 'ask' in frame and 'bid' in frame:
            frame['spread_price']=frame['ask']-frame['bid']
        buf=io.BytesIO(); frame.to_parquet(buf,index=False,compression='zstd')
        if p.exists() and p.read_bytes()!=buf.getvalue():
            raise CaptureDenied('UNRECEIPTED_DERIVED_INTEGRITY')
        self.write_stage('derived',p,buf.getvalue())

    def reconcile(self):
        """Validate entire commit graph before repair; no branch selected by time."""
        with self.mutex:
            committed=[]
            for p in (self.base/'batches').glob('TB2-*'):
                if p.is_symlink() or p.resolve().parent!=(self.base/'batches').resolve():
                    raise CaptureDenied('BATCH_PATH_REDIRECTION')
                if not (p/'COMMIT.json').exists(): raise CaptureDenied('PUBLISHED_BATCH_WITHOUT_COMMIT')
                c=read(p/'COMMIT.json'); core={k:v for k,v in c.items() if k!='hash'}
                if digest(encoded(core))!=c['hash'] or digest((p/'manifest.json').read_bytes())!=c['manifest_hash']:
                    raise CaptureDenied('COMMIT_HASH_INCONSISTENT')
                m=read(p/'manifest.json')
                if m['batch']!=p.name or c['batch']!=p.name or m['config_hash']!=self.config_hash:
                    raise CaptureDenied('BATCH_IDENTITY_INCONSISTENT')
                for name,h in m['artifacts'].items():
                    if Path(name).name!=name or (p/name).is_symlink() or digest((p/name).read_bytes())!=h:
                        raise CaptureDenied('COMMITTED_RAW_HASH_INCONSISTENT')
                committed.append((m,c,p))
            committed.sort(key=lambda x:x[0]['sequence'])
            prev=None
            for i,(m,c,p) in enumerate(committed,1):
                if m['sequence']!=i or m['previous']!=prev: raise CaptureDenied('COMMIT_CHAIN_FORK')
                prev=c['hash']
            expected={f"{m['sequence']:09d}.json":{'sequence':m['sequence'],'batch':m['batch'],'commit_hash':c['hash'],'cursor':m['cursor']} for m,c,p in committed}
            for p in (self.base/'journal').glob('*.json'):
                if p.name not in expected or read(p)!=expected[p.name]: raise CaptureDenied('CHECKPOINT_WITHOUT_VALID_COMMIT')
            self.sequence,self.head,self.cursor=0,None,self.origin
            for m,c,p in committed:
                self._checkpoint(m,c)
                self._derived(p,read(p/'descriptor.json'))
            seen={e['detail'].get('orphan') for e in self.events if e['kind']=='ORPHAN_PRESERVED'}
            for p in (self.base/'staging').glob('TB2-*'):
                if p.name not in seen:
                    self.gap('PARTIAL_STAGING',orphan=p.name)
                    self.event('ORPHAN_PRESERVED',orphan=p.name,files=sorted(x.name for x in p.iterdir()))

    def read_derived(self,batch_id,request):
        expected={'track':'B','partition':'FORWARD_EXECUTION','purpose':'FORWARD_CAPTURE_AUDIT','environment':'DEMO'}
        if request!=expected: raise CaptureDenied('SCOPE_DENIED_BEFORE_IO')
        self._check()
        if not isinstance(batch_id,str) or not batch_id.startswith('TB2-') or Path(batch_id).name!=batch_id:
            raise CaptureDenied('BATCH_ID_DENIED')
        self.reconcile()
        return pd.read_parquet(self.base/'derived'/(batch_id+'.parquet'))

    def run(self, stop=None):
        while not self.stop_event.is_set() and not (stop and stop()):
            result=self.capture_once()
            if self.stop_event.wait(1 if result['status']=='RECOVERING' else 30): break

    def inspect_health(self):
        """Trusted local monitor: never kills/restarts a live process.

        A missing-heartbeat incident is published in a separate signal directory,
        avoiding competing writers to the worker's event chain. It is joined to
        the recovery episode when the worker can run again.
        """
        if self.base is None: raise CaptureDenied('STORAGE_REQUIRED')
        events=[read(p) for p in sorted((self.base/'events').glob('[0-9]*.json'))]
        owner=next((e['detail']['owner'] for e in reversed(events) if e['kind']=='INSTANCE_OPEN'),None)
        if owner is None:return {'status':'NO_INSTANCE','restart':False}
        proc=process_identity(owner['pid'])
        live=bool(proc and proc['process_creation_time']==owner['process_creation_time'])
        hb=next((e for e in reversed(events) if e['kind']=='HEARTBEAT' and e['detail']['worker_instance_id']==owner['worker_instance_id']),None)
        last=dt(hb['stamp']['local_wall']) if hb else self.origin
        missing=(self.clock.now()-last).total_seconds()>30
        if missing:
            key=f"{owner['worker_instance_id']}-{hb['sequence'] if hb else 0}"
            path=self.base/'signals'/('HEARTBEAT-'+key+'.json')
            if not path.exists():
                self.publish(path,encoded({'kind':'HEARTBEAT_MISSING','cause':'UNKNOWN',
                    'last_observed':iso(last),'observed':self.stamp(),'owner':owner}))
        return {'status':'ALIVE_NO_RESTART' if live else 'DEAD_REQUIRES_LOCK_IDENTITY_RECONCILE_BUDGET',
                'heartbeat_missing':missing,'restart':False}

    def close(self):
        if self.inflight.locked(): raise CaptureDenied('API_IN_FLIGHT_NO_UNLOCK')
        self.stop_event.set()
        for t in self.threads: t.join(timeout=4)
        if any(t.is_alive() for t in self.threads): raise CaptureDenied('OBSERVER_STILL_ALIVE_NO_UNLOCK')
        if self.opened:
            self.event('INSTANCE_CLOSE',instance=self.owner['worker_instance_id'])
            self.source.close(); self.opened=False
        if self.lock:self.lock.close()

    def __enter__(self):return self.open()
    def __exit__(self,*args):self.close()
