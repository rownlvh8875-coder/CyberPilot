"""Immutable array persistence with explicit external, nonoverlapping stores."""
import io
import hashlib
import os
from pathlib import Path
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


def safe(value):
  path = Path(value)
  if not path.is_absolute() or '..' in path.parts or any(x.is_symlink() for x in (path, *path.parents)):
    raise ValueError('ABSOLUTE_NO_ALIAS_NO_TRAVERSAL_REQUIRED')
  return path


def external(value, excluded):
  path = safe(value)
  repo = Path(__file__).resolve().parents[3]
  for other in [repo, *map(Path, excluded)]:
    safe(other)
    if path == other or path in other.parents or other in path.parents:
      raise ValueError('PRIVATE_STORE_OVERLAP')
  return path


def atomic_bytes(path, data):
  path = safe(path)
  path.parent.mkdir(parents=True, exist_ok=True)
  if path.exists():
    if path.read_bytes() != data:
      raise ValueError('IMMUTABLE_ARRAY_CONFLICT')
    return
  temp = path.with_name(path.name + '.atomic')
  safe(temp)
  if temp.exists():
    if temp.read_bytes() != data:
      raise ValueError('INTERRUPTED_ARRAY_CONFLICT')
  else:
    with temp.open('xb') as f:
      f.write(data)
      f.flush()
      os.fsync(f.fileno())
  os.link(temp, path)
  temp.unlink()


def array_write(path, array):
  if array.dtype.hasobject:
    raise ValueError('NO_OBJECT_ARRAYS')
  buffer = io.BytesIO()
  np.save(buffer, np.ascontiguousarray(array), allow_pickle=False)
  data = buffer.getvalue()
  atomic_bytes(path, data)
  return {'dtype': array.dtype.str, 'shape': list(array.shape), 'order': 'C',
          'array_sha256': p.sha(array.tobytes(order='C')), 'file_sha256': p.sha(data)}


def tree_identity(path):
  path = safe(path)
  files = []
  for item in sorted(path.rglob('*')):
    safe(item)
    if item.is_file():
      digest = hashlib.sha256()
      with item.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
          digest.update(block)
      files.append((item.relative_to(path).as_posix(), digest.hexdigest()))
  return p.sha(p.canonical(files))
