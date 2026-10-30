"""Catch caller state loss, weak regression gates and unsafe harness entry paths."""

import contextlib
import hashlib
import importlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from dataclasses import asdict, replace
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

    def assert_batch_and_step_golden_controls(self, p):
        catalog = package_feature('cyberlateral_dev.synthetic_catalog').fixed_catalog()
        golden = self.expected()['scenarios']
        for scenario, expected in zip(catalog, golden, strict=True):
            full = p.simulate(scenario.samples, scenario.initial_state)
            state, outputs = scenario.initial_state, []
            for sample in scenario.samples:
                output = p.step(sample, state)
                outputs.append(output)
                state = output.next_state
            chain = p.SimulationResult(tuple(outputs), state)
            for result in [full, chain]:
                raw = (json.dumps(asdict(result), sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), expected['result_sha256'], scenario.id)

    def test_split_only_history_reset_rejected_at_resume_comparison(self):
        m, p = self.module(), package_feature()
        ramp = next(s for s in package_feature('cyberlateral_dev.synthetic_catalog').fixed_catalog() if s.id == 'ramp')
        simulate = p.simulate
        suffix = ramp.samples[1:]

        def reset_only_suffix(samples, state):
            if samples == suffix:
                # Keep the valid invocation index; erase only continuation history.
                state = replace(state, previous_requested=0, previous_applied=0, angle_counter=0)
            return simulate(samples, state)

        with patch.object(p, 'simulate', side_effect=reset_only_suffix):
            self.assert_batch_and_step_golden_controls(p)
            prefix = p.simulate(ramp.samples[:1], ramp.initial_state)
            bad_suffix = p.simulate(suffix, prefix.next_state)
            self.assertEqual([o.projection.integer_command for o in prefix.outputs + bad_suffix.outputs], [2, 2, 4])
            with self.assertRaisesRegex(m.HarnessError, '^SPLIT_RESUME_MISMATCH:ramp:1$'):
                m.run_harness(self.expected())

    def test_interleaving_only_history_leak_rejected_at_caller_comparison(self):
        m, p = self.module(), package_feature()
        step = p.step
        last_index, last_history, interleaving = None, None, False

        def leak_only_interleaved(sample, state):
            nonlocal last_index, last_history, interleaving
            # The closed catalog has consecutive index0 callers only in round-robin.
            if sample.index == last_index == 0:
                interleaving = True
            if interleaving and state.index > 0 and last_history is not None:
                state = replace(state, previous_requested=last_history.previous_requested,
                                previous_applied=last_history.previous_applied, angle_counter=last_history.angle_counter)
            output = step(sample, state)
            last_index, last_history = sample.index, output.next_state
            return output

        with patch.object(p, 'step', side_effect=leak_only_interleaved):
            self.assert_batch_and_step_golden_controls(p)
            with self.assertRaisesRegex(m.HarnessError, '^INTERLEAVED_CALLER_MISMATCH$'):
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

    def test_missing_package_location_rejects_without_publishing_results(self):
        m, p = self.module(), package_feature()
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / 'out'
            with patch.object(p, '__file__', None), contextlib.redirect_stderr(io.StringIO()):
                try:
                    code = m.main(['--output', str(output)])
                except TypeError:
                    code = -1
            self.assertEqual(code, 2, 'Missing package location escaped the rejection boundary')
            self.assertFalse((output / 'RESULTS.json').exists())

    def test_manifest_write_failure_does_not_publish_a_pass_result(self):
        m = self.module()
        original = Path.open

        def fail_manifest(path, *args, **kwargs):
            if path.name == 'SHA256SUMS.txt':
                raise OSError('SYNTHETIC_MANIFEST_WRITE_FAILURE')
            return original(path, *args, **kwargs)

        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / 'out'
            with patch.object(Path, 'open', fail_manifest), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(m.main(['--output', str(output)]), 2)
            self.assertFalse((output / 'RESULTS.json').exists(), 'Rejected run published a PASS result')

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


class InstalledHarnessTests(unittest.TestCase):
    def verifier(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        m = importlib.import_module('integration_tools.verify')
        self.assertTrue(hasattr(m, 'verify_installed_harness'), 'Missing installed caller verification gate')
        self.assertTrue(hasattr(m, 'harness_pair_summary'), 'Missing harness artifact acceptance gate')
        return m

    def test_real_empty_environment_pair_and_tamper_rejection(self):
        m = self.verifier()
        backend = importlib.import_module('build_backend')
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            name = backend.build_wheel(str(root / 'dist'))
            subprocess.run([sys.executable, '-B', '-m', 'venv', '--without-pip', str(root / 'env')], check=True, capture_output=True)
            py = root / 'env/bin/python'
            subprocess.run(['uv', 'pip', 'install', '--offline', '--no-deps', '--link-mode=copy', '--python', str(py),
                            str(root / 'dist' / name)], check=True, capture_output=True)
            output = root / 'artifacts'
            output.mkdir()
            result = m.verify_installed_harness(ROOT, py, output, root)
            self.assertTrue(result['byte_identical'])
            self.assertEqual((result['scenario_count'], result['total_steps'], result['two_chunk_splits'], result['rejection_cases']), (7, 112, 105, 11))
            first, second = output / 'harness_one', output / 'harness_two'
            data = json.loads((first / 'RESULTS.json').read_bytes())
            self.assertEqual(data['execution_environment'], {
                'isolated': True, 'installed_package': True, 'numpy_available': False, 'forbidden_modules_loaded': [],
            })
            (second / 'RESULTS.json').write_bytes(b'{}\n')
            with self.assertRaisesRegex(ValueError, 'REPRODUCTION_BYTE_MISMATCH'):
                m.harness_pair_summary(first, second)
            data['status'] = 'NOT_PASS'
            raw = m.canonical(data)
            for directory in [first, second]:
                (directory / 'RESULTS.json').write_bytes(raw)
                (directory / 'SHA256SUMS.txt').write_text(hashlib.sha256(raw).hexdigest() + '  RESULTS.json\n')
            with self.assertRaisesRegex(ValueError, 'HARNESS_CONTRACT'):
                m.harness_pair_summary(first, second)

    def test_missing_harness_results_cannot_be_a_successful_empty_pair(self):
        m = self.verifier()
        with tempfile.TemporaryDirectory() as scratch:
            first, second = Path(scratch) / 'one', Path(scratch) / 'two'
            first.mkdir()
            second.mkdir()
            with self.assertRaisesRegex(ValueError, 'MISSING_HARNESS_ARTIFACTS'):
                m.harness_pair_summary(first, second)

    def test_identically_malformed_payloads_with_valid_checksums_reject(self):
        m = self.verifier()
        harness = SyntheticHarnessTests().module()
        data = harness.run_harness(SyntheticHarnessTests().expected())
        data['execution_environment'] = {
            'isolated': True, 'installed_package': True, 'numpy_available': False, 'forbidden_modules_loaded': [],
        }
        with tempfile.TemporaryDirectory() as scratch:
            first, second = Path(scratch) / 'one', Path(scratch) / 'two'
            first.mkdir()
            second.mkdir()
            for corruption in ['missing-scenarios', 'result', 'fixture', 'golden-source', 'rejections', 'gates']:
                bad = deepcopy(data)
                if corruption == 'missing-scenarios':
                    del bad['scenarios']
                elif corruption == 'result':
                    scenario = bad['scenarios'][0]
                    scenario['result']['outputs'][0]['projection']['integer_command'] = 999
                    scenario['result_sha256'] = hashlib.sha256(m.canonical(scenario['result'])).hexdigest()
                elif corruption == 'fixture':
                    bad['fixture_catalog_sha256'] = '0' * 64
                elif corruption == 'golden-source':
                    bad['golden_source_report_sha256'] = '0' * 64
                elif corruption == 'rejections':
                    bad['rejections'][0]['code'] = 'WRONG_REJECTION'
                else:
                    bad['gates']['STATIC_EVIDENCE_GATE'] = 'PASS'
                raw = m.canonical(bad)
                for directory in [first, second]:
                    (directory / 'RESULTS.json').write_bytes(raw)
                    (directory / 'SHA256SUMS.txt').write_text(hashlib.sha256(raw).hexdigest() + '  RESULTS.json\n')
                with self.subTest(corruption=corruption), self.assertRaisesRegex(ValueError, 'HARNESS_CONTRACT'):
                    m.harness_pair_summary(first, second)

    def test_typecheck_boundary_rejects_attribute_error_despite_parent_ignores(self):
        m = self.verifier()
        self.assertTrue(hasattr(m, 'typecheck_project'), 'Missing explicit component typecheck boundary')
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            probe = root / 'probe.py'
            probe.write_text('value = object()\nvalue.nonexistent_attribute\n')
            log = root / 'probe.log'
            with self.assertRaisesRegex(RuntimeError, 'COMMAND_FAILED'):
                m.typecheck_project(ROOT, Path(sys.executable), [probe], log)
            self.assertIn('unresolved-attribute', log.read_text())


if __name__ == '__main__':
    unittest.main()
