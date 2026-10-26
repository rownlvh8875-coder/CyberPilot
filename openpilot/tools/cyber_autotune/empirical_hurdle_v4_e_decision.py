"""E-only D1 TRAIN selection. No readers, fitting, calibration or model admission."""

import re

import numpy as np

JOBS = tuple((f'HRI_D{d:02}_L{length:02}', fold) for d in (0, 5, 10, 20) for length in (1, 5, 15, 45) for fold in ('FOLD_A', 'FOLD_B'))
MAX_COUNT = 336941  # Frozen V4 job manifest maximum TRAIN population.


def need(condition, code='E_DECISION_INPUT_CONFLICT'):
  if not condition:
    raise ValueError(code)


def probability(p):
  need(isinstance(p, np.ndarray) and p.dtype == np.float64 and p.ndim == 1 and 0 < len(p) <= MAX_COUNT)
  need(bool(np.all(np.isfinite(p))) and bool(np.all((p >= 0) & (p <= 1))))


def select_context(p, y, *, role):
  """Maximize (exact integer BA_NUM, TN, decision), strict p>decision.

  The sorted sweep removes each equal-score group before evaluating its value.
  Sorting is an objective calculation only; saved row order is never modified.
  """
  need(role == 'TRAIN', 'E_TRAIN_ONLY_REQUIRED')
  probability(p)
  need(isinstance(y, np.ndarray) and y.dtype == np.bool_ and y.shape == p.shape)
  positive = int(np.count_nonzero(y))
  negative = len(y) - positive
  need(positive > 0 and negative > 0, 'E_CONTEXT_CLASS_SUPPORT_MISSING')
  order = np.argsort(p, kind='stable')
  scores, labels = p[order], y[order]
  candidates = np.union1d(np.array([0.0, 1.0]), scores)
  index, tp, tn = 0, positive, 0
  best, chosen = None, None
  for candidate in candidates:
    value = 0.0 if candidate == 0 else float(candidate)  # One numeric zero identity.
    while index < len(scores) and scores[index] <= value:
      if labels[index]:
        tp -= 1
      else:
        tn += 1
      index += 1
    objective = tp * negative + tn * positive  # Python exact integer arithmetic.
    key = (objective, tn, value)
    if best is None or key > best:
      best = key
      chosen = {'decision': value, 'BA_NUM': objective, 'TN': tn, 'TP': tp}
  return {**chosen, 'positive': positive, 'negative': negative, 'count': len(p), 'candidate_count': len(candidates)}


def select_job(p, y, prior, *, candidate, fold, anchor, role):
  need((candidate, fold) in JOBS and isinstance(anchor, str) and re.fullmatch('[0-9a-f]{64}', anchor) is not None)
  probability(p)
  need(isinstance(prior, np.ndarray) and prior.dtype == np.int64 and prior.shape == p.shape)
  need(isinstance(y, np.ndarray) and y.dtype == np.bool_ and y.shape == p.shape)
  context = prior != 0
  return {
    'candidate_id': candidate,
    'fold': fold,
    'anchor_sha256': anchor,
    'count': len(p),
    'contexts': {name: select_context(p[context == state], y[context == state], role=role) for state, name in enumerate(('PREVIOUS_STATIC', 'PREVIOUS_MOVE'))},
  }


def gate(p, prior, decisions):
  probability(p)
  need(isinstance(prior, np.ndarray) and prior.dtype == np.int64 and prior.shape == p.shape)
  need(type(decisions) is tuple and len(decisions) == 2 and all(type(v) is float and np.isfinite(v) and 0 <= v <= 1 for v in decisions))
  return p > np.where(prior == 0, decisions[0], decisions[1])
