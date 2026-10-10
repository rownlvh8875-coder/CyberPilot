"""Only aggregate metadata outcomes; no driving numeric data or private paths."""

from collections import Counter
from pathlib import Path
import re

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_dataset_v2_publication as historical
from openpilot.tools.cyber_autotune import empirical_additional_root_policy as policy
from openpilot.tools.cyber_autotune import empirical_cross_root_inventory as reader
from openpilot.tools.cyber_autotune import empirical_export_metadata as exports
from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as receipts

PINS = {}
STATUSES = {
  'ROUTE_DUPLICATE_EXISTING_V1',
  'ROUTE_COMPATIBLE_WITH_V1_GENERATION',
  'ROUTE_DIFFERENT_SOURCE_GENERATION',
  'ROUTE_DIFFERENT_CARPARAMS',
  'ROUTE_INCOMPATIBLE_CONTROL_TYPE',
  'ROUTE_CORRUPT_OR_INCOMPLETE',
  'ROUTE_IDENTITY_AMBIGUOUS',
}


def source_identity():
  return {Path(module.__file__).name: p.sha(Path(module.__file__).read_bytes()) for module in (policy, reader, exports)}


def public_generation(generation):
  if generation.get('status') == 'MIXED_METADATA_GENERATIONS':
    return {'status': 'MIXED_METADATA_GENERATIONS', 'observed_generations': [public_generation(x) for x in generation['observed_generations']]}
  result = {}
  patterns = {
    'source_commit': r'[0-9a-f]{40}',
    'os_version': r'[A-Za-z0-9_.+-]{1,80}',
    'fingerprint': r'[A-Za-z0-9_ .()+-]{1,100}',
    'control_type': r'(torque|angle)',
    'carparams_sha256': r'[0-9a-f]{64}',
    'software_profile_sha256': r'[0-9a-f]{64}',
  }
  for key, pattern in patterns.items():
    value = generation.get(key)
    if type(value) is str and re.fullmatch(pattern, value):
      result[key] = value
    else:
      result[key] = None
      result[key + '_opaque_sha256'] = p.sha(p.canonical(value))
  result['flags'] = generation.get('flags') if type(generation.get('flags')) is int and generation['flags'] >= 0 else None
  return result


def derive(private):
  p.verify(private)
  if (
    private.get('schema') != 'EMPIRICAL_CROSS_ROOT_PRIVATE_INVENTORY_V1'
    or private.get('numeric_payloads_opened') is not False
    or private.get('numeric_coverage') is not None
    or private.get('holdout_opened') is not False
  ):
    raise ValueError('METADATA_ONLY_RECEIPT_REQUIRED')
  routes = private['routes']
  for route in routes:
    if route['status'] not in STATUSES or route['compatibility'] not in STATUSES:
      raise ValueError('PUBLIC_STATUS_ENUM_REQUIRED')
    for key in ('route_id', 'identity_receipt_sha256'):
      policy.old.hash_required(route[key])
    for key in ('segment_count', 'duplicate_file_count', 'root_count'):
      if type(route[key]) is not int or route[key] < 0:
        raise ValueError('PUBLIC_ROUTE_COUNT_TYPE_REQUIRED')
    if type(route['v1_overlap']) is not bool or type(route['compatible']) is not bool:
      raise ValueError('PUBLIC_ROUTE_BOOLEAN_TYPE_REQUIRED')
    if route['compatible'] != (route['status'] == 'ROUTE_COMPATIBLE_WITH_V1_GENERATION'):
      raise ValueError('PUBLIC_COMPATIBILITY_CONFLICT')

  if any(x['untouched'] is not False or x['prior_analysis'] not in ('V1_PLANNING_CONTEXT_ONLY', 'ROUTE_PRIOR_ANALYSIS_STATUS_UNKNOWN') for x in routes):
    raise ValueError('NO_UNATTESTED_UNTOUCHED_CLAIM')
  if type(private.get('export_log_file_count', 0)) is not int or private.get('export_log_file_count', 0) < 0:
    raise ValueError('PUBLIC_EXPORT_COUNT_REQUIRED')
  for key in ('export_inventory_sha256', 'parent_inventory_sha256'):
    if private.get(key) is not None:
      policy.old.hash_required(private[key])
  expected_split = policy.metadata_split(
    [{'route_id': row['route_id'], 'compatible': row['compatible'], 'v1_overlap': row['v1_overlap'], 'prior_analysis': 'UNKNOWN'} for row in routes]
  )
  if private['split']['status'] != expected_split['status']:
    raise ValueError('COMBINED_METADATA_SPLIT_CONFLICT')
  counters = {
    'distinct_metadata_route_groups': len(routes),
    'v1_duplicate_route_groups': sum(x['v1_overlap'] for x in routes),
    'compatible_metadata_routes': sum(x['compatible'] for x in routes),
    'compatible_untouched_routes': sum(x['compatible'] and x['untouched'] for x in routes),
    'prior_analysis_unknown_routes': sum(x['prior_analysis'] == 'ROUTE_PRIOR_ANALYSIS_STATUS_UNKNOWN' for x in routes),
    'cross_root_route_groups': sum(x['root_count'] > 1 for x in routes),
    'route_groups_with_repeated_metadata': sum(x['duplicate_file_count'] > 0 for x in routes),
    'duplicate_selected_files': sum(x['duplicate_file_count'] for x in routes),
    'distinct_metadata_segments': sum(x['segment_count'] for x in routes),
    'metadata_failed_selected_files': private['failed_file_count'],
    'selected_metadata_files': private['selected_metadata_files'],
    'alternative_log_files_not_parsed': private['alternative_log_files_not_parsed'],
  }
  if any(type(value) is not int or value < 0 for value in counters.values()):
    raise ValueError('NONNEGATIVE_INTEGER_COUNTS_REQUIRED')
  snapshots = private['snapshot'].values()
  inventory = p.seal(
    {
      'schema': 'EMPIRICAL_DATASET_V2_CROSS_ROOT_INVENTORY_V1',
      'root_policy_sha256': policy.root_policy()['receipt_sha256'],
      'private_inventory_sha256': private['receipt_sha256'],
      'binding_sha256': private['binding_sha256'],
      'source_identity': source_identity(),
      **counters,
      'export_log_file_count': private.get('export_log_file_count', 0),
      'export_inventory_sha256': private.get('export_inventory_sha256'),
      'parent_inventory_sha256': private.get('parent_inventory_sha256'),
      'canonical_log_counts': {kind: sum(x['log_counts'].get(kind, 0) for x in snapshots) for kind in reader.LOGS},
      'filesystem_file_count': sum(x['file_count'] for x in snapshots),
      'media_file_count_metadata_only': sum(x['media_file_count_metadata_only'] for x in snapshots),
      'archive_count_not_opened': sum(x['archive_count'] for x in snapshots),
      'routes': reader.public_routes(routes),
      'numeric_coverage': None,
      'numeric_values_opened': False,
      'holdout_opened': False,
      'image_video_opened': False,
      'gps_payload_opened': False,
      'route_identity_interpretation': 'METADATA_LOGGER_GROUPS_OTHER_SOURCE_LOGGER_SEMANTICS_REQUIRE_AUDIT',
    }
  )
  buckets = p.seal(
    {
      'schema': 'EMPIRICAL_DATASET_V2_GENERATION_BUCKETS_V1',
      'inventory_sha256': inventory['receipt_sha256'],
      'buckets': [{**row, 'generation': public_generation(row['generation'])} for row in reader.buckets(routes)],
      'source_commit_distribution': dict(Counter(public_generation(x['generation']).get('source_commit') or 'UNKNOWN_OR_MIXED' for x in routes)),
      'carparams_distribution': dict(Counter(public_generation(x['generation']).get('carparams_sha256') or 'UNKNOWN_OR_MIXED' for x in routes)),
      'os_distribution': dict(Counter(public_generation(x['generation']).get('os_version') or 'UNKNOWN_OR_MIXED' for x in routes)),
      'control_type_distribution': dict(Counter(public_generation(x['generation']).get('control_type') or 'UNKNOWN_OR_MIXED' for x in routes)),
      'generation_merge_allowed': False,
      'numeric_coverage': None,
    }
  )
  distinct = [x for x in routes if not x['v1_overlap']]
  different = any(x['status'] == 'ROUTE_DIFFERENT_SOURCE_GENERATION' for x in distinct)
  if different:
    status, next_state = 'ADDITIONAL_ROUTES_FOUND_DIFFERENT_GENERATION', 'EMPIRICAL_DATASET_V2_NEW_SOURCE_AUDIT_REQUIRED'
  elif distinct or private['failed_file_count']:
    status, next_state = 'ROUTE_IDENTITY_AMBIGUOUS', 'PRIOR_ANALYSIS_AND_METADATA_IDENTITY_REVIEW_REQUIRED'
  elif routes:
    status, next_state = 'ONLY_DUPLICATE_OR_USED_ROUTES_FOUND', 'WAIT_FOR_UNTOUCHED_ROUTE_DATA'
  else:
    status, next_state = 'NO_ADDITIONAL_ROUTES_FOUND', 'WAIT_FOR_UNTOUCHED_ROUTE_DATA'
  ready = p.seal(
    {
      'schema': 'EMPIRICAL_DATASET_V2_ROUTE_READINESS_V1',
      'status': status,
      'next': next_state,
      'inventory_sha256': inventory['receipt_sha256'],
      'buckets_sha256': buckets['receipt_sha256'],
      'previous_readiness_sha256': historical.PINS['empirical-dataset-v2-readiness.json'],
      'previous_readiness_scope': 'FIRST_APPROVED_ROOT_ONLY_UNCHANGED',
      'split_status': private['split']['status'],
      'numeric_coverage': None,
      'numeric_extraction': 'NOT_RUN_NOT_AUTHORIZED',
      'support_computation': 'NOT_RUN_NOT_AUTHORIZED',
      'yaw_crosscheck': 'NOT_RUN_NOT_AUTHORIZED',
      'fitting': 'NOT_RUN_NOT_AUTHORIZED',
      'holdout_opened': False,
      'prior_analysis_unknown_holdout_allowed': False,
      'historical': p.policy()['historical'],
      'command_bridge': 'RAW_TO_NORMALIZED_COMMAND_CONFIRMED_UNCHANGED',
      'stage_a': 'EMPIRICAL_ACTUATOR_MODEL_ONLY',
      'yaw': 'EMPIRICAL_YAW_SIGNAL_PARTIAL',
      'yaw_unit': 'YAW_UNIT_LIKELY_NOT_CONFIRMED',
      'yaw_model': 'EMPIRICAL_YAW_MODEL_BLOCKED',
      'composition': 'COMPOSITION_NOT_AUTHORIZED',
      'composition_recommendation': 'COMPOSITION_NOT_RECOMMENDED',
      'search': 'SEARCH_NOT_AUTHORIZED',
      'frozen_evaluation': 'FROZEN_EVALUATION_NOT_AUTHORIZED',
      'calibration_blockers': p.BLOCKERS,
      'sealed_reference': 'NOT_GENERATED',
      'vehicle': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
    }
  )
  result = {
    'empirical-dataset-v2-root-policy-v2.json': policy.root_policy(),
    'empirical-dataset-v2-cross-root-inventory-v1.json': inventory,
    'empirical-dataset-v2-generation-buckets-v1.json': buckets,
    'empirical-dataset-v2-route-readiness-v1.json': ready,
  }
  if private['split']['status'] == 'ROUTE_DISJOINT_SPLIT_POSSIBLE':
    result['empirical-dataset-v2-metadata-split-v1.json'] = private['split']
  return result


def load():
  historical.load()
  if not PINS:
    raise ValueError('PUBLICATION_NOT_FROZEN')
  result = {name: receipts.read(p.PUBLIC / name) for name in PINS}
  if any(row['receipt_sha256'] != PINS[name] for name, row in result.items()):
    raise ValueError('ADDITIONAL_ROOT_RECEIPT_DRIFT')
  if result['empirical-dataset-v2-root-policy-v2.json'] != policy.root_policy():
    raise ValueError('ROOT_POLICY_V2_DRIFT')
  if result['empirical-dataset-v2-cross-root-inventory-v1.json']['source_identity'] != source_identity():
    raise ValueError('CROSS_ROOT_EXECUTOR_DRIFT')
  return result
