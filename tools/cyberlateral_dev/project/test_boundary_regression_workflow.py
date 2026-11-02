"""R41 real workflow parity and coherent wrong-history negative controls."""

import hashlib
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_boundary_regression_pack import EXPECTED, PACK, assert_saved_case
from test_regression_pack import assert_typed, row_projection
from v1_helpers import ROOT


def read_json(path):
    return json.loads(path.read_bytes())


def rewrite_saved(source, change):
    """Rebuild duplicate projections of a deliberate wrong saved record, no model."""
    from integration_tools.scenario_output import render_outputs
    from integration_tools.scenario_report_data import _spec

    record = read_json(source / 'RESULTS.json')
    change(record)
    result = {key: record[key] for key in ['model_steps', 'rows', 'final_state']}
    files = render_outputs(_spec(read_json(source / 'INPUT.json')), result,
                           record['identity'], read_json(source / 'RECEIPT.json'))
    for name, raw in files.items():
        (source / name).write_bytes(raw)


class BoundaryRegressionWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix='r41-workflow-test-')
        cls.addClassCleanup(cls.scratch.cleanup)
        cls.root = Path(cls.scratch.name)
        cls.want = read_json(EXPECTED)
        cls.inputs = [PACK / name for name in cls.want['order']]
        cls.originals = {p: p.read_bytes() for p in [EXPECTED, *cls.inputs]}
        cls.outputs = [cls.root / name for name in ['one', 'two', 'baseline-check']]
        cls.records = []
        for i, output in enumerate(cls.outputs):
            args = [part for source in cls.inputs for part in ['--input', str(source)]]
            if i == 2:
                args.extend(['--baseline', str(cls.outputs[0] / 'batch')])
            result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'tools/scenario_workflow.py'),
                                     *args, '--output', str(output)], capture_output=True, timeout=90, check=False)
            if result.returncode != 0:
                raise AssertionError(f'R41 workflow failed: exit{result.returncode}: {result.stderr.decode()}')
            cls.records.append(read_json(output / 'WORKFLOW.json'))

    def test_all_three_workflows_keep_saved_selected_rows_and_views(self):
        for output, record in zip(self.outputs, self.records, strict=True):
            assert_typed(self, [record[k] for k in ['status', 'completed', 'rejected', 'model_steps', 'reference_steps']],
                         ['VERIFIED', 3, 0, 324, 324])
            batch = read_json(output / 'batch/BATCH.json')
            for case, filename in zip(batch['cases'], self.want['order'], strict=True):
                saved = read_json(output / 'batch' / case['data'] / 'RESULTS.json')
                assert_saved_case(self, filename, saved)
                view = read_json(output / 'batch' / case['report'] / 'VIEW.json')
                assert_typed(self, [[row[k] for k in self.want['row_columns']] for row in view['rows']], row_projection(saved))
                self.assertEqual(view['renderer_model_executions'], 0)

    def test_independent_selected_source_checks_all324_steps_and_full_state(self):
        for output, workflow in zip(self.outputs, self.records, strict=True):
            self.assertEqual((workflow['reference_status'], workflow['reference_difference_count']), ('MATCH', 0))
            reference = read_json(output / 'reference/BATCH_REFERENCE_CHECK.json')
            self.assertEqual((reference['matched_cases'], reference['reference_steps'], reference['new_model_executions']), (3, 324, 0))
            counts = reference['reference_helper_counts']
            self.assertEqual((counts['limiter_traced'], counts['fault_explicit'], counts['traced_clip_calls']), (324, 324, 648))
            self.assertEqual([c['reference_steps'] for c in reference['cases']], [12, 128, 184])
            for case in reference['cases']:
                detail = read_json(output / 'reference' / case['report'])
                self.assertEqual((detail['status'], detail['difference_count']), ('MATCH', 0))
                self.assertEqual(detail['reference_forbidden_modules_loaded'], [])

    def test_full_nested_manifest_closure_and_portable_reproduction(self):
        for output in self.outputs:
            for manifest in output.rglob('*SHA256SUMS.txt'):
                for line in manifest.read_text().splitlines():
                    sha, name = line.split('  ')
                    self.assertEqual(hashlib.sha256((manifest.parent / name).read_bytes()).hexdigest(), sha)
            root_names = {line.split('  ')[1] for line in (output / 'SHA256SUMS.txt').read_text().splitlines()}
            self.assertEqual(root_names, {p.relative_to(output).as_posix() for p in output.rglob('*')
                                         if p.is_file() and p != output / 'SHA256SUMS.txt'})
        one, two = self.outputs[:2]
        for name in ['WORKFLOW.json', 'SUMMARY_KO.md', 'VALIDATION.json', 'batch/PORTABLE_SHA256SUMS.txt']:
            self.assertEqual((one / name).read_bytes(), (two / name).read_bytes())
        lines = (one / 'batch/PORTABLE_SHA256SUMS.txt').read_text().splitlines()
        self.assertEqual(len(lines), 23)
        for line in lines:
            name = line.split('  ')[1]
            self.assertEqual((one / 'batch' / name).read_bytes(), (two / 'batch' / name).read_bytes())
        # Private path-bearing receipts are intentionally outside portable equality.
        self.assertNotEqual((one / 'RECEIPT.json').read_bytes(), (two / 'RECEIPT.json').read_bytes())

    def test_complete_baseline_comparison_covers324_samples_without_new_model(self):
        record = self.records[2]
        self.assertEqual((record['regression_status'], record['regression_difference_count']), ('MATCH', 0))
        comparison = read_json(self.outputs[2] / 'regression/COMPARE.json')
        self.assertEqual((comparison['status'], comparison['difference_count'], comparison['compared_sample_count'],
                          comparison['new_model_executions']), ('MATCH', 0, 324, 0))
        self.assertEqual([c['classification'] for c in comparison['cases']], ['MATCH', 'MATCH', 'MATCH'])

    def test_no_policy_time_or_vehicle_gate_is_opened_and_inputs_unchanged(self):
        self.assertEqual(self.originals, {p: p.read_bytes() for p in self.originals})
        for workflow in self.records:
            self.assertEqual(workflow['time_semantics'], 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME')
            for name in ['validation_new_model_executions', 'renderer_new_model_executions',
                         'reference_new_public_model_executions', 'regression_new_model_executions']:
                self.assertEqual(workflow[name], 0)
            gates = workflow['gates']
            self.assertEqual((gates['R_BUDGET'], gates['STATIC_EVIDENCE_GATE'], gates['Candidate'], gates['Runtime']),
                             ('UNRESOLVED', 'FAIL', 'NO_GO', 'NO_GO'))
            self.assertTrue(all(gates[k] is None for k in ['actual_r', 'T2', 'vehicle_scale']))
            for name in ['F70UH', 'F70V', 'F71', 'actual_production_activation', 'actual_vehicle_input_authorization']:
                self.assertEqual(gates[name], 'NOT_ALLOWED')
            for name in ['F61_calculator_executions', 'r_calculations', 'dt_calculations']:
                self.assertEqual(gates[name], 0)

    def check_mutant(self, case_id, name, change, expected_field, steps):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        reference = importlib.import_module('integration_tools.scenario_reference_run')
        source = self.root / (name + '-saved')
        original = self.outputs[0] / 'batch' / case_id / 'data'
        before = {p.name: p.read_bytes() for p in original.iterdir()}
        shutil.copytree(original, source)
        rewrite_saved(source, change)
        record = reference.check_saved(source, self.root / (name + '-check'))
        self.assertEqual((record['status'], record['new_model_executions'], record['reference_steps']), ('DIFFERENT', 0, steps))
        self.assertTrue(any(d['field'] == expected_field for d in record['differences']))
        self.assertEqual(before, {p.name: p.read_bytes() for p in original.iterdir()})

    def test_coherent_wrong_applied_at_cycle_boundary_is_not_reference_history(self):
        def change(record):
            output = record['rows'][7]['model_output']
            output['projection'].update(integer_command=16, normalized_expression=1.0,
                                        normalized_expression_hex='0x1.0000000000000p+0')
            output['trace']['downstream']['final_command'] = 16
            output['next_state']['previous_applied'] = 16
            output['trace']['downstream']['next_state']['previous_applied'] = 16
            record['rows'][8]['prepared']['state']['previous_applied'] = 16
            record['rows'][8]['model_output']['trace']['downstream']['limiter_previous'] = 16

        self.check_mutant('case-002', 'wrong-applied', change, 'rows[8].prepared.state.previous_applied', 128)

    def test_coherent_wrong_fault_counter_is_not_reference_counter(self):
        def change(record):
            output = record['rows'][89]['model_output']
            output['next_state']['angle_counter'] = 89
            output['trace']['downstream']['next_state']['angle_counter'] = 89
            record['rows'][90]['prepared']['state']['angle_counter'] = 89

        self.check_mutant('case-003', 'wrong-counter', change, 'rows[90].prepared.state.angle_counter', 184)
