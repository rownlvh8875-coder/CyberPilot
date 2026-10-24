import copy
import unittest

from openpilot.tools.cyber_autotune import trajectory_v0_screen as s
from openpilot.tools.cyber_autotune import trajectory_v0_metrics as m


class TestTrajectoryScreen(unittest.TestCase):
  def test_scenario_policy_exact(self):
    rows = s.scenarios()
    self.assertEqual(len(rows), 11)
    self.assertTrue(all(len(r) == 800 for r in rows.values()))

  def test_unknown_scenario(self):
    with self.assertRaises(ValueError):
      s.run_arm('NEW', 'DISABLED')

  def test_unauthorized_role(self):
    with self.assertRaises(ValueError):
      s.authorize('FROZEN_EVALUATION')

  def test_search(self):
    with self.assertRaises(ValueError):
      s.authorize('SEARCH')

  def test_sg(self):
    with self.assertRaises(ValueError):
      s.authorize('DEVELOPMENT_SCREEN', sg_enabled=True)

  def test_composition(self):
    with self.assertRaises(ValueError):
      s.authorize('DEVELOPMENT_SCREEN', composition=True)

  def test_straight_control(self):
    result = s.run_arm('straight', 'CANONICAL_V0')
    self.assertTrue(all(r['requested'] == 0. for r in result))

  def test_repeat_exact(self):
    self.assertEqual(s.run_arm('gentle_left', 'CANONICAL_V0'), s.run_arm('gentle_left', 'CANONICAL_V0'))

  def test_disabled_current_alias(self):
    a = s.run_arm('gentle_left', 'DISABLED')
    b = s.run_arm('gentle_left', 'CURRENT_ALIAS')
    self.assertEqual(a, b)

  def test_unknown_config(self):
    with self.assertRaises(ValueError):
      s.run_arm('straight', 'SCALE')

  def test_side_mirror(self):
    a = s.run_arm('gentle_left', 'CANONICAL_V0')
    b = s.run_arm('gentle_right', 'CANONICAL_V0')
    for x, y in zip(a, b, strict=True):
      self.assertAlmostEqual(x['requested'], -y['requested'], places=14)
      self.assertAlmostEqual(x['pose_y'], -y['pose_y'], places=14)

  def test_driver_reset_events(self):
    result = s.run_arm('driver_events', 'CANONICAL_V0')
    events = {e for r in result for e in r['reset_events']}
    self.assertTrue({'STEERING_PRESSED', 'RELEASE', 'INACTIVE', 'REENGAGEMENT'} <= events)

  def test_closed_loop_feedback_is_causal(self):
    result = s.run_arm('gentle_left', 'CANONICAL_V0')
    for a, b in zip(result, result[1:], strict=False):
      self.assertEqual(a['curvature'], b['input']['actual_curvature_1pm'])


class TestTrajectoryMetrics(unittest.TestCase):
  def test_empty_null(self):
    self.assertIsNone(m.distribution([], 5)['p95'])

  def test_unavailable_accounting(self):
    self.assertEqual(m.distribution([1., 2.], 5)['unavailable'], 3)

  def test_quantiles_deterministic(self):
    self.assertEqual(m.distribution([1., 2., 3.], 3), m.distribution([3., 2., 1.], 3))

  def test_distribution_finite(self):
    with self.assertRaises(ValueError):
      m.distribution([float('nan')], 1)

  def test_no_extrapolation(self):
    self.assertIsNone(m.distance_value([{'pose_x': 1., 'pose_y': 2.}], 5., 'pose_y'))

  def test_interpolation(self):
    rows = [{'pose_x': 0., 'pose_y': 0.}, {'pose_x': 10., 'pose_y': 2.}]
    self.assertEqual(m.distance_value(rows, 5., 'pose_y'), 1.)

  def test_nonmonotonic_distance(self):
    rows = [{'pose_x': 10., 'pose_y': 0.}, {'pose_x': 0., 'pose_y': 2.}]
    self.assertIsNone(m.distance_value(rows, 5., 'pose_y'))

  def test_constant_lag_unavailable(self):
    self.assertIsNone(m.lag([0.]*10, [0.]*10)['lag_s'])

  def test_known_lag(self):
    self.assertEqual(m.lag([0., 1., 0., -1., 0., 0.], [0., 0., 1., 0., -1., 0.])['lag_s'], .01)

  def test_mask_separation(self):
    rows = s.run_arm('driver_events', 'CANONICAL_V0')
    report = m.evaluate(rows)
    self.assertLess(report['trajectory']['tracking']['n'], len(rows))
    self.assertGreater(report['trajectory']['tracking']['unavailable'], 0)

  def test_no_weighted_score(self):
    report = m.evaluate(s.run_arm('straight', 'CANONICAL_V0'))
    self.assertEqual(set(report), {'trajectory', 'smoothness', 'coverage'})

  def test_negative_control_effect(self):
    rows = s.run_arm('straight', 'DISABLED')
    self.assertEqual(m.effects(rows, copy.deepcopy(rows))['states'], ['NO_OUTPUT_DIFFERENCE'])

  def test_positive_control_detected(self):
    baseline = s.run_arm('gentle_left', 'DISABLED')
    ta = s.run_arm('gentle_left', 'CANONICAL_V0')
    self.assertIn('REQUESTED_OUTPUT_DIFFERENCE_PRESENT', m.effects(baseline, ta)['states'])

class TestReviewRegressions(unittest.TestCase):
  def test_press_window_mask_and_support(self):
    r = m.evaluate(s.run_arm('driver_events', 'CANONICAL_V0'))
    event = next(v for v in r['smoothness']['event_transients'] if v['event'] == 'STEERING_PRESSED')
    self.assertEqual(event['peak_support']['valid'], 100)
    self.assertEqual(event['requested_derivative']['n'], 0)
    self.assertEqual(event['boundary_jump_status'], 'OUTSIDE_FROZEN_DERIVATIVE_ESTIMATOR_SUPPORT')
    self.assertIsNotNone(event['requested_before_event'])

  def test_release_boundary_disclosed(self):
    r = m.evaluate(s.run_arm('driver_events', 'CANONICAL_V0'))
    for event in r['smoothness']['event_transients']:
      self.assertIn('OUTSIDE', event['boundary_jump_status'])

  def test_unsaturated_is_not_missing(self):
    r = m.evaluate(s.run_arm('straight', 'CANONICAL_V0'))
    sat = r['trajectory']['saturation_tracking_loss']
    self.assertEqual(sat['unavailable'], 0)
    self.assertEqual(sat['conditioning']['unsaturated'], 800)
    self.assertEqual(sat['conditioning']['observation_unavailable'], 0)

  def test_phase_coverage_disclosed(self):
    r = m.evaluate(s.run_arm('gentle_left', 'CANONICAL_V0'))
    for phase in r['trajectory']['phases'].values():
      self.assertIn('coverage', phase)
      self.assertIn('requested_derivative_abs', phase)
      self.assertIn('saturation_support', phase)

  def test_support_hash_binding(self):
    b = s.binding()
    self.assertIn('openpilot/common/filter_simple.py', b['executed_support_sha256'])

class TestMetricTimebaseRegressions(unittest.TestCase):
  def test_adjacent_indices_time_gap_split(self):
    rows = s.run_arm('straight', 'DISABLED')[:3]
    for i, r in enumerate(rows):
      r['input']['time_s'] = i*.02
    self.assertEqual([len(v) for v in m.segments(rows)], [1, 1, 1])
    self.assertEqual(m.derivative(m.segments(rows), 'requested'), [])

  def test_wrong_dt_rejected(self):
    rows = s.run_arm('straight', 'DISABLED')[:3]
    rows[1]['input']['dt_s'] = .02
    with self.assertRaises(ValueError):
      m.evaluate(rows)

  def test_nonfinite_rows_rejected(self):
    rows = s.run_arm('straight', 'DISABLED')[:3]
    rows[1]['requested'] = float('nan')
    with self.assertRaises(ValueError):
      m.evaluate(rows)

  def test_executed_support_drift(self):
    from unittest.mock import patch
    original = s.digest
    with patch.object(s, 'digest', side_effect=lambda payload: original(payload)+('0' if b'class FirstOrderFilter' in payload else '')):
      changed = s.binding()
    self.assertNotEqual(changed['native_software_sha256'], s.binding()['native_software_sha256'])

class TestIdentityAndControls(unittest.TestCase):
  def test_binding_rejection(self):
    bad = s.binding()
    bad['executed_support_sha256']['openpilot/common/filter_simple.py'] = '0'*64
    with self.assertRaisesRegex(ValueError, 'DRIFT'):
      s.verify_binding(bad)

  def test_alias_identity(self):
    b = s.binding()
    self.assertEqual(s.arm_identity('DISABLED', b), s.arm_identity('CURRENT_ALIAS', b))

  def test_ta_identity_distinct(self):
    b = s.binding()
    self.assertNotEqual(s.arm_identity('DISABLED', b), s.arm_identity('CANONICAL_V0', b))

  def test_control_scope(self):
    self.assertTrue(all(s.positive_controls()['checks'].values()))
    self.assertEqual(s.positive_controls()['scope'], 'TEST_ONLY_NOT_CANDIDATE_PERFORMANCE')

  def test_no_bytecode_context_rejected(self):
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as folder, self.assertRaisesRegex(ValueError, 'SOURCE_ONLY'):
      s.execute(folder)
