"""Family-specific derived admission identity; historical identities never rewritten."""
import numpy as np
from openpilot.tools.cyber_autotune import empirical_s2_ri_math as m
from openpilot.tools.cyber_autotune.empirical_identifiability_math import streaks

REQUIRED = ('state.speed_mps', 'state.angle_deg', 'state.driver_pressed', 'state.driver_torque', 'state.gear',
            'state.fault_temporary', 'state.fault_permanent', 'command.raw', 'command.normalized', 'control.lat_active')
CONTEXT = ('control.lat_active', 'state.driver_pressed', 'state.fault_temporary', 'state.fault_permanent')
HEALTH = ('time_ns', 'age_ns', 'event_valid', 'present', 'fresh', 'gap')
FIELDS = (*REQUIRED, *(k+'.available' for k in REQUIRED), 'grid_time_ns', 'legacy_diagnostic_valid',
          *(kind+'.'+f for kind in ('state', 'command', 'control') for f in HEALTH))


def derive(a):
  """Process exactly one receipt-bound segment. No rate/request/historical run gate."""
  if not set(FIELDS) <= a.keys():
    raise ValueError('REQUIRED_RATE_FREE_FIELDS_MISSING')
  n = len(a['grid_time_ns'])
  bools = {k+'.available' for k in REQUIRED} | {'legacy_diagnostic_valid'}
  bools |= {k+'.'+f for k in ('state', 'command', 'control') for f in ('present', 'fresh', 'gap')}
  integers = {'grid_time_ns'} | {k+'.'+f for k in ('state', 'command', 'control') for f in ('time_ns', 'age_ns', 'event_valid')}
  for k in FIELDS:
    if not isinstance(a[k], np.ndarray) or a[k].shape != (n,):
      raise ValueError('ONE_SEALED_VALUE_PER_ROW_REQUIRED')
    expected = 'b' if k in bools else 'iu' if k in integers else 'U' if k == 'state.gear' else 'f'
    if a[k].dtype.kind not in expected:
      raise ValueError('EXACT_SOURCE_FIELD_DTYPE_REQUIRED')
  grid = a['grid_time_ns']
  if np.any(np.diff(grid) <= 0):
    raise ValueError('STRICT_GRID_ORDER_REQUIRED')
  good = np.ones(n, dtype=bool)
  for field in REQUIRED:
    finite = a[field] != '' if field == 'state.gear' else np.isfinite(a[field])
    good &= a[field+'.available'] & finite
  for field in CONTEXT:
    available = a[field+'.available']
    if np.any(available & ~np.isin(a[field], [0., 1.])):
      raise ValueError('EXPLICIT_BOOLEAN_SOURCE_VALUE_REQUIRED')
  for kind in ('state', 'command', 'control'):
    time, age, present = (a[kind+'.'+f] for f in ('time_ns', 'age_ns', 'present'))
    target = grid if kind == 'state' else a['state.time_ns']
    if np.any(np.diff(time[present]) < 0):
      raise ValueError('SOURCE_CLOCK_REGRESSION_REJECTED')
    if np.any(present & (time > target)):
      raise ValueError('FUTURE_MESSAGE_LEAKAGE_REJECTED')
    if np.any(present & (age != target-time)):
      raise ValueError('SOURCE_AGE_IDENTITY_CONFLICT')
    good &= present & a[kind+'.fresh'] & ~a[kind+'.gap'] & (a[kind+'.event_valid'] == 1)
    good &= (time >= 0) & (age >= 0) & (age <= m.AGE)
  good &= ~np.r_[False, np.diff(a['state.time_ns']) == 0]
  bridge = a['command.raw.available'] & a['command.normalized.available']
  raw, normalized = a['command.raw'], a['command.normalized']
  if np.any(bridge & (~np.isfinite(raw) | (raw != np.rint(raw)) | (abs(raw) > 409)
                      | (normalized != (raw/409).astype(np.float32).astype(np.float64)))):
    raise ValueError('SOURCE_COMMAND_BRIDGE_CONFLICT')
  tick, grid_valid = m.grid_ticks(a['state.angle_deg'])
  # Source/timing integrity and model regime remain separate.
  regime = (a['control.lat_active'] == 1) & (a['state.driver_pressed'] == 0)
  regime &= (a['state.fault_temporary'] == 0) & (a['state.fault_permanent'] == 0)
  regime &= (a['state.gear'] == 'drive') & (a['state.speed_mps'] >= 5)
  eligible = good & grid_valid & regime & a['legacy_diagnostic_valid']
  runs = np.full(n, -1, dtype=np.int64)
  within = np.full(n, -1, dtype=np.int64)
  serial, index = -1, 0
  for k in range(n):
    if not good[k]:
      continue
    linked = (k > 0 and good[k-1] and grid[k]-grid[k-1] == m.DT
              and all(a[f][k] == a[f][k-1] for f in CONTEXT))
    if not linked:
      serial += 1
      index = 0
    runs[k], within[k] = serial, index
    index += 1
  rail = bridge & (abs(raw) == 409)
  return {'s2_ri_causal_valid': good, 's2_ri_causal_run_id': runs,
          'within_s2_ri_causal_run_index': within, 'model_eligible': eligible,
          'angle_grid_valid': grid_valid, 'angle_tick': tick, 'rail': rail,
          'base_regime': regime, 'streak_all': streaks(eligible, runs, within, grid),
          'streak_non_rail': streaks(eligible & ~rail, runs, within, grid)}


def identity_contract():
  from openpilot.tools.cyber_autotune import empirical_plant_policy as p
  return p.seal({'schema': 'EMPIRICAL_S2_RI_CAUSAL_IDENTITY_V1',
    'meaning': 'FAMILY_SPECIFIC_DERIVED_ADMISSION_IDENTITY',
    'historical_generic_causal_identity': 'RATE_DEPENDENT_IMMUTABLE_REFERENCE_ONLY',
    's2_ri_causal_identity': 'RATE_FREE_FAMILY_SPECIFIC_IDENTITY',
    'required': list(REQUIRED), 'source_health': list(HEALTH), 'dt_ns': m.DT, 'max_age_ns': m.AGE,
    'excluded_dependencies': ['state.rate', 'state.rate.available', 'control.requested', 'control.requested.available',
      'causal_required_valid', 'causal_run_id', 'within_causal_run_index', 'run_boundary', 'consumed_input_snapshot_sha256'],
    'validity': 'REQUIRED_FINITE_AVAILABLE_HEALTHY_LATEST_PAST_NONREPEATED_STATE',
    'runs': 'SEGMENT_LOCAL_SOURCE_VALID_CONTIGUOUS_GRID_BREAK_AT_ACTIVE_PRESSED_FAULT_CHANGES',
    'source_config_drift': 'HARD_FAILURE_BEFORE_ARRAYS',
    'explicit_reset_observability': 'NO_SEPARATE_RESET_EVENT_IN_CACHE_GAPS_SEGMENT_AND_CONTEXT_BOUNDARIES_ENFORCED',
    'historical_legacy_mask': 'RATE_INDEPENDENT_DIAGNOSTIC_VALID_ADDITIONAL_MODEL_GATE',
    'model_regime': 'ACTIVE_NO_OVERRIDE_NO_FAULT_DRIVE_SPEED_GE_5_AND_EXACT_SOURCE_GRID',
    'historical_rewrite': False, 'source_dataset_correction_claim': False})


def row_contract():
  from openpilot.tools.cyber_autotune import empirical_plant_policy as p
  return p.seal({'schema': 'EMPIRICAL_S2_RI_ROW_ADMISSION_V1',
    'causal_identity_sha256': identity_contract()['receipt_sha256'],
    'container': 'EXACT_154_RLOG_CONTENT_IDENTITIES_BEFORE_ARRAY_ACCESS',
    'source_profile_config': 'EXACT_HISTORICAL_RECEIPT_BINDINGS',
    'causal_layer': 'S2_RI_CAUSAL_VALID',
    'model_layer': 'S2_RI_BASE_MODEL_ELIGIBLE',
    'steering_rate_required': False, 'controller_request_required': False,
    'historical_generic_causal_identity': 'RATE_DEPENDENT_IMMUTABLE_REFERENCE_ONLY',
    's2_ri_causal_identity': 'RATE_FREE_FAMILY_SPECIFIC_IDENTITY',
    'scopes': list(m.SCOPES), 'selected_scope': None,
    'qlog_model_support': 0, 'holdout_allowed': False, 'fitting_allowed': False,
    'missing': 'REJECT_NO_ZERO_OR_FALSE_SUBSTITUTION'})
