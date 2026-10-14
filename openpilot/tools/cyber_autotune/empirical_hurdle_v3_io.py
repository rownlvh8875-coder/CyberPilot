"""Externally authorized V3 admission. No grant minting, path search or refitting."""

from dataclasses import dataclass
from contextlib import contextmanager, ExitStack
from pathlib import Path
import shutil
import math
import re
import os
import struct
import subprocess
import weakref

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_policy as policy
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_io as legacy
from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as verified
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_external_storage as external
from openpilot.tools.cyber_autotune.empirical_hurdle_v3_scaffold import validate_reference

AUTH_SCHEMA = 'EMPIRICAL_HURDLE_STAGE1_V3_RETROSPECTIVE_EXECUTION_AUTHORIZATION'
COMPRESSION = {'format': 'NPY_GZIP_V1', 'order': 'C', 'level': 1, 'mtime': 0, 'filename': ''}
MANIFEST_KEYS = ('causal', 'derived_index', 'derived_result', 'source_file_set', 'derived_file_set', 'v1_file_set')
ROOT_KEYS = ('source', 'causal', 'derived', 'output')
FORBIDDEN_CALLS = ('STAGE1_FIT', 'STAGE2_FIT', 'NORMALIZER_FIT', 'RAW_RLOG', 'QLOG', 'HOLDOUT', 'CAUSAL_REBUILD', 'POOLED_REFIT', 'VEHICLE_WRITE')
FIREWALL_SHA = p.sha(p.canonical(FORBIDDEN_CALLS))
AUTH_FIELDS = {
  'schema', 'head', 'policies', 'executor_sources', 'v1_manifest_sha256', 'v1_authorization_sha256', 'v1_repeatability_sha256',
  'source_manifests', 'root_identities', 'jobs', 'environment', 'compression', 'capacity_preflight', 'no_refit_firewall_sha256',
  'numeric_access_authorized', 'prediction_only_authorized', 'train_only_decision_authorized', 'stage1_refit_authorized',
  'stage2_refit_authorized', 'normalizer_refit_authorized', 'holdout', 'opening_count', 'holdout_discovery', 'vehicle_authority',
  'pooled_refit_authorized', 'raw_qlog_authorized',
} | set(p.FIREWALL) | {'receipt_sha256'}
ENV_KEYS = {'python', 'numpy', 'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'blas_build_identity_sha256', 'private_build_metadata',
            'dtype', 'order', 'rng', 'zlib_runtime_version'}
JOBS = verified.JOBS
_GATES = weakref.WeakKeyDictionary()
_PERMITS = weakref.WeakKeyDictionary()
safe, member, digest, read_json = verified.safe, verified.member, verified.digest, verified.read_json


def require(value, message='V3_EXECUTION_AUTHORIZATION_CONFLICT'):
  if not value:
    raise ValueError(message)


def sources():
  root = Path(__file__).parent
  names = set(legacy.sources()) | {x.name for x in root.glob('empirical_hurdle_v3*.py')}
  names.update(('empirical_s2_ri_execution.py', 'empirical_causal_dataset_store.py', 'empirical_s2_ri_policy.py', 'empirical_s2_ri_reconstruction_math.py'))
  return {name: digest(root / name) for name in sorted(names)}


def current_head():
  return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=p.PUBLIC, text=True).strip()


def job_identity(job):
  return {
    'candidate_id': job['candidate_id'], 'fold': job['fold'],
    'train_count': job['train_count'], 'train_move_count': job['train_move_count'], 'train_static_count': job['train_static_count'],
    'train_route': job['train_route'], 'development_route': job['development_route'],
    'train_anchor_sha256': job['train_anchor_sha256'],
    'development_anchor': {k: job['one_step'][k] for k in ('count', 'anchor_sha256')},
    'rollout_anchors': {str(h): {k: job['rollout'][str(h)]['overall'][k] for k in ('count', 'anchor_sha256')} for h in verified.HORIZONS},
    'models': {stage: {k: job[stage][k] for k in ('model_receipt_sha256', 'coefficient_sha256', 'normalizer_receipt_sha256')}
               for stage in ('stage1', 'stage2')},
    'v1_confusion_receipt_sha256': job['threshold']['receipt_sha256'], 'reference_tp': job['threshold']['TP'],
  }


def reference(job, row):
  expected = {
    'candidate_id': job['candidate_id'], 'fold': job['fold'], 'reference_tp': job['threshold']['TP'],
    'positive_count': job['train_move_count'], 'negative_count': job['train_static_count'],
    'v1_confusion_receipt_sha256': job['threshold']['receipt_sha256'], 'train_anchor_sha256': job['train_anchor_sha256'],
    'stage1_model_sha256': job['stage1']['model_receipt_sha256'], 'stage1_coefficient_sha256': job['stage1']['coefficient_sha256'],
    'stage1_normalizer_sha256': job['stage1']['normalizer_receipt_sha256'],
  }
  require(row == expected, 'V3_REFERENCE_CONFLICT')
  validate_reference(row['reference_tp'], row['positive_count'])
  require(type(row['negative_count']) is int and row['negative_count'] >= 201, 'V3_REFERENCE_CONFLICT')
  return row


def contracts():
  bundle = policy.build()
  policy.validate(bundle)
  require(all(read_json(p.PUBLIC / name) == row for name, row in bundle.items()), 'V3_PUBLIC_POLICY_CONFLICT')
  jobs = verified.public_inputs()['fit-cv-results']['jobs']
  training = bundle[policy.filename('fitting-policy')]['training_contract']
  require(training == {k: v for k, v in bundle[policy.filename('training-policy')].items()
                       if k in training}, 'V3_PUBLIC_POLICY_CONFLICT')
  refs = training['references']
  require(len(refs) == len(jobs) == 32)
  for job, ref in zip(jobs, refs, strict=True):
    reference(job, ref)
  return {
    'bundle': bundle, 'jobs': jobs, 'references': refs,
    'receipts': {k: bundle[policy.filename(k)]['receipt_sha256'] for k in ('policy', 'fitting-policy', 'execution-policy')},
    'clauses': legacy.old.contracts()['acceptance-gate']['clauses'], 'source_policy': legacy.old.source_policy.policy(),
  }


def capacity(jobs):
  # Exact V3 payload: TRAIN gate+int16 tick; DEV p/gate/delta/error/int16 tick;
  # each rollout int16 path + bool gate path + float64 endpoint error.
  payload, peak = 0, 0
  for job in jobs:
    n, dev = job['train_count'], job['one_step']['count']
    require(type(n) is int and type(dev) is int and min(n, dev) >= 0)
    payload += n * 3 + dev * 27
    peak = max(peak, n * 2, dev * 8)
    for h in verified.HORIZONS:
      count = job['rollout'][str(h)]['overall']['count']
      require(type(count) is int and count >= 0)
      payload += count * ((h + 1) * 2 + h + 8)
      peak = max(peak, count * (h + 1) * 2)
  # Reuse the established V2 incompressible gzip and metadata/reserve bounds.
  bound = payload + payload // 100 + legacy.METADATA_BUDGET
  atomic = peak + peak // 100 + 65536
  return {'run1_upper_bytes': bound, 'run2_upper_bytes': bound, 'atomic_upper_bytes': atomic,
          'metadata_upper_bytes': legacy.METADATA_BUDGET, 'safety_reserve_bytes': legacy.RESERVE,
          'required_bytes': 2 * bound + atomic + legacy.RESERVE}


def validate_authorization(auth, expected, head, pack):
  if auth is None:
    raise ValueError('V3_PRIVATE_EXECUTION_NOT_AUTHORIZED')
  try:
    require(type(auth) is dict)
    amended = auth.get('storage_volume') == 'E_EXTERNAL_SSD'
    require(set(auth) == AUTH_FIELDS | (external.AUTH_FIELDS if amended else set()))
    p.verify(auth)
    require(type(expected) is str and auth['receipt_sha256'] == expected)
    require(auth['schema'] == AUTH_SCHEMA and auth['head'] == head)
    require(auth['policies'] == pack['receipts'] and auth['executor_sources'] == sources())
    require(auth['v1_manifest_sha256'] == verified.SOURCE_SHA and auth['v1_authorization_sha256'] == verified.AUTH_SHA
            and auth['v1_repeatability_sha256'] == verified.REPEAT_SHA)
    require(auth['jobs'] == [job_identity(j) for j in pack['jobs']])
    require(auth['no_refit_firewall_sha256'] == FIREWALL_SHA and auth['compression'] == COMPRESSION)
    require(set(auth['source_manifests']) == set(MANIFEST_KEYS))
    require(set(auth['root_identities']) == set(ROOT_KEYS))
    for value in (*auth['source_manifests'].values(), *auth['root_identities'].values()):
      require(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value))
    require(all(auth[k] is True for k in ('numeric_access_authorized', 'prediction_only_authorized', 'train_only_decision_authorized')))
    require(all(auth[k] is False for k in ('stage1_refit_authorized', 'stage2_refit_authorized', 'normalizer_refit_authorized',
                                         'pooled_refit_authorized', 'raw_qlog_authorized')))
    require(auth['holdout'] == 'CLOSED' and auth['vehicle_authority'] == 'NONE')
    require(all(type(auth[k]) is int and auth[k] == 0 for k in ('opening_count', 'holdout_discovery')))
    require(set(auth['environment']) == ENV_KEYS)
    required_env = {'python': '3.12.13', 'numpy': '2.5.3', 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
                    'blas_build_identity_sha256': legacy.BLAS_SHA, 'dtype': 'float64', 'order': 'C', 'rng': 'NONE'}
    require(all(auth['environment'][k] == v for k, v in required_env.items()))
    estimate = capacity(pack['jobs'])
    require(set(auth['capacity_preflight']) == set(estimate) | {'free_bytes'})
    require(all(auth['capacity_preflight'][k] == v for k, v in estimate.items()))
    require(type(auth['capacity_preflight']['free_bytes']) is int and auth['capacity_preflight']['free_bytes'] >= estimate['required_bytes'])
    if amended:
      external.validate_bindings(auth)
  except (ValueError, KeyError, TypeError, AttributeError) as exc:
    raise ValueError('V3_EXECUTION_AUTHORIZATION_CONFLICT') from exc


def roots_explicit(source, causal, derived, output, auth):
  if any(x is None for x in (source, causal, derived)):
    raise ValueError('V3_PRIVATE_SOURCE_UNRESOLVED')
  require(output is not None, 'V3_OUTPUT_ROOT_INVALID')
  try:
    roots = {key: safe(value) for key, value in zip(ROOT_KEYS, (source, causal, derived, output), strict=True)}
    if 'storage_volume' not in auth:
      for root in roots.values():
        reject_mount_aliases(root)
    require({key: p.sha(str(value).encode()) for key, value in roots.items()} == auth['root_identities'])
    require(all(roots[key].is_dir() for key in ('source', 'causal', 'derived')), 'V3_PRIVATE_SOURCE_UNRESOLVED')
    return roots
  except (ValueError, OSError) as exc:
    if str(exc) in ('V3_PRIVATE_SOURCE_UNRESOLVED', 'V3_OUTPUT_ROOT_INVALID', 'V3_EXECUTION_AUTHORIZATION_CONFLICT'):
      raise
    raise ValueError('V3_OUTPUT_ROOT_INVALID') from exc


def non_overlap(roots):
  values = [*roots.values(), p.PUBLIC.parents[2]]
  for i, left in enumerate(values):
    for right in values[i + 1:]:
      a, b = str(left).casefold().rstrip('/'), str(right).casefold().rstrip('/')
      require(not (a == b or a.startswith(b + '/') or b.startswith(a + '/')), 'V3_OUTPUT_ROOT_INVALID')
      # Examine ancestors only; never inventory caller roots.
      for root, other in ((left, right), (right, left)):
        if root.exists():
          require(not any(x.exists() and root.samefile(x) for x in (other, *other.parents)), 'V3_OUTPUT_ROOT_INVALID')


def mount_records():
  """Kernel mount metadata only, never a filesystem/root inventory."""
  def decode(value):
    return re.sub(r'\\([0-7]{3})', lambda match: chr(int(match[1], 8)), value)

  records = []
  for line in Path('/proc/self/mountinfo').read_text().splitlines():
    fields = line.split()
    separator = fields.index('-')
    records.append({'point': Path(decode(fields[4])), 'root': decode(fields[3]), 'device': fields[2],
                    'filesystem': fields[separator + 1], 'source': decode(fields[separator + 2])})
  return records


def mount_points():
  return {row['point'] for row in mount_records()}


def reject_mount_aliases(root):
  # The supported execution topology is the WSL root plus the explicit D
  # volume. Additional ancestor mounts can hide source descendant aliases.
  # Reject them rather than resolve a caller-controlled nested bind mapping.
  require(not any(root.is_relative_to(point) for point in mount_points() if point not in (Path('/'), Path('/mnt/d'))),
          'V3_OUTPUT_ROOT_INVALID')


def prove_d(root):
  root = safe(root)
  require(root.is_relative_to(Path('/mnt/d')), 'V3_OUTPUT_ROOT_INVALID')
  records = [row for row in mount_records() if row['point'] == Path('/mnt/d')]
  require(len(records) == 1, 'V3_OUTPUT_ROOT_INVALID')
  row = records[0]
  require(row['root'] == '/' and row['filesystem'] == '9p' and row['source'].casefold().rstrip('\\/') == 'd:', 'V3_OUTPUT_ROOT_INVALID')
  existing = root
  while not existing.exists():
    existing = existing.parent
  device = existing.stat().st_dev
  require(device == Path('/mnt/d').stat().st_dev and row['device'] == f'{os.major(device)}:{os.minor(device)}', 'V3_OUTPUT_ROOT_INVALID')


def free_bytes(root):
  existing = root
  while not existing.exists():
    existing = existing.parent
  return shutil.disk_usage(existing).free


def environment():
  try:
    env = legacy.old.environment()
    require(env['blas_build_identity_sha256'] == legacy.BLAS_SHA)
    return env
  except ValueError as exc:
    raise ValueError('V3_EXECUTION_ENVIRONMENT_CONFLICT') from exc


def preflight(*, authorization, authorization_sha256, source_root=None, causal_root=None, derived_root=None, output_root=None):
  pack, head = contracts(), current_head()
  if isinstance(authorization, Path):
    try:
      require(authorization.suffix == '.json')
      authorization = read_json(safe(authorization), authorization_sha256)
    except (ValueError, OSError, KeyError, TypeError) as exc:
      raise ValueError('V3_EXECUTION_AUTHORIZATION_CONFLICT') from exc
  validate_authorization(authorization, authorization_sha256, head, pack)
  roots = roots_explicit(source_root, causal_root, derived_root, output_root, authorization)
  if 'storage_volume' in authorization:
    external.roots_checked(roots, authorization)
  else:
    prove_d(roots['output'])
  non_overlap(roots)
  require(free_bytes(roots['output']) >= capacity(pack['jobs'])['required_bytes'], 'V3_STORAGE_CAPACITY_BLOCKED')
  require(environment() == authorization['environment'], 'V3_EXECUTION_ENVIRONMENT_CONFLICT')
  gate = AdmissionGate(roots, authorization, authorization_sha256, pack)
  _GATES[gate] = authorization_sha256
  try:
    return admit_metadata(gate)
  except OSError as exc:
    raise ValueError('V3_PRIVATE_SOURCE_UNRESOLVED') from exc
  except ValueError as exc:
    if str(exc).startswith('V3_'):
      raise
    raise ValueError('V3_EXECUTION_AUTHORIZATION_CONFLICT') from exc


@dataclass(frozen=True, eq=False)
class AdmissionGate:
  roots: dict
  authorization: dict
  trusted_sha256: str
  pack: dict


@dataclass(frozen=True, eq=False)
class Permit:
  roots: dict
  authorization: dict
  trusted_sha256: str
  pack: dict
  jobs: tuple
  records: tuple
  pins: dict
  record_sha256: str


def records_identity(records):
  return p.sha(p.canonical([{'base': str(base), 'segment': segment, 'root': str(root), 'derived': local} for base, segment, root, local in records]))


def permit_valid(permit):
  require(isinstance(permit, Permit), 'V3_PRIVATE_EXECUTION_NOT_AUTHORIZED')
  require(_PERMITS.get(permit) == permit.trusted_sha256, 'V3_PRIVATE_EXECUTION_NOT_AUTHORIZED')
  p.verify(permit.authorization)
  require(permit.authorization['receipt_sha256'] == permit.trusted_sha256)
  require({k: p.sha(str(v).encode()) for k, v in permit.roots.items()} == permit.authorization['root_identities'])
  if 'storage_volume' in permit.authorization:
    external.check_live_volume(permit.authorization['volume_identity_sha256'])
    for root in permit.roots.values():
      external.prove_authorized_external_volume(root, expected_mount=permit.authorization['mount_identity_sha256'])
  require([job_identity(j) for j in permit.jobs] == permit.authorization['jobs'])
  require(records_identity(permit.records) == permit.record_sha256, 'V3_ANCHOR_IDENTITY_CONFLICT')
  require(set(permit.pins) == {'v1', 'causal', 'derived'})
  for key, binding in (('v1', 'v1_file_set'), ('causal', 'source_file_set'), ('derived', 'derived_file_set')):
    require(p.sha(p.canonical(permit.pins[key])) == permit.authorization['source_manifests'][binding])
  for job in permit.jobs:
    p.verify(job)


@contextmanager
def execution_storage(permit):
  permit_valid(permit)
  if 'storage_volume' in permit.authorization:
    with external.output_scope(permit.authorization, permit.roots['output']):
      yield
  else:
    yield


def validate_saved_storage(output, auth):
  if 'storage_volume' in auth:
    external.verify_saved_output(output, auth)


@contextmanager
def saved_storage(output, auth):
  validate_saved_storage(output, auth)
  if 'storage_volume' in auth:
    with external.output_scope(auth, output):
      yield
  else:
    yield


def metadata_member(root, name, pins, expected=None):
  path = member(root, name)
  require(name in pins and digest(path) == pins[name], 'V3_MODEL_IDENTITY_CONFLICT')
  try:
    return read_json(path, expected)
  except ValueError as exc:
    raise ValueError('V3_MODEL_IDENTITY_CONFLICT') from exc


def admit_metadata(gate):
  """Only admitted JSON/metadata. No V2 authorize() or metadata() grant minting."""
  require(isinstance(gate, AdmissionGate) and _GATES.get(gate) == gate.trusted_sha256, 'V3_PRIVATE_EXECUTION_NOT_AUTHORIZED')
  roots, auth, trusted, pack = gate.roots, gate.authorization, gate.trusted_sha256, gate.pack
  p.verify(auth)
  require(auth['receipt_sha256'] == trusted)
  source, causal, derived = (roots[k] for k in ('source', 'causal', 'derived'))
  original_auth = read_json(source / 'authorization.json', verified.AUTH_SHA)
  manifest = read_json(source / 'repeat-1/manifest.json', verified.SOURCE_SHA)
  repeat = read_json(source / 'repeatability.json', verified.REPEAT_SHA)
  require(manifest['authorization_sha256'] == verified.AUTH_SHA and manifest['job_count'] == 32)
  require(repeat['manifest_sha256'] == verified.SOURCE_SHA and repeat['all_file_hashes_equal'] is True)
  # Reject malformed members before opening any manifest-listed member.
  for name in manifest['files']:
    member(source / 'repeat-1', name)
  pins = read_json(source / 'input-pins.json')
  require(pins['authorization_sha256'] == verified.AUTH_SHA)
  for key in ('source', 'derived'):
    require(p.sha(p.canonical(pins[key])) == original_auth[key + '_file_set_sha256'])
    for name in pins[key]:
      member(causal if key == 'source' else derived, name)
  source_policy = pack['source_policy']
  _, resolved, causal_manifest, records, _ = legacy.old.metadata.preflight(causal, source_policy)
  require(resolved['final_dataset_status'] == 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL')
  index = read_json(derived / 'repeat-1/derived-index.json', original_auth['derived_index_sha256'])
  result = read_json(derived / 'repeat-1/results.json', original_auth['derived_result_sha256'])
  admission = read_json(derived / 'repeat-1/admission.json', result['admission_sha256'])
  require(admission['manifest_sha256'] == causal_manifest['receipt_sha256'])
  identities = {'causal': causal_manifest['receipt_sha256'], 'derived_index': index['receipt_sha256'], 'derived_result': result['receipt_sha256'],
                'source_file_set': original_auth['source_file_set_sha256'], 'derived_file_set': original_auth['derived_file_set_sha256'],
                'v1_file_set': p.sha(p.canonical(manifest['files']))}
  require(identities == auth['source_manifests'])
  require(causal_manifest['receipt_sha256'] == original_auth['source_manifest_sha256'])
  indexed = {s['content_sha256']: s['receipt_sha256'] for s in index['segments']}
  require(len(indexed) == len(records) == 154 and set(indexed) == {s['segment_sha256'] for _, s in records})
  require(not set(indexed).intersection(source_policy['excluded_qlog_content_sha256']))
  attached = []
  for base, segment in sorted(records, key=lambda row: (row[1]['route_id'], row[1]['segment_sha256'])):
    root = derived / 'repeat-1/segments' / segment['segment_sha256']
    local = read_json(root / 'receipt.json', indexed[segment['segment_sha256']])
    require(local['source_receipt_sha256'] == segment['receipt_sha256'] and local['policy_sha256'] == source_policy['receipt_sha256'])
    attached.append((base, segment, root, local))
  jobs = []
  for public, ref in zip(pack['jobs'], pack['references'], strict=True):
    prefix = f"candidates/{public['candidate_id']}/{public['fold']}"
    job = metadata_member(source / 'repeat-1', prefix + '/receipt.json', manifest['files'], public['receipt_sha256'])
    require(job['status'] == 'EXECUTED_COMPLETE' and job_identity(job) == job_identity(public), 'V3_MODEL_IDENTITY_CONFLICT')
    reference(job, ref)
    decision = metadata_member(source / 'repeat-1', prefix + '/threshold/receipt.json', manifest['files'], ref['v1_confusion_receipt_sha256'])
    require(all(decision['selection'][k] == ref[r] for k, r in (('TP', 'reference_tp'), ('P', 'positive_count'), ('N', 'negative_count'))),
            'V3_REFERENCE_CONFLICT')
    for stage in ('stage1', 'stage2'):
      model = metadata_member(source / 'repeat-1', prefix + f'/{stage}/model/receipt.json', manifest['files'], job[stage]['model_receipt_sha256'])
      norm = metadata_member(source / 'repeat-1', prefix + f'/{stage}/normalizer/receipt.json', manifest['files'], job[stage]['normalizer_receipt_sha256'])
      require(model['normalizer_sha256'] == norm['receipt_sha256']
              and model['arrays']['coefficients']['array_sha256'] == job[stage]['coefficient_sha256'], 'V3_MODEL_IDENTITY_CONFLICT')
      for name, receipt in (('model', model), ('normalizer', norm)):
        for binding in receipt['arrays'].values():
          relative = prefix + f'/{stage}/{name}/' + binding['filename']
          member(source / 'repeat-1', relative)
          require(manifest['files'].get(relative) == binding['file_sha256'], 'V3_MODEL_IDENTITY_CONFLICT')
    jobs.append(job)
  permit = Permit(roots, auth, trusted, pack, tuple(jobs), tuple(attached),
                  {'v1': manifest['files'], 'causal': pins['source'], 'derived': pins['derived']}, records_identity(attached))
  _PERMITS[permit] = trusted
  permit_valid(permit)
  return permit


def job_checked(permit, job):
  permit_valid(permit)
  identity = (job['candidate_id'], job['fold'])
  require(identity in JOBS, 'V3_ANCHOR_IDENTITY_CONFLICT')
  expected = permit.jobs[JOBS.index(identity)]
  require(job == expected, 'V3_MODEL_IDENTITY_CONFLICT')
  return f'candidates/{identity[0]}/{identity[1]}'


def population(permit, job, name):
  prefix = job_checked(permit, job)
  allowed = ('train', 'threshold', 'one-step', *(f'rollout-{h}' for h in verified.HORIZONS))
  require(name in allowed, 'V3_ANCHOR_IDENTITY_CONFLICT')
  expected = job['threshold']['receipt_sha256'] if name == 'threshold' else job['population_receipts'][name]
  return metadata_member(permit.roots['source'] / 'repeat-1', prefix + f'/{name}/receipt.json', permit.pins['v1'], expected)


def require_finalized(permit, job, receipt, replica):
  """A complete, identity-bound, durable decision is required for DEV access."""
  prefix = job_checked(permit, job)
  try:
    require(replica in ('repeat-1', 'repeat-2'))
    p.verify(receipt)
    require(receipt['schema'] == 'V3_PRIVATE_THRESHOLD_RECEIPT' and receipt['status'] == 'V3_THRESHOLD_FINALIZED')
    require((receipt['candidate_id'], receipt['fold']) == (job['candidate_id'], job['fold']))
    require(receipt['authorization_sha256'] == permit.trusted_sha256 and receipt['train_anchor_sha256'] == job['train_anchor_sha256'])
    require(receipt['reference'] == reference(job, permit.pack['references'][JOBS.index((job['candidate_id'], job['fold']))]))
    require(receipt['model_receipts'] == job['stage1']['model_receipt_sha256'] + ':' + job['stage2']['model_receipt_sha256'])
    value = receipt['threshold']
    require(type(value) is float and math.isfinite(value) and 0 <= value <= 1)
    require(receipt['threshold_bytes_sha256'] == p.sha(struct.pack('=d', value)))
    for key in ('probability_sha256', 'stage2_all_train_sha256'):
      require(type(receipt[key]) is str and len(receipt[key]) == 64)
    require(receipt['saved_probability_comparison'] in ('BYTE_EXACT_PASS', 'UNAVAILABLE'))
    require(type(receipt['candidate_count']) is int and type(receipt['feasible_count']) is int
            and 0 < receipt['feasible_count'] <= receipt['candidate_count'] <= job['train_count'] + 2)
    objective = receipt['objective']
    require(objective['feasible'] is True and type(objective['tp']) is int
            and receipt['reference']['reference_tp'] <= objective['tp'] <= receipt['reference']['positive_count'])
    require(type(receipt['canonical_checks']) is int and receipt['canonical_checks'] > 0)
    finalized = read_json(permit.roots['output'] / replica / prefix / 'threshold/receipt.json', receipt['receipt_sha256'])
    require(finalized == receipt)
  except (ValueError, KeyError, TypeError, OSError) as exc:
    raise ValueError('V3_THRESHOLD_FINALIZATION_REQUIRED') from exc
  return receipt


def source_array(permit, job, name, receipt, key, *, decision=None, replica=None):
  # The generic historical reader is not a second DEVELOPMENT loader.
  require(name == 'threshold' and key in ('train_probability', 'threshold'), 'V3_THRESHOLD_FINALIZATION_REQUIRED')
  if key == 'threshold':
    require_finalized(permit, job, decision, replica)
  original = population(permit, job, name)
  require(original == receipt, 'V3_MODEL_IDENTITY_CONFLICT')
  prefix = job_checked(permit, job) + '/' + name
  binding = receipt['arrays'][key]
  relative = prefix + '/' + binding['filename']
  require(permit.pins['v1'].get(relative) == binding['file_sha256'], 'V3_MODEL_IDENTITY_CONFLICT')
  status = 'V3_STAGE1_PREDICTION_IDENTITY_FAILURE' if key == 'train_probability' else 'V3_MODEL_IDENTITY_CONFLICT'
  return decode_bound_array(member(permit.roots['source'] / 'repeat-1', prefix), receipt, key, status)


def decode_bound_array(root, receipt, key, status):
  try:
    return verified.load_array(root, receipt, key)
  except (ValueError, OSError, EOFError) as exc:
    raise ValueError(status) from exc


def load_model(permit, job, stage):
  prefix = job_checked(permit, job)
  require(stage in ('stage1', 'stage2'), 'V3_MODEL_IDENTITY_CONFLICT')
  source = permit.roots['source'] / 'repeat-1'
  expected = job[stage]
  receipts = {name: metadata_member(source, prefix + f'/{stage}/{name}/receipt.json', permit.pins['v1'], expected[name + '_receipt_sha256'])
              for name in ('model', 'normalizer')}
  require(receipts['model']['normalizer_sha256'] == receipts['normalizer']['receipt_sha256']
          and receipts['model']['arrays']['coefficients']['array_sha256'] == expected['coefficient_sha256'], 'V3_MODEL_IDENTITY_CONFLICT')
  arrays = {}
  for name, receipt in receipts.items():
    base = prefix + f'/{stage}/{name}'
    for key, binding in receipt['arrays'].items():
      require(permit.pins['v1'].get(base + '/' + binding['filename']) == binding['file_sha256'], 'V3_MODEL_IDENTITY_CONFLICT')
      arrays[name, key] = decode_bound_array(member(source, base), receipt, key, 'V3_MODEL_IDENTITY_CONFLICT')
  return {'normalizer': {key: arrays['normalizer', key] for key in receipts['normalizer']['arrays']},
          'coefficients': arrays['model', 'coefficients'], 'effective_x_sha256': receipts['model']['effective_x_sha256']}


def load_route(permit, job, *, development=False, threshold_receipt=None, replica=None):
  job_checked(permit, job)
  if development:
    require_finalized(permit, job, threshold_receipt, replica)
  # The unchanged V2 numerical route adapter receives only permit-derived
  # records/route and an ephemeral adapter seal, never an externally minted grant.
  adapter = p.seal({'schema': 'EMPIRICAL_HURDLE_STAGE1_V2_RETROSPECTIVE_EXECUTION_AUTHORIZATION',
                    'prediction_only_authorized': True, 'array_access_before_seal': False,
                    'stage1_fitting_authorized': False, 'stage2_fitting_authorized': False, 'normalizer_fitting_authorized': False,
                    'executor_sources': legacy.sources(), 'routes': permit.pack['source_policy']['route_ids'],
                    'qlog_deny_identities': sorted(permit.pack['source_policy']['excluded_qlog_content_sha256'])})
  route = job['development_route'] if development else job['train_route']
  try:
    return legacy.load_route(permit.records, route, adapter)
  except (ValueError, OSError, EOFError) as exc:
    raise ValueError('V3_ANCHOR_IDENTITY_CONFLICT') from exc


def verify_source_immutability(permit):
  permit_valid(permit)
  read_json(permit.roots['source'] / 'repeat-1/manifest.json', permit.authorization['v1_manifest_sha256'])
  if permit.authorization['schema'] == AUTH_SCHEMA:
    read_json(permit.roots['source'] / 'authorization.json', verified.AUTH_SHA)
    read_json(permit.roots['source'] / 'repeatability.json', verified.REPEAT_SHA)
  for name, root in (('v1', permit.roots['source'] / 'repeat-1'), ('causal', permit.roots['causal']), ('derived', permit.roots['derived'])):
    verified.verify_files(root, permit.pins[name])
  require(sources() == permit.authorization['executor_sources'] and current_head() == permit.authorization['head'])


@contextmanager
def firewall():
  from unittest.mock import patch
  from openpilot.tools.cyber_autotune import empirical_hurdle_v2_execution as executor
  from openpilot.tools.cyber_autotune import empirical_hurdle_v2_threshold as old_threshold

  with ExitStack() as stack:
    stack.enter_context(legacy.firewall())
    for module, names in ((executor, ('run', 'execute_job')), (old_threshold, ('sweep',))):
      for name in names:
        stack.enter_context(patch.object(module, name, legacy.forbidden))
    yield
