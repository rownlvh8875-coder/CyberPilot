"""Synthetic pair metrics and exact integer context tables. No filesystem API."""

import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune.empirical_s2_ri_fit_cv_math import project

COUNT_FIELDS = ('exact_hit_count', 'within_one_tick_count', 'static_projected_false_move_count', 'TP', 'TN', 'FP', 'FN', 'predicted_move_count')


def require(value, status='V4_TWO_CONTEXT_SYNTHETIC_ONLY_OR_SCHEMA_CONFLICT'):
  if not value:
    raise ValueError(status)


class SyntheticTrain:
  """Explicit synthetic provenance, no path or actual-execution authorization interface."""

  def __init__(self, *, score, context, branch_delta, current, target, role, scope):
    require(role == 'SYNTHETIC_TRAIN' and scope == 'SYNTHETIC_ONLY')
    self.role, self.scope = role, scope
    values = {'score': score, 'context': context, 'branch_delta': branch_delta, 'current': current, 'target': target}
    require(all(isinstance(v, np.ndarray) and v.ndim == 1 and len(v) == len(score) for v in values.values()) and len(score) > 0)
    require(score.dtype == branch_delta.dtype == np.float64 and current.dtype == target.dtype == np.int64)
    require(context.dtype in (np.bool_, np.uint8) and np.isin(context, [0, 1]).all())
    require(all(np.isfinite(v).all() for v in values.values()) and ((score >= 0) & (score <= 1)).all())
    require(all(((v >= -32768) & (v <= 32767)).all() for v in (current, target)))
    for name, value in values.items():
      copied = np.ascontiguousarray(value).copy()
      copied.setflags(write=False)
      setattr(self, name, copied)
    self.identity = self.digest()
    self.projected_move = project(self.current.astype(np.float64) + self.branch_delta)
    self.projected_move.setflags(write=False)

  def digest(self):
    return p.sha(p.canonical({name: {'shape': list(getattr(self, name).shape), 'dtype': getattr(self, name).dtype.str,
                                    'content': p.sha(getattr(self, name).tobytes())}
                             for name in ('score', 'context', 'branch_delta', 'current', 'target')}))

  def verify(self):
    require(self.role == 'SYNTHETIC_TRAIN' and self.scope == 'SYNTHETIC_ONLY' and self.identity == self.digest())
    require(np.array_equal(self.projected_move, project(self.current.astype(np.float64) + self.branch_delta)))


def threshold_sets(population):
  population.verify()
  return tuple(np.unique(np.r_[np.array([0., 1.], np.float64), population.score[population.context == c]]) for c in (0, 1))


def scalar_metrics(error):
  if len(error) == 0:
    return None
  return {'rmse': float(np.sqrt(np.mean(error * error))), 'mae': float(np.mean(np.abs(error))),
          'p95': float(np.percentile(np.abs(error), 95, method='linear'))}


def counts(move, gate, current, target, projected):
  return dict(zip(COUNT_FIELDS, (int(np.count_nonzero(v)) for v in (
    projected == target, np.abs(projected - target) <= 1, ~move & (projected != current),
    move & gate, ~move & ~gate, ~move & gate, move & ~gate, gate)), strict=True))


def evaluate_pair(population, pair):
  """Authoritative original-row-order metrics. The pair carries no V4 policy authority."""
  population.verify()
  require(len(pair) == 2 and all(np.isfinite(t) and 0 <= t <= 1 for t in pair))
  current, target = population.current, population.target
  # Both inputs are validated signed16, widened int64 BEFORE subtraction.
  actual = target - current
  move = actual != 0
  gate = population.score > np.asarray(pair, np.float64)[population.context.astype(np.int64)]
  delta = np.zeros(len(current), np.float64)
  delta[gate] = population.branch_delta[gate]
  projected = current.copy()
  projected[gate] = population.projected_move[gate]
  error, hold_error = delta - actual.astype(np.float64), -actual.astype(np.float64)
  return {'all': scalar_metrics(error), 'move': scalar_metrics(error[move]),
          'hold_all': scalar_metrics(hold_error), 'hold_move': scalar_metrics(hold_error[move]),
          'true_move_count': int(np.count_nonzero(move)), 'count': len(current),
          'counts': counts(move, gate, current, target, projected),
          'contexts': [counts(move[s], gate[s], current[s], target[s], projected[s]) for s in (population.context == 0, population.context == 1)]}


class RangeMaximum:
  """Python-int range maxima, O(T) storage and O(log T) inclusive queries."""

  def __init__(self, values):
    self.n = len(values)
    self.tree = [None] * (2 * self.n)
    self.tree[self.n:] = [int(v) for v in values]
    for i in range(self.n - 1, 0, -1):
      self.tree[i] = max(self.tree[2 * i], self.tree[2 * i + 1])

  def query(self, lo, hi):
    require(0 <= lo <= hi < self.n)
    lo, hi, result = lo + self.n, hi + self.n + 1, None
    while lo < hi:
      if lo & 1:
        result = self.tree[lo] if result is None else max(result, self.tree[lo])
        lo += 1
      if hi & 1:
        hi -= 1
        result = self.tree[hi] if result is None else max(result, self.tree[hi])
      lo, hi = lo // 2, hi // 2
    return result


class IntegerTables:
  """Sorted equal-score transitions; no N-by-T prediction matrix or float subtotal."""

  def __init__(self, population):
    population.verify()
    self.domain = threshold_sets(population)
    self.rows = []
    for context in (0, 1):
      indices = np.flatnonzero(population.context == context)
      indices = indices[np.argsort(population.score[indices], kind='stable')]
      score = population.score[indices]
      current, target = population.current[indices], population.target[indices]
      move = target != current
      # Each transition is a difference between two exact per-row integer contributions.
      def contribution(i, opened, indices=indices, current=current, target=target, move=move):
        changed = population.projected_move[indices[i]] if opened else current[i]
        return (int(changed == target[i]), int(abs(int(changed) - int(target[i])) <= 1),
                int(not move[i] and changed != current[i]), int(move[i] and opened), int(not move[i] and not opened),
                int(not move[i] and opened), int(move[i] and not opened), int(opened))
      initial_gate = score > 0.
      final = np.where(initial_gate, population.projected_move[indices], current)
      state = counts(move, initial_gate, current, target, final)
      cursor = int(np.count_nonzero(score <= 0.))
      table = []
      for threshold in self.domain[context]:
        while cursor < len(indices) and score[cursor] <= threshold:
          before, after = contribution(cursor, True), contribution(cursor, False)
          for key, a, b in zip(COUNT_FIELDS, before, after, strict=True):
            state[key] += b - a
          cursor += 1
        table.append(state.copy())
      self.rows.append(table)
    self.cache = {}

  def upper(self, rectangle, field, sign=1):
    require(field in COUNT_FIELDS and sign in (-1, 1))
    key = (field, sign)
    if key not in self.cache:
      self.cache[key] = [RangeMaximum([sign * row[field] for row in context]) for context in self.rows]
    a, b, c, d = rectangle
    return self.cache[key][0].query(a, b) + self.cache[key][1].query(c, d)

  def pair(self, indices):
    return [float(self.domain[c][indices[c]]) for c in (0, 1)]

  def additive(self, indices):
    return {k: self.rows[0][indices[0]][k] + self.rows[1][indices[1]][k] for k in COUNT_FIELDS}
