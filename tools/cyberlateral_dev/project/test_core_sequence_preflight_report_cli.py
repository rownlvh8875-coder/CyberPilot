"""CORE23 Markdown parity and no-cache/error/output boundaries."""

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

CASES = ('sign-cycle', 'declared-difference', 'late-invalid')


def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(v): return (json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CorePreflightReportCliTests(unittest.TestCase):
    def setUp(self):
        self.script = ROOT / 'tools/core_sequence_preflight_report.py'
        self.assertTrue(self.script.is_file(), 'Missing CORE24 Korean preflight report command')
        package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.api: Any = importlib.import_module('integration_tools.core_sequence_preflight_report')
        self.preflight: Any = importlib.import_module('integration_tools.core_sequence_archive_preflight')
        self.bundle = importlib.import_module('integration_tools.core_sequence_bundle')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        producer = importlib.import_module('integration_tools.core_sequence_run'); self.source = {}
        for case in CASES:
            folder = self.root / case; producer.run_sequence_case(case, folder)
            self.source.update({'suite/' + case + '/' + n: (folder / n).read_bytes() for n in ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt')})
        self.archive = self.root / 'packet.zip'; self.store(self.bundle.build_suite_archive(self.source))
        spec = importlib.util.spec_from_file_location('core24_test_cli', self.script)
        assert spec is not None and spec.loader is not None
        self.cli: Any = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.cli)

    def store(self, raw): self.archive.write_bytes(raw); self.digest = sha(raw)
    def args(self): return ['--archive', str(self.archive), '--sha256', self.digest]
    def expected(self): return self.api.report_preflight_archive(self.archive, self.digest)[1]
    def command(self, args=None):
        return subprocess.run([sys.executable, '-I', '-B', str(self.script), *(self.args() if args is None else args)], capture_output=True, cwd=self.root)
    def invoke(self, args=None):
        err = StringIO(); path = self.root / 'stdout.bin'
        with path.open('wb') as out, patch('sys.stdout', out), patch('sys.stderr', err): code = self.cli.main(self.args() if args is None else args)
        return code, path.read_bytes(), err.getvalue()
    def edit(self, changes):
        files = dict(self.source)
        for case, change in changes:
            prefix = 'suite/' + case + '/'; value = json.loads(files[prefix + 'INPUT.json']); change(value)
            files[prefix + 'INPUT.json'] = canonical(value)
            files[prefix + 'SHA256SUMS.txt'] = ''.join(sha(files[prefix + n]) + '  ' + n + '\n' for n in ('INPUT.json', 'RESULTS.json')).encode()
        self.store(self.bundle.build_suite_archive(files))
    def snapshot(self): return self.archive.read_bytes(), self.archive.stat().st_mode

    def test_default_archive_returns_exact_markdown_and_exit_one(self):
        result = self.command()
        self.assertEqual((result.returncode, result.stderr), (1, b'')); self.assertEqual(result.stdout, self.expected())
        text = result.stdout.decode()
        for row in ('| `"compatible_case_count"` | `2` |', '| `"rejected_case_count"` | `1` |', '| `"validated_transition_count"` | `8` |'):
            self.assertIn(row, text)
        self.assertTrue(text.startswith('# CORE23 ZIP 입력 사전 검증 요약\n'))
        self.assertEqual(len([line for line in text.splitlines() if any(line.startswith('| `"' + case + '"` |') for case in CASES)]), 3)

    def test_all_compatible_even_historical_rejected_exits_zero(self):
        self.edit([('late-invalid', lambda r: r['contexts'][2].update(current_driver_hex=(1.5).hex()))])
        result = self.command(); self.assertEqual((result.returncode, result.stderr), (0, b'')); self.assertEqual(result.stdout, self.expected())
        text = result.stdout.decode(); self.assertIn('| `"validated_transition_count"` | `9` |', text)
        self.assertIn('| `"late-invalid"` | `"INPUTS_COMPATIBLE"` | `null` | `3` | `3` | `"REJECTED"` |', text)

    def test_all_rejected_is_not_vacuous_exit_zero(self):
        self.edit([(case, lambda r: r['frames'][0]['request'].update(request_override=True)) for case in CASES])
        result = self.command(); self.assertEqual((result.returncode, result.stderr), (1, b'')); self.assertEqual(result.stdout, self.expected())
        text = result.stdout.decode(); self.assertIn('| `"rejected_case_count"` | `3` |', text)
        self.assertIn('| `"validated_transition_count"` | `0` |', text)

    def test_first_rejection_still_reports_all_three_cases(self):
        self.edit([('sign-cycle', lambda r: r['frames'][0]['request'].update(request_override=True))])
        result = self.command(); self.assertEqual(result.returncode, 1, result.stderr)
        text = result.stdout.decode()
        rows = [line for line in text.splitlines() if any(line.startswith('| `"' + c + '"` |') for c in CASES)]
        self.assertEqual(len(rows), 3); self.assertIn('sign-cycle', rows[0]); self.assertIn('declared-difference', rows[1]); self.assertIn('late-invalid', rows[2])
        self.assertIn('| `"validated_transition_count"` | `5` |', text)

    def test_wrong_full_sha_is_operational_two_without_receipt_or_path_echo(self):
        result = self.command(['--archive', str(self.archive), '--sha256', '0' * 64])
        self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', b'REJECTED: ARCHIVE_PREFLIGHT:PORTABLE_ARCHIVE_CHECKSUM\n'))

    def test_malformed_sha_precedes_missing_or_unsafe_path_access(self):
        portable = importlib.import_module('integration_tools.core_sequence_portable')
        for digest in ('0', 'A' * 64, '0' * 63, '0' * 65, ' ' + '0' * 64):
            with self.subTest(digest=digest), patch.object(self.preflight, '_read_archive', side_effect=AssertionError('caller path access')), \
                    patch.object(portable, '_path', side_effect=AssertionError('path metadata')):
                code, raw, err = self.invoke(['--archive', 'missing\0unsafe', '--sha256', digest])
            self.assertEqual((code, raw, err), (2, b'', 'REJECTED: ARCHIVE_PREFLIGHT:PORTABLE_EXPECTED_SHA256\n'))

    def test_invalid_syntax_precedes_project_import_and_caller_file_access(self):
        original = builtins.__import__
        def importing(name, *a, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')): raise AssertionError('project imported')
            return original(name, *a, **kw)
        variants = ([], ['--archive', str(self.archive)], ['--sha256', self.digest],
            ['--arch', str(self.archive), '--sha256', self.digest], self.args() + self.args(),
            self.args() + ['--sha256', self.digest], self.args() + ['--run'], self.args() + ['--export'],
            self.args() + ['--output', 'DO_NOT_ECHO'], self.args() + ['--format', 'json'], self.args() + ['--rate-budget-per-s', '0'],
            ['--archive', '', '--sha256', self.digest], ['--archive', str(self.archive), '--sha256', ''], self.args() + ['positional'])
        for args in variants:
            out, err = StringIO(), StringIO()
            with self.subTest(args=args), patch('builtins.__import__', side_effect=importing), \
                    patch('os.open', side_effect=AssertionError('caller file')), patch('sys.stdout', out), patch('sys.stderr', err), \
                    self.assertRaises(SystemExit) as found: self.cli.main(args)
            self.assertEqual(found.exception.code, 2); self.assertEqual(out.getvalue(), '')
            self.assertEqual(err.getvalue(), 'REJECTED: PREFLIGHT_REPORT_USAGE_NO_MODEL_EXECUTION\n')

    def test_help_does_not_import_api_or_access_input_and_restores_globals(self):
        original = builtins.__import__; paths = list(sys.path); out = StringIO()
        def importing(name, *a, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')): raise AssertionError('project imported')
            return original(name, *a, **kw)
        with patch.object(sys, 'dont_write_bytecode', False), patch('builtins.__import__', side_effect=importing), \
                patch('os.open', side_effect=AssertionError('caller file')), patch('sys.stdout', out), self.assertRaises(SystemExit) as found:
            try: self.cli.main(['--help'])
            finally: self.assertFalse(sys.dont_write_bytecode); self.assertEqual(sys.path, paths)
        self.assertEqual(found.exception.code, 0); self.assertIn('--archive', out.getvalue()); self.assertIn('--sha256', out.getvalue())

    def test_equals_form_and_reversed_options_keep_exact_api_values(self):
        result = self.command(['--sha256=' + self.digest, '--archive=' + str(self.archive)])
        self.assertEqual((result.returncode, result.stderr), (1, b'')); self.assertEqual(result.stdout, self.expected())

    def test_unrelated_cwd_and_space_path_are_supported(self):
        self.archive.rename(self.root / 'packet with spaces.zip'); self.archive = self.root / 'packet with spaces.zip'
        result = self.command(); self.assertEqual(result.returncode, 1, result.stderr); self.assertEqual(result.stdout, self.expected())

    def test_readonly_archive_bytes_modes_and_layout_remain_unchanged(self):
        self.archive.chmod(0o444); before = self.snapshot(); layout = sorted(p.name for p in self.root.iterdir())
        result = self.command(); self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(before, self.snapshot()); self.assertEqual(layout, sorted(p.name for p in self.root.iterdir()))

    def test_single_api_capture_verification_and_three_case_processing(self):
        opened = []; counts = {'api': 0, 'verify': 0, 'cases': 0, 'renders': 0}; original = os.open
        def observe(path, flags, *a, **kw):
            self.assertFalse(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
            fd = original(path, flags, *a, **kw)
            if stat.S_ISREG(os.fstat(fd).st_mode): opened.append(Path(path).name)
            return fd
        def profile(frame, event, arg):
            if event != 'call': return
            key = (frame.f_globals.get('__name__'), frame.f_code.co_name)
            if key == ('integration_tools.core_sequence_preflight_report', 'report_preflight_archive'): counts['api'] += 1
            if key == ('integration_tools.core_sequence_preflight_report', '_markdown'): counts['renders'] += 1
            if key == ('integration_tools.core_sequence_bundle', '_verified_suite'): counts['verify'] += 1
            if key == ('integration_tools.core_sequence_input_preflight', '_preflight_captured'): counts['cases'] += 1
        sys.setprofile(profile)
        try:
            with patch('os.open', side_effect=observe): code, raw, err = self.invoke()
        finally: sys.setprofile(None)
        self.assertEqual((code, err), (1, '')); self.assertEqual(raw, self.expected())
        self.assertEqual(counts, {'api': 1, 'verify': 1, 'cases': 3, 'renders': 1}); self.assertEqual(opened, ['packet.zip'])

    def test_producer_reference_f61_imports_and_model_step_are_blocked(self):
        script = '''import importlib.abc,runpy,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  modules=('integration_tools.core_sequence_run','integration_tools.core_sequence_archive_run','integration_tools.synthetic_sequence_check','integration_tools.synthetic_transition_check','integration_tools.sequence_reference','integration_tools.fixed_model_reference','numpy','openpilot','opendbc')
  if any(fullname==m or fullname.startswith(m+'.') for m in modules) or fullname.startswith('integration_tools.f61_'):raise AssertionError('forbidden import:'+fullname)
def profile(frame,event,arg):
 if event=='call' and frame.f_globals.get('__name__','').startswith('cyberlateral_dev') and frame.f_code.co_name in ('step','step_normalized'):raise AssertionError('model executed')
sys.meta_path.insert(0,Block());sys.setprofile(profile);sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(self.script), *self.args()], capture_output=True, cwd=self.root)
        self.assertEqual((result.returncode, result.stderr), (1, b'')); self.assertEqual(result.stdout, self.expected())

    def test_temp_settings_never_probe_or_allocate_cache(self):
        before = self.snapshot(); prefix = sys.pycache_prefix
        with patch.dict(os.environ, {k: str(self.root) for k in ('TMPDIR', 'TEMP', 'TMP')}), patch.object(tempfile, 'tempdir', str(self.root)), \
                patch.object(tempfile, 'gettempdir', side_effect=AssertionError('temp probe')), patch.object(tempfile, 'gettempdirb', side_effect=AssertionError('temp probe')), \
                patch.object(tempfile, 'TemporaryDirectory', side_effect=AssertionError('cache allocation')):
            code, raw, err = self.invoke(); self.assertEqual(tempfile.tempdir, str(self.root))
            self.assertTrue(all(os.environ[k] == str(self.root) for k in ('TMPDIR', 'TEMP', 'TMP')))
        self.assertEqual((code, err), (1, '')); self.assertEqual(raw, self.expected())
        self.assertEqual(before, self.snapshot()); self.assertEqual(sys.pycache_prefix, prefix)

    def test_cold_parser_and_api_imports_suppress_bytecode_without_global_leak(self):
        script = '''import sys
sys.dont_write_bytecode=True
import importlib.util,importlib._bootstrap_external as external
import builtins,os,tempfile
source,folder,*args=sys.argv[1:]
spec=importlib.util.spec_from_file_location('cold_core24',source);cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
assert 'locale' not in sys.modules,'child preloaded locale'
writes=[];mkdirs=[];locale_flags=[];real_import=builtins.__import__
def importing(name,*a,**kw):
 if name=='locale':locale_flags.append(sys.dont_write_bytecode)
 return real_import(name,*a,**kw)
def store(self,path,data,**kw):writes.append(path)
def mkdir(*a,**kw):mkdirs.append(1);raise AssertionError('mkdir')
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
        for failed in (False, True):
            args = ['--archive', str(self.root / 'missing'), '--sha256', self.digest] if failed else self.args()
            result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(self.script), str(self.root), *args], capture_output=True)
            self.assertEqual(result.returncode, 2 if failed else 1, result.stderr)
            self.assertEqual(result.stdout, b'' if failed else self.expected())
        self.assertEqual(before, self.snapshot())

    def test_success_and_unexpected_api_failure_restore_paths_and_bytecode(self):
        before = self.snapshot(); prefix = sys.pycache_prefix
        for failed in (False, True):
            with patch.object(sys, 'dont_write_bytecode', False), patch.object(sys, 'path', [*sys.path, 'caller-marker']):
                paths = list(sys.path)
                if failed:
                    with patch.object(self.api, 'report_preflight_archive', side_effect=RuntimeError('SECRET_INPUT_TEXT')): code, raw, err = self.invoke()
                else: code, raw, err = self.invoke()
                self.assertFalse(sys.dont_write_bytecode); self.assertEqual(sys.path, paths); self.assertEqual(sys.pycache_prefix, prefix)
            self.assertEqual(code, 2 if failed else 1)
            if failed: self.assertEqual((raw, err), (b'', 'REJECTED: PREFLIGHT_REPORT_FAILED_NO_MODEL_EXECUTION\n'))
        self.assertEqual(before, self.snapshot())

    def test_import_failure_is_fixed_operational_two(self):
        original = builtins.__import__; paths = list(sys.path)
        def importing(name, *a, **kw):
            if name == 'integration_tools.core_sequence_preflight_report': raise ImportError('SECRET_IMPORT_TEXT')
            return original(name, *a, **kw)
        with patch.object(sys, 'dont_write_bytecode', False), patch('builtins.__import__', side_effect=importing):
            code, raw, err = self.invoke(); self.assertFalse(sys.dont_write_bytecode); self.assertEqual(sys.path, paths)
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: PREFLIGHT_REPORT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_unknown_api_status_fails_closed_before_output(self):
        value, md = self.api.report_preflight_archive(self.archive, self.digest); value['preflight_status'] = 'UNKNOWN'
        with patch.object(self.api, 'report_preflight_archive', return_value=(value, md)): code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: PREFLIGHT_REPORT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_renderer_failure_has_no_partial_report(self):
        with patch.object(self.api, '_markdown', side_effect=ValueError('SECRET_RECORD_TEXT')): code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: PREFLIGHT_REPORT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_short_stdout_writes_complete_the_same_markdown(self):
        original = os.write
        def short(fd, raw): return original(fd, raw[:7])
        with patch('os.write', side_effect=short): code, raw, err = self.invoke()
        self.assertEqual((code, err), (1, '')); self.assertEqual(raw, self.expected())

    def test_nonpositive_stdout_progress_is_operational_two(self):
        for value in (0, -1):
            calls = []
            def write(fd, raw, value=value, calls=calls): calls.append(1); return value
            with self.subTest(value=value), patch('os.write', side_effect=write): code, raw, err = self.invoke()
            self.assertEqual(calls, [1]); self.assertEqual((code, raw, err), (2, b'', 'REJECTED: PREFLIGHT_REPORT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_partial_stdout_failure_returns_two_with_unretractable_prefix(self):
        expected = self.expected(); original = os.write; calls = []
        def write(fd, raw):
            calls.append(1)
            if len(calls) > 1: raise OSError('later failure')
            return original(fd, raw[:11])
        with patch('os.write', side_effect=write): code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, expected[:11], 'REJECTED: PREFLIGHT_REPORT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_real_failed_stdout_is_operational_two(self):
        with Path('/dev/full').open('wb', buffering=0) as failed:
            result = subprocess.run([sys.executable, '-I', '-B', str(self.script), *self.args()], stdout=failed, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 2); self.assertEqual(result.stderr, b'REJECTED: PREFLIGHT_REPORT_FAILED_NO_MODEL_EXECUTION\n')

    def test_real_failed_stderr_preserves_operational_two(self):
        injected = '''import importlib.util,sys
sys.path[:0]=[sys.argv[1],sys.argv[1]+'/src']
import integration_tools.core_sequence_preflight_report as api
def fail(*args):raise RuntimeError('unexpected failure')
api.report_preflight_archive=fail
spec=importlib.util.spec_from_file_location('failed_core24',sys.argv[2]);cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
raise SystemExit(cli.main(sys.argv[3:]))
'''
        for mode in ('integrity', 'usage', 'unexpected'):
            args = self.args() if mode == 'unexpected' else (['--archive', str(self.root / 'missing'), '--sha256', self.digest] if mode == 'integrity' else ['--unknown', 'DO_NOT_ECHO'])
            command = [sys.executable, '-I', '-B', str(self.script), *args]
            if mode == 'unexpected': command = [sys.executable, '-I', '-B', '-c', injected, str(ROOT), str(self.script), *args]
            with self.subTest(mode=mode), Path('/dev/full').open('wb', buffering=0) as failed:
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=failed)
                self.assertEqual(result.returncode, 2); self.assertEqual(result.stdout, b'')

    def test_closed_stderr_preserves_operational_two(self):
        script = '''import os,runpy,sys
os.close(2);sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(self.script), '--archive', str(self.root / 'missing'), '--sha256', self.digest], capture_output=True)
        self.assertEqual((result.returncode, result.stdout), (2, b''))

    def test_failed_help_stdout_is_operational_two(self):
        with Path('/dev/full').open('wb', buffering=0) as failed:
            result = subprocess.run([sys.executable, '-I', '-B', str(self.script), '--help'], stdout=failed, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 2); self.assertEqual(result.stderr, b'REJECTED: PREFLIGHT_REPORT_FAILED_NO_MODEL_EXECUTION\n')

    def test_failed_in_memory_diagnostic_does_not_escape(self):
        class Failed(StringIO):
            def write(self, text: str, /) -> int: raise OSError('diagnostic unavailable')
        paths = list(sys.path)
        with patch.object(sys, 'dont_write_bytecode', False), patch('sys.stdout', StringIO()), patch('sys.stderr', Failed()), \
                patch.object(self.api, 'report_preflight_archive', side_effect=RuntimeError('unexpected')):
            code = self.cli.main(self.args()); self.assertFalse(sys.dont_write_bytecode); self.assertEqual(sys.path, paths)
        self.assertEqual(code, 2)

    def test_baseexception_propagates_after_global_restoration(self):
        paths = list(sys.path)
        with patch.object(sys, 'dont_write_bytecode', False), patch.object(self.api, 'report_preflight_archive', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            try: self.invoke()
            finally: self.assertFalse(sys.dont_write_bytecode); self.assertEqual(sys.path, paths)

    def test_missing_symlink_fifo_and_bad_path_text_have_fixed_file_errors(self):
        alias = self.root / 'alias.zip'; alias.symlink_to(self.archive)
        fifo = self.root / 'fifo'; os.mkfifo(fifo)
        for path in (str(self.root / 'absent'), str(alias), str(fifo), 'bad\0path', 'bad\ud800path'):
            code, raw, err = self.invoke(['--archive', path, '--sha256', self.digest])
            self.assertEqual((code, raw, err), (2, b'', 'REJECTED: ARCHIVE_PREFLIGHT:PORTABLE_ARCHIVE_FILE\n'))

    def test_oversized_archive_is_rejected_without_receipt(self):
        self.store(b'x' * 2_000_001); result = self.command()
        self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', b'REJECTED: ARCHIVE_PREFLIGHT:PORTABLE_ARCHIVE_SIZE\n'))

    def test_corrupt_zip_is_operational_not_semantic_rejection(self):
        self.store(b'broken'); result = self.command()
        self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', b'REJECTED: ARCHIVE_PREFLIGHT:PORTABLE_ZIP_FORMAT\n'))

    def test_policy_and_calculator_denial_gates_remain_closed(self):
        result = self.command(); text = result.stdout.decode()
        self.assertEqual(result.returncode, 1, result.stderr)
        for row in ('| `"new_synthetic_model_steps"` | `0` |', '| `"new_reference_steps"` | `0` |',
                    '| `"R_BUDGET"` | `"UNRESOLVED"` |', '| `"STATIC_EVIDENCE_GATE"` | `"FAIL"` |',
                    '| `"f61_input_allowed"` | `false` |', '| `"actual_activation_allowed"` | `false` |',
                    '| `"actual_r"` | `null` |', '| `"T2"` | `null` |', '| `"vehicle_scale"` | `null` |'):
            self.assertIn(row, text)
        self.assertIn('NONZERO_NOT_AGGREGATED', text)

    def test_report_size_error_is_known_operational_two_without_partial_markdown(self):
        with patch.object(self.api, 'REPORT_CAP', 1): code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: PREFLIGHT_REPORT_SIZE\n'))

    def test_partial_multibyte_write_failure_does_not_claim_valid_utf8_or_success(self):
        expected = self.expected(); cut = expected.index('입'.encode()) + 1
        with self.assertRaises(UnicodeDecodeError): expected[:cut].decode('utf-8')
        original = os.write; calls = []; before = self.snapshot()
        def write(fd, raw):
            calls.append(1)
            if len(calls) > 1: raise OSError('later failure')
            return original(fd, raw[:cut])
        with patch('os.write', side_effect=write): code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, expected[:cut], 'REJECTED: PREFLIGHT_REPORT_FAILED_NO_MODEL_EXECUTION\n'))
        self.assertEqual(before, self.snapshot())
