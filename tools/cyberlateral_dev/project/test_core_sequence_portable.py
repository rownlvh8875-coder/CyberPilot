"""Exact saved-byte custody, hostile ZIP bounds and no-execution publication."""

import hashlib
import importlib
import importlib.util
import io
import json
import os
import struct
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
MEMBERS = ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CoreSequencePortableTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_sequence_portable.py').is_file(), 'Missing CORE13 portable saved-suite boundary')
        self.assertTrue((ROOT / 'tools/core_sequence_portable.py').is_file(), 'Missing CORE13 portable CLI')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.core_sequence_portable')
        self.b: Any = importlib.import_module('integration_tools.core_sequence_bundle')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.suite = self.root / 'suite'
        self.suite.mkdir()
        producer = importlib.import_module('integration_tools.core_sequence_run')
        for case in CASES:
            producer.run_sequence_case(case, self.suite / case)

    def source(self):
        return {'suite/' + c + '/' + n: (self.suite / c / n).read_bytes() for c in CASES for n in MEMBERS}

    def archive(self):
        raw = self.b.build_suite_archive(self.source())
        return raw, sha(raw)

    def command(self, *args):
        return subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence_portable.py', *args], capture_output=True)

    def zip(self, files, *, compress=0, comment=b'', reverse=False, extras=None):
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w', compression=compress) as z:
            z.comment = comment
            names = sorted(files, reverse=reverse)
            for name in names:
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = compress
                if extras is not None:
                    extras(info)
                z.writestr(info, files[name])
        return out.getvalue()

    def files(self):
        raw, _ = self.archive()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            return {n: z.read(n) for n in z.namelist()}

    def refresh(self, files):
        files['SHA256SUMS.txt'] = ''.join(sha(files[n]) + '  ' + n + '\n' for n in sorted(files) if n != 'SHA256SUMS.txt').encode()

    def reject(self, raw, code='PORTABLE_'):
        with self.assertRaisesRegex(self.m.PortableError, code):
            self.b.verify_suite_bytes(raw, sha(raw))

    def test_export_preserves_nine_literal_source_files_and_saved_outcomes(self):
        before = self.source()
        report = self.m.export_saved_suite(self.suite, self.root / 'a.zip')
        raw = (self.root / 'a.zip').read_bytes()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertEqual(len(z.infolist()), 11)
            self.assertIsNone(z.testzip())
            for name, data in before.items():
                self.assertEqual(z.read(name), data)
        self.assertEqual(report['archive_sha256'], sha(raw))
        self.assertEqual(report['suite']['saved_status_counts'], {'MATCH': 1, 'DIFFERENT': 1, 'REJECTED': 1})
        self.assertEqual(report['suite']['recorded_model_steps'], 6)
        self.assertEqual(report['new_synthetic_model_steps'], 0)
        self.assertIsNone(report['suite']['difference_count'])
        self.assertFalse(report['source_identity_reauthenticated'])
        self.assertEqual(before, self.source())

    def test_deterministic_zip_has_fixed_metadata_and_independently_valid_manifests(self):
        raw, digest = self.archive()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertEqual(z.namelist(), sorted([*self.source(), 'SUITE_REPORT.json', 'SHA256SUMS.txt']))
            for info in z.infolist():
                self.assertEqual((info.compress_type, info.date_time, info.external_attr, info.extra, info.comment),
                                 (0, (1980, 1, 1, 0, 0, 0), 0o100644 << 16, b'', b''))
            for line in z.read('SHA256SUMS.txt').decode().splitlines():
                expected, name = line.split('  ')
                self.assertEqual(sha(z.read(name)), expected)
        self.m.export_saved_suite(self.suite, self.root / 'elsewhere.zip')
        self.assertEqual((self.root / 'elsewhere.zip').read_bytes(), raw)
        r = self.b.verify_suite_bytes(raw, digest)
        self.assertEqual((r['member_count'], r['source_member_count']), (11, 9))

    def test_existing_core9_loader_and_core12_report_stay_byte_compatible(self):
        saved = importlib.import_module('integration_tools.core_sequence_saved')
        suite = importlib.import_module('integration_tools.core_sequence_suite')
        for c in CASES:
            decoded = saved.read_saved_sequence_records(self.suite / c)
            self.assertEqual(set(decoded), {'input_record', 'result_record', 'summary'})
            self.assertEqual(decoded, saved._decode({n: (self.suite / c / n).read_bytes() for n in MEMBERS}))
        files = self.files()
        self.assertEqual(files['SUITE_REPORT.json'], canonical(suite.check_closed_suite(self.suite)))

    def test_expected_sha_is_required_before_path_access(self):
        for value in (None, True, '', 'a' * 63, 'A' * 64, 'g' * 64, 'a' * 65):
            with self.subTest(value=value), patch('os.open', side_effect=AssertionError('must not open')):
                with self.assertRaisesRegex(self.m.PortableError, '^PORTABLE_EXPECTED_SHA256$'):
                    self.m.verify_suite_archive(object(), value)

    def test_wrong_external_sha_and_wrong_byte_type_are_rejected(self):
        raw, digest = self.archive()
        with self.assertRaisesRegex(self.m.PortableError, 'PORTABLE_ARCHIVE_CHECKSUM'):
            self.b.verify_suite_bytes(raw, '0' * 64)
        with self.assertRaisesRegex(self.m.PortableError, 'PORTABLE_ARCHIVE'):
            self.b.verify_suite_bytes(bytearray(raw), digest)

    def test_archive_and_source_caps_are_enforced(self):
        self.reject(b'x' * 2000001, 'PORTABLE_ARCHIVE_SIZE')
        source = self.source()
        source['suite/sign-cycle/INPUT.json'] = b'x' * 65537
        with self.assertRaisesRegex(self.m.PortableError, 'PORTABLE_'):
            self.b.build_suite_archive(source)

    def test_extra_missing_traversal_and_directory_members_are_rejected(self):
        for name in ('../outside', '/absolute', 'suite/sign-cycle/', 'unknown'):
            files = self.files(); files[name] = b'x'
            self.reject(self.zip(files))
        files = self.files(); del files['suite/late-invalid/RESULTS.json']
        self.reject(self.zip(files))

    def test_duplicate_member_is_rejected(self):
        files = self.files()
        out = io.BytesIO(self.zip(files))
        with self.assertWarns(UserWarning), zipfile.ZipFile(out, 'a') as z:
            z.writestr('SUITE_REPORT.json', files['SUITE_REPORT.json'])
        self.reject(out.getvalue())

    def test_compressed_symlink_and_executable_profiles_are_rejected(self):
        files = self.files()
        self.reject(self.zip(files, compress=zipfile.ZIP_DEFLATED))
        for mode in (0o120777, 0o100755):
            self.reject(self.zip(files, extras=lambda info, mode=mode: setattr(info, 'external_attr', mode << 16)))

    def test_metadata_order_prefix_suffix_and_comment_changes_are_rejected(self):
        files = self.files()
        raw, _ = self.archive()
        for altered in (b'prefix' + raw, raw + b'tail', self.zip(files, reverse=True), self.zip(files, comment=b'comment'),
                        self.zip(files, extras=lambda info: setattr(info, 'date_time', (2020, 1, 1, 0, 0, 0)))):
            self.reject(altered)

    def test_eocd_count_and_central_directory_bounds_precede_zip_parser(self):
        raw, _ = self.archive()
        for offset, value, fmt in ((8, 65535, '<H'), (12, 100000, '<L'), (4, 1, '<H')):
            altered = bytearray(raw)
            struct.pack_into(fmt, altered, len(raw) - 22 + offset, value)
            with patch.object(zipfile, 'ZipFile', side_effect=AssertionError('parser must not run')):
                self.reject(bytes(altered), 'PORTABLE_ZIP_FORMAT')

    def test_crc_damage_is_not_hidden_by_correct_whole_zip_sha(self):
        raw, _ = self.archive()
        broken = bytearray(raw)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            info = z.getinfo('SUITE_REPORT.json')
            start = info.header_offset + 30 + len(info.filename.encode())
        broken[start] ^= 1
        self.reject(bytes(broken))

    def test_root_manifest_damage_is_rejected(self):
        files = self.files(); files['SHA256SUMS.txt'] = b'forged\n'
        self.reject(self.zip(files), 'PORTABLE_MANIFEST')

    def test_promoted_or_noncanonical_report_with_refreshed_manifest_is_rejected(self):
        for kind in ('promote', 'whitespace'):
            files = self.files()
            r = json.loads(files['SUITE_REPORT.json'])
            if kind == 'promote':
                r['saved_status_counts'] = {'MATCH': 3, 'DIFFERENT': 0, 'REJECTED': 0}
                files['SUITE_REPORT.json'] = canonical(r)
            else:
                files['SUITE_REPORT.json'] += b' '
            self.refresh(files)
            self.reject(self.zip(files), 'PORTABLE_REPORT')

    def test_source_checksum_failure_is_rejected_even_with_root_manifest_refreshed(self):
        files = self.files(); files['suite/late-invalid/INPUT.json'] += b' '
        self.refresh(files)
        self.reject(self.zip(files), 'PORTABLE_CASE:late-invalid:INSPECT_CHECKSUM')

    def test_wrong_case_packet_cannot_use_another_directory_label(self):
        source = self.source()
        for n in MEMBERS:
            source['suite/sign-cycle/' + n] = source['suite/declared-difference/' + n]
        with self.assertRaisesRegex(self.m.PortableError, 'PORTABLE_CASE_ID:sign-cycle'):
            self.b.build_suite_archive(source)

    def test_closed_gate_violation_is_rejected_after_all_manifests_refreshed(self):
        files = self.files()
        name = 'suite/sign-cycle/RESULTS.json'
        r = json.loads(files[name]); r['gates']['R_BUDGET'] = 'RESOLVED'
        files[name] = canonical(r)
        files['suite/sign-cycle/SHA256SUMS.txt'] = ''.join(sha(files['suite/sign-cycle/' + n]) + '  ' + n + '\n'
            for n in ('INPUT.json', 'RESULTS.json')).encode()
        self.refresh(files)
        self.reject(self.zip(files), 'PORTABLE_CASE:sign-cycle:')

    def test_invalid_last_source_prevents_any_output(self):
        (self.suite / 'late-invalid/RESULTS.json').write_bytes(b'bad')
        target = self.root / 'never.zip'
        with self.assertRaises(self.m.PortableError):
            self.m.export_saved_suite(self.suite, target)
        self.assertFalse(target.exists())

    def test_output_guards_prevent_overwrite_source_overlap_and_checkout_write(self):
        existing = self.root / 'existing'; existing.write_bytes(b'keep')
        for output in (existing, self.suite / 'extra.zip', self.root / 'missing/x.zip', ROOT / 'no-core13-write.zip', 'bad'):
            with self.subTest(output=output), self.assertRaises(self.m.PortableError):
                self.m.export_saved_suite(self.suite, output)
        self.assertEqual(existing.read_bytes(), b'keep')
        self.assertEqual({p.name for p in self.suite.iterdir()}, set(CASES))

    def test_source_symlink_fifo_and_invalid_types_are_rejected(self):
        link = self.root / 'link'; link.symlink_to(self.suite)
        for source in (link, 'bad', self.root / 'missing'):
            with self.assertRaises(self.m.PortableError):
                self.m.export_saved_suite(source, self.root / 'no.zip')
        child = self.suite / 'sign-cycle/INPUT.json'; child.unlink(); os.mkfifo(child)
        with self.assertRaises(self.m.PortableError):
            self.m.export_saved_suite(self.suite, self.root / 'no.zip')
        self.assertFalse((self.root / 'no.zip').exists())

    def test_archive_symlink_parent_symlink_directory_and_fifo_are_rejected(self):
        raw, digest = self.archive()
        archive = self.root / 'real.zip'; archive.write_bytes(raw)
        link = self.root / 'link'; link.symlink_to(archive)
        parent = self.root / 'parent'; parent.symlink_to(self.root)
        fifo = self.root / 'fifo'; os.mkfifo(fifo)
        for path in (link, parent / 'real.zip', self.root, fifo, 'bad'):
            with self.subTest(path=path), self.assertRaises(self.m.PortableError):
                self.m.verify_suite_archive(path, digest)

    def test_export_source_is_captured_once_and_verify_file_opened_once(self):
        real = os.open
        opens = []
        def record(*args, **kwargs):
            opens.append(args[0])
            return real(*args, **kwargs)
        with patch('os.open', side_effect=record):
            r = self.m.export_saved_suite(self.suite, self.root / 'a.zip')
        self.assertEqual(len(opens), 15)
        opens.clear()
        with patch('os.open', side_effect=record):
            self.m.verify_suite_archive(self.root / 'a.zip', r['archive_sha256'])
        self.assertEqual(len(opens), 1)

    def test_partial_writes_complete_without_retrying_source(self):
        real = os.write
        def partial(fd, data):
            return real(fd, data[:17])
        with patch('os.write', side_effect=partial):
            r = self.m.export_saved_suite(self.suite, self.root / 'a.zip')
        self.assertEqual(r['archive_sha256'], sha((self.root / 'a.zip').read_bytes()))

    def test_zero_write_leaves_file_and_emits_no_success(self):
        with patch('os.write', return_value=0), self.assertRaisesRegex(self.m.PortableError, 'PUBLICATION_FAILED_PARTIAL_FILE_POSSIBLE'):
            self.m.export_saved_suite(self.suite, self.root / 'partial.zip')
        self.assertTrue((self.root / 'partial.zip').is_file())

    def test_readback_corruption_never_returns_export_success(self):
        raw, _ = self.archive()
        with patch.object(self.m, '_read_archive', return_value=raw + b'corrupted'), \
                self.assertRaisesRegex(self.m.PortableError, 'PUBLISHED_ARCHIVE_MISMATCH'):
            self.m.export_saved_suite(self.suite, self.root / 'exists.zip')
        self.assertTrue((self.root / 'exists.zip').is_file())

    def test_readback_io_failure_retains_published_file(self):
        with patch.object(self.m, '_read_archive', side_effect=OSError('private detail')), \
                self.assertRaisesRegex(self.m.PortableError, 'PUBLICATION_CHECK_FAILED_FILE_MAY_EXIST'):
            self.m.export_saved_suite(self.suite, self.root / 'exists.zip')
        self.assertTrue((self.root / 'exists.zip').is_file())

    def test_cli_export_verify_and_reject_exit_contract(self):
        output = self.root / 'cli.zip'
        p = self.command('export', '--input-root', str(self.suite), '--output', str(output))
        self.assertEqual((p.returncode, p.stderr), (0, b''))
        r = json.loads(p.stdout)
        self.assertEqual(p.stdout, canonical(r))
        p = self.command('verify', '--archive', str(output), '--sha256', r['archive_sha256'])
        self.assertEqual((p.returncode, p.stderr), (0, b''))
        self.assertEqual(json.loads(p.stdout)['status'], 'SUITE_ARCHIVE_VERIFIED')
        p = self.command('verify', '--archive', str(output), '--sha256', '0' * 64)
        self.assertEqual((p.returncode, p.stdout), (2, b''))
        self.assertIn(b'PORTABLE_ARCHIVE_CHECKSUM', p.stderr)

    def test_cli_has_no_run_extract_fallback_or_abbreviated_options(self):
        for args in ((), ('run',), ('extract',), ('verify', '--archive', 'x'),
                     ('export', '--input-r', str(self.suite), '--output', str(self.root / 'x'))):
            p = self.command(*args)
            self.assertEqual((p.returncode, p.stdout), (2, b''))

    def test_readonly_paths_do_not_import_producer_model_or_extract(self):
        raw, digest = self.archive()
        archive = self.root / 'a.zip'; archive.write_bytes(raw)
        script = '''import importlib.abc, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.startswith(('cyberlateral_dev', 'integration_tools.core_sequence_run', 'integration_tools.core_sequence_execution', 'numpy')):
   raise AssertionError('execution import: '+fullname)
sys.meta_path.insert(0, Block())
import zipfile
def forbidden(*a, **k): raise AssertionError('extraction forbidden')
zipfile.ZipFile.extract = forbidden
zipfile.ZipFile.extractall = forbidden
from integration_tools.core_sequence_portable import export_saved_suite, verify_suite_archive
r = export_saved_suite(Path(sys.argv[2]), Path(sys.argv[3]))
v = verify_suite_archive(Path(sys.argv[3]), r['archive_sha256'])
assert v['new_synthetic_model_steps'] == 0
assert v['suite']['reader_model_executions'] == 0
'''
        p = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(ROOT), str(self.suite), str(self.root / 'blocked.zip')], capture_output=True)
        self.assertEqual((p.returncode, p.stdout, p.stderr), (0, b'', b''))
        self.assertEqual(self.m.verify_suite_archive(archive, digest)['new_synthetic_model_steps'], 0)

    def test_cli_cleanup_failure_does_not_print_success_or_leak_exception(self):
        spec = importlib.util.spec_from_file_location('core13_cli_test', ROOT / 'tools/core_sequence_portable.py')
        assert spec is not None and spec.loader is not None
        cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
        original = tempfile.TemporaryDirectory
        class BadCleanup(original):
            def __exit__(self, exc, value, tb):
                super().__exit__(exc, value, tb)
                raise OSError('private cleanup')
        raw, digest = self.archive(); archive = self.root / 'a.zip'; archive.write_bytes(raw)
        before = sys.pycache_prefix
        with patch.object(cli.tempfile, 'TemporaryDirectory', BadCleanup), patch.object(sys, 'stdout', io.StringIO()) as out, \
                patch.object(sys, 'stderr', io.StringIO()) as err:
            self.assertEqual(cli.main(['verify', '--archive', str(archive), '--sha256', digest]), 2)
        self.assertEqual(out.getvalue(), '')
        self.assertEqual(err.getvalue(), 'REJECTED: PORTABLE_OPERATION_FAILED_NO_MODEL_EXECUTION\n')
        self.assertEqual(sys.pycache_prefix, before)

    def test_pure_source_names_and_types_are_closed(self):
        for mutate in (lambda f: f.update(extra=b'x'), lambda f: f.pop('suite/late-invalid/INPUT.json'),
                       lambda f: f.update({'suite/sign-cycle/INPUT.json': 'not bytes'})):
            source = self.source(); mutate(source)
            with self.assertRaises(self.m.PortableError):
                self.b.build_suite_archive(source)

    def test_readback_fixed_capture_error_reports_possible_existing_file(self):
        with patch.object(self.m, '_read_archive', side_effect=self.m.PortableError('PORTABLE_ARCHIVE_FILE')), \
                self.assertRaisesRegex(self.m.PortableError, '^PORTABLE_PUBLICATION_CHECK_FAILED_FILE_MAY_EXIST$'):
            self.m.export_saved_suite(self.suite, self.root / 'published.zip')
        self.assertTrue((self.root / 'published.zip').exists())

    def test_source_overlap_has_output_diagnostic_not_root_capture_diagnostic(self):
        with self.assertRaisesRegex(self.m.PortableError, '^PORTABLE_OUTPUT_SOURCE_OVERLAP$'):
            self.m.export_saved_suite(self.suite, self.suite / 'nested.zip')
