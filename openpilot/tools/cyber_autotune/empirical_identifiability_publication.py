"""Aggregate-only identifiability publication; no raw readers or models."""
import argparse
from pathlib import Path
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_identifiability_policy as policy
from openpilot.tools.cyber_autotune.empirical_identifiability_execution import read_json
from openpilot.tools.cyber_autotune.empirical_causal_dataset_store import safe


INPUT_NAMES = (
  'empirical-model-family-identifiability-policy-v1.json', 'empirical-steering-rate-semantics-v1.json',
  'empirical-s3-source-mechanism-v1.json', 'empirical-identifiability-excitation-v1.json',
  'empirical-identifiability-history-support-v1.json', 'empirical-identifiability-leakage-reset-v1.json',
  'empirical-s1-structural-diagnostics-v1.json', 'empirical-s2-structural-diagnostics-v1.json')


def validate_public(value):
  from openpilot.tools.cyber_autotune.empirical_identifiability_schema import public
  public(value)
  return value


def build(store):
  store = safe(store)
  pol = read_json(store/'policy.json')
  if pol != policy.policy():
    raise ValueError('FROZEN_EXECUTOR_POLICY_DRIFT')
  source = policy.validate_source(read_json(store/'source-contract.json'))
  a, b = (read_json(store/r/'results.json') for r in ('repeat-1', 'repeat-2'))
  if a != b or a['policy_sha256'] != pol['receipt_sha256'] or a['source_contract_sha256'] != source['receipt_sha256']:
    raise ValueError('TWO_COMPLETE_EXACT_EXECUTIONS_REQUIRED')
  from openpilot.tools.cyber_autotune.empirical_identifiability_schema import result
  for replica, value in (('repeat-1', a), ('repeat-2', b)):
    result(value, pol, source, read_json(store/replica/'admission.json'))
  support = {f: all(r['both_routes_next_state_support_at_least_201'] for r in a['families'][f]) for f in ('S1', 'S2')}
  rows = {
    'empirical-model-family-identifiability-policy-v1.json': pol,
    'empirical-steering-rate-semantics-v1.json': source,
    'empirical-s3-source-mechanism-v1.json': p.seal({'schema': 'EMPIRICAL_S3_SOURCE_MECHANISM_V1',
      'source_contract_sha256': source['receipt_sha256'], **source['s3']}),
    'empirical-identifiability-excitation-v1.json': p.seal({'schema': 'EMPIRICAL_IDENTIFIABILITY_EXCITATION_V1',
      'policy_sha256': pol['receipt_sha256'], 'coverage': a['coverage'], 'scopes': a['excitation']}),
    'empirical-identifiability-history-support-v1.json': p.seal({'schema': 'EMPIRICAL_IDENTIFIABILITY_HISTORY_SUPPORT_V1',
      'policy_sha256': pol['receipt_sha256'], 'scopes': a['history_support'], 'selected_history': None,
      'threshold': 201, 'threshold_meaning': 'ROUTE_DEVELOPMENT_AVAILABILITY_NOT_MODEL_ACCEPTANCE'}),
    'empirical-identifiability-leakage-reset-v1.json': policy.leakage_reset()}
  for family in ('S1', 'S2'):
    rows[f'empirical-{family.lower()}-structural-diagnostics-v1.json'] = p.seal({
      'schema': f'EMPIRICAL_{family}_STRUCTURAL_DIAGNOSTICS_V1', 'policy_sha256': pol['receipt_sha256'],
      'source_contract_sha256': source['receipt_sha256'], 'forms': a['families'][family],
      'selected_form': None, 'target_fitting': 'NOT_RUN', 'physical_rate_semantics': 'SOURCE_SEMANTICS_BLOCKED'})
  readiness = p.seal({'schema': 'EMPIRICAL_MODEL_FAMILY_IDENTIFIABILITY_READINESS_V1',
    'status': 'EMPIRICAL_MODEL_FAMILY_IDENTIFIABILITY_AUDIT_COMPLETE',
    'inputs': {n: v['receipt_sha256'] for n, v in rows.items()},
    'dataset_completeness': pol['resolution']['final_dataset_status'], 'legacy_reproduction': 'PASS', 'qlog_reconciliation': 'COMPLETE',
    'rlog_stream_count': 154, 'qlog_support': 0, 'qlog_arrays_opened': 0,
    'family_states': {'S1': ('S1_NUMERIC_STRUCTURE_AVAILABLE_BUT_RATE_SEMANTICS_BLOCKED'
                             if support['S1'] else 'S1_SUPPORT_INSUFFICIENT_RATE_SEMANTICS_BLOCKED'),
                      'S2': ('S2_STRUCTURAL_SUPPORT_PRESENT_RATE_SEMANTICS_BLOCKED' if support['S2'] else 'S2_SUPPORT_INSUFFICIENT_RATE_SEMANTICS_BLOCKED'),
                      'S3': 'S3_SOURCE_MECHANISM_BLOCKED'},
    'rate_contract': source['rate']['contract'], 'signed_physical_rate_proven': False,
    'both_routes_support_for_all_forms': support,
    'symbolic_identifiability_established': False, 'fitting_admission': False,
    'closed_loop_bias': 'CLOSED_LOOP_IDENTIFICATION_BIAS_RISK', 'transaction': pol['transaction'], 'physical_eps': pol['physical_eps'],
    'authority': policy.AUTHORITY, 'model_fitting': 'NOT_RUN', 'model_selection': 'NOT_RUN', 'cv_scoring': 'NOT_RUN',
    'family_selected': None, 'holdout': 'HOLDOUT_OPENING_CLOSED', 'opening_count': 0,
    'future_holdout': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED', 'stage_b': 'STAGE_B_SIGNAL_ADMISSION_BLOCKED',
    'historical_track': 'CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED',
    'ta': 'TA_STANDALONE_TRADEOFF_ONLY', 'sg': 'SG_CLOSED_LOOP_TRADEOFF_ONLY',
    'composition': ['COMPOSITION_NOT_RECOMMENDED', 'COMPOSITION_NOT_AUTHORIZED'],
    'calibration_blockers': p.BLOCKERS, 'sealed_reference': 'NOT_GENERATED',
    'vehicle': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED']})
  rows['empirical-model-family-identifiability-readiness-v1.json'] = readiness
  rows['empirical-identifiability-repeatability-v1.json'] = p.seal({
    'schema': 'EMPIRICAL_IDENTIFIABILITY_REPEATABILITY_V1', 'executions': 2, 'exact': True,
    'policy_sha256': pol['receipt_sha256'], 'result_sha256': a['receipt_sha256'],
    'readiness_sha256': readiness['receipt_sha256'], 'historical_inputs_byte_identical': a['historical_inputs_byte_identical'],
    'array_read_only': True, 'raw_logs_opened': 0, 'qlog_arrays_opened': 0,
    'receipt_and_aggregate_bytes_exact': True, 'model_operations': 'NOT_RUN'})
  return {n: validate_public(v) for n, v in rows.items()}


def publish(store, output=p.PUBLIC):
  rows = build(store)
  output = safe(output)
  for name, row in rows.items():
    path = safe(output/name)
    if path.exists() and read_json(path) != row:
      raise ValueError('IMMUTABLE_PUBLICATION_CONFLICT')
  for name, row in rows.items():
    p.persist(output/name, row)
  return rows


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--store', required=True)
  args = parser.parse_args()
  publish(Path(args.store))


if __name__ == '__main__':
  main()
