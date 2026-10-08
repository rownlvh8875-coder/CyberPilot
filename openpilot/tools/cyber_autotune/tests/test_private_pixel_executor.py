import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock

from openpilot.tools.cyber_autotune import private_pixel_executor as e
from openpilot.tools.cyber_autotune import private_pixel_execution as p
from openpilot.tools.cyber_autotune.tests import test_private_pixel_execution as fixture
SHA = fixture.SHA


class TestPrivateExecutor(unittest.TestCase):
  def setUp(self):
    case = fixture.TestPrivateExecution()
    case.setUp()
    self.manifest, self.auth = case.manifest, case.auth

  def test_decode_callback_not_called_without_authorization(self):
    callback = Mock()
    with self.assertRaises(ValueError):
      e.guarded_open(self.manifest, None, self.manifest['selected'][0]['sample_id'], callback)
    callback.assert_not_called()

  def test_decode_callback_not_called_for_holdout(self):
    callback = Mock()
    with self.assertRaises(ValueError):
      e.guarded_open(self.manifest, self.auth, self.manifest['selected'][-1]['sample_id'], callback)
    callback.assert_not_called()

  def test_callback_only_after_authentication(self):
    callback = Mock(return_value='fixture')
    self.assertEqual(e.guarded_open(self.manifest, self.auth, self.manifest['selected'][0]['sample_id'], callback), 'fixture')
    callback.assert_called_once()

  def test_hash_drift(self):
    with tempfile.TemporaryDirectory() as temp:
      path = Path(temp) / 'qcamera.ts'
      path.write_bytes(b'test')
      with self.assertRaises(ValueError):
        with e.verified_video(path, SHA, 4):
          self.fail('stale video admitted')

  def test_video_snapshot_immutable_and_same_bytes(self):
    with tempfile.TemporaryDirectory() as temp:
      path = Path(temp) / 'qcamera.ts'
      path.write_bytes(b'test')
      with e.verified_video(path, p.digest(b'test'), 4) as fdpath:
        self.assertEqual(Path(fdpath).read_bytes(), b'test')
        with self.assertRaises(PermissionError):
          Path(fdpath).write_bytes(b'changed')

  def test_symlink_video_rejected(self):
    with tempfile.TemporaryDirectory() as temp:
      target = Path(temp) / 'video'
      target.write_bytes(b'test')
      path = Path(temp) / 'qcamera.ts'
      path.symlink_to(target)
      with self.assertRaises(ValueError):
        e.verified_video(path, p.digest(b'test'), 4).__enter__()

  def test_sparse_geometry_has_no_temporal_continuity_claim(self):
    self.assertEqual(self.manifest['policy']['temporal'], 'NOT_EVALUATED_UNLESS_CONSECUTIVE_SELECTED_FRAMES')

  def test_holdout_plan_has_no_labels_or_images(self):
    plan = e.holdout_plan(self.manifest)
    self.assertEqual(len(plan['samples']), 3)
    self.assertEqual(plan['labels'], [])
    self.assertEqual(plan['status'], 'PRIVATE_HUMAN_HOLDOUT_PENDING')
    self.assertFalse(plan['image_materialization_allowed_this_run'])

  def test_plan_requires_current_exception_acknowledgment(self):
    with self.assertRaises(ValueError):
      e.plan(Path('/not-opened'), Path('/not-created'), acknowledged=False)

  def test_source_root_and_cache_overlap_rejected(self):
    with tempfile.TemporaryDirectory() as temp, self.assertRaises(ValueError):
      p.private_directories(Path(temp), Path(temp) / 'cache')

  def test_missing_cached_image_rejected_by_hash_reader(self):
    with tempfile.TemporaryDirectory() as temp, self.assertRaises(FileNotFoundError):
      e.hash_file(Path(temp) / 'missing.png')
