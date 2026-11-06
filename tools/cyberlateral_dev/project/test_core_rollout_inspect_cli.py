"""Fixed saved-output command: strict syntax, no cache writes, complete output."""

import builtins
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT, package_feature

CASES = ('sign-cycle', 'declared-difference', 'late-invalid')
def canonical(v): return (json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CoreRolloutInspectCliTests(unittest.TestCase):
    def setUp(self):
        self.script = ROOT / 'tools/core_rollout_inspect.py'
        self.assertTrue(self.script.is_file(), 'Missing CORE29 pinned inspection command')
        package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.api: Any = importlib.import_module('integration_tools.core_rollout_inspect')
        producer = importlib.import_module('integration_tools.core_rollout_run')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        for c in CASES: producer.run_rollout_case(c, self.root / c)
        spec = importlib.util.spec_from_file_location('core29_cli_test', self.script)
        assert spec is not None and spec.loader is not None
        self.cli: Any = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.cli)

    def args(self, case='sign-cycle'): return ['--case', case, '--input-root', str(self.root / case)]
    def command(self, args=None, stdout: Any = subprocess.PIPE, stderr: Any = subprocess.PIPE):
        return subprocess.run([sys.executable, '-I', '-B', str(self.script), *(self.args() if args is None else args)], cwd=self.root, stdout=stdout, stderr=stderr)
    def invoke(self, args=None):
        err = StringIO(); p = self.root / 'stdout.bin'
        with p.open('wb') as out, patch('sys.stdout', out), patch('sys.stderr', err): code = self.cli.main(self.args() if args is None else args)
        return code, p.read_bytes(), err.getvalue()

    def test_all_three_cli_inspections_zero_including_historical_rejected(self):
        for c, historical in zip(CASES, (0, 1, 2), strict=True):
            r = self.command(self.args(c)); self.assertEqual((r.returncode, r.stderr), (0, b'')); v = json.loads(r.stdout)
            self.assertEqual((v['inspection_exit_code'], v['recorded_result_exit_code']), (0, historical)); self.assertEqual(r.stdout, canonical(v))

    def test_api_direct_cli_byte_parity(self):
        self.assertEqual(self.command().stdout, canonical(self.api.inspect_rollout_case('sign-cycle', self.root / 'sign-cycle')))

    def test_syntax_and_closed_case_validation_precede_import_and_path(self):
        original = builtins.__import__
        def importing(name, *a, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')): raise AssertionError('project import')
            return original(name, *a, **kw)
        variants = ([], self.args()[:-1], self.args() + self.args(), self.args() + ['--run'], self.args() + ['--output-root', 'x'],
            self.args() + ['--rate-budget-per-s', '0'], self.args() + ['positional'], ['--case', 'foreign', '--input-root', 'x'],
            ['--case', 'sign-cycle', '--input', 'x'], ['--case', 'sign-cycle', '--input-root', ''])
        for args in variants:
            err, out = StringIO(), StringIO()
            with self.subTest(args=args), patch('builtins.__import__', side_effect=importing), patch('os.open', side_effect=AssertionError('path')), patch('sys.stderr', err), patch('sys.stdout', out), self.assertRaises(SystemExit) as found: self.cli.main(args)
            self.assertEqual(found.exception.code, 2); self.assertEqual(out.getvalue(), ''); self.assertEqual(err.getvalue(), 'REJECTED: ROLLOUT_INSPECT_USAGE_NO_MODEL_EXECUTION\n')

    def test_help_is_available_before_path_access(self):
        r = self.command(['--help']); self.assertEqual((r.returncode, r.stderr), (0, b'')); self.assertIn(b'--input-root', r.stdout)
        with patch('os.open', side_effect=AssertionError('path')), patch('sys.stdout', StringIO()), self.assertRaises(SystemExit) as found: self.cli.main(['--help'])
        self.assertEqual(found.exception.code, 0)

    def test_changed_bytes_preserve_identity_error_and_no_receipt(self):
        p = self.root / 'sign-cycle/RESULTS.json'; p.write_bytes(b'!' + p.read_bytes()[1:]); r = self.command()
        self.assertEqual((r.returncode, r.stdout, r.stderr), (2, b'', b'REJECTED: ROLLOUT_INSPECT_ARTIFACT_IDENTITY\n'))

    def test_missing_input_has_fixed_diagnostic_without_raw_path(self):
        r = self.command(['--case', 'sign-cycle', '--input-root', str(self.root / 'PRIVATE')])
        self.assertEqual((r.returncode, r.stdout, r.stderr), (2, b'', b'REJECTED: ROLLOUT_INSPECT_INPUT\n'))

    def test_unknown_backend_failure_is_fixed_two(self):
        with patch.object(self.api, 'inspect_rollout_case', side_effect=AssertionError('PRIVATE')): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'', 'REJECTED: ROLLOUT_INSPECT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_unknown_backend_status_cannot_print_success(self):
        with patch.object(self.api, 'inspect_rollout_case', return_value={'inspection_status': 'OTHER'}): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'', 'REJECTED: ROLLOUT_INSPECT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_import_failure_restores_caller_globals(self):
        original = builtins.__import__; before = list(sys.path), sys.dont_write_bytecode
        def importing(name, *a, **kw):
            if name == 'integration_tools.core_rollout_inspect': raise ImportError('PRIVATE')
            return original(name, *a, **kw)
        with patch('builtins.__import__', side_effect=importing): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'', 'REJECTED: ROLLOUT_INSPECT_FAILED_NO_MODEL_EXECUTION\n')); self.assertEqual((sys.path, sys.dont_write_bytecode), before)

    def test_baseexception_propagates_after_global_restore(self):
        before = list(sys.path), sys.dont_write_bytecode
        with patch.object(self.api, 'inspect_rollout_case', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt): self.cli.main(self.args())
        self.assertEqual((sys.path, sys.dont_write_bytecode), before)

    def test_cold_no_cache_temp_or_nonstdio_writes(self):
        code = r'''
import builtins, importlib.util, importlib._bootstrap_external as ext, os, sys, tempfile
spec = importlib.util.spec_from_file_location('cold29', sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
original_open, original_write = os.open, os.write
def no(*a, **kw): raise AssertionError('write/cache/temp')
def opening(path, flags, *a, **kw):
    assert flags & os.O_ACCMODE == os.O_RDONLY
    return original_open(path, flags, *a, **kw)
def writing(fd, raw):
    assert fd in (1, 2)
    return original_write(fd, raw)
ext.SourceFileLoader.set_data = no; os.mkdir = no; os.open = opening; os.write = writing
tempfile.gettempdir = no; tempfile.gettempdirb = no; tempfile.TemporaryDirectory = no
tempfile.tempdir = sys.pycache_prefix = sys.argv[2]; sys.dont_write_bytecode = False
before = list(sys.path)
assert m.main(sys.argv[3:]) == 0
assert sys.path == before and sys.dont_write_bytecode is False
assert tempfile.tempdir == sys.pycache_prefix == sys.argv[2]
sys.dont_write_bytecode = True
'''
        folder = self.root / 'sign-cycle'; before = {p.name: p.read_bytes() for p in folder.iterdir()}
        r = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(self.script), str(folder), *self.args()], capture_output=True, cwd=self.root)
        self.assertEqual((r.returncode, r.stderr), (0, b'')); self.assertEqual(json.loads(r.stdout)['new_synthetic_model_steps'], 0)
        self.assertEqual({p.name: p.read_bytes() for p in folder.iterdir()}, before)

    def test_short_stdout_writes_complete_receipt(self):
        original = os.write
        with patch('os.write', side_effect=lambda fd, raw: original(fd, raw[:7])): code, raw, error = self.invoke()
        self.assertEqual((code, error), (0, '')); self.assertEqual(raw, canonical(json.loads(raw)))

    def test_nonpositive_stdout_is_two(self):
        with patch('os.write', return_value=0): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'', 'REJECTED: ROLLOUT_INSPECT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_partial_stdout_failure_is_not_success_or_retractable(self):
        original = os.write; first = True
        def writing(fd, raw):
            nonlocal first
            if first: first = False; return original(fd, raw[:11])
            raise OSError('failed')
        with patch('os.write', side_effect=writing): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'{"actual_ac', 'REJECTED: ROLLOUT_INSPECT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_real_failed_stdout_is_two_and_preserves_inputs(self):
        folder = self.root / 'sign-cycle'; before = {p.name: p.read_bytes() for p in folder.iterdir()}
        with open('/dev/full', 'wb') as sink: r = self.command(stdout=sink)
        self.assertEqual((r.returncode, r.stderr), (2, b'REJECTED: ROLLOUT_INSPECT_FAILED_NO_MODEL_EXECUTION\n'))
        self.assertEqual({p.name: p.read_bytes() for p in folder.iterdir()}, before)

    def test_real_failed_help_is_operational_two(self):
        with open('/dev/full', 'wb') as sink: r = self.command(['--help'], stdout=sink)
        self.assertEqual((r.returncode, r.stderr), (2, b'REJECTED: ROLLOUT_INSPECT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_failed_usage_stderr_keeps_two(self):
        with open('/dev/full', 'wb') as sink: r = self.command([], stderr=sink)
        self.assertEqual((r.returncode, r.stdout), (2, b''))

    def test_closed_or_short_stderr_does_not_escape_error(self):
        class Short(StringIO):
            def write(self, text): return 0
        closed = StringIO(); closed.close()
        for stream in (closed, Short()):
            with self.subTest(stream=type(stream)), patch('sys.stderr', stream): self.assertEqual(self.cli.main(['--case', 'sign-cycle', '--input-root', 'PRIVATE-MISSING']), 2)

    def test_caller_settings_restored_on_success_and_failure(self):
        before = list(sys.path), sys.dont_write_bytecode, sys.pycache_prefix, tempfile.tempdir
        self.assertEqual(self.invoke()[0], 0)
        with patch.object(self.api, 'inspect_rollout_case', side_effect=OSError('PRIVATE')): self.assertEqual(self.invoke()[0], 2)
        self.assertEqual((sys.path, sys.dont_write_bytecode, sys.pycache_prefix, tempfile.tempdir), before)
