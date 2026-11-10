"""Explicit fixed-suite CLI: no accidental execution, cache writes or false output success."""

import builtins
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


class CoreReferenceSuiteCliTests(unittest.TestCase):
    def setUp(self):
        self.script = ROOT / 'tools/core_reference_suite.py'
        self.assertTrue(self.script.is_file(), 'Missing CORE32 reference suite command')
        self.model = package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.api: Any = importlib.import_module('integration_tools.core_reference_suite')
        spec = importlib.util.spec_from_file_location('core32_cli_test', self.script)
        assert spec is not None and spec.loader is not None
        self.cli: Any = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.cli)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)

    def command(self, args=None, stdout: Any = subprocess.PIPE, stderr: Any = subprocess.PIPE):
        return subprocess.run([sys.executable, '-I', '-B', str(self.script), *(['--run'] if args is None else args)], cwd=self.root, stdout=stdout, stderr=stderr)
    def invoke(self, args=None):
        err = StringIO(); target = self.root / 'stdout.bin'
        with target.open('wb') as out, patch('sys.stdout', out), patch('sys.stderr', err): code = self.cli.main(['--run'] if args is None else args)
        return code, target.read_bytes(), err.getvalue()

    def test_normal_command_zero_preserves_expected_different_and_rejected_cases(self):
        r = self.command(); self.assertEqual((r.returncode, r.stderr), (0, b'')); v = json.loads(r.stdout)
        self.assertEqual(v['audit_counts'], {'MATCH': 6, 'DIFFERENT': 0}); self.assertEqual(v['observed_rollout_counts'], {'MATCH': 4, 'DIFFERENT': 1, 'REJECTED': 1})
        self.assertEqual(v['reported_synthetic_model_steps'], 19)

    def test_api_and_direct_cli_bytes_are_identical(self):
        from integration_tools.scenario_output import canonical
        self.assertEqual(self.command().stdout, canonical(self.api.run_reference_suite()))

    def test_real_mismatch_returns_one_with_complete_six_case_report(self):
        original = self.model.step
        def changed(sample, state):
            o = original(sample, state); return replace(o, projection=replace(o.projection, status='CORRUPTED'))
        with patch.object(self.model, 'step', side_effect=changed): code, raw, error = self.invoke()
        self.assertEqual((code, error), (1, '')); v = json.loads(raw)
        self.assertEqual((v['case_count'], v['difference_count'], v['audit_counts']), (6, 19, {'MATCH': 1, 'DIFFERENT': 5}))

    def test_syntax_rejected_before_project_import_or_reference_work(self):
        original = builtins.__import__
        def importing(name, *a, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')): raise AssertionError('project')
            return original(name, *a, **kw)
        for args in ([], ['--run', '--run'], ['--ru'], ['--run=1'], ['--run', 'x'], ['--run', '--case', 'sign-cycle'],
                     ['--run', '--input-root', 'x'], ['--run', '--output', 'x'], ['--run', '--rate-budget-per-s', '0'], ['--run', '--format', 'json']):
            err, out = StringIO(), StringIO()
            with self.subTest(args=args), patch('builtins.__import__', side_effect=importing), patch('os.open', side_effect=AssertionError('read')), patch('sys.stderr', err), patch('sys.stdout', out), self.assertRaises(SystemExit) as found: self.cli.main(args)
            self.assertEqual(found.exception.code, 2); self.assertEqual(out.getvalue(), ''); self.assertEqual(err.getvalue(), 'REJECTED: REFERENCE_SUITE_USAGE_NO_MODEL_EXECUTION\n')

    def test_help_precedes_reference_and_model_execution(self):
        r = self.command(['--help']); self.assertEqual((r.returncode, r.stderr), (0, b'')); self.assertIn(b'--run', r.stdout)
        with patch('os.open', side_effect=AssertionError('read')), patch('sys.stdout', StringIO()), self.assertRaises(SystemExit) as found: self.cli.main(['--help'])
        self.assertEqual(found.exception.code, 0)

    def test_known_failure_keeps_fixed_code_and_no_success_json(self):
        with patch.object(self.api, 'run_reference_suite', side_effect=self.api.ReferenceSuiteError('REFERENCE_SUITE_CASE_FAILED:CORE30:sign-cycle:WORK_MAY_BE_NONZERO')): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'', 'REJECTED: REFERENCE_SUITE_CASE_FAILED:CORE30:sign-cycle:WORK_MAY_BE_NONZERO\n'))

    def test_unknown_backend_failure_is_fixed_nonzero_work_diagnostic(self):
        with patch.object(self.api, 'run_reference_suite', side_effect=AssertionError('PRIVATE')): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'', 'REJECTED: REFERENCE_SUITE_FAILED_WORK_MAY_BE_NONZERO\n'))

    def test_unknown_backend_status_cannot_print_success(self):
        with patch.object(self.api, 'run_reference_suite', return_value={'suite_status': 'OTHER'}): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'', 'REJECTED: REFERENCE_SUITE_FAILED_WORK_MAY_BE_NONZERO\n'))

    def test_import_error_restores_caller_path_and_bytecode_flag(self):
        original = builtins.__import__; before = list(sys.path), sys.dont_write_bytecode
        def importing(name, *a, **kw):
            if name == 'integration_tools.core_reference_suite': raise ImportError('PRIVATE')
            return original(name, *a, **kw)
        with patch('builtins.__import__', side_effect=importing): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'', 'REJECTED: REFERENCE_SUITE_FAILED_WORK_MAY_BE_NONZERO\n')); self.assertEqual((sys.path, sys.dont_write_bytecode), before)

    def test_baseexception_propagates_after_restoring_globals(self):
        before = list(sys.path), sys.dont_write_bytecode
        with patch.object(self.api, 'run_reference_suite', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt): self.cli.main(['--run'])
        self.assertEqual((sys.path, sys.dont_write_bytecode), before)

    def test_cold_run_has_no_cache_temp_or_nonstdio_writes(self):
        code = r'''
import importlib.util, importlib._bootstrap_external as ext, os, sys, tempfile
spec = importlib.util.spec_from_file_location('cold32', sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
real_open, real_write = os.open, os.write
def no(*a, **kw): raise AssertionError('write/temp/cache')
def opening(path, flags, *a, **kw):
    assert flags & os.O_ACCMODE == os.O_RDONLY
    return real_open(path, flags, *a, **kw)
def writing(fd, raw):
    assert fd in (1, 2)
    return real_write(fd, raw)
os.open = opening; os.write = writing; os.mkdir = no; ext.SourceFileLoader.set_data = no
tempfile.gettempdir = no; tempfile.gettempdirb = no; tempfile.TemporaryDirectory = no
tempfile.tempdir = sys.pycache_prefix = sys.argv[2]; sys.dont_write_bytecode = False
before = list(sys.path)
assert m.main(['--run']) == 0
assert sys.path == before and sys.dont_write_bytecode is False
assert tempfile.tempdir == sys.pycache_prefix == sys.argv[2]
sys.dont_write_bytecode = True
'''
        r = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(self.script), str(self.root)], capture_output=True, cwd=self.root)
        self.assertEqual((r.returncode, r.stderr), (0, b'')); self.assertEqual(json.loads(r.stdout)['suite_exit_code'], 0)

    def test_short_stdout_writes_deliver_full_canonical_json(self):
        from integration_tools.scenario_output import canonical
        original = os.write
        with patch('os.write', side_effect=lambda fd, raw: original(fd, raw[:7])): code, raw, error = self.invoke()
        self.assertEqual((code, error), (0, '')); self.assertEqual(raw, canonical(json.loads(raw)))

    def test_nonpositive_stdout_is_operational_two(self):
        with patch('os.write', return_value=0): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'', 'REJECTED: REFERENCE_SUITE_FAILED_WORK_MAY_BE_NONZERO\n'))

    def test_partial_stdout_failure_is_two_and_not_retractable(self):
        original = os.write; first = True
        def writing(fd, raw):
            nonlocal first
            if first: first = False; return original(fd, raw[:11])
            raise OSError('PRIVATE')
        with patch('os.write', side_effect=writing): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'{"actual_ac', 'REJECTED: REFERENCE_SUITE_FAILED_WORK_MAY_BE_NONZERO\n'))

    def test_real_full_stdout_fails_without_false_success(self):
        with open('/dev/full', 'wb') as sink: r = self.command(stdout=sink)
        self.assertEqual((r.returncode, r.stderr), (2, b'REJECTED: REFERENCE_SUITE_FAILED_WORK_MAY_BE_NONZERO\n'))

    def test_failed_help_is_operational_two(self):
        with open('/dev/full', 'wb') as sink: r = self.command(['--help'], stdout=sink)
        self.assertEqual((r.returncode, r.stderr), (2, b'REJECTED: REFERENCE_SUITE_FAILED_WORK_MAY_BE_NONZERO\n'))

    def test_failed_usage_stderr_keeps_two(self):
        with open('/dev/full', 'wb') as sink: r = self.command([], stderr=sink)
        self.assertEqual((r.returncode, r.stdout), (2, b''))

    def test_closed_and_short_error_streams_do_not_escape_failure(self):
        class Short(StringIO):
            def write(self, text): return 0
        closed = StringIO(); closed.close()
        for stream in (closed, Short()):
            with patch('sys.stderr', stream): self.assertEqual(self.cli.main(['--run', '--invalid']), 2)

    def test_caller_settings_restore_on_success_and_failure(self):
        before = list(sys.path), sys.dont_write_bytecode, tempfile.tempdir, sys.pycache_prefix
        self.assertEqual(self.invoke()[0], 0)
        with patch.object(self.api, 'run_reference_suite', side_effect=ValueError('PRIVATE')): self.assertEqual(self.invoke()[0], 2)
        self.assertEqual((sys.path, sys.dont_write_bytecode, tempfile.tempdir, sys.pycache_prefix), before)
