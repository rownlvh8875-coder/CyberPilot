"""The closed DEV command must preserve outcomes, bytes, work and output ownership."""

import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT


class CoreSequenceRunTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/core_sequence_run.py').is_file(), 'Missing CORE8 closed sequence runner')
        self.assertTrue((ROOT / 'tools/core_sequence.py').is_file(), 'Missing CORE8 sequence CLI')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.core_sequence_run')

    def package(self, output):
        self.assertEqual({p.name for p in output.iterdir()}, {'INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt'})
        entries = (output / 'SHA256SUMS.txt').read_text().splitlines()
        self.assertEqual([line.split('  ', 1)[1] for line in entries], ['INPUT.json', 'RESULTS.json'])
        for line in entries:
            digest, name = line.split('  ', 1)
            self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), digest)
        record = json.loads((output / 'RESULTS.json').read_bytes())
        for name in ('INPUT.json', 'RESULTS.json'):
            raw = (output / name).read_bytes()
            self.assertEqual(raw, (json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False,
                                             separators=(',', ':'), allow_nan=False) + '\n').encode())
        return record

    def reject_before_load(self, m, code, case, output):
        with patch.object(m, 'load_model', side_effect=AssertionError('MODEL_LOADED')):
            with self.assertRaises(m.DemoError) as raised:
                m.run_sequence_case(case, output)
        self.assertEqual((raised.exception.code, str(raised.exception)), (code, code))

    def command(self, case, output, cwd=None):
        return subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence.py',
                               '--case', case, '--output', output], cwd=cwd, capture_output=True, text=True)

    def test_literal_matching_sequence_publishes_three_computed_states(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'match'
            returned = m.run_sequence_case('sign-cycle', output)
            result = self.package(output)
            self.assertEqual(returned, result)
            self.assertEqual((result['status'], result['sequence_completed'], result['model_steps'],
                              result['completed_transition_count'], m.exit_code(result)), ('MATCH', True, 3, 3, 0))
            self.assertEqual([row['computed_next_state'] for row in result['rows']], [
                {'index': 6, 'previous_requested': 8, 'previous_applied': 2, 'angle_counter': 5},
                {'index': 7, 'previous_requested': -8, 'previous_applied': -2, 'angle_counter': 6},
                {'index': 8, 'previous_requested': 4, 'previous_applied': 2, 'angle_counter': 7},
            ])
            self.assertEqual([row['computed_next_state']['previous_applied'] for row in result['rows']], [2, -2, 2])
            self.assertEqual(result['differing_transition_indices'], [])

    def test_declared_difference_is_not_repaired_or_promoted_to_match(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'different'
            m.run_sequence_case('declared-difference', output)
            result = self.package(output)
            self.assertEqual((result['status'], m.exit_code(result), result['model_steps']), ('DIFFERENT', 1, 3))
            self.assertEqual(result['differing_transition_indices'], [0])
            self.assertEqual([row['status'] for row in result['rows']], ['DIFFERENT', 'MATCH', 'MATCH'])
            self.assertEqual(result['rows'][0]['differences'], [{'field': 'saved_limited_state', 'declared': 10, 'computed': 2}])
            self.assertEqual(result['rows'][1]['entry_state']['previous_applied'], 10)
            self.assertEqual([row['computed_next_state']['previous_applied'] for row in result['rows']], [2, 5, 4])

    def test_late_invalid_is_saved_preflight_rejection_not_vacuous_success(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'rejected'
            m.run_sequence_case('late-invalid', output)
            result = self.package(output)
            self.assertEqual((result['status'], result['sequence_completed'], result['model_steps'],
                              result['completed_transition_count'], m.exit_code(result)), ('REJECTED', False, 0, 0, 2))
            self.assertEqual(result['rejection_code'], 'SEQUENCE_INPUT:2:MODEL_DRIVER')
            self.assertEqual(result['rows'], [])
            self.assertEqual((result['frame_count'], result['declared_transition_count']), (4, 3))

    def test_portable_input_preserves_raw_roles_times_and_float_hex(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            m.run_sequence_case('sign-cycle', output)
            record = json.loads((output / 'INPUT.json').read_bytes())
            self.assertEqual([f['request']['requested_binary32_be_hex'] for f in record['frames']],
                             ['be800000', '3f000000', 'bf000000', '3e800000'])
            self.assertEqual([f['request']['sample_time_ns'] for f in record['frames']],
                             [1_000_000_000, 1_010_000_000, 1_020_000_000, 1_030_000_000])
            self.assertEqual([c['model_index'] for c in record['contexts']], [5, 6, 7])
            self.assertEqual([c['previous_integer_request'] for c in record['contexts']], [-4, 8, -8])
            self.assertEqual(record['contexts'][0]['current_driver_hex'], '0x1.8000000000000p+0')
            self.assertEqual(record['contexts'][0]['current_angle_deg_hex'], '0x1.5400000000000p+6')

    def test_repeated_new_outputs_are_byte_identical_and_have_no_workspace_paths(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            one, two = Path(tmp) / 'one', Path(tmp) / 'two'
            m.run_sequence_case('sign-cycle', one)
            m.run_sequence_case('sign-cycle', two)
            first = {p.name: p.read_bytes() for p in one.iterdir()}
            self.assertEqual(first, {p.name: p.read_bytes() for p in two.iterdir()})
            self.assertNotIn(str(ROOT).encode(), b''.join(first.values()))
            self.assertNotIn(str(tmp).encode(), b''.join(first.values()))

    def test_source_identity_includes_actual_cli_bytes_not_vehicle_authentication(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            result = m.run_sequence_case('sign-cycle', Path(tmp) / 'out')
            self.assertEqual(result['identity']['demo_cli_sha256'], hashlib.sha256((ROOT / 'tools/core_sequence.py').read_bytes()).hexdigest())
            self.assertEqual(result['identity']['model_version'], '0.3.0')
            self.assertIn('integration_tools/core_sequence_cases.py', result['identity']['observed_dev_source_hashes'])
            for key in ('source_authenticated', 'anchor_transition_checked', 'prehistory_checked'):
                self.assertFalse(result[key])

    def test_gates_and_actual_null_values_remain_closed_after_caller_mutates_return(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            a = m.run_sequence_case('sign-cycle', Path(tmp) / 'one')
            a['gates']['R_BUDGET'] = 'not global policy'
            b = m.run_sequence_case('sign-cycle', Path(tmp) / 'two')
            self.assertEqual((b['gates']['R_BUDGET'], b['gates']['STATIC_EVIDENCE_GATE']), ('UNRESOLVED', 'FAIL'))
            for key in ('actual_r', 'T2', 'vehicle_scale'):
                self.assertIsNone(b['gates'][key])
            for key in ('F70UH', 'F70V', 'F71'):
                self.assertEqual(b['gates'][key], 'NOT_ALLOWED')

    def test_unknown_or_nonbuiltin_case_is_rejected_before_output_or_model_access(self):
        m = self.module()

        class Foreign:
            def __getattribute__(self, _name):
                raise AssertionError('OUTPUT_READ')

        class Text(str):
            pass

        for case in ('vehicle', 'SIGN-CYCLE', None, 1, Text('sign-cycle')):
            self.reject_before_load(m, 'DEMO_CASE', case, Foreign())

    def test_existing_directory_file_and_dangling_symlink_are_not_overwritten(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'old').mkdir()
            (root / 'old/keep').write_bytes(b'keep')
            (root / 'file').write_bytes(b'file')
            (root / 'dangling').symlink_to(root / 'missing')
            for name in ('old', 'file', 'dangling'):
                self.reject_before_load(m, 'DEMO_OUTPUT_EXISTS', 'sign-cycle', root / name)
            self.assertEqual((root / 'old/keep').read_bytes(), b'keep')
            self.assertEqual((root / 'file').read_bytes(), b'file')

    def test_missing_parent_and_inside_checkout_outputs_are_rejected_before_load(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            self.reject_before_load(m, 'DEMO_OUTPUT_PARENT', 'sign-cycle', Path(tmp) / 'missing/out')
        self.reject_before_load(m, 'DEMO_OUTPUT_LOCATION', 'sign-cycle', ROOT / 'core8-test-new-output')
        self.reject_before_load(m, 'DEMO_OUTPUT_LOCATION', 'sign-cycle', ROOT.parents[1] / 'core8-test-new-output')

    def test_symlink_parent_cannot_redirect_new_outputs(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'real').mkdir()
            (root / 'alias').symlink_to(root / 'real', target_is_directory=True)
            self.reject_before_load(m, 'DEMO_OUTPUT_LOCATION', 'sign-cycle', root / 'alias/out')
            self.assertEqual(list((root / 'real').iterdir()), [])

    def test_bad_output_path_types_and_encodings_are_fixed_errors(self):
        m = self.module()
        for value in (None, 'text-not-Path', Path('/tmp/bad\0name'), Path('/tmp/bad\udcffname')):
            self.reject_before_load(m, 'DEMO_OUTPUT_PATH', 'sign-cycle', value)

    def test_loader_failure_does_not_publish_or_claim_zero_work_success(self):
        m = self.module()
        from integration_tools.scenario_input import ScenarioError

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            with patch.object(m, 'load_model', side_effect=ScenarioError('SCENARIO_RUNTIME')):
                with self.assertRaisesRegex(m.DemoError, '^DEMO_SOURCE:SCENARIO_RUNTIME$'):
                    m.run_sequence_case('sign-cycle', output)
            self.assertFalse(output.exists())

    def test_source_change_after_calculation_prevents_any_publication(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            with patch.object(m, 'source_identity', return_value={'changed': True}):
                with self.assertRaisesRegex(m.DemoError, '^DEMO_SOURCE_CHANGED$'):
                    m.run_sequence_case('sign-cycle', output)
            self.assertFalse(output.exists())

    def test_nonpreflight_checker_error_never_publishes_rejected_zero_step_result(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / 'warm'
            m.run_sequence_case('sign-cycle', first)
            checker = importlib.import_module('integration_tools.synthetic_sequence_check')
            output = Path(tmp) / 'error'
            with patch.object(checker, 'check_synthetic_sequence', side_effect=checker.SequenceCheckError(
                'SEQUENCE_TRANSITION:2:TRANSITION_MODEL_FAILURE')):
                with self.assertRaisesRegex(m.DemoError, '^DEMO_CHECK_FAILED_WORK_MAY_BE_NONZERO$'):
                    m.run_sequence_case('sign-cycle', output)
            self.assertFalse(output.exists())

    def test_unexpected_calculation_exception_propagates_without_artifact(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            m.run_sequence_case('sign-cycle', Path(tmp) / 'warm')
            checker = importlib.import_module('integration_tools.synthetic_sequence_check')
            output = Path(tmp) / 'error'
            with patch.object(checker, 'check_synthetic_sequence', side_effect=RuntimeError('unexpected')):
                with self.assertRaisesRegex(RuntimeError, '^unexpected$'):
                    m.run_sequence_case('sign-cycle', output)
            self.assertFalse(output.exists())

    def test_partial_publication_is_retained_and_not_retried_or_reused(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'partial'
            original = m._write_exclusive

            def fail_result(path, raw):
                if path.name == 'RESULTS.json':
                    raise OSError('injected IO error')
                original(path, raw)

            with patch.object(m, '_write_exclusive', side_effect=fail_result):
                with self.assertRaisesRegex(m.DemoError, '^DEMO_PUBLICATION_FAILED_WORK_MAY_BE_NONZERO$'):
                    m.run_sequence_case('sign-cycle', output)
            self.assertEqual({p.name for p in output.iterdir()}, {'INPUT.json'})
            before = (output / 'INPUT.json').read_bytes()
            self.reject_before_load(m, 'DEMO_OUTPUT_EXISTS', 'sign-cycle', output)
            self.assertEqual((output / 'INPUT.json').read_bytes(), before)

    def test_cli_actual_case_exit_codes_and_packages_from_arbitrary_cwd(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for case, status, code, steps in [('sign-cycle', 'MATCH', 0, 3), ('declared-difference', 'DIFFERENT', 1, 3),
                                              ('late-invalid', 'REJECTED', 2, 0)]:
                output = root / case
                result = self.command(case, output, cwd=root)
                self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout)['status'], status)
                self.assertEqual(self.package(output)['model_steps'], steps)

    def test_cli_unknown_case_missing_arguments_and_unapproved_input_options_write_nothing(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for args in [[], ['--case', 'vehicle', '--output', str(root / 'x')],
                         ['--case', 'sign-cycle', '--output', str(root / 'x'), '--input', '/not/read'],
                         ['--case', 'sign-cycle', '--output', str(root / 'x'), '--rate_budget_per_s', '0']]:
                result = subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence.py', *args],
                                        cwd=root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
            self.assertEqual(list(root.iterdir()), [])

    def test_cli_help_is_available_without_opening_model_or_output(self):
        self.module()
        result = subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence.py', '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('--case', result.stdout)
        self.assertIn('--output', result.stdout)

    def test_cli_repeat_outputs_have_identical_portable_bytes(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            one, two = root / 'one', root / 'two'
            for output in (one, two):
                result = self.command('declared-difference', output, cwd=root)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertEqual({p.name: p.read_bytes() for p in one.iterdir()}, {p.name: p.read_bytes() for p in two.iterdir()})

    def test_lightweight_frontend_and_guards_import_no_model_or_original_runtime(self):
        self.module()
        script = f'''
import json,sys
from pathlib import Path
sys.path.insert(0, {str(ROOT)!r})
from integration_tools.core_sequence_run import run_sequence_case,DemoError
try:
    run_sequence_case('not-approved', Path('/not/created/core8'))
except DemoError as error:
    assert error.code == 'DEMO_CASE'
bad = [n for n in sys.modules if n == 'cyberlateral_dev' or n == 'numpy' or n.startswith(('openpilot','selfdrive','opendbc','synthetic_rate_constraint_feasibility'))]
assert bad == [], bad
print(json.dumps({{'forbidden_modules':bad}}))
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout), {'forbidden_modules': []})

    def test_fresh_cli_main_restores_cache_and_does_not_load_original_modules(self):
        self.module()
        script = f'''
import importlib.util,json,sys,tempfile
from pathlib import Path
tool = {str(ROOT / 'tools/core_sequence.py')!r}
spec=importlib.util.spec_from_file_location('core8_cli',tool)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
before=sys.pycache_prefix
with tempfile.TemporaryDirectory() as tmp:
    code=m.main(['--case','sign-cycle','--output',str(Path(tmp)/'out')])
assert code == 0 and sys.pycache_prefix == before
bad=[n for n in sys.modules if n == 'numpy' or n.startswith(('openpilot','selfdrive','opendbc','synthetic_rate_constraint_feasibility'))]
assert bad == [],bad
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
