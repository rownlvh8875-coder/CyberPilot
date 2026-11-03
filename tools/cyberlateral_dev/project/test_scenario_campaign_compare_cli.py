"""Isolated R44 CLI must remain data-only with stable exits and no unsafe writes."""

import contextlib
import io
import json
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

from scenario_campaign_compare_fixture import change_saved_trace, copy_campaign, real_campaign
from v1_helpers import ROOT

REAL_TEMP = tempfile.TemporaryDirectory


@contextlib.contextmanager
def late_cleanup_fault(*args, **kwargs):
    # Real creation, publication and cleanup; only the final cleanup result fails.
    with REAL_TEMP(*args, **kwargs) as scratch:
        yield scratch
    raise OSError('controlled late cleanup fault')


class CampaignCompareCliTests(unittest.TestCase):
    def cli(self, *args):
        self.assertTrue((ROOT / 'tools/scenario_campaign_compare.py').is_file(), 'Missing R44 CLI')
        return subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/scenario_campaign_compare.py', *map(str, args)],
                              capture_output=True, timeout=30, check=False)

    def test_real_isolated_cli_match_has_no_model_numpy_native_or_reference_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = real_campaign()
            output = Path(tmp) / 'out'
            result = self.cli('--baseline', source, '--candidate', source, '--output', output)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            record = json.loads((output / 'CAMPAIGN_COMPARE.json').read_bytes())
            receipt = json.loads((output / 'RECEIPT.json').read_bytes())
            self.assertEqual((record['compared_sample_count'], record['difference_count']), (32, 0))
            self.assertEqual(receipt['forbidden_modules_loaded'], [])
            self.assertEqual((record['new_model_executions'], record['new_reference_executions']), (0, 0))

    def test_difference_error_source_and_corrupt_input_have_distinct_record_behavior(self):
        for kind, code in [('different', 1), ('error', 2), ('corrupt', 2)]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                old = real_campaign()
                source = copy_campaign(root / 'input', seeds=(42,), status='ERROR') if kind == 'error' else copy_campaign(root / 'input')
                if kind == 'different':
                    change_saved_trace(source)
                elif kind == 'corrupt':
                    (source / 'CAMPAIGN.json').write_bytes(b'corrupt')
                result = self.cli('--baseline', old, '--candidate', source, '--output', root / 'out')
                self.assertEqual(result.returncode, code, result.stderr.decode())
                marker = root / 'out/CAMPAIGN_COMPARE.json'
                self.assertEqual(marker.is_file(), kind != 'corrupt')
                if kind == 'error':
                    self.assertEqual(json.loads(marker.read_bytes())['status'], 'ERROR')
                if kind == 'corrupt':
                    self.assertIn(b'REJECTED: CAMPAIGN_COMPARE_', result.stderr)
                    self.assertNotIn(b'Traceback', result.stderr)

    def test_required_unknown_and_abbreviated_flags_never_create_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            for flags in [[], ['--output', output], ['--base', 'x', '--candidate', 'x', '--output', output],
                          ['--baseline', 'x', '--candidate', 'x', '--output', output, '--input', 'x']]:
                with self.subTest(flags=flags):
                    self.assertEqual(self.cli(*flags).returncode, 2)
                    self.assertFalse(output.exists())

    def test_preflight_path_failures_have_bounded_cli_rejection_without_outputs(self):
        cli = runpy.run_path(str(ROOT / 'tools/scenario_campaign_compare.py'), run_name='_r45_path_probe')
        original = Path.exists
        for kind in ['permission', 'invalid-path']:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                output = root / 'out'
                baseline = root / ('invalid\0path' if kind == 'invalid-path' else 'missing-input')

                def exists(path, output=output, kind=kind):
                    if kind == 'permission' and path == output:
                        raise PermissionError('private denied-path details')
                    return original(path)

                stdout, stderr = io.StringIO(), io.StringIO()
                with patch.object(Path, 'exists', exists), contextlib.redirect_stdout(stdout), \
                        contextlib.redirect_stderr(stderr):
                    code = cli['main'](['--baseline', str(baseline), '--candidate', str(root / 'missing-input'),
                                        '--output', str(output)])
                self.assertEqual(code, 2)
                self.assertEqual(stdout.getvalue(), '')
                self.assertEqual(stderr.getvalue(), 'REJECTED: CAMPAIGN_COMPARE_IO\n')
                self.assertEqual(list(root.iterdir()), [])

    def test_cli_cache_cleanup_failure_preserves_the_completed_exit_code(self):
        source = real_campaign()
        cli = runpy.run_path(str(ROOT / 'tools/scenario_campaign_compare.py'), run_name='_r44_cache_probe')
        original = shutil.rmtree

        def fail_cache(path, *, onexc=None):
            original(path, onexc=onexc)
            if Path(path).name.startswith('cyberlateral-r44-cache-'):
                raise OSError('controlled cache cleanup failure')

        with tempfile.TemporaryDirectory() as tmp, warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter('always')
            output = Path(tmp) / 'out'
            with patch.object(shutil, 'rmtree', side_effect=fail_cache), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                try:
                    code = cli['main'](['--baseline', str(source), '--candidate', str(source), '--output', str(output)])
                except OSError:
                    self.fail('CLI cleanup must not contradict a completed comparison exit')
            self.assertEqual(code, 0)
            self.assertEqual(json.loads((output / 'CAMPAIGN_COMPARE.json').read_bytes())['status'], 'MATCH')
            self.assertEqual(len(observed), 1)
            self.assertIn('CACHE_CLEANUP_FAILED_AFTER_RESULT', str(observed[0].message))

    def assert_closed_result(self, output):
        import hashlib

        record = json.loads((output / 'CAMPAIGN_COMPARE.json').read_bytes())
        files = {p.relative_to(output).as_posix(): p for p in output.rglob('*') if p.is_file()}
        expected = {'CAMPAIGN_COMPARE.json', 'SUMMARY_KO.md', 'RECEIPT.json', 'SHA256SUMS.txt'}
        for run in record['runs']:
            if run['comparison_report'] is not None:
                expected.update({run['comparison_report'], str(Path(run['comparison_report']).parent / 'SHA256SUMS.txt')})
        self.assertEqual(set(files), expected)
        for name, path in files.items():
            self.assertFalse(path.is_symlink())
            if path.name == 'SHA256SUMS.txt':
                prefix = '' if path.parent == output else path.parent.relative_to(output).as_posix() + '/'
                sums = ''.join(hashlib.sha256(file.read_bytes()).hexdigest() + '  ' + key.removeprefix(prefix) + '\n'
                               for key, file in sorted(files.items()) if key.startswith(prefix) and key != name)
                self.assertEqual(path.read_text(), sums)
        return record

    def completed_api(self, source, output):
        from integration_tools.scenario_campaign_compare_run import run_campaign_comparison

        try:
            result = run_campaign_comparison(source, source, output)
        except Exception as error:
            self.fail(f'Diagnostic replaced a completed comparison: {type(error).__name__}: {error}')
        self.assertEqual(self.assert_closed_result(output), result)
        return result

    def fault_cli(self, fault, *args):
        # Keep the CLI and comparator real in an isolated process; no product hook.
        wrapper = '''
import runpy
import sys
import tempfile
import warnings
from contextlib import contextmanager
real_temp = tempfile.TemporaryDirectory
fault = sys.argv[2]
@contextmanager
def cache_fault(*args, **kwargs):
    cache = kwargs.get('prefix') == 'cyberlateral-r44-cache-'
    if cache and fault == 'enter':
        raise OSError('controlled cache creation failure')
    with real_temp(*args, **kwargs) as scratch:
        yield scratch
    if cache:
        raise OSError('controlled cache cleanup failure')
tempfile.TemporaryDirectory = cache_fault
if fault in {'hook', 'hook_sink'}:
    warnings.simplefilter('always', RuntimeWarning)
    def failed_warning(*args, **kwargs):
        raise RuntimeError('controlled warning hook failure')
    warnings.showwarning = failed_warning
if fault == 'hook_sink':
    class BrokenSink:
        def write(self, value):
            raise OSError('controlled broken diagnostic sink')
        def flush(self):
            pass
    sys.stderr = BrokenSink()
module = runpy.run_path(sys.argv[1], run_name='r48_cache_fault')
raise SystemExit(module['main'](sys.argv[3:]))
'''
        return subprocess.run([sys.executable, '-I', '-B', '-W', 'error::RuntimeWarning', '-c', wrapper,
                               str(ROOT / 'tools/scenario_campaign_compare.py'), fault, *map(str, args)],
                              capture_output=True, timeout=40)

    def test_postcommit_warning_as_error_preserves_each_source_verdict(self):
        from integration_tools import scenario_campaign_compare_run as runner

        for status, code in [('MATCH', 0), ('DIFFERENT', 1), ('ERROR', 2)]:
            source = real_campaign(seeds=(42,), status=status)
            diagnostic = io.StringIO()
            with self.subTest(status=status), REAL_TEMP() as tmp, warnings.catch_warnings(), contextlib.redirect_stderr(diagnostic):
                warnings.simplefilter('error', RuntimeWarning)
                with patch.object(runner.tempfile, 'TemporaryDirectory', late_cleanup_fault):
                    record = self.completed_api(source, Path(tmp) / 'out')
                self.assertEqual((record['status'], record['regression_status'], record['difference_count'], runner.exit_code(record)),
                                 (status, 'MATCH', 0, code))
                self.assertIn('CAMPAIGN_COMPARE_CLEANUP_FAILED_AFTER_COMMIT', diagnostic.getvalue())

    def test_postcommit_failed_warning_hook_preserves_completed_result(self):
        from integration_tools import scenario_campaign_compare_run as runner

        source = real_campaign()
        diagnostic = io.StringIO()
        with REAL_TEMP() as tmp, warnings.catch_warnings(), contextlib.redirect_stderr(diagnostic):
            warnings.simplefilter('always', RuntimeWarning)
            with patch.object(runner.tempfile, 'TemporaryDirectory', late_cleanup_fault), \
                    patch.object(warnings, 'showwarning', side_effect=RuntimeError('controlled warning hook')):
                record = self.completed_api(source, Path(tmp) / 'out')
            self.assertEqual(record['status'], 'MATCH')
        self.assertIn('CAMPAIGN_COMPARE_CLEANUP_FAILED_AFTER_COMMIT', diagnostic.getvalue())

    def test_postcommit_unavailable_diagnostic_sink_preserves_completed_result(self):
        from integration_tools import scenario_campaign_compare_run as runner

        source = real_campaign()
        for failure in [OSError('broken pipe'), ValueError('closed stream')]:
            with self.subTest(failure=type(failure).__name__), REAL_TEMP() as tmp, warnings.catch_warnings():
                warnings.simplefilter('always', RuntimeWarning)
                with patch.object(runner.tempfile, 'TemporaryDirectory', late_cleanup_fault), \
                        patch.object(warnings, 'showwarning', side_effect=RuntimeError('controlled warning hook')), \
                        patch.object(sys.stderr, 'write', side_effect=failure):
                    record = self.completed_api(source, Path(tmp) / 'out')
                self.assertEqual(record['status'], 'MATCH')

    def test_diagnostic_base_exceptions_are_not_swallowed_after_commit(self):
        from integration_tools import scenario_campaign_compare_run as runner

        source = real_campaign()
        for stop in [KeyboardInterrupt, SystemExit]:
            with self.subTest(stop=stop.__name__), REAL_TEMP() as tmp, warnings.catch_warnings():
                warnings.simplefilter('always', RuntimeWarning)
                output = Path(tmp) / 'out'
                with patch.object(runner.tempfile, 'TemporaryDirectory', late_cleanup_fault), \
                        patch.object(warnings, 'showwarning', side_effect=stop), self.assertRaises(stop):
                    runner.run_campaign_comparison(source, source, output)
                self.assertEqual(self.assert_closed_result(output)['status'], 'MATCH')

    def test_precommit_hardlink_failure_remains_rejected(self):
        from integration_tools import scenario_campaign_compare_run as runner

        source = real_campaign()
        with REAL_TEMP() as tmp, warnings.catch_warnings():
            warnings.simplefilter('error', RuntimeWarning)
            output = Path(tmp) / 'out'
            with patch.object(runner.os, 'link', side_effect=OSError('controlled link failure')), \
                    self.assertRaisesRegex(runner.CampaignCompareError, 'CAMPAIGN_COMPARE_PUBLICATION_FAILED'):
                runner.run_campaign_comparison(source, source, output)
            self.assertFalse((output / 'CAMPAIGN_COMPARE.json').exists())

    def test_cache_warning_error_preserves_all_cli_result_kinds(self):
        for kind, code, status in [('match', 0, 'MATCH'), ('difference', 1, 'DIFFERENT'),
                                   ('source_error', 2, 'ERROR'), ('rejected', 2, None)]:
            with self.subTest(kind=kind), REAL_TEMP() as tmp:
                home = Path(tmp)
                old = new = real_campaign(seeds=(42,), status='ERROR') if kind == 'source_error' else real_campaign()
                if kind == 'difference':
                    new = copy_campaign(home / 'changed')
                    change_saved_trace(new)
                elif kind == 'rejected':
                    old = new = home / 'missing'
                normal = self.cli('--baseline', old, '--candidate', new, '--output', home / 'normal')
                result = self.fault_cli('cleanup', '--baseline', old, '--candidate', new, '--output', home / 'fault')
                self.assertEqual(normal.returncode, code, normal.stderr)
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertEqual(result.stdout, normal.stdout)
                self.assertEqual(result.stderr, normal.stderr + b'WARNING: CAMPAIGN_COMPARE_CACHE_CLEANUP_FAILED_AFTER_RESULT\n')
                self.assertNotIn(b'Traceback', result.stderr)
                if status is None:
                    self.assertIn(b'REJECTED: CAMPAIGN_COMPARE_', normal.stderr)
                    self.assertFalse((home / 'normal').exists())
                    self.assertFalse((home / 'fault').exists())
                else:
                    record = self.assert_closed_result(home / 'fault')
                    self.assertEqual(record, self.assert_closed_result(home / 'normal'))
                    self.assertEqual(record['status'], status)
                    self.assertEqual(record['difference_count'], 1 if kind == 'difference' else 0)

    def test_cli_failed_warning_hook_and_sink_preserve_completed_result(self):
        source = real_campaign()
        for fault in ['hook', 'hook_sink']:
            with self.subTest(fault=fault), REAL_TEMP() as tmp:
                output = Path(tmp) / 'out'
                result = self.fault_cli(fault, '--baseline', source, '--candidate', source, '--output', output)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(b'MATCH: regression=MATCH; 0 differences;', result.stdout)
                self.assertNotIn(b'Traceback', result.stderr)
                self.assertEqual(self.assert_closed_result(output)['status'], 'MATCH')
                self.assertEqual(result.stderr, b'' if fault == 'hook_sink' else
                                 b'WARNING: CAMPAIGN_COMPARE_CACHE_CLEANUP_FAILED_AFTER_RESULT\n')

    def test_cache_creation_failure_before_result_is_rejected(self):
        source = real_campaign()
        with REAL_TEMP() as tmp:
            output = Path(tmp) / 'out'
            result = self.fault_cli('enter', '--baseline', source, '--candidate', source, '--output', output)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(result.stdout, b'')
            self.assertEqual(result.stderr, b'REJECTED: CAMPAIGN_COMPARE_IO\n')
            self.assertFalse(output.exists())
