"""Catch unpinned summaries,false semantic authority,unbounded reads and hidden replay."""

import builtins
import copy
import hashlib
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

import test_recording_reference_workflow as fixtures
from v1_helpers import ROOT


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class ReferencePackageIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/reference_package_integrity.py').is_file(), 'Missing CORE71 integrity API')
        self.script = ROOT / 'tools/reference_package_inspect.py'
        self.assertTrue(self.script.is_file(), 'Missing CORE71 inspect CLI')
        self.case = fixtures.ReferenceWorkflowTests('test_full_literal_record_is_saved_after_one_real_checker_and_publish')
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.case.publish()
        self.root, self.package = self.case.root, self.case.output
        self.m: Any = importlib.import_module('integration_tools.reference_package_integrity')
        spec = importlib.util.spec_from_file_location('core71_test_cli', self.script)
        assert spec is not None and spec.loader is not None
        self.cli: Any = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.cli)

    def pin(self):
        return hashlib.sha256((self.package / 'SHA256SUMS.txt').read_bytes()).hexdigest()

    def inspect(self):
        return self.m.inspect_reference_package(self.package, self.pin())

    def args(self):
        return ['--input-root', str(self.package), '--expected-manifest-sha256', self.pin()]

    def reseal(self):
        raw = ''.join(hashlib.sha256((self.package / n).read_bytes()).hexdigest() + '  ' + n + '\n'
                      for n in ('REFERENCE_AUDIT.json', 'SUMMARY_KO.md')).encode()
        (self.package / 'SHA256SUMS.txt').write_bytes(raw)

    def replace_json(self, value):
        (self.package / 'REFERENCE_AUDIT.json').write_bytes(canonical(value))
        self.reseal()

    def record(self):
        return json.loads((self.package / 'REFERENCE_AUDIT.json').read_bytes())

    def reject(self, code=None, call=None):
        with self.assertRaises(ValueError) as found:
            (self.inspect if call is None else call)()
        if code:
            self.assertEqual(str(found.exception), code)

    def invoke(self, args=None):
        target, err = self.root / 'inspect.stdout', StringIO()
        with target.open('wb') as stream, patch('sys.stdout', stream), patch('sys.stderr', err):
            code = self.cli.main(self.args() if args is None else args)
        return code, target.read_bytes(), err.getvalue()

    def expected(self):
        return {'schema_version': 1, 'contract_id': 'CORE71_REFERENCE_PACKAGE_INTEGRITY_INSPECTION_V1',
            'inspection_status': 'REFERENCE_PACKAGE_INTEGRITY_VERIFIED', 'inspection_exit_code': 0,
            'manifest_sha256': self.pin(), 'captured_file_count': 3,
            'files': {n: {'sha256': hashlib.sha256((self.package / n).read_bytes()).hexdigest(),
                         'byte_size': (self.package / n).stat().st_size}
                      for n in ('REFERENCE_AUDIT.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt')},
            'envelope_validation': 'CORE69_IDENTIFICATION_AND_CLOSED_AUTHORITY_FLAGS_ONLY',
            'audit_semantics_validated': False, 'summary_consistency_checked': False,
            'recorded_work_counts_validated': False, 'original_input_verified': False, 'arithmetic_recomputed': False,
            'new_synthetic_model_steps': 0, 'new_reference_steps': 0,
            **{n: False for n in self.case.case.m.FLAGS}, 'gates': self.case.fixture.expected()['gates'],
            'scope': 'CAPTURED_THREE_FILE_INTEGRITY_ENVELOPE_NOT_AUDIT_SEMANTIC_NUMERICAL_OR_ORIGIN_PROOF'}

    # Break: treating a stored audit MATCH as fresh arithmetic or invoking the producer.
    def test_real_package_has_exact_integrity_receipt_and_zero_new_work(self):
        with patch.object(self.case.case.m, '_launch', side_effect=AssertionError('reference')), \
                patch.object(self.case.m, 'check_recording_reference', side_effect=AssertionError('checker')):
            result, counts = self.case.fixture.base.counted(self.inspect)
        self.assertEqual(result, self.expected())
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_actual_different_audit_package_still_has_inspection_exit_zero(self):
        producer = self.case.case
        producer.record['rows'][-1]['computed_next_state']['previous_applied'] = 202
        producer.record['rows'][-1]['declared_saved_state']['saved_limited_state'] = 202
        producer.persist()
        self.package = self.root / 'different package'
        receipt = self.case.publish(self.package)
        self.assertEqual(receipt['audit_exit_code'], 1)
        self.assertEqual(self.inspect(), self.expected())

    def test_changed_json_or_summary_cannot_pass_original_manifest(self):
        for name in ('REFERENCE_AUDIT.json', 'SUMMARY_KO.md'):
            path = self.package / name
            raw = path.read_bytes()
            path.write_bytes(raw + b' ')
            self.reject('REFERENCE_PACKAGE_CHECKSUM')
            path.write_bytes(raw)

    def test_rehashed_summary_manifest_does_not_bypass_external_manifest_pin(self):
        original = self.pin()
        (self.package / 'SUMMARY_KO.md').write_bytes(b'changed summary\n')
        self.reseal()
        self.assertNotEqual(self.pin(), original)
        self.reject('REFERENCE_PACKAGE_CHECKSUM', lambda: self.m.inspect_reference_package(self.package, original))

    def test_invalid_external_pin_precedes_all_caller_path_work(self):
        for digest in (None, True, 'A' * 64, '0' * 63, 'g' * 64):
            with patch('os.open', side_effect=AssertionError('open')):
                self.reject('REFERENCE_PACKAGE_EXPECTED_MANIFEST_SHA256',
                            lambda digest=digest: self.m.inspect_reference_package(Path('/missing'), digest))

    def test_manifest_names_order_spacing_duplicates_and_trailing_data_reject(self):
        original = (self.package / 'SHA256SUMS.txt').read_bytes()
        one, two = original.splitlines(keepends=True)
        for raw in (two + one, one + one, original.rstrip(b'\n'), original + b'\n',
                    original.replace(b'  ', b' '), original.replace(b'SUMMARY_KO.md', b'../SUMMARY_KO.md')):
            (self.package / 'SHA256SUMS.txt').write_bytes(raw)
            self.reject('REFERENCE_PACKAGE_CHECKSUM')

    def test_json_requires_canonical_object_without_float_duplicate_or_constant(self):
        original = self.record()
        variants = [b'{}', b'[]\n', b'{"a":1,"a":1}\n', b'{"a":NaN}\n',
                    canonical({**original, 'extra': 1.5}), json.dumps(original, indent=2).encode() + b'\n', b'\xff']
        for raw in variants:
            (self.package / 'REFERENCE_AUDIT.json').write_bytes(raw)
            self.reseal()
            self.reject('REFERENCE_PACKAGE_JSON')

    def test_required_envelope_and_exact_false_authority_flags_reject(self):
        original = self.record()
        variants = [dict(original, schema_version=True), dict(original, schema_version=2),
                    dict(original, contract_id='OTHER'), dict(original, scope='OTHER')]
        for name in self.case.case.m.FLAGS:
            variants.extend((dict(original, **{name: True}), dict(original, **{name: 0})))
        del_variant = copy.deepcopy(original)
        del del_variant['gates']
        variants.append(del_variant)
        for value in variants:
            self.replace_json(value)
            self.reject('REFERENCE_PACKAGE_ENVELOPE')

    def test_changed_gate_values_and_extra_gate_keys_are_not_accepted(self):
        original = self.record()
        for key, value in [('R_BUDGET', 'RESOLVED'), ('actual_r', 0), ('unexpected', 'value')]:
            changed = copy.deepcopy(original)
            changed['gates'][key] = value
            self.replace_json(changed)
            self.reject('REFERENCE_PACKAGE_ENVELOPE')

    def test_unknown_or_misleading_audit_body_is_explicitly_not_semantically_validated(self):
        changed = self.record()
        changed.update(audit_status='UNVALIDATED_CLAIM', audit_exit_code=999,
                       reference_identity={'untrusted': 'DO_NOT_COPY'}, new_reference_steps=False,
                       rows='NOT_A_TYPED_AUDIT_RECORD', extra='UNTRUSTED_EXTRA')
        self.replace_json(changed)
        (self.package / 'SUMMARY_KO.md').write_bytes(b'semantically unrelated summary\n')
        self.reseal()
        value = self.inspect()
        self.assertEqual(value, self.expected())
        self.assertFalse(value['audit_semantics_validated'])
        self.assertFalse(value['summary_consistency_checked'])
        self.assertNotIn(b'UNVALIDATED_CLAIM', canonical(value))
        self.assertNotIn(b'DO_NOT_COPY', canonical(value))

    def test_invalid_summary_utf8_rejects_even_with_coherent_hashes(self):
        (self.package / 'SUMMARY_KO.md').write_bytes(b'\xff\xfe')
        self.reseal()
        self.reject('REFERENCE_PACKAGE_SUMMARY_UTF8')

    def test_exact_flat_layout_rejects_missing_extra_directory_symlink_and_fifo(self):
        extra = self.package / 'extra'
        extra.write_bytes(b'x')
        self.reject('REFERENCE_PACKAGE_INPUT')
        extra.unlink()
        file = self.package / 'SUMMARY_KO.md'
        raw = file.read_bytes()
        file.unlink()
        self.reject('REFERENCE_PACKAGE_INPUT')
        file.mkdir()
        self.reject('REFERENCE_PACKAGE_INPUT')
        file.rmdir()
        outside = self.root / 'outside summary'
        outside.write_bytes(raw)
        file.symlink_to(outside)
        self.reject('REFERENCE_PACKAGE_INPUT')
        file.unlink()
        os.mkfifo(file)
        self.reject('REFERENCE_PACKAGE_INPUT')

    def test_symlink_root_and_ancestor_are_rejected(self):
        link = self.root / 'link'
        link.symlink_to(self.package, target_is_directory=True)
        self.reject('REFERENCE_PACKAGE_INPUT', lambda: self.m.inspect_reference_package(link, self.pin()))
        parent = self.root / 'ancestor'
        parent.symlink_to(self.root, target_is_directory=True)
        self.reject('REFERENCE_PACKAGE_INPUT', lambda: self.m.inspect_reference_package(parent / self.package.name, self.pin()))

    def test_all_file_minimum_and_maximum_limits_are_enforced(self):
        original_pin = self.pin()
        for name, cap in [('REFERENCE_AUDIT.json', 2097152), ('SUMMARY_KO.md', 65536), ('SHA256SUMS.txt', 512)]:
            file = self.package / name
            original = file.read_bytes()
            for raw in (b'', b'x' * (cap + 1)):
                file.write_bytes(raw)
                self.reject('REFERENCE_PACKAGE_INPUT', lambda: self.m.inspect_reference_package(self.package, original_pin))
            file.write_bytes(original)

    def test_three_single_captures_close_all_descriptors_before_envelope_checks(self):
        original_open, original_envelope = os.open, self.m._envelope
        descriptors = []
        def opening(*args, **kw):
            fd = original_open(*args, **kw)
            descriptors.append(fd)
            return fd
        def checking(value):
            self.assertEqual(len(descriptors), 4)
            for fd in descriptors:
                with self.assertRaises(OSError):
                    os.fstat(fd)
            return original_envelope(value)
        with patch('os.open', side_effect=opening), patch.object(self.m, '_envelope', side_effect=checking), \
                patch.object(self.m, '_read_file', wraps=self.m._read_file) as read:
            self.assertEqual(self.inspect(), self.expected())
        self.assertEqual([x.args[1] for x in read.call_args_list], ['REFERENCE_AUDIT.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt'])

    def test_replacement_after_capture_cannot_change_captured_result(self):
        expected, original = self.expected(), self.m._envelope
        def checking(value):
            for p in self.package.iterdir():
                p.write_bytes(b'later replacement')
            return original(value)
        with patch.object(self.m, '_envelope', side_effect=checking):
            self.assertEqual(self.inspect(), expected)

    def test_late_read_error_closes_all_descriptors_without_success(self):
        original_open, original_read = os.open, self.m._read_file
        descriptors = []
        def opening(*args, **kw):
            fd = original_open(*args, **kw); descriptors.append(fd); return fd
        def reading(fd, name, cap):
            if name == 'SHA256SUMS.txt':
                raise OSError('private late read')
            return original_read(fd, name, cap)
        with patch('os.open', side_effect=opening), patch.object(self.m, '_read_file', side_effect=reading):
            self.reject('REFERENCE_PACKAGE_INPUT')
        for fd in descriptors:
            with self.assertRaises(OSError):
                os.fstat(fd)

    def test_inputs_remain_byte_mode_and_file_set_identical(self):
        before = {p.name: (p.read_bytes(), p.stat().st_mode) for p in self.package.iterdir()}
        self.inspect()
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mode) for p in self.package.iterdir()})

    def test_cold_no_site_packages_or_algorithm_imports_are_needed(self):
        program = '''import importlib.abc,runpy,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.startswith(('cyberlateral_dev','numpy','project.kernel','project.normalized_reference','integration_tools.recording_diagnostics_reference','integration_tools.recording_reference_workflow')):
   raise AssertionError('ALGORITHM_IMPORT_FORBIDDEN')
sys.meta_path.insert(0,Block())
sys.argv=sys.argv[1:]
runpy.run_path(sys.argv[0],run_name='__main__')
'''
        p = subprocess.run([sys.executable, '-I', '-B', '-S', '-c', program, str(self.script), *self.args()],
                           cwd=self.root, capture_output=True)
        self.assertEqual((p.returncode, p.stderr), (0, b''))
        self.assertEqual(json.loads(p.stdout), self.expected())

    def test_cli_unique_flags_no_run_and_bad_pin_reject_before_project_imports(self):
        original, args = builtins.__import__, self.args()
        def importing(name, *a, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')):
                raise AssertionError('project import')
            return original(name, *a, **kw)
        variants = [[], args[:2], args[2:], args + ['--run'], args + args[:2], args + args[2:],
                    args[:-1] + ['A' * 64], args + ['--r', '0'], args + ['--input', 'x'], args[:-1] + ['']]
        for argv in variants:
            with patch('builtins.__import__', side_effect=importing), patch('os.open', side_effect=AssertionError('open')), \
                    patch('sys.stderr', StringIO()) as err, self.assertRaises(SystemExit) as found:
                self.cli.main(argv)
            self.assertEqual((found.exception.code, err.getvalue()), (2, 'REJECTED: REFERENCE_PACKAGE_INSPECT_USAGE_NO_EXECUTION\n'))

    def test_cli_help_restores_globals_without_inspection(self):
        paths = list(sys.path)
        with patch.object(sys, 'dont_write_bytecode', False), patch('sys.stdout', StringIO()) as out, \
                patch.object(self.m, 'inspect_reference_package', side_effect=AssertionError('inspect')), self.assertRaises(SystemExit) as found:
            self.cli.main(['--help'])
        self.assertEqual(found.exception.code, 0)
        self.assertIn('--expected-manifest-sha256', out.getvalue())
        self.assertEqual(sys.path, paths)

    def test_positive_short_stdout_writes_complete_one_inspection(self):
        original = os.write
        def short(fd, raw):
            return original(fd, raw[:13]) if fd == sys.stdout.fileno() else original(fd, raw)
        with patch('os.write', side_effect=short), patch.object(self.m, 'inspect_reference_package', wraps=self.m.inspect_reference_package) as run:
            code, raw, err = self.invoke()
        self.assertEqual((code, err, run.call_count), (0, '', 1))
        self.assertEqual(json.loads(raw), self.expected())

    def test_stdout_prefix_then_failure_is_not_a_success_receipt_or_retry(self):
        original, sent = os.write, []
        def broken(fd, raw):
            if fd != sys.stdout.fileno():
                return original(fd, raw)
            if not sent:
                sent.append(True); return original(fd, raw[:9])
            return 0
        with patch('os.write', side_effect=broken), patch.object(self.m, 'inspect_reference_package', wraps=self.m.inspect_reference_package) as run:
            code, raw, err = self.invoke()
        self.assertEqual((code, len(raw), run.call_count), (2, 9, 1))
        self.assertIn('REFERENCE_PACKAGE_INSPECT_FAILED_NO_EXECUTION', err)

    def test_broken_stdout_and_unknown_error_have_fixed_codes_and_restore_globals(self):
        paths, original = list(sys.path), os.write
        def broken(fd, raw):
            if fd == sys.stdout.fileno():
                raise BrokenPipeError('private caller data')
            return original(fd, raw)
        with patch.object(sys, 'dont_write_bytecode', False), patch('os.write', side_effect=broken):
            code, raw, err = self.invoke()
            self.assertFalse(sys.dont_write_bytecode)
        self.assertEqual((code, raw), (2, b''))
        self.assertNotIn('private caller data', err)
        self.assertEqual(sys.path, paths)

    def test_fresh_repeated_cli_output_is_byte_identical_and_does_not_write(self):
        before = {p.name: p.read_bytes() for p in self.package.iterdir()}
        cmd = [sys.executable, '-I', '-B', str(self.script), *self.args()]
        one, two = (subprocess.run(cmd, cwd=self.root, capture_output=True) for _ in range(2))
        self.assertEqual((one.returncode, two.returncode, one.stderr, two.stderr), (0, 0, b'', b''))
        self.assertEqual(one.stdout, two.stdout)
        self.assertEqual(json.loads(one.stdout), self.expected())
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.package.iterdir()})


if __name__ == '__main__':
    unittest.main()
