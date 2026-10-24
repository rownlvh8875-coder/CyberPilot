"""Selective metadata/receipt reader. Numeric caches, traces and media never open."""

import json
import os
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p

SAFE_NAMES = frozenset(
  (
    'split.json',
    'folds.json',
    'holdout-opening.json',
    'opening.json',
    'combined-inventory.json',
    'route-inventory.json',
    'manifest.json',
    'public-origin.json',
    'execution-binding.json',
  )
)
IGNORED_DIRECTORIES = frozenset(('.git', '.venv', 'node_modules', '__pycache__', 'development-source', 'historical-source', 'site-packages', 'pkgs'))
FORBIDDEN_PARTS = frozenset(('numeric', 'aligned', 'predictions', 'rows', 'drafts', 'annotations', 'raw'))


def no_alias(path):
  path = Path(path)
  if any(x.is_symlink() for x in (path, *path.parents)):
    raise ValueError('PRIVATE_STORE_SYMLINK')
  return path.absolute()


def safe_path(store, allowed, relative):
  store = no_alias(store)
  if store not in [no_alias(x) for x in allowed]:
    raise ValueError('EXPLICIT_STORE_ALLOWLIST_REQUIRED')
  relative = Path(relative)
  if relative.is_absolute() or '..' in relative.parts:
    raise ValueError('PRIVATE_STORE_PATH_ESCAPE')
  return no_alias(store / relative)


def read_receipt(store, allowed, relative):
  relative = Path(relative)
  fold_receipt = (
    len(relative.parts) == 6
    and relative.parts[:2] == ('folds', 'STAGE_A')
    and relative.parts[2] in ('LOW', 'MEDIUM', 'HIGH')
    and relative.parts[4] in ('FOLD_A', 'FOLD_B')
    and relative.name == 'receipt.json'
  )
  if (
    not fold_receipt
    and relative.name not in SAFE_NAMES
    and not (len(relative.parts) == 3 and relative.parts[0] == 'openings' and relative.suffix == '.json')
  ):
    raise ValueError('PRIVATE_RECEIPT_ALLOWLIST_REQUIRED')
  if set(relative.parts) & FORBIDDEN_PARTS:
    raise ValueError('PRIVATE_RECEIPT_ALLOWLIST_REQUIRED')
  path = safe_path(store, allowed, relative)
  before = path.stat()
  row = p.verify(json.loads(path.read_bytes()))
  schema = row.get('schema', '')
  allowed_prefixes = ('EMPIRICAL_', 'ADDITIONAL_', 'CYBER_')
  if not schema.startswith(allowed_prefixes) or any(k in row for k in ('rows', 'targets', 'predictions', 'aligned')):
    raise ValueError('PRIVATE_RECEIPT_SCHEMA_REJECTED')
  if fold_receipt and schema != 'EMPIRICAL_PLANT_V3_PRIVATE_FOLD_RESULT_V1':
    raise ValueError('PRIVATE_FOLD_RECEIPT_SCHEMA_REJECTED')
  after = path.stat()
  if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (
    before.st_dev,
    before.st_ino,
    before.st_size,
    before.st_mtime_ns,
    before.st_ctime_ns,
  ):
    raise ValueError('RECEIPT_CHANGED_DURING_READ')
  return row


def file_inventory(store):
  store = no_alias(store)
  files, excluded = [], []
  if not store.is_dir():
    raise ValueError('REGISTERED_STORE_MISSING')
  for directory, dirs, names in os.walk(store, followlinks=False):
    for name in dirs + names:
      no_alias(Path(directory) / name)
    excluded.extend(str((Path(directory) / x).relative_to(store)) for x in dirs if x in IGNORED_DIRECTORIES)
    dirs[:] = sorted(x for x in dirs if x not in IGNORED_DIRECTORIES)
    for name in sorted(names):
      path = Path(directory) / name
      stat = path.stat()
      files.append({'relative': str(path.relative_to(store)), 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns, 'inode': stat.st_ino})
  return {'files': sorted(files, key=lambda x: x['relative']), 'excluded_non_evidence_directories': sorted(excluded)}


def closure_complete(registry, blockers):
  return registry.get('carrot_simulator_evidence_registry_complete') is True and not blockers


def use_record(
  project,
  generation,
  role,
  receipt,
  source_identity,
  *,
  metadata=True,
  numeric=False,
  fitting=False,
  selection=False,
  evaluation=False,
  holdout=False,
):
  p.verify(receipt)
  if any(type(x) is not bool for x in (metadata, numeric, fitting, selection, evaluation, holdout)):
    raise ValueError('USE_FLAGS_MUST_BE_BOOLEAN')
  return {
    'project': project,
    'generation': generation,
    'role': role,
    'metadata_opened': metadata,
    'numeric_opened': numeric,
    'fitting_used': fitting,
    'selection_used': selection,
    'evaluation_used': evaluation,
    'holdout_used': holdout,
    'receipt_sha256': receipt['receipt_sha256'],
    'source_identity_sha256': source_identity,
  }
