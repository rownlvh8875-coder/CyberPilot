"""Authoritative additive readiness resolution; aggregate receipts only, no extraction."""
from pathlib import Path
import json

from openpilot.tools.cyber_autotune import empirical_plant_policy as p

PINS = {
  'empirical-qlog-reconciliation-policy-v1.json': '0137693603f08ab22c4939362627b8c472638bb045f13a25424fa12c1f9f8534',
  'empirical-qlog-identity-v1.json': '2a673cc59f65923cfd31dc2bd7c085318af5ef77a27eeb7a73c7aec40032daa6',
  'empirical-qlog-source-semantics-v1.json': '66b2f383abc24e150d21c1c615e0487e40adae7e4b3f80cad8bf0e632159d96e',
  'empirical-qlog-rlog-equivalence-v1.json': '6d1ae7d38ae4018603c829f33e112d59f0fc29ef835d3c7d15d52fff806218b4',
  'empirical-qlog-numeric-authorization-v1.json': '26456b452e26d5b879a70d86040aa55fed514b7c069fc95f9b3dc9001b26b66a',
  'empirical-qlog-causal-coverage-v1.json': 'cd80460b7adc4f5fbe3d9f822ddd39974112ceb51551dfea022870ee2c9186e5',
  'empirical-qlog-legacy-reproduction-v1.json': '2aa5b936523d840d483c02e628280d2a476632d7cd123ed2a7fd3e5ddf598df6',
  'empirical-qlog-additive-merge-v1.json': '00d81f23724337866259a8183c4539107d5e529e904f20950c39cf7bb34fd808',
  'empirical-qlog-reconciliation-repeatability-v1.json': 'f1a99d2a7e13fc322c75dd6a6431dd13bb76efff3e6dd6fae80060c3f2a21430',
  'empirical-qlog-reconciliation-readiness-v1.json': 'a016fd843cd4e5f7478951811127deb581cfee9870611dd9ddccd661e14156ec',
  'empirical-qlog-final-assessment-v1.json': 'cd4591e909d6dd1c074b872f271a1d1d75ae8a5ae70aa17e7a6b88cf5bcad580',
  'empirical-causal-train-dev-policy-v1.json': '661d0dc9d5bdf79e70f69ef9aeb589314ef82fd0c845ac13d72ce208346182fb',
  'empirical-causal-train-dev-route-set-v1.json': 'e1b55f689677f46eabe96e4b0a0b3482543266a3abde3f680459dfaa78fd13d8',
  'empirical-causal-numeric-authorization-v1.json': 'c16b154c4780d9d28199d7a502295dad0396cc48e5bbfc7017890910316c89d2',
  'empirical-causal-route-coverage-v1.json': 'd2f4166bd51ee9e134c5c8126aafe485cd92ee50e48a386f911a65f478c994e1',
  'empirical-causal-train-dev-readiness-v1.json': 'bb70eee36c9b426e6d04ee4cceca0cd57cabeb8bee39e7736a7c43c37207fecf',
  'empirical-causal-context-schema-v2-execution-v1.json': '9992b4d67db40484acd642419b6a4cccb776bbc749ea29b0b5291c6969281b31',
  'empirical-causal-h1-mapping-v1.json': '0998cb9fbd072127d022a54c9417e5b6823864734f5e145309f6f3eaba74219e',
  'future-model-family-readiness-v1.json': 'ab86e1206feec5fbcf67a57d488f232dc40c98585fdad125f05466866dc70a22',
}
FINAL = 'empirical-qlog-final-assessment-v1.json'
EXECUTION = 'empirical-qlog-reconciliation-readiness-v1.json'
INTERMEDIATE = 'empirical-causal-train-dev-readiness-v1.json'
RLOG_ROUTES = 'empirical-causal-train-dev-route-set-v1.json'
RLOG_AUTH = 'empirical-causal-numeric-authorization-v1.json'
RLOG_COVERAGE = 'empirical-causal-route-coverage-v1.json'
QLOG_COVERAGE = 'empirical-qlog-causal-coverage-v1.json'
MERGE = 'empirical-qlog-additive-merge-v1.json'
LEGACY = 'empirical-qlog-legacy-reproduction-v1.json'
PARTIAL = 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL'
GENERATION = 'EMPIRICAL_FINAL_READINESS_RESOLUTION_V2'
ROLE = 'RETROSPECTIVE_TRAIN_DEV_CV_POOL'
PRECEDENCE = ['AUTHORITATIVE_FINAL_ASSESSMENT', 'EXECUTION_READINESS', 'INTERMEDIATE_EXTRACTION_STATE']


def load(directory=p.PUBLIC):
  """Read exact public receipts only; never discover private data or substitute evidence."""
  directory = Path(directory)
  if not directory.is_absolute() or '..' in directory.parts:
    raise ValueError('ABSOLUTE_PUBLIC_RECEIPT_DIRECTORY_REQUIRED')
  result = {}
  for name in PINS:
    path = directory/name
    if any(x.is_symlink() for x in (path, *path.parents)):
      raise ValueError('NO_SYMLINK_RECEIPTS')
    result[name] = json.loads(path.read_bytes())
  return validate_inputs(result)


def validate_inputs(evidence):
  if type(evidence) is not dict or set(evidence) != set(PINS):
    raise ValueError('AUTHORITATIVE_FINAL_AND_COMPLETE_PINNED_CHAIN_REQUIRED_NO_FALLBACK')
  for name, row in evidence.items():
    p.verify(row)
    if row['receipt_sha256'] != PINS[name]:
      raise ValueError('HISTORICAL_READINESS_PIN_DRIFT')
  final, execution, intermediate = (evidence[n] for n in (FINAL, EXECUTION, INTERMEDIATE))
  if (final['schema'] != 'EMPIRICAL_QLOG_FINAL_ASSESSMENT_V1'
      or final['status'] != PARTIAL or final['authoritative_final_dataset_completeness'] != PARTIAL
      or final['initial_aggregate_gate_sha256'] != execution['receipt_sha256']
      or final['inputs'] != {n: evidence[n]['receipt_sha256'] for n in final['inputs']}
      or execution['artifacts'] != {n: evidence[n]['receipt_sha256'] for n in execution['artifacts']}):
    raise ValueError('FINAL_ASSESSMENT_PRECEDENCE_OR_CHAIN_CONFLICT')
  if (final['historical_accounting'] != 'LEGACY_ALIGNMENT_REPRODUCED'
      or evidence[LEGACY]['status'] != 'LEGACY_ALIGNMENT_REPRODUCED'
      or any(v is not True for r in evidence[LEGACY]['routes'] for v in r['checks'].values())
      or final['reconciliation'] != 'QLOG_HISTORICAL_RECONCILIATION_COMPLETE'
      or final['qlog_training_admission'] != 'NO_CONTIGUOUS_CAUSAL_MODEL_SUPPORT_AT_CURRENT_TIMEBASE'
      or final['added_causal_valid_rows'] != 0 or final['added_causal_runs'] != 0):
    raise ValueError('LEGACY_ACCOUNTING_CANNOT_PROMOTE_CAUSAL_SUPPORT')
  routes, auth, coverage = (evidence[n] for n in (RLOG_ROUTES, RLOG_AUTH, RLOG_COVERAGE))
  ids = [r['route_id'] for r in routes['routes']]
  if len(ids) != 2 or len(set(ids)) != 2 or set(auth['segment_sets']) != set(ids):
    raise ValueError('EXACT_TWO_RETROSPECTIVE_ROUTES_REQUIRED')
  if auth['route_set_sha256'] != routes['receipt_sha256'] or intermediate['route_set_sha256'] != routes['receipt_sha256']:
    raise ValueError('RLOG_ROUTE_CHAIN_CONFLICT')
  if (intermediate['coverage_sha256'] != coverage['receipt_sha256']
      or intermediate['authorization_sha256'] != auth['private_authorization_sha256']
      or intermediate['policy_sha256'] != evidence['empirical-causal-train-dev-policy-v1.json']['receipt_sha256']
      or evidence[MERGE]['historical_manifest_sha256'] != intermediate['dataset_manifest_sha256']):
    raise ValueError('RLOG_DATASET_CHAIN_CONFLICT')
  for row in (final, execution, intermediate):
    if (row['holdout'] != 'HOLDOUT_OPENING_CLOSED' or row['opening_count'] != 0 or row['reservation'] != 'NONE'
        or row['model_fitting'] != 'MODEL_FITTING_NOT_RUN' or row['model_selection'] != 'NOT_RUN'
        or row['stage_b'] != 'STAGE_B_SIGNAL_ADMISSION_BLOCKED' or row['calibration_blockers'] != p.BLOCKERS):
      raise ValueError('READINESS_AUTHORITY_OR_BLOCKER_DRIFT')
  pol = evidence['empirical-causal-train-dev-policy-v1.json']
  if pol['dt_ns'] != 10_000_000 or pol['max_age_ns'] != 20_000_000:
    raise ValueError('FROZEN_TIMEBASE_REQUIRED')
  old = {r['route_id']: r for r in coverage['routes']}
  merged = {r['route_id']: r for r in evidence[MERGE]['routes']}
  qlogs = evidence[QLOG_COVERAGE]['segments']
  if set(old) != set(ids) or set(merged) != set(ids) or len(qlogs) != 2:
    raise ValueError('EXACT_SUPPORT_PARTITION_REQUIRED')
  excluded = {s['source_sha256'] for r in routes['routes'] for s in r['excluded_sources']}
  if len(excluded) != 2 or excluded != {s['segment_sha256'] for s in qlogs}:
    raise ValueError('EXACT_QLOG_EXCLUSION_IDENTITY_REQUIRED')
  for r in routes['routes']:
    rid = r['route_id']
    add = [s for s in qlogs if s['route_id'] == rid]
    binding = auth['segment_sets'][rid]
    if (binding != {'count': r['segment_count'], 'set_sha256': r['segment_set_sha256']}
        or r['role'] != ROLE or r['holdout_allowed'] is not False or r['independent_validation_allowed'] is not False
        or merged[rid]['rlog_count'] != r['segment_count'] or merged[rid]['qlog_count'] != len(add)):
      raise ValueError('RLOG_SEGMENT_OR_ROLE_BINDING_CONFLICT')
    for key in ('source_commit', 'full_carparams_sha256', 'empirical_profile_sha256'):
      if r[key] != old[rid][key] or r[key] != merged[rid][key]:
        raise ValueError('SOURCE_PROFILE_PARTITION_CONFLICT')
    if (old[rid]['bridge']['status'] != 'ROUTE_COMMAND_BRIDGE_CONFIRMED'
        or old[rid]['bridge']['steer_max'] != 409 or merged[rid]['bridge']['status'] != 'ROUTE_COMMAND_BRIDGE_CONFIRMED'):
      raise ValueError('COMMAND_BRIDGE_CONFLICT')
    if (merged[rid]['coverage']['total_grid_samples'] != old[rid]['coverage']['total_grid_samples'] +
        sum(s['coverage']['total_grid_samples'] for s in add)
        or merged[rid]['bridge']['eligible'] != old[rid]['bridge']['eligible'] + sum(s['bridge']['eligible'] for s in add)
        or merged[rid]['coverage']['causal_required_valid'] != old[rid]['coverage']['causal_required_valid']
        or any(s['coverage']['causal_required_valid'] != 0 or s['coverage']['causal_runs'] != 0
               or any(s['coverage']['bins'][b]['common_design_rows'] != 0 for b in ('LOW', 'MEDIUM', 'HIGH')) for s in add)):
      raise ValueError('ACCOUNTING_CAUSAL_PARTITION_CONFLICT')
  if sum(r['segment_count'] for r in routes['routes']) != 154:
    raise ValueError('EXACT_154_RLOG_SUBSET_REQUIRED')
  return evidence


def resolve(evidence=None):
  x = load() if evidence is None else validate_inputs(evidence)
  final, execution, intermediate = (x[n] for n in (FINAL, EXECUTION, INTERMEDIATE))
  return p.seal({'schema': 'EMPIRICAL_FINAL_READINESS_RESOLUTION_V2', 'generation': GENERATION,
    'precedence': PRECEDENCE, 'authoritative_source': FINAL, 'authoritative_sha256': final['receipt_sha256'],
    'execution_source': EXECUTION, 'execution_sha256': execution['receipt_sha256'],
    'historical_execution_status': execution['status'], 'historical_intermediate_status': intermediate['status'],
    'final_dataset_status': final['authoritative_final_dataset_completeness'],
    'legacy_reproduction_status': 'PASS', 'qlog_reconciliation_status': 'COMPLETE',
    'qlog_causal_admission': final['qlog_training_admission'], 'fallback_to_execution_ready': False,
    'rlog_dataset_manifest_sha256': intermediate['dataset_manifest_sha256'],
    'qlog_accounting_manifest_sha256': x[MERGE]['manifest_sha256'],
    'inputs': {n: row['receipt_sha256'] for n, row in x.items()},
    'resolver_sha256': p.sha(Path(__file__).read_bytes()),
    'model_execution_authorized': False, 'model_fitting': 'NOT_RUN', 'model_selection': 'NOT_RUN', 'cv_scoring': 'NOT_RUN',
    'holdout': 'HOLDOUT_OPENING_CLOSED', 'opening_count': 0, 'future_holdout': final['future_holdout'],
    'stage_b': final['stage_b'], 'historical_track': final['historical_track'],
    'no_model': final['no_model'], 'calibration_blockers': p.BLOCKERS, 'historical_artifacts_modified': False})


def validate_resolution(receipt, evidence=None):
  p.verify(receipt)
  if receipt != resolve(evidence):
    raise ValueError('AUTHORITATIVE_RESOLUTION_REQUIRED_EXECUTION_READY_NOT_ACCEPTED')
  return receipt


def partition(evidence=None):
  x = load() if evidence is None else validate_inputs(evidence)
  resolved = resolve(x)
  old = {r['route_id']: r for r in x[RLOG_COVERAGE]['routes']}
  routes = []
  for r in x[RLOG_ROUTES]['routes']:
    c = old[r['route_id']]
    routes.append({k: r[k] for k in ('route_id', 'role', 'source_commit', 'full_carparams_sha256',
      'empirical_profile_sha256', 'semantic_class_id', 'segment_count', 'segment_set_sha256')})
    routes[-1].update({'config_sha256': c['config_sha256'], 'coverage': c['coverage'],
      'legacy_bin_accounting': c['bins'], 'legacy_bin_accounting_is_not_new_model_support': True,
      'holdout_allowed': False, 'independent_validation_allowed': False})
  qlogs = [{'route_id': s['route_id'], 'segment_sha256': s['segment_sha256'],
    'grid_count': s['coverage']['total_grid_samples'], 'command_pairs': s['bridge']['eligible'],
    'causal_valid_count': 0, 'causal_runs': 0, 'model_design_support': 0,
    'model_fit_allowed': False, 'model_selection_allowed': False, 'cv_support_allowed': False}
    for s in x[QLOG_COVERAGE]['segments']]
  return p.seal({'schema': 'EMPIRICAL_CAUSAL_SUPPORT_PARTITION_V1', 'resolution_sha256': resolved['receipt_sha256'],
    'rlog_subset': {'kind': 'rlog.zst', 'count': 154, 'routes': routes,
      'grid_count': sum(r['coverage']['total_grid_samples'] for r in old.values()),
      'causal_valid_count': sum(r['coverage']['causal_required_valid'] for r in old.values()),
      'causal_runs': sum(r['coverage']['causal_runs'] for r in old.values()),
      'status': 'RETROSPECTIVE_RICH_CAUSAL_SUBSET_FUTURE_AUTHORIZATION_REQUIRED'},
    'qlog_subset': {'kind': 'qlog.zst', 'count': 2, 'segments': qlogs,
      'grid_count': sum(s['grid_count'] for s in qlogs), 'command_pairs': sum(s['command_pairs'] for s in qlogs),
      'causal_valid_count': 0, 'causal_runs': 0, 'model_design_support': 0,
      'status': 'HISTORICAL_ACCOUNTING_ONLY_NOT_MODEL_SUPPORT'},
    'all_stream_grid_count': x[FINAL]['total_aligned_rows'],
    'rlog_manifest_sha256': resolved['rlog_dataset_manifest_sha256'],
    'qlog_manifest_sha256': resolved['qlog_accounting_manifest_sha256'],
    'mask_support_recomputed': False, 'numeric_arrays_opened': False})
