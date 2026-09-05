"""Child process for a real Windows crash AFTER synthetic durable commit."""
import sys
from pathlib import Path
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tests.data_quality.test_track_b_forward_capture_v2 import FakeClock,Source,Reference,Observer,ORIGIN
from src.data.track_b_forward_capture_v2 import TrackBForwardCaptureV2

if __name__=='__main__':
    base,ready=map(Path,sys.argv[1:3])
    target=sys.argv[3] if len(sys.argv)>3 else 'after_commit'
    clock=FakeClock();source=Source()
    def crash_point(point):
        if point==target:
            ready.write_text('SYNTHETIC_COMMIT_READY_FOR_PROCESS_TERMINATION')
            while True:time.sleep(1)
    w=TrackBForwardCaptureV2(ROOT,'config/track_b_xm_forward_capture_v2.json',storage_root=base,
        source=source,utc_reference=Reference(clock),synthetic_origin=ORIGIN,clock=clock,
        observer=Observer(),fault=crash_point)
    w.open(background=False);clock.advance(600);w.capture_once()
