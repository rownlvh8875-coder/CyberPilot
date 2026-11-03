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
