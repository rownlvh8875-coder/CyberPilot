import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.cyberpilot_web_native.isolation import namespace, validate_namespace
from tools.cyberpilot_web_native.prepare import check_gitlinks, check_output_path

ROOT = Path(__file__).resolve().parents[3]


class BoundaryTests(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)

  def test_private_namespace_and_restore(self):
    with patch.dict(os.environ, {}, clear=True):
      with namespace(self.root) as run:
        self.assertEqual(run.path.stat().st_mode & 0o777, 0o700)
        self.assertEqual(os.environ['OPENPILOT_PREFIX'], run.prefix)
        validate_namespace(run)
        self.assertTrue(run.path.is_dir())
      self.assertNotIn('OPENPILOT_PREFIX', os.environ)
      self.assertFalse(run.path.exists())

  def test_existing_process_namespace_refused(self):
    for env in ({'OPENPILOT_PREFIX': 'actual'}, {'CEREAL_FAKE': ''}):
      with patch.dict(os.environ, env, clear=True), self.assertRaises(ValueError):
        with namespace(self.root):
          self.fail('unsafe namespace accepted')
      self.assertEqual(list(self.root.iterdir()), [])

  def test_public_namespace_refused(self):
    with patch.dict(os.environ, {}, clear=True), namespace(self.root) as run:
      run.path.chmod(0o755)
      with self.assertRaises(ValueError):
        validate_namespace(run)
      run.path.chmod(0o700)

  def test_symlink_endpoint_refused_and_unrelated_file_preserved(self):
    outside = self.root / 'unrelated'
    outside.write_text('preserve')
    with patch.dict(os.environ, {}, clear=True), namespace(self.root) as run:
      endpoint = run.path / 'carState'
      endpoint.symlink_to(outside)
      with self.assertRaises(ValueError):
        validate_namespace(run)
      endpoint.unlink()
    self.assertEqual(outside.read_text(), 'preserve')

  def test_environment_change_refused(self):
    with patch.dict(os.environ, {}, clear=True), namespace(self.root) as run:
      os.environ['OPENPILOT_PREFIX'] = 'different'
      with self.assertRaises(ValueError):
        validate_namespace(run)
      os.environ['OPENPILOT_PREFIX'] = run.prefix

  def test_owned_endpoint_cleanup_only(self):
    unrelated = self.root / 'msgq_do_not_touch'
    unrelated.mkdir()
    keep = unrelated / 'carState'
    keep.write_text('unrelated IPC')
    with patch.dict(os.environ, {}, clear=True), namespace(self.root) as run:
      (run.path / 'carState').write_bytes(b'synthetic')
    self.assertFalse(run.path.exists())
    self.assertEqual(keep.read_text(), 'unrelated IPC')

  def test_wrong_or_missing_gitlinks_rejected(self):
    with self.assertRaises(ValueError):
      check_gitlinks(self.root)

  def test_real_gitlinks_match_profile(self):
    self.assertEqual(set(check_gitlinks(ROOT)), {'msgq', 'opendbc'})

  def test_output_cannot_be_used_or_inside_checkout(self):
    for path in (self.root, ROOT / 'native-output-test'):
      with self.assertRaises(ValueError):
        check_output_path(ROOT, path)
    allowed = self.root / 'new-output'
    self.assertEqual(check_output_path(ROOT, allowed), allowed)
    self.assertFalse(allowed.exists())
