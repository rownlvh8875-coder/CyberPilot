"""Descriptive reductions of stored evidence; no model or decision execution."""

import numpy as np

SUPPORT = 201
CHUNK = 512


def require(condition, message='HURDLE_ATTRIBUTION_INPUT_CONFLICT'):
  if not condition:
    raise ValueError(message)


def count(mask):
  return int(np.count_nonzero(mask))


def summary(values):
  values = np.ascontiguousarray(values)
  if not len(values):
    return {'count': 0, 'min': None, 'median': None, 'p95': None, 'max': None}
  require(bool(np.isfinite(values).all()))
  return {
    'count': len(values),
    'min': float(np.min(values)),
    'median': float(np.median(values)),
    'p95': float(np.percentile(values, 95, method='linear')),
    'max': float(np.max(values)),
  }


def metrics(error, projected=None, target=None):
  error = np.ascontiguousarray(error, dtype=np.float64)
  require(error.ndim == 1 and bool(np.isfinite(error).all()))
  if not len(error):
    return None
  absolute = np.abs(error)
  result = {
    'rmse': float(np.sqrt(np.mean(error * error))),
    'mae': float(np.mean(absolute)),
    'p95': float(np.percentile(absolute, 95, method='linear')),
    'sae': float(np.sum(absolute)),
    'sse': float(np.sum(error * error)),
  }
  if projected is not None:
    require(projected.shape == target.shape == error.shape)
    distance = np.abs(projected - target)
    result.update(
      exact_hit_count=count(distance == 0),
      within_one_tick_count=count(distance <= 1),
      exact_hit=count(distance == 0) / len(error),
      within_one_tick=count(distance <= 1) / len(error),
    )
  require(all(np.isfinite(v) for v in result.values()))
  return result


def pair(error, hold, projected=None, target=None, current=None):
  require(error.shape == hold.shape)
  c, b = metrics(error, projected, target), metrics(hold, current, target)
  return {
    'count': len(error),
    'support_status': 'EMPTY' if not len(error) else ('SMALL_SUPPORT_DESCRIPTIVE_ONLY' if len(error) < SUPPORT else 'DESCRIPTIVE_ONLY'),
    'candidate': c,
    'hold_last': b,
    'delta_sae': None if c is None else c['sae'] - b['sae'],
    'delta_sse': None if c is None else c['sse'] - b['sse'],
  }


def confusion_counts(counts):
  tn, fp, fn, tp = (int(counts[k]) for k in ('TN', 'FP', 'FN', 'TP'))
  require(min(tn, fp, fn, tp) >= 0)
  n, positives, negatives = tn + fp + fn + tp, tp + fn, tn + fp

  def ratio(x, d):
    return x / d if d else None

  recall, specificity = ratio(tp, positives), ratio(tn, negatives)
  return {
    'counts': {'TN': tn, 'FP': fp, 'FN': fn, 'TP': tp},
    'count': n,
    'fractions': {k: ratio(int(v), n) for k, v in counts.items()},
    'true_move_fraction': ratio(positives, n),
    'predicted_move_fraction': ratio(tp + fp, n),
    'false_move_rate': ratio(fp, negatives),
    'missed_move_rate': ratio(fn, positives),
    'precision': ratio(tp, tp + fp),
    'recall': recall,
    'specificity': specificity,
    'balanced_accuracy': None if recall is None or specificity is None else 0.5 * (recall + specificity),
  }


def confusion(truth, gate):
  require(truth.dtype == gate.dtype == np.bool_ and truth.shape == gate.shape)
  return confusion_counts({'TN': count(~truth & ~gate), 'FP': count(~truth & gate), 'FN': count(truth & ~gate), 'TP': count(truth & gate)})


def transfer(train, dev):
  names = ('false_move_rate', 'missed_move_rate', 'recall', 'specificity', 'balanced_accuracy')
  require(all(train[k] is not None and dev[k] is not None for k in names))
  return {
    'train': train,
    'development': dev,
    'dev_minus_train': {k: dev[k] - train[k] for k in names},
    'threshold_lineage': 'SAME_FROZEN_TRAIN_THRESHOLD',
    'alternative_thresholds_evaluated': 0,
  }


def partition_accounting(error, hold, masks):
  """Row-exact reconciliation, retaining float reduction-order residuals, no tolerance."""
  coverage = sum(mask.astype(np.int8) for mask in masks)
  require(bool(np.all(coverage == 1)))
  result = {'row_partition_exact': True, 'count': len(error), 'classes_count': [count(m) for m in masks]}
  for label, values in (('candidate', error), ('hold_last', hold)):
    result[label] = {}
    for name, terms in (('sae', np.abs(values)), ('sse', values * values)):
      # Scatter the disjoint contributions back into original anchor order.
      restored = np.empty_like(terms)
      for mask in masks:
        restored[mask] = terms[mask]
      require(restored.tobytes() == terms.tobytes())
      original = float(np.sum(terms))
      partitioned = float(sum(float(np.sum(terms[m])) for m in masks))
      result[label][name] = {
        'original_anchor_order': original,
        'partition_order': partitioned,
        'partition_minus_original': partitioned - original,
        'contribution_bytes_exact': True,
      }
  return result


def one_step(arrays):
  a = arrays
  actual, current, target = (a[k] for k in ('actual_delta_tick', 'current_tick', 'target_next_tick'))
  gate, projected = a['predicted_gate'], a['projected_next_tick']
  delta, error, hold = (a[k] for k in ('integrated_delta', 'candidate_error', 'comparator_error'))
  require(actual.dtype == current.dtype == target.dtype == projected.dtype == np.int64)
  require(gate.dtype == np.bool_ and all(v.shape == actual.shape for v in (current, target, gate, projected, delta, error, hold)))
  require(actual.ndim == 1 and len(actual) > 0 and error.dtype == hold.dtype == delta.dtype == np.float64)
  move = actual != 0
  require(count(move) > 0 and count(~move) > 0)
  require(np.array_equal(actual, target - current) and np.array_equal(a['true_move'], move))
  require(np.array_equal(a['hold_last_next_tick'], current))
  require(error.tobytes() == (delta - actual.astype(np.float64)).tobytes())
  require(hold.tobytes() == (-actual.astype(np.float64)).tobytes())
  require(bool(np.all(delta[~gate] == 0)) and np.array_equal(projected[~gate], current[~gate]))
  tn, fp, fn, tp = ~move & ~gate, ~move & gate, move & ~gate, move & gate
  moved = projected != current
  classes = {
    'ALL': np.ones(len(actual), dtype=bool),
    'STATIC': ~move,
    'MOVE': move,
    'MOVE_POSITIVE': actual > 0,
    'MOVE_NEGATIVE': actual < 0,
    'ONE_TICK_MOVE': np.abs(actual) == 1,
    'MULTI_TICK_MOVE': np.abs(actual) >= 2,
    'TN': tn,
    'FP_PROJECTED_HOLD': fp & ~moved,
    'FP_PROJECTED_MOVE': fp & moved,
    'FN': fn,
    'TP': tp,
  }
  require(count(classes['MOVE_POSITIVE']) + count(classes['MOVE_NEGATIVE']) == count(move))
  require(count(classes['ONE_TICK_MOVE']) + count(classes['MULTI_TICK_MOVE']) == count(move))
  measures = {k: pair(error[m], hold[m], projected[m], target[m], current[m]) for k, m in classes.items()}
  for label in ('MOVE', 'TP'):
    m = classes[label]
    measures[label]['continuous_sign_accuracy'] = float(np.mean(np.sign(delta[m]) == np.sign(actual[m]))) if count(m) else None
    measures[label]['projected_sign_accuracy'] = float(np.mean(np.sign(projected[m] - current[m]) == np.sign(actual[m]))) if count(m) else None
  hit, basehit = projected == target, current == target
  hits = {
    'candidate_static_hits': count(hit & ~move),
    'hold_static_hits': count(basehit & ~move),
    'candidate_move_hits': count(hit & move),
    'hold_move_hits': count(basehit & move),
    'candidate_total_hits': count(hit),
    'hold_total_hits': count(basehit),
  }
  hits.update(
    static_hit_loss=hits['hold_static_hits'] - hits['candidate_static_hits'],
    move_hit_gain=hits['candidate_move_hits'] - hits['hold_move_hits'],
    net_hit_delta=hits['candidate_total_hits'] - hits['hold_total_hits'],
  )
  require(hits['net_hit_delta'] == hits['move_hit_gain'] - hits['static_hit_loss'])
  require(hits['hold_static_hits'] == count(~move) and bool(np.all(hold[~move] == 0)))
  hits['integer_accounting_exact'] = True
  hits['static_loss_exceeds_move_gain'] = hits['static_hit_loss'] > hits['move_hit_gain']
  oracle = a['stage2_oracle_move_prediction']
  require(oracle.shape == (count(move),) and bool(np.isfinite(oracle).all()))
  oracle_error = oracle - actual[move].astype(np.float64)
  oracle_metrics = metrics(oracle_error)
  integrated = measures['MOVE']['candidate']
  fn_equal = error[fn].tobytes() == hold[fn].tobytes()
  require(fn_equal)
  return {
    'confusion': confusion(move, gate),
    'exact_hit': hits,
    'classes': measures,
    'static_fraction': count(~move) / len(actual),
    'fp': {
      'stage2_invoked_count': count(fp),
      'projected_same_tick_count': count(fp & ~moved),
      'projected_moved_count': count(fp & moved),
      'exact_hit_count': count(fp & hit),
      'within_one_tick_count': count(fp & (np.abs(projected - target) <= 1)),
    },
    'fn': {'count': count(fn), 'integrated_equals_hold': fn_equal, 'metrics': metrics(error[fn]), 'actual_delta_magnitude': summary(np.abs(actual[fn]))},
    'oracle': {
      'role': 'DIAGNOSTIC_ONLY',
      'metrics': oracle_metrics,
      'sign_accuracy': float(np.mean(np.sign(oracle) == np.sign(actual[move]))),
      'integrated': integrated,
      'hold_last': measures['MOVE']['hold_last'],
      'oracle_to_integrated_delta_sae': integrated['sae'] - oracle_metrics['sae'],
      'oracle_to_integrated_delta_sse': integrated['sse'] - oracle_metrics['sse'],
      'tp_fn_accounting': partition_accounting(error[move], hold[move], [gate[move], ~gate[move]]),
    },
    'accounting': partition_accounting(error, hold, [~move, move]),
  }


def first(mask):
  require(mask.ndim == 2 and mask.dtype == np.bool_)
  return np.where(np.any(mask, axis=1), np.argmax(mask, axis=1) + 1, 0).astype(np.int64)


def path_rows(observed, projected, gates):
  require(observed.dtype == projected.dtype == np.int64 and gates.dtype == np.bool_)
  require(observed.shape == projected.shape and gates.shape == (len(observed), observed.shape[1] - 1))
  require(np.array_equal(observed[:, 0], projected[:, 0]))
  truth = np.diff(observed, axis=1) != 0
  projected_move = np.diff(projected, axis=1) != 0
  mismatch = gates != truth
  fg = first(mismatch)
  is_fp = np.zeros(len(fg), dtype=bool)
  has = fg > 0
  is_fp[has] = gates[np.flatnonzero(has), fg[has] - 1]
  return {
    'first_gate': fg,
    'first_divergence': first(projected[:, 1:] != observed[:, 1:]),
    'first_gate_fp': is_fp,
    'gate_perfect': ~has,
    'path_moved': np.any(observed != observed[:, :1], axis=1),
    'gate_fp_count': np.count_nonzero(gates & ~truth, axis=1),
    'gate_fn_count': np.count_nonzero(~gates & truth, axis=1),
    'gate_tn_count': np.count_nonzero(~gates & ~truth, axis=1),
    'gate_tp_count': np.count_nonzero(gates & truth, axis=1),
    'observed_move_count': np.count_nonzero(truth, axis=1),
    'projected_move_count': np.count_nonzero(projected_move, axis=1),
    'first_projected_move': first(projected_move),
    'any_move_gate': np.any(gates, axis=1),
  }


def event_summary(steps):
  n, hits = len(steps), count(steps > 0)
  return {
    'count': n,
    'event_count': hits,
    'no_event_count': n - hits,
    'event_fraction': hits / n if n else None,
    'no_event_fraction': (n - hits) / n if n else None,
    'event_step_summary': summary(steps[steps > 0]),
  }


def rollout(rows, error, hold):
  fg, fd = rows['first_gate'], rows['first_divergence']
  moved, perfect = rows['path_moved'], rows['gate_perfect']
  n = len(fg)
  require(all(len(v) == n for v in rows.values()) and len(error) == len(hold) == n)
  relations = {
    'gate_precedes_divergence': (fg > 0) & (fd > fg),
    'same_step': (fg > 0) & (fd == fg),
    'divergence_precedes_gate': (fd > 0) & (fg > fd),
    'gate_mismatch_only': (fg > 0) & (fd == 0),
    'divergence_only': (fg == 0) & (fd > 0),
    'neither': (fg == 0) & (fd == 0),
  }
  require(bool(np.all(sum(m.astype(np.int8) for m in relations.values()) == 1)))
  masks = {
    'ALL': np.ones(n, dtype=bool),
    'PATH_MOVED': moved,
    'PATH_FLAT': ~moved,
    'GATE_PERFECT_PATH_MOVED': moved & perfect,
    'GATE_ERROR_PATH_MOVED': moved & ~perfect,
    'NO_GATE_MISMATCH': perfect,
    'FIRST_FP': ~perfect & rows['first_gate_fp'],
    'FIRST_FN': ~perfect & ~rows['first_gate_fp'],
  }
  require(bool(np.all(hold[~moved] == 0)))
  gate_counts = {k: int(np.sum(rows['gate_' + k.lower() + '_count'])) for k in ('TN', 'FP', 'FN', 'TP')}
  return {
    'count': n,
    'classes': {k: pair(error[m], hold[m]) for k, m in masks.items()},
    'gate_confusion': confusion_counts(gate_counts),
    'first_gate_mismatch': event_summary(fg),
    'first_projected_divergence': event_summary(fd),
    'first_event_relation': {k: count(v) for k, v in relations.items()},
    'path_flat': {
      'count': count(~moved),
      'any_move_gate_count': count(~moved & rows['any_move_gate']),
      'any_projected_motion_count': count(~moved & (rows['projected_move_count'] > 0)),
      'first_false_gate': event_summary(fg[~moved]),
      'first_projected_false_move': event_summary(rows['first_projected_move'][~moved]),
    },
    'count_distributions': {k: summary(rows[k]) for k in ('gate_fp_count', 'gate_fn_count', 'projected_move_count', 'observed_move_count')},
  }
