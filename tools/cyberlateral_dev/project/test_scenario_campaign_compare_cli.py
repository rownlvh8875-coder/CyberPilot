"""Isolated R44 CLI must remain data-only with stable exits and no unsafe writes."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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
