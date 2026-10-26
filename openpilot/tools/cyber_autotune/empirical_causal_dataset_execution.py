"""Explicit two-route extraction CLI. No discovery, model, controller or holdout calls."""
import argparse
from collections import Counter
import platform
import subprocess

import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_execution as previous
from openpilot.tools.cyber_autotune import empirical_source_metadata as metadata
from openpilot.tools.cyber_autotune import empirical_cross_root_inventory as logs
from openpilot.tools.cyber_autotune import empirical_causal_dataset_policy as policy
from openpilot.tools.cyber_autotune import empirical_causal_dataset_reader as reader
from openpilot.tools.cyber_autotune import empirical_causal_dataset_alignment as alignment
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage


def source_proof(repo, source, destination):
  """Read committed public blobs only; never execute source or modify checkout."""
  roles = sorted(source['files'])
  entries, text = {}, {}
  for role in roles:
    row = source['files'][role]
    data = subprocess.check_output(['git', '-c', f'safe.directory={repo}', '-C', str(repo),
                                    'show', source['commit']+':'+row['path']])
    if p.sha(data) != row['file_sha256']:
      raise ValueError('EXACT_SOURCE_BLOB_DRIFT')
    entries[role] = row
    text[role] = data.decode()
    storage.atomic_bytes(destination / (row['file_sha256']+'.source'), data)
  for fact in ('ret.steeringAngleDeg = cp.vl["SAS11"]["SAS_Angle"]',
               'ret.steeringRateDeg = cp.vl["SAS11"]["SAS_Speed"]', 'ret.yawRate = cp.vl["ESP12"]["YAW_RATE"]'):
    if fact not in text['carstate']:
      raise ValueError('SOURCE_MEASURED_FIELD_BINDING_CONFLICT')
  if 'SG_ SAS_Speed : 16|8@1+ (4.0,0.0)' not in text['dbc'] or 'SG_ SAS_Angle : 0|16@1- (0.1,0.0)' not in text['dbc']:
    raise ValueError('SOURCE_DBC_BINDING_CONFLICT')
  if 'self.STEER_MAX = 409' not in text['controller_limits']:
    raise ValueError('SOURCE_STEER_MAX_BINDING_CONFLICT')
  return p.seal({'schema': 'EMPIRICAL_CAUSAL_SIGNAL_PROVENANCE_V1', 'repository': source['repository'],
    'commit': source['commit'], 'source_fingerprint_sha256': source['receipt_sha256'],
    'source_manifest_sha256': source['manifest_sha256'], 'license_status': source['license_status'], 'licenses': source['licenses'],
    'files': entries, 'angle': {'signal': 'SAS11.SAS_Angle', 'factor': 0.1, 'offset': 0, 'unit': 'Deg', 'layout': '0|16@1-'},
    'rate': {'signal': 'SAS11.SAS_Speed', 'factor': 4.0, 'offset': 0, 'dbc_unit': '', 'schema_name': 'steeringRateDeg',
             'physical_unit_status': 'DBC_UNIT_EMPTY_PHYSICAL_RATE_SEMANTICS_UNRESOLVED', 'layout': '16|8@1+'},
    'yaw': {'signal': 'ESP12.YAW_RATE', 'factor': 0.01, 'offset': -40.95, 'dbc_unit': '', 'unit': 'UNRESOLVED', 'vehicle_frame': 'UNVERIFIED'},
    'gyro': {'sources': ['lsm6ds3', 'lsm6ds3trc'], 'unit': 'SOURCE_DECLARED_RAD_PER_SECOND_DEVICE_AXES',
             'imu_to_vehicle_transform': 'UNVERIFIED', 'producer_identity': 'EXACT_PRIOR_SOURCE_FINGERPRINT_AND_DEPENDENCY_CLOSURE'},
    'command': {'request': 'carControl.actuators.torque', 'post_controller': 'carOutput.actuatorsOutput.torque',
                'raw': 'carOutput.actuatorsOutput.torqueOutputCan', 'physical_eps_applied': None},
    'request_output_linkage': 'REQUEST_OUTPUT_TRANSACTION_LINK_UNAVAILABLE',
    'publication_order': 'CARD_PUBLISHES_LAST_ACTUATORS_OUTPUT_THEN_UPDATES_FROM_CARCONTROL_NO_TRANSACTION_ID',
    'numeric_unit_or_yaw_adjudication': 'NOT_RUN'})


def prepare(store, v2_store, v3_store, source_store, source_repo, roots):
  v2_store, v3_store, source_store = map(storage.safe, (v2_store, v3_store, source_store))
  approved = previous.approved_root_map(roots)
  store = storage.external(store, [v2_store, v3_store, source_store, *approved.values()])
  x = policy.inputs()
  routes = policy.resolve_routes(x)
  trees = {'v2': storage.tree_identity(v2_store), 'v3': storage.tree_identity(v3_store), 'source': storage.tree_identity(source_store)}
  expected_trees = x['empirical-stage-a-causal-recovery-policy-v1.json']['input_tree_sha256']
  if any(trees[k] != expected_trees[k] for k in ('v2', 'v3')):
    raise ValueError('HISTORICAL_PRIVATE_TREE_DRIFT')
  p.persist(store/'historical-trees-before.json', p.seal({'schema': 'EMPIRICAL_CAUSAL_HISTORICAL_TREE_PINS_V1', 'trees': trees}))
  split, auth0, manifest = (policy.read(v2_store/n) for n in ('split.json', 'authorization.json', 'manifest.json'))
  if split != x['empirical-plant-v2-train-dev-split-v1.json'] or auth0 != x['empirical-plant-v2-numeric-authorization-v1.json']:
    raise ValueError('EXACT_V2_PRIVATE_PUBLIC_BINDING_REQUIRED')
  cache = policy.read(v3_store/'cache-integrity.json')
  if (cache['receipt_sha256'] != x['empirical-stage-a-causal-recovery-policy-v1.json']['v3_cache_integrity_sha256']
      or cache['v2_manifest_sha256'] != manifest['receipt_sha256'] or manifest['split_sha256'] != split['receipt_sha256']):
    raise ValueError('V2_V3_MANIFEST_BINDING_DRIFT')
  source = policy.read(source_store/'fingerprints'/(routes[0]['source_commit']+'.json'))
  adapter = policy.read(source_store/'adapters-final'/(routes[0]['source_commit']+'.json'))
  policy.validate_source(routes[0], source, adapter, policy.read(source_store/'public-origin.json'))
  proof = source_proof(source_repo, source, store/'source-proof')
  pol = policy.policy()
  p.persist(store/'policy.json', pol)
  p.persist(store/'source-provenance.json', proof)
  bindings = []
  selected_sources = {}
  excluded_sources = {}
  for route in routes:
    items = manifest['routes'][route['route_id']]
    if [s['ordinal'] for s in items] != list(range(len(items))) or any(s['kind'] not in ('rlog.zst', 'qlog.zst') for s in items):
      raise ValueError('COMPLETE_CANONICAL_RLOG_LINEAGE_REQUIRED')
    digests = sorted(s['source_sha256'] for s in items)
    if len(set(digests)) != len(items) or p.sha(p.canonical(digests)) != route['source_set_sha256']:
      raise ValueError('EXACT_PINNED_SEGMENT_SET_REQUIRED')
    oldroute = policy.read(v2_store/'routes'/(route['route_id']+'.json'))
    check = next(r for r in cache['routes'] if r['route_id'] == route['route_id'])
    if oldroute['receipt_sha256'] != check['route_receipt_sha256']:
      raise ValueError('HISTORICAL_ROUTE_RECEIPT_DRIFT')
    for segment in items:
      prior = policy.read(source_store/'segments'/route['source_commit']/(segment['source_sha256']+'.json'))
      if prior['receipt_sha256'] != segment['metadata_sha256'] or prior['status'] != 'SOURCE_SPECIFIC_METADATA_REVALIDATED':
        raise ValueError('METADATA_RECEIPT_DRIFT')
      oldsegment = next(r for r in oldroute['segments'] if r['source_sha256'] == segment['source_sha256'])
      opening = policy.read(v2_store/'openings'/route['route_id']/(segment['source_sha256']+'.json'))
      if (opening['source_sha256'] != segment['source_sha256']
          or opening['split_sha256'] != split['receipt_sha256'] or opening['authorization_sha256'] != auth0['receipt_sha256']
          or oldsegment['status'] != 'EXTRACTED'):
        raise ValueError('HISTORICAL_OPENING_RECEIPT_DRIFT')
    allowed = [s for s in items if s['kind'] == 'rlog.zst']
    excluded = [{'source_sha256': s['source_sha256'], 'ordinal': s['ordinal'], 'kind': s['kind'],
                 'reason': 'QLOG_NUMERIC_REOPENING_NOT_AUTHORIZED'} for s in items if s['kind'] != 'rlog.zst']
    selected_sources[route['route_id']] = allowed
    excluded_sources[route['route_id']] = excluded
    bindings.append({**route, 'segment_count': len(allowed), 'historical_segment_count': len(items),
                     'excluded_sources': excluded,
                     'segment_set_sha256': p.sha(p.canonical(sorted(s['source_sha256'] for s in allowed))),
                     'historical_segment_set_sha256': p.sha(p.canonical(digests)),
                     'route_receipt_sha256': oldroute['receipt_sha256'], 'holdout_allowed': False})
  route_set = p.seal({'schema': 'EMPIRICAL_CAUSAL_TRAIN_DEV_ROUTE_SET_V1', 'routes': bindings,
    'policy_sha256': pol['receipt_sha256'], 'numeric_opened_before_route_set': False,
    'zero_support_development': 'V2_ZERO_SUPPORT_DEVELOPMENT_CONTEXT_ONLY_EXCLUDED',
    'source_semantics_sha256': split['source_equivalence_sha256']})
  authorization = p.seal({'schema': 'EMPIRICAL_CAUSAL_NUMERIC_AUTHORIZATION_V1',
    'route_set_sha256': route_set['receipt_sha256'], 'policy_sha256': pol['receipt_sha256'],
    'segments': {rid: sorted(s['source_sha256'] for s in segments) for rid, segments in selected_sources.items()},
    'excluded_sources': excluded_sources,
    'source_fingerprint_sha256': source['receipt_sha256'], 'source_provenance_sha256': proof['receipt_sha256'],
    'recorded_adapter_sha256': adapter['receipt_sha256'], 'numeric_adapter_sha256': pol['executor_sources']['reader'],
    'source_schema_sha256': p.sha(p.canonical({k: v['file_sha256'] for k, v in source['files'].items() if k.startswith('schema_')})),
    'full_carparams_sha256': routes[0]['full_carparams_sha256'], 'empirical_profile_sha256': routes[0]['empirical_profile_sha256'],
    'signal_whitelist_sha256': p.sha(p.canonical(policy.WHITELIST)),
    'alignment_policy_sha256': pol['executor_sources']['alignment'], 'causal_schema_sha256': policy.INPUT_PINS['empirical-causal-context-schema-v2.json'],
    'h1_mapping_policy_sha256': p.sha(p.canonical(mapping())), 'privacy_policy_sha256': p.sha(pol['privacy'].encode()),
    'output_store_identity_sha256': p.sha(str(store).encode()), 'execution_source_sha256': p.sha(p.canonical(policy.code_identity())),
    'historical_tree_sha256': trees,
    'numeric_opening_scope': 'EXACT_TWO_RETROSPECTIVE_POOL_ROUTES_PINNED_RLOG_SEGMENTS_ONLY',
    'holdout_opening_allowed': False})
  # Both seals exist before any numeric decoder is invoked.
  p.persist(store/'route-set.json', route_set)
  p.persist(store/'authorization.json', authorization)
  p.persist(store/'source-manifest.json', p.seal({'schema': 'EMPIRICAL_CAUSAL_PRIVATE_SOURCE_MANIFEST_V1',
    'authorization_sha256': authorization['receipt_sha256'],
    'routes': selected_sources, 'excluded_sources': excluded_sources}))
  return route_set, authorization


def mapping():
  return {'schema': 'EMPIRICAL_CAUSAL_TO_H1_MAPPING_V1',
    'base_h1_sha256': policy.INPUT_PINS['cyber-lateral-observability-contract-v1.json'],
    'base_causal_schema_sha256': policy.INPUT_PINS['empirical-causal-context-schema-v2.json'],
    'future_only_schema_execution': 'NEW_AUTHORIZED_GENERATION_ONLY_NO_HISTORICAL_REGENERATION',
    'requested_torque': 'control.requested', 'controller_limited_torque': 'command.normalized',
    'torqueOutputCan': 'command.raw', 'steering_angle': 'state.angle_deg', 'steering_rate': 'state.rate',
    'steeringPressed': 'state.driver_pressed', 'driver_torque': 'state.driver_torque', 'active': 'control.lat_active',
    'config_sequence': 'config_sequence', 'config_sha256': 'SEGMENT_CONFIG_RECEIPT',
    'consumed_input_snapshot_sha256': 'consumed_input_snapshot_sha256',
    'events': 'SEGMENT_BOUNDARY_ACTIVE_RISING_FALLING_PRESSED_RISING_FALLING_SOURCE_TRANSITIONS',
    'service_health': 'SOURCE_EVENT_PRESENT_VALID_AGE_NEW_EVENT_GAP_NOT_LIVE_SUBMASTER',
    'source_message_identity': 'SEGMENT_CONTENT_SHA_EVENT_STREAM_MESSAGE_INDEX_AND_PUBLISH_CLOCK',
    'decision_time': None, 'process_epoch': 'LOGGER_START_RECEIPT_IDENTITY_NOT_LIVE_CONTROLLER_EPOCH',
    'actual_curvature': None, 'desired_curvature': None, 'physical_applied_torque': None,
    'unavailable': policy.UNAVAILABLE, 'production_observer': False, 'plant_output': None}


def compare_legacy(arrays, stats, historical, bridge):
  old = historical['aligned']['rows']
  checks = {'row_count': len(old) == stats['total_grid_samples']}
  checks['grid_order'] = arrays['grid_time_ns'].tolist() == [r['grid_time_ns'] for r in old]
  checks['state_clock'] = arrays['state.time_ns'].tolist() == [r['state_time_ns'] for r in old]
  checks['diagnostic_mask'] = arrays['legacy_diagnostic_valid'].tolist() == [r['actuator_valid'] for r in old]
  checks['reason_sets'] = arrays['legacy_reason_bits'].tolist() == [
    sum(1 << alignment.REASONS.index(x) for x in r['reasons'] if x != 'YAW_UNAVAILABLE') for r in old]
  checks['speed_bin'] = arrays['speed_bin'].tolist() == [r['speed_bin'] or '' for r in old]
  valid = arrays['legacy_diagnostic_valid']
  checks['valid_angle'] = arrays['state.angle_deg'][valid].tolist() == [r['angle_deg'] for r in old if r['actuator_valid']]
  checks['valid_command'] = arrays['command.raw'][valid].tolist() == [r['command_raw'] for r in old if r['actuator_valid']]
  checks['support'] = all(stats['bins'][b][k] == historical['coverage']['bins'][b][k]
    for b in alignment.BINS for k in ('total_grid_samples', 'diagnostic_valid', 'contiguous_runs', 'common_design_rows'))
  checks['bridge'] = all(bridge[k] == historical['bridge'][k] for k in (
    'total', 'eligible', 'invalid', 'steer_max', 'exact_ratio_match_count', 'float32_expected_exact_count',
    'sign_conflicts', 'domain_conflicts', 'raw_saturated_count', 'normalized_saturated_count'))
  return checks


def extract(store, replica, v2_store, source_store, roots):
  store, v2_store, source_store = map(storage.safe, (store, v2_store, source_store))
  if replica not in ('repeat-1', 'repeat-2'):
    raise ValueError('EXACT_EXECUTION_REPLICA_REQUIRED')
  pol, route_set, auth, manifest = (policy.read(store/n) for n in ('policy.json', 'route-set.json', 'authorization.json', 'source-manifest.json'))
  if pol != policy.policy() or route_set['policy_sha256'] != pol['receipt_sha256'] or auth['route_set_sha256'] != route_set['receipt_sha256']:
    raise ValueError('SEALED_POLICY_EXECUTOR_DRIFT')
  if manifest['authorization_sha256'] != auth['receipt_sha256'] or auth['output_store_identity_sha256'] != p.sha(str(store).encode()):
    raise ValueError('AUTHORIZATION_STORE_MANIFEST_DRIFT')
  expected = policy.resolve_routes()
  if [r['route_id'] for r in route_set['routes']] != [r['route_id'] for r in expected]:
    raise ValueError('DECODER_EXACT_TWO_ROUTE_GATE')
  old_manifest = policy.read(v2_store/'manifest.json')
  for route in route_set['routes']:
    rid = route['route_id']
    allowed = [s for s in old_manifest['routes'][rid] if s['kind'] == 'rlog.zst']
    if manifest['routes'][rid] != allowed or auth['segments'][rid] != sorted(s['source_sha256'] for s in allowed):
      raise ValueError('DECODER_EXACT_PINNED_SEGMENT_GATE')
  approved = previous.approved_root_map(roots)
  destination = storage.external(store/replica, [v2_store, source_store, *approved.values()])
  results = []
  for route in route_set['routes']:
    rid, commit = route['route_id'], route['source_commit']
    source = policy.read(source_store/'fingerprints'/(commit+'.json'))
    adapter = policy.read(source_store/'adapters-final'/(commit+'.json'))
    policy.validate_source(route, source, adapter, policy.read(source_store/'public-origin.json'))
    schema = metadata.schema_from_source(source, source_store/'schemas'/commit)
    offset, config_sha, segments = 0, None, []
    route_commands = []
    for segment in manifest['routes'][rid]:
      digest = segment['source_sha256']
      policy.require_segment(auth, rid, digest)
      path = previous.source_location(segment['location'], approved)
      if path.name != 'rlog.zst' or logs.file_sha(path) != digest:
        raise ValueError('SOURCE_SEGMENT_HASH_DRIFT')
      historic_meta = policy.read(source_store/'segments'/commit/(digest+'.json'))
      if historic_meta['receipt_sha256'] != segment['metadata_sha256']:
        raise ValueError('SOURCE_METADATA_DRIFT')
      out = destination/'routes'/rid/'segments'/digest
      if (out/'receipt.json').exists():
        record = policy.read(out/'receipt.json')
        if (record['authorization_sha256'] != auth['receipt_sha256'] or record['route_global_start'] != offset
            or record['route_id'] != rid or record['segment_sha256'] != digest or record['ordinal'] != segment['ordinal']):
          raise ValueError('STALE_SEGMENT_RESUME')
        for field, binding in record['arrays'].items():
          storage.safe(out/'arrays'/(field+'.npy'))
          if p.sha((out/'arrays'/(field+'.npy')).read_bytes()) != binding['file_sha256']:
            raise ValueError('RESUME_ARRAY_DRIFT')
        opening = policy.read(out/'opening.json')
        if (opening['receipt_sha256'] != record['opening_sha256'] or opening['authorization_sha256'] != auth['receipt_sha256']
            or opening['route_id'] != rid or opening['segment_sha256'] != digest or opening['role'] != policy.ROLE
            or opening['holdout_opened'] is not False):
          raise ValueError('RESUME_OPENING_RECEIPT_DRIFT')
        config = policy.read(out/'config.json')
        if config['receipt_sha256'] != record['config_sha256']:
          raise ValueError('RESUME_CONFIG_DRIFT')
        storage.safe(out/'source-command.npy')
        if p.sha((out/'source-command.npy').read_bytes()) != record['source_command_array']['file_sha256']:
          raise ValueError('RESUME_SOURCE_COMMAND_DRIFT')
        commands = np.load(out/'source-command.npy', allow_pickle=False)
        route_commands.extend({'raw': float(x[0]), 'normalized': float(x[1]), 'valid': bool(x[2])} for x in commands)
      else:
        opening = p.seal({'schema': 'EMPIRICAL_CAUSAL_EXTRACTION_OPENING_V1', 'authorization_sha256': auth['receipt_sha256'],
                          'route_set_sha256': route_set['receipt_sha256'], 'route_id': rid, 'segment_sha256': digest,
                          'role': policy.ROLE, 'holdout_opened': False})
        p.persist(out/'opening.json', opening)
        streams = reader.numeric(logs.log_events(path, schema))
        config = reader.configuration(streams, route)
        if config['logger_start_sha256'] != historic_meta['metadata']['init']['logger_start_sha256']:
          raise ValueError('LOGGER_START_IDENTITY_CONFLICT')
        p.persist(out/'config.json', config)
        arrays, coverage = alignment.build(streams, config['receipt_sha256'], segment['ordinal'], offset)
        bridge = reader.bridge(streams['command'], config['runtime_steer_max'])
        historical = policy.read(v2_store/'segments'/rid/(digest+'.json'))
        legacy = compare_legacy(arrays, coverage, historical, bridge)
        if (historical['adapter_sha256'] != adapter['receipt_sha256'] or historical['runtime_steer_max'] != 409
            or historical['source_sha256'] != digest or historical['role'] != 'TRAIN'):
          raise ValueError('HISTORICAL_NUMERIC_CACHE_IDENTITY_DRIFT')
        if historical['receipt_sha256'] not in {r['receipt_sha256'] for r in policy.read(v2_store/'routes'/(rid+'.json'))['segments']}:
          raise ValueError('LEGACY_SEGMENT_RECEIPT_DRIFT')
        fields = {name: storage.array_write(out/'arrays'/(name+'.npy'), array) for name, array in sorted(arrays.items())}
        command_array = np.asarray([[r['raw'], r['normalized'], r['valid']] for r in streams['command']], dtype='<f8').reshape(-1, 3)
        command_binding = storage.array_write(out/'source-command.npy', command_array)
        route_commands.extend(streams['command'])
        record = p.seal({'schema': 'EMPIRICAL_CAUSAL_SEGMENT_EXTRACTION_V1', 'route_id': rid, 'segment_sha256': digest,
          'ordinal': segment['ordinal'], 'metadata_sha256': historic_meta['receipt_sha256'],
          'historical_segment_sha256': historical['receipt_sha256'], 'route_receipt_sha256': route['route_receipt_sha256'],
          'source_fingerprint_sha256': source['receipt_sha256'], 'recorded_adapter_sha256': adapter['receipt_sha256'],
          'numeric_adapter_sha256': pol['executor_sources']['reader'], 'authorization_sha256': auth['receipt_sha256'],
          'opening_sha256': opening['receipt_sha256'], 'config_sha256': config['receipt_sha256'],
          'route_global_start': offset, 'arrays': fields, 'source_command_array': command_binding,
          'coverage': coverage, 'bridge': bridge, 'legacy_checks': legacy,
          'unavailable_fields': policy.UNAVAILABLE, 'null_encoding': 'FLOAT_NAN_OR_NEGATIVE_INDEX_WITH_EXPLICIT_AVAILABILITY_MASK',
          'raw_event_decode': 'WHITELIST_ONLY', 'model_operations': 'NOT_RUN'})
        # Commit last: interrupted arrays are reconciled byte-for-byte on rerun.
        p.persist(out/'receipt.json', record)
      if config_sha is not None and record['config_sha256'] != config_sha:
        raise ValueError('ROUTE_CONFIG_DRIFT')
      config_sha = record['config_sha256']
      if logs.file_sha(path) != digest:
        raise ValueError('SOURCE_CHANGED_DURING_EXTRACTION')
      offset += record['coverage']['total_grid_samples']
      segments.append(record)
      print(replica, 'route', len(results)+1, 'segment', len(segments), '/', route['segment_count'], flush=True)
    summary = route_summary(route, segments, reader.bridge(route_commands, 409), destination/'routes'/rid)
    p.persist(destination/'routes'/rid/'route-receipt.json', summary)
    results.append(summary)
  final = p.seal({'schema': 'EMPIRICAL_CAUSAL_PRIVATE_DATASET_MANIFEST_V1',
    'authorization_sha256': auth['receipt_sha256'], 'route_set_sha256': route_set['receipt_sha256'],
    'routes': results, 'solver': 'NOT_USED', 'environment': {'python': platform.python_version(), 'numpy': np.__version__,
      'threads': 1, 'rng': 'NONE'}, 'model_fitting': 'NOT_RUN', 'holdout_opened': False})
  p.persist(destination/'manifest.json', final)
  return final


def route_summary(route, segments, bridge, route_store):
  counts = Counter()
  field_counts = Counter()
  bin_counts = {b: Counter() for b in alignment.BINS}
  reasons, run_lengths = Counter(), Counter()
  for s in segments:
    c = s['coverage']
    for k in ('total_grid_samples', 'diagnostic_valid', 'causal_required_valid', 'causal_runs', 'gyro_xyz_available',
              'gyro_acquisition_clock_failures', 'gyro_rejected', 'simultaneous_command_coverage'):
      counts[k] += c[k]
    field_counts.update(c['required_field_coverage'])
    reasons.update(c['mask_reason_counts'])
    run_lengths.update(c['causal_run_length_distribution'])
    for b in alignment.BINS:
      bin_counts[b].update({k: v for k, v in c['bins'][b].items() if k != 'longest_contiguous_samples'})
  all_fields = Counter()
  transitions = Counter()
  for s in segments:
    all_fields.update(s['coverage']['field_coverage'])
    transitions.update(s['coverage']['transitions'])
  ages = {}
  for kind in ('state', 'command', 'control', 'gyro'):
    values = []
    for s in segments:
      base = route_store/'segments'/s['segment_sha256']/'arrays'
      age = np.load(base/(kind+'.age_ns.npy'), allow_pickle=False)
      present = np.load(base/(kind+'.present.npy'), allow_pickle=False)
      values.append(age[present])
    ages[kind] = alignment.distribution(np.concatenate(values))
  ordering = Counter()
  for s in segments:
    ordering.update(s['coverage']['request_output_order'])
  historical = next(r for r in policy.inputs()['empirical-plant-v3-route-coverage-v1.json']['routes'] if r['route_id'] == route['route_id'])
  full_lineage = not route['excluded_sources'] and len(segments) == route['historical_segment_count']
  aggregate_checks = {'full_historical_segment_set': full_lineage,
    'grid_count': counts['total_grid_samples'] == historical['coverage']['total_grid_samples'],
    'diagnostic_valid': counts['diagnostic_valid'] == historical['coverage']['diagnostic_valid'],
    'bridge_counts': all(bridge[k] == historical['bridge'][k] for k in (
      'total', 'eligible', 'invalid', 'steer_max', 'exact_ratio_match_count', 'float32_expected_exact_count',
      'sign_conflicts', 'domain_conflicts', 'raw_saturated_count', 'normalized_saturated_count')),
    'per_bin_common_support': all(bin_counts[b]['common_design_rows'] == historical['coverage']['bins'][b]['common_design_rows'] for b in alignment.BINS)}
  all_legacy = all(all(s['legacy_checks'].values()) for s in segments) and all(aggregate_checks.values())
  ready = bridge['status'] == 'ROUTE_COMMAND_BRIDGE_CONFIRMED' and all_legacy and all(field_counts[k] > 0 for k in alignment.REQUIRED)
  return p.seal({'schema': 'EMPIRICAL_CAUSAL_ROUTE_DATASET_V1', 'route_id': route['route_id'], 'role': policy.ROLE,
    'source_commit': route['source_commit'], 'full_carparams_sha256': route['full_carparams_sha256'],
    'empirical_profile_sha256': route['empirical_profile_sha256'], 'config_sha256': segments[0]['config_sha256'],
    'segment_count': len(segments), 'historical_segment_count': route['historical_segment_count'],
    'excluded_sources': route['excluded_sources'], 'segments': [s['receipt_sha256'] for s in segments],
    'aggregate_legacy_checks': aggregate_checks, 'per_segment_legacy_reproduction_exact': all(all(s['legacy_checks'].values()) for s in segments),
    'coverage': dict(counts), 'required_field_coverage': dict(field_counts), 'bins': {b: dict(v) for b, v in bin_counts.items()},
    'mask_reason_counts': dict(reasons), 'causal_run_length_distribution': dict(run_lengths),
    'field_coverage': dict(all_fields), 'transitions': dict(transitions), 'source_age': ages, 'request_output_order': dict(ordering),
    'longest_causal_run': max(s['coverage']['longest_causal_run'] for s in segments),
    'legacy_reproduction_exact': all_legacy, 'bridge': bridge,
    'status': 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_READY' if ready else 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_BLOCKED',
    'holdout_allowed': False, 'independent_validation_allowed': False})


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--store', required=True)
  parser.add_argument('--v2-store', required=True)
  parser.add_argument('--v3-store', required=True)
  parser.add_argument('--source-store', required=True)
  parser.add_argument('--source-repo', required=True)
  parser.add_argument('--root', action='append', required=True)
  parser.add_argument('--replica', choices=('repeat-1', 'repeat-2'), required=True)
  args = parser.parse_args()
  prepare(args.store, args.v2_store, args.v3_store, args.source_store, args.source_repo, args.root)
  extract(args.store, args.replica, args.v2_store, args.source_store, args.root)


if __name__ == '__main__':
  main()
