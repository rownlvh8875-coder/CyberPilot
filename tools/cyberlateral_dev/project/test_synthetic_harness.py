"""Catch caller state loss, weak regression gates and unsafe harness entry paths."""

import contextlib
import hashlib
import importlib
import io
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


class SyntheticHarnessTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/synthetic_harness.py').is_file(), 'Missing planned synthetic caller harness')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        package_feature()
        return importlib.import_module('integration_tools.synthetic_harness')

    def expected(self):
        return json.loads((ROOT / 'reference/synthetic_harness_expected_v1.json').read_bytes())

    def test_fixed_catalog_step_split_and_interleaved_callers_pass(self):
        m = self.module()
        result = m.run_harness(self.expected())
        self.assertEqual(result['status'], 'F70UGZ_R9_SYNTHETIC_CALLER_HARNESS_PASS')
        self.assertEqual((result['scenario_count'], result['total_steps'], result['two_chunk_splits']), (7, 112, 105))
        self.assertTrue(result['step_chain_parity'])
        self.assertTrue(result['interleaved_caller_parity'])
        ramp = next(s for s in result['scenarios'] if s['id'] == 'ramp')
        self.assertEqual([o['projection']['integer_command'] for o in ramp['result']['outputs']], [2, 4, 6])
        inactive = next(s for s in result['scenarios'] if s['id'] == 'inactive')
        self.assertEqual([o['projection']['integer_command'] for o in inactive['result']['outputs']], [2, 0, 0, 2])
        self.assertEqual(result['gates']['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(result['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
        for key in ['actual_r', 'actual_T2', 'actual_vehicle_scale']:
            self.assertIsNone(result['gates'][key])

    def test_poisoned_or_incomplete_golden_rejects(self):
        m = self.module()
        for mutation, code in [('fixture', 'FIXTURE_IDENTITY'), ('result', 'GOLDEN_RESULT'), ('missing', 'GOLDEN_COVERAGE')]:
            expected = deepcopy(self.expected())
            if mutation == 'fixture':
                expected['fixture_catalog_sha256'] = '0' * 64
            elif mutation == 'result':
                expected['scenarios'][0]['result_sha256'] = '0' * 64
            else:
                expected['scenarios'].pop()
            with self.subTest(mutation=mutation), self.assertRaisesRegex(m.HarnessError, code):
                m.run_harness(expected)

    def test_corrupted_batch_result_cannot_match_golden(self):
        m, p = self.module(), package_feature()
        simulate = p.simulate

        def corrupt(samples, state):
            return replace(simulate(samples, state), outputs=())

        with patch.object(p, 'simulate', side_effect=corrupt), self.assertRaisesRegex(m.HarnessError, 'GOLDEN_RESULT'):
            m.run_harness(self.expected())

    def test_single_step_caller_corruption_cannot_hide_behind_batch(self):
        m, p = self.module(), package_feature()
        step = p.step

        def corrupt(sample, state):
            result = step(sample, state)
            return replace(result, steer_request=not result.steer_request)

        with patch.object(p, 'step', side_effect=corrupt), self.assertRaisesRegex(m.HarnessError, 'STEP_CHAIN'):
            m.run_harness(self.expected())

    def test_exact_rejections_preserve_the_supplied_state(self):
        m = self.module()
        result = m.run_harness(self.expected())
        observed = {r['id']: (r['exception'], r['code']) for r in result['rejections']}
        self.assertEqual(observed, {
            'missing-state': ('FlowError', 'EXACT_SYNTHETIC_MODELS_REQUIRED'),
            'reset-mid-sequence': ('FlowError', 'ADJACENT_MODEL_INVOCATION_REQUIRED'),
            'gap': ('FlowError', 'ADJACENT_MODEL_INVOCATION_REQUIRED'),
            'duplicate': ('FlowError', 'ADJACENT_MODEL_INVOCATION_REQUIRED'),
            'missing-history': ('FlowError', 'SYNTHETIC_STATE_INTEGER_REQUIRED'),
            'missing-limits': ('QuantizationError', 'EXACT_SYNTHETIC_SAMPLE_AND_LIMITS_REQUIRED'),
            'nonfinite-request': ('QuantizationError', 'BUILTIN_FINITE_NORMALIZED_FLOAT_REQUIRED'),
            'exhausted-state': ('FlowError', 'SYNTHETIC_STATE_INTEGER_REQUIRED'),
            'production-label': ('QuantizationError', 'SYNTHETIC_SCOPE_REQUIRED'),
            'empty-batch': ('SimulationError', 'EXPLICIT_BOUNDED_SYNTHETIC_TUPLE_REQUIRED'),
            'list-batch': ('SimulationError', 'EXPLICIT_BOUNDED_SYNTHETIC_TUPLE_REQUIRED'),
        })
        self.assertTrue(all(r['state_unchanged'] for r in result['rejections']))

    def test_existing_file_directory_and_dangling_link_reject_before_work(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            targets = [root / 'file', root / 'directory', root / 'dangling']
            targets[0].write_bytes(b'KEEP')
            targets[1].mkdir()
            targets[2].symlink_to(root / 'absent', target_is_directory=True)
            for target in targets:
                with contextlib.redirect_stderr(io.StringIO()), patch.object(m, 'run_harness', side_effect=AssertionError('NO_WORK')):
                    self.assertEqual(m.main(['--output', str(target)]), 2)
            self.assertEqual(targets[0].read_bytes(), b'KEEP')
            self.assertEqual(list(targets[1].iterdir()), [])
            self.assertTrue(targets[2].is_symlink())

    def test_arbitrary_input_mode_is_not_exposed(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / 'out'
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                m.main(['--output', str(output), '--data', 'actual-log'])
            self.assertEqual(error.exception.code, 2)
            self.assertFalse(output.exists())

    def test_two_cli_runs_emit_exact_canonical_results_and_manifest(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            outputs = [Path(scratch) / 'one', Path(scratch) / 'two']
            for output in outputs:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(m.main(['--output', str(output)]), 0)
            one = {p.name: p.read_bytes() for p in outputs[0].iterdir()}
            self.assertEqual(set(one), {'RESULTS.json', 'SHA256SUMS.txt'})
            self.assertEqual(one, {p.name: p.read_bytes() for p in outputs[1].iterdir()})
            raw = one['RESULTS.json']
            expected = (json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
            self.assertEqual(raw, expected)
            self.assertEqual(one['SHA256SUMS.txt'], (hashlib.sha256(raw).hexdigest() + '  RESULTS.json\n').encode())


if __name__ == '__main__':
    unittest.main()
