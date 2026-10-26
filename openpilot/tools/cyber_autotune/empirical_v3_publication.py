"""Public V3 receipts contain aggregate development evidence, never fitted coefficients."""

import copy
from pathlib import PureWindowsPath
from pathlib import Path
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_execution as prior
from openpilot.tools.cyber_autotune import empirical_v3_policy as v

PINS = {
  'empirical-plant-v3-folds-v1.json': '0b4e62a8e75519edaab900a274878daaac0893cfe9d903fd840a52c825da60ee',
  'empirical-plant-v3-readiness-v1.json': '39eb4547a7868dc79ae5b94b053793f6650e7b1686e9bde6ed767d220347758a',
  'empirical-plant-v3-repeatability-v1.json': '4ff9368150dad99d4d03c43fc3390d0db14eae10d19926b2f8e45eccea992143',
  'empirical-plant-v3-route-coverage-v1.json': '208c67899cd0577b571848ae5f2ae48e8fc0635b36d20069c7507be003e92e75',
  'empirical-plant-v3-route-cv-policy-v1.json': '5c47b1a833dad3803f94e822ff9a45f1b0c6bfd6ea6b75299375415a6085f5f8',
  'empirical-plant-v3-stage-a-cv-results-v1.json': '498db371afc8fa645db7b382ba602f2bd81bea94202ad1f794f0a67e14588a0c',
  'empirical-plant-v3-stage-a-selection-v1.json': '997f458ce3a0ad8101cf678c17374a378007b5e16408c433e7848aa2ba9c0478',
  'empirical-plant-v3-yaw-admission-v1.json': '63b3b6e752a4c1da4d858ba6091c486335c2c93914f2e5315bf0caeec7a33f43',
  'future-empirical-plant-v3-holdout-package-v1.json': '3a369b528162f1ea5aaaa504af24ce7e3fea4a0c1d5126947806e30fcf009418',
}


def outputs(store):
  store = Path(store)
  policy = v.require_frozen(store)
  result = prior.read(store / 'results.json')
  package = prior.read(store / 'holdout-package.json')
  integrity = prior.read(store / 'cache-integrity.json')
  repeat = prior.read(store / 'repeatability.json')
  if (
    result['policy_sha256'] != policy['receipt_sha256']
    or result['folds_sha256'] != v.folds()['receipt_sha256']
    or result['integrity_sha256'] != integrity['receipt_sha256']
    or result['v2_private_before_sha256'] != result['v2_private_after_sha256']
    or package['result_sha256'] != result['receipt_sha256']
    or not repeat['exact_repeatability']
    or repeat['result_sha256'] != result['receipt_sha256']
    or repeat['package_sha256'] != package['receipt_sha256']
  ):
    raise ValueError('V3_PUBLIC_CHAIN_DRIFT')
  public = {
    'empirical-plant-v3-route-cv-policy-v1.json': policy,
    'empirical-plant-v3-folds-v1.json': v.folds(),
    'empirical-plant-v3-route-coverage-v1.json': p.seal(
      {
        'schema': 'EMPIRICAL_PLANT_V3_ROUTE_COVERAGE_V1',
        'policy_sha256': policy['receipt_sha256'],
        'routes': [{'route_id': x['route_id'], 'coverage': x['coverage'], 'bridge': x['bridge']} for x in integrity['routes']],
        'v2_cache_unchanged': True,
        'raw_payload_redecoded': False,
        'numeric_route_count': 2,
      }
    ),
    'empirical-plant-v3-yaw-admission-v1.json': p.seal(
      {'schema': 'EMPIRICAL_PLANT_V3_YAW_ADMISSION_V1', **result['yaw_admission'], 'policy_sha256': policy['receipt_sha256']}
    ),
    'future-empirical-plant-v3-holdout-package-v1.json': package,
    'empirical-plant-v3-repeatability-v1.json': repeat,
  }
  for stage, key in (('STAGE_A', 'stage_a'), ('STAGE_B', 'stage_b')):
    table = result[key]
    if not table:
      continue
    # Each result contains aggregate metrics and private array/coefficient hashes only.
    public['empirical-plant-v3-' + stage.lower().replace('_', '-') + '-cv-results-v1.json'] = p.seal(
      {
        'schema': 'EMPIRICAL_PLANT_V3_' + stage + '_CV_RESULTS_V1',
        'bins': {b: {'candidates': copy.deepcopy(x['candidates'])} for b, x in table.items()},
        'policy_sha256': policy['receipt_sha256'],
        'interpretation': 'RETROSPECTIVE_MODEL_DEVELOPMENT',
      }
    )
    public['empirical-plant-v3-' + stage.lower().replace('_', '-') + '-selection-v1.json'] = p.seal(
      {
        'schema': 'EMPIRICAL_PLANT_V3_' + stage + '_SELECTION_V1',
        'bins': {
          b: {
            'state': x['selection']['state'],
            'selected_structure': x['selection']['selected']['config'] if x['selection']['selected'] else None,
            'aggregation': x['selection']['selected']['aggregation'] if x['selection']['selected'] else None,
            'directional_gate': x['selection']['gate'],
            'final_model_sha256': x['final_model_sha256'],
          }
          for b, x in table.items()
        },
        'policy_sha256': policy['receipt_sha256'],
        'no_pooled_refit_development_metric': True,
      }
    )
    if result['models'][stage]:
      public['empirical-plant-v3-' + stage.lower().replace('_', '-') + '-model-freeze-v1.json'] = p.seal(
        {
          'schema': 'EMPIRICAL_PLANT_V3_' + stage + '_MODEL_FREEZE_V1',
          'models': result['models'][stage],
          'state': stage + '_MODEL_FROZEN_AWAITING_FUTURE_HOLDOUT',
          'development_metrics': None,
          'selection_evidence': 'TWO_FOLD_ROUTE_CV_ONLY',
          'policy_sha256': policy['receipt_sha256'],
        }
      )
  historical = v.inputs()['empirical-plant-v2-train-dev-readiness-v1.json']['historical']
  public['empirical-plant-v3-readiness-v1.json'] = p.seal(
    {
      'schema': 'EMPIRICAL_PLANT_V3_READINESS_V1',
      'status': 'EMPIRICAL_PLANT_V3_ROUTE_CV_COMPLETE',
      'limitation': 'RETROSPECTIVE_MODEL_DEVELOPMENT',
      'stage_a_states': {b: x['selection']['state'] for b, x in result['stage_a'].items()},
      'stage_b_state': 'STAGE_B_MODEL_FROZEN_AWAITING_FUTURE_HOLDOUT'
      if result['models']['STAGE_B']
      else ('STAGE_B_SIGNAL_ADMISSION_BLOCKED' if not result['yaw_admission']['admitted'] else 'STAGE_B_MODEL_SELECTION_BLOCKED'),
      'admissible_models': result['models'],
      'model_admission': 'MODELS_FROZEN_AWAITING_FUTURE_HOLDOUT' if result['models']['STAGE_A'] else 'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT',
      'future_holdout': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
      'one_time_opening_state': 'CLOSED',
      'holdout_opened': False,
      'holdout_evaluated': False,
      'plant_ready': False,
      'v2_artifacts_immutable': True,
      'stage_c': 'NOT_RUN',
      'stage_c_state': 'STAGE_C_PENDING_FUTURE_HOLDOUT',
      'ta_sg_execution': 'NOT_RUN',
      'candidate_evaluation': 'NOT_RUN',
      'historical': historical,
      'calibration_blockers': p.BLOCKERS,
      'sealed_reference': 'NOT_GENERATED',
      'vehicle': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
      'policy_sha256': policy['receipt_sha256'],
      'result_sha256': result['receipt_sha256'],
      'package_sha256': package['receipt_sha256'],
    }
  )
  for row in public.values():
    validate_public(row)
  return public


FORBIDDEN = {
  'coefficients',
  'static_gain',
  'singular_values',
  'source_key',
  'location',
  'grid_time_ns',
  'command_raw',
  'angle_deg',
  'yaw_raw',
  'gyro_options',
  'raw_timestamps',
  'predictions',
  'design_matrix',
  'residuals',
}


def validate_public(row):
  p.verify(row)

  def visit(value):
    if isinstance(value, dict):
      if set(value) & FORBIDDEN:
        raise ValueError('PRIVATE_V3_FIELD_PUBLICATION_FORBIDDEN')
      for child in value.values():
        visit(child)
    elif isinstance(value, list):
      for child in value:
        visit(child)
    elif isinstance(value, str) and (value.startswith('/') or PureWindowsPath(value).is_absolute()):
      raise ValueError('PRIVATE_PATH_PUBLICATION_FORBIDDEN')

  visit(row)
  return row


def load():
  v.inputs()
  if not PINS:
    raise ValueError('V3_PUBLIC_RECEIPTS_NOT_PINNED')
  outputs = {}
  for name, digest in PINS.items():
    row = validate_public(prior.read(p.PUBLIC / name))
    if row['receipt_sha256'] != digest:
      raise ValueError('V3_PUBLIC_RECEIPT_DRIFT')
    outputs[name] = row
  return outputs
