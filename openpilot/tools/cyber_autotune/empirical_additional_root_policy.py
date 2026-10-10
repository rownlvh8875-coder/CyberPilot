"""Versioned two-root metadata authority. Existing V2 policy stays immutable."""

from pathlib import Path, PureWindowsPath
import re

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as old

ROOTS = {
  old.ROOT_IDENTITY_SHA256: 'b022cc98c4755a9bab7c825e45f0c79328952c4961844f520ff662ac3be3e658',
  '52a91bdfda461379a476af5bf6857ada399c5014712c9eb3f6f66fcec4e1beaf': 'c280c1a63ad7101093058ab8c9a32f6ecb51627d34c968d2cd6a4c1a3453df1f',
}
BASELINE = '9d3df6222afcd954fe9ff91d59cb41e3e62113fa'


def canonical_alias(value):
  value = str(value)
  if value.startswith(('\\\\', '//')) or '..' in re.split(r'[/\\]', value):
    raise ValueError('NETWORK_OR_PARENT_ALIAS_REJECTED')
  if re.match(r'^[A-Za-z]:[/\\]', value):
    path = PureWindowsPath(value)
    return '/mnt/' + path.drive[0].lower() + '/' + '/'.join(path.parts[1:])
  if not value.startswith('/'):
    raise ValueError('ABSOLUTE_ROOT_REQUIRED')
  return value.rstrip('/') or '/'


def require_root_hash(key):
  if key not in ROOTS:
    raise ValueError('ROOT_NOT_EXPLICITLY_APPROVED')
  return key


def root_key(value):
  text = str(value)
  if re.match(r'^[A-Za-z]:[/\\]', text):
    win = p.sha(PureWindowsPath(text).as_posix().casefold().encode())
    matches = [key for key, alias in ROOTS.items() if alias == win]
    if len(matches) != 1:
      raise ValueError('ROOT_NOT_EXPLICITLY_APPROVED')
    canonical_alias(value)
    return matches[0]
  return require_root_hash(p.sha(canonical_alias(value).encode()))


def approved_root(value):
  root_key(value)
  path = old.no_alias(canonical_alias(value))
  if not path.is_dir():
    raise ValueError('APPROVED_ROOT_UNAVAILABLE')
  return path.resolve(strict=True)


def root_policy():
  return p.seal({
    'schema': 'EMPIRICAL_DATASET_V2_ROOT_POLICY_V2',
    'baseline_commit': BASELINE, 'root_count': 2,
    'allowed_root_alias_hashes': ROOTS,
    'aliases': 'EACH_WINDOWS_WSL_PAIR_ONE_STORAGE_ROOT',
    'previous_policy_sha256': old.root_policy()['receipt_sha256'],
    'parent_scan': False, 'network_scan': False, 'archives_opened': False,
    'maximum_directory_depth': 32,
    'metadata_payloads': ['initData', 'carParams'],
    'envelope_only_other_messages': True, 'numeric_signal_values_opened': False,
    'image_video_opened': False, 'numeric_coverage': None,
    'prior_analysis_default': 'ROUTE_PRIOR_ANALYSIS_STATUS_UNKNOWN',
    'prior_analysis_unknown_holdout_allowed': False,
    'split_policy_sha256': old.split_policy()['receipt_sha256'],
    'minimum_routes': 3, 'numeric_extraction_authorized': False,
    'model_fitting_authorized': False, 'holdout_opening_authorized': False,
    'calibration_blockers': p.BLOCKERS,
  })


def compatibility(generation):
  expected = old.expected_generation()
  if generation.get('control_type') != 'torque':
    return 'ROUTE_INCOMPATIBLE_CONTROL_TYPE'
  if generation.get('source_commit') != expected['source_commit'] or generation.get('os_version') != expected['os_version']:
    return 'ROUTE_DIFFERENT_SOURCE_GENERATION'
  if generation.get('carparams_sha256') != expected['carparams_sha256']:
    return 'ROUTE_DIFFERENT_CARPARAMS'
  if generation != expected:
    return 'ROUTE_IDENTITY_AMBIGUOUS'
  return 'ROUTE_COMPATIBLE_WITH_V1_GENERATION'


def metadata_split(routes):
  seen, eligible = set(), []
  for route in routes:
    key = old.hash_required(route['route_id'])
    if key in seen:
      raise ValueError('DUPLICATE_ROUTE_IN_SPLIT')
    seen.add(key)
    if route['compatible'] is True and route['v1_overlap'] is False and route['prior_analysis'] == 'ATTESTED_NOT_USED':
      eligible.append({'route_id': key, 'status': 'ROUTE_METADATA_COMPATIBLE', 'v1_overlap': False})
  split = old.split_routes(eligible)
  return p.seal({
    'schema': 'EMPIRICAL_DATASET_V2_METADATA_SPLIT_V1',
    'status': 'ROUTE_DISJOINT_SPLIT_POSSIBLE' if split['routes'] else 'ROUTE_DISJOINT_SPLIT_UNAVAILABLE',
    'routes': split['routes'], 'policy_sha256': old.split_policy()['receipt_sha256'],
    'root_policy_sha256': root_policy()['receipt_sha256'],
    'numeric_extraction_authorized': False, 'holdout_opened': False,
  })
