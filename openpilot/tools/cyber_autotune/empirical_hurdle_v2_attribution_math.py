"""Threshold-free rankings and descriptive reductions of stored V2 evidence."""

import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_math as old

require, count = old.require, old.count


def ranking(probability, move):
  x = np.ascontiguousarray(probability, dtype=np.float64)
  require(x.ndim == 1 and x.shape == move.shape and move.dtype == np.bool_)
  require(bool(np.isfinite(x).all()) and bool(np.all((x >= 0) & (x <= 1))))
  positives, negatives = count(move), count(~move)
  require(positives > 0 and negatives > 0, 'ATTRIBUTION_CLASS_SUPPORT_REQUIRED')
  order = np.argsort(x, kind='stable')
  scores, labels = x[order], move[order]
  starts = np.r_[0, np.flatnonzero(scores[1:] != scores[:-1]) + 1]
  ends = np.r_[starts[1:], len(x)]
  positive_groups = np.add.reduceat(labels.astype(np.int64), starts)
  below, numerator = 0, 0
  for lo, hi, pg in zip(starts, ends, positive_groups, strict=True):
    pg, ng = int(pg), int(hi - lo) - int(pg)
    numerator += 2 * pg * below + pg * ng
    below += ng
  denominator = 2 * positives * negatives
  prevalence = positives / len(x)
  average = float(np.mean(x))
  static_mean, move_mean = float(np.mean(x[~move])), float(np.mean(x[move]))
  return {
    'count': len(x),
    'positive_count': positives,
    'negative_count': negatives,
    'auc_num2': numerator,
    'auc_den2': denominator,
    'auc': numerator / denominator,
    'brier': float(np.mean((x - move.astype(np.float64)) ** 2)),
    'true_move_prevalence': prevalence,
    'mean_probability': average,
    'calibration_bias': average - prevalence,
    'static_score_mean': static_mean,
    'move_score_mean': move_mean,
    'score_mean_gap': move_mean - static_mean,
  }


def transfer(train, dev):
  # Compare exact pair fractions, including near-chance values that round alike.
  half = 2 * dev['auc_num2'] - dev['auc_den2']
  difference = dev['auc_num2'] * train['auc_den2'] - train['auc_num2'] * dev['auc_den2']
  return {
    'train': train,
    'development': dev,
    'dev_minus_train_auc': dev['auc'] - train['auc'],
    'rank_state': 'RANK_ABOVE_CHANCE' if half > 0 else ('RANK_AT_CHANCE' if half == 0 else 'RANK_BELOW_CHANCE'),
    'transfer_state': 'RANK_TRANSFER_INCREASED' if difference > 0 else ('RANK_TRANSFER_EQUAL' if difference == 0 else 'RANK_TRANSFER_DECREASED'),
    'classifier_review_evidence': 2 * train['auc_num2'] > train['auc_den2'] and half <= 0,
    'authority': 'THRESHOLD_FREE_DIAGNOSTIC_ONLY',
  }


def hit_counts(current, target, projected):
  move, hit = target != current, projected == target
  loss, gain = count(~move & (projected != current)), count(move & hit)
  net = count(hit) - count(~move)
  require(net == gain - loss, 'ATTRIBUTION_IDENTITY_FAILURE')
  return {
    'static_hit_loss': loss,
    'move_hit_gain': gain,
    'net_hit_delta': net,
    'candidate_exact_hit_count': count(hit),
    'hold_exact_hit_count': count(~move),
    'exact_hit_deficit_count': max(-net, 0),
    'exact_hit_surplus_count': max(net, 0),
    'state': 'MOVE_GAIN_DEFICIT_DOMINATES' if net < 0 else 'NO_EXACT_HIT_DEFICIT',
    'integer_identity_exact': True,
  }


def decisions(move, gate, projected_move):
  r = old.confusion(move, gate)
  require(r['true_move_fraction'] > 0)
  r.update(
    move_coverage_ratio=count(gate) / count(move),
    projected_move_fraction=count(projected_move) / len(move),
    extreme_move_suppression=r['missed_move_rate'] > 0.95,
  )
  return r


def one_step(current, target, gate, projected, delta, error, hold):
  current, target, projected = (np.asarray(v, dtype=np.int64) for v in (current, target, projected))
  require(current.ndim == 1 and len(current) > 0 and all(v.shape == current.shape for v in (target, gate, projected, delta, error, hold)))
  require(gate.dtype == np.bool_ and all(v.dtype == np.float64 and np.isfinite(v).all() for v in (delta, error, hold)))
  actual = target - current
  move, fn, tp = actual != 0, (actual != 0) & ~gate, (actual != 0) & gate
  require((delta - actual.astype(float)).tobytes() == error.tobytes(), 'ATTRIBUTION_IDENTITY_FAILURE')
  require((-actual.astype(float)).tobytes() == hold.tobytes(), 'ATTRIBUTION_IDENTITY_FAILURE')
  require(np.all(delta[~gate] == 0) and np.array_equal(projected[~gate], current[~gate]), 'ATTRIBUTION_IDENTITY_FAILURE')
  require(error[fn].tobytes() == hold[fn].tobytes(), 'ATTRIBUTION_IDENTITY_FAILURE')
  axes = {'ONE_TICK_MOVE': np.abs(actual) == 1, 'MULTI_TICK_MOVE': np.abs(actual) >= 2, 'MOVE_POSITIVE': actual > 0, 'MOVE_NEGATIVE': actual < 0}
  hit, within, hold_within = projected == target, np.abs(projected - target) <= 1, np.abs(actual) <= 1
  masks = {
    'STATIC_PROJECTED_FALSE_MOVE': ~move & (projected != current),
    'STATIC_PROJECTED_HOLD': ~move & (projected == current),
    'ONE_TICK_FN': fn & axes['ONE_TICK_MOVE'],
    'MULTI_TICK_FN': fn & axes['MULTI_TICK_MOVE'],
    'TP_STAGE2': tp,
  }
  require(np.all(sum(v.astype(np.int8) for v in masks.values()) == 1))
  within_parts = {
    k: {
      'count': count(v),
      'candidate_count': count(v & within),
      'hold_count': count(v & hold_within),
      'delta_count': count(v & within) - count(v & hold_within),
    }
    for k, v in masks.items()
  }
  require(sum(v['delta_count'] for v in within_parts.values()) == count(within) - count(hold_within))
  require(within_parts['ONE_TICK_FN']['delta_count'] == within_parts['MULTI_TICK_FN']['delta_count'] == 0)
  return {
    'exact_hit': hit_counts(current, target, projected),
    'confusion': decisions(move, gate, projected != current),
    'move': {name: {k: count(mask & v) for k, v in axes.items()} for name, mask in (('TP', tp), ('FN', fn), ('EXACT_HITS', move & hit))},
    'fn': {
      'count': count(fn),
      'one_tick_fraction': count(fn & axes['ONE_TICK_MOVE']) / count(fn) if count(fn) else None,
      'multi_tick_fraction': count(fn & axes['MULTI_TICK_MOVE']) / count(fn) if count(fn) else None,
      'hold_identity_exact': True,
      'metrics': old.metrics(error[fn]),
    },
    'tp': {
      'count': count(tp),
      'exact_count': count(tp & hit),
      'exact_rate': count(tp & hit) / count(tp) if count(tp) else None,
      'within_one_tick_rate': count(tp & within) / count(tp) if count(tp) else None,
      'sign_accuracy': float(np.mean(np.sign(delta[tp]) == np.sign(actual[tp]))) if count(tp) else None,
      'metrics': old.pair(error[tp], hold[tp], projected[tp], target[tp], current[tp]),
    },
    'within': within_parts,
    'classes': {
      k: old.pair(error[v], hold[v], projected[v], target[v], current[v])
      for k, v in (('ALL', np.ones(len(move), dtype=bool)), ('MOVE', move), ('STATIC', ~move))
    },
    'sae_sse_partition': old.partition_accounting(error, hold, [~move, move]),
  }


def path_rows(observed, projected, gate):
  observed, projected = np.asarray(observed, dtype=np.int64), np.asarray(projected, dtype=np.int64)
  result = old.path_rows(observed, projected, gate)
  require(bool(np.all((np.diff(projected, axis=1) == 0) | gate)), 'ATTRIBUTION_STATIC_PATH_IDENTITY_FAILURE')
  result['first_departure'] = old.first(projected[:, 1:] != observed[:, :1])
  result['predicted_move_count'] = np.count_nonzero(gate, axis=1)
  return result


def rollout(rows, error, hold):
  result = old.rollout(rows, error, hold)
  any_move, moved = rows['any_move_gate'], rows['path_moved']
  for name, mask in (
    ('NO_PREDICTED_MOVE', ~any_move),
    ('ANY_PREDICTED_MOVE', any_move),
    ('PATH_MOVED_NO_PREDICTED_MOVE', moved & ~any_move),
    ('PATH_MOVED_ANY_PREDICTED_MOVE', moved & any_move),
  ):
    result['classes'][name] = old.pair(error[mask], hold[mask])
  require(error[~any_move].tobytes() == hold[~any_move].tobytes(), 'ATTRIBUTION_NO_MOVE_HOLD_IDENTITY_FAILURE')
  identical = count(rows['first_departure'] == 0)
  result.update(
    hold_last_identical_count=identical,
    hold_last_identical_fraction=identical / len(error),
    first_departure_from_hold_last=old.event_summary(rows['first_departure']),
  )
  result['count_distributions']['predicted_move_count'] = old.summary(rows['predicted_move_count'])
  result['event_totals'] = {k: int(np.sum(rows[k])) for k in ('predicted_move_count', 'projected_move_count', 'observed_move_count')}
  return result
