"""Public review logic and declared synthetic mathematical witnesses only.

No optimizer, threshold candidate enumeration, model, source loader or rollout.
The fixed toy cutoffs below illustrate properties; they predict no real winner.
"""

from fractions import Fraction

import numpy as np

SCOPE = 'SYNTHETIC_POLICY_MATHEMATICS_ONLY'
OUTCOMES = {
  'A': 'V4_TWO_CONTEXT_SEPARABLE_POLICY_DESIGN_REVIEW_SUPPORTED',
  'B': 'V4_TWO_CONTEXT_THRESHOLD_TRACK_PROJECT_PRIORITY_CLOSED',
  'C': 'V4_TWO_CONTEXT_POLICY_DECISION_INCONCLUSIVE',
}
RULE = ('SCIENTIFIC_FAILURE_RELEVANCE', 'POLICY_INTERPRETABILITY', 'NO_ARBITRARY_NEW_TARGET',
        'ROUTE_TRANSFER_RELEVANCE', 'COMPUTATIONAL_EXACTNESS', 'COMPLEXITY')


def need(condition):
  if not condition:
    raise ValueError('V4_POLICY_REVIEW_SCHEMA_OR_AUTHORITY_CONFLICT')


def fixed_decisions(score, context, cutoffs, *, scope):
  need(scope == SCOPE)
  need(type(score) is np.ndarray and score.dtype == np.float64 and score.ndim == 1 and len(score) > 0)
  need(type(context) is np.ndarray and context.dtype == np.uint8 and context.shape == score.shape)
  need(np.isin(context, [0, 1]).all() and np.isfinite(score).all() and ((score >= 0) & (score <= 1)).all())
  need(type(cutoffs) is tuple and len(cutoffs) == 2 and all(type(t) is float and np.isfinite(t) and 0 <= t <= 1 for t in cutoffs))
  return score > np.array(cutoffs)[context]


def fixed_score_brier(score, label, *, scope):
  need(scope == SCOPE and score.shape == label.shape and score.ndim == 1 and len(score) > 0)
  need(np.isfinite(score).all() and ((score >= 0) & (score <= 1)).all() and np.isin(label, [0., 1.]).all())
  # A fixed probability loss contains NO threshold parameter.
  return float(np.mean((score - label) ** 2))


def additive_identity(context_utilities):
  """max_i,j(a_i+b_j)=max_i(a_i)+max_j(b_j); utilities are declared toy integers."""
  need(type(context_utilities) is tuple and len(context_utilities) == 2)
  need(all(type(v) is tuple and len(v) > 0 and all(type(x) is int for x in v) for v in context_utilities))
  return sum(max(v) for v in context_utilities)


def decide(*, separable, representation, closure_justified):
  """Review-only tri-state evidence. Unknown cannot become rejection or closure.

  The external scientific assessment supplies these predicates; this interface
  does not infer them from runtime, AUC quality cutoffs, or a convenient optimizer.
  If both directions are justified, an unresolved first-priority comparison stays C.
  """
  need(all(type(v) is tuple and len(v) == 6 and all(x is None or type(x) is bool for x in v) for v in (separable, representation)))
  need(closure_justified is None or type(closure_justified) is bool)
  a = all(x is True for x in separable)
  signal = all(x is True for x in representation)
  b = signal and closure_justified is True
  outcome = 'A' if a and not b else 'B' if b and not a else 'C'
  return {'outcome': outcome, 'status': OUTCOMES[outcome], 'separable_review_criteria_satisfied': a,
          'representation_review_signal': signal, 'two_context_track_closed': outcome == 'B',
          'positive_closure_justification': closure_justified, 'architecture_frozen': False,
          'fitting_policy_frozen': False, 'actual_execution_authorized': False}


def witnesses():
  """Fixed counterexamples, not fitted thresholds or a surrogate performance run."""
  def rmse(a):
    return float(np.sqrt(np.mean(a * a)))
  def p95(a):
    return float(np.percentile(a, 95, method='linear'))
  hold, candidate = np.array([1., 1., 10., 10.]), np.array([2., 2., 0., 0.])
  quantile_hold, quantile_candidate = np.array([19.] * 4), np.array([0., 20., 0., 20.])
  reference = np.array([1., 2.**-53, 2.**-53])
  changed = np.nextafter(reference, 0.)  # Error-value witness, never a threshold epsilon.
  scores, contexts, cuts = np.array([.125, .375, .625, .875]), np.array([0, 0, 1, 1], np.uint8), (.375, .75)
  def get(s):
    return fixed_decisions(s, contexts, cuts, scope=SCOPE).tolist()
  # Two declared coupled alternatives; no claim about independent additive maxima.
  support, hits = (100, 1), ((100, 0), (98, 1))
  return {
    'scope': SCOPE, 'no_real_performance_prediction': True,
    'rmse_compensation': {'reference_errors': hold.tolist(), 'candidate_errors': candidate.tolist(), 'contexts': [0, 0, 1, 1],
      'reference_local_rmse': [rmse(hold[:2]), rmse(hold[2:])], 'candidate_local_rmse': [rmse(candidate[:2]), rmse(candidate[2:])],
      'reference_global_rmse': rmse(hold), 'candidate_global_rmse': rmse(candidate)},
    'pooled_p95': {'reference_errors': quantile_hold.tolist(), 'candidate_errors': quantile_candidate.tolist(), 'contexts': [0, 0, 1, 1],
      'reference_local_p95': [p95(quantile_hold[:2]), p95(quantile_hold[2:])],
      'candidate_local_p95': [p95(quantile_candidate[:2]), p95(quantile_candidate[2:])],
      'reference_pooled_p95': p95(quantile_hold), 'candidate_pooled_p95': p95(quantile_candidate)},
    'support_weighting': {'supports': list(support), 'declared_alternative_hits': [list(h) for h in hits],
      'population_weighted': [sum(h) / sum(support) for h in hits],
      'equal_context_weighted': [float(sum(Fraction(h[c], support[c]) for c in (0, 1)) / 2) for h in hits],
      'not_an_unconstrained_separable_optimum_claim': True,
      'scope_note': 'WEIGHTING_OF_TWO_DECLARED_COUPLED_ALTERNATIVES_NOT_FITTING_OR_REAL_POLICY_PREFERENCE'},
    'float_reduction': {'reference_errors': reference.tolist(), 'candidate_errors': changed.tolist(), 'contexts': [0, 1, 1],
      'reference_local_mae': [float(np.mean(reference[:1])), float(np.mean(reference[1:]))],
      'candidate_local_mae': [float(np.mean(changed[:1])), float(np.mean(changed[1:]))],
      'reference_canonical_mae': float(np.mean(reference)), 'candidate_canonical_mae': float(np.mean(changed)),
      'reference_context_subtotal_mae': float((np.sum(reference[:1]) + np.sum(reference[1:])) / 3),
      'candidate_context_subtotal_mae': float((np.sum(changed[:1]) + np.sum(changed[1:])) / 3)},
    'fixed_shift': {'toy_scores': scores.tolist(), 'toy_contexts': contexts.tolist(), 'toy_cutoffs': list(cuts),
      'original_decisions': get(scores), 'up_decisions': get(scores + .125), 'down_decisions': get(scores - .125),
      'original_order': np.argsort(scores).tolist(), 'up_order': np.argsort(scores + .125).tolist(),
      'down_order': np.argsort(scores - .125).tolist(), 'within_state_score_order_unchanged': True,
      'binary_gate_auc_invariance_claim': False, 'structural_robustness': 'NO_STRUCTURAL_CORRECTION'},
    'onset_heavy': {'onset_count': 55, 'continuation_count': 45, 'unresolved_onset_if_only_continuation_changes': 55,
      'real_performance_prediction': False, 'interpretation': 'DECLARED_100_EVENT_TOY_PARTITION_NOT_HISTORICAL_ROW_RECONSTRUCTION'},
    'pooled_ba_separation': {'identity': 'BA=(N_GLOBAL*TP+P_GLOBAL*TN)/(2*P_GLOBAL*N_GLOBAL)',
      'context_contribution': 'N_GLOBAL*TP_z+P_GLOBAL*TN_z',
      'proof': 'POSITIVE_CONSTANT_GLOBAL_DENOMINATOR; ADDITIVE_INTEGER_NUMERATOR; UNCOUPLED_DOMAIN_MAX_SEPARATES',
      'context_local_ba': 'TP_z/(2*P_z)+TN_z/(2*N_z); DIFFERENT_WEIGHTS',
      'support_requirement': 'P_z_AND_N_z_POSITIVE_FOR_LOCAL_BA_NO_UNDEFINED_IMPUTATION',
      'not_equivalent_to_integrated_task_feasibility': True, 'adopted': False},
  }
