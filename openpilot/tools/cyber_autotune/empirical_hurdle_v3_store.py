"""Immutable V3 payloads; explicit E amendment or historical D authority."""

from pathlib import Path
import gzip
import hashlib
import os
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_io as io

p = io.p


def checked_output(path, required=0):
  path = io.safe(path)
  if not io.external.checked_bound_output(path):
    io.prove_d(path)
  io.require(io.free_bytes(path) >= required + io.legacy.RESERVE, 'V3_STORAGE_CAPACITY_BLOCKED')
  return path


def durable_directory(path):
  descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
  try:
    os.fsync(descriptor)
  finally:
    os.close(descriptor)


def write_json(path, value):
  path = checked_output(path)
  io.require(not path.exists(), 'V3_NO_OVERWRITE')
  make_directories(path.parent)
  p.persist(path, value)
  durable_directory(path.parent)


def make_directories(path):
  missing = []
  while not path.exists():
    missing.append(path)
    path = path.parent
  for directory in reversed(missing):
    directory.mkdir()
    durable_directory(directory.parent)


def ensure_json(path, value):
  """A shared authorization may already exist; identical bytes are never rewritten."""
  if path.exists():
    io.require(io.read_json(path) == value, 'V3_NO_OVERWRITE')
  else:
    write_json(path, value)


def array_write(path, array):
  array = np.ascontiguousarray(array)
  io.require(not array.dtype.hasobject and array.dtype.kind in 'bifu' and np.isfinite(array).all(), 'V3_NUMERICAL_FAILURE')
  path = checked_output(path, array.nbytes + array.nbytes // 100 + 65536)
  io.require(not path.exists(), 'V3_NO_OVERWRITE')
  make_directories(path.parent)
  temporary = io.safe(path.with_name(path.name + '.atomic'))
  with temporary.open('xb') as stream:
    with gzip.GzipFile(fileobj=stream, mode='wb', filename='', mtime=0, compresslevel=1) as compressed:
      writer = io.legacy.old._HashedWriter(compressed)
      np.save(writer, array, allow_pickle=False)
    stream.flush()
    os.fsync(stream.fileno())
  decoded = hashlib.sha256()
  with gzip.open(temporary, 'rb') as stream:
    for block in iter(lambda: stream.read(1024**2), b''):
      decoded.update(block)
  io.require(decoded.hexdigest() == writer.sha.hexdigest(), 'V3_NUMERICAL_FAILURE_STORAGE')
  os.link(temporary, path)
  temporary.unlink()
  durable_directory(path.parent)
  return {'dtype': array.dtype.str, 'shape': list(array.shape), 'order': 'C',
          'array_sha256': io.legacy.old.array_digest(array), 'file_sha256': io.digest(path), 'npy_sha256': decoded.hexdigest(),
          'storage_format': 'NPY_GZIP_V1', 'filename': path.name, 'lossless_roundtrip_verified': True}


def payload_schema(name, arrays):
  if name == 'train':
    expected = {'predicted_gate': 'b', 'projected_next_tick': 'i'}
  elif name == 'one-step':
    expected = {'p_move': 'f', 'predicted_gate': 'b', 'integrated_delta': 'f', 'candidate_error': 'f', 'projected_next_tick': 'i'}
  elif name in {f'rollout-{h}' for h in io.verified.HORIZONS}:
    expected = {'projected_path': 'i', 'predicted_gate_path': 'b', 'candidate_error': 'f'}
  else:
    raise ValueError('V3_PAYLOAD_SCHEMA_CONFLICT')
  io.require(set(arrays) == set(expected), 'V3_PAYLOAD_SCHEMA_CONFLICT')
  count = len(next(iter(arrays.values())))
  for key, array in arrays.items():
    kind = expected[key]
    io.require(array.dtype.kind == kind and len(array) == count and array.flags.c_contiguous, 'V3_PAYLOAD_SCHEMA_CONFLICT')
    if kind == 'i':
      io.require(array.dtype == np.int16, 'V3_PAYLOAD_SCHEMA_CONFLICT')
    elif kind == 'f':
      io.require(array.dtype == np.float64, 'V3_PAYLOAD_SCHEMA_CONFLICT')
    shape = (count,)
    if key in ('projected_path', 'predicted_gate_path'):
      horizon = int(name.split('-')[1])
      shape = (count, horizon + int(key == 'projected_path'))
    io.require(array.shape == shape, 'V3_PAYLOAD_SCHEMA_CONFLICT')
    io.require(np.isfinite(array).all(), 'V3_NUMERICAL_FAILURE')
  if 'p_move' in arrays:
    io.require(np.all((arrays['p_move'] >= 0) & (arrays['p_move'] <= 1)), 'V3_NUMERICAL_FAILURE')


def population(root, arrays, body):
  payload_schema(body['population'], arrays)
  io.require(not root.exists(), 'V3_NO_OVERWRITE')
  saved = {key: array_write(root / (key + '.npy.gz'), array) for key, array in sorted(arrays.items())}
  row = p.seal({**body, 'arrays': saved})
  write_json(root / 'receipt.json', row)
  return row


def finish(root, body):
  root = io.safe(root)
  io.require(not (root / 'manifest.json').exists(), 'V3_NO_OVERWRITE')
  files = {}
  for path in sorted(root.rglob('*')):
    io.safe(path)
    io.require(not path.name.endswith('.atomic'), 'V3_INCOMPLETE_STORE')
    if path.is_file():
      files[path.relative_to(root).as_posix()] = io.digest(path)
  row = p.seal({**body, 'files': files})
  write_json(root / 'manifest.json', row)
  return row


def verify_manifest(root):
  try:
    root = io.safe(Path(root))
    manifest = io.read_json(root / 'manifest.json')
    io.require(type(manifest['files']) is dict)
    for name in manifest['files']:
      io.member(root, name)
    io.verified.verify_files(root, manifest['files'])
    actual = set()
    for path in root.rglob('*'):
      io.safe(path)
      if path.is_file():
        actual.add(path.relative_to(root).as_posix())
    io.require(actual == set(manifest['files']) | {'manifest.json'})
    return manifest
  except (ValueError, OSError, KeyError, TypeError) as exc:
    raise ValueError('V3_RESUME_INTEGRITY_FAILURE') from exc


def verify_population(root, receipt):
  """Own saved payload only; source_reference fields are inert."""
  arrays = receipt['arrays']
  name = receipt['population']
  expected = {'train': {'predicted_gate': '|b1', 'projected_next_tick': '<i2'},
              'one-step': {'p_move': '<f8', 'predicted_gate': '|b1', 'integrated_delta': '<f8', 'candidate_error': '<f8', 'projected_next_tick': '<i2'}}
  kinds = expected.get(name, {'projected_path': '<i2', 'predicted_gate_path': '|b1', 'candidate_error': '<f8'}
                       if name in {f'rollout-{h}' for h in io.verified.HORIZONS} else None)
  io.require(kinds is not None and set(arrays) == set(kinds), 'V3_RESUME_INTEGRITY_FAILURE')
  count = next(iter(arrays.values()))['shape'][0]
  for key, binding in receipt['arrays'].items():
    shape = [count]
    if key in ('projected_path', 'predicted_gate_path'):
      shape.append(int(name.split('-')[1]) + int(key == 'projected_path'))
    io.require(binding['shape'] == shape and binding['dtype'] == kinds[key] and binding['order'] == 'C', 'V3_RESUME_INTEGRITY_FAILURE')
    path = io.member(root, binding['filename'])
    # Bounded decoded SHA/content/header verification, no inference or metrics.
    for _ in io.verified.array_chunks(path, binding):
      pass
