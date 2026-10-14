"""Public architecture algebra. Synthetic witnesses, never a fitting executor."""

import numpy as np

from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as old

SCOPE = 'SYNTHETIC_REPRESENTATION_ALGEBRA_ONLY'
SELECTED = 'STAGE1_V4_REPRESENTATION_ARCHITECTURE_SELECTED'
INCONCLUSIVE = 'STAGE1_V4_REPRESENTATION_REVIEW_INCONCLUSIVE'
ELIGIBILITY = (
  'CAN_CHANGE_WITHIN_STATE_RANKING', 'NOT_FIXED_SCORE_REPARAMETERIZATION', 'CAUSAL_INPUTS_ONLY',
  'NO_NEW_SENSOR_SEMANTICS', 'NO_RATE_DEPENDENCY', 'DETERMINISTIC_FITTING_CONTRACT_POSSIBLE',
  'BOUNDED_PARAMETERS', 'NO_ARBITRARY_SUBSET', 'NO_UNJUSTIFIED_HYPERPARAMETER_OR_HAS_PRINCIPLED_FREEZE_PATH',
  'ROUTE_FOLD_COMPATIBLE', 'BOUNDED_INFERENCE', 'FAIL_CLOSED',
)
RULE = (
  'FEWEST_NEW_REPRESENTATIONAL_ASSUMPTIONS', 'FEWEST_EFFECTIVE_FITTED_PARAMETERS', 'FEWEST_NEW_STATE_VARIABLES',
  'FEWEST_NEW_HYPERPARAMETERS', 'EXISTING_SOLVER_REUSE', 'NUMERICAL_RISK', 'INFERENCE_COMPLEXITY', 'ARTIFACT_COMPLEXITY',
)


def need(ok):
  if not ok:
    raise ValueError('STAGE1_REPRESENTATION_REVIEW_INPUT_CONFLICT')


def counts(candidate):
  d, length = old.parameters(candidate)
  p = 2 * length + 3
  q = p - 1
  m = p * (p + 1) // 2
  return {'candidate_id': candidate, 'd': d, 'L': length, 'P': p, 'dual_nominal': 2 * p,
          'dual_generic_identifiable_upper': 2 * p - 1, 'dual_increment_over_global_full_rank': p - 1,
          'actual_context_ranks': 'UNKNOWN_NOT_MEASURED', 'quadratic_total': m,
          'quadratic_new_products': q * (q + 1) // 2,
          'dual_coefficient_bytes': 16 * p, 'dual_independent_hessian_bytes_upper': 16 * p * p,
          'quadratic_hessian_bytes': 8 * m * m}


def feature_names(candidate):
  d, length = old.parameters(candidate)
  return (['intercept'] + [f'command[k-{j}]' for j in range(d + length - 1, d - 1, -1)] +
          [f'tick[k-{j}]-tick[k-{j + 1}]' for j in range(length - 1, -1, -1)] + ['tick[k]', 'vEgo[k]'])


def checked(x, scope):
  need(scope == SCOPE)
  x = np.asarray(x, dtype=np.float64)
  need(x.ndim == 2 and x.shape[0] > 0 and x.shape[1] >= 5 and x.shape[1] % 2 == 1)
  need(np.all(np.isfinite(x)) and np.all(x[:, 0] == 1))
  return x


def context(x, *, scope):
  x = checked(x, scope)
  return (x[:, -3] != 0).astype(np.int64)


def block_design(x, *, scope):
  x = checked(x, scope)
  z = context(x, scope=scope)[:, None]
  return np.ascontiguousarray(np.column_stack(((1 - z) * x, z * x)))


def quadratic_basis(x, *, scope):
  x = checked(x, scope)
  with np.errstate(over='ignore', invalid='ignore'):
    out = np.ascontiguousarray(np.column_stack([x] + [x[:, i] * x[:, j]
                              for i in range(1, x.shape[1]) for j in range(i, x.shape[1])]))
  need(np.all(np.isfinite(out)))
  return out


def mlp_counts(p, h):
  need(type(p) is int and type(h) is int and p >= 5 and h > 0)
  return {'global': h * (p + 1) + 1, 'state_concat': h * (p + 2) + 1,
          'dual_heads': 2 * (h * (p + 1) + 1)}


def rank_fixture():
  # Raw last-increment column 2 is structurally zero in STATIC context.
  return np.array([[1, 0, 0, 0, 0], [1, 1, 0, 0, 0], [1, 0, 0, 1, 0], [1, 0, 0, 0, 1],
                   [1, 0, 1, 0, 0], [1, 1, 1, 0, 0], [1, 0, 2, 0, 0], [1, 0, 1, 1, 0],
                   [1, 0, 1, 0, 1]], dtype=np.float64)


def witnesses():
  """Explicit coefficients are synthetic mathematical witnesses, never fitted."""
  old_logit = np.array([-2., -1., 0., 1., 2.])
  z = np.array([0, 0, 1, 1, 1])
  b, cut = .75, .25
  # Distinct synthetic score values for an unambiguous reversed ordering.
  distinct = np.array([.1, .2, .4, .8])
  order = np.argsort(distinct).tolist()
  x = np.array([[1., -1., 0., 0., 10.], [1., 1., 0., 0., 10.],
                [1., -1., 1., 0., 10.], [1., 1., 1., 0., 10.]])
  zs = context(x, scope=SCOPE)
  w0 = np.array([0., 1., 0., 0., 0.])
  w1 = -w0
  eta_old = x @ w0
  eta = np.where(zs == 0, x @ w0, x @ w1)
  block = block_design(x, scope=SCOPE)
  block_eta = block @ np.concatenate((w0, w1))
  base_delta = x @ w0 + zs * (x @ (w1 - w0))
  y = np.array([0., 1., 1., 0.])
  loss = np.logaddexp(0, eta) - y * eta
  block_loss = np.logaddexp(0, block_eta) - y * block_eta
  prob = 1 / (1 + np.exp(-eta))
  hessian = block.T @ ((prob * (1 - prob))[:, None] * block)
  # Polynomial and ReLU examples use the same STATIC state throughout.
  command = np.array([-1., 0., .5])
  quadratic = command ** 2
  relu = np.maximum(command, 0) + np.maximum(-command, 0)
  tolerance = old.GRADIENT_TOLERANCE  # Existing constant, not a proposed V4 policy.
  return {
    'state_intercept': {'transformed_decisions': (old_logit + b * z > cut).tolist(),
      'equivalent_logit_cut_decisions': (old_logit > cut - b * z).tolist(), 'within_state_order_preserved': True,
      'real_math': 'sigmoid(eta+b*z)>tau iff eta>logit(tau)-b*z for 0<tau<1',
      'endpoint_cases': 'ALL_OR_NONE; BINARY64_SIGMOID_SATURATION_CAN_COARSEN_TIES'},
    'state_affine': {'old_order': order, 'positive_order': np.argsort(2 * distinct + .3).tolist(),
      'negative_order': np.argsort(-2 * distinct + .3).tolist(), 'negative_slope_usefulness_established': False,
      'zero_slope': 'CONSTANT_WITHIN_STATE'},
    'dual_head': {'old_logits': eta_old.tolist(), 'new_logits': eta.tolist(),
      'static_command_contrast': float(eta[1] - eta[0]), 'move_command_contrast': float(eta[3] - eta[2]),
      'same_state_reversal': 'ROWS_2_3_MOVE', 'coefficient_origin': SCOPE},
    'quadratic': {'old_logits': command.tolist(), 'new_logits': quadratic.tolist(), 'same_state': 'STATIC'},
    'mlp': {'new_logits': relu.tolist(), 'illustrative_hidden_width': 2, 'actual_width_selected': False,
      'equation': 'ReLU(command)+ReLU(-command)', 'same_state': 'STATIC'},
    'training_algebra': {'head_logits': eta.tolist(), 'block_logits': block_eta.tolist(),
      'base_delta_logits': base_delta.tolist(), 'head_per_row_nll': loss.tolist(),
      'block_per_row_nll': block_loss.tolist(), 'head_original_order_sum': float(np.sum(loss)),
      'block_original_order_sum': float(np.sum(block_loss)), 'sum_hessian_off_block_zero': bool(np.all(hessian[:5, 5:] == 0)),
      'optimizer_byte_equivalence_claim': False, 'context_float_subtotals_assumed_equal': False},
    'mean_stopping': {'local_gradient': 2e-8, 'context_weight': .1,
      'joint_mean_scaled_gradient': .1 * 2e-8, 'current_tolerance': tolerance,
      'new_v4_tolerance_chosen': False},
    'separation': {'design_rank': 2, 'class_counts': [201, 201], 'finite_mle_exists': False,
      'proof': 'x=(1,-1),y=0 and x=(1,1),y=1; beta=(0,a); loss=log(1+exp(-a)) infimum 0 unattained',
      'illustrative_gradient_magnitude': float(1 / (1 + np.exp(32.))), 'current_tolerance': tolerance,
      'fit_executed': False},
  }


def options():
  yes = (True,) * len(ELIGIBILITY)
  no_rank = (False, False) + yes[2:]
  unresolved = yes[:8] + (None,) + yes[9:]
  # Assumption strata are categorical: fixed-score controls; one empirically
  # supported context interaction; unrestricted degree-two curvature; unspecified
  # feature subsets/neural/tree architecture. They are not fitted cost weights.
  return [
    {'id': 'A', 'family': 'STATE_INTERCEPT_ONLY_LOGISTIC', 'eligibility': no_rank,
     'reason': 'TWO_THRESHOLD_REPARAMETERIZATION', 'design_key': (0, 1, 1, 0, 0, 0, 0, 0)},
    {'id': 'B', 'family': 'POSITIVE_STATE_AFFINE_FIXED_SCORE', 'eligibility': no_rank,
     'domain': 'a_z>0; NEGATIVE_SLOPE_VARIANT_REVIEWED_SEPARATELY_NOT_AN_ELIGIBLE_NEW_REPRESENTATION',
     'reason': 'POSITIVE_VARIANT_FAILS_RANKING; NEGATIVE_FULL_REVERSAL_HAS_NO_SUPPORTED_REPRESENTATION_JUSTIFICATION', 'design_key': (0, 4, 1, 0, 0, 0, 0, 0)},
    {'id': 'C', 'family': 'HURDLE_STAGE1_CONTEXT_CONDITIONAL_LOGISTIC_V4', 'eligibility': yes,
     'reason': 'ALL_EXISTING_FEATURES_INTERACT_WITH_EMPIRICALLY_SUPPORTED_SINGLE_BIT; NO_SUBSET_OR_WIDTH',
     'design_key': (1, 9, 1, 0, 0, 1, 0, 0), 'parameter_key_basis': 'SMALLEST_P=5; SAME_ORDER_FOR_ALL_16_STRUCTURES'},
    {'id': 'D', 'family': 'FULL_DEGREE2_POLYNOMIAL_LOGISTIC', 'eligibility': yes,
     'reason': 'UNRESTRICTED_PAIRWISE_CURVATURE_WITHOUT_SPECIFIC_EMPIRICAL_SUPPORT',
     'design_key': (2, 15, 0, 0, 0, 2, 1, 0)},
    {'id': 'E', 'family': 'BOUNDED_PREDECLARED_INTERACTION_LOGISTIC', 'eligibility': yes[:7] + (None,) + yes[8:],
     'reason': 'ARBITRARY_TERM_SELECTION_REQUIRED; FULL_STATE_INTERACTION_IS_C_ALIAS',
     'design_key': (3, 0, 1, 1, 0, 1, 0, 0)},
    {'id': 'F', 'family': 'SMALL_DETERMINISTIC_MLP', 'eligibility': unresolved,
     'reason': 'WIDTH_ACTIVATION_INITIALIZATION_OPTIMIZER_REGULARIZATION_UNFROZEN',
     'design_key': (3, 0, 0, 1, 1, 2, 1, 1)},
    {'id': 'G', 'family': 'SMALL_STATE_CONDITIONED_MLP', 'eligibility': unresolved,
     'reason': 'FREEDOMS_OF_F_PLUS_CONCAT_VS_DUAL_HEAD_CHOICE', 'design_key': (3, 0, 1, 1, 1, 2, 1, 1)},
    {'id': 'H', 'family': 'TREE_OR_BOOSTED_TREE', 'eligibility': unresolved,
     'reason': 'DEPTH_LEAF_SPLIT_ENSEMBLE_CHOICES_UNSUPPORTED_NO_NEW_DEPENDENCY',
     'design_key': (3, 0, 0, 1, 1, 2, 1, 1)},
  ]


def select(rows):
  need(all(len(row['eligibility']) == len(ELIGIBILITY) and len(row['design_key']) == len(RULE) for row in rows))
  eligible = [row for row in rows if all(v is True for v in row['eligibility'])]
  minimum = min((tuple(row['design_key']) for row in eligible), default=None)
  winners = [row for row in eligible if tuple(row['design_key']) == minimum]
  chosen = winners[0] if len(winners) == 1 else None
  return {'status': SELECTED if chosen else INCONCLUSIVE, 'selected_option': chosen['id'] if chosen else None,
          'selected_family': chosen['family'] if chosen else None, 'eligible_options': [row['id'] for row in eligible],
          'scope': 'DECLARED_REVIEWED_FAMILIES_ONLY_NOT_UNIVERSAL_MINIMALITY',
          'performance_used': False}
