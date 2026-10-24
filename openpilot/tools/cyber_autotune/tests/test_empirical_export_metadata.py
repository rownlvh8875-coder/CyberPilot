from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class TestExportMetadata(unittest.TestCase):
  def test_export_lineage_uses_filename_segment(self):
    from openpilot.tools.cyber_autotune import empirical_export_metadata as e

    a = e.export_lineage('exports/opaque--4--rlog.zst')
    b = e.export_lineage('exports/opaque--5--rlog.zst')
    self.assertEqual(a['lineage_sha256'], b['lineage_sha256'])
    self.assertEqual(a['ordinal'], 4)
    self.assertEqual(b['ordinal'], 5)

  def test_unstructured_export_has_unknown_ordinal(self):
    from openpilot.tools.cyber_autotune import empirical_export_metadata as e

    self.assertIsNone(e.export_lineage('exports/unknown-rlog.zst')['ordinal'])

  def test_export_discovery_is_metadata_only_and_excludes_canonical_media_archives(self):
    from openpilot.tools.cyber_autotune import empirical_export_metadata as e

    with tempfile.TemporaryDirectory() as d:
      root = Path(d)
      for name in ('x--4--rlog.zst', 'strange-rlog.zst', 'rlog.zst', 'qcamera.ts', 'rlog.zip'):
        (root / name).write_bytes(b'x')
      with patch.object(e.policy, 'approved_root', return_value=root), patch.object(Path, 'open', side_effect=AssertionError('BODY_FORBIDDEN')):
        rows = e.discover(root)
      self.assertEqual(len(rows), 2)
      self.assertEqual({x['ordinal'] for x in rows}, {4, None})

  def test_export_guard_rejects_nonlog_and_canonical(self):
    from openpilot.tools.cyber_autotune import empirical_export_metadata as e

    for name in ('rlog.zst', 'x.mp4', 'private.zip', 'gps.json', 'qlog.zst'):
      self.assertFalse(e.is_export(name))

  def test_extension_cannot_reuse_stale_parent(self):
    from openpilot.tools.cyber_autotune import empirical_export_metadata as e
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    with self.assertRaisesRegex(ValueError, 'PARENT'):
      e.validate_parent(p.seal({'schema': 'wrong'}), {})

  def test_extension_refuses_numeric_parent(self):
    from openpilot.tools.cyber_autotune import empirical_export_metadata as e
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    parent = p.seal({'schema': 'EMPIRICAL_CROSS_ROOT_PRIVATE_INVENTORY_V1', 'binding_sha256': 'a' * 64, 'numeric_payloads_opened': True})
    with self.assertRaisesRegex(ValueError, 'PARENT'):
      e.validate_parent(parent, {'receipt_sha256': 'a' * 64})

  def test_export_binding_rejects_stale_reader_policy_or_contract(self):
    from openpilot.tools.cyber_autotune import empirical_export_metadata as e
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    parent = {'reader_sha256': 'a' * 64, 'root_policy_sha256': 'b' * 64, 'source_contract_sha256': 'c' * 64}
    for field in parent:
      candidate = {**parent, 'extension_source_sha256': e.source_identity(), field: 'd' * 64}
      with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'BINDING'):
        e.validate_extension_binding(p.seal(candidate), parent)

  def test_export_content_drift_rejected_even_when_metadata_unchanged(self):
    from openpilot.tools.cyber_autotune import empirical_export_metadata as e

    with tempfile.TemporaryDirectory() as d:
      root = Path(d)
      source = root / 'x-rlog.zst'
      source.write_bytes(b'original')
      row = {'root_id': 'a' * 64, 'source_key': source.name, 'source_sha256': e.reader.file_sha(source)}
      source.write_bytes(b'different')
      with patch.object(e.policy, 'root_key', return_value='a' * 64), self.assertRaisesRegex(ValueError, 'CONTENT'):
        e.validate_export_sources([root], [row])

  def test_cached_export_parent_traversal_rejected_before_hash(self):
    from openpilot.tools.cyber_autotune import empirical_export_metadata as e

    with tempfile.TemporaryDirectory() as d:
      for key in ('../outside-rlog.zst', '/outside-rlog.zst', 'nested/../../outside-rlog.zst'):
        row = {'root_id': 'a' * 64, 'source_key': key, 'source_sha256': 'b' * 64}
        with (
          self.subTest(key=key),
          patch.object(e.policy, 'root_key', return_value='a' * 64),
          patch.object(e.reader, 'file_sha', side_effect=AssertionError('OUTSIDE_FILE_OPENED')),
        ):
          with self.assertRaisesRegex(ValueError, 'OUTSIDE_ROOT'):
            e.validate_export_sources([Path(d)], [row])
