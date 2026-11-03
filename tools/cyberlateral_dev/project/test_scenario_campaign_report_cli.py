"""Isolated CLI and publication boundary; injected I/O faults only."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from scenario_campaign_compare_fixture import edit
from scenario_campaign_report_fixture import copy_comparison, real_comparison
from v1_helpers import ROOT

CLI = ROOT / 'tools/scenario_campaign_compare_report.py'


class CampaignReportCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-B', str(CLI), *map(str, args)], capture_output=True, timeout=40)

    def run_api(self, source, output):
        from integration_tools.scenario_campaign_report_run import run_report
        return run_report(source, output)

    def test_complete_report_closed_manifest_and_no_worker_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'view'
            result = self.run_cli('--input', real_comparison(), '--output', out)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b'REPORT_COMPLETE', result.stdout)
            self.assertEqual({p.name for p in out.iterdir()}, {'index.html', 'VIEW.json', 'RECEIPT.json', 'SHA256SUMS.txt'})
            expected = ''.join(hashlib.sha256((out / n).read_bytes()).hexdigest() + '  ' + n + '\n'
                               for n in ['RECEIPT.json', 'VIEW.json', 'index.html'])
            self.assertEqual((out / 'SHA256SUMS.txt').read_text(), expected)
            receipt = json.loads((out / 'RECEIPT.json').read_bytes())
            self.assertEqual(receipt['forbidden_modules_loaded'], [])
            self.assertEqual((receipt['renderer_model_executions'], receipt['renderer_reference_executions']), (0, 0))

    def test_source_error_report_success_is_not_source_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli('--input', real_comparison('error'), '--output', Path(tmp) / 'view')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b'overall=ERROR', result.stdout)
            self.assertIn(b'regression=MATCH', result.stdout)

    def test_invalid_input_exit_two_no_output_or_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = copy_comparison(Path(tmp) / 'input')
            edit(source, 'CAMPAIGN_COMPARE.json', lambda r: r.update(difference_count=9))
            out = Path(tmp) / 'view'
            result = self.run_cli('--input', source, '--output', out)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b'CAMPAIGN_REPORT_', result.stderr)
            self.assertNotIn(b'Traceback', result.stderr)
            self.assertFalse(out.exists())

    def test_required_arguments_no_abbreviation_or_rate_option(self):
        for args in [[], ['--inp', 'x', '--output', 'y'], ['--input', 'x', '--output', 'y', '--r', '1']]:
            with self.subTest(args=args):
                self.assertEqual(self.run_cli(*args).returncode, 2)

    def test_output_guards_before_read_and_no_overwrite(self):
        from integration_tools.scenario_campaign_report_schema import CampaignReportError
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            source = copy_comparison(home / 'input')
            (home / 'existing').mkdir()
            (home / 'alias').symlink_to(home, target_is_directory=True)
            for out in [home / 'existing', source / 'inside', ROOT / 'r46-forbidden', home / 'alias/output', home / 'missing/output']:
                with self.subTest(out=out), self.assertRaises(CampaignReportError):
                    self.run_api(source, out)
            self.assertEqual(list((home / 'existing').iterdir()), [])

    def test_late_input_change_prevents_completion(self):
        from integration_tools import scenario_campaign_report_run as module
        from integration_tools.scenario_campaign_report_schema import CampaignReportError
        with tempfile.TemporaryDirectory() as tmp:
            source = copy_comparison(Path(tmp) / 'input')
            out = Path(tmp) / 'view'
            real_render = module._render_html

            def changed(view):
                result = real_render(view)
                (source / 'SUMMARY_KO.md').write_text('late change')
                return result

            with patch.object(module, '_render_html', side_effect=changed), self.assertRaises(CampaignReportError):
                self.run_api(source, out)
            self.assertFalse((out / 'index.html').exists())

    def test_late_source_change_prevents_completion(self):
        from integration_tools import scenario_campaign_report_run as module
        from integration_tools.scenario_campaign_report_schema import CampaignReportError
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'view'
            with patch.object(module, '_source_hashes', side_effect=[{'test': 'a'}, {'test': 'b'}]):
                with self.assertRaisesRegex(CampaignReportError, 'SOURCE_CHANGED'):
                    self.run_api(real_comparison(), out)
            self.assertFalse((out / 'index.html').exists())

    def test_pending_html_failure_does_not_publish_index(self):
        from integration_tools import scenario_campaign_report_run as module
        from integration_tools.scenario_campaign_report_schema import CampaignReportError
        real_write = module._write

        def failed(path, raw):
            if path.name == 'pending_html':
                real_write(path, raw[:3])
                raise OSError('injected write failure')
            real_write(path, raw)

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'view'
            with patch.object(module, '_write', side_effect=failed), self.assertRaises(CampaignReportError):
                self.run_api(real_comparison(), out)
            self.assertFalse((out / 'index.html').exists())

    def test_cleanup_failure_after_commit_warns_but_returns_completion(self):
        from integration_tools import scenario_campaign_report_run as module
        real_temp = tempfile.TemporaryDirectory

        @contextmanager
        def cleanup_failure(*args, **kwargs):
            with real_temp(*args, **kwargs) as scratch:
                yield scratch
            raise OSError('injected cleanup failure')

        source = real_comparison()
        with real_temp() as tmp:
            out = Path(tmp) / 'view'
            with patch.object(module.tempfile, 'TemporaryDirectory', cleanup_failure), self.assertWarnsRegex(RuntimeWarning, 'AFTER_COMMIT'):
                result = self.run_api(source, out)
            self.assertEqual(result['status'], 'REPORT_COMPLETE')
            self.assertTrue((out / 'index.html').is_file())


if __name__ == '__main__':
    unittest.main()
