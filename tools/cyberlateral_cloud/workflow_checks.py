"""Check real saved R41 workflows and choose portable, path-free payloads."""

import argparse
import importlib
import json
import sys
import unittest
from pathlib import Path

from artifacts import sha, validate_names


def verify_tree(root: Path) -> list[dict]:
    paths = list(root.rglob('*'))
    if root.is_symlink() or any(p.is_symlink() for p in paths):
        raise ValueError('MANIFEST_SYMLINK')
    files = {p.relative_to(root).as_posix(): p for p in paths if p.is_file()}
    validate_names(files)
    records = []
    root_names = None
    for name, path in sorted(files.items()):
        if not name.endswith('SHA256SUMS.txt'):
            continue
        entries = {}
        for line in path.read_text().splitlines():
            digest, member = line.split('  ')
            if member in entries:
                raise ValueError('MANIFEST_CLOSURE')
            entries[member] = digest
        validate_names(entries)
        for member, digest in entries.items():
            target = path.parent / member
            if not target.resolve().is_relative_to(root.resolve()) or not target.is_file():
                raise ValueError('MANIFEST_CLOSURE')
            if sha(target.read_bytes()) != digest:
                raise ValueError('MANIFEST_HASH')
        records.append({'manifest': name, 'entries': len(entries)})
        if name == 'SHA256SUMS.txt':
            root_names = set(entries)
    if root_names != set(files) - {'SHA256SUMS.txt'}:
        raise ValueError('MANIFEST_CLOSURE')
    return records


def portable_files(root: Path) -> dict[str, bytes]:
    verify_tree(root)
    names = ['WORKFLOW.json', 'SUMMARY_KO.md', 'VALIDATION.json']
    for line in (root / 'batch/PORTABLE_SHA256SUMS.txt').read_text().splitlines():
        _, member = line.split('  ')
        names.append('batch/' + member)
    validate_names(names)
    allowed = {'WORKFLOW.json', 'SUMMARY_KO.md', 'VALIDATION.json', 'batch/BATCH.json', 'batch/index.html'}
    for number in range(1, 4):
        case = f'case-{number:03d}'
        allowed.add(f'batch/inputs/{case}.json')
        allowed.update(f'batch/{case}/data/{n}' for n in ['INPUT.json', 'RESULTS.json', 'SUMMARY_KO.md', 'TRACE.csv'])
        allowed.update(f'batch/{case}/report/{n}' for n in ['VIEW.json', 'index.html'])
    if set(names) != allowed:
        raise ValueError('PORTABLE_ALLOWLIST')
    return {name: (root / name).read_bytes() for name in names}


def check_workflows(component: Path, root: Path) -> dict:
    sys.path.insert(0, str(component))
    sys.path.insert(0, str(component / 'project'))
    literal = importlib.import_module('test_boundary_regression_pack')
    rows = importlib.import_module('test_regression_pack')
    test = unittest.TestCase()
    expected = json.loads((component / 'reference/r41_regression_expected_v1.json').read_bytes())
    total = sum(expected['cases'][n]['sample_count'] for n in expected['order'])
    if total != 324 or len(expected['order']) != 3:
        raise ValueError('R41_FIXED_PACK_CONTRACT')
    checks = []
    for alias in ['one', 'two', 'baseline']:
        saved = root / alias
        checks.extend({'run': alias, **r} for r in verify_tree(saved))
        record = json.loads((saved / 'WORKFLOW.json').read_bytes())
        rows.assert_typed(test, [record[k] for k in ['status', 'completed', 'rejected', 'model_steps', 'reference_steps']],
                          ['VERIFIED', 3, 0, 324, 324])
        test.assertEqual((record['reference_status'], record['reference_difference_count']), ('MATCH', 0))
        test.assertEqual(record['time_semantics'], 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME')
        gates = record['gates']
        test.assertEqual((gates['R_BUDGET'], gates['STATIC_EVIDENCE_GATE'], gates['Candidate'], gates['Runtime']),
                         ('UNRESOLVED', 'FAIL', 'NO_GO', 'NO_GO'))
        for field in ['actual_r', 'T2', 'vehicle_scale']:
            test.assertIsNone(gates[field])
        for field in ['F70UH', 'F70V', 'F71', 'actual_production_activation', 'actual_vehicle_input_authorization']:
            test.assertEqual(gates[field], 'NOT_ALLOWED')
        for field in ['F61_calculator_executions', 'r_calculations', 'dt_calculations']:
            rows.assert_typed(test, gates[field], 0)
        batch = json.loads((saved / 'batch/BATCH.json').read_bytes())
        test.assertEqual(len(batch['cases']), 3)
        for number, (case, filename) in enumerate(zip(batch['cases'], expected['order'], strict=True), 1):
            test.assertEqual(case['data'], f'case-{number:03d}/data')
            test.assertEqual(case['report'], f'case-{number:03d}/report')
            data = json.loads((saved / 'batch' / case['data'] / 'RESULTS.json').read_bytes())
            literal.assert_saved_case(test, filename, data)
            view = json.loads((saved / 'batch' / case['report'] / 'VIEW.json').read_bytes())
            rows.assert_typed(test, [[r[k] for k in expected['row_columns']] for r in view['rows']], rows.row_projection(data))
            test.assertEqual(view['renderer_model_executions'], 0)
        reference = json.loads((saved / 'reference/BATCH_REFERENCE_CHECK.json').read_bytes())
        test.assertEqual((reference['status'], reference['matched_cases'], reference['reference_steps'],
                          reference['new_model_executions']), ('MATCH', 3, 324, 0))
        test.assertEqual([c['reference_steps'] for c in reference['cases']], [12, 128, 184])
        test.assertEqual([reference['reference_helper_counts'][k] for k in ['limiter_traced', 'fault_explicit', 'traced_clip_calls']],
                         [324, 324, 648])
        for number, case in enumerate(reference['cases'], 1):
            test.assertEqual(case['report'], f'case-{number:03d}/REFERENCE_CHECK.json')
            detail = json.loads((saved / 'reference' / case['report']).read_bytes())
            test.assertEqual(detail['reference_forbidden_modules_loaded'], [])
    one, two = [portable_files(root / n) for n in ['one', 'two']]
    if one != two or len(one) != 26:
        raise ValueError('PORTABLE_REPRODUCTION')
    comparison = json.loads((root / 'baseline/regression/COMPARE.json').read_bytes())
    test.assertEqual((comparison['status'], comparison['difference_count'], comparison['compared_sample_count'],
                      comparison['new_model_executions']), ('MATCH', 0, 324, 0))
    return {'status': 'R41_SAVED_ACCEPTANCE_PASS', 'explicit_model_steps': 972, 'explicit_reference_steps': 972,
            'portable_files': 26, 'baseline_samples': 324, 'baseline_differences': 0,
            'manifests': checks, 'unit_gate_work': 'ADDITIONAL_NONZERO_NOT_AGGREGATED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component', type=Path, required=True)
    parser.add_argument('--work-root', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(check_workflows(args.component, args.work_root), sort_keys=True))


if __name__ == '__main__':
    main()
