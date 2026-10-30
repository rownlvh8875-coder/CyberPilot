"""Existing filesystem entries must reject BEFORE source reads or numeric work."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_sequences
from test_source_contract import REFERENCE


class OutputGuardTests(unittest.TestCase):
    def test_existing_entries_including_dangling_links_before_source_reads(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            target_dir = root / "target-dir"
            target_dir.mkdir()
            target_file = root / "target-file"
            target_file.write_bytes(b"preserve")
            dir_link, file_link = root / "dir-link", root / "file-link"
            dead_dir, dead_file = root / "dead-dir", root / "dead-file"
            dir_link.symlink_to(target_dir, target_is_directory=True)
            file_link.symlink_to(target_file)
            dead_dir.symlink_to(root / "absent-dir", target_is_directory=True)
            dead_file.symlink_to(root / "absent-file")
            for output in [target_dir, target_file, dir_link, file_link, dead_dir, dead_file]:
                with self.subTest(output=output.name):
                    argv = ["run_sequences", "--controller", str(root / "missing.py"), "--helper", str(root / "missing2.py"), "--output", str(output)]
                    stderr = io.StringIO()
                    with patch.object(sys, "argv", argv), contextlib.redirect_stderr(stderr):
                        code = run_sequences.main()
                    self.assertEqual(code, 2)
                    self.assertIn("OUTPUT_EXISTS_NO_HELPER_EXECUTION", stderr.getvalue())
            self.assertEqual(target_file.read_bytes(), b"preserve")
            self.assertTrue(all(p.is_symlink() for p in [dir_link, file_link, dead_dir, dead_file]))

    def test_dangling_entry_valid_sources_never_reach_numeric_builder(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            output = root / "dead-link"
            output.symlink_to(root / "missing-target", target_is_directory=True)
            argv = ["run_sequences", "--controller", str(REFERENCE / "carcontroller.py"),
                    "--helper", str(REFERENCE / "lateral.py"), "--output", str(output)]
            stderr = io.StringIO()
            with (patch.object(sys, "argv", argv), contextlib.redirect_stderr(stderr),
                  patch.object(run_sequences, "build_results", side_effect=AssertionError("NUMERIC_WORK_REACHED"))):
                try:
                    code = run_sequences.main()
                except AssertionError:
                    self.fail("Existing dangling entry reached numeric work before rejection")
            self.assertEqual(code, 2)
            self.assertIn("OUTPUT_EXISTS_NO_HELPER_EXECUTION", stderr.getvalue())
            self.assertTrue(output.is_symlink())
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
