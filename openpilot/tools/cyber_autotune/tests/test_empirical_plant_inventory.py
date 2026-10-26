import importlib.util
import unittest


class TestInventory(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(importlib.util.find_spec('openpilot.tools.cyber_autotune.empirical_plant_inventory'))
    from openpilot.tools.cyber_autotune import empirical_plant_inventory as inv, empirical_plant_policy as p

    self.inv, self.p = inv, p

  def test_metadata_receipt(self):
    segment = {'segment_id': 'a' * 64, 'source_sha256': 'b' * 64, 'role': 'HOLDOUT'}
    receipt = self.inv.metadata_receipt(segment, 'c' * 64, {'init': [], 'profiles': [], 'rates': {}, 'message_counts': {}})
    self.p.verify(receipt)
    self.assertEqual(receipt['role'], 'HOLDOUT')
    self.assertEqual(receipt['schema'], 'EMPIRICAL_SEGMENT_METADATA_V1')

  def test_integrity_failure_no_prefix(self):
    segment = {'segment_id': 'a' * 64, 'source_sha256': 'b' * 64, 'role': 'EMBARGO'}
    r = self.inv.failure_receipt(segment, 'c' * 64, 'KjException')
    self.assertFalse(r['parsed_prefix_used'])
    self.assertEqual(r['status'], 'REJECTED_LOG_INTEGRITY')

  def test_unknown_failure_rejected(self):
    self.assertRaises(ValueError, self.inv.failure_receipt, {'segment_id': 'a', 'source_sha256': 'b', 'role': 'TRAIN'}, 'c', 'AssertionError')

  def test_video_failure_not_reclassified(self):
    self.assertRaises(ValueError, self.inv.failure_receipt, {'segment_id': 'a', 'source_sha256': 'b', 'role': 'TRAIN'}, 'c', 'PermissionError')

  def test_store_cannot_be_inside_input(self):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as temp:
      root = Path(temp) / 'input'
      root.mkdir()
      self.assertRaises(ValueError, self.inv.bootstrap, root, root / 'private', 'unused')

  def test_existing_cache_symlink_rejected(self):
    import tempfile
    from pathlib import Path
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as temp:
      root = Path(temp) / 'input'
      folder = root / 'opaque--0'
      folder.mkdir(parents=True)
      (folder / 'rlog.zst').write_bytes(b'synthetic')
      store = Path(temp) / 'private'
      source = self.p.seal({'schema': 'TEST_SOURCE'})
      with (
        patch.object(self.inv.s, 'source_contract', return_value=source),
        patch.object(self.inv.s, 'schema', return_value=object()),
        patch.object(self.inv.s, 'events', return_value=iter([])),
      ):
        self.inv.bootstrap(root, store, 'unused')
        cache = next((store / 'metadata').glob('*.json'))
        outside = Path(temp) / 'outside.json'
        outside.write_bytes(cache.read_bytes())
        cache.unlink()
        cache.symlink_to(outside)
        self.assertRaises(ValueError, self.inv.bootstrap, root, store, 'unused')
