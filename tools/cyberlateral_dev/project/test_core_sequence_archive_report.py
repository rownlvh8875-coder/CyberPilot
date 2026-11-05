"""Bounded Markdown preserves comparison meaning and treats metadata as data."""

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

from v1_helpers import ROOT

CASES = ('sign-cycle', 'declared-difference', 'late-invalid')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CoreArchiveReportTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_sequence_archive_report.py').is_file(), 'Missing CORE15 readable archive summary')
        self.assertTrue((ROOT / 'tools/core_sequence_archive_report.py').is_file(), 'Missing CORE15 summary CLI')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.core_sequence_archive_report')
        self.compare = importlib.import_module('integration_tools.core_sequence_archive_compare')
        self.bundle = importlib.import_module('integration_tools.core_sequence_bundle')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        producer = importlib.import_module('integration_tools.core_sequence_run')
        self.source = {}
        for case in CASES:
            folder = self.root / case; producer.run_sequence_case(case, folder)
            for name in ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt'):
                self.source['suite/' + case + '/' + name] = (folder / name).read_bytes()
        self.raw = self.bundle.build_suite_archive(self.source)
        self.left = self.root / 'left.zip'; self.left.write_bytes(self.raw)
        self.right = self.root / 'right.zip'; self.right.write_bytes(self.raw)

    def modified(self, changes):
        files = dict(self.source)
        for case, change in changes:
            prefix = 'suite/' + case + '/'
            data = json.loads(files[prefix + 'RESULTS.json']); change(data['identity'])
            files[prefix + 'RESULTS.json'] = canonical(data)
            files[prefix + 'SHA256SUMS.txt'] = ''.join(sha(files[prefix + n]) + '  ' + n + '\n' for n in ('INPUT.json', 'RESULTS.json')).encode()
        return self.bundle.build_suite_archive(files)

    def report(self, other=None):
        other = self.raw if other is None else other
        return self.m.report_suite_archive_bytes(self.raw, sha(self.raw), other, sha(other))

    def args(self):
        return ['--left-archive', str(self.left), '--left-sha256', sha(self.left.read_bytes()),
                '--right-archive', str(self.right), '--right-sha256', sha(self.right.read_bytes())]

    def command(self, args=None):
        return subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence_archive_report.py', *(self.args() if args is None else args)], capture_output=True)

    def cli_module(self):
        spec = importlib.util.spec_from_file_location('core15_cli_test', ROOT / 'tools/core_sequence_archive_report.py')
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def test_identical_summary_preserves_core14_dict_and_qualified_status(self):
        r, raw = self.report()
        self.assertEqual(r, self.compare.compare_suite_archive_bytes(self.raw, sha(self.raw), self.raw, sha(self.raw)))
        text = raw.decode()
        self.assertTrue(text.startswith('# CORE15 저장 ZIP 비교 요약\n'))
        for value in ('CORE15_ARCHIVE_SUMMARY_V1', 'SAVED_SUITE_ARCHIVES_IDENTICAL', '전체 차이: 0', 'CORE14 상세: 0', '요약 표시: 0',
                      '새 수치 판정', '기록된 과거 model steps', '신규 모델 실행: 0', '신규 reference 실행: 0'):
            self.assertIn(value, text)
        self.assertEqual(r['left']['suite']['saved_status_counts'], {'MATCH': 1, 'DIFFERENT': 1, 'REJECTED': 1})
        self.assertEqual(r['left']['suite']['recorded_model_steps'], 6)
        self.assertNotIn('NUMERICAL_PASS', text)

    def test_changed_summary_has_full_sha_and_all_case_labels(self):
        other = self.modified([('late-invalid', lambda i: i.update(marker=None))])
        r, raw = self.report(other); text = raw.decode()
        self.assertEqual(r['difference_counts'], {'INPUT': 0, 'RESULT': 0, 'IDENTITY': 1})
        for value in (sha(self.raw), sha(other), 'SAVED_SUITE_ARCHIVES_DIFFERENT', *CASES): self.assertIn(value, text)
        self.assertIn('전체 차이: 1', text)
        self.assertEqual(r['reports'][2]['comparison']['differences'][0]['kind'], 'RIGHT_ONLY')

    def test_case_categories_remain_visible_when_result_detail_is_not_shown(self):
        files = dict(self.source)
        prefix = 'suite/late-invalid/'
        data = json.loads(files[prefix + 'RESULTS.json'])
        data['identity'].update({f'marker_{i:02}': i for i in range(25)})
        data['rejection_code'] = ('SEQUENCE_INPUT:2:MODEL_DRIVER' if data['rejection_code'] != 'SEQUENCE_INPUT:2:MODEL_DRIVER'
                                  else 'SEQUENCE_INPUT:2:MODEL_ANGLE')
        files[prefix + 'RESULTS.json'] = canonical(data)
        files[prefix + 'SHA256SUMS.txt'] = ''.join(sha(files[prefix + n]) + '  ' + n + '\n' for n in ('INPUT.json', 'RESULTS.json')).encode()
        r, raw = self.report(self.bundle.build_suite_archive(files))
        c = r['reports'][2]['comparison']
        self.assertEqual(c['difference_counts'], {'INPUT': 0, 'RESULT': 1, 'IDENTITY': 25})
        self.assertEqual((c['difference_count'], c['reported_difference_count']), (26, 26))
        text = raw.decode()
        table = text.split('## case별 집계\n', 1)[1].split('## 상세 요약\n', 1)[0]
        self.assertIn('| case | 왼쪽 저장 판정 | 오른쪽 저장 판정 | 전체 차이 | INPUT | RESULT | IDENTITY | CORE14 상세 | 요약 표시 |', table)
        self.assertIn('| `"late-invalid"` | `"REJECTED"` | `"REJECTED"` | `26` | `0` | `1` | `25` | `26` | `20` |', table)
        self.assertNotIn('"/RESULTS.json/rejection_code"', text)
        self.assertEqual(len([line for line in text.splitlines() if line.startswith('| `"/RESULTS.json/identity/marker_')]), 20)

    def test_case_categories_use_local_totals_and_leave_comparison_json_unchanged(self):
        files = dict(self.source)
        source = json.loads(files['suite/sign-cycle/INPUT.json'])
        source['frames'][0]['request']['requested_binary32_be_hex'] = 'be000000'
        files['suite/sign-cycle/INPUT.json'] = canonical(source)
        result = json.loads(files['suite/declared-difference/RESULTS.json'])
        result['identity'].update(marker_a=0, marker_b=1)
        files['suite/declared-difference/RESULTS.json'] = canonical(result)
        result = json.loads(files['suite/late-invalid/RESULTS.json'])
        result['rejection_code'] = ('SEQUENCE_INPUT:2:MODEL_DRIVER' if result['rejection_code'] != 'SEQUENCE_INPUT:2:MODEL_DRIVER'
                                    else 'SEQUENCE_INPUT:2:MODEL_ANGLE')
        files['suite/late-invalid/RESULTS.json'] = canonical(result)
        for case in CASES:
            prefix = 'suite/' + case + '/'
            files[prefix + 'SHA256SUMS.txt'] = ''.join(sha(files[prefix + n]) + '  ' + n + '\n' for n in ('INPUT.json', 'RESULTS.json')).encode()
        other = self.bundle.build_suite_archive(files)
        r, raw = self.report(other)
        self.assertEqual(r['difference_counts'], {'INPUT': 1, 'RESULT': 1, 'IDENTITY': 2})
        self.assertEqual(r, self.compare.compare_suite_archive_bytes(self.raw, sha(self.raw), other, sha(other)))
        table = raw.decode().split('## case별 집계\n', 1)[1].split('## 상세 요약\n', 1)[0]
        for wanted in (
            '| `"sign-cycle"` | `"MATCH"` | `"MATCH"` | `1` | `1` | `0` | `0` | `1` | `1` |',
            '| `"declared-difference"` | `"DIFFERENT"` | `"DIFFERENT"` | `2` | `0` | `0` | `2` | `2` | `2` |',
            '| `"late-invalid"` | `"REJECTED"` | `"REJECTED"` | `1` | `0` | `1` | `0` | `1` | `1` |',
        ):
            self.assertIn(wanted, table)
        self.right.write_bytes(other)
        p = self.command()
        self.assertEqual((p.returncode, p.stdout, p.stderr), (1, raw, b''))
        self.assertLessEqual(len(raw), 65536)

    def test_missing_null_and_presence_are_distinct_in_display(self):
        _, raw = self.report(self.modified([('late-invalid', lambda i: i.update(marker=None))]))
        row = next(line for line in raw.decode().splitlines() if '/RESULTS.json/identity/marker' in line)
        self.assertIn('`false` | `null` | `true` | `null`', row)

    def test_boolean_false_and_integer_zero_are_not_display_coerced(self):
        left = self.modified([('sign-cycle', lambda i: i.update(marker=False))])
        right = self.modified([('sign-cycle', lambda i: i.update(marker=0))])
        r, raw = self.m.report_suite_archive_bytes(left, sha(left), right, sha(right))
        self.assertEqual(r['difference_count'], 1)
        row = next(line for line in raw.decode().splitlines() if '/RESULTS.json/identity/marker' in line)
        self.assertIn('TYPE_CHANGED', row)
        self.assertIn('`true` | `false` | `true` | `0`', row)

    def test_full_retained_and_summary_counts_have_separate_omission_numbers(self):
        left = self.modified([(c, lambda i: i.update(marker=[0] * 300)) for c in CASES])
        right = self.modified([(c, lambda i: i.update(marker=[1] * 300)) for c in CASES])
        r, raw = self.m.report_suite_archive_bytes(left, sha(left), right, sha(right)); text = raw.decode()
        self.assertEqual((r['difference_count'], r['reported_difference_count']), (900, 768))
        for value in ('전체 차이: 900', 'CORE14 상세: 768', '요약 표시: 60',
                      'CORE14 상세에서 요약 미표시: 708', 'CORE14 상세 한도 밖: 132'):
            self.assertIn(value, text)
        rows = [line for line in text.splitlines() if line.startswith('| `"/RESULTS.json/identity/marker/')]
        self.assertEqual(len(rows), 60)
        self.assertNotIn('/marker/20"', text)
        self.assertLessEqual(len(raw), 65536)

    def test_cell_preview_exact_ascii_boundary_and_truncation_marker(self):
        full, truncated = self.m._preview('a' * 158)
        self.assertFalse(truncated)
        self.assertEqual(full, '`"' + 'a' * 158 + '"`')
        clipped, truncated = self.m._preview('a' * 159)
        self.assertTrue(truncated)
        self.assertIn('PREVIEW_TRUNCATED', clipped)
        self.assertLessEqual(len(clipped), 190)

    def test_cell_limit_counts_escape_expansion_not_raw_characters(self):
        full, truncated = self.m._preview('`' * 26)
        self.assertFalse(truncated)
        self.assertEqual(full, '`"' + r'\u0060' * 26 + '"`')
        raw, truncated = self.m._preview('`' * 27)
        self.assertTrue(truncated)
        self.assertEqual(raw.count('`'), 2)
        self.assertLessEqual(len(raw), 190)

    def test_hostile_metadata_cannot_inject_html_columns_controls_or_code_spans(self):
        value = '<script>|`\n\x1b\u202e한글'
        _, raw = self.report(self.modified([('late-invalid', lambda i: i.update({value: value}))])); text = raw.decode()
        for forbidden in ('<script>', '\x1b', '\u202e'): self.assertNotIn(forbidden, text)
        for escaped in (r'\u003cscript\u003e', r'\u007c', r'\u0060', r'\n', r'\u001b', r'\u202e', r'\ud55c'):
            self.assertIn(escaped, text)
        row = next(line for line in text.splitlines() if '/RESULTS.json/identity/' in line)
        self.assertEqual(row.count('|'), 8)
        self.assertEqual(row.count('`'), 14)

    def test_long_paths_and_nested_values_remain_bounded_and_marked_as_previews(self):
        key = '/' * 10000
        value = {'nested': ['x' * 100000]}
        other = self.modified([('late-invalid', lambda i: i.update({key: value}))])
        r, raw = self.report(other)
        self.assertEqual(r['reports'][2]['comparison']['differences'][0]['right'], value)
        self.assertIn(b'PREVIEW_TRUNCATED', raw)
        self.assertLessEqual(len(raw), 65536)
        self.assertLess(len(raw), 15000)
        self.assertIn('원문 전체가 아닌 표시용 발췌', raw.decode())

    def test_report_shows_every_unchanged_gate_and_explicit_closed_boundaries(self):
        r, raw = self.report(); text = raw.decode()
        for key in r['gates']: self.assertIn(key, text)
        for value in ('R_BUDGET=UNRESOLVED', 'Static Evidence Gate=FAIL', '실제 r/T2/scale=null', '실차 활성화 금지',
                      'source_identity_reauthenticated=false', 'arithmetic_recomputed=false'):
            self.assertIn(value, text)

    def test_both_digest_validation_precedes_input_access_and_rendering(self):
        with patch('os.open', side_effect=AssertionError('input accessed')), patch.object(self.m, '_markdown', side_effect=AssertionError('rendered')):
            with self.assertRaisesRegex(self.compare.ArchiveCompareError, 'ARCHIVE_COMPARE_RIGHT:PORTABLE_EXPECTED_SHA256'):
                self.m.report_suite_archives(object(), sha(self.raw), object(), '')

    def test_corrupt_archive_never_reaches_markdown_or_partial_cli_output(self):
        self.right.write_bytes(b'broken')
        with patch.object(self.m, '_markdown', side_effect=AssertionError('invalid input rendered')):
            with self.assertRaisesRegex(self.compare.ArchiveCompareError, 'ARCHIVE_COMPARE_RIGHT:PORTABLE_ZIP_FORMAT'):
                self.m.report_suite_archives(self.left, sha(self.raw), self.right, sha(b'broken'))
        p = self.command()
        self.assertEqual((p.returncode, p.stdout), (2, b''))
        self.assertIn(b'ARCHIVE_COMPARE_RIGHT:PORTABLE_ZIP_FORMAT', p.stderr)

    def test_inherited_four_mib_diagnostic_limit_cannot_be_bypassed_by_summary(self):
        key = '/' * 16384
        left = self.modified([('late-invalid', lambda i: i.update({key: [0] * 300}))])
        right = self.modified([('late-invalid', lambda i: i.update({key: [1] * 300}))])
        with patch.object(self.m, '_markdown', side_effect=AssertionError('oversized comparison rendered')):
            with self.assertRaisesRegex(self.compare.ArchiveCompareError, '^ARCHIVE_COMPARE_DETAIL_BYTE_LIMIT$'):
                self.m.report_suite_archive_bytes(left, sha(left), right, sha(right))

    def test_file_api_compares_once_and_captures_exactly_two_readonly_roles(self):
        real = os.open; flags = []
        def capture(*args, **kwargs): flags.append(args[1]); return real(*args, **kwargs)
        with patch.object(self.m, 'compare_suite_archives', wraps=self.compare.compare_suite_archives) as compare, patch('os.open', side_effect=capture):
            r, raw = self.m.report_suite_archives(self.left, sha(self.raw), self.right, sha(self.raw))
        self.assertEqual(compare.call_count, 1)
        self.assertEqual(len(flags), 2)
        self.assertTrue(all(f & os.O_ACCMODE == os.O_RDONLY for f in flags))
        self.assertEqual((r, raw), self.report())

    def test_input_bytes_modes_and_file_set_are_preserved(self):
        before = {p.relative_to(self.root).as_posix(): (p.read_bytes(), p.stat().st_mode) for p in self.root.rglob('*') if p.is_file()}
        self.m.report_suite_archives(self.left, sha(self.raw), self.right, sha(self.raw))
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): (p.read_bytes(), p.stat().st_mode) for p in self.root.rglob('*') if p.is_file()})

    def test_mirror_locations_and_repeats_have_identical_summary_bytes(self):
        a = self.m.report_suite_archives(self.left, sha(self.raw), self.right, sha(self.raw))
        mirror = self.root / 'mirror.zip'; mirror.write_bytes(self.raw)
        b = self.m.report_suite_archives(mirror, sha(self.raw), mirror, sha(self.raw))
        self.assertEqual(a, b)
        self.assertNotIn(str(self.root).encode(), a[1])
        self.assertEqual(a, self.report())

    def test_cli_identical_and_difference_match_api_and_exit_codes(self):
        p = self.command()
        self.assertEqual((p.returncode, p.stderr, p.stdout), (0, b'', self.report()[1]))
        other = self.modified([('late-invalid', lambda i: i.update(marker=None))]); self.right.write_bytes(other)
        p = self.command()
        self.assertEqual((p.returncode, p.stderr, p.stdout), (1, b'', self.report(other)[1]))

    def test_cli_rejects_missing_sha_abbreviations_and_unsupported_flags(self):
        for args in ([], self.args()[:-2], ['--left-a', *self.args()[1:]], self.args() + ['--format', 'html'],
                     self.args() + ['--run'], self.args() + ['--extract'], self.args() + ['--output', 'x'], self.args() + ['--r', '0']):
            p = self.command(args)
            self.assertEqual((p.returncode, p.stdout), (2, b''))

    def test_size_guard_rejects_before_cli_publication(self):
        with patch.object(self.m, 'REPORT_CAP', 1):
            with self.assertRaisesRegex(self.m.ArchiveReportError, '^ARCHIVE_REPORT_SIZE$'): self.report()
            cli = self.cli_module()
            with patch.object(sys, 'stdout', StringIO()) as out, patch.object(sys, 'stderr', StringIO()) as err:
                code = cli.main(self.args())
        self.assertEqual((code, out.getvalue(), err.getvalue()), (2, '', 'REJECTED: ARCHIVE_REPORT_SIZE\n'))

    def test_render_and_exit_failures_emit_fixed_error_without_summary(self):
        for target, name in ((self.m, '_markdown'), (self.compare, 'exit_code')):
            cli = self.cli_module()
            with patch.object(target, name, side_effect=RuntimeError('private detail')), patch.object(sys, 'stdout', StringIO()) as out, \
                    patch.object(sys, 'stderr', StringIO()) as err:
                code = cli.main(self.args())
            self.assertEqual((code, out.getvalue(), err.getvalue()), (2, '', 'REJECTED: ARCHIVE_REPORT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_cache_cleanup_failure_precedes_output_and_restores_setting(self):
        cli = self.cli_module(); real = tempfile.TemporaryDirectory
        class FailCleanup(real):
            def __exit__(self, exc, value, tb):
                super().__exit__(exc, value, tb); raise OSError('private cleanup path')
        before = sys.pycache_prefix
        with patch.object(cli.tempfile, 'TemporaryDirectory', FailCleanup), patch.object(sys, 'stdout', StringIO()) as out, \
                patch.object(sys, 'stderr', StringIO()) as err:
            code = cli.main(self.args())
        self.assertEqual((code, out.getvalue(), err.getvalue()), (2, '', 'REJECTED: ARCHIVE_REPORT_FAILED_NO_MODEL_EXECUTION\n'))
        self.assertEqual(sys.pycache_prefix, before)

    def test_cache_creation_failure_has_fixed_diagnostic(self):
        cli = self.cli_module()
        with patch.object(cli.tempfile, 'TemporaryDirectory', side_effect=OSError('private path')), patch.object(sys, 'stdout', StringIO()) as out, \
                patch.object(sys, 'stderr', StringIO()) as err:
            code = cli.main(self.args())
        self.assertEqual((code, out.getvalue(), err.getvalue()), (2, '', 'REJECTED: ARCHIVE_REPORT_CACHE_IO_NO_MODEL_EXECUTION\n'))

    def test_stdout_failure_is_guarded_and_cache_restored(self):
        cli = self.cli_module(); real = os.write; before = sys.pycache_prefix
        def fail(fd, raw):
            if fd == sys.stdout.fileno(): raise OSError('private stdout')
            return real(fd, raw)
        with patch.object(cli.os, 'write', side_effect=fail), patch.object(sys, 'stderr', StringIO()) as err:
            code = cli.main(self.args())
        self.assertEqual((code, err.getvalue()), (2, 'REJECTED: ARCHIVE_REPORT_FAILED_NO_MODEL_EXECUTION\n'))
        self.assertEqual(sys.pycache_prefix, before)

    def test_fresh_cli_cannot_extract_or_import_execution_and_profiles_zero_steps(self):
        script = '''import importlib.abc,runpy,sys,zipfile
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.startswith(('cyberlateral_dev','integration_tools.core_sequence_run','numpy')): raise AssertionError(fullname)
sys.meta_path.insert(0,Block())
def forbidden(*a,**k): raise AssertionError('extract')
zipfile.ZipFile.extract=forbidden
zipfile.ZipFile.extractall=forbidden
steps=[]
def profile(frame,event,arg):
 if event=='call' and frame.f_code.co_name=='step' and frame.f_code.co_filename.endswith('/src/cyberlateral_dev/api.py'): steps.append(1)
sys.setprofile(profile)
cli=runpy.run_path(sys.argv[1],run_name='core15_blocked')
try: code=cli['main'](sys.argv[2:])
finally: sys.setprofile(None)
assert not steps
raise SystemExit(code)
'''
        p = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(ROOT / 'tools/core_sequence_archive_report.py'), *self.args()], capture_output=True)
        self.assertEqual((p.returncode, p.stderr, p.stdout), (0, b'', self.report()[1]))
