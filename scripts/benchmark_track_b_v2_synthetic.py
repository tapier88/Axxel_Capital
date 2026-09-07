"""Bounded readiness measurement; uses existing synthetic fixtures, never MT5.

Not a capture entrypoint. Preserves its temporary corpus and incremental metrics.
The production configuration and worker are not patched by this harness.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    spec = json.loads((out / 'PERFORMANCE_PREREGISTRATION.json').read_bytes())
    assert spec['status'] == 'PREREGISTERED_SYNTHETIC_ONLY'
    module_spec = importlib.util.spec_from_file_location('fixtures', ROOT / 'tests/data_quality/test_track_b_forward_capture_v2.py')
    fixture = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(fixture)
    base = Path(tempfile.mkdtemp(prefix='axxel-tb2-readiness-')) / 'synthetic'
    clock = fixture.FakeClock()
    source = fixture.Source()
    ref = fixture.Reference(clock)
    observer = fixture.Observer()
    worker = fixture.DataEngine(ROOT).track_b_forward_capture_v2(
        storage_root=base, source=source, utc_reference=ref,
        synthetic_origin=fixture.ORIGIN, clock=clock, observer=observer)
    process = psutil.Process()
    begin = time.perf_counter()
    cpu0, io0 = process.cpu_times(), process.io_counters()
    result = {'synthetic_only': True, 't0_created': False, 'fixture_path': str(base),
              'measurements': [], 'status': 'RUNNING'}
    heartbeat_probe = []
    original_heartbeat = worker.heartbeat_once
    def measured_heartbeat():
        started = time.perf_counter()
        original_heartbeat()
        heartbeat_probe.append({'started': started - begin, 'completed': time.perf_counter() - begin})
    worker.heartbeat_once = measured_heartbeat
    with (out / 'performance_progress.jsonl').open('x', encoding='utf-8') as log:
        try:
            worker.open(background=True)
            for sequence in range(1, spec['batches'] + 1):
                if time.perf_counter() - begin > spec['deadline_seconds']:
                    result['status'] = 'DEADLINE_REACHED'
                    break
                clock.advance(spec['clock_step_seconds'])
                tick = time.perf_counter()
                batch = worker.capture_once()
                duration = time.perf_counter() - tick
                row = {'sequence': sequence, 'capture_seconds': duration,
                       'rss_bytes': process.memory_info().rss,
                       'elapsed_seconds': time.perf_counter() - begin}
                if sequence in spec['milestones']:
                    tick = time.perf_counter()
                    worker.reconcile()
                    row['reconcile_hash_chain_checkpoint_seconds'] = time.perf_counter() - tick
                    tick = time.perf_counter()
                    fixture.read(base / 'journal' / f'{sequence:09d}.json')
                    row['journal_direct_lookup_seconds'] = time.perf_counter() - tick
                    # Background heartbeat publishes transient .partial files.
                    # Count durable names only; never treat a removed temporary
                    # publication file as an acquisition integrity failure.
                    files = [p for p in base.rglob('*') if not p.name.startswith('.partial') and p.is_file()]
                    row['storage_bytes'] = sum(p.stat().st_size for p in files)
                    row['files'] = len(files)
                    row['events'] = len(worker.events)
                    print(json.dumps(row), flush=True)
                result['measurements'].append(row)
                log.write(json.dumps(row) + '\n'); log.flush()
            else:
                result['status'] = 'COMPLETED'
            result['sequence'] = worker.sequence
            result['source_calls'] = source.calls
            result['heartbeat_wall_times'] = [e['stamp']['local_wall'] for e in worker.events if e['kind'] == 'HEARTBEAT']
            worker.close()
            reopened = fixture.reopened(worker, source, clock, ref, observer)
            tick = time.perf_counter()
            reopened.open(background=False)
            result['restart_journal_recovery_seconds'] = time.perf_counter() - tick
            result['restart_sequence'] = reopened.sequence
            reopened.close()
        except BaseException as exc:
            result['status'] = 'FAILED'
            result['error'] = repr(exc)
            raise
        finally:
            if worker.opened:
                worker.close()
            cpu, io = process.cpu_times(), process.io_counters()
            result['elapsed_seconds'] = time.perf_counter() - begin
            result['cpu_seconds'] = cpu.user + cpu.system - cpu0.user - cpu0.system
            result['process_write_bytes'] = io.write_bytes - io0.write_bytes
            result['process_read_bytes'] = io.read_bytes - io0.read_bytes
            result['heartbeat_real_seconds'] = heartbeat_probe
            result['io_limit'] = 'Process I/O counters include cached I/O; not physical device writes.'
            result['heartbeat_limit'] = 'Real completion latency measured around unchanged heartbeat; host observer is a fixture.'
            (out / 'PERFORMANCE_RESULT.json').write_text(json.dumps(result, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
