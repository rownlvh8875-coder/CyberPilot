"""Restartable private identification; no image decoder, controller, CAN or Params."""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import platform
import re
import sys

import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_plant_signals as s
from openpilot.tools.cyber_autotune import empirical_plant_model as m


def read(path):
  return p.verify(json.loads(Path(path).read_bytes()))


def extraction_gate(role, frozen, models=None, selection=None, binding=None):
  if role not in ('TRAIN', 'DEVELOPMENT', 'HOLDOUT'):
    raise ValueError('ONLY_FROZEN_ACTIVE_SPLIT')
  if role == 'HOLDOUT':
    if frozen is None:
      raise ValueError('HOLDOUT_CLOSED_MODEL_NOT_FROZEN')
    p.verify(frozen)
    if any(x is None for x in (models, selection, binding)):
      raise ValueError('PERSISTED_MODEL_SELECTION_BINDING_REQUIRED')
    for row in (models, selection, binding):
      p.verify(row)
    if (
      frozen.get('schema') != 'EMPIRICAL_MODEL_FROZEN_V1'
      or models.get('schema') != 'EMPIRICAL_PRIVATE_MODELS_V1'
      or selection.get('schema') != 'EMPIRICAL_PLANT_SELECTION_V1'
      or binding.get('schema') != 'EMPIRICAL_PLANT_EXECUTION_BINDING_V1'
      or frozen.get('models_sha256') != models['receipt_sha256']
      or frozen.get('selection_sha256') != selection['receipt_sha256']
      or frozen.get('execution_binding_sha256') != binding['receipt_sha256']
      or models.get('execution_binding_sha256') != binding['receipt_sha256']
      or selection.get('execution_binding_sha256') != binding['receipt_sha256']
      or selection.get('local_model_sha256') != models['receipt_sha256']
    ):
      raise ValueError('HOLDOUT_FREEZE_CONTENT_OR_IDENTITY_MISMATCH')


def verdict(model_available, signals_available, yaw_proven):
  if yaw_proven:
    raise ValueError('NO_NEW_YAW_UNIT_EVIDENCE_ADMITTED')
  if not signals_available:
    return 'EMPIRICAL_SIGNAL_CHAIN_UNAVAILABLE'
  return 'EMPIRICAL_ACTUATOR_MODEL_ONLY' if model_available else 'EMPIRICAL_PLANT_PARTIAL'


def public_shapes():
  metric = dict.fromkeys(['MAE', 'RMSE', 'MEDIAN_ABS', 'P95_ABS', 'BIAS', 'CORRELATION'], float) | {'count': int}
  short = {'count': int, 'RMSE': float}
  config = {'family': str, 'delay_samples': int, 'input_taps': int, 'output_lags': int, 'intercept': bool}
  estimates = dict.fromkeys(['model', 'ZERO_RESPONSE', 'HOLD_LAST_OUTPUT', 'TRAIN_STATIC_GAIN'], metric)
  correlations = {str(k): {'correlation': float, 'count': int} for k in range(1, 21)}
  diagnosis = {
    'residual_autocorrelation': correlations,
    'residual_past_input_correlation': correlations,
    'residual_past_output_correlation': correlations,
    'input_sign': dict.fromkeys(['ZERO', 'POSITIVE', 'NEGATIVE'], metric),
    'amplitude_quartiles': {str(k): metric for k in range(4)},
    'amplitude_boundaries_source': str,
    'per_segment_quarter_index_pooled': {str(k): metric for k in range(4)},
    'command_excitation': {'minimum': float, 'maximum': float, 'std': float, 'distinct_count': int},
    'condition_number': float,
    'saturation_intervention_residual': str,
  }
  evaluated = {
    'status': str,
    'unit': str,
    'one_step': estimates,
    'rollout': {str(k): estimates for k in [25, 50, 100, 200]},
    'residual_diagnostics': diagnosis,
    'finite_horizon_bounded': bool,
    'rollout_drift': str,
  }
  candidate = {'config': config, 'fit_status': str, 'train_count': int, 'development': ('union', metric, short)}
  selection = {
    k: {'selected_config': config, 'development': metric, 'candidate_count': int, 'candidate_dispositions': [candidate], 'coefficients_public': bool}
    for k in ['LOW', 'MEDIUM', 'HIGH']
  }
  reasons = [
    'MISSING_OR_GAP',
    'SOURCE_EVENT_GAP',
    'REPEATED_OUTPUT_EVENT',
    'NONFINITE',
    'INVALID_MESSAGE',
    'INACTIVE',
    'DRIVER_OVERRIDE',
    'EPS_FAULT',
    'NON_FORWARD_GEAR',
    'LOW_SPEED',
    'RAW_CAN_DOMAIN',
  ]
  coverage = {
    'total_grid_samples': int,
    'diagnostic_valid': int,
    'unavailable': int,
    'clean_primary_valid': int,
    'clean_limit_mask': str,
    'excluded_reasons_nonexclusive': ('map', reasons, int),
    'valid_by_speed_bin': ('map', ['LOW', 'MEDIUM', 'HIGH'], int),
    'segment_count': int,
    'measurement_clock': str,
  }
  historical = dict.fromkeys(['current', 'v1', 'v2', 'ta', 'sg'], str) | {'v2_violations': int}
  shapes = {
    'empirical-plant-selection-v1.json': {
      'schema': str,
      'execution_binding_sha256': str,
      'local_model_sha256': str,
      'selection': selection,
      'fit_exact_repeatability': str,
      'holdout_selection_input': bool,
      'performance_acceptance': bool,
      'closed_loop_bias': str,
    },
    'empirical-plant-holdout-validation-v1.json': {
      'schema': str,
      'execution_binding_sha256': str,
      'model_freeze_sha256': str,
      'holdout_opening_sha256': str,
      'holdout_state': str,
      'evaluation_repeats': int,
      'exact_repeatability': str,
      'results': {
        k: ('union', evaluated, {'status': str, 'holdout_runs': int}, {'status': str, 'one_step': estimates, 'rollout': dict})
        for k in ['LOW', 'MEDIUM', 'HIGH']
      },
      'coverage': dict.fromkeys(['TRAIN', 'DEVELOPMENT', 'HOLDOUT'], coverage),
      'integrity_dispositions': [{'segment_id': str, 'reason': str}],
      'fit_reselected_after_holdout': bool,
      'physical_units': str,
      'rollout_input': str,
    },
    'real-log-signal-audit-v1.json': {
      'schema': str,
      'metadata_receipt_sha256': str,
      'signal_source_sha256': str,
      'generation_sha256': str,
      'recorded_commit': str,
      'inventory_segments': int,
      'metadata_complete_segments': int,
      'metadata_integrity_rejected_segments': int,
      'video_image_payload_opened': bool,
      'gps_payload_read': bool,
      'model_payload_read': bool,
      'command': str,
      'command_provenance': str,
      'steering': str,
      'yaw': {'status': str, 'physical_unit': str, 'frame': str, 'reason': str},
      'tier': str,
      'safety_curvature_limited_mask': str,
      'raw_imu_camera_or_vehicle_transform': str,
      'single_route': str,
    },
    'descriptive-vs-empirical-plant-v1.json': {
      'schema': str,
      'local_model_sha256': str,
      'status': str,
      'descriptive': str,
      'empirical': str,
      'missing_bridge': [str],
      'physical_gain_comparison': float,
      'physical_delay_validation': float,
      'descriptive_results_recomputed': bool,
      'ta_sg_executed': bool,
    },
    'empirical-plant-readiness-v1.json': {
      'schema': str,
      'status': str,
      'holdout_state': str,
      'validation_sha256': str,
      'signal_audit_sha256': str,
      'comparison_sha256': str,
      'local_model_sha256': str,
      'signal_provenance': str,
      'yaw_model': str,
      'full_plant_ready': bool,
      'clean_primary_evaluation_available': bool,
      'ordinary_limit_unobserved': bool,
      'closed_loop_identification_bias': str,
      'single_route_generalization': str,
      'counterfactual_use': str,
      'calibration_blockers': [str],
      'historical': historical,
      'composition_recommendation': str,
      'composition_authorization': str,
      'candidate_search': str,
      'frozen_candidate_evaluation': str,
      'sealed_reference': str,
      'vehicle': [str],
    },
  }
  return {name: shape | dict.fromkeys(p.FIREWALL, bool) | {'receipt_sha256': str} for name, shape in shapes.items()}


def shape_check(value, shape):
  if value is None:
    return
  if isinstance(shape, tuple):
    if shape[0] == 'union':
      for option in shape[1:]:
        try:
          shape_check(value, option)
          return
        except ValueError:
          pass
      raise ValueError('PUBLIC_UNION_SCHEMA')
    if type(value) is not dict or set(value) - set(shape[1]):
      raise ValueError('PUBLIC_MAP_KEYS')
    for item in value.values():
      shape_check(item, shape[2])
  elif isinstance(shape, dict):
    if type(value) is not dict or set(value) != set(shape):
      raise ValueError('PUBLIC_EXACT_FIELDS_REQUIRED')
    for key, item in value.items():
      shape_check(item, shape[key])
  elif isinstance(shape, list):
    if type(value) is not list:
      raise ValueError('PUBLIC_LIST_REQUIRED')
    for item in value:
      shape_check(item, shape[0])
  elif shape is float:
    if type(value) not in (float, int) or not np.isfinite(value):
      raise ValueError('PUBLIC_FINITE_NUMBER')
  elif shape is str:
    if type(value) is not str or len(value) > 256 or re.fullmatch(r'[A-Za-z0-9_ .:=<>+()\-]+', value) is None:
      raise ValueError('PUBLIC_ENUM_OR_HASH_ONLY_NO_PATHS')
  elif shape is dict:
    if value != {}:
      raise ValueError('NO_ARBITRARY_PUBLIC_DICT')
  elif type(value) is not shape:
    raise ValueError('PUBLIC_TYPE_MISMATCH')


def publication_guard(row, name=None):
  shapes = public_shapes()
  if name not in shapes:
    raise ValueError('EXACT_PUBLIC_ARTIFACT_BASENAME_REQUIRED')
  p.verify(row)
  shape_check(row, shapes[name])


def publish(name, row):
  if name not in public_shapes():
    raise ValueError('EXACT_PUBLIC_ARTIFACT_BASENAME_REQUIRED')
  receipt = p.seal(row)
  publication_guard(receipt, name)
  p.persist(p.PUBLIC / name, receipt)
  return receipt


def source_identity():
  files = [Path(__file__), Path(s.__file__), Path(m.__file__), Path(p.__file__)]
  return {f.name: p.sha(f.read_bytes()) for f in files}


def environment():
  names = ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')
  if any(os.environ.get(name) != '1' for name in names):
    raise ValueError('FROZEN_SINGLE_THREAD_ENVIRONMENT_REQUIRED')
  return {
    'python': sys.version.split()[0],
    'numpy': np.__version__,
    'machine': platform.machine(),
    'threads': dict.fromkeys(names, '1'),
    'solver': 'numpy.linalg.lstsq/rcond=None/float64',
    'randomness': False,
  }


def extraction(base, root, segments, metadata, source, schema, authorization, frozen=None):
  results = []
  failures = []
  for index, segment in enumerate(segments):
    proof = [read(base / name) for name in ('models.json', 'model-selection.json', 'execution-binding.json')] if segment['role'] == 'HOLDOUT' else [None] * 3
    extraction_gate(segment['role'], frozen, *proof)
    if source_identity() != authorization['source_identity']:
      raise ValueError('EXTRACTION_SOURCE_IDENTITY_DRIFT')
    meta = metadata[segment['segment_id']]
    if meta['schema'] != 'EMPIRICAL_SEGMENT_METADATA_V1':
      failures.append({'segment_id': segment['segment_id'], 'reason': 'METADATA_INTEGRITY_REJECTED'})
      continue
    generation = s.validate_generation(segment, meta, source)
    if p.sha((root / segment['source_key']).read_bytes()) != segment['source_sha256']:
      raise ValueError('PRIVATE_SOURCE_CHANGED_CACHE_REJECTED')
    dest = base / 'aligned' / f"{segment['segment_id']}.json"
    if dest.exists():
      r = read(dest)
      if (
        r['execution_binding_sha256'] != authorization['receipt_sha256']
        or r['source_sha256'] != segment['source_sha256']
        or r['generation_sha256'] != generation
      ):
        raise ValueError('STALE_EXTRACTION_CACHE')
    else:
      # Re-read and align twice, not merely hash the same cached data twice.
      a = s.extract(root / segment['source_key'], segment, meta, source, schema)
      if segment['role'] != 'HOLDOUT':
        b = s.extract(root / segment['source_key'], segment, meta, source, schema)
        if a != b:
          raise ValueError('EXTRACTION_EXACT_REPEATABILITY_FAILED')
      r = p.seal(
        {k: v for k, v in a.items() if k != 'receipt_sha256'}
        | {'execution_binding_sha256': authorization['receipt_sha256'], 'extraction_repeats': 1 if segment['role'] == 'HOLDOUT' else 2}
      )
      p.persist(dest, r)
    results.append(r)
    if index % 10 == 0:
      print('extracted', segment['role'], index + 1, 'of', len(segments), flush=True)
  return results, failures


def pool(receipts, regime):
  return [run for receipt in receipts for run in m.runs(receipt['aligned']['rows'], regime)]


def coverage(receipts):
  reasons = Counter()
  regimes = Counter()
  total = valid = 0
  for receipt in receipts:
    for row in receipt['aligned']['rows']:
      total += 1
      valid += int(row['diagnostic_valid'])
      reasons.update(row['reasons'])
      if row['diagnostic_valid']:
        regimes[row['speed_bin']] += 1
  return {
    'total_grid_samples': total,
    'diagnostic_valid': valid,
    'unavailable': total - valid,
    'clean_primary_valid': 0,
    'clean_limit_mask': 'UNOBSERVED_NOT_FALSE',
    'excluded_reasons_nonexclusive': dict(reasons),
    'valid_by_speed_bin': dict(regimes),
    'segment_count': len(receipts),
    'measurement_clock': 'PUBLISH_TIME_ONLY',
  }


def model_public(selection):
  public = {}
  for regime, entry in selection.items():
    chosen = entry['selected']
    public[regime] = {
      'selected_config': None if chosen is None else chosen['model']['config'],
      'development': None if chosen is None else chosen['development'],
      'candidate_count': len(entry['candidates']),
      'candidate_dispositions': [
        {'config': r['model']['config'], 'fit_status': r['model']['status'], 'train_count': r['model']['count'], 'development': r['development']}
        for r in entry['candidates']
      ],
      'coefficients_public': False,
    }
  return public


def run(base, source_root):
  base = Path(base)
  if base.resolve().is_relative_to(p.PUBLIC.parents[2].resolve()):
    raise ValueError('PRIVATE_STORE_MUST_BE_OUTSIDE_REPOSITORY')
  inventory = read(base / 'inventory.json')
  split = read(base / 'split.json')
  meta_all = read(base / 'metadata-all.json')
  if split != p.split(inventory['segments']):
    raise ValueError('SPLIT_IDENTITY_DRIFT')
  metadata = {r['segment_id']: p.verify(r) for r in meta_all['segments']}
  source = s.source_contract(source_root)
  profiles = set()
  active = [r for r in split['segments'] if r['role'] != 'EMBARGO']
  for segment in active:
    profiles.add(s.validate_generation(segment, metadata[segment['segment_id']], source))
  if len(profiles) != 1:
    raise ValueError('MULTIPLE_DATASET_GENERATIONS_REJECTED')
  binding = p.seal(
    {
      'schema': 'EMPIRICAL_PLANT_EXECUTION_BINDING_V1',
      'inventory_sha256': inventory['receipt_sha256'],
      'split_sha256': split['receipt_sha256'],
      'metadata_sha256': meta_all['receipt_sha256'],
      'signal_source_sha256': source['receipt_sha256'],
      'source_identity': source_identity(),
      'environment': environment(),
      'data_policy_sha256': p.policy()['receipt_sha256'],
      'family_policy_sha256': p.family_policy()['receipt_sha256'],
      'metric_policy_sha256': p.metric_policy()['receipt_sha256'],
      'alignment_policy_sha256': p.alignment_policy()['receipt_sha256'],
      'generation_sha256': next(iter(profiles)),
      'initial_holdout_state': 'HOLDOUT_CLOSED',
      'stage': 'RAW_POST_LIMIT_LOGGED_COMMAND_TO_CAN_MEASURED_STEERING_DEG',
      'yaw_stage': 'BLOCKED_UNIT_AND_FRAME_UNVERIFIED',
      'clean_limit_mask': 'UNAVAILABLE',
    }
  )
  p.persist(base / 'execution-binding.json', binding)
  schema = s.schema(source_root)
  root = Path(inventory['root'])
  byrole = {}
  failures = []
  for role in ('TRAIN', 'DEVELOPMENT'):
    byrole[role], failed = extraction(base, root, [r for r in active if r['role'] == role], metadata, source, schema, binding)
    failures.extend(failed)
  print('TRAIN_DEVELOPMENT_ALIGNED_HOLDOUT_STILL_CLOSED', flush=True)
  selected = {}
  for regime, _, _ in p.policy()['speed_bins']:
    data = {role: pool(byrole[role], regime) for role in ('TRAIN', 'DEVELOPMENT')}
    a = m.select(data, p.family_policy()['candidates'])
    b = m.select(data, p.family_policy()['candidates'])
    if a != b:
      raise ValueError('MODEL_FIT_REPEATABILITY_FAILED')
    selected[regime] = a
    print('selected', regime, None if a['selected'] is None else a['selected']['model']['config'], flush=True)
  local = p.seal(
    {
      'schema': 'EMPIRICAL_PRIVATE_MODELS_V1',
      'execution_binding_sha256': binding['receipt_sha256'],
      'selection': selected,
      'fit_repeats': 2,
      'training_role': 'TRAIN',
      'selection_role': 'DEVELOPMENT',
    }
  )
  p.persist(base / 'models.json', local)
  selected_public = publish(
    'empirical-plant-selection-v1.json',
    {
      'schema': 'EMPIRICAL_PLANT_SELECTION_V1',
      'execution_binding_sha256': binding['receipt_sha256'],
      'local_model_sha256': local['receipt_sha256'],
      'selection': model_public(selected),
      'fit_exact_repeatability': 'PASS',
      'holdout_selection_input': False,
      'performance_acceptance': False,
      'closed_loop_bias': 'OLS_OBSERVATIONAL_NOT_CAUSAL',
    },
  )
  p.persist(base / 'model-selection.json', selected_public)
  freeze = p.seal(
    {
      'schema': 'EMPIRICAL_MODEL_FROZEN_V1',
      'models_sha256': local['receipt_sha256'],
      'selection_sha256': selected_public['receipt_sha256'],
      'execution_binding_sha256': binding['receipt_sha256'],
    }
  )
  p.persist(base / 'model-frozen.json', freeze)
  opening = p.seal(
    {
      'schema': 'EMPIRICAL_HOLDOUT_OPENED_V1',
      'model_freeze_sha256': freeze['receipt_sha256'],
      'split_sha256': split['receipt_sha256'],
      'purpose': 'ONE_SELECTION_FINAL_EVALUATION_EXACT_REPEAT_ONLY',
      'reselection_allowed': False,
    }
  )
  p.persist(base / 'holdout-opening.json', opening)
  print('MODEL_FROZEN_HOLDOUT_OPENING_RECORDED', flush=True)
  byrole['HOLDOUT'], failed = extraction(base, root, [r for r in active if r['role'] == 'HOLDOUT'], metadata, source, schema, binding, freeze)
  failures.extend(failed)
  evaluations = {}
  for regime, entry in selected.items():
    choice = entry['selected']
    data = pool(byrole['HOLDOUT'], regime)
    if choice is None:
      evaluations[regime] = {'status': 'UNAVAILABLE_NO_DEVELOPMENT_MODEL', 'holdout_runs': len(data)}
      continue
    a = m.evaluate(data, choice['model'], entry['static_gain'], entry['train_amplitude_quartiles'])
    b = m.evaluate(data, choice['model'], entry['static_gain'], entry['train_amplitude_quartiles'])
    if a != b:
      raise ValueError('EVALUATION_EXACT_REPEATABILITY_FAILED')
    evaluations[regime] = a
    # Full one-step predictions/residuals remain private and reproducible per segment.
    for receipt in byrole['HOLDOUT']:
      segment_data = m.runs(receipt['aligned']['rows'], regime)
      x, y, _, _ = m.design(segment_data, choice['model']['config'])
      prediction = x @ np.asarray(choice['model']['coefficients'])
      trace = p.seal(
        {
          'schema': 'EMPIRICAL_PRIVATE_PREDICTIONS_V1',
          'segment_id': receipt['segment_id'],
          'regime': regime,
          'aligned_sha256': receipt['receipt_sha256'],
          'model_sha256': local['receipt_sha256'],
          'predictions': prediction.tolist(),
          'measured': y.tolist(),
          'residuals': (prediction - y).tolist(),
        }
      )
      p.persist(base / 'predictions' / f"{receipt['segment_id']}-{regime}.json", trace)
  validation = p.seal(
    {
      'schema': 'EMPIRICAL_PLANT_HOLDOUT_VALIDATION_V1',
      'execution_binding_sha256': binding['receipt_sha256'],
      'model_freeze_sha256': freeze['receipt_sha256'],
      'holdout_opening_sha256': opening['receipt_sha256'],
      'holdout_state': 'HOLDOUT_EVALUATED',
      'evaluation_repeats': 2,
      'exact_repeatability': 'PASS',
      'results': evaluations,
      'coverage': {role: coverage(values) for role, values in byrole.items()},
      'integrity_dispositions': failures,
      'fit_reselected_after_holdout': False,
      'physical_units': 'COMMAND_RAW_CAN_TO_STEERING_DEGREES',
      'rollout_input': 'OBSERVED_COMMAND_CONDITIONAL_FORECAST_NOT_COUNTERFACTUAL_CONTROLLER_SIMULATION',
    }
  )
  p.persist(base / 'holdout-validation.json', validation)
  publish('empirical-plant-holdout-validation-v1.json', {k: v for k, v in validation.items() if k != 'receipt_sha256'})
  audit = publish(
    'real-log-signal-audit-v1.json',
    {
      'schema': 'REAL_LOG_SIGNAL_AUDIT_V1',
      'metadata_receipt_sha256': meta_all['receipt_sha256'],
      'signal_source_sha256': source['receipt_sha256'],
      'generation_sha256': next(iter(profiles)),
      'recorded_commit': s.RECORDED_COMMIT,
      'inventory_segments': len(split['segments']),
      'metadata_complete_segments': sum('metadata' in x for x in metadata.values()),
      'metadata_integrity_rejected_segments': sum('metadata' not in x for x in metadata.values()),
      'video_image_payload_opened': False,
      'gps_payload_read': False,
      'model_payload_read': False,
      'command': 'carOutput.actuatorsOutput.torqueOutputCan',
      'command_provenance': 'POST_CARCONTROLLER_RATE_LIMIT_LOGGED_NOT_EPS_ACK',
      'steering': 'CAN_SAS11_ANGLE_DEGREES',
      'yaw': s.yaw_provenance(''),
      'tier': 'TIER_B_ACTUAL_POST_CONTROLLER_COMMAND_AND_MEASURED_STEERING_ONLY',
      'safety_curvature_limited_mask': 'UNOBSERVED_DIAGNOSTIC_SUBSET_ONLY',
      'raw_imu_camera_or_vehicle_transform': 'NOT_AUDITED_NO_INVENTED_DIRECT_YAW',
      'single_route': 'TIME_BLOCK_HOLDOUT_NOT_ROUTE_INDEPENDENT',
    },
  )
  comparison = publish(
    'descriptive-vs-empirical-plant-v1.json',
    {
      'schema': 'DESCRIPTIVE_VS_EMPIRICAL_PLANT_DIAGNOSTIC_V1',
      'local_model_sha256': local['receipt_sha256'],
      'status': 'UNCOMPARABLE_COORDINATE_BASIS',
      'descriptive': 'NORMALIZED_TORQUE_TO_CURVATURE_YAW_POSE',
      'empirical': 'RAW_CAN_COMMAND_TO_STEERING_ANGLE_DEGREES',
      'missing_bridge': ['SOURCE_BOUND_RAW_TO_NORMALIZED_APPLIED_COMMAND', 'PROVEN_MEASURED_YAW_UNIT_FRAME'],
      'physical_gain_comparison': None,
      'physical_delay_validation': None,
      'descriptive_results_recomputed': False,
      'ta_sg_executed': False,
    },
  )
  hasmodel = any(x['selected'] is not None for x in selected.values())
  ready = publish(
    'empirical-plant-readiness-v1.json',
    {
      'schema': 'EMPIRICAL_PLANT_READINESS_V1',
      'status': verdict(hasmodel, True, False),
      'holdout_state': 'HOLDOUT_EVALUATED',
      'validation_sha256': validation['receipt_sha256'],
      'signal_audit_sha256': audit['receipt_sha256'],
      'comparison_sha256': comparison['receipt_sha256'],
      'local_model_sha256': local['receipt_sha256'],
      'signal_provenance': 'TIER_B',
      'yaw_model': 'BLOCKED_UNIT_AND_FRAME_UNVERIFIED',
      'full_plant_ready': False,
      'clean_primary_evaluation_available': False,
      'ordinary_limit_unobserved': True,
      'closed_loop_identification_bias': 'UNRESOLVED_OBSERVATIONAL_OLS',
      'single_route_generalization': 'UNAVAILABLE',
      'counterfactual_use': 'NOT_ADMITTED_NO_TA_SG_EXECUTION',
      'calibration_blockers': p.BLOCKERS,
      'historical': p.policy()['historical'],
      'composition_recommendation': 'COMPOSITION_NOT_RECOMMENDED',
      'composition_authorization': 'NOT_AUTHORIZED',
      'candidate_search': 'NOT_AUTHORIZED',
      'frozen_candidate_evaluation': 'NOT_AUTHORIZED',
      'sealed_reference': 'NOT_GENERATED',
      'vehicle': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
    },
  )
  print('DONE', ready['status'], ready['receipt_sha256'], flush=True)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--private-store', required=True)
  parser.add_argument('--recorded-source', required=True)
  args = parser.parse_args()
  run(args.private_store, args.recorded_source)


if __name__ == '__main__':
  main()
