"""Frozen Hurdle numerical execution; arrays only, no I/O or vehicle interfaces."""

import numpy as np
from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as source

CANDIDATES = tuple(v.replace('S2RI_', 'HRI_') for v in source.CANDIDATES)
HORIZONS = source.HORIZONS
SUPPORT = 201
MAX_UPDATES = 100
GRADIENT_TOLERANCE = 1e-8
ARMIJO_C = 1e-4
TRIAL_EXPONENTS = tuple(range(21))
CHUNK = 512
project = source.project
transform = source.transform


def parameters(candidate):
  if candidate not in CANDIDATES:
    raise ValueError('EXACT_HURDLE_CANDIDATE_REQUIRED')
  return source.parameters(candidate.replace('HRI_', 'S2RI_'))


def anchors(data, candidate, horizon):
  parameters(candidate)
  return source.anchors(data, candidate.replace('HRI_', 'S2RI_'), horizon)


def features(data, indices, candidate):
  parameters(candidate)
  return source.features(data, indices, candidate.replace('HRI_', 'S2RI_'))


def finite(*values):
  if any(not np.all(np.isfinite(v)) for v in values):
    raise ValueError('HURDLE_NUMERICAL_FAILURE_NONFINITE')


def train_only(role):
  if role != 'TRAIN':
    raise ValueError('TRAIN_ONLY_REQUIRED')


def normalizer(x, *, role, stage):
  train_only(role)
  if stage not in ('STAGE1', 'STAGE2') or x.dtype != np.float64 or x.ndim != 2 or not len(x) or not np.all(x[:, 0] == 1):
    raise ValueError('FLOAT64_TRAIN_DESIGN_REQUIRED')
  finite(x)
  constant = np.all(x == x[0], axis=0)
  constant[0] = False
  mean, std = x.mean(axis=0), x.std(axis=0, ddof=0)
  std[constant] = 0.0
  finite(mean, std)
  if np.any((std[1:] == 0) & ~constant[1:]):
    raise ValueError('HURDLE_NUMERICAL_FAILURE_NONCONSTANT_ZERO_STD')
  return {'mean': mean, 'std': std, 'constant': constant, 'effective': np.flatnonzero(~constant), 'constant_reference': x[0].copy()}


def sigmoid(z):
  finite(z)
  p = np.empty_like(z, dtype=np.float64)
  positive = z >= 0
  p[positive] = 1.0 / (1.0 + np.exp(-z[positive]))
  e = np.exp(z[~positive])
  p[~positive] = e / (1.0 + e)
  validate_probability(p)
  return p


def validate_probability(p):
  finite(p)
  if p.ndim != 1 or np.any((p < 0) | (p > 1)):
    raise ValueError('HURDLE_NUMERICAL_FAILURE_INVALID_PROBABILITY')


def loss(x, y, beta):
  z = x @ beta
  finite(z)
  value = float(np.mean(np.logaddexp(0.0, z) - y * z))
  finite(value)
  return value


def newton(x, y):
  beta = np.zeros(x.shape[1], dtype=np.float64)
  updates = 0
  accepted_trials = []
  while True:
    try:
      current_loss = loss(x, y, beta)
      p = sigmoid(x @ beta)
      g = x.T @ (p - y) / len(x)
      finite(g)
      maxabs = float(np.max(np.abs(g)))
      if maxabs <= GRADIENT_TOLERANCE:
        return beta, {'status': 'CONVERGED', 'updates': updates, 'loss': current_loss, 'maxabs_gradient': maxabs, 'accepted_trial_exponents': accepted_trials}
      if updates >= MAX_UPDATES:
        raise ValueError('MOVE_GATE_NONCONVERGENCE')
      w = p * (1.0 - p)
      hessian = x.T @ (w[:, None] * x) / len(x)
      finite(hessian)
      direction = np.linalg.solve(hessian, g)
      finite(direction)
      slope = float(np.dot(g, direction))
      finite(slope)
      if slope <= 0:
        raise ValueError('MOVE_GATE_NUMERICAL_FAILURE')
      for j in TRIAL_EXPONENTS:
        alpha = 1.0 * 0.5**j
        trial = beta - alpha * direction
        finite(trial)
        trial_loss = loss(x, y, trial)
        if trial_loss <= current_loss - ARMIJO_C * alpha * slope:
          beta = trial
          accepted_trials.append(j)
          break
      else:
        raise ValueError('MOVE_GATE_LINE_SEARCH_FAILURE')
      updates += 1
    except (np.linalg.LinAlgError, FloatingPointError) as error:
      raise ValueError('MOVE_GATE_NUMERICAL_FAILURE') from error
    except ValueError as error:
      if 'HURDLE_NUMERICAL' in str(error):
        raise ValueError('MOVE_GATE_NUMERICAL_FAILURE') from error
      raise


def model_result(x, norm, z, beta, rank):
  nominal = np.zeros(x.shape[1], dtype=np.float64)
  nominal[norm['effective']] = beta
  finite(beta, nominal)
  return {'normalizer': norm, 'coefficients': beta, 'nominal_coefficients': nominal, 'rank': rank, 'effective_x_sha_input': z}


def fit_stage1(x, y, *, role):
  train_only(role)
  if y.shape != (len(x),) or not np.all((y == 0) | (y == 1)):
    raise ValueError('BINARY_TRAIN_LABEL_REQUIRED')
  move, static = int(np.count_nonzero(y)), int(np.count_nonzero(y == 0))
  if not move or not static:
    raise ValueError('MOVE_GATE_TRAIN_CLASS_MISSING')
  if min(move, static) < SUPPORT:
    raise ValueError('MOVE_GATE_INSUFFICIENT_CLASS_SUPPORT')
  norm = normalizer(x, role=role, stage='STAGE1')
  z = transform(x, norm)
  rank = int(np.linalg.matrix_rank(z))
  if rank != z.shape[1]:
    raise ValueError('MOVE_GATE_FIT_PRECONDITION_RANK_FAILURE')
  beta, convergence = newton(z, y.astype(np.float64))
  return {**model_result(x, norm, z, beta, rank), 'convergence': convergence}


def probability(x, model):
  return sigmoid(transform(x, model['normalizer']) @ model['coefficients'])


def threshold(probabilities, labels, *, role):
  """One sorted TRAIN sweep. Python integers preserve exact BA comparison."""
  train_only(role)
  validate_probability(probabilities)
  if labels.shape != probabilities.shape or not np.all((labels == 0) | (labels == 1)):
    raise ValueError('BINARY_TRAIN_LABEL_REQUIRED')
  y = labels.astype(bool)
  positives, negatives = int(y.sum()), int((~y).sum())
  if not positives or not negatives:
    raise ValueError('MOVE_GATE_TRAIN_CLASS_MISSING')
  order = np.argsort(probabilities, kind='stable')
  sorted_p, sorted_y = probabilities[order], y[order]
  values, first, counts = np.unique(sorted_p, return_index=True, return_counts=True)
  moves = np.add.reduceat(sorted_y.astype(np.int64), first)
  group = 0
  tp, tn = positives, 0
  best, selected = None, None
  candidates = np.union1d(values, np.array([0.0, 1.0]))
  for value in candidates:
    while group < len(values) and values[group] <= value:
      moved = int(moves[group])
      tp -= moved
      tn += int(counts[group]) - moved
      group += 1
    score = tp * negatives + tn * positives
    key = (score, tn, float(value))
    if best is None or key > best:
      best = key
      selected = {'value': float(value), 'BA_NUM': score, 'TP': tp, 'TN': tn, 'FP': negatives - tn, 'FN': positives - tp, 'P': positives, 'N': negatives}
  return {**selected, 'candidate_count': len(candidates), 'decision': '>', 'population': 'TRAIN_ONLY'}


def fit_stage2(x, delta, *, role):
  train_only(role)
  finite(delta)
  if delta.dtype != np.float64 or delta.shape != (len(x),):
    raise ValueError('FLOAT64_DELTA_REQUIRED')
  mask = delta != 0
  if int(mask.sum()) < max(x.shape[1], SUPPORT):
    raise ValueError('CONDITIONAL_DELTA_INSUFFICIENT_SUPPORT')
  move_x = np.ascontiguousarray(x[mask])
  norm = normalizer(move_x, role=role, stage='STAGE2')
  z = transform(move_x, norm)
  rank = int(np.linalg.matrix_rank(z))
  if rank != z.shape[1]:
    raise ValueError('CONDITIONAL_DELTA_RANK_FAILURE')
  try:
    beta, _, returned, singular = np.linalg.lstsq(z, np.ascontiguousarray(delta[mask]), rcond=None)
  except np.linalg.LinAlgError as error:
    raise ValueError('CONDITIONAL_DELTA_NUMERICAL_FAILURE') from error
  if returned != rank:
    raise ValueError('CONDITIONAL_DELTA_NUMERICAL_FAILURE')
  finite(beta, singular)
  condition = float(singular[0] / singular[-1])
  finite(condition)
  return {**model_result(move_x, norm, z, beta, rank), 'train_mask': mask, 'singular_values': singular, 'condition': condition}


def predict_delta(x, model):
  value = transform(x, model['normalizer']) @ model['coefficients']
  finite(value)
  return value


def integrated(x, current, stage1, threshold_value, stage2):
  p = probability(x, stage1)
  if not np.isfinite(threshold_value) or not 0 <= threshold_value <= 1:
    raise ValueError('FROZEN_TRAIN_THRESHOLD_REQUIRED')
  gate = p > threshold_value
  delta = np.zeros(len(x), dtype=np.float64)
  projected = current.copy()
  if np.any(gate):
    delta[gate] = predict_delta(np.ascontiguousarray(x[gate]), stage2)
    projected[gate] = project(current[gate].astype(np.float64) + delta[gate])
  return delta, projected, p, gate


def diagnostics(actual, predicted):
  tp, tn = int(np.count_nonzero(actual & predicted)), int(np.count_nonzero(~actual & ~predicted))
  fp, fn = int(np.count_nonzero(~actual & predicted)), int(np.count_nonzero(actual & ~predicted))
  defined = bool(tp + fn and tn + fp and tp + fp)
  return {
    'TP': tp,
    'TN': tn,
    'FP': fp,
    'FN': fn,
    'status': 'DEFINED' if defined else 'STAGE1_DIAGNOSTIC_UNDEFINED',
    'false_move_rate': fp / (tn + fp) if tn + fp else None,
    'missed_move_rate': fn / (tp + fn) if tp + fn else None,
    'precision': tp / (tp + fp) if tp + fp else None,
    'recall': tp / (tp + fn) if tp + fn else None,
    'specificity': tn / (tn + fp) if tn + fp else None,
    'balanced_accuracy': 0.5 * (tp / (tp + fn) + tn / (tn + fp)) if tp + fn and tn + fp else None,
  }


def metrics(error, projected=None, target=None):
  result = source.metrics(np.ascontiguousarray(error, dtype=np.float64))
  if projected is not None:
    distance = np.abs(projected - target)
    result.update(exact_hit=float(np.count_nonzero(distance == 0) / len(distance)), within_one_tick=float(np.count_nonzero(distance <= 1) / len(distance)))
  return result


def recursive(initial_ticks, command, speed, candidate, stage1, threshold_value, stage2, horizon):
  """Only initial measured steering history is accepted, never future truth."""
  _, length = parameters(candidate)
  n = len(initial_ticks)
  if (
    horizon not in HORIZONS
    or initial_ticks.dtype != np.int64
    or initial_ticks.shape != (n, length + 1)
    or command.shape != (n, length + horizon - 1)
    or speed.shape != (n, horizon)
  ):
    raise ValueError('EXACT_ROLLOUT_HISTORY_AND_HORIZON_REQUIRED')
  finite(initial_ticks, command, speed)
  path = np.empty((n, horizon + 1), dtype=np.int64)
  gates = np.empty((n, horizon), dtype=bool)
  current = initial_ticks[:, -1].copy()
  path[:, 0] = current
  past = np.diff(initial_ticks, axis=1)
  for step in range(horizon):
    x = np.ascontiguousarray(np.column_stack((np.ones(n), command[:, step : step + length], past, current, speed[:, step])), dtype=np.float64)
    _, new, _, gate = integrated(x, current, stage1, threshold_value, stage2)
    path[:, step + 1], gates[:, step] = new, gate
    past[:, :-1] = past[:, 1:]
    past[:, -1] = new - current
    current = new
  return path, gates
