"""Publish only fixed contracts and validated aggregate S2-RI evidence."""
import argparse
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as store
from openpilot.tools.cyber_autotune import empirical_identifiability_execution as read
from openpilot.tools.cyber_autotune import empirical_identifiability_schema as historical_schema
from openpilot.tools.cyber_autotune import empirical_s2_ri_policy as policy
from openpilot.tools.cyber_autotune import empirical_s2_ri_admission as admission
from openpilot.tools.cyber_autotune import empirical_s2_ri_schema as schema


def build(root):
  root = store.safe(root)
  pol = read.read_json(root/'policy.json')
  if pol != policy.policy():
    raise ValueError('FROZEN_POLICY_EXECUTOR_DRIFT')
  a, b = (read.read_json(root/r/'results.json') for r in ('repeat-1', 'repeat-2'))
  if a != b:
    raise ValueError('TWO_EXACT_INDEPENDENT_EXECUTIONS_REQUIRED')
  for replica, result in (('repeat-1', a), ('repeat-2', b)):
    receipt = read.read_json(root/replica/'admission.json')
    schema.validate_result(result, pol, receipt)
    index = read.read_json(root/replica/'derived-index.json')
    if set(index) != {*p.FIREWALL, 'schema', 'receipt_sha256', 'segments'} or index['schema'] != 'EMPIRICAL_S2_RI_DERIVED_INDEX_V1':
      raise ValueError('EXACT_DERIVED_INDEX_REQUIRED')
    if len(index['segments']) != 154:
      raise ValueError('COMPLETE_DERIVED_ARRAY_PROOF_REQUIRED')
    admitted = {v['content_sha256']: v for v in receipt['segment_bindings']}
    if [v['content_sha256'] for v in index['segments']] != [v['content_sha256'] for v in receipt['segment_bindings']]:
      raise ValueError('EXACT_ORDERED_UNIQUE_ADMITTED_DERIVED_INDEX_REQUIRED')
    digests = []
    for row in index['segments']:
      if set(row) != {'content_sha256', 'receipt_sha256'}:
        raise ValueError('EXACT_DERIVED_INDEX_ROW')
      for v in row.values():
        schema.digest(v)
      path = store.safe(root/replica/'segments'/row['content_sha256'])
      local = read.read_json(path/'receipt.json')
      if local['receipt_sha256'] != row['receipt_sha256'] or local['policy_sha256'] != pol['receipt_sha256']:
        raise ValueError('DERIVED_RECEIPT_DRIFT')
      source = admitted[row['content_sha256']]
      schema.validate_derived(local, path, pol['receipt_sha256'], source['receipt_sha256'], source['rows'])
      digests.append(local['receipt_sha256'])
    if len(set(digests)) != 154 or p.sha(p.canonical(digests)) != result['derived_receipt_set_sha256']:
      raise ValueError('DERIVED_RECEIPT_SET_CONFLICT')
  contracts = policy.contracts()
  names = {'signal': 'signal-contract', 'angle-grid': 'angle-grid', 'target': 'target-contract',
           'history-reset': 'history-reset', 'route-cv': 'route-cv-contract', 'future-metric': 'future-metric-contract'}
  rows = {f'empirical-s2-ri-{names[k]}-v1.json': v for k, v in contracts.items()}
  rows['empirical-s2-ri-design-policy-v1.json'] = schema.public(pol)
  rows['empirical-s2-ri-causal-identity-v1.json'] = schema.public(admission.identity_contract())
  rows['empirical-s2-ri-row-admission-v1.json'] = schema.public(admission.row_contract())
  shared = {'policy_sha256': pol['receipt_sha256'], 'causal_identity_sha256': pol['causal_identity_sha256'],
    'historical_generic_causal_identity': 'RATE_DEPENDENT_IMMUTABLE_REFERENCE_ONLY',
    's2_ri_causal_identity': 'RATE_FREE_FAMILY_SPECIFIC_IDENTITY'}
  rows['empirical-s2-ri-support-v1.json'] = p.seal({'schema': 'EMPIRICAL_S2_RI_SUPPORT_V1', **shared,
    'counts': a['counts'], 'scopes': a['support'], 'qlog_model_support': 0,
    'mask_target_and_identity_set_sha256': a['derived_receipt_set_sha256']})
  rows['empirical-s2-ri-structural-diagnostics-v1.json'] = p.seal({'schema': 'EMPIRICAL_S2_RI_STRUCTURAL_DIAGNOSTICS_V1',
    **shared, 'forms': a['forms'], 'selected_form': None, 'normalizer_fitted': False,
    'condition_threshold': None, 'symbolic_identifiability_claim': False})
  both_support = all(v['diagnostics'][r]['rows'] >= 201 for v in a['forms'] for r in pol['route_ids'])
  full_rank = all(v['diagnostics'][r]['status'] == 'FULL_RANK_DIAGNOSTIC' for v in a['forms'] for r in [*pol['route_ids'], 'POOLED'])
  grid = a['counts']['POOLED']['grid_inconsistent_available_rows'] == 0
  ready = both_support and full_rank and grid
  readiness = p.seal({'schema': 'EMPIRICAL_S2_RI_READINESS_V1', **shared,
    'status': 'S2_RI_MODEL_DESIGN_READY_FOR_SEPARATE_FITTING_POLICY' if ready else 'S2_RI_MODEL_DESIGN_PARTIAL',
    'both_routes_boundary_support_at_least_201': both_support, 'all_boundary_forms_full_numerical_rank': full_rank,
    'all_available_angles_source_grid_consistent': grid, 'steering_rate_dependency': 'NONE',
    'rate_independence_proof_sha256': a['receipt_sha256'], 'angle_source_grid': 'SOURCE_PROVEN_0P1_DEG',
    'target': 'MEASURED_ANGLE_GRID_INCREMENT_PER_SAMPLE', 'primary_command': 'LOGGED_POST_CARCONTROLLER_NORMALIZED_COMMAND',
    'physical_eps': 'PHYSICAL_EPS_APPLICATION_UNAVAILABLE', 'transaction': 'REQUEST_OUTPUT_TRANSACTION_LINK_UNAVAILABLE',
    'dataset': pol['resolution']['final_dataset_status'], 'rlog_stream_count': 154, 'qlog_model_support': 0,
    'route_cv': 'FROZEN_RETROSPECTIVE_ROUTE_LEVEL_DEVELOPMENT',
    'model_fitting': 'NOT_RUN', 'model_selection': 'NOT_RUN', 'cv_scoring': 'NOT_RUN',
    'prediction': 'NOT_RUN', 'residual': 'NOT_RUN', 'rollout': 'NOT_RUN', 'normalizer_fitting': 'NOT_RUN',
    'holdout': 'HOLDOUT_OPENING_CLOSED', 'opening_count': 0, 'future_holdout': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
    'historical_track': 'CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED',
    'historical_grid_verdict': 'SOURCE_GRID_OBSERVATION_REJECTED',
    'S1': 'S1_NUMERIC_STRUCTURE_AVAILABLE_BUT_RATE_SEMANTICS_BLOCKED',
    'S2': 'S2_STRUCTURAL_SUPPORT_PRESENT_RATE_SEMANTICS_BLOCKED', 'S3': 'S3_SOURCE_MECHANISM_BLOCKED',
    'stage_b': 'STAGE_B_SIGNAL_ADMISSION_BLOCKED', 'ta': 'TA_STANDALONE_TRADEOFF_ONLY', 'sg': 'SG_CLOSED_LOOP_TRADEOFF_ONLY',
    'composition': ['COMPOSITION_NOT_RECOMMENDED', 'COMPOSITION_NOT_AUTHORIZED'],
    'closed_loop_bias': 'CLOSED_LOOP_IDENTIFICATION_BIAS_RISK', 'calibration_blockers': p.BLOCKERS,
    'sealed_reference': 'NOT_GENERATED', 'vehicle': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
    'authority': policy.AUTHORITY})
  rows['empirical-s2-ri-readiness-v1.json'] = readiness
  rows['empirical-s2-ri-validation-v1.json'] = p.seal({'schema': 'EMPIRICAL_S2_RI_VALIDATION_V1',
    'policy_sha256': pol['receipt_sha256'], 'audit_result_sha256': a['receipt_sha256'],
    'readiness_sha256': readiness['receipt_sha256'], 'executions': 2, 'exact_repeatability': True,
    'derived_array_set_sha256': a['derived_receipt_set_sha256'], 'input_bytes_unchanged': True,
    'rate_adversarial_views': a['rate_views'], 'rate_and_request_independence': 'PASS',
    'generic_run_and_snapshot_overlays': 'PASS', 'feature_matrix_bytes_exact': True, 'rank_repetitions_per_form': 3,
    'readiness_receipt_rate_invariant': True, 'no_model_operations': True,
    'raw_logs_opened': 0, 'qlog_arrays_opened': 0, 'browser': 'NOT_APPLICABLE'})
  for row in rows.values():
    historical_schema.privacy(row)
  return rows


def publish(root, destination=p.PUBLIC):
  rows = build(root)
  destination = store.safe(destination)
  for name, row in rows.items():
    path = store.safe(destination/name)
    if path.exists() and read.read_json(path) != row:
      raise ValueError('IMMUTABLE_PUBLICATION_CONFLICT')
  for name, row in rows.items():
    p.persist(destination/name, row)
  return rows


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--store', required=True)
  args = parser.parse_args()
  publish(args.store)


if __name__ == '__main__':
  main()
