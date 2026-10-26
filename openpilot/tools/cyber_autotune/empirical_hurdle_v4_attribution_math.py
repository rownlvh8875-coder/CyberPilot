"""Deterministic reductions of saved V4 evidence, without model execution."""

from collections import Counter
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_math as old
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_attribution_math as v2

count = old.count
CONTEXTS = ('PREV_STATIC_TRUE_STATIC', 'PREV_STATIC_MOVE_ONSET', 'PREV_MOVE_TRUE_STATIC', 'PREV_MOVE_MOVE_CONTINUATION')


def require(value):
  old.require(value, 'V4_ATTRIBUTION_INPUT_CONFLICT')


def support(n):
  return 'EMPTY' if n == 0 else ('SMALL_SUPPORT_DESCRIPTIVE_ONLY' if n < 201 else 'FULL_DESCRIPTIVE_SUPPORT')


def ranking(probability, move):
  probability, move = np.asarray(probability), np.asarray(move)
  require(probability.dtype == np.float64 and move.dtype == np.bool_ and probability.ndim == 1 and probability.shape == move.shape)
  require(np.isfinite(probability).all() and np.all((probability >= 0) & (probability <= 1)))
  if not len(move) or not move.any() or move.all():
    return {
      'status': 'INPUT_INSUFFICIENT',
      'reason': 'AUC_REQUIRES_BOTH_CLASSES',
      'count': len(move),
      'positive_count': count(move),
      'negative_count': count(~move),
    }
  return {'status': 'COMPLETE', **v2.ranking(probability, move)}


def rankings(probability, move, previous):
  require(previous.dtype == np.bool_ and previous.shape == move.shape)
  return {
    name: ranking(probability[mask], move[mask]) for name, mask in (('OVERALL', np.ones(len(move), bool)), ('PREV_STATIC', ~previous), ('PREV_MOVE', previous))
  }


def rank_compare(current, historical):
  if current['status'] != 'COMPLETE' or historical['status'] != 'COMPLETE':
    return 'INPUT_INSUFFICIENT'
  diff = current['auc_num2'] * historical['auc_den2'] - historical['auc_num2'] * current['auc_den2']
  return 'V4_RANK_IMPROVED' if diff > 0 else ('V4_RANK_DECREASED' if diff < 0 else 'V4_RANK_EQUAL')


def transfer(train, dev):
  if train['status'] != 'COMPLETE' or dev['status'] != 'COMPLETE':
    return {'status': 'INPUT_INSUFFICIENT', 'train': train, 'development': dev}
  keys = ('auc', 'mean_probability', 'true_move_prevalence', 'calibration_bias', 'brier', 'move_score_mean', 'static_score_mean', 'score_mean_gap')
  return {
    'status': 'COMPLETE',
    'train': train,
    'development': dev,
    'dev_minus_train_auc': dev['auc'] - train['auc'],
    'dev_minus_train': {k: dev[k] - train[k] for k in keys},
    'rank_comparison': rank_compare(dev, train),
  }


def one_step(current, target, gate, projected, delta, error, hold, previous):
  require(all(np.asarray(x).dtype.kind in 'iu' for x in (current, target, projected)))
  current, target, projected = (np.asarray(v, np.int64) for v in (current, target, projected))
  require(current.ndim == 1 and len(current) > 0 and all(v.shape == current.shape for v in (target, gate, projected, delta, error, hold, previous)))
  require(gate.dtype == previous.dtype == np.bool_)
  require(all(v.dtype == np.float64 and np.isfinite(v).all() for v in (delta, error, hold)))
  actual = target - current
  move, realized = actual != 0, projected != current
  require((delta - actual.astype(float)).tobytes() == error.tobytes() and (-actual.astype(float)).tobytes() == hold.tobytes())
  require(np.all(delta[~gate] == 0) and np.array_equal(projected[~gate], current[~gate]))
  hit = v2.hit_counts(current, target, projected)
  hit.update(static_truth_count=count(~move), move_truth_count=count(move))
  fp, harmful = ~move & gate, ~move & realized
  require(np.all(~harmful | fp))
  static = {
    'gate_fp': count(fp),
    'harmful_false_movement': count(harmful),
    'gate_fp_projected_hold': count(fp & ~realized),
    'harmful_fraction_of_fp': count(harmful) / count(fp) if fp.any() else None,
    'false_projected_motion_magnitude': old.metrics((projected - current)[harmful]),
  }
  masks = ((~previous & ~move), (~previous & move), (previous & ~move), (previous & move))
  contexts = {
    name: {
      'count': count(mask),
      'true_move_prevalence': count(mask & move) / count(mask) if mask.any() else None,
      'confusion': old.confusion(move[mask], gate[mask]),
      'harmful_false_movement': count(mask & harmful),
    }
    for name, mask in zip(CONTEXTS, masks, strict=True)
  }
  parts = {}
  for label, mask in (('TP', move & gate), ('FN', move & ~gate)):
    parts[label] = {
      'count': count(mask),
      'one_tick_count': count(mask & (np.abs(actual) == 1)),
      'multi_tick_count': count(mask & (np.abs(actual) >= 2)),
      'positive_count': count(mask & (actual > 0)),
      'negative_count': count(mask & (actual < 0)),
      'exact_count': count(mask & (projected == target)),
      'within_one_tick_count': count(mask & (np.abs(projected - target) <= 1)),
      'signed_delta_error_mean': float(np.mean(error[mask])) if mask.any() else None,
      'continuous_delta_error': old.metrics(error[mask]),
      'projected_tick_error': old.metrics((projected - target)[mask]),
    }
  parts['FN']['hold_identity_exact'] = True
  return {
    'exact_hit': hit,
    'static': static,
    'confusion': old.confusion(move, gate),
    'move': parts,
    'contexts': contexts,
    'continuous_error_metrics': old.metrics(error),
    'true_move_continuous_error_metrics': old.metrics(error[move]),
    'projected_tick_error_metrics': old.metrics(projected - target),
    'identities_exact': True,
  }


class IntegerHistogram:
  """Exact integer sufficient statistics; memory depends on distinct values, not rows."""

  def __init__(self):
    self.values = Counter()

  def add(self, values):
    values = np.asarray(values)
    require(values.dtype.kind in 'biu')
    keys, counts = np.unique(values, return_counts=True)
    self.values.update({int(k): int(n) for k, n in zip(keys, counts, strict=True)})

  def quantile(self, fraction):
    n = sum(self.values.values())
    if not n:
      return None
    position = (n - 1) * fraction
    lo, hi = int(np.floor(position)), int(np.ceil(position))
    a = b = None
    total = 0
    for value, number in sorted(self.values.items()):
      if a is None and total + number > lo:
        a = value
      if total + number > hi:
        b = value
        break
      total += number
    gamma = position - lo
    return float(b - (b - a) * (1 - gamma) if gamma >= 0.5 else a + (b - a) * gamma)

  def summary(self):
    n = sum(self.values.values())
    return {
      'count': n,
      'min': min(self.values) if n else None,
      'median': self.quantile(0.5),
      'p95': self.quantile(0.95),
      'max': max(self.values) if n else None,
    }

  def metrics(self):
    n = sum(self.values.values())
    if not n:
      return None
    absolute = IntegerHistogram()
    for value, number in self.values.items():
      absolute.values[abs(value)] += number
    sae = sum(abs(v) * number for v, number in self.values.items())
    sse = sum(v * v * number for v, number in self.values.items())
    signed = sum(v * number for v, number in self.values.items())
    return {
      'count': n,
      'signed_sum': signed,
      'sae': sae,
      'sse': sse,
      'mae': sae / n,
      'rmse': float(np.sqrt(sse / n)),
      'p95': absolute.quantile(0.95),
      'exact_count': self.values[0],
      'within_one_tick_count': sum(self.values[v] for v in (-1, 0, 1)),
    }


def add_streaks(histogram, values):
  require(values.ndim == 2 and values.dtype == np.bool_)
  edges = np.diff(np.pad(values.astype(np.int8), ((0, 0), (1, 1))), axis=1)
  starts, ends = np.nonzero(edges == 1), np.nonzero(edges == -1)
  require(np.array_equal(starts[0], ends[0]))
  histogram.add(ends[1] - starts[1])


def first(mask):
  return np.where(np.any(mask, axis=1), np.argmax(mask, axis=1) + 1, 0).astype(np.int64)


def bands(h):
  return {
    25: ((1, 5), (6, 10), (11, 25)),
    50: ((1, 10), (11, 25), (26, 50)),
    100: ((1, 25), (26, 50), (51, 100)),
    200: ((1, 25), (26, 50), (51, 100), (101, 200)),
  }.get(h, ((1, h),))


class PathAccumulator:
  """Streaming saved integer paths; never emits or duplicates scientific arrays."""

  def __init__(self, horizon):
    require(type(horizon) is int and horizon > 0)
    self.h = horizon
    self.n = self.context_count = self.hold_gate = 0
    self.gate = Counter(dict.fromkeys(('TN', 'FP', 'FN', 'TP'), 0))
    self.movement = self.gate.copy()
    self.band_counts = {f'{lo}-{hi}': self.gate.copy() for lo, hi in bands(horizon)}
    self.classes = {k: IntegerHistogram() for k in self.gate}
    self.fp_hold, self.fp_move = IntegerHistogram(), IntegerHistogram()
    self.tp_context = {k: IntegerHistogram() for k in ('ONSET', 'CONTINUATION')}
    self.events = {k: IntegerHistogram() for k in ('gate_mismatch', 'projected_movement_mismatch', 'context_divergence', 'tick_path_departure')}
    self.streaks = {k: IntegerHistogram() for k in ('true_move_streak', 'predicted_gate_move', 'projected_move', 'observed_context', 'projected_context')}
    names = (
      'ALL',
      'PATH_MOVED',
      'GATE_PERFECT',
      'GATE_PERFECT_PATH_MOVED',
      'PROJECTED_MOVEMENT_PATTERN_PERFECT',
      'PROJECTED_MOVEMENT_PATTERN_PERFECT_PATH_MOVED',
      'NO_CONTEXT_DIVERGENCE',
      'EARLY_CONTEXT_DIVERGENCE',
      'LATE_CONTEXT_DIVERGENCE',
    )
    self.subsets = {k: (IntegerHistogram(), IntegerHistogram()) for k in names}
    self.feedback = {
      k: Counter(numerator=0, denominator=0)
      for k in ('gate_after_projected_move', 'gate_after_projected_static', 'true_after_true_move', 'true_after_true_static')
    }

  def add(self, observed, projected, gate, error, hold, initial):
    require(observed.dtype.kind in 'iu' and projected.dtype.kind in 'iu')
    observed, projected = observed.astype(np.int64), projected.astype(np.int64)
    n = len(observed)
    require(observed.shape == projected.shape == (n, self.h + 1) and gate.shape == (n, self.h) and gate.dtype == np.bool_)
    require(error.dtype == hold.dtype == np.float64 and error.shape == hold.shape == initial.shape == (n,) and initial.dtype == np.bool_)
    require(np.array_equal(observed[:, 0], projected[:, 0]))
    actual, predicted = np.diff(observed, axis=1), np.diff(projected, axis=1)
    move, realized = actual != 0, predicted != 0
    step_error = predicted - actual
    terminal = projected[:, -1] - observed[:, -1]
    baseline = observed[:, 0] - observed[:, -1]
    require(np.array_equal(terminal.astype(float), error) and np.array_equal(baseline.astype(float), hold))
    require(np.array_equal(step_error.sum(axis=1), terminal) and np.all(predicted[~gate] == 0))
    oz = np.column_stack((initial, move[:, :-1]))
    pz = np.column_stack((initial, realized[:, :-1]))
    divergence = oz != pz
    require(np.array_equal(divergence[:, 1:], (move != realized)[:, :-1]) and not divergence[:, 0].any())
    self.n += n
    self.context_count += count(divergence[:, 1:])
    self.hold_gate += count(gate & ~realized)
    masks = {'TN': ~move & ~gate, 'FP': ~move & gate, 'FN': move & ~gate, 'TP': move & gate}
    mc = old.confusion(move, realized)['counts']
    self.movement.update(mc)
    for k, mask in masks.items():
      self.gate[k] += count(mask)
      self.classes[k].add(step_error[mask])
      for lo, hi in bands(self.h):
        self.band_counts[f'{lo}-{hi}'][k] += count(mask[:, lo - 1 : hi])
    self.fp_hold.add(predicted[masks['FP'] & ~realized])
    self.fp_move.add(predicted[masks['FP'] & realized])
    for k, mask in (('ONSET', ~oz), ('CONTINUATION', oz)):
      self.tp_context[k].add(step_error[masks['TP'] & mask])
    firsts = {
      'gate_mismatch': first(gate != move),
      'projected_movement_mismatch': first(realized != move),
      'context_divergence': first(divergence),
      'tick_path_departure': first(projected[:, 1:] != observed[:, 1:]),
    }
    for k, values in firsts.items():
      self.events[k].add(values)
    moved = np.any(move, axis=1)
    gp, mp = firsts['gate_mismatch'] == 0, firsts['projected_movement_mismatch'] == 0
    fd = firsts['context_divergence']
    subset_masks = {
      'ALL': np.ones(n, bool),
      'PATH_MOVED': moved,
      'GATE_PERFECT': gp,
      'GATE_PERFECT_PATH_MOVED': gp & moved,
      'PROJECTED_MOVEMENT_PATTERN_PERFECT': mp,
      'PROJECTED_MOVEMENT_PATTERN_PERFECT_PATH_MOVED': mp & moved,
      'NO_CONTEXT_DIVERGENCE': fd == 0,
      'EARLY_CONTEXT_DIVERGENCE': (fd > 0) & (4 * fd <= self.h),
      'LATE_CONTEXT_DIVERGENCE': 4 * fd > self.h,
    }
    for k, mask in subset_masks.items():
      self.subsets[k][0].add(terminal[mask])
      self.subsets[k][1].add(baseline[mask])
    for k, values in (
      ('true_move_streak', move),
      ('predicted_gate_move', gate),
      ('projected_move', realized),
      ('observed_context', oz),
      ('projected_context', pz),
    ):
      add_streaks(self.streaks[k], values)
    for k, condition, outcome in (
      ('gate_after_projected_move', realized[:, :-1], gate[:, 1:]),
      ('gate_after_projected_static', ~realized[:, :-1], gate[:, 1:]),
      ('true_after_true_move', move[:, :-1], move[:, 1:]),
      ('true_after_true_static', ~move[:, :-1], move[:, 1:]),
    ):
      self.feedback[k].update(numerator=count(condition & outcome), denominator=count(condition))

  def finish(self):
    def pair(histograms):
      c, b = (h.metrics() for h in histograms)
      n = c['count'] if c else 0
      return {'count': n, 'support_status': support(n), 'candidate': c, 'hold_last': b}

    events = {k: {**v.summary(), 'none_count': v.values[0], 'histogram': {str(x): n for x, n in sorted(v.values.items())}} for k, v in self.events.items()}
    return {
      'count': self.n,
      'horizon': self.h,
      'terminal_error_identity_exact': True,
      'context_identity_exact': True,
      'gate': old.confusion_counts(self.gate),
      'movement': old.confusion_counts(self.movement),
      'step_bands': {k: old.confusion_counts(v) for k, v in self.band_counts.items()},
      'gate_move_projected_hold_count': self.hold_gate,
      'context_divergence': {
        'count': self.context_count,
        'eligible_steps': self.n * (self.h - 1),
        'rate': self.context_count / (self.n * (self.h - 1)) if self.n and self.h > 1 else None,
        'identity': 'DIVERGENCE_AT_STEP_h_EQUALS_MOVEMENT_PATTERN_MISMATCH_AT_STEP_h_MINUS_1',
      },
      'first_events': events,
      'classes': {k: v.metrics() for k, v in self.classes.items()},
      'static_fp': {'projected_hold': self.fp_hold.metrics(), 'projected_move': self.fp_move.metrics()},
      'tp_magnitude': {k: v.metrics() for k, v in self.tp_context.items()},
      'subsets': {k: pair(v) for k, v in self.subsets.items()},
      'streaks': {k: {**v.summary(), 'histogram': {str(x): n for x, n in sorted(v.values.items())}} for k, v in self.streaks.items()},
      'feedback': {k: {**v, 'probability': v['numerator'] / v['denominator'] if v['denominator'] else None} for k, v in self.feedback.items()},
      'interpretation': 'DESCRIPTIVE_ASSOCIATION_ONLY; STEP_SAE_SSE_DO_NOT_ADD_TO_TERMINAL_RMSE',
    }
