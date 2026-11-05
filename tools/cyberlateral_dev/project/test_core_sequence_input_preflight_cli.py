"""CORE19 wrapper bytes, exit semantics and cold no-cache command boundaries."""

import builtins
import hashlib
import importlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


def canonical(value): return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CorePreflightCliTests(unittest.TestCase):
    def setUp(self):
        self.script = ROOT / 'tools/core_sequence_input_preflight.py'
        self.assertTrue(self.script.is_file(), 'Missing CORE20 preflight CLI')
        package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.api: Any = importlib.import_module('integration_tools.core_sequence_input_preflight')
        self.producer = importlib.import_module('integration_tools.core_sequence_run')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        self.folder = self.root / 'packet'; self.producer.run_sequence_case('sign-cycle', self.folder)
        spec = importlib.util.spec_from_file_location('core20_test_cli', self.script)
        assert spec is not None and spec.loader is not None
        self.cli: Any = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.cli)

    def args(self): return ['--input-root', str(self.folder)]
    def command(self, args=None):
        return subprocess.run([sys.executable, '-I', '-B', str(self.script), *(self.args() if args is None else args)], capture_output=True, cwd=self.root)
    def expected(self): return canonical(self.api.preflight_saved_sequence(self.folder))
    def snapshot(self): return {p.name: (p.read_bytes(), p.stat().st_mode) for p in self.folder.iterdir()}
    def edit(self, filename, change):
        path = self.folder / filename; value = json.loads(path.read_bytes()); change(value); path.write_bytes(canonical(value))
        (self.folder / 'SHA256SUMS.txt').write_bytes(''.join(hashlib.sha256((self.folder / n).read_bytes()).hexdigest() + '  ' + n + '\n' for n in ('INPUT.json', 'RESULTS.json')).encode())
    def invoke(self, args=None):
        err = StringIO(); path = self.root / 'stdout.bin'
        with path.open('wb') as out, patch('sys.stdout', out), patch('sys.stderr', err): code = self.cli.main(self.args() if args is None else args)
        return code, path.read_bytes(), err.getvalue()

    def test_three_cases_emit_exact_api_receipts_with_current_verdict_exits(self):
        for case, status, code in (('sign-cycle', 'MATCH', 0), ('declared-difference', 'DIFFERENT', 0), ('late-invalid', 'REJECTED', 1)):
            folder = self.root / case; self.producer.run_sequence_case(case, folder)
            result = self.command(['--input-root', str(folder)])
            self.assertEqual(result.returncode, code, result.stderr); self.assertEqual(result.stderr, b'')
            self.assertEqual(result.stdout, canonical(self.api.preflight_saved_sequence(folder)))
            self.assertEqual(json.loads(result.stdout)['saved_status'], status)

    def test_valid_input_with_historical_rejection_still_exits_zero(self):
        self.edit('RESULTS.json', lambda r: r.update(status='REJECTED', rejection_code='SEQUENCE_INPUT:2:MODEL_DRIVER', sequence_completed=False,
            model_steps=0, completed_transition_count=0, rows=[], differing_transition_indices=[]))
        result = self.command(); self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['saved_status'], 'REJECTED'); self.assertEqual(result.stdout, self.expected())

    def test_coherent_match_with_invalid_driver_emits_rejection_receipt_exit_one(self):
        self.edit('INPUT.json', lambda r: r['contexts'][0].update(current_driver_hex=(0.1).hex()))
        result = self.command(); self.assertEqual(result.returncode, 1, result.stderr); self.assertEqual(result.stdout, self.expected())
        value = json.loads(result.stdout); self.assertEqual(value['saved_status'], 'MATCH')
        self.assertEqual(value['rejection_code'], 'SEQUENCE_INPUT:0:MODEL_DRIVER')

    def test_checksum_failure_is_exit_two_without_receipt_or_input_path(self):
        (self.folder / 'SHA256SUMS.txt').write_bytes(b'wrong'); result = self.command()
        self.assertEqual(result.returncode, 2); self.assertEqual(result.stdout, b'')
        self.assertEqual(result.stderr, b'REJECTED: INPUT_PREFLIGHT_SAVED:INSPECT_CHECKSUM\n'); self.assertNotIn(str(self.folder).encode(), result.stderr)

    def test_invalid_syntax_precedes_project_imports_and_input_access(self):
        original = builtins.__import__
        def importing(name, *a, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')): raise AssertionError('project import')
            return original(name, *a, **kw)
        variants = ([], ['--input', str(self.folder)], self.args() + ['--run'], self.args() + ['--output-root', 'DO_NOT_ECHO'],
            self.args() + ['--rate-budget-per-s', '0'], self.args() + ['--format', 'json'], self.args() + self.args(), ['--input-root', ''])
        for args in variants:
            err, out = StringIO(), StringIO()
            with self.subTest(args=args), patch('builtins.__import__', side_effect=importing), patch('os.open', side_effect=AssertionError('input open')), \
                    patch('sys.stderr', err), patch('sys.stdout', out), self.assertRaises(SystemExit) as found:
                self.cli.main(args)
            self.assertEqual(found.exception.code, 2); self.assertEqual(out.getvalue(), '')
            self.assertEqual(err.getvalue(), 'REJECTED: INPUT_PREFLIGHT_USAGE_NO_MODEL_EXECUTION\n')

    def test_help_never_imports_api_or_inspects_input_and_restores_globals(self):
        original = builtins.__import__; before = list(sys.path)
        def importing(name, *a, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')): raise AssertionError('project import')
            return original(name, *a, **kw)
        out = StringIO()
        with patch.object(sys, 'dont_write_bytecode', False), patch('builtins.__import__', side_effect=importing), \
                patch('os.open', side_effect=AssertionError('input open')), patch('sys.stdout', out), self.assertRaises(SystemExit) as found:
            try: self.cli.main(['--help'])
            finally: self.assertFalse(sys.dont_write_bytecode); self.assertEqual(sys.path, before)
        self.assertEqual(found.exception.code, 0); self.assertIn('--input-root', out.getvalue())

    def test_unrelated_cwd_and_space_containing_path_work(self):
        self.folder.rename(self.root / 'packet with spaces'); self.folder = self.root / 'packet with spaces'
        result = self.command(); self.assertEqual(result.returncode, 0, result.stderr); self.assertEqual(result.stdout, self.expected())

    def test_readonly_bytes_modes_layout_are_unchanged(self):
        for p in self.folder.iterdir(): p.chmod(0o444)
        self.folder.chmod(0o555); before = self.snapshot(); result = self.command()
        self.assertEqual(result.returncode, 0, result.stderr); self.assertEqual(before, self.snapshot())

    def test_exactly_three_regular_files_captured_readonly(self):
        original = os.open; opened = []; paths = {}
        def observe(path, flags, *a, **kw):
            self.assertFalse(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
            target = paths[kw['dir_fd']] / path if kw.get('dir_fd') in paths else Path(path).absolute()
            fd = original(path, flags, *a, **kw); paths[fd] = target
            if stat.S_ISREG(os.fstat(fd).st_mode): opened.append(target.name)
            return fd
        with patch('os.open', side_effect=observe): code, raw, err = self.invoke()
        self.assertEqual((code, err), (0, '')); self.assertEqual(raw, self.expected())
        self.assertEqual(sorted(opened), ['INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt'])

    def test_producer_reference_f61_imports_and_model_step_are_blocked(self):
        script = '''import importlib.abc,runpy,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  modules=('integration_tools.core_sequence_run','integration_tools.synthetic_sequence_check','integration_tools.synthetic_transition_check','integration_tools.sequence_reference','integration_tools.fixed_model_reference','numpy','openpilot','opendbc')
  if any(fullname==m or fullname.startswith(m+'.') for m in modules) or fullname.startswith('integration_tools.f61_'): raise AssertionError('forbidden import:'+fullname)
def profile(frame,event,arg):
 if event=='call' and frame.f_globals.get('__name__','').startswith('cyberlateral_dev') and frame.f_code.co_name in ('step','step_normalized'): raise AssertionError('model executed')
sys.meta_path.insert(0,Block());sys.setprofile(profile);sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(self.script), *self.args()], capture_output=True, cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr); self.assertEqual(result.stdout, self.expected())

    def test_temp_settings_under_input_never_probe_or_allocate_cache(self):
        before = self.snapshot(); prefix = sys.pycache_prefix
        with patch.dict(os.environ, {k: str(self.folder) for k in ('TMPDIR', 'TEMP', 'TMP')}), patch.object(tempfile, 'tempdir', str(self.folder)), \
                patch.object(tempfile, 'gettempdir', side_effect=AssertionError('temp probe')), patch.object(tempfile, 'gettempdirb', side_effect=AssertionError('temp probe')), \
                patch.object(tempfile, 'TemporaryDirectory', side_effect=AssertionError('cache allocation')):
            code, raw, err = self.invoke(); self.assertEqual(tempfile.tempdir, str(self.folder))
            self.assertTrue(all(os.environ[k] == str(self.folder) for k in ('TMPDIR', 'TEMP', 'TMP')))
        self.assertEqual((code, err), (0, '')); self.assertEqual(raw, self.expected()); self.assertEqual(before, self.snapshot()); self.assertEqual(sys.pycache_prefix, prefix)

    def test_cold_main_suppresses_parser_and_api_bytecode_with_prefix_inside_input(self):
        script = '''import sys
sys.dont_write_bytecode=True
import importlib.util
import importlib._bootstrap_external as external
import builtins,os,tempfile
from pathlib import Path
source,folder,*args=sys.argv[1:];root=Path(folder);writes=[];mkdirs=[];locale_flags=[]
spec=importlib.util.spec_from_file_location('cold_core20',source);cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
assert 'locale' not in sys.modules,'child preloaded locale'
real_import=builtins.__import__;real_mkdir=os.mkdir
def importing(name,*a,**kw):
 if name=='locale':locale_flags.append(sys.dont_write_bytecode)
 return real_import(name,*a,**kw)
def store(self,path,data,**kw):writes.append(path)
def mkdir(path,*a,**kw):
 if Path(path).absolute().is_relative_to(root):mkdirs.append(str(path));raise OSError('input mkdir')
 return real_mkdir(path,*a,**kw)
def probe(*a,**kw):raise AssertionError('temp probe/allocation')
external.SourceFileLoader.set_data=store;os.mkdir=mkdir;builtins.__import__=importing
tempfile.gettempdir=probe;tempfile.gettempdirb=probe;tempfile.TemporaryDirectory=probe;tempfile.tempdir=folder
for key in ('TMPDIR','TEMP','TMP'):os.environ[key]=folder
before=list(sys.path);sys.pycache_prefix=folder;sys.dont_write_bytecode=False
code=cli.main(args)
assert not writes and not mkdirs,(writes,mkdirs)
assert locale_flags and all(locale_flags),locale_flags
assert sys.pycache_prefix==folder and sys.dont_write_bytecode is False and sys.path==before,'globals leaked'
assert tempfile.tempdir==folder and all(os.environ[k]==folder for k in ('TMPDIR','TEMP','TMP'))
sys.dont_write_bytecode=True
raise SystemExit(code)
'''
        before = self.snapshot()
        for invalid in (False, True):
            args = ['--input-root', str(self.root / 'absent')] if invalid else self.args()
            result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(self.script), str(self.folder), *args], capture_output=True)
            self.assertEqual(result.returncode, 2 if invalid else 0, result.stderr)
            self.assertEqual(result.stdout, b'' if invalid else self.expected())
        self.assertEqual(before, self.snapshot())

    def test_success_and_api_failure_restore_source_paths_and_bytecode_flag(self):
        before = self.snapshot(); prefix = sys.pycache_prefix
        for failed in (False, True):
            with patch.object(sys, 'dont_write_bytecode', False), patch.object(sys, 'path', [*sys.path, 'caller-path-marker']):
                paths = list(sys.path)
                if failed:
                    with patch.object(self.api, 'preflight_saved_sequence', side_effect=RuntimeError('SECRET_INPUT_TEXT')): code, raw, err = self.invoke()
                else: code, raw, err = self.invoke()
                self.assertFalse(sys.dont_write_bytecode); self.assertEqual(sys.path, paths); self.assertEqual(sys.pycache_prefix, prefix)
            self.assertEqual(code, 2 if failed else 0)
            if failed: self.assertEqual(raw, b''); self.assertEqual(err, 'REJECTED: INPUT_PREFLIGHT_FAILED_NO_MODEL_EXECUTION\n')
        self.assertEqual(before, self.snapshot())

    def test_import_failure_has_fixed_exit_two_and_restores_globals(self):
        original = builtins.__import__; paths = list(sys.path)
        def importing(name, *a, **kw):
            if name == 'integration_tools.core_sequence_input_preflight': raise ImportError('SECRET_IMPORT_TEXT')
            return original(name, *a, **kw)
        with patch.object(sys, 'dont_write_bytecode', False), patch('builtins.__import__', side_effect=importing):
            code, raw, err = self.invoke(); self.assertFalse(sys.dont_write_bytecode); self.assertEqual(sys.path, paths)
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: INPUT_PREFLIGHT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_unknown_api_status_never_becomes_a_semantic_rejection(self):
        record = self.api.preflight_saved_sequence(self.folder); record['preflight_status'] = 'UNKNOWN'
        with patch.object(self.api, 'preflight_saved_sequence', return_value=record): code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: INPUT_PREFLIGHT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_serialization_failure_emits_no_partial_receipt(self):
        output = importlib.import_module('integration_tools.scenario_output')
        with patch.object(output, 'canonical', side_effect=ValueError('SECRET_RECORD_TEXT')): code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: INPUT_PREFLIGHT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_short_stdout_writes_complete_the_same_receipt(self):
        original = os.write
        def short(fd, raw): return original(fd, raw[:7])
        with patch('os.write', side_effect=short): code, raw, err = self.invoke()
        self.assertEqual((code, err), (0, '')); self.assertEqual(raw, self.expected())

    def test_nonpositive_stdout_write_fails_immediately_without_retry(self):
        for value in (0, -1):
            calls = []
            def write(fd, raw, value=value, calls=calls): calls.append(1); return value
            with self.subTest(value=value), patch('os.write', side_effect=write): code, raw, err = self.invoke()
            self.assertEqual(calls, [1]); self.assertEqual((code, raw, err), (2, b'', 'REJECTED: INPUT_PREFLIGHT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_stdout_failure_restores_flags_without_changing_input(self):
        before = self.snapshot(); paths = list(sys.path)
        with patch.object(sys, 'dont_write_bytecode', False), patch('os.write', side_effect=OSError('SECRET_STDOUT_TEXT')):
            code, raw, err = self.invoke(); self.assertFalse(sys.dont_write_bytecode); self.assertEqual(sys.path, paths)
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: INPUT_PREFLIGHT_FAILED_NO_MODEL_EXECUTION\n')); self.assertEqual(before, self.snapshot())

    def test_partial_stdout_failure_is_exit_two_and_cannot_retract_prefix(self):
        expected = self.expected(); original = os.write; calls = []
        def write(fd, raw):
            calls.append(1)
            if len(calls) > 1: raise OSError('later failure')
            return original(fd, raw[:11])
        with patch('os.write', side_effect=write): code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, expected[:11], 'REJECTED: INPUT_PREFLIGHT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_baseexception_propagates_after_restoring_globals(self):
        paths = list(sys.path)
        with patch.object(sys, 'dont_write_bytecode', False), patch.object(self.api, 'preflight_saved_sequence', side_effect=KeyboardInterrupt), \
                self.assertRaises(KeyboardInterrupt):
            try: self.invoke()
            finally: self.assertFalse(sys.dont_write_bytecode); self.assertEqual(sys.path, paths)

    def test_missing_symlink_and_invalid_path_text_have_fixed_file_errors(self):
        alias = self.root / 'alias'; alias.symlink_to(self.folder, target_is_directory=True)
        for path in (str(self.root / 'absent'), str(alias), 'bad\0path', 'bad\ud800path'):
            code, raw, err = self.invoke(['--input-root', path])
            self.assertEqual((code, raw, err), (2, b'', 'REJECTED: INPUT_PREFLIGHT_SAVED:INSPECT_INPUT_FILE\n'))

    def test_successful_command_leaves_policy_and_calculator_gates_closed(self):
        result = self.command(); value = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((value['new_synthetic_model_steps'], value['new_reference_steps']), (0, 0))
        self.assertEqual(value['numeric_validation_work'], 'NONZERO_NOT_AGGREGATED')
        self.assertEqual(value['gates']['R_BUDGET'], 'UNRESOLVED'); self.assertEqual(value['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
        self.assertIs(value['f61_input_allowed'], False); self.assertIs(value['actual_activation_allowed'], False)
