import tempfile
import unittest
from pathlib import Path
from openpilot.tools.cyber_autotune import empirical_v2_execution as e
from openpilot.tools.cyber_autotune import empirical_v2_policy as v
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_publication as old
from openpilot.tools.cyber_autotune.tests.test_empirical_v2_policy import make_split


class TestV2Execution(unittest.TestCase):
  def test_permission_before_any_file_access(self):
    with tempfile.TemporaryDirectory() as directory:
      with self.assertRaises((ValueError,FileNotFoundError)):
        e.authorized_segment(directory,'0'*64,{'source_sha256':'1'*64},'2'*64)

  def test_source_manifest_dedup(self):
    rows=[{'ordinal':1,'kind':'qlog.zst','source_sha256':'b'}, {'ordinal':1,'kind':'rlog.zst','source_sha256':'a'}]
    chosen=e.choose_sources(rows)
    self.assertEqual([x['source_sha256'] for x in chosen],['a'])

  def test_unknown_ordinal_rejected(self):
    with self.assertRaises(ValueError):
      e.choose_sources([{'ordinal':None,'kind':'rlog.zst','source_sha256':'a'}])

  def test_conflicting_rlog_ordinal_rejected(self):
    with self.assertRaises(ValueError):
      e.choose_sources([{'ordinal':1,'kind':'rlog.zst','source_sha256':'a'}, {'ordinal':1,'kind':'rlog.zst','source_sha256':'b'}])

  def test_authorization_covers_only_exact_route_sources(self):
    frozen=make_split(old.load())
    with self.assertRaises(ValueError):
      v.authorization(frozen, {'0'*64:[]})

  def test_immutable_split_store(self):
    with tempfile.TemporaryDirectory() as directory:
      f=make_split(old.load())
      path=Path(directory)/'split.json'
      p.persist(path,f)
      p.persist(path,f)
      with self.assertRaises(ValueError):
        p.persist(path,p.seal({'schema':'other'}))

  def test_in_repo_store_rejected(self):
    with self.assertRaises(ValueError):
      e.private_store(Path.cwd()/'private-test-store')
