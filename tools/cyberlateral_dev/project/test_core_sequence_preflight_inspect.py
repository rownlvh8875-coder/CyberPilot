"""Saved report consistency, not input compatibility or numerical replay."""

import hashlib
import importlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT, package_feature

CASES = ('sign-cycle', 'declared-difference', 'late-invalid')
NAMES = ('PREFLIGHT.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt')
def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(v): return (json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CorePreflightInspectTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_sequence_preflight_inspect.py').is_file(), 'Missing CORE26 inspection API')
        package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.core_sequence_preflight_inspect')
        self.pub: Any = importlib.import_module('integration_tools.core_sequence_preflight_workflow')
        self.report: Any = importlib.import_module('integration_tools.core_sequence_preflight_report')
        self.bundle = importlib.import_module('integration_tools.core_sequence_bundle')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        producer = importlib.import_module('integration_tools.core_sequence_run'); self.source = {}
        for c in CASES:
            p = self.root / c; producer.run_sequence_case(c, p)
            self.source.update({'suite/' + c + '/' + n: (p / n).read_bytes() for n in ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt')})
        self.raw = self.bundle.build_suite_archive(self.source); self.archive = self.root / 'input.zip'; self.archive.write_bytes(self.raw)
        self.folder = self.root / 'report'; self.pub.publish_preflight_report(self.archive, sha(self.raw), self.folder)

    def inspect(self, folder=None): return self.m.inspect_preflight_report(self.folder if folder is None else folder, self.archive, sha(self.raw))
    def snapshot(self): return {p.relative_to(self.root).as_posix(): (p.read_bytes() if p.is_file() else None, p.stat().st_mode) for p in self.root.rglob('*')}
    def checksum(self):
        (self.folder / 'SHA256SUMS.txt').write_bytes(''.join(sha((self.folder / n).read_bytes()) + '  ' + n + '\n' for n in NAMES[:2]).encode())
    def changed(self, changes, publish=True):
        files = dict(self.source)
        for c, change in changes:
            prefix = 'suite/' + c + '/'; v = json.loads(files[prefix + 'INPUT.json']); change(v)
            files[prefix + 'INPUT.json'] = canonical(v)
            files[prefix + 'SHA256SUMS.txt'] = ''.join(sha(files[prefix + n]) + '  ' + n + '\n' for n in ('INPUT.json', 'RESULTS.json')).encode()
        self.raw = self.bundle.build_suite_archive(files); self.archive.write_bytes(self.raw)
        if publish:
            self.folder = self.root / 'changed-report'; self.pub.publish_preflight_report(self.archive, sha(self.raw), self.folder)

    def test_current_rejection_is_consistent_without_becoming_compatible(self):
        r = self.inspect()
        self.assertEqual((r['contract_id'], r['inspection_status'], r['inspection_exit_code']),
            ('CORE26_SAVED_PREFLIGHT_REPORT_INSPECTION_V1', 'SAVED_PREFLIGHT_REPORT_CONSISTENT', 0))
        self.assertEqual((r['preflight_status'], r['preflight_exit_code'], r['compatible_case_count'], r['rejected_case_count']), ('INPUTS_REJECTED', 1, 2, 1))
        self.assertEqual((r['validated_transition_count'], r['declared_transition_count'], r['recorded_model_steps']), (8, 9, 6))
        self.assertEqual((r['archive_sha256'], r['archive_byte_size'], r['captured_report_file_count']), (sha(self.raw), len(self.raw), 3))
        self.assertEqual(r['files'], {n: {'sha256': sha((self.folder / n).read_bytes()), 'byte_size': (self.folder / n).stat().st_size} for n in NAMES})

    def test_historical_rejected_now_compatible_retains_both_meanings(self):
        self.changed([('late-invalid', lambda r: r['contexts'][2].update(current_driver_hex=(1.5).hex()))])
        r = self.inspect(); self.assertEqual((r['inspection_exit_code'], r['preflight_exit_code'], r['compatible_case_count']), (0, 0, 3))
        self.assertEqual(json.loads((self.folder / NAMES[0]).read_bytes())['case_reports'][2]['saved_status'], 'REJECTED')

    def test_all_current_rejected_still_inspects_consistent(self):
        self.changed([(c, lambda r: r['frames'][0]['request'].update(request_override=True)) for c in CASES])
        r = self.inspect(); self.assertEqual((r['inspection_exit_code'], r['preflight_exit_code'], r['rejected_case_count'], r['validated_transition_count']), (0, 1, 3, 0))

    def test_copied_folders_have_path_independent_receipts(self):
        other = self.root / 'copy'; shutil.copytree(self.folder, other)
        self.assertEqual(canonical(self.inspect()), canonical(self.inspect(other)))

    def test_one_report_verifier_renderer_and_four_regular_captures(self):
        original = os.open; opens = []; calls = {'report': 0, 'verify': 0, 'render': 0}
        def opening(path, flags, *a, **kw):
            self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY)
            if not flags & os.O_DIRECTORY: opens.append(path)
            return original(path, flags, *a, **kw)
        def profile(frame, event, arg):
            if event != 'call': return
            key = (frame.f_globals.get('__name__'), frame.f_code.co_name)
            mapping = {('integration_tools.core_sequence_preflight_report', 'report_preflight_archive'): 'report',
                ('integration_tools.core_sequence_bundle', '_verified_suite'): 'verify', ('integration_tools.core_sequence_preflight_report', '_markdown'): 'render'}
            if key in mapping: calls[mapping[key]] += 1
        sys.setprofile(profile)
        try:
            with patch('os.open', side_effect=opening): self.inspect()
        finally: sys.setprofile(None)
        self.assertEqual(calls, {'report': 1, 'verify': 1, 'render': 1}); self.assertEqual(opens, [self.archive, *NAMES])

    def test_readonly_inputs_no_filesystem_writes_and_layout_unchanged(self):
        self.archive.chmod(0o444)
        for p in self.folder.iterdir(): p.chmod(0o400)
        self.folder.chmod(0o500); before = self.snapshot()
        try:
            with patch('os.write', side_effect=AssertionError('write')), patch('os.mkdir', side_effect=AssertionError('mkdir')): self.inspect()
            self.assertEqual(self.snapshot(), before)
        finally: self.folder.chmod(0o700)

    def test_bad_sha_precedes_all_caller_path_work(self):
        with patch.object(self.m, '_path', side_effect=AssertionError('path')), patch('os.open', side_effect=AssertionError('open')):
            for digest in ('', 'A' * 64, '0' * 63, None, 3):
                with self.subTest(digest=digest), self.assertRaises(self.m.ArchivePreflightError): self.m.inspect_preflight_report(None, None, digest)

    def test_invalid_root_and_layout_precede_archive_capture(self):
        with patch.object(self.m, 'report_preflight_archive', side_effect=AssertionError('archive')):
            for value in ('not Path', Path('bad\0path'), Path('bad\ud800'), self.root / 'absent'):
                with self.subTest(value=repr(value)), self.assertRaises(self.m.PreflightInspectError): self.inspect(value)
            (self.folder / 'extra').write_bytes(b'x')
            with self.assertRaises(self.m.PreflightInspectError): self.inspect()

    def test_wrong_sha_rejects_before_report_file_reads(self):
        with patch.object(self.m, '_read_file', side_effect=AssertionError('report read')), self.assertRaises(self.m.ArchivePreflightError):
            self.m.inspect_preflight_report(self.folder, self.archive, '0' * 64)

    def test_corrupt_zip_rejects_before_report_file_reads(self):
        self.raw = b'bad zip'; self.archive.write_bytes(self.raw)
        with patch.object(self.m, '_read_file', side_effect=AssertionError('report read')), self.assertRaises(self.m.ArchivePreflightError): self.inspect()

    def test_coherently_changed_json_rejects_despite_valid_checksum(self):
        p = self.folder / NAMES[0]; value = json.loads(p.read_bytes()); value['compatible_case_count'] = 3; p.write_bytes(canonical(value)); self.checksum()
        with self.assertRaises(self.m.PreflightInspectError) as found: self.inspect()
        self.assertEqual(found.exception.code, 'PREFLIGHT_INSPECT_REPORT_MISMATCH')

    def test_coherently_changed_markdown_rejects(self):
        p = self.folder / NAMES[1]; raw = p.read_bytes(); p.write_bytes(raw.replace(b'CORE23', b'CORE99', 1)); self.checksum()
        with self.assertRaises(self.m.PreflightInspectError): self.inspect()

    def test_missing_extra_and_checksum_self_entry_reject(self):
        for index, action in enumerate(('missing', 'extra', 'manifest')):
            folder = self.root / str(index); shutil.copytree(self.folder, folder)
            if action == 'missing': (folder / NAMES[0]).unlink()
            elif action == 'extra': (folder / 'stdout-receipt.json').write_bytes(b'{}')
            else: (folder / NAMES[2]).write_bytes((folder / NAMES[2]).read_bytes() + b'0  SHA256SUMS.txt\n')
            with self.subTest(action=action), self.assertRaises(self.m.PreflightInspectError): self.inspect(folder)

    def test_root_and_member_symlinks_reject(self):
        link = self.root / 'link'; link.symlink_to(self.folder, target_is_directory=True)
        with self.assertRaises(self.m.PreflightInspectError): self.inspect(link)
        for index, name in enumerate(NAMES):
            folder = self.root / str(index); shutil.copytree(self.folder, folder); (folder / name).unlink(); (folder / name).symlink_to(self.folder / name)
            with self.subTest(name=name), self.assertRaises(self.m.PreflightInspectError): self.inspect(folder)

    def test_fifo_and_directory_members_reject_without_blocking(self):
        for index, directory in enumerate((False, True)):
            folder = self.root / str(index); shutil.copytree(self.folder, folder); p = folder / NAMES[0]; p.unlink()
            if directory: p.mkdir()
            else: os.mkfifo(p)
            with self.subTest(directory=directory), self.assertRaises(self.m.PreflightInspectError): self.inspect(folder)

    def test_report_caps_reject_oversized_member_before_read(self):
        p = self.folder / NAMES[0]; p.write_bytes(p.read_bytes() + b'X')
        with self.assertRaises(self.m.PreflightInspectError) as found: self.inspect()
        self.assertEqual(found.exception.code, 'PREFLIGHT_INSPECT:RUN_INSPECT_SIZE')

    def test_short_reads_complete_and_stay_within_expected_caps(self):
        real_read = os.read; bounds = {}; original = self.m._read_file
        def read_file(fd, name, cap):
            bounds[name] = cap
            with patch('os.read', side_effect=lambda f, n: real_read(f, min(n, 7))): return original(fd, name, cap)
        with patch.object(self.m, '_read_file', side_effect=read_file): r = self.inspect()
        self.assertEqual(bounds, {n: (self.folder / n).stat().st_size for n in NAMES}); self.assertEqual(r['inspection_exit_code'], 0)

    def test_truncated_read_is_not_consistent(self):
        original = self.m._read_file
        with patch.object(self.m, '_read_file', side_effect=lambda fd, name, cap: original(fd, name, cap)[:-1]), self.assertRaises(self.m.PreflightInspectError): self.inspect()

    def test_growing_file_read_is_bounded_and_rejected(self):
        original = os.read; grown = False
        def reading(fd, size):
            nonlocal grown
            if not grown and Path('/proc/self/fd/' + str(fd)).resolve() == self.folder / NAMES[0]:
                with (self.folder / NAMES[0]).open('ab') as stream: stream.write(b'X')
                grown = True
            return original(fd, size)
        with patch('os.read', side_effect=reading), self.assertRaises(self.m.PreflightInspectError): self.inspect()
        self.assertTrue(grown)

    def test_root_replacement_rejects_after_capture(self):
        original = self.m._read_file
        def reading(fd, name, cap):
            raw = original(fd, name, cap)
            if name == NAMES[-1]: self.folder.rename(self.root / 'held'); self.folder.mkdir()
            return raw
        with patch.object(self.m, '_read_file', side_effect=reading), self.assertRaises(self.m.PreflightInspectError) as found: self.inspect()
        self.assertEqual(found.exception.code, 'PREFLIGHT_INSPECT_ROOT_IDENTITY')

    def test_extra_file_added_after_reads_rejects(self):
        original = self.m._read_file
        def reading(fd, name, cap):
            raw = original(fd, name, cap)
            if name == NAMES[-1]: (self.folder / 'extra').write_bytes(b'x')
            return raw
        with patch.object(self.m, '_read_file', side_effect=reading), self.assertRaises(self.m.PreflightInspectError): self.inspect()

    def test_different_valid_original_archive_cannot_authenticate_old_report(self):
        self.changed([('late-invalid', lambda r: r['contexts'][2].update(current_driver_hex=(1.5).hex()))], publish=False)
        with self.assertRaises(self.m.PreflightInspectError): self.inspect()

    def test_presentation_failure_and_unknown_current_status_precede_saved_reads(self):
        with patch.object(self.report, 'REPORT_CAP', 1), patch.object(self.m, '_read_file', side_effect=AssertionError('saved read')), self.assertRaises(self.m.PreflightReportError): self.inspect()
        receipt, md = self.report.report_preflight_archive(self.archive, sha(self.raw)); receipt['preflight_status'] = 'UNKNOWN'
        with patch.object(self.m, 'report_preflight_archive', return_value=(receipt, md)), patch.object(self.m, '_read_file', side_effect=AssertionError('saved read')), self.assertRaises(KeyError): self.inspect()

    def test_no_model_reference_publisher_or_f61_execution(self):
        def profile(frame, event, arg):
            if event == 'call':
                module = frame.f_globals.get('__name__', ''); name = frame.f_code.co_name
                if name in ('run_sequence_case', 'publish_preflight_report', '_publish', 'step', 'step_normalized') or module.startswith('integration_tools.f61_'):
                    raise AssertionError('unexpected execution')
        sys.setprofile(profile)
        try: r = self.inspect()
        finally: sys.setprofile(None)
        self.assertEqual((r['new_synthetic_model_steps'], r['new_reference_steps']), (0, 0)); self.assertEqual(r['numeric_validation_work'], 'NONZERO_NOT_AGGREGATED')

    def test_unchanged_false_authority_flags_and_denial_gates(self):
        r = self.inspect()
        for key in ('execution_requested', 'source_identity_reauthenticated', 'arithmetic_recomputed', 'prehistory_checked', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'): self.assertIs(r[key], False)
        self.assertEqual(r['gates']['R_BUDGET'], 'UNRESOLVED'); self.assertEqual(r['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')

    def test_unexpected_internal_failure_is_not_partial_success(self):
        with patch.object(self.m, 'report_preflight_archive', side_effect=AssertionError('internal')), self.assertRaises(AssertionError): self.inspect()
