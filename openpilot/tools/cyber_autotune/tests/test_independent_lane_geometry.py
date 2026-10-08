"""Known-by-construction geometry only; no public/private ego GT manufactured."""

import copy
import unittest
import numpy as np
from openpilot.tools.cyber_autotune.tests.test_camera_calibration_evidence import fixture
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal

try:
  from openpilot.tools.cyber_autotune import independent_lane_geometry as g
except ImportError:
  g = None


def pair_fixture():
  markings = {
    'scope': 'TEST_ONLY',
    'source_role': 'INDEPENDENT_DETECTOR',
    'source_sha256': 'a' * 64,
    'resolution_wh': [1344, 760],
    'modelv2_used': False,
    'planner_used': False,
    'candidate_used': False,
    'steering_command_used': False,
    'markings': [{'id': 'left', 'points': [[500, 450], [400, 650]]}, {'id': 'right', 'points': [[800, 450], [900, 650]]}],
  }
  evidence = {
    'method': 'INDEPENDENT_HUMAN_PROPOSAL',
    'source_sha256': 'b' * 64,
    'direction_evidence_sha256': 'c' * 64,
    'pairs': [{'left_id': 'left', 'right_id': 'right', 'proposal_sha256': 'd' * 64}],
    'context': dict.fromkeys(('merge', 'split', 'intersection', 'markings_inconsistent', 'outside_validated_range'), False),
    'modelv2_used': False,
    'planner_used': False,
    'candidate_used': False,
    'steering_command_used': False,
  }
  return markings, evidence


def road():
  return {'yaw_rad': 0.0, 'origin_m': [0.0, 0.0, 0.0], 'translation_bound_m': [0.001] * 3, 'yaw_bound_rad': 0.001, 'source_sha256': 'e' * 64}


class TestGeometry(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(g, 'Missing independent geometry contract')
    self.markings, self.evidence = pair_fixture()

  def test_unique_independent_proposal_is_candidate_not_validated(self):
    x = g.assess_pair(self.markings, self.evidence)
    self.assertEqual(x['status'], 'EGO_PAIR_AVAILABLE')
    self.assertEqual(x['validation'], 'VALIDATION_PENDING')
    self.assertFalse(x['ego_association_validated'])
    self.assertFalse(x['reference_promotable'])

  def test_merge_split_intersection_multiple_or_inconsistent_ambiguous(self):
    for flag in ('merge', 'split', 'intersection', 'markings_inconsistent'):
      e = copy.deepcopy(self.evidence)
      e['context'][flag] = True
      self.assertEqual(g.assess_pair(self.markings, e)['status'], 'EGO_PAIR_AMBIGUOUS')
    e = copy.deepcopy(self.evidence)
    e['pairs'] *= 2
    self.assertEqual(g.assess_pair(self.markings, e)['status'], 'EGO_PAIR_AMBIGUOUS')

  def test_one_side_no_proposal_outside_domain_unavailable(self):
    m = copy.deepcopy(self.markings)
    m['markings'] = m['markings'][:1]
    self.assertEqual(g.assess_pair(m, self.evidence)['status'], 'EGO_PAIR_UNAVAILABLE')
    e = copy.deepcopy(self.evidence)
    e['pairs'] = []
    self.assertEqual(g.assess_pair(self.markings, e)['status'], 'EGO_PAIR_UNAVAILABLE')
    e = copy.deepcopy(self.evidence)
    e['context']['outside_validated_range'] = True
    self.assertEqual(g.assess_pair(self.markings, e)['status'], 'EGO_PAIR_UNAVAILABLE')

  def test_contamination_flags_and_fabricated_validation_rejected(self):
    for field in ('modelv2_used', 'planner_used', 'candidate_used', 'steering_command_used'):
      e = copy.deepcopy(self.evidence)
      e[field] = True
      with self.assertRaises(ValueError):
        g.assess_pair(self.markings, e)
    x = unseal(g.assess_pair(self.markings, self.evidence))
    x['ego_association_validated'] = True
    with self.assertRaises(ValueError):
      g.validate_pair(seal(x))

  def test_left_right_reversal_not_valid_pair(self):
    e = copy.deepcopy(self.evidence)
    e['pairs'][0].update(left_id='right', right_id='left')
    self.assertEqual(g.assess_pair(self.markings, e)['status'], 'EGO_PAIR_AMBIGUOUS')

  def test_road_registration_gate_requires_real_metric_and_ego_validation(self):
    m, i = fixture()
    x = g.registration_gate(c.admit(m, i), g.assess_pair(self.markings, self.evidence))
    self.assertEqual(x['status'], 'BLOCKED')
    self.assertIn('METRIC_CALIBRATION_UNAVAILABLE', x['blockers'])
    self.assertIn('COMMA10K_EGO_LANE_IDENTITY_UNAVAILABLE', x['blockers'])
    self.assertFalse(x['reference_promotable'])

  def test_known_straight_parallel_and_symmetry(self):
    m, i = fixture()
    r, center, _, _ = c.pose(m)
    points = np.array([[10, 1.5, 0], [10, -1.5, 0], [20, 1.5, 0], [20, -1.5, 0]], float)
    k = np.array(i['matrix'])
    cam = (r.T @ (points - center).T).T
    uv = (k @ cam.T).T
    pixels = (uv[:, :2] / uv[:, 2:]).tolist()
    x = g.known_registration(k.tolist(), r.tolist(), center.tolist(), pixels, road(), i['resolution_wh'])
    np.testing.assert_allclose(x['road_points_m'], points, atol=1e-9)
    self.assertFalse(x['reference_promotable'])

  def test_known_left_right_curves_pitch_height_roll_and_road_origin(self):
    m, i = fixture()
    r, center, _, _ = c.pose(m)
    k = np.array(i['matrix'])
    for sign in (-1, 1):
      points = np.array([[x, sign * 0.002 * x * x, 0] for x in (5.0, 10.0, 20.0, 30.0)])
      cam = (r.T @ (points - center).T).T
      uv = (k @ cam.T).T
      pixels = (uv[:, :2] / uv[:, 2:]).tolist()
      transform = road()
      transform['yaw_rad'] = 0.1
      transform['origin_m'] = [0.5, 0.2, 0.0]
      x = g.known_registration(k.tolist(), r.tolist(), center.tolist(), pixels, transform, i['resolution_wh'])
      expected = (g.rotation_z(0.1) @ points.T).T + np.array(transform['origin_m'])
      np.testing.assert_allclose(x['road_points_m'], expected, atol=1e-9)

  def test_negative_coordinate_units_axes_origin_and_image_y(self):
    m, i = fixture()
    r, center, _, _ = c.pose(m)
    k = i['matrix']
    uv = [[672.0, 600.0]]
    for kwargs in ({'angle_unit': 'deg'}, {'optical_frame': 'Y_UP'}, {'vehicle_frame': 'LEFT_HANDED'}, {'pixel_origin': 'BOTTOM_LEFT'}):
      with self.assertRaises(ValueError):
        g.known_registration(k, r.tolist(), center.tolist(), uv, road(), i['resolution_wh'], **kwargs)
    rr = r.copy()
    rr[:, 0] *= -1
    with self.assertRaises(ValueError):
      g.known_registration(k, rr.tolist(), center.tolist(), uv, road(), i['resolution_wh'])
    for pixel in ([-1, 600], [672, -1], [672, 760]):
      with self.assertRaises(ValueError):
        g.known_registration(k, r.tolist(), center.tolist(), [pixel], road(), i['resolution_wh'])

  def test_same_xy_ray_known_wrong_orientation_cannot_silently_pass(self):
    m, i = fixture()
    r, center, _, _ = c.pose(m)
    # Proper swapped orientation can be mathematically a different pose: numerical
    # fixture must expose different values, not invent an automatic semantic check.
    swapped = r.copy()
    swapped[:, [0, 1]] = swapped[:, [1, 0]]
    swapped[:, 2] *= -1
    with self.assertRaises(ValueError):
      g.known_registration(i['matrix'], swapped.tolist(), center.tolist(), [[672, 600]], road(), i['resolution_wh'])

  def test_midpoint_common_samples_deterministic_not_optimal_path(self):
    left = [[5.0, 2.0], [6.0, 2.1], [7.0, 2.3]]
    right = [[5.0, -2.0], [6.0, -1.9], [7.0, -1.7]]
    x = g.midpoint_fixture(left, right, maximum_gap_m=1.1)
    np.testing.assert_allclose(x['points_m'], [[5.0, 0.0], [6.0, 0.1], [7.0, 0.3]], atol=1e-12)
    self.assertEqual(x, g.midpoint_fixture(left, right, maximum_gap_m=1.1))
    self.assertFalse(x['optimal_driving_path'])
    self.assertFalse(x['reference_promotable'])

  def test_missing_side_gap_crossing_or_mismatched_samples_unavailable(self):
    for left, right in (
      ([], [[5, -2], [6, -2]]),
      ([[5, 2], [8, 2]], [[5, -2], [8, -2]]),
      ([[5, -2], [6, -2]], [[5, 2], [6, 2]]),
      ([[5, 2], [6, 2]], [[5, -2], [7, -2]]),
    ):
      self.assertEqual(g.midpoint_fixture(left, right, maximum_gap_m=1.1)['status'], 'REFERENCE_UNAVAILABLE')

  def test_centerline_gate_no_reference_from_constructed_midpoint(self):
    x = g.lane_center_gate(g.registration_gate(c.admit(None), None))
    self.assertEqual(x['status'], 'REFERENCE_UNAVAILABLE')
    self.assertIsNone(x['points_m'])
    self.assertFalse(x['sealed_reference_allowed'])

  def test_registration_and_centerline_contract_identity(self):
    self.assertEqual(g.ego_contract(), g.ego_contract())
    self.assertEqual(g.centerline_contract()['definition'], 'INDEPENDENT_LANE_CENTER_REFERENCE_NOT_OPTIMAL_DRIVING_PATH')

  def test_mutating_contract_does_not_change_algorithm_policy(self):
    before = copy.deepcopy(g.POLICY)
    try:
      receipt = g.ego_contract()
      receipt['policy']['interpolation'] = True
      self.assertEqual(g.POLICY, before)
    finally:
      g.POLICY.clear()
      g.POLICY.update(before)

  def test_midpoint_nonfinite_arithmetic_cannot_escape(self):
    x = g.midpoint_fixture([[5.0, 1e308], [6.0, 1e308]], [[5.0, 0.9e308], [6.0, 0.9e308]], maximum_gap_m=2.0)
    self.assertTrue(np.all(np.isfinite(x['points_m'])))
