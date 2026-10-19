"""Fresh canonical three-arm DEV arithmetic; never reuses saved BLAS outputs."""

import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bridge as b
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_evaluation as e1

need = b.need


def pair(error, baseline, anchor):
  need(error.dtype == baseline.dtype == np.float64 and error.shape == baseline.shape and error.ndim == 1, 'CANONICAL_METRIC_SHAPE')
  b.original.m.finite(error, baseline)
  if len(error) < 201:
    return None
  return {
    'count': len(error),
    'anchor_sha256': anchor,
    'candidate': b.original.m.metrics(error),
    'comparator_anchor_sha256': anchor,
    'comparator': b.original.m.metrics(baseline),
    'hold_last': b.original.m.metrics(baseline),
  }


def subset_anchor(anchor, mask):
  return e1.data.subset_sha(anchor, mask)


def evaluate(data, paths, policies, clauses, counters):
  current, target, prior, p = (data[k] for k in ('current', 'target', 'prior', 'p'))
  truth = target != current
  actual = (target - current).astype(np.float64)
  hold = -actual
  results = {}
  for arm in b.ARMS:
    row = b.infer(data['x'], current, data['stage1'], data['stage2'], policies[arm], arm, counters, scope=b.SCOPE, p_move=p)
    error = row['delta'] - actual
    predicted = row['projected']
    one = pair(error, hold, data['anchor'])
    if one is not None:
      one['candidate'].update({'exact_hit': float(np.mean(predicted == target)), 'within_one_tick': float(np.mean(np.abs(predicted - target) <= 1))})
      one['comparator'].update({'exact_hit': float(np.mean(current == target)), 'within_one_tick': float(np.mean(np.abs(current - target) <= 1))})
    result = {
      'status': 'EXECUTED_COMPLETE',
      'one_step': one,
      'true_move': pair(error[truth], hold[truth], subset_anchor(data['anchor'], truth)),
      'tick_diagnostics': e1.tick_diagnostics(current, target, prior, row),
      'score_diagnostics': e1.score_diagnostics(p, truth, prior),
      'rollout': {},
    }
    for h in b.HORIZONS:
      need(h in paths['horizons'], 'CANONICAL_HORIZON_BINDING')
      inputs = paths['horizons'][h]
      initial, command, speed, observed = (inputs[k] for k in ('initial', 'command', 'speed', 'observed'))
      count = len(initial)
      need(observed.dtype == np.int64 and observed.shape == (count, h + 1) and np.array_equal(observed[:, 0], initial[:, -1]), 'CANONICAL_REFERENCE_ANCHOR')
      need(np.all((observed >= -32768) & (observed <= 32767)), 'CANONICAL_REFERENCE_TICK_RANGE')
      errors, baselines, moved, drift = [], [], [], {}
      for first in range(0, count, 512):
        stop = min(first + 512, count)
        out = b.recursive(
          initial[first:stop],
          command[first:stop],
          speed[first:stop],
          data['candidate'],
          data['stage1'],
          data['stage2'],
          policies[arm],
          arm,
          h,
          inputs['available_steps'][first:stop],
          counters,
          scope=b.SCOPE,
        )
        reference = observed[first:stop]  # Truth used only after recursive prediction.
        errors.append((out['path'][:, -1] - reference[:, -1]).astype(np.float64))
        baselines.append((reference[:, 0] - reference[:, -1]).astype(np.float64))
        moved.append(b.path_moved(reference))
        chunk, _, _ = e1.drift_chunk(initial[first:stop], reference, out['path'], out['gate'], out['context'], b.original.m.parameters(data['candidate'])[1])
        for key, value in chunk.items():
          drift[key] = drift.get(key, np.zeros_like(value)) + value
        del out
      error_h, hold_h, moved_h = np.concatenate(errors), np.concatenate(baselines), np.concatenate(moved)
      anchor = inputs['anchor']
      result['rollout'][str(h)] = {
        'overall': pair(error_h, hold_h, anchor),
        'path_moved': pair(error_h[moved_h], hold_h[moved_h], subset_anchor(anchor, moved_h)),
        'status': 'COMPLETE' if count >= 201 and int(np.count_nonzero(moved_h)) >= 201 else 'V4_ROLLOUT_SUPPORT_FAILURE',
        'full_state_drift': {key: value.tolist() for key, value in drift.items()},
      }
    result['gate'] = e1.gates.fold_gate(result, clauses)
    results[arm] = result
  return {'candidate_id': data['candidate'], 'fold': data['fold'], 'anchor': data['anchor'], 'arms': results, 'evidence_scope': 'SYNTHETIC_ONLY'}
