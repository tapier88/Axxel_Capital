"""Package the canonical master without overwriting historical snapshots."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import uuid
import zipfile

REQUIRED = ('README.md', '00_START_HERE/AXXEL_MASTER_PLAN_V2.md',
 '00_START_HERE/ARCHITECTURE_AUDIT.md', '00_START_HERE/FOUNDATION_RECOVERY_PLAN_ADR_001.md',
 '13_STATE/AXXEL_STATE.json', '12_ROADMAP_BACKLOG/MASTER_ROADMAP.md',
 '12_ROADMAP_BACKLOG/DETAILED_TASK_BACKLOG.md')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def build(source):
    source = Path(source).resolve()
    for name in REQUIRED:
        if not (source / name).is_file():
            raise ValueError('MISSING_MASTER:' + name)
    contents = {}
    for path in sorted(source.rglob('*')):
        if path.is_symlink() or path.is_junction():
            raise ValueError('LINK_DENIED:' + str(path))
        if not path.is_file():
            continue
        name = path.relative_to(source).as_posix()
        data = path.read_bytes()
        if path.suffix == '.json':
            json.loads(data)
        if path.suffix == '.md':
            text = data.decode('utf-8-sig')
            refs = re.findall(r'`((?:\d{2}_[A-Z_]+/|\.axxel/master_architecture/)[^`\n]+\.(?:md|json))`', text)
            for ref in refs:
                target = source / ref.removeprefix('.axxel/master_architecture/')
                if not target.is_file():
                    raise ValueError('MISSING_CRITICAL_REFERENCE:' + ref)
        contents[name] = data
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED) as z:
        for name, data in contents.items():
            info = zipfile.ZipInfo('AXXEL_MASTER_ARCHITECTURE_V2/' + name, (1980,1,1,0,0,0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
    payload = buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP_VERIFY_FAILED')
        for name, data in contents.items():
            if z.read('AXXEL_MASTER_ARCHITECTURE_V2/' + name) != data:
                raise ValueError('ZIP_CONTENT_MISMATCH')
    return payload, {name: sha(data) for name, data in contents.items()}

def package(source, output):
    payload, inventory = build(source)
    output = Path(output).resolve()
    if output.is_relative_to(Path(source).resolve()):
        raise ValueError('OUTPUT_MUST_BE_OUTSIDE_SOURCE')
    output.mkdir(parents=True, exist_ok=False)
    target = output / 'AXXEL_MASTER_ARCHITECTURE_V2_UPDATED.zip'
    with target.open('xb') as f:
        f.write(payload)
        f.flush()
        import os
        os.fsync(f.fileno())
    record = {'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'source': str(Path(source).resolve()), 'source_state_sha256': inventory['13_STATE/AXXEL_STATE.json'],
        'zip_path': str(target), 'zip_sha256': sha(payload), 'files': inventory,
        'deterministic': True, 'source_of_truth': '.axxel/master_architecture/'}
    (output / 'manifest.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return record

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='.axxel/master_architecture')
    parser.add_argument('--output', default='reports/master_architecture_exports/' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    args = parser.parse_args()
    result = package(args.source, args.output)
    print(json.dumps({k:v for k,v in result.items() if k != 'files'}, indent=2))
