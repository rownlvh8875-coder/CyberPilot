"""Real CLI exits/publication and fresh independent-worker import barrier."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scenario_report_fixture import canonical, edit_json, write_bundle
from v1_helpers import ROOT


class ScenarioReferenceCLITests(unittest.TestCase):
    def cli(self, *args):
        path = ROOT / 'tools/scenario_reference_check.py'
        self.assertTrue(path.is_file(), 'Missing R38 independent check CLI')
        return subprocess.run([sys.executable, '-I', '-B', path, *map(str, args)], capture_output=True, timeout=30, check=False)

    def test_cli_match_result_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'saved')
            process = self.cli('--input', source, '--output', root / 'check')
            self.assertEqual(process.returncode, 0, process.stderr.decode())
            self.assertEqual(process.stderr, b'')
            self.assertEqual(json.loads(process.stdout), {'status': 'MATCH', 'difference_count': 0,
                             'reference_steps': 4, 'new_model_executions': 0})
            raw = (root / 'check/REFERENCE_CHECK.json').read_bytes()
            self.assertEqual((root / 'check/SHA256SUMS.txt').read_text(), hashlib.sha256(raw).hexdigest() + '  REFERENCE_CHECK.json\n')

    def test_cli_arithmetic_difference_is_exit_one_not_error_or_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'saved')
            # Float32 bits have no redundant CSV column; rehash preserves record consistency.
            edit_json(source, 'RESULTS.json', lambda r: r['rows'][0]['model_output']['projection']['torque_float32'].update(bits_hex='00000000'))
            process = self.cli('--input', source, '--output', root / 'check')
            self.assertEqual(process.returncode, 1, process.stderr.decode())
            self.assertEqual(process.stderr, b'')
            self.assertEqual(json.loads(process.stdout)['status'], 'DIFFERENT')
            record = json.loads((root / 'check/REFERENCE_CHECK.json').read_bytes())
            self.assertEqual(record['difference_count'], 1)
            self.assertEqual(record['first_difference']['field'], 'rows[0].model_output.projection.torque_float32.bits_hex')

    def test_cli_invalid_options_corruption_and_output_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'saved')
            for args in [[], ['--input', source], ['--input', source, '--output', root / 'out', '--rate', '0']]:
                process = self.cli(*args)
                self.assertEqual(process.returncode, 2)
                self.assertFalse((root / 'out').exists())
            output = root / 'existing'
            output.mkdir()
            process = self.cli('--input', root / 'missing', '--output', output)
            self.assertEqual(process.returncode, 2)
            self.assertIn(b'REFERENCE_OUTPUT_EXISTS', process.stderr)
            self.assertEqual(list(output.iterdir()), [])
            (source / 'RESULTS.json').write_bytes(b'{}')
            process = self.cli('--input', source, '--output', root / 'out')
            self.assertEqual(process.returncode, 2)
            self.assertIn(b'REPORT_CHECKSUM', process.stderr)
            self.assertFalse((root / 'out').exists())

    def test_fresh_worker_cannot_import_public_or_shared_model_backend(self):
        self.assertTrue((ROOT / 'tools/scenario_reference_worker.py').is_file(), 'Missing R38 isolated reference worker')
        blocked = {'cyberlateral_dev', 'capnp', 'openpilot', 'opendbc', 'cereal',
                   'oracle', 'state_model', 'request_quantizer', 'normalized_pipeline'}
        code = ('import runpy,sys\nblocked=' + repr(blocked) + '\n'
                'class Barrier:\n'
                ' def find_spec(self, fullname, path=None, target=None):\n'
                '  if fullname.split(".")[0] in blocked: raise AssertionError("MODEL_IMPORT:"+fullname)\n'
                'sys.meta_path.insert(0,Barrier())\n'
                'runpy.run_path(sys.argv[1],run_name="__main__")\n')
        with tempfile.TemporaryDirectory() as tmp:
            source = write_bundle(Path(tmp) / 'saved')
            process = subprocess.run([sys.executable, '-I', '-B', '-c', code, ROOT / 'tools/scenario_reference_worker.py'],
                                     input=(source / 'INPUT.json').read_bytes(), capture_output=True, timeout=30, check=False)
            self.assertEqual(process.returncode, 0, process.stderr.decode())
            self.assertEqual(process.stderr, b'')
            result = json.loads(process.stdout)
            self.assertEqual(result['forbidden_modules_loaded'], [])
            self.assertEqual(result['reference_steps'], 4)
            self.assertEqual([r['model_output']['projection']['integer_command'] for r in result['rows']], [2, -2, 0, 2])
            self.assertEqual(process.stdout, canonical(result))

    def test_cli_looping_input_reports_input_error_and_creates_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'loop'
            source.symlink_to('loop')
            process = self.cli('--input', source, '--output', root / 'check')
            self.assertEqual(process.returncode, 2)
            self.assertEqual(process.stdout, b'')
            self.assertEqual(process.stderr, b'REJECTED: REPORT_INPUT_FILE\n')
            self.assertEqual(list(root.iterdir()), [source])

    def test_fresh_checker_parent_does_not_import_model_or_numpy(self):
        blocked = {'cyberlateral_dev', 'numpy', 'capnp', 'openpilot', 'opendbc', 'cereal'}
        code = ('import importlib.util,sys\nblocked=' + repr(blocked) + '\n'
                'class Barrier:\n'
                ' def find_spec(self, fullname, path=None, target=None):\n'
                '  if fullname.split(".")[0] in blocked: raise AssertionError("MODEL_IMPORT:"+fullname)\n'
                'sys.meta_path.insert(0,Barrier())\n'
                'spec=importlib.util.spec_from_file_location("r38_cli",sys.argv[1])\n'
                'cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)\n'
                'raise SystemExit(cli.main(sys.argv[2:]))\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'saved')
            process = subprocess.run([sys.executable, '-I', '-B', '-c', code, ROOT / 'tools/scenario_reference_check.py',
                                      '--input', str(source), '--output', str(root / 'check')],
                                     capture_output=True, timeout=30, check=False)
            self.assertEqual(process.returncode, 0, process.stderr.decode())
            self.assertEqual(json.loads(process.stdout)['status'], 'MATCH')


if __name__ == '__main__':
    unittest.main()
