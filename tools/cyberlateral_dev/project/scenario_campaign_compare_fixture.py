"""Complete real R43 fixtures and coherent saved-data controls, test-only."""

import atexit
import hashlib
import importlib
import json
import shutil
import sys
import tempfile
from functools import cache
from pathlib import Path
from unittest.mock import patch

from scenario_compare_fixture import refresh
from scenario_report_fixture import edit_json
from v1_helpers import ROOT

_scratch = tempfile.TemporaryDirectory(prefix='r44-real-campaigns-')
atexit.register(_scratch.cleanup)


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rehash_all(root):
    for sums in sorted(root.rglob('*SHA256SUMS.txt'),
                       key=lambda p: (len(p.parts), p.name == 'PORTABLE_SHA256SUMS.txt'), reverse=True):
        if sums.name == 'PORTABLE_SHA256SUMS.txt':
            names = [line.split('  ')[1] for line in sums.read_text().splitlines()]
        else:
            names = [p.relative_to(sums.parent).as_posix() for p in sums.parent.rglob('*') if p.is_file() and p != sums]
        sums.write_bytes(''.join(sha(sums.parent / name) + '  ' + name + '\n' for name in sorted(names)).encode())


def edit(root, name, change):
    target = root / name
    record = json.loads(target.read_bytes())
    change(record)
    target.write_bytes(canonical(record))
    rehash_all(root)


@cache
def real_campaign(seeds=(42, 43), cases=1, steps=16, status='MATCH', differences=1):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    m = importlib.import_module('integration_tools.scenario_campaign_run')
    target = Path(_scratch.name) / f'campaign-{len(list(Path(_scratch.name).iterdir())):03d}'
    checker = m.exploration.workflow.reference
    real_check = checker.check_batch

    def wrong_projection(source, output):
        for offset in range(differences):
            edit_json(source / 'case-001/data', 'RESULTS.json',
                      lambda record, offset=offset: record['rows'][offset]['model_output']['projection']['torque_float32'].update(bits_hex='00000000'))
        refresh(source)
        return real_check(source, output)

    if status == 'DIFFERENT':
        with patch.object(checker, 'check_batch', side_effect=wrong_projection):
            result = m.run_campaign(list(seeds), cases, steps, target)
    elif status == 'ERROR':
        worker = checker.reference
        with patch.object(worker, '_launch', side_effect=worker.ReferenceCheckError('REFERENCE_WORKER_FAILED')):
            result = m.run_campaign(list(seeds), cases, steps, target)
    else:
        result = m.run_campaign(list(seeds), cases, steps, target)
    if result['status'] != status:
        raise AssertionError(f'Real fixture has {result["status"]}, not {status}')
    return target


def copy_campaign(target, **parameters):
    shutil.copytree(real_campaign(**parameters), target)
    return target


def change_saved_trace(root, *, many=False):
    """Change one saved trace, repair byte bindings, but never recompute references."""
    child = root / 'runs/seed-001'
    batch = child / 'workflow/batch'
    if many:
        for data in batch.glob('case-*/data'):
            target = data / 'RESULTS.json'
            record = json.loads(target.read_bytes())
            for row in record['rows']:
                trace = row['model_output']['trace']['downstream']
                trace['limited_command'] += 1
            target.write_bytes(canonical(record))
    else:
        edit_json(batch / 'case-001/data', 'RESULTS.json',
                  lambda record: record['rows'][0]['model_output']['trace']['downstream'].update(limited_command=-7))
    from integration_tools.scenario_output import render_outputs
    from integration_tools.scenario_report_data import _spec

    for data in (batch.glob('case-*/data') if many else [batch / 'case-001/data']):
        source, result, receipt = [json.loads((data / name).read_bytes())
                                   for name in ['INPUT.json', 'RESULTS.json', 'RECEIPT.json']]
        saved = {key: result[key] for key in ['model_steps', 'rows', 'final_state']}
        for name, raw in render_outputs(_spec(source), saved, result['identity'], receipt).items():
            (data / name).write_bytes(raw)
    refresh(batch)
    from integration_tools.scenario_report_data import CAPS

    for report in (child / 'workflow/reference').glob('case-*/REFERENCE_CHECK.json'):
        value = json.loads(report.read_bytes())
        value['input_source_hashes'] = {name: sha(batch / report.parent.name / 'data' / name) for name in CAPS}
        report.write_bytes(canonical(value))
    report = child / 'workflow/reference/BATCH_REFERENCE_CHECK.json'
    value = json.loads(report.read_bytes())
    value.update(input_root_manifest_sha256=sha(batch / 'SHA256SUMS.txt'),
                 input_portable_manifest_sha256=sha(batch / 'PORTABLE_SHA256SUMS.txt'))
    report.write_bytes(canonical(value))
    workflow = child / 'workflow/WORKFLOW.json'
    value = json.loads(workflow.read_bytes())
    value['batch_portable_manifest_sha256'] = sha(batch / 'PORTABLE_SHA256SUMS.txt')
    workflow.write_bytes(canonical(value))
    rehash_all(root)
