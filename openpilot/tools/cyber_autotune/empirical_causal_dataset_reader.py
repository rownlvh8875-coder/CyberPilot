"""Recorded-source field whitelist. Forbidden event bodies are never dereferenced."""
import math
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_causal_dataset_policy as policy
from openpilot.tools.cyber_autotune import empirical_source_metadata as metadata


def field(value, name, convert=float):
  if name not in value.schema.fields:
    return None
  return convert(getattr(value, name))


def numeric(events):
  result = {'state': [], 'command': [], 'control': [], 'gyro': [], 'settings': [], 'init': [], 'profiles': [], 'gyro_rejected': 0}
  for event in events:
    kind = event.which()
    if kind not in policy.WHITELIST:
      continue
    if kind == 'initData':
      x = event.initData
      result['init'].append({'commit': str(x.gitCommit), 'remote': str(x.gitRemote),
                             'dirty': bool(x.dirty), 'os_version': str(x.osVersion),
                             'branch_sha256': p.sha(str(x.gitBranch).encode()), 'version_sha256': p.sha(str(x.version).encode()),
                             'logger_start_sha256': p.sha(p.canonical({'init_envelope_ns': int(event.logMonoTime),
                               'wall_ns': int(x.wallTimeNanos), 'boot_sha256': p.sha(str(x.bootlogId).encode()),
                               'device_sha256': p.sha(str(x.dongleId).encode())}))})
      settings = {}
      for entry in x.params.entries:
        if str(entry.key) in policy.SETTINGS:
          value = bytes(entry.value).decode('ascii')
          if not value.lstrip('-').isdigit():
            raise ValueError('ALLOWLISTED_SETTING_INTEGER_REQUIRED')
          settings[str(entry.key)] = int(value)
      result['settings'].append(settings)
      continue
    if kind == 'carParams':
      x = event.carParams
      fields = {}
      for name in metadata.PROFILE_FIELDS:
        if name not in x.schema.fields:
          fields[name] = None
          continue
        value = getattr(x, name)
        if hasattr(value, 'to_dict'):
          value = value.to_dict()
        elif name == 'safetyConfigs':
          value = [v.to_dict() for v in value]
        elif not isinstance(value, (str, int, float, bool)):
          value = str(value)
        fields[name] = value
      result['profiles'].append({'fields': fields, 'full_carparams_sha256': p.sha(x.as_builder().to_bytes()),
                                 'empirical_profile_sha256': p.sha(p.canonical(fields))})
      continue
    base = {'time_ns': int(event.logMonoTime), 'valid': bool(event.valid)}
    if kind == 'carState':
      x = event.carState
      row = {**base, 'speed_mps': field(x, 'vEgo'), 'angle_deg': field(x, 'steeringAngleDeg'),
             'rate': field(x, 'steeringRateDeg'), 'driver_pressed': field(x, 'steeringPressed', bool),
             'driver_torque': field(x, 'steeringTorque'), 'torque_eps': field(x, 'steeringTorqueEps'),
             'fault_temporary': field(x, 'steerFaultTemporary', bool),
             'fault_permanent': field(x, 'steerFaultPermanent', bool),
             'gear': field(x, 'gearShifter', str), 'yaw_raw': field(x, 'yawRate')}
      row['eps_fault'] = None if row['fault_temporary'] is None or row['fault_permanent'] is None else row['fault_temporary'] or row['fault_permanent']
      wheel = x.wheelSpeeds if 'wheelSpeeds' in x.schema.fields else None
      row.update({'wheel_'+name: field(wheel, name) if wheel is not None else None for name in ('fl', 'fr', 'rl', 'rr')})
      result['state'].append(row)
    elif kind == 'carControl':
      x = event.carControl
      result['control'].append({**base, 'requested': field(x.actuators, 'torque'),
                                'lat_active': field(x, 'latActive', bool), 'desired_curvature': None})
    elif kind == 'carOutput':
      x = event.carOutput.actuatorsOutput
      result['command'].append({**base, 'raw': field(x, 'torqueOutputCan'), 'normalized': field(x, 'torque')})
    elif kind == 'gyroscope':
      x = event.gyroscope
      if str(x.source) not in ('lsm6ds3', 'lsm6ds3trc') or x.which() != 'gyroUncalibrated' or len(x.gyroUncalibrated.v) != 3:
        result['gyro_rejected'] += 1
        continue
      result['gyro'].append({**base, 'sensor_ns': int(x.timestamp), 'source': str(x.source),
                             'xyz': [float(v) for v in x.gyroUncalibrated.v]})
  return result


def configuration(streams, route):
  if not streams['init'] or not streams['profiles'] or not streams['settings']:
    raise ValueError('MISSING_CONFIG_METADATA')
  if any(len({p.sha(p.canonical(x)) for x in streams[key]}) != 1 for key in ('init', 'profiles', 'settings')):
    raise ValueError('SEGMENT_CONFIG_DRIFT')
  init, profile, settings = streams['init'][0], streams['profiles'][0], streams['settings'][0]
  if init['commit'] != route['source_commit'] or init['dirty'] or init['remote'].rstrip('/').removesuffix('.git') not in (
      'https://github.com/ajouatom/openpilot', 'git@github.com:ajouatom/openpilot'):
    raise ValueError('RECORDED_SOURCE_OR_DIRTY_CONFLICT')
  if any(profile[k] != route[k] for k in ('full_carparams_sha256', 'empirical_profile_sha256')):
    raise ValueError('FULL_CARPARAMS_OR_PROFILE_DRIFT')
  fields = profile['fields']
  if fields['steerControlType'] != 'torque' or fields['flags'] & ((1 << 24) | (1 << 13)):
    raise ValueError('SOURCE_BOUND_LEGACY_TORQUE_ONLY')
  # Runtime evidence must explicitly attest 409; never substitute a historical constant.
  if settings.get('CustomSteerMax') not in (0, 409) or fields['flags'] & (1 << 4):
    raise ValueError('RUNTIME_STEER_MAX_409_METADATA_REQUIRED')
  return p.seal({'schema': 'EMPIRICAL_CAUSAL_CONFIG_SNAPSHOT_V1', **init, **profile,
                 'settings': settings, 'runtime_steer_max': 409,
                 'runtime_setting_provenance': 'ALLOWLISTED_INITDATA_CUSTOM_STEER_MAX_OR_EXACT_SOURCE_DEFAULT',
                 'buses': 'SOURCE_BOUND_LEGACY_PT_0_CAM_2_RUNTIME_BUS_METADATA_UNAVAILABLE'})


def bridge(rows, maximum):
  if maximum != 409:
    raise ValueError('EXACT_SOURCE_RUNTIME_STEER_MAX_REQUIRED')
  selected = [r for r in rows if r['valid'] and r['raw'] is not None and r['normalized'] is not None
              and math.isfinite(r['raw']) and math.isfinite(r['normalized'])]
  raw = np.array([r['raw'] for r in selected], dtype='<f8')
  norm = np.array([r['normalized'] for r in selected], dtype='<f8')
  expected = raw / maximum
  residual = np.abs(norm - expected)
  count = len(raw)
  exact = int(np.sum(norm == expected.astype(np.float32).astype(np.float64)))
  domain = int(np.sum((abs(raw)>maximum) | (abs(norm)>1) | (raw != np.rint(raw))))
  signs = int(np.sum(np.sign(raw) != np.sign(norm)))
  return {'status': 'ROUTE_COMMAND_BRIDGE_CONFIRMED' if count and exact == count and not domain and not signs else 'ROUTE_COMMAND_BRIDGE_CONFLICT',
          'total': len(rows), 'eligible': count, 'invalid': len(rows)-count, 'steer_max': maximum,
          'float32_expected_exact_count': exact, 'float32_exact_rate': exact/count if count else None,
          'exact_ratio_match_count': int(np.sum(norm == expected)),
          'median_residual': float(np.median(residual)) if count else None,
          'p95_residual': float(np.percentile(residual, 95)) if count else None,
          'max_residual': float(np.max(residual)) if count else None,
          'sign_conflicts': signs, 'domain_conflicts': domain,
          'raw_saturated_count': int(np.sum(abs(raw) == maximum)),
          'normalized_saturated_count': int(np.sum(abs(norm) == 1)),
          'physical_eps_application_proven': False}
