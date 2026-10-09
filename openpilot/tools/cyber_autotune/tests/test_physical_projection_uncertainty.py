"""Known geometry and synthetic uncertainty bounds, not measured vehicle results."""
import copy
import math
import unittest
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune.tests.test_camera_calibration_evidence import fixture
from openpilot.tools.cyber_autotune.tests.test_qcamera_pixel_registration import registered_fixture
try:
  from openpilot.tools.cyber_autotune import physical_projection_uncertainty as u
except ImportError:
  u = None


class TestPhysicalUncertainty(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(u, 'physical uncertainty engine missing')
    m, i = fixture()
    self.cal = c.admit(m, i)
    self.bounds = {'grade_rad': .001, 'camber_rad': .001, 'nonplanarity_m': .002,
                   'annotation_px': .5, 'source_sha256': 'a' * 64}
    self.mapping = registered_fixture(self.cal)

  def test_absent_measurements_pending_no_meter_numbers(self):
    x = u.report(None, None, None)
    self.assertEqual(x['status'], 'CALIBRATION_MEASUREMENT_PENDING')
    self.assertIsNone(x['meter_results'])
    self.assertFalse(x['sealed_reference_allowed'])

  def test_pixel_input_historical_binding_coverage_and_quantiles(self):
    p = u.pixel_input()
    self.assertAlmostEqual(p['center']['p95'], 5.053136006631054)
    self.assertEqual(p['center']['available_frames'], 44)
    self.assertEqual(p['center']['unavailable_frames'], 11)
    self.assertEqual(p['source_wh'], [526, 330])
    self.assertEqual(p['kind'], 'ASSISTED_MATCHED_POINT_QUANTILES_NOT_ABSOLUTE_BOUND')

  def test_original_to_calibrated_pixel_mapping_mandatory(self):
    with self.assertRaises(ValueError):
      u.report(self.cal, self.bounds, None)
    bad = copy.deepcopy(self.mapping)
    bad['verified_crop_resize'] = False
    with self.assertRaises(ValueError):
      u.report(self.cal, self.bounds, bad)

  def test_numeric_report_is_test_scope_not_actual_physical_result(self):
    x = u.report(self.cal, self.bounds, self.mapping)
    self.assertEqual(x['scope'], 'TEST_ONLY')
    self.assertEqual(len(x['meter_results']), 6)
    self.assertFalse(x['qualification_allowed'])
    self.assertEqual(x['center_availability'], {'matched': 44, 'evaluable': 55, 'unavailable': 11})
    for row in x['meter_results']:
      self.assertIsNone(row['total_detector_plus_calibration_absolute_bound_m'])
      self.assertGreaterEqual(row['calibration_interval_envelope_m'], row['calibration_corner_max_m'])

  def test_intrinsic_rotation_jacobian_central_difference(self):
    x = u.query(self.cal, 20., 1.)
    for name in x['derivatives']:
      eps = 1e-5
      plus = dict(x['nominal'])
      minus = dict(x['nominal'])
      plus[name] += eps
      minus[name] -= eps
      numeric = (u.project_state(plus) - u.project_state(minus)) / (2 * eps)
      self.assertAlmostEqual(numeric, x['derivatives'][name], delta=1e-5)

  def test_interval_encloses_corner_and_nonlinear_remainder(self):
    x = u.query(self.cal, 30., 1.)
    out = u.envelope(x, self.cal, self.bounds, self.mapping)
    self.assertGreaterEqual(out['calibration_interval_envelope_m'], out['calibration_corner_max_m'])
    self.assertGreaterEqual(out['sampled_nonlinear_remainder_m'], 0)
    self.assertEqual(out['nonlinear_sampling_scope'], 'AXIS_ENDPOINTS_NOT_CERTIFICATE')
    self.assertIn('pitch_rad', out['first_order_terms_m'])

  def test_uncertainty_monotonicity_and_distance(self):
    x = u.report(self.cal, self.bounds, self.mapping)
    bigger = copy.deepcopy(self.bounds)
    bigger['annotation_px'] *= 2
    y = u.report(self.cal, bigger, self.mapping)
    for a, b in zip(x['meter_results'], y['meter_results'], strict=True):
      self.assertGreaterEqual(b['calibration_interval_envelope_m'], a['calibration_interval_envelope_m'])
    self.assertGreater(x['meter_results'][-1]['detector_equivalent_center_p95_m'], x['meter_results'][0]['detector_equivalent_center_p95_m'])

  def test_horizon_domain_invalid_not_clipped(self):
    bad = copy.deepcopy(self.bounds)
    bad['grade_rad'] = 1.
    with self.assertRaises(ValueError):
      u.report(self.cal, bad, self.mapping)

  def test_quantile_not_absolute_bound_and_assisted_not_independent(self):
    x = u.report(self.cal, self.bounds, self.mapping)
    self.assertFalse(x['independent_ground_truth'])
    for row in x['meter_results']:
      self.assertIn('conditional', row['detector_quantile_scope'].lower())
      self.assertIsNone(row['total_detector_plus_calibration_absolute_bound_m'])
    self.assertEqual(c.admit(x, self.cal['intrinsics'])['status'], 'CALIBRATION_EVIDENCE_REJECTED')

  def test_bad_road_annotation_bounds_and_boolean_rejected(self):
    for k in ('annotation_px', 'grade_rad', 'camber_rad', 'nonplanarity_m'):
      bad = copy.deepcopy(self.bounds)
      bad[k] = None
      with self.assertRaises(ValueError):
        u.report(self.cal, bad, self.mapping)
    bad = copy.deepcopy(self.mapping)
    bad['verified_same_camera'] = 1
    with self.assertRaises(ValueError):
      u.report(self.cal, self.bounds, bad)

  def test_cosine_interval_contains_actual_scalar_cosine(self):
    for value in (1.4, -math.pi / 2, math.pi, 0.):
      interval = u.trig(u.Interval(value), True)
      self.assertLessEqual(interval.lo, math.cos(value))
      self.assertGreaterEqual(interval.hi, math.cos(value))

  def test_tampered_admitted_calibration_rejected(self):
    x = copy.deepcopy(self.cal)
    x['measurement']['observations']['height_m']['value'] = 1.4
    with self.assertRaises(ValueError):
      u.report(x, self.bounds, self.mapping)


if __name__ == '__main__':
  unittest.main()
