"""Real R39 CLI, mixed R35 acceptance, errors and cold frontend import barrier."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scenario_compare_fixture import refresh, write_batch
from scenario_report_fixture import edit_json
from v1_helpers import ROOT


class BatchReferenceCLITests(unittest.TestCase):
    def cli(self, *args):
        tool = ROOT / 'tools/scenario_batch_reference_check.py'
        self.assertTrue(tool.is_file(), 'Missing R39 batch reference CLI')
        return subprocess.run([sys.executable, '-I', '-B', tool, *map(str, args)], capture_output=True, timeout=60, check=False)

    def test_real_complete_and_mixed_cli_exits_and_canonical_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i, profiles in enumerate([('sign', 'resumed'), ('sign', 'bad'), ('bad',), ('sign', 'missing')]):
                source = write_batch(root / f'batch-{i}', profiles)
                process = self.cli('--input', source, '--output', root / f'out-{i}')
                self.assertEqual(process.returncode, [0, 0, 1, 1][i], process.stderr.decode())
                self.assertEqual(process.stderr, b'')
                observed = json.loads(process.stdout)
                self.assertEqual(observed['status'], ['MATCH', 'MATCH_WITH_INPUT_REJECTIONS', 'NO_COMPLETED_CASES', 'INCOMPLETE'][i])
                self.assertEqual(observed['new_model_executions'], 0)

    def test_cli_wrong_projection_reports_different_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'batch', ('sign',))
            edit_json(source / 'case-001/data', 'RESULTS.json',
                      lambda r: r['rows'][0]['model_output']['projection']['torque_float32'].update(bits_hex='00000000'))
            refresh(source)
            process = self.cli('--input', source, '--output', root / 'out')
            self.assertEqual(process.returncode, 1, process.stderr.decode())
            self.assertEqual(json.loads(process.stdout)['status'], 'DIFFERENT')
            record = json.loads((root / 'out/BATCH_REFERENCE_CHECK.json').read_bytes())
            self.assertEqual(record['numerical_difference_count'], 1)

    def test_cli_corrupt_or_portable_input_and_options_are_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'batch')
            for args in [[], ['--input', source], ['--input', source, '--output', root / 'out', '--rate', '0']]:
                self.assertEqual(self.cli(*args).returncode, 2)
            (source / 'RECEIPT.json').unlink()
            process = self.cli('--input', source, '--output', root / 'out')
            self.assertEqual(process.returncode, 2)
            self.assertEqual(process.stdout, b'')
            self.assertIn(b'REJECTED: COMPARE_', process.stderr)
            self.assertFalse((root / 'out').exists())

    def test_cli_loop_input_is_bounded_error_not_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'loop').symlink_to('loop')
            process = self.cli('--input', root / 'loop', '--output', root / 'out')
            self.assertEqual(process.returncode, 2)
            self.assertEqual(process.stdout, b'')
            self.assertEqual(process.stderr, b'REJECTED: BATCH_REFERENCE_INPUT_FILE\n')
            self.assertFalse((root / 'out').exists())

    def test_fresh_cli_frontend_cannot_import_public_model_or_numpy(self):
        tool = ROOT / 'tools/scenario_batch_reference_check.py'
        self.assertTrue(tool.is_file(), 'Missing R39 batch reference CLI')
        blocked = {'cyberlateral_dev', 'numpy', 'capnp', 'openpilot', 'opendbc', 'cereal'}
        code = ('import runpy,sys\nblocked=' + repr(blocked) + '\n'
                'class Barrier:\n'
                ' def find_spec(self,fullname,path=None,target=None):\n'
                '  if fullname.split(".")[0] in blocked: raise AssertionError("MODEL_IMPORT:"+fullname)\n'
                'sys.meta_path.insert(0,Barrier())\n'
                'sys.argv=sys.argv[1:]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'batch')
            process = subprocess.run([sys.executable, '-I', '-B', '-c', code, tool,
                '--input', source, '--output', root / 'out'], capture_output=True, timeout=40, check=False)
            self.assertEqual(process.returncode, 0, process.stderr.decode())
            self.assertEqual(json.loads(process.stdout)['reference_steps'], 5)

    def test_real_r35_mixed_batch_all_six_results_and_three_rejections(self):
        tool = ROOT / 'tools/scenario_batch_reference_check.py'
        self.assertTrue(tool.is_file(), 'Missing R39 batch reference CLI')
        from integration_tools.scenario_batch_run import run_batch

        literal = json.loads((ROOT / 'reference/r35_regression_expected_v1.json').read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_batch([ROOT / 'examples/r35' / n for n in literal['order']], root / 'batch')
            process = self.cli('--input', root / 'batch', '--output', root / 'out')
            self.assertEqual(process.returncode, 0, process.stderr.decode())
            r = json.loads((root / 'out/BATCH_REFERENCE_CHECK.json').read_bytes())
            self.assertEqual((r['status'], r['matched_cases'], r['input_rejections_confirmed'], r['reference_steps']),
                             ('MATCH_WITH_INPUT_REJECTIONS', 6, 3, 38))
            self.assertEqual([c['observed_rejection_code'] for c in r['cases'][-3:]],
                             ['SCENARIO_DOMAIN', 'SCENARIO_ORDER', 'SCENARIO_KEYS'])


if __name__ == '__main__':
    unittest.main()
