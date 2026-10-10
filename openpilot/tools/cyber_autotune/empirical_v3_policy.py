"""Retrospective V3 authority; immutable V2 evidence supplies the exact route set."""

from pathlib import Path
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_execution as prior
from openpilot.tools.cyber_autotune import empirical_v2_policy as v2
from openpilot.tools.cyber_autotune import empirical_v2_publication as old

CODE = ('empirical_v3_policy.py', 'empirical_v3_cache.py', 'empirical_v3_models.py', 'empirical_v3_generation.py')
BINS = ('LOW', 'MEDIUM', 'HIGH')


def inputs():
  return old.load()


def routes():
  split = inputs()['empirical-plant-v2-train-dev-split-v1.json']
  v2.validate_split(split)
  result = sorted((x for x in split['routes'] if x['role'] == 'TRAIN'), key=lambda x: x['route_id'])
  if len(result) != 2 or len({x['route_id'] for x in result}) != 2:
    raise ValueError('EXACT_TWO_V2_TRAIN_ROUTES_REQUIRED')
  for key in ('semantic_class_id', 'full_carparams_sha256', 'empirical_profile_sha256', 'source_commit', 'adapter_sha256'):
    if len({x[key] for x in result}) != 1:
      raise ValueError('V3_SOURCE_PROFILE_ADAPTER_CONFLICT')
  return result


def require_route(rid):
  result = next((x for x in routes() if x['route_id'] == rid), None)
  if result is None:
    raise ValueError('EXACT_TWO_ROUTE_V3_ALLOWLIST')
  return result


def code_identity():
  return {**v2.code_identity(), **{name: p.sha(Path(__file__).with_name(name).read_bytes()) for name in CODE}}


def policy():
  public = inputs()
  split = public['empirical-plant-v2-train-dev-split-v1.json']
  excluded = next(x for x in split['routes'] if x['role'] == 'DEVELOPMENT')
  return p.seal(
    {
      'schema': 'EMPIRICAL_PLANT_V3_ROUTE_CV_POLICY_V1',
      'baseline': '2c3bdad7d66a62d0de4dbf91a97f1603e8030330',
      'limitation': 'RETROSPECTIVE_MODEL_DEVELOPMENT',
      'created_after_v2_zero_development_support_known': True,
      'v2_inputs': old.PINS,
      'routes': routes(),
      'route_set_sha256': p.sha(p.canonical(routes())),
      'excluded_context': {'route_id': excluded['route_id'], 'state': 'V2_ZERO_SUPPORT_DEVELOPMENT_CONTEXT_ONLY'},
      'source_equivalence_sha256': split['source_equivalence_sha256'],
      'minimum_development_rows': 201,
      'family_policy': p.family_policy(),
      'timebase_policy': p.alignment_policy(),
      'mask_policy': p.policy(),
      'metric_policy': p.metric_policy(),
      'yaw_policy': v2.policy()['yaw_policy'],
      'fold_assignment': 'TWO_WHOLE_ROUTES_EXACT_INVERSION_NO_RANDOMNESS',
      'selection': ['WORST_ROUTE_DEVELOPMENT_RMSE', 'EQUAL_ROUTE_ARITHMETIC_MEAN_RMSE', 'LOWER_PARAMETER_COUNT', 'FAMILY_LEXICAL', 'LOWER_DELAY'],
      'sample_weighted_metrics': 'SUPPORTING_ONLY',
      'directional_gate': {
        'required_primary_scopes': ['one_step', 'endpoint_100'],
        'each_fold': 'FINITE_STABLE_MODEL_AND_COMMON_SUPPORT_201',
        'hold_last': {'RMSE': 'STRICTLY_LOWER', 'MAE': 'NO_HIGHER', 'P95_ABS': 'NO_HIGHER'},
        'zero_static': {'RMSE': 'NO_HIGHER', 'MAE': 'NO_HIGHER', 'P95_ABS': 'NO_HIGHER'},
        'all_endpoints': 'POSITIVE_SUPPORT_FINITE_ALL_REFERENCES_SAME_COUNT',
        'coverage': 'EXACT_SHARED_ORIGINS_NO_MODEL_ONLY_MASK',
        'threshold': 'NO_PERCENTAGE_OR_ABSOLUTE_EFFECT_THRESHOLD',
      },
      'yaw_admission': 'EACH_ROUTE_EXISTING_CONSERVATIVE_ADMISSION_PLUS_BOTH_FOLD_SAME_HYPOTHESIS_AXIS_SIGN_LAG',
      'yaw_support': 'EACH_FOLD_COMMON_DEVELOPMENT_ROWS_201',
      'final_refit': 'ONLY_DIRECTIONAL_GATE_PASS_SAME_STRUCTURE_TWO_ROUTE_POOLED_ONCE_NO_DEVELOPMENT_METRICS',
      'solver': 'NUMPY_LSTSQ_RCOND_NONE_FLOAT64_SINGLE_THREAD_BLAS',
      'randomness': 'NONE',
      'private_arrays': 'NPY_EXACT_BYTES_ATOMIC_NO_OVERWRITE',
      'code_sha256': code_identity(),
      'stage_c': 'STAGE_C_PENDING_FUTURE_HOLDOUT',
      'holdout_opening_allowed': False,
      'future_holdout': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
      'privacy': 'AGGREGATES_ONLY_NO_COEFFICIENTS_TRACES_PATHS_TIMESTAMPS',
      'calibration_blockers': p.BLOCKERS,
    }
  )


def folds():
  a, b = [x['route_id'] for x in routes()]
  return p.seal(
    {
      'schema': 'EMPIRICAL_PLANT_V3_FOLDS_V1',
      'policy_sha256': policy()['receipt_sha256'],
      'folds': [{'fold': 'FOLD_A', 'train_route': a, 'development_route': b}, {'fold': 'FOLD_B', 'train_route': b, 'development_route': a}],
      'old_routes_holdout_allowed': False,
    }
  )


def freeze(store):
  store = Path(store)
  p.persist(store / 'policy.json', policy())
  p.persist(store / 'folds.json', folds())


def require_frozen(store):
  row = prior.read(Path(store) / 'policy.json')
  if row != policy() or prior.read(Path(store) / 'folds.json') != folds():
    raise ValueError('V3_FROZEN_POLICY_CODE_OR_INPUT_DRIFT')
  return row
