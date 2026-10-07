"""Frozen synthetic catalog, equivalent-arm contract and descriptive measurement."""
import copy
import unittest

from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from unittest.mock import patch


class TestCurvatureYawScreening(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    from openpilot.tools.cyber_autotune.curvature_yaw_screening import build_screening_case, run_screening_case
    cls.case = build_screening_case('gentle_low_left')
    cls.report = run_screening_case(cls.case, expected_manifest_sha256=digest(canonical(cls.case['manifest'])), timeout_s=10.)

  def test_alias_and_candidate_are_real_repeatable_public_replayed_outputs(self):
    result = self.report
    self.assertEqual(result['status'], 'STRUCTURAL_SYNTHETIC_SCREENING')
    self.assertEqual(result['executed_runs'], 6)
    self.assertTrue(result['exact_repeatability'])
    self.assertTrue(result['baseline_current_exact_alias'])
    self.assertGreater(result['candidate_difference']['changed_command_frames'], 0)
    self.assertGreater(result['candidate_difference']['max_abs_pose_difference_m'], 0.)
    self.assertEqual(result['reference_status'], 'NO INDEPENDENT LANE TRUTH')
    self.assertEqual(result['physical_delay_owner'], 'PLANT')
    self.assertFalse(result['controller_physical_delay_queue_present'])
    for arm in result['arms']:
      self.assertEqual(arm['structural_status'], 'STRUCTURAL_ADMISSION')
      self.assertTrue(all(abs(row['requested_torque'])<=1. for row in arm['samples']))
      self.assertNotIn('lane_center_rmse_m',arm['diagnostics'])
    self.assertFalse(result['performance_qualified'])
    self.assertFalse(result['runtime_accepted'])
    self.assertFalse(result['promotable'])

  def test_manifest_alias_and_common_basis_tamper_abort_preexecution(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_screening import run_screening_case
    for field in ('alias','candidate','cp','input','freeze'):
      value = copy.deepcopy(self.case)
      if field == 'alias':
        value['requests'][1]['native']['frames'][0]['driver_torque'] = .1
      elif field == 'candidate':
        value['requests'][2] = copy.deepcopy(value['requests'][0])
      elif field == 'cp':
        value['requests'][2]['native']['car_params_sha256'] = 'a'*64
      elif field == 'input':
        value['requests'][2]['native']['frames'][1]['active'] = False
      else:
        value['manifest']['scenario'] = 'sharp_high_left'
      with self.subTest(field=field), self.assertRaises(ValueError):
        run_screening_case(value,expected_manifest_sha256=digest(canonical(self.case['manifest'])),timeout_s=10.)

  def test_catalog_frozen_inputs_cover_requested_transitions(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_screening import SCREENING_CASES, build_screening_case
    self.assertEqual(len(SCREENING_CASES),13)
    for name in SCREENING_CASES:
      case = build_screening_case(name)
      self.assertEqual(case['requests'][0], case['requests'][1])
      self.assertEqual(case['requests'][0]['native'],case['requests'][2]['native'])
      self.assertEqual(case['manifest']['candidate_kind'],'FIXED_BOUNDED_A1_COMBINED_NO_SEARCH')
      self.assertEqual(len(case['manifest']['phase_labels']),401)
    case = build_screening_case('reengage_high')
    frames = case['requests'][0]['native']['frames']
    self.assertTrue(any(f['steering_pressed'] for f in frames))
    self.assertTrue(any(not f['active'] for f in frames))
    self.assertTrue(any(f['speed_mps']==25. for f in frames))

  def test_mirrored_inputs_preserve_curvature_pose_and_torque_symmetry(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_screening import build_screening_case, run_screening_case
    right = build_screening_case('gentle_low_right')
    result = run_screening_case(right,expected_manifest_sha256=digest(canonical(right['manifest'])),timeout_s=10.)
    for left_arm,right_arm in zip(self.report['arms'],result['arms'],strict=True):
      for left,right in zip(left_arm['samples'],right_arm['samples'],strict=True):
        for field in ('requested_torque','curvature_1pm','pose_y_m','steering_angle_deg'):
          self.assertAlmostEqual(left[field],-right[field],places=12)

  def test_diagnostics_and_events_are_measured_without_acceptance_threshold(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_screening import diagnose_samples
    samples = [
      {'requested_torque':u,'curvature_1pm':c,'desired_curvature_1pm':0.,'saturated':s,
       'pose_y_m':0.,'phase':'entry'} for u,c,s in ((0.,0.,False),(1.,.1,True),(0.,.2,False),(-1.,.3,False),(0.,.4,False),(1.,.5,False))
    ]
    result = diagnose_samples(samples,.01)
    self.assertEqual(result['command_zero_crossings'],2)
    self.assertEqual(result['command_derivative_rms_per_s'],100.)
    self.assertEqual(result['max_abs_command_derivative_per_s'],100.)
    self.assertEqual(result['saturation_occupancy'],1/6)
    self.assertEqual(result['command_total_variation'],5.)
    self.assertGreater(result['curvature_tracking_rmse_1pm'],0.)
    self.assertIn('phase_tracking_rmse_1pm',result)
    self.assertNotIn('accepted', result)

  def test_unknown_scenario_or_bad_report_is_not_silently_visualized(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_screening import build_screening_case, validate_screening_report
    with self.assertRaises(ValueError):
      build_screening_case('private_route')
    for field in ('receipt_sha256','reference_status','performance_qualified'):
      result = copy.deepcopy(self.report)
      result[field] = True
      with self.subTest(field=field), self.assertRaises(ValueError):
        validate_screening_report(result)

  def test_rehashed_physical_trace_and_authority_tamper_still_rejected(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_screening import validate_screening_report, diagnose_samples, _difference
    for field in ('curvature_1pm','applied_normalized_torque','pose_y_m','performance_qualified'):
      result = copy.deepcopy(self.report)
      if field == 'performance_qualified':
        result[field] = True
      else:
        row = result['arms'][2]['samples'][80]
        row[field] += .00001
        result['arms'][2]['samples_sha256'] = digest(canonical(result['arms'][2]['samples']))
        result['arms'][2]['diagnostics'] = diagnose_samples(result['arms'][2]['samples'],.01)
      result['candidate_difference'] = _difference(result['arms'][0]['samples'],result['arms'][2]['samples'])
      result['receipt_sha256'] = digest(canonical({k:v for k,v in result.items() if k != 'receipt_sha256'}))
      with self.subTest(field=field), self.assertRaises(ValueError):
        validate_screening_report(result)

  def test_freeze_rejection_never_starts_worker_and_worker_failure_never_emits_report(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_screening import run_screening_case
    with patch('openpilot.tools.cyber_autotune.curvature_yaw_screening.run_native_transcript') as worker:
      with self.assertRaises(ValueError):
        run_screening_case(self.case,expected_manifest_sha256='a'*64,timeout_s=10.)
      worker.assert_not_called()
      worker.return_value = {'status':'WORKER_FAILED'}
      with self.assertRaisesRegex(ValueError,'SCREENING_WORKER_FAILED'):
        run_screening_case(self.case,expected_manifest_sha256=digest(canonical(self.case['manifest'])),timeout_s=10.)

  def test_curvature_trace_uses_plant_state_and_not_negative_yaw_equivalent(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_plant import CurvatureYawPlantConfig, CurvatureYawPlantState, observe_curvature_yaw_step
    config = CurvatureYawPlantConfig(**self.case['requests'][0]['plant_config'])
    for arm in self.report['arms']:
      state = CurvatureYawPlantState(0.,0.,(0.,0.))
      for row in arm['samples']:
        state = observe_curvature_yaw_step(config,state,command=-row['requested_torque'],speed_mps=row['speed_mps'],roll_rad=0.).next_state
        self.assertEqual(row['curvature_1pm'],state.curvature_1pm)

  def test_identical_observations_are_reported_as_no_difference(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_screening import _difference
    result = _difference(self.report['arms'][0]['samples'],self.report['arms'][1]['samples'])
    self.assertEqual(result, {'changed_command_frames':0,'max_abs_command_difference':0.,'max_abs_pose_difference_m':0.})

  def test_source_support_drift_is_blocked_before_any_worker(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_screening import run_screening_case, _manifest
    value = copy.deepcopy(self.case)
    for request in value['requests']:
      first = next(iter(request['support_files']))
      request['support_files'][first] = 'a'*64
    value['manifest'] = _manifest(value['manifest']['scenario'],value['requests'])
    with patch('openpilot.tools.cyber_autotune.curvature_yaw_screening.run_native_transcript') as worker:
      worker.return_value = {'status':'WORKER_FAILED'}
      with self.assertRaises(ValueError):
        run_screening_case(value,expected_manifest_sha256=digest(canonical(value['manifest'])),timeout_s=10.)
      worker.assert_not_called()


if __name__ == '__main__':
  unittest.main()
