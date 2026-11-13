import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpilot.system.cyberpilot_web.cli import main, source_identity


class CliTests(unittest.TestCase):
  def test_init_does_not_print_token(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "token"
      output = io.StringIO()
      with contextlib.redirect_stdout(output):
        self.assertEqual(main(["init", "--token-file", str(path)]), 0)
      self.assertNotIn(path.read_text().strip(), output.getvalue())

  def test_help_does_not_import_cereal(self):
    import sys
    before = set(sys.modules)
    with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as result:
      main(["--help"])
    self.assertEqual(result.exception.code, 0)
    self.assertFalse(any(name.startswith("openpilot.cereal") for name in set(sys.modules) - before))

  def test_source_identity_is_read_only(self):
    identity = source_identity()
    self.assertEqual(len(identity["commit"]), 40)
    self.assertIsInstance(identity["branch"], str)

  def test_serve_requires_existing_credentials(self):
    with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stderr(io.StringIO()):
      with patch("openpilot.system.cyberpilot_web.cli.run") as run:
        self.assertEqual(main(["serve", "--token-file", str(Path(directory) / "absent")]), 2)
        run.assert_not_called()
