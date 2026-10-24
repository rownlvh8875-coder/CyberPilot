"""Policy and immutable cache identities; freeze before aligned-cache decoding."""
from pathlib import Path
import sys
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_execution as read
from openpilot.tools.cyber_autotune import empirical_v3_publication as v3
from openpilot.tools.cyber_autotune import empirical_v3_policy as v
from openpilot.tools.cyber_autotune import empirical_stage_a_publication as attribution
from openpilot.tools.cyber_autotune import empirical_stage_a_attribution as selected
from openpilot.tools.cyber_autotune import empirical_causal_analysis as c
from openpilot.tools.cyber_autotune.empirical_v3_cache import distinct_stores, tree_identity

CODE = ('empirical_causal_policy.py', 'empirical_causal_recovery.py', 'empirical_causal_analysis.py')
NAMES = ('v2', 'v3', 'attribution')


def stores(inputs, output):
  if set(inputs) != set(NAMES):
    raise ValueError('EXACT_THREE_INPUT_STORES')
  paths = {name: distinct_stores(path, output)[0] for name, path in inputs.items()}
  for i, name in enumerate(NAMES):
    for other in NAMES[i+1:]:
      distinct_stores(paths[name], paths[other])
  return paths, distinct_stores(paths['v2'], output)[1]


def condition_policy():
  return p.seal({'schema': 'EMPIRICAL_CAUSAL_CONDITION_POLICY_V1', 'conditions': c.DEFINITIONS,
    'minimum_per_branch_per_route_bin': c.MINIMUM, 'scopes': 6,
    'true': 'ARX_RMSE_STRICTLY_LOWER_MAE_P95_NO_HIGHER',
    'false': 'HOLD_RMSE_MAE_P95_NO_HIGHER', 'all_scopes_required': True,
    'combined_rules_allowed': False, 'threshold_search_allowed': False,
    'floating_comparison': 'EXACT_METRIC_RESULT_NO_EPSILON',
    'causal_fields': ['u[k-1]', 'u[k-2]', 'u[k-5]', 'u[k-6]', 'y[k-1]', 'y[k-2]'],
    'C6_role': 'MODEL_DERIVED_CAUSAL_ARCHITECTURE_DIAGNOSTIC',
    'normalized_command_condition': 'VERIFY_INJECTIVE_FLOAT32_RAW_DIV_409_ALIAS_NOT_INDEPENDENT_EVIDENCE',
    'selector': 'ONLY_AFTER_STRICT_PASS_EXISTING_PREDICTIONS_ONE_STEP_NO_ROLLOUT'})


def static_policy():
  pub, att = v3.load(), attribution.load()
  pol = pub['empirical-plant-v3-route-cv-policy-v1.json']
  split = v.inputs()['empirical-plant-v2-train-dev-split-v1.json']
  auth = v.inputs()['empirical-plant-v2-numeric-authorization-v1.json']
  return {
    'schema': 'EMPIRICAL_STAGE_A_CAUSAL_RECOVERY_POLICY_V1', 'baseline': '608fbd3d091a6ae0dca292152dd1bfb87e6b1ac5',
    'v2_split_sha256': split['receipt_sha256'], 'v2_numeric_authorization_sha256': auth['receipt_sha256'],
    'v3_policy_sha256': pol['receipt_sha256'],
    'v3_fold_sha256': pub['empirical-plant-v3-folds-v1.json']['receipt_sha256'],
    'v3_result_sha256': pub['empirical-plant-v3-readiness-v1.json']['result_sha256'],
    'attribution_result_sha256': att['empirical-stage-a-regime-results-v1.json']['receipt_sha256'],
    'source_equivalence_sha256': pol['source_equivalence_sha256'],
    'empirical_profile_sha256': v.routes()[0]['empirical_profile_sha256'],
    'exact_dbc_sha256': selected.source_contract()['dbc']['file_sha256'],
    'source_quantization_sha256': selected.source_contract()['receipt_sha256'],
    'routes': v.routes(), 'selected': selected.selected(),
    'selected_structure_sha256': p.sha(p.canonical([x['config'] for x in selected.selected()])),
    'private_derivative_set_sha256': p.sha(p.canonical([x['array_sha256'] for x in selected.selected()])),
    'timebase_policy': pol['timebase_policy'], 'mask_policy': pol['mask_policy'],
    'metric_policy_sha256': pol['metric_policy']['receipt_sha256'],
    'condition_policy': condition_policy(),
    'privacy_policy_sha256': p.sha(b'AGGREGATES_HASHES_ONLY_NO_ORIGINS_TIMESTAMPS_PRIVATE_VALUES'),
    'executor_sha256': {n: p.sha(Path(__file__).with_name(n).read_bytes()) for n in CODE},
    'history': 45, 'config': selected.selected()[0]['config'],
    'preexecution_repair': {'failed_policy_sha256':'2dba14f9a31115126153c6106e4ff67c46bc5324eceed24cf4661aafceac245c',
      'reason':'EXECUTOR_OMITTED_EXISTING_INTERCEPT_FIELD_STOPPED_BEFORE_DERIVATIVE_ANALYSIS',
      'causal_results_observed_before_repair':False,'conditions_thresholds_metrics_changed':False},
    'run_order': 'V2_ROUTE_RECEIPT_SEGMENT_ORDER_THEN_VALID_SAME_BIN_RUN_THEN_K_44_TO_END',
    'mapping': 'FLOAT64_DTYPE_SHAPE_C_ORDER_BYTES_EXACT_NO_TOLERANCE_NO_NEAREST_MATCH',
    'prediction_proof': 'EXISTING_COEFFICIENTS_ONLY_SAME_CONCATENATED_DESIGN_MATMUL_NO_REFIT',
    'clock': 'PUBLISH_TIME_ONLY_COMMAND_AND_CONTROL_LE_PRIOR_STATE_LE_GRID_STRICT_PRIOR_STATE_BEFORE_TARGET',
    'raw_source_integrity': 'PRIOR_V3_ATTESTATION_AND_CACHED_RECEIPT_HASHES_ONLY_NO_CURRENT_RAW_FILE_REHASH',
    'raw_logs_opening_allowed': False, 'fitting_allowed': False, 'stage_b_analysis_allowed': False,
    'rollout_allowed': False, 'holdout_opening_allowed': False,
    'source_steering_rate': 'UNAVAILABLE_NOT_PRESERVED',
    'environment': {'python':sys.version,'numpy':np.__version__,'blas_threads':1,'rng':'NONE','solver':'NONE_NO_REFIT'},
    'future_holdout': 'CLOSED_MISSING_ADMISSIBLE_MODEL', 'calibration_blockers': p.BLOCKERS,
  }


def freeze(inputs, output):
  paths, output = stores(inputs, output)
  static = static_policy()
  # Only aggregate identity receipts are decoded before the policy; aligned
  # samples and selected arrays are not deserialized here.
  integrity = read.read(paths['v3'] / 'cache-integrity.json')
  result = read.read(paths['v3'] / 'results.json')
  if result['receipt_sha256'] != static['v3_result_sha256'] or result['integrity_sha256'] != integrity['receipt_sha256']:
    raise ValueError('PINNED_V3_INTEGRITY_CHAIN_REQUIRED')
  old_attribution = read.read(paths['attribution'] / 'results.json')
  if old_attribution['receipt_sha256'] != static['attribution_result_sha256']:
    raise ValueError('PINNED_ATTRIBUTION_INPUT_REQUIRED')
  actual_trees = {name: tree_identity(path) for name,path in paths.items()}
  if actual_trees['v3'] != old_attribution['v3_private_after_sha256'] or result['v2_private_before_sha256'] != result['v2_private_after_sha256']:
    raise ValueError('HISTORICAL_PRIVATE_PRESERVATION_ATTESTATION_CONFLICT')
  if actual_trees['v2'] != result['v2_private_after_sha256']:
    raise ValueError('V2_PRIVATE_TREE_NOT_PREVIOUSLY_ATTESTED')
  bindings = [{'route_id': x['route_id'], 'route_receipt_sha256': x['route_receipt_sha256'],
               'segment_receipt_set_sha256': p.sha(p.canonical(x['segments']))} for x in integrity['routes']]
  policy = p.seal({**static, 'v2_route_bindings': bindings, 'v3_cache_integrity_sha256': integrity['receipt_sha256'],
                   'input_tree_sha256': actual_trees,
                   'numeric_cache_deserialized_before_freeze': False})
  p.persist(output / 'policy.json', policy)
  return policy


def require_frozen(inputs, output):
  paths, output = stores(inputs, output)
  pol = read.read(output / 'policy.json')
  if any(pol.get(k) != val for k, val in static_policy().items()):
    raise ValueError('FROZEN_RECOVERY_CODE_POLICY_DRIFT')
  if pol['input_tree_sha256'] != {name: tree_identity(path) for name, path in paths.items()}:
    raise ValueError('IMMUTABLE_INPUT_TREE_DRIFT')
  return paths, output, pol
