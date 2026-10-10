import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from openpilot.tools.cyber_autotune import empirical_source_execution as e, empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_additional_root_policy as roots


class TestSourceExecution(unittest.TestCase):
  def test_corrupt_persistent_receipt(self):
    with tempfile.TemporaryDirectory() as tmp:
      path = Path(tmp)/'bad.json'
      path.write_text('{"receipt_sha256":"wrong"}')
      with self.assertRaises(ValueError):
        e.read(path)

  def test_store_no_overwrite(self):
    with tempfile.TemporaryDirectory() as tmp:
      path = Path(tmp)/'receipt.json'
      p.persist(path, p.seal({'identity': 'a'}))
      with self.assertRaises(ValueError):
        p.persist(path, p.seal({'identity': 'b'}))

  def test_restart_exact_receipt(self):
    with tempfile.TemporaryDirectory() as tmp:
      path = Path(tmp)/'receipt.json'
      row = p.seal({'identity': 'a'})
      p.persist(path, row)
      p.persist(path, row)
      self.assertEqual(e.read(path), row)

  def test_file_map_wrong_inventory(self):
    with self.assertRaisesRegex(ValueError, 'IMMUTABLE_INVENTORY'):
      e.map_selected_files(p.seal({}), [], [], '/unused')

  def test_source_path_escape(self):
    key = next(iter(roots.ROOTS))
    with self.assertRaisesRegex(ValueError, 'PATH_ESCAPE'):
      e.source_location({'root_id': key, 'source_key': '../escape', 'path': '/escape'}, {key: Path('/safe')})

  def test_source_path_root_allowlist(self):
    with self.assertRaisesRegex(ValueError, 'ROOT_NOT'):
      e.source_location({'root_id': '0'*64}, {})

  def test_source_path_mismatch(self):
    key = next(iter(roots.ROOTS))
    with patch('openpilot.tools.cyber_autotune.empirical_dataset_v2_policy.no_alias', side_effect=lambda x: x):
      with self.assertRaisesRegex(ValueError, 'FILE_MAP_PATH_MISMATCH'):
        e.source_location({'root_id': key, 'source_key': 'rlog.zst', 'path': '/elsewhere'}, {key: Path('/safe')})

  def test_source_path_exact(self):
    key = next(iter(roots.ROOTS))
    with patch('openpilot.tools.cyber_autotune.empirical_dataset_v2_policy.no_alias', side_effect=lambda x: x):
      self.assertEqual(e.source_location({'root_id': key, 'source_key': 'rlog.zst', 'path': '/safe/rlog.zst'},
                                         {key: Path('/safe')}), Path('/safe/rlog.zst'))

  def test_materialized_schema_hash_checked(self):
    source = {'commit': 'a'*40, 'files': {'schema_car': {'path': 'c/car.capnp', 'file_sha256': '0'*64}}}
    with tempfile.TemporaryDirectory() as tmp, patch.object(e.subprocess, 'check_output', return_value=b'wrong'):
      with self.assertRaisesRegex(ValueError, 'SOURCE_SCHEMA_DRIFT'):
        e.materialize_schemas('/source', source, tmp)

  def test_materialized_schema_no_overwrite(self):
    source = {'commit': 'a'*40, 'files': {'schema_car': {'path': 'c/car.capnp', 'file_sha256': p.sha(b'valid')}}}
    with tempfile.TemporaryDirectory() as tmp, patch.object(e.subprocess, 'check_output', return_value=b'valid'):
      directory = e.materialize_schemas('/source', source, tmp)
      (directory/'c/car.capnp').write_bytes(b'old')
      with self.assertRaisesRegex(ValueError, 'IMMUTABLE_SCHEMA'):
        e.materialize_schemas('/source', source, tmp)

  def test_no_private_root_literals(self):
    self.assertNotIn('/mnt/', Path(e.__file__).read_text())

  def test_revalidation_requires_explicit_roots(self):
    with self.assertRaisesRegex(ValueError, 'EXPLICIT_APPROVED_ROOTS_REQUIRED'):
      e.revalidate_commit('/unused', '/unused', '/unused', 'a'*40)

  def test_root_map_rejects_one_root(self):
    key = next(iter(roots.ROOTS))
    with patch.object(roots, 'approved_root', return_value=Path('/synthetic')), patch.object(roots, 'root_key', return_value=key):
      with self.assertRaisesRegex(ValueError, 'EXACT_TWO_APPROVED_ROOTS'):
        e.approved_root_map(['/synthetic'])
