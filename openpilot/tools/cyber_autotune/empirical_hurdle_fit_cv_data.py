"""Read only the sealed source fields, one route at a time, in fixed order."""

import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_identifiability_execution as read
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m
from openpilot.tools.cyber_autotune import empirical_s2_ri_reconstruction_math as context_source


def load_route(records, route, authorization):
  p.verify(authorization)
  if not authorization.get('retrospective_fit_cv_authorized') or authorization['array_access_before_seal']:
    raise ValueError('SEALED_HURDLE_EXECUTION_AUTHORIZATION_REQUIRED')
  if route not in authorization['routes']:
    raise ValueError('EXACT_ROUTE_REQUIRED')
  if any(s['segment_sha256'] in authorization['qlog_deny_content_sha256'] for _, s, _, _ in records):
    raise ValueError('QLOG_CAUSAL_ADMISSION_FORBIDDEN')
  result = []
  for base, s, root, local in records:
    if s['route_id'] != route:
      continue
    d = {
      k: read.read_array(root / read.array_name(k), local['arrays'][k])
      for k in ('angle_tick', 'streak_all', 'model_eligible', 'rail', 's2_ri_causal_run_id', 'within_s2_ri_causal_run_index')
    }
    a = {k: read.read_array(base / 'arrays' / read.array_name(k), s['arrays'][k]) for k in ('command.normalized', 'state.speed_mps', 'grid_time_ns')}
    n = len(d['angle_tick'])
    if any(len(v) != n for v in [*d.values(), *a.values()]):
      raise ValueError('HURDLE_SOURCE_SHAPE_CONFLICT')
    good = d['model_eligible']
    continuity = np.r_[
      False,
      (np.diff(a['grid_time_ns']) == 10_000_000)
      & (d['s2_ri_causal_run_id'][1:] == d['s2_ri_causal_run_id'][:-1])
      & (np.diff(d['within_s2_ri_causal_run_index']) == 1),
    ]
    starts = good & ~(continuity & np.r_[False, good[:-1]])
    index = np.arange(n)
    expected = np.where(good, index - np.maximum.accumulate(np.where(starts, index, -1)) + 1, 0)
    if not np.array_equal(expected, d['streak_all']):
      raise ValueError('HURDLE_SOURCE_CONTINUITY_CONFLICT')
    result.append(
      {
        'route_id': route,
        'segment_sha256': s['segment_sha256'],
        'tick': d['angle_tick'],
        'streak': d['streak_all'],
        'command': a['command.normalized'],
        'speed': a['state.speed_mps'],
        'rail': d['rail'],
        'eligible': good,
        'run': d['s2_ri_causal_run_id'],
        'within': d['within_s2_ri_causal_run_index'],
      }
    )
  if not result or [s['segment_sha256'] for s in result] != sorted(s['segment_sha256'] for s in result):
    raise ValueError('HURDLE_SOURCE_ORDER_CONFLICT')
  return result


def binding(segments, candidate, horizon):
  blocks = [(s, m.anchors(s, candidate, horizon)) for s in segments]
  digest = p.sha(p.canonical([{'segment_sha256': s['segment_sha256'], 'count': len(ix), 'indices_sha256': p.sha(ix.tobytes())} for s, ix in blocks]))
  return blocks, digest, sum(len(ix) for _, ix in blocks)


def context(blocks, candidate):
  m.parameters(candidate)
  return context_source.context(blocks, candidate.replace('HRI_', 'S2RI_'))


def subset_sha(parent, mask):
  return p.sha(p.canonical({'parent_anchor_sha256': parent, 'mask_sha256': p.sha(mask.tobytes()), 'count': int(mask.sum())}))


def design(segments, candidate):
  blocks, digest, _ = binding(segments, candidate, 1)
  x = np.ascontiguousarray(np.concatenate([m.features(s, ix, candidate) for s, ix in blocks]))
  current = np.concatenate([s['tick'][ix] for s, ix in blocks])
  target = np.concatenate([s['tick'][ix + 1] for s, ix in blocks])
  return blocks, digest, x, current, target


def pair(error, baseline, digest, projected=None, target=None, hold=None):
  return {
    'count': len(error),
    'anchor_sha256': digest,
    'comparator_anchor_sha256': digest,
    'candidate': m.metrics(error, projected, target),
    'comparator': m.metrics(baseline, hold, target),
  }


def one_step(segments, candidate, stage1, threshold_value, stage2):
  blocks, digest, x, current, target = design(segments, candidate)
  actual = target - current
  move = actual != 0
  if min(len(x), int(move.sum()), int((~move).sum())) < m.SUPPORT:
    raise ValueError('HURDLE_DEVELOPMENT_SUPPORT_INSUFFICIENT')
  delta, projected, probability, gate = m.integrated(x, current, stage1, threshold_value, stage2)
  error = delta - actual.astype(np.float64)
  baseline = -actual.astype(np.float64)
  oracle_failure = None
  oracle = np.empty(0, dtype=np.float64)
  oracle_metrics = None
  try:
    oracle = m.predict_delta(np.ascontiguousarray(x[move]), stage2)
    oracle_projected = m.project(current[move].astype(np.float64) + oracle)
    oracle_metrics = m.metrics(oracle - actual[move].astype(np.float64), oracle_projected, target[move])
    oracle_metrics['sign_accuracy'] = float(np.mean(np.sign(oracle) == np.sign(actual[move])))
  except (ValueError, FloatingPointError) as oracle_error:
    if not any(term in str(oracle_error) for term in ('NUMERICAL', 'NONFINITE', 'RANGE')):
      raise
    oracle_failure = 'STAGE2_ORACLE_NUMERICAL_FAILURE'
  static_metrics = m.metrics(error[~move], projected[~move], target[~move])
  static_metrics.update(gate_false_move_rate=float(np.mean(gate[~move])), projected_false_move_rate=float(np.mean(projected[~move] != current[~move])))
  aggregates = {
    'one_step': pair(error, baseline, digest, projected, target, current),
    'true_move': pair(error[move], baseline[move], subset_sha(digest, move), projected[move], target[move], current[move]),
    'stage1_diagnostics': m.diagnostics(move, gate),
    'stage2_oracle': {'role': 'DIAGNOSTIC_ONLY', 'count': int(move.sum()), 'metrics': oracle_metrics, 'failure': oracle_failure},
    'static_diagnostics': {'count': int((~move).sum()), 'metrics': static_metrics},
    'development_constant_drift_columns': {
      label: int(sum(np.any(x[:, j] != model['normalizer']['constant_reference'][j]) for j in np.flatnonzero(model['normalizer']['constant'])))
      for label, model in (('stage1', stage1), ('stage2', stage2))
    },
  }
  arrays = {
    **context(blocks, candidate),
    'current_tick': current,
    'target_next_tick': target,
    'actual_delta_tick': actual,
    'p_move': probability,
    'predicted_gate': gate,
    'integrated_delta': delta,
    'projected_next_tick': projected,
    'candidate_error': error,
    'comparator_error': baseline,
    'true_move': move,
    'hold_last_next_tick': current.copy(),
    'stage2_oracle_move_prediction': oracle,
  }
  return aggregates, arrays


def rollout(segments, candidate, stage1, threshold_value, stage2, horizon):
  blocks, digest, n = binding(segments, candidate, horizon)
  if n < m.SUPPORT:
    raise ValueError('HURDLE_DEVELOPMENT_SUPPORT_INSUFFICIENT')
  d, length = m.parameters(candidate)
  paths, truth, gates = [], [], []
  for s, indices in blocks:
    for start in range(0, len(indices), m.CHUNK):
      ix = indices[start : start + m.CHUNK]
      initial = s['tick'][ix[:, None] + np.arange(-length, 1)]
      command = s['command'][ix[:, None] + np.arange(-d - length + 1, horizon - d)]
      speed = s['speed'][ix[:, None] + np.arange(horizon)]
      path, gate = m.recursive(initial, command, speed, candidate, stage1, threshold_value, stage2, horizon)
      paths.append(path)
      gates.append(gate)
      truth.append(s['tick'][ix[:, None] + np.arange(horizon + 1)])
  path, observed, gate_path = map(np.concatenate, (paths, truth, gates))
  initial, target = observed[:, 0].copy(), observed[:, -1].copy()
  error, baseline = (path[:, -1] - target).astype(np.float64), (initial - target).astype(np.float64)
  moved = np.any(observed != initial[:, None], axis=1)
  overall = pair(error, baseline, digest)
  protected = pair(error[moved], baseline[moved], subset_sha(digest, moved)) if int(moved.sum()) >= m.SUPPORT else None
  arrays = {
    **context(blocks, candidate),
    'initial_tick': initial,
    'target_endpoint_tick': target,
    'observed_path': observed,
    'projected_path': path,
    'hold_last_path': np.repeat(initial[:, None], horizon + 1, axis=1),
    'predicted_gate_path': gate_path,
    'candidate_error': error,
    'comparator_error': baseline,
    'path_moved': moved,
  }
  return {
    'overall': overall,
    'path_moved': protected,
    'path_moved_count': int(moved.sum()),
    'status': 'COMPLETE' if protected is not None else 'HURDLE_DEVELOPMENT_SUPPORT_INSUFFICIENT',
  }, arrays
