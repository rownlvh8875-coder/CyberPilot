"""Private, repeatable signal provenance completion. No controller or plant execution."""

import argparse
from bisect import bisect_right
from collections import Counter
import json
from pathlib import Path

import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_plant_signals as s
from openpilot.tools.cyber_autotune import empirical_plant_model as m
from openpilot.tools.cyber_autotune import empirical_plant_run as oldrun
from openpilot.tools.cyber_autotune import empirical_plant_publication as oldpub
from openpilot.tools.cyber_autotune import empirical_signal_policy as q
from openpilot.tools.cyber_autotune import empirical_signal_reader as r
from openpilot.tools.cyber_autotune import empirical_signal_crosscheck as c

SOURCE_RECEIPT = 'bf903fa6f10ceaa0fd4529436f151f110580dd98ac8b43610886f0289a487f08'


def read(path):
  path = Path(path)
  if any(x.is_symlink() for x in (path, *path.parents)):
    raise ValueError('NO_RECEIPT_PATH_ALIAS')
  return p.verify(json.loads(path.read_bytes()))


def source_gate(source):
  p.verify(source)
  if source['receipt_sha256'] != SOURCE_RECEIPT:
    raise ValueError('EXACT_RECORDED_SOURCE_AND_FACTS_REQUIRED')


def store_gate(base, prior):
  base, prior = Path(base), Path(prior)
  for path in (base, prior):
    if any(x.is_symlink() for x in (path, *path.parents)):
      raise ValueError('NO_STORE_PATH_ALIAS')
  b, a = base.resolve(), prior.resolve()
  if b.is_relative_to(p.PUBLIC.parents[2].resolve()) or b.is_relative_to(a) or a.is_relative_to(b):
    raise ValueError('NEW_PRIVATE_STORE_OUTSIDE_REPOSITORY_AND_PRIOR_REQUIRED')


def historical():
  rows = oldpub.load()
  row = rows['empirical-plant-readiness-v1.json']
  return {
    **row['historical'],
    'stage_a': 'STRICT_READY_GATE_FAILED',
    'stage_a_readiness_sha256': row['receipt_sha256'],
    'stage_a_validation_sha256': row['validation_sha256'],
    'calibration_blockers': p.BLOCKERS,
    'ta_execution': False,
    'sg_execution': False,
    'composition_authorized': False,
  }


def stage_c_allowed(_yaw_admissible):
  historical()
  return False


def open_gate(role, freeze, selection, binding):
  if role not in ('TRAIN', 'DEVELOPMENT', 'COMMAND_BRIDGE_ONLY', 'YAW_HOLDOUT'):
    raise ValueError('ONLY_FROZEN_PROVENANCE_ROLES')
  if role != 'YAW_HOLDOUT':
    return
  if any(x is None for x in (freeze, selection, binding)):
    raise ValueError('YAW_HOLDOUT_CLOSED_NO_IMMUTABLE_FREEZE')
  for x in (freeze, selection, binding):
    p.verify(x)
  if (
    freeze.get('schema') != 'EMPIRICAL_YAW_FREEZE_V1'
    or selection.get('schema') != 'EMPIRICAL_PROVENANCE_SELECTION_V1'
    or binding.get('schema') != 'EMPIRICAL_PROVENANCE_EXECUTION_V1'
    or freeze.get('selection_sha256') != selection['receipt_sha256']
    or freeze.get('binding_sha256') != binding['receipt_sha256']
    or selection.get('binding_sha256') != binding['receipt_sha256']
  ):
    raise ValueError('EXACT_FROZEN_YAW_SELECTION_BINDING_REQUIRED')


def source_identity():
  return {Path(module.__file__).name: p.sha(Path(module.__file__).read_bytes()) for module in [q, r, c, p, s, m, oldrun, oldpub]} | {
    Path(__file__).name: p.sha(Path(__file__).read_bytes())
  }


def settings_complete(roles):
  rows = [row for role in ['TRAIN', 'DEVELOPMENT'] for row in roles.get(role, [])]
  return (
    all(roles.get(role) for role in ['TRAIN', 'DEVELOPMENT'])
    and all(row['runtime_setting_known'] for row in rows)
    and len({row['settings_sha256'] for row in rows}) == 1
  )


def prior_gate(split, inventory, metadata, binding, rows):
  for row in [split, inventory, metadata, binding]:
    p.verify(row)
  public_split = rows['empirical-plant-split-v1.json']
  if (
    split['receipt_sha256'] != public_split['local_split_sha256']
    or inventory['receipt_sha256'] != public_split['inventory_sha256']
    or binding['receipt_sha256'] != rows['empirical-plant-selection-v1.json']['execution_binding_sha256']
    or binding.get('split_sha256') != split['receipt_sha256']
    or binding.get('inventory_sha256') != inventory['receipt_sha256']
    or binding.get('metadata_sha256') != metadata['receipt_sha256']
  ):
    raise ValueError('HISTORICAL_PRIVATE_ROLES_NOT_PUBLICLY_BOUND')


def numeric_once(path, expected, raw_path, schema, yaw):
  atomic = path.with_name(path.name + '.atomic')
  if atomic.exists() or atomic.is_symlink():
    durable = read(atomic)
    if durable.get('schema') != 'EMPIRICAL_PROVENANCE_NUMERIC_V1' or any(durable.get(k) != v for k, v in expected.items()):
      raise ValueError('STALE_ATOMIC_NUMERIC_RECEIPT')
    p.persist(path, durable)
  if path.exists() or path.is_symlink():
    value = read(path)
    if value.get('schema') != 'EMPIRICAL_PROVENANCE_NUMERIC_V1' or any(value.get(k) != v for k, v in expected.items()):
      raise ValueError('STALE_PRIVATE_NUMERIC_RECEIPT')
    return value
  first = r.read_numeric(s.events(raw_path, schema), yaw)
  second = r.read_numeric(s.events(raw_path, schema), yaw) if expected['role'] != 'YAW_HOLDOUT' else first
  if first != second:
    raise ValueError('NUMERIC_EXTRACTION_NOT_EXACT')
  value = p.seal({'schema': 'EMPIRICAL_PROVENANCE_NUMERIC_V1', **expected, 'streams': first, 'payload_repeats': 1 if expected['role'] == 'YAW_HOLDOUT' else 2})
  p.persist(path, value)
  return value


def ready_rule(result):
  if result.get('status') != 'EVALUATED':
    return False
  groups = [result['one_step'], result['rollout']['100']]
  return all(
    group['model']['count'] >= 201
    and all(
      group['model'][metric] is not None and group[name][metric] is not None and group['model'][metric] < group[name][metric]
      for name in ['ZERO_RESPONSE', 'HOLD_LAST_OUTPUT', 'TRAIN_STATIC_GAIN']
      for metric in ['MAE', 'RMSE', 'P95_ABS']
    )
    for group in groups
  )


def yaw_result_unit(result):
  return {**result, 'unit': 'YAW_RAD_PER_S_CONDITIONAL'}


def _limit_comparison(streams):
  command = streams['command']
  control = streams['control']
  state = streams['state']
  times = [x['time_ns'] for x in control]
  st = [x['time_ns'] for x in state]
  residual = []
  pressed = 0
  faults = 0
  for previous, output in zip(command, command[1:], strict=False):
    index = bisect_right(times, previous['time_ns']) - 1
    j = bisect_right(st, output['time_ns']) - 1
    if (
      index < 0
      or output['time_ns'] - previous['time_ns'] > 20_000_000
      or output['time_ns'] - times[index] > 20_000_000
      or previous['time_ns'] - times[index] > 20_000_000
      or not output['valid']
      or not control[index]['valid']
    ):
      continue
    a, b = output['normalized'], control[index]['requested']
    if not np.isfinite([a, b]).all():
      continue
    residual.append(a - b)
    if j >= 0 and output['time_ns'] - st[j] <= 20_000_000:
      pressed += int(state[j]['driver_pressed'])
      faults += int(state[j]['eps_fault'])
  return {
    'pairs': len(residual),
    'different': sum(x != 0 for x in residual),
    'driver_pressed_context': pressed,
    'eps_fault_context': faults,
    'residual': m.statistics(residual, np.zeros(len(residual))),
    'safety_limited': None,
    'curvature_limited': None,
    'reason': 'LIMIT_REASON_UNOBSERVED',
  }


def _extract(base, prior, root, segments, metadata, original_source, schema, binding, freeze=None, selection=None):
  results = []
  rejected = []
  for count, segment in enumerate(segments):
    role = segment['role']
    open_gate(role, freeze, selection, binding)
    if source_identity() != binding['executor_sha256']:
      raise ValueError('PROVENANCE_EXECUTOR_DRIFT')
    meta = metadata[segment['segment_id']]
    p.verify(meta)
    if meta['schema'] != 'EMPIRICAL_SEGMENT_METADATA_V1':
      rejected.append({'segment_id': segment['segment_id'], 'role': role, 'reason': 'PREEXISTING_TRUNCATED_SEGMENT_REJECTED_WHOLE'})
      continue
    s.validate_generation(segment, meta, original_source)
    path = root / segment['source_key']
    if any(x.is_symlink() for x in (path, *path.parents)) or not path.resolve().is_relative_to(root.resolve()):
      raise ValueError('NO_SOURCE_ALIAS_OR_ROOT_ESCAPE')
    if p.sha(path.read_bytes()) != segment['source_sha256']:
      raise ValueError('SOURCE_INVENTORY_HASH_CHANGED')
    cache = base / 'segments' / f"{segment['segment_id']}.json"
    numeric_path = base / 'numeric' / f"{segment['segment_id']}.json"
    expected = {
      'segment_id': segment['segment_id'],
      'role': role,
      'source_sha256': segment['source_sha256'],
      'metadata_sha256': meta['receipt_sha256'],
      'binding_sha256': binding['receipt_sha256'],
    }
    if cache.exists() or cache.is_symlink():
      value = read(cache)
      numeric = read(numeric_path)
      if (
        any(value.get(k) != v for k, v in expected.items())
        or value.get('numeric_sha256') != numeric['receipt_sha256']
        or any(numeric.get(k) != v for k, v in expected.items())
      ):
        raise ValueError('STALE_PROVENANCE_CACHE')
    else:
      yaw = role != 'COMMAND_BRIDGE_ONLY'
      numeric = numeric_once(numeric_path, expected, path, schema, yaw)
      first = numeric['streams']
      settings = first['settings']
      if len({p.sha(p.canonical(x)) for x in settings}) > 1:
        raise ValueError('CHANGING_CONTROL_SETTINGS_WITHIN_SEGMENT')
      settings = settings[0] if settings else {}
      profile = meta['metadata']['profiles'][0]
      maximum, known = r.effective_steer_max(profile, settings)
      pairs = [{k: x[k] for k in ['raw', 'normalized', 'valid']} for x in first['command']]
      value = p.seal(
        {
          'schema': 'EMPIRICAL_PROVENANCE_SEGMENT_V1',
          **expected,
          'numeric_sha256': numeric['receipt_sha256'],
          'settings_sha256': p.sha(p.canonical(settings)),
          'steer_max': maximum,
          'runtime_setting_known': known,
          'command_pairs': pairs,
          'bridge': r.command_bridge(pairs, maximum, known),
          'limits': _limit_comparison(first),
          'gyro_rejected': first['gyro_rejected'],
          'gyro_count': len(first['gyro']),
          'aligned': r.aligned(first) if yaw else None,
        }
      )
      p.persist(cache, value)
    if source_identity() != binding['executor_sha256'] or p.sha(path.read_bytes()) != segment['source_sha256']:
      raise ValueError('SOURCE_CHANGED_DURING_EXTRACTION')
    results.append(value)
    print('segment_complete', role, count + 1, len(segments), flush=True)
  index = p.seal(
    {
      'schema': 'EMPIRICAL_PROVENANCE_EXTRACTION_INDEX_V1',
      'binding_sha256': binding['receipt_sha256'],
      'segments': {x['segment_id']: x['receipt_sha256'] for x in results},
      'rejected': rejected,
    }
  )
  suffix = segments[0]['role'] if segments else 'EMPTY'
  p.persist(base / f'index-{suffix}.json', index)
  return results, rejected


def shapes():
  metric = dict.fromkeys(['MAE', 'RMSE', 'MEDIAN_ABS', 'P95_ABS', 'BIAS', 'CORRELATION'], float) | {'count': int}
  crossmetric = metric | {'SCALE_RATIO_RMS_DIAGNOSTIC_ONLY': float}
  pair = {'gyro': crossmetric, 'kinematic': crossmetric}
  option = {'axis': int, 'sign': int, 'lag_samples': int}
  analysis = {
    **pair,
    'coverage': {'total': int, 'valid': int, 'unavailable': int, 'segment_count': int, 'supported_segments': int, 'minimum_support_met': bool},
    'speed_bins': dict.fromkeys(['LOW', 'MEDIUM', 'HIGH'], pair),
    'turn_sign': dict.fromkeys(['POSITIVE', 'NEGATIVE'], pair),
    'time_blocks': dict.fromkeys(['0', '1', '2', '3'], pair),
    'segments': [{'segment_id': str, **pair}],
    'residual_autocorrelation': {str(i): {'correlation': float, 'count': int} for i in range(1, 21)},
    'vehicle_frame_calibrated': bool,
    'unit': str,
  }
  bridge = {
    'status': str,
    'total': int,
    'eligible': int,
    'invalid': int,
    'steer_max': int,
    'runtime_setting_known': bool,
    'exact_ratio_match_count': int,
    'float32_expected_exact_count': int,
    'sign_conflicts': int,
    'domain_conflicts': int,
    'raw_saturated_count': int,
    'normalized_saturated_count': int,
    'residual': metric | {'MAX_ABS': float},
    'mismatch_taxonomy': dict.fromkeys(['FLOAT32_RELATION', 'SIGN', 'SOURCE_DOMAIN', 'INVALID_OR_NONFINITE'], int),
    'physical_applied_command_acknowledged': bool,
  }
  hist = dict.fromkeys(['current', 'v1', 'v2', 'ta', 'sg', 'stage_a', 'stage_a_readiness_sha256', 'stage_a_validation_sha256'], str) | {
    'v2_violations': int,
    'calibration_blockers': [str],
    'ta_execution': bool,
    'sg_execution': bool,
    'composition_authorized': bool,
  }
  verdict = {
    'status': str,
    'unit_status': str,
    'device_frame': str,
    'vehicle_frame_calibrated': bool,
    'rigid_transform': dict,
    'fitting_allowed': bool,
    'fitting_gates': dict.fromkeys(q.GATES, bool),
    'hypothesis': str,
    'gyro_candidate': option,
    'source_unit_string': str,
    'holdout_used_for_selection': bool,
  }
  evaluated = oldrun.public_shapes()['empirical-plant-holdout-validation-v1.json']['results']['LOW']
  selection = oldrun.public_shapes()['empirical-plant-selection-v1.json']['selection']
  output = {
    'empirical-command-bridge-v1.json': {
      'status': str,
      'groups': [bridge],
      'segments': int,
      'segment_status_counts': (
        'map',
        [
          'RAW_TO_NORMALIZED_COMMAND_CONFIRMED',
          'RAW_TO_NORMALIZED_COMMAND_PARTIAL',
          'RAW_TO_NORMALIZED_COMMAND_CONFLICT',
          'RAW_TO_NORMALIZED_COMMAND_UNAVAILABLE',
        ],
        int,
      ),
      'source_sha256': str,
      'same_message_pairs': bool,
      'units': str,
    },
    'empirical-limit-observability-v1.json': {
      'status': str,
      'reason': str,
      'safety_limited': bool,
      'curvature_limited': bool,
      'driver_limited': bool,
      'rate_limited': bool,
      'request_output_linkage': str,
      'difference_includes_quantization_and_timing': bool,
      'historical_clean_primary_valid': int,
      'pairs': int,
      'different': int,
      'driver_pressed_context': int,
      'eps_fault_context': int,
      'clean_limit_mask_confirmed': bool,
    },
    'empirical-gyro-crosscheck-v1.json': {
      'status': str,
      'hypothesis': str,
      'gyro_candidate': option,
      'roles': dict.fromkeys(['TRAIN', 'DEVELOPMENT', 'YAW_HOLDOUT'], analysis),
      'rejected_sensor_messages': int,
      'selection_sha256': str,
      'candidates_evaluated': int,
      'continuous_scale_fit': bool,
      'bias_corrected': bool,
    },
    'empirical-kinematic-yaw-crosscheck-v1.json': {
      'status': str,
      'wheelbase_m': float,
      'steer_ratio': float,
      'angle_offset': str,
      'hypotheses_development': {h: {**pair, 'candidate': option} for h in q.policy()['hypotheses']},
      'unit_source': str,
      'truth': bool,
      'limitations': [str],
    },
    'empirical-yaw-verdict-v1.json': verdict,
    'empirical-signal-provenance-readiness-v1.json': {
      'status': str,
      'command_bridge': str,
      'yaw_signal': str,
      'yaw_model': str,
      'stage_a': str,
      'stage_c': str,
      'historical': hist,
      'calibration_blockers': [str],
      'sealed_reference': str,
      'vehicle': [str],
      'route_count': int,
      'additional_homogeneous_routes': int,
      'route_generalization': str,
      'historical_holdout_reused_for_yaw': bool,
      'new_yaw_holdout_segments': int,
      'new_yaw_holdout_rejected': int,
      'temporal_separation': str,
      'exact_repeatability': str,
      'full_plant_ready': bool,
      'actual_physical_delay': float,
      'counterfactual_use_admitted': bool,
    },
    'empirical-yaw-family-policy-v1.json': {
      'family_policy_sha256': str,
      'metric_policy_sha256': str,
      'model_input': str,
      'fitting_allowed': bool,
      'maximum_candidates_per_bin': int,
    },
    'empirical-yaw-selection-v1.json': {'selection': selection, 'local_model_sha256': str, 'hypothesis': str, 'holdout_selection_input': bool},
    'empirical-yaw-holdout-validation-v1.json': {
      'results': dict.fromkeys(['LOW', 'MEDIUM', 'HIGH'], evaluated),
      'model_sha256': str,
      'freeze_sha256': str,
      'opening_sha256': str,
      'exact_repeatability': str,
      'unit': str,
      'fit_reselected': bool,
    },
    'empirical-two-stage-readiness-v1.json': {'stage_a': str, 'stage_b': str, 'stage_c': str, 'historical': hist, 'full_plant_ready': bool},
  }
  return {name: fields | {'schema': str, 'binding_sha256': str, 'receipt_sha256': str} | dict.fromkeys(p.FIREWALL, bool) for name, fields in output.items()}


def public_yaw_unit():
  return 'EMPTY_DBC_UNIT_UNVERIFIED'


def publication_guard(name, row):
  if name not in shapes():
    raise ValueError('EXACT_PROVENANCE_PUBLIC_BASENAME')
  p.verify(row)
  oldrun.shape_check(row, shapes()[name])


def publish(base, name, body, binding):
  row = p.seal({'schema': name.removesuffix('.json').upper().replace('-', '_'), 'binding_sha256': binding['receipt_sha256'], **body})
  publication_guard(name, row)
  p.persist(base / 'public' / name, row)
  p.persist(p.PUBLIC / name, row)
  return row


def run(prior, base, source_root):
  prior, base = Path(prior), Path(base)
  store_gate(base, prior)
  hist = historical()
  inventory = read(base / 'inventory.json')
  split = read(base / 'split.json')
  original_split = read(prior / 'split.json')
  metadata_all = read(prior / 'metadata-all.json')
  prior_gate(original_split, read(prior / 'inventory.json'), metadata_all, read(prior / 'execution-binding.json'), oldpub.load())
  if inventory != read(prior / 'inventory.json'):
    raise ValueError('SAME_PRIVATE_INVENTORY_REQUIRED')
  if split['segments'] != q.split_roles(original_split['segments']):
    raise ValueError('FROZEN_PROVENANCE_SPLIT_DRIFT')
  if read(base / 'policy.json') != q.policy() or read(p.PUBLIC / 'empirical-yaw-hypothesis-policy-v1.json') != q.policy():
    raise ValueError('FROZEN_PROVENANCE_POLICY_DRIFT')
  source = q.source_contract(source_root)
  source_gate(source)
  if read(base / 'source.json') != source:
    raise ValueError('RECORDED_SOURCE_DRIFT')
  original_source = s.source_contract(source_root)
  metadata = {x['segment_id']: x for x in metadata_all['segments']}
  generations = {
    s.validate_generation(x, metadata[x['segment_id']], original_source)
    for x in split['segments']
    if metadata[x['segment_id']]['schema'] == 'EMPIRICAL_SEGMENT_METADATA_V1'
  }
  if len(generations) != 1:
    raise ValueError('ONE_SOURCE_PROFILE_GENERATION_REQUIRED')
  # New evaluation role must never have been numerically extracted by Stage A.
  for segment in split['segments']:
    if segment['role'] == 'YAW_HOLDOUT' and (prior / 'aligned' / f"{segment['segment_id']}.json").exists():
      raise ValueError('NEW_YAW_HOLDOUT_PREVIOUSLY_OPENED')
  binding = p.seal(
    {
      'schema': 'EMPIRICAL_PROVENANCE_EXECUTION_V1',
      'source_sha256': source['receipt_sha256'],
      'policy_sha256': q.policy()['receipt_sha256'],
      'split_sha256': split['receipt_sha256'],
      'inventory_sha256': inventory['receipt_sha256'],
      'metadata_sha256': metadata_all['receipt_sha256'],
      'generation_sha256': next(iter(generations)),
      'executor_sha256': source_identity(),
      'environment': oldrun.environment(),
      'historical': hist,
      'yaw_holdout_initial_state': 'CLOSED_NUMERIC_UNOPENED_OLD_EMBARGO',
    }
  )
  p.persist(base / 'execution-binding.json', binding)
  schema = s.schema(source_root)
  root = Path(inventory['root'])
  roles = {}
  failures = []
  for role in ['TRAIN', 'DEVELOPMENT', 'COMMAND_BRIDGE_ONLY']:
    roles[role], bad = _extract(base, prior, root, [x for x in split['segments'] if x['role'] == role], metadata, original_source, schema, binding)
    failures.extend(bad)
  profiles = [x['metadata']['profiles'][0] for x in metadata.values() if x['schema'] == 'EMPIRICAL_SEGMENT_METADATA_V1']
  profile = profiles[0]
  correspondence = c.select({name: roles[name] for name in ['TRAIN', 'DEVELOPMENT']}, profile)
  if correspondence != c.select({name: roles[name] for name in ['TRAIN', 'DEVELOPMENT']}, profile):
    raise ValueError('CORRESPONDENCE_NOT_EXACT_REPEATABLE')
  gates = {
    'unit_supported': correspondence['unit_supported'],
    'frozen_selection': True,
    'source_complete': settings_complete(roles),
    'split_disjoint': True,
    'train_dev_support': correspondence['hypothesis'] is not None,
    'untouched_role': True,
  }
  fit_allowed = q.yaw_fit_allowed(gates)
  selected = {}
  if fit_allowed:
    for regime in ['LOW', 'MEDIUM', 'HIGH']:
      data = {role: c.yaw_runs(roles[role], correspondence['hypothesis'], profile, regime) for role in ['TRAIN', 'DEVELOPMENT']}
      a = m.select(data, q.policy()['yaw_model_candidates'])
      b = m.select(data, q.policy()['yaw_model_candidates'])
      if a != b:
        raise ValueError('YAW_FIT_NOT_EXACT')
      selected[regime] = a
  models = p.seal({'schema': 'EMPIRICAL_YAW_PRIVATE_MODELS_V1', 'binding_sha256': binding['receipt_sha256'], 'selected': selected, 'fit_allowed': fit_allowed})
  p.persist(base / 'models.json', models)
  selection = p.seal(
    {
      'schema': 'EMPIRICAL_PROVENANCE_SELECTION_V1',
      'binding_sha256': binding['receipt_sha256'],
      'correspondence': correspondence,
      'fitting_gates': gates,
      'models_sha256': models['receipt_sha256'],
    }
  )
  p.persist(base / 'selection.json', selection)
  freeze = p.seal(
    {
      'schema': 'EMPIRICAL_YAW_FREEZE_V1',
      'binding_sha256': binding['receipt_sha256'],
      'selection_sha256': selection['receipt_sha256'],
      'models_sha256': models['receipt_sha256'],
    }
  )
  p.persist(base / 'freeze.json', freeze)
  print(
    'CORRESPONDENCE_AND_OPTIONAL_MODEL_FROZEN',
    correspondence['hypothesis'],
    'unit_supported',
    correspondence['unit_supported'],
    'fit_allowed',
    fit_allowed,
    flush=True,
  )
  open_gate('YAW_HOLDOUT', freeze, selection, binding)
  opening = p.seal(
    {
      'schema': 'EMPIRICAL_YAW_HOLDOUT_OPENING_V1',
      'binding_sha256': binding['receipt_sha256'],
      'freeze_sha256': freeze['receipt_sha256'],
      'selection_sha256': selection['receipt_sha256'],
      'model_sha256': models['receipt_sha256'],
    }
  )
  p.persist(base / 'opening.json', opening)
  roles['YAW_HOLDOUT'], bad = _extract(
    base, prior, root, [x for x in split['segments'] if x['role'] == 'YAW_HOLDOUT'], metadata, original_source, schema, binding, freeze, selection
  )
  failures.extend(bad)
  hypothesis = correspondence['hypothesis']
  option = correspondence['gyro_candidate']
  analyses = {role: c.analyze(roles[role], hypothesis, option, profile) if hypothesis is not None else None for role in ['TRAIN', 'DEVELOPMENT', 'YAW_HOLDOUT']}
  again = {role: c.analyze(roles[role], hypothesis, option, profile) if hypothesis is not None else None for role in ['TRAIN', 'DEVELOPMENT', 'YAW_HOLDOUT']}
  if analyses != again:
    raise ValueError('YAW_CROSSCHECK_REPEATABILITY')
  results = {}
  for regime, model in selected.items():
    data = c.yaw_runs(roles['YAW_HOLDOUT'], hypothesis, profile, regime)
    if model['selected'] is None:
      results[regime] = {'status': 'UNAVAILABLE', 'holdout_runs': len(data)}
      continue
    a = yaw_result_unit(m.evaluate(data, model['selected']['model'], model['static_gain'], model['train_amplitude_quartiles']))
    b = yaw_result_unit(m.evaluate(data, model['selected']['model'], model['static_gain'], model['train_amplitude_quartiles']))
    if a != b:
      raise ValueError('YAW_MODEL_EVALUATION_REPEATABILITY')
    results[regime] = a
  evaluation = p.seal(
    {
      'schema': 'EMPIRICAL_YAW_PRIVATE_VALIDATION_V1',
      'binding_sha256': binding['receipt_sha256'],
      'analyses': analyses,
      'results': results,
      'freeze_sha256': freeze['receipt_sha256'],
      'opening_sha256': opening['receipt_sha256'],
      'models_sha256': models['receipt_sha256'],
      'failures': failures,
    }
  )
  p.persist(base / 'validation.json', evaluation)
  all_receipts = [x for rows in roles.values() for x in rows]
  group = []
  for maximum, known in sorted({(x['steer_max'], x['runtime_setting_known']) for x in all_receipts}):
    pairs = [pair for x in all_receipts if (x['steer_max'], x['runtime_setting_known']) == (maximum, known) for pair in x['command_pairs']]
    group.append(r.command_bridge(pairs, maximum, known))
  statuses = Counter(x['bridge']['status'] for x in all_receipts)
  command_status = (
    'RAW_TO_NORMALIZED_COMMAND_CONFLICT'
    if any(x['status'] == 'RAW_TO_NORMALIZED_COMMAND_CONFLICT' for x in group)
    else 'RAW_TO_NORMALIZED_COMMAND_CONFIRMED'
    if group and all(x['status'] == 'RAW_TO_NORMALIZED_COMMAND_CONFIRMED' for x in group)
    else 'RAW_TO_NORMALIZED_COMMAND_PARTIAL'
    if group
    else 'RAW_TO_NORMALIZED_COMMAND_UNAVAILABLE'
  )
  publish(
    base,
    'empirical-command-bridge-v1.json',
    {
      'status': command_status,
      'groups': group,
      'segments': len(all_receipts),
      'segment_status_counts': dict(statuses),
      'source_sha256': source['receipt_sha256'],
      'same_message_pairs': True,
      'units': 'RAW_CAN_AND_NORMALIZED_POST_CARCONTROLLER',
    },
    binding,
  )
  totals = {name: sum(x['limits'][name] for x in all_receipts) for name in ['pairs', 'different', 'driver_pressed_context', 'eps_fault_context']}
  publish(base, 'empirical-limit-observability-v1.json', {**r.limit_verdict(bool(totals['different'])), **totals, 'clean_limit_mask_confirmed': False}, binding)
  publish(
    base,
    'empirical-gyro-crosscheck-v1.json',
    {
      'status': 'YAW_UNIT_AND_AXIS_CORRESPONDENCE_DIAGNOSTIC',
      'hypothesis': hypothesis,
      'gyro_candidate': option,
      'roles': analyses,
      'rejected_sensor_messages': sum(x['gyro_rejected'] for x in all_receipts),
      'selection_sha256': selection['receipt_sha256'],
      'candidates_evaluated': 144,
      'continuous_scale_fit': False,
      'bias_corrected': False,
    },
    binding,
  )
  dev = {h: row['best'] for h, row in correspondence['candidates'].items()}
  publish(
    base,
    'empirical-kinematic-yaw-crosscheck-v1.json',
    {
      'status': 'KINEMATIC_YAW_SUPPORTING_DIAGNOSTIC',
      'wheelbase_m': profile['wheelbase'],
      'steer_ratio': profile['steer_ratio'],
      'angle_offset': q.policy()['angle_offset'],
      'hypotheses_development': dev,
      'unit_source': 'STATIC_CARPARAMS_AND_DEGREES_SAS11_NOT_MEASURED_KINEMATIC_TRUTH',
      'truth': False,
      'limitations': ['TIRE_SLIP', 'COMPLIANCE', 'UNDERSTEER', 'ANGLE_OFFSET_PENDING', 'STATIC_STEER_RATIO', 'NO_INDEPENDENT_ROAD_GEOMETRY'],
    },
    binding,
  )
  held = analyses['YAW_HOLDOUT']
  support = held is not None and held['coverage']['minimum_support_met']
  yaw_status = q.yaw_verdict(held is not None and held['gyro']['count'] > 0, correspondence['unit_supported'], support)
  model_status = (
    'EMPIRICAL_YAW_MODEL_BLOCKED'
    if not fit_allowed
    else ('EMPIRICAL_YAW_MODEL_DIAGNOSTIC_READY' if any(ready_rule(x) for x in results.values()) else 'EMPIRICAL_YAW_MODEL_REJECTED')
  )
  publish(
    base,
    'empirical-yaw-verdict-v1.json',
    {
      'status': yaw_status,
      'unit_status': 'YAW_UNIT_EMPIRICALLY_SUPPORTED' if yaw_status == 'YAW_UNIT_SUPPORTED_FRAME_PARTIAL' else 'UNCONFIRMED',
      'device_frame': 'DEVICE_AXIS_CORRESPONDENCE_ONLY',
      'vehicle_frame_calibrated': False,
      'rigid_transform': None,
      'fitting_allowed': fit_allowed,
      'fitting_gates': gates,
      'hypothesis': hypothesis,
      'gyro_candidate': option,
      'source_unit_string': public_yaw_unit(),
      'holdout_used_for_selection': False,
    },
    binding,
  )
  if fit_allowed:
    publish(
      base,
      'empirical-yaw-family-policy-v1.json',
      {
        'family_policy_sha256': p.family_policy()['receipt_sha256'],
        'metric_policy_sha256': p.metric_policy()['receipt_sha256'],
        'model_input': q.policy()['yaw_model_input'],
        'fitting_allowed': True,
        'maximum_candidates_per_bin': 8,
      },
      binding,
    )
    publish(
      base,
      'empirical-yaw-selection-v1.json',
      {'selection': oldrun.model_public(selected), 'local_model_sha256': models['receipt_sha256'], 'hypothesis': hypothesis, 'holdout_selection_input': False},
      binding,
    )
    publish(
      base,
      'empirical-yaw-holdout-validation-v1.json',
      {
        'results': results,
        'model_sha256': models['receipt_sha256'],
        'freeze_sha256': freeze['receipt_sha256'],
        'opening_sha256': opening['receipt_sha256'],
        'exact_repeatability': 'PASS',
        'unit': 'YAW_RAD_PER_S_CONDITIONAL',
        'fit_reselected': False,
      },
      binding,
    )
    publish(
      base,
      'empirical-two-stage-readiness-v1.json',
      {
        'stage_a': 'HISTORICAL_STRICT_READY_GATE_FAILED',
        'stage_b': model_status,
        'stage_c': 'BLOCKED_STAGE_A_GATE_FAILED_NO_COMPOSED_ROLLOUT',
        'historical': hist,
        'full_plant_ready': False,
      },
      binding,
    )
  readiness = publish(
    base,
    'empirical-signal-provenance-readiness-v1.json',
    {
      'status': 'EMPIRICAL_PLANT_PARTIAL',
      'command_bridge': command_status,
      'yaw_signal': yaw_status,
      'yaw_model': model_status,
      'stage_a': 'EMPIRICAL_ACTUATOR_MODEL_ONLY_UNCHANGED',
      'stage_c': 'BLOCKED_STAGE_A_GATE_FAILED',
      'historical': hist,
      'calibration_blockers': p.BLOCKERS,
      'sealed_reference': 'NOT_GENERATED',
      'vehicle': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
      'route_count': 1,
      'additional_homogeneous_routes': 0,
      'route_generalization': 'SINGLE_ROUTE_GENERALIZATION_UNAVAILABLE',
      'historical_holdout_reused_for_yaw': False,
      'new_yaw_holdout_segments': len(roles['YAW_HOLDOUT']),
      'new_yaw_holdout_rejected': sum(x['role'] == 'YAW_HOLDOUT' for x in failures),
      'temporal_separation': 'ADJACENT_EMBARGO_SEGMENTS_NO_ROUTE_INDEPENDENCE',
      'exact_repeatability': 'PASS',
      'full_plant_ready': False,
      'actual_physical_delay': None,
      'counterfactual_use_admitted': False,
    },
    binding,
  )
  historical()
  if source_identity() != binding['executor_sha256']:
    raise ValueError('FINAL_EXECUTOR_DRIFT')
  print('FINAL', readiness['status'], command_status, yaw_status, model_status, readiness['receipt_sha256'], flush=True)
  return readiness


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--prior-store', required=True)
  parser.add_argument('--private-store', required=True)
  parser.add_argument('--recorded-source', required=True)
  args = parser.parse_args()
  run(args.prior_store, args.private_store, args.recorded_source)


if __name__ == '__main__':
  main()
