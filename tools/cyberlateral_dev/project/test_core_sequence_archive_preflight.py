"""Verified portable bytes precede all semantic work; no extraction or replay."""

import hashlib
import importlib
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT, package_feature

CASES = ('sign-cycle', 'declared-difference', 'late-invalid')
NAMES = ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt')


def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CoreArchivePreflightTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_sequence_archive_preflight.py').is_file(), 'Missing CORE21 archive semantic preflight')
        package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.core_sequence_archive_preflight')
        self.b = importlib.import_module('integration_tools.core_sequence_bundle')
        self.old = importlib.import_module('integration_tools.core_sequence_input_preflight')
        self.preparer = importlib.import_module('integration_tools.synthetic_model_input')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        producer = importlib.import_module('integration_tools.core_sequence_run'); self.source = {}
        for case in CASES:
            folder = self.root / case; producer.run_sequence_case(case, folder)
            self.source.update({'suite/' + case + '/' + n: (folder / n).read_bytes() for n in NAMES})
        self.raw = self.b.build_suite_archive(self.source); self.path = self.root / 'input.zip'; self.path.write_bytes(self.raw)

    def check(self, raw=None):
        raw = self.raw if raw is None else raw
        return self.m.preflight_suite_archive_bytes(raw, sha(raw))

    def changed(self, mutations):
        files = dict(self.source)
        for case, change in mutations:
            prefix = 'suite/' + case + '/'; value = json.loads(files[prefix + 'INPUT.json']); change(value)
            files[prefix + 'INPUT.json'] = canonical(value)
            files[prefix + 'SHA256SUMS.txt'] = ''.join(sha(files[prefix + n]) + '  ' + n + '\n' for n in ('INPUT.json', 'RESULTS.json')).encode()
        return self.b.build_suite_archive(files)

    def members(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as archive: return {n: archive.read(n) for n in archive.namelist()}

    def invalid(self, files):
        files['SHA256SUMS.txt'] = self.b._manifest(files)
        return self.b._zip(files)

    def test_default_bundle_keeps_saved_outcomes_and_current_input_counts_separate(self):
        result = self.check()
        self.assertEqual(result['contract_id'], 'CORE21_PORTABLE_SUITE_INPUT_PREFLIGHT_V1')
        self.assertEqual(result['preflight_status'], 'INPUTS_REJECTED')
        self.assertEqual((result['case_count'], result['compatible_case_count'], result['rejected_case_count']), (3, 2, 1))
        self.assertEqual((result['validated_transition_count'], result['declared_transition_count'], result['recorded_model_steps']), (8, 9, 6))
        self.assertEqual(result['case_ids'], list(CASES)); self.assertIs(result['all_cases_processed'], True)
        self.assertEqual([r['saved_status'] for r in result['case_reports']], ['MATCH', 'DIFFERENT', 'REJECTED'])
        self.assertEqual([r['rejection_code'] for r in result['case_reports']], [None, None, 'SEQUENCE_INPUT:2:MODEL_DRIVER'])

    def test_folder_bytes_path_and_existing_portable_receipts_match_exactly(self):
        result = self.check(); path_result = self.m.preflight_suite_archive(self.path, sha(self.raw))
        self.assertEqual(canonical(result), canonical(path_result))
        self.assertEqual(canonical(result['archive']), canonical(self.b.verify_suite_bytes(self.raw, sha(self.raw))))
        for case, report in zip(CASES, result['case_reports'], strict=True):
            self.assertEqual(canonical(report), canonical(self.old.preflight_saved_sequence(self.root / case)))

    def test_all_compatible_inputs_can_keep_a_historical_rejected_case(self):
        raw = self.changed([('late-invalid', lambda r: r['contexts'][2].update(current_driver_hex=(1.5).hex()))])
        result = self.check(raw)
        self.assertEqual((result['preflight_status'], result['compatible_case_count'], result['rejected_case_count']), ('INPUTS_COMPATIBLE', 3, 0))
        self.assertEqual(result['validated_transition_count'], 9); self.assertEqual(result['recorded_model_steps'], 6)
        self.assertEqual(result['case_reports'][2]['saved_status'], 'REJECTED')

    def test_all_rejected_inputs_are_not_a_vacuous_success(self):
        raw = self.changed([(case, lambda r: r['frames'][0]['request'].update(request_override=True)) for case in CASES])
        result = self.check(raw)
        self.assertEqual((result['preflight_status'], result['compatible_case_count'], result['rejected_case_count']), ('INPUTS_REJECTED', 0, 3))
        self.assertEqual(result['validated_transition_count'], 0)
        self.assertEqual([r['rejection_code'] for r in result['case_reports']], ['SEQUENCE_INPUT:0:MODEL_OVERRIDE'] * 3)

    def test_early_semantic_rejection_does_not_skip_later_cases(self):
        raw = self.changed([('sign-cycle', lambda r: r['frames'][0]['request'].update(requested_binary32_be_hex='3f800001'))])
        result = self.check(raw)
        self.assertEqual([r['case_id'] for r in result['case_reports']], list(CASES))
        self.assertEqual((result['compatible_case_count'], result['rejected_case_count'], result['validated_transition_count']), (1, 2, 5))
        self.assertEqual(result['case_reports'][0]['rejection_code'], 'SEQUENCE_INPUT:0:MODEL_LIMITER:LIMITER_REQUEST:REQUEST_WORD')

    def test_float_encoding_rejection_preserves_other_case_prefix_counts(self):
        raw = self.changed([('sign-cycle', lambda r: r['contexts'][2].update(current_driver_hex='0x1.0000000000000p-9999'))])
        result = self.check(raw)
        self.assertEqual(result['case_reports'][0]['rejection_code'], 'INPUT_PREFLIGHT_FLOAT_ENCODING:2')
        self.assertEqual(result['validated_transition_count'], 5); self.assertEqual(result['rejected_case_count'], 2)

    def test_signed_zero_reaches_existing_preparer_without_normalization(self):
        raw = self.changed([('sign-cycle', lambda r: r['contexts'][0].update(current_driver_hex='-0x0.0p+0'))])
        original = self.old.prepare_model_input; observed = []
        def prepare(previous, current, context):
            observed.append(context.current_driver.hex()); return original(previous, current, context)
        with patch.object(self.old, 'prepare_model_input', side_effect=prepare): result = self.check(raw)
        self.assertEqual(observed[0], '-0x0.0p+0'); self.assertEqual(result['case_reports'][0]['preflight_status'], 'INPUTS_COMPATIBLE')

    def test_expected_sha_format_precedes_all_caller_path_work(self):
        class Foreign:
            def __getattribute__(self, name): raise AssertionError('caller path accessed')
        for expected in ('bad', 'A' * 64, None, True, b'0' * 64):
            with self.subTest(expected=expected), patch.object(self.m, '_read_archive', side_effect=AssertionError('archive read')), self.assertRaises(self.m.ArchivePreflightError) as found:
                self.m.preflight_suite_archive(Foreign(), expected)
            self.assertEqual(found.exception.code, 'ARCHIVE_PREFLIGHT:PORTABLE_EXPECTED_SHA256')

    def test_wrong_expected_sha_precedes_any_semantic_validation(self):
        with patch.object(self.m, '_preflight_captured', side_effect=AssertionError('semantic access')), self.assertRaises(self.m.ArchivePreflightError) as found:
            self.m.preflight_suite_archive_bytes(self.raw, '0' * 64)
        self.assertEqual(found.exception.code, 'ARCHIVE_PREFLIGHT:PORTABLE_ARCHIVE_CHECKSUM')

    def test_only_exact_bytes_are_accepted_without_coercion(self):
        class Child(bytes): pass
        for raw in (bytearray(self.raw), memoryview(self.raw), Child(self.raw), 'not bytes', None):
            with self.subTest(kind=type(raw)), self.assertRaises(self.m.ArchivePreflightError) as found:
                self.m.preflight_suite_archive_bytes(raw, sha(self.raw))
            self.assertEqual(found.exception.code, 'ARCHIVE_PREFLIGHT:PORTABLE_ARCHIVE_FILE')

    def test_archive_cap_precedes_parse_or_semantic_work(self):
        raw = b'x' * 2_000_001; self.path.write_bytes(raw)
        for call in (lambda: self.check(raw), lambda: self.m.preflight_suite_archive(self.path, sha(raw))):
            with patch.object(self.m, '_preflight_captured', side_effect=AssertionError('semantic access')), self.assertRaises(self.m.ArchivePreflightError) as found: call()
            self.assertEqual(found.exception.code, 'ARCHIVE_PREFLIGHT:PORTABLE_ARCHIVE_SIZE')

    def test_damaged_zip_is_not_treated_as_semantically_rejected_input(self):
        raw = bytearray(self.raw); raw[50] ^= 1; raw = bytes(raw)
        with patch.object(self.m, '_preflight_captured', side_effect=AssertionError('semantic access')), self.assertRaises(self.m.ArchivePreflightError): self.check(raw)

    def test_bad_manifest_is_rejected_before_any_case_semantics(self):
        files = self.members(); files['SHA256SUMS.txt'] = b'wrong'; raw = self.b._zip(files)
        with patch.object(self.m, '_preflight_captured', side_effect=AssertionError('semantic access')), self.assertRaises(self.m.ArchivePreflightError) as found: self.check(raw)
        self.assertEqual(found.exception.code, 'ARCHIVE_PREFLIGHT:PORTABLE_MANIFEST')

    def test_corrupt_last_case_schema_blocks_semantics_for_every_case(self):
        files = self.members(); prefix = 'suite/late-invalid/'; value = json.loads(files[prefix + 'INPUT.json']); value.pop('contexts')
        files[prefix + 'INPUT.json'] = canonical(value)
        files[prefix + 'SHA256SUMS.txt'] = ''.join(sha(files[prefix + n]) + '  ' + n + '\n' for n in ('INPUT.json', 'RESULTS.json')).encode()
        raw = self.invalid(files)
        with patch.object(self.m, '_preflight_captured', side_effect=AssertionError('semantic access')), self.assertRaises(self.m.ArchivePreflightError) as found: self.check(raw)
        self.assertEqual(found.exception.code, 'ARCHIVE_PREFLIGHT:PORTABLE_CASE:late-invalid:INSPECT_RECORD')

    def test_altered_saved_suite_report_blocks_semantics(self):
        files = self.members(); value = json.loads(files['SUITE_REPORT.json']); value['recorded_model_steps'] = 999
        files['SUITE_REPORT.json'] = canonical(value); raw = self.invalid(files)
        with patch.object(self.m, '_preflight_captured', side_effect=AssertionError('semantic access')), self.assertRaises(self.m.ArchivePreflightError) as found: self.check(raw)
        self.assertEqual(found.exception.code, 'ARCHIVE_PREFLIGHT:PORTABLE_REPORT')

    def test_noncanonical_zip_metadata_stays_rejected(self):
        files = self.members(); buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, raw in files.items(): archive.writestr(name, raw)
        with self.assertRaises(self.m.ArchivePreflightError): self.check(buffer.getvalue())

    def test_path_capture_and_complete_archive_verification_each_run_once(self):
        original_open = os.open; original_verify = self.m._verified_suite; opened = []; verified = []
        def observe(path, flags, *a, **kw):
            self.assertFalse(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
            fd = original_open(path, flags, *a, **kw)
            if stat.S_ISREG(os.fstat(fd).st_mode): opened.append(Path(path).absolute())
            return fd
        def verify(raw, expected): verified.append((raw, expected)); return original_verify(raw, expected)
        with patch('os.open', side_effect=observe), patch.object(self.m, '_verified_suite', side_effect=verify):
            result = self.m.preflight_suite_archive(self.path, sha(self.raw))
        self.assertEqual(opened, [self.path]); self.assertEqual(verified, [(self.raw, sha(self.raw))])
        self.assertEqual(result['archive']['archive_sha256'], sha(self.raw))

    def test_bytes_variant_never_reads_paths_extracts_or_writes_files(self):
        with patch('os.open', side_effect=AssertionError('filesystem open')), patch('os.write', side_effect=AssertionError('filesystem write')), \
                patch.object(self.m, '_read_archive', side_effect=AssertionError('path capture')), \
                patch.object(zipfile.ZipFile, 'extractall', side_effect=AssertionError('extraction')):
            result = self.check()
        self.assertEqual(result['case_count'], 3)

    def test_readonly_archive_bytes_and_modes_remain_unchanged(self):
        self.path.chmod(0o444); before = (self.path.read_bytes(), self.path.stat().st_mode, set(self.root.iterdir()))
        self.m.preflight_suite_archive(self.path, sha(self.raw))
        self.assertEqual(before, (self.path.read_bytes(), self.path.stat().st_mode, set(self.root.iterdir())))

    def test_missing_symlink_fifo_and_bad_paths_reject_with_fixed_codes(self):
        alias = self.root / 'alias.zip'; alias.symlink_to(self.path); fifo = self.root / 'fifo'; os.mkfifo(fifo)
        for path in (self.root / 'missing', alias, fifo, Path('bad\0path'), Path('bad\ud800path')):
            with self.subTest(path=str(path)), self.assertRaises(self.m.ArchivePreflightError) as found:
                self.m.preflight_suite_archive(path, sha(self.raw))
            self.assertEqual(found.exception.code, 'ARCHIVE_PREFLIGHT:PORTABLE_ARCHIVE_FILE')

    def test_model_step_and_reference_work_are_not_run(self):
        with patch.object(self.preparer.model, 'step', side_effect=AssertionError('model executed')): result = self.check()
        self.assertEqual((result['new_synthetic_model_steps'], result['new_reference_steps']), (0, 0))
        self.assertEqual(result['numeric_validation_work'], 'NONZERO_NOT_AGGREGATED')

    def test_unexpected_case_failure_propagates_without_partial_aggregate(self):
        original = self.m._preflight_captured; observed = []
        def check(captured):
            observed.append(captured['summary']['case_id'])
            if len(observed) == 2: raise RuntimeError('unexpected helper failure')
            return original(captured)
        with patch.object(self.m, '_preflight_captured', side_effect=check), self.assertRaisesRegex(RuntimeError, '^unexpected helper failure$'): self.check()
        self.assertEqual(observed, ['sign-cycle', 'declared-difference'])

    def test_unknown_helper_status_cannot_be_counted_as_normal_rejection(self):
        original = self.m._preflight_captured
        def check(captured):
            value = original(captured); value['preflight_status'] = 'UNKNOWN'; return value
        with patch.object(self.m, '_preflight_captured', side_effect=check), self.assertRaises(KeyError): self.check()

    def test_returned_receipts_are_owned_and_repeated_output_is_deterministic(self):
        value = self.check(); before = canonical(value)
        value['gates']['R_BUDGET'] = 'FORGED'; value['archive']['gates'].clear(); value['case_reports'][0]['captured_sha256'].clear()
        self.assertEqual(canonical(self.check()), before); self.assertEqual(canonical(self.check()), before)

    def test_no_calculator_args_source_or_vehicle_authority_are_exposed(self):
        result = self.check()
        for key in ('source_identity_reauthenticated', 'arithmetic_recomputed', 'prehistory_checked', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
            self.assertIs(result[key], False)
        self.assertFalse(set(result) & {'prepared', 'model_input', 'f61_input', 'rate_budget_per_s'})
        self.assertEqual(result['gates']['R_BUDGET'], 'UNRESOLVED'); self.assertEqual(result['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')

    def test_subprocess_blocks_producer_reference_f61_and_model_execution(self):
        script = '''import importlib.abc,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  modules=('integration_tools.core_sequence_run','integration_tools.synthetic_sequence_check','integration_tools.synthetic_transition_check','integration_tools.sequence_reference','integration_tools.fixed_model_reference','numpy','openpilot','opendbc')
  if any(fullname==m or fullname.startswith(m+'.') for m in modules) or fullname.startswith('integration_tools.f61_'):raise AssertionError('forbidden import:'+fullname)
def profile(frame,event,arg):
 if event=='call' and frame.f_globals.get('__name__','').startswith('cyberlateral_dev') and frame.f_code.co_name in ('step','step_normalized'):raise AssertionError('model executed')
sys.meta_path.insert(0,Block());sys.path[:0]=[sys.argv[1],sys.argv[1]+'/src'];sys.setprofile(profile)
from pathlib import Path
from integration_tools.core_sequence_archive_preflight import preflight_suite_archive
from integration_tools.scenario_output import canonical
sys.stdout.buffer.write(canonical(preflight_suite_archive(Path(sys.argv[2]),sys.argv[3])))
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(ROOT), str(self.path), sha(self.raw)], capture_output=True, cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr); self.assertEqual(result.stdout, canonical(self.check()))
