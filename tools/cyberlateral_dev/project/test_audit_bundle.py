"""Bounded data-only bundle export, snapshot identity and offline verification."""

import builtins
import contextlib
import hashlib
import importlib
import io
import json
import struct
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


class AuditBundleTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/audit_bundle.py').is_file(), 'Missing planned fixed audit bundle')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.audit_bundle')

    def evidence(self, root):
        self.module()
        helper = importlib.import_module('test_handoff_audit').HandoffAuditTests('test_complete_source_to_table_mapping')
        source, paths = helper.sources(root)
        audit = helper.module()
        for name in ['audit_one', 'audit_two']:
            target = root / name
            audit.write_audit(*paths, target)
            (target / 'EXECUTION.json').write_bytes(audit.canonical({'isolated': True, 'forbidden_modules_loaded': []}))
            helper.manifest(target)
        return source

    def members(self, path):
        with zipfile.ZipFile(path) as archive:
            return {name: archive.read(name) for name in archive.namelist()}

    def archive(self, items, compression=zipfile.ZIP_STORED, mode=0o100644, timestamp=(1980, 1, 1, 0, 0, 0)):
        stream = io.BytesIO()
        with warnings.catch_warnings(), zipfile.ZipFile(stream, 'w') as archive:
            warnings.simplefilter('ignore', UserWarning)
            for name, raw in items:
                info = zipfile.ZipInfo(name, timestamp)
                info.create_system = 3
                info.external_attr = mode << 16
                info.compress_type = compression
                archive.writestr(info, raw)
        return stream.getvalue()

    def rewrite_manifest(self, files):
        files['SHA256SUMS.txt'] = ''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n'
                                         for name, raw in sorted(files.items()) if name != 'SHA256SUMS.txt').encode()

    def test_export_and_verify_exact_payloads(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source = self.evidence(root)
            m.write_bundle(root, root / 'out')
            target = root / 'out' / m.ZIP_NAME
            result = m.verify_bundle(target)
            self.assertEqual((result['archive_members'], result['manifest_entries'], result['scenario_count'], result['rows'], result['columns']), (17, 16, 7, 112, 37))
            self.assertEqual((result['model_steps'], result['extractor_calls']), (0, 0))
            self.assertEqual(result, json.loads((root / 'out/RESULTS.json').read_bytes()))
            self.assertEqual(result['bundle_sha256'], hashlib.sha256(target.read_bytes()).hexdigest())
            payloads = self.members(target)
            expected = {f'{folder}/{name}' for folder in ['lifecycle_one', 'lifecycle_two'] for name in ['RESULTS.json', 'SHA256SUMS.txt']}
            expected |= {f'{folder}/{name}' for folder in ['audit_one', 'audit_two'] for name in ['AUDIT.json', 'audit.csv', 'SUMMARY_KO.md', 'EXECUTION.json', 'SHA256SUMS.txt']}
            self.assertEqual(set(payloads), expected | {'BUNDLE.json', 'README_KO.md', 'SHA256SUMS.txt'})
            for name in expected:
                self.assertEqual(payloads[name], (root / name).read_bytes())
            metadata = json.loads(payloads['BUNDLE.json'])
            self.assertEqual(metadata['source_lifecycle_sha256'], 'd6dfe2ba38ac52c4924c0a8aa02b5a78c31200cee76e2d3ad943e3f1c10035fe')
            self.assertEqual(metadata['audit_sha256'], 'b3c41ca1d309d47a003d2ca866a1c1d1283eb51d79383f7f8d0b551e596d71a7')
            self.assertEqual(metadata['gates'], source['gates'])
            self.assertEqual(metadata['source_execution_counts'], {'model_steps': 9010, 'extractor_calls': 9010})
            self.assertEqual(metadata['bundle_execution_counts'], {'model_steps': 0, 'extractor_calls': 0, 'F61': 0, 'r_calculations': 0, 'dt_calculations': 0})

    def test_canonical_zip_metadata_and_determinism(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.evidence(root)
            for name in ['one', 'two']:
                m.write_bundle(root, root / name)
            raw = (root / 'one' / m.ZIP_NAME).read_bytes()
            self.assertEqual(raw, (root / 'two' / m.ZIP_NAME).read_bytes())
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                self.assertEqual(archive.namelist(), sorted(archive.namelist()))
                for info in archive.infolist():
                    self.assertEqual((info.date_time, info.compress_type, info.create_system, info.external_attr >> 16), ((1980, 1, 1, 0, 0, 0), 0, 3, 0o100644))
                    self.assertFalse(info.filename.endswith(('.py', '.whl')))
            files = self.members(root / 'one' / m.ZIP_NAME)
            for bad in [raw + b'TRAILING', self.archive(sorted(files.items()), timestamp=(2000, 1, 1, 0, 0, 0))]:
                with self.assertRaisesRegex(ValueError, 'BUNDLE_'):
                    m._verify_bytes(bad)

    def test_reject_corrupt_source_before_output(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.evidence(root)
            (root / 'audit_two/AUDIT.json').write_bytes(b'{}\n')
            with self.assertRaises(ValueError):
                m.write_bundle(root, root / 'bad')
            self.assertFalse((root / 'bad').exists())
            with self.assertRaises(ValueError):
                m.write_bundle(root / 'missing', root / 'also_bad')
            self.assertFalse((root / 'also_bad').exists())

    def test_snapshot_not_reread_and_zero_model_work(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.evidence(root)
            collect = m._collect_snapshot
            original_import = builtins.__import__
            p = package_feature()
            boundary = importlib.import_module('integration_tools.message_boundary')

            def captured_then_changed(path):
                data = collect(path)
                (path / 'audit_one/AUDIT.json').write_bytes(b'{}\n')
                return data

            def forbid(name, *args, **kwargs):
                if name.split('.')[0] in {'cyberlateral_dev', 'numpy', 'openpilot', 'opendbc', 'cereal', 'capnp'}:
                    raise AssertionError('NO_MODEL_OR_NATIVE_IMPORT')
                return original_import(name, *args, **kwargs)

            with patch.object(m, '_collect_snapshot', side_effect=captured_then_changed), patch.object(builtins, '__import__', side_effect=forbid), \
                    patch.object(p, 'step', side_effect=AssertionError('NO_STEP')), patch.object(p, 'simulate', side_effect=AssertionError('NO_SIMULATE')), \
                    patch.object(boundary, 'extract_synthetic_message', side_effect=AssertionError('NO_EXTRACT')):
                m.write_bundle(root, root / 'out')
                result = m.verify_bundle(root / 'out' / m.ZIP_NAME)
            self.assertEqual(result['audit_sha256'], 'b3c41ca1d309d47a003d2ca866a1c1d1283eb51d79383f7f8d0b551e596d71a7')
            self.assertNotEqual(self.members(root / 'out' / m.ZIP_NAME)['audit_one/AUDIT.json'], (root / 'audit_one/AUDIT.json').read_bytes())

    def test_archive_member_and_path_rejections(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.evidence(root)
            m.write_bundle(root, root / 'out')
            items = sorted(self.members(root / 'out' / m.ZIP_NAME).items())
            variants = [items[:-1], items + [items[0]]]
            for name in ['extra', '../escape', '/absolute', 'C:/drive', 'audit_one\\AUDIT.json', 'directory/']:
                variants.append(items[:-1] + [(name, items[-1][1])])
            with patch.object(m, '_validate_data', side_effect=AssertionError('NO_MATERIALIZATION')):
                for index, bad in enumerate(variants):
                    with self.subTest(index=index), self.assertRaisesRegex(ValueError, 'BUNDLE_'):
                        m._verify_bytes(self.archive(bad))
                with self.assertRaisesRegex(ValueError, 'BUNDLE_'):
                    m._verify_bytes(self.archive(items, mode=0o120777))

    def test_archive_content_and_metadata_tampering(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.evidence(root)
            m.write_bundle(root, root / 'out')
            original = self.members(root / 'out' / m.ZIP_NAME)
            for mutation in ['gate', 'hash', 'readme', 'manifest', 'report_rows']:
                files = dict(original)
                metadata = json.loads(files['BUNDLE.json'])
                if mutation == 'gate':
                    metadata['gates']['STATIC_EVIDENCE_GATE'] = 'PASS'
                elif mutation == 'hash':
                    metadata['audit_sha256'] = '0' * 64
                elif mutation == 'readme':
                    files['README_KO.md'] += b'PROMOTED\n'
                elif mutation == 'report_rows':
                    for folder in ['audit_one', 'audit_two']:
                        row = json.loads(files[folder + '/AUDIT.json'])
                        row['rows'][0]['final_command'] = 999
                        files[folder + '/AUDIT.json'] = m.canonical(row)
                        local = {name.split('/', 1)[1]: raw for name, raw in files.items() if name.startswith(folder + '/')}
                        self.rewrite_manifest(local)
                        files[folder + '/SHA256SUMS.txt'] = local['SHA256SUMS.txt']
                    metadata['data_sha256'] = {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items() if '/' in name}
                    metadata['audit_sha256'] = hashlib.sha256(files['audit_one/AUDIT.json']).hexdigest()
                files['BUNDLE.json'] = m.canonical(metadata)
                self.rewrite_manifest(files)
                if mutation == 'manifest':
                    files['SHA256SUMS.txt'] = b'BAD\n'
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    m._verify_bytes(self.archive(sorted(files.items())))
            raw = bytearray((root / 'out' / m.ZIP_NAME).read_bytes())
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                info = archive.getinfo('README_KO.md')
                raw[info.header_offset + 30 + len(info.filename) + len(info.extra)] ^= 1
            with self.assertRaisesRegex(ValueError, 'BUNDLE_'):
                m._verify_bytes(bytes(raw))

    def test_archive_resource_limits(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.evidence(root)
            m.write_bundle(root, root / 'out')
            files = self.members(root / 'out' / m.ZIP_NAME)
            oversized = root / 'oversized.zip'
            oversized.write_bytes(b'x' * (8 * 1024 * 1024 + 1))
            member = dict(files)
            member['lifecycle_one/RESULTS.json'] = b'x' * (4 * 1024 * 1024 + 1)
            declared = bytearray(self.archive(sorted(files.items())))
            with zipfile.ZipFile(io.BytesIO(declared)) as archive:
                position = archive.start_dir
            for _ in range(4):
                struct.pack_into('<I', declared, position + 24, 3 * 1024 * 1024)
                name_size, extra_size, comment_size = struct.unpack_from('<HHH', declared, position + 28)
                position += 46 + name_size + extra_size + comment_size
            with patch.object(m, '_validate_data', side_effect=AssertionError('NO_MATERIALIZATION')):
                with self.assertRaisesRegex(ValueError, 'BUNDLE_.*LIMIT'):
                    m.verify_bundle(oversized)
                for bad in [self.archive(sorted(member.items())), bytes(declared)]:
                    with self.assertRaisesRegex(ValueError, 'BUNDLE_.*LIMIT'):
                        m._verify_bytes(bad)
                with self.assertRaisesRegex(ValueError, 'BUNDLE_'):
                    m._verify_bytes(self.archive(sorted(files.items()), compression=zipfile.ZIP_DEFLATED))

    def test_existing_output_and_failed_publication(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.evidence(root)
            targets = [root / 'file', root / 'directory', root / 'dangling']
            targets[0].write_bytes(b'KEEP')
            targets[1].mkdir()
            targets[2].symlink_to(root / 'absent', target_is_directory=True)
            with patch.object(m, '_collect_snapshot', side_effect=AssertionError('NO_READ')):
                for target in targets:
                    with self.assertRaises(FileExistsError):
                        m.write_bundle(root, target)
            original = Path.open

            def fail_checksum(path, *args, **kwargs):
                if path.name == m.ZIP_NAME + '.sha256' and args and args[0] == 'xb':
                    raise OSError('SYNTHETIC_CHECKSUM_FAILURE')
                return original(path, *args, **kwargs)

            with patch.object(Path, 'open', fail_checksum), self.assertRaises(OSError):
                m.write_bundle(root, root / 'failed')
            self.assertFalse((root / 'failed' / m.ZIP_NAME).exists())
            self.assertEqual(targets[0].read_bytes(), b'KEEP')

    def test_isolated_installed_bundle_pair(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            evidence = root / 'artifacts'
            evidence.mkdir()
            self.evidence(evidence)
            v = importlib.import_module('integration_tools.verify')
            self.assertTrue(callable(getattr(v, 'verify_installed_bundle', None)), 'Missing installed bundle gate')
            backend = importlib.import_module('build_backend')
            name = backend.build_wheel(str(root / 'dist'))
            subprocess.run([sys.executable, '-B', '-m', 'venv', '--without-pip', str(root / 'env')], check=True, capture_output=True)
            py = root / 'env/bin/python'
            subprocess.run(['uv', 'pip', 'install', '--offline', '--no-deps', '--link-mode=copy', '--python', str(py), str(root / 'dist' / name)], check=True, capture_output=True)
            result = v.verify_installed_bundle(ROOT, py, evidence, root)
            self.assertEqual((result['archive_members'], result['rows'], result['model_steps']), (17, 112, 0))
            self.assertEqual(json.loads((evidence / 'bundle_one/EXECUTION.json').read_bytes()), {'isolated': True, 'forbidden_modules_loaded': []})
            (evidence / 'bundle_two/RESULTS.json').write_bytes(b'{}\n')
            with self.assertRaisesRegex(ValueError, 'BUNDLE_'):
                m.bundle_pair_summary(evidence / 'bundle_one', evidence / 'bundle_two')

    def test_cli_verify_is_read_only_and_invalid_flags(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.evidence(root)
            m.write_bundle(root, root / 'out')
            target = root / 'out' / m.ZIP_NAME
            before = target.read_bytes()
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(m.main(['verify', '--bundle', str(target)]), 0)
            printed = json.loads(stdout.getvalue())
            self.assertEqual(printed['result']['bundle_sha256'], hashlib.sha256(before).hexdigest())
            self.assertEqual(target.read_bytes(), before)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(m.main(['verify', '--bundle', str(root / 'missing.zip')]), 2)
            with patch.object(m, '_collect_snapshot', side_effect=AssertionError('NO_READ')):
                for flag in ['--data', '--native', '--r', '--dt', '--extract']:
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                        m.main(['export', '--evidence', str(root), '--output', str(root / 'unused'), flag, 'UNSUPPORTED'])
            self.assertFalse((root / 'unused').exists())


if __name__ == '__main__':
    unittest.main()
