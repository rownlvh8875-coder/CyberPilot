"""Future-consumer rlog admission only; no reader, model, scoring or control execution.

Call require_segment before loading any arrays. eligible_rows consumes already
authorized, immutable in-memory arrays and returns a mask, never a fitting permit.
No process/global state, interpolation, imputation, new thresholds or file access.
"""
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_final_readiness as readiness


def require_segment(resolution, manifest, segment, evidence=None):
  x = readiness.load() if evidence is None else readiness.validate_inputs(evidence)
  readiness.validate_resolution(resolution, x)
  # Deny by content identity, not a caller-provided extension or stream label.
  excluded = {s['segment_sha256'] for s in x[readiness.QLOG_COVERAGE]['segments']}
  if segment.get('segment_sha256') in excluded:
    raise ValueError('QLOG_ACCOUNTING_ONLY_NEVER_MODEL_SUPPORT')
  p.verify(manifest)
  p.verify(segment)
  auth = x[readiness.RLOG_AUTH]
  if (manifest['schema'] != 'EMPIRICAL_CAUSAL_PRIVATE_DATASET_MANIFEST_V1'
      or manifest['receipt_sha256'] != resolution['rlog_dataset_manifest_sha256']
      or manifest['authorization_sha256'] != auth['private_authorization_sha256']
      or manifest['route_set_sha256'] != x[readiness.RLOG_ROUTES]['receipt_sha256']):
    raise ValueError('EXACT_HISTORICAL_RLOG_MANIFEST_REQUIRED')
  routes = {r['route_id']: r for r in x[readiness.RLOG_ROUTES]['routes']}
  members = {r['route_id']: r for r in manifest['routes']}
  rid = segment['route_id']
  if (set(members) != set(routes) or len(manifest['routes']) != 2 or rid not in routes
      or members[rid]['role'] != readiness.ROLE or segment['receipt_sha256'] not in members[rid]['segments']):
    raise ValueError('EXACT_RLOG_SEGMENT_MEMBER_AND_ROUTE_ROLE_REQUIRED')
  coverage = next(r for r in x[readiness.RLOG_COVERAGE]['routes'] if r['route_id'] == rid)
  if (segment['schema'] != 'EMPIRICAL_CAUSAL_SEGMENT_EXTRACTION_V1'
      or segment['authorization_sha256'] != auth['private_authorization_sha256']
      or segment['source_fingerprint_sha256'] != auth['source_fingerprint_sha256']
      or segment['recorded_adapter_sha256'] != auth['recorded_adapter_sha256']
      or segment['numeric_adapter_sha256'] != auth['numeric_adapter_sha256']
      or segment['config_sha256'] != coverage['config_sha256']):
    raise ValueError('SOURCE_ADAPTER_CONFIG_SEGMENT_BINDING_CONFLICT')
  return segment['arrays']


def eligible_rows(resolution, manifest, segment, arrays, evidence=None, history=1):
  """Return conservative future-design eligibility, not actual CV/model support.

  history is a caller's separately frozen contiguous window length, not selected
  here. All samples in that window must pass and stay in this single segment/run.
  The unchanged legacy diagnostic mask excludes inactive/override/fault contexts.
  This does not select family, history, output target, score or coefficients.
  """
  bindings = require_segment(resolution, manifest, segment, evidence)
  x = readiness.load() if evidence is None else evidence
  if type(history) is not int or history < 1:
    raise ValueError('POSITIVE_FROZEN_HISTORY_REQUIRED')
  if set(arrays) != set(bindings):
    raise ValueError('EXACT_SEALED_ARRAY_SET_REQUIRED')
  n = segment['coverage']['total_grid_samples']
  if type(n) is not int or n < 1:
    raise ValueError('VALID_SEGMENT_ROW_COUNT_REQUIRED')
  for key, array in arrays.items():
    binding = bindings[key]
    if (not isinstance(array, np.ndarray) or array.dtype.hasobject or not array.flags.c_contiguous
        or array.dtype.str != binding['dtype'] or list(array.shape) != binding['shape']
        or binding['order'] != 'C' or len(array) != n
        or p.sha(array.tobytes(order='C')) != binding['array_sha256']):
      raise ValueError('SEALED_ARRAY_DTYPE_SHAPE_ORDER_BYTES_CONFLICT')
  required = x['empirical-causal-context-schema-v2-execution-v1.json']['required_fields']
  essential = set(required) | {k+'.available' for k in required}
  essential |= {'grid_time_ns', 'causal_run_id', 'within_causal_run_index', 'causal_required_valid', 'legacy_diagnostic_valid'}
  essential |= {k+'.'+f for k in ('state', 'command', 'control') for f in
                ('time_ns', 'age_ns', 'event_valid', 'present', 'fresh', 'gap')}
  if not essential <= arrays.keys():
    raise ValueError('REQUIRED_CAUSAL_ARRAY_UNAVAILABLE_NO_SUBSTITUTION')
  bool_fields = [k+'.available' for k in required] + ['causal_required_valid', 'legacy_diagnostic_valid']
  bool_fields += [kind+'.'+field for kind in ('state', 'command', 'control') for field in ('present', 'fresh', 'gap')]
  if any(arrays[k].dtype.kind != 'b' or arrays[k].shape != (n,) for k in bool_fields):
    raise ValueError('EXPLICIT_BOOLEAN_AVAILABILITY_MASK_REQUIRED')
  integer_fields = ['grid_time_ns', 'causal_run_id', 'within_causal_run_index']
  integer_fields += [k+'.'+f for k in ('state', 'command', 'control') for f in ('time_ns', 'age_ns', 'event_valid')]
  if any(arrays[k].dtype.kind not in 'iu' or arrays[k].shape != (n,) for k in integer_fields):
    raise ValueError('EXACT_INTEGER_CLOCK_RUN_IDENTITY_REQUIRED')
  grid = arrays['grid_time_ns']
  if np.any(np.diff(grid) <= 0):
    raise ValueError('STRICT_GRID_ORDER_REQUIRED')
  if np.any(np.diff(arrays['state.time_ns']) < 0):
    raise ValueError('SOURCE_CLOCK_REGRESSION_REJECTED')
  mask = arrays['causal_required_valid'].copy() & arrays['legacy_diagnostic_valid']
  mask &= ~np.r_[False, np.diff(arrays['state.time_ns']) == 0]
  mask &= (arrays['causal_run_id'] >= 0) & (arrays['within_causal_run_index'] >= 0)
  for field in required:
    available, value = arrays[field+'.available'], arrays[field]
    if value.shape != (n,):
      raise ValueError('ONE_VALUE_PER_CAUSAL_ROW_REQUIRED')
    finite = value != '' if field == 'state.gear' else np.isfinite(value)
    mask &= available & finite
  for kind in ('state', 'command', 'control'):
    target_time = grid if kind == 'state' else arrays['state.time_ns']
    time, age, present = (arrays[kind+'.'+f] for f in ('time_ns', 'age_ns', 'present'))
    if np.any(present & (time > target_time)):
      raise ValueError('FUTURE_MESSAGE_LEAKAGE_REJECTED')
    if np.any(present & (age != target_time-time)):
      raise ValueError('SOURCE_AGE_IDENTITY_CONFLICT')
    mask &= (present & arrays[kind+'.fresh'] & (arrays[kind+'.event_valid'] == 1)
             & ~arrays[kind+'.gap'] & (time >= 0) & (age >= 0) & (age <= 20_000_000))
  result = mask.copy()
  for i in range(n):
    first = i-history+1
    if first < 0:
      result[i] = False
      continue
    span = slice(first, i+1)
    result[i] = (bool(mask[span].all()) and bool((arrays['causal_run_id'][span] == arrays['causal_run_id'][i]).all())
                 and bool((np.diff(arrays['within_causal_run_index'][span]) == 1).all())
                 and bool((np.diff(grid[span]) == 10_000_000).all()))
  return result
