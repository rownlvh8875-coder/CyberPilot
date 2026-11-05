"""Closed run orchestration: preflight, truthful work, portable output and failures."""

import hashlib
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT

CASES = ('sign-cycle', 'declared-difference', 'late-invalid')


def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CoreArchiveRunTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_sequence_archive_run.py').is_file(), 'Missing CORE17 offline archive run')
        self.assertTrue((ROOT / 'tools/core_sequence_archive_run.py').is_file(), 'Missing CORE17 explicit run CLI')
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.core_sequence_archive_run')
        self.suite = importlib.import_module('integration_tools.core_sequence_suite')
        self.portable = importlib.import_module('integration_tools.core_sequence_portable')
        self.bundle = importlib.import_module('integration_tools.core_sequence_bundle')
        self.report = importlib.import_module('integration_tools.core_sequence_archive_workflow')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.output = self.root / 'output'
        source = self.root / 'fixture'; self.suite.run_closed_suite(source)
        files = {'suite/' + c + '/' + n: (source / c / n).read_bytes() for c in CASES for n in ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt')}
        self.raw = self.bundle.build_suite_archive(files)
        self.baseline = self.root / 'baseline.zip'; self.baseline.write_bytes(self.raw)
        self.files = files

    def execute(self, output=None):
        return self.m.run_archived_suite(self.baseline, sha(self.raw), self.output if output is None else output)

    def observe(self, action):
        count = 0; previous = sys.getprofile()
        def profile(frame, event, arg):
            nonlocal count
            if event == 'call' and frame.f_code.co_name == 'step' and frame.f_code.co_filename.endswith('/src/cyberlateral_dev/api.py'):
                count += 1
        sys.setprofile(profile)
        try: result = action()
        finally: sys.setprofile(previous)
        return result, count

    def snapshot(self, folder):
        return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*') if p.is_file()}

    def changed_baseline(self):
        files = dict(self.files); prefix = 'suite/late-invalid/'
        value = json.loads(files[prefix + 'RESULTS.json']); value['identity']['marker'] = None
        files[prefix + 'RESULTS.json'] = canonical(value)
        files[prefix + 'SHA256SUMS.txt'] = ''.join(sha(files[prefix + n]) + '  ' + n + '\n' for n in ('INPUT.json', 'RESULTS.json')).encode()
        self.raw = self.bundle.build_suite_archive(files); self.baseline.write_bytes(self.raw)

    def args(self, output=None):
        return ['run', '--baseline-archive', str(self.baseline), '--baseline-sha256', sha(self.raw),
                '--output-root', str(self.output if output is None else output)]

    def cli(self, args=None):
        return subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence_archive_run.py', *(self.args() if args is None else args)], capture_output=True)

    def cli_module(self):
        spec = importlib.util.spec_from_file_location('core17_cli_test', ROOT / 'tools/core_sequence_archive_run.py')
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

    def test_complete_run_has_six_observed_steps_and_fourteen_files(self):
        result, count = self.observe(self.execute)
        self.assertEqual((count, result['new_synthetic_model_steps']), (6, 6))
        self.assertTrue(result['execution_requested'])
        self.assertEqual(result['contract_id'], 'CORE17_CLOSED_OFFLINE_ARCHIVE_RUN_V1')
        self.assertEqual(result['status'], 'OFFLINE_SYNTHETIC_ARCHIVE_RUN_COMPLETED')
        self.assertEqual(result['comparison_exit_code'], 0)
        self.assertEqual(result['suite_run']['saved_status_counts'], {'MATCH': 1, 'DIFFERENT': 1, 'REJECTED': 1})
        expected = {'BASELINE.zip', 'CURRENT.zip', *(f'suite/{c}/{n}' for c in CASES for n in ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt')),
                    *(f'comparison/{n}' for n in ('COMPARISON.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt'))}
        self.assertEqual(set(self.snapshot(self.output)), expected)
        self.assertEqual((self.output / 'BASELINE.zip').read_bytes(), self.raw)
        self.assertEqual((self.output / 'CURRENT.zip').read_bytes(), self.raw)
        self.assertEqual(result['comparison_publication']['new_synthetic_model_steps'], 0)
        self.assertFalse(result['source_identity_reauthenticated'])
        self.assertEqual(result['gates']['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(result['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')

    def test_valid_baseline_difference_is_complete_not_a_run_failure(self):
        self.changed_baseline(); r, count = self.observe(self.execute)
        self.assertEqual(count, 6); self.assertEqual(r['comparison_exit_code'], 1)
        comparison = json.loads((self.output / 'comparison/COMPARISON.json').read_bytes())
        self.assertEqual(comparison['difference_counts'], {'INPUT': 0, 'RESULT': 0, 'IDENTITY': 1})
        detail = comparison['reports'][2]['comparison']['differences'][0]
        self.assertTrue(detail['left_present']); self.assertFalse(detail['right_present'])

    def test_existing_public_composition_produces_exact_same_artifacts(self):
        got = self.execute(); manual = self.root / 'manual'; manual.mkdir()
        (manual / 'BASELINE.zip').write_bytes(self.raw)
        suite = self.suite.run_closed_suite(manual / 'suite')
        exported = self.portable.export_saved_suite(manual / 'suite', manual / 'CURRENT.zip')
        compared = self.report.publish_archive_report(manual / 'BASELINE.zip', sha(self.raw), manual / 'CURRENT.zip', exported['archive_sha256'], manual / 'comparison')
        self.assertEqual(self.snapshot(self.output), self.snapshot(manual))
        self.assertEqual(got['suite_run'], suite); self.assertEqual(got['current_export'], exported)
        self.assertEqual(got['comparison_publication'], compared)

    def test_two_runs_have_identical_artifacts_and_receipts(self):
        first = self.execute(); other = self.root / 'second'; second = self.execute(other)
        self.assertEqual(first, second); self.assertEqual(self.snapshot(self.output), self.snapshot(other))

    def test_malformed_sha_precedes_output_metadata_and_source_access(self):
        with patch.object(self.m, '_output', side_effect=AssertionError('metadata before SHA')), \
                patch('os.open', side_effect=AssertionError('file open before SHA')):
            with self.assertRaises(self.m.ArchiveRunError) as found:
                self.m.run_archived_suite(self.baseline, 'short', self.output)
        self.assertIn('PREFLIGHT', found.exception.code); self.assertIn('NO_MODEL_EXECUTION', found.exception.code)
        self.assertFalse(self.output.exists())

    def test_wrong_sha_never_runs_model_or_creates_output(self):
        def action():
            with self.assertRaises(self.m.ArchiveRunError) as found:
                self.m.run_archived_suite(self.baseline, '0' * 64, self.output)
            self.assertIn('NO_MODEL_EXECUTION', found.exception.code)
        _, count = self.observe(action); self.assertEqual(count, 0); self.assertFalse(self.output.exists())

    def test_bad_zip_never_runs_model_or_creates_output(self):
        self.raw = b'broken ZIP'; self.baseline.write_bytes(self.raw)
        def action():
            with self.assertRaises(self.m.ArchiveRunError): self.execute()
        _, count = self.observe(action); self.assertEqual(count, 0); self.assertFalse(self.output.exists())

    def test_oversized_source_and_fifo_are_rejected_without_model_work(self):
        huge = self.root / 'huge.zip'
        with huge.open('wb') as stream: stream.truncate(2_000_001)
        fifo = self.root / 'fifo'; os.mkfifo(fifo)
        for source in (huge, fifo):
            def action(source=source):
                with self.assertRaises(self.m.ArchiveRunError): self.m.run_archived_suite(source, sha(self.raw), self.output)
            _, count = self.observe(action); self.assertEqual(count, 0)
        self.assertFalse(self.output.exists())

    def test_output_guards_do_not_start_execution(self):
        link = self.root / 'link'; link.symlink_to(self.root, target_is_directory=True)
        self.output.mkdir(); (self.output / 'keep').write_bytes(b'keep')
        for output in (self.output, link / 'new', self.root / 'missing/child', ROOT / 'core17-output', Path('bad\0name'), 'not Path'):
            def action(output=output):
                with self.assertRaises(self.m.ArchiveRunError): self.execute(output)
            _, count = self.observe(action); self.assertEqual(count, 0)
        self.assertEqual((self.output / 'keep').read_bytes(), b'keep')
        self.assertFalse((ROOT / 'core17-output').exists())

    def test_original_baseline_read_once_before_model_and_bytes_modes_unchanged(self):
        original = os.open; reads = []; steps = []; before = (self.baseline.read_bytes(), self.baseline.stat().st_mode)
        def observed(path, flags, *args, **kwargs):
            if path == self.baseline: reads.append('baseline')
            return original(path, flags, *args, **kwargs)
        real = self.m.run_closed_suite
        def run(*args, **kwargs):
            steps.append(len(reads)); return real(*args, **kwargs)
        with patch('os.open', side_effect=observed), patch.object(self.m, 'run_closed_suite', side_effect=run): self.execute()
        self.assertEqual(reads, ['baseline']); self.assertEqual(steps, [1])
        self.assertEqual((self.baseline.read_bytes(), self.baseline.stat().st_mode), before)

    def test_original_changed_after_capture_does_not_reopen_or_replace_snapshot(self):
        real = self.m.run_closed_suite
        def run(*args, **kwargs):
            self.baseline.write_bytes(b'changed after snapshot'); return real(*args, **kwargs)
        with patch.object(self.m, 'run_closed_suite', side_effect=run): result = self.execute()
        self.assertEqual(result['comparison_exit_code'], 0)
        self.assertEqual((self.output / 'BASELINE.zip').read_bytes(), self.raw)
        self.assertEqual(result['baseline_verification']['archive_sha256'], sha(self.raw))

    def test_baseline_copy_zero_progress_preserves_partial_and_executes_zero_steps(self):
        def action():
            with patch('os.write', return_value=0), self.assertRaises(self.m.ArchiveRunError) as found: self.execute()
            self.assertIn('BASELINE_COPY', found.exception.code); self.assertIn('NO_MODEL_EXECUTION', found.exception.code)
            self.assertIn('OUTPUT_MAY_EXIST', found.exception.code)
        _, count = self.observe(action); self.assertEqual(count, 0)
        self.assertTrue((self.output / 'BASELINE.zip').exists()); self.assertFalse((self.output / 'suite').exists())

    def test_short_writes_complete_baseline_export_and_report(self):
        original = os.write
        with patch('os.write', side_effect=lambda fd, raw: original(fd, raw[:97])): result = self.execute()
        self.assertEqual(result['comparison_exit_code'], 0); self.assertEqual((self.output / 'CURRENT.zip').read_bytes(), self.raw)

    def test_second_case_failure_preserves_first_case_and_nonzero_work(self):
        real = self.suite._run_captured
        from integration_tools.core_sequence_workflow import WorkflowError
        def fail(case, *args):
            if case == 'declared-difference': raise WorkflowError('INJECTED_CASE_FAILURE')
            return real(case, *args)
        def action():
            with patch.object(self.suite, '_run_captured', side_effect=fail), self.assertRaises(self.m.ArchiveRunError) as found: self.execute()
            self.assertIn('RUN:', found.exception.code); self.assertIn('WORK_MAY_BE_NONZERO', found.exception.code)
            self.assertNotIn('NO_MODEL_EXECUTION', found.exception.code)
        _, count = self.observe(action); self.assertEqual(count, 3)
        self.assertTrue((self.output / 'suite/sign-cycle/RESULTS.json').is_file()); self.assertFalse((self.output / 'CURRENT.zip').exists())

    def test_export_failure_preserves_run_with_truthful_uncertainty(self):
        original = os.open
        def fail(path, flags, *args, **kwargs):
            if Path(path).name == 'CURRENT.zip' and flags & os.O_WRONLY: raise OSError('disk full')
            return original(path, flags, *args, **kwargs)
        def action():
            with patch('os.open', side_effect=fail), self.assertRaises(self.m.ArchiveRunError) as found: self.execute()
            self.assertIn('EXPORT:', found.exception.code); self.assertIn('WORK_MAY_BE_NONZERO', found.exception.code)
        _, count = self.observe(action); self.assertEqual(count, 6)
        self.assertTrue((self.output / 'suite/late-invalid/RESULTS.json').is_file()); self.assertFalse((self.output / 'comparison').exists())

    def test_report_failure_preserves_current_zip_with_truthful_uncertainty(self):
        original = os.open
        def fail(path, flags, *args, **kwargs):
            if path == 'COMPARISON.json' and flags & os.O_WRONLY: raise OSError('disk full')
            return original(path, flags, *args, **kwargs)
        def action():
            with patch('os.open', side_effect=fail), self.assertRaises(self.m.ArchiveRunError) as found: self.execute()
            self.assertIn('COMPARE:', found.exception.code); self.assertIn('WORK_MAY_BE_NONZERO', found.exception.code)
        _, count = self.observe(action); self.assertEqual(count, 6)
        self.assertEqual((self.output / 'CURRENT.zip').read_bytes(), self.raw)

    def test_extra_root_member_rejects_final_success(self):
        original = self.m.publish_archive_report
        def extra(*args):
            result = original(*args); (self.output / 'unexpected').touch(); return result
        with patch.object(self.m, 'publish_archive_report', side_effect=extra), self.assertRaises(self.m.ArchiveRunError) as found: self.execute()
        self.assertIn('FINAL_LAYOUT', found.exception.code); self.assertIn('WORK_MAY_BE_NONZERO', found.exception.code)
        self.assertTrue((self.output / 'comparison/SUMMARY_KO.md').is_file())

    def test_cli_literal_run_required_and_unknown_options_rejected(self):
        args = self.args()
        for bad in (args[1:], args[:-2], [*args, '--format', 'json'], [*args, '--input', 'real.log'], ['check', *args[1:]]):
            result = self.cli(bad); self.assertEqual(result.returncode, 2); self.assertEqual(result.stdout, b'')
        self.assertFalse(self.output.exists())

    def test_cli_receipt_exit_zero_and_one_preserve_stage_results(self):
        for changed in (False, True):
            if changed: self.changed_baseline()
            output = self.root / ('cli-' + str(changed)); result = self.cli(self.args(output))
            self.assertEqual(result.returncode, int(changed), result.stderr); self.assertEqual(result.stderr, b'')
            receipt = json.loads(result.stdout); self.assertEqual(result.stdout, canonical(receipt))
            expected = self.execute(self.root / ('api-' + str(changed)))
            self.assertEqual(receipt, expected); self.assertEqual(receipt['new_synthetic_model_steps'], 6)

    def test_cli_bad_baseline_has_no_producer_import_or_output(self):
        self.raw = b'broken'; self.baseline.write_bytes(self.raw)
        script = '''import importlib.abc,runpy,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.startswith(('integration_tools.core_sequence_run','integration_tools.scenario_run','cyberlateral_dev','numpy')):
   raise AssertionError('forbidden producer import before preflight:'+fullname)
sys.meta_path.insert(0,Block()); sys.argv=sys.argv[1:]
runpy.run_path(sys.argv[0],run_name='__main__')
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(ROOT / 'tools/core_sequence_archive_run.py'), *self.args()], capture_output=True)
        self.assertEqual(result.returncode, 2); self.assertEqual(result.stdout, b'')
        self.assertIn(b'NO_MODEL_EXECUTION', result.stderr); self.assertFalse(self.output.exists())

    def test_cli_cache_creation_failure_prevents_work(self):
        cli = self.cli_module(); err = StringIO()
        with patch.object(cli.tempfile, 'TemporaryDirectory', side_effect=OSError('cache')), patch('sys.stderr', err):
            self.assertEqual(cli.main(self.args()), 2)
        self.assertIn('NO_MODEL_EXECUTION', err.getvalue()); self.assertFalse(self.output.exists())

    def test_cli_cleanup_failure_after_run_keeps_outputs_and_restores_cache(self):
        cli = self.cli_module(); original = tempfile.TemporaryDirectory; before = sys.pycache_prefix
        class BadCleanup(original):
            def __exit__(self, exc, value, tb):
                super().__exit__(exc, value, tb); raise OSError('cache cleanup')
        err, out = StringIO(), StringIO()
        with patch.object(cli.tempfile, 'TemporaryDirectory', BadCleanup), patch('sys.stderr', err), patch('sys.stdout', out):
            self.assertEqual(cli.main(self.args()), 2)
        self.assertEqual(sys.pycache_prefix, before); self.assertEqual(out.getvalue(), '')
        self.assertIn('WORK_MAY_BE_NONZERO', err.getvalue()); self.assertIn('OUTPUT_MAY_EXIST', err.getvalue())
        self.assertTrue((self.output / 'comparison/SUMMARY_KO.md').is_file())

    def test_cli_stdout_failure_does_not_claim_zero_work_or_delete_results(self):
        cli = self.cli_module(); err = StringIO()
        with patch('sys.stdout', StringIO()), patch('sys.stderr', err): self.assertEqual(cli.main(self.args()), 2)
        self.assertIn('WORK_MAY_BE_NONZERO', err.getvalue()); self.assertNotIn('NO_MODEL_EXECUTION', err.getvalue())
        self.assertEqual((self.output / 'CURRENT.zip').read_bytes(), self.raw)
