"""Validation-only contract, actual file inputs and model-free fresh processes."""

import contextlib
import hashlib
import importlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scenario_fixture import document, encode
from v1_helpers import ROOT

IDENTITY = ['input_raw_sha256', 'scenario_id', 'sample_count', 'first_index', 'last_index']
FORBIDDEN = {'cyberlateral_dev', 'capnp', 'numpy', 'openpilot', 'opendbc', 'cereal',
             'integration_tools.scenario_engine', 'integration_tools.scenario_run', 'integration_tools.verify'}


class ScenarioValidationTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_validate.py').is_file(), 'Missing R37 input-only validator')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_validate')

    def cli(self, root, *args):
        return subprocess.run([sys.executable, '-I', '-B', root / 'tools/scenario.py', *map(str, args)],
                              capture_output=True, timeout=20, check=False)

    def result(self, process, accepted, code=None):
        self.assertEqual(process.returncode, 0 if accepted else 2, process.stderr.decode())
        self.assertEqual(process.stderr, b'')
        self.assertTrue(process.stdout, 'Missing validation JSON')
        result = json.loads(process.stdout)
        self.assertIs(result['accepted'], accepted)
        self.assertEqual(result['rejection_code'], code)
        self.assertEqual(result['status'], 'SCENARIO_INPUT_VALID' if accepted else 'SCENARIO_INPUT_REJECTED')
        self.assertEqual(result['validation_scope'], 'INPUT_SCHEMA_AND_DOMAIN_ONLY_NOT_MODEL_RUNTIME_OR_ORIGIN')
        self.assertEqual(result['model_executions'], 0)
        self.assertEqual(result['gates']['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(result['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
        self.assertIsNone(result['gates']['actual_r'])
        self.assertEqual(process.stdout, (json.dumps(result, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode())
        if not accepted:
            self.assertTrue(all(result[key] is None for key in IDENTITY))
        return result

    def test_cli_valid_and_resumed_json_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for raw, count, first, last in [(encode(document(2)), 2, 0, 1),
                    ((ROOT / 'examples/synthetic_resumed_v1.json').read_bytes(), 1, 5, 5)]:
                source = root / 'input.json'
                source.write_bytes(raw)
                result = self.result(self.cli(ROOT, '--input', source, '--validate-only'), True)
                self.assertEqual([result['sample_count'], result['first_index'], result['last_index']], [count, first, last])
                self.assertEqual(result['input_raw_sha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(list(root.iterdir()), [source])
                self.assertEqual(source.read_bytes(), raw)

    def test_invalid_inputs_report_original_codes_and_null_identity(self):
        late, order, state, policy = [document(2) for _ in range(4)]
        late['samples'][-1]['request'] = 1
        order['samples'][-1]['index'] = 3
        state['initial_state']['previous_applied'] = 1
        policy['rate_budget_per_s'] = 0
        cases = [(b'{', 'SCENARIO_JSON'), (encode(document()).replace(b'0.25', b'NaN'), 'SCENARIO_JSON'),
                 (encode(late), 'SCENARIO_DOMAIN'), (encode(order), 'SCENARIO_ORDER'),
                 (encode(state), 'SCENARIO_STATE'), (encode(policy), 'SCENARIO_KEYS')]
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'input.json'
            for raw, code in cases:
                with self.subTest(code=code):
                    source.write_bytes(raw)
                    self.result(self.cli(ROOT, '--input', source, '--validate-only'), False, code)
                    self.assertEqual(list(Path(tmp).iterdir()), [source])
                    self.assertEqual(source.read_bytes(), raw)

    def test_file_rejections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'valid').write_bytes(encode(document()))
            (root / 'link').symlink_to(root / 'valid')
            (root / 'directory').mkdir()
            os.mkfifo(root / 'fifo')
            (root / 'oversize').write_bytes(b' ' * 1048577)
            for name in ['missing', 'link', 'directory', 'fifo', 'oversize']:
                with self.subTest(name=name):
                    self.result(self.cli(ROOT, '--input', root / name, '--validate-only'), False,
                                'SCENARIO_SIZE' if name == 'oversize' else 'SCENARIO_INPUT_FILE')

    def test_mode_errors_before_input_read(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        reader = importlib.import_module('integration_tools.scenario_input')
        spec = importlib.util.spec_from_file_location('r37_actual_cli', ROOT / 'tools/scenario.py')
        assert spec is not None and spec.loader is not None
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            for args in [['--input', str(path / 'missing'), '--validate-only', '--output', str(path / 'out')],
                         ['--input', str(path / 'missing')]]:
                with self.subTest(args=args), patch.object(reader, 'read_scenario', side_effect=AssertionError('INPUT_READ')):
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                        cli.main(args)
                    self.assertEqual(caught.exception.code, 2)
                    self.assertEqual(list(path.iterdir()), [])

    def test_repeated_moved_inputs_are_canonical_and_private_path_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = encode(document(2))
            outputs = []
            for name in ['one.json', 'two.json']:
                path = root / name
                path.write_bytes(raw)
                process = self.cli(ROOT, '--input', path, '--validate-only')
                self.result(process, True)
                self.assertNotIn(str(root).encode(), process.stdout)
                outputs.append(process.stdout)
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual({p.name for p in root.iterdir()}, {'one.json', 'two.json'})

    def test_fresh_cli_import_barrier(self):
        # A real import trap: loading any model/runner/engine fails this process.
        code = ('import importlib.util,sys;sys.path.insert(0,' + repr(str(ROOT)) + ');'
                'blocked=' + repr(FORBIDDEN) + ';\n'
                'class Barrier:\n'
                ' def find_spec(self, fullname, path=None, target=None):\n'
                '  if fullname in blocked or fullname.split(".")[0] in blocked: raise AssertionError("MODEL_IMPORT:"+fullname)\n'
                'sys.meta_path.insert(0,Barrier())\n'
                'spec=importlib.util.spec_from_file_location("actual_cli",' + repr(str(ROOT / 'tools/scenario.py')) + ')\n'
                'cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)\n'
                'result=cli.main(sys.argv[1:])\n'
                'assert not any(n in blocked or n.split(".")[0] in blocked for n in sys.modules)\n'
                'raise SystemExit(result)\n')
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'input.json'
            for raw, accepted, error in [(encode(document()), True, None), (b'{', False, 'SCENARIO_JSON')]:
                source.write_bytes(raw)
                process = subprocess.run([sys.executable, '-I', '-B', '-c', code, '--input', str(source), '--validate-only'],
                                         capture_output=True, timeout=20, check=False)
                self.result(process, accepted, error)

    def test_minimal_export_needs_no_model_payload(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            minimal = root / 'component'
            for relative in ['tools/scenario.py', 'integration_tools/__init__.py', 'integration_tools/scenario_input.py',
                             'integration_tools/scenario_output.py', 'integration_tools/scenario_validate.py']:
                target = minimal / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            source = root / 'input.json'
            source.write_bytes(encode(document()))
            self.result(self.cli(minimal, '--input', source, '--validate-only'), True)
            self.assertFalse((minimal / 'src').exists())
            self.assertFalse((minimal / 'integration_tools/scenario_run.py').exists())
            self.assertEqual({p.name for p in root.iterdir()}, {'component', 'input.json'})

    def test_validator_import_is_inert(self):
        self.module()
        code = ('import sys;sys.path.insert(0,' + repr(str(ROOT)) + ');import integration_tools.scenario_validate;'
                'blocked=' + repr(FORBIDDEN) + ';'
                'assert not any(n in blocked or n.split(".")[0] in blocked for n in sys.modules)')
        process = subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, timeout=20, check=False)
        self.assertEqual(process.returncode, 0, process.stderr.decode())
        self.assertEqual(process.stdout, b'')

    def test_validator_returns_independent_closed_gate_records(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'input.json'
            source.write_bytes(encode(document()))
            first = module.validate_scenario(source)
            self.assertTrue(first['accepted'])
            first['gates']['R_BUDGET'] = 'CHANGED_BY_CALLER'
            self.assertEqual(module.validate_scenario(source)['gates']['R_BUDGET'], 'UNRESOLVED')
