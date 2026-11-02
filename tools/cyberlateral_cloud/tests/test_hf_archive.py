"""Exercise the private archival contract with a stateful external transport."""

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
seal = importlib.import_module('artifacts').seal

COMMIT = '1' * 40
REPO = 'owner/evidence'


class MemoryHub:
    """External service stand-in; no model/gate/business acceptance is replaced."""
    def __init__(self):
        self.private = True
        self.user = 'owner'
        self.snapshots = {'0' * 40: {}}
        self.head = '0' * 40
        self.upload_error = False
        self.download_error = False
        self.mutate_download = False
        self.turn_public_after_commit = False
        self.identity_callback = None

    def whoami(self):
        if self.identity_callback:
            self.identity_callback()
        return self.user

    def info(self, repo, revision=None):
        if repo != REPO:
            raise RuntimeError('unexpected repo')
        return {'private': self.private, 'sha': revision or self.head}

    def list_files(self, repo, revision):
        if repo != REPO:
            raise RuntimeError('unexpected repo')
        return set(self.snapshots[revision])

    def commit(self, repo, parent, files):
        if self.upload_error:
            raise RuntimeError('simulated upstream text must not escape')
        if repo != REPO or parent != self.head:
            raise RuntimeError('concurrent update')
        self.head = f'{len(self.snapshots):040x}'
        self.snapshots[self.head] = {**self.snapshots[parent], **files}
        if self.turn_public_after_commit:
            self.private = False
        return self.head

    def download(self, repo, name, revision, max_bytes):
        if self.download_error:
            raise RuntimeError('simulated download failure')
        raw = self.snapshots[revision][name]
        if repo != REPO or len(raw) > max_bytes:
            raise RuntimeError('unexpected read')
        return b'wrong' if self.mutate_download else raw


class ArchiveTests(unittest.TestCase):
    def module(self):
        self.assertTrue((TOOLS / 'hf_archive.py').is_file(), 'HF implementation missing')
        return importlib.import_module('hf_archive')

    def bundle(self, root):
        path = root / 'EVIDENCE.zip'
        sealed = seal(path, {'SOURCE_IDENTITY.json': json.dumps({'commit': COMMIT}).encode(), 'value.txt': b'fixed\n'})
        return path, sealed['archive_sha256']

    def test_private_upload_download_and_content_addressed_target(self):
        h = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self.bundle(Path(tmp))
            hub = MemoryHub()
            result = h.backup(path, digest, REPO, COMMIT, hub)
            self.assertEqual(result['status'], 'PRIVATE_BACKUP_EXACT')
            self.assertEqual(result['verified_files'], 2)
            self.assertEqual(result['prefix'], f'runs/{COMMIT}/{digest}/')
            self.assertEqual(hub.snapshots[hub.head][result['prefix'] + 'EVIDENCE.zip'], path.read_bytes())
            self.assertTrue(result['private'])

    def test_public_target_is_rejected_without_remote_write(self):
        h = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self.bundle(Path(tmp))
            hub = MemoryHub()
            hub.private = False
            with self.assertRaisesRegex(ValueError, 'PRIVATE_REPOSITORY_REQUIRED'):
                h.backup(path, digest, REPO, COMMIT, hub)
            self.assertEqual(hub.snapshots, {'0' * 40: {}})

    def test_wrong_account_and_bad_repo_id_do_not_write(self):
        h = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self.bundle(Path(tmp))
            hub = MemoryHub()
            hub.user = 'different-owner'
            with self.assertRaisesRegex(ValueError, 'OWN_NAMESPACE_REQUIRED'):
                h.backup(path, digest, REPO, COMMIT, hub)
            for repo in ['https://example.invalid', '../evidence', 'a/b/c']:
                with self.subTest(repo=repo), self.assertRaisesRegex(ValueError, 'REPO_ID'):
                    h.backup(path, digest, repo, COMMIT, hub)
            self.assertEqual(len(hub.snapshots), 1)

    def test_identical_backup_reuses_commit_but_verifies_downloads_again(self):
        h = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self.bundle(Path(tmp))
            hub = MemoryHub()
            first = h.backup(path, digest, REPO, COMMIT, hub)
            second = h.backup(path, digest, REPO, COMMIT, hub)
            self.assertEqual(second['commit_sha'], first['commit_sha'])
            self.assertTrue(second['reused_commit'])
            self.assertEqual(len(hub.snapshots), 2)
            hub.mutate_download = True
            with self.assertRaisesRegex(ValueError, 'DOWNLOAD_MISMATCH'):
                h.backup(path, digest, REPO, COMMIT, hub)

    def test_conflicting_or_partial_target_is_not_overwritten(self):
        h = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self.bundle(Path(tmp))
            hub = MemoryHub()
            prefix = f'runs/{COMMIT}/{digest}/'
            hub.snapshots[hub.head][prefix + 'EVIDENCE.zip'] = b'conflict'
            before = dict(hub.snapshots[hub.head])
            with self.assertRaisesRegex(ValueError, 'REMOTE_(CONFLICT|PARTIAL)'):
                h.backup(path, digest, REPO, COMMIT, hub)
            self.assertEqual(hub.snapshots[hub.head], before)
            self.assertEqual(len(hub.snapshots), 1)

    def test_upload_failure_keeps_local_archive_and_does_not_leak_upstream_text(self):
        h = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self.bundle(Path(tmp))
            hub = MemoryHub()
            hub.upload_error = True
            with self.assertRaisesRegex(ValueError, '^STORAGE_UPLOAD_FAILED$'):
                h.backup(path, digest, REPO, COMMIT, hub)
            self.assertTrue(path.is_file())
            self.assertEqual(len(hub.snapshots), 1)

    def test_download_failure_can_retry_existing_upload_without_new_commit(self):
        h = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self.bundle(Path(tmp))
            hub = MemoryHub()
            hub.download_error = True
            with self.assertRaisesRegex(ValueError, '^STORAGE_DOWNLOAD_FAILED$'):
                h.backup(path, digest, REPO, COMMIT, hub)
            self.assertEqual(len(hub.snapshots), 2)
            hub.download_error = False
            result = h.backup(path, digest, REPO, COMMIT, hub)
            self.assertTrue(result['reused_commit'])
            self.assertEqual(len(hub.snapshots), 2)

    def test_wrong_download_never_becomes_backup_success(self):
        h = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self.bundle(Path(tmp))
            hub = MemoryHub()
            hub.mutate_download = True
            with self.assertRaisesRegex(ValueError, 'DOWNLOAD_MISMATCH'):
                h.backup(path, digest, REPO, COMMIT, hub)

    def test_changed_privacy_after_upload_is_not_accepted(self):
        h = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self.bundle(Path(tmp))
            hub = MemoryHub()
            hub.turn_public_after_commit = True
            with self.assertRaisesRegex(ValueError, 'PRIVATE_REPOSITORY_REQUIRED'):
                h.backup(path, digest, REPO, COMMIT, hub)

    def test_archive_corruption_or_source_label_mismatch_never_uploads(self):
        h = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self.bundle(Path(tmp))
            hub = MemoryHub()
            with self.assertRaisesRegex(ValueError, 'SOURCE_COMMIT_MISMATCH'):
                h.backup(path, digest, REPO, '2' * 40, hub)
            path.write_bytes(path.read_bytes() + b'changed')
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_HASH'):
                h.backup(path, digest, REPO, COMMIT, hub)
            self.assertEqual(len(hub.snapshots), 1)

    def test_local_archive_change_during_preflight_is_not_uploaded(self):
        h = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self.bundle(Path(tmp))
            hub = MemoryHub()
            hub.identity_callback = lambda: path.write_bytes(b'changed during auth')
            with self.assertRaisesRegex(ValueError, 'ARCHIVE_HASH'):
                h.backup(path, digest, REPO, COMMIT, hub)
            self.assertEqual(len(hub.snapshots), 1)

    def test_sdk_missing_file_size_is_rejected_before_download(self):
        h = self.module()
        class InvalidMetadataApi:
            def get_paths_info(self, *args, **kwargs):
                return [object()]
            def hf_hub_download(self, *args, **kwargs):
                raise AssertionError('download must not start')
        worker = object.__new__(h.SdkHub)
        worker.api = InvalidMetadataApi()
        observed = None
        try:
            worker.download(REPO, 'folder', '0' * 40, 10)
        except Exception as error:
            observed = error
        self.assertIs(type(observed), ValueError)
        self.assertEqual(str(observed), 'DOWNLOAD_LIMIT')


if __name__ == '__main__':
    unittest.main()
