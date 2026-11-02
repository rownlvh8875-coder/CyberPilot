"""Exercise the real campaign CLI, not source-text or argparse-only assertions."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from v1_helpers import ROOT


class CampaignCliTests(unittest.TestCase):
    def command(self, *arguments):
        tool = ROOT / 'tools/scenario_campaign.py'
        self.assertTrue(tool.is_file(), 'Missing campaign CLI')
        return subprocess.run([sys.executable, '-B', tool, *map(str, arguments)], capture_output=True, timeout=120)

    def test_real_cli_two_seed_result_and_saved_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            result = self.command('--seed', 42, '--seed', 43, '--cases', 1, '--steps', 16, '--output', output)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            summary = json.loads(result.stdout)
            self.assertEqual((summary['status'], summary['model_steps'], summary['reference_steps']), ('MATCH', 32, 32))
            self.assertEqual(summary['parameters'], {'seeds': [42, 43], 'cases': 1, 'steps': 16})
            saved = json.loads((output / 'CAMPAIGN.json').read_bytes())
            self.assertEqual(saved['status_counts'], {'MATCH': 2, 'DIFFERENT': 0, 'ERROR': 0})

    def test_missing_unknown_and_duplicate_seeds_never_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            base = ['--seed', 42, '--cases', 1, '--steps', 16, '--output', output]
            for arguments in [[], base + ['--r', 1], base + ['--seed', 42],
                              ['--seed', '42.0', '--cases', 1, '--steps', 16, '--output', output]]:
                with self.subTest(arguments=arguments):
                    result = self.command(*arguments)
                    self.assertEqual(result.returncode, 2)
                    self.assertFalse(output.exists())

    def test_existing_output_preserved_and_frontend_imports_no_model_numpy_or_native(self):
        tool = ROOT / 'tools/scenario_campaign.py'
        self.assertTrue(tool.is_file(), 'Missing campaign CLI')
        script = (
            'import contextlib,io,json,runpy,sys; '
            f'main=runpy.run_path({str(tool)!r})["main"]; '
            'out,err=io.StringIO(),io.StringIO(); previous=sys.pycache_prefix; '
            '\nwith contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):\n'
            ' code=main(["--seed","42","--cases","1","--steps","16","--output",sys.argv[1]])\n'
            'forbidden=[n for n in sys.modules if n.split(".")[0] in '
            '{"cyberlateral_dev","numpy","openpilot","cereal","capnp","panda"}]; '
            'print(json.dumps({"code":code,"forbidden":forbidden,"out":out.getvalue(),'
            '"err":err.getvalue(),"cache_restored":sys.pycache_prefix==previous}))')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'keep').write_bytes(b'keep')
            result = subprocess.run([sys.executable, '-B', '-c', script, root], capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(json.loads(result.stdout), {'code': 2, 'forbidden': [], 'out': '',
                                                        'err': 'REJECTED: CAMPAIGN_OUTPUT_EXISTS\n', 'cache_restored': True})
            self.assertEqual([p.name for p in root.iterdir()], ['keep'])


if __name__ == '__main__':
    unittest.main()
