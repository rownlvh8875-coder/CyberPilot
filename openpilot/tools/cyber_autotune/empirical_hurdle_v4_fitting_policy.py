"""Synthetic-only V4 fitting-policy reference, never a private-data executor."""

from fractions import Fraction
import hashlib
import json

import numpy as np

from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as old

SCOPE = 'SYNTHETIC_ONLY'
SUPPORT = old.SUPPORT
MAX_UPDATES = old.MAX_UPDATES
GRADIENT_TOLERANCE = old.GRADIENT_TOLERANCE
ARMIJO_C = old.ARMIJO_C
TRIAL_EXPONENTS = old.TRIAL_EXPONENTS
REGULARIZATION = 'NONE'
CLASS_WEIGHTING = 'NONE'
RESAMPLING = False


def need(ok, status='V4_FITTING_POLICY_SCHEMA_CONFLICT'):
  if not ok:
    raise ValueError(status)


def synthetic(scope, role='TRAIN'):
  need(scope == SCOPE and role == 'TRAIN', 'V4_PRIVATE_FITTING_NOT_AUTHORIZED')


def matrix(x):
  need(isinstance(x, np.ndarray) and x.dtype == np.float64 and x.ndim == 2 and min(x.shape) > 0)
  need(x.flags.c_contiguous and bool(np.all(np.isfinite(x))), 'V4_STAGE1_NUMERICAL_FAILURE')
  return x


def labels(y, n):
  y = np.asarray(y)
  need(y.shape == (n,) and bool(np.all((y == 0) | (y == 1))))
  return y.astype(np.int64)


def array_identity(a):
  a = np.ascontiguousarray(a)
  return {'dtype': a.dtype.str, 'shape': list(a.shape), 'order': 'C', 'sha256': hashlib.sha256(a.tobytes()).hexdigest()}


def frozen(value):
  if isinstance(value, np.ndarray):
    return array_identity(value)
  if isinstance(value, Fraction):
    return [str(value.numerator), str(value.denominator)]
  if isinstance(value, dict):
    return {k: frozen(v) for k, v in value.items()}
  if isinstance(value, (list, tuple)):
    return [frozen(v) for v in value]
  return value


def identity(value):
  return hashlib.sha256(json.dumps(frozen(value), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def normalizer_identity(norm):
  return identity(norm)


def validate_normalizer(norm, candidate):
  _, length = old.parameters(candidate)
  p = 2 * length + 3
  need(set(norm) == {'mean', 'std', 'constant', 'effective', 'constant_reference'}, 'V4_NORMALIZER_IDENTITY_CONFLICT')
  need(all(isinstance(norm[k], np.ndarray) and norm[k].dtype == np.float64 and norm[k].shape == (p,)
           and np.all(np.isfinite(norm[k])) for k in ('mean', 'std', 'constant_reference')), 'V4_NORMALIZER_IDENTITY_CONFLICT')
  need(norm['constant'].dtype == np.bool_ and norm['constant'].shape == (p,) and not norm['constant'][0],
       'V4_NORMALIZER_IDENTITY_CONFLICT')
  effective = norm['effective']
  need(effective.dtype.kind in 'iu' and np.array_equal(effective, np.flatnonzero(~norm['constant'])) and effective[0] == 0,
       'V4_NORMALIZER_IDENTITY_CONFLICT')
  need(bool(np.all(norm['std'][effective[1:]] > 0)) and bool(np.all(norm['std'][norm['constant']] == 0)),
       'V4_NORMALIZER_IDENTITY_CONFLICT')
  return p


def basis(norm, candidate, state):
  p = validate_normalizer(norm, candidate)
  need(type(state) is int and state in (0, 1))
  return [int(j) for j in norm['effective'] if state == 1 or j != p - 3]


def apply_shared(x, norm, *, expected_identity, scope):
  synthetic(scope)
  matrix(x)
  need(normalizer_identity(norm) == expected_identity, 'V4_NORMALIZER_IDENTITY_CONFLICT')
  # Exact source transform, no means/stds or context constants recomputed.
  return np.ascontiguousarray(old.transform(x, norm))


def support(y, parameter_count, *, scope):
  synthetic(scope)
  y = labels(y, len(y))
  pos, neg = int(np.count_nonzero(y)), int(np.count_nonzero(y == 0))
  need(pos >= SUPPORT and neg >= SUPPORT and len(y) > parameter_count, 'V4_STAGE1_HEAD_SUPPORT_FAILURE')
  return {'positive': pos, 'negative': neg, 'count': len(y)}


def rational(value):
  if isinstance(value, Fraction):
    return value
  if isinstance(value, (int, np.integer)) and not isinstance(value, (bool, np.bool_)):
    return Fraction(int(value))
  if isinstance(value, (float, np.floating)) and np.isfinite(value):
    return Fraction.from_float(float(value))
  raise ValueError('V4_CERTIFICATE_RATIONAL_SCHEMA_CONFLICT')


def exact_minor_rows(x):
  """First independent rows, exact binary64-as-rational elimination.

  Synthetic reference only. Future large generator may propose a minor, but
  must verify that minor exactly without dropping any fitting population rows.
  """
  pivots, indices = {}, []
  for index, row in enumerate(x):
    q = [rational(v) for v in row]
    for pivot in sorted(pivots):
      amount = q[pivot]
      q = [a - amount * b for a, b in zip(q, pivots[pivot], strict=True)]
    pivot = next((j for j, a in enumerate(q) if a), None)
    if pivot is not None:
      scale = q[pivot]
      pivots[pivot] = [a / scale for a in q]
      indices.append(index)
    if len(indices) == x.shape[1]:
      return indices
  return None


def rank_certificate(x, *, scope):
  synthetic(scope)
  matrix(x)
  try:
    singular = np.linalg.svd(x, compute_uv=False)
  except np.linalg.LinAlgError as error:
    raise ValueError('V4_STAGE1_HEAD_RANK_FAILURE') from error
  need(bool(np.all(np.isfinite(singular))), 'V4_STAGE1_HEAD_RANK_FAILURE')
  tolerance = float(singular[0] * max(x.shape) * np.finfo(np.float64).eps)
  rank = int(np.count_nonzero(singular > tolerance))
  need(rank == x.shape[1], 'V4_STAGE1_HEAD_RANK_FAILURE')
  rows = exact_minor_rows(x)
  need(rows is not None, 'V4_STAGE1_HEAD_RANK_FAILURE')
  return {'rank': rank, 'columns': x.shape[1], 'count': len(x), 'singular_values': singular.tolist(),
          'tolerance': tolerance, 'exact_minor_rows': rows, 'exact_minor_verified': True,
          'minor_sha256': identity(np.ascontiguousarray(x[rows])), 'witness_rows_are_not_fit_row_filter': True}


def matrix_binding(x, y):
  matrix(x)
  return identity({'X': x, 'y': labels(y, len(x))})


def separation_certificate(x, y, certificate, *, scope):
  """Exact primal/dual proof verification, no LP optimizer or heuristic."""
  synthetic(scope)
  matrix(x)
  y = labels(y, len(x))
  unknown = {'status': 'SEPARATION_CERTIFICATE_INCONCLUSIVE', 'matrix_binding': matrix_binding(x, y)}
  if type(certificate) is not dict or certificate.get('matrix_binding') != unknown['matrix_binding']:
    return unknown
  try:
    signed = [[(2 * int(label) - 1) * rational(v) for v in row] for row, label in zip(x, y, strict=True)]
    if certificate.get('kind') == 'POSITIVE_DUAL':
      weights = [rational(v) for v in certificate['weights']]
      if len(weights) != len(x) or any(w < 1 for w in weights):
        return unknown
      residual = [sum((weights[i] * signed[i][j] for i in range(len(x))), Fraction(0)) for j in range(x.shape[1])]
      if any(residual):
        return unknown
      return {**unknown, 'status': 'NO_SEPARATION', 'certificate_sha256': identity(certificate),
              'exact_dual_residual': '0', 'certified_lp_optimum': '0', 'primal_zero_feasible': True,
              'proof': 'lambda>=1; A^T*lambda=0; q=lambda-1>=0; dual_mu=0'}
    if certificate.get('kind') == 'SEPARATING_DIRECTION':
      direction = [rational(v) for v in certificate['direction']]
      if len(direction) != x.shape[1] or sum(map(abs, direction), Fraction(0)) > 1:
        return unknown
      margins = [sum((a * b for a, b in zip(row, direction, strict=True)), Fraction(0)) for row in signed]
      if any(v < 0 for v in margins) or not any(v > 0 for v in margins):
        return unknown
      return {**unknown, 'status': 'SEPARATION_PRESENT', 'certificate_sha256': identity(certificate),
              'positive_margin_count': sum(v > 0 for v in margins), 'zero_margin_count': sum(v == 0 for v in margins),
              'exact_positive_objective': frozen(sum(margins, Fraction(0))),
              'complete_vs_quasi_not_inferred_from_zero_margins_alone': True}
  except (KeyError, TypeError, ValueError, OverflowError):
    return unknown
  return unknown


def converged(local_mean_gradient):
  need(bool(np.all(np.isfinite(local_mean_gradient))), 'V4_STAGE1_NUMERICAL_FAILURE')
  return bool(np.max(np.abs(local_mean_gradient)) <= GRADIENT_TOLERANCE)


def newton_synthetic(x, y, *, scope):
  synthetic(scope)
  matrix(x)
  y = labels(y, len(x))
  # Reuse exactly; callers must independently pass support/rank/separation.
  return old.newton(x, y.astype(np.float64))


def combine(transformed, z, heads, *, scope):
  synthetic(scope)
  matrix(transformed)
  need(isinstance(z, np.ndarray) and z.shape == (len(transformed),) and bool(np.all((z == 0) | (z == 1))))
  result = np.empty(len(transformed), np.float64)
  for state in (0, 1):
    mask = z == state
    head = heads[state]
    values = np.ascontiguousarray(transformed[mask][:, head['positions']])
    result[mask] = old.sigmoid(values @ head['coefficients'])
  old.validate_probability(result)
  return result


def threshold_synthetic(probabilities, y, *, scope, role):
  synthetic(scope, role)
  return old.threshold(probabilities, y, role=role)


def fit_synthetic(x, y, norm, *, candidate, fold, expected_normalizer_identity, certificate_factory, scope, role):
  synthetic(scope, role)
  matrix(x)
  need(fold in ('FOLD_A', 'FOLD_B'))
  need(x.shape[1] == validate_normalizer(norm, candidate))
  need(bool(np.all(x[:, 0] == 1)))
  y = labels(y, len(x))
  context = (x[:, -3] != 0).astype(np.int64)  # Raw prior increment, never centered.
  heads = {}
  try:
    transformed = apply_shared(x, norm, expected_identity=expected_normalizer_identity, scope=scope)
    for state in (0, 1):
      mask = context == state
      raw_basis = basis(norm, candidate, state)
      positions = [int(np.flatnonzero(norm['effective'] == j)[0]) for j in raw_basis]
      design = np.ascontiguousarray(transformed[mask][:, positions])
      target = y[mask]
      counts = support(target, len(positions), scope=scope)
      rank = rank_certificate(design, scope=scope)
      separation = separation_certificate(design, target, certificate_factory(design, target, state), scope=scope)
      need(separation['status'] == 'NO_SEPARATION', separation['status'])
      coefficients, convergence = newton_synthetic(design, target, scope=scope)
      heads[state] = {'basis': raw_basis, 'positions': positions, 'coefficients': coefficients, 'coefficient_identity': array_identity(coefficients),
                      'support': counts, 'rank': rank, 'separation': separation, 'convergence': convergence}
    probability = combine(transformed, context, heads, scope=scope)
    threshold = threshold_synthetic(probability, y, scope=scope, role=role)
    return {'status': 'SYNTHETIC_FIT_COMPLETE_NO_PRIVATE_AUTHORITY', 'candidate': candidate, 'fold': fold,
            'normalizer_identity': expected_normalizer_identity, 'heads': {'STATIC': heads[0], 'MOVE': heads[1]},
            'probabilities': probability, 'threshold': threshold, 'row_order': 'ORIGINAL_TRAIN'}
  except (ValueError, np.linalg.LinAlgError, FloatingPointError) as error:
    return {'status': 'V4_STAGE1_FIT_FAILED_CLOSED', 'candidate': candidate, 'fold': fold, 'cause': str(error),
            'fallback': False, 'partial_head_artifacts_promotable': False}


def result_identity(result):
  return identity(result)


def algebra_witness():
  x = np.array([[1., -1., 0., 1., 8.], [1., 1., 0., -1., 12.],
                [1., -1., 1., 1., 8.], [1., 1., -1., -1., 12.]])
  norm = {'mean': np.array([1., 0., .5, 0., 10.]), 'std': np.array([0., 1., .5, 1., 2.]),
          'constant': np.zeros(5, dtype=bool), 'effective': np.arange(5),
          'constant_reference': np.array([1., 0., 0., 0., 10.])}
  shared = apply_shared(x, norm, expected_identity=normalizer_identity(norm), scope=SCOPE)
  # Raw coefficients converted via beta_j=w_j*std_j; beta_0=w_0+sum w_j*mean_j.
  raw = np.array([1., 2., 4., -1., .5])
  beta = np.array([8., 2., 2., -1., 1.])
  static_beta = beta[[0, 1, 3, 4]].copy()
  static_beta[0] += beta[2] * (-1.)  # q_delta=(0-.5)/.5=-1.
  a, b = x[:2] @ raw, shared[:2][:, [0, 1, 3, 4]] @ static_beta
  c, d = x[2:] @ raw, shared[2:] @ beta
  eta = np.r_[b, d]
  y = np.array([0., 1., 1., 0.])
  row_nll = np.logaddexp(0., eta) - y * eta
  return {'raw_static_logits': a.tolist(), 'normalized_static_logits': b.tolist(),
          'raw_move_logits': c.tolist(), 'normalized_move_logits': d.tolist(),
          'off_support_empirical_constant_equivalence_claim': False,
          'independent_sum_nll': float(np.sum(row_nll[:2]) + np.sum(row_nll[2:])),
          'block_sum_nll': float(np.sum(row_nll)), 'block_optimizer_byte_equivalence_claim': False}


def execute_private():
  raise ValueError('V4_PRIVATE_FITTING_NOT_AUTHORIZED')
