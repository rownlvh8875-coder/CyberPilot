"""Additive E-only storage authority. No fitting, grants or numerical policy."""

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import os
import re
import subprocess

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as verified

MOUNT = Path('/mnt/e')
AMENDMENT_FILE = 'empirical-hurdle-stage1-v3-external-storage-amendment.json'
MIGRATION_FILE = 'empirical-hurdle-stage1-v3-storage-migration-verification.json'
AUTH_FIELDS = {'storage_amendment_receipt_sha256', 'storage_migration_receipt_sha256', 'storage_volume',
               'mount_identity_sha256', 'volume_identity_sha256'}
BASE_RECEIPTS = {
  'policy': 'c6795b87374f696d9701e30eaaa675ec88e2e1de5e60d381bc33efd90be20925',
  'fitting-policy': 'e9991c5ea12ecf5f52b07651c08ad66be0fe1d23fccafbe90b68216ab1c1e09f',
  'execution-policy': '9f46c3ff85df88eff84f36c126eb847cd7a1b509a0de25bac1193c707e8e9461',
}
_OUTPUT = ContextVar('v3_authorized_external_output', default=None)


def require(value, message='V3_OUTPUT_ROOT_INVALID'):
  if not value:
    raise ValueError(message)


def amendment():
  return p.seal({
    'schema': 'HURDLE_STAGE1_V3_EXTERNAL_STORAGE_AMENDMENT_V1',
    'status': 'HURDLE_STAGE1_V3_EXTERNAL_STORAGE_AMENDMENT_V1_FROZEN',
    'baseline': '3acd6543eff2b88b8128f6fb71a2b60f08ac5617',
    'change_scope': 'STORAGE_AUTHORITY_ONLY', 'storage_volume': 'E_EXTERNAL_SSD',
    'base_policy_receipts': BASE_RECEIPTS, 'numerical_semantics': 'UNCHANGED',
    'authorized_roots': ['source', 'causal', 'derived', 'output'],
    'mount_rule': 'UNIQUE_E_9P_ROOT_SLASH_SAME_DEVICE_NO_NESTED_MOUNT_NO_ALIAS',
    'volume_identity': 'LIVE_WINDOWS_UNIQUE_ID_AND_KERNEL_MOUNT_ID_BOUND',
    'root_identity': 'EXPLICIT_ABSOLUTE_RESOLVED_PATH_SHA256',
    'overlap': 'SOURCE_CAUSAL_DERIVED_OUTPUT_REPOSITORY_DISJOINT',
    'compression': {'format': 'NPY_GZIP_V1', 'order': 'C', 'level': 1, 'mtime': 0, 'filename': ''},
    'migration': 'EXACT_MANIFEST_LISTED_MEMBERS_ONLY_NO_REBUILD',
    'authorization_minting': False, 'external_trusted_receipt_required': True,
    'storage_binding_rechecked': 'EACH_NUMERIC_PERMIT_AND_EACH_OUTPUT_WRITE',
    'resume': 'SAVED_OUTPUT_ONLY_MOUNT_IDENTITY_STILL_REQUIRED',
    'run2_cleanup': 'ELIGIBILITY_ONLY_RETAIN_BY_DEFAULT',
    'holdout': 'CLOSED', 'opening_count': 0, 'holdout_discovery': 0, 'vehicle_authority': 'NONE',
  })


def mount_records():
  def decode(value):
    return re.sub(r'\\([0-7]{3})', lambda match: chr(int(match[1], 8)), value)

  rows = []
  for line in Path('/proc/self/mountinfo').read_text().splitlines():
    fields = line.split()
    separator = fields.index('-')
    rows.append({'point': Path(decode(fields[4])), 'root': decode(fields[3]), 'device': fields[2],
                 'mount_id': fields[0], 'parent_id': fields[1],
                 'filesystem': fields[separator + 1], 'source': decode(fields[separator + 2])})
  return rows


def prove_authorized_external_volume(root, *, expected_mount=None):
  root = verified.safe(root)
  require(root != MOUNT and root.is_relative_to(MOUNT) and root.resolve() == root)
  rows = mount_records()
  mounted = [row for row in rows if row['point'] == MOUNT]
  require(len(mounted) == 1)
  row = mounted[0]
  require(row['root'] == '/' and row['filesystem'] == '9p' and row['source'].casefold().rstrip('\\/') == 'e:')
  for other in rows:
    point = other['point']
    if point not in (Path('/'), MOUNT):
      require(not root.is_relative_to(point) and not point.is_relative_to(root))
  existing = root
  while not existing.exists():
    existing = existing.parent
  device = existing.stat().st_dev
  require(device == MOUNT.stat().st_dev and row['device'] == f'{os.major(device)}:{os.minor(device)}')
  identity = {key: str(value) for key, value in row.items()}
  digest = p.sha(p.canonical(identity))
  require(expected_mount is None or digest == expected_mount, 'V3_EXTERNAL_VOLUME_IDENTITY_CONFLICT')
  return {'storage_volume': 'E_EXTERNAL_SSD', 'mount_identity_sha256': digest}


def volume_identity():
  """Live volume metadata only; no file inventory or filesystem writes."""
  try:
    # /L is the native read-only volume-name query; no compiler/temp files.
    value = subprocess.check_output(['/mnt/c/Windows/System32/mountvol.exe', 'E:\\', '/L'],
                                    text=True, encoding='utf-8', timeout=10).strip().lstrip('\ufeff')
  except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
    raise ValueError('V3_EXTERNAL_VOLUME_IDENTITY_CONFLICT') from exc
  require(re.fullmatch(r'\\\\\?\\Volume\{[0-9a-fA-F-]{36}\}\\', value) is not None,
          'V3_EXTERNAL_VOLUME_IDENTITY_CONFLICT')
  return p.sha(value.encode())


def contracts():
  stored = verified.read_json(p.PUBLIC / AMENDMENT_FILE)
  require(stored == amendment(), 'V3_STORAGE_AMENDMENT_CONFLICT')
  migration = verified.read_json(p.PUBLIC / MIGRATION_FILE)
  require(migration['status'] == 'CYBERPILOT_STORAGE_MIGRATION_V1_VERIFIED'
          and migration['source_manifest_sha256'] == verified.SOURCE_SHA
          and migration['destination_volume'] == 'E_EXTERNAL_SSD'
          and migration['source_rebuild_count'] == 0, 'V3_STORAGE_MIGRATION_CONFLICT')
  return stored, migration


def verify_manifest_members(root, files, *, sizes=None):
  """Opaque byte hashes only. Never inventory a source or interpret arrays."""
  root = verified.safe(root)
  require(type(files) is dict and (sizes is None or type(sizes) is dict), 'V3_STORAGE_MIGRATION_CONFLICT')
  total = 0
  for name, expected in files.items():
    path = verified.member(root, name)
    require(type(expected) is str and re.fullmatch('[0-9a-f]{64}', expected) is not None, 'V3_STORAGE_MIGRATION_CONFLICT')
    require(verified.digest(path) == expected, 'V3_STORAGE_MIGRATION_CONFLICT')
    length = path.stat().st_size
    if sizes is not None and name in sizes:
      require(type(sizes[name]) is int and sizes[name] >= 0 and length == sizes[name], 'V3_STORAGE_MIGRATION_CONFLICT')
    total += length
  return {'members': len(files), 'bytes': total, 'file_set_sha256': p.sha(p.canonical(files))}


def validate_bindings(auth):
  stored, migration = contracts()
  require(auth['storage_volume'] == 'E_EXTERNAL_SSD'
          and auth['storage_amendment_receipt_sha256'] == stored['receipt_sha256']
          and auth['storage_migration_receipt_sha256'] == migration['receipt_sha256']
          and auth['policies'] == BASE_RECEIPTS, 'V3_EXECUTION_AUTHORIZATION_CONFLICT')
  for key in ('source', 'causal', 'derived'):
    require(auth['root_identities'][key] == migration['destination_root_sha256'][key], 'V3_EXECUTION_AUTHORIZATION_CONFLICT')
  for key in ('mount_identity_sha256', 'volume_identity_sha256'):
    require(type(auth[key]) is str and re.fullmatch('[0-9a-f]{64}', auth[key]) is not None, 'V3_EXECUTION_AUTHORIZATION_CONFLICT')


def roots_checked(roots, auth):
  check_live_volume(auth['volume_identity_sha256'])
  for root in roots.values():
    prove_authorized_external_volume(root, expected_mount=auth['mount_identity_sha256'])


def check_live_volume(expected):
  require(volume_identity() == expected, 'V3_EXTERNAL_VOLUME_IDENTITY_CONFLICT')


def verify_saved_output(output, auth):
  validate_bindings(auth)
  require(p.sha(str(output).encode()) == auth['root_identities']['output'], 'V3_EXECUTION_AUTHORIZATION_CONFLICT')
  roots_checked({'output': output}, auth)


@contextmanager
def output_scope(auth, root):
  prove_authorized_external_volume(root, expected_mount=auth['mount_identity_sha256'])
  check_live_volume(auth['volume_identity_sha256'])
  token = _OUTPUT.set((root, auth['mount_identity_sha256'], auth['volume_identity_sha256']))
  try:
    yield
  finally:
    _OUTPUT.reset(token)


def checked_bound_output(path):
  binding = _OUTPUT.get()
  if binding is None:
    return False
  root, mount, volume = binding
  require(path.is_relative_to(root))
  prove_authorized_external_volume(root, expected_mount=mount)
  check_live_volume(volume)
  require(verified.safe(path).resolve() == path)
  return True
