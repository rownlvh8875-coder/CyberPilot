import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_store as s
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestFitCVStore(unittest.TestCase):
  def test_historical_derived_digest_is_ordered_receipt_list(self):
    index={'segments':[{'content_sha256':'a'*64,'receipt_sha256':'b'*64},
                       {'content_sha256':'c'*64,'receipt_sha256':'d'*64}]}
    self.assertEqual(s.derived_receipt_set(index),p.sha(p.canonical(['b'*64,'d'*64])))
    self.assertNotEqual(s.derived_receipt_set(index),s.derived_receipt_set({'segments':index['segments'][::-1]}))

  def test_frozen_public_bundle(self):
    bundle=s.contracts()
    self.assertEqual(bundle['empirical-s2-ri-fitting-policy-v1.json']['receipt_sha256'],s.POLICY_SHA)

  def test_atomic_exact_resume_and_conflict(self):
    with tempfile.TemporaryDirectory() as root:
      path=Path(root)/'receipt.json'
      value=p.seal({'schema':'SYNTHETIC'})
      s.write_json(path,value)
      s.write_json(path,value)
      with self.assertRaises(ValueError):
        s.write_json(path,p.seal({'schema':'CONFLICT'}))

  def test_symlink_and_traversal(self):
    with tempfile.TemporaryDirectory() as root:
      path=Path(root)
      (path/'target').write_text('do not overwrite')
      (path/'link').symlink_to(path/'target')
      for destination in (path/'link',path/'../bad'):
        with self.assertRaises(ValueError):
          s.write_json(destination,{})

  def test_atomic_symlink(self):
    with tempfile.TemporaryDirectory() as root:
      path=Path(root)/'a.json'
      path.with_name('a.json.atomic').symlink_to(Path(root)/'elsewhere')
      with self.assertRaises(ValueError):
        s.write_json(path,{})

  def test_verify_resume_never_array_loads(self):
    with tempfile.TemporaryDirectory() as root:
      path=Path(root)
      s.write_json(path/'item.json',p.seal({'schema':'SYNTHETIC'}))
      manifest=s.finish(path,['item.json'],{'schema':'TEST'})
      with patch('numpy.load',side_effect=AssertionError('ARRAY_OPEN_FORBIDDEN')):
        self.assertEqual(s.verify_manifest(path),manifest)
      (path/'item.json').write_text('changed')
      with self.assertRaises(ValueError):
        s.verify_manifest(path)
