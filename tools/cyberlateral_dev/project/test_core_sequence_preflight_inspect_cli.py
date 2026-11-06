"""Read-only inspection CLI exits, cold invocation and failed output boundaries."""

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
def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(v): return (json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CorePreflightInspectCliTests(unittest.TestCase):
    def setUp(self):
        self.script = ROOT / 'tools/core_sequence_preflight_inspect.py'
        self.assertTrue(self.script.is_file(), 'Missing CORE26 inspection command')
        package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.api: Any = importlib.import_module('integration_tools.core_sequence_preflight_inspect')
        self.pub: Any = importlib.import_module('integration_tools.core_sequence_preflight_workflow')
        bundle = importlib.import_module('integration_tools.core_sequence_bundle')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        producer = importlib.import_module('integration_tools.core_sequence_run'); files = {}
        for c in CASES:
            p = self.root / c; producer.run_sequence_case(c, p)
            files.update({'suite/' + c + '/' + n: (p / n).read_bytes() for n in ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt')})
        self.raw = bundle.build_suite_archive(files); self.archive = self.root / 'input.zip'; self.archive.write_bytes(self.raw)
        self.folder = self.root / 'report'; self.pub.publish_preflight_report(self.archive, sha(self.raw), self.folder)
        spec = importlib.util.spec_from_file_location('core26_cli_test', self.script)
        assert spec is not None and spec.loader is not None
        self.cli: Any = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.cli)

    def args(self): return ['--input-root', str(self.folder), '--archive', str(self.archive), '--sha256', sha(self.raw)]
    def command(self, args=None, stdout: Any = subprocess.PIPE, stderr: Any = subprocess.PIPE):
        return subprocess.run([sys.executable, '-I', '-B', str(self.script), *(self.args() if args is None else args)], cwd=self.root, stdout=stdout, stderr=stderr)
    def invoke(self, args=None):
        err = StringIO(); p = self.root / 'stdout.bin'
        with p.open('wb') as out, patch('sys.stdout', out), patch('sys.stderr', err): code = self.cli.main(self.args() if args is None else args)
        return code, p.read_bytes(), err.getvalue()

    def test_consistent_rejection_cli_exits_zero_and_records_preflight_one(self):
        r = self.command(); self.assertEqual((r.returncode, r.stderr), (0, b'')); value = json.loads(r.stdout)
        self.assertEqual(r.stdout, canonical(value)); self.assertEqual(value['inspection_status'], 'SAVED_PREFLIGHT_REPORT_CONSISTENT')
        self.assertEqual((value['inspection_exit_code'], value['preflight_exit_code'], value['compatible_case_count'], value['rejected_case_count']), (0, 1, 2, 1))

    def test_api_and_cli_receipts_match_exactly(self):
        r = self.command(); self.assertEqual(r.stdout, canonical(self.api.inspect_preflight_report(self.folder, self.archive, sha(self.raw))))

    def test_syntax_errors_precede_project_import_and_path_work(self):
        original = builtins.__import__
        def importing(name, *a, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')): raise AssertionError('project import')
            return original(name, *a, **kw)
        variants = ([], self.args()[:-2], self.args() + self.args(), self.args() + ['--run'], self.args() + ['--output-root', 'x'],
            self.args() + ['--export'], self.args() + ['--format', 'json'], self.args() + ['--rate-budget-per-s', '0'],
            self.args() + ['positional'], ['--input', str(self.folder), *self.args()[2:]], [*self.args()[:-1], ''])
        for args in variants:
            err, out = StringIO(), StringIO()
            with self.subTest(args=args), patch('builtins.__import__', side_effect=importing), patch('os.open', side_effect=AssertionError('path')), \
                    patch('sys.stderr', err), patch('sys.stdout', out), self.assertRaises(SystemExit) as found: self.cli.main(args)
            self.assertEqual(found.exception.code, 2); self.assertEqual(out.getvalue(), '')
            self.assertEqual(err.getvalue(), 'REJECTED: PREFLIGHT_INSPECT_USAGE_NO_MODEL_EXECUTION\n')

    def test_help_precedes_project_imports_and_has_three_options(self):
        r = self.command(['--help']); self.assertEqual((r.returncode, r.stderr), (0, b''))
        for option in (b'--input-root', b'--archive', b'--sha256'): self.assertIn(option, r.stdout)
        with patch('os.open', side_effect=AssertionError('path')), patch('sys.stdout', StringIO()), self.assertRaises(SystemExit) as found: self.cli.main(['--help'])
        self.assertEqual(found.exception.code, 0)

    def test_bad_sha_preserves_fixed_error_and_no_receipt(self):
        r = self.command([*self.args()[:-1], 'A' * 64]); self.assertEqual((r.returncode, r.stdout, r.stderr), (2, b'', b'REJECTED: ARCHIVE_PREFLIGHT:PORTABLE_EXPECTED_SHA256\n'))

    def test_missing_archive_has_fixed_error_without_path_leak(self):
        args = self.args(); args[3] = str(self.root / 'PRIVATE-PATH-DO-NOT-ECHO')
        r = self.command(args); self.assertEqual((r.returncode, r.stdout, r.stderr), (2, b'', b'REJECTED: ARCHIVE_PREFLIGHT:PORTABLE_ARCHIVE_FILE\n'))

    def test_rechecksummed_changed_report_rejects_without_output(self):
        p = self.folder / 'SUMMARY_KO.md'; p.write_bytes(p.read_bytes().replace(b'CORE23', b'CORE99', 1))
        (self.folder / 'SHA256SUMS.txt').write_bytes(''.join(sha((self.folder / n).read_bytes()) + '  ' + n + '\n' for n in ('PREFLIGHT.json', 'SUMMARY_KO.md')).encode())
        r = self.command(); self.assertEqual((r.returncode, r.stdout, r.stderr), (2, b'', b'REJECTED: PREFLIGHT_INSPECT_REPORT_MISMATCH\n'))

    def test_invalid_layout_uses_wrapped_error_not_current_verdict(self):
        (self.folder / 'extra').write_bytes(b'x'); r = self.command()
        self.assertEqual((r.returncode, r.stdout, r.stderr), (2, b'', b'REJECTED: PREFLIGHT_INSPECT:RUN_INSPECT_LAYOUT\n'))

    def test_presentation_cap_error_preserved(self):
        report = importlib.import_module('integration_tools.core_sequence_preflight_report')
        with patch.object(report, 'REPORT_CAP', 1): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'', 'REJECTED: PREFLIGHT_REPORT_SIZE\n'))

    def test_unknown_backend_failure_has_fixed_no_model_diagnostic(self):
        with patch.object(self.api, 'inspect_preflight_report', side_effect=AssertionError('PRIVATE')): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'', 'REJECTED: PREFLIGHT_INSPECT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_import_failure_restores_caller_settings(self):
        original = builtins.__import__; before = list(sys.path), sys.dont_write_bytecode
        def importing(name, *a, **kw):
            if name == 'integration_tools.core_sequence_preflight_inspect': raise ImportError('PRIVATE')
            return original(name, *a, **kw)
        with patch('builtins.__import__', side_effect=importing): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'', 'REJECTED: PREFLIGHT_INSPECT_FAILED_NO_MODEL_EXECUTION\n')); self.assertEqual((sys.path, sys.dont_write_bytecode), before)

    def test_baseexception_propagates_after_flag_and_path_restore(self):
        before = list(sys.path), sys.dont_write_bytecode
        with patch.object(self.api, 'inspect_preflight_report', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt): self.cli.main(self.args())
        self.assertEqual((sys.path, sys.dont_write_bytecode), before)

    def test_cold_no_bytecode_temp_probe_or_nonstdio_write(self):
        code = r'''
import builtins, importlib.util, importlib._bootstrap_external as ext, os, sys, tempfile
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('cold26', sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
assert 'locale' not in sys.modules
original_import = builtins.__import__; flags = []; original_write = os.write; original_open = os.open
def no(*a, **kw): raise AssertionError('write/temp/cache')
def importing(name, *a, **kw):
    if name == 'locale': flags.append(sys.dont_write_bytecode)
    return original_import(name, *a, **kw)
def opening(path, flag, *a, **kw):
    assert flag & os.O_ACCMODE == os.O_RDONLY
    return original_open(path, flag, *a, **kw)
def writing(fd, raw):
    assert fd in (1, 2)
    return original_write(fd, raw)
ext.SourceFileLoader.set_data = no; os.mkdir = no; os.open = opening; os.write = writing
tempfile.gettempdir = no; tempfile.gettempdirb = no; tempfile.TemporaryDirectory = no
tempfile.tempdir = sys.argv[2]; sys.pycache_prefix = sys.argv[2]
builtins.__import__ = importing; sys.dont_write_bytecode = False
before = list(sys.path)
result = m.main(sys.argv[3:]); assert result == 0 and sys.path == before and sys.dont_write_bytecode is False
assert flags and all(flags); assert tempfile.tempdir == sys.pycache_prefix == sys.argv[2]
sys.dont_write_bytecode = True
'''
        before = {p.relative_to(self.folder): p.read_bytes() for p in self.folder.iterdir()}
        r = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(self.script), str(self.folder), *self.args()], capture_output=True, cwd=self.root)
        self.assertEqual((r.returncode, r.stderr), (0, b'')); self.assertEqual(json.loads(r.stdout)['inspection_exit_code'], 0)
        self.assertEqual({p.relative_to(self.folder): p.read_bytes() for p in self.folder.iterdir()}, before)

    def test_short_stdout_writes_deliver_complete_canonical_receipt(self):
        original = os.write
        with patch('os.write', side_effect=lambda fd, raw: original(fd, raw[:7])): code, raw, error = self.invoke()
        self.assertEqual((code, error), (0, '')); self.assertEqual(raw, canonical(json.loads(raw)))

    def test_nonpositive_stdout_is_operational_two(self):
        with patch('os.write', return_value=0): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'', 'REJECTED: PREFLIGHT_INSPECT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_partial_stdout_failure_is_not_success_or_retractable(self):
        original = os.write; first = True
        def writing(fd, raw):
            nonlocal first
            if first: first = False; return original(fd, raw[:11])
            raise OSError('failed')
        with patch('os.write', side_effect=writing): code, raw, error = self.invoke()
        self.assertEqual((code, raw, error), (2, b'{"actual_ac', 'REJECTED: PREFLIGHT_INSPECT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_real_dev_full_stdout_is_two_and_preserves_inputs(self):
        before = {p.name: p.read_bytes() for p in self.folder.iterdir()}
        with open('/dev/full', 'wb') as sink: r = self.command(stdout=sink, stderr=subprocess.PIPE)
        self.assertEqual((r.returncode, r.stderr), (2, b'REJECTED: PREFLIGHT_INSPECT_FAILED_NO_MODEL_EXECUTION\n'))
        self.assertEqual({p.name: p.read_bytes() for p in self.folder.iterdir()}, before)

    def test_real_failed_help_output_is_operational_two(self):
        with open('/dev/full', 'wb') as sink: r = self.command(['--help'], stdout=sink, stderr=subprocess.PIPE)
        self.assertEqual((r.returncode, r.stderr), (2, b'REJECTED: PREFLIGHT_INSPECT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_failed_usage_stderr_does_not_escape_or_become_success(self):
        with open('/dev/full', 'wb') as sink: r = self.command([], stdout=subprocess.PIPE, stderr=sink)
        self.assertEqual((r.returncode, r.stdout), (2, b''))

    def test_closed_stderr_and_error_path_keep_two(self):
        closed = StringIO(); closed.close()
        with patch('sys.stderr', closed): self.assertEqual(self.cli.main([*self.args()[:-1], 'bad']), 2)

    def test_inmemory_short_diagnostic_does_not_replace_two(self):
        class Short(StringIO):
            def write(self, text): return 0
        with patch('sys.stderr', Short()): self.assertEqual(self.cli.main([*self.args()[:-1], 'bad']), 2)

    def test_caller_globals_restored_on_success_and_operational_failure(self):
        before = list(sys.path), sys.dont_write_bytecode, sys.pycache_prefix, tempfile.tempdir
        self.assertEqual(self.invoke()[0], 0); self.assertEqual(self.invoke([*self.args()[:-1], 'bad'])[0], 2)
        self.assertEqual((sys.path, sys.dont_write_bytecode, sys.pycache_prefix, tempfile.tempdir), before)

    def test_consistent_receipt_does_not_open_vehicle_or_calculator_gates(self):
        r = json.loads(self.command().stdout)
        for name in ('source_identity_reauthenticated', 'arithmetic_recomputed', 'prehistory_checked', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'): self.assertIs(r[name], False)
        self.assertEqual((r['new_synthetic_model_steps'], r['new_reference_steps']), (0, 0)); self.assertEqual(r['gates']['R_BUDGET'], 'UNRESOLVED')
