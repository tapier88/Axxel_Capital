"""Read-only DEV diagnostics; output is evidence, never a replacement certificate."""
from pathlib import Path
import argparse
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data.integrity_audit import audit

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset-id', required=True)
    parser.add_argument('--output', default='reports/data_integrity/2026-09-04/diagnostic')
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to(ROOT / 'reports/data_integrity'):
        raise PermissionError('Audit writes only to reports/data_integrity')
    print(json.dumps(audit(ROOT, args.dataset_id, output)['summary'], indent=2))
