"""Readonly V2 cache admission. Hash source bytes, never decode raw logs again."""

from pathlib import Path
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_plant_model as m
from openpilot.tools.cyber_autotune import empirical_source_execution as prior
from openpilot.tools.cyber_autotune import empirical_source_metadata as metadata
from openpilot.tools.cyber_autotune import empirical_cross_root_inventory as logs
from openpilot.tools.cyber_autotune import empirical_v2_execution as execution
from openpilot.tools.cyber_autotune import empirical_v2_policy as v2
from openpilot.tools.cyber_autotune import empirical_v2_generation as g2
from openpilot.tools.cyber_autotune import empirical_v2_signals as signals
from openpilot.tools.cyber_autotune import empirical_v3_policy as v


def distinct_stores(old_store, new_store):
  a, b = execution.private_store(old_store), execution.private_store(new_store)
  if a == b or a in b.parents or b in a.parents:
    raise ValueError('V3_STORE_MUST_BE_SEPARATE_FROM_V2')
  return a, b


def tree_identity(store):
  """Hash bytes for preservation only; no numeric deserialization or discovery."""
  root = Path(store)
  rows = []
  for path in sorted(root.rglob('*')):
    if path.is_symlink():
      raise ValueError('NO_SYMLINK_PRIVATE_CACHE')
    if path.is_file():
      rows.append((path.relative_to(root).as_posix(), logs.file_sha(path)))
  return p.sha(p.canonical(rows))


def validate_segment(row, opening, route, digest, split_sha, auth_sha):
  if (
    row['status'] != 'EXTRACTED'
    or row['route_id'] != route['route_id']
    or row['role'] != 'TRAIN'
    or row['source_sha256'] != digest
    or row['segment_id'] != digest
    or row['adapter_sha256'] != route['adapter_sha256']
    or row['opening_sha256'] != opening['receipt_sha256']
    or opening['route_id'] != route['route_id']
    or opening['source_sha256'] != digest
    or opening['split_sha256'] != split_sha
    or opening['authorization_sha256'] != auth_sha
    or opening['role'] != 'TRAIN'
    or opening['holdout_opened'] is not False
    or row['runtime_steer_max'] != 409
    or row['runtime_setting_known'] is not True
    or row['profile']['steer_control_type'] != 'torque'
  ):
    raise ValueError('V3_CACHE_SOURCE_PROFILE_OPENING_OR_ADAPTER_DRIFT')
  bridge = row['bridge']
  if (
    bridge['status'] != 'RAW_TO_NORMALIZED_COMMAND_CONFIRMED'
    or bridge['float32_expected_exact_count'] != bridge['eligible']
    or bridge['sign_conflicts']
    or bridge['domain_conflicts']
  ):
    raise ValueError('V3_ROUTE_COMMAND_BRIDGE_NOT_CONFIRMED')


def validate_parent(result, public, receipt):
  if result['receipt_sha256'] != public['empirical-plant-v2-model-freeze-v1.json']['result_sha256']:
    raise ValueError('PINNED_V2_RESULT_REQUIRED')
  parent = next((x for x in result['routes'] if x['route_id'] == receipt['route_id']), None)
  if parent is None or parent['receipt_sha256'] != receipt['receipt_sha256']:
    raise ValueError('PINNED_V2_ROUTE_CHAIN_REQUIRED')


def load(old_store, new_store, source_store, roots):
  old_store, new_store = distinct_stores(old_store, new_store)
  v.require_frozen(new_store)
  public = v.inputs()
  split = v2.validate_split(prior.read(old_store / 'split.json'))
  if split != public['empirical-plant-v2-train-dev-split-v1.json']:
    raise ValueError('V2_SPLIT_PUBLIC_PRIVATE_CONFLICT')
  auth = prior.read(old_store / 'authorization.json')
  if auth != public['empirical-plant-v2-numeric-authorization-v1.json'] or auth != v2.authorization(split, auth['sources']):
    raise ValueError('V2_EXECUTION_CODE_POLICY_DRIFT')
  if prior.read(old_store / 'policy.json') != v2.policy():
    raise ValueError('V2_POLICY_DRIFT')
  historical_result = prior.read(old_store / 'train-dev-results.json')
  manifest = prior.read(old_store / 'manifest.json')
  if manifest['split_sha256'] != split['receipt_sha256']:
    raise ValueError('V2_MANIFEST_SPLIT_DRIFT')
  approved = prior.approved_root_map(roots)
  source_store = Path(source_store)
  data, yaw, bindings = {}, {}, []
  profile = None
  for route in v.routes():
    rid = route['route_id']
    source = prior.read(source_store / 'fingerprints' / (route['source_commit'] + '.json'))
    adapter = prior.read(source_store / 'adapters-final' / (route['source_commit'] + '.json'))
    metadata.validate_adapter(adapter, source)
    if adapter['receipt_sha256'] != route['adapter_sha256'] or source['receipt_sha256'] != route['source_fingerprint_sha256']:
      raise ValueError('EXACT_SOURCE_SPECIFIC_ADAPTER_REQUIRED')
    receipt = prior.read(old_store / 'routes' / (rid + '.json'))
    validate_parent(historical_result, public, receipt)
    if receipt['route_id'] != rid or receipt['role'] != 'TRAIN' or receipt['split_sha256'] != split['receipt_sha256'] or receipt['holdout_opened'] is not False:
      raise ValueError('IMMUTABLE_V2_ROUTE_RECEIPT_DRIFT')
    segments = manifest['routes'][rid]
    expected = sorted(x['source_sha256'] for x in segments)
    if (
      expected != sorted(x['source_sha256'] for x in receipt['segments'])
      or expected != auth['sources'][rid]
      or route['source_set_sha256'] != p.sha(p.canonical(expected))
    ):
      raise ValueError('EXACT_SEGMENT_LINEAGE_REQUIRED')
    row_by_sha = {x['source_sha256']: x for x in receipt['segments']}
    data[rid] = {b: [] for b in v.BINS}
    yaw[rid] = []
    checks = []
    for i, segment in enumerate(segments):
      digest = segment['source_sha256']
      # Reading compressed bytes for integrity is not event/payload decoding.
      if logs.file_sha(prior.source_location(segment['location'], approved)) != digest:
        raise ValueError('SOURCE_BYTES_CHANGED')
      meta = prior.read(source_store / 'segments' / route['source_commit'] / (digest + '.json'))
      if (
        meta['receipt_sha256'] != segment['metadata_sha256']
        or meta['metadata']['profile']['full_carparams_sha256'] != route['full_carparams_sha256']
        or meta['metadata']['init']['commit'] != route['source_commit']
        or meta['metadata']['init']['dirty']
      ):
        raise ValueError('SOURCE_METADATA_PROFILE_DRIFT')
      opening = prior.read(old_store / 'openings' / rid / (digest + '.json'))
      x = prior.read(old_store / 'segments' / rid / (digest + '.json'))
      validate_segment(x, opening, route, digest, split['receipt_sha256'], auth['receipt_sha256'])
      if x['profile'] != signals.profile_for_models(meta['metadata']['profile']['fields']):
        raise ValueError('SOURCE_BOUND_NUMERIC_PROFILE_REQUIRED')
      if x['receipt_sha256'] != row_by_sha[digest]['receipt_sha256']:
        raise ValueError('CACHED_SEGMENT_RECEIPT_DRIFT')
      if profile is None:
        profile = x['profile']
      elif profile != x['profile']:
        raise ValueError('NUMERIC_CACHE_PROFILE_CONFLICT')
      for b in v.BINS:
        data[rid][b].extend(signals.actuator_runs([x], b))
      yaw[rid].append(g2.compact(x))
      checks.append({'source_sha256': digest, 'cache_sha256': x['receipt_sha256'], 'opening_sha256': opening['receipt_sha256']})
      print('verified cache', rid[:8], i + 1, '/', len(segments), flush=True)
    bridge = next(x for x in public['empirical-plant-v2-command-bridge-v1.json']['routes'] if x['route_id'] == rid)
    if bridge['status'] != 'ROUTE_COMMAND_BRIDGE_CONFIRMED' or bridge['steer_max'] != 409:
      raise ValueError('POOLED_BRIDGE_GATE_FAILED')
    coverage = next(x for x in public['empirical-plant-v2-route-coverage-v1.json']['routes'] if x['route_id'] == rid)
    for b in v.BINS:
      count = len(m.design(data[rid][b], p.family_policy()['candidates'][0])[1])
      if count != coverage['bins'][b]['common_design_rows']:
        raise ValueError('CACHE_DESIGN_SUPPORT_DRIFT')
    bindings.append({'route_id': rid, 'route_receipt_sha256': receipt['receipt_sha256'], 'segments': checks, 'coverage': coverage, 'bridge': bridge})
  integrity = p.seal(
    {
      'schema': 'EMPIRICAL_PLANT_V3_CACHE_INTEGRITY_V1',
      'policy_sha256': v.policy()['receipt_sha256'],
      'v2_manifest_sha256': manifest['receipt_sha256'],
      'routes': bindings,
      'raw_payload_redecoded': False,
      'only_two_route_cache_deserialized': True,
    }
  )
  p.persist(new_store / 'cache-integrity.json', integrity)
  return data, yaw, profile, integrity
