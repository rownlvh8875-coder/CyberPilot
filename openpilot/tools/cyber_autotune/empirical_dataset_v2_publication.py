"""Redacted V2 waiting evidence. Private inventory is never copied to publication."""

from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_signal_publication as history
from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as v
from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as inv
from openpilot.tools.cyber_autotune import empirical_route_eligibility as eligibility

PINS = {
  'empirical-dataset-v2-root-policy.json': '33f4e9e92d8306ad0982402a5ae25523810d1fb997674e4985a463afeedcec70',
  'empirical-dataset-v2-homogeneity-policy.json': 'a2d81bf5c786404c7a3aaa47f7d0c0b3163fa6821e35845762ba6b2fc607b847',
  'empirical-dataset-v2-split-policy.json': 'ba60c5e59fe5d093abab4c2ec81d96d2373d94e745195779623c84dbf67f0e8b',
  'empirical-route-eligibility-policy.json': 'ee0d9b7efd76790c7e8b0be66b0ef1cfc328c7dedadd779d4cfb4df3f327530b',
  'empirical-dataset-v2-route-inventory.json': '34275cadac3c634c096528011738953272fe0bddbda3a90d72eb837d3e1e3a99',
  'empirical-dataset-v2-readiness.json': '7d42caa4ededd64e0cc6075daa64bb970584862a17b25594369606f2c33dd63a',
}


def source_identity():
  return {Path(x.__file__).name: p.sha(Path(x.__file__).read_bytes()) for x in (v, inv, eligibility)}


def policies():
  return {
    'empirical-dataset-v2-root-policy.json': v.root_policy(),
    'empirical-dataset-v2-homogeneity-policy.json': v.homogeneity_policy(),
    'empirical-dataset-v2-split-policy.json': v.split_policy(),
    'empirical-route-eligibility-policy.json': v.eligibility_policy(),
  }


def readiness(inventory):
  return p.seal(
    {
      'schema': 'EMPIRICAL_DATASET_V2_READINESS',
      'status': 'EMPIRICAL_DATASET_V2_WAITING_FOR_NEW_ROUTE_DATA',
      'inventory_status': 'EMPIRICAL_DATASET_V2_ROUTE_INVENTORY_COMPLETE',
      'generation': 'EMPIRICAL_LATERAL_DATASET_V2',
      'inventory_sha256': inventory['receipt_sha256'],
      'source_identity': source_identity(),
      'split': 'ROUTE_DISJOINT_SPLIT_UNAVAILABLE',
      'execution': 'EMPIRICAL_DATASET_V2_NOT_EXECUTED',
      'future_log_eligibility_monitor': 'IMPLEMENTED_PASSIVE_TOOL_NOT_SCHEDULED',
      'new_numeric_routes_opened': 0,
      'fitting_performed': False,
      'model_selection_performed': False,
      'holdout_opened': False,
      'holdout_evaluated': False,
      'v1_data_role': 'PLANNING_CONTEXT_ONLY',
      'numeric_coverage': None,
      'gyro_crosscheck': 'NOT_RUN_NO_NEW_ROUTE',
      'wheel_speed_crosscheck': 'BLOCKED_SOURCE_UNITS_SIGN_TRACK_WIDTH',
      'lateral_accel_crosscheck': 'BLOCKED_SOURCE_UNITS_SIGN_FRAME',
      'yaw_model': 'EMPIRICAL_YAW_MODEL_V2_BLOCKED',
      'full_plant_ready': False,
      'command_bridge': 'RAW_TO_NORMALIZED_COMMAND_CONFIRMED_UNCHANGED',
      'stage_a': 'EMPIRICAL_ACTUATOR_MODEL_ONLY_STRICT_READY_FAILED_UNCHANGED',
      'yaw_signal': 'EMPIRICAL_YAW_SIGNAL_PARTIAL',
      'yaw_unit': 'YAW_UNIT_LIKELY_NOT_CONFIRMED',
      'historical_yaw_model': 'EMPIRICAL_YAW_MODEL_BLOCKED',
      'historical': p.policy()['historical'],
      'composition_recommendation': 'COMPOSITION_NOT_RECOMMENDED',
      'composition': 'COMPOSITION_NOT_AUTHORIZED',
      'search': 'SEARCH_NOT_AUTHORIZED',
      'candidate_frozen_evaluation': 'FROZEN_EVALUATION_NOT_AUTHORIZED',
      'calibration_blockers': p.BLOCKERS,
      'sealed_reference': 'NOT_GENERATED',
      'vehicle': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
    }
  )


def derive(private):
  p.verify(private)
  if private.get('schema') != 'EMPIRICAL_DATASET_V2_PRIVATE_INVENTORY' or private.get('numeric_payloads_opened') is not False:
    raise ValueError('ONLY_METADATA_WAITING_INVENTORY_ALLOWED')
  p.verify(private['split'])
  if private['split'] != v.split_routes([]) or private.get('new_numeric_route_count') != 0:
    raise ValueError('NO_SPLIT_OR_NUMERIC_EXECUTION_IN_WAITING_PUBLICATION')
  routes = private['routes']
  if any(x['status'] == 'ROUTE_METADATA_COMPATIBLE' for x in routes):
    raise ValueError('NEW_ROUTES_REQUIRE_SEPARATE_V2_DISPOSITION')
  for route in routes:
    v.hash_required(route['route_id'])
    if route['status'] not in (
      'V1_PLANNING_CONTEXT_ONLY',
      'ROUTE_IDENTITY_AMBIGUOUS',
      'ROUTE_REJECTED_INCOMPATIBLE_SOURCE',
      'ROUTE_REJECTED_INSUFFICIENT_SIGNALS',
    ):
      raise ValueError('PUBLIC_ROUTE_STATUS_ENUM_REQUIRED')
    if type(route['segment_count']) is not int or route['segment_count'] < 0 or type(route['v1_overlap']) is not bool:
      raise ValueError('PUBLIC_ROUTE_COUNT_TYPE_REQUIRED')
  counts = private['snapshot']['file_counts']
  v.hash_required(private['binding_sha256'])
  if any(type(n) is not int or n < 0 for n in counts.values()):
    raise ValueError('PUBLIC_NONNEGATIVE_FILE_COUNTS_REQUIRED')
  inventory = p.seal(
    {
      'schema': 'EMPIRICAL_DATASET_V2_ROUTE_INVENTORY',
      'status': 'METADATA_ONLY_COMPLETE',
      'private_inventory_sha256': private['receipt_sha256'],
      'metadata_binding_sha256': private['binding_sha256'],
      'root_policy_sha256': v.root_policy()['receipt_sha256'],
      'source_generation': v.expected_generation(),
      'v1_inventory_sha256': v.V1_INVENTORY,
      'v1_metadata_sha256': v.V1_METADATA,
      'route_count': len(routes),
      'v1_excluded_routes': sum(x['v1_overlap'] is True for x in routes),
      'new_compatible_untouched_routes': 0,
      'route_dispositions': [{'route_id': x['route_id'], 'status': x['status'], 'segment_count': x['segment_count']} for x in routes],
      'log_file_count': sum(counts.get(k, 0) for k in ('rlog.zst', 'qlog.zst')),
      'video_file_count_metadata_only': sum(counts.get(k, 0) for k in ('qcamera.ts', 'dcamera.hevc', 'fcamera.hevc', 'ecamera.hevc')),
      'other_file_count_metadata_only': sum(
        n for key, n in counts.items() if key not in ('rlog.zst', 'qlog.zst', 'qcamera.ts', 'dcamera.hevc', 'fcamera.hevc', 'ecamera.hevc')
      ),
      'metadata_failure_count': len(private['failures']),
      'numeric_values_opened': False,
      'image_video_opened': False,
      'gps_payload_opened': False,
      'source_identity': source_identity(),
    }
  )
  return {**policies(), 'empirical-dataset-v2-route-inventory.json': inventory, 'empirical-dataset-v2-readiness.json': readiness(inventory)}


def load():
  history.load()
  if set(PINS) != set(policies()) | {'empirical-dataset-v2-route-inventory.json', 'empirical-dataset-v2-readiness.json'}:
    raise ValueError('COMPLETE_V2_PUBLICATION_PINS_REQUIRED')
  rows = {name: inv.read(p.PUBLIC / name) for name in PINS}
  if any(rows[name]['receipt_sha256'] != pin for name, pin in PINS.items()):
    raise ValueError('IMMUTABLE_V2_PUBLICATION_DRIFT')
  for name, row in policies().items():
    if rows[name] != row:
      raise ValueError('V2_POLICY_DRIFT')
  inventory = rows['empirical-dataset-v2-route-inventory.json']
  if inventory['source_identity'] != source_identity() or rows['empirical-dataset-v2-readiness.json'] != readiness(inventory):
    raise ValueError('V2_EXECUTOR_OR_READINESS_DRIFT')
  return rows
