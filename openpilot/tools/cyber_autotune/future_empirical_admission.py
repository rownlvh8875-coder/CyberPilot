"""Manual metadata admission and immutable roles. Never reads a log payload."""

import json
from functools import lru_cache
from pathlib import Path
import re
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import future_empirical_contracts as c

ROOTS = {'/mnt/d/carrotlog': 'CARROTLOG', 'D:\\carrotlog': 'CARROTLOG', '/mnt/d/CarrotLogs': 'CARROT_LOGS', 'D:\\CarrotLogs': 'CARROT_LOGS'}
META_FIELDS = set(c.admission_contract()['identity']) | {'schema', 'control_type', 'complete_lineage', 'dirty', 'root_id', 'field_presence'}
SEALED = set(p.FIREWALL) | {'receipt_sha256'}


def hash_required(value):
  if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
    raise ValueError('OPAQUE_SHA256_REQUIRED')


def root_id(root):
  if str(root) not in ROOTS:
    raise ValueError('EXACT_TWO_ROOT_ALIAS_ALLOWLIST')
  return ROOTS[str(root)]


def canonical_path(path):
  path = Path(path).absolute()
  if '..' in path.parts or any(x.is_symlink() for x in (path, *path.parents)):
    raise ValueError('NO_PATH_TRAVERSAL_OR_SYMLINK')
  return path.resolve()


def private_store(path):
  path = canonical_path(path)
  repo = Path(__file__).resolve().parents[3]
  if any(x.is_symlink() for x in (path, *path.parents)) or path.is_relative_to(repo):
    raise ValueError('PRIVATE_STORE_OUTSIDE_REPOSITORY_NO_SYMLINK')
  for root in ('/mnt/d/carrotlog', '/mnt/d/CarrotLogs'):
    if path.is_relative_to(Path(root)):
      raise ValueError('NO_WRITE_TO_RAW_ROOT')
  return path


def source_status(meta):
  if meta.get('dirty') is not False or meta.get('control_type') != 'torque' or meta.get('vehicle_fingerprint') != 'HYUNDAI_SANTA_FE_2022':
    return 'SOURCE_INCOMPATIBLE'
  known = next((z for z in c.known_sources() if z['commit'] == meta.get('source_commit')), None)
  if known is None:
    return 'SOURCE_AUDIT_PENDING'
  if meta.get('source_class_sha256') != known['class_sha256'] or meta.get('source_fingerprint_sha256') != known['fingerprint_sha256']:
    return 'SOURCE_AUDIT_PENDING'
  if not any(
    meta.get('full_carparams_sha256') == profile['full_carparams_sha256']
    and meta.get('empirical_profile_sha256') == profile['empirical_profile_sha256']
    and known['class_sha256'] == profile['semantic_class_id']
    for profile in c.known_profiles()
  ):
    return 'SOURCE_AUDIT_PENDING'
  return 'SOURCE_EQUIVALENT' if meta.get('adapter_sha256') == known['adapter_sha256'] else 'SOURCE_ADAPTER_REQUIRED'


def old_route_ids():
  data = (p.PUBLIC / 'empirical-source-route-reclassification-v1.json').read_bytes()
  return _old_ids(data)


@lru_cache(maxsize=4)
def _old_ids(data):
  return frozenset(z['route_id'] for z in c._verified(data)['routes'])


def inventory(meta, history, existing):
  p.verify(meta)
  p.verify(history)
  if set(meta) != META_FIELDS | SEALED or meta['schema'] != 'FUTURE_ROUTE_METADATA_V1':
    raise ValueError('EXACT_METADATA_WHITELIST_NO_NUMERIC_BODY')
  if (
    set(history) != {'schema', 'inventory_sha256', 'complete', 'routes', 'metadata_inventory'} | SEALED
    or history['schema'] != 'FUTURE_ROUTE_HISTORY_METADATA_V1'
    or history['complete'] is not True
    or history['inventory_sha256'] != c.history_sha()
  ):
    raise ValueError('COMPLETE_SOURCE_BOUND_HISTORY_REGISTRY_REQUIRED')
  old_inventory = p.verify(history['metadata_inventory'])
  if old_inventory['receipt_sha256'] != c.history_private_sha() or old_inventory.get('numeric_payloads_opened') is not False:
    raise ValueError('PINNED_OLD_METADATA_INVENTORY_REQUIRED_NO_REANALYSIS')
  old_segments = {z['route_id']: z['source_hashes'] for z in old_inventory['routes']}
  expected = c.history_bindings()
  if type(history['routes']) is not list or len(history['routes']) != len(expected):
    raise ValueError('FULL_HISTORICAL_ROUTE_METADATA_PROOFS_REQUIRED')
  seen_ids = set()
  for h in history['routes']:
    if set(h) != {'route_id', 'identity', 'logger_start_sha256', 'segment_receipts'}:
      raise ValueError('EXACT_HISTORY_IDENTITY_PROOF_REQUIRED')
    rid = h['route_id']
    identity = h['identity']
    if (
      rid in seen_ids or rid not in expected or p.sha(p.canonical(identity)) != expected[rid] or identity.get('logger_start_sha256') != h['logger_start_sha256']
    ):
      raise ValueError('HISTORY_IDENTITY_PREIMAGE_CONFLICT')
    if rid not in old_segments or sorted(h['segment_receipts']) != sorted(old_segments[rid]):
      raise ValueError('HISTORY_SEGMENTS_NOT_BOUND_TO_IMMUTABLE_INVENTORY')
    hash_required(h['logger_start_sha256'])
    if type(h['segment_receipts']) is not list or not h['segment_receipts']:
      raise ValueError('HISTORY_SEGMENT_RECEIPTS_REQUIRED')
    for value in h['segment_receipts']:
      hash_required(value)
    seen_ids.add(rid)
  for key in ('full_carparams_sha256', 'empirical_profile_sha256', 'logger_start_sha256', 'adapter_sha256', 'source_class_sha256', 'source_fingerprint_sha256'):
    hash_required(meta[key])
  if not re.fullmatch('[0-9a-f]{40}', meta['source_commit']) or meta['root_id'] not in ROOTS.values():
    raise ValueError('EXACT_SOURCE_ROOT_REQUIRED')
  segments = meta['segments']
  if (
    not segments
    or any(set(s) != {'ordinal', 'receipt_sha256'} or type(s['ordinal']) is not int for s in segments)
    or [s['ordinal'] for s in segments] != list(range(len(segments)))
  ):
    raise ValueError('WHOLE_ROUTE_COMPLETE_LINEAGE_REQUIRED_NO_TIME_BLOCK_ROUTES')
  hashes = [s['receipt_sha256'] for s in segments]
  for value in hashes:
    hash_required(value)
  if len(set(hashes)) != len(hashes):
    raise ValueError('DUPLICATE_SEGMENT')
  if any(type(meta['envelopes'].get(k)) is not int or meta['envelopes'][k] < 0 for k in c.REQUIRED_MESSAGES):
    raise ValueError('METADATA_ENVELOPE_COUNTS_REQUIRED')
  if set(meta['field_presence']) != set(c.SIGNAL_FIELDS) or any(v not in ('AVAILABLE', 'UNAVAILABLE', 'UNKNOWN') for v in meta['field_presence'].values()):
    raise ValueError('SOURCE_BOUND_PRESENCE_MATRIX_REQUIRED')
  seen = history['routes'] + existing
  for row in seen:
    if row.get('logger_start_sha256') == meta['logger_start_sha256'] or set(row.get('segment_receipts', ())) & set(hashes):
      raise ValueError('DUPLICATE_RENAMED_RECOMPRESSED_OR_APPENDED_ROUTE')
  identity = {k: meta[k] for k in c.admission_contract()['identity'] if k not in ('prior_analysis', 'numeric_opened', 'envelopes')}
  rid = p.sha(p.canonical(identity))
  if rid in old_route_ids():
    raise ValueError('OLD_ROUTE_REUSE_FORBIDDEN')
  status = source_status(meta)
  admitted = (
    status == 'SOURCE_EQUIVALENT'
    and meta['complete_lineage'] is True
    and meta['numeric_opened'] is False
    and meta['prior_analysis'] == 'NONE'
    and all(meta['envelopes'][k] > 0 for k in c.REQUIRED_MESSAGES)
    and all(meta['field_presence'][k] == 'AVAILABLE' for k in c.REQUIRED_STAGE_A_FIELDS)
  )
  state = (
    'ROUTE_METADATA_ADMITTED' if admitted else ('REJECTED' if status == 'SOURCE_INCOMPATIBLE' or meta['numeric_opened'] is True else 'METADATA_ONLY_PENDING')
  )
  return p.seal(
    {
      **identity,
      'schema': 'FUTURE_ROUTE_INVENTORY_RECEIPT_V1',
      'route_id': rid,
      'metadata_sha256': meta['receipt_sha256'],
      'history_sha256': history['receipt_sha256'],
      'metadata': meta,
      'history': history,
      'source_status': status,
      'status': state,
      'segment_receipts': hashes,
      'prior_analysis': meta['prior_analysis'],
      'numeric_opened': meta['numeric_opened'],
      'numeric_coverage': None,
      'numeric_opening_allowed': False,
    }
  )


def verify_inventory(row):
  p.verify(row)
  rebuilt = inventory(row['metadata'], row['history'], [])
  if rebuilt != row:
    raise ValueError('ADMISSION_RECEIPT_DRIFT')
  return row


def assign(rows):
  if len(rows) < 3:
    raise ValueError('ROUTE_DISJOINT_GENERATION_UNAVAILABLE')
  for row in rows:
    verify_inventory(row)
    if row['status'] != 'ROUTE_METADATA_ADMITTED':
      raise ValueError('ALL_ROUTES_COMPATIBLE_DISTINCT_PREVIOUSLY_UNOPENED')
  if len({z['route_id'] for z in rows}) != len(rows) or len({z['logger_start_sha256'] for z in rows}) != len(rows):
    raise ValueError('WHOLE_DISTINCT_ROUTE_ASSIGNMENTS_REQUIRED')
  segments = [h for row in rows for h in row['segment_receipts']]
  if len(set(segments)) != len(segments):
    raise ValueError('CROSS_ROUTE_SEGMENT_LEAKAGE')
  fields = ('source_class_sha256', 'full_carparams_sha256', 'empirical_profile_sha256')
  if any(len({z[k] for z in rows}) != 1 for k in fields):
    raise ValueError('HOMOGENEOUS_FULL_PROFILE_REQUIRED')
  rows = sorted(rows, key=lambda z: z['route_id'])
  n = len(rows)
  ntrain = max(1, n * 60 // 100)
  ndev = max(1, n * 20 // 100)
  if ntrain + ndev >= n:
    ntrain = n - ndev - 1
  roles = ['TRAIN'] * ntrain + ['DEVELOPMENT'] * ndev + ['HOLDOUT'] * (n - ntrain - ndev)
  return p.seal(
    {
      'schema': 'FUTURE_ROUTE_ROLE_LEDGER_V1',
      'policy_sha256': c.generation_policy()['receipt_sha256'],
      **{k: rows[0][k] for k in fields},
      'routes': [
        {
          **{
            k: row[k]
            for k in (
              'route_id',
              'source_commit',
              'adapter_sha256',
              'empirical_profile_sha256',
              'full_carparams_sha256',
              'segment_receipts',
              'logger_start_sha256',
            )
          },
          'inventory_sha256': row['receipt_sha256'],
          'role': role,
          'numeric_opened_before_assignment': False,
        }
        for row, role in zip(rows, roles, strict=True)
      ],
      'inventory_receipts': rows,
      'opening_state': 'CLOSED',
      'opening_allowed': False,
    }
  )


def verify_roles(roles):
  p.verify(roles)
  if roles != assign(roles['inventory_receipts']):
    raise ValueError('IMMUTABLE_EXACT_ROUTE_ROLES_REQUIRED')
  return roles


def holdout_plan(roles, model, opened_route_ids):
  verify_roles(roles)
  holdouts = [z for z in roles['routes'] if z['role'] == 'HOLDOUT']
  if any(z['route_id'] in opened_route_ids for z in holdouts):
    raise ValueError('HOLDOUT_ONE_TIME_ALREADY_OPENED')
  if model is None:
    state = 'CLOSED_MISSING_ADMISSIBLE_MODEL'
  else:
    p.verify(model)
    fields = ('family_sha256', 'config_sha256', 'model_sha256', 'metrics_sha256', 'support_policy_sha256')
    if (
      model.get('schema') != 'FUTURE_MODEL_FREEZE_CONTRACT_V1'
      or model.get('roles_sha256') != roles['receipt_sha256']
      or model.get('source_class_sha256') != roles['source_class_sha256']
      or model.get('empirical_profile_sha256') != roles['empirical_profile_sha256']
      or model.get('status') != 'MODEL_FROZEN_AWAITING_HOLDOUT'
      or model.get('no_reselection') is not True
      or model.get('no_refit') is not True
    ):
      raise ValueError('EXACT_FROZEN_MODEL_METRICS_SUPPORT_REQUIRED')
    for k in fields:
      hash_required(model.get(k))
    state = 'CLOSED_FUTURE_AUTHORIZATION_REQUIRED'
  return p.seal(
    {
      'schema': 'FUTURE_HOLDOUT_EVALUATION_PLAN_V1',
      'roles_sha256': roles['receipt_sha256'],
      'model_sha256': model['receipt_sha256'] if model else None,
      'status': state,
      'opening_allowed': False,
      'one_time': True,
      'opening_receipt': 'REQUIRED_BEFORE_FUTURE_NUMERIC_ACCESS',
    }
  )


def eligibility(row):
  verify_inventory(row)
  return p.seal(
    {
      'schema': 'FUTURE_METADATA_ROUTE_ELIGIBILITY_V1',
      'route_id': row['route_id'],
      'status': row['status'],
      'source_status': row['source_status'],
      'messages': row['metadata']['envelopes'],
      'signals': row['metadata']['field_presence'],
      'numeric_coverage': None,
      'speed_bin_potential': None,
      'active_no_override_potential': None,
      'timestamps': 'SOURCE_PRESENCE_ONLY_ACQUISITION_AGE_PENDING',
      'role': 'METADATA_ONLY_PENDING',
      'opening_state': 'CLOSED',
      'fitting_performed': False,
      'numeric_extension': 'FUTURE_AUTHORIZED_TRAIN_DEV_ONLY_REUSE_EXISTING_SUPPORT_POLICY_201',
    }
  )


def numeric_open(*_args):
  raise ValueError('NO_NUMERIC_EXTRACTION_OR_OPENING_AUTHORIZED_THIS_INCREMENT')


def load_private(path, store):
  path = canonical_path(path)
  store = private_store(store)
  if not path.is_relative_to(store) or any(x.is_symlink() for x in (path, *path.parents)) or path.suffix != '.json':
    raise ValueError('ONLY_EXPLICIT_PRIVATE_METADATA_JSON_IN_STORE')
  row = json.loads(path.read_bytes())
  return p.verify(row)
