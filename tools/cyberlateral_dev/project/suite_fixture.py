"""Complete retained data, explicit fake process receipts, never native execution."""

import hashlib
import json
from pathlib import Path

from v1_helpers import ROOT

FIXTURE_SHA = 'f77995b8db18d745c59da9ee5d5a0e092b02daab79f54e60b7d61400885bd680'


def canonical(data):
    return (json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def fixture(stage_id):
    raw = (ROOT / 'reference/r27_stage_records_v1.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA
    return next(record for record in json.loads(raw)['records'] if record['stage_id'] == stage_id)


def write_stage(path: Path, stage_id, *, mutate=None):
    record = fixture(stage_id)
    if mutate is not None:
        mutate(record)
    path.mkdir()
    files = {'OBSERVATIONS.json': canonical(record['observations']), 'SUMMARY.json': canonical(record['summary']),
             'RECEIPT_1.json': canonical({'scope': 'TEST_DOUBLE_NOT_NATIVE_EXECUTION'}),
             'RECEIPT_2.json': canonical({'scope': 'TEST_DOUBLE_NOT_NATIVE_EXECUTION'})}
    for name, raw in files.items():
        (path / name).write_bytes(raw)
    rehash(path)
    return record['summary']


def rehash(path):
    names = ['OBSERVATIONS.json', 'RECEIPT_1.json', 'RECEIPT_2.json', 'SUMMARY.json']
    (path / 'SHA256SUMS.txt').write_text(''.join(hashlib.sha256((path / name).read_bytes()).hexdigest() + '  ' + name + '\n' for name in names))
