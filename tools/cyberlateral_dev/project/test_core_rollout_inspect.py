"""Pinned saved bytes: no producer, semantic parse or numeric execution in inspection."""

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
NAMES = ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt')


class CoreRolloutInspectTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_rollout_inspect.py').is_file(), 'Missing CORE29 pinned inspection API')
        package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.core_rollout_inspect')
        producer = importlib.import_module('integration_tools.core_rollout_run')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        for case in CASES: producer.run_rollout_case(case, self.root / case)
        self.folder = self.root / 'sign-cycle'

    def inspect(self, case='sign-cycle', folder=None): return self.m.inspect_rollout_case(case, self.folder if folder is None else folder)
    def reject(self, code, case='sign-cycle', folder=None):
        with self.assertRaises(self.m.RolloutInspectError) as found: self.inspect(case, folder)
        self.assertEqual(found.exception.code, code)
    def snapshot(self): return {p.relative_to(self.root).as_posix(): (p.read_bytes(), p.stat().st_mode) for p in self.root.rglob('*') if p.is_file()}

    def test_three_historical_statuses_all_inspect_zero_without_reclassifying(self):
        for case, status, code, steps in zip(CASES, ('MATCH', 'DIFFERENT', 'REJECTED'), (0, 1, 2), (3, 3, 0), strict=True):
            with self.subTest(case=case):
                r = self.inspect(case, self.root / case)
                self.assertEqual((r['inspection_status'], r['inspection_exit_code']), ('PINNED_CORE28_ARTIFACTS_MATCH', 0))
                self.assertEqual((r['recorded_result_status'], r['recorded_result_exit_code'], r['recorded_model_steps']), (status, code, steps))
                self.assertEqual(r['recorded_metadata_origin'], 'PINNED_CORE28_VECTOR_NOT_REPARSED')

    def test_receipt_contains_captured_full_identities_and_pinned_provenance(self):
        r = self.inspect()
        self.assertEqual(r['files'], {n: {'byte_size': (self.folder / n).stat().st_size, 'sha256': hashlib.sha256((self.folder / n).read_bytes()).hexdigest()} for n in NAMES})
        self.assertEqual(r['files']['INPUT.json'], {'byte_size': 4732, 'sha256': '5d25bdc18d3fb8d29fca5905ce111e5727572f8801dc0071280cd5adf1371309'})
        self.assertEqual(r['reference_evidence_zip_sha256'], '2e8f658c5bfa03aea6d688cded43314118d10a949abdc9f7928a3fe4b9362fdc')
        self.assertFalse(r['reference_evidence_verified_during_inspection']); self.assertTrue(r['reference_byte_match'])

    def test_closed_case_validation_precedes_any_path_access(self):
        class Foreign(str): pass
        for case in (None, 1, True, '', 'other', Foreign('sign-cycle')):
            with self.subTest(case=case), patch.object(self.m, '_path', side_effect=AssertionError('path')): self.reject('ROLLOUT_INSPECT_CASE', case)

    def test_different_valid_case_folder_is_not_interchangeable(self):
        self.reject('ROLLOUT_INSPECT_ARTIFACT_IDENTITY', case='declared-difference')

    def test_exact_three_single_bounded_captures(self):
        original = self.m._read_file; seen = []
        def capture(fd, name, cap): seen.append((name, cap)); return original(fd, name, cap)
        with patch.object(self.m, '_read_file', side_effect=capture): r = self.inspect()
        self.assertEqual(seen, [('INPUT.json', 4732), ('RESULTS.json', 2908), ('SHA256SUMS.txt', 156)])
        self.assertEqual(r['captured_file_count'], 3)

    def test_inspection_never_invokes_producer_model_quantizer_or_json_decoder(self):
        calls = []; old = sys.getprofile()
        def profile(frame, event, arg):
            if event != 'call': return
            module = frame.f_globals.get('__name__', '')
            if module.startswith(('cyberlateral_dev', 'integration_tools.synthetic_', 'integration_tools.core_rollout_run', 'integration_tools.core_sequence_cases')): calls.append((module, frame.f_code.co_name))
        try:
            sys.setprofile(profile)
            with patch('json.loads', side_effect=AssertionError('decode')), patch('json.load', side_effect=AssertionError('decode')): r = self.inspect()
        finally: sys.setprofile(old)
        self.assertEqual(calls, []); self.assertEqual((r['new_synthetic_model_steps'], r['new_reference_steps']), (0, 0))

    def test_unchanged_modes_bytes_and_readonly_opens(self):
        before = self.snapshot(); original = os.open
        def opening(path, flags, *a, **kw):
            self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY)
            self.assertTrue(flags & os.O_NOFOLLOW); self.assertTrue(flags & os.O_NONBLOCK); self.assertTrue(flags & os.O_CLOEXEC)
            return original(path, flags, *a, **kw)
        with patch('os.open', side_effect=opening), patch('os.mkdir', side_effect=AssertionError('write')): self.inspect()
        self.assertEqual(self.snapshot(), before)

    def test_coherently_rechecksummed_mutation_is_still_rejected(self):
        p = self.folder / 'RESULTS.json'; p.write_bytes(p.read_bytes().replace(b'MATCH', b'OTHER', 1))
        (self.folder / 'SHA256SUMS.txt').write_bytes(''.join(hashlib.sha256((self.folder / n).read_bytes()).hexdigest() + '  ' + n + '\n' for n in NAMES[:2]).encode())
        self.reject('ROLLOUT_INSPECT_ARTIFACT_IDENTITY')

    def test_same_size_invalid_json_is_rejected_without_parsing(self):
        p = self.folder / 'INPUT.json'; raw = p.read_bytes(); p.write_bytes(b'!' + raw[1:])
        with patch('json.loads', side_effect=AssertionError('parse')): self.reject('ROLLOUT_INSPECT_ARTIFACT_IDENTITY')

    def test_semantically_equal_reformatted_json_is_not_historical_identity(self):
        p = self.folder / 'INPUT.json'; p.write_bytes(json.dumps(json.loads(p.read_bytes()), separators=(',', ':'), ensure_ascii=False).encode())
        self.reject('ROLLOUT_INSPECT_ARTIFACT_IDENTITY')

    def test_checksum_is_itself_pinned_not_trusted_or_extended(self):
        p = self.folder / 'SHA256SUMS.txt'; raw = p.read_bytes(); p.write_bytes(b'0' + raw[1:])
        self.reject('ROLLOUT_INSPECT_ARTIFACT_IDENTITY')
        p.write_bytes(raw + b'x'); self.reject('ROLLOUT_INSPECT:RUN_INSPECT_SIZE')

    def test_missing_or_extra_file_rejects_before_capture(self):
        p = self.folder / 'extra'; p.write_bytes(b'x')
        with patch.object(self.m, '_read_file', side_effect=AssertionError('capture')): self.reject('ROLLOUT_INSPECT:RUN_INSPECT_LAYOUT')
        p.unlink(); (self.folder / 'INPUT.json').unlink()
        self.reject('ROLLOUT_INSPECT:RUN_INSPECT_LAYOUT')

    def test_symlink_root_is_not_followed(self):
        link = self.root / 'link'; link.symlink_to(self.folder, target_is_directory=True)
        with self.assertRaises(self.m.RolloutInspectError): self.inspect(folder=link)

    def test_nonregular_members_reject_before_capture(self):
        p = self.folder / 'INPUT.json'; raw = p.read_bytes(); p.unlink()
        for kind in ('link', 'directory', 'fifo'):
            if kind == 'link': p.symlink_to(self.root / 'late-invalid/INPUT.json')
            elif kind == 'directory': p.mkdir()
            else: os.mkfifo(p)
            with self.subTest(kind=kind): self.reject('ROLLOUT_INSPECT:RUN_INSPECT_FILE_TYPE')
            if kind == 'directory': p.rmdir()
            else: p.unlink()
        p.write_bytes(raw)

    def test_oversize_file_rejects_before_regular_read(self):
        p = self.folder / 'INPUT.json'; p.write_bytes(p.read_bytes() + b'x')
        with patch('os.read', side_effect=AssertionError('read')): self.reject('ROLLOUT_INSPECT:RUN_INSPECT_SIZE')

    def test_truncated_file_is_identity_mismatch(self):
        p = self.folder / 'RESULTS.json'; p.write_bytes(p.read_bytes()[:-1]); self.reject('ROLLOUT_INSPECT_ARTIFACT_IDENTITY')

    def test_short_reads_capture_complete_bytes(self):
        original = os.read
        with patch('os.read', side_effect=lambda fd, count: original(fd, min(count, 7))): self.assertEqual(self.inspect()['captured_file_count'], 3)

    def test_growth_after_fstat_is_bounded_and_rejected(self):
        original = os.read; first = True
        def reading(fd, count):
            nonlocal first
            if first:
                first = False
                with (self.folder / 'INPUT.json').open('ab') as stream: stream.write(b'x')
            return original(fd, count)
        with patch('os.read', side_effect=reading): self.reject('ROLLOUT_INSPECT:RUN_INSPECT_SIZE')

    def test_root_replacement_after_capture_rejects(self):
        original = self.m._read_file
        def capture(fd, name, cap):
            raw = original(fd, name, cap)
            if name == 'SHA256SUMS.txt':
                self.folder.rename(self.root / 'moved'); self.folder.mkdir()
                for n in NAMES: (self.folder / n).write_bytes((self.root / 'moved' / n).read_bytes())
            return raw
        with patch.object(self.m, '_read_file', side_effect=capture): self.reject('ROLLOUT_INSPECT_ROOT_IDENTITY')

    def test_post_capture_extra_file_prevents_receipt(self):
        original = self.m._read_file
        def capture(fd, name, cap):
            raw = original(fd, name, cap)
            if name == 'SHA256SUMS.txt': (self.folder / 'extra').write_bytes(b'x')
            return raw
        with patch.object(self.m, '_read_file', side_effect=capture): self.reject('ROLLOUT_INSPECT:RUN_INSPECT_LAYOUT')

    def test_os_failure_is_fixed_without_raw_path(self):
        with patch.object(self.m, '_read_file', side_effect=PermissionError('PRIVATE')): self.reject('ROLLOUT_INSPECT_INPUT')

    def test_receipts_are_path_independent_without_runtime_zip_access(self):
        other = self.root / 'copy'; other.mkdir()
        for n in NAMES: (other / n).write_bytes((self.folder / n).read_bytes())
        self.assertEqual(self.inspect(), self.inspect(folder=other))

    def test_byte_match_does_not_grant_semantic_or_vehicle_authority(self):
        r = self.inspect()
        for key in ('execution_requested', 'input_semantics_revalidated', 'stored_arithmetic_recomputed', 'source_identity_reauthenticated', 'prehistory_checked', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'): self.assertIs(r[key], False)
        self.assertEqual(r['numeric_validation_work'], 'NOT_PERFORMED_SAVED_BYTES_ONLY')
        self.assertEqual((r['gates']['R_BUDGET'], r['gates']['STATIC_EVIDENCE_GATE']), ('UNRESOLVED', 'FAIL'))
