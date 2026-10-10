import importlib.util
import unittest
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestSignalPolicy(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(importlib.util.find_spec('openpilot.tools.cyber_autotune.empirical_signal_policy'), 'provenance policy missing')
    from openpilot.tools.cyber_autotune import empirical_signal_policy as q
    self.q = q

  def test_exact_four_hypotheses(self):
    self.assertEqual(self.q.policy()['hypotheses'], ['YAW_H1', 'YAW_H2', 'YAW_H3', 'YAW_H4'])

  def test_no_posthoc_continuous_scale_or_bias_fit(self):
    x = self.q.policy()
    self.assertFalse(x['continuous_scale_fit'])
    self.assertEqual(x['gyro_bias'], 'NO_CORRECTION_REPORT_BIAS')

  def test_axis_sign_lag_grid(self):
    self.assertEqual(len(self.q.policy()['gyro_candidates']), 36)
    self.assertEqual(self.q.policy()['lag_samples'], [0, 1, 2, 5, 10, 20])

  def test_historical_preservation(self):
    self.assertEqual(self.q.policy()['stage_a'], 'EMPIRICAL_ACTUATOR_MODEL_ONLY_STRICT_GATE_FAILED')
    self.assertFalse(self.q.policy()['stage_c_allowed'])

  def test_no_frame_promotion(self):
    self.assertEqual(self.q.yaw_verdict(True, True, True), 'YAW_UNIT_SUPPORTED_FRAME_PARTIAL')
    self.assertEqual(self.q.yaw_verdict(True, False, True), 'YAW_UNIT_LIKELY_NOT_CONFIRMED')

  def test_missing_gyro_unusable(self):
    self.assertEqual(self.q.yaw_verdict(False, False, False), 'YAW_SIGNAL_UNUSABLE')

  def test_discrete_conversion(self):
    import math
    self.assertEqual(self.q.convert_yaw(180., 'YAW_H1'), math.pi)
    self.assertEqual(self.q.convert_yaw(180., 'YAW_H2'), -math.pi)
    self.assertEqual(self.q.convert_yaw(2., 'YAW_H3'), 2.)
    self.assertEqual(self.q.convert_yaw(2., 'YAW_H4'), -2.)

  def test_no_new_hypothesis(self):
    with self.assertRaises(ValueError):
      self.q.convert_yaw(1., 'fit scale')

  def test_relabel_split(self):
    rows=[{'segment_id': str(i), 'role': role} for i,role in enumerate(['TRAIN','DEVELOPMENT','HOLDOUT','EMBARGO'])]
    result=self.q.split_roles(rows)
    self.assertEqual([x['role'] for x in result], ['TRAIN','DEVELOPMENT','COMMAND_BRIDGE_ONLY','YAW_HOLDOUT'])
    self.assertEqual([x['original_role'] for x in result], ['TRAIN','DEVELOPMENT','HOLDOUT','EMBARGO'])

  def test_unknown_role_rejected(self):
    with self.assertRaises(ValueError):
      self.q.split_roles([{'segment_id':'x','role':'TEST'}])

  def test_yaw_fit_conditional(self):
    for key in ['unit_supported','frozen_selection','source_complete','split_disjoint','train_dev_support','untouched_role']:
      gates=dict.fromkeys(['unit_supported','frozen_selection','source_complete','split_disjoint','train_dev_support','untouched_role'], True)
      gates[key]=False
      self.assertFalse(self.q.yaw_fit_allowed(gates))

  def test_unknown_gate_rejected(self):
    with self.assertRaises(ValueError):
      self.q.yaw_fit_allowed({'modelV2':True})

  def test_blockers_and_authority(self):
    x=self.q.policy()
    self.assertEqual(x['calibration_blockers'], p.BLOCKERS)
    self.assertTrue(all(x[k] is False for k in p.FIREWALL))
