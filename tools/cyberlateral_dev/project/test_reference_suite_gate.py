"""Explicit child execution and immutable normal receipt pins, never a self-updated baseline."""

import contextlib
import hashlib
import importlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT, package_feature

PIN = '6dba6db52bbaf8a5e602a4c2266a2e29908629f894683c67bcdb11adaf32dead'
NAMES = ('core_reference_one.json', 'core_reference_two.json', 'core_reference_one.log', 'core_reference_two.log')


class ReferenceSuiteGateTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/reference_suite_gate.py').is_file(), 'Missing CORE33 reference suite gate')
        self.model = package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.reference_suite_gate')
        self.v: Any = importlib.import_module('integration_tools.verify')
        from integration_tools.core_reference_suite import run_reference_suite
        from integration_tools.scenario_output import canonical
        self.raw = canonical(run_reference_suite())

    def summarize(self, a=None, b=None):
        return self.m.reference_suite_pair_summary(self.raw if a is None else a, self.raw if b is None else b)

    def corrupt(self, change):
        r = json.loads(self.raw); change(r)
        return self.v.canonical(r)

    def fake_run(self, raw=None, fail=None):
        calls = []
        def run(args, log, cwd):
            calls.append((args, log, cwd))
            with log.open('xb') as stream: stream.write(b'CHILD_LOG' if fail == len(calls) else self.raw)
            if fail == len(calls): raise RuntimeError('CHILD_FAILED')
            return self.raw if raw is None else raw
        return calls, run

    def test_real_normal_receipt_matches_prior_sealed_identity_and_summary(self):
        self.assertEqual((len(self.raw), hashlib.sha256(self.raw).hexdigest()), (10463, PIN))
        r = self.summarize()
        self.assertEqual((r['status'], r['invocation_count'], r['case_count_per_invocation']), ('CORE33_FIXED_REFERENCE_SUITE_GATE_PASS', 2, 6))
        self.assertEqual(r['audit_counts_per_invocation'], {'MATCH': 6, 'DIFFERENT': 0})
        self.assertEqual(r['observed_counts_per_invocation'], {'MATCH': 4, 'DIFFERENT': 1, 'REJECTED': 1})
        self.assertEqual((r['reported_model_steps_per_invocation'], r['reported_model_steps_pair']), (19, 38))
        self.assertIs(r['reported_work_is_runtime_attestation'], False)

    def test_identical_corruption_is_not_a_new_approved_baseline(self):
        changed = self.raw.replace(b'CORE32', b'CORE99')
        with self.assertRaises(ValueError): self.summarize(changed, changed)

    def test_different_runs_cannot_be_reported_byte_identical(self):
        with self.assertRaises(ValueError): self.summarize(self.raw, self.raw[:-1] + b' ')

    def test_empty_or_wrong_size_receipts_reject(self):
        for value in (b'', self.raw[:-1], self.raw + b'\n', b'x' * 10464):
            with self.subTest(size=len(value)), self.assertRaises(ValueError): self.summarize(value, value)

    def test_nonbytes_records_reject_without_coercion(self):
        for value in (self.raw.decode(), bytearray(self.raw), memoryview(self.raw), {}, False):
            with self.subTest(kind=type(value)), self.assertRaises(ValueError): self.summarize(value, value)

    def test_json_reformatting_is_not_the_canonical_pinned_receipt(self):
        pretty = json.dumps(json.loads(self.raw), indent=2).encode()
        with self.assertRaises(ValueError): self.summarize(pretty, pretty)

    def test_forged_success_counts_or_runtime_attestation_reject(self):
        for key, value in (('reported_synthetic_model_steps', 0), ('case_count', True), ('reported_work_is_runtime_attestation', True)):
            raw = self.corrupt(lambda r, k=key, v=value: r.__setitem__(k, v))
            with self.subTest(key=key), self.assertRaises(ValueError): self.summarize(raw, raw)

    def test_opened_authority_gates_or_flags_reject(self):
        for change in (lambda r: r['gates'].__setitem__('STATIC_EVIDENCE_GATE', 'PASS'),
                       lambda r: r.__setitem__('actual_activation_allowed', True)):
            raw = self.corrupt(change)
            with self.assertRaises(ValueError): self.summarize(raw, raw)

    def test_normal_suite_difference_cannot_pass_the_gate(self):
        raw = self.corrupt(lambda r: r.update(suite_status='CLOSED_REFERENCE_SUITE_DIFFERENT', suite_exit_code=1))
        with self.assertRaises(ValueError): self.summarize(raw, raw)

    def test_byte_validator_has_zero_model_quantizer_or_reference_work(self):
        calls = []; before = sys.getprofile()
        def profile(frame, event, arg):
            if event == 'call' and (frame.f_globals.get('__name__'), frame.f_code.co_name) in {
                ('cyberlateral_dev.api', 'step'), ('cyberlateral_dev._r4.request_quantizer', 'quantize'),
                ('integration_tools.core_sequence_run_inspect', '_read_file')}:
                calls.append(frame.f_code.co_name)
        try:
            sys.setprofile(profile); self.summarize()
        finally: sys.setprofile(before)
        self.assertEqual(calls, [])

    def test_summary_does_not_alias_callers_or_claim_installed_wheel(self):
        r = self.summarize(); r['audit_counts_per_invocation']['MATCH'] = 0
        self.assertEqual(self.summarize()['audit_counts_per_invocation']['MATCH'], 6)
        self.assertEqual(r['execution_mode'], 'DEVELOPMENT_TREE_CLI_NOT_INSTALLED_WHEEL')
        self.assertEqual(r['numeric_preflight_work'], 'NONZERO_NOT_AGGREGATED')

    def test_real_two_process_cli_pair_keeps_exact_stdout_and_logs(self):
        with tempfile.TemporaryDirectory() as scratch:
            out = Path(scratch)
            r = self.v.verify_reference_suite(ROOT, Path(sys.executable), out, out)
            self.assertEqual(set(p.name for p in out.iterdir()), set(NAMES))
            for name in NAMES: self.assertEqual((out / name).read_bytes(), self.raw)
            self.assertEqual(r['file_hashes'], {name: PIN for name in NAMES[:2]})

    def test_child_command_is_explicit_twice_in_requested_external_cwd(self):
        calls, run = self.fake_run()
        with tempfile.TemporaryDirectory() as scratch:
            out = Path(scratch)
            with patch.object(self.v, '_run', side_effect=run): r = self.v.verify_reference_suite(ROOT, Path(sys.executable), out, out)
            self.assertEqual(len(calls), 2)
            for i, (args, log, cwd) in enumerate(calls):
                self.assertEqual(args, [Path(sys.executable), '-I', '-B', ROOT / 'tools/core_reference_suite.py', '--run'])
                self.assertEqual((log.name, cwd), (NAMES[i + 2], out))
            self.assertEqual(r, self.summarize())

    def test_all_artifact_collisions_reject_before_child_work(self):
        for name in NAMES:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as scratch:
                out = Path(scratch); (out / name).write_bytes(b'KEEP')
                with patch.object(self.v, '_run', side_effect=AssertionError('NO_CHILD')), self.assertRaises(RuntimeError):
                    self.v.verify_reference_suite(ROOT, Path(sys.executable), out, out)
                self.assertEqual({p.name: p.read_bytes() for p in out.iterdir()}, {name: b'KEEP'})

    def test_dangling_artifact_symlink_is_not_followed_or_replaced(self):
        with tempfile.TemporaryDirectory() as scratch:
            out = Path(scratch); link = out / NAMES[1]; link.symlink_to(out / 'missing')
            with patch.object(self.v, '_run', side_effect=AssertionError('NO_CHILD')), self.assertRaises(RuntimeError):
                self.v.verify_reference_suite(ROOT, Path(sys.executable), out, out)
            self.assertTrue(link.is_symlink()); self.assertFalse((out / 'missing').exists())

    def test_first_command_failure_preserves_log_without_retry(self):
        calls, run = self.fake_run(fail=1)
        with tempfile.TemporaryDirectory() as scratch:
            out = Path(scratch)
            with patch.object(self.v, '_run', side_effect=run), self.assertRaisesRegex(RuntimeError, 'REFERENCE_SUITE_GATE_FAILED_WORK_MAY_BE_NONZERO'):
                self.v.verify_reference_suite(ROOT, Path(sys.executable), out, out)
            self.assertEqual(len(calls), 1)
            self.assertEqual({p.name: p.read_bytes() for p in out.iterdir()}, {NAMES[2]: b'CHILD_LOG'})

    def test_invalid_first_stdout_is_saved_before_second_is_suppressed(self):
        calls, run = self.fake_run(raw=b'INVALID')
        with tempfile.TemporaryDirectory() as scratch:
            out = Path(scratch)
            with patch.object(self.v, '_run', side_effect=run), self.assertRaisesRegex(RuntimeError, 'WORK_MAY_BE_NONZERO'):
                self.v.verify_reference_suite(ROOT, Path(sys.executable), out, out)
            self.assertEqual(len(calls), 1); self.assertEqual((out / NAMES[0]).read_bytes(), b'INVALID')
            self.assertFalse((out / NAMES[1]).exists())

    def test_second_command_failure_retains_first_receipt_and_both_logs(self):
        calls, run = self.fake_run(fail=2)
        with tempfile.TemporaryDirectory() as scratch:
            out = Path(scratch)
            with patch.object(self.v, '_run', side_effect=run), self.assertRaises(RuntimeError):
                self.v.verify_reference_suite(ROOT, Path(sys.executable), out, out)
            self.assertEqual(len(calls), 2); self.assertEqual((out / NAMES[0]).read_bytes(), self.raw)
            self.assertEqual((out / NAMES[3]).read_bytes(), b'CHILD_LOG'); self.assertFalse((out / NAMES[1]).exists())

    def test_second_stdout_corruption_never_returns_partial_success(self):
        calls, normal = self.fake_run()
        def run(*a):
            raw = normal(*a); return raw if len(calls) == 1 else b'INVALID_SECOND'
        with tempfile.TemporaryDirectory() as scratch:
            out = Path(scratch)
            with patch.object(self.v, '_run', side_effect=run), self.assertRaises(RuntimeError):
                self.v.verify_reference_suite(ROOT, Path(sys.executable), out, out)
            self.assertEqual((out / NAMES[0]).read_bytes(), self.raw)
            self.assertEqual((out / NAMES[1]).read_bytes(), b'INVALID_SECOND')

    def test_baseexception_propagates_instead_of_becoming_success(self):
        with tempfile.TemporaryDirectory() as scratch:
            out = Path(scratch)
            with patch.object(self.v, '_run', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
                self.v.verify_reference_suite(ROOT, Path(sys.executable), out, out)

    def test_dev_failure_before_wheels_cannot_publish_summary_or_manifest(self):
        dev = importlib.import_module('dev')
        def prelude(args, log, cwd):
            with log.open('xb') as stream: stream.write(b'Ran 137 tests in 1s\n\nOK\n' if log.name == 'unittest.log' else b'')
            return b''
        with tempfile.TemporaryDirectory() as scratch:
            out = Path(scratch) / 'new'; error = io.StringIO()
            with (patch.object(self.v, 'verify_imports', return_value={}), patch.object(self.v, '_runtime', return_value={}),
                  patch.object(self.v, '_run', side_effect=prelude), patch.object(self.v, 'typecheck_project'),
                  patch.object(self.v, 'verify_reference_suite', side_effect=RuntimeError('REFERENCE_SUITE_GATE_FAILED_WORK_MAY_BE_NONZERO')),
                  patch.object(self.v, 'build_wheels', side_effect=AssertionError('WHEELS_MUST_NOT_RUN')), contextlib.redirect_stderr(error)):
                self.assertEqual(dev.main(['verify', '--output', str(out)]), 2)
            self.assertIn('WORK_MAY_BE_NONZERO', error.getvalue())
            self.assertTrue((out / 'unittest.log').is_file())
            self.assertFalse((out / 'SUMMARY.json').exists()); self.assertFalse((out / 'SHA256SUMS.txt').exists())

    def test_readonly_pair_validation_has_deterministic_canonical_summary(self):
        self.assertEqual(self.v.canonical(self.summarize()), self.v.canonical(self.summarize()))
