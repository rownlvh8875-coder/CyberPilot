"""Summary identity must match active validated observation, not a stale filename."""

import importlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_fault_mode import fault_observations
from test_native_coverage import observations
from v1_helpers import ROOT


class ReferenceIdentityTests(unittest.TestCase):
    def test_all_existing_numerical_summaries_use_validated_active_reference(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        runner = importlib.import_module('native_qualification.run')
        for mode in ['R24', 'R22', 'R23']:
            with tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                data = fault_observations() if mode == 'R24' else observations(mode)
                done = subprocess.CompletedProcess([], 0, runner.canonical({'observations': data, 'receipt': {}}), b'')
                with patch.object(runner, 'verify_experiment'), patch.object(runner, 'verify_inputs'), \
                        patch.object(runner.subprocess, 'run', return_value=done):
                    result = runner.qualify(root / 'python', root / 'native', root / 'output', model_consumption=mode == 'R22',
                                            model_sequence=mode == 'R23', fault_boundaries=mode == 'R24', package_wheel=root / 'public')
                self.assertEqual(result['model_reference_sha256'], data['model_reference_sha256'], mode + ' active reference')


if __name__ == '__main__':
    unittest.main()
