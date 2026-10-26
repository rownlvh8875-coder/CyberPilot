"""Approved coarse estimates cannot become measurement or qualification evidence."""

import copy
import math
import unittest
from openpilot.tools.cyber_autotune import approximate_geometry_diagnostic as a
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune.native_protocol import canonical
from openpilot.tools.cyber_autotune.tests.test_camera_calibration_evidence import fixture

try:
  from openpilot.tools.cyber_autotune import coarse_camera_height_diagnostic as h
except ImportError:
  h = None


class TestCoarseHeight(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(h, 'Missing separate coarse height diagnostic')
    self.prior = h.height_prior()
    self.policy = h.frozen_policy()

  def test_user_estimate_preserved_without_measurement_uncertainty(self):
    self.assertEqual(self.prior['nominal_height_m'], 1.40)
    self.assertEqual(self.prior['diagnostic_sensitivity_range'], [1.33, 1.47])
    self.assertEqual(self.prior['source_role'], 'USER_APPROVED_DIAGNOSTIC_ESTIMATE')
    self.assertIsNone(self.prior['measurement_uncertainty'])
    self.assertIs(self.prior['physical_measurement'], False)
    self.assertIsNone(a.prior()['camera_height_m'])

  def test_vehicle_context_never_derives_camera_height(self):
    v = h.vehicle_context()
    self.assertEqual(v['overall_height_m'], 1.685)
    self.assertEqual(v['user_vehicle_model_year'], 2021)
    self.assertEqual(v['official_source']['page_variant'], '2021.12 Smartstream D2.2 2WD/FWD')
    self.assertIsNone(v['derived_camera_height_m'])
    self.assertFalse(v['actual_trim_verified'])

  def test_tire_calculation_nominal_not_loaded_radius(self):
    v = h.vehicle_context()['tire_geometry']
    self.assertAlmostEqual(v['sidewall_mm'], 141.0)
    self.assertAlmostEqual(v['wheel_diameter_mm'], 457.2)
    self.assertAlmostEqual(v['outer_diameter_m'], 0.7392)
    self.assertAlmostEqual(v['unloaded_nominal_radius_m'], 0.3696)
    self.assertFalse(v['camera_height_measurement'])

  def test_frozen_grid_and_identity_before_result(self):
    self.assertEqual(self.policy['heights_m'], [1.33, 1.35, 1.375, 1.4, 1.425, 1.45, 1.47])
    self.assertEqual(self.policy['pitches_deg'], [1.84, 2.34, 2.84])
    self.assertEqual(self.policy['distances_m'], [5.0, 10.0, 20.0, 30.0])
    self.assertEqual(self.policy['range_role'], 'DIAGNOSTIC_SENSITIVITY_RANGE_NOT_PHYSICAL_UNCERTAINTY')
    self.assertEqual(canonical(h.evaluate(self.prior, self.policy)), canonical(h.evaluate(self.prior, self.policy)))

  def test_fixed_ray_height_scaling_does_not_retarget_ground_point(self):
    report = h.evaluate(self.prior, self.policy)
    for row in report['sensitivity_envelope']['matrix']:
      if row['pitch_deg'] != 2.34:
        continue
      self.assertAlmostEqual(row['forward_m'], row['nominal_forward_distance_m'] * row['height_m'] / 1.4, places=10)
      self.assertAlmostEqual(row['lateral_probe_left_m'], row['height_m'] / 1.4, places=10)
      self.assertAlmostEqual(row['center_lateral_left_m'], 0, places=10)
    nominal = report['nominal_result']['rows']
    self.assertEqual(len(nominal), 4)
    self.assertNotEqual(report['nominal_result']['receipt_sha256'], report['sensitivity_envelope']['receipt_sha256'])
    self.assertIsNone(report['nominal_result']['actual_fx_px'])

  def test_positive_reported_pitch_shortens_fixed_ray_ground_intersection(self):
    rows = h.evaluate(self.prior, self.policy)['sensitivity_envelope']['matrix']
    by_pitch = {r['pitch_deg']:r for r in rows if r['height_m'] == 1.4 and r['nominal_forward_distance_m'] == 30.0}
    self.assertLess(by_pitch[2.84]['forward_m'], by_pitch[2.34]['forward_m'])
    self.assertGreater(by_pitch[1.84]['forward_m'], by_pitch[2.34]['forward_m'])

  def test_nominal_rotation_preserves_full_inverse_frame_adapter(self):
    r = h.evaluate(self.prior, self.policy)['nominal_result']
    self.assertEqual(r['source_orientation_deg'], [0.0, 2.34, 0.2])
    self.assertEqual(r['rotation_optical_to_diagnostic_road'], a.rotation([0, math.radians(2.34), math.radians(0.2)]).tolist())
    self.assertEqual(r['parameter_roles']['height'], 'USER_APPROVED_COARSE_GEOMETRY_PRIOR')
    self.assertEqual(r['parameter_roles']['orientation'], 'MODEL_DERIVED_EXTRINSICS_PRIOR')
    self.assertEqual(r['parameter_roles']['mount_y'], 'USER_DECLARED_APPROX_CENTER_MOUNT')

  def test_yaw_and_roll_sweeps_are_not_physical_uncertainty(self):
    r = h.evaluate(self.prior, self.policy)['sensitivity_envelope']
    self.assertEqual(len(r['orientation_1d']), 24)
    yaw = [x for x in r['orientation_1d'] if x['axis'] == 'yaw' and x['nominal_forward_distance_m'] == 10]
    self.assertGreater(yaw[-1]['center_lateral_left_m'], yaw[0]['center_lateral_left_m'])
    self.assertIsNone(r['physical_uncertainty'])
    self.assertEqual(r['range_role'], 'MODEL_PRIOR_SENSITIVITY_NOT_PHYSICAL_UNCERTAINTY')

  def test_resealed_prior_mutation_or_promotion_rejected(self):
    for key, replacement in (('nominal_height_m', 1.685), ('measurement_uncertainty', 0.07), ('qualification_allowed', True), ('independent', True)):
      altered = copy.deepcopy(self.prior)
      altered.pop('receipt_sha256')
      altered[key] = replacement
      with self.assertRaises(ValueError):
        h.evaluate(c.seal(altered), self.policy)

  def test_resealed_grid_mutation_or_nonfinite_rejected(self):
    for value in ([1.4], [float('nan')], [1.33, 1.47]):
      altered = copy.deepcopy(self.policy)
      altered.pop('receipt_sha256')
      altered['heights_m'] = value
      with self.assertRaises(ValueError):
        h.evaluate(self.prior, c.seal(altered))

  def test_independent_admission_rejects_coarse_artifact_and_roles(self):
    m, i = fixture()
    self.assertEqual(c.admit(self.prior, i)['status'], 'CALIBRATION_EVIDENCE_REJECTED')
    self.assertEqual(c.admit(h.evaluate(self.prior, self.policy), i)['status'], 'CALIBRATION_EVIDENCE_REJECTED')
    for role in ('USER_APPROVED_COARSE_GEOMETRY_PRIOR', 'USER_APPROVED_DIAGNOSTIC_ESTIMATE', 'VEHICLE_SPEC_PRIOR'):
      changed = copy.deepcopy(m)
      changed['observations']['height_m']['provenance']['role'] = role
      self.assertEqual(c.admit(changed, i)['status'], 'CALIBRATION_EVIDENCE_REJECTED')

  def test_valid_physical_outside_range_not_rejected_or_clamped(self):
    m, i = fixture()
    m['observations']['height_m']['value'] = 1.6
    physical = c.admit(m, i)
    self.assertEqual(physical['status'], 'CALIBRATION_EVIDENCE_ADMITTED')
    r = h.compare_physical(self.prior, physical)
    self.assertAlmostEqual(r['height']['delta_physical_minus_coarse_m'], 0.2)
    self.assertFalse(r['height']['within_diagnostic_range'])
    self.assertEqual(r['height']['physical_m'], 1.6)
    self.assertEqual(r['height']['provenance_precedence'], 'PHYSICAL_RECEIPT_OVER_COARSE_FOR_FUTURE_MATCHED_DEVICE')
    self.assertFalse(r['cross_device_identity_verified'])
    self.assertFalse(r['qualification_allowed'])

  def test_no_physical_receipt_keeps_pending_and_never_imputes(self):
    r = h.compare_physical(self.prior, None)
    self.assertIsNone(r['height']['physical_m'])
    self.assertEqual(r['status'], 'PHYSICAL_MEASUREMENT_COMPARISON_PENDING')
    with self.assertRaises(ValueError):
      h.compare_physical(self.prior, self.prior)

  def test_blockers_remain_and_private_and_sealing_stay_closed(self):
    r = h.readiness(self.prior)
    self.assertEqual(r['coarse_height_status'], 'COARSE_CAMERA_HEIGHT_PRIOR_AVAILABLE')
    self.assertEqual(r['calibration_status'], 'CALIBRATION_MEASUREMENT_PENDING')
    self.assertEqual(r['independent_validation_status'], 'INDEPENDENT_CALIBRATION_VALIDATION_PENDING')
    self.assertEqual(r['independent_reference_status'], 'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE')
    self.assertEqual(r['private_comma4'], 'NOT_OPENED')
    self.assertEqual(r['sealed_reference'], 'NOT_GENERATED')
    for k in a.FIREWALL:
      self.assertIs(r[k], False)

  def test_source_drift_cannot_claim_frozen_execution_identity(self):
    from pathlib import Path
    from unittest.mock import patch
    original = Path.read_bytes

    def changed(path):
      return original(path) + (b'TEST_ONLY_DRIFT' if path == Path(h.__file__) else b'')

    with patch.object(Path, 'read_bytes', changed):
      with self.assertRaises(ValueError):
        h.height_prior()
