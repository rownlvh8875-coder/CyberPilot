import unittest

from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_publication as pub


class TestFitCVPublication(unittest.TestCase):
  def test_public_job_strips_unknown_private_values(self):
    source=dict.fromkeys(pub.JOB_FIELDS,None)
    source.update(coefficients=[12.],mean=[3.],std=[4.],private_path='secret',predictions=[8.])
    result=pub.public_job(source)
    self.assertEqual(set(result),set(pub.JOB_FIELDS))
    self.assertNotIn('coefficients',result)
    self.assertNotIn('private_path',result)

  def test_nested_numerics_cannot_publish_coefficients(self):
    source=dict.fromkeys(pub.JOB_FIELDS,None)
    source['numerics']={'coefficients':[1.,2.]}
    with self.assertRaises(ValueError):
      pub.public_job(source)

  def test_publication_missing_required_job_field_fails(self):
    with self.assertRaises(ValueError):
      pub.public_job({'candidate_id':'S2RI_D00_L01'})

  def test_publication_raw_metric_shape_rejected(self):
    with self.assertRaises(ValueError):
      pub.check_metrics({'candidate':{'rmse':[1,2]},'comparator':{},'count':300})

  def test_repeatability_failure_blocks_publication(self):
    with self.assertRaisesRegex(ValueError,'REPEATABILITY'):
      pub.same_manifests({'receipt_sha256':'a'},{'receipt_sha256':'b'})
