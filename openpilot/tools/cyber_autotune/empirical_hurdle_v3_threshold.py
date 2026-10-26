"""Bounded TRAIN sweep: frozen V2 numerical primitives plus the V3 TP floor.

Only one-dimensional O(N+T) arrays are retained. Observations are streaming,
provisional copies; callers must wait for successful finalization before use.
No source loader, prediction, fitting or DEVELOPMENT input exists here.
"""

from copy import deepcopy
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_threshold as v2
from openpilot.tools.cyber_autotune.empirical_hurdle_v3_scaffold import validate_reference

FAILURE = 'V3_THRESHOLD_EVALUATOR_EQUIVALENCE_FAILURE'
NO_FEASIBLE = 'V3_NO_FEASIBLE_THRESHOLD'


def _prepare(probability, branch_delta, current, target):
  for array in (probability, branch_delta, current, target):
    if not isinstance(array, np.ndarray) or not array.flags.c_contiguous:
      raise ValueError('V3_NUMERICAL_FAILURE_ARRAY_LAYOUT')
  for array in (current, target):
    if array.dtype != np.int64 or array.ndim != 1 or not np.all((array >= -32768) & (array <= 32767)):
      raise ValueError('V3_NUMERICAL_FAILURE_TICK_RANGE')
  try:
    return v2.prepare(probability, branch_delta, current, target)
  except (ValueError, FloatingPointError) as exc:
    raise ValueError('V3_NUMERICAL_FAILURE') from exc


def canonical(probability, branch_delta, current, target, value, reference_tp):
  row = v2.canonical(probability, branch_delta, current, target, value)
  row['tp'] = int(np.count_nonzero((target != current) & (probability > value)))
  row['feasible'] = bool(row['feasible'] and row['tp'] >= reference_tp)
  return row


def sweep(probability, branch_delta, current, target, *, reference_tp, role, observer=None):
  if role != 'TRAIN':
    raise ValueError('V3_TRAIN_ONLY_THRESHOLD_REQUIRED')
  move, _, _, _ = _prepare(probability, branch_delta, current, target)
  validate_reference(reference_tp, int(np.count_nonzero(move)))
  return _sweep(probability, branch_delta, current, target, reference_tp=reference_tp, observer=observer)


def _sweep(probability, branch_delta, current, target, *, reference_tp, observer=None):
  """Numeric core; zero-reference access is for synthetic V2 parity tests only.

  The authorized orchestrator calls sweep(), whose reference guard is mandatory.
  Existing V2 OrderedSum/OrderStatistics implement all floating-point updates.
  """
  move, projected, branch_error, hold_error = _prepare(probability, branch_delta, current, target)
  thresholds = v2.candidates(probability)
  n, nm = len(move), int(np.count_nonzero(move))
  index_move = np.full(n, -1, dtype=np.int64)
  index_move[move] = np.arange(nm)
  gate = probability > 0.0
  error = np.where(gate, branch_error, hold_error)
  final = np.where(gate, projected, current)
  all_sse = v2.OrderedSum(error * error)
  move_sse = v2.OrderedSum(error[move] * error[move])
  move_sae = v2.OrderedSum(np.abs(error[move]))
  order = v2.OrderStatistics(np.abs(error[move]), np.abs(hold_error[move]))
  exact = int(np.count_nonzero(final == target))
  false_move = int(np.count_nonzero(~move & (final != current)))
  within = int(np.count_nonzero(np.abs(final - target) <= 1))
  tp = int(np.count_nonzero(move & gate))
  baseline = {'all_rmse': float(np.sqrt(np.mean(hold_error * hold_error))), 'move': v2.scalar_metrics(hold_error[move])}
  indices = np.argsort(probability, kind='stable')
  cursor = int(np.searchsorted(probability[indices], 0.0, side='right'))
  unique = np.unique(probability)
  checkpoints = {0.0, 1.0, float(unique[0]), float(unique[-1]), float(unique[len(unique) // 2])}
  reference = {t: canonical(probability, branch_delta, current, target, t, reference_tp) for t in checkpoints}
  best, selected, feasible = None, None, 0
  for threshold in thresholds:
    while cursor < n and probability[indices[cursor]] <= threshold:
      i = int(indices[cursor])
      all_sse.update(i, hold_error[i] * hold_error[i])
      if move[i]:
        j = int(index_move[i])
        move_sse.update(j, hold_error[i] * hold_error[i])
        move_sae.update(j, abs(hold_error[i]))
        order.replace(abs(branch_error[i]), abs(hold_error[i]))
        tp -= 1
      exact += int(current[i] == target[i]) - int(projected[i] == target[i])
      false_move -= int(not move[i] and projected[i] != current[i])
      within += int(abs(current[i] - target[i]) <= 1) - int(abs(projected[i] - target[i]) <= 1)
      cursor += 1
    metrics = {'rmse': float(np.sqrt(move_sse.total() / nm)), 'mae': move_sae.total() / nm, 'p95': order.p95()}
    row = v2.describe(float(np.sqrt(all_sse.total() / n)), metrics, baseline, exact, false_move, within)
    row['tp'] = tp
    row['feasible'] = bool(row['feasible'] and tp >= reference_tp)
    if float(threshold) in reference and row != reference[float(threshold)]:
      raise ValueError(FAILURE)
    if row['feasible']:
      feasible += 1
      score = v2.key(threshold, row)
      if best is None or score > best:
        best, selected = score, row
    if observer is not None:
      observer(float(threshold), deepcopy(row))
  value = best[-1] if best is not None else None
  if value is not None and selected != canonical(probability, branch_delta, current, target, value, reference_tp):
    raise ValueError(FAILURE)
  return {
    'status': 'V3_THRESHOLD_FINALIZED' if best is not None else NO_FEASIBLE,
    'threshold': value,
    'candidate_count': len(thresholds),
    'feasible_count': feasible,
    'objective': selected,
    'canonical_checks': len(reference) + (value is not None),
  }
