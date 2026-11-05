"""Bounded all-case preflight, truthful work totals and fail-safe suite receipts."""

import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT

CASES = ('sign-cycle', 'declared-difference', 'late-invalid')


class CoreSequenceSuiteTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/core_sequence_suite.py').is_file(), 'Missing CORE12 closed suite')
        self.assertTrue((ROOT / 'tools/core_sequence_suite.py').is_file(), 'Missing CORE12 suite CLI')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.core_sequence_suite')

    def fixture(self, root, name='suite'):
        producer = importlib.import_module('integration_tools.core_sequence_run')
        folder = root / name
        folder.mkdir()
        for case in CASES:
            producer.run_sequence_case(case, folder / case)
        return folder

    def observe(self, action):
        calls = []
        previous = sys.getprofile()

        def profile(frame, event, arg):
            if event == 'call' and frame.f_code.co_name == 'step' and frame.f_code.co_filename.endswith('/src/cyberlateral_dev/api.py'):
                calls.append(1)

        sys.setprofile(profile)
        try:
            value = action()
        finally:
            sys.setprofile(previous)
        return value, len(calls)

    def command(self, *args):
        return subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence_suite.py', *args], capture_output=True)

    def snapshot(self, folder):
        return {p.relative_to(folder).as_posix(): (p.read_bytes(), p.stat().st_mode) for p in folder.rglob('*') if p.is_file()}

    def edit(self, folder, change):
        target = folder / 'RESULTS.json'
        data = json.loads(target.read_bytes())
        change(data)
        target.write_bytes((json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode())
        (folder / 'SHA256SUMS.txt').write_bytes(''.join(hashlib.sha256((folder / name).read_bytes()).hexdigest() + '  ' + name + '\n'
            for name in ('INPUT.json', 'RESULTS.json')).encode())

    def test_check_aggregates_actual_saved_outcomes_in_fixed_order_with_zero_work(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            r, calls = self.observe(lambda: m.check_closed_suite(folder))
            self.assertEqual((r['mode'], r['case_count'], r['case_ids']), ('CHECK_SAVED_SUITE', 3, list(CASES)))
            self.assertEqual(r['saved_status_counts'], {'MATCH': 1, 'DIFFERENT': 1, 'REJECTED': 1})
            self.assertEqual([r['saved_status'] for r in r['reports']], ['MATCH', 'DIFFERENT', 'REJECTED'])
            self.assertEqual((r['recorded_model_steps'], r['new_synthetic_model_steps'], calls), (6, 0, 0))
            self.assertTrue(r['all_cases_processed'])
            self.assertFalse(r['execution_requested'])
            self.assertEqual(m.exit_code(r), 0)

    def test_no_baseline_has_null_differences_not_silent_identical(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            r = m.check_closed_suite(self.fixture(Path(tmp)))
            self.assertEqual(r['suite_status'], 'SAVED_SUITE_INSPECTED')
            self.assertEqual(r['comparison_counts'], {'NOT_REQUESTED': 3, 'IDENTICAL': 0, 'DIFFERENT': 0})
            self.assertIsNone(r['difference_count'])
            self.assertIsNone(r['difference_counts'])
            self.assertFalse(r['baseline_comparison_requested'])
            self.assertTrue(all(report['comparison'] is None for report in r['reports']))

    def test_same_suite_baseline_has_three_identical_comparisons(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            r = m.check_closed_suite(folder, folder)
            self.assertEqual((r['suite_status'], m.exit_code(r)), ('SAVED_SUITE_IDENTICAL', 0))
            self.assertEqual(r['comparison_counts'], {'NOT_REQUESTED': 0, 'IDENTICAL': 3, 'DIFFERENT': 0})
            self.assertEqual(r['difference_count'], 0)
            self.assertEqual(r['difference_counts'], {'INPUT': 0, 'RESULT': 0, 'IDENTITY': 0})

    def test_one_identity_difference_sets_suite_exit_one_without_status_promotion(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = self.fixture(root)
            current = root / 'current'; shutil.copytree(baseline, current)
            self.edit(current / 'late-invalid', lambda r: r['identity'].update(marker=None))
            r = m.check_closed_suite(current, baseline)
            self.assertEqual((r['suite_status'], m.exit_code(r), r['difference_count']), ('SAVED_SUITE_DIFFERENT', 1, 1))
            self.assertEqual(r['comparison_counts'], {'NOT_REQUESTED': 0, 'IDENTICAL': 2, 'DIFFERENT': 1})
            self.assertEqual(r['difference_counts'], {'INPUT': 0, 'RESULT': 0, 'IDENTITY': 1})
            self.assertEqual(r['saved_status_counts'], {'MATCH': 1, 'DIFFERENT': 1, 'REJECTED': 1})
            self.assertEqual(r['new_synthetic_model_steps'], 0)

    def test_check_missing_extra_case_and_extra_root_file_are_not_partial_success(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for kind in ('missing', 'extra-case', 'extra-file'):
                folder = self.fixture(root, kind)
                if kind == 'missing': (folder / 'late-invalid').rename(root / 'removed-case')
                elif kind == 'extra-case': (folder / 'fourth-case').mkdir()
                else: (folder / 'summary.json').write_bytes(b'{}')
                with self.assertRaisesRegex(m.SuiteError, '^SUITE_INPUT_LAYOUT$'):
                    m.check_closed_suite(folder)

    def test_wrong_stored_case_id_cannot_hide_behind_directory_label(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = self.fixture(root)
            (folder / 'sign-cycle').rename(root / 'original')
            shutil.copytree(folder / 'declared-difference', folder / 'sign-cycle')
            with self.assertRaisesRegex(m.SuiteError, '^SUITE_INPUT_CASE_ID:sign-cycle$'):
                m.check_closed_suite(folder)

    def test_root_symlink_child_symlink_and_fifo_are_rejected_without_following(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = self.fixture(root)
            link = root / 'link'; link.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(m.SuiteError, '^SUITE_INPUT_ROOT$'):
                m.check_closed_suite(link)
            for kind in ('symlink', 'fifo'):
                folder = self.fixture(root, kind)
                child = folder / 'late-invalid'
                outside = root / (kind + '-outside'); child.rename(outside)
                if kind == 'symlink': child.symlink_to(outside, target_is_directory=True)
                else: os.mkfifo(child)
                with self.assertRaisesRegex(m.SuiteError, '^SUITE_INPUT_LAYOUT$'):
                    m.check_closed_suite(folder)

    def test_bad_root_types_missing_and_nul_have_fixed_errors(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            for value in (None, 'not-Path', Path(tmp) / 'missing', Path(tmp) / 'bad\0path'):
                with self.assertRaisesRegex(m.SuiteError, '^SUITE_INPUT_ROOT$'):
                    m.check_closed_suite(value)

    def test_corrupt_last_input_case_aborts_without_summary(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            (folder / 'late-invalid/INPUT.json').write_bytes(b'corrupt')
            with self.assertRaisesRegex(m.SuiteError, '^SUITE_INPUT:late-invalid:INSPECT_CHECKSUM$'):
                m.check_closed_suite(folder)
            cli = self.command('check', '--input-root', folder)
            self.assertEqual((cli.returncode, cli.stdout, cli.stderr),
                (2, b'', b'REJECTED: SUITE_INPUT:late-invalid:INSPECT_CHECKSUM\n'))

    def test_check_two_roles_open_twenty_six_readonly_descriptors_once(self):
        m = self.module()
        original = os.open
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            calls = []

            def observe(path, flags, mode=0o777, *, dir_fd=None):
                calls.append((path, flags))
                return original(path, flags, mode, dir_fd=dir_fd)

            with patch('os.open', observe):
                r = m.check_closed_suite(folder, folder)
            self.assertEqual(r['difference_count'], 0)
            self.assertEqual(len(calls), 26)
            self.assertEqual([str(p) for p, _ in calls].count('INPUT.json'), 6)
            self.assertEqual([str(p) for p, _ in calls].count('RESULTS.json'), 6)
            self.assertTrue(all(flags & os.O_NOFOLLOW and not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
                                for _, flags in calls))

    def test_check_api_cli_preserve_both_root_sets_bytes_and_modes(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = self.fixture(root)
            current = root / 'current'; shutil.copytree(baseline, current)
            before = {str(p): self.snapshot(p) for p in (baseline, current)}
            m.check_closed_suite(current, baseline)
            self.assertEqual(self.command('check', '--input-root', current, '--baseline-root', baseline).returncode, 0)
            self.assertEqual(before, {str(p): self.snapshot(p) for p in (baseline, current)})

    def test_explicit_run_processes_all_cases_with_six_actual_new_steps(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'output'
            r, calls = self.observe(lambda: m.run_closed_suite(output))
            self.assertEqual((r['mode'], r['execution_requested']), ('RUN_CLOSED_SYNTHETIC_SUITE', True))
            self.assertEqual((r['new_synthetic_model_steps'], r['recorded_model_steps'], calls), (6, 6, 6))
            self.assertEqual([r['new_synthetic_model_steps'] for r in r['reports']], [3, 3, 0])
            self.assertEqual(r['saved_status_counts'], {'MATCH': 1, 'DIFFERENT': 1, 'REJECTED': 1})
            self.assertEqual(m.exit_code(r), 0)
            self.assertEqual({p.name for p in output.iterdir()}, set(CASES))
            for case in CASES:
                self.assertEqual({p.name for p in (output / case).iterdir()}, {'INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt'})

    def test_run_with_current_source_baseline_compares_all_without_double_execution(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = self.fixture(root)
            before = self.snapshot(baseline)
            r, calls = self.observe(lambda: m.run_closed_suite(root / 'output', baseline))
            self.assertEqual((calls, r['new_synthetic_model_steps'], r['difference_count'], m.exit_code(r)), (6, 6, 0, 0))
            self.assertEqual(r['comparison_counts']['IDENTICAL'], 3)
            self.assertEqual(before, self.snapshot(baseline))

    def test_bad_last_baseline_prevents_all_output_creation_and_new_steps(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = self.fixture(root)
            (baseline / 'late-invalid/RESULTS.json').write_bytes(b'bad')
            output = root / 'output'

            def reject():
                with self.assertRaisesRegex(m.SuiteError, '^SUITE_BASELINE:late-invalid:INSPECT_CHECKSUM$'):
                    m.run_closed_suite(output, baseline)

            _, calls = self.observe(reject)
            self.assertEqual(calls, 0)
            self.assertFalse(output.exists())

    def test_wrong_last_baseline_case_prevents_all_new_work(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = self.fixture(root)
            (baseline / 'late-invalid').rename(root / 'removed')
            shutil.copytree(baseline / 'sign-cycle', baseline / 'late-invalid')

            def reject():
                with self.assertRaisesRegex(m.SuiteError, '^SUITE_BASELINE_CASE_ID:late-invalid$'):
                    m.run_closed_suite(root / 'output', baseline)

            _, calls = self.observe(reject)
            self.assertEqual(calls, 0)
            self.assertFalse((root / 'output').exists())

    def test_output_guards_reject_existing_link_missing_parent_checkout_and_bad_type(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = self.fixture(root)
            before = self.snapshot(existing)
            link = root / 'link'; link.symlink_to(existing, target_is_directory=True)
            for output in (existing, link, root / 'missing/output', ROOT / 'must-not-create-core12', None, 'bad', root / 'bad\0path'):
                with self.assertRaises(m.SuiteError):
                    m.run_closed_suite(output)
            self.assertEqual(before, self.snapshot(existing))
            self.assertFalse((ROOT / 'must-not-create-core12').exists())

    def test_output_nested_in_baseline_rejects_before_model_and_preserves_input(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            baseline = self.fixture(Path(tmp))
            before = self.snapshot(baseline)

            def reject():
                with self.assertRaisesRegex(m.SuiteError, '^SUITE_OUTPUT_BASELINE_OVERLAP_NO_MODEL_EXECUTION$'):
                    m.run_closed_suite(baseline / 'nested', baseline)

            _, calls = self.observe(reject)
            self.assertEqual(calls, 0)
            self.assertEqual(before, self.snapshot(baseline))
            self.assertFalse((baseline / 'nested').exists())

    def test_all_baseline_cases_are_owned_before_first_execution(self):
        m = self.module()
        original = m._run_captured
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = self.fixture(root)

            def external_actor(case, output, captured):
                if case == 'sign-cycle':
                    (baseline / 'late-invalid/INPUT.json').write_bytes(b'external-test-actor-change')
                return original(case, output, captured)

            with patch.object(m, '_run_captured', external_actor):
                r = m.run_closed_suite(root / 'output', baseline)
            self.assertEqual((r['difference_count'], r['comparison_counts']['IDENTICAL']), (0, 3))
            self.assertEqual(r['reports'][2]['baseline_inspection']['saved_status'], 'REJECTED')

    def test_second_case_failure_retains_first_and_never_starts_later_case(self):
        m = self.module()
        workflow = importlib.import_module('integration_tools.core_sequence_workflow')
        original = m._run_captured
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'output'

            def fail(case, path, baseline):
                if case == 'declared-difference': raise workflow.WorkflowError('INJECTED')
                return original(case, path, baseline)

            def reject():
                with self.assertRaisesRegex(m.SuiteError, '^SUITE_RUN:declared-difference:INJECTED:WORK_MAY_BE_NONZERO$'):
                    m.run_closed_suite(output)

            with patch.object(m, '_run_captured', fail):
                _, calls = self.observe(reject)
            self.assertEqual(calls, 3)
            self.assertEqual({p.name for p in output.iterdir()}, {'sign-cycle'})
            with self.assertRaises(m.SuiteError): m.run_closed_suite(output)

    def test_zero_step_last_case_failure_cannot_hide_six_prefix_steps(self):
        m = self.module()
        workflow = importlib.import_module('integration_tools.core_sequence_workflow')
        original = m._run_captured
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'output'

            def fail(case, path, baseline):
                if case == 'late-invalid': raise workflow.WorkflowError('INJECTED_ZERO_CASE')
                return original(case, path, baseline)

            def reject():
                with self.assertRaisesRegex(m.SuiteError, '^SUITE_RUN:late-invalid:INJECTED_ZERO_CASE:WORK_MAY_BE_NONZERO$'):
                    m.run_closed_suite(output)

            with patch.object(m, '_run_captured', fail): _, calls = self.observe(reject)
            self.assertEqual(calls, 6)
            self.assertEqual({p.name for p in output.iterdir()}, {'sign-cycle', 'declared-difference'})

    def test_postrun_root_layout_error_preserves_all_outputs_and_reports_possible_work(self):
        m = self.module()
        original = m._run_captured
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'output'

            def extra(case, path, baseline):
                report = original(case, path, baseline)
                if case == 'late-invalid': (output / 'unexpected').write_bytes(b'external-test-actor')
                return report

            with patch.object(m, '_run_captured', extra):
                with self.assertRaisesRegex(m.SuiteError, '^SUITE_GENERATED_LAYOUT_WORK_MAY_BE_NONZERO$'):
                    m.run_closed_suite(output)
            self.assertEqual({p.name for p in output.iterdir()}, {*CASES, 'unexpected'})

    def test_fresh_invalid_baseline_run_cannot_import_producer(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = self.fixture(root)
            (baseline / 'late-invalid/INPUT.json').write_bytes(b'corrupt')
            output = root / 'output'
            script = f'''
import importlib.abc,sys
sys.path.insert(0,{str(ROOT)!r})
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.startswith(('cyberlateral_dev','integration_tools.core_sequence_run','integration_tools.synthetic_model_input')):
   raise AssertionError('PRODUCER_IMPORTED')
sys.meta_path.insert(0,Block())
from pathlib import Path
from integration_tools.core_sequence_suite import run_closed_suite,SuiteError
try: run_closed_suite(Path({str(output)!r}),Path({str(baseline)!r}))
except SuiteError as e: assert e.code=='SUITE_BASELINE:late-invalid:INSPECT_CHECKSUM'
else: raise AssertionError('ACCEPTED')
assert not Path({str(output)!r}).exists()
'''
            result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b'', b''))

    def test_fresh_check_api_cli_imports_no_model_or_execution_path(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            script = f'''
import importlib.abc,runpy,sys
sys.path.insert(0,{str(ROOT)!r})
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.startswith(('cyberlateral_dev','numpy','selfdrive','openpilot','opendbc','synthetic_rate_constraint_feasibility',
   'integration_tools.core_sequence_run','integration_tools.synthetic_model_input','integration_tools.synthetic_transition_check',
   'integration_tools.synthetic_sequence_check')): raise AssertionError('FORBIDDEN_IMPORT:'+fullname)
sys.meta_path.insert(0,Block())
from pathlib import Path
from integration_tools.core_sequence_suite import check_closed_suite
r=check_closed_suite(Path({str(folder)!r}),Path({str(folder)!r}))
assert r['new_synthetic_model_steps']==0 and r['comparison_counts']['IDENTICAL']==3
sys.argv=['suite','check','--input-root',{str(folder)!r}]
runpy.run_path({str(ROOT / 'tools/core_sequence_suite.py')!r},run_name='__main__')
'''
            result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True)
            self.assertEqual((result.returncode, result.stderr), (0, b''))
            self.assertEqual(json.loads(result.stdout)['new_synthetic_model_steps'], 0)

    def test_cli_run_check_comparison_exit_codes_are_not_saved_case_codes(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = self.fixture(root)
            output = root / 'output'
            run = self.command('run', '--output-root', output, '--baseline-root', baseline)
            self.assertEqual((run.returncode, run.stderr), (0, b''))
            self.assertEqual(json.loads(run.stdout)['new_synthetic_model_steps'], 6)
            self.assertEqual(self.command('check', '--input-root', output, '--baseline-root', baseline).returncode, 0)
            self.edit(output / 'sign-cycle', lambda r: r['identity'].update(marker=0))
            changed = self.command('check', '--input-root', output, '--baseline-root', baseline)
            self.assertEqual(changed.returncode, 1)
            self.assertEqual(json.loads(changed.stdout)['difference_count'], 1)

    def test_cli_requires_explicit_mode_and_rejects_subset_or_vehicle_options(self):
        self.module()
        for args, code in [(['--help'], 0), (['check', '--help'], 0), (['run', '--help'], 0), ([], 2), (['run'], 2),
            (['check'], 2), (['check', '--in', 'x'], 2), (['run', '--output-root', 'x', '--case', 'sign-cycle'], 2),
            (['run', '--output-root', 'x', '--rate', '0'], 2), (['check', '--input-root', 'x', '--output-root', 'y'], 2)]:
            self.assertEqual(self.command(*args).returncode, code)

    def test_stdout_device_failure_is_fixed_and_retains_explicit_run_output(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            saved = self.fixture(root)
            for mode in ('check', 'run'):
                for unbuffered in (False, True):
                    output = root / f'{mode}-{unbuffered}'
                    args = ['check', '--input-root', str(saved)] if mode == 'check' else ['run', '--output-root', str(output)]
                    with open('/dev/full', 'wb') as full:
                        result = subprocess.run([sys.executable, '-I', '-B', *(['-u'] if unbuffered else []),
                            ROOT / 'tools/core_sequence_suite.py', *args], stdout=full, stderr=subprocess.PIPE)
                    code = 'SUITE_CHECK_FAILED_NO_MODEL_EXECUTION' if mode == 'check' else 'SUITE_RUN_FAILED_WORK_MAY_BE_NONZERO'
                    self.assertEqual((result.returncode, result.stderr), (2, ('REJECTED: ' + code + '\n').encode()))
                    self.assertEqual(output.exists(), mode == 'run')

    def test_cache_cleanup_failure_is_handled_before_success_receipt_in_both_modes(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            saved = self.fixture(root)
            for mode in ('check', 'run'):
                output = root / mode
                args = ['check', '--input-root', str(saved)] if mode == 'check' else ['run', '--output-root', str(output)]
                script = f'''
import runpy,sys,tempfile
original=tempfile.TemporaryDirectory.cleanup
def fail(self):
 original(self)
 raise OSError('PRIVATE_CLEANUP')
tempfile.TemporaryDirectory.cleanup=fail
sys.argv=['suite',*{args!r}]
runpy.run_path({str(ROOT / 'tools/core_sequence_suite.py')!r},run_name='__main__')
'''
                result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True)
                code = 'SUITE_CHECK_FAILED_NO_MODEL_EXECUTION' if mode == 'check' else 'SUITE_RUN_FAILED_WORK_MAY_BE_NONZERO'
                self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', ('REJECTED: ' + code + '\n').encode()))
                self.assertEqual(output.exists(), mode == 'run')

    def test_canonical_summary_repeats_without_caller_paths(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            one = m.check_closed_suite(folder, folder)
            expected = (json.dumps(one, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
            self.assertEqual(self.command('check', '--input-root', folder, '--baseline-root', folder).stdout, expected)
            self.assertEqual(m.check_closed_suite(folder, folder), one)
            self.assertNotIn(tmp.encode(), expected)

    def test_per_case_reports_preserve_core11_public_check_contract(self):
        m = self.module()
        workflow = importlib.import_module('integration_tools.core_sequence_workflow')
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp))
            r = m.check_closed_suite(folder, folder)
            for case, report in zip(CASES, r['reports'], strict=True):
                self.assertEqual(report, workflow.check_saved_sequence(folder / case, folder / case))
            self.assertEqual(r['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
            self.assertFalse(r['source_identity_reauthenticated'])
            self.assertIsNone(r['gates']['actual_r'])

    def test_cache_creation_failure_before_dispatch_reports_no_model_execution(self):
        self.module()
        script = f'''
import runpy,sys,tempfile
def fail(*args,**kwargs): raise OSError('PRIVATE_VALUE')
tempfile.TemporaryDirectory=fail
sys.argv=['suite','run','--output-root','not-created']
runpy.run_path({str(ROOT / 'tools/core_sequence_suite.py')!r},run_name='__main__')
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', b'REJECTED: SUITE_CACHE_IO_NO_MODEL_EXECUTION\n'))

    def test_unexpected_error_after_operation_has_mode_specific_code_and_no_receipt(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            saved = self.fixture(root)
            for mode in ('check', 'run'):
                output = root / mode
                args = ['check', '--input-root', str(saved)] if mode == 'check' else ['run', '--output-root', str(output)]
                function = 'check_closed_suite' if mode == 'check' else 'run_closed_suite'
                script = f'''
import runpy,sys
sys.path.insert(0,{str(ROOT)!r})
import integration_tools.core_sequence_suite as s
original=getattr(s,{function!r})
def fail(*args):
 original(*args)
 raise TypeError('PRIVATE_VALUE')
setattr(s,{function!r},fail)
sys.argv=['suite',*{args!r}]
runpy.run_path({str(ROOT / 'tools/core_sequence_suite.py')!r},run_name='__main__')
'''
                result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True)
                code = 'SUITE_CHECK_FAILED_NO_MODEL_EXECUTION' if mode == 'check' else 'SUITE_RUN_FAILED_WORK_MAY_BE_NONZERO'
                self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', ('REJECTED: ' + code + '\n').encode()))
                self.assertEqual(output.exists(), mode == 'run')

    def test_output_root_creation_failure_precedes_any_model_steps(self):
        m = self.module()
        original = Path.mkdir
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'output'

            def fail(path, *args, **kwargs):
                if path == output: raise OSError('PRIVATE_VALUE')
                return original(path, *args, **kwargs)

            def reject():
                with self.assertRaisesRegex(m.SuiteError, '^SUITE_OUTPUT_CREATE_NO_MODEL_EXECUTION$'):
                    m.run_closed_suite(output)

            with patch.object(Path, 'mkdir', fail): _, calls = self.observe(reject)
            self.assertEqual(calls, 0)
            self.assertFalse(output.exists())
