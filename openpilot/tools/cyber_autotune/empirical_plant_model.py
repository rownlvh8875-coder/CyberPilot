"""Small predeclared actuator identification. No controller or candidate execution."""

import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p

HISTORY = 45


def runs(rows, regime):
  output, u, y, blocks = [], [], [], []
  for i, row in enumerate(rows):
    if row['diagnostic_valid'] and row['speed_bin'] == regime:
      u.append(row['command_raw'])
      y.append(row['angle_deg'])
      blocks.append(min(3, 4 * i // max(1, len(rows))))
    else:
      if u:
        output.append({'u': np.asarray(u, dtype=np.float64), 'y': np.asarray(y, dtype=np.float64), 'blocks': np.asarray(blocks, dtype=int)})
      u, y, blocks = [], [], []
  if u:
    output.append({'u': np.asarray(u, dtype=np.float64), 'y': np.asarray(y, dtype=np.float64), 'blocks': np.asarray(blocks, dtype=int)})
  return output


def config_check(c):
  if c not in p.family_policy()['candidates']:
    raise ValueError('ONLY_FROZEN_EIGHT_MODEL_CONFIGS')


def design(data, c):
  config_check(c)
  matrices, targets, commands, previous = [], [], [], []
  for r in data:
    u, y = r['u'], r['y']
    k = np.arange(HISTORY - 1, len(y))
    if not len(k):
      continue
    cols = ([y[k - 1]] if c['family'] == 'ARX1' else []) + [u[k - c['delay_samples'] - j] for j in range(c['input_taps'])] + [np.ones(len(k))]
    matrices.append(np.column_stack(cols))
    targets.append(y[k])
    commands.append(u[k])
    previous.append(y[k - 1])
  columns = c['input_taps'] + c['output_lags'] + 1
  return tuple(np.concatenate(x, axis=0) if x else np.empty((0, columns) if i == 0 else (0,)) for i, x in enumerate([matrices, targets, commands, previous]))


def stable(family, coefficients):
  return bool(np.isfinite(coefficients).all() and (family != 'ARX1' or abs(coefficients[0]) < 1))


def fit(data, c):
  x, y, _, _ = design(data, c)
  base = {'config': dict(c), 'count': len(y)}
  if len(y) < max(201, 10 * x.shape[1]):
    return {**base, 'status': 'INSUFFICIENT_SUPPORT', 'coefficients': None}
  b, _, rank, s = np.linalg.lstsq(x, y, rcond=None)
  if rank != x.shape[1]:
    return {**base, 'status': 'RANK_DEFICIENT', 'coefficients': None}
  return {
    **base,
    'status': 'FITTED' if stable(c['family'], b) else 'UNSTABLE_REJECTED',
    'coefficients': b.tolist(),
    'rank': int(rank),
    'singular_values': s.tolist(),
  }


def static_fit(data):
  c = p.family_policy()['candidates'][0]
  _, y, u, _ = design(data, c)
  if len(y) < 201:
    return None
  x = np.column_stack([u, np.ones(len(u))])
  b, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
  return b.tolist() if rank == 2 else None


def correlate(a, b):
  a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
  if len(a) < 2 or np.ptp(a) == 0 or np.ptp(b) == 0:
    return None
  result = float(np.corrcoef(a, b)[0, 1])
  return result if np.isfinite(result) else None


def statistics(residual, truth):
  e = np.asarray(residual, dtype=float)
  t = np.asarray(truth, dtype=float)
  if len(e) != len(t) or not np.isfinite(e).all() or not np.isfinite(t).all():
    raise ValueError('FINITE_SHARED_SUPPORT_REQUIRED')
  if not len(e):
    return dict.fromkeys(['MAE', 'RMSE', 'MEDIAN_ABS', 'P95_ABS', 'BIAS', 'CORRELATION']) | {'count': 0}
  return {
    'count': len(e),
    'MAE': float(np.mean(abs(e))),
    'RMSE': float(np.sqrt(np.mean(e * e))),
    'MEDIAN_ABS': float(np.median(abs(e))),
    'P95_ABS': float(np.quantile(abs(e), 0.95)),
    'BIAS': float(np.mean(e)),
    'CORRELATION': correlate(t + e, t),
  }


def group_stats(truth, predictions):
  return {name: statistics(np.asarray(pred) - truth, truth) for name, pred in predictions.items()}


def evaluate(data, model, static, quartiles=None):
  if model['status'] != 'FITTED' or static is None:
    return {'status': 'UNAVAILABLE', 'one_step': None, 'rollout': None}
  c = model['config']
  b = np.asarray(model['coefficients'])
  x, y, u, prev = design(data, c)
  one = group_stats(y, {'model': x @ b, 'ZERO_RESPONSE': np.zeros(len(y)), 'HOLD_LAST_OUTPUT': prev, 'TRAIN_STATIC_GAIN': u * static[0] + static[1]})
  rollout = {}
  for horizon in p.metric_policy()['rollout_samples']:
    truths = []
    preds = []
    lasts = []
    gains = []
    for r in data:
      uu, yy = r['u'], r['y']
      # k is first predicted index. Forecast uses observed exogenous input, never future measured output.
      k = np.arange(HISTORY - 1, len(yy) - horizon + 1)
      if not len(k):
        continue
      predicted = yy[k - 1].copy()
      for step in range(horizon):
        j = k + step
        if c['family'] == 'ARX1':
          predicted = b[0] * predicted + b[1] * uu[j - c['delay_samples']] + b[-1]
        else:
          predicted = sum(b[tap] * uu[j - c['delay_samples'] - tap] for tap in range(c['input_taps'])) + b[-1]
      end = k + horizon - 1
      truths.append(yy[end])
      preds.append(predicted)
      lasts.append(yy[k - 1])
      gains.append(uu[end] * static[0] + static[1])

    def cat(a):
      return np.concatenate(a) if a else np.empty(0)

    truth = cat(truths)
    rollout[str(horizon)] = group_stats(
      truth, {'model': cat(preds), 'ZERO_RESPONSE': np.zeros(len(truth)), 'HOLD_LAST_OUTPUT': cat(lasts), 'TRAIN_STATIC_GAIN': cat(gains)}
    )
  residual = x @ b - y
  diag = {'residual_autocorrelation': {}, 'residual_past_input_correlation': {}, 'residual_past_output_correlation': {}}
  # Do not concatenate across run boundaries for temporal correlation.
  for lag in p.policy()['residual_lags']:
    e1 = []
    e0 = []
    up = []
    yp = []
    for r in data:
      xx, yy, uu, _ = design([r], c)
      ee = xx @ b - yy
      if len(ee) > lag:
        e1.extend(ee[lag:])
        e0.extend(ee[:-lag])
        up.extend(uu[:-lag])
        yp.extend(yy[:-lag])
    diag['residual_autocorrelation'][str(lag)] = {'correlation': correlate(e1, e0), 'count': len(e1)}
    diag['residual_past_input_correlation'][str(lag)] = {'correlation': correlate(e1, up), 'count': len(e1)}
    diag['residual_past_output_correlation'][str(lag)] = {'correlation': correlate(e1, yp), 'count': len(e1)}
  diag['input_sign'] = {name: statistics(residual[mask], y[mask]) for name, mask in [('ZERO', u == 0), ('POSITIVE', u > 0), ('NEGATIVE', u < 0)]}
  if quartiles is None:
    diag['amplitude_quartiles'] = 'UNAVAILABLE_NO_TRAIN_BOUNDARIES'
  else:
    edges = [0.0, *quartiles, float('inf')]
    diag['amplitude_quartiles'] = {
      str(i): statistics(residual[(abs(u) >= edges[i]) & (abs(u) < edges[i + 1])], y[(abs(u) >= edges[i]) & (abs(u) < edges[i + 1])]) for i in range(4)
    }
    diag['amplitude_boundaries_source'] = 'TRAIN_ABSOLUTE_COMMAND_QUARTILES'
  block_values = []
  for r in data:
    block_values.extend(r.get('blocks', np.full(len(r['y']), -1))[HISTORY - 1 :])
  block_values = np.asarray(block_values)
  diag['per_segment_quarter_index_pooled'] = {str(i): statistics(residual[block_values == i], y[block_values == i]) for i in range(4)}
  diag['command_excitation'] = {
    'minimum': float(min(u)) if len(u) else None,
    'maximum': float(max(u)) if len(u) else None,
    'std': float(np.std(u)) if len(u) else None,
    'distinct_count': len(np.unique(u)),
  }
  diag['condition_number'] = float(np.linalg.cond(x)) if len(x) else None
  diag['saturation_intervention_residual'] = 'UNAVAILABLE_CLEAN_LIMIT_MASK_UNOBSERVED_DRIVER_EXCLUDED_DISCLOSED'
  return {
    'status': 'EVALUATED',
    'unit': 'STEERING_ANGLE_DEGREES',
    'one_step': one,
    'rollout': rollout,
    'residual_diagnostics': diag,
    'finite_horizon_bounded': True,
    'rollout_drift': 'ENDPOINT_BIAS_PER_HORIZON_NOT_STABILITY_PROOF',
  }


def select(roles, candidates):
  if set(roles) != {'TRAIN', 'DEVELOPMENT'}:
    raise ValueError('SELECTION_TRAIN_DEVELOPMENT_ONLY_NO_HOLDOUT')
  records = []
  static = static_fit(roles['TRAIN'])
  for c in candidates:
    model = fit(roles['TRAIN'], c)
    if model['status'] == 'FITTED' and static is not None:
      x, y, _, _ = design(roles['DEVELOPMENT'], c)
      metrics = statistics(x @ np.asarray(model['coefficients']) - y, y)
    else:
      metrics = {'count': 0, 'RMSE': None}
    records.append({'model': model, 'development': metrics})
  eligible = [r for r in records if r['model']['status'] == 'FITTED' and r['development']['count'] >= 201]
  selected = (
    min(
      eligible, key=lambda r: (r['development']['RMSE'], len(r['model']['coefficients']), r['model']['config']['family'], r['model']['config']['delay_samples'])
    )
    if eligible
    else None
  )
  _, _, train_u, _ = design(roles['TRAIN'], p.family_policy()['candidates'][0])
  quartiles = np.quantile(abs(train_u), [0.25, 0.5, 0.75]).tolist() if len(train_u) else None
  return {'selected': selected, 'candidates': records, 'static_gain': static, 'train_amplitude_quartiles': quartiles}
