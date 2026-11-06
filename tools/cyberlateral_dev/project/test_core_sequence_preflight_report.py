"""Owned input semantics stay distinct from historical results in bounded Markdown."""

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


def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(v): return (json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CorePreflightReportTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_sequence_preflight_report.py').is_file(), 'Missing CORE23 preflight summary')
        package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.core_sequence_preflight_report')
        self.api = importlib.import_module('integration_tools.core_sequence_archive_preflight')
        self.bundle = importlib.import_module('integration_tools.core_sequence_bundle')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        producer = importlib.import_module('integration_tools.core_sequence_run'); self.source = {}
        for case in CASES:
            folder = self.root / case; producer.run_sequence_case(case, folder)
            self.source.update({'suite/' + case + '/' + n: (folder / n).read_bytes() for n in ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt')})
        self.raw = self.bundle.build_suite_archive(self.source); self.path = self.root / 'input.zip'; self.path.write_bytes(self.raw)

    def report(self, raw=None):
        raw = self.raw if raw is None else raw
        return self.m.report_preflight_archive_bytes(raw, sha(raw))
    def changed(self, changes, filename='INPUT.json'):
        files = dict(self.source)
        for case, change in changes:
            prefix = 'suite/' + case + '/'; value = json.loads(files[prefix + filename]); change(value)
            files[prefix + filename] = canonical(value)
            files[prefix + 'SHA256SUMS.txt'] = ''.join(sha(files[prefix + n]) + '  ' + n + '\n' for n in ('INPUT.json', 'RESULTS.json')).encode()
        return self.bundle.build_suite_archive(files)
    def cases(self, text): return [line for line in text.splitlines() if any(line.startswith('| `"' + c + '"` |') for c in CASES)]

    def test_default_summary_has_current_counts_and_all_three_ordered_rows(self):
        r, raw = self.report(); text = raw.decode()
        self.assertEqual(r['preflight_status'], 'INPUTS_REJECTED')
        for row in ('| `"current_status"` | `"INPUTS_REJECTED"` |', '| `"case_count"` | `3` |',
                    '| `"compatible_case_count"` | `2` |', '| `"rejected_case_count"` | `1` |',
                    '| `"validated_transition_count"` | `8` |', '| `"declared_transition_count"` | `9` |',
                    '| `"recorded_model_steps"` | `6` |', '| `"all_cases_processed"` | `true` |'):
            self.assertIn(row, text)
        self.assertEqual(self.cases(text), [
            '| `"sign-cycle"` | `"INPUTS_COMPATIBLE"` | `null` | `3` | `3` | `"MATCH"` | `null` | `3` |',
            '| `"declared-difference"` | `"INPUTS_COMPATIBLE"` | `null` | `3` | `3` | `"DIFFERENT"` | `null` | `3` |',
            '| `"late-invalid"` | `"INPUTS_REJECTED"` | `"SEQUENCE_INPUT:2:MODEL_DRIVER"` | `2` | `3` | `"REJECTED"` | `"SEQUENCE_INPUT:2:MODEL_DRIVER"` | `0` |'])

    def test_original_core21_canonical_json_is_unchanged(self):
        before = canonical(self.api.preflight_suite_archive_bytes(self.raw, sha(self.raw)))
        r, _ = self.report(); self.assertEqual(canonical(r), before)
        held = canonical(r); self.m._markdown(r); self.assertEqual(canonical(r), held)

    def test_bytes_path_and_repeated_reports_are_identical_owned_results(self):
        r, raw = self.report(); other, report = self.m.report_preflight_archive(self.path, sha(self.raw))
        self.assertEqual((canonical(r), raw), (canonical(other), report))
        r['case_reports'][0]['gates']['actual_r'] = 'caller mutation'
        fresh, repeated = self.report(); self.assertEqual((canonical(other), report), (canonical(fresh), repeated))

    def test_all_compatible_keeps_historical_rejected_visible(self):
        r, raw = self.report(self.changed([('late-invalid', lambda v: v['contexts'][2].update(current_driver_hex=(1.5).hex()))]))
        self.assertEqual(r['preflight_status'], 'INPUTS_COMPATIBLE')
        self.assertIn('| `"compatible_case_count"` | `3` |', raw.decode())
        self.assertIn('| `"validated_transition_count"` | `9` |', raw.decode())
        self.assertIn('| `"late-invalid"` | `"INPUTS_COMPATIBLE"` | `null` | `3` | `3` | `"REJECTED"` | `"SEQUENCE_INPUT:2:MODEL_DRIVER"` | `0` |', raw.decode())

    def test_all_rejected_displays_zero_validated_not_empty_success(self):
        r, raw = self.report(self.changed([(c, lambda v: v['frames'][0]['request'].update(request_override=True)) for c in CASES]))
        self.assertEqual((r['compatible_case_count'], r['rejected_case_count'], r['validated_transition_count']), (0, 3, 0))
        self.assertEqual(len(self.cases(raw.decode())), 3)
        self.assertIn('| `"validated_transition_count"` | `0` |', raw.decode())

    def test_first_rejection_does_not_hide_later_case_rows(self):
        r, raw = self.report(self.changed([('sign-cycle', lambda v: v['frames'][0]['request'].update(request_override=True))]))
        self.assertEqual((r['compatible_case_count'], r['rejected_case_count'], r['validated_transition_count']), (1, 2, 5))
        rows = self.cases(raw.decode()); self.assertEqual(len(rows), 3)
        self.assertIn('SEQUENCE_INPUT:0:MODEL_OVERRIDE', rows[0]); self.assertIn('INPUTS_COMPATIBLE', rows[1])
        self.assertIn('SEQUENCE_INPUT:2:MODEL_DRIVER', rows[2])

    def test_float_encoding_failure_preserves_zero_case_prefix_and_other_rows(self):
        r, raw = self.report(self.changed([('sign-cycle', lambda v: v['contexts'][2].update(current_driver_hex='0x1.0000000000000p-9999'))]))
        self.assertEqual(r['validated_transition_count'], 5)
        self.assertIn('INPUT_PREFLIGHT_FLOAT_ENCODING:2', self.cases(raw.decode())[0]); self.assertEqual(len(self.cases(raw.decode())), 3)
        self.assertIn('| `0` | `3` | `"MATCH"`', self.cases(raw.decode())[0])

    def test_entire_sha_size_and_historical_status_counts_are_displayed(self):
        r, raw = self.report(); text = raw.decode()
        self.assertIn(sha(self.raw), text); self.assertIn('| `"archive_byte_size"` | `' + str(len(self.raw)) + '` |', text)
        self.assertIn('| `"member_count"` | `11` |', text)
        self.assertIn('| `"saved_MATCH"` | `1` |', text); self.assertIn('| `"saved_DIFFERENT"` | `1` |', text)
        self.assertIn('| `"saved_REJECTED"` | `1` |', text); self.assertEqual(r['recorded_model_steps'], 6)

    def test_every_gate_and_false_authority_flag_remains_typed_and_visible(self):
        r, raw = self.report(); text = raw.decode()
        for key, value in r['gates'].items():
            encoded = json.dumps(value, sort_keys=True, separators=(',', ':'))
            self.assertIn('| `"' + key + '"` | `' + encoded + '` |', text)
        for key in ('source_identity_reauthenticated', 'arithmetic_recomputed', 'prehistory_checked', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
            self.assertIs(r[key], False); self.assertIn('| `"' + key + '"` | `false` |', text)
        self.assertIn('| `"actual_r"` | `null` |', text); self.assertIn('| `"T2"` | `null` |', text)
        self.assertIn('| `"vehicle_scale"` | `null` |', text)

    def test_new_work_and_numeric_validation_are_not_historical_steps(self):
        _, raw = self.report(); text = raw.decode()
        self.assertIn('| `"new_synthetic_model_steps"` | `0` |', text)
        self.assertIn('| `"new_reference_steps"` | `0` |', text)
        self.assertIn('| `"numeric_validation_work"` | `"NONZERO_NOT_AGGREGATED"` |', text)
        self.assertIn('prefix', text); self.assertNotIn('NUMERICAL_PASS', text); self.assertNotIn('actual period = 0.01', text)

    def test_private_owned_renderer_escapes_display_cells_without_mutating_receipt(self):
        r, _ = self.report(); hostile = '<script>|`\n\x1b\u202e한글'
        # Formatter-only counterexample, not an admissible public archive/API record.
        r['case_reports'][0]['saved_rejection_code'] = hostile; before = canonical(r)
        text = self.m._markdown(r).decode(); self.assertEqual(canonical(r), before)
        for value in ('<script>', '\x1b', '\u202e'): self.assertNotIn(value, text)
        for value in (r'\u003cscript\u003e', r'\u007c', r'\u0060', r'\n', r'\u001b', r'\u202e', r'\ud55c'): self.assertIn(value, text)
        self.assertEqual(self.cases(text)[0].count('|'), 9)

    def test_clipped_display_is_marked_but_original_field_is_not_clamped(self):
        r, _ = self.report(); value = '`' * 1000
        r['case_reports'][0]['saved_rejection_code'] = value
        text = self.m._markdown(r).decode(); self.assertIn('PREVIEW_TRUNCATED', text)
        self.assertIn('표시용 셀 발췌 잘림 수: 1', text); self.assertLess(len(text.encode()), 65536)
        self.assertEqual(r['case_reports'][0]['saved_rejection_code'], value)

    def test_utf8_cap_accepts_exact_boundary_and_rejects_without_clamping(self):
        _, expected = self.report()
        with patch.object(self.m, 'REPORT_CAP', len(expected)):
            self.assertEqual(self.report()[1], expected)
        with patch.object(self.m, 'REPORT_CAP', len(expected) - 1), self.assertRaisesRegex(self.m.PreflightReportError, '^PREFLIGHT_REPORT_SIZE$'):
            self.report()

    def test_malformed_sha_and_checksum_errors_precede_renderer_or_path_access(self):
        with patch.object(self.m, '_markdown', side_effect=AssertionError('rendered bad input')):
            with patch.object(self.api, '_read_archive', side_effect=AssertionError('path access')):
                with self.assertRaisesRegex(self.api.ArchivePreflightError, '^ARCHIVE_PREFLIGHT:PORTABLE_EXPECTED_SHA256$'):
                    self.m.report_preflight_archive(Path('unsafe\0path'), 'BAD')
            with self.assertRaisesRegex(self.api.ArchivePreflightError, '^ARCHIVE_PREFLIGHT:PORTABLE_ARCHIVE_CHECKSUM$'):
                self.m.report_preflight_archive_bytes(self.raw, '0' * 64)

    def test_corrupt_final_case_blocks_all_semantics_and_summary(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as archive: files = {n: archive.read(n) for n in archive.namelist()}
        prefix = 'suite/late-invalid/'; value = json.loads(files[prefix + 'INPUT.json']); value['frames'] = []
        files[prefix + 'INPUT.json'] = canonical(value)
        files[prefix + 'SHA256SUMS.txt'] = ''.join(sha(files[prefix + n]) + '  ' + n + '\n' for n in ('INPUT.json', 'RESULTS.json')).encode()
        files['SHA256SUMS.txt'] = self.bundle._manifest(files); raw = self.bundle._zip(files)
        with patch.object(self.m, '_markdown', side_effect=AssertionError('rendered corruption')), \
                patch.object(self.api, '_preflight_captured', side_effect=AssertionError('semantic work')):
            with self.assertRaisesRegex(self.api.ArchivePreflightError, '^ARCHIVE_PREFLIGHT:PORTABLE_CASE:late-invalid:'):
                self.m.report_preflight_archive_bytes(raw, sha(raw))

    def test_unexpected_semantic_failure_cannot_become_partial_summary(self):
        original = self.api._preflight_captured; visited = []
        def preflight(record):
            visited.append(record['summary']['case_id'])
            if len(visited) == 3: raise RuntimeError('unexpected helper failure')
            return original(record)
        with patch.object(self.api, '_preflight_captured', side_effect=preflight), patch.object(self.m, '_markdown', side_effect=AssertionError('partial summary')):
            with self.assertRaisesRegex(RuntimeError, '^unexpected helper failure$'): self.report()
        self.assertEqual(visited, list(CASES))

    def test_unexpected_renderer_error_propagates_without_fallback(self):
        with patch.object(self.m, '_markdown', side_effect=RuntimeError('render failure')):
            with self.assertRaisesRegex(RuntimeError, '^render failure$'): self.report()

    def test_path_api_captures_once_readonly_and_verifies_once(self):
        opened = []; counts = {'verify': 0, 'cases': 0}; original = os.open
        def opening(path, flags, *a, **kw):
            self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY)
            fd = original(path, flags, *a, **kw)
            if stat.S_ISREG(os.fstat(fd).st_mode): opened.append(Path(path).name)
            return fd
        def profile(frame, event, arg):
            if event != 'call': return
            key = (frame.f_globals.get('__name__'), frame.f_code.co_name)
            if key == ('integration_tools.core_sequence_bundle', '_verified_suite'): counts['verify'] += 1
            if key == ('integration_tools.core_sequence_input_preflight', '_preflight_captured'): counts['cases'] += 1
        sys.setprofile(profile)
        try:
            with patch('os.open', side_effect=opening): r, raw = self.m.report_preflight_archive(self.path, sha(self.raw))
        finally: sys.setprofile(None)
        self.assertEqual(opened, ['input.zip']); self.assertEqual(counts, {'verify': 1, 'cases': 3})
        self.assertEqual((canonical(r), raw), (canonical(self.report()[0]), self.report()[1]))

    def test_bytes_api_does_not_open_write_or_extract(self):
        with patch('os.open', side_effect=AssertionError('file open')), patch('os.write', side_effect=AssertionError('write')), \
                patch.object(zipfile.ZipFile, 'extractall', side_effect=AssertionError('extract')):
            r, raw = self.report()
        self.assertEqual(r['case_count'], 3); self.assertTrue(raw.endswith(b'\n'))

    def test_blocked_subprocess_imports_and_model_steps_still_produce_same_report(self):
        script = '''import importlib.abc,json,sys
from pathlib import Path
raw=Path(sys.argv[2]).read_bytes();sys.path[:0]=[sys.argv[1],sys.argv[1]+'/src']
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  modules=('integration_tools.core_sequence_run','integration_tools.core_sequence_archive_run','integration_tools.synthetic_sequence_check','integration_tools.synthetic_transition_check','integration_tools.sequence_reference','integration_tools.fixed_model_reference','numpy','openpilot','opendbc')
  if any(fullname==m or fullname.startswith(m+'.') for m in modules) or fullname.startswith('integration_tools.f61_'):raise AssertionError('forbidden import:'+fullname)
def profile(frame,event,arg):
 if event=='call' and frame.f_globals.get('__name__','').startswith('cyberlateral_dev') and frame.f_code.co_name in ('step','step_normalized'):raise AssertionError('model executed')
sys.meta_path.insert(0,Block());sys.setprofile(profile)
from integration_tools.core_sequence_preflight_report import report_preflight_archive_bytes
r,md=report_preflight_archive_bytes(raw,sys.argv[3]);print(json.dumps({'receipt':r,'markdown_hex':md.hex()},sort_keys=True,separators=(',',':')))
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(ROOT), str(self.path), sha(self.raw)], capture_output=True)
        self.assertEqual((result.returncode, result.stderr), (0, b'')); r, raw = self.report(); value = json.loads(result.stdout)
        self.assertEqual((canonical(value['receipt']), bytes.fromhex(value['markdown_hex'])), (canonical(r), raw))

    def test_inherited_bytes_type_and_path_restrictions_remain_fixed_errors(self):
        alias = self.root / 'alias'; alias.symlink_to(self.path)
        with self.assertRaisesRegex(self.api.ArchivePreflightError, '^ARCHIVE_PREFLIGHT:PORTABLE_ARCHIVE_FILE$'):
            self.m.report_preflight_archive(alias, sha(self.raw))
        with self.assertRaisesRegex(self.api.ArchivePreflightError, '^ARCHIVE_PREFLIGHT:PORTABLE_ARCHIVE_FILE$'):
            self.m.report_preflight_archive_bytes(bytearray(self.raw), sha(self.raw))

    def test_arbitrary_identity_metadata_is_not_inserted_into_human_report(self):
        hostile = '<script>|`\n\u202e'
        raw = self.changed([('sign-cycle', lambda r: r['identity'].update({hostile: hostile}))], filename='RESULTS.json')
        r, md = self.report(raw)
        self.assertEqual(r['preflight_status'], 'INPUTS_REJECTED')
        self.assertNotIn(hostile, md.decode()); self.assertNotIn('<script>', md.decode()); self.assertEqual(len(self.cases(md.decode())), 3)
