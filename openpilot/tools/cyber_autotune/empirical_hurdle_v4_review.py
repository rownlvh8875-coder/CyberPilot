"""Read-only design evidence checks; no model, threshold or rollout executor."""

import json
from pathlib import Path

import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_temporal_math as temporal

BASELINE = 'b7e91e57c3d19be827c8757d9803e4744ddcf4a9'
INCONCLUSIVE = 'V4_ARCHITECTURE_REDESIGN_INCONCLUSIVE'


def require(condition):
  if not condition:
    raise ValueError('V4_ARCHITECTURE_INPUT_CONFLICT')


def verify_inputs(binding, directory=p.PUBLIC):
  """Only receipt-pinned public JSON members, never private numeric payloads."""
  p.verify(binding)
  require(binding['baseline'] == BASELINE and type(binding['public_inputs']) is dict)
  result = {}
  for name, pin in binding['public_inputs'].items():
    require(Path(name).name == name and name.endswith('.json'))
    member = directory / name
    require(not member.is_symlink())
    data = member.read_bytes()
    require(p.sha(data) == pin['file_sha256'])
    row = p.verify(json.loads(data))
    require(row['receipt_sha256'] == pin['receipt_sha256'])
    result[name] = row
  return result


def singleton_fragments(delta, linked):
  """Eligible stored fragments; censored ends are never called complete runs."""
  temporal.truth(delta, delta)
  require(linked.dtype == np.bool_ and linked.shape == delta.shape and not linked[0])
  move = delta != 0
  starts = np.flatnonzero(~linked | np.r_[False, move[1:] != move[:-1]])
  ends = np.r_[starts[1:], len(move)]
  selected = move[starts]
  starts, ends = starts[selected], ends[selected]
  single = ends - starts == 1
  censored = np.array([not linked[lo] or hi == len(move) or not linked[hi]
                       for lo, hi in zip(starts, ends, strict=True)], dtype=bool)
  count = int(np.sum(single))
  return {
    'move_fragment_count': len(starts),
    'length_one_count': count,
    'length_one_fraction': count / len(starts) if len(starts) else None,
    'boundary_censored_length_one_count': int(np.sum(single & censored)),
    'uncensored_length_one_count': int(np.sum(single & ~censored)),
    'boundary_censored_move_fragment_count': int(np.sum(censored)),
    'interpretation': 'ELIGIBLE_OBSERVED_FRAGMENTS_NOT_COMPLETE_RAW_ROUTE_RUNS',
  }


def valid_prior_context(relative_delta_index, source, same_continuous_run):
  """Timing witness only. Missing/reset state must not silently become STATIC."""
  return relative_delta_index == -1 and source == 'OBSERVED_SOURCE_GRID' and same_continuous_run is True


def design_outcome(options):
  """Select architectures by a unique lexicographic design key, never performance."""
  eligible = [r for r in options if r['eligible'] is True]
  if not eligible:
    return {'status': INCONCLUSIVE, 'selected': None, 'reason': 'NO_FULLY_ELIGIBLE_ARCHITECTURE'}
  best = min(tuple(r['cost']) for r in eligible)
  tied = [r for r in eligible if tuple(r['cost']) == best]
  if len(tied) != 1:
    return {'status': INCONCLUSIVE, 'selected': None, 'reason': 'UNRESOLVED_DESIGN_TIE'}
  return {'status': 'V4_ARCHITECTURE_SELECTED', 'selected': tied[0]['id'], 'reason': 'UNIQUE_ELIGIBLE_LEXICOGRAPHIC_MINIMUM'}


def validate_audit(wrapper, lock_sha):
  """Validate independent run receipts and exact aggregate schema before publication."""
  sealed = set(p.FIREWALL) | {'receipt_sha256'}
  wrapper_fields = {'schema', 'baseline', 'public_input_lock_sha256', 'runs', 'status', 'audit_executor_sha256'}
  run_fields = {'schema', 'baseline', 'public_input_lock_sha256', 'v1_manifest_sha256', 'storage', 'routes',
                'source_member_count', 'numeric_array_open_count', 'source_members_unchanged_sha256', 'immutability_scope',
                'source_writes', 'fit_calls', 'prediction_calls', 'threshold_search_calls', 'rollout_calls', 'raw_qlog_holdout_openings'}
  route_fields = {'anchor_sha256', 'source_receipt_sha256', 'move_fragment_count', 'length_one_count', 'length_one_fraction',
                  'boundary_censored_length_one_count', 'uncensored_length_one_count', 'boundary_censored_move_fragment_count', 'interpretation'}
  def sha(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)
  p.verify(wrapper)
  require(set(wrapper) == wrapper_fields | sealed)
  require(wrapper['schema'] == 'V4_STORED_SINGLETON_AUDIT_REPEATABILITY' and wrapper['baseline'] == BASELINE)
  require(wrapper['public_input_lock_sha256'] == lock_sha and wrapper['status'] == 'BYTE_EXACT_PASS')
  require(sha(wrapper['audit_executor_sha256']) and type(wrapper['runs']) is list and len(wrapper['runs']) == 2)
  for run in wrapper['runs']:
    p.verify(run)
    require(set(run) == run_fields | sealed)
    require(run['schema'] == 'V4_STORED_SINGLETON_FRAGMENT_AUDIT' and run['baseline'] == BASELINE)
    require(run['public_input_lock_sha256'] == lock_sha)
    require(run['v1_manifest_sha256'] == 'c4de3955c12cd0d9721d4c7c1519da53b4d80f80be0c05e142047853a7b217a6')
    require(run['storage'] == 'E_EXTERNAL_SSD' and run['source_member_count'] == 15 and run['numeric_array_open_count'] == 12)
    require(run['immutability_scope'] == 'OPENED_MANIFEST_BOUND_MEMBERS_ONLY' and sha(run['source_members_unchanged_sha256']))
    require(all(type(run[k]) is int and run[k] == 0 for k in ('source_writes', 'fit_calls', 'prediction_calls',
                                                           'threshold_search_calls', 'rollout_calls', 'raw_qlog_holdout_openings')))
    require(type(run['routes']) is dict and len(run['routes']) == 2)
    for route, row in run['routes'].items():
      require(sha(route) and type(row) is dict and set(row) == route_fields)
      require(sha(row['anchor_sha256']) and sha(row['source_receipt_sha256']))
      require(row['interpretation'] == 'ELIGIBLE_OBSERVED_FRAGMENTS_NOT_COMPLETE_RAW_ROUTE_RUNS')
      counts = ('move_fragment_count', 'length_one_count', 'boundary_censored_length_one_count',
                'uncensored_length_one_count', 'boundary_censored_move_fragment_count')
      require(all(type(row[k]) is int and row[k] >= 0 for k in counts) and row['move_fragment_count'] > 0)
      require(row['length_one_count'] == row['boundary_censored_length_one_count'] + row['uncensored_length_one_count'])
      require(row['length_one_count'] <= row['move_fragment_count'])
      require(row['boundary_censored_length_one_count'] <= row['boundary_censored_move_fragment_count'] <= row['move_fragment_count'])
      require(row['length_one_fraction'] == row['length_one_count'] / row['move_fragment_count'])
  require(p.canonical(wrapper['runs'][0]) == p.canonical(wrapper['runs'][1]))
  return wrapper['runs'][0]
