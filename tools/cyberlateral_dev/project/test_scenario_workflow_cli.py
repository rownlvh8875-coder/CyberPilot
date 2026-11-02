"""Actual one-command synthetic workflow, exits and isolated frontend boundary."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scenario_compare_fixture import refresh, write_batch
from scenario_report_fixture import edit_json
from v1_helpers import ROOT


class WorkflowCLITests(unittest.TestCase):
    def tool(self):
        tool = ROOT / 'tools/scenario_workflow.py'
        self.assertTrue(tool.is_file(), 'Missing R40 integrated workflow CLI')
        return tool

    def cli(self, *args):
        return subprocess.run([sys.executable, '-I', '-B', self.tool(), *map(str, args)], capture_output=True, timeout=90, check=False)

    def test_real_valid_cli_has_canonical_stdout_real_reports_and_bound_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = ROOT / 'examples/synthetic_sign_cycle_v1.json'
            raw = source.read_bytes()
            p = self.cli('--input', source, '--input', ROOT / 'examples/synthetic_resumed_v1.json', '--output', root / 'out')
            self.assertEqual(p.returncode, 0, p.stderr.decode())
            self.assertEqual(p.stderr, b'')
            r = json.loads(p.stdout)
            self.assertEqual((r['status'], r['completed'], r['rejected'], r['model_steps'], r['reference_steps']), ('VERIFIED', 2, 0, 5, 5))
            self.assertEqual(p.stdout, (json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(',', ':')) + '\n').encode())
            saved = json.loads((root / 'out/WORKFLOW.json').read_bytes())
            self.assertEqual(saved['observed_dev_source_hashes']['tools/scenario_workflow.py'], hashlib.sha256(self.tool().read_bytes()).hexdigest())
            self.assertTrue((root / 'out/batch/index.html').is_file())
            self.assertEqual(source.read_bytes(), raw)

    def test_mixed_and_all_rejected_cli_exit_one_not_false_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = root / 'bad.json'
            bad.write_bytes(b'{')
            for number, inputs in enumerate([[ROOT / 'examples/synthetic_sign_cycle_v1.json', bad], [bad]]):
                p = self.cli(*[part for source in inputs for part in ['--input', source]], '--output', root / f'out-{number}')
                self.assertEqual(p.returncode, 1, p.stderr.decode())
                self.assertEqual(json.loads(p.stdout)['status'], ['VERIFIED_WITH_INPUT_REJECTIONS', 'NO_COMPLETED_CASES'][number])

    def test_baseline_match_and_coherent_difference_do_not_overwrite_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = write_batch(root / 'baseline', ('sign',))
            p = self.cli('--input', ROOT / 'examples/synthetic_sign_cycle_v1.json', '--baseline', baseline, '--output', root / 'match')
            self.assertEqual(p.returncode, 0, p.stderr.decode())
            self.assertEqual(json.loads(p.stdout)['regression_status'], 'MATCH')
            edit_json(baseline / 'case-001/data', 'RESULTS.json',
                      lambda r: r['rows'][0]['model_output']['projection']['torque_float32'].update(bits_hex='00000000'))
            refresh(baseline)
            before = {p.relative_to(baseline): p.read_bytes() for p in baseline.rglob('*') if p.is_file()}
            p = self.cli('--input', ROOT / 'examples/synthetic_sign_cycle_v1.json', '--baseline', baseline, '--output', root / 'different')
            self.assertEqual(p.returncode, 1, p.stderr.decode())
            self.assertEqual(json.loads(p.stdout)['status'], 'REGRESSION_DIFFERENT')
            self.assertEqual(before, {p.relative_to(baseline): p.read_bytes() for p in baseline.rglob('*') if p.is_file()})

    def test_invalid_flags_missing_raw_and_output_collision_have_no_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = ROOT / 'examples/synthetic_resumed_v1.json'
            (root / 'exists').mkdir()
            for args in [[], ['--input', source], ['--input', source, '--output', root / 'out', '--rate', '0'],
                         ['--input', root / 'missing', '--output', root / 'out'],
                         ['--input', source, '--output', root / 'exists']]:
                p = self.cli(*args)
                self.assertEqual(p.returncode, 2)
                self.assertEqual(p.stdout, b'')
                self.assertNotIn(b'Traceback', p.stderr)
            self.assertFalse((root / 'out').exists())
            self.assertEqual(list((root / 'exists').iterdir()), [])

    def test_corrupt_baseline_cli_rejects_before_any_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = write_batch(root / 'baseline')
            (baseline / 'RECEIPT.json').unlink()
            p = self.cli('--input', ROOT / 'examples/synthetic_sign_cycle_v1.json', '--baseline', baseline, '--output', root / 'out')
            self.assertEqual(p.returncode, 2)
            self.assertEqual(p.stdout, b'')
            self.assertIn(b'REJECTED: COMPARE_', p.stderr)
            self.assertFalse((root / 'out').exists())

    def test_real_r35_mixed_pack_remains_38_model_and_reference_steps(self):
        self.tool()
        literal = json.loads((ROOT / 'reference/r35_regression_expected_v1.json').read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = [part for name in literal['order'] for part in ['--input', ROOT / 'examples/r35' / name]]
            p = self.cli(*args, '--output', root / 'out')
            self.assertEqual(p.returncode, 1, p.stderr.decode())
            r = json.loads(p.stdout)
            self.assertEqual((r['status'], r['completed'], r['rejected'], r['model_steps'], r['reference_steps']),
                             ('VERIFIED_WITH_INPUT_REJECTIONS', 6, 3, 38, 38))
            checked = json.loads((root / 'out/reference/BATCH_REFERENCE_CHECK.json').read_bytes())
            self.assertEqual([c['observed_rejection_code'] for c in checked['cases'][-3:]], ['SCENARIO_DOMAIN', 'SCENARIO_ORDER', 'SCENARIO_KEYS'])

    def test_real_frontend_cannot_import_model_numpy_or_native_modules(self):
        code = ('import runpy,sys\n'
                'class Barrier:\n'
                ' def find_spec(self,fullname,path=None,target=None):\n'
                '  if fullname.split(".")[0] in {"cyberlateral_dev","numpy","capnp","openpilot","opendbc","cereal"}: '
                'raise AssertionError("FRONTEND_IMPORT:"+fullname)\n'
                'sys.meta_path.insert(0,Barrier())\n'
                'sys.argv=sys.argv[1:]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = subprocess.run([sys.executable, '-I', '-B', '-c', code, self.tool(), '--input', ROOT / 'examples/synthetic_resumed_v1.json',
                                '--output', root / 'out'], capture_output=True, timeout=40, check=False)
            self.assertEqual(p.returncode, 0, p.stderr.decode())
            self.assertEqual(json.loads(p.stdout)['model_steps'], 1)


if __name__ == '__main__':
    unittest.main()
