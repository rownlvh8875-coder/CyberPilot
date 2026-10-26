"""Policy mathematics only. No actual threshold fitting or performance proxy."""

import unittest
from unittest.mock import patch

import numpy as np


class TestPolicyWitnesses(unittest.TestCase):
  def review(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_policy_review as r
    return r

  def test_joint_compensation_local_rejection(self):
    w = self.review().witnesses()['rmse_compensation']
    self.assertGreater(w['candidate_local_rmse'][0], w['reference_local_rmse'][0])
    self.assertLess(w['candidate_global_rmse'], w['reference_global_rmse'])

  def test_local_p95_pass_can_fail_pooled(self):
    w = self.review().witnesses()['pooled_p95']
    self.assertTrue(all(a <= b for a, b in zip(w['candidate_local_p95'], w['reference_local_p95'], strict=True)))
    self.assertGreater(w['candidate_pooled_p95'], w['reference_pooled_p95'])

  def test_support_weighting_reverses_two_declared_alternatives(self):
    w = self.review().witnesses()['support_weighting']
    self.assertGreater(w['population_weighted'][0], w['population_weighted'][1])
    self.assertLess(w['equal_context_weighted'][0], w['equal_context_weighted'][1])
    self.assertTrue(w['not_an_unconstrained_separable_optimum_claim'])

  def test_unconstrained_additive_counts_do_separate(self):
    r = self.review()
    self.assertEqual(r.additive_identity(((3, 7, 4), (2, 9, 1))), 16)
    self.assertEqual(r.additive_identity(((1,), (2,))), 3)

  def test_local_float_improvements_can_pool_to_equality(self):
    w = self.review().witnesses()['float_reduction']
    self.assertTrue(all(a < b for a, b in zip(w['candidate_local_mae'], w['reference_local_mae'], strict=True)))
    self.assertEqual(w['candidate_canonical_mae'], w['reference_canonical_mae'])
    self.assertLess(w['candidate_context_subtotal_mae'], w['reference_context_subtotal_mae'])

  def test_fixed_two_thresholds_sensitive_to_monotonic_shift(self):
    w = self.review().witnesses()['fixed_shift']
    self.assertNotEqual(w['original_decisions'], w['up_decisions'])
    self.assertNotEqual(w['original_decisions'], w['down_decisions'])
    self.assertEqual(w['original_order'], w['up_order'])
    self.assertEqual(w['original_order'], w['down_order'])

  def test_co_transformed_cutoffs_restore_decisions(self):
    r = self.review()
    scores = np.array([.125, .375, .625, .875])
    contexts = np.array([0, 0, 1, 1], np.uint8)
    np.testing.assert_array_equal(r.fixed_decisions(scores, contexts, (.375, .75), scope=r.SCOPE),
                                  r.fixed_decisions(scores + .125, contexts, (.5, .875), scope=r.SCOPE))

  def test_same_score_different_state_distinct_decision(self):
    r = self.review()
    got = r.fixed_decisions(np.array([.5, .5]), np.array([0, 1], np.uint8), (.25, .75), scope=r.SCOPE)
    self.assertEqual(got.tolist(), [True, False])

  def test_same_state_order_preserved_and_equality_static(self):
    r = self.review()
    got = r.fixed_decisions(np.array([.125, .375, .5, .75]), np.zeros(4, np.uint8), (.375, .75), scope=r.SCOPE)
    self.assertEqual(got.tolist(), [False, False, True, True])
    self.assertTrue(np.all(np.diff(got.astype(int)) >= 0))

  def test_state_rank_signal_unchanged_not_gate_auc_claim(self):
    w = self.review().witnesses()['fixed_shift']
    self.assertTrue(w['within_state_score_order_unchanged'])
    self.assertFalse(w['binary_gate_auc_invariance_claim'])

  def test_majority_onset_not_solved_by_continuation_alone(self):
    w = self.review().witnesses()['onset_heavy']
    self.assertGreater(w['onset_count'], w['continuation_count'])
    self.assertEqual(w['unresolved_onset_if_only_continuation_changes'], w['onset_count'])
    self.assertFalse(w['real_performance_prediction'])

  def test_proper_loss_of_fixed_scores_does_not_fit_threshold(self):
    r = self.review()
    p, labels = np.array([.25, .75]), np.array([0., 1.])
    self.assertEqual(r.fixed_score_brier(p, labels, scope=r.SCOPE), .0625)
    with self.assertRaises(TypeError):
      r.fixed_score_brier(p, labels, scope=r.SCOPE, threshold=.5)

  def test_pooled_ba_separable_but_local_ba_weights_differ(self):
    from fractions import Fraction
    # Two contexts: (P,N)=(9,1),(1,9). Declared confusion alternatives.
    a, b = ((9, 0), (0, 9)), ((7, 1), (1, 7))
    def global_ba(rows):
      tp, tn = sum(x[0] for x in rows), sum(x[1] for x in rows)
      decomposed = sum(10 * x[0] + 10 * x[1] for x in rows)
      self.assertEqual(Fraction(decomposed, 200), Fraction(tp, 20) + Fraction(tn, 20))
      return Fraction(decomposed, 200)
    def local(rows):
      return [Fraction(tp, 2 * pos) + Fraction(tn, 2 * neg) for (tp, tn), pos, neg in zip(rows, (9, 1), (1, 9), strict=True)]
    self.assertGreater(global_ba(a), global_ba(b))
    self.assertTrue(all(y > x for x, y in zip(local(a), local(b), strict=True)))

  def test_synthetic_only_and_nonfinite_rejection(self):
    r = self.review()
    for scope in ('PRIVATE', 'TRAIN', 'DEVELOPMENT', 'HOLDOUT'):
      with self.assertRaises(ValueError):
        r.fixed_decisions(np.array([.5]), np.array([0], np.uint8), (.25, .75), scope=scope)
    with self.assertRaises(ValueError):
      r.fixed_decisions(np.array([np.nan]), np.array([0], np.uint8), (.25, .75), scope=r.SCOPE)

  def test_no_loader_fit_threshold_search_rollout_or_holdout(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as old
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_two_context_exact as joint
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_two_context_oracle as oracle
    with patch('numpy.load', side_effect=AssertionError('private/HOLDOUT loader')), \
         patch.object(old, 'fit_stage1', side_effect=AssertionError('fit')), \
         patch.object(old, 'fit_stage2', side_effect=AssertionError('fit')), \
         patch.object(old, 'normalizer', side_effect=AssertionError('fit')), \
         patch.object(old, 'probability', side_effect=AssertionError('replay')), \
         patch.object(old, 'threshold', side_effect=AssertionError('threshold fit')), \
         patch.object(old, 'recursive', side_effect=AssertionError('rollout')), \
         patch.object(joint, 'fit', side_effect=AssertionError('pair search')), \
         patch.object(oracle, 'exhaustive', side_effect=AssertionError('pair search')):
      self.review().witnesses()


class TestPolicyDecision(unittest.TestCase):
  def decide(self, separable, representation, closure):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_policy_review import decide
    return decide(separable=separable, representation=representation, closure_justified=closure)

  def test_outcome_a_path(self):
    self.assertEqual(self.decide((True,) * 6, (False,) * 6, False)['outcome'], 'A')

  def test_outcome_b_requires_positive_closure_reason(self):
    self.assertEqual(self.decide((True, True, False, True, True, True), (True,) * 6, True)['outcome'], 'B')

  def test_inconclusive_unknown_not_rejection(self):
    got = self.decide((True, True, None, True, True, True), (True,) * 6, None)
    self.assertEqual(got['outcome'], 'C')
    self.assertFalse(got['two_context_track_closed'])
    self.assertTrue(got['representation_review_signal'])

  def test_computational_simplicity_cannot_decide(self):
    got = self.decide((None, True, None, True, True, True), (True,) * 6, None)
    self.assertEqual(got['outcome'], 'C')

  def test_both_supported_needs_priority_resolution(self):
    self.assertEqual(self.decide((True,) * 6, (True,) * 6, True)['outcome'], 'C')

  def test_no_representation_escalation_from_auc_cutoff(self):
    got = self.decide((None,) * 6, (True, True, True, True, True, None), None)
    self.assertFalse(got['representation_review_signal'])

  def test_invalid_schema_or_coerced_booleans_rejected(self):
    for criteria in ((1,) * 6, (True,) * 5, [True] * 6):
      with self.assertRaises(ValueError):
        self.decide(criteria, (True,) * 6, None)

  def test_decision_returns_no_model_or_policy_authority(self):
    for args in (((True,) * 6, (False,) * 6, False), ((None,) * 6, (True,) * 6, True), ((None,) * 6, (True,) * 6, None)):
      row = self.decide(*args)
      self.assertFalse(row['architecture_frozen'])
      self.assertFalse(row['fitting_policy_frozen'])
      self.assertFalse(row['actual_execution_authorized'])


class TestPublicPolicyReview(unittest.TestCase):
  def test_exact_public_input_locks_and_mutation_rejection(self):
    from tools.cyberpilot.build_hurdle_v4_policy_review import locked_inputs, PINS
    self.assertEqual(len(locked_inputs()), 16)
    key = next(iter(PINS))
    with patch.dict(PINS, {key: ('0' * 64, PINS[key][1])}), self.assertRaisesRegex(ValueError, 'INPUT_CONFLICT'):
      locked_inputs()

  def test_eleven_artifacts_match_builder_and_receipts(self):
    import json
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    from tools.cyberpilot.build_hurdle_v4_policy_review import build
    rows = build()
    self.assertEqual(len(rows), 11)
    for name, row in rows.items():
      self.assertEqual(p.verify(row), json.loads((p.PUBLIC / name).read_bytes()))
      self.assertEqual(row['private_numeric_array_opens'], 0)
      self.assertFalse(row['actual_execution_authorized'])
      self.assertFalse(row['architecture_frozen'])
      self.assertEqual(set(row['v4'].values()), {'NOT_RUN'})

  def test_signal_does_not_close_track_or_start_hf(self):
    from tools.cyberpilot.build_hurdle_v4_policy_review import build, PREFIX
    rows = build()
    decision, trigger = rows[PREFIX + 'policy-decision.json'], rows[PREFIX + 'next-architecture-trigger.json']
    self.assertEqual(decision['outcome'], 'C')
    self.assertFalse(decision['two_context_track_closed'])
    self.assertTrue(trigger['signal_satisfied'])
    self.assertFalse(trigger['outcome_b_registry_trigger_now'])
    self.assertEqual(trigger['hugging_face'], {'setup': 'NOT_RUN', 'login': 'NOT_RUN', 'repo': 'NOT_CREATED', 'upload': 0, 'download': 0})

  def test_public_state_conditional_shift_has_same_direction(self):
    from tools.cyberpilot.build_hurdle_v4_policy_review import build, PREFIX
    rows = build()[PREFIX + 'route-shift-structural-analysis.json']['folds']
    for values in rows['FOLD_A']['conditional_mean_score_shifts'].values():
      self.assertGreater(values['min'], 0)
    for values in rows['FOLD_B']['conditional_mean_score_shifts'].values():
      self.assertLess(values['max'], 0)

  def test_mathematics_module_has_no_execution_or_private_io_api(self):
    import ast
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / 'empirical_hurdle_v4_policy_review.py'
    tree = ast.parse(path.read_text())
    forbidden = {'open', 'read_bytes', 'read_text', 'load', 'fit', 'exhaustive', 'probability', 'normalizer', 'recursive',
                 'fit_stage1', 'fit_stage2', 'lstsq', 'solve', 'threshold'}
    calls = {n.func.id if isinstance(n.func, ast.Name) else n.func.attr for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))}
    self.assertFalse(calls & forbidden)


if __name__ == '__main__':
  unittest.main()
