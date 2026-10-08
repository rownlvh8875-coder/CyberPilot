import unittest
from openpilot.tools.cyber_autotune import private_pixel_analysis as a


class TestPrivateAnalysis(unittest.TestCase):
  def test_projection_is_hypothetical_nonqualification(self):
    policy = a.projection_policy()
    self.assertEqual(policy['heights_m'], [1.33, 1.35, 1.375, 1.4, 1.425, 1.45, 1.47])
    self.assertFalse(policy['actual_sensor_identified'])
    self.assertEqual(policy['distortion'], 'UNKNOWN_NOT_ASSUMED_ZERO')

  def test_height_linear_envelope(self):
    result = a.projection_sensitivity([{'image_geometry': [330, 526], 'points': [[263., 270.]], 'lane_count': 1,
                                       'lanes': [{'confidence': .9, 'points': [[263., 270.]]}]}], a.projection_policy())
    for hypothesis in result['hypotheses']:
      self.assertFalse(hypothesis['qualification_allowed'])
      self.assertEqual(hypothesis['forward_height_ratio_min'], .95)
      self.assertEqual(hypothesis['forward_height_ratio_max'], 1.05)

  def test_changed_projection_policy_rejected(self):
    policy = a.projection_policy()
    policy['heights_m'] = [1.42]
    with self.assertRaises(ValueError):
      a.projection_sensitivity([], policy)

  def test_public_private_common_metric_only(self):
    result = a.comparable_behavior([{'image_geometry':[100,100], 'points':[[50.,80.]], 'lane_count':1,
                                    'lanes':[{'confidence':.8,'points':[[50.,80.]]}]}])
    self.assertEqual(result['per_frame_normalized_centroid_x']['median'], .5)
    self.assertNotIn('localization_error', result)
    self.assertNotIn('recall', result)

  def test_empty_predictions_explicit(self):
    result = a.comparable_behavior([{'image_geometry':[100,100], 'points':[], 'lane_count':0,'lanes':[]}])
    self.assertEqual(result['no_output_rate'], 1)
    self.assertIsNone(result['per_lane_confidence']['median'])
