import copy
import unittest

from openpilot.tools.cyber_autotune import resolution_candidate_audit as a


class TestResolutionCandidateAudit(unittest.TestCase):
  def trace(self):
    return [
      {'pose_x_m': x, 'pose_y_m': y, 'time_s': x / 10, 'phase': 'entry', 'speed_mps': 10.0, 'desired_curvature_1pm': 0.001}
      for x, y in ((1.0, 0.1), (10.0, 1.0), (30.0, 3.0))
    ]

  def test_interpolation(self):
    self.assertEqual(a.at_distance(self.trace(), 5.0, a.BASIS)['pose_y_m'], 0.5)

  def test_exact_endpoint(self):
    self.assertEqual(a.at_distance(self.trace(), 30.0, a.BASIS)['pose_y_m'], 3.0)

  def test_no_extrapolation(self):
    for d in (0.0, 31.0):
      self.assertEqual(a.at_distance(self.trace(), d, a.BASIS)['status'], 'DISTANCE_NOT_REACHED')

  def test_missing_trace(self):
    self.assertEqual(a.at_distance([], 5.0, a.BASIS)['status'], 'COVERAGE_UNAVAILABLE')

  def test_torque_only_uncomparable(self):
    self.assertEqual(a.at_distance([{'torque': 1.0}], 5.0, a.BASIS)['status'], 'UNCOMPARABLE_COORDINATE_BASIS')

  def test_units_frame_mismatch(self):
    for key, value in [('units', 'px'), ('frame', 'CAMERA'), ('distance', 'TIME'), ('effect', 'TORQUE')]:
      basis = {**a.BASIS, key: value}
      self.assertEqual(a.at_distance(self.trace(), 5.0, basis)['status'], 'UNCOMPARABLE_COORDINATE_BASIS')

  def test_nonmonotone_rejected(self):
    t = self.trace()
    t[1]['pose_x_m'] = 0.5
    self.assertEqual(a.at_distance(t, 5.0, a.BASIS)['status'], 'UNCOMPARABLE_COORDINATE_BASIS')

  def test_duplicate_x_rejected(self):
    t = self.trace()
    t[1]['pose_x_m'] = 1.0
    self.assertEqual(a.at_distance(t, 5.0, a.BASIS)['status'], 'UNCOMPARABLE_COORDINATE_BASIS')

  def test_nonfinite_rejected(self):
    for value in (float('nan'), float('inf'), True):
      t = self.trace()
      t[0]['pose_y_m'] = value
      self.assertEqual(a.at_distance(t, 5.0, a.BASIS)['status'], 'UNCOMPARABLE_COORDINATE_BASIS')

  def test_classification_boundaries(self):
    for effect, status in [
      (0.0, 'EFFECT_BELOW_DECLARED_ENVELOPE'),
      (0.099, 'EFFECT_BELOW_DECLARED_ENVELOPE'),
      (0.1, 'EFFECT_OVERLAPS_DECLARED_ENVELOPE'),
      (0.2, 'EFFECT_OVERLAPS_DECLARED_ENVELOPE'),
      (0.201, 'EFFECT_EXCEEDS_DECLARED_ENVELOPE'),
    ]:
      self.assertEqual(a.classify(effect, 0.1, 0.2), status)

  def test_absolute_effect(self):
    self.assertEqual(a.classify(-0.3, 0.1, 0.2), 'EFFECT_EXCEEDS_DECLARED_ENVELOPE')

  def test_invalid_envelope(self):
    for lo, hi in [(0.0, 1.0), (0.2, 0.1), (None, 1.0), (0.1, float('nan'))]:
      self.assertEqual(a.classify(0.1, lo, hi), 'COVERAGE_UNAVAILABLE')

  def test_ratio(self):
    d = a.compare(0.01, 0.04, 0.01, {'minimum_p95_m': 0.1, 'maximum_p95_m': 0.2}, True)
    self.assertAlmostEqual(d['effect_to_min_envelope_ratio'], 0.3)
    self.assertAlmostEqual(d['effect_to_max_envelope_ratio'], 0.15)
    self.assertAlmostEqual(d['candidate_minus_current_m'], 0.03)

  def test_repeatability_gate(self):
    self.assertEqual(a.compare(0.0, 1.0, 0.0, {'minimum_p95_m': 0.1, 'maximum_p95_m': 0.2}, False)['classification'], 'REPEATABILITY_FAILED')

  def test_coverage_gate(self):
    self.assertEqual(a.compare(0.0, 1.0, 0.0, None, True)['classification'], 'COVERAGE_UNAVAILABLE')

  def test_current_alias(self):
    self.assertEqual(a.compare(0.2, 0.2, 0.2, {'minimum_p95_m': 0.1, 'maximum_p95_m': 0.2}, True)['absolute_effect_m'], 0.0)

  def test_signs(self):
    self.assertEqual(a.sign(0.1), 1)
    self.assertEqual(a.sign(-0.1), -1)
    self.assertEqual(a.sign(0.0), 0)

  def test_signed_displacement_not_improvement(self):
    r = a.compare(0.1, 0.2, 0.1, {'minimum_p95_m': 0.1, 'maximum_p95_m': 0.2}, True)
    self.assertEqual(r['direction_semantics'], 'SIGNED_PLANT_DISPLACEMENT_NOT_IMPROVEMENT')

  def test_sign_inconsistency(self):
    self.assertEqual(a.direction_status([1, -1]), 'DIRECTIONALLY_INCONSISTENT_TRADEOFF')
    self.assertEqual(a.direction_status([0, 1]), 'ONE_DISPLACEMENT_DIRECTION_ONLY_NOT_IMPROVEMENT')

  def test_summary_empty(self):
    self.assertIsNone(a.stats([])['median'])

  def test_quantiles_deterministic(self):
    self.assertEqual(a.stats([0.0, 1.0, 2.0]), a.stats([2.0, 0.0, 1.0]))

  def test_no_input_mutation(self):
    t = self.trace()
    old = copy.deepcopy(t)
    a.at_distance(t, 5.0, a.BASIS)
    self.assertEqual(t, old)

  def test_firewall(self):
    r = a.seal({'schema': 'TEST'})
    for k in a.FIREWALL:
      self.assertIs(r[k], False)
    self.assertIsNone(r['total_physical_bound_m'])
    self.assertEqual(r['sealed_reference'], 'NOT_GENERATED')

  def test_frozen_magnitude_split(self):
    self.assertEqual(a.curvature_bucket(0.0), 'ZERO')
    self.assertEqual(a.curvature_bucket(0.0005), 'GENTLE')
    self.assertEqual(a.curvature_bucket(0.000501), 'SHARP')
