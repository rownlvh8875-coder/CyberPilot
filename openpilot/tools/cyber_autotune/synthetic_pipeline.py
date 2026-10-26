"""Bounded OFFLINE synthetic comparison, never runtime or vehicle admission.

Fixed trusted worker only (not an adversarial OS sandbox). Source content hashes
bind declared local dependencies, not hardware qualification or signed evidence.
Baseline/current are identity arms of the same pinned native controller core;
this is not a whole-upstream versus whole-Cyber planner/process comparison.
"""
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import tempfile

from openpilot.tools.cyber_autotune.contracts import finite_number, is_sha256
from openpilot.tools.cyber_autotune.native_protocol import _unique_pairs, canonical, digest
from openpilot.tools.cyber_autotune.native_runner import _run_process
from openpilot.tools.cyber_autotune.synthetic_native_v2 import POLICY_SHA256, frozen_policy
from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog, catalog_digest, input_digest


ROOT = Path(__file__).resolve().parents[3]
MAX_OUTPUT = 2 * 1024 * 1024
ARMS = {'baseline': 'identity', 'current': 'identity', 'gentle': 'gentle', 'firm': 'firm'}
AUTHORITY = ('real_vehicle_verified', 'runtime_accepted', 'active_profile_enabled', 'vehicle_write_enabled',
             'can_write_enabled', 'promotable_to_vehicle')
SOURCE_DIRS = ('openpilot/tools/cyber_autotune', 'openpilot/common', 'openpilot/selfdrive/controls/lib',
               'openpilot/cereal', 'opendbc_repo/opendbc/car', 'opendbc_repo/opendbc/can')
SOURCE_EXTRA = ('openpilot/__init__.py', 'openpilot/selfdrive/__init__.py', 'openpilot/selfdrive/controls/__init__.py',
                'openpilot/selfdrive/modeld/__init__.py', 'openpilot/selfdrive/modeld/constants.py',
                'openpilot/tools/__init__.py', 'opendbc_repo/opendbc/__init__.py')
COMMON_METRICS = set(AUTHORITY) | {'metric_version', 'truth_scope', 'sample_count', 'dt_s', 'trace_sha256',
                                 'timebase_gap_count', 'vehicle_activation_allowed', 'saturation_ratio'}
AXIS_METRICS = {
  'lateral': set('''center_rms_m center_p95_abs_m center_max_abs_m center_mean_m left_curve_rms_m right_curve_rms_m
                 left_right_rms_asymmetry_m curve_inside_bias_m lane_edge_minimum_margin_m heading_error_rms_rad
                 curvature_tracking_rms_1pm yaw_tracking_rms_rps command_derivative_rms_per_s requested_command_jerk_rms_per_s3
                 applied_command_jerk_rms_per_s3 steering_jerk_rms_deg_s3 steering_tracking_rms_deg command_zero_crossings
                 command_crossing_pair_frequency_hz saturation_duration_s rate_limited_duration_s override_frames
                 override_recovery_s unresolved_recoveries maximum_command_step command_oscillation_pair_count lane_loss_recovery_s'''.split()),
  'longitudinal': set('''minimum_ttc_s lead_distance_rms_m maximum_deceleration_mps2 acceleration_tracking_rms_mps2
                      braking_overshoot_mps2 actual_jerk_rms_mps3 command_jerk_rms_mps3 stopping_overshoot_m stop_episode_count
                      unresolved_stops stopping_error_m stopping_error_abs_m restart_delay_s unresolved_restarts cut_in_response_s
                      unresolved_cut_ins false_stop_frames false_braking_frames maximum_acceleration_command_step_mps2
                      actual_jerk_p95_abs_mps3 actual_jerk_max_abs_mps3 command_jerk_p95_abs_mps3 command_jerk_max_abs_mps3
                      cut_in_peak_deceleration_mps2 false_stop_duration_s'''.split()),
}
NULLABLE_METRICS = set('''left_curve_rms_m right_curve_rms_m left_right_rms_asymmetry_m curve_inside_bias_m override_recovery_s
                       minimum_ttc_s lead_distance_rms_m braking_overshoot_mps2 stopping_overshoot_m stopping_error_m
                       stopping_error_abs_m restart_delay_s cut_in_response_s lane_loss_recovery_s cut_in_peak_deceleration_mps2'''.split())
VARIANT_FIELDS = set(AUTHORITY) | set('''schema scope case_id axis tune_id tune_sha256 policy_sha256 input_sha256 physical_delay_s
  physical_delay_owner controller_delay_queue_present input_status controller_executed metrics perception_planner_executed
  vehicle_carcontroller_executed unexercised_inputs unavailable_behavior time_semantics lateral_reference_history_compensation_s
  feedback_measurement status'''.split())
COMPLETED_FIELDS = set('base_car_params_sha256 candidate_car_params_sha256 controller plant_sha256 reset_sha256'.split())


def source_binding() -> dict:
  files = {}
  for name in SOURCE_EXTRA:
    files[name] = digest((ROOT / name).read_bytes())
  for directory in SOURCE_DIRS:
    for path in sorted((ROOT / directory).rglob('*')):
      if path.suffix not in ('.py', '.so', '.capnp', '.yaml', '.toml') or not path.is_file():
        continue
      if not path.resolve().is_relative_to(ROOT) or path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('UNSUPPORTED_SOURCE_DEPENDENCY')
      files[path.relative_to(ROOT).as_posix()] = digest(path.read_bytes())
  if not files:
    raise ValueError('MISSING_SOURCE_DEPENDENCIES')
  return {'files_sha256': digest(canonical(files)), 'file_count': len(files), 'python': platform.python_version(),
          'platform': platform.machine(), 'numpy': importlib.metadata.version('numpy'),
          'pycapnp': importlib.metadata.version('pycapnp'), 'policy_sha256': POLICY_SHA256,
          'catalog_sha256': catalog_digest(), 'metric_sha256': digest((Path(__file__).with_name('synthetic_metrics.py')).read_bytes()),
          'source_scope': [*SOURCE_DIRS, *SOURCE_EXTRA]}


def verify_worker_imports():
  """Worker-only assertion: executed local modules must belong to bound scope."""
  for name, module in tuple(sys.modules.items()):
    if name not in ('openpilot', 'opendbc') and not name.startswith(('openpilot.', 'opendbc.')):
      continue
    filename = getattr(module, '__file__', None)
    if filename is None:
      raise ValueError('UNBOUND_NAMESPACE_IMPORT')
    path = Path(filename).resolve()
    if not path.is_relative_to(ROOT):
      raise ValueError('IMPORT_ROOT_MISMATCH')
    relative = path.relative_to(ROOT).as_posix()
    if (path.suffix not in ('.py', '.so', '.capnp', '.yaml', '.toml') or
        not (relative in SOURCE_EXTRA or any(relative.startswith(directory + '/') for directory in SOURCE_DIRS))):
      raise ValueError('UNBOUND_SOURCE_IMPORT')


def validate_binding(binding):
  expected = {'files_sha256', 'file_count', 'python', 'platform', 'numpy', 'pycapnp', 'policy_sha256',
              'catalog_sha256', 'metric_sha256', 'source_scope'}
  if type(binding) is not dict or set(binding) != expected:
    raise ValueError('INVALID_SOURCE_BINDING')
  for key in expected:
    value = binding[key]
    if key.endswith('_sha256') and (type(value) is not str or not is_sha256(value)):
      raise ValueError('INVALID_SOURCE_DIGEST')
  if (type(binding['file_count']) is not int or binding['file_count'] < 1 or
      binding['source_scope'] != [*SOURCE_DIRS, *SOURCE_EXTRA] or
      any(type(binding[k]) is not str or not binding[k] or len(binding[k]) > 64 for k in ('python', 'platform', 'numpy', 'pycapnp'))):
    raise ValueError('INVALID_SOURCE_METADATA')


def validate_arm(result, tune, binding):
  validate_binding(binding)
  policy = frozen_policy()
  if tune not in policy['candidate_grid']:
    raise ValueError('INVALID_TUNE')
  if type(result) is not dict or set(result) != {'schema', 'status', 'tune_id', 'binding', 'results', 'vehicle_activation_allowed'}:
    raise ValueError('INVALID_ARM_FIELDS')
  if (result['schema'] != 'synthetic-arm-v2' or result['status'] != 'COMPLETED_SYNTHETIC_ONLY' or
      result['tune_id'] != tune or result['binding'] != binding or result['vehicle_activation_allowed'] is not False):
    raise ValueError('INVALID_ARM_BINDING')
  rows = result['results']
  variants = [(case, delay) for case in catalog() for delay in case.physical_delays_s]
  if type(rows) is not list or len(rows) != len(variants):
    raise ValueError('INCOMPLETE_VARIANT_MATRIX')
  for row, (case, delay) in zip(rows, variants, strict=True):
    expected_fields = VARIANT_FIELDS | (COMPLETED_FIELDS if case.expected_input_status == 'VALID' else set())
    if type(row) is not dict or set(row) != expected_fields:
      raise ValueError('INVALID_VARIANT_FIELDS')
    if (type(row) is not dict or row.get('case_id') != case.case_id or row.get('physical_delay_s') != delay or
        row.get('tune_id') != tune or row.get('policy_sha256') != POLICY_SHA256 or
        any(row.get(key) is not False for key in AUTHORITY) or row.get('input_status') != case.expected_input_status):
      raise ValueError('INVALID_VARIANT_BINDING')
    if (row['axis'] != case.axis or row['schema'] != 'synthetic-native-v2' or
        row['input_sha256'] != input_digest(case) or row['tune_sha256'] != digest(canonical(policy['candidate_grid'][tune])) or
        row['physical_delay_owner'] != 'PLANT' or row['controller_delay_queue_present'] is not False or
        row['perception_planner_executed'] is not False or row['vehicle_carcontroller_executed'] is not False):
      raise ValueError('VARIANT_IDENTITY_MISMATCH')
    fixed = {
      'scope': 'NATIVE_CONTROLLER_CORE_SUPPLIED_PLAN_GENERIC_PLANT',
      'unavailable_behavior': 'PERCEPTION_PLANNER_AND_VEHICLE_CARCONTROLLER',
      'time_semantics': 'INPUT_COMMAND_AT_INTERVAL_START_STATE_AT_INTERVAL_END',
      'unexercised_inputs': ['lane_visible'] if case.axis == 'lateral' else ['radar_model_disagreement'],
      'lateral_reference_history_compensation_s': .15 if case.axis == 'lateral' else None,
      'feedback_measurement': 'NATIVE_VEHICLE_MODEL_INVERSE' if case.axis == 'lateral' else 'GENERIC_PLANT_STATE',
    }
    if any(row[key] != value for key, value in fixed.items()):
      raise ValueError('INVALID_FIXED_METADATA')
    if case.expected_input_status != 'VALID':
      if row.get('status') != 'REJECTED_INPUT' or row.get('controller_executed') is not False or row.get('metrics') is not None:
        raise ValueError('FAULT_NOT_REJECTED')
    elif (row.get('status') != 'COMPLETED_SYNTHETIC_ONLY' or row.get('controller_executed') is not True or
          type(row.get('metrics')) is not dict or any(row['metrics'].get(key) is not False for key in AUTHORITY)):
      raise ValueError('INVALID_COMPLETED_VARIANT')
    if case.expected_input_status == 'VALID':
      if row['controller'] != ('LatControlTorque' if case.axis == 'lateral' else 'LongControl'):
        raise ValueError('INVALID_CONTROLLER')
      for key in ('base_car_params_sha256', 'candidate_car_params_sha256', 'plant_sha256', 'reset_sha256'):
        if type(row[key]) is not str or not is_sha256(row[key]):
          raise ValueError('INVALID_VARIANT_DIGEST')
      metrics = row['metrics']
      if (set(metrics) != COMMON_METRICS | AXIS_METRICS[case.axis] or
          metrics['metric_version'] != 'synthetic-metrics-v2' or metrics['truth_scope'] != 'GENERIC_SYNTHETIC_ONLY' or
          type(metrics['sample_count']) is not int or metrics['sample_count'] != round(case.duration_s / case.dt_s) or
          metrics['dt_s'] != case.dt_s or metrics['timebase_gap_count'] != 0 or
          metrics['vehicle_activation_allowed'] is not False or not is_sha256(metrics['trace_sha256'])):
        raise ValueError('INVALID_METRIC_SCHEMA')
      if case.axis == 'lateral' and metrics['lane_loss_recovery_s'] is not None:
        raise ValueError('UNAVAILABLE_LANE_LOSS_MEASUREMENT')
      for key in AXIS_METRICS[case.axis] | {'saturation_ratio'}:
        value = metrics[key]
        if value is None and key in NULLABLE_METRICS:
          continue
        if not finite_number(value):
          raise ValueError('INVALID_METRIC_VALUE')
        if key not in {'center_mean_m', 'curve_inside_bias_m', 'lane_edge_minimum_margin_m', 'stopping_error_m'} and value < 0:
          raise ValueError('INVALID_METRIC_DOMAIN')
        if key.endswith(('_frames', '_count')) or key.startswith('unresolved_') or key == 'command_zero_crossings':
          if type(value) is not int or value > metrics['sample_count']:
            raise ValueError('INVALID_METRIC_COUNT')
        if key == 'saturation_ratio' and value > 1:
          raise ValueError('INVALID_METRIC_RATIO')
  canonical(result)  # reject NaN/Infinity anywhere


def run_arm(tune_id: str, *, timeout_s: float = 60.) -> dict:
  policy = frozen_policy()
  if type(tune_id) is not str or tune_id not in policy['candidate_grid'] or not finite_number(timeout_s) or not 0 < timeout_s <= 120:
    raise ValueError('INVALID_SYNTHETIC_WORKER_REQUEST')
  failure = {'status': 'BLOCKED', 'reason': 'WORKER_FAILED', 'vehicle_activation_allowed': False}
  if sys.platform != 'linux':
    return {**failure, 'reason': 'UNSUPPORTED_PLATFORM'}
  try:
    before = source_binding()
    if before['catalog_sha256'] != policy['catalog_sha256']:
      return {**failure, 'reason': 'CATALOG_CHANGED'}
    payload = canonical({'tune_id': tune_id, 'binding': before})
    # -B prevents cache writes; a fresh empty prefix prevents reading old pyc.
    with tempfile.TemporaryDirectory(prefix='cyber-synthetic-') as cache:
      observed = _run_process([sys.executable, '-I', '-B', '-X', 'pycache_prefix=' + cache,
                               str(Path(__file__).with_name('synthetic_worker_v2.py'))], payload, timeout_s)
    if observed.status != 'EXITED' or observed.returncode != 0:
      return {**failure, 'reason': 'WORKER_TIMEOUT' if observed.status == 'TIMEOUT' else 'WORKER_FAILED'}
    if not 0 < len(observed.stdout) <= MAX_OUTPUT:
      return {**failure, 'reason': 'OUTPUT_BOUND'}
    result = json.loads(observed.stdout, object_pairs_hook=_unique_pairs)
    validate_arm(result, tune_id, before)
    if source_binding() != before:
      return {**failure, 'reason': 'SOURCE_CHANGED_DURING_RUN'}
    return result
  except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
    return {**failure, 'reason': 'INVALID_WORKER_EVIDENCE'}


def _compare(base, candidate, policy):
  reasons = []
  improvements = []
  keys = ('input_sha256', 'plant_sha256', 'reset_sha256', 'base_car_params_sha256', 'time_semantics',
          'policy_sha256', 'physical_delay_owner', 'controller_delay_queue_present')
  for left, right in zip(base['results'], candidate['results'], strict=True):
    case = left['case_id']
    if any(left.get(k) != right.get(k) for k in keys) or left['status'] != right['status']:
      reasons.append(case + ':COMPARISON_BINDING_MISMATCH')
      continue
    if left['metrics'] is None:
      continue
    lm, rm = left['metrics'], right['metrics']
    if set(lm) != set(rm):
      reasons.append(case + ':METRIC_SCHEMA_CHANGED')
      continue
    for key in (*policy['lower_is_better'], *policy['higher_is_better']):
      if key not in lm:
        continue  # other axis; schemas must match above
      a, b = lm[key], rm[key]
      if a is None or b is None:
        if a != b:
          reasons.append(case + ':' + key + ':AVAILABILITY_CHANGED')
        continue
      if not finite_number(a) or not finite_number(b):
        reasons.append(case + ':' + key + ':INVALID_METRIC')
        continue
      delta = b - a if key in policy['lower_is_better'] else a - b
      if delta > policy['absolute_numeric_allowance']:
        reasons.append(case + ':' + key + ':REGRESSION')
      if key in policy['primary_metrics'] and a > 0:
        improvements.append((a - b) / a)
  if not improvements or max(improvements) < policy['minimum_primary_improvement_fraction']:
    reasons.append('NO_REQUIRED_PRIMARY_IMPROVEMENT')
  return {'status': 'REJECTED' if reasons else 'PASS_SYNTHETIC_ONLY', 'reasons': sorted(set(reasons)),
          'vehicle_activation_allowed': False}


def evaluate(arms: dict) -> dict:
  """Frozen prospective metric policy; malformed/missing evidence fails closed."""
  failure = {'status': 'BLOCKED', 'reason': 'INVALID_OR_NONREPEATABLE_EVIDENCE', 'vehicle_activation_allowed': False}
  try:
    policy = frozen_policy()
    if type(arms) is not dict or set(arms) != set(ARMS):
      return failure
    binding = arms['baseline'][0]['binding']
    if binding['catalog_sha256'] != policy['catalog_sha256'] or binding['policy_sha256'] != POLICY_SHA256:
      return failure
    for name, tune in ARMS.items():
      if type(arms[name]) is not list or len(arms[name]) != policy['required_repetitions_per_arm']:
        return failure
      for arm in arms[name]:
        validate_arm(arm, tune, binding)
      if arms[name][0] != arms[name][1]:
        return failure
    if arms['baseline'][0] != arms['current'][0]:
      return {**failure, 'reason': 'BASELINE_CURRENT_NONINTERFERENCE_FAILED'}
    verdicts = {name: _compare(arms['baseline'][0], arms[name][0], policy) for name in ('gentle', 'firm')}
    return {'schema': 'synthetic-comparison-v2', 'status': 'COMPLETED_SYNTHETIC_ONLY',
            'baseline_current_strict_aa': 'PASS', 'deterministic_repeats': 'PASS', 'variant_count_per_arm': 50,
            'comparisons': verdicts, 'policy_sha256': POLICY_SHA256, 'binding': binding,
            'evidence_sha256': digest(canonical(arms)), 'vehicle_activation_allowed': False,
            'vehicle_status': 'REAL_VEHICLE_UNVERIFIED', 'readiness': 'NOT_READY',
            'scope': 'SAME_SOURCE_NATIVE_CORE_IDENTITY_ARMS_NOT_FULL_PLANNER_AB'}
  except (ValueError, TypeError, KeyError, IndexError, UnicodeError, RecursionError):
    return failure


def main():
  arms = {name: [run_arm(tune) for _ in range(2)] for name, tune in ARMS.items()}
  report = {'evaluation': evaluate(arms), 'arms': arms}
  print(canonical(report).decode())
  return 0 if report['evaluation']['status'] == 'COMPLETED_SYNTHETIC_ONLY' else 1


if __name__ == '__main__':
  raise SystemExit(main())
