"""Known-construction geometry parameters, never actual measured height."""

import copy
import math
import unittest
import numpy as np
from openpilot.common.transformations.camera import device_frame_from_view_frame
from openpilot.common.transformations.orientation import rot_from_euler
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune.tests.test_camera_calibration_evidence import fixture
from openpilot.tools.cyber_autotune.tests.test_physical_calibration_wizard import filled
from openpilot.tools.cyber_autotune.native_protocol import canonical

try:
  from openpilot.tools.cyber_autotune import approximate_geometry_diagnostic as a
except ImportError:
  a = None


class TestApproxGeometry(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(a, 'Missing approximate diagnostic tier')
    self.prior = a.prior()

  def test_missing_height_and_uncertainty_stay_unknown(self):
    self.assertIsNone(self.prior['camera_height_m'])
    self.assertIsNone(self.prior['physical_uncertainty'])
    self.assertIsNone(self.prior['mount_x_m'])
    self.assertEqual(self.prior['status'], 'PARTIAL_APPROX_GEOMETRY')
    self.assertEqual(self.prior['mount_y']['role'], 'USER_DECLARED_APPROX_GEOMETRY')
    self.assertEqual(self.prior['mount_y']['nominal_m'], 0)

  def test_original_degrees_and_rounded_radians_not_conflated(self):
    x = self.prior['orientation']
    self.assertEqual(x['reported_deg'], [0.0, 2.34, 0.2])
    self.assertEqual(x['reported_rounded_rad'], [None, 0.0408, 0.00349])
    self.assertAlmostEqual(x['converted_rad'][1], math.radians(2.34), places=15)
    self.assertNotEqual(x['converted_rad'][1], x['reported_rounded_rad'][1])
    self.assertEqual(x['role'], 'MODEL_DERIVED_EXTRINSICS_PRIOR')

  def test_firewall_stale_and_forged_receipts_rejected(self):
    for field in ('qualification_allowed', 'reference_promotable', 'sealed_reference_allowed', 'vehicle_activation_allowed', 'private_input_allowed'):
      self.assertIs(self.prior[field], False)
      x = copy.deepcopy(self.prior)
      x[field] = True
      with self.assertRaises(ValueError):
        a.symbolic_height(x, [0, 0.1])
    x = copy.deepcopy(self.prior)
    x['camera_height_m'] = 1.42
    with self.assertRaises(ValueError):
      a.symbolic_height(x, [0, 0.1])

  def test_prior_cannot_enter_independent_admission(self):
    m, i = fixture()
    self.assertEqual(c.admit(self.prior, i)['status'], 'CALIBRATION_EVIDENCE_REJECTED')
    for role in ('MODEL_DERIVED_EXTRINSICS_PRIOR', 'VEHICLE_SPEC_PRIOR', 'USER_DECLARED_APPROX_GEOMETRY'):
      x = copy.deepcopy(m)
      x['observations']['pitch_rad']['provenance']['role'] = role
      self.assertEqual(c.admit(x, i)['status'], 'CALIBRATION_EVIDENCE_REJECTED')

  def test_wizard_rejects_each_approximate_role(self):
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import physical_calibration_wizard as w

    with tempfile.TemporaryDirectory() as root:
      session = w.MeasurementSession(Path(root) / 'test', scope='TEST_ONLY')
      for role in ('MODEL_DERIVED_EXTRINSICS_PRIOR', 'VEHICLE_SPEC_PRIOR', 'USER_DECLARED_APPROX_GEOMETRY'):
        d = filled(session)
        d['observations']['pitch_rad']['source_kind'] = role
        self.assertFalse(session.preflight(d)['valid'])

  def test_full_source_adapter_matrix_inverse_and_axis_changes(self):
    rpy = [0.12, 0.21, -0.16]
    e = rot_from_euler(rpy)
    f = np.diag([1.0, -1.0, -1.0])
    expected = f @ e.T @ device_frame_from_view_frame
    r = a.rotation(rpy)
    np.testing.assert_allclose(r, expected, rtol=0, atol=1e-14)
    np.testing.assert_allclose(e @ f @ r, device_frame_from_view_frame, atol=1e-14)
    self.assertGreater(np.max(np.abs(r - rot_from_euler(rpy) @ c.BASE_ROTATION)), 0.01)

  def test_pure_pitch_yaw_roll_direction_and_no_naive_composite_reuse(self):
    t = 0.2
    for rpy, want in (([0, t, 0], [0, t, 0]), ([0, 0, t], [0, 0, t]), ([t, 0, 0], [-t, 0, 0])):
      actual = a.physical_euler(rpy)
      np.testing.assert_allclose(actual, want, atol=1e-13)
    x = a.physical_euler([0.12, 0.21, -0.16])
    self.assertGreater(np.max(np.abs(np.array(x) - [-0.12, 0.21, -0.16])), 0.01)

  def test_aligned_ray_affine_height_and_left_sign(self):
    x = a.ray_relation([0, 0, 0], [0.1, 0.2])
    self.assertAlmostEqual(x['forward_per_height'], 5.0)
    self.assertAlmostEqual(x['lateral_per_height'], -0.5)
    self.assertIsNone(x['actual_height_m'])
    self.assertIs(x['reference_promotable'], False)

  def test_parametric_height_scaling_preserves_unknown_nominal(self):
    relation = a.symbolic_height(self.prior, [0.1, 0.2])
    r1 = a.project(self.prior, [0.1, 0.2], 1.0)
    r2 = a.project(self.prior, [0.1, 0.2], 2.0)
    self.assertAlmostEqual(r2['forward_m'], 2 * r1['forward_m'])
    self.assertAlmostEqual(r2['lateral_left_m'], 2 * r1['lateral_left_m'])
    self.assertAlmostEqual(r1['forward_m'], relation['forward_per_height'])
    self.assertIsNone(self.prior['camera_height_m'])
    self.assertEqual(r1['height_role'], 'ALGEBRAIC_PARAMETER_NOT_PHYSICAL_PRIOR')

  def test_horizon_invalid_height_and_nonfinite_rejected(self):
    for uv in ([0, -0.2], [math.inf, 0.2]):
      with self.assertRaises(ValueError):
        a.symbolic_height(self.prior, uv)
    for h in (0, -1, True, float('nan'), float('inf')):
      with self.assertRaises(ValueError):
        a.project(self.prior, [0, 0.2], h)

  def test_mount_sweep_is_diagnostic_parameter_not_uncertainty(self):
    r1 = a.project(self.prior, [0, 0.2], 1.0, mount_y_m=-0.1)
    r2 = a.project(self.prior, [0, 0.2], 1.0, mount_y_m=0.1)
    self.assertAlmostEqual(r2['lateral_left_m'] - r1['lateral_left_m'], 0.2)
    self.assertIsNone(r2['physical_uncertainty'])

  def test_sweep_policy_binding_determinism_and_four_distances(self):
    policy = a.parameter_policy([1.0, 2.0], [[0.0, 2.34, 0.2], [0.0, 2.5, 0.2]], [-0.1, 0.0, 0.1], rationale='TEST_ONLY algebraic domains')
    x = a.sensitivity(self.prior, policy)
    self.assertEqual(canonical(x), canonical(a.sensitivity(self.prior, policy)))
    self.assertEqual(len(x['rows']), 48)
    self.assertEqual({r['forward_distance_m'] for r in x['rows']}, {5.0, 10.0, 20.0, 30.0})
    self.assertEqual(x['policy_sha256'], policy['receipt_sha256'])
    self.assertIs(x['qualification_allowed'], False)
    y = a.parameter_policy([1.0], [[0.0, 2.34, 0.2]], [-0.1, 0.0, 0.1], rationale='TEST_ONLY')
    self.assertNotEqual(policy['receipt_sha256'], y['receipt_sha256'])

  def test_sweep_malformed_nonfinite_duplicate_or_excessive_rejected(self):
    for heights in ([], [1.0, 1.0], [0.0], [True], [float('nan')], list(range(1, 1000))):
      with self.assertRaises(ValueError):
        a.parameter_policy(heights, [[0, 2.34, 0.2]], [0.0], rationale='TEST_ONLY')
    p = a.parameter_policy([1.0], [[0, 2.34, 0.2]], [0.0], rationale='TEST_ONLY')
    p['heights_m'] = [2.0]
    with self.assertRaises(ValueError):
      a.sensitivity(self.prior, p)

  def test_fixed_normalized_ray_pitch_change_is_not_fixed_distance_uncertainty(self):
    one = a.project(self.prior, [0, 0.2], 1.0)
    two = a.project(self.prior, [0, 0.2], 1.0, rpy_deg=[0.0, 2.5, 0.2])
    self.assertNotEqual(one['forward_m'], two['forward_m'])
    self.assertEqual(one['input_domain'], 'SYNTHETIC_NORMALIZED_RAY_NO_PRIVATE_PIXEL')

  def test_vehicle_identity_not_inferred_from_replay_and_no_height_estimate(self):
    self.assertEqual(self.prior['vehicle']['status'], 'VEHICLE_SPEC_IDENTITY_PENDING')
    self.assertIsNone(self.prior['vehicle']['overall_height_m'])
    self.assertEqual(self.prior['vehicle']['repository_candidate'], 'HYUNDAI_SANTA_FE_2022_FIXED_REPLAY_TEST_TARGET_ONLY')
    self.assertIsNone(self.prior['camera_height_m'])

  def test_declared_spec_sanity_only_never_imputes_camera_height(self):
    spec = {
      'schema': 'VEHICLE_SPEC_PRIOR_V1',
      'role': 'VEHICLE_SPEC_PRIOR',
      'model_identity': 'TEST_ONLY',
      'overall_length_m': 4.8,
      'overall_width_m': 1.9,
      'overall_height_m': 1.7,
      'wheelbase_m': 2.7,
      'source_url': 'https://example.invalid/TEST_ONLY',
      'source_sha256': 'a' * 64,
      'assumptions': 'SAME_GROUND_DATUM_INSIDE_CABIN_TEST_ONLY',
    }
    x = a.vehicle_sanity(self.prior, spec, 1.8)
    self.assertEqual(x['status'], 'OUTSIDE_DECLARED_SPEC_SANITY_DOMAIN')
    self.assertIsNone(x['camera_height_estimate_m'])
    self.assertIs(x['qualification_allowed'], False)
    self.assertIsNone(self.prior['camera_height_m'])

  def test_physical_comparison_pending_then_receipt_bound_not_validation(self):
    x = a.compare_physical(self.prior, None)
    self.assertEqual(x['status'], 'PHYSICAL_MEASUREMENT_COMPARISON_PENDING')
    m, i = fixture()
    physical = c.admit(m, i)
    r = a.compare_physical(self.prior, physical)
    self.assertEqual(r['scope'], 'APPROX_PHYSICAL_CONSISTENCY_DIAGNOSTIC')
    self.assertIs(r['live_calibration_validated'], False)
    self.assertEqual(r['physical_receipt_sha256'], physical['receipt_sha256'])
    self.assertEqual(r['height']['approximate_m'], None)
    self.assertEqual(r['height']['physical_m'], m['observations']['height_m']['value'])
    self.assertEqual(r['physical_scope'], 'TEST_ONLY')
    self.assertEqual(canonical(r), canonical(a.compare_physical(self.prior, physical)))

  def test_physical_comparison_signs_and_difference_are_not_absolute_prior_error(self):
    m, i = fixture()
    x = a.compare_physical(self.prior, c.admit(m, i))
    # Positive reported pure-ish pitch maps to positive physical Euler pitch.
    self.assertGreater(x['orientation']['pitch']['approximate_deg'], 2.0)
    self.assertAlmostEqual(
      x['orientation']['pitch']['delta_physical_minus_approx_rad'],
      m['observations']['pitch_rad']['value'] - math.radians(x['orientation']['pitch']['approximate_deg']),
    )
    self.assertIsNone(x['automatic_discrepancy_threshold_rad'])

  def test_forged_physical_comparison_rejected(self):
    with self.assertRaises(ValueError):
      a.compare_physical(self.prior, self.prior)

  def test_additive_blocker_keeps_independent_path_blocked_and_private_closed(self):
    x = a.readiness(self.prior)
    self.assertEqual(x['diagnostic_status'], 'APPROX_GEOMETRY_DIAGNOSTIC_AVAILABLE')
    self.assertEqual(x['calibration_status'], 'CALIBRATION_MEASUREMENT_PENDING')
    self.assertEqual(x['private_comma4'], 'NOT_OPENED')
    self.assertEqual(x['sealed_reference'], 'NOT_GENERATED')
    self.assertIs(x['private_input_allowed'], False)
    self.assertIs(x['qualification_allowed'], False)

  def test_numeric_equivalent_parameter_duplicates_rejected(self):
    with self.assertRaises(ValueError):
      a.parameter_policy([1, 1.0], [[0, 2.34, 0.2]], [0.0], rationale='TEST_ONLY')

  def test_loaded_diagnostic_cannot_report_new_disk_source_as_executed(self):
    from pathlib import Path
    from unittest.mock import patch

    original = Path.read_bytes

    def changed(path):
      data = original(path)
      return data + b'\nTEST_ONLY_DRIFT' if path == Path(a.__file__) else data

    with patch.object(Path, 'read_bytes', changed):
      with self.assertRaises(ValueError):
        a.prior()
