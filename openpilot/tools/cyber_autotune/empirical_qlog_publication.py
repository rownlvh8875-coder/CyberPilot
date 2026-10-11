"""Aggregate-only additive qlog reconciliation evidence."""
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_causal_dataset_policy as base
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage
from openpilot.tools.cyber_autotune import empirical_causal_dataset_publication as historical
from openpilot.tools.cyber_autotune import empirical_source_execution as previous
from openpilot.tools.cyber_autotune import empirical_cross_root_inventory as logs
from openpilot.tools.cyber_autotune import empirical_qlog_reconciliation_policy as policy

FILES = ('empirical-qlog-reconciliation-policy-v1.json', 'empirical-qlog-identity-v1.json',
         'empirical-qlog-source-semantics-v1.json', 'empirical-qlog-rlog-equivalence-v1.json',
         'empirical-qlog-numeric-authorization-v1.json', 'empirical-qlog-causal-coverage-v1.json',
         'empirical-qlog-legacy-reproduction-v1.json', 'empirical-qlog-additive-merge-v1.json',
         'empirical-qlog-reconciliation-repeatability-v1.json', 'empirical-qlog-reconciliation-readiness-v1.json')


def repeatability(store, causal, v2, v3, source, roots, firewall):
  store = storage.safe(store)
  a, b = (base.read(store/n/'manifest.json') for n in ('repeat-1', 'repeat-2'))
  ta, tb = (storage.tree_identity(store/n) for n in ('repeat-1', 'repeat-2'))
  if a != b or ta != tb:
    raise ValueError('QLOG_EXACT_REPEATABILITY_CONFLICT')
  auth = base.read(store/'authorization.json')
  after = {k: storage.tree_identity(storage.safe(path)) for k, path in
           zip(('causal', 'v2', 'v3', 'source'), (causal, v2, v3, source), strict=True)}
  if after != auth['historical_tree_sha256']:
    raise ValueError('HISTORICAL_PRIVATE_STORE_MUTATION')
  approved = previous.approved_root_map(roots)
  for segment in auth['segments']:
    if logs.file_sha(previous.source_location(segment['location'], approved)) != segment['source_sha256']:
      raise ValueError('QLOG_RAW_SOURCE_MUTATION')
  p.verify(firewall)
  if firewall['model_apis_patched_to_fail'] is not True or firewall['resume_decoder_patched_to_fail'] is not True:
    raise ValueError('QLOG_EXECUTION_FIREWALL_PROOF_REQUIRED')
  result = p.seal({'schema': 'EMPIRICAL_QLOG_REPEATABILITY_V1', 'repeats': 2, 'exact': True,
    'manifest_sha256': a['receipt_sha256'], 'replica_tree_sha256': ta, 'new_qlog_count': 2,
    'array_dtype_shape_order_bytes': 'EXACT', 'origin_run_snapshot_config_receipts': 'EXACT',
    'historical_trees_before': auth['historical_tree_sha256'], 'historical_trees_after': after,
    'exact_qlog_hashes_before_after': True, 'firewall_sha256': firewall['receipt_sha256']})
  p.persist(store/'repeatability.json', result)
  return result


def validate_public(row):
  historical.validate_public(row)
  def visit(x):
    if isinstance(x, dict):
      if {'segment_origins', 'original_route_global_start', 'reconciled_route_global_start', 'location', 'file_size'} & x.keys():
        raise ValueError('PRIVATE_QLOG_IDENTITY_OR_ORIGIN')
      for value in x.values():
        visit(value)
    elif isinstance(x, list):
      for value in x:
        visit(value)
  visit(row)
  return row


def publish(store):
  store = storage.safe(store)
  pol, auth, audit, manifest, repeat = (base.read(store/n) for n in (
    'policy.json', 'authorization.json', 'source-audit.json', 'repeat-1/manifest.json', 'repeatability.json'))
  if (pol != policy.policy() or repeat['exact'] is not True or repeat['manifest_sha256'] != manifest['receipt_sha256']
      or manifest['authorization_sha256'] != auth['receipt_sha256']):
    raise ValueError('QLOG_PUBLICATION_CHAIN_CONFLICT')
  routes = manifest['routes']
  ready = all(r['status'] == 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_READY' for r in routes)
  public_routes = [{k: r[k] for k in ('route_id', 'source_commit', 'full_carparams_sha256', 'empirical_profile_sha256',
    'config_sha256', 'source_set_sha256', 'segment_count', 'rlog_count', 'qlog_count', 'coverage',
    'required_field_coverage', 'bins', 'mask_reason_counts', 'causal_run_length_distribution', 'transitions', 'bridge',
    'legacy_checks', 'status', 'role', 'holdout_allowed', 'independent_validation_allowed')} for r in routes]
  inventory = base.read(store/'service-inventory.json')
  outputs = dict(zip(FILES, [
    pol,
    p.seal({'schema': 'EMPIRICAL_QLOG_IDENTITY_PUBLIC_V1', 'count': 2,
      'identities': [{k: s[k] for k in ('route_id', 'source_sha256', 'metadata_sha256', 'historical_opening_sha256',
        'source_commit', 'full_carparams_sha256', 'empirical_profile_sha256')} for s in auth['segments']],
      'identity_resolution': 'EXACT_HISTORICAL_EXCLUSION_RECEIPTS_NO_DISCOVERY'}),
    audit,
    p.seal({'schema': 'EMPIRICAL_QLOG_RLOG_EQUIVALENCE_V1', 'source_audit_sha256': audit['receipt_sha256'],
      'fields': audit['equivalence'], 'cadence_admission': audit['cadence_admission'],
      'same_event_semantics_not_same_sampling': True, 'live_submaster_health': None, 'physical_eps_application': None}),
    p.seal({'schema': 'EMPIRICAL_QLOG_NUMERIC_AUTHORIZATION_PUBLIC_V1', 'private_authorization_sha256': auth['receipt_sha256'],
      'policy_sha256': pol['receipt_sha256'], 'source_audit_sha256': audit['receipt_sha256'],
      'historical_route_set_sha256': auth['historical_route_set_sha256'], 'source_schema_sha256': auth['source_schema_sha256'],
      'source_fingerprint_sha256': auth['source_fingerprint_sha256'], 'recorded_adapter_sha256': auth['recorded_adapter_sha256'],
      'numeric_adapter_sha256': auth['numeric_adapter_sha256'], 'alignment_code_sha256': auth['alignment_code_sha256'],
      'signal_whitelist_sha256': auth['signal_whitelist_sha256'], 'segment_set_sha256': p.sha(p.canonical(
        sorted(s['source_sha256'] for s in auth['segments']))), 'count': 2, 'raw_kind_allowlist': ['qlog.zst'],
      'holdout_opening_allowed': False}),
    p.seal({'schema': 'EMPIRICAL_QLOG_CAUSAL_COVERAGE_V1', 'segments': [
      {k: s[k] for k in ('route_id', 'segment_sha256', 'coverage', 'bridge', 'cadence', 'unavailable_fields')} for s in manifest['new_segments']],
      'service_inventory': inventory['segments'], 'all_aligned_rows_preserved': True,
      'no_gap_fill': True, 'physical_rate_unit': 'DBC_UNIT_EMPTY_PHYSICAL_RATE_SEMANTICS_UNRESOLVED'}),
    p.seal({'schema': 'EMPIRICAL_QLOG_LEGACY_REPRODUCTION_V1', 'routes': [
      {'route_id': r['route_id'], 'checks': r['legacy_checks']} for r in routes],
      'new_segments': [{'segment_sha256': s['segment_sha256'], 'checks': s['legacy_checks']} for s in manifest['new_segments']],
      'status': 'LEGACY_ALIGNMENT_REPRODUCED' if all(all(r['legacy_checks'].values()) for r in routes) else 'LEGACY_ALIGNMENT_REPRODUCTION_CONFLICT',
      'historical_results_rewritten': False, 'history': 45, 'minimum_support': 201}),
    p.seal({'schema': 'EMPIRICAL_QLOG_ADDITIVE_MERGE_V1', 'routes': public_routes,
      'manifest_sha256': manifest['receipt_sha256'], 'historical_manifest_sha256': manifest['historical_manifest_sha256'],
      'rlog_reference_count': sum(r['rlog_count'] for r in routes), 'new_qlog_count': 2,
      'old_arrays_modified': False, 'old_origin_indices_modified': False,
      'new_logical_origin': 'SEPARATE_FULL_ROUTE_INDEX_OVERLAY_LOCAL_ONLY',
      'qlog_cadence': 'MIXED_CADENCE_EXPLICIT_NULL_GAP_WITH_UNCHANGED_20MS_POLICY'}),
    repeat,
    {}], strict=True))
  outputs[FILES[-1]] = p.seal({'schema': 'EMPIRICAL_QLOG_RECONCILIATION_READINESS_V1',
    'status': 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_READY' if ready else 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_BLOCKED',
    'generation': 'QLOG_HISTORICAL_RECONCILIATION_V1', 'reconciliation': 'QLOG_HISTORICAL_RECONCILIATION_COMPLETE',
    'manifest_sha256': manifest['receipt_sha256'], 'input_rlog_dataset_state': 'IMMUTABLE_HISTORICAL_BLOCKED_RESULT_PRESERVED',
    'artifacts': {n: r['receipt_sha256'] for n, r in outputs.items() if n != FILES[-1]},
    'route_count': len(routes), 'rlog_reference_count': sum(r['rlog_count'] for r in routes), 'qlog_count': 2,
    'total_aligned_rows': sum(r['coverage']['total_grid_samples'] for r in routes),
    'actual_rate': 'ACTUAL_STEERING_RATE_PRESERVED', 'causal_context': 'CAUSAL_CONTEXT_V2_EXTRACTED',
    'command_provenance': 'THREE_STAGE_COMMAND_PROVENANCE_READY', 'h1_mapping': 'H1_OBSERVABILITY_MAPPING_READY',
    'h1_mapping_sha256': historical.PINS['empirical-causal-h1-mapping-v1.json'],
    'qlog_valid_support': 'REPORTED_SEPARATELY_NO_CONTIGUOUS_SUPPORT_PROMOTION_FROM_ACCOUNTING',
    'blockers': [] if ready else ['LEGACY_OR_REQUIRED_FIELD_OR_COMMAND_BRIDGE_CONFLICT'],
    'model_fitting': 'MODEL_FITTING_NOT_RUN', 'model_selection': 'NOT_RUN', 'candidate_execution': 'NOT_RUN',
    'historical_track': 'CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED',
    'stage_b': 'STAGE_B_SIGNAL_ADMISSION_BLOCKED', 'holdout': 'HOLDOUT_OPENING_CLOSED', 'opening_count': 0, 'reservation': 'NONE',
    'future_holdout': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED', 'no_model': 'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT',
    'ta': 'TA_STANDALONE_TRADEOFF_ONLY', 'sg': 'SG_CLOSED_LOOP_TRADEOFF_ONLY',
    'composition': 'COMPOSITION_NOT_RECOMMENDED', 'composition_authority': 'COMPOSITION_NOT_AUTHORIZED',
    'search': 'SEARCH_NOT_AUTHORIZED', 'frozen_evaluation': 'FROZEN_EVALUATION_NOT_AUTHORIZED',
    'calibration_blockers': p.BLOCKERS, 'sealed_reference': 'NOT_GENERATED', 'vehicle': 'NOT_READY',
    'real_vehicle': 'REAL_VEHICLE_UNVERIFIED', 'vehicle_activation': 'VEHICLE_ACTIVATION_BLOCKED',
    'qualification_allowed': False, 'reference_promotable': False, 'production_authority': False})
  validate_chain(outputs)
  for name, row in outputs.items():
    p.persist(p.PUBLIC/name, row)
  return outputs


def validate_chain(rows):
  if set(rows) != set(FILES):
    raise ValueError('EXACT_QLOG_PUBLIC_ARTIFACT_SET_REQUIRED')
  for row in rows.values():
    validate_public(row)
  ready = rows[FILES[-1]]
  if ready['artifacts'] != {n: r['receipt_sha256'] for n, r in rows.items() if n != FILES[-1]}:
    raise ValueError('QLOG_PUBLIC_RECEIPT_CHAIN_DRIFT')
  if (rows[FILES[0]] != policy.policy() or ready['holdout'] != 'HOLDOUT_OPENING_CLOSED'
      or ready['opening_count'] != 0 or ready['reservation'] != 'NONE'
      or ready['model_fitting'] != 'MODEL_FITTING_NOT_RUN' or ready['model_selection'] != 'NOT_RUN'
      or ready['stage_b'] != 'STAGE_B_SIGNAL_ADMISSION_BLOCKED' or ready['calibration_blockers'] != p.BLOCKERS
      or ready['qualification_allowed'] is not False or ready['production_authority'] is not False):
    raise ValueError('QLOG_UNAUTHORIZED_PROMOTION')
  auth, audit, equivalence, merged, repeat = (rows[FILES[i]] for i in (4, 2, 3, 7, 8))
  expected_routes = [r['route_id'] for r in base.resolve_routes()]
  expected_rlogs = sum(r['segment_count'] for r in historical.load()['empirical-causal-train-dev-route-set-v1.json']['routes'])
  if (repeat['manifest_sha256'] != ready['manifest_sha256'] or merged['manifest_sha256'] != ready['manifest_sha256']
      or repeat['repeats'] != 2 or repeat['new_qlog_count'] != 2 or repeat['exact'] is not True
      or repeat['historical_trees_before'] != repeat['historical_trees_after']
      or repeat['exact_qlog_hashes_before_after'] is not True):
    raise ValueError('QLOG_PUBLIC_REPEATABILITY_CHAIN_DRIFT')
  if (auth['source_audit_sha256'] != audit['receipt_sha256'] or equivalence['source_audit_sha256'] != audit['receipt_sha256']
      or auth['policy_sha256'] != rows[FILES[0]]['receipt_sha256']
      or audit['status'] != 'QLOG_SOURCE_SEMANTICS_COMPLETE'):
    raise ValueError('QLOG_PUBLIC_SOURCE_AUTHORIZATION_DRIFT')
  if (ready['route_count'] != 2 or ready['qlog_count'] != 2 or auth['count'] != 2 or rows[FILES[1]]['count'] != 2
      or merged['new_qlog_count'] != 2 or merged['rlog_reference_count'] != expected_rlogs
      or ready['rlog_reference_count'] != expected_rlogs or [r['route_id'] for r in merged['routes']] != expected_routes
      or sum(r['rlog_count'] for r in merged['routes']) != expected_rlogs
      or sum(r['qlog_count'] for r in merged['routes']) != 2
      or any(r['segment_count'] != r['rlog_count']+r['qlog_count'] for r in merged['routes'])):
    raise ValueError('QLOG_PUBLIC_EXACT_ROUTE_SOURCE_COUNT_DRIFT')
  identity_set = {s['source_sha256'] for s in rows[FILES[1]]['identities']}
  historical_set = {s['source_sha256'] for r in historical.load()['empirical-causal-train-dev-route-set-v1.json']['routes']
                    for s in r['excluded_sources']}
  if (identity_set != historical_set or auth['segment_set_sha256'] != p.sha(p.canonical(sorted(identity_set)))
      or len(identity_set) != 2 or identity_set != {s['segment_sha256'] for s in rows[FILES[5]]['segments']}
      or any(s['route_id'] not in expected_routes for s in rows[FILES[1]]['identities'])):
    raise ValueError('QLOG_PUBLIC_EXACT_SEGMENT_IDENTITY_DRIFT')
  if ready['status'] == 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_READY':
    if (rows[FILES[6]]['status'] != 'LEGACY_ALIGNMENT_REPRODUCED' or rows[FILES[8]]['exact'] is not True
        or any(not all(r['legacy_checks'].values()) or r['bridge']['status'] != 'ROUTE_COMMAND_BRIDGE_CONFIRMED'
               for r in rows[FILES[7]]['routes'])):
      raise ValueError('QLOG_FALSE_READY_PROMOTION')
  return rows
