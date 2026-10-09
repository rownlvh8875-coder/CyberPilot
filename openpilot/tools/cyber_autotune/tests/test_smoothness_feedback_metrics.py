from copy import deepcopy
import unittest

from openpilot.tools.cyber_autotune import smoothness_feedback_metrics as m
from openpilot.tools.cyber_autotune import smoothness_closed_loop as s


class TestFeedbackDiagnostics(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.rows = s.run_arm('straight', s.ARMS[2])

  def test_source_bound_contains_zero(self):
    self.assertTrue(m.containment(self.rows)['all_within_source_envelope'])

  def test_nonfinite_rejected(self):
    rows = deepcopy(self.rows)
    rows[0]['curvature'] = float('nan')
    with self.assertRaises(ValueError):
      m.containment(rows)

  def test_impossible_curvature_rejected(self):
    rows = deepcopy(self.rows)
    rows[0]['curvature'] = 1e6
    with self.assertRaises(ValueError):
      m.containment(rows)

  def test_finite_native_state(self):
    self.assertTrue(m.diagnostics(self.rows)['native_state_all_finite'])

  def test_quarter_support(self):
    d = m.blocks(self.rows)
    self.assertEqual([r['support'] for r in d['quarters']], [200] * 4)

  def test_constant_tail_support(self):
    d = m.blocks(self.rows)
    self.assertEqual([r['support'] for r in d['constant_demand_tail']], [100] * 3)

  def test_zero_rms(self):
    self.assertEqual(m.blocks(self.rows)['quarters'][0]['curvature']['rms'], 0.)

  def test_not_proven_stable(self):
    self.assertFalse(m.diagnostics(self.rows)['stability_proof'])

  def test_no_growth_for_zero(self):
    self.assertFalse(m.blocks(self.rows)['tail_growth']['curvature'])

  def test_unequal_demand_not_growth_evidence(self):
    rows = deepcopy(self.rows)
    rows[100]['input']['desired_curvature_1pm'] = .01
    self.assertIsNone(m.blocks(rows)['quarter_growth']['curvature'])

  def test_growth_accounting(self):
    series = [{'input': r['input'], 'curvature': float(i // 100 + 1)} for i, r in enumerate(self.rows[-300:])]
    self.assertTrue(m.equivalent_growth([series[:100], series[100:200], series[200:]], 'curvature'))

  def test_missing_distance_disclosed(self):
    rows = deepcopy(self.rows[:10])
    self.assertEqual(m.pose_alignment(rows, rows)['queries']['5']['reason'], 'DISTANCE_NOT_REACHED')

  def test_nonmonotone_distance_disclosed(self):
    rows = deepcopy(self.rows)
    rows[20]['pose_x'] = -1.
    self.assertEqual(m.pose_alignment(rows, rows)['queries']['5']['reason'], 'NONMONOTONE_FORWARD_COORDINATE')

  def test_no_extrapolation(self):
    d = m.pose_alignment(self.rows[:10], self.rows[:10])
    self.assertIsNone(d['queries']['30']['delta_pose_y_m'])

  def test_zero_divergence(self):
    markers = m.markers(self.rows, self.rows)
    self.assertTrue(all(v is None for v in markers.values()))

  def test_first_pre_post_divergence(self):
    rows = deepcopy(self.rows)
    rows[20]['pre'] = .5
    rows[22]['curvature'] = .001
    markers = m.markers(self.rows, rows)
    self.assertEqual(markers['core_requested_torque']['index'], 20)
    self.assertEqual(markers['plant_curvature_post']['index'], 22)

  def test_unknown_distances_not_meter_classified(self):
    self.assertFalse(m.pose_alignment(self.rows, self.rows)['meter_envelope_classification'])

  def test_null_metric_delta(self):
    self.assertIsNone(m.delta(None, .2))

  def test_metric_delta(self):
    self.assertEqual(m.delta(.5, .25), .25)

  def test_stability_scope(self):
    self.assertEqual(m.diagnostics(self.rows)['scope'], 'FINITE_HORIZON_CLOSED_LOOP_STABILITY_DIAGNOSTIC')


class TestInteractionPolicy(unittest.TestCase):
  def interaction(self, baseline, replay, closed, phase_cost=0.):
    return {'metric_table': {'curvature_tracking_p95':
              {'baseline_closed_loop': baseline, 'sg_frozen_replay': replay, 'sg_closed_loop': closed}},
            'phase_lag_vs_baseline': {'APEX': {'closed_loop_lag_segments':
              [{'status': 'IDENTIFIED_DESCRIPTIVE', 'lag_s': phase_cost, 'pairs': 100}],
              'replay_lag_segments': [{'status': 'IDENTIFIED_DESCRIPTIVE', 'lag_s': 0., 'pairs': 100}]}},
            'phase_lag_vs_replay': {'APEX': {'closed_loop_lag_segments':
              [{'status': 'IDENTIFIED_DESCRIPTIVE', 'lag_s': phase_cost, 'pairs': 100}],
              'replay_lag_segments': [{'status': 'IDENTIFIED_DESCRIPTIVE', 'lag_s': 0., 'pairs': 100}]}},
            'closed_signal_chain_exact_baseline': False,
            'same_time_peak_pose_difference_m': {'closed_loop_vs_baseline': 1., 'frozen_replay_vs_baseline': 2.}}

  def test_compensates(self):
    self.assertEqual(m.classify_interaction(self.interaction(2., 3., 1.)), 'FEEDBACK_COMPENSATES_GOVERNOR_LAG')

  def test_preserves(self):
    self.assertEqual(m.classify_interaction(self.interaction(2., 4., 3.)), 'FEEDBACK_PRESERVES_GOVERNOR_TRADEOFF')

  def test_amplifies(self):
    self.assertEqual(m.classify_interaction(self.interaction(1., 2., 3.)), 'FEEDBACK_AMPLIFIES_GOVERNOR_TRADEOFF')

  def test_contradictory_phase_is_mixed(self):
    self.assertEqual(m.classify_interaction(self.interaction(2., 3., 1., .1)), 'MIXED_OR_UNRESOLVED')

  def test_ambiguous_phase_not_assumed(self):
    row = self.interaction(2., 3., 1.)
    row['phase_lag_vs_baseline']['APEX']['closed_loop_lag_segments'][0]['status'] = 'AMBIGUOUS_TIE'
    self.assertEqual(m.classify_interaction(row), 'MIXED_OR_UNRESOLVED')

  def test_no_coverage_no_claim(self):
    self.assertEqual(m.classify_interaction(self.interaction(2., 3., None)), 'MIXED_OR_UNRESOLVED')

  def test_replay_artifact_requires_exact_zero(self):
    row = self.interaction(2., 3., 2.)
    row['same_time_peak_pose_difference_m']['closed_loop_vs_baseline'] = 0.
    row['closed_signal_chain_exact_baseline'] = True
    self.assertEqual(m.classify_interaction(row), 'FROZEN_REPLAY_ARTIFACT_DOMINANT')


class TestScreeningClaim(unittest.TestCase):
  def record(self):
    keys = ('requested_derivative_p95', 'requested_derivative_rms', 'applied_derivative_p95', 'applied_derivative_rms',
            'reversals', 'high_frequency_energy', 'total_variation', 'output_saturation_occupancy',
            'curvature_tracking_p95', 'pose_y_absolute_peak_m')
    table = {k: {'closed_minus_baseline': 0.} for k in keys}
    phase = {'ENTRY': {'closed_loop_lag_segments': [{'status': 'IDENTIFIED_DESCRIPTIVE', 'lag_s': .01, 'pairs': 100}],
                       'replay_lag_segments': [{'status': 'IDENTIFIED_DESCRIPTIVE', 'lag_s': .01, 'pairs': 100}]}}
    return {'interaction': {'metric_table': table, 'phase_lag_vs_baseline': phase,
            'coverage': {'sg_closed_loop': {'eligible': 800}, 'baseline_closed_loop': {'eligible': 800}}}}

  def test_pose_only_not_improvement(self):
    row = self.record()
    row['interaction']['metric_table']['pose_y_absolute_peak_m']['closed_minus_baseline'] = -1.
    self.assertNotEqual(m.standalone_verdict([row]), 'SG_CLOSED_LOOP_SCREENING_IMPROVED')

  def test_missing_scalar_not_improvement(self):
    row = self.record()
    row['interaction']['metric_table']['requested_derivative_p95']['closed_minus_baseline'] = -.1
    row['interaction']['metric_table']['applied_derivative_rms']['closed_minus_baseline'] = None
    self.assertNotEqual(m.standalone_verdict([row]), 'SG_CLOSED_LOOP_SCREENING_IMPROVED')

  def test_missing_lag_not_improvement(self):
    row = self.record()
    row['interaction']['metric_table']['requested_derivative_p95']['closed_minus_baseline'] = -.1
    row['interaction']['phase_lag_vs_baseline'] = {}
    self.assertNotEqual(m.standalone_verdict([row]), 'SG_CLOSED_LOOP_SCREENING_IMPROVED')

  def test_phase_support_loss_not_improvement(self):
    row = self.record()
    row['interaction']['metric_table']['requested_derivative_p95']['closed_minus_baseline'] = -.1
    row['interaction']['phase_lag_vs_baseline']['ENTRY']['closed_loop_lag_segments'][0]['pairs'] = 99
    self.assertNotEqual(m.standalone_verdict([row]), 'SG_CLOSED_LOOP_SCREENING_IMPROVED')

  def test_actual_supported_benefit(self):
    row = self.record()
    row['interaction']['metric_table']['requested_derivative_p95']['closed_minus_baseline'] = -.1
    self.assertEqual(m.standalone_verdict([row]), 'SG_CLOSED_LOOP_SCREENING_IMPROVED')


class TestStageTimestamps(unittest.TestCase):
  def test_post_state_not_command_time(self):
    row = {'input': {'time_s': .2, 'actual_curvature_1pm': 0., 'desired_curvature_1pm': 0.},
           'pre': 0., 'requested': 0., 'applied': 0., 'curvature': 0., 'pose_y': 0.}
    modified = deepcopy(row)
    modified['curvature'] = .1
    result = m.markers([row] * 20 + [row], [row] * 20 + [modified])['plant_curvature_post']
    self.assertEqual(result['sample_time_s'], .2)
    self.assertEqual(result['observed_state_time_s'], .21)

  def test_command_timestamp(self):
    row = {'input': {'time_s': 0., 'actual_curvature_1pm': 0., 'desired_curvature_1pm': 0.},
           'pre': 0., 'requested': 0., 'applied': 0., 'curvature': 0., 'pose_y': 0.}
    modified = deepcopy(row)
    modified['pre'] = .1
    result = m.markers([row], [modified])['core_requested_torque']
    self.assertEqual(result['sample_time_s'], 0.)
    self.assertIsNone(result['observed_state_time_s'])
