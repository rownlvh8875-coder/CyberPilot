"""Predeclared descriptive saved-score metrics. No decisions or model execution."""

import math
import statistics

import numpy as np

CONTEXTS = ('OVERALL', 'PREVIOUS_STATIC', 'PREVIOUS_MOVE')
TRANSITIONS = ('STATIC_HOLD', 'MOVE_ONSET', 'MOVE_TERMINATION', 'MOVE_CONTINUATION')
EDGES = tuple(i / 10 for i in range(11))
PUBLIC_MIN_SUPPORT = 201  # Conservative publication floor, never a performance acceptance clause.
SCORE_METRICS = ('auc', 'brier', 'mean_probability', 'prevalence', 'calibration_bias')
TRANSFER_METRICS = ('auc', 'brier', 'calibration_bias', 'prevalence')


def need(condition, code='C_NUMERIC_CONFLICT'):
  if not condition:
    raise ValueError(code)


def ratio(numerator, denominator):
  return numerator / denominator if denominator else None


def auc(p, y):
  """Exact integer pair count; ties contribute one half; no score rounding."""
  positive, n = int(np.count_nonzero(y)), len(y)
  negative = n - positive
  if not positive or not negative:
    return {'status': 'NOT_IDENTIFIABLE', 'value': None, 'numerator': None, 'denominator': None, 'positive': positive, 'negative': negative}
  order = np.argsort(p, kind='stable')
  sorted_p, sorted_y = p[order], y[order]
  starts = np.r_[0, np.flatnonzero(sorted_p[1:] != sorted_p[:-1]) + 1]
  sizes = np.diff(np.r_[starts, n])
  group_positive = np.add.reduceat(sorted_y.astype(np.int64), starts)
  group_negative = sizes - group_positive
  negatives_before = np.cumsum(group_negative, dtype=np.int64) - group_negative
  # N <=336941: every sum/product is below 2*N*N < 2**38, safely int64.
  numerator = int(np.sum(group_positive * (2 * negatives_before + group_negative), dtype=np.int64))
  denominator = 2 * positive * negative
  return {
    'status': 'IDENTIFIABLE',
    'value': numerator / denominator,
    'numerator': numerator,
    'denominator': denominator,
    'positive': positive,
    'negative': negative,
  }


def score_metrics(p, y):
  n, positives = len(p), int(np.count_nonzero(y))
  mean = math.fsum(map(float, p)) / n if n else None
  prevalence = ratio(positives, n)
  bins = []
  for index in range(10):
    selected = (p >= EDGES[index]) & ((p < EDGES[index + 1]) if index < 9 else (p <= 1))
    count = int(np.count_nonzero(selected))
    bins.append(
      {
        'bin': index,
        'count': count,
        'mean_probability': math.fsum(map(float, p[selected])) / count if count else None,
        'observed_move_rate': ratio(int(np.count_nonzero(y[selected])), count),
        'status': 'IDENTIFIABLE' if count else 'NOT_IDENTIFIABLE',
      }
    )
  return {
    'n': n,
    'positives': positives,
    'negatives': n - positives,
    'auc': auc(p, y),
    'mean_probability': mean,
    'prevalence': prevalence,
    'brier': math.fsum(map(float, (p - y) ** 2)) / n if n else None,
    'calibration_bias': mean - prevalence if n else None,
    'reliability': bins,
  }


def confusion(y, gate):
  counts = {
    'TP': int(np.count_nonzero(y & gate)),
    'FP': int(np.count_nonzero(~y & gate)),
    'TN': int(np.count_nonzero(~y & ~gate)),
    'FN': int(np.count_nonzero(y & ~gate)),
  }
  tp, fp, tn, fn = (counts[k] for k in ('TP', 'FP', 'TN', 'FN'))
  metrics = {'precision': ratio(tp, tp + fp), 'recall': ratio(tp, tp + fn), 'FPR': ratio(fp, fp + tn), 'FNR': ratio(fn, fn + tp)}
  return dict(counts=counts, **metrics, status={k: 'IDENTIFIABLE' if v is not None else 'NOT_IDENTIFIABLE' for k, v in metrics.items()})


def analyze(p, y, prior, *, gate=None):
  need(all(isinstance(v, np.ndarray) and v.ndim == 1 for v in (p, y, prior)))
  need(p.dtype.str == '<f8' and y.dtype.str == '|b1' and prior.dtype.str == '<i8')
  need(0 < len(p) <= 336941 and len(p) == len(y) == len(prior))
  need(bool(np.all(np.isfinite(p))) and bool(np.all((p >= 0) & (p <= 1))))
  if gate is not None:
    need(isinstance(gate, np.ndarray) and gate.dtype.str == '|b1' and gate.ndim == 1 and gate.shape == p.shape)
  previous_move = prior != 0
  contexts = (np.ones(len(p), dtype=bool), ~previous_move, previous_move)
  populations = (~previous_move & ~y, ~previous_move & y, previous_move & ~y, previous_move & y)
  support = dict(OVERALL=len(p), **{key: int(np.count_nonzero(mask)) for key, mask in zip(TRANSITIONS, populations, strict=True)})
  need(sum(support[k] for k in TRANSITIONS) == len(p))
  scores = {key: score_metrics(p[mask], y[mask]) for key, mask in zip(CONTEXTS, contexts, strict=True)}
  gates, transitions = None, None
  if gate is not None:
    gates = {key: confusion(y[mask], gate[mask]) for key, mask in zip(CONTEXTS, contexts, strict=True)}
    transitions = {}
    for key, mask in zip(TRANSITIONS, populations, strict=True):
      n = support[key]
      moved = int(np.count_nonzero(gate[mask]))
      transitions[key] = {
        'n': n,
        'move_gate': moved,
        'static_gate': n - moved,
        'rate': ratio(moved, n),
        'complement_rate': ratio(n - moved, n),
        'status': 'IDENTIFIABLE' if n else 'NOT_IDENTIFIABLE',
      }
  return {'support': support, 'scores': scores, 'gates': gates, 'transitions': transitions}


def metric(row, name):
  return row['auc']['value'] if name == 'auc' else row[name]


def transfer(train, dev):
  return {
    context: {
      name: None
      if metric(train['scores'][context], name) is None or metric(dev['scores'][context], name) is None
      else metric(dev['scores'][context], name) - metric(train['scores'][context], name)
      for name in TRANSFER_METRICS
    }
    for context in CONTEXTS
  }


def summary(values):
  need(all(v is None or (type(v) in (int, float) and math.isfinite(v)) for v in values), 'C_PUBLIC_NUMERIC_ONLY')
  valid = [v for v in values if v is not None]
  return {
    'valid_jobs': len(valid),
    'median': statistics.median(valid) if valid else None,
    'minimum': min(valid) if valid else None,
    'maximum': max(valid) if valid else None,
    'status': 'IDENTIFIABLE' if valid else 'NOT_IDENTIFIABLE',
  }


def cell_safe(n, positive):
  return n >= PUBLIC_MIN_SUPPORT and all(v == 0 or v >= PUBLIC_MIN_SUPPORT for v in (positive, n - positive))


def public_folds(jobs):
  """No bins, cells, supports, candidate IDs or per-job scores leave this projection.

  All score/transfer contexts co-suppress if any context in any TRAIN/DEV job
  in either fold has fewer than201 of either truth class. Overall and companion
  contexts cannot be used to subtract a hidden context. Transition families require every event/complement
  to be either zero or >=201. Otherwise the entire cross-fold family is hidden;
  no totals or companion cells are published for subtraction reconstruction.
  These are publication rules, not scientific acceptance gates.
  """
  need(len(jobs) == 32 and all(sum(j['fold'] == f for j in jobs) == 16 for f in ('FOLD_A', 'FOLD_B')), 'C_PUBLIC_JOB_SCOPE')
  result = {}
  hidden = {'status': 'SUPPRESSED_PRIVACY'}
  eligible = {
    context: all(
      min(j[role]['scores'][context]['positives'], j[role]['scores'][context]['negatives']) >= PUBLIC_MIN_SUPPORT for j in jobs for role in ('TRAIN', 'DEV')
    )
    for context in CONTEXTS
  }
  score_family_safe = all(eligible.values())
  for fold in ('FOLD_A', 'FOLD_B'):
    selected = [j for j in jobs if j['fold'] == fold]
    row = {}
    for role in ('TRAIN', 'DEV'):
      row[role] = {
        'scores': {
          context: {
            name: summary([metric(j[role]['scores'][context], name) for j in selected]) if score_family_safe else hidden.copy() for name in SCORE_METRICS
          }
          for context in CONTEXTS
        }
      }
    row['transfer'] = {
      context: {name: summary([j['transfer'][context][name] for j in selected]) if score_family_safe else hidden.copy() for name in TRANSFER_METRICS}
      for context in CONTEXTS
    }
    row['DEV']['transitions'] = {}
    for key in TRANSITIONS:
      safe = all(cell_safe(j['DEV']['transitions'][key]['n'], j['DEV']['transitions'][key]['move_gate']) for j in jobs)
      row['DEV']['transitions'][key] = summary([j['DEV']['transitions'][key]['rate'] for j in selected]) if safe else hidden.copy()
    result[fold] = row
  return result
