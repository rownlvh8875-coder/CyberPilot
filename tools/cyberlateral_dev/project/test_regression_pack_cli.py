"""R35 real CLI workflow: literals first, saved-byte parity second."""

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_regression_pack import EXPECTED, PACK, assert_case, assert_typed
from v1_helpers import ROOT


def cli(tool, *args):
    return subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools' / tool, *map(str, args)],
                          capture_output=True, timeout=45, check=False)


def batch(inputs, output):
    args = [part for source in inputs for part in ['--input', source]]
    return cli('scenario_batch.py', *args, '--output', output)


def saved_json(root, name):
    return json.loads((root / name).read_bytes())


class RegressionPackCLITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix='r35-pack-test-')
        cls.addClassCleanup(cls.scratch.cleanup)
        cls.root = Path(cls.scratch.name)
        cls.want = json.loads(EXPECTED.read_bytes())
        cls.inputs = [PACK / name for name in cls.want['order']]
        cls.originals = {p: p.read_bytes() for p in [EXPECTED, *cls.inputs]}
        cls.batches = [cls.root / name for name in ['one', 'two']]
        cls.batch_results = [batch(cls.inputs, output) for output in cls.batches]
        for result in cls.batch_results:
            if result.returncode != 1:
                raise AssertionError('Expected mixed batch exit1: ' + result.stderr.decode())
        cls.comparisons = [cls.root / name for name in ['compare-one', 'compare-two']]
        cls.compare_results = [cli('scenario_compare.py', '--baseline', cls.batches[0],
                                   '--candidate', cls.batches[1], '--output', output) for output in cls.comparisons]

    def test_mixed_batch_rows_states_csv_and_view_match_hand_literals(self):
        for output in self.batches:
            record = saved_json(output, 'BATCH.json')
            self.assertEqual((record['input_count'], record['completed'], record['rejected'],
                              record['total_model_steps'], record['renderer_model_executions']), (9, 6, 3, 38, 0))
            self.assertEqual([r['input_name'] for r in record['cases']], self.want['order'])
            for case, filename in zip(record['cases'], self.want['order'], strict=True):
                with self.subTest(run=output.name, fixture=filename):
                    want = self.want['cases'][filename]
                    if 'rejection_code' in want:
                        self.assertEqual((case['status'], case['rejection_code'], case['model_steps']),
                                         ('REJECTED', want['rejection_code'], 0))
                        self.assertIsNone(case['data'])
                        self.assertIsNone(case['report'])
                        self.assertFalse((output / case['case_id']).exists())
                        continue
                    result = saved_json(output / case['data'], 'RESULTS.json')
                    assert_case(self, filename, result)
                    view = saved_json(output / case['report'], 'VIEW.json')
                    assert_typed(self, [[r[key] for key in self.want['row_columns']] for r in view['rows']], want['rows'])
                    self.assertEqual(view['renderer_model_executions'], 0)
                    with (output / case['data'] / 'TRACE.csv').open(newline='') as stream:
                        rows = list(csv.DictReader(stream))
                    expected_text = [['null' if v is None else str(v).lower() if type(v) is bool else str(v)
                                      for v in row] for row in want['rows']]
                    self.assertEqual([[r[key] for key in self.want['row_columns']] for r in rows], expected_text)

    def test_all_manifests_and_every_portable_byte_reproduce(self):
        for output in [*self.batches, *self.comparisons]:
            for manifest in output.rglob('*SHA256SUMS.txt'):
                for line in manifest.read_text().splitlines():
                    digest, name = line.split('  ')
                    self.assertEqual(hashlib.sha256((manifest.parent / name).read_bytes()).hexdigest(), digest)
        raw = (self.batches[0] / 'PORTABLE_SHA256SUMS.txt').read_bytes()
        self.assertEqual(raw, (self.batches[1] / 'PORTABLE_SHA256SUMS.txt').read_bytes())
        names = [line.split('  ')[1] for line in raw.decode().splitlines()]
        self.assertEqual(len(names), 47)
        for name in names:
            self.assertEqual((self.batches[0] / name).read_bytes(), (self.batches[1] / name).read_bytes())
        self.assertEqual(self.originals, {p: p.read_bytes() for p in self.originals})

    def test_closed_gates_and_no_rate_policy_values(self):
        for output, marker in [(p, 'BATCH.json') for p in self.batches] + [(p, 'COMPARE.json') for p in self.comparisons]:
            gates = saved_json(output, marker)['gates']
            self.assertEqual(gates['R_BUDGET'], 'UNRESOLVED')
            self.assertEqual(gates['STATIC_EVIDENCE_GATE'], 'FAIL')
            self.assertEqual(gates['Candidate'], 'NO_GO')
            self.assertEqual(gates['Runtime'], 'NO_GO')
            for key in ['actual_r', 'T2', 'vehicle_scale']:
                self.assertIsNone(gates[key])
            for key in ['actual_production_activation', 'actual_vehicle_input_authorization', 'F70UH', 'F70V', 'F71']:
                self.assertEqual(gates[key], 'NOT_ALLOWED')
            for key in ['F61_calculator_executions', 'r_calculations', 'dt_calculations']:
                self.assertEqual(gates[key], 0)

    def test_saved_rejected_inputs_match_and_comparator_does_no_model_work(self):
        for result, output in zip(self.compare_results, self.comparisons, strict=True):
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            record = saved_json(output, 'COMPARE.json')
            self.assertEqual((record['status'], record['difference_count'], record['compared_sample_count'],
                              record['new_model_executions']), ('MATCH', 0, 38, 0))
            self.assertTrue(record['all_observed_producer_identities_match'])
            self.assertEqual([r['classification'] for r in record['cases']], ['MATCH'] * 9)
            self.assertEqual(saved_json(output, 'RECEIPT.json')['forbidden_modules_loaded'], [])
        for name in ['COMPARE.json', 'SUMMARY_KO.md']:
            self.assertEqual((self.comparisons[0] / name).read_bytes(), (self.comparisons[1] / name).read_bytes())

    def test_changed_raw_input_is_not_mislabeled_as_same_input_regression(self):
        changed = json.loads(self.originals[self.inputs[0]])
        changed['samples'][0]['request'] = 0.5
        source = self.root / 'changed-positive.json'
        source.write_text(json.dumps(changed), encoding='utf-8')
        output = self.root / 'changed-batch'
        result = batch([source, *self.inputs[1:]], output)
        self.assertEqual(result.returncode, 1, result.stderr.decode())
        comparison = self.root / 'changed-comparison'
        result = cli('scenario_compare.py', '--baseline', self.batches[0], '--candidate', output, '--output', comparison)
        self.assertEqual(result.returncode, 1, result.stderr.decode())
        record = saved_json(comparison, 'COMPARE.json')
        self.assertEqual(record['status'], 'DIFFERENT')
        self.assertEqual(record['cases'][0]['classification'], 'INPUT_CHANGED')
        self.assertEqual([r['classification'] for r in record['cases'][1:]], ['MATCH'] * 8)
        self.assertEqual(record['new_model_executions'], 0)
        self.assertEqual(self.originals, {p: p.read_bytes() for p in self.originals})
