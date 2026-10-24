"""Route-equal CV and same-support diagnostics; arrays and coefficients stay private."""

import io
import os
from pathlib import Path
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_model as m
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


def save_array(path, array):
  path = Path(path)
  if any(x.is_symlink() for x in (path, *path.parents)):
    raise ValueError('NO_SYMLINK_PRIVATE_ARRAY')
  data = io.BytesIO()
  np.save(data, np.asarray(array), allow_pickle=False)
  raw = data.getvalue()
  digest = p.sha(raw)
  path.parent.mkdir(parents=True, exist_ok=True)
  if path.exists():
    if p.sha(path.read_bytes()) != digest:
      raise ValueError('IMMUTABLE_ARRAY_CONFLICT')
    return digest
  tmp = path.with_name(path.name + '.atomic')
  if tmp.exists():
    if tmp.is_symlink() or tmp.read_bytes() != raw:
      raise ValueError('STALE_ATOMIC_ARRAY')
  else:
    with tmp.open('xb') as f:
      f.write(raw)
      f.flush()
      os.fsync(f.fileno())
  os.link(tmp, path)
  tmp.unlink()
  return digest


def predictions(data, model, static):
  """Columns: truth, model, zero, hold-last, TRAIN static. No cross-run history.

  FIR endpoint uses exactly the same dot product at its endpoint as recursive
  execution (no output recurrence exists). ARX recursively uses its own predicted
  output. Observed exogenous inputs are conditional context, never future truth.
  """
  c = model['config']
  m.config_check(c)
  b = np.asarray(model['coefficients'])
  x, y, u, previous = m.design(data, c)
  output = {'design': x, 'one_step': np.column_stack([y, x @ b, np.zeros(len(y)), previous, u * static[0] + static[1]])}
  for h in p.metric_policy()['rollout_samples']:
    arrays = []
    for r in data:
      uu, yy = r['u'], r['y']
      k = np.arange(m.HISTORY - 1, len(yy) - h + 1)
      if not len(k):
        continue
      end = k + h - 1
      if c['family'] == 'ARX1':
        pred = yy[k - 1].copy()
        for step in range(h):
          pred = b[0] * pred + b[1] * uu[k + step - c['delay_samples']] + b[-1]
      else:
        # Preserve explicit tap accumulation ordering, matching the frozen oracle.
        pred = sum(b[t] * uu[end - c['delay_samples'] - t] for t in range(c['input_taps'])) + b[-1]
      arrays.append(np.column_stack([yy[end], pred, np.zeros(len(k)), yy[k - 1], uu[end] * static[0] + static[1]]))
    output['endpoint_' + str(h)] = np.concatenate(arrays) if arrays else np.empty((0, 5))
  return output


def groups(array):
  return {
    name: m.statistics(array[:, i] - array[:, 0], array[:, 0]) for i, name in enumerate(('model', 'ZERO_RESPONSE', 'HOLD_LAST_OUTPUT', 'TRAIN_STATIC_GAIN'), 1)
  }


def evaluate(data, model, static):
  if model['status'] != 'FITTED' or static is None:
    return {'status': 'UNAVAILABLE', 'one_step': None, 'rollout': None}, {}
  arrays = predictions(data, model, static)
  one = groups(arrays['one_step'])
  rollout = {str(h): groups(arrays['endpoint_' + str(h)]) for h in p.metric_policy()['rollout_samples']}
  diag = {}
  for lag in p.policy()['residual_lags']:
    a, b, u, y = [], [], [], []
    for run in data:
      x, target, command, _ = m.design([run], model['config'])
      e = x @ np.asarray(model['coefficients']) - target
      if len(e) > lag:
        a.append(e[lag:])
        b.append(e[:-lag])
        u.append(command[:-lag])
        y.append(target[:-lag])

    def cat(parts):
      return np.concatenate(parts) if parts else np.empty(0)

    aa, bb, uu, yy = map(cat, (a, b, u, y))
    diag[str(lag)] = {
      'count': len(aa),
      'autocorrelation': m.correlate(aa, bb),
      'past_input_correlation': m.correlate(aa, uu),
      'past_output_correlation': m.correlate(aa, yy),
    }
  return {
    'status': 'EVALUATED',
    'one_step': one,
    'rollout': rollout,
    'residual_temporal_diagnostics': diag,
    'finite_horizon_bounded': all(np.isfinite(x).all() for x in arrays.values()),
    'coverage': {key: {'valid': len(value), 'total': len(value), 'unavailable': 0} for key, value in arrays.items() if key != 'design'},
    'rollout_interpretation': 'CONDITIONAL_OBSERVED_EXOGENOUS_INPUT_ENDPOINT_NOT_STABILITY_PROOF',
  }, arrays


def directional_gate(record):
  failures = []
  for fold in record['folds']:
    f, e = fold['fold'], fold['evaluation']
    if fold['fit_status'] != 'FITTED' or e.get('status') != 'EVALUATED':
      failures.append(f + ':FIT_OR_EVALUATION_UNAVAILABLE')
      continue
    if set(e.get('rollout') or {}) != {str(h) for h in p.metric_policy()['rollout_samples']}:
      failures.append(f + ':MISSING_FROZEN_HORIZON')
      continue
    expected = {'model', 'ZERO_RESPONSE', 'HOLD_LAST_OUTPUT', 'TRAIN_STATIC_GAIN'}
    if any(set(t) != expected for t in [e['one_step'], *e['rollout'].values()]):
      failures.append(f + ':MISSING_REFERENCE')
      continue
    if not e['finite_horizon_bounded']:
      failures.append(f + ':NONFINITE')
    tables = {'one_step': e['one_step'], **{'endpoint_' + k: val for k, val in e['rollout'].items()}}
    for name, table in tables.items():
      counts = {x['count'] for x in table.values()}
      if len(counts) != 1:
        raise ValueError('NAIVE_AND_MODEL_COMMON_SUPPORT_REQUIRED')
      support = table['model']['count']
      if not support:
        failures.append(f + ':' + name + ':NO_SUPPORT')
      if any(t.get(metric) is None or not np.isfinite(t[metric]) for t in table.values() for metric in ('RMSE', 'MAE', 'P95_ABS')):
        failures.append(f + ':' + name + ':NONFINITE_METRIC')
        continue
      if name not in ('one_step', 'endpoint_100'):
        continue
      if support < 201:
        failures.append(f + ':' + name + ':INSUFFICIENT_SUPPORT')
        continue
      model = table['model']
      for ref in ('HOLD_LAST_OUTPUT', 'ZERO_RESPONSE', 'TRAIN_STATIC_GAIN'):
        for metric in ('RMSE', 'MAE', 'P95_ABS'):
          strict = ref == 'HOLD_LAST_OUTPUT' and metric == 'RMSE'
          good = model[metric] < table[ref][metric] if strict else model[metric] <= table[ref][metric]
          if not good:
            failures.append(f + ':' + name + ':' + ref + ':' + metric)
  return {'passed': not failures, 'failures': failures}


def choose(records, stage='STAGE_A'):
  eligible = []
  for row in records:
    if len(row['folds']) != 2 or {x['fold'] for x in row['folds']} != {'FOLD_A', 'FOLD_B'}:
      raise ValueError('EXACT_TWO_FOLDS_REQUIRED')
    if all(x['fit_status'] == 'FITTED' and x['evaluation'].get('one_step') and x['evaluation']['one_step']['model']['count'] >= 201 for x in row['folds']):
      errors = [x['evaluation']['one_step']['model']['RMSE'] for x in row['folds']]
      if all(x is not None and np.isfinite(x) for x in errors):
        aggregate = {'worst_route_RMSE': max(errors), 'equal_route_mean_RMSE': sum(errors) / 2}
        eligible.append({**row, 'aggregation': aggregate})
  if not eligible:
    return {'state': stage + '_CV_BLOCKED_INSUFFICIENT_SUPPORT', 'selected': None, 'gate': None}
  selected = min(
    eligible,
    key=lambda r: (
      r['aggregation']['worst_route_RMSE'],
      r['aggregation']['equal_route_mean_RMSE'],
      r['parameter_count'],
      r['config']['family'],
      r['config']['delay_samples'],
    ),
  )
  gate = directional_gate(selected)
  state = stage + '_CV_MODEL_SELECTED_DEVELOPMENT_ONLY' if gate['passed'] else stage + '_CV_TRADEOFF_ONLY'
  return {'state': state, 'selected': selected, 'gate': gate}


def yaw_consistent(admissions):
  if len(admissions) != 2 or not all(x['admitted'] for x in admissions):
    return False
  a, b = admissions
  return a['selection']['hypothesis'] == b['selection']['hypothesis'] and a['selection']['gyro_candidate'] == b['selection']['gyro_candidate']
