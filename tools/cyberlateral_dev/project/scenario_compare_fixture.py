"""Synthetic saved-batch test construction, never a model/origin attestation."""

import hashlib
import json

from scenario_report_fixture import canonical, rehash, write_bundle
from v1_helpers import ROOT


def manifest(files):
    return ''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n' for name, raw in sorted(files.items())).encode()


def refresh(root):
    from integration_tools.scenario_report_data import read_report

    record = json.loads((root / 'BATCH.json').read_bytes())
    portable = {'BATCH.json': canonical(record), 'index.html': (root / 'index.html').read_bytes()}
    for row in record['cases']:
        if row['snapshot']:
            portable[row['snapshot']] = (root / row['snapshot']).read_bytes()
        if row['status'] == 'COMPLETE':
            data, report = root / row['data'], root / row['report']
            rehash(data)
            view = read_report(data)['view']
            (report / 'VIEW.json').write_bytes(canonical(view))
            (report / 'SHA256SUMS.txt').write_bytes(manifest({p.name: p.read_bytes() for p in report.iterdir() if p.name != 'SHA256SUMS.txt'}))
            for directory, names in [(data, ['INPUT.json', 'RESULTS.json', 'TRACE.csv', 'SUMMARY_KO.md']), (report, ['VIEW.json', 'index.html'])]:
                portable.update({(directory / n).relative_to(root).as_posix(): (directory / n).read_bytes() for n in names})
    (root / 'PORTABLE_SHA256SUMS.txt').write_bytes(manifest(portable))
    (root / 'SHA256SUMS.txt').write_bytes(manifest({p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*')
                                                if p.is_file() and p != root / 'SHA256SUMS.txt'}))


def write_batch(root, profiles=('sign', 'resumed')):
    from integration_tools.scenario_output import GATES

    root.mkdir()
    (root / 'inputs').mkdir()
    cases: list[dict] = []
    for number, profile in enumerate(profiles, 1):
        case = f'case-{number:03d}'
        complete = profile in ('sign', 'resumed')
        raw = (ROOT / ('examples/synthetic_' + ('sign_cycle' if profile == 'sign' else 'resumed') + '_v1.json')).read_bytes() if complete else b'{'
        snapshot = f'inputs/{case}.json' if profile != 'missing' else None
        if snapshot:
            (root / snapshot).write_bytes(raw)
        row = {'case_id': case, 'input_name': profile + '.json', 'input_sha256': hashlib.sha256(raw).hexdigest() if snapshot else None,
               'snapshot': snapshot, 'scenario_id': None, 'status': 'REJECTED', 'rejection_code': 'SCENARIO_JSON' if snapshot else 'SCENARIO_INPUT_FILE',
               'model_steps': 0, 'data': None, 'report': None}
        if complete:
            (root / case).mkdir()
            data = write_bundle(root / case / 'data', profile)
            record = json.loads((data / 'RESULTS.json').read_bytes())
            report = root / case / 'report'
            report.mkdir()
            (report / 'index.html').write_bytes(b'<!doctype html><title>saved fixture</title>')
            (report / 'RECEIPT.json').write_bytes(canonical({'scope': 'SYNTHETIC_TEST_FIXTURE'}))
            for name in ['producer.log', 'renderer.log']:
                (root / case / name).write_bytes(b'SYNTHETIC_FIXTURE_NOT_NEW_MODEL_EXECUTION\n')
            row.update(status='COMPLETE', rejection_code=None, scenario_id=record['scenario_id'], model_steps=record['model_steps'],
                       data=f'{case}/data', report=f'{case}/report')
        cases.append(row)
    rejected = sum(r['status'] == 'REJECTED' for r in cases)
    record = {'schema_version': 1, 'contract_id': 'F70UGZ_R33_DECLARED_SYNTHETIC_BATCH_V1',
              'status': 'BATCH_COMPLETE_WITH_REJECTIONS' if rejected else 'BATCH_COMPLETE',
              'input_count': len(cases), 'completed': len(cases) - rejected, 'rejected': rejected,
              'total_model_steps': sum(r['model_steps'] for r in cases), 'renderer_model_executions': 0,
              'input_order': 'EXPLICIT_ARGUMENT_ORDER', 'state_scope': 'INDEPENDENT_PER_FILE_NO_CROSS_FILE_STATE',
              'input_origin': 'CALLER_DECLARATION_NOT_AUTHENTICATED', 'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
              'numerical_claim': 'MODEL_RESULTS_NOT_GENERIC_INDEPENDENT_ORACLE', 'gates': dict(GATES), 'cases': cases}
    (root / 'BATCH.json').write_bytes(canonical(record))
    (root / 'index.html').write_bytes(b'<!doctype html><title>synthetic batch fixture</title>')
    (root / 'RECEIPT.json').write_bytes(canonical({'scope': 'SYNTHETIC_TEST_FIXTURE', 'never_open': '/private/not-an-input',
                                                'observed_source_hashes': {'integration_tools/scenario_batch_run.py': '0' * 64}}))
    refresh(root)
    return root


def edit_batch(root, change):
    value = json.loads((root / 'BATCH.json').read_bytes())
    change(value)
    (root / 'BATCH.json').write_bytes(canonical(value))
    # Deliberately hash all actual files, without repairing record contradictions.
    (root / 'SHA256SUMS.txt').write_bytes(manifest({p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*')
                                                if p.is_file() and p != root / 'SHA256SUMS.txt'}))
