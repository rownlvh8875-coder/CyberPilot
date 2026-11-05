"""Two-role verified ZIP comparison without extraction, reopening or replay."""

import hashlib
import importlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT

CASES = ('sign-cycle', 'declared-difference', 'late-invalid')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CoreArchiveCompareTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_sequence_archive_compare.py').is_file(), 'Missing CORE14 archive comparison')
        self.assertTrue((ROOT / 'tools/core_sequence_archive_compare.py').is_file(), 'Missing CORE14 comparison CLI')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.core_sequence_archive_compare')
        self.b = importlib.import_module('integration_tools.core_sequence_bundle')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        producer = importlib.import_module('integration_tools.core_sequence_run')
        self.source = {}
        for case in CASES:
            folder = self.root / case
            producer.run_sequence_case(case, folder)
            for name in ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt'):
                self.source['suite/' + case + '/' + name] = (folder / name).read_bytes()
        self.raw = self.b.build_suite_archive(self.source)
        self.left = self.root / 'left.zip'; self.left.write_bytes(self.raw)
        self.right = self.root / 'right.zip'; self.right.write_bytes(self.raw)

    def modified(self, changes):
        files = dict(self.source)
        for case, filename, change in changes:
            key = 'suite/' + case + '/' + filename
            data = json.loads(files[key]); change(data); files[key] = canonical(data)
            prefix = 'suite/' + case + '/'
            files[prefix + 'SHA256SUMS.txt'] = ''.join(sha(files[prefix + n]) + '  ' + n + '\n'
                for n in ('INPUT.json', 'RESULTS.json')).encode()
        return self.b.build_suite_archive(files)

    def compare(self, other=None):
        raw = self.raw if other is None else other
        return self.m.compare_suite_archive_bytes(self.raw, sha(self.raw), raw, sha(raw))

    def command(self, right=None, right_sha=None, extra=()):
        return subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence_archive_compare.py',
            '--left-archive', self.left, '--left-sha256', sha(self.raw), '--right-archive', self.right if right is None else right,
            '--right-sha256', sha(self.right.read_bytes()) if right_sha is None else right_sha, *extra], capture_output=True)

    def test_identical_archive_keeps_all_saved_outcomes_and_zero_new_work(self):
        r = self.compare()
        self.assertEqual(r['comparison_status'], 'SAVED_SUITE_ARCHIVES_IDENTICAL')
        self.assertTrue(r['archive_bytes_identical'])
        self.assertEqual(r['difference_count'], 0)
        self.assertEqual(r['difference_counts'], {'INPUT': 0, 'RESULT': 0, 'IDENTITY': 0})
        self.assertEqual(r['comparison_counts'], {'IDENTICAL': 3, 'DIFFERENT': 0})
        self.assertEqual(r['case_ids'], list(CASES))
        self.assertTrue(r['all_cases_processed'])
        for role in ('left', 'right'):
            self.assertEqual(r[role]['suite']['saved_status_counts'], {'MATCH': 1, 'DIFFERENT': 1, 'REJECTED': 1})
            self.assertEqual(r[role]['suite']['recorded_model_steps'], 6)
        self.assertEqual((r['new_synthetic_model_steps'], r['comparison_model_executions'], r['comparison_reference_executions']), (0, 0, 0))
        self.assertFalse(r['source_identity_reauthenticated'])
        self.assertFalse(r['arithmetic_recomputed'])
        self.assertEqual(self.m.exit_code(r), 0)

    def test_one_opaque_identity_difference_is_not_ignored(self):
        raw = self.modified([('late-invalid', 'RESULTS.json', lambda r: r['identity'].update(marker=None))])
        r = self.compare(raw)
        self.assertFalse(r['archive_bytes_identical'])
        self.assertEqual((r['comparison_status'], self.m.exit_code(r), r['difference_count']), ('SAVED_SUITE_ARCHIVES_DIFFERENT', 1, 1))
        self.assertEqual(r['difference_counts'], {'INPUT': 0, 'RESULT': 0, 'IDENTITY': 1})
        self.assertEqual(r['comparison_counts'], {'IDENTICAL': 2, 'DIFFERENT': 1})
        d = r['reports'][2]['comparison']['differences'][0]
        self.assertEqual(d, {'path': '/RESULTS.json/identity/marker', 'section': 'IDENTITY', 'kind': 'RIGHT_ONLY',
                            'left_present': False, 'right_present': True, 'left': None, 'right': None})

    def test_multiple_cases_and_sections_are_fully_aggregated(self):
        def rejection(r):
            r['rejection_code'] = ('SEQUENCE_INPUT:2:MODEL_DRIVER' if r['rejection_code'] != 'SEQUENCE_INPUT:2:MODEL_DRIVER'
                                   else 'SEQUENCE_INPUT:2:MODEL_ANGLE')
        raw = self.modified([('sign-cycle', 'INPUT.json', lambda r: r['frames'][0]['request'].update(requested_binary32_be_hex='be000000')),
            ('declared-difference', 'RESULTS.json', lambda r: r['identity'].update(marker=1)), ('late-invalid', 'RESULTS.json', rejection)])
        r = self.compare(raw)
        self.assertEqual(r['difference_count'], 3)
        self.assertEqual(r['difference_counts'], {'INPUT': 1, 'RESULT': 1, 'IDENTITY': 1})
        self.assertEqual(r['comparison_counts'], {'IDENTICAL': 0, 'DIFFERENT': 3})

    def test_identity_false_and_zero_are_type_distinct(self):
        left = self.modified([('sign-cycle', 'RESULTS.json', lambda r: r['identity'].update(marker=False))])
        right = self.modified([('sign-cycle', 'RESULTS.json', lambda r: r['identity'].update(marker=0))])
        r = self.m.compare_suite_archive_bytes(left, sha(left), right, sha(right))
        d = r['reports'][0]['comparison']['differences'][0]
        self.assertEqual((d['kind'], d['left'], d['right'], r['difference_count']), ('TYPE_CHANGED', False, 0, 1))

    def test_nested_pointer_escaping_and_positional_lists_are_preserved(self):
        left = self.modified([('sign-cycle', 'RESULTS.json', lambda r: r['identity'].update({'a~/한글': [1, None]}))])
        right = self.modified([('sign-cycle', 'RESULTS.json', lambda r: r['identity'].update({'a~/한글': [2]}))])
        r = self.m.compare_suite_archive_bytes(left, sha(left), right, sha(right))
        ds = r['reports'][0]['comparison']['differences']
        self.assertEqual([d['path'] for d in ds], ['/RESULTS.json/identity/a~0~1한글/0', '/RESULTS.json/identity/a~0~1한글/1'])
        self.assertEqual((ds[1]['kind'], ds[1]['left_present'], ds[1]['right_present']), ('LEFT_ONLY', True, False))

    def test_per_case_detail_caps_do_not_truncate_total_counts(self):
        def changes(value):
            return [(c, 'RESULTS.json', lambda r, value=value: r['identity'].update(marker=[value] * 300)) for c in CASES]
        left, right = self.modified(changes(0)), self.modified(changes(1))
        r = self.m.compare_suite_archive_bytes(left, sha(left), right, sha(right))
        self.assertEqual((r['difference_count'], r['reported_difference_count']), (900, 768))
        self.assertTrue(r['differences_truncated'])
        self.assertEqual([v['comparison']['difference_count'] for v in r['reports']], [300, 300, 300])
        self.assertEqual([len(v['comparison']['differences']) for v in r['reports']], [256, 256, 256])

    def test_reversal_changes_direction_not_count(self):
        other = self.modified([('late-invalid', 'RESULTS.json', lambda r: r['identity'].update(marker='new'))])
        reverse = self.m.compare_suite_archive_bytes(other, sha(other), self.raw, sha(self.raw))
        forward = self.compare(other)
        self.assertEqual(reverse['difference_counts'], forward['difference_counts'])
        self.assertEqual(reverse['reports'][2]['comparison']['differences'][0]['kind'], 'LEFT_ONLY')
        self.assertEqual(forward['reports'][2]['comparison']['differences'][0]['kind'], 'RIGHT_ONLY')

    def test_both_digests_are_preflighted_before_any_path_access(self):
        for side in ('LEFT', 'RIGHT'):
            for bad in (None, False, '', 'A' * 64, 'a' * 63, 'g' * 64):
                a, b = (bad, sha(self.raw)) if side == 'LEFT' else (sha(self.raw), bad)
                with self.subTest(side=side, bad=bad), patch('os.open', side_effect=AssertionError('early open')):
                    with self.assertRaisesRegex(self.m.ArchiveCompareError, '^ARCHIVE_COMPARE_' + side + ':PORTABLE_EXPECTED_SHA256$'):
                        self.m.compare_suite_archives(object(), a, object(), b)

    def test_both_digests_are_preflighted_before_pure_zip_parsing(self):
        with patch.object(zipfile, 'ZipFile', side_effect=AssertionError('early parser')):
            with self.assertRaisesRegex(self.m.ArchiveCompareError, 'ARCHIVE_COMPARE_RIGHT:PORTABLE_EXPECTED_SHA256'):
                self.m.compare_suite_archive_bytes(self.raw, sha(self.raw), self.raw, '')

    def test_whole_checksum_mismatch_is_side_qualified(self):
        for side in ('LEFT', 'RIGHT'):
            a, b = ('0' * 64, sha(self.raw)) if side == 'LEFT' else (sha(self.raw), '0' * 64)
            with self.assertRaisesRegex(self.m.ArchiveCompareError, '^ARCHIVE_COMPARE_' + side + ':PORTABLE_ARCHIVE_CHECKSUM$'):
                self.m.compare_suite_archive_bytes(self.raw, a, self.raw, b)

    def test_corrupt_right_emits_no_partial_cli_summary(self):
        self.right.write_bytes(b'broken')
        p = self.command()
        self.assertEqual((p.returncode, p.stdout), (2, b''))
        self.assertIn(b'ARCHIVE_COMPARE_RIGHT:PORTABLE_ZIP_FORMAT', p.stderr)
        self.assertNotIn(str(self.root).encode(), p.stderr)

    def test_malformed_left_stops_before_right_file_access(self):
        self.left.write_bytes(b'bad')
        real = os.open
        def guard(path, *args, **kwargs):
            if path == self.right: raise AssertionError('right accessed')
            return real(path, *args, **kwargs)
        with patch('os.open', side_effect=guard), self.assertRaisesRegex(self.m.ArchiveCompareError, 'ARCHIVE_COMPARE_LEFT:PORTABLE_ZIP_FORMAT'):
            self.m.compare_suite_archives(self.left, sha(b'bad'), self.right, sha(self.raw))

    def test_core13_member_report_and_gate_rejections_remain_enforced(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as z:
            original = {n: z.read(n) for n in z.namelist()}
        for kind in ('member', 'report', 'gate'):
            files = dict(original)
            if kind == 'member': files['suite/late-invalid/INPUT.json'] += b' '
            elif kind == 'report': files['SUITE_REPORT.json'] += b' '
            else:
                name = 'suite/sign-cycle/RESULTS.json'
                data = json.loads(files[name]); data['gates']['actual_r'] = 0; files[name] = canonical(data)
                files['suite/sign-cycle/SHA256SUMS.txt'] = ''.join(sha(files['suite/sign-cycle/' + n]) + '  ' + n + '\n'
                    for n in ('INPUT.json', 'RESULTS.json')).encode()
            files['SHA256SUMS.txt'] = ''.join(sha(files[n]) + '  ' + n + '\n' for n in sorted(files) if n != 'SHA256SUMS.txt').encode()
            raw = self.b._zip(files)
            with self.subTest(kind=kind), self.assertRaises(self.m.ArchiveCompareError):
                self.compare(raw)

    def test_zip64_override_is_rejected_before_stdlib_parser(self):
        raw = bytearray(self.raw)
        raw[-42:-38] = b'PK\x06\x07'
        with patch.object(zipfile, 'ZipFile', side_effect=AssertionError('ZIP64 parser entered')):
            with self.assertRaisesRegex(self.m.ArchiveCompareError, 'ARCHIVE_COMPARE_LEFT:PORTABLE_ZIP_FORMAT'):
                self.m.compare_suite_archive_bytes(bytes(raw), sha(raw), self.raw, sha(self.raw))

    def test_file_type_symlink_fifo_directory_and_missing_are_fixed_errors(self):
        link = self.root / 'link'; link.symlink_to(self.left)
        fifo = self.root / 'fifo'; os.mkfifo(fifo)
        for path in (link, fifo, self.root, self.root / 'absent', 'bad'):
            with self.subTest(path=path), self.assertRaisesRegex(self.m.ArchiveCompareError, 'ARCHIVE_COMPARE_LEFT:PORTABLE_ARCHIVE_FILE'):
                self.m.compare_suite_archives(path, sha(self.raw), self.right, sha(self.raw))

    def test_archive_caps_and_invalid_byte_types_do_not_reach_comparison(self):
        for raw, code in ((b'x' * 2000001, 'PORTABLE_ARCHIVE_SIZE'), (bytearray(self.raw), 'PORTABLE_ARCHIVE_FILE')):
            with self.assertRaisesRegex(self.m.ArchiveCompareError, 'ARCHIVE_COMPARE_RIGHT:' + code):
                self.m.compare_suite_archive_bytes(self.raw, sha(self.raw), raw, sha(raw))

    def test_each_role_is_captured_and_parsed_once_without_writes(self):
        opens, modes, decoded = [], [], []
        real_open, real_zip, real_decode = os.open, zipfile.ZipFile, self.b._decode
        def capture(*args, **kwargs):
            opens.append(args[1]); return real_open(*args, **kwargs)
        def parse(*args, **kwargs):
            modes.append(args[1] if len(args) > 1 else kwargs.get('mode', 'r')); return real_zip(*args, **kwargs)
        def decode(files):
            decoded.append(1); return real_decode(files)
        with patch('os.open', side_effect=capture), patch.object(zipfile, 'ZipFile', side_effect=parse), patch.object(self.b, '_decode', side_effect=decode):
            r = self.m.compare_suite_archives(self.left, sha(self.raw), self.right, sha(self.raw))
        self.assertEqual((len(opens), modes.count('r'), len(decoded)), (2, 2, 6))
        self.assertTrue(all(flags & os.O_ACCMODE == os.O_RDONLY for flags in opens))
        self.assertTrue(r['archive_bytes_identical'])

    def test_same_path_roles_are_each_checked_and_input_files_unchanged(self):
        before = {p.relative_to(self.root).as_posix(): (p.read_bytes(), p.stat().st_mode) for p in self.root.rglob('*') if p.is_file()}
        r = self.m.compare_suite_archives(self.left, sha(self.raw), self.left, sha(self.raw))
        self.assertEqual(r['difference_count'], 0)
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): (p.read_bytes(), p.stat().st_mode) for p in self.root.rglob('*') if p.is_file()})

    def test_core13_public_receipt_and_zip_format_are_unchanged(self):
        receipt = self.b.verify_suite_bytes(self.raw, sha(self.raw))
        verified, records = self.b._verified_suite(self.raw, sha(self.raw))
        self.assertEqual(receipt, verified)
        self.assertEqual(set(records), set(CASES))
        self.assertEqual(receipt, self.compare()['left'])
        self.assertEqual(self.b.build_suite_archive(self.source), self.raw)

    def test_file_and_byte_api_have_identical_canonical_reports(self):
        a = self.m.compare_suite_archives(self.left, sha(self.raw), self.right, sha(self.raw))
        self.assertEqual(canonical(a), canonical(self.compare()))

    def test_cli_identical_difference_and_rejection_exit_codes(self):
        p = self.command()
        self.assertEqual((p.returncode, p.stderr, p.stdout), (0, b'', canonical(self.compare())))
        other = self.modified([('late-invalid', 'RESULTS.json', lambda r: r['identity'].update(marker=None))])
        self.right.write_bytes(other)
        p = self.command()
        self.assertEqual((p.returncode, p.stderr, p.stdout), (1, b'', canonical(self.compare(other))))
        p = self.command(right_sha='0' * 64)
        self.assertEqual((p.returncode, p.stdout), (2, b''))
        self.assertIn(b'ARCHIVE_COMPARE_RIGHT:PORTABLE_ARCHIVE_CHECKSUM', p.stderr)

    def test_cli_rejects_missing_digest_abbreviation_and_unapproved_modes(self):
        for extra in (('--run',), ('--extract',), ('--r', '0'), ('--format', 'markdown'), ('--output', 'x')):
            p = self.command(extra=extra)
            self.assertEqual((p.returncode, p.stdout), (2, b''))
        for args in ([], ['--left-archive', str(self.left)], ['--left-a', str(self.left)]):
            p = subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence_archive_compare.py', *args], capture_output=True)
            self.assertEqual((p.returncode, p.stdout), (2, b''))

    def cli_module(self):
        spec = importlib.util.spec_from_file_location('core14_test_cli', ROOT / 'tools/core_sequence_archive_compare.py')
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def args(self):
        return ['--left-archive', str(self.left), '--left-sha256', sha(self.raw), '--right-archive', str(self.right), '--right-sha256', sha(self.raw)]

    def test_cli_cache_cleanup_failure_precedes_any_summary_output(self):
        cli = self.cli_module()
        real = tempfile.TemporaryDirectory
        class FailingCleanup(real):
            def __exit__(self, exc, value, tb):
                super().__exit__(exc, value, tb)
                raise OSError('private cleanup path')
        before = sys.pycache_prefix
        with patch.object(cli.tempfile, 'TemporaryDirectory', FailingCleanup), patch.object(sys, 'stdout', io.StringIO()) as out, \
                patch.object(sys, 'stderr', io.StringIO()) as err:
            code = cli.main(self.args())
        self.assertEqual((code, out.getvalue(), err.getvalue()), (2, '', 'REJECTED: ARCHIVE_COMPARE_FAILED_NO_MODEL_EXECUTION\n'))
        self.assertEqual(sys.pycache_prefix, before)

    def test_cli_unexpected_api_failure_is_fixed_not_success(self):
        cli = self.cli_module()
        with patch.object(self.m, 'compare_suite_archives', side_effect=RuntimeError('private value')), \
                patch.object(sys, 'stdout', io.StringIO()) as out, patch.object(sys, 'stderr', io.StringIO()) as err:
            code = cli.main(self.args())
        self.assertEqual((code, out.getvalue(), err.getvalue()), (2, '', 'REJECTED: ARCHIVE_COMPARE_FAILED_NO_MODEL_EXECUTION\n'))

    def test_cli_stdout_failure_is_guarded_and_cache_setting_restored(self):
        cli = self.cli_module()
        real = os.write
        def fail(fd, data):
            if fd == sys.stdout.fileno(): raise OSError('private stdout failure')
            return real(fd, data)
        before = sys.pycache_prefix
        with patch.object(cli.os, 'write', side_effect=fail), patch.object(sys, 'stderr', io.StringIO()) as err:
            code = cli.main(self.args())
        self.assertEqual((code, err.getvalue()), (2, 'REJECTED: ARCHIVE_COMPARE_FAILED_NO_MODEL_EXECUTION\n'))
        self.assertEqual(sys.pycache_prefix, before)

    def test_fresh_cli_cannot_import_execution_or_extract(self):
        script = '''import importlib.abc, runpy, sys, zipfile
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.startswith(('cyberlateral_dev', 'integration_tools.core_sequence_run', 'numpy')): raise AssertionError(fullname)
sys.meta_path.insert(0, Block())
def forbidden(*a,**k): raise AssertionError('extract')
zipfile.ZipFile.extract=forbidden
zipfile.ZipFile.extractall=forbidden
cli=runpy.run_path(sys.argv[1],run_name='core14_blocked')
raise SystemExit(cli['main'](sys.argv[2:]))
'''
        p = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(ROOT / 'tools/core_sequence_archive_compare.py'), *self.args()], capture_output=True)
        self.assertEqual((p.returncode, p.stderr, p.stdout), (0, b'', canonical(self.compare())))

    def test_json_stdout_preserves_untrusted_metadata_as_data(self):
        other = self.modified([('late-invalid', 'RESULTS.json', lambda r: r['identity'].update(marker='<script>|`\n\x1b'))])
        self.right.write_bytes(other)
        p = self.command()
        self.assertEqual(p.returncode, 1)
        self.assertNotIn(b'\x1b', p.stdout)
        r = json.loads(p.stdout)
        self.assertEqual(r['reports'][2]['comparison']['differences'][0]['right'], '<script>|`\n\x1b')

    def large_identity_pair(self, cases, width):
        key = '/' * width
        left = self.modified([(c, 'RESULTS.json', lambda r: r['identity'].update({key: [0] * 300})) for c in cases])
        right = self.modified([(c, 'RESULTS.json', lambda r: r['identity'].update({key: [1] * 300})) for c in cases])
        return left, right

    def test_oversized_path_details_are_rejected_before_report_materialization(self):
        left, right = self.large_identity_pair(('late-invalid',), 16384)
        with patch.object(self.m, '_compare_captured', side_effect=AssertionError('report materialization before byte guard')), \
                self.assertRaisesRegex(self.m.ArchiveCompareError, '^ARCHIVE_COMPARE_DETAIL_BYTE_LIMIT$'):
            self.m.compare_suite_archive_bytes(left, sha(left), right, sha(right))

    def test_cli_oversized_diagnostics_reject_without_large_or_partial_stdout(self):
        left, right = self.large_identity_pair(('late-invalid',), 16384)
        self.left.write_bytes(left); self.right.write_bytes(right)
        p = subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence_archive_compare.py',
            '--left-archive', self.left, '--left-sha256', sha(left), '--right-archive', self.right, '--right-sha256', sha(right)], capture_output=True)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(len(p.stdout), 0)
        self.assertEqual(p.stderr, b'REJECTED: ARCHIVE_COMPARE_DETAIL_BYTE_LIMIT\n')

    def test_detail_byte_budget_is_aggregate_not_reset_for_each_case(self):
        left, right = self.large_identity_pair(('sign-cycle', 'declared-difference'), 4096)
        with self.assertRaisesRegex(self.m.ArchiveCompareError, '^ARCHIVE_COMPARE_DETAIL_BYTE_LIMIT$'):
            self.m.compare_suite_archive_bytes(left, sha(left), right, sha(right))

    def test_large_under_budget_details_preserve_counts_and_exact_byte_accounting(self):
        left, right = self.large_identity_pair(('late-invalid',), 4096)
        r = self.m.compare_suite_archive_bytes(left, sha(left), right, sha(right))
        self.assertEqual((r['difference_count'], r['reported_difference_count']), (300, 256))
        self.assertTrue(r['differences_truncated'])
        self.assertEqual(r['detail_byte_limit'], 4194304)
        self.assertEqual(r['reported_difference_bytes'], sum(len(canonical(d)) for v in r['reports'] for d in v['comparison']['differences']))
        self.assertLessEqual(r['reported_difference_bytes'], 4194304)
