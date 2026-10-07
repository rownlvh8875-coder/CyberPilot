"""Descriptive decomposition with explicit time/sign boundaries, no lane truth."""
import copy
import unittest

from openpilot.tools.cyber_autotune.curvature_yaw_screening import build_screening_case, run_screening_case
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


class TestCurvatureYawAttribution(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    from openpilot.tools.cyber_autotune.curvature_yaw_attribution import attribute_report
    case = build_screening_case('gentle_low_left')
    cls.report = run_screening_case(case,expected_manifest_sha256=digest(canonical(case['manifest'])),timeout_s=10.)
    cls.result = attribute_report(cls.report)

  def test_speed_boundaries_and_sign_are_explicit(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_attribution import speed_bucket
    self.assertEqual([speed_bucket(v) for v in (3.,9.999,10.,19.999,20.,27.)],
                     ['LOW','LOW','MID','MID','HIGH','HIGH'])
    for v in (True,float('nan'),2.99,27.01):
      with self.assertRaises(ValueError):
        speed_bucket(v)

  def test_baseline_current_alias_and_no_lane_metric(self):
    self.assertEqual(self.result['arms'][0]['groups'],self.result['arms'][1]['groups'])
    self.assertEqual(self.result['reference_status'],'NO INDEPENDENT LANE TRUTH')
    self.assertFalse(self.result['performance_qualified'])
    self.assertNotIn('lane_center_rmse_m',self.result['arms'][2])
    self.assertTrue(any(g['phase']=='apex' for g in self.result['arms'][2]['groups']))

  def test_desired_angle_is_model_derived_pre_step_not_vehicle_truth(self):
    row = self.result['arms'][0]['rows'][120]
    self.assertLess(row['desired_steering_angle_deg'],0.)
    self.assertEqual(row['desired_curvature_1pm'],.00015)
    self.assertEqual(row['speed_bucket'],'LOW')
    self.assertEqual(row['command_derivative_per_s'],
                     (row['requested_torque']-self.result['arms'][0]['rows'][119]['requested_torque'])/.01)
    self.assertEqual(row['torque_derivative_per_s'],
                     (row['applied_normalized_torque']-self.result['arms'][0]['rows'][119]['applied_normalized_torque'])/.01)

  def test_phase_residual_uses_native_reference_history_and_pre_step_measurement(self):
    rows=self.result['arms'][0]['rows']
    self.assertAlmostEqual(rows[120]['native_aligned_desired_curvature_1pm'], rows[105]['desired_curvature_1pm'],places=16)
    self.assertAlmostEqual(rows[120]['native_aligned_residual_1pm'],
                     rows[119]['curvature_1pm']-rows[105]['desired_curvature_1pm'])

  def test_lag_requires_excitation_and_never_creates_physical_queue(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_attribution import estimate_lag
    self.assertEqual(estimate_lag([1.]*40,[1.]*40)['status'],'INSUFFICIENT_EXCITATION')
    desired=[0.,1.,2.,3.,4.,3.,2.,1.,0.]*5
    actual=[0.,0.]+desired[:-2]
    result=estimate_lag(desired,actual)
    self.assertEqual(result['lag_steps'],2)
    self.assertEqual(result['status'],'DESCRIPTIVE_LAG')
    self.assertFalse(result['physical_delay_estimate'])

  def test_tamper_never_receives_attribution(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_attribution import attribute_report
    report=copy.deepcopy(self.report)
    report['arms'][2]['samples'][80]['curvature_1pm']+=.01
    with self.assertRaises(ValueError):
      attribute_report(report)


if __name__=='__main__':
  unittest.main()
