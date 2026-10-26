"""Exact public source audit. Hash equality is scoped, never runtime validation."""

import ast
from pathlib import Path
import re
import subprocess

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_policy as policy


def origin_identity(remote, commit, dirty, public_available):
  if not re.fullmatch(r'[0-9a-f]{40}', commit):
    return 'SOURCE_REMOTE_AMBIGUOUS'
  normalized = remote.removesuffix('.git').removesuffix('/')
  if normalized not in ('https://github.com/ajouatom/openpilot', 'git@github.com:ajouatom/openpilot'):
    return 'SOURCE_REMOTE_AMBIGUOUS'
  if type(dirty) is not bool or dirty:
    return 'SOURCE_DIRTY_BUILD_UNATTESTED'
  return 'SOURCE_COMMIT_PUBLICLY_AVAILABLE' if public_available is True else 'SOURCE_COMMIT_UNAVAILABLE'


def normalized_source(data, suffix):
  if suffix == '.py':
    tree = ast.parse(data.decode('utf-8-sig'))
    return ast.dump(tree, annotate_fields=True, include_attributes=False).encode()
  # Conservative raw-byte hash for C++, schemas and DBC: no guessed lexer.
  # Formatting-only equivalence outside Python requires explicit source review.
  return data


def source_entry(path, data):
  symbols = {}
  if Path(path).suffix == '.py':
    tree = ast.parse(data.decode('utf-8-sig'))
    for node in ast.walk(tree):
      if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        key = f'{node.name}:{node.lineno}'
        symbols[key] = {'source_slice_sha256': p.sha('\n'.join(data.decode('utf-8-sig').splitlines()[node.lineno - 1:node.end_lineno]).encode()),
                        'normalized_ast_sha256': p.sha(ast.dump(node, include_attributes=False).encode())}
  return {'path': path, 'file_sha256': p.sha(data),
          'normalized_source_sha256': p.sha(normalized_source(data, Path(path).suffix)),
          'symbols': symbols}


def compare(a, b, reviewed_difference=None):
  if not a['complete'] or not b['complete'] or not all(x.get('origin_attested') is True and x.get('dependency_closure_complete') is True for x in (a, b)):
    return 'SOURCE_AUDIT_PARTIAL'
  if set(a['files']) != set(b['files']):
    return 'NOT_EQUIVALENT'
  differences = [k for k in a['files'] if a['files'][k]['file_sha256'] != b['files'][k]['file_sha256']]
  if not differences:
    return 'EXACT_RELEVANT_SOURCE_EQUIVALENT'
  normalized = all(a['files'][k]['normalized_source_sha256'] == b['files'][k]['normalized_source_sha256'] for k in differences)
  if normalized and reviewed_difference == {'paths': sorted(differences), 'scope': 'COMMENTS_FORMATTING_ONLY_REVIEWED'}:
    return 'EMPIRICAL_SIGNAL_SEMANTICS_EQUIVALENT'
  command = ('controller', 'controller_limits', 'controller_helpers', 'card', 'schema_car',
             'can_builder', 'canfd_builder', 'dbc', 'interface', 'interface_base')
  if all(k in a['files'] and k in b['files'] and a['files'][k]['file_sha256'] == b['files'][k]['file_sha256'] for k in command):
    return 'COMMAND_BRIDGE_ONLY_EQUIVALENT'
  return 'NOT_EQUIVALENT'


def audit(repo, commit):
  prefix = ['git', '-c', f'safe.directory={repo}', '-C', str(repo)]
  def git(*args):
    return subprocess.check_output([*prefix, *args])
  if git('rev-parse', f'{commit}^{{commit}}').decode().strip() != commit:
    raise ValueError('EXACT_COMMIT_REQUIRED')
  paths = set(git('ls-tree', '-r', '--name-only', commit).decode().splitlines())
  scope = policy.manifest()
  resolved, missing = {}, []
  for role, choices in scope['files'].items():
    candidates = list(choices)
    if role == 'sensor_main':
      # Explicit language migration; retain all frozen required roles.
      candidates += ['openpilot/system/sensord/sensord.py', 'system/sensord/sensord.py']
    available = [name for name in candidates if name in paths]
    if len(available) != 1:
      missing.append(role)
    else:
      resolved[role] = available[0]
  for name in sorted(paths):
    if any(name.startswith(prefix) for prefix in scope['sensor_dependency_prefixes']) and Path(name).suffix in ('.py', '.cc', '.h'):
      resolved['sensor_dependency:' + name] = name
  # Every imported schema in the two producer schema directories, including C++ import.
  for name in sorted(paths):
    if (name.startswith(('openpilot/cereal/', 'cereal/', 'opendbc_repo/opendbc/car/'))) and name.endswith('.capnp'):
      resolved['schema_dependency:' + name] = name
  files = {role: source_entry(name, git('show', f'{commit}:{name}')) for role, name in sorted(resolved.items())}
  licenses = {name: p.sha(git('show', f'{commit}:{name}')) for name in scope['license_paths'] if name in paths}
  return p.seal({
    'schema': 'EMPIRICAL_SOURCE_SEMANTICS_FINGERPRINT_V1', 'commit': commit,
    'repository': 'https://github.com/ajouatom/openpilot', 'manifest_sha256': scope['receipt_sha256'],
    'path_resolution': 'FROZEN_ROLE_SET_PLUS_EXPLICIT_PYTHON_SENSOR_MAIN_LANGUAGE_MIGRATION',
    'files': files, 'missing_roles': missing, 'complete': not missing and bool(licenses),
    'licenses': licenses, 'license_status': 'EXACT_LICENSE_BLOBS_BOUND_REVIEW_REQUIRED',
    'public_origin_status': 'LOCAL_OBJECT_REQUIRES_PUBLIC_ORIGIN_ATTESTATION',
    'dependency_closure_complete': False, 'dependency_status': 'TRANSITIVE_CALLER_AND_NATIVE_TRANSPORT_CLOSURE_PENDING',
    'signal_physical_units_verified': False, 'numeric_runtime_validation': 'NOT_RUN',
  })
