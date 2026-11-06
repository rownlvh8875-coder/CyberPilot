"""Exclusive three-file input preflight publication and honest failure custody."""

import hashlib
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT, package_feature

CASES = ('sign-cycle', 'declared-difference', 'late-invalid')
NAMES = {'PREFLIGHT.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt'}
def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(v): return (json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CorePreflightWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_sequence_preflight_workflow.py').is_file(), 'Missing CORE25 publication API')
        package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.core_sequence_preflight_workflow')
        self.report: Any = importlib.import_module('integration_tools.core_sequence_preflight_report')
        self.api: Any = importlib.import_module('integration_tools.core_sequence_archive_preflight')
        self.publisher: Any = importlib.import_module('integration_tools.core_sequence_archive_workflow')
        self.bundle = importlib.import_module('integration_tools.core_sequence_bundle')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        producer = importlib.import_module('integration_tools.core_sequence_run'); self.source = {}
        for c in CASES:
            p = self.root / c; producer.run_sequence_case(c, p)
            self.source.update({'suite/' + c + '/' + n: (p / n).read_bytes() for n in ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt')})
        self.raw = self.bundle.build_suite_archive(self.source); self.archive = self.root / 'input.zip'; self.archive.write_bytes(self.raw)
        self.output = self.root / 'output'

    def publish(self, output=None): return self.m.publish_preflight_report(self.archive, sha(self.raw), self.output if output is None else output)
    def changed(self, changes):
        files = dict(self.source)
        for c, change in changes:
            prefix = 'suite/' + c + '/'; value = json.loads(files[prefix + 'INPUT.json']); change(value)
            files[prefix + 'INPUT.json'] = canonical(value)
            files[prefix + 'SHA256SUMS.txt'] = ''.join(sha(files[prefix + n]) + '  ' + n + '\n' for n in ('INPUT.json', 'RESULTS.json')).encode()
        self.raw = self.bundle.build_suite_archive(files); self.archive.write_bytes(self.raw)
    def package(self, receipt, output=None):
        target = self.output if output is None else output
        self.assertEqual({p.name for p in target.iterdir()}, NAMES)
        r, md = self.report.report_preflight_archive(self.archive, sha(self.raw))
        self.assertEqual((target / 'PREFLIGHT.json').read_bytes(), canonical(r)); self.assertEqual((target / 'SUMMARY_KO.md').read_bytes(), md)
        manifest = ''.join(sha((target / n).read_bytes()) + '  ' + n + '\n' for n in ('PREFLIGHT.json', 'SUMMARY_KO.md')).encode()
        self.assertEqual((target / 'SHA256SUMS.txt').read_bytes(), manifest)
        self.assertEqual(receipt['files'], {n: {'sha256': sha((target / n).read_bytes()), 'byte_size': (target / n).stat().st_size} for n in NAMES})

    def test_default_rejection_is_published_with_exact_existing_artifacts(self):
        r = self.publish(); self.package(r)
        self.assertEqual((r['contract_id'], r['status']), ('CORE25_PREFLIGHT_WORKFLOW_V1', 'PREFLIGHT_REPORT_PUBLISHED'))
        self.assertEqual((r['preflight_status'], r['preflight_exit_code'], r['compatible_case_count'], r['rejected_case_count']), ('INPUTS_REJECTED', 1, 2, 1))
        self.assertEqual((r['validated_transition_count'], r['declared_transition_count'], r['recorded_model_steps']), (8, 9, 6))

    def test_now_compatible_historical_rejected_is_published_exit_zero(self):
        self.changed([('late-invalid', lambda r: r['contexts'][2].update(current_driver_hex=(1.5).hex()))])
        r = self.publish(); self.package(r); self.assertEqual((r['preflight_status'], r['preflight_exit_code']), ('INPUTS_COMPATIBLE', 0))
        saved = json.loads((self.output / 'PREFLIGHT.json').read_bytes())
        self.assertEqual(saved['case_reports'][2]['saved_status'], 'REJECTED'); self.assertEqual(saved['validated_transition_count'], 9)

    def test_all_current_rejections_are_saved_not_vacuous_success(self):
        self.changed([(c, lambda r: r['frames'][0]['request'].update(request_override=True)) for c in CASES])
        r = self.publish(); self.package(r)
        self.assertEqual((r['preflight_exit_code'], r['compatible_case_count'], r['rejected_case_count'], r['validated_transition_count']), (1, 0, 3, 0))

    def test_receipts_and_files_are_identical_across_destinations(self):
        r = self.publish(); other = self.root / 'other'; self.assertEqual(canonical(self.publish(other)), canonical(r))
        for n in NAMES: self.assertEqual((self.output / n).read_bytes(), (other / n).read_bytes())

    def test_requested_private_directory_and_file_modes(self):
        self.publish(); self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in self.output.iterdir()))

    def test_one_capture_report_verifier_renderer_and_three_readbacks(self):
        original = os.open; source_opens = []; counts = {'report': 0, 'verify': 0, 'render': 0, 'publish': 0, 'readbacks': 0}
        def opening(path, flags, *a, **kw):
            if path == self.archive:
                self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY); source_opens.append(path)
            return original(path, flags, *a, **kw)
        def profile(frame, event, arg):
            if event != 'call': return
            key = (frame.f_globals.get('__name__'), frame.f_code.co_name)
            mapping = {('integration_tools.core_sequence_preflight_report', 'report_preflight_archive'): 'report',
                ('integration_tools.core_sequence_bundle', '_verified_suite'): 'verify',
                ('integration_tools.core_sequence_preflight_report', '_markdown'): 'render',
                ('integration_tools.core_sequence_archive_workflow', '_publish'): 'publish',
                ('integration_tools.core_sequence_archive_workflow', '_readback'): 'readbacks'}
            if key in mapping: counts[mapping[key]] += 1
        sys.setprofile(profile)
        try:
            with patch('os.open', side_effect=opening): r = self.publish()
        finally: sys.setprofile(None)
        self.assertEqual(counts, {'report': 1, 'verify': 1, 'render': 1, 'publish': 1, 'readbacks': 3})
        self.assertEqual(source_opens, [self.archive]); self.package(r)

    def test_readonly_source_bytes_modes_and_other_files_are_unchanged(self):
        self.archive.chmod(0o444); before = self.archive.read_bytes(), self.archive.stat().st_mode
        self.publish(); self.assertEqual(before, (self.archive.read_bytes(), self.archive.stat().st_mode))
        self.assertEqual({p.name for p in self.root.iterdir()}, {*CASES, 'input.zip', 'output'})

    def test_malformed_sha_precedes_input_and_output_path_work(self):
        with patch.object(self.m, '_output', side_effect=AssertionError('output path')), patch('os.open', side_effect=AssertionError('input path')):
            with self.assertRaisesRegex(self.api.ArchivePreflightError, '^ARCHIVE_PREFLIGHT:PORTABLE_EXPECTED_SHA256$'):
                self.m.publish_preflight_report(Path('bad\0input'), 'BAD', Path('bad\0output'))
        self.assertFalse(self.output.exists())

    def test_wrong_full_sha_leaves_output_absent(self):
        with self.assertRaisesRegex(self.api.ArchivePreflightError, '^ARCHIVE_PREFLIGHT:PORTABLE_ARCHIVE_CHECKSUM$'):
            self.m.publish_preflight_report(self.archive, '0' * 64, self.output)
        self.assertFalse(self.output.exists())

    def test_corrupt_zip_leaves_output_absent(self):
        self.raw = b'broken'; self.archive.write_bytes(self.raw)
        with self.assertRaises(self.api.ArchivePreflightError): self.publish()
        self.assertFalse(self.output.exists())

    def test_report_cap_failure_precedes_mkdir(self):
        with patch.object(self.report, 'REPORT_CAP', 1), self.assertRaisesRegex(self.report.PreflightReportError, '^PREFLIGHT_REPORT_SIZE$'): self.publish()
        self.assertFalse(self.output.exists())

    def test_serialization_failure_precedes_mkdir(self):
        with patch.object(self.m, 'canonical', side_effect=ValueError('encoding failed')), self.assertRaisesRegex(ValueError, '^encoding failed$'): self.publish()
        self.assertFalse(self.output.exists())

    def test_unknown_current_status_cannot_publish(self):
        r, md = self.report.report_preflight_archive(self.archive, sha(self.raw)); r['preflight_status'] = 'UNKNOWN'
        with patch.object(self.m, 'report_preflight_archive', return_value=(r, md)), self.assertRaises(KeyError): self.publish()
        self.assertFalse(self.output.exists())

    def test_existing_output_is_preserved_without_input_capture(self):
        self.output.mkdir(); sentinel = self.output / 'keep'; sentinel.write_bytes(b'unchanged')
        with patch('os.open', side_effect=AssertionError('capture')), self.assertRaisesRegex(self.publisher.ArchiveWorkflowError, '^ARCHIVE_WORKFLOW_OUTPUT_EXISTS$'): self.publish()
        self.assertEqual(sentinel.read_bytes(), b'unchanged')

    def test_bad_output_path_parent_symlink_and_checkout_guards(self):
        link = self.root / 'link'; link.symlink_to(self.root, target_is_directory=True)
        for p in (self.root / 'missing' / 'child', link / 'child', ROOT / 'core25-output', Path('bad\0name'), Path('bad\ud800'), 'not Path'):
            with self.subTest(path=repr(p)), self.assertRaises(self.publisher.ArchiveWorkflowError): self.publish(p)
        self.assertFalse((self.root / 'child').exists()); self.assertFalse((ROOT / 'core25-output').exists())

    def test_dangling_output_symlink_is_not_followed(self):
        self.output.symlink_to(self.root / 'missing')
        with self.assertRaises(self.publisher.ArchiveWorkflowError): self.publish()
        self.assertTrue(self.output.is_symlink())

    def test_short_writes_complete_every_file(self):
        original = os.write
        with patch('os.write', side_effect=lambda fd, raw: original(fd, raw[:13])): r = self.publish()
        self.package(r)

    def test_nonpositive_progress_preserves_partial_directory(self):
        with patch('os.write', return_value=0), self.assertRaisesRegex(self.publisher.ArchiveWorkflowError, 'PARTIAL_DIRECTORY_POSSIBLE'): self.publish()
        self.assertTrue(self.output.is_dir()); self.assertTrue((self.output / 'PREFLIGHT.json').exists())

    def test_later_write_failure_preserves_complete_first_artifact(self):
        original = os.write
        def writing(fd, raw):
            if os.readlink('/proc/self/fd/' + str(fd)).endswith('SUMMARY_KO.md'): raise OSError('disk full')
            return original(fd, raw)
        with patch('os.write', side_effect=writing), self.assertRaises(self.publisher.ArchiveWorkflowError): self.publish()
        self.assertEqual(json.loads((self.output / 'PREFLIGHT.json').read_bytes())['case_count'], 3)

    def test_creation_race_never_overwrites_competitor(self):
        original = os.mkdir
        def racing(path, *a, **kw):
            if path == self.output: original(path, *a, **kw); (path / 'sentinel').write_bytes(b'keep')
            return original(path, *a, **kw)
        with patch('os.mkdir', side_effect=racing), self.assertRaises(self.publisher.ArchiveWorkflowError): self.publish()
        self.assertEqual([p.name for p in self.output.iterdir()], ['sentinel'])

    def test_readback_corruption_never_returns_success(self):
        original = os.read
        def reading(fd, size):
            raw = original(fd, size)
            return b'X' + raw[1:] if raw and os.readlink('/proc/self/fd/' + str(fd)).endswith('PREFLIGHT.json') else raw
        with patch('os.read', side_effect=reading), self.assertRaisesRegex(self.publisher.ArchiveWorkflowError, 'CHECK_FAILED_DIRECTORY_MAY_EXIST'): self.publish()
        self.assertTrue(self.output.is_dir())

    def test_extra_output_file_is_not_accepted(self):
        original = os.write
        def writing(fd, raw):
            n = original(fd, raw); (self.output / 'extra').touch(exist_ok=True); return n
        with patch('os.write', side_effect=writing), self.assertRaises(self.publisher.ArchiveWorkflowError): self.publish()
        self.assertTrue((self.output / 'extra').exists())

    def test_fifo_readback_is_rejected_without_blocking(self):
        original = os.open
        def opening(path, flags, *a, **kw):
            if path == 'PREFLIGHT.json' and not flags & os.O_WRONLY:
                os.unlink(path, dir_fd=kw['dir_fd']); os.mkfifo(path, dir_fd=kw['dir_fd'])
            return original(path, flags, *a, **kw)
        with patch('os.open', side_effect=opening), self.assertRaises(self.publisher.ArchiveWorkflowError): self.publish()

    def test_replaced_root_cannot_return_success(self):
        original = os.listdir; replaced = False
        def listing(fd):
            nonlocal replaced
            if not replaced: self.output.rename(self.root / 'moved'); self.output.mkdir(); replaced = True
            return original(fd)
        with patch('os.listdir', side_effect=listing), self.assertRaises(self.publisher.ArchiveWorkflowError): self.publish()
        self.assertEqual({p.name for p in (self.root / 'moved').iterdir()}, NAMES)

    def test_every_authority_flag_and_gate_remains_closed(self):
        r = self.publish()
        for k in ('source_identity_reauthenticated', 'arithmetic_recomputed', 'prehistory_checked', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'): self.assertIs(r[k], False)
        self.assertEqual((r['new_synthetic_model_steps'], r['new_reference_steps']), (0, 0)); self.assertEqual(r['numeric_validation_work'], 'NONZERO_NOT_AGGREGATED')
        self.assertEqual(r['gates']['STATIC_EVIDENCE_GATE'], 'FAIL'); self.assertEqual(r['gates']['R_BUDGET'], 'UNRESOLVED')
        self.assertIsNone(r['gates']['actual_r']); self.assertIsNone(r['gates']['T2']); self.assertIsNone(r['gates']['vehicle_scale'])

    def test_helper_failure_propagates_before_output_creation(self):
        with patch.object(self.m, 'report_preflight_archive', side_effect=RuntimeError('unexpected helper failure')), self.assertRaisesRegex(RuntimeError, '^unexpected helper failure$'): self.publish()
        self.assertFalse(self.output.exists())

    def test_manifest_excludes_itself_receipt_covers_all_three_files(self):
        r = self.publish(); self.assertEqual(set(r['files']), NAMES)
        lines = (self.output / 'SHA256SUMS.txt').read_text().splitlines()
        self.assertEqual([line.split('  ', 1)[1] for line in lines], ['PREFLIGHT.json', 'SUMMARY_KO.md'])
        for line in lines:
            digest, name = line.split('  ', 1); self.assertEqual(sha((self.output / name).read_bytes()), digest)
