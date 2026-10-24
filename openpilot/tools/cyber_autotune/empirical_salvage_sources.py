"""Exact additional public source fingerprints; no log/vehicle execution."""

from pathlib import Path
import subprocess

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_fingerprint as f
from openpilot.tools.cyber_autotune import empirical_source_dependencies as d


def compare(a, b):
  if not all(x.get('complete') is True and x.get('public_available') is True and x.get('dirty') is False for x in (a, b)):
    return 'SOURCE_AUDIT_PARTIAL'
  if set(a['files']) != set(b['files']):
    return 'NOT_EQUIVALENT'
  changed = {k for k in a['files'] if a['files'][k]['normalized_source_sha256'] != b['files'][k]['normalized_source_sha256']}
  if not changed and a['closure'] == b['closure']:
    return 'SOURCE_EQUIVALENT'
  if any(k.startswith(('logger', 'schema_')) for k in changed):
    return 'NOT_EQUIVALENT'
  return 'SOURCE_ADAPTER_REQUIRED'


def safe_entry(path, data):
  try:
    return f.source_entry(path, data)
  except (UnicodeError, SyntaxError):
    return {'path': path, 'file_sha256': p.sha(data), 'normalized_source_sha256': None, 'symbols': {}, 'parse_status': 'SOURCE_AST_UNAVAILABLE'}


def audit(repo, commit, public_available):
  repo = Path(repo)
  git = ['git', '-c', f'safe.directory={repo}', '-C', str(repo)]
  source = f.audit(repo, commit)
  paths = set(subprocess.check_output([*git, 'ls-tree', '-r', '--name-only', commit]).decode().splitlines())
  closure, missing = {}, []
  for path in sorted(set(d.DEPENDENCIES) | set(d.CLOSURE_PATHS)):
    candidates = [path]
    if path.startswith('openpilot/'):
      candidates.append(path.removeprefix('openpilot/'))
    if path == 'opendbc_repo/opendbc/car/common/crc.py':
      candidates.append('opendbc_repo/opendbc/car/crc.py')
    found = [x for x in candidates if x in paths]
    if len(found) != 1:
      missing.append(path)
      continue
    data = subprocess.check_output([*git, 'show', f'{commit}:{found[0]}'])
    closure[path] = safe_entry(found[0], data)
  return p.seal(
    {
      'schema': 'EMPIRICAL_ADDITIONAL_SOURCE_FINGERPRINT_V1',
      'commit': commit,
      'repository': source['repository'],
      'public_available': public_available is True,
      # Per-route dirty initData remains an additional admission gate, never inferred from Git.
      'dirty': False,
      'dirty_meaning': 'PUBLIC_COMMIT_OBJECT_ONLY_RECORDED_BUILD_ATTESTATION_REQUIRED',
      'recorded_build_clean_attested': False,
      'files': source['files'],
      'licenses': source['licenses'],
      'missing_roles': source['missing_roles'],
      'missing_dependencies': missing,
      'closure': {k: v['normalized_source_sha256'] for k, v in closure.items()},
      'closure_entries': closure,
      'complete': source['complete'] and not missing and all(v['normalized_source_sha256'] is not None for v in closure.values()),
      'schema_manifest_sha256': source['manifest_sha256'],
      'metadata_adapter': 'EXACT_LOGGER_SCHEMA_REVIEW_REQUIRED_NO_GENERIC_FALLBACK',
      'numeric_adapter': 'PREPARATION_ONLY_NOT_IMPLEMENTED_NOT_AUTHORIZED',
      'runtime_steer_max': 'METADATA_PROVENANCE_REQUIRED_NUMERIC_CONFIRMATION_NOT_RUN',
      'numeric_runtime_validation': 'NOT_RUN',
    }
  )


def compare_bound(a, b):
  if not a.get('predicate_sha256') or not b.get('predicate_sha256'):
    return 'SOURCE_AUDIT_PARTIAL'
  result = compare(a, b)
  if result == 'SOURCE_EQUIVALENT' and a['predicate_sha256'] != b['predicate_sha256']:
    return 'SOURCE_ADAPTER_REQUIRED'
  return result


def predicate(repo, commit):
  import ast

  git = ['git', '-c', f'safe.directory={repo}', '-C', str(repo)]
  paths = subprocess.check_output([*git, 'ls-tree', '-r', '--name-only', commit]).decode().splitlines()
  path = next((x for x in ('openpilot/selfdrive/controls/lib/drive_helpers.py', 'selfdrive/controls/lib/drive_helpers.py') if x in paths), None)
  if path is None:
    return p.seal({'schema': 'EMPIRICAL_ADDITIONAL_PREDICATE_V1', 'commit': commit, 'predicate_sha256': None, 'status': 'SOURCE_AST_UNAVAILABLE'})
  data = subprocess.check_output([*git, 'show', f'{commit}:{path}'])
  try:
    text = data.decode()
    node = next(x for x in ast.parse(text).body if isinstance(x, ast.FunctionDef) and x.name == 'is_volkswagen_meb')
    segment = ast.get_source_segment(text, node).encode()
    normalized = p.sha(f.normalized_source(segment, '.py'))
  except (UnicodeError, SyntaxError, StopIteration):
    normalized = None
  return p.seal(
    {
      'schema': 'EMPIRICAL_ADDITIONAL_PREDICATE_V1',
      'commit': commit,
      'path': path,
      'file_sha256': p.sha(data),
      'predicate_sha256': normalized,
      'status': 'SOURCE_SYMBOL_BOUND' if normalized else 'SOURCE_AST_UNAVAILABLE',
    }
  )


def class_report(sources, predicates, reference):
  """Full normalized manifest/closure equality only; no similarity promotion."""
  groups, rows = {}, []
  for item in sources:
    p.verify(item)
    pred = p.verify(predicates[item['commit']])
    bound = {**item, 'predicate_sha256': pred['predicate_sha256']}
    status = compare_bound(reference, bound)
    key = p.sha(
      p.canonical(
        {
          'files': {k: v['normalized_source_sha256'] for k, v in item['files'].items()},
          'closure': item['closure'],
          'predicate_sha256': pred['predicate_sha256'],
        }
      )
    )
    complete = item['complete'] is True and pred['predicate_sha256'] is not None
    if complete:
      groups.setdefault(key, []).append(item['commit'])
    rows.append(
      {
        'source_commit': item['commit'],
        'repository': item['repository'],
        'source_receipt_sha256': item['receipt_sha256'],
        'predicate_receipt_sha256': pred['receipt_sha256'],
        'status_against_existing_source_reference': status,
        'source_audit_complete': complete,
        'class_id': key if complete else None,
        'missing_roles': item['missing_roles'],
        'missing_dependencies': item['missing_dependencies'],
        'files': item['files'],
        'closure_entries': item.get('closure_entries', {}),
        'licenses': item.get('licenses', {}),
        'predicate': pred,
        'recorded_build_attestation': 'ROUTE_METADATA_REQUIRED_NOT_INFERRED_FROM_PUBLIC_COMMIT',
        'metadata_adapter': 'SOURCE_BOUND_CONTRACT_PREPARED_EXECUTOR_NOT_IMPLEMENTED',
        'numeric_adapter': 'SOURCE_BOUND_CONTRACT_PREPARED_NO_NUMERIC_EXECUTION',
        'adapter_contract': {
          'source_fingerprint_sha256': item['receipt_sha256'],
          'logger_schema_file_sha256': {k: v['file_sha256'] for k, v in item['files'].items() if k.startswith(('logger', 'schema_'))},
          'generic_fallback': False,
          'missing_field': 'NULL_WITH_REASON',
          'runtime_steer_max': 'SOURCE_DEFAULT_NOT_RUNTIME_PROOF_METADATA_RECEIPT_REQUIRED',
          'route_admission': 'EXACT_IDENTITY_CLEAN_BUILD_PROFILE_LINEAGE_REQUIRED',
          'execution_allowed': False,
        },
      }
    )
  return p.seal(
    {
      'schema': 'EMPIRICAL_ADDITIONAL_SOURCE_CLASSES_V1',
      'reference_commit': reference['commit'],
      'scope': 'EXACT_REQUIRED_SOURCE_AND_LOGICAL_CLOSURE_ONLY',
      'source_results': rows,
      'classes': [
        {'class_id': key, 'member_commits': sorted(members), 'physical_runtime_equivalence': False} for key, members in sorted(groups.items())
      ],
      'public_source_available_count': sum(x['public_available'] for x in sources),
      'complete_source_count': sum(x['source_audit_complete'] for x in rows),
      'partial_source_count': sum(not x['source_audit_complete'] for x in rows),
      'route_admission_automatic': False,
      'numeric_runtime_validation': 'NOT_RUN',
      'old_source_receipts_reused_not_regenerated': True,
    }
  )
