"""Read-only fetch tests: real archives, external storage transport only doubled."""

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
seal = importlib.import_module('artifacts').seal
fixtures = importlib.import_module('test_hf_archive')
COMMIT, REPO, MemoryHub = fixtures.COMMIT, fixtures.REPO, fixtures.MemoryHub

REVISION = '9' * 40


class ReadOnlyHub(MemoryHub):
    def commit(self, repo, parent, files):
        raise AssertionError('fetch must never upload')


class FetchTests(unittest.TestCase):
    def function(self):
        function = getattr(importlib.import_module('hf_archive'), 'fetch', None)
        self.assertTrue(callable(function), 'read-only pinned fetch is missing')
        return function

    def fixture(self, root, source=COMMIT):
        archive = root / 'fixture.zip'
        info = seal(archive, {'SOURCE_IDENTITY.json': json.dumps({'commit': source}).encode(),
                              'source.txt': b'fixed original\r\n'})
        digest = info['archive_sha256']
        prefix = f'runs/{COMMIT}/{digest}/'
        hub = ReadOnlyHub()
        hub.snapshots[REVISION] = {prefix + 'EVIDENCE.zip': archive.read_bytes(),
                                   prefix + 'SHA256SUMS.txt': (digest + '  EVIDENCE.zip\n').encode()}
        return digest, prefix, hub

    def test_fetch_uses_pinned_snapshot_without_upload_and_retains_exact_bytes(self):
        fetch = self.function()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest, prefix, hub = self.fixture(root)
            result = fetch(digest, REPO, COMMIT, REVISION, root / 'new', hub)
            self.assertEqual(result['status'], 'PRIVATE_FETCH_EXACT')
            self.assertEqual(result['commit_sha'], REVISION)
            self.assertEqual(result['verified_files'], 2)
            self.assertEqual((root / 'new/EVIDENCE.zip').read_bytes(), hub.snapshots[REVISION][prefix + 'EVIDENCE.zip'])
            self.assertEqual((root / 'new/SHA256SUMS.txt').read_bytes(), (digest + '  EVIDENCE.zip\n').encode())
            self.assertEqual(hub.head, '0' * 40)
            self.assertEqual(len(hub.snapshots), 2)

    def test_invalid_full_identities_are_rejected_before_output(self):
        fetch = self.function()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest, _, hub = self.fixture(root)
            for values in [('abc', COMMIT, REVISION), (digest, 'HEAD', REVISION),
                           (digest, COMMIT, 'main'), (digest.upper(), COMMIT, REVISION)]:
                with self.subTest(values=values), self.assertRaisesRegex(ValueError, 'FULL_'):
                    fetch(values[0], REPO, values[1], values[2], root / 'new', hub)
            self.assertFalse((root / 'new').exists())

    def test_public_or_wrong_owner_never_fetches_success(self):
        fetch = self.function()
        for field, value, error in [('private', False, 'PRIVATE_REPOSITORY_REQUIRED'),
                                     ('user', 'other', 'OWN_NAMESPACE_REQUIRED')]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                digest, _, hub = self.fixture(root)
                setattr(hub, field, value)
                with self.assertRaisesRegex(ValueError, error):
                    fetch(digest, REPO, COMMIT, REVISION, root / 'new', hub)

    def test_wrong_checksum_fails_even_when_zip_is_valid(self):
        fetch = self.function()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest, prefix, hub = self.fixture(root)
            hub.snapshots[REVISION][prefix + 'SHA256SUMS.txt'] = b'0' * 64 + b'  EVIDENCE.zip\n'
            with self.assertRaisesRegex(ValueError, 'CHECKSUM'):
                fetch(digest, REPO, COMMIT, REVISION, root / 'new', hub)

    def test_corrupt_archive_never_becomes_success(self):
        fetch = self.function()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest, prefix, hub = self.fixture(root)
            hub.snapshots[REVISION][prefix + 'EVIDENCE.zip'] = b'corrupt'
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_HASH'):
                fetch(digest, REPO, COMMIT, REVISION, root / 'new', hub)

    def test_wrong_source_label_is_not_recovered(self):
        fetch = self.function()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest, _, hub = self.fixture(root, source='2' * 40)
            with self.assertRaisesRegex(ValueError, 'SOURCE_COMMIT_MISMATCH'):
                fetch(digest, REPO, COMMIT, REVISION, root / 'new', hub)

    def test_upstream_exception_is_replaced_by_safe_code(self):
        fetch = self.function()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest, _, hub = self.fixture(root)
            hub.download_error = True
            with self.assertRaisesRegex(ValueError, '^STORAGE_DOWNLOAD_FAILED$'):
                fetch(digest, REPO, COMMIT, REVISION, root / 'new', hub)

    def test_existing_directory_and_broken_symlink_are_not_overwritten(self):
        fetch = self.function()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest, _, hub = self.fixture(root)
            existing = root / 'existing'
            existing.mkdir()
            (existing / 'keep.txt').write_bytes(b'preserved')
            broken = root / 'broken'
            broken.symlink_to(root / 'missing')
            for path in (existing, broken):
                with self.subTest(path=path.name), self.assertRaises(FileExistsError):
                    fetch(digest, REPO, COMMIT, REVISION, path, hub)
            self.assertEqual((existing / 'keep.txt').read_bytes(), b'preserved')
            self.assertTrue(broken.is_symlink())

    def test_visibility_change_during_read_is_rejected(self):
        fetch = self.function()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest, _, hub = self.fixture(root)
            original = hub.download

            def changing(*args):
                raw = original(*args)
                hub.private = False
                return raw

            hub.download = changing
            with self.assertRaisesRegex(ValueError, 'PRIVATE_REPOSITORY_REQUIRED'):
                fetch(digest, REPO, COMMIT, REVISION, root / 'new', hub)

    def test_symlink_parent_does_not_create_output_in_another_directory(self):
        fetch = self.function()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest, _, hub = self.fixture(root)
            real = root / 'real'
            real.mkdir()
            (root / 'alias').symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'RESTORE_PATH_SYMLINK'):
                fetch(digest, REPO, COMMIT, REVISION, root / 'alias/new', hub)
            self.assertEqual(list(real.iterdir()), [])

    def test_response_for_different_revision_is_not_accepted(self):
        fetch = self.function()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest, _, hub = self.fixture(root)
            original = hub.info
            hub.info = lambda repo, revision=None: original(repo)
            with self.assertRaisesRegex(ValueError, 'REMOTE_COMMIT_INVALID'):
                fetch(digest, REPO, COMMIT, REVISION, root / 'new', hub)


if __name__ == '__main__':
    unittest.main()
