"""Mandatory E-authorized immutable V4 store; separately labelled synthetic store."""

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import gzip
import io
import os

import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_authorization as a

p = a.p
_SCOPE = ContextVar('v4_output', default=None)
_USAGE = ContextVar('v4_output_bytes', default=None)


@contextmanager
def synthetic_output(root):
  root = a.prior.safe(Path(root))
  a.need(not any(root.is_relative_to(Path('/mnt') / x) for x in ('c', 'd', 'f')), 'V4_OUTPUT_ROOT_INVALID')
  token = _SCOPE.set((root, None))
  used = _USAGE.set({'all': 0, 'json': 0})
  try:
    yield
  finally:
    _USAGE.reset(used)
    _SCOPE.reset(token)


@contextmanager
def output(permit):
  a.valid(permit)
  token = _SCOPE.set((permit.roots['output'] / permit.replica, permit))
  used = _USAGE.set({'all': 0, 'json': 0})
  try:
    yield
  finally:
    _USAGE.reset(used)
    _SCOPE.reset(token)


def checked(path, required=0):
  scope = _SCOPE.get()
  a.need(scope is not None, 'V4_OUTPUT_NOT_AUTHORIZED')
  root, permit = scope
  path = a.prior.safe(Path(path))
  a.need(path.is_relative_to(root) and path != root, 'V4_OUTPUT_ROOT_INVALID')
  if permit is not None:
    a.valid(permit)
    a.need(a.prior.free_bytes(root) >= required + permit.authorization['resource_budget']['reserve_bytes'], 'V4_EXECUTION_STORAGE_CAPACITY_FAILURE')
  return path


def durable(path):
  fd = os.open(path, os.O_DIRECTORY | os.O_RDONLY)
  try:
    os.fsync(fd)
  finally:
    os.close(fd)


def atomic(path, payload):
  path = checked(path, len(payload))
  usage = _USAGE.get()
  _, permit = _SCOPE.get()
  if permit is not None:
    bound = a.capacity(permit.pack['jobs'], permit.authorization['resource_budget'])
    a.need(usage['all'] + len(payload) <= bound['run1_upper_bytes'], 'V4_EXECUTION_STORAGE_CAPACITY_FAILURE')
    if path.suffix == '.json':
      a.need(usage['json'] + len(payload) <= bound['metadata_upper_bytes'], 'V4_EXECUTION_METADATA_RESOURCE_BOUND')
  a.need(not path.exists(), 'V4_NO_OVERWRITE')
  path.parent.mkdir(parents=True, exist_ok=True)
  temp = checked(path.with_name(path.name + '.atomic'), len(payload))
  with temp.open('xb') as stream:
    stream.write(payload)
    stream.flush()
    os.fsync(stream.fileno())
  os.link(temp, path)
  temp.unlink()
  durable(path.parent)
  usage['all'] += len(payload)
  if path.suffix == '.json':
    usage['json'] += len(payload)


def write_json(path, row):
  p.verify(row)
  atomic(path, p.canonical(row))


def array_write(path, array):
  array = np.ascontiguousarray(array)
  a.need(array.dtype.kind in 'biuf' and not array.dtype.hasobject and np.isfinite(array).all(), 'V4_NUMERICAL_FAILURE')
  # Buffer bounded by one array, no N×threshold structures.
  decoded = io.BytesIO()
  np.save(decoded, array, allow_pickle=False)
  raw = decoded.getvalue()
  stream = io.BytesIO()
  with gzip.GzipFile(fileobj=stream, mode='wb', compresslevel=1, mtime=0, filename='') as gz:
    gz.write(raw)
  payload = stream.getvalue()
  atomic(path, payload)
  return {
    'dtype': array.dtype.str,
    'shape': list(array.shape),
    'order': 'C',
    'array_sha256': p.sha(array.tobytes()),
    'npy_sha256': p.sha(raw),
    'file_sha256': p.sha(payload),
    'filename': Path(path).name,
    'storage_format': 'NPY_GZIP_V1',
    'lossless_roundtrip_verified': True,
  }


def finish(root, body):
  root = a.prior.safe(Path(root))
  files = {}
  for path in sorted(root.rglob('*')):  # Own output only, never inventory inputs.
    a.prior.safe(path)
    a.need(not path.name.endswith('.atomic'), 'V4_INCOMPLETE_STORE')
    if path.is_file():
      files[path.relative_to(root).as_posix()] = a.prior.digest(path)
  manifest = p.seal({**body, 'files': files})
  write_json(root / 'manifest.json', manifest)
  return manifest


def verify(root, expected_sha):
  """Saved-output hashes and decoded array identities, no inference/dependencies open."""
  try:
    root = a.prior.safe(Path(root))
    manifest = a.prior.read_json(root / 'manifest.json', expected_sha)
    a.need(manifest['schema'] in ('V4_RUN_MANIFEST', 'V4_JOB_MANIFEST', 'V4_TRAIN_MANIFEST'))
    names = set(manifest['files'])
    actual = set()
    for path in root.rglob('*'):
      a.prior.safe(path)
      if path.is_file():
        actual.add(path.relative_to(root).as_posix())
    a.need(actual == names | {'manifest.json'})
    for name, sha in manifest['files'].items():
      path = a.prior.member(root, name)
      a.need(a.prior.digest(path) == sha)
      if name.endswith('.json'):
        row = a.prior.read_json(path)
        if 'arrays' in row:
          for entry in row['arrays'].values():
            array_path = a.prior.member(path.parent, entry['filename'])
            relative = array_path.relative_to(root).as_posix()
            a.need(manifest['files'].get(relative) == entry['file_sha256'])
            for _ in a.prior.verified.array_chunks(array_path, entry):
              pass
        if row.get('schema') in ('V4_TRAIN_MANIFEST', 'V4_JOB_MANIFEST'):
          for member_name, member_sha in row['files'].items():
            child = a.prior.member(path.parent, member_name)
            a.need(manifest['files'].get(child.relative_to(root).as_posix()) == member_sha)
        if row.get('schema') == 'V4_TRAIN_FINALIZED':
          train = a.prior.read_json(path.parent / 'train/manifest.json', row['train_manifest_sha256'])
          model = a.prior.read_json(path.parent / 'train/receipt.json', row['model_threshold_receipt_sha256'])
          a.need(train['train_receipt_sha256'] == model['receipt_sha256'] and model['schema'] == 'V4_MODEL_THRESHOLD')
          a.need(model['train_anchor_sha256'] == row['train_anchor_sha256'] and model['authorization_sha256'] == row['authorization_sha256'])
      elif name.endswith('.npy.gz'):
        with gzip.open(path, 'rb') as stream:
          value = np.load(stream, allow_pickle=False)
          a.need(value.dtype.kind in 'biuf' and value.flags.c_contiguous and np.isfinite(value).all() and not stream.read(1))
      else:
        a.need(False)
    if manifest['schema'] == 'V4_RUN_MANIFEST' and manifest.get('synthetic') is False:
      results = a.prior.read_json(root / 'results.json', manifest['result_sha256'])
      selected = a.prior.read_json(root / 'selection.json', manifest['selection_sha256'])
      a.need(results['schema'] == 'V4_RESULTS' and results['job_count'] == 32 and selected['schema'] == 'V4_SELECTION')
      a.need(results['selection_sha256'] == selected['receipt_sha256'])
      a.need([(j['candidate_id'], j['fold']) for j in results['jobs']] == list(a.prior.JOBS))
      for job in results['jobs']:
        base = root / 'candidates' / job['candidate_id'] / job['fold']
        saved = a.prior.read_json(base / 'receipt.json', job['receipt_sha256'])
        job_manifest = a.prior.read_json(base / 'manifest.json')
        a.need(saved == job and job_manifest['job_receipt_sha256'] == saved['receipt_sha256'])
        a.need(len(job['gate']['clauses']) == 32 and type(job['gate']['pass']) is bool)
    return manifest
  except (OSError, ValueError, TypeError, KeyError, EOFError) as exc:
    raise ValueError('V4_RESUME_INTEGRITY_FAILURE') from exc
