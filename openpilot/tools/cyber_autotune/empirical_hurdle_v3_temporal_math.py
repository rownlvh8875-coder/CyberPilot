"""Descriptive temporal reductions of already stored evidence; no gate executor."""

import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_attribution_math as a


def truth(delta, prior):
  a.require(delta.ndim == prior.ndim == 1 and delta.shape == prior.shape and len(delta) > 0)
  a.require(all(np.isfinite(x).all() and np.equal(x, np.rint(x)).all() for x in (delta, prior)))
  return delta != 0, prior != 0


def continuity(arrays):
  n = len(arrays['anchor_index'])
  linked = np.ones(n, dtype=bool)
  a.require(n > 0 and all(v.shape == (n,) for v in arrays.values()))
  linked[0] = False
  for k in ('anchor_route_id', 'anchor_segment_sha', 's2_ri_run_id'):
    linked[1:] &= arrays[k][1:] == arrays[k][:-1]
  for k in ('anchor_index', 'within_run_index'):
    linked[1:] &= arrays[k][1:] == arrays[k][:-1] + 1
  return linked


def fraction(positive, mask):
  numerator, denominator = a.count(positive & mask), a.count(mask)
  return {'numerator': numerator, 'denominator': denominator, 'ratio': numerator / denominator if denominator else None}


def transitions(delta, prior, linked):
  move, previous = truth(delta, prior)
  a.require(linked.dtype == np.bool_ and linked.shape == move.shape and not linked[0])
  a.require(np.array_equal(prior[1:][linked[1:]], delta[:-1][linked[1:]]), 'PRIOR_CONTEXT_CONFLICT')
  prev2 = np.r_[False, previous[:-1]]
  return {
    'count': len(move),
    'counts': {k: a.count(mask) for k, mask in (('SS', ~previous & ~move), ('SM', ~previous & move), ('MS', previous & ~move), ('MM', previous & move))},
    'previous_static': fraction(move, ~previous),
    'previous_move': fraction(move, previous),
    'history_two': {
      'support': a.count(linked),
      'last_two_static': fraction(move, linked & ~previous & ~prev2),
      'any_last_two_move': fraction(move, linked & (previous | prev2)),
    },
  }


def runs(delta, linked):
  move, _ = truth(delta, delta)
  a.require(linked.shape == move.shape and linked.dtype == np.bool_ and not linked[0])
  starts = np.flatnonzero(~linked | np.r_[False, move[1:] != move[:-1]])
  ends = np.r_[starts[1:], len(move)]
  result = {}
  for name, state in (('STATIC', False), ('MOVE', True)):
    mask = move[starts] == state
    lengths = (ends - starts)[mask]
    censored = [not linked[lo] or hi == len(move) or not linked[hi] for lo, hi in zip(starts[mask], ends[mask], strict=True)]
    result[name] = {
      'count': len(lengths),
      'boundary_censored_count': int(sum(censored)),
      'median': float(np.median(lengths)) if len(lengths) else None,
      'p90': float(np.percentile(lengths, 90, method='linear')) if len(lengths) else None,
      'p95': float(np.percentile(lengths, 95, method='linear')) if len(lengths) else None,
      'max': int(np.max(lengths)) if len(lengths) else None,
    }
  result['fragment_count'] = a.count(~linked)
  result['interpretation'] = 'ELIGIBLE_OBSERVED_FRAGMENTS_BOUNDARY_CENSORED_NOT_RAW_ROUTE_RUNS'
  return result


def subset_ranking(probability, move, mask):
  positive, negative = a.count(move & mask), a.count(~move & mask)
  if not positive or not negative:
    return {'positive_count': positive, 'negative_count': negative, 'auc': None, 'auc_num2': None, 'auc_den2': None, 'support_state': 'EMPTY_CLASS'}
  return {**a.ranking(probability[mask], move[mask]), 'support_state': 'SUPPORTED' if min(positive, negative) >= 201 else 'SMALL_SUPPORT_DESCRIPTIVE_ONLY'}


def scores(probability, delta, prior):
  move, previous = truth(delta, prior)
  a.require(probability.dtype == np.float64 and probability.shape == move.shape)
  a.require(np.isfinite(probability).all() and ((probability >= 0) & (probability <= 1)).all())
  return {
    'onset': subset_ranking(probability, move, ~move | ~previous),
    'continuation': subset_ranking(probability, move, ~move | previous),
    'previous_static': subset_ranking(probability, move, ~previous),
    'previous_move': subset_ranking(probability, move, previous),
  }


def persistence(row):
  m, s = row['previous_move'], row['previous_static']
  return min(m['denominator'], s['denominator']) >= 201 and m['numerator'] * s['denominator'] > s['numerator'] * m['denominator']


def rank_trigger(rows):
  return len(rows) == 32 and all(min(r['positive_count'], r['negative_count']) >= 201 and 2 * r['auc_num2'] > r['auc_den2'] for r in rows)
