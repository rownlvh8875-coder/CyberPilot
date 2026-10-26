"""Receipt-only ledger and conservative pools. No raw reader or numeric executor."""

from collections import Counter
import json
import subprocess
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_prior_use as u
from openpilot.tools.cyber_autotune import empirical_salvage_policy as policy


def reservation_candidate(routes):
  eligible = [
    x
    for x in routes
    if x.get('prior_use_state') == 'PIPELINE_UNTOUCHED_PROVABLE'
    and all(x.get(k) is True for k in ('metadata_complete', 'source_compatible', 'required_messages'))
    and all(isinstance(x.get(k), str) and len(x[k]) == 64 for k in ('source_class_sha256', 'full_carparams_sha256', 'lineage_sha256'))
  ]
  return min(eligible, key=lambda x: (-x['segment_count'], not x['exact_source'], x['route_id'])) if eligible else None


def reservation(route, ledger_sha):
  if route is None:
    return None
  if reservation_candidate([route]) is None:
    raise ValueError('PROVABLE_PIPELINE_UNTOUCHED_ONLY')
  return p.seal(
    {
      'schema': 'EMPIRICAL_PIPELINE_HOLDOUT_RESERVATION_V1',
      'route_id': route['route_id'],
      'source_class_sha256': route['source_class_sha256'],
      'full_carparams_sha256': route['full_carparams_sha256'],
      'lineage_sha256': route['lineage_sha256'],
      'ledger_sha256': ledger_sha,
      'role': 'PIPELINE_HOLDOUT',
      'tier': 'PIPELINE_UNTOUCHED_ENGINEERING_HOLDOUT',
      'numeric_opened': False,
      'opening_state': 'CLOSED',
      'opening_count': 0,
      'independent_qualification_allowed': False,
      'one_time_receipt_required': True,
      'engineering_evaluation_allowed': 'FUTURE_CONDITIONAL_SEPARATE_AUTHORIZATION',
    }
  )


def future_mapping():
  names = ('empirical-causal-context-schema-v2.json', 'cyber-lateral-observability-contract-v1.json')
  parents = {name: p.sha((p.PUBLIC / name).read_bytes()) for name in names}
  return p.seal(
    {
      'schema': 'EMPIRICAL_CAUSAL_H1_SALVAGE_MAPPING_V1',
      'parents_file_sha256': parents,
      'scope': 'FUTURE_GENERATIONS_ONLY',
      'numeric_extraction_executed': False,
      'production_observer_implemented': False,
      'historical_regeneration': False,
      'mappings': {
        'requested_torque': 'SOURCE_PROVEN_REQUESTED_NORMALIZED_TORQUE_NOT_POST_LIMIT_INTENT',
        'controller_limited_torque': 'POST_CARCONTROLLER_NORMALIZED_TORQUE',
        'torque_output_can': 'LOGGED_POST_CONTROLLER_REPRESENTATION_NOT_EPS_ACK',
        'steering_angle_rate': 'ACTUAL_SOURCE_SAMPLES_WITH_HISTORY_NOT_FINITE_COUNTS',
        'driver_context': 'STEERING_PRESSED_DRIVER_TORQUE_ACTIVE_RESET_INTERVENTION',
        'yaw_gyro': 'RAW_MEASUREMENT_SOURCE_UNITS_AXES_ACQUISITION_AND_PUBLISH_CLOCKS',
        'causal_origin': 'ROUTE_SEGMENT_ALIGNED_RUN_WITHIN_RUN_DESIGN_ROW_RECEIPT',
        'time_order': 'LATEST_PAST_100_HZ_MAX_20_MS_NO_FUTURE_SAMPLE',
        'source_identity': 'EXACT_SOURCE_CLASS_CONFIG_PROFILE_ADAPTER_POLICY_SHA',
      },
      'missing': 'NULL_WITH_REASON_NEVER_FALSE_OR_ZERO',
      'forbidden_inputs': [
        'modelV2',
        'planner',
        'path',
        'lane',
        'liveCalibration',
        'cameraOdometry',
        'liveLocationKalman',
        'future_target',
        'candidate_result_label',
      ],
    }
  )


def read_private(root, name):
  return u.read_receipt(root, [root], name)


def public_uses(row, known):
  """References are not opening proof; extract only exact named route IDs."""
  found = set()
  if isinstance(row, dict):
    for key, value in row.items():
      if key in ('route_id', 'train_route', 'development_route') and isinstance(value, str) and value in known:
        found.add(value)
      elif key == 'route_ids' and isinstance(value, list):
        found.update(x for x in value if isinstance(x, str) and x in known)
      elif isinstance(value, (dict, list)):
        found.update(public_uses(value, known))
  elif isinstance(row, list):
    for value in row:
      found.update(public_uses(value, known))
  return found


def train_dev_sufficient(groups):
  return any(len(set(routes)) >= 2 for routes in groups.values())


def completeness_blockers(registry, stores):
  blockers = []
  if registry.get('carrot_simulator_evidence_registry_complete') is not True:
    blockers.append('SIMULATOR_PRIVATE_EVIDENCE_LOCATION_REGISTRY_INCOMPLETE')
  blockers += sorted({x['status'] for x in stores if x['status'] != 'FILESYSTEM_METADATA_INVENTORIED'})
  if registry.get('legacy_route_alias_reconciliation_complete') is not True:
    blockers.append('LEGACY_NON_EMPIRICAL_PRIVATE_RECEIPT_ROUTE_ALIAS_RECONCILIATION_INCOMPLETE')
  return blockers


def baseline_public_inputs():
  repo = p.PUBLIC.parents[2]
  prefix = ['git', '-C', str(repo)]
  directory = p.PUBLIC.relative_to(repo).as_posix()
  names = subprocess.check_output([*prefix, 'ls-tree', '-r', '--name-only', policy.BASELINE, '--', directory])
  for name in sorted(names.decode().splitlines()):
    if name.endswith('.json'):
      raw = subprocess.check_output([*prefix, 'show', f'{policy.BASELINE}:{name}'])
      yield Path(name).name, raw


def public_receipt(name):
  return p.verify(json.loads((p.PUBLIC / name).read_bytes()))


def derive(store, output=None):
  store = u.no_alias(store)
  output = u.no_alias(output) if output else store
  registry = p.verify(json.loads((store / 'registry.json').read_bytes()))
  frozen = p.verify(json.loads((store / 'policy.json').read_bytes()))
  if frozen != policy.policy():
    raise ValueError('FROZEN_SALVAGE_POLICY_DRIFT')
  fs = p.verify(json.loads((store / 'store-filesystem-inventory.json').read_bytes()))
  roots = {Path(x['path']).name: Path(x['path']) for x in registry['stores']}
  inventory = read_private(roots['additional-root-metadata-v1'], 'combined-inventory.json')
  if inventory['receipt_sha256'] != 'e4c796ef3211e8c0d7be1094e80e8e4845ba255398764992b1da5db640e46c2b':
    raise ValueError('EXACT_HISTORICAL_METADATA_INVENTORY_REQUIRED')
  prior = p.verify(json.loads((p.PUBLIC / 'empirical-source-route-reclassification-v1.json').read_bytes()))
  classified = {x['route_id']: x for x in prior['routes']}
  routes = inventory['routes']
  records = {x['route_id']: [] for x in routes}
  identities = {x['route_id']: p.sha(p.canonical(x['generation'])) for x in routes}
  for row in routes:
    records[row['route_id']].append(u.use_record('CYBERPILOT', 'CROSS_ROOT_METADATA_V1', 'METADATA_ONLY', inventory, identities[row['route_id']]))
  # Private opening receipts, not public absences, establish numeric access.
  v2 = roots['empirical-plant-v2-train-dev-v1']
  split = read_private(v2, 'split.json')
  authoritative_split = public_receipt('empirical-plant-v2-train-dev-split-v1.json')
  authorization = public_receipt('empirical-plant-v2-numeric-authorization-v1.json')
  if split != authoritative_split or authorization['split_sha256'] != split['receipt_sha256']:
    raise ValueError('EXACT_V2_PUBLIC_SPLIT_AUTHORIZATION_REQUIRED')
  v2_roles = {x['route_id']: x['role'] for x in split['routes']}
  v2_bindings = {x['route_id']: x for x in split['routes']}
  manifest = read_private(v2, 'manifest.json')
  for rid, role in v2_roles.items():
    for item in manifest['routes'][rid]:
      opening = read_private(v2, Path('openings') / rid / (item['source_sha256'] + '.json'))
      if (
        opening['route_id'] != rid
        or opening['role'] != role
        or opening['split_sha256'] != split['receipt_sha256']
        or opening['authorization_sha256'] != authorization['receipt_sha256']
        or opening['source_sha256'] != item['source_sha256']
      ):
        raise ValueError('NUMERIC_OPENING_IDENTITY_CONFLICT')
      records[rid].append(u.use_record('CYBERPILOT', 'EMPIRICAL_PLANT_V2_TRAIN_DEV', role, opening, identities[rid], numeric=True))
  # Each private V3 fold receipt binds TRAIN fit and opposite-route DEVELOPMENT evaluation.
  v3 = roots['empirical-plant-v3-route-cv-v1']
  folds = read_private(v3, 'folds.json')
  if folds != public_receipt('empirical-plant-v3-folds-v1.json'):
    raise ValueError('EXACT_V3_PUBLIC_FOLDS_REQUIRED')
  cv = public_receipt('empirical-plant-v3-stage-a-cv-results-v1.json')
  expected_results = {}
  for speed_bin, data in cv['bins'].items():
    for candidate in data['candidates']:
      for result in candidate['folds']:
        config = candidate['config']
        expected_results[(speed_bin, config['family'], config['delay_samples'], result['fold'])] = result['private_result_sha256']
  expected_folds = {x['fold']: x for x in folds['folds']}
  receipts = sorted(v3.glob('folds/STAGE_A/*/*/*/receipt.json'))
  if len(receipts) != 48:
    raise ValueError('COMPLETE_V3_PRIVATE_FOLD_RECEIPT_SET_REQUIRED')
  for file in receipts:
    result = read_private(v3, file.relative_to(v3))
    identity = (result['speed_bin'], result['config']['family'], result['config']['delay_samples'], result['fold'])
    if (
      expected_results.get(identity) != result['receipt_sha256']
      or result['policy_sha256'] != folds['policy_sha256']
      or result['stage'] != 'STAGE_A'
      or file.parent.name != result['fold']
      or file.parent.parent.parent.name != result['speed_bin']
    ):
      raise ValueError('EXACT_V3_PUBLIC_EXECUTED_RESULT_REQUIRED')
    assignment = expected_folds[result['fold']]
    if any(result[key] != assignment[key] for key in ('train_route', 'development_route')):
      raise ValueError('V3_EXECUTED_FOLD_ROUTE_CONFLICT')
    for role, key in (('TRAIN', 'train_route'), ('DEVELOPMENT', 'development_route')):
      rid = result[key]
      records[rid].append(
        u.use_record(
          'CYBERPILOT',
          'EMPIRICAL_PLANT_V3_ROUTE_CV',
          role,
          result,
          identities[rid],
          numeric=True,
          fitting=role == 'TRAIN',
          selection=role == 'DEVELOPMENT',
          evaluation=role == 'DEVELOPMENT',
        )
      )
  # V1 used a different opaque-ID construction. Canonical V1 overlap anchor unifies it.
  v1routes = [x for x in routes if x['v1_overlap']]
  if len(v1routes) != 1:
    raise ValueError('EXACT_V1_OVERLAP_ANCHOR_REQUIRED')
  canonical_v1 = v1routes[0]['route_id']
  v1 = roots['empirical-plant-v1']
  v1split = read_private(v1, 'split.json')
  holdout = read_private(v1, 'holdout-opening.json')
  for role in sorted({x['role'] for x in v1split['segments']}):
    records[canonical_v1].append(
      u.use_record(
        'CYBERPILOT',
        'EMPIRICAL_PLANT_V1',
        role,
        holdout if role == 'HOLDOUT' else v1split,
        identities[canonical_v1],
        numeric=role != 'EMBARGO',
        fitting=role == 'TRAIN',
        selection=role == 'DEVELOPMENT',
        evaluation=role == 'HOLDOUT',
        holdout=role == 'HOLDOUT',
      )
    )
  public_counts = Counter()
  for _, raw in baseline_public_inputs():
    row = json.loads(raw)
    for rid in public_uses(row, records):
      public_counts[rid] += 1
  blockers = completeness_blockers(registry, fs['stores'])
  complete = u.closure_complete(registry, blockers)
  rows = []
  for original in routes:
    rid = original['route_id']
    corrected = classified.get(rid, {})
    identity_ok = corrected.get('classification') == 'ROUTE_SOURCE_AUDITED_IDENTITY_COMPLETE'
    compatible = corrected.get('signal_semantics_complete') is True and corrected.get('profile_complete') is True
    state = policy.prior_state(records[rid], complete, identity_ok)
    if original['status'] == 'ROUTE_CORRUPT_OR_INCOMPLETE' and not any(x['numeric_opened'] for x in records[rid]):
      state = 'CORRUPT_OR_INCOMPLETE'
    b = v2_bindings.get(rid, {})
    rows.append(
      {
        'route_id': rid,
        'generation_id': identities[rid],
        'source_commit': original['generation'].get('source_commit'),
        'full_carparams_sha256': corrected.get('full_carparams_sha256', original['generation'].get('carparams_sha256')),
        'empirical_profile_sha256': corrected.get('empirical_profile_sha256'),
        'source_class_sha256': corrected.get('semantic_class_id'),
        'lineage_sha256': b.get('lineage_sha256'),
        'identity_receipt_sha256': original['identity_receipt_sha256'],
        'metadata_complete': identity_ok,
        'source_compatible': compatible,
        'required_messages': None,
        'exact_source': compatible,
        'segment_count': original['segment_count'],
        'prior_use_state': state,
        'v1_overlap': original['v1_overlap'],
        'uses': records[rid],
        'public_reference_count_supporting_only': public_counts[rid],
        'numeric_coverage': None,
        'speed_coverage_potential': None,
        'steering_rate': 'SOURCE_AVAILABLE_RUNTIME_COVERAGE_NOT_OPENED' if compatible else 'SEMANTICS_PENDING',
        'gyro': 'SOURCE_AVAILABLE_DEVICE_FRAME_RUNTIME_COVERAGE_NOT_OPENED' if compatible else 'SEMANTICS_PENDING',
        'active_control': 'SOURCE_SCHEMA_AVAILABLE_RUNTIME_NOT_OPENED' if compatible else 'SEMANTICS_PENDING',
      }
    )
  ledger = p.seal(
    {
      'schema': 'EMPIRICAL_ROUTE_PRIOR_USE_LEDGER_V1',
      'policy_sha256': frozen['receipt_sha256'],
      'private_registry_sha256': registry['receipt_sha256'],
      'private_filesystem_receipt_sha256': fs['receipt_sha256'],
      'input_inventory_sha256': inventory['receipt_sha256'],
      'routes': rows,
      'state_counts': dict(Counter(x['prior_use_state'] for x in rows)),
      'private_store_audit_complete': complete,
      'completeness_blockers': blockers,
      'scope': 'CYBERPILOT_PIPELINE_UNTOUCHED_NOT_GLOBALLY_NEVER_ANALYZED',
      'numeric_payloads_opened': False,
      'holdout_opened': False,
      'v1_alias_mapping': 'EXACT_SINGLE_V1_OVERLAP_ANCHOR_FROM_PINNED_METADATA_CHAIN',
    }
  )
  p.persist(output / 'ledger.json', ledger)
  eligible = [x for x in rows if x['metadata_complete'] and x['source_compatible'] and not x['v1_overlap']]
  groups = {}
  for row in eligible:
    key = (row['source_class_sha256'], row['full_carparams_sha256'], row['empirical_profile_sha256'])
    groups.setdefault(key, []).append(row['route_id'])
  pools = p.seal(
    {
      'schema': 'EMPIRICAL_EXISTING_ROUTE_POOLS_V1',
      'ledger_sha256': ledger['receipt_sha256'],
      'pools': [
        {
          'source_class_sha256': key[0],
          'full_carparams_sha256': key[1],
          'empirical_profile_sha256': key[2],
          'train_candidates': sorted(ids),
          'development_candidates': sorted(ids),
          'candidate_pool_overlap_not_role_assignment': True,
          'future_train_dev_assignment_must_be_route_disjoint': True,
          'retrospective_development_limitation': True,
        }
        for key, ids in sorted(groups.items())
      ],
      'compatible_train_dev_candidate_count': len(eligible),
      'train_pool_expanded': False,
      'development_pool_expanded': False,
      'numeric_split_created': False,
      'pipeline_holdout_candidates': [x['route_id'] for x in rows if reservation_candidate([x])],
      'strict_independent_holdout_created': False,
      'numeric_coverage': None,
    }
  )
  p.persist(output / 'pools.json', pools)
  reserved = reservation(reservation_candidate(rows), ledger['receipt_sha256'])
  if reserved is not None:
    p.persist(output / 'pipeline-holdout-reservation.json', reserved)
  readiness = p.seal(
    {
      'schema': 'EMPIRICAL_EXISTING_DATA_READINESS_V1',
      'ledger_sha256': ledger['receipt_sha256'],
      'pools_sha256': pools['receipt_sha256'],
      'status': 'EXISTING_DATA_TRAIN_DEV_ONLY_STRICT_HOLDOUT_STILL_REQUIRED'
      if train_dev_sufficient(groups)
      else 'EXISTING_DATA_INSUFFICIENT_NEW_ROUTE_REQUIRED',
      'pipeline_holdout_status': 'PIPELINE_HOLDOUT_RESERVED' if reserved else 'NO_PROVABLE_PIPELINE_UNTOUCHED_ROUTE',
      'source_audit_status': 'ADDITIONAL_SOURCE_AUDIT_RECORDED_SEPARATELY',
      'new_collection_required_for_train_dev': not train_dev_sufficient(groups),
      'store_audit_complete': complete,
      'completeness_blockers': blockers,
      'numeric_extraction': 'NOT_RUN',
      'fitting': 'NOT_RUN',
      'model_selection': 'NOT_RUN',
      'holdout_opening': 'CLOSED',
      'opening_count': 0,
      'stage_b': 'STAGE_B_SIGNAL_ADMISSION_BLOCKED',
      'historical_ta': 'TA_STANDALONE_TRADEOFF_ONLY',
      'historical_sg': 'SG_CLOSED_LOOP_TRADEOFF_ONLY',
      'composition': 'COMPOSITION_NOT_RECOMMENDED',
      'empirical_track': 'CURRENT_ARX1_FIR25_SIMPLE_OBSERVATION_TRACK_CLOSED',
      'future_holdout': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
      'calibration_blockers': p.BLOCKERS,
      'vehicle': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
      'sealed_reference': 'NOT_GENERATED',
    }
  )
  p.persist(output / 'readiness.json', readiness)
  return {'ledger': ledger, 'pools': pools, 'readiness': readiness}
