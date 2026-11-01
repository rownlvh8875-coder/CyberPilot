"""Guard integration orchestration without recursively invoking full verification."""

import contextlib
import hashlib
import importlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT


class DevCommandTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/verify.py').is_file(), 'Missing verification helpers')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.verify')

    def test_existing_entries_rejected_without_mutation(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            targets = [root / 'file', root / 'dir', root / 'dead']
            targets[0].write_bytes(b'KEEP')
            targets[1].mkdir()
            targets[2].symlink_to(root / 'absent', target_is_directory=True)
            for target in targets:
                with self.assertRaises(FileExistsError):
                    m.verify_new_output(target)
            self.assertEqual(targets[0].read_bytes(), b'KEEP')
            self.assertTrue(targets[2].is_symlink())

    def test_cli_guard_precedes_verification_or_environment_work(self):
        self.module()
        self.assertTrue((ROOT / 'dev.py').is_file(), 'Missing one-command CLI')
        dev = importlib.import_module('dev')
        with tempfile.TemporaryDirectory() as scratch:
            error = io.StringIO()
            with contextlib.redirect_stderr(error), patch.object(dev, 'verify_project', side_effect=AssertionError('WORK_MUST_NOT_RUN')):
                self.assertEqual(dev.main(['verify', '--output', scratch]), 2)
            self.assertIn('OUTPUT_EXISTS', error.getvalue())

    def test_import_hash_tamper_and_path_escape_reject(self):
        m = self.module()
        original = json.loads((ROOT / 'IMPORTED_ARTIFACT.json').read_bytes())
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            p = root / 'sample.txt'
            p.write_bytes(b'exact')
            record = dict(original, imported_files={'sample.txt': hashlib.sha256(b'exact').hexdigest()})
            (root / 'IMPORTED_ARTIFACT.json').write_text(json.dumps(record))
            self.assertEqual(m.verify_imports(root)['files'], 1)
            p.write_bytes(b'wrong')
            with self.assertRaises(ValueError):
                m.verify_imports(root)
            record['imported_files'] = {'../outside': hashlib.sha256(b'exact').hexdigest()}
            (root / 'IMPORTED_ARTIFACT.json').write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                m.verify_imports(root)

    def test_actual_two_process_wheels_match_sealed_artifact(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            result = m.build_wheels(ROOT, Path(scratch) / 'wheels')
            self.assertTrue(result['byte_identical'])
            self.assertEqual(result['sha256'], '3f3db36f62aa79ba97e4536a183b7e685a9d06c4e264d1fec9dd3bbda7c4d73c')
            self.assertEqual(result['record_entries'], 27)

    def test_missing_dependency_rejects_before_output_creation(self):
        m = self.module()
        dev = importlib.import_module('dev')
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / 'out'
            with (
                patch.object(m.importlib.metadata, 'version', side_effect=m.importlib.metadata.PackageNotFoundError('numpy')),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                try:
                    result = dev.main(['verify', '--output', str(output)])
                except m.importlib.metadata.PackageNotFoundError:
                    result = -1
                self.assertEqual(result, 2, 'Missing dependency escaped the rejection boundary')
            self.assertFalse(output.exists())

    def test_missing_or_truncated_test_ledger_cannot_report_success(self):
        m = self.module()
        self.assertTrue(hasattr(m, 'test_count'), 'Missing suite-ledger validation')
        for text in ['', 'Ran 0 tests in 0s\nOK', 'Ran 1 tests in 0s\nOK']:
            with self.assertRaises(ValueError):
                m.test_count(text)
        self.assertEqual(m.test_count('Ran 137 tests in 20s\n\nOK\n'), 137)


if __name__ == '__main__':
    unittest.main()
