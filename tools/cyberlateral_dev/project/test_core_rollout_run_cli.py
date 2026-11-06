"""Explicit run intent, saved rejection vs operation failure, and output custody."""

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

NAMES = {'INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt'}
def canonical(v): return (json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CoreRolloutRunCliTests(unittest.TestCase):
    def setUp(self):
        self.script = ROOT / 'tools/core_rollout_run.py'
        self.assertTrue(self.script.is_file(), 'Missing CORE28 explicit rollout command')
        package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.api: Any = importlib.import_module('integration_tools.core_rollout_run')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name); self.output = self.root / 'output'
        spec = importlib.util.spec_from_file_location('core28_cli_test', self.script)
        assert spec is not None and spec.loader is not None
        self.cli: Any = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.cli)

    def args(self, case='sign-cycle'): return ['--case', case, '--output-root', str(self.output), '--run']
    def command(self, args=None, stdout: Any = subprocess.PIPE, stderr: Any = subprocess.PIPE):
        return subprocess.run([sys.executable, '-I', '-B', str(self.script), *(self.args() if args is None else args)], cwd=self.root, stdout=stdout, stderr=stderr)
    def invoke(self, args=None):
        err = StringIO(); path = self.root / 'stdout.bin'
        with path.open('wb') as out, patch('sys.stdout', out), patch('sys.stderr', err): code = self.cli.main(self.args() if args is None else args)
        return code, path.read_bytes(), err.getvalue()
    def package(self): self.assertEqual({p.name for p in self.output.iterdir()}, NAMES)

    def test_three_cases_exit_zero_one_two_with_complete_publication_receipts(self):
        for case, code, status, steps in (('sign-cycle', 0, 'MATCH', 3), ('declared-difference', 1, 'DIFFERENT', 3), ('late-invalid', 2, 'REJECTED', 0)):
            self.output = self.root / case; r = self.command(self.args(case)); self.assertEqual((r.returncode, r.stderr), (code, b'')); self.package()
            value = json.loads(r.stdout); self.assertEqual(r.stdout, canonical(value))
            self.assertEqual((value['status'], value['result_status'], value['result_exit_code'], value['model_steps']), ('COMPUTED_ROLLOUT_RUN_PUBLISHED', status, code, steps))

    def test_api_and_cli_outputs_are_path_independent_and_identical(self):
        r = self.command(); value = self.api.run_rollout_case('sign-cycle', self.root / 'api')
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, canonical(value), b''))
        for name in NAMES: self.assertEqual((self.output / name).read_bytes(), (self.root / 'api' / name).read_bytes())

    def test_missing_or_duplicate_run_never_imports_project_or_accesses_output(self):
        original = builtins.__import__
        def importing(name, *a, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')): raise AssertionError('project import')
            return original(name, *a, **kw)
        variants = ([], self.args()[:-1], self.args() + ['--run'], self.args() + self.args(),
            ['--case', 'unknown', *self.args()[2:]], self.args() + ['--check'], self.args() + ['--input', 'vehicle'],
            self.args() + ['--archive', 'x'], self.args() + ['--rate-budget-per-s', '0'], self.args() + ['--format', 'json'],
            self.args() + ['positional'], ['--cas', 'sign-cycle', *self.args()[2:]], ['--case', '', *self.args()[2:]])
        for args in variants:
            err, out = StringIO(), StringIO()
            with self.subTest(args=args), patch('builtins.__import__', side_effect=importing), patch('os.open', side_effect=AssertionError('path')), \
                    patch('sys.stderr', err), patch('sys.stdout', out), self.assertRaises(SystemExit) as found: self.cli.main(args)
            self.assertEqual(found.exception.code, 2); self.assertEqual(out.getvalue(), '')
            self.assertEqual(err.getvalue(), 'REJECTED: ROLLOUT_RUN_USAGE_NO_MODEL_EXECUTION\n')
        self.assertFalse(self.output.exists())

    def test_help_does_not_execute_and_explains_required_run(self):
        r = self.command(['--help']); self.assertEqual((r.returncode, r.stderr), (0, b''))
        for text in (b'--run', b'--case', b'--output-root', b'late-invalid'): self.assertIn(text, r.stdout)
        self.assertFalse(self.output.exists())

    def test_existing_folder_fixed_error_and_zero_backend_calls(self):
        self.output.mkdir(); (self.output / 'sentinel').write_bytes(b'keep')
        with patch.object(self.api, 'build_case', side_effect=AssertionError('factory')): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'', 'REJECTED: ARCHIVE_WORKFLOW_OUTPUT_EXISTS\n'))
        self.assertEqual((self.output / 'sentinel').read_bytes(), b'keep')

    def test_real_rerun_never_overwrites_completed_output(self):
        self.assertEqual(self.command().returncode, 0); before = {p.name: p.read_bytes() for p in self.output.iterdir()}
        r = self.command(); self.assertEqual((r.returncode, r.stdout, r.stderr), (2, b'', b'REJECTED: ARCHIVE_WORKFLOW_OUTPUT_EXISTS\n'))
        self.assertEqual({p.name: p.read_bytes() for p in self.output.iterdir()}, before)

    def test_execution_failure_not_saved_as_intentional_rejection(self):
        error = self.api.SequenceRolloutError('ROLLOUT_MODEL_FAILURE:1:WORK_MAY_BE_NONZERO')
        with patch.object(self.api, 'rollout_synthetic_sequence', side_effect=error): code, raw, text = self.invoke()
        self.assertEqual((code, raw, text), (2, b'', 'REJECTED: ROLLOUT_RUN_EXECUTION_FAILED_WORK_MAY_BE_NONZERO\n')); self.assertFalse(self.output.exists())

    def test_publication_failure_has_work_uncertainty_and_keeps_partial_data(self):
        publisher = importlib.import_module('integration_tools.core_sequence_archive_workflow'); original = publisher._write
        def writing(directory, name, raw):
            if name == 'RESULTS.json': raise OSError('PRIVATE')
            return original(directory, name, raw)
        with patch.object(publisher, '_write', side_effect=writing): code, raw, error = self.invoke()
        self.assertEqual((code, raw), (2, b'')); self.assertIn('ROLLOUT_RUN_PUBLICATION:', error); self.assertIn('WORK_MAY_BE_NONZERO', error); self.assertNotIn('PRIVATE', error)
        self.assertEqual({p.name for p in self.output.iterdir()}, {'INPUT.json'})

    def test_unexpected_backend_failure_has_fixed_diagnostic(self):
        with patch.object(self.api, 'run_rollout_case', side_effect=AssertionError('PRIVATE')): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'', 'REJECTED: ROLLOUT_RUN_FAILED_WORK_MAY_BE_NONZERO_DIRECTORY_MAY_EXIST\n'))

    def test_unknown_backend_status_cannot_be_false_success(self):
        with patch.object(self.api, 'run_rollout_case', return_value={'result_status': 'UNKNOWN'}): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'', 'REJECTED: ROLLOUT_RUN_FAILED_WORK_MAY_BE_NONZERO_DIRECTORY_MAY_EXIST\n'))

    def test_import_failure_restores_flags_and_does_not_publish(self):
        original = builtins.__import__; before = list(sys.path), sys.dont_write_bytecode
        def importing(name, *a, **kw):
            if name == 'integration_tools.core_rollout_run': raise ImportError('PRIVATE')
            return original(name, *a, **kw)
        with patch('builtins.__import__', side_effect=importing): code, raw, error = self.invoke()
        self.assertEqual(code, 2); self.assertEqual(raw, b''); self.assertNotIn('PRIVATE', error)
        self.assertEqual((sys.path, sys.dont_write_bytecode), before); self.assertFalse(self.output.exists())

    def test_baseexception_propagates_after_caller_settings_restore(self):
        before = list(sys.path), sys.dont_write_bytecode
        with patch.object(self.api, 'run_rollout_case', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt): self.cli.main(self.args())
        self.assertEqual((sys.path, sys.dont_write_bytecode), before)

    def test_cold_call_only_writes_explicit_three_files_without_cache_or_temp(self):
        code = r'''
import builtins, importlib.util, importlib._bootstrap_external as ext, os, sys, tempfile
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('cold28', sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
assert 'locale' not in sys.modules
original_import = builtins.__import__; flags = []; original_open = os.open; original_mkdir = os.mkdir; paths = {}; counts = {'model':0,'writes':0,'mkdir':0}
target = os.path.abspath(sys.argv[2]); names = {'INPUT.json','RESULTS.json','SHA256SUMS.txt'}
def no(*a, **kw): raise AssertionError('temp/cache')
def importing(name, *a, **kw):
    if name == 'locale': flags.append(sys.dont_write_bytecode)
    return original_import(name, *a, **kw)
def opening(path, flag, *a, **kw):
    if flag & os.O_ACCMODE != os.O_RDONLY:
        assert path in names and flag & os.O_EXCL and flag & os.O_NOFOLLOW; counts['writes'] += 1
    return original_open(path, flag, *a, **kw)
def mkdir(path,*a,**kw):
    assert os.path.abspath(path) == target; counts['mkdir'] += 1; return original_mkdir(path,*a,**kw)
def profile(frame,event,arg):
    if event == 'call' and frame.f_globals.get('__name__') == 'cyberlateral_dev.api' and frame.f_code.co_name == 'step': counts['model'] += 1
ext.SourceFileLoader.set_data = no; os.mkdir = mkdir; os.open = opening
tempfile.gettempdir = no; tempfile.gettempdirb = no; tempfile.TemporaryDirectory = no
tempfile.tempdir = sys.argv[2]; sys.pycache_prefix = sys.argv[2]; builtins.__import__ = importing
sys.dont_write_bytecode = False; before = list(sys.path); sys.setprofile(profile)
try: result = m.main(sys.argv[3:])
finally: sys.setprofile(None)
assert result == 0 and sys.path == before and sys.dont_write_bytecode is False and flags and all(flags)
assert counts == {'model':3,'writes':3,'mkdir':1}; assert tempfile.tempdir == sys.pycache_prefix == sys.argv[2]
sys.dont_write_bytecode = True
'''
        r = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(self.script), str(self.output), *self.args()], capture_output=True, cwd=self.root)
        self.assertEqual((r.returncode, r.stderr), (0, b'')); self.assertEqual(json.loads(r.stdout)['model_steps'], 3); self.package()

    def test_short_stdout_delivers_complete_canonical_receipt(self):
        original = os.write
        with patch('os.write', side_effect=lambda fd, raw: original(fd, raw[:7])): code, raw, error = self.invoke()
        self.assertEqual((code, error), (0, '')); self.assertEqual(raw, canonical(json.loads(raw))); self.package()

    def test_nonpositive_stdout_after_publication_is_two_with_complete_files(self):
        original = os.write
        def writing(fd, raw):
            if os.fstat(fd).st_ino == (self.root / 'stdout.bin').stat().st_ino: return 0
            return original(fd, raw)
        with patch('os.write', side_effect=writing): code, raw, error = self.invoke()
        self.assertEqual((code, raw), (2, b'')); self.assertIn('WORK_MAY_BE_NONZERO_DIRECTORY_MAY_EXIST', error); self.package()

    def test_partial_stdout_failure_preserves_prefix_and_complete_files(self):
        original = os.write; first = True
        def writing(fd, raw):
            nonlocal first
            if os.fstat(fd).st_ino != (self.root / 'stdout.bin').stat().st_ino: return original(fd, raw)
            if first: first = False; return original(fd, raw[:11])
            raise OSError('failed')
        with patch('os.write', side_effect=writing): code, raw, error = self.invoke()
        self.assertEqual((code, raw), (2, b'{"actual_ac')); self.assertIn('WORK_MAY_BE_NONZERO_DIRECTORY_MAY_EXIST', error); self.package()

    def test_real_dev_full_stdout_is_two_after_complete_publication(self):
        with open('/dev/full', 'wb') as sink: r = self.command(stdout=sink, stderr=subprocess.PIPE)
        self.assertEqual((r.returncode, r.stderr), (2, b'REJECTED: ROLLOUT_RUN_FAILED_WORK_MAY_BE_NONZERO_DIRECTORY_MAY_EXIST\n')); self.package()

    def test_failed_help_and_usage_streams_are_operational_two_without_model(self):
        with open('/dev/full', 'wb') as sink:
            help_result = self.command(['--help'], stdout=sink, stderr=subprocess.PIPE)
            usage_result = self.command([], stdout=subprocess.PIPE, stderr=sink)
        self.assertEqual(help_result.returncode, 2); self.assertEqual((usage_result.returncode, usage_result.stdout), (2, b'')); self.assertFalse(self.output.exists())

    def test_closed_or_short_stderr_does_not_escape_or_change_two(self):
        closed = StringIO(); closed.close()
        with patch('sys.stderr', closed): self.assertEqual(self.cli.main(self.args()[:-1]), 2)
        class Short(StringIO):
            def write(self, text): return 0
        with patch('sys.stderr', Short()): self.assertEqual(self.cli.main(self.args()[:-1]), 2)

    def test_globals_and_temp_settings_unchanged_on_success(self):
        before = list(sys.path), sys.dont_write_bytecode, sys.pycache_prefix, tempfile.tempdir
        self.assertEqual(self.invoke()[0], 0); self.assertEqual((sys.path, sys.dont_write_bytecode, sys.pycache_prefix, tempfile.tempdir), before)

    def test_denial_gates_are_present_in_cli_and_saved_results(self):
        r = self.command(); value = json.loads(r.stdout); saved = json.loads((self.output / 'RESULTS.json').read_bytes())
        for record in (value, saved):
            self.assertFalse(record['f61_input_allowed']); self.assertFalse(record['actual_activation_allowed'])
            self.assertEqual(record['gates']['R_BUDGET'], 'UNRESOLVED'); self.assertEqual(record['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
