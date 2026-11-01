"""Catch output overwrites, source leakage and installed-consumer divergence."""
import contextlib
import importlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from consumer_reference import expected_simulation
from normalized_reference import NormalizedReference
from test_source_contract import REFERENCE
from v1_helpers import ROOT, package_feature


class OfflineCliTests(unittest.TestCase):
    def cli(self):
        return package_feature('cyberlateral_dev.cli')

    def test_default_stdout_is_canonical_report(self):
        module = self.cli()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(module.main([]), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report['scenario_count'], 7)
        self.assertEqual(report['total_steps'], 112)
        self.assertEqual(output.getvalue(), json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')

    def test_existing_entries_reject_before_report_generation(self):
        module = self.cli()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            targets = [root / 'file', root / 'dir', root / 'dead']
            targets[0].write_bytes(b'KEEP'); targets[1].mkdir(); targets[2].symlink_to(root / 'absent', target_is_directory=True)
            for path in targets:
                error = io.StringIO()
                with (contextlib.redirect_stderr(error), patch.object(module, 'catalog_report', side_effect=AssertionError('MODEL_MUST_NOT_RUN'))):
                    self.assertEqual(module.main(['--output', str(path)]), 2)
                self.assertIn('OUTPUT_EXISTS_NO_SIMULATION', error.getvalue())
            self.assertEqual(targets[0].read_bytes(), b'KEEP')
            self.assertTrue(targets[2].is_symlink())

    def test_output_file_equals_stdout_and_cannot_be_replaced(self):
        module = self.cli()
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / 'new'
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(['--output', str(output)]), 0)
            raw = (output / 'simulation.json').read_bytes()
            self.assertEqual(json.loads(raw)['total_steps'], 112)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(module.main(['--output', str(output)]), 2)
            self.assertEqual((output / 'simulation.json').read_bytes(), raw)

    def test_actual_data_runtime_capture_install_and_source_flags_rejected(self):
        module = self.cli()
        for flag in ['--data', '--production', '--runtime', '--capture', '--install', '--controller']:
            with (self.subTest(flag=flag), contextlib.redirect_stderr(io.StringIO()),
                  patch.object(module, 'catalog_report', side_effect=AssertionError('MODEL_MUST_NOT_RUN')),
                  self.assertRaises(SystemExit) as error):
                module.main([flag, 'not_allowed'])
            self.assertEqual(error.exception.code, 2)

    def test_actual_installed_module_two_processes_independent_parity_and_licenses(self):
        self.cli()
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        backend = importlib.import_module('build_backend')
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            name = backend.build_wheel(str(root / 'dist'))
            subprocess.run([sys.executable, '-B', '-m', 'venv', '--without-pip', str(root / 'env')], check=True, capture_output=True)
            python = root / 'env/bin/python'
            install = subprocess.run(['uv', 'pip', 'install', '--offline', '--no-deps', '--link-mode=copy', '--python', str(python), str(root / 'dist' / name)],
                                     capture_output=True, text=True, check=False)
            self.assertEqual(install.returncode, 0, install.stderr)
            results = [subprocess.run([str(python), '-I', '-B', '-m', 'cyberlateral_dev'], cwd=root, capture_output=True, check=False) for _ in range(2)]
            for result in results:
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(results[0].stdout, results[1].stdout)
            report = json.loads(results[0].stdout)
            scenarios = package_feature('cyberlateral_dev.synthetic_catalog').fixed_catalog()
            reference = NormalizedReference((REFERENCE / 'carcontroller.py').read_bytes(), (REFERENCE / 'lateral.py').read_bytes())
            for scenario, record in zip(scenarios, report['scenarios'], strict=True):
                self.assertEqual(record['result'], json.loads(json.dumps(expected_simulation(scenario, reference))))
            check = """
import importlib.metadata,importlib.util,pathlib,sys
from email.parser import Parser
assert importlib.util.find_spec('numpy') is None
import cyberlateral_dev as p
assert '/site-packages/cyberlateral_dev/' in p.__file__
assert not importlib.metadata.requires('cyberlateral-dev')
d=importlib.metadata.distribution('cyberlateral-dev')
m=Parser().parsestr(d.read_text('METADATA'))
for name in m.get_all('License-File'):
    assert pathlib.Path(d.locate_file('cyberlateral_dev-0.3.0.dist-info/licenses/'+name)).is_file()
assert not [n for n in sys.modules if n.split('.')[0] in {'numpy','opendbc','cereal','capnp','openpilot','selfdrive','kernel'}]
print('INSTALLED_CONSUMER_AND_LICENSES_PASS')
"""
            checked = subprocess.run([str(python), '-I', '-B', '-c', check], cwd=root, capture_output=True, text=True, check=False)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertEqual(checked.stdout, 'INSTALLED_CONSUMER_AND_LICENSES_PASS\n')


if __name__ == '__main__':
    unittest.main()
