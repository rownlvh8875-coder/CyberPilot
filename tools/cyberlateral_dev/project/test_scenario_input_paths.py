"""Input-open rejection must precede parsing/model work without hiding defects."""

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

IDENTITY = ['input_raw_sha256', 'scenario_id', 'sample_count', 'first_index', 'last_index']


class ScenarioInputPathTests(unittest.TestCase):
    def reader(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_input')

    def input_error(self, call):
        reader = self.reader()
        try:
            call()
        except reader.ScenarioError as error:
            self.assertEqual(error.code, 'SCENARIO_INPUT_FILE')
            return error
        except Exception as error:
            self.fail(f'Unclassified input path failure: {type(error).__name__}')
        self.fail('Invalid input path unexpectedly accepted')

    def isolated_cli(self, arguments):
        # OS argv cannot contain NUL: construct it inside the fresh child instead.
        blocked = {'cyberlateral_dev', 'capnp', 'numpy', 'openpilot', 'opendbc', 'cereal',
                   'integration_tools.scenario_engine', 'integration_tools.verify'}
        if '--validate-only' in arguments:
            blocked.add('integration_tools.scenario_run')
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

    def test_invalid_input_paths_reject_before_snapshot_or_parse(self):
        reader = self.reader()
        for text, cause in [('invalid\0path', ValueError), ('invalid\ud800path', UnicodeEncodeError)]:
            with (self.subTest(kind=cause.__name__),
                  patch.object(reader.os, 'fdopen', side_effect=AssertionError('SNAPSHOT_OPEN')),
                  patch.object(reader, 'parse_scenario', side_effect=AssertionError('PARSE'))):
                error = self.input_error(lambda text=text: reader.read_scenario(Path(text)))
                self.assertIsInstance(error.__cause__, cause)

    def test_open_errors_are_chained_and_existing_classification_is_preserved(self):
        reader = self.reader()
        for original in [ValueError('private-open-diagnostic'), PermissionError('private-permission-diagnostic')]:
            with (self.subTest(kind=type(original).__name__),
                  patch.object(reader.os, 'open', side_effect=original),
                  patch.object(reader, 'parse_scenario', side_effect=AssertionError('PARSE'))):
                error = self.input_error(lambda: reader.read_scenario(Path('unused')))
                self.assertIs(error.__cause__, original)
        classified = reader.ScenarioError('SCENARIO_SIZE')
        original_cause = ValueError('original-cause')
        classified.__cause__ = original_cause
        with patch.object(reader.os, 'open', side_effect=classified), self.assertRaises(reader.ScenarioError) as caught:
            reader.read_scenario(Path('unused'))
        self.assertIs(caught.exception, classified)
        self.assertEqual(caught.exception.code, 'SCENARIO_SIZE')
        self.assertIs(caught.exception.__cause__, original_cause)

    def test_programmer_interrupt_and_parser_errors_are_not_reclassified(self):
        reader = self.reader()
        for original in [TypeError('programmer'), KeyboardInterrupt(), SystemExit(7)]:
            with patch.object(reader.os, 'open', side_effect=original), self.assertRaises(type(original)) as caught:
                reader.read_scenario(Path('unused'))
            self.assertIs(caught.exception, original)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'input.json'
            raw = encode(document())
            source.write_bytes(raw)
            for original in [ValueError('parser-defect'), reader.ScenarioError('SCENARIO_JSON')]:
                with patch.object(reader, 'parse_scenario', side_effect=original), self.assertRaises(type(original)) as caught:
                    reader.read_scenario(source)
                self.assertIs(caught.exception, original)
                self.assertEqual(source.read_bytes(), raw)

    def test_runner_rejects_input_path_before_model_load_or_output(self):
        self.reader()
        runner = importlib.import_module('integration_tools.scenario_run')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for text in ['invalid\0path', 'invalid\ud800path']:
                with self.subTest(path=repr(text)), patch.object(runner, 'load_model', side_effect=AssertionError('MODEL_LOAD')):
                    self.input_error(lambda text=text: runner.run_scenario(root / text, root / 'out'))
                self.assertEqual(list(root.iterdir()), [])

    def test_validator_path_rejection_has_null_identity_and_closed_gates(self):
        self.reader()
        validator = importlib.import_module('integration_tools.scenario_validate')
        for text in ['invalid\0path', 'invalid\ud800path']:
            with self.subTest(path=repr(text)):
                try:
                    result = validator.validate_scenario(Path(text))
                except Exception as error:
                    self.fail(f'Validator leaked {type(error).__name__}')
                self.assertIs(result['accepted'], False)
                self.assertEqual(result['status'], 'SCENARIO_INPUT_REJECTED')
                self.assertEqual(result['rejection_code'], 'SCENARIO_INPUT_FILE')
                self.assertEqual([result[key] for key in IDENTITY], [None] * 5)
                self.assertEqual(result['model_executions'], 0)
                self.assertEqual(result['gates']['R_BUDGET'], 'UNRESOLVED')
                self.assertEqual(result['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
                self.assertIsNone(result['gates']['actual_r'])

    def test_isolated_cli_path_rejections_are_bounded_and_model_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for text in ['invalid\0path', 'invalid\ud800path']:
                for validate in [False, True]:
                    with self.subTest(path=repr(text), validate=validate):
                        arguments = ['--input', str(root / text)]
                        arguments += ['--validate-only'] if validate else ['--output', str(root / 'out')]
                        process = self.isolated_cli(arguments)
                        self.assertEqual(process.returncode, 2, process.stderr.decode(errors='replace'))
                        if validate:
                            self.assertEqual(process.stderr, b'')
                            result = json.loads(process.stdout)
                            self.assertIs(result['accepted'], False)
                            self.assertEqual(result['rejection_code'], 'SCENARIO_INPUT_FILE')
                            self.assertEqual([result[key] for key in IDENTITY], [None] * 5)
                            self.assertEqual(result['model_executions'], 0)
                            self.assertEqual(process.stdout, (json.dumps(result, sort_keys=True, ensure_ascii=False,
                                                                         separators=(',', ':'), allow_nan=False) + '\n').encode())
                        else:
                            self.assertEqual(process.stdout, b'')
                            self.assertEqual(process.stderr, b'REJECTED: SCENARIO_INPUT_FILE\n')
                        self.assertNotIn(str(root).encode(), process.stdout + process.stderr)
                        self.assertEqual(list(root.iterdir()), [])

    def test_valid_unicode_and_surrogateescape_paths_preserve_snapshot(self):
        reader = self.reader()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = encode(document())
            for text in ['한글.json', 'linux-\udcff.json']:
                with self.subTest(path=repr(text)):
                    source = root / text
                    source.write_bytes(raw)
                    spec = reader.read_scenario(source)
                    self.assertEqual(spec.scenario_id, 'R31_test')
                    self.assertEqual(spec.raw_sha256, hashlib.sha256(raw).hexdigest())
                    self.assertEqual(len(spec.samples), 1)
                    self.assertEqual(source.read_bytes(), raw)

    @unittest.skipIf(os.geteuid() == 0, 'Actual mode000 requires an unprivileged actor')
    def test_actual_unreadable_input_uses_existing_cli_rejection_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'input.json'
            raw = encode(document())
            source.write_bytes(raw)
            source.chmod(0)
            try:
                for validate in [False, True]:
                    arguments = ['--input', str(source)]
                    arguments += ['--validate-only'] if validate else ['--output', str(root / 'out')]
                    process = subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/scenario.py', *arguments],
                                             capture_output=True, timeout=20, check=False)
                    self.assertEqual(process.returncode, 2)
                    if validate:
                        self.assertEqual(process.stderr, b'')
                        self.assertEqual(json.loads(process.stdout)['rejection_code'], 'SCENARIO_INPUT_FILE')
                    else:
                        self.assertEqual(process.stdout, b'')
                        self.assertEqual(process.stderr, b'REJECTED: SCENARIO_INPUT_FILE\n')
                    self.assertEqual(list(root.iterdir()), [source])
            finally:
                source.chmod(0o600)
            self.assertEqual(source.read_bytes(), raw)
