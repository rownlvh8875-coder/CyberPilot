"""Read only selected V3 derivatives after a persisted policy. No raw-log API."""

import argparse
import io
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_execution as prior
from openpilot.tools.cyber_autotune import empirical_v3_publication as old
from openpilot.tools.cyber_autotune import empirical_stage_a_regime as r
from openpilot.tools.cyber_autotune.empirical_v3_models import save_array
from openpilot.tools.cyber_autotune.empirical_v2_execution import private_store
from openpilot.tools.cyber_autotune.empirical_v3_cache import distinct_stores, tree_identity

COMMIT = '18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29'
SOURCE_FILES = {
  'dbc': ('opendbc_repo/opendbc/dbc/hyundai_kia_generic.dbc', '1590039abb51cbfc3dc8ab4151ab78e7f549088fec878480ab4d6f850b18898a'),
  'carstate': ('opendbc_repo/opendbc/car/hyundai/carstate.py', '018ba9c239f8ab378de26354e3dd9c7eafe40ac513be1213d38f59a4c3a9e374'),
  'schema': ('opendbc_repo/opendbc/car/car.capnp', 'db5444005dcff5fdbbecf617ea031eb90852e51a848a9d832a02756ddc6bc024'),
}
DBC_DEFINITION = 'SG_ SAS_Angle : 0|16@1- (0.1,0.0) [-3276.8|3276.7] "Deg"'
ASSIGNMENT = 'ret.steeringAngleDeg = cp.vl["SAS11"]["SAS_Angle"]'
SCHEMA_FIELD = 'steeringAngleDeg @7 :Float32;'
CODE = ('empirical_stage_a_attribution.py', 'empirical_stage_a_regime.py')


def parse_dbc(line):
  match = re.search(r'SG_ SAS_Angle\s*:\s*(\d+)\|(\d+)@(\d)([+-])\s*\(([^,]+),([^)]+)\)\s*\[([^|]+)\|([^]]+)\]\s*"([^"]*)"', line)
  if not match:
    raise ValueError('EXACT_SOURCE_STEERING_SIGNAL_REQUIRED')
  start, length, endian, sign, factor, offset, low, high, unit = match.groups()
  if (int(start), int(length), int(endian), sign, float(factor), float(offset), unit) != (0, 16, 1, '-', 0.1, 0.0, 'Deg'):
    raise ValueError('SOURCE_QUANTIZATION_CONFLICT')
  return {
    'bit_start': int(start),
    'bit_length': int(length),
    'byte_order': 'LITTLE_ENDIAN',
    'signed': True,
    'step_deg': float(factor),
    'offset_deg': float(offset),
    'declared_range_deg': [float(low), float(high)],
    'declared_unit': unit,
    'sign': 1,
  }


def source_contract():
  return p.seal(
    {
      'schema': 'EMPIRICAL_STEERING_QUANTIZATION_SOURCE_CONTRACT_V1',
      'repository': 'https://github.com/ajouatom/openpilot',
      'commit': COMMIT,
      'license_sha256': '716ce815a0467219c59ec2433e6bce7f32efc45240725c6d3141a52b111d2558',
      **{role: {'path': path, 'file_sha256': digest} for role, (path, digest) in SOURCE_FILES.items()},
      'signal': 'SAS11.SAS_Angle',
      'signal_definition': DBC_DEFINITION,
      'source_slice_sha256': p.sha(DBC_DEFINITION.encode()),
      'carstate_assignment': ASSIGNMENT,
      'carstate_slice_sha256': p.sha(ASSIGNMENT.encode()),
      'schema_field': SCHEMA_FIELD,
      'schema_slice_sha256': p.sha(SCHEMA_FIELD.encode()),
      'storage': 'Float32',
      'carstate_conversion': 'DIRECT_COPY_LEGACY_NON_CANFD_NO_SIGN_OR_OFFSET_CHANGE',
      **parse_dbc(DBC_DEFINITION),
    }
  )


def audit_source(repo):
  facts = source_contract()
  for role, (path, digest) in SOURCE_FILES.items():
    raw = subprocess.check_output(['git', '-C', str(repo), 'show', f'{COMMIT}:{path}'])
    if p.sha(raw) != digest:
      raise ValueError('EXACT_RECORDED_SOURCE_HASH_CONFLICT')
    text = raw.decode()
    needle = {'dbc': DBC_DEFINITION, 'carstate': ASSIGNMENT, 'schema': SCHEMA_FIELD}[role]
    if needle not in text:
      raise ValueError('SOURCE_QUANTIZATION_SLICE_CONFLICT')
  if any(x['source_commit'] != COMMIT for x in old.load()['empirical-plant-v3-route-cv-policy-v1.json']['routes']):
    raise ValueError('SOURCE_CLASS_ROUTE_CONFLICT')
  return facts


def selected():
  public = old.load()
  table = public['empirical-plant-v3-stage-a-cv-results-v1.json']['bins']
  selection = public['empirical-plant-v3-stage-a-selection-v1.json']['bins']
  rows = []
  for speed in ('LOW', 'MEDIUM', 'HIGH'):
    c = selection[speed]['selected_structure']
    if c['family'] != 'ARX1' or c['delay_samples'] != 5:
      raise ValueError('FROZEN_SELECTED_ARX1_DELAY5_ONLY')
    found = [x for x in table[speed]['candidates'] if x['config'] == c]
    if len(found) != 1:
      raise ValueError('EXACT_SELECTED_STRUCTURE_REQUIRED')
    for fold in found[0]['folds']:
      rows.append({'speed_bin': speed, 'config': c, **fold})
  return rows


def policy():
  public = old.load()
  v3 = public['empirical-plant-v3-route-cv-policy-v1.json']
  facts = source_contract()
  return p.seal(
    {
      'schema': 'EMPIRICAL_STAGE_A_REGIME_POLICY_V1',
      'baseline': '9d887fc8a1233c16e545e434974faa7a7da314b2',
      'v3_public_inputs': old.PINS,
      'v3_policy_sha256': v3['receipt_sha256'],
      'v3_fold_sha256': public['empirical-plant-v3-folds-v1.json']['receipt_sha256'],
      'v3_result_sha256': public['empirical-plant-v3-readiness-v1.json']['result_sha256'],
      'selected': selected(),
      'source_equivalence_sha256': v3['source_equivalence_sha256'],
      'routes': v3['routes'],
      'speed_bins': v3['mask_policy']['speed_bins'],
      'metric_policy_sha256': v3['metric_policy']['receipt_sha256'],
      'source_quantization_sha256': facts['receipt_sha256'],
      'exact_dbc_sha256': facts['dbc']['file_sha256'],
      'executor_sha256': {name: p.sha(Path(__file__).with_name(name).read_bytes()) for name in CODE},
      'privacy_policy_sha256': p.sha(b'AGGREGATES_ONLY_NO_RAW_VALUES_TRACES_COEFFICIENTS_PATHS_TIMESTAMPS'),
      'numeric_raw_opening': 'PROHIBITED',
      'v2_numeric_cache_opening': 'PROHIBITED',
      'allowed_arrays': ['SELECTED_DEVELOPMENT_DESIGN', 'SELECTED_DEVELOPMENT_ONE_STEP'],
      'grid_tolerance': 'EXACT_FLOAT32_GRID_OR_HALF_ADJACENT_FLOAT32_ULP_NO_TUNED_EPSILON',
      'target_grid_conflict': 'BLOCK_ARCHITECTURE_REVIEW_DO_NOT_ROUND_TARGETS',
      'outcome_partition': list(r.PARTITION) + ['TARGET_OFF_GRID_OR_SUBQUANTUM_CHANGE'],
      'large_transition': 'SOURCE_GRID_ORDINAL_DELTA_AT_LEAST_TWO_SAME_AS_MULTI_QUANTUM',
      'outcome_overlaps': ['TARGET_SIGN_REVERSAL', 'TARGET_LARGE_TRANSITION'],
      'causal_conditions': r.availability(),
      'causal_boundary': r.CAUSAL_BOUNDARY,
      'causal_condition_operator': 'ABS_FROZEN_PREDICTION_MINUS_PAST_MEASUREMENT_GE_SOURCE_HALF_QUANTUM',
      'source_clock_history': 'NO_ADJACENT_ROW_INFERENCE_WITHOUT_RUN_BOUNDARY_MAP',
      'rule_combination_search': False,
      'optimized_thresholds': False,
      'prediction_quantization': False,
      'win_tie_loss': 'EXACT_ABSOLUTE_ERROR_COMPARISON_NO_TOLERANCE',
      'paired_columns': [
        'ARX_ABS',
        'ARX_SQUARED',
        'HOLD_ABS',
        'HOLD_SQUARED',
        'ABS_DELTA',
        'SQUARED_DELTA',
        'TARGET_DELTA',
        *list(r.PARTITION),
        'TARGET_OFF_GRID_OR_SUBQUANTUM_CHANGE',
        'TARGET_SIGN_REVERSAL',
        'TARGET_LARGE_TRANSITION',
        r.CAUSAL_BOUNDARY,
      ],
      'unavailable_paired_columns': [
        'CURRENT_RAW_COMMAND_DELTA',
        'CURRENT_NORMALIZED_COMMAND_DELTA',
        'CURRENT_MEASUREMENT_DELTA',
        'CURRENT_STEERING_RATE',
        'ACTIVE_INTERVENTION_STATE',
      ],
      'primary_interpretation': 'EQUAL_ROUTE_PER_SPEED_BIN',
      'pooled_statistics': 'SUPPORTING_ONLY',
      'contribution': 'SUM_REGIME_ERROR_DELTA_DIVIDE_ALL_PAIRED_N_RMSE_DIVIDE_GLOBAL_RMSE_SUM_ZERO_DENOMINATOR_ZERO',
      'hypotheses': {
        'H1': 'UNCHANGED_MAE_CONTRIBUTION_EXCEEDS_OTHER_POSITIVE_CONTRIBUTIONS_AND_SMALL_ERROR_EXCEEDS_OTHER_UNCHANGED_ERROR_EACH_ROUTE_BIN',
        'H2': 'MULTI_QUANTUM_NEGATIVE_MSE_CONTRIBUTION_EXCEEDS_OTHER_NEGATIVE_CONTRIBUTIONS_EACH_ROUTE_BIN',
        'H3': 'HALF_QUANTUM_CONDITION_SEPARATES_ALL_THREE_METRICS_EACH_ROUTE_BIN_WITH_201_SUPPORT_BOTH_BRANCHES',
        'H4': 'ONLY_NONCAUSAL_UNRESOLVED_WHEN_A_THROUGH_E_UNAVAILABLE',
        'H5': 'QUANTIZATION_DOMINANCE_NOT_SUPPORTED',
        'H6': 'OBSERVED_OPPOSITE_SIGNS_ACROSS_ROUTE_OR_SPEED_SUPPORT_INSUFFICIENCY_DISCLOSED_SEPARATELY',
      },
      'architecture_readiness': 'REVIEW_ONLY_NEVER_MODEL_ADMISSION',
      'minimum_causal_diagnostic_support': 201,
      'threshold': 'NO_PERFORMANCE_THRESHOLD',
      'environment': {
        'python': sys.version.split()[0],
        'numpy': np.__version__,
        'platform': platform.system(),
        'threads': 1,
        'solver': 'NONE_NO_FITTING',
        'rng': 'NONE',
      },
      'future_holdout': 'CLOSED_MISSING_ADMISSIBLE_MODEL',
      'stage_b': 'STAGE_B_SIGNAL_ADMISSION_BLOCKED',
      'calibration_blockers': p.BLOCKERS,
    }
  )


def freeze(store, repo, v3_store):
  v3_store, store = distinct_stores(v3_store, store)
  p.persist(store / 'v3-integrity-before.json', p.seal({'schema': 'ATTRIBUTION_V3_PRIVATE_PRESERVATION_V1', 'tree_sha256': tree_identity(v3_store)}))
  p.persist(Path(store) / 'source-contract.json', audit_source(repo))
  p.persist(Path(store) / 'policy.json', policy())


def require_frozen(store):
  store = private_store(store)
  row = prior.read(Path(store) / 'policy.json')
  if row != policy() or prior.read(Path(store) / 'source-contract.json') != source_contract():
    raise ValueError('ATTRIBUTION_FROZEN_POLICY_SOURCE_OR_CODE_DRIFT')
  return row


def load_array(path, digest):
  path = Path(path)
  if any(x.is_symlink() for x in (path, *path.parents)):
    raise ValueError('NO_SYMLINK_DERIVATIVE')
  raw = path.read_bytes()
  if p.sha(raw) != digest:
    raise ValueError('DERIVATIVE_HASH_MISMATCH')
  return np.load(io.BytesIO(raw), allow_pickle=False)


def validate_pair(design, one):
  if design.shape != (len(one), 3) or one.ndim != 2 or one.shape[1] != 5:
    raise ValueError('EXACT_SELECTED_DERIVATIVE_SCHEMA')
  if not np.array_equal(design[:, 0], one[:, 3]):
    raise ValueError('PAST_MEASUREMENT_MISMATCH')


def validate_public(row):
  old.validate_public(row)
  forbidden = {'targets', 'commands', 'paired_rows', 'numeric_values', 'raw_route_path'}

  def walk(x):
    if isinstance(x, dict):
      if set(x) & forbidden:
        raise ValueError('PRIVATE_ATTRIBUTION_VALUES_FORBIDDEN')
      for v in x.values():
        walk(v)
    elif isinstance(x, list):
      for v in x:
        walk(v)

  walk(row)
  return row


def run(store, v3_store):
  v3_store, store = distinct_stores(v3_store, store)
  pol = require_frozen(store)
  before = tree_identity(v3_store)
  if before != prior.read(store / 'v3-integrity-before.json')['tree_sha256']:
    raise ValueError('V3_PRIVATE_TREE_DRIFT')
  if any(os.environ.get(k) != '1' for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS')):
    raise ValueError('SINGLE_THREAD_ENVIRONMENT_REQUIRED')
  old_result = prior.read(v3_store / 'results.json')
  if old_result['receipt_sha256'] != pol['v3_result_sha256']:
    raise ValueError('V3_PRIVATE_RESULT_DRIFT')
  rows = []
  for expected in selected():
    speed, fold = expected['speed_bin'], expected['fold']
    folder = v3_store / 'folds' / 'STAGE_A' / speed / 'ARX1-5' / fold
    receipt = prior.read(folder / 'receipt.json')
    if receipt['receipt_sha256'] != expected['private_result_sha256'] or receipt['config'] != expected['config']:
      raise ValueError('SELECTED_PRIVATE_FOLD_IDENTITY_DRIFT')
    for key in ('train_route', 'development_route', 'fold'):
      if receipt[key] != expected[key]:
        raise ValueError('FOLD_ROUTE_DRIFT')
    design = load_array(folder / 'design.npy', expected['array_sha256']['design'])
    one = load_array(folder / 'one_step.npy', expected['array_sha256']['one_step'])
    validate_pair(design, one)
    facts = source_contract()
    result, derivative = r.analyze(one, facts['step_deg'], facts['offset_deg'])
    if result['all']['count'] != expected['evaluation']['coverage']['one_step']['valid']:
      raise ValueError('EXACT_PAIRED_SUPPORT_DRIFT')
    for name, key in (('arx', 'model'), ('hold_last', 'HOLD_LAST_OUTPUT')):
      if result['all'][name] != expected['evaluation']['one_step'][key]:
        raise ValueError('FROZEN_METRIC_RECONSTRUCTION_DRIFT')
    digest = save_array(store / 'paired' / speed / (fold + '.npy'), derivative)
    rows.append(
      {
        'route_id': expected['development_route'],
        'fold': fold,
        'speed_bin': speed,
        'private_fold_sha256': receipt['receipt_sha256'],
        'paired_derivative_sha256': digest,
        **result,
      }
    )
  decision = r.adjudicate(rows)
  after = tree_identity(v3_store)
  if before != after:
    raise ValueError('V3_PRIVATE_TREE_MUTATED')
  result = p.seal(
    {
      'schema': 'EMPIRICAL_STAGE_A_REGIME_RESULTS_V1',
      'policy_sha256': pol['receipt_sha256'],
      'route_fold_speed_results': rows,
      'equal_route_by_speed': {b: r.aggregate([x for x in rows if x['speed_bin'] == b]) for b in ('LOW', 'MEDIUM', 'HIGH')},
      'decision': decision,
      'v3_private_before_sha256': before,
      'v3_private_after_sha256': after,
      'v3_arrays_reused': True,
      'raw_payloads_opened': False,
      'model_refit': 'NOT_RUN',
    }
  )
  p.persist(store / 'results.json', result)
  return result


def validate_repeatability(row, result_sha):
  if row.get('runs') != 2 or row.get('exact_repeatability') is not True or row.get('result_sha256') != result_sha:
    raise ValueError('ATTRIBUTION_REPEATABILITY_RECEIPT_MISMATCH')
  return row


def outputs(store):
  store = Path(store)
  pol = require_frozen(store)
  result = prior.read(store / 'results.json')
  if result['policy_sha256'] != pol['receipt_sha256']:
    raise ValueError('ATTRIBUTION_PUBLIC_POLICY_DRIFT')
  validate_repeatability(prior.read(store / 'repeatability.json'), result['receipt_sha256'])
  rows = result['route_fold_speed_results']
  quant = p.seal(
    {
      'schema': 'EMPIRICAL_STAGE_A_QUANTIZATION_AUDIT_V1',
      'source': source_contract(),
      'status': 'STEERING_MEASUREMENT_QUANTIZATION_CONFIRMED',
      'target_grid_status': 'CONFLICT' if any(x['target_grid']['off_grid_count'] for x in rows) else 'CONSISTENT',
      'routes': [
        {
          'route_id': x['route_id'],
          'fold': x['fold'],
          'speed_bin': x['speed_bin'],
          **{k: x[k] for k in ('target_grid', 'past_measurement_grid', 'arx_prediction_grid', 'quantization')},
        }
        for x in rows
      ],
      'policy_sha256': pol['receipt_sha256'],
    }
  )
  causal = p.seal(
    {
      'schema': 'EMPIRICAL_STAGE_A_CAUSAL_SEPARATOR_AUDIT_V1',
      'availability': r.availability(),
      'rows': [{'route_id': x['route_id'], 'fold': x['fold'], 'speed_bin': x['speed_bin'], 'conditions': x['causal']} for x in rows],
      'route_consistent_separator_supported': result['decision'].get('causal_hybrid_review_possible', False),
      'outcome_gate_allowed': False,
      'combination_search': 'NOT_RUN',
      'policy_sha256': pol['receipt_sha256'],
    }
  )
  historical = old.load()['empirical-plant-v3-readiness-v1.json']
  readiness = p.seal(
    {
      'schema': 'EMPIRICAL_STAGE_A_ATTRIBUTION_READINESS_V1',
      **result['decision'],
      'model_admission': 'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT',
      'future_holdout': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
      'package_status': 'CLOSED_MISSING_ADMISSIBLE_MODEL',
      'holdout_opening': 'HOLDOUT_OPENING_CLOSED',
      'stage_b': 'STAGE_B_SIGNAL_ADMISSION_BLOCKED',
      'ta_sg_execution': 'NOT_RUN',
      'stage_c': 'NOT_RUN',
      'fitting': 'NOT_RUN',
      'model_selection': 'NOT_RUN',
      'threshold_search': 'NOT_RUN',
      'historical': historical['historical'],
      'calibration_blockers': p.BLOCKERS,
      'sealed_reference': 'NOT_GENERATED',
      'vehicle': historical['vehicle'],
      'policy_sha256': pol['receipt_sha256'],
      'result_sha256': result['receipt_sha256'],
      'repeatability_sha256': prior.read(store / 'repeatability.json')['receipt_sha256'],
    }
  )
  outputs = {
    'empirical-stage-a-regime-policy-v1.json': pol,
    'empirical-stage-a-quantization-audit-v1.json': quant,
    'empirical-stage-a-regime-results-v1.json': result,
    'empirical-stage-a-causal-separator-audit-v1.json': causal,
    'empirical-stage-a-attribution-readiness-v1.json': readiness,
    'empirical-stage-a-repeatability-v1.json': prior.read(store / 'repeatability.json'),
  }
  if result['decision']['verdict'] in ('QUANTIZATION_AWARE_OBSERVATION_REVIEW_POSSIBLE', 'CAUSAL_HYBRID_REVIEW_POSSIBLE'):
    outputs['empirical-stage-a-v4-architecture-contract-v1.json'] = r.architecture_contract(result['decision']['verdict'], pol['receipt_sha256'])
  for row in outputs.values():
    validate_public(row)
  return outputs


def main():
  cli = argparse.ArgumentParser(description=__doc__)
  cli.add_argument('mode', choices=('freeze', 'run', 'publish'))
  cli.add_argument('--store', type=Path, required=True)
  cli.add_argument('--v3-store', type=Path, required=True)
  args = cli.parse_args()
  distinct_stores(args.v3_store, args.store)
  if args.mode == 'freeze':
    freeze(args.store, Path(__file__).resolve().parents[3], args.v3_store)
  elif args.mode == 'run':
    first = run(args.store, args.v3_store)
    second = run(args.store, args.v3_store)
    if first != second:
      raise ValueError('ATTRIBUTION_EXACT_REPEATABILITY_FAILURE')
    p.persist(
      args.store / 'repeatability.json',
      p.seal(
        {
          'schema': 'EMPIRICAL_STAGE_A_ATTRIBUTION_REPEATABILITY_V1',
          'runs': 2,
          'exact_repeatability': True,
          'result_sha256': first['receipt_sha256'],
          'compared': ['REGIME_ASSIGNMENTS', 'PRIVATE_PAIRED_BYTES', 'COUNTS', 'PAIRED_METRICS', 'CONTRIBUTIONS', 'CAUSAL_AUDIT', 'VERDICT', 'RECEIPT_SHA'],
        }
      ),
    )
    print(first['decision'])
  else:
    for name, row in outputs(args.store).items():
      p.persist(p.PUBLIC / name, row)
    print('aggregate publication complete')


if __name__ == '__main__':
  main()
