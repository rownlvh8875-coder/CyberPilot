"""Detached offline H1 records and immutable synthetic packages; no controller imports."""

import json
import math
from pathlib import Path
import re

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_lateral_h1_contract as c

FILENAME = 'cyber-lateral-h1-trace-v1.json'


def keys(row, names):
  if type(row) is not dict or set(row) != set(names):
    raise ValueError('H1_EXACT_SCHEMA')


def digest(value):
  if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
    raise ValueError('H1_SHA256')
  return value


def integer(value, minimum=0):
  if type(value) is not int or not minimum <= value < 2**63:
    raise ValueError('H1_INTEGER_CLOCK_SEQUENCE')
  return value


def clone(value):
  return json.loads(p.canonical(value))


def row_sha(row):
  return p.sha(p.canonical({k: v for k, v in row.items() if k != 'row_sha256'}))


def make_row(binding, config, index, native, torque, applied, plant, reset_events):
  native = clone(native)
  clock = index * c.DT_NS
  health = c.service_health()
  snapshot = {'native_input': native, 'source_time_ns': clock, 'service_health': health}
  signals = dict.fromkeys(c.PROVENANCE)
  signals.update({key: native[value] for key, value in c.INPUT_MAP.items()})
  signals.update(dict.fromkeys(c.TORQUES, torque))
  signals['applied_torque'] = applied
  signals['saturation_state'] = abs(torque) == 1.0
  events = [event for event in reset_events if event != 'EXPERIMENT_START']
  event = 'SCENARIO_BOUNDARY' if index == 0 else (events[0] if events else 'ORDINARY')
  row = {
    'schema': 'CYBER_LATERAL_H1_TRACE_V1',
    'sample_index': index,
    'process_epoch': config['process_epoch'],
    'loop_sequence': index + 1,
    'config_sequence': config['config_sequence'],
    'config_sha256': config['config_sha256'],
    'source_sha256': binding['source_sha256'],
    'experiment_sha256': binding['experiment_sha256'],
    'capture_time_ns': clock,
    'decision_time_ns': clock + c.DECISION_TICK_NS,
    'completion_time_ns': clock + c.DT_NS,
    'dt_ns': c.DT_NS,
    'consumed_input_snapshot': snapshot,
    'consumed_input_snapshot_sha256': p.sha(p.canonical(snapshot)),
    'native_input_sha256': p.sha(p.canonical(native)),
    'signals': signals,
    'provenance': dict(c.PROVENANCE),
    'unavailable': dict(c.UNAVAILABLE),
    'service_health': health,
    'plant_output': {'state_time_ns': clock + c.DT_NS, **{key: plant[key] for key in ('curvature', 'yaw_rate', 'heading', 'pose_x', 'pose_y')}},
    'event': event,
    'reset_events': list(reset_events),
  }
  row['row_sha256'] = row_sha(row)
  return row


def validate_row(row, binding, config):
  keys(row, c.ROW_FIELDS)
  for key in ('source_sha256', 'experiment_sha256', 'config_sha256', 'row_sha256', 'native_input_sha256', 'consumed_input_snapshot_sha256'):
    digest(row[key])
  if (
    row['schema'] != 'CYBER_LATERAL_H1_TRACE_V1' or row['source_sha256'] != binding['source_sha256'] or row['experiment_sha256'] != binding['experiment_sha256']
  ):
    raise ValueError('H1_SOURCE_EXPERIMENT_DRIFT')
  if config is None or row['config_sha256'] != config['config_sha256']:
    raise ValueError('H1_CONFIG_DRIFT')
  index = integer(row['sample_index'])
  for key in ('process_epoch', 'loop_sequence', 'config_sequence'):
    integer(row[key], 1)
  capture, decision, completion = (integer(row[key]) for key in ('capture_time_ns', 'decision_time_ns', 'completion_time_ns'))
  if (
    type(row['dt_ns']) is not int
    or row['dt_ns'] != c.DT_NS
    or capture != index * c.DT_NS
    or not capture < decision < completion
    or decision != capture + c.DECISION_TICK_NS
    or completion != capture + c.DT_NS
  ):
    raise ValueError('H1_CAUSAL_CLOCK_DRIFT')
  snapshot = row['consumed_input_snapshot']
  keys(snapshot, ('native_input', 'source_time_ns', 'service_health'))
  native = snapshot['native_input']
  keys(native, c.INPUTS)
  if type(snapshot['source_time_ns']) is not int or snapshot['source_time_ns'] != capture:
    raise ValueError('H1_FUTURE_INPUT')
  if snapshot['service_health'] != c.service_health() or row['service_health'] != c.service_health() or snapshot['service_health'] != row['service_health']:
    raise ValueError('H1_NO_FABRICATED_SERVICE_HEALTH')
  for key, value in native.items():
    if key in ('active', 'steering_pressed', 'safety_limited', 'curvature_limited'):
      if type(value) is not bool:
        raise ValueError('H1_EXACT_BOOLEAN')
    elif type(value) not in (int, float) or not math.isfinite(value):
      raise ValueError('H1_FINITE_INPUT')
  if native['time_s'] != index * 0.01 or native['dt_s'] != 0.01 or native['speed_mps'] < 0:
    raise ValueError('H1_NATIVE_TIMEBASE')
  if p.sha(p.canonical(snapshot)) != row['consumed_input_snapshot_sha256'] or p.sha(p.canonical(native)) != row['native_input_sha256']:
    raise ValueError('H1_CONSUMED_INPUT_DRIFT')
  keys(row['signals'], c.PROVENANCE)
  if row['provenance'] != c.PROVENANCE or row['unavailable'] != c.UNAVAILABLE:
    raise ValueError('H1_PROVENANCE_DRIFT')
  signals = row['signals']
  for key, value in signals.items():
    if key in c.UNAVAILABLE:
      if value is not None:
        raise ValueError('H1_UNAVAILABLE_MUST_BE_NULL')
    elif key in c.BOOLS:
      if type(value) is not bool:
        raise ValueError('H1_EXACT_BOOLEAN')
    elif type(value) not in (int, float) or not math.isfinite(value):
      raise ValueError('H1_FINITE_SIGNAL')
  if any(signals[key] != native[value] for key, value in c.INPUT_MAP.items()):
    raise ValueError('H1_CONSUMED_SIGNAL_MISMATCH')
  if (
    any(abs(signals[key]) > 1.0 for key in c.TORQUES)
    or len({signals[key] for key in c.TORQUES if key != 'applied_torque'}) != 1
    or signals['saturation_state'] != (abs(signals['final_requested_torque']) == 1.0)
  ):
    raise ValueError('H1_BASELINE_STAGE_IDENTITY')
  keys(row['plant_output'], ('state_time_ns', 'curvature', 'yaw_rate', 'heading', 'pose_x', 'pose_y'))
  if type(row['plant_output']['state_time_ns']) is not int or row['plant_output']['state_time_ns'] != completion:
    raise ValueError('H1_POST_STEP_TIMING')
  if any(type(v) not in (int, float) or not math.isfinite(v) for k, v in row['plant_output'].items() if k != 'state_time_ns'):
    raise ValueError('H1_FINITE_PLANT_OUTPUT')
  if (
    row['event'] not in c.EVENTS
    or type(row['reset_events']) is not list
    or len(set(row['reset_events'])) != len(row['reset_events'])
    or any(event not in (*c.EVENTS, 'EXPERIMENT_START') or event in ('ORDINARY', 'CONFIG_CHANGE', 'SCENARIO_BOUNDARY') for event in row['reset_events'])
  ):
    raise ValueError('H1_EVENT_SCHEMA')
  if row_sha(row) != row['row_sha256']:
    raise ValueError('H1_ROW_DIGEST')


class Producer:
  """Observer owns copies only; no core/plant handle, callback or return command."""

  def __init__(self, policy, binding, configs):
    if policy != c.policy():
      raise ValueError('H1_POLICY_OR_SOURCE_DRIFT')
    keys(binding, ('experiment_sha256', 'source_sha256', 'expected_rows', 'data_class', 'tier', 'dt_ns'))
    digest(binding['experiment_sha256'])
    digest(binding['source_sha256'])
    integer(binding['expected_rows'], 1)
    if (
      binding['source_sha256'] != policy['source_sha256']
      or binding['expected_rows'] > policy['samples']
      or binding['tier'] != c.TIER
      or binding['data_class'] != 'SYNTHETIC_ONLY'
      or type(binding['dt_ns']) is not int
      or binding['dt_ns'] != c.DT_NS
    ):
      raise ValueError('H1_SYNTHETIC_BASELINE_ONLY')
    if type(configs) is not list or not configs:
      raise ValueError('H1_CONFIG_LIST')
    self._configs = {}
    for config in configs:
      keys(config, ('process_epoch', 'config_sequence', 'config', 'config_sha256'))
      identity = integer(config['process_epoch'], 1), integer(config['config_sequence'], 1)
      if type(config['config']) is not dict or digest(config['config_sha256']) != p.sha(p.canonical(config['config'])) or identity in self._configs:
        raise ValueError('H1_CONFIG_DIGEST_COLLISION')
      self._configs[identity] = clone(config)
    self._policy, self._binding, self._config_list = clone(policy), clone(binding), clone(configs)
    self._rows = []
    self._epochs = set()
    self._closed = False

  def append(self, row):
    if self._closed:
      raise ValueError('H1_PRODUCER_CLOSED')
    row = clone(row)
    config = self._configs.get((row.get('process_epoch'), row.get('config_sequence')))
    validate_row(row, self._binding, config)
    if row['sample_index'] != len(self._rows) or len(self._rows) >= self._binding['expected_rows']:
      raise ValueError('H1_MISSING_OR_DUPLICATE_SAMPLE')
    previous = self._rows[-1] if self._rows else None
    if previous is None or previous['process_epoch'] != row['process_epoch']:
      if row['process_epoch'] in self._epochs or row['loop_sequence'] != 1 or row['config_sequence'] != 1 or row['event'] != 'SCENARIO_BOUNDARY':
        raise ValueError('H1_EPOCH_RESTART_BOUNDARY')
      self._epochs.add(row['process_epoch'])
    else:
      if (
        row['loop_sequence'] != previous['loop_sequence'] + 1
        or row['capture_time_ns'] < previous['decision_time_ns']
        or row['decision_time_ns'] <= previous['decision_time_ns']
      ):
        raise ValueError('H1_CROSS_LOOP_ORDER')
      changed = row['config_sequence'] != previous['config_sequence']
      if (
        changed
        and (row['config_sequence'] != previous['config_sequence'] + 1 or row['event'] != 'CONFIG_CHANGE')
        or not changed
        and row['event'] == 'CONFIG_CHANGE'
      ):
        raise ValueError('H1_CONFIG_SEQUENCE')
    old_native = None if previous is None or previous['process_epoch'] != row['process_epoch'] else previous['consumed_input_snapshot']['native_input']
    native = row['consumed_input_snapshot']['native_input']
    events = ['EXPERIMENT_START'] if old_native is None else []
    if not native['active'] and (old_native is None or old_native['active']):
      events.append('INACTIVE')
    if native['steering_pressed'] and (old_native is None or not old_native['steering_pressed']):
      events.append('STEERING_PRESSED')
    if old_native is not None and old_native['steering_pressed'] and not native['steering_pressed']:
      events.append('RELEASE')
    if old_native is not None and not old_native['active'] and native['active']:
      events.append('REENGAGEMENT')
    boundary = old_native is None
    config_change = previous is not None and not boundary and row['config_sequence'] != previous['config_sequence']
    expected_event = 'SCENARIO_BOUNDARY' if boundary else ('CONFIG_CHANGE' if config_change else (events[0] if events else 'ORDINARY'))
    if row['reset_events'] != events or row['event'] != expected_event:
      raise ValueError('H1_EXACT_INTERVENTION_TRANSITION')
    self._rows.append(row)

  def finish(self):
    if len(self._rows) != self._binding['expected_rows']:
      raise ValueError('H1_INCOMPLETE_TRACE')
    if self._policy != c.policy():
      raise ValueError('H1_POLICY_OR_SOURCE_DRIFT')
    self._closed = True
    return p.seal(
      {
        'schema': 'CYBER_LATERAL_H1_PACKAGE_V1',
        'policy': self._policy,
        'binding': self._binding,
        'configs': self._config_list,
        'rows': clone(self._rows),
        'row_count': len(self._rows),
        'trace_sha256': p.sha(p.canonical(self._rows)),
        'policy_sha256': self._policy['receipt_sha256'],
        'producer_sha256': self._policy['producer_sha256'],
        'calibration_blockers': p.BLOCKERS,
        'production_observer_implemented': False,
        'holdout_opening': 'CLOSED',
        'opening_count': 0,
        'holdout_opener_implemented': False,
      }
    )


def verify_package(package):
  p.verify(package)
  producer = Producer(package['policy'], package['binding'], package['configs'])
  for row in package['rows']:
    producer.append(row)
  if producer.finish() != package:
    raise ValueError('H1_PACKAGE_INTEGRITY')
  return package


def store_path(store):
  path = Path(store)
  if not path.is_absolute() or any(part.is_symlink() for part in (path, *path.parents)):
    raise ValueError('H1_ABSOLUTE_NON_SYMLINK_STORE')
  path = path.resolve()
  root = Path(__file__).resolve().parents[3]
  if path.is_relative_to(root) or any(path.is_relative_to(Path(x)) for x in ('/mnt/d/carrotlog', '/mnt/d/CarrotLogs')):
    raise ValueError('H1_STORE_OUTSIDE_REPOSITORY_AND_RAW_ROOTS')
  target = path / FILENAME
  if target.is_symlink():
    raise ValueError('H1_TRACE_TARGET_SYMLINK')
  return target


def persist(store, package):
  verify_package(package)
  path = store_path(store)
  expected = json.dumps(package, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n'
  if path.exists() and path.read_bytes() != expected:
    raise ValueError('H1_IMMUTABLE_BYTES_CONFLICT')
  p.persist(path, package)
  if path.read_bytes() != expected:
    raise ValueError('H1_PERSISTENCE_BYTES_DRIFT')
