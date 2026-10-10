"""Synthetic attribution tests never open private driving data."""

import unittest
import numpy as np
from openpilot.tools.cyber_autotune import empirical_stage_a_regime as r


class TestRegime(unittest.TestCase):
  def test_grid_float32(self):
    x = np.array([0, 0.1, -0.2], dtype=np.float32).astype(float)
    out = r.grid(x, 0.1, 0)
    self.assertEqual(out['float32_tolerant_grid_count'], 3)
    self.assertEqual(out['off_grid_count'], 0)

  def test_off_grid_not_rounded(self):
    x = np.array([0.123])
    self.assertEqual(r.grid(x, 0.1, 0)['off_grid_count'], 1)
    self.assertEqual(x[0], 0.123)

  def test_conflicting_quantization(self):
    with self.assertRaisesRegex(ValueError, 'QUANTIZATION_CONFLICT'):
      r.require_quantization([{'step_deg': 0.1, 'offset_deg': 0, 'sign': 1}, {'step_deg': 0.2, 'offset_deg': 0, 'sign': 1}])

  def test_empty_grid(self):
    self.assertIsNone(r.grid(np.array([]), 0.1, 0)['residual']['p95'])

  def test_nonfinite(self):
    with self.assertRaises(ValueError):
      r.analyze(np.array([[np.nan, 0, 0, 0, 0]]), 0.1, 0)

  def test_wrong_schema(self):
    with self.assertRaises(ValueError):
      r.analyze(np.zeros((3, 4)), 0.1, 0)

  def test_selected_predictions_only(self):
    out, paired = r.analyze(np.array([[0, 0.02, 0, 0, 3], [0.1, 0.08, 0, 0, 3]]), 0.1, 0)
    self.assertEqual(out['all']['count'], 2)
    np.testing.assert_equal(paired[:, 0], [abs(0.02 - 0), abs(0.08 - 0.1)])

  def test_outcome_partition(self):
    q = np.array([0, 0.1, 0.3], dtype=np.float32).astype(float)
    out, _ = r.analyze(np.column_stack([q, q, q * 0, q * 0, q * 0]), 0.1, 0)
    self.assertEqual([out['outcome'][x]['count'] for x in r.PARTITION], [1, 1, 1])

  def test_sign_reversal_overlap(self):
    out, _ = r.analyze(np.array([[-0.1, 0, 0, 0.1, 0]]), 0.1, 0)
    self.assertEqual(out['outcome']['TARGET_SIGN_REVERSAL']['count'], 1)
    self.assertEqual(out['outcome']['TARGET_MULTI_QUANTUM_CHANGE']['count'], 1)

  def test_contribution_reconstruction(self):
    a = np.array([[0, 0.02, 0, 0, 0], [0.1, 0.08, 0, 0, 0], [0.3, 0.2, 0, 0, 0]])
    out, _ = r.analyze(a, 0.1, 0)
    for field in ('mae_difference_contribution', 'mse_difference_contribution', 'rmse_difference_contribution'):
      self.assertAlmostEqual(sum(out['outcome'][x][field] for x in r.PARTITION), out['all'][field])

  def test_zero_rmse_denominator(self):
    out, _ = r.analyze(np.zeros((2, 5)), 0.1, 0)
    self.assertEqual(out['all']['rmse_difference_contribution'], 0)

  def test_win_tie_loss(self):
    out, _ = r.analyze(np.array([[0, 0, 0, 0, 0], [1, 1, 0, 0, 0], [0, 1, 0, 0, 0]]), 0.1, 0)
    self.assertEqual(out['all']['win_tie_loss'], {'win': 1, 'tie': 1, 'loss': 1})

  def test_no_optimized_boundary(self):
    self.assertEqual(r.CAUSAL_BOUNDARY, 'SOURCE_HALF_QUANTUM_PREDICTION_MOVEMENT')

  def test_causal_condition_ignores_future_target(self):
    a = np.array([[0, 0.08, 0, 0, 0], [1, 0.01, 0, 0, 0]])
    b = a.copy()
    b[:, 0] = [100, -100]
    np.testing.assert_equal(r.causal_masks(a, 0.1), r.causal_masks(b, 0.1))

  def test_outcome_gate_forbidden(self):
    with self.assertRaisesRegex(ValueError, 'OUTCOME_GATE_FORBIDDEN'):
      r.authorize_gate('TARGET_UNCHANGED')

  def test_unknown_causal_gate(self):
    with self.assertRaises(ValueError):
      r.authorize_gate('OPTIMAL_COMMAND_THRESHOLD')

  def test_unpreserved_fields(self):
    for key in ('RAW_COMMAND_CHANGED', 'CURRENT_STEERING_RATE_NONZERO', 'CURRENT_MEASURED_ANGLE_CHANGED'):
      self.assertEqual(r.availability()[key]['status'], 'UNAVAILABLE')

  def test_no_combination_search(self):
    with self.assertRaises(ValueError):
      r.authorize_gate(['RAW_COMMAND_CHANGED', r.CAUSAL_BOUNDARY])

  def test_equal_route_not_sample_weighted(self):
    rows = [
      {'all': {'count': 100, 'mae_difference_contribution': 1, 'mse_difference_contribution': 1, 'rmse_difference_contribution': 1}},
      {'all': {'count': 1, 'mae_difference_contribution': -1, 'mse_difference_contribution': -1, 'rmse_difference_contribution': -1}},
    ]
    out = r.aggregate(rows)
    self.assertEqual(out['equal_route']['mae_difference_contribution'], 0)
    self.assertGreater(out['sample_weighted_supporting']['mae_difference_contribution'], 0)

  def test_no_supported_causal_claim_on_low_support(self):
    fake = {'count': 1, 'arx': {'MAE': 0, 'RMSE': 0, 'P95_ABS': 0}, 'hold_last': {'MAE': 1, 'RMSE': 1, 'P95_ABS': 1}}
    self.assertFalse(r.causal_gate_supported([{'causal': {'MOVEMENT_AT_LEAST_HALF_QUANTUM': fake, 'MOVEMENT_BELOW_HALF_QUANTUM': fake}}] * 6))

  def test_v4_nonexecuting(self):
    row = r.architecture_contract('QUANTIZATION_AWARE_OBSERVATION_REVIEW_POSSIBLE', 'a' * 64)
    for k in ('actual_algorithm_implemented', 'model_fitted', 'execution_allowed', 'search_allowed'):
      self.assertIs(row[k], False)
    self.assertEqual(row['rounding_rule'], 'NOT_SELECTED')

  def test_v4_rejects_unsupported_verdict(self):
    with self.assertRaises(ValueError):
      r.architecture_contract('STAGE_A_ATTRIBUTION_MIXED_OR_UNRESOLVED', 'a' * 64)

  def test_exact_repeat(self):
    a = np.array([[0, 0.02, 0, 0, 0], [0.1, 0.08, 0, 0, 0]])
    x, p = r.analyze(a, 0.1, 0)
    y, q = r.analyze(a, 0.1, 0)
    self.assertEqual(x, y)
    np.testing.assert_array_equal(p, q)


class TestInterpretation(unittest.TestCase):
  def rows(self):
    # Unchanged small errors cost MAE; a multi-quantum transition saves MSE.
    one = np.array([[0, 0.001, 0, 0, 0]] * 300 + [[1, 1, 0, 0, 0]] * 201)
    out, _ = r.analyze(one, 0.1, 0)
    import copy

    return [copy.deepcopy(out) for _ in range(6)]

  def test_quantization_review_requires_each_route_bin(self):
    self.assertEqual(r.adjudicate(self.rows())['verdict'], 'QUANTIZATION_AWARE_OBSERVATION_REVIEW_POSSIBLE')

  def test_one_conflicting_grid_blocks(self):
    rows = self.rows()
    import copy

    rows = copy.deepcopy(rows)
    rows[0]['target_grid']['off_grid_count'] = 1
    self.assertEqual(r.adjudicate(rows)['verdict'], 'STAGE_A_ATTRIBUTION_BLOCKED_SOURCE_CONFLICT')

  def test_inconsistent_route_not_promoted(self):
    rows = self.rows()
    import copy

    rows = copy.deepcopy(rows)
    rows[0]['outcome']['TARGET_MULTI_QUANTUM_CHANGE']['mse_difference_contribution'] = 1
    self.assertNotEqual(r.adjudicate(rows)['verdict'], 'QUANTIZATION_AWARE_OBSERVATION_REVIEW_POSSIBLE')

  def test_six_scope_requirement(self):
    self.assertFalse(r.adjudicate(self.rows()[:5])['hypotheses']['H1'])

  def test_equal_route_regime_metric(self):
    rows = self.rows()[:2]
    out = r.aggregate(rows)
    self.assertEqual(out['regimes']['outcome']['TARGET_UNCHANGED']['equal_route_metrics']['arx']['MAE'], rows[0]['outcome']['TARGET_UNCHANGED']['arx']['MAE'])

  def test_nonempty_float_tolerance_not_tuned(self):
    source = np.array([0.1], dtype=np.float32).astype(float)
    shifted = source + 1e-4
    self.assertEqual(r.grid(shifted, 0.1, 0)['off_grid_count'], 1)

  def test_half_quantum_boundary_inclusive(self):
    a = np.array([[0, 0.05, 0, 0, 0], [0, 0.049, 0, 0, 0]])
    np.testing.assert_array_equal(r.causal_masks(a, 0.1), [True, False])

  def test_exact_zero_no_epsilon(self):
    a = np.array([[1e-12, 0, 0, 0, 0]])
    out, _ = r.analyze(a, 0.1, 0)
    self.assertEqual(out['outcome']['TARGET_UNCHANGED']['count'], 0)
    self.assertEqual(out['outcome']['TARGET_OFF_GRID_OR_SUBQUANTUM_CHANGE']['count'], 1)

  def test_empty_subgroup_metrics_unavailable(self):
    out, _ = r.analyze(np.zeros((3, 5)), 0.1, 0)
    self.assertIsNone(out['outcome']['TARGET_MULTI_QUANTUM_CHANGE']['arx']['RMSE'])

  def test_overlapping_regime_not_partition(self):
    out, _ = r.analyze(np.array([[-0.1, 0, 0, 0.1, 0]]), 0.1, 0)
    self.assertNotIn('TARGET_SIGN_REVERSAL', out['partition'])

  def test_partition_includes_off_grid(self):
    out, _ = r.analyze(np.array([[0.123, 0.1, 0, 0, 0]]), 0.1, 0)
    self.assertEqual(sum(out['outcome'][k]['count'] for k in out['partition']), 1)

  def test_retrospective_no_model_admission(self):
    self.assertEqual(r.adjudicate(self.rows())['family_status'], 'NO_ADMISSIBLE_MODEL_REVIEW_ONLY')


class TestEvidenceStates(unittest.TestCase):
  def test_low_support_is_not_direction_conflict(self):
    rows = TestInterpretation().rows()
    import copy

    rows = copy.deepcopy(rows)
    rows[0]['outcome']['TARGET_MULTI_QUANTUM_CHANGE']['count'] = 1
    verdict = r.adjudicate(rows)
    self.assertFalse(verdict['hypotheses']['H6'])
    self.assertFalse(verdict['regime_support_complete'])

  def test_conflicting_direction_is_reported(self):
    rows = TestInterpretation().rows()
    import copy

    rows = copy.deepcopy(rows)
    rows[0]['outcome']['TARGET_MULTI_QUANTUM_CHANGE']['mse_difference_contribution'] = 1
    self.assertTrue(r.adjudicate(rows)['hypotheses']['H6'])
