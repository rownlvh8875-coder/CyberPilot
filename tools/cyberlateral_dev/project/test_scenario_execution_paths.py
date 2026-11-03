"""Execution path rejection must precede input/model work, not hide later defects."""

import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scenario_fixture import document, encode
from v1_helpers import ROOT


class ScenarioExecutionPathTests(unittest.TestCase):
    def modules(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return (importlib.import_module('integration_tools.scenario_input'),
                importlib.import_module('integration_tools.scenario_run'))

    def rejection(self, call, code):
        reader, _ = self.modules()
        try:
            call()
        except reader.ScenarioError as error:
            self.assertEqual(error.code, code)
            return error
        except Exception as error:
            self.fail(f'Unbounded or late path failure: {type(error).__name__}')
        self.fail('Unsupported execution path accepted')

    def isolated_cli(self, arguments):
        blocked = {'cyberlateral_dev', 'numpy', 'capnp', 'openpilot', 'opendbc', 'cereal',
                   'integration_tools.scenario_engine', 'integration_tools.verify'}
        code = ('import importlib.util,sys\n'
                'sys.path.insert(0,' + repr(str(ROOT)) + ')\n'
                'blocked=' + repr(blocked) + '\n'
                'class Barrier:\n'
                ' def find_spec(self, fullname, path=None, target=None):\n'
                '  if fullname in blocked or fullname.split(".")[0] in blocked: raise AssertionError("MODEL_IMPORT:"+fullname)\n'
                'sys.meta_path.insert(0,Barrier())\n'
                'spec=importlib.util.spec_from_file_location("actual_cli",' + repr(str(ROOT / 'tools/scenario.py')) + ')\n'
                'cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)\n'
                'status=cli.main(' + repr(arguments) + ')\n'
                'assert not any(n in blocked or n.split(".")[0] in blocked for n in sys.modules)\n'
                'raise SystemExit(status)\n')
        return subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, timeout=20, check=False)

    def test_unrepresentable_outputs_reject_before_input_read(self):
        _, runner = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for text in ['invalid\0output', 'invalid\ud800output', 'linux-\udcff']:
                with (self.subTest(path=repr(text)),
                      patch.object(runner, 'read_scenario', side_effect=AssertionError('INPUT_READ')),
                      patch.object(runner, 'load_model', side_effect=AssertionError('MODEL_LOAD'))):
                    error = self.rejection(lambda text=text: runner.run_scenario(root / 'missing', root / text),
                                           'SCENARIO_OUTPUT_PATH')
                    self.assertIsInstance(error.__cause__, ValueError)
                self.assertEqual(list(root.iterdir()), [])

    def test_unrepresentable_execution_inputs_reject_before_input_read(self):
        _, runner = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for text in ['invalid\0input', 'invalid\ud800input', 'linux-\udcff']:
                with (self.subTest(path=repr(text)),
                      patch.object(runner, 'read_scenario', side_effect=AssertionError('INPUT_READ')),
                      patch.object(runner, 'load_model', side_effect=AssertionError('MODEL_LOAD'))):
                    error = self.rejection(lambda text=text: runner.run_scenario(root / text, root / 'out'),
                                           'SCENARIO_INPUT_FILE')
                    self.assertIsInstance(error.__cause__, ValueError)
                self.assertEqual(list(root.iterdir()), [])

    def test_classified_output_codes_objects_and_saved_causes_keep_precedence(self):
        reader, runner = self.modules()
        cause = OSError('original-cause')
        classified = reader.ScenarioError('SCENARIO_OUTPUT_PARENT')
        classified.__cause__ = cause
        with patch.object(Path, 'exists', side_effect=classified), self.assertRaises(reader.ScenarioError) as caught:
            runner.run_scenario(Path('unused'), Path('unused-output'))
        self.assertIs(caught.exception, classified)
        self.assertEqual(caught.exception.code, 'SCENARIO_OUTPUT_PARENT')
        self.assertIs(caught.exception.__cause__, cause)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / 'linux-\udcff'
            existing.write_bytes(b'keep')
            for output, code in [(existing, 'SCENARIO_OUTPUT_EXISTS'), (root / 'missing/out', 'SCENARIO_OUTPUT_PARENT')]:
                with patch.object(runner, 'read_scenario', side_effect=AssertionError('INPUT_READ')):
                    self.rejection(lambda output=output: runner.run_scenario(root / 'invalid\0input', output), code)
            self.assertEqual(existing.read_bytes(), b'keep')

    def test_unclassified_output_filesystem_errors_are_chained(self):
        _, runner = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root, output = Path(tmp), Path(tmp) / 'out'
            for method, target in [('exists', output), ('is_symlink', output), ('is_dir', root)]:
                actual = getattr(Path, method)
                for original in [PermissionError('private-path'), ValueError('private-value')]:
                    def fail(path, *, target=target, actual=actual, original=original):
                        if path == target:
                            raise original
                        return actual(path)

                    with (self.subTest(method=method, error=type(original).__name__),
                          patch.object(Path, method, autospec=True, side_effect=fail),
                          patch.object(runner, 'read_scenario', side_effect=AssertionError('INPUT_READ'))):
                        error = self.rejection(lambda: runner.run_scenario(root / 'missing', output), 'SCENARIO_OUTPUT_PATH')
                        self.assertIs(error.__cause__, original)
            self.assertEqual(list(root.iterdir()), [])

    def test_output_programmer_errors_and_interrupts_are_not_hidden(self):
        _, runner = self.modules()
        for original in [TypeError('programmer'), KeyboardInterrupt(), SystemExit(7)]:
            with patch.object(Path, 'exists', side_effect=original), self.assertRaises(type(original)) as caught:
                runner.run_scenario(Path('unused'), Path('unused-output'))
            self.assertIs(caught.exception, original)

    def test_later_reader_and_loader_errors_are_not_path_rejections(self):
        reader, runner = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'input.json'
            raw = encode(document())
            source.write_bytes(raw)
            for stage in ['read_scenario', 'load_model']:
                for original in [ValueError('later-defect'), reader.ScenarioError('SCENARIO_DOMAIN')]:
                    with (self.subTest(stage=stage, kind=type(original).__name__),
                          patch.object(runner, stage, side_effect=original), self.assertRaises(type(original)) as caught):
                        runner.run_scenario(source, root / 'out')
                    self.assertIs(caught.exception, original)
                    self.assertEqual(source.read_bytes(), raw)
                    self.assertFalse((root / 'out').exists())

    def test_isolated_cli_invalid_execution_paths_are_bounded_and_model_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = encode(document())
            source, surrogate = root / 'input.json', root / 'linux-\udcff'
            source.write_bytes(raw)
            surrogate.write_bytes(raw)
            cases = [(source, root / text, 'SCENARIO_OUTPUT_PATH')
                     for text in ['invalid\0output', 'invalid\ud800output', 'output-\udcff']]
            cases += [(root / text, root / 'out', 'SCENARIO_INPUT_FILE')
                      for text in ['invalid\0input', 'invalid\ud800input', 'linux-\udcff']]
            for input_path, output, code in cases:
                with self.subTest(input=repr(str(input_path)), output=repr(str(output))):
                    process = self.isolated_cli(['--input', str(input_path), '--output', str(output)])
                    self.assertEqual(process.returncode, 2, process.stderr.decode(errors='replace'))
                    self.assertEqual(process.stdout, b'')
                    self.assertEqual(process.stderr, ('REJECTED: ' + code + '\n').encode())
                    self.assertEqual({p.name for p in root.iterdir()}, {source.name, surrogate.name})
                    self.assertEqual(source.read_bytes(), raw)
                    self.assertEqual(surrogate.read_bytes(), raw)

    @unittest.skipIf(os.geteuid() == 0, 'Actual mode000 requires an unprivileged actor')
    def test_actual_permission_output_is_bounded_in_api_and_cli(self):
        _, runner = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            denied = root / 'denied'
            denied.mkdir()
            denied.chmod(0)
            try:
                with self.subTest(interface='API'), patch.object(runner, 'read_scenario', side_effect=AssertionError('INPUT_READ')):
                    error = self.rejection(lambda: runner.run_scenario(root / 'missing', denied / 'out'), 'SCENARIO_OUTPUT_PATH')
                    self.assertIsInstance(error.__cause__, PermissionError)
                with self.subTest(interface='CLI'):
                    process = subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/scenario.py',
                                              '--input', root / 'missing', '--output', denied / 'out'],
                                             capture_output=True, timeout=20, check=False)
                    self.assertEqual(process.returncode, 2)
                    self.assertEqual(process.stdout, b'')
                    self.assertEqual(process.stderr, b'REJECTED: SCENARIO_OUTPUT_PATH\n')
            finally:
                denied.chmod(0o700)
            self.assertEqual(list(denied.iterdir()), [])

    def test_unicode_execution_preserves_literal_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, output = root / '입력.json', root / '출력'
            raw = (ROOT / 'examples/synthetic_sign_cycle_v1.json').read_bytes()
            source.write_bytes(raw)
            process = subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/scenario.py',
                                      '--input', source, '--output', output], capture_output=True, timeout=20, check=False)
            self.assertEqual(process.returncode, 0, process.stderr.decode())
            self.assertEqual(process.stderr, b'')
            result = json.loads((output / 'RESULTS.json').read_bytes())
            self.assertEqual(result['model_steps'], 4)
            self.assertEqual([row['model_output']['projection']['integer_command'] for row in result['rows']], [2, -2, 0, 2])
            self.assertEqual(result['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
            self.assertIsNone(result['gates']['actual_r'])
            self.assertEqual(source.read_bytes(), raw)
            manifest = dict(line.split('  ', 1)[::-1] for line in (output / 'SHA256SUMS.txt').read_text().splitlines())
            self.assertEqual(manifest, {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                        for p in output.iterdir() if p.name != 'SHA256SUMS.txt'})

    def test_validation_only_keeps_surrogateescape_reader_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'linux-\udcff.json'
            raw = (ROOT / 'examples/synthetic_sign_cycle_v1.json').read_bytes()
            source.write_bytes(raw)
            process = subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/scenario.py',
                                      '--input', source, '--validate-only'], capture_output=True, timeout=20, check=False)
            self.assertEqual(process.returncode, 0, process.stderr.decode())
            self.assertEqual(process.stderr, b'')
            result = json.loads(process.stdout)
            self.assertIs(result['accepted'], True)
            self.assertEqual(result['model_executions'], 0)
            self.assertEqual(result['sample_count'], 4)
            self.assertEqual(result['input_raw_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(list(root.iterdir()), [source])
            self.assertEqual(source.read_bytes(), raw)
