"""Source-bound numeric readers. Never decode images or dereference model/GPS payloads."""

from bisect import bisect_right
from collections import Counter, defaultdict
import math
from pathlib import Path
import subprocess

import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p

RECORDED_COMMIT = '5a970f1ad25d9f07d055955d7a7c14603b6b7813'
SOURCE_FILES = [
  'openpilot/cereal/log.capnp',
  'openpilot/cereal/custom.capnp',
  'openpilot/cereal/deprecated.capnp',
  'opendbc_repo/opendbc/car/car.capnp',
  'opendbc_repo/opendbc/car/hyundai/carstate.py',
  'opendbc_repo/opendbc/car/hyundai/carcontroller.py',
  'opendbc_repo/opendbc/car/hyundai/values.py',
  'opendbc_repo/opendbc/dbc/hyundai_kia_generic.dbc',
  'openpilot/selfdrive/car/card.py',
  'openpilot/cereal/services.py',
]


def source_contract(root):
  root = Path(root)
  prefix = ['git', '-c', f'safe.directory={root}', '-C', str(root)]
  if subprocess.check_output([*prefix, 'rev-parse', 'HEAD']).decode().strip() != RECORDED_COMMIT:
    raise ValueError('RECORDED_SOURCE_COMMIT_MISMATCH')
  blobs = {}
  for name in SOURCE_FILES:
    committed = subprocess.check_output([*prefix, 'show', f'{RECORDED_COMMIT}:{name}'])
    if (root / name).read_bytes() != committed:
      raise ValueError('RECORDED_SIGNAL_SOURCE_DRIFT')
    blobs[name] = p.sha(committed)
  return p.seal(
    {
      'schema': 'EMPIRICAL_SIGNAL_SOURCE_BINDING_V1',
      'commit': RECORDED_COMMIT,
      'blobs': blobs,
      'repository': 'https://github.com/ajouatom/openpilot',
      'command_provenance': 'POST_CARCONTROLLER_RATE_LIMIT_LOGGED_NOT_EPS_ACK',
      'yaw': yaw_provenance(''),
      'steering': 'SAS11.SAS_Angle_DBC_Deg',
      'physical_measurement_clock': 'CAN_ACQUISITION_TO_PUBLISH_AGE_UNVERIFIED',
    }
  )


def schema(root):
  import capnp

  root = Path(root)
  source_contract(root)
  return capnp.load(str(root / 'openpilot/cereal/log.capnp'), imports=[str(root / 'openpilot/cereal'), str(root / 'opendbc_repo/opendbc/car')])


def events(path, capnp_schema):
  import zstandard as zstd

  path = Path(path)
  if path.name != 'rlog.zst' or any(x.is_symlink() for x in (path, *path.parents)):
    raise ValueError('ONLY_EXACT_NUMERIC_LOG_SOURCE')
  # Lossless decompression parses event envelopes only; no image codec is invoked.
  with zstd.ZstdDecompressor().stream_reader(path.open('rb')) as reader:
    data = reader.read()
  yield from capnp_schema.Event.read_multiple_bytes(data)


def metadata(iterator):
  counts, times = Counter(), defaultdict(list)
  initial, profiles = [], []
  for event in iterator:
    kind = event.which()
    counts[kind] += 1
    if kind in ('carState', 'carOutput', 'carControl'):
      times[kind].append(int(event.logMonoTime))
    if kind == 'initData':
      x = event.initData
      initial.append({'commit': x.gitCommit, 'os_version': x.osVersion, 'dirty': bool(x.dirty), 'branch_sha256': p.sha(x.gitBranch.encode())})
    elif kind == 'carParams':
      x = event.carParams
      identity = {
        'fingerprint': x.carFingerprint,
        'brand': x.brand,
        'flags': int(x.flags),
        'steer_control_type': str(x.steerControlType),
        'steer_ratio': float(x.steerRatio),
        'wheelbase': float(x.wheelbase),
        'steer_actuator_delay': float(x.steerActuatorDelay),
        'lateral_tuning_type': x.lateralTuning.which(),
        'full_carparams_sha256': p.sha(x.as_builder().to_bytes()),
      }
      if x.lateralTuning.which() == 'torque':
        t = x.lateralTuning.torque
        identity['torque'] = {'latAccelFactor': float(t.latAccelFactor), 'latAccelOffset': float(t.latAccelOffset), 'friction': float(t.friction)}
      profiles.append(identity)
  rates = {}
  for kind, t in times.items():
    differences = np.diff(np.asarray(t, dtype=np.int64))
    rates[kind] = {
      'count': len(t),
      'nonincreasing': int(np.sum(differences <= 0)),
      'median_period_ns': float(np.median(differences)) if len(differences) else None,
      'maximum_gap_ns': int(max(differences)) if len(differences) else None,
      'span_s': (t[-1] - t[0]) * 1e-9 if len(t) > 1 else 0.0,
    }
  return {'message_counts': dict(counts), 'init': initial, 'profiles': profiles, 'rates': rates}


def numeric(iterator):
  streams = {'state': [], 'command': [], 'control': []}
  for event in iterator:
    kind = event.which()
    if kind not in ('carState', 'carOutput', 'carControl'):
      continue
    base = {'time_ns': int(event.logMonoTime), 'valid': bool(event.valid)}
    if kind == 'carState':
      x = event.carState
      streams['state'].append(
        {
          **base,
          'speed_mps': float(x.vEgo),
          'angle_deg': float(x.steeringAngleDeg),
          'driver_pressed': bool(x.steeringPressed),
          'driver_torque': float(x.steeringTorque),
          'eps_fault': bool(x.steerFaultTemporary or x.steerFaultPermanent),
          'gear': str(x.gearShifter),
          'yaw_raw': float(x.yawRate),
        }
      )
    elif kind == 'carOutput':
      streams['command'].append({**base, 'command_raw': float(event.carOutput.actuatorsOutput.torqueOutputCan)})
    else:
      streams['control'].append({**base, 'lat_active': bool(event.carControl.latActive)})
  return streams


def yaw_provenance(dbc_unit):
  if dbc_unit == '':
    return {
      'status': 'BLOCKED_UNIT_UNVERIFIED',
      'physical_unit': None,
      'frame': 'UNVERIFIED',
      'reason': 'SOURCE_COPIES_ESP12_YAW_RATE_DBC_UNIT_EMPTY_NO_RADIANS_CONVERSION',
    }
  raise ValueError('NO_NEW_YAW_UNIT_ASSUMPTION_AUTHORIZED')


def validate_units(command_units, steering_units):
  expected = p.policy()
  if command_units != expected['command_units'] or steering_units != expected['steering_units']:
    raise ValueError('EXACT_SOURCE_UNITS_REQUIRED_NO_IMPLICIT_384_OR_DEG_RAD_CONVERSION')


def speed_bin(speed):
  for name, lower, upper in p.policy()['speed_bins']:
    if lower <= speed and (upper is None or speed < upper):
      return name
  return None


def align(streams):
  if set(streams) != {'state', 'command', 'control'}:
    raise ValueError('EXACT_SIGNAL_STREAM_WHITELIST')
  fields = {
    'state': {'time_ns', 'valid', 'speed_mps', 'angle_deg', 'driver_pressed', 'driver_torque', 'eps_fault', 'gear', 'yaw_raw'},
    'command': {'time_ns', 'valid', 'command_raw'},
    'control': {'time_ns', 'valid', 'lat_active'},
  }
  times = {}
  for kind, rows in streams.items():
    if any(set(row) != fields[kind] for row in rows):
      raise ValueError('EXACT_SIGNAL_FIELD_WHITELIST')
    t = [row['time_ns'] for row in rows]
    if any(type(v) is not int for v in t) or any(b <= a for a, b in zip(t, t[1:], strict=False)):
      raise ValueError('UNIQUE_INCREASING_EVENT_TIME_REQUIRED')
    times[kind] = t
  if not streams['state']:
    return {'rows': [], 'reasons': {'NO_MEASURED_STEERING': 1}}
  policy = p.policy()
  dt, age = policy['dt_ns'], policy['max_age_ns']
  first, last = times['state'][0], times['state'][-1]
  output, counts, previous_target = [], Counter(), None
  for grid in range(((first + dt - 1) // dt) * dt, last + 1, dt):
    target = bisect_right(times['state'], grid) - 1
    if target < 0:
      continue
    state = streams['state'][target]
    target_time = state['time_ns']
    selected = {'state': state}
    reasons = []
    for kind in ('command', 'control'):
      index = bisect_right(times[kind], target_time) - 1
      selected[kind] = None if index < 0 else streams[kind][index]
      if index < 0 or target_time - times[kind][index] > age:
        reasons.append('MISSING_OR_GAP')
    if grid - target_time > age:
      reasons.append('MISSING_OR_GAP')
    if target_time == previous_target:
      reasons.append('REPEATED_OUTPUT_EVENT')
    for kind, row in selected.items():
      if row is None:
        continue
      idx = bisect_right(times[kind], row['time_ns']) - 1
      if idx > 0 and times[kind][idx] - times[kind][idx - 1] > age:
        reasons.append('SOURCE_EVENT_GAP')
    previous_target = target_time
    command, control = selected['command'], selected['control']
    u = None if command is None else command['command_raw']
    if any(not math.isfinite(state[k]) for k in ('speed_mps', 'angle_deg', 'driver_torque')) or (u is not None and not math.isfinite(u)):
      reasons.append('NONFINITE')
    if not state['valid'] or (command and not command['valid']) or (control and not control['valid']):
      reasons.append('INVALID_MESSAGE')
    if control and not control['lat_active']:
      reasons.append('INACTIVE')
    if state['driver_pressed']:
      reasons.append('DRIVER_OVERRIDE')
    if state['eps_fault']:
      reasons.append('EPS_FAULT')
    if state['gear'] != 'drive':
      reasons.append('NON_FORWARD_GEAR')
    if state['speed_mps'] < policy['minimum_speed_mps']:
      reasons.append('LOW_SPEED')
    if u is not None and not -1024 <= u <= 1023:
      reasons.append('RAW_CAN_DOMAIN')
    reasons = sorted(set(reasons))
    counts.update(reasons)

    def finite(value):
      return value if value is not None and math.isfinite(value) else None

    output.append(
      {
        'grid_time_ns': grid,
        'state_time_ns': target_time,
        'command_time_ns': None if command is None else command['time_ns'],
        'control_time_ns': None if control is None else control['time_ns'],
        'command_raw': finite(u),
        'angle_deg': finite(state['angle_deg']),
        'speed_mps': finite(state['speed_mps']),
        'driver_torque': finite(state['driver_torque']),
        'speed_bin': speed_bin(state['speed_mps']),
        'reasons': reasons,
        'diagnostic_valid': not reasons,
        'clean_primary_valid': False,
        'safety_limited': None,
        'curvature_limited': None,
      }
    )
  return {
    'rows': output,
    'reasons': dict(counts),
    'limit_observation': 'UNAVAILABLE_NOT_FALSE',
    'measurement_clock': 'PUBLISH_EVENT_ONLY',
    'yaw_stage': 'BLOCKED_UNIT_UNVERIFIED',
  }


def validate_generation(segment, metadata_receipt, source):
  """Mandatory extraction entry gate; never derive identity from numeric quality."""
  p.verify(metadata_receipt)
  p.verify(source)
  if metadata_receipt.get('schema') != 'EMPIRICAL_SEGMENT_METADATA_V1' or source.get('schema') != 'EMPIRICAL_SIGNAL_SOURCE_BINDING_V1':
    raise ValueError('EXACT_METADATA_SOURCE_BINDING_REQUIRED')
  if segment.get('source_sha256') != metadata_receipt.get('source_sha256'):
    raise ValueError('INVENTORY_SOURCE_MISMATCH')
  meta = metadata_receipt['metadata']
  if not meta['init'] or any(x['commit'] != RECORDED_COMMIT or x['dirty'] for x in meta['init']):
    raise ValueError('RECORDED_SOFTWARE_UNBOUND_OR_DIRTY')
  profiles = meta['profiles']
  if not profiles or len({x['full_carparams_sha256'] for x in profiles}) != 1:
    raise ValueError('HOMOGENEOUS_CARPARAMS_REQUIRED')
  for x in profiles:
    if x['brand'] != 'hyundai' or x['fingerprint'] != 'HYUNDAI_SANTA_FE_2022' or x['steer_control_type'] != 'torque' or x['flags'] & ((1 << 24) | (1 << 13)):
      raise ValueError('RAW_TORQUE_LEGACY_SAS11_SOURCE_NOT_APPLICABLE')
  if source['commit'] != RECORDED_COMMIT:
    raise ValueError('SOURCE_COMMIT_MISMATCH')
  return profiles[0]['full_carparams_sha256']


def extract(path, segment, metadata_receipt, source, capnp_schema):
  generation = validate_generation(segment, metadata_receipt, source)
  if p.sha(Path(path).read_bytes()) != segment['source_sha256']:
    raise ValueError('SOURCE_CHANGED')
  return p.seal(
    {
      'schema': 'EMPIRICAL_ALIGNED_SEGMENT_V1',
      'segment_id': segment['segment_id'],
      'role': segment['role'],
      'source_sha256': segment['source_sha256'],
      'generation_sha256': generation,
      'source_binding_sha256': source['receipt_sha256'],
      'metadata_sha256': metadata_receipt['receipt_sha256'],
      'alignment_policy_sha256': p.alignment_policy()['receipt_sha256'],
      'data_policy_sha256': p.policy()['receipt_sha256'],
      'aligned': align(numeric(events(path, capnp_schema))),
    }
  )
