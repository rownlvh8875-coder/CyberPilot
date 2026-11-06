"""Single publication command, current verdict exits and post-write failure honesty."""

import builtins
import hashlib
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
NAMES = {'PREFLIGHT.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt'}
def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(v): return (json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CorePreflightWorkflowCliTests(unittest.TestCase):
    def setUp(self):
        self.script = ROOT / 'tools/core_sequence_preflight_workflow.py'
        self.assertTrue(self.script.is_file(), 'Missing CORE25 publication command')
        package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.api: Any = importlib.import_module('integration_tools.core_sequence_preflight_workflow')
        self.report: Any = importlib.import_module('integration_tools.core_sequence_preflight_report')
        self.bundle = importlib.import_module('integration_tools.core_sequence_bundle')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        producer = importlib.import_module('integration_tools.core_sequence_run'); self.source = {}
        for c in CASES:
            p = self.root / c; producer.run_sequence_case(c, p)
            self.source.update({'suite/' + c + '/' + n: (p / n).read_bytes() for n in ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt')})
        self.raw = self.bundle.build_suite_archive(self.source); self.archive = self.root / 'input.zip'; self.archive.write_bytes(self.raw)
        self.output = self.root / 'output'; self.stdout_fd = None
        spec = importlib.util.spec_from_file_location('core25_cli_test', self.script)
        assert spec is not None and spec.loader is not None
        self.cli: Any = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.cli)

    def args(self): return ['--archive', str(self.archive), '--sha256', sha(self.raw), '--output-root', str(self.output)]
    def command(self, args=None): return subprocess.run([sys.executable, '-I', '-B', str(self.script), *(self.args() if args is None else args)], capture_output=True, cwd=self.root)
    def invoke(self, args=None):
        err = StringIO(); p = self.root / 'stdout.bin'
        with p.open('wb') as out, patch('sys.stdout', out), patch('sys.stderr', err):
            self.stdout_fd = out.fileno(); code = self.cli.main(self.args() if args is None else args)
        return code, p.read_bytes(), err.getvalue()
    def changed(self, changes):
        files = dict(self.source)
        for c, change in changes:
            prefix = 'suite/' + c + '/'; r = json.loads(files[prefix + 'INPUT.json']); change(r)
            files[prefix + 'INPUT.json'] = canonical(r)
            files[prefix + 'SHA256SUMS.txt'] = ''.join(sha(files[prefix + n]) + '  ' + n + '\n' for n in ('INPUT.json', 'RESULTS.json')).encode()
        self.raw = self.bundle.build_suite_archive(files); self.archive.write_bytes(self.raw)
    def package(self):
        self.assertEqual({p.name for p in self.output.iterdir()}, NAMES)
        r, md = self.report.report_preflight_archive(self.archive, sha(self.raw))
        self.assertEqual((self.output / 'PREFLIGHT.json').read_bytes(), canonical(r)); self.assertEqual((self.output / 'SUMMARY_KO.md').read_bytes(), md)
        self.assertEqual((self.output / 'SHA256SUMS.txt').read_bytes(), ''.join(sha((self.output / n).read_bytes()) + '  ' + n + '\n' for n in ('PREFLIGHT.json', 'SUMMARY_KO.md')).encode())

    def test_default_command_publishes_rejection_with_canonical_receipt(self):
        r = self.command(); self.assertEqual((r.returncode, r.stderr), (1, b'')); value = json.loads(r.stdout)
        self.assertEqual(r.stdout, canonical(value)); self.assertEqual(value['status'], 'PREFLIGHT_REPORT_PUBLISHED')
        self.assertEqual((value['preflight_status'], value['preflight_exit_code'], value['compatible_case_count'], value['rejected_case_count']), ('INPUTS_REJECTED', 1, 2, 1)); self.package()

    def test_now_compatible_historical_rejected_exits_zero(self):
        self.changed([('late-invalid', lambda r: r['contexts'][2].update(current_driver_hex=(1.5).hex()))])
        r = self.command(); self.assertEqual((r.returncode, r.stderr), (0, b'')); self.package()
        self.assertEqual(json.loads((self.output / 'PREFLIGHT.json').read_bytes())['case_reports'][2]['saved_status'], 'REJECTED')

    def test_all_rejected_is_successful_publication_exit_one(self):
        self.changed([(c, lambda r: r['frames'][0]['request'].update(request_override=True)) for c in CASES])
        r = self.command(); self.assertEqual(r.returncode, 1, r.stderr); self.assertEqual(json.loads(r.stdout)['rejected_case_count'], 3); self.package()

    def test_api_and_command_produce_same_receipt_and_three_files(self):
        r = self.command(); other = self.root / 'api-output'
        api = self.api.publish_preflight_report(self.archive, sha(self.raw), other)
        self.assertEqual((r.returncode, r.stdout), (1, canonical(api)))
        for n in NAMES: self.assertEqual((self.output / n).read_bytes(), (other / n).read_bytes())

    def test_syntax_rejections_precede_imports_and_all_input_output_access(self):
        original = builtins.__import__
        def importing(name, *a, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')): raise AssertionError('project import')
            return original(name, *a, **kw)
        variants = ([], self.args()[:-2], self.args() + self.args(), self.args() + ['--run'], self.args() + ['--format', 'json'],
            self.args() + ['--rate-budget-per-s', '0'], self.args() + ['--export'], self.args() + ['positional'],
            ['--arch', str(self.archive), *self.args()[2:]], [*self.args()[:-1], ''])
        for args in variants:
            err, out = StringIO(), StringIO()
            with self.subTest(args=args), patch('builtins.__import__', side_effect=importing), patch('os.open', side_effect=AssertionError('path access')), \
                    patch('sys.stderr', err), patch('sys.stdout', out), self.assertRaises(SystemExit) as found: self.cli.main(args)
            self.assertEqual(found.exception.code, 2); self.assertEqual(out.getvalue(), '')
            self.assertEqual(err.getvalue(), 'REJECTED: PREFLIGHT_WORKFLOW_USAGE_NO_MODEL_EXECUTION\n')
        self.assertFalse(self.output.exists())

    def test_help_restores_globals_without_project_import_or_paths(self):
        original = builtins.__import__; paths = list(sys.path); out = StringIO()
        def importing(name, *a, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')): raise AssertionError('project import')
            return original(name, *a, **kw)
        with patch.object(sys, 'dont_write_bytecode', False), patch('builtins.__import__', side_effect=importing), patch('sys.stdout', out), self.assertRaises(SystemExit) as found:
            try: self.cli.main(['--help'])
            finally: self.assertFalse(sys.dont_write_bytecode); self.assertEqual(sys.path, paths)
        self.assertEqual(found.exception.code, 0); self.assertIn('--output-root', out.getvalue()); self.assertFalse(self.output.exists())

    def test_malformed_sha_is_fixed_before_output_inspection(self):
        with patch.object(self.api, '_output', side_effect=AssertionError('output inspection')):
            code, raw, err = self.invoke(['--archive', 'bad\0path', '--sha256', 'BAD', '--output-root', 'bad\0output'])
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: ARCHIVE_PREFLIGHT:PORTABLE_EXPECTED_SHA256\n')); self.assertFalse(self.output.exists())

    def test_existing_output_is_not_captured_or_overwritten(self):
        self.output.mkdir(); p = self.output / 'sentinel'; p.write_bytes(b'keep')
        with patch.object(self.api, 'report_preflight_archive', side_effect=AssertionError('source capture')): code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: ARCHIVE_WORKFLOW_OUTPUT_EXISTS\n')); self.assertEqual(p.read_bytes(), b'keep')

    def test_bad_input_creates_no_output_and_echoes_no_raw_path(self):
        self.raw = b'broken'; self.archive.write_bytes(self.raw); r = self.command()
        self.assertEqual((r.returncode, r.stdout, r.stderr), (2, b'', b'REJECTED: ARCHIVE_PREFLIGHT:PORTABLE_ZIP_FORMAT\n')); self.assertFalse(self.output.exists())

    def test_report_size_error_is_preserved_without_output(self):
        with patch.object(self.report, 'REPORT_CAP', 1): code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: PREFLIGHT_REPORT_SIZE\n')); self.assertFalse(self.output.exists())

    def test_publication_failure_preserves_partial_output_and_fixed_code(self):
        with patch('os.write', return_value=0): code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: ARCHIVE_WORKFLOW_PUBLICATION_FAILED_PARTIAL_DIRECTORY_POSSIBLE\n'))
        self.assertTrue(self.output.is_dir())

    def test_unexpected_backend_failure_restores_globals_and_hides_text(self):
        paths = list(sys.path)
        with patch.object(sys, 'dont_write_bytecode', False), patch.object(self.api, 'publish_preflight_report', side_effect=RuntimeError('SECRET_PATH')):
            code, raw, err = self.invoke(); self.assertFalse(sys.dont_write_bytecode); self.assertEqual(sys.path, paths)
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: PREFLIGHT_WORKFLOW_FAILED_DIRECTORY_MAY_EXIST_NO_MODEL_EXECUTION\n')); self.assertFalse(self.output.exists())

    def test_unknown_current_status_is_operational_not_false_success(self):
        r = self.api.publish_preflight_report(self.archive, sha(self.raw), self.output); r['preflight_status'] = 'UNKNOWN'
        with patch.object(self.api, 'publish_preflight_report', return_value=r): code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: PREFLIGHT_WORKFLOW_FAILED_DIRECTORY_MAY_EXIST_NO_MODEL_EXECUTION\n')); self.package()

    def test_import_failure_restores_globals_without_output(self):
        original = builtins.__import__; paths = list(sys.path)
        def importing(name, *a, **kw):
            if name == 'integration_tools.core_sequence_preflight_workflow': raise ImportError('SECRET_IMPORT')
            return original(name, *a, **kw)
        with patch.object(sys, 'dont_write_bytecode', False), patch('builtins.__import__', side_effect=importing):
            code, raw, err = self.invoke(); self.assertFalse(sys.dont_write_bytecode); self.assertEqual(sys.path, paths)
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: PREFLIGHT_WORKFLOW_FAILED_DIRECTORY_MAY_EXIST_NO_MODEL_EXECUTION\n')); self.assertFalse(self.output.exists())

    def test_cold_main_suppresses_bytecode_and_only_mkdirs_explicit_output(self):
        script = '''import sys
sys.dont_write_bytecode=True
import importlib.util,importlib._bootstrap_external as external
import builtins,os,tempfile
from pathlib import Path
source,parent,*args=sys.argv[1:];target=Path(args[args.index('--output-root')+1]).absolute()
spec=importlib.util.spec_from_file_location('core25_cold',source);cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
assert 'locale' not in sys.modules
writes=[];mkdirs=[];locale_flags=[];real_import=builtins.__import__;real_mkdir=os.mkdir
def importing(name,*a,**kw):
 if name=='locale':locale_flags.append(sys.dont_write_bytecode)
 return real_import(name,*a,**kw)
def storing(self,path,data,**kw):writes.append(path)
def mkdir(path,*a,**kw):
 assert Path(path).absolute()==target,'unexpected mkdir'
 mkdirs.append(str(path));return real_mkdir(path,*a,**kw)
def probe(*a,**kw):raise AssertionError('temp probe/allocation')
external.SourceFileLoader.set_data=storing;os.mkdir=mkdir;builtins.__import__=importing
tempfile.gettempdir=probe;tempfile.gettempdirb=probe;tempfile.TemporaryDirectory=probe;tempfile.tempdir=parent
for key in ('TMPDIR','TEMP','TMP'):os.environ[key]=parent
before=list(sys.path);sys.pycache_prefix=parent;sys.dont_write_bytecode=False
code=cli.main(args)
assert code==1 and not writes and mkdirs==[str(target)],(code,writes,mkdirs)
assert locale_flags and all(locale_flags)
assert sys.path==before and sys.dont_write_bytecode is False and sys.pycache_prefix==parent
assert tempfile.tempdir==parent and all(os.environ[k]==parent for k in ('TMPDIR','TEMP','TMP'))
sys.dont_write_bytecode=True
raise SystemExit(code)
'''
        r = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(self.script), str(self.root), *self.args()], capture_output=True)
        self.assertEqual((r.returncode, r.stderr), (1, b'')); self.package()

    def test_temp_settings_unchanged_without_cache_probes(self):
        prefix = sys.pycache_prefix
        with patch.dict(os.environ, {k: str(self.root) for k in ('TMPDIR', 'TEMP', 'TMP')}), patch.object(tempfile, 'tempdir', str(self.root)), \
                patch.object(tempfile, 'gettempdir', side_effect=AssertionError('probe')), patch.object(tempfile, 'gettempdirb', side_effect=AssertionError('probe')), \
                patch.object(tempfile, 'TemporaryDirectory', side_effect=AssertionError('allocation')):
            code, raw, err = self.invoke(); self.assertEqual(tempfile.tempdir, str(self.root))
        self.assertEqual((code, err), (1, '')); self.assertEqual(json.loads(raw)['preflight_exit_code'], 1); self.assertEqual(sys.pycache_prefix, prefix)

    def test_short_stdout_writes_finish_canonical_receipt_after_publication(self):
        original = os.write
        def writing(fd, raw): return original(fd, raw[:7] if fd == self.stdout_fd else raw)
        with patch('os.write', side_effect=writing): code, raw, err = self.invoke()
        self.assertEqual((code, err), (1, '')); self.assertEqual(raw, canonical(json.loads(raw))); self.package()

    def test_nonpositive_stdout_after_publication_keeps_complete_package(self):
        original = os.write
        def writing(fd, raw): return 0 if fd == self.stdout_fd else original(fd, raw)
        with patch('os.write', side_effect=writing): code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: PREFLIGHT_WORKFLOW_FAILED_DIRECTORY_MAY_EXIST_NO_MODEL_EXECUTION\n')); self.package()

    def test_partial_stdout_after_publication_cannot_retract_receipt_prefix(self):
        original = os.write; calls = []
        def writing(fd, raw):
            if fd != self.stdout_fd: return original(fd, raw)
            calls.append(1)
            if len(calls) > 1: raise OSError('later stdout failure')
            return original(fd, raw[:11])
        with patch('os.write', side_effect=writing): code, raw, err = self.invoke()
        self.assertEqual(code, 2); self.assertEqual(raw, b'{"actual_ac'); self.assertIn('DIRECTORY_MAY_EXIST', err); self.package()

    def test_real_failed_stdout_preserves_published_files(self):
        with Path('/dev/full').open('wb', buffering=0) as full:
            r = subprocess.run([sys.executable, '-I', '-B', str(self.script), *self.args()], stdout=full, stderr=subprocess.PIPE)
        self.assertEqual(r.returncode, 2); self.assertEqual(r.stderr, b'REJECTED: PREFLIGHT_WORKFLOW_FAILED_DIRECTORY_MAY_EXIST_NO_MODEL_EXECUTION\n'); self.package()

    def test_real_failed_stderr_keeps_usage_and_input_error_exit_two(self):
        for args in (['--unknown', 'DO_NOT_ECHO'], ['--archive', str(self.root / 'absent'), *self.args()[2:]]):
            with Path('/dev/full').open('wb', buffering=0) as full:
                r = subprocess.run([sys.executable, '-I', '-B', str(self.script), *args], stdout=subprocess.PIPE, stderr=full)
            self.assertEqual((r.returncode, r.stdout), (2, b''))
        self.assertFalse(self.output.exists())

    def test_closed_stderr_error_is_operational_two(self):
        script = '''import os,runpy,sys
os.close(2);sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')
'''
        r = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(self.script), '--archive', str(self.root / 'absent'), *self.args()[2:]], capture_output=True)
        self.assertEqual((r.returncode, r.stdout), (2, b'')); self.assertFalse(self.output.exists())

    def test_help_stdout_failure_is_two_without_output_directory(self):
        with Path('/dev/full').open('wb', buffering=0) as full:
            r = subprocess.run([sys.executable, '-I', '-B', str(self.script), '--help'], stdout=full, stderr=subprocess.PIPE)
        self.assertEqual(r.returncode, 2); self.assertFalse(self.output.exists())

    def test_in_memory_diagnostic_failure_is_best_effort(self):
        class Failed(StringIO):
            def write(self, text: str, /) -> int: raise OSError('diagnostic unavailable')
        with patch('sys.stdout', StringIO()), patch('sys.stderr', Failed()), patch.object(self.api, 'publish_preflight_report', side_effect=RuntimeError('unexpected')):
            code = self.cli.main(self.args())
        self.assertEqual(code, 2); self.assertFalse(self.output.exists())

    def test_baseexception_restores_caller_globals(self):
        paths = list(sys.path)
        with patch.object(sys, 'dont_write_bytecode', False), patch.object(self.api, 'publish_preflight_report', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            try: self.invoke()
            finally: self.assertFalse(sys.dont_write_bytecode); self.assertEqual(sys.path, paths)
        self.assertFalse(self.output.exists())

    def test_blocked_producer_reference_f61_and_model_step_still_publish(self):
        script = '''import importlib.abc,runpy,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  modules=('integration_tools.core_sequence_run','integration_tools.core_sequence_archive_run','integration_tools.synthetic_sequence_check','integration_tools.synthetic_transition_check','integration_tools.sequence_reference','integration_tools.fixed_model_reference','numpy','openpilot','opendbc')
  if any(fullname==m or fullname.startswith(m+'.') for m in modules) or fullname.startswith('integration_tools.f61_'):raise AssertionError('forbidden import:'+fullname)
def profile(frame,event,arg):
 if event=='call' and frame.f_globals.get('__name__','').startswith('cyberlateral_dev') and frame.f_code.co_name in ('step','step_normalized'):raise AssertionError('model executed')
sys.meta_path.insert(0,Block());sys.setprofile(profile);sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')
'''
        r = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(self.script), *self.args()], capture_output=True)
        self.assertEqual((r.returncode, r.stderr), (1, b'')); self.package()

    def test_space_paths_unrelated_cwd_and_readonly_input(self):
        self.archive.rename(self.root / 'input with spaces.zip'); self.archive = self.root / 'input with spaces.zip'; self.archive.chmod(0o444)
        before = self.archive.read_bytes(), self.archive.stat().st_mode; self.output = self.root / 'output with spaces'
        r = self.command(); self.assertEqual(r.returncode, 1, r.stderr); self.package(); self.assertEqual(before, (self.archive.read_bytes(), self.archive.stat().st_mode))

    def test_repeat_command_rejects_without_touching_completed_package(self):
        first = self.command(); self.assertEqual(first.returncode, 1, first.stderr)
        before = {p.name: (p.read_bytes(), p.stat().st_mode) for p in self.output.iterdir()}
        second = self.command(); self.assertEqual((second.returncode, second.stdout, second.stderr), (2, b'', b'REJECTED: ARCHIVE_WORKFLOW_OUTPUT_EXISTS\n'))
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mode) for p in self.output.iterdir()})

    def test_receipt_keeps_gates_and_numeric_work_scope(self):
        r = self.command(); value = json.loads(r.stdout); self.assertEqual(r.returncode, 1, r.stderr)
        self.assertEqual(set(value['files']), NAMES); self.assertEqual(value['numeric_validation_work'], 'NONZERO_NOT_AGGREGATED')
        self.assertEqual((value['new_synthetic_model_steps'], value['new_reference_steps']), (0, 0))
        self.assertEqual(value['gates']['R_BUDGET'], 'UNRESOLVED'); self.assertEqual(value['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
        self.assertIs(value['f61_input_allowed'], False); self.assertIs(value['actual_activation_allowed'], False)
