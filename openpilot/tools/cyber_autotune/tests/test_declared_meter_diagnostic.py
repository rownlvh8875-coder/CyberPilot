import unittest
import numpy as np

from openpilot.tools.cyber_autotune import declared_meter_diagnostic as m
from openpilot.tools.cyber_autotune import approximate_geometry_diagnostic as a
from openpilot.tools.cyber_autotune import qcamera_pixel_registration as q


class TestDeclaredMeterDiagnostic(unittest.TestCase):
  def test_frozen_policy(self):
    p = m.policy()
    self.assertEqual(p['height_grid_m'], [1.33, 1.35, 1.375, 1.4, 1.425, 1.45, 1.47])
    self.assertEqual(p['physical_observation_height_m'], 1.385)
    self.assertEqual(p['original_matrix_rows'], 84)
    self.assertEqual(p['original_orientation_rows'], 24)
    self.assertFalse(p['hypotheses_exhaustive'])

  def test_all_three_mappings(self):
    ts = m.transforms()
    self.assertEqual(set(ts), set(q.RULES))
    for rule, v in ts.items():
      self.assertEqual(v['affine']['resize_rule'], rule)
      self.assertFalse(v['kq']['independently_calibrated'])

  def test_scenarios_preserve_grid_and_observation(self):
    ss = m.scenarios()
    self.assertEqual(len(ss), 26)
    self.assertEqual(sum(s['height_m'] == 1.385 for s in ss), 1)
    self.assertEqual({s['height_m'] for s in ss}, set(m.policy()['height_grid_m'] + [1.385]))
    self.assertTrue(all(s['rpy_deg'][0] in [-0.5, 0, 0.5] for s in ss))

  def test_mapping_inverse_and_k(self):
    for t in m.transforms().values():
      uv = np.array([[24.0, 210.0], [260.0, 300.0]])
      native = q.forward(uv, t['affine'])
      np.testing.assert_allclose(q.inverse(native, t['affine']), uv, atol=1e-12)
      kk = np.array(t['kq']['matrix'])
      np.testing.assert_allclose((uv - [kk[0, 2], kk[1, 2]]) / [kk[0, 0], kk[1, 1]], (native - [672, 380]) / 1141.5, atol=1e-12)

  def test_fixed_query_distance(self):
    for rule in q.RULES:
      for d in m.DISTANCES:
        uv = m.fixed_query(d, rule)
        x, y, status = m.project([uv], m.nominal(), rule)
        self.assertEqual(status[0], 'VALID')
        self.assertAlmostEqual(x[0], d, places=10)
        self.assertAlmostEqual(y[0], 0, places=10)

  def test_exact_zero_residual(self):
    uv = m.fixed_query(10, 'CENTER_ALIGNED')
    result = m.project_pairs([[*uv, *uv]], m.nominal(), 'CENTER_ALIGNED')
    self.assertAlmostEqual(result['lateral_residual_m'][0], 0)

  def test_projective_not_scalar(self):
    ss = m.nominal()
    ss['rpy_deg'] = [0.5, 2.34, 0.2]
    uv = m.fixed_query(10, 'ZERO_ORIGIN')
    pair = [*uv, uv[0] + 5, uv[1] + 2]
    p = m.project_pairs([pair], ss, 'ZERO_ORIGIN')
    self.assertGreater(p['lateral_residual_m'][0], 0)
    self.assertNotAlmostEqual(p['human_forward_m'][0], p['detector_forward_m'][0])

  def test_pitch_sign_agrees_existing_adapter(self):
    uv = m.fixed_query(10, 'ZERO_ORIGIN')
    native = q.forward([uv], m.transforms()['ZERO_ORIGIN']['affine'])[0]
    k = m.K_NATIVE
    r = a.rotation(a.degrees([0, 2.34, 0.2]))
    ray = r @ np.array([(native[0] - k[0, 2]) / k[0, 0], (native[1] - k[1, 2]) / k[1, 1], 1])
    self.assertLess(ray[2], 0)

  def test_horizon_nonforward_unavailable(self):
    x, y, status = m.project([[260, 0]], m.nominal(), 'CENTER_ALIGNED')
    self.assertEqual(status[0], 'NONFORWARD_OR_HORIZON')
    self.assertTrue(np.isnan(x[0]))
    self.assertTrue(np.isnan(y[0]))

  def test_bad_points_rejected(self):
    for bad in ([[np.nan, 1]], [[1, np.inf]], [[True, 1]], [[-1, 10]], [[526, 10]]):
      with self.subTest(bad=bad), self.assertRaises(ValueError):
        m.project(bad, m.nominal(), 'ZERO_ORIGIN')

  def test_fixed_query_may_be_subpixel(self):
    self.assertTrue(np.isfinite(m.fixed_query(30, 'CORNER_ALIGNED')).all())

  def test_distance_accounting(self):
    xs = [4.9, 5, 7.5, 12.5, 17.5, 22.5, 27.5, 30, 30.1]
    b = m.distance_bins(xs)
    self.assertEqual(b.tolist(), [-1, 0, 1, 2, 3, 4, 5, 5, -1])

  def test_empty_distribution(self):
    self.assertEqual(m.distribution([]), {'count': 0, 'median': None, 'p90': None, 'p95': None, 'maximum': None})

  def test_statistics_deterministic(self):
    self.assertEqual(m.distribution([1, 2, 3]), m.distribution([3, 1, 2]))
    self.assertEqual(m.distribution([1, 2, 3])['p95'], 2.9)

  def test_analytic_distribution(self):
    r = m.analytic([1.0, 5.0], 10, m.nominal(), 'ZERO_ORIGIN')
    self.assertEqual(r['lateral_m']['count'], 2)
    self.assertGreater(r['lateral_m']['p95'], r['lateral_m']['median'])
    self.assertEqual(r['residual_semantics'], 'ABSOLUTE_X_MAGNITUDE_BOTH_SIGNS_MAX_PINHOLE_CONDITIONAL')

  def test_fixed_distance_height_scaling(self):
    base = m.analytic([5.0], 10, m.nominal(), 'ZERO_ORIGIN')['lateral_m']['median']
    other = m.nominal()
    other['height_m'] = 1.47
    value = m.analytic([5.0], 10, other, 'ZERO_ORIGIN')['lateral_m']['median']
    self.assertAlmostEqual(value / base, 1.47 / 1.385, places=10)

  def test_no_default_mapping(self):
    with self.assertRaises(ValueError):
      m.fixed_query(10, 'ACTUAL')

  def test_wrong_scenario_rejected(self):
    ss = m.nominal()
    ss['height_m'] = 0
    with self.assertRaises(ValueError):
      m.project([[260, 200]], ss, 'ZERO_ORIGIN')

  def test_result_firewall(self):
    x = m.output({'status': 'CONDITIONAL_DIAGNOSTIC_COMPLETE'})
    for k in q.FLAGS:
      self.assertIs(x[k], False)
    self.assertIsNone(x['total_physical_bound_m'])
    self.assertIsNone(x['actual_forward_mapping'])
    self.assertIsNone(x['actual_qcamera_intrinsics'])

  def test_firewall_cannot_override(self):
    x = m.output({'qualification_allowed': True, 'total_physical_bound_m': 0})
    self.assertIs(x['qualification_allowed'], False)
    self.assertIsNone(x['total_physical_bound_m'])

  def test_distortion_open(self):
    self.assertIn('DISTORTION_CONTRIBUTION_UNBOUNDED_OR_PENDING', m.OPEN_TERMS)

  def test_no_mapping_bound(self):
    self.assertIsNone(m.output({})['pixel_mapping_bound_native_px'])
    self.assertFalse(m.policy()['hypotheses_exhaustive'])

  def test_summary_coverage(self):
    uv = m.fixed_query(10, 'ZERO_ORIGIN')
    pairs = [[uv[0], uv[1], uv[0] + 5, uv[1]], [260, 0, 261, 0]]
    p = m.project_pairs(pairs, m.nominal(), 'ZERO_ORIGIN')
    s = m.summarize(p)
    self.assertEqual(s['total_candidate_points'], 2)
    self.assertEqual(s['nonforward_horizon'], 1)
    self.assertEqual(s['valid_in_domain'], 1)
    self.assertEqual(s['bins'][1]['lateral_m']['count'], 1)

  def test_empty_projection(self):
    p = m.project_pairs([], m.nominal(), 'ZERO_ORIGIN')
    self.assertEqual(m.summarize(p)['total_candidate_points'], 0)

  def test_no_total_physical_bound_label(self):
    p = m.policy()
    self.assertEqual(p['bound_scope'], 'CONSERVATIVE_ACROSS_DECLARED_SAMPLED_HYPOTHESES_ONLY')
    self.assertIsNone(m.output({})['independent_meter_result'])

  def test_nominal_pose_provenance(self):
    s = m.nominal()
    self.assertEqual(s['rpy_deg'], [0, 2.34, 0.2])
    self.assertEqual(s['height_m'], 1.385)
    self.assertIsNone(m.policy()['measurement_uncertainty'])

  def test_road_origin_and_units(self):
    p = m.policy()
    self.assertEqual(p['road_axes'], 'X_FORWARD_Y_LEFT_Z_UP_ASSUMED_FLAT')
    self.assertEqual(p['distances_m'], [5, 10, 15, 20, 25, 30])

  def test_intrinsics_candidate_source(self):
    self.assertEqual(m.policy()['intrinsics_role'], 'STATIC_INTRINSICS_PRIOR')
    np.testing.assert_array_equal(m.K_NATIVE, [[1141.5, 0, 672], [0, 1141.5, 380], [0, 0, 1]])

  def test_sweep_not_physical_uncertainty(self):
    self.assertEqual(m.policy()['height_range_role'], 'HISTORICAL_DIAGNOSTIC_HEIGHT_SENSITIVITY_RANGE')
    self.assertIsNone(m.policy()['measurement_uncertainty'])

  def test_bin_coverage_denominator_separate_from_error(self):
    uv = m.fixed_query(10, 'ZERO_ORIGIN')
    bad = [uv[0], uv[1], 260, 0]
    p = m.project_pairs([[*uv, *uv], bad], m.nominal(), 'ZERO_ORIGIN')
    b = m.summarize(p)['bins'][1]
    self.assertEqual(b['candidate_count'], 2)
    self.assertEqual(b['lateral_m']['count'], 1)
    self.assertEqual(b['unavailable_count'], 1)
    self.assertEqual(b['unavailable_rate'], 0.5)


if __name__ == '__main__':
  unittest.main()
