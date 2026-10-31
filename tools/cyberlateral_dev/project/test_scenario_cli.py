"""Repository DEV CLI provenance, exclusive output, preflight and portable bytes."""

import csv
import hashlib
import importlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scenario_fixture import document, encode
from v1_helpers import ROOT, package_feature

PORTABLE = ['INPUT.json', 'RESULTS.json', 'TRACE.csv', 'SUMMARY_KO.md']


class ScenarioCLITests(unittest.TestCase):
    def modules(self):
        self.assertTrue((ROOT / 'tools/scenario.py').is_file(), 'Missing R31 CLI')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_input'), importlib.import_module('integration_tools.scenario_run')

    def cli(self, root, *args):
        return subprocess.run([sys.executable, '-I', '-B', root / 'tools/scenario.py', *map(str, args)], capture_output=True, timeout=20, check=False)

    def test_cli_portable_repeats_csv_manifest_receipt_and_closed_gates(self):
        self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source = root / 'input.json'
            source.write_bytes(encode(document(2)))
            for name in ['a', 'b']:
                result = self.cli(ROOT, '--input', source, '--output', root / name)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual({n: (root / 'a' / n).read_bytes() for n in PORTABLE}, {n: (root / 'b' / n).read_bytes() for n in PORTABLE})
            self.assertEqual({p.name for p in (root / 'a').iterdir()}, set(PORTABLE) | {'RECEIPT.json', 'SHA256SUMS.txt'})
            record = json.loads((root / 'a/RESULTS.json').read_bytes())
            self.assertEqual(record['model_steps'], 2)
            self.assertEqual(record['gates']['R_BUDGET'], 'UNRESOLVED')
            self.assertEqual(record['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
            self.assertEqual(record['input_origin'], 'CALLER_DECLARATION_NOT_AUTHENTICATED')
            self.assertNotIn('actual_input_count', record)
            receipt = json.loads((root / 'a/RECEIPT.json').read_bytes())
            self.assertEqual(receipt['model_origin'], str(ROOT / 'src/cyberlateral_dev/__init__.py'))
            self.assertEqual(receipt['forbidden_modules_loaded'], [])
            csv_rows = list(csv.reader(io.StringIO((root / 'a/TRACE.csv').read_text())))
            self.assertEqual(len(csv_rows[0]), 13)
            self.assertEqual(csv_rows[1], ['0', '0x1.0000000000000p-2', '0x0.0p+0', '0x0.0p+0', 'true', 'null', '0', '0', '4', '2', '2', 'true', '0'])
            lines = (root / 'a/SHA256SUMS.txt').read_text().splitlines()
            self.assertEqual(len(lines), 5)
            for line in lines:
                digest, name = line.split('  ')
                self.assertEqual(hashlib.sha256((root / 'a' / name).read_bytes()).hexdigest(), digest)

    def test_moved_input_same_bytes_portable_same_receipt_different(self):
        _, run = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            for name in ['x', 'y']:
                path = root / (name + '.json')
                path.write_bytes(encode(document()))
                run.run_scenario(path, root / name)
            self.assertEqual([(root / 'x' / n).read_bytes() for n in PORTABLE], [(root / 'y' / n).read_bytes() for n in PORTABLE])
            self.assertNotEqual((root / 'x/RECEIPT.json').read_bytes(), (root / 'y/RECEIPT.json').read_bytes())

    def test_existing_output_dangling_and_missing_parent_before_input_read(self):
        m, run = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / 'file').write_bytes(b'keep')
            (root / 'dir').mkdir()
            (root / 'link').symlink_to(root / 'absent')
            for path, code in [(root / 'file', 'SCENARIO_OUTPUT_EXISTS'), (root / 'dir', 'SCENARIO_OUTPUT_EXISTS'),
                               (root / 'link', 'SCENARIO_OUTPUT_EXISTS'), (root / 'missing/out', 'SCENARIO_OUTPUT_PARENT')]:
                with patch.object(run, 'read_scenario', side_effect=AssertionError('INPUT_READ')), self.assertRaises(m.ScenarioError) as raised:
                    run.run_scenario(root / 'missing.json', path)
                self.assertEqual(raised.exception.code, code)
            self.assertEqual((root / 'file').read_bytes(), b'keep')

    def test_invalid_late_sample_no_loader_no_output(self):
        m, run = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source = root / 'input.json'
            data = document(3)
            data['samples'][-1]['request'] = 2.0
            source.write_bytes(encode(data))
            with patch.object(run, 'load_model', side_effect=AssertionError('MODEL_LOAD')), self.assertRaises(m.ScenarioError):
                run.run_scenario(source, root / 'out')
            self.assertFalse((root / 'out').exists())

    def test_help_unknown_arguments_missing_input(self):
        self.modules()
        self.assertEqual(self.cli(ROOT, '--help').returncode, 0)
        self.assertEqual(self.cli(ROOT, '--rate-budget', '0').returncode, 2)
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            result = self.cli(ROOT, '--input', root / 'none', '--output', root / 'out')
            self.assertEqual(result.returncode, 2)
            self.assertIn(b'SCENARIO_INPUT_FILE', result.stderr)
            self.assertFalse((root / 'out').exists())

    def test_model_origin_and_version_guard(self):
        m, run = self.modules()
        p = package_feature()
        for name, value in [('__version__', '0.4.0'), ('__file__', '/other/cyberlateral_dev/__init__.py')]:
            with patch.object(p, name, value), self.assertRaises(m.ScenarioError) as raised:
                run.load_model(ROOT)
            self.assertEqual(raised.exception.code, 'SCENARIO_MODEL_IDENTITY')

    def test_changed_frozen_source_refused_in_fresh_cli(self):
        self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            copy = root / 'component'
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns('.venv', '__pycache__', 'out'))
            source = root / 'input.json'
            source.write_bytes(encode(document()))
            with (copy / 'src/cyberlateral_dev/api.py').open('ab') as stream:
                stream.write(b'\n# changed frozen source\n')
            result = self.cli(copy, '--input', source, '--output', root / 'out')
            self.assertEqual(result.returncode, 2)
            self.assertIn(b'SCENARIO_SOURCE_IDENTITY', result.stderr)
            self.assertFalse((root / 'out').exists())

    def test_failed_publication_has_no_success_result_and_no_retry(self):
        m, run = self.modules()
        output = importlib.import_module('integration_tools.scenario_output')
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source = root / 'input.json'
            source.write_bytes(encode(document()))
            actual = output._write_exclusive

            def fail(path, raw):
                if path.name == 'TRACE.csv':
                    raise OSError('synthetic write fault')
                return actual(path, raw)

            with patch.object(output, '_write_exclusive', side_effect=fail), self.assertRaises(m.ScenarioError):
                run.run_scenario(source, root / 'out')
            self.assertTrue((root / 'out').is_dir())
            self.assertFalse((root / 'out/RESULTS.json').exists())
            with self.assertRaises(m.ScenarioError) as raised:
                run.run_scenario(source, root / 'out')
            self.assertEqual(raised.exception.code, 'SCENARIO_OUTPUT_EXISTS')

    def test_late_collision_does_not_overwrite(self):
        m, _ = self.modules()
        output = importlib.import_module('integration_tools.scenario_output')
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / 'out').mkdir()
            (root / 'out/keep').write_bytes(b'keep')
            with self.assertRaises(m.ScenarioError):
                output.publish(root / 'out', {'RESULTS.json': b'{}'})
            self.assertEqual((root / 'out/keep').read_bytes(), b'keep')

    def test_inert_run_module_import_and_unsupported_runtime(self):
        m, run = self.modules()
        code = ('import sys;sys.path.insert(0,' + repr(str(ROOT)) + ');import integration_tools.scenario_run;'
                'assert not any(n.split(".")[0] in {"cyberlateral_dev","capnp","numpy","openpilot","opendbc","cereal"} for n in sys.modules)')
        result = subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        with patch.object(run.platform, 'python_version', return_value='3.12.14'), self.assertRaises(m.ScenarioError) as raised:
            run.load_model(ROOT)
        self.assertEqual(raised.exception.code, 'SCENARIO_RUNTIME')
