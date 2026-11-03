"""Campaign evidence cannot qualify missing, unbounded or linked saved bytes."""

import hashlib
import importlib
import os
import tempfile
import unittest
from pathlib import Path

from v1_helpers import ROOT


def manifest(files):
    return ''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n'
                   for name, raw in sorted(files.items())).encode()


class CampaignEvidenceTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_campaign_evidence.py').is_file(), 'Missing campaign evidence boundary')
        import sys
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_campaign_evidence')

    def fixture(self, root):
        (root / 'nested').mkdir()
        files = {'nested/data.json': b'{}\n', 'nested/other.txt': b'owned\n'}
        files['nested/SHA256SUMS.txt'] = manifest({'data.json': b'{}\n', 'other.txt': b'owned\n'})
        files['nested/PORTABLE_SHA256SUMS.txt'] = manifest({'data.json': b'{}\n'})
        files['nested/SHA256SUMS.txt'] = manifest({name.removeprefix('nested/'): raw for name, raw in files.items()
                                                if name != 'nested/SHA256SUMS.txt'})
        files['SHA256SUMS.txt'] = manifest(files)
        for name, raw in files.items():
            (root / name).write_bytes(raw)
        return files

    def test_real_nested_closed_and_portable_subset_manifests(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = self.fixture(root)
            captured = m.capture_tree(root)
            self.assertEqual(captured, {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()})
            self.assertIsNone(m.verify_manifests(root, captured))

    def test_changed_missing_and_extra_payloads_fail_closure(self):
        m = self.module()
        for operation in ['changed', 'missing', 'extra']:
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.fixture(root)
                if operation == 'changed':
                    (root / 'nested/data.json').write_bytes(b'changed')
                elif operation == 'missing':
                    (root / 'nested/data.json').unlink()
                else:
                    (root / 'extra').write_bytes(b'extra')
                with self.assertRaisesRegex(m.CampaignError, 'CAMPAIGN_CHILD_EVIDENCE'):
                    m.verify_manifests(root, m.capture_tree(root))

    def test_rehashed_root_does_not_hide_broken_nested_manifest(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = self.fixture(root)
            files['nested/data.json'] = b'changed'
            (root / 'nested/data.json').write_bytes(b'changed')
            (root / 'SHA256SUMS.txt').write_bytes(manifest({n: raw for n, raw in files.items() if n != 'SHA256SUMS.txt'}))
            with self.assertRaisesRegex(m.CampaignError, 'CAMPAIGN_CHILD_EVIDENCE'):
                m.verify_manifests(root, m.capture_tree(root))

    def test_file_directory_root_symlinks_and_fifo_are_rejected(self):
        m = self.module()
        for kind in ['file', 'directory', 'root', 'fifo']:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                parent = Path(tmp)
                root = parent / 'owned'
                root.mkdir()
                outside = parent / 'outside'
                outside.mkdir()
                (outside / 'data').write_bytes(b'not owned')
                if kind == 'fifo':
                    os.mkfifo(root / 'pipe')
                elif kind == 'root':
                    (parent / 'link').symlink_to(root, target_is_directory=True)
                    root = parent / 'link'
                else:
                    (root / 'link').symlink_to(outside if kind == 'directory' else outside / 'data',
                                              target_is_directory=kind == 'directory')
                with self.assertRaisesRegex(m.CampaignError, 'CAMPAIGN_CHILD_EVIDENCE'):
                    m.capture_tree(root)

    def test_file_count_total_size_and_per_file_caps(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'one').write_bytes(b'123')
            (root / 'two').write_bytes(b'456')
            for kwargs in [{'max_files': 1}, {'max_bytes': 5}]:
                with self.subTest(kwargs=kwargs), self.assertRaisesRegex(m.CampaignError, 'CAMPAIGN_CHILD_EVIDENCE'):
                    m.capture_tree(root, **kwargs)
            with (root / 'large').open('wb') as stream:
                stream.truncate(16 * 1024 * 1024 + 1)
            with self.assertRaisesRegex(m.CampaignError, 'CAMPAIGN_CHILD_EVIDENCE'):
                m.capture_tree(root)

    def test_unsafe_names_and_excessive_depth_are_rejected(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'new\nline').write_bytes(b'data')
            with self.assertRaises(m.CampaignError):
                m.capture_tree(root)
            (root / 'new\nline').unlink()
            deep = root.joinpath(*(['nested'] * 17))
            deep.mkdir(parents=True)
            (deep / 'data').write_bytes(b'data')
            with self.assertRaises(m.CampaignError):
                m.capture_tree(root)


if __name__ == '__main__':
    unittest.main()
