"""Run the actual fixed demo: isolated cwd, no external input or execution modes."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_offline_call_recorder import ROOT


class RecorderDemoTests(unittest.TestCase):
    def setUp(self):
        self.script = ROOT / 'tools/offline_call_recorder_demo.py'
        self.assertTrue(self.script.is_file(), 'Missing CORE41 isolated demo')

    def test_fixed_demo_twice_is_byte_identical_from_external_cwd(self):
        outputs = []
        with tempfile.TemporaryDirectory() as name:
            for _ in range(2):
                run = subprocess.run([sys.executable, '-I', '-B', str(self.script)], cwd=name, capture_output=True, check=False)
                self.assertEqual((run.returncode, run.stderr), (0, b''))
                outputs.append(run.stdout)
            self.assertEqual(list(Path(name).iterdir()), [])
        self.assertEqual(outputs[0], outputs[1])
        obj = json.loads(outputs[0])
        self.assertEqual(obj['contract_id'], 'CORE41_COUNTERFACTUAL_CALL_RECORDING_V1')
        self.assertEqual([x['request']['requested_binary32_hex'] for x in obj['records']], ['80000000', '00000001'])
        self.assertIs(obj['actual_activation_allowed'], False)

    def test_external_inputs_rate_arguments_and_runtime_modes_are_not_accepted(self):
        for args in (['--input', 'missing.json'], ['--rate-budget-per-s', '0'], ['--capture'], ['--runtime'], ['--output', 'x']):
            run = subprocess.run([sys.executable, '-I', '-B', str(self.script), *args], capture_output=True, check=False)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(run.stdout, b'')

    def test_help_labels_scope_without_running_the_demo(self):
        run = subprocess.run([sys.executable, '-I', '-B', str(self.script), '--help'], capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 0)
        self.assertIn('synthetic', run.stdout.lower())
        self.assertNotIn('"records"', run.stdout)
