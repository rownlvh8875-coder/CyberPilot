"""Real committed bytes and corrupt ZIPs exercise the archive trust boundary."""

import hashlib
import importlib
import io
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))


class ArtifactTests(unittest.TestCase):
    def module(self):
        self.assertTrue((TOOLS / 'artifacts.py').is_file(), 'artifact implementation missing')
        return importlib.import_module('artifacts')

    def repository(self, root):
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        source = root / 'tools/cyberlateral_dev/sample.txt'
        source.parent.mkdir(parents=True)
        source.write_bytes(b'original\r\n')
        subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(root), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                        'commit', '-qm', 'fixture'], check=True)
        commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD']).decode().strip()
        return source, commit

    def test_export_reads_committed_bytes_not_dirty_or_untracked_content(self):
        a = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, commit = self.repository(root / 'repo')
            source.write_bytes(b'dirty')
            (source.parent / 'untracked.txt').write_bytes(b'private')
            result = a.export_source(root / 'repo', commit, root / 'export')
            self.assertEqual((root / 'export/tools/cyberlateral_dev/sample.txt').read_bytes(), b'original\r\n')
            self.assertFalse((root / 'export/tools/cyberlateral_dev/untracked.txt').exists())
            self.assertEqual(result['commit'], commit)
            self.assertEqual(result['files']['tools/cyberlateral_dev/sample.txt']['byte_size'], 10)
            self.assertEqual(source.read_bytes(), b'dirty')

    def test_export_rejects_revision_options_and_short_ids(self):
        a = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, commit = self.repository(root / 'repo')
            for value in ['HEAD', commit[:8], '--help', '../HEAD']:
                with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'FULL_COMMIT_REQUIRED'):
                    a.export_source(root / 'repo', value, root / 'export')
            self.assertFalse((root / 'export').exists())

    def test_export_rejects_committed_symlink(self):
        a = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, _ = self.repository(root / 'repo')
            (source.parent / 'link').symlink_to('/etc/passwd')
            subprocess.run(['git', '-C', str(root / 'repo'), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(root / 'repo'), '-c', 'user.name=Fixture', '-c',
                            'user.email=fixture@example.invalid', 'commit', '-qm', 'link'], check=True)
            commit = subprocess.check_output(['git', '-C', str(root / 'repo'), 'rev-parse', 'HEAD']).decode().strip()
            with self.assertRaisesRegex(ValueError, 'SOURCE_MODE'):
                a.export_source(root / 'repo', commit, root / 'export')

    def test_seal_is_deterministic_and_manifest_covers_every_payload(self):
        a = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = a.seal(root / 'one.zip', {'z.txt': b'z\n', 'nested/a.txt': b'a\n'})
            second = a.seal(root / 'two.zip', {'nested/a.txt': b'a\n', 'z.txt': b'z\n'})
            self.assertEqual((root / 'one.zip').read_bytes(), (root / 'two.zip').read_bytes())
            self.assertEqual(first['archive_sha256'], second['archive_sha256'])
            verified = a.verify_archive(root / 'one.zip', first['archive_sha256'])
            self.assertEqual(verified['member_count'], 3)
            self.assertEqual(set(verified['members']), {'z.txt', 'nested/a.txt', 'SHA256SUMS.txt'})
            with zipfile.ZipFile(root / 'one.zip') as archive:
                self.assertEqual(archive.read('SHA256SUMS.txt'),
                    (hashlib.sha256(b'a\n').hexdigest() + '  nested/a.txt\n' + hashlib.sha256(b'z\n').hexdigest() + '  z.txt\n').encode())

    def test_seal_rejects_empty_or_caller_supplied_manifest(self):
        a = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            for members in [{}, {'SHA256SUMS.txt': b'forged'}]:
                with self.subTest(members=members), self.assertRaises(ValueError):
                    a.seal(Path(tmp) / 'bad.zip', members)
            self.assertFalse((Path(tmp) / 'bad.zip').exists())

    def test_unsafe_alias_and_file_directory_names_are_rejected(self):
        a = self.module()
        cases = [{'../escape': b'x'}, {'/root': b'x'}, {'a\\b': b'x'}, {'a:b': b'x'},
                 {'CON.txt': b'x'}, {'a.': b'x'}, {'a\nx': b'x'}, {'a': b'x', 'A': b'y'},
                 {'a': b'x', 'a/b': b'y'}, {'cafe\u0301.txt': b'x'}]
        with tempfile.TemporaryDirectory() as tmp:
            for members in cases:
                with self.subTest(names=list(members)), self.assertRaisesRegex(ValueError, 'UNSAFE_MEMBER'):
                    a.seal(Path(tmp) / 'bad.zip', members)

    def test_output_collision_and_broken_symlink_are_not_overwritten(self):
        a = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / 'existing.zip'
            existing.write_bytes(b'keep')
            broken = root / 'broken.zip'
            broken.symlink_to(root / 'absent')
            for path in [existing, broken]:
                with self.subTest(path=path.name), self.assertRaises(FileExistsError):
                    a.seal(path, {'ok': b'ok'})
            self.assertEqual(existing.read_bytes(), b'keep')
            self.assertTrue(broken.is_symlink())

    def test_secret_shaped_payload_is_not_sealed(self):
        a = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            for raw in [b'hf_' + b'x' * 30, b'-----BEGIN ' + b'PRIVATE KEY-----']:
                with self.subTest(raw_length=len(raw)), self.assertRaisesRegex(ValueError, 'CREDENTIAL_SHAPED_PAYLOAD'):
                    a.seal(Path(tmp) / 'secret.zip', {'data.txt': raw})

    def test_oversized_payload_is_rejected_before_archive_write(self):
        a = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'large.zip'
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_LIMIT'):
                a.seal(path, {'large': b'x' * (8 * 1024 * 1024 + 1)})
            self.assertFalse(path.exists())

    def corrupt(self, root, change):
        a = self.module()
        path = root / 'source.zip'
        a.seal(path, {'a.txt': b'hello'})
        with zipfile.ZipFile(path) as archive:
            files = {n: archive.read(n) for n in archive.namelist()}
        change(files)
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as archive:
            for name, value in files.items():
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(info, value)
        target = root / 'mutated.zip'
        target.write_bytes(raw.getvalue())
        return target

    def test_bad_hash_missing_and_extra_members_are_detected(self):
        a = self.module()
        cases = [lambda f: f.update({'a.txt': b'wrong'}), lambda f: f.pop('a.txt'),
                 lambda f: f.update({'extra.txt': b'x'})]
        for change in cases:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                path = self.corrupt(Path(tmp), change)
                with self.assertRaisesRegex(ValueError, 'ARCHIVE_(HASH|CLOSURE)'):
                    a.verify_archive(path)

    def test_explicit_archive_hash_and_nonregular_member_are_rejected(self):
        a = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'ok.zip'
            a.seal(path, {'a': b'a'})
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_HASH'):
                a.verify_archive(path, '0' * 64)
            bad = Path(tmp) / 'link.zip'
            with zipfile.ZipFile(bad, 'w') as archive:
                info = zipfile.ZipInfo('link')
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, b'/etc/passwd')
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_MODE'):
                a.verify_archive(bad)

    def test_consistently_resealed_secret_is_rejected_on_backup_ingress(self):
        a = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            secret = b'hf_' + b'x' * 30
            def change(files):
                files['a.txt'] = secret
                files['SHA256SUMS.txt'] = (hashlib.sha256(secret).hexdigest() + '  a.txt\n').encode()
            path = self.corrupt(Path(tmp), change)
            with self.assertRaisesRegex(ValueError, 'CREDENTIAL_SHAPED_PAYLOAD'):
                a.verify_archive(path)

    def test_raw_nul_header_name_is_rejected_before_python_truncation(self):
        a = self.module()
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as archive:
            for name, data in [('aXb', b'value'), ('SHA256SUMS.txt',
                                (hashlib.sha256(b'value').hexdigest() + '  a\n').encode())]:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(info, data)
        # ZipInfo construction itself truncates NUL, so mutate both raw headers.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'nul.zip'
            path.write_bytes(raw.getvalue().replace(b'aXb', b'a\0b'))
            with self.assertRaisesRegex(ValueError, 'UNSAFE_MEMBER'):
                a.verify_archive(path)


if __name__ == '__main__':
    unittest.main()
