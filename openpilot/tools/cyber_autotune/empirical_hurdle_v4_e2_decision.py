"""Frozen D2 TRAIN-only selection. Numeric arrays only; no I/O, model fit or DEV."""

import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_decision as e1
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_execution as frozen

need = e1.need
JOBS = e1.JOBS
MAX_COUNT = e1.MAX_COUNT
CONTEXTS = ('PREVIOUS_STATIC', 'PREVIOUS_MOVE')


def count(counters, name, rows=0):
  counters[name] = counters.get(name, 0) + 1
  if rows:
    counters[name + '_rows'] = counters.get(name + '_rows', 0) + rows


def byte_equal(a, b):
  return a.dtype == b.dtype and a.shape == b.shape and a.tobytes(order='C') == b.tobytes(order='C')


def validate(p, y, prior=None):
  e1.probability(p)
  need(isinstance(y, np.ndarray) and y.dtype == np.bool_ and y.shape == p.shape, 'E2_BINARY_LABEL_DTYPE_CONFLICT')
  if prior is not None:
    need(isinstance(prior, np.ndarray) and prior.dtype == np.int64 and prior.shape == p.shape, 'E2_PRIOR_DTYPE_CONFLICT')


def reconstruct_D0(p, y, *, role, counters):
  need(role == 'TRAIN', 'E2_TRAIN_ONLY_REQUIRED')
  validate(p, y)
  selected = frozen.m.threshold(p, y, role='TRAIN')
  count(counters, 'D0_TRAIN_reconstruction_calls')
  return selected


def potentials(blocks, candidate, stage2, p, y, prior, D0_decision, expected, counters):
  """All-row fixed512 segment chunks, then byte-exact subset qualifications."""
  validate(p, y, prior)
  need(type(D0_decision) is float and 0 <= D0_decision <= 1)
  design, current, target, deltas, moves = [], [], [], [], []
  n = 0
  gate = p > D0_decision
  for segment, indices in blocks:
    x = frozen.m.features(segment, indices, candidate)
    c, t = segment['tick'][indices].astype(np.int64), segment['tick'][indices + 1].astype(np.int64)
    need(n + len(x) <= len(p), 'E2_TRAIN_POPULATION_CONFLICT')
    local_u, local_move = np.empty(len(x), np.float64), np.empty(len(x), np.int64)
    for start in range(0, len(x), frozen.m.CHUNK):
      stop = min(start + frozen.m.CHUNK, len(x))
      part = np.ascontiguousarray(x[start:stop])
      u = frozen.m.predict_delta(part, stage2)
      count(counters, 'TRAIN_counterfactual_Stage2_calls', len(part))
      local_u[start:stop] = u
      local_move[start:stop] = frozen.m.project(c[start:stop].astype(np.float64) + u)
      count(counters, 'TRAIN_potential_projection_calls', len(part))
      mask = gate[n + start : n + stop]
      if np.any(mask):
        subset = frozen.m.predict_delta(np.ascontiguousarray(part[mask]), stage2)
        count(counters, 'D0_chunk_subset_qualification_calls', int(np.count_nonzero(mask)))
        need(byte_equal(subset, u[mask]), 'E2_D0_TRAIN_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED')
    design.append(x)
    current.append(c)
    target.append(t)
    deltas.append(local_u)
    moves.append(local_move)
    n += len(x)
  need(n == len(p) == expected['count'], 'E2_TRAIN_POPULATION_CONFLICT')
  x = np.ascontiguousarray(np.concatenate(design))
  c, t, u, move = map(np.concatenate, (current, target, deltas, moves))
  need(np.array_equal(x[:, -3], prior) and np.array_equal(t != c, y), 'E2_TRAIN_RECORDED_ORDER_CONFLICT')
  need(x.dtype == np.float64 and x.shape == (len(p), expected['feature_dimension']))
  frozen.m.finite(x, u)
  need(bool(np.all((c >= -32768) & (c <= 32767) & (t >= -32768) & (t <= 32767))), 'E2_TRAIN_TICK_RANGE')
  # Frozen original integrated source would call predict_delta on x[gate].
  if np.any(gate):
    original = frozen.m.predict_delta(np.ascontiguousarray(x[gate]), stage2)
    count(counters, 'D0_full_subset_qualification_calls', int(np.count_nonzero(gate)))
    need(byte_equal(original, u[gate]), 'E2_D0_TRAIN_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED')
  count(counters, 'TRAIN_numerical_qualification_jobs')
  return {'p': p, 'y': y, 'prior': prior, 'current': c, 'target': t, 'u': u, 'move_tick': move, 'D0_gate': gate}


class LossTree:
  """Four original-row loss channels with fixed pairwise binary64 topology."""

  def __init__(self, leaves):
    need(isinstance(leaves, np.ndarray) and leaves.dtype == np.float64 and leaves.ndim == 2 and leaves.shape[1] == 4)
    need(0 < len(leaves) <= MAX_COUNT and bool(np.all(np.isfinite(leaves))), 'E2_NONFINITE_LOSS')
    self.n = len(leaves)
    self.width = 1 << (self.n - 1).bit_length()
    self.values = np.zeros((2 * self.width, 4), np.float64)
    self.values[self.width : self.width + self.n] = leaves
    width = self.width
    with np.errstate(over='raise', invalid='raise'):
      while width > 1:
        self.values[width // 2 : width] = self.values[width : 2 * width : 2] + self.values[width + 1 : 2 * width : 2]
        width //= 2
    need(bool(np.all(np.isfinite(self.values[1]))), 'E2_NONFINITE_LOSS')

  @property
  def root(self):
    return self.values[1]

  def replace(self, row, leaves):
    need(type(row) is int and 0 <= row < self.n and leaves.dtype == np.float64 and leaves.shape == (4,))
    need(bool(np.all(np.isfinite(leaves))), 'E2_NONFINITE_LOSS')
    j = self.width + row
    self.values[j] = leaves
    with np.errstate(over='raise', invalid='raise'):
      j //= 2
      while j:
        self.values[j] = self.values[2 * j] + self.values[2 * j + 1]
        j //= 2
    need(bool(np.all(np.isfinite(self.root))), 'E2_NONFINITE_LOSS')


def leaf_losses(delta, actual, truth):
  with np.errstate(over='raise', invalid='raise'):
    error = delta - actual
    square, absolute = error * error, np.abs(error)
  leaves = np.column_stack((square, absolute, np.where(truth, square, 0.0), np.where(truth, absolute, 0.0)))
  need(leaves.dtype == np.float64 and bool(np.all(np.isfinite(leaves))), 'E2_NONFINITE_LOSS')
  return leaves


def select_context(p, y, current, target, u, move_tick, D0_decision, *, role):
  need(role == 'TRAIN', 'E2_TRAIN_ONLY_REQUIRED')
  validate(p, y)
  n = len(p)
  need(all(isinstance(a, np.ndarray) and a.shape == (n,) for a in (current, target, u, move_tick)))
  need(current.dtype == target.dtype == move_tick.dtype == np.int64 and u.dtype == np.float64, 'E2_TRAIN_DTYPE_CONFLICT')
  need(np.array_equal(target != current, y), 'E2_TRAIN_LABEL_CONFLICT')
  need(bool(np.all(np.isfinite(u))) and bool(np.all((current >= -32768) & (current <= 32767))))
  need(bool(np.all((target >= -32768) & (target <= 32767))))
  need(byte_equal(frozen.m.project(current.astype(np.float64) + u), move_tick), 'E2_TRAIN_POTENTIAL_CONFLICT')
  positives, negatives = int(np.count_nonzero(y)), int(np.count_nonzero(~y))
  need(positives > 0 and negatives > 0, 'E2_TRAIN_CLASS_MISSING')
  need(type(D0_decision) is float and np.isfinite(D0_decision) and 0 <= D0_decision <= 1)
  actual = (target - current).astype(np.float64)
  hold_leaves = leaf_losses(np.zeros(n, np.float64), actual, y)
  move_leaves = leaf_losses(u, actual, y)
  old_gate = p > D0_decision
  old_tree = LossTree(np.where(old_gate[:, None], move_leaves, hold_leaves))
  old_loss = old_tree.root.copy()
  del old_tree
  old_tp = int(np.count_nonzero(old_gate & y))
  harmful = ~y & (move_tick != current)
  old_harm = int(np.count_nonzero(old_gate & harmful))
  hold_hit = current == target
  gain = (move_tick == target).astype(np.int8) - hold_hit.astype(np.int8)
  old_gain = sum(map(int, gain[old_gate]))
  tree = LossTree(move_leaves)
  tp, harm, net_gain = positives, int(np.count_nonzero(harmful)), sum(map(int, gain))
  order = np.argsort(p, kind='stable')
  sorted_p = p[order]
  values, first, sizes = np.unique(sorted_p, return_index=True, return_counts=True)
  candidates = np.union1d(values, np.array([0.0, 1.0]))
  witness = max(0.0, float(np.max(p[p <= D0_decision], initial=0.0)))
  group, best, selected, feasible, witness_verified = 0, None, None, 0, False
  for raw_value in candidates:
    value = 0.0 if raw_value == 0 else float(raw_value)
    while group < len(values) and values[group] <= value:
      rows = order[first[group] : first[group] + sizes[group]]
      tp -= int(np.count_nonzero(y[rows]))
      harm -= int(np.count_nonzero(harmful[rows]))
      net_gain -= sum(map(int, gain[rows]))
      for row in rows:
        tree.replace(int(row), hold_leaves[row])
      group += 1
    loss = tree.root
    if value == witness:
      need(
        np.array_equal(p > value, old_gate) and byte_equal(loss, old_loss) and tp == old_tp and harm == old_harm and net_gain == old_gain,
        'D2_TRAIN_FEASIBILITY_CONTRACT_UNRESOLVED',
      )
      witness_verified = True
    guards = {
      'TRUE_MOVE_TP': tp >= old_tp,
      'TRUE_MOVE_SSE': bool(loss[2] <= old_loss[2]),
      'TRUE_MOVE_SAE': bool(loss[3] <= old_loss[3]),
      'HARMFUL_STATIC': harm <= old_harm,
    }
    if not all(guards.values()):
      continue
    feasible += 1
    key = net_gain, -float(loss[0]), -float(loss[1]), -harm, value
    if best is None or key > best:
      best = key
      selected = {
        'decision': value,
        'net_exact_hit_gain': net_gain,
        'continuous_sse': float(loss[0]),
        'continuous_sae': float(loss[1]),
        'TRUE_MOVE_TP': tp,
        'TRUE_MOVE_SSE': float(loss[2]),
        'TRUE_MOVE_SAE': float(loss[3]),
        'harmful_static': harm,
        'guards': guards,
      }
  need(witness_verified and selected is not None and selected['net_exact_hit_gain'] >= old_gain, 'D2_TRAIN_FEASIBILITY_CONTRACT_UNRESOLVED')
  return {
    **selected,
    'count': n,
    'positive': positives,
    'negative': negatives,
    'candidate_count': len(candidates),
    'feasible_count': feasible,
    'witness_verified': True,
    'D0_reference': {
      'TP': old_tp,
      'TRUE_MOVE_SSE': float(old_loss[2]),
      'TRUE_MOVE_SAE': float(old_loss[3]),
      'harmful_static': old_harm,
      'net_exact_hit_gain': old_gain,
    },
  }


def select_job(cache, D0_decision, *, candidate, fold, anchor, counters):
  need((candidate, fold) in JOBS and type(anchor) is str and len(anchor) == 64)
  contexts = {}
  for state, name in enumerate(CONTEXTS):
    mask = (cache['prior'] != 0) == state
    arrays = [cache[k][mask] for k in ('p', 'y', 'current', 'target', 'u', 'move_tick')]
    contexts[name] = select_context(*arrays, D0_decision, role='TRAIN')
    count(counters, 'D2_context_decision_selection_calls')
  return {
    'candidate_id': candidate,
    'fold': fold,
    'anchor_sha256': anchor,
    'count': len(cache['p']),
    'contexts': contexts,
    'D0_reconstructed_decision': D0_decision,
    'historical_TRAIN_gate': 'NOT_SAVED',
    'new_D0_gate': 'NEW_E2_RECONSTRUCTED_D0_TRAIN_GATE',
  }
