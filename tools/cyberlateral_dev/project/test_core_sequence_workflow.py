"""Explicit run versus check, captured baselines and honest work/error reports."""

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


class CoreSequenceWorkflowTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/core_sequence_workflow.py').is_file(), 'Missing CORE11 closed workflow')
        self.assertTrue((ROOT / 'tools/core_sequence_workflow.py').is_file(), 'Missing CORE11 workflow CLI')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.core_sequence_workflow')

    def fixture(self, root, name, case='sign-cycle'):
        producer = importlib.import_module('integration_tools.core_sequence_run')
        path = root / name
        producer.run_sequence_case(case, path)
        return path

    def observe(self, action):
        calls = []
        previous = sys.getprofile()

        def profile(frame, event, arg):
            if event == 'call' and frame.f_code.co_name == 'step' and frame.f_code.co_filename.endswith('/src/cyberlateral_dev/api.py'):
                calls.append(frame.f_code.co_name)

        sys.setprofile(profile)
        try:
            result = action()
        finally:
            sys.setprofile(previous)
        return result, len(calls)

    def command(self, *args):
        return subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence_workflow.py', *args], capture_output=True)

    def snapshot(self, folder):
        return {p.name: (p.read_bytes(), p.stat().st_mode) for p in folder.iterdir()}

    def test_check_saved_outcomes_preserve_historical_steps_but_run_none(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            for case, status, steps in [('sign-cycle', 'MATCH', 3), ('declared-difference', 'DIFFERENT', 3), ('late-invalid', 'REJECTED', 0)]:
                folder = self.fixture(Path(tmp), case, case)
                r, calls = self.observe(lambda folder=folder: m.check_saved_sequence(folder))
                self.assertEqual((r['mode'], r['saved_status'], r['recorded_model_steps']), ('CHECK_SAVED_ONLY', status, steps))
                self.assertEqual((r['new_synthetic_model_steps'], r['reader_model_executions'], r['reader_reference_executions'], calls), (0, 0, 0, 0))
                self.assertFalse(r['execution_requested'])
                self.assertEqual(m.exit_code(r), 0)

    def test_no_baseline_means_no_regression_comparison_or_default(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            r = m.check_saved_sequence(self.fixture(Path(tmp), 'packet'))
            self.assertIsNone(r['comparison'])
            self.assertIsNone(r['baseline_inspection'])
            self.assertEqual(r['workflow_status'], 'SAVED_RECORDS_INSPECTED')
            self.assertFalse(r['source_identity_reauthenticated'])
            self.assertEqual(r['gates']['R_BUDGET'], 'UNRESOLVED')
            self.assertIsNone(r['gates']['actual_r'])

    def test_check_mirrored_baseline_is_identical_and_keeps_both_inspections(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = self.fixture(root, 'baseline')
            current = root / 'current'
            shutil.copytree(baseline, current)
            r = m.check_saved_sequence(current, baseline)
            self.assertEqual((r['workflow_status'], m.exit_code(r)), ('SAVED_PACKAGES_IDENTICAL', 0))
            self.assertEqual(r['inspection']['saved_status'], 'MATCH')
            self.assertEqual(r['baseline_inspection']['saved_status'], 'MATCH')
            self.assertEqual(r['comparison']['difference_count'], 0)

    def test_check_different_baseline_preserves_role_order_and_literal_counts(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = self.fixture(root, 'baseline')
            current = self.fixture(root, 'current', 'declared-difference')
            r = m.check_saved_sequence(current, baseline)
            self.assertEqual((r['workflow_status'], m.exit_code(r)), ('SAVED_PACKAGES_DIFFERENT', 1))
            self.assertEqual(r['comparison']['difference_counts'], {'INPUT': 6, 'RESULT': 12, 'IDENTITY': 0})
            self.assertEqual((r['comparison']['left']['case_id'], r['comparison']['right']['case_id']), ('sign-cycle', 'declared-difference'))

    def test_check_input_and_baseline_corruption_have_fixed_role_errors(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = self.fixture(root, 'good')
            bad = root / 'bad'
            shutil.copytree(good, bad)
            (bad / 'INPUT.json').write_bytes(b'corrupt')
            for current, baseline, role in [(bad, good, 'INPUT'), (good, bad, 'BASELINE')]:
                with self.assertRaisesRegex(m.WorkflowError, '^WORKFLOW_' + role + ':INSPECT_CHECKSUM$'):
                    m.check_saved_sequence(current, baseline)

    def test_check_captures_each_role_once_with_eight_readonly_opens(self):
        m = self.module()
        original = os.open
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp), 'packet')
            calls = []

            def trace(path, flags, mode=0o777, *, dir_fd=None):
                calls.append((path, flags))
                return original(path, flags, mode, dir_fd=dir_fd)

            with patch('os.open', trace):
                r = m.check_saved_sequence(folder, folder)
            self.assertEqual(r['comparison']['difference_count'], 0)
            self.assertEqual(len(calls), 8)
            self.assertEqual([str(p) for p, _ in calls if str(p) in ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt')],
                             ['INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt'] * 2)
            self.assertTrue(all(flags & os.O_NOFOLLOW and not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
                                for _, flags in calls))

    def test_check_api_cli_preserve_file_sets_bytes_modes(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp), 'packet')
            before = self.snapshot(folder)
            m.check_saved_sequence(folder, folder)
            self.assertEqual(self.command('check', '--input', folder, '--baseline', folder).returncode, 0)
            self.assertEqual(self.snapshot(folder), before)

    def test_explicit_run_reports_actual_three_three_zero_public_model_steps(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            for case, status, steps in [('sign-cycle', 'MATCH', 3), ('declared-difference', 'DIFFERENT', 3), ('late-invalid', 'REJECTED', 0)]:
                folder = Path(tmp) / case
                r, calls = self.observe(lambda case=case, folder=folder: m.run_closed_sequence(case, folder))
                self.assertEqual((r['mode'], r['execution_requested']), ('RUN_CLOSED_SYNTHETIC', True))
                self.assertEqual((r['saved_status'], r['new_synthetic_model_steps'], calls), (status, steps, steps))
                self.assertEqual(r['recorded_model_steps'], steps)
                self.assertEqual(m.exit_code(r), 0)

    def test_run_persists_only_core8_three_files_with_valid_saved_records(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'output'
            r = m.run_closed_sequence('sign-cycle', folder)
            self.assertEqual(set(self.snapshot(folder)), {'INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt'})
            self.assertEqual([row['computed_limited_state'] for row in r['inspection']['rows']], [2, -2, 2])
            self.assertEqual(r['inspection']['captured_sha256'], importlib.import_module('integration_tools.core_sequence_saved').inspect_saved_sequence(folder)['captured_sha256'])

    def test_run_matching_current_source_baseline_does_not_double_run(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = self.fixture(root, 'baseline')
            r, calls = self.observe(lambda: m.run_closed_sequence('sign-cycle', root / 'output', baseline))
            self.assertEqual((m.exit_code(r), r['comparison']['difference_count'], calls, r['new_synthetic_model_steps']), (0, 0, 3, 3))

    def test_run_cross_case_baseline_differs_without_reinterpreting_saved_status(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = self.fixture(root, 'baseline', 'declared-difference')
            r = m.run_closed_sequence('sign-cycle', root / 'output', baseline)
            self.assertEqual((r['saved_status'], r['workflow_status'], m.exit_code(r)), ('MATCH', 'SAVED_PACKAGES_DIFFERENT', 1))
            self.assertEqual(r['comparison']['difference_count'], 18)

    def test_run_reuses_preexecution_baseline_capture_not_changed_disk(self):
        m = self.module()
        producer = importlib.import_module('integration_tools.core_sequence_run')
        original = producer.run_sequence_case
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = self.fixture(root, 'baseline')
            before = json.loads((baseline / 'INPUT.json').read_bytes())

            def external_change(case, output):
                (baseline / 'INPUT.json').write_bytes(b'external-test-actor-changed-disk')
                return original(case, output)

            with patch.object(producer, 'run_sequence_case', external_change):
                r = m.run_closed_sequence('sign-cycle', root / 'output', baseline)
            self.assertEqual(r['baseline_inspection']['case_id'], before['case_id'])
            self.assertEqual((r['comparison']['difference_count'], m.exit_code(r)), (0, 0))

    def test_run_captures_baseline_and_generated_package_once(self):
        m = self.module()
        original = os.open
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = self.fixture(root, 'baseline')
            with patch('os.open', wraps=original) as observed:
                r = m.run_closed_sequence('sign-cycle', root / 'output', baseline)
            self.assertEqual(r['comparison']['difference_count'], 0)
            self.assertEqual(observed.call_count, 8)

    def test_returned_record_mismatch_after_work_is_not_zero_work_success(self):
        m = self.module()
        producer = importlib.import_module('integration_tools.core_sequence_run')
        original = producer.run_sequence_case
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'output'

            def wrong_return(case, path):
                record = original(case, path)
                return {**record, 'model_steps': 2}

            with patch.object(producer, 'run_sequence_case', wrong_return):
                with self.assertRaisesRegex(m.WorkflowError, '^WORKFLOW_GENERATED_RECORD_MISMATCH_WORK_MAY_BE_NONZERO$'):
                    m.run_closed_sequence('sign-cycle', output)
            self.assertEqual(set(self.snapshot(output)), {'INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt'})

    def test_generated_corruption_after_work_is_labeled_and_preserved(self):
        m = self.module()
        producer = importlib.import_module('integration_tools.core_sequence_run')
        original = producer.run_sequence_case
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'output'

            def corrupt(case, path):
                record = original(case, path)
                (path / 'INPUT.json').write_bytes(b'corrupted-after-publication')
                return record

            with patch.object(producer, 'run_sequence_case', corrupt):
                with self.assertRaisesRegex(m.WorkflowError, '^WORKFLOW_GENERATED:INSPECT_CHECKSUM:WORK_MAY_BE_NONZERO$'):
                    m.run_closed_sequence('sign-cycle', output)
            self.assertEqual((output / 'INPUT.json').read_bytes(), b'corrupted-after-publication')

    def test_partial_publication_failure_is_not_deleted_or_retried(self):
        m = self.module()
        producer = importlib.import_module('integration_tools.core_sequence_run')
        original = producer._write_exclusive
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'output'

            def fail_second(path, raw):
                if path.name == 'RESULTS.json':
                    raise OSError('PRIVATE_VALUE')
                original(path, raw)

            with patch.object(producer, '_write_exclusive', fail_second):
                with self.assertRaisesRegex(m.WorkflowError, '^WORKFLOW_RUN:DEMO_PUBLICATION_FAILED_WORK_MAY_BE_NONZERO:WORK_MAY_BE_NONZERO$'):
                    m.run_closed_sequence('sign-cycle', output)
            self.assertEqual(set(self.snapshot(output)), {'INPUT.json'})
            with self.assertRaises(m.WorkflowError):
                m.run_closed_sequence('sign-cycle', output)

    def test_bad_case_rejects_before_baseline_access_or_producer_call(self):
        m = self.module()

        class Foreign:
            def __getattribute__(self, name):
                raise AssertionError('BASELINE_ACCESSED')

        for case in ('vehicle', None, True, 0, Foreign()):
            with self.assertRaisesRegex(m.WorkflowError, '^WORKFLOW_CASE$'):
                m.run_closed_sequence(case, Foreign(), Foreign())

    def test_bad_baseline_is_rejected_in_fresh_process_before_producer_import(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'not-created'
            script = f'''
import importlib.abc,sys
sys.path.insert(0,{str(ROOT)!r})
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.startswith(('cyberlateral_dev','integration_tools.core_sequence_run','integration_tools.synthetic_model_input')):
   raise AssertionError('PRODUCER_IMPORTED')
sys.meta_path.insert(0,Block())
from pathlib import Path
from integration_tools.core_sequence_workflow import run_closed_sequence,WorkflowError
try: run_closed_sequence('sign-cycle',Path({str(output)!r}),Path({str(Path(tmp) / 'missing')!r}))
except WorkflowError as e: assert e.code=='WORKFLOW_BASELINE:INSPECT_INPUT_FILE'
else: raise AssertionError('ACCEPTED')
assert not Path({str(output)!r}).exists()
'''
            result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b'', b''))
            self.assertFalse(output.exists())

    def test_existing_symlink_missing_parent_checkout_and_bad_output_do_zero_steps(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = self.fixture(root, 'existing')
            before = self.snapshot(existing)
            link = root / 'link'; link.symlink_to(existing, target_is_directory=True)
            calls = []

            def profile(frame, event, arg):
                if event == 'call' and frame.f_code.co_name == 'step' and frame.f_code.co_filename.endswith('/src/cyberlateral_dev/api.py'):
                    calls.append(1)

            previous = sys.getprofile(); sys.setprofile(profile)
            try:
                for path in (existing, link, root / 'missing/output', ROOT / 'must-not-create-core11', None, 'bad', root / 'bad\0path'):
                    with self.assertRaises(m.WorkflowError):
                        m.run_closed_sequence('sign-cycle', path)
            finally:
                sys.setprofile(previous)
            self.assertEqual(calls, [])
            self.assertEqual(self.snapshot(existing), before)
            self.assertFalse((ROOT / 'must-not-create-core11').exists())

    def test_cli_check_codes_are_not_saved_numerical_codes(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folders = [self.fixture(Path(tmp), case, case) for case in ('sign-cycle', 'declared-difference', 'late-invalid')]
            for folder in folders:
                result = self.command('check', '--input', folder)
                self.assertEqual((result.returncode, result.stderr), (0, b''))
                self.assertEqual(json.loads(result.stdout)['new_synthetic_model_steps'], 0)
            different = self.command('check', '--input', folders[1], '--baseline', folders[0])
            self.assertEqual(different.returncode, 1)
            self.assertEqual(json.loads(different.stdout)['comparison']['difference_count'], 18)

    def test_cli_run_is_explicit_and_reports_case_specific_new_work(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            for case, steps in [('sign-cycle', 3), ('declared-difference', 3), ('late-invalid', 0)]:
                output = Path(tmp) / case
                result = self.command('run', '--case', case, '--output', output)
                self.assertEqual((result.returncode, result.stderr), (0, b''))
                r = json.loads(result.stdout)
                self.assertTrue(r['execution_requested'])
                self.assertEqual(r['new_synthetic_model_steps'], steps)
                self.assertEqual(set(self.snapshot(output)), {'INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt'})

    def test_cli_requires_mode_case_output_and_rejects_cross_mode_options(self):
        self.module()
        for args, code in [(['--help'], 0), (['check', '--help'], 0), (['run', '--help'], 0), ([], 2),
            (['run', '--case', 'sign-cycle'], 2), (['run', '--output', '/not-created'], 2),
            (['run', '--case', 'vehicle', '--output', '/not-created'], 2),
            (['check', '--input', '/not-read', '--output', '/not-created'], 2),
            (['check', '--in', '/not-read'], 2), (['run', '--case', 'sign-cycle', '--output', '/not-created', '--rate', '0'], 2)]:
            self.assertEqual(self.command(*args).returncode, code)

    def test_fresh_check_api_cli_never_import_execution_modules(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = self.fixture(root, 'current', 'declared-difference')
            baseline = self.fixture(root, 'baseline')
            script = f'''
import importlib.abc,json,runpy,sys
sys.path.insert(0,{str(ROOT)!r})
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.startswith(('cyberlateral_dev','numpy','openpilot','opendbc','selfdrive','synthetic_rate_constraint_feasibility',
   'integration_tools.core_sequence_run','integration_tools.synthetic_model_input','integration_tools.synthetic_transition_check',
   'integration_tools.synthetic_sequence_check')): raise AssertionError('FORBIDDEN_IMPORT:'+fullname)
sys.meta_path.insert(0,Block())
from pathlib import Path
from integration_tools.core_sequence_workflow import check_saved_sequence
r=check_saved_sequence(Path({str(current)!r}),Path({str(baseline)!r}))
assert r['new_synthetic_model_steps']==0 and r['saved_status']=='DIFFERENT'
sys.argv=['workflow','check','--input',{str(current)!r},'--baseline',{str(baseline)!r}]
runpy.run_path({str(ROOT / 'tools/core_sequence_workflow.py')!r},run_name='__main__')
'''
            result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True)
            self.assertEqual((result.returncode, result.stderr), (1, b''))
            self.assertEqual(json.loads(result.stdout)['new_synthetic_model_steps'], 0)

    def test_stdout_failure_has_mode_specific_honest_work_error(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = self.fixture(root, 'input')
            for mode in ('check', 'run'):
                for unbuffered in (False, True):
                    output = root / f'output-{mode}-{unbuffered}'
                    args = ['check', '--input', folder] if mode == 'check' else ['run', '--case', 'sign-cycle', '--output', output]
                    with open('/dev/full', 'wb') as full:
                        result = subprocess.run([sys.executable, '-I', '-B', *(['-u'] if unbuffered else []),
                            ROOT / 'tools/core_sequence_workflow.py', *args], stdout=full, stderr=subprocess.PIPE)
                    code = 'WORKFLOW_CHECK_FAILED_NO_MODEL_EXECUTION' if mode == 'check' else 'WORKFLOW_RUN_FAILED_WORK_MAY_BE_NONZERO'
                    self.assertEqual((result.returncode, result.stderr), (2, ('REJECTED: ' + code + '\n').encode()))
                    self.assertEqual(output.exists(), mode == 'run')

    def test_unexpected_postwork_exception_preserves_output_and_labels_cli_error(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'output'
            script = f'''
import runpy,sys
sys.path.insert(0,{str(ROOT)!r})
import integration_tools.core_sequence_run as p
original=p.run_sequence_case
def fail(case,output):
 original(case,output)
 raise TypeError('PRIVATE_VALUE')
p.run_sequence_case=fail
sys.argv=['workflow','run','--case','sign-cycle','--output',{str(output)!r}]
runpy.run_path({str(ROOT / 'tools/core_sequence_workflow.py')!r},run_name='__main__')
'''
            result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True)
            self.assertEqual((result.returncode, result.stdout, result.stderr),
                             (2, b'', b'REJECTED: WORKFLOW_RUN_FAILED_WORK_MAY_BE_NONZERO\n'))
            self.assertEqual(set(self.snapshot(output)), {'INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt'})

    def test_check_unexpected_exception_is_fixed_error_without_raw_values(self):
        self.module()
        script = f'''
import runpy,sys
sys.path.insert(0,{str(ROOT)!r})
import integration_tools.core_sequence_workflow as w
def fail(*args): raise TypeError('PRIVATE_VALUE')
w.check_saved_sequence=fail
sys.argv=['workflow','check','--input','unused']
runpy.run_path({str(ROOT / 'tools/core_sequence_workflow.py')!r},run_name='__main__')
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', b'REJECTED: WORKFLOW_CHECK_FAILED_NO_MODEL_EXECUTION\n'))

    def test_canonical_repeatable_receipt_has_no_caller_location(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.fixture(Path(tmp), 'packet')
            one = m.check_saved_sequence(folder, folder)
            two = m.check_saved_sequence(folder, folder)
            self.assertEqual(one, two)
            cli = self.command('check', '--input', folder, '--baseline', folder)
            expected = (json.dumps(one, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
            self.assertEqual(cli.stdout, expected)
            self.assertNotIn(tmp.encode(), expected)

    def test_core10_public_comparison_still_matches_integrated_captured_result(self):
        m = self.module()
        comparison = importlib.import_module('integration_tools.core_sequence_compare')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = self.fixture(root, 'baseline')
            current = self.fixture(root, 'current', 'declared-difference')
            integrated = m.check_saved_sequence(current, baseline)['comparison']
            self.assertEqual(integrated['difference_count'], 18)
            self.assertEqual(comparison.compare_saved_sequences(baseline, current), integrated)

    def test_producer_cannot_substitute_different_case_even_if_saved_record_matches(self):
        m = self.module()
        producer = importlib.import_module('integration_tools.core_sequence_run')
        original = producer.run_sequence_case
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'output'
            with patch.object(producer, 'run_sequence_case', lambda case, path: original('declared-difference', path)):
                with self.assertRaisesRegex(m.WorkflowError, '^WORKFLOW_GENERATED_RECORD_MISMATCH_WORK_MAY_BE_NONZERO$'):
                    m.run_closed_sequence('sign-cycle', output)
            self.assertTrue(output.exists())

    def test_cache_creation_failure_before_dispatch_reports_no_model_work(self):
        self.module()
        script = f'''
import runpy,sys,tempfile
def fail(*args,**kwargs): raise OSError('PRIVATE_VALUE')
tempfile.TemporaryDirectory=fail
sys.argv=['workflow','run','--case','sign-cycle','--output','not-created']
runpy.run_path({str(ROOT / 'tools/core_sequence_workflow.py')!r},run_name='__main__')
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', b'REJECTED: WORKFLOW_CACHE_IO_NO_MODEL_EXECUTION\n'))

    def test_cli_exit_mapping_failure_is_caught_before_success_receipt(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            saved = self.fixture(root, 'saved')
            for mode in ('check', 'run'):
                output = root / mode
                args = ['check', '--input', str(saved)] if mode == 'check' else ['run', '--case', 'sign-cycle', '--output', str(output)]
                script = f'''
import runpy,sys
sys.path.insert(0,{str(ROOT)!r})
import integration_tools.core_sequence_workflow as w
def fail(report): raise TypeError('PRIVATE_VALUE')
w.exit_code=fail
sys.argv=['workflow',*{args!r}]
runpy.run_path({str(ROOT / 'tools/core_sequence_workflow.py')!r},run_name='__main__')
'''
                result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True)
                code = 'WORKFLOW_CHECK_FAILED_NO_MODEL_EXECUTION' if mode == 'check' else 'WORKFLOW_RUN_FAILED_WORK_MAY_BE_NONZERO'
                self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', ('REJECTED: ' + code + '\n').encode()))
                self.assertEqual(output.exists(), mode == 'run')

    def test_cli_cache_cleanup_failure_precedes_receipt_with_honest_mode_error(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            saved = self.fixture(root, 'saved')
            for mode in ('check', 'run'):
                with self.subTest(mode=mode):
                    output = root / mode
                    args = ['check', '--input', str(saved)] if mode == 'check' else ['run', '--case', 'sign-cycle', '--output', str(output)]
                    script = f'''
import runpy,sys,tempfile
original=tempfile.TemporaryDirectory.cleanup
def fail(self):
 original(self)
 raise OSError('PRIVATE_CLEANUP_VALUE')
tempfile.TemporaryDirectory.cleanup=fail
sys.argv=['workflow',*{args!r}]
runpy.run_path({str(ROOT / 'tools/core_sequence_workflow.py')!r},run_name='__main__')
'''
                    result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True)
                    code = 'WORKFLOW_CHECK_FAILED_NO_MODEL_EXECUTION' if mode == 'check' else 'WORKFLOW_RUN_FAILED_WORK_MAY_BE_NONZERO'
                    self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', ('REJECTED: ' + code + '\n').encode()))
                    self.assertEqual(output.exists(), mode == 'run')
                    if mode == 'run':
                        self.assertEqual(set(self.snapshot(output)), {'INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt'})

    def test_run_output_inside_baseline_is_rejected_without_mutating_input(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            baseline = self.fixture(Path(tmp), 'baseline')
            before = self.snapshot(baseline)
            output = baseline / 'new-output'
            with self.assertRaisesRegex(m.WorkflowError, '^WORKFLOW_OUTPUT_BASELINE_OVERLAP_NO_MODEL_EXECUTION$'):
                m.run_closed_sequence('sign-cycle', output, baseline)
            self.assertEqual(before, self.snapshot(baseline))
            self.assertFalse(output.exists())
