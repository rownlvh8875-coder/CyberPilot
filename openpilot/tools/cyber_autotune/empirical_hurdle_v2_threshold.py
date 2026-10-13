"""TRAIN-only V2 sweep, preserving canonical NumPy ordered reductions.

No model, data loader, DEVELOPMENT input, or fitting interface is present.
The update tree retains NumPy's binary64 pairwise reduction order (128-element
leaves, midpoint rounded down to eight). Leaves use NumPy itself. This is
validated against the pinned runtime; no cumulative subtract/add sums are used.
"""

from copy import deepcopy
import math
import numpy as np

from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m

FAILURE = 'V2_THRESHOLD_EVALUATOR_EQUIVALENCE_FAILURE'
NO_FEASIBLE = 'STAGE1_DECISION_POLICY_V2_NO_FEASIBLE_THRESHOLD'


class OrderedSum:
  """Point updates with the original population order, never probability order."""

  def __init__(self, values):
    self.values = np.ascontiguousarray(values, dtype=np.float64).copy()
    self.parents, self.children, self.ranges, self.sums = [], [], [], []
    self.leaves = np.empty(len(values), dtype=np.int64)
    self._build(0, len(values), -1)

  def _build(self, start, count, parent):
    node = len(self.sums)
    self.parents.append(parent)
    self.children.append(None)
    self.ranges.append((start, count))
    self.sums.append(0.0)
    if count <= 128:
      self.leaves[start : start + count] = node
      self.sums[node] = float(np.sum(self.values[start : start + count]))
    else:
      half = count // 2
      half -= half % 8
      left = self._build(start, half, node)
      right = self._build(start + half, count - half, node)
      self.children[node] = left, right
      self.sums[node] = self.sums[left] + self.sums[right]
    return node

  def update(self, index, value):
    self.values[index] = value
    node = int(self.leaves[index])
    start, count = self.ranges[node]
    self.sums[node] = float(np.sum(self.values[start : start + count]))
    node = self.parents[node]
    while node >= 0:
      left, right = self.children[node]
      self.sums[node] = self.sums[left] + self.sums[right]
      node = self.parents[node]

  def total(self):
    return self.sums[0]


class OrderStatistics:
  """Exact float64 coordinates with integer Fenwick counts; no value binning."""

  def __init__(self, current, alternate):
    self.values = np.unique(np.concatenate((current, alternate)))
    self.positions = {float(value): i + 1 for i, value in enumerate(self.values)}
    self.count = len(current)
    self.tree = np.zeros(len(self.values) + 1, dtype=np.int64)
    for value in current:
      self._add(value, 1)

  def _add(self, value, amount):
    i = self.positions[float(value)]
    while i < len(self.tree):
      self.tree[i] += amount
      i += i & -i

  def replace(self, old, new):
    self._add(old, -1)
    self._add(new, 1)

  def kth(self, rank):
    index = 0
    bit = 1 << (len(self.values).bit_length() - 1)
    while bit:
      nxt = index + bit
      if nxt < len(self.tree) and int(self.tree[nxt]) <= rank:
        rank -= int(self.tree[nxt])
        index = nxt
      bit >>= 1
    return float(self.values[index])

  def p95(self):
    position = (self.count - 1) * np.float64(0.95)
    low = math.floor(position)
    fraction = float(position - low)
    a, b = self.kth(low), self.kth(min(low + 1, self.count - 1))
    difference = b - a
    return b - difference * (1.0 - fraction) if fraction >= 0.5 else a + difference * fraction


def candidates(probability):
  if probability.dtype != np.float64 or probability.ndim != 1 or not len(probability):
    raise ValueError('V2_FLOAT64_PROBABILITY_REQUIRED')
  m.validate_probability(probability)
  return np.unique(np.concatenate((np.array([0.0, 1.0]), probability)))


def prepare(probability, branch_delta, current, target):
  candidates(probability)
  n = len(probability)
  if (
    branch_delta.dtype != np.float64
    or branch_delta.shape != (n,)
    or current.dtype != np.int64
    or target.dtype != np.int64
    or current.shape != (n,)
    or target.shape != (n,)
  ):
    raise ValueError('V2_EXACT_TRAIN_ARRAY_SCHEMA_REQUIRED')
  m.finite(branch_delta)
  actual = target - current
  move = actual != 0
  if not move.any() or move.all():
    raise ValueError('V2_TRAIN_CLASSES_REQUIRED')
  projected = m.project(current.astype(np.float64) + branch_delta)
  error = branch_delta - actual.astype(np.float64)
  hold_error = -actual.astype(np.float64)
  m.finite(error, error * error, hold_error)
  return move, projected, error, hold_error


def scalar_metrics(error):
  return {'rmse': float(np.sqrt(np.mean(error * error))), 'mae': float(np.mean(np.abs(error))), 'p95': float(np.percentile(np.abs(error), 95, method='linear'))}


def describe(all_rmse, move_metrics, baseline, exact, false_move, within):
  result = {
    'all_rmse': all_rmse,
    'move': move_metrics,
    'exact_hit_count': int(exact),
    'static_projected_false_move_count': int(false_move),
    'within_one_tick_count': int(within),
  }
  result['feasible'] = bool(all_rmse < baseline['all_rmse'] and all(move_metrics[k] <= baseline['move'][k] for k in ('rmse', 'mae', 'p95')))
  if any(not math.isfinite(x) for x in (all_rmse, *move_metrics.values())):
    raise ValueError('V2_THRESHOLD_NONFINITE_METRIC')
  return result


def canonical(probability, branch_delta, current, target, threshold):
  move, projected, _, hold_error = prepare(probability, branch_delta, current, target)
  gate = probability > threshold
  delta = np.zeros(len(gate), dtype=np.float64)
  delta[gate] = branch_delta[gate]
  final = current.copy()
  final[gate] = projected[gate]
  error = delta - (target - current).astype(np.float64)
  baseline = {'all_rmse': float(np.sqrt(np.mean(hold_error * hold_error))), 'move': scalar_metrics(hold_error[move])}
  return describe(
    float(np.sqrt(np.mean(error * error))),
    scalar_metrics(error[move]),
    baseline,
    np.count_nonzero(final == target),
    np.count_nonzero(~move & (final != current)),
    np.count_nonzero(np.abs(final - target) <= 1),
  )


def key(threshold, row):
  return (row['exact_hit_count'], -row['static_projected_false_move_count'], row['within_one_tick_count'], float(threshold))


def sweep(probability, branch_delta, current, target, *, role, observer=None):
  if role != 'TRAIN':
    raise ValueError('V2_TRAIN_ONLY_THRESHOLD_REQUIRED')
  move, projected, branch_error, hold_error = prepare(probability, branch_delta, current, target)
  thresholds = candidates(probability)
  n, nm = len(move), int(move.sum())
  index_move = np.full(n, -1, dtype=np.int64)
  index_move[move] = np.arange(nm)
  gate = probability > 0.0
  error = np.where(gate, branch_error, hold_error)
  final = np.where(gate, projected, current)
  all_sse = OrderedSum(error * error)
  move_sse = OrderedSum(error[move] * error[move])
  move_sae = OrderedSum(np.abs(error[move]))
  order = OrderStatistics(np.abs(error[move]), np.abs(hold_error[move]))
  exact = int(np.count_nonzero(final == target))
  false_move = int(np.count_nonzero(~move & (final != current)))
  within = int(np.count_nonzero(np.abs(final - target) <= 1))
  baseline = {'all_rmse': float(np.sqrt(np.mean(hold_error * hold_error))), 'move': scalar_metrics(hold_error[move])}
  indices = np.argsort(probability, kind='stable')
  cursor = int(np.searchsorted(probability[indices], 0.0, side='right'))
  best, selected, feasible = None, None, 0
  observed = [] if observer is not None else None
  # Deterministic canonical checks before the full sweep, then selected check.
  unique = np.unique(probability)
  checkpoints = {0.0, 1.0, float(unique[0]), float(unique[-1]), float(unique[len(unique) // 2])}
  reference = {t: canonical(probability, branch_delta, current, target, t) for t in checkpoints}
  for threshold in thresholds:
    while cursor < n and probability[indices[cursor]] <= threshold:
      i = int(indices[cursor])
      all_sse.update(i, hold_error[i] * hold_error[i])
      if move[i]:
        j = int(index_move[i])
        move_sse.update(j, hold_error[i] * hold_error[i])
        move_sae.update(j, abs(hold_error[i]))
        order.replace(abs(branch_error[i]), abs(hold_error[i]))
      exact += int(current[i] == target[i]) - int(projected[i] == target[i])
      false_move -= int(not move[i] and projected[i] != current[i])
      within += int(abs(current[i] - target[i]) <= 1) - int(abs(projected[i] - target[i]) <= 1)
      cursor += 1
    metrics = {'rmse': float(np.sqrt(move_sse.total() / nm)), 'mae': move_sae.total() / nm, 'p95': order.p95()}
    row = describe(float(np.sqrt(all_sse.total() / n)), metrics, baseline, exact, false_move, within)
    if float(threshold) in reference and row != reference[float(threshold)]:
      raise ValueError(FAILURE)
    if observed is not None:
      observed.append((float(threshold), deepcopy(row)))
    if row['feasible']:
      feasible += 1
      score = key(threshold, row)
      if best is None or score > best:
        best, selected = score, row
  threshold = best[-1] if best is not None else None
  if threshold is not None and selected != canonical(probability, branch_delta, current, target, threshold):
    raise ValueError(FAILURE)
  if observer is not None:
    for value, record in observed:
      observer(value, record)
  return {
    'status': 'V2_THRESHOLD_FINALIZED' if best is not None else NO_FEASIBLE,
    'threshold': threshold,
    'candidate_count': len(thresholds),
    'feasible_count': feasible,
    'objective': selected,
    'canonical_checks': len(reference) + (threshold is not None),
  }
