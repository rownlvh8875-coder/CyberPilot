"""Crash-consistent public diagnostic receipts; no acquisition or promotion."""

from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import stat
import tempfile

from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

SCHEMA = {
  'version': 'PUBLIC_DURABLE_RUN_V1',
  'row_commit': 'fsync_file_atomic_replace_fsync_directory',
  'recovery': 'verify_indexed_and_orphan_rows_before_rebuilding_index',
  'migration': 'NONE',
  'completion': 'all_rows_and_artifacts_verified_marker_last',
}
SCHEMA_SHA256 = digest(canonical(SCHEMA))
MAX_JSON_BYTES = 256 * 1024 * 1024  # Full public metadata; never truncate on this resource cap.
FRAME_STATES = {'COMPLETED', 'REFERENCE_UNAVAILABLE', 'DETECTOR_FAILED'}


def read_json(path):
  try:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
      if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
        raise ValueError('REGULAR_RECEIPT_REQUIRED')
      data = stream.read(MAX_JSON_BYTES + 1)
    if len(data) > MAX_JSON_BYTES:
      raise ValueError('PUBLIC_METADATA_RESOURCE_CAP')
    return json.loads(data)
  except (OSError, json.JSONDecodeError) as exc:
    raise ValueError('DURABLE_RECEIPT_READ_FAILED') from exc


def durable_mkdir(path):
  path = Path(path)
  missing = []
  while not path.exists():
    missing.append(path)
    path = path.parent
  for directory in reversed(missing):
    directory.mkdir(exist_ok=True)
    fd = os.open(directory.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
      os.fsync(fd)
    finally:
      os.close(fd)


def atomic_json(path, value):
  path = Path(path)
  durable_mkdir(path.parent)
  data = canonical(value) + b'\n'
  if len(data) > MAX_JSON_BYTES:
    raise ValueError('PUBLIC_METADATA_RESOURCE_CAP')
  fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
  try:
    with os.fdopen(fd, 'wb') as stream:
      stream.write(data)
      stream.flush()
      os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
      os.fsync(directory)
    finally:
      os.close(directory)
  finally:
    if os.path.exists(temporary):
      os.unlink(temporary)


@contextmanager
def writer_lease(root):
  root = Path(root)
  durable_mkdir(root)
  fd = os.open(root / 'writer.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
  try:
    try:
      fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
      raise ValueError('PUBLIC_RUN_WRITER_ALREADY_ACTIVE') from exc
    yield
  finally:
    os.close(fd)


class DurableRun:
  def __init__(self, root, run, expected):
    unseal(run)
    if type(expected) is not list or not expected or any(type(v) is not str or not v for v in expected) or len(set(expected)) != len(expected):
      raise ValueError('UNIQUE_ORDERED_PUBLIC_INPUTS_REQUIRED')
    self.root, self.run, self.expected = Path(root), run, expected
    durable_mkdir(self.root)
    self.rows_dir = self.root / 'rows'
    durable_mkdir(self.rows_dir)
    if self.root.is_symlink() or self.rows_dir.is_symlink():
      raise ValueError('SYMLINK_STORE_FORBIDDEN')
    self.index_path = self.root / 'index.json'
    self.marker_path = self.root / 'completed.json'
    self.binding = {
      'schema_sha256': SCHEMA_SHA256,
      'run_sha256': run['receipt_sha256'],
      'input_order_sha256': digest(canonical(expected)),
      'expected': len(expected),
    }
    freeze = self.root / 'storage-freeze.json'
    value = seal({**self.binding, 'run': run})
    if freeze.exists():
      if read_json(freeze) != value:
        raise ValueError('EXACT_DURABLE_RUN_IDENTITY_REQUIRED_NO_MIGRATION')
    else:
      if any(self.rows_dir.iterdir()) or self.index_path.exists() or self.marker_path.exists():
        raise ValueError('UNBOUND_EXISTING_CACHE_FORBIDDEN')
      atomic_json(freeze, value)
    self.rows = {}

  def row_path(self, ordinal):
    if type(ordinal) is not int or not 0 <= ordinal < len(self.expected):
      raise ValueError('INVALID_FRAME_ORDINAL')
    return self.rows_dir / f'{ordinal:05d}.json'

  def _validate(self, ordinal, row, validator):
    core = unseal(row)
    if core.get('run_sha256') != self.run['receipt_sha256'] or type(core.get('ordinal')) is not int or core['ordinal'] != ordinal:
      raise ValueError('DURABLE_FRAME_BINDING_MISMATCH')
    if core.get('frame_status') not in FRAME_STATES:
      raise ValueError('EXPLICIT_FRAME_DISPOSITION_REQUIRED')
    validator(row)
    return row

  def index(self):
    value = read_json(self.index_path)
    core = unseal(value)
    if any(core.get(k) != v for k, v in self.binding.items()) or set(core) != set(self.binding) | {'storage_status', 'rows'}:
      raise ValueError('DURABLE_INDEX_BINDING_MISMATCH')
    if core['storage_status'] not in {'RUNNING', 'INTERRUPTED_RESUMABLE', 'PARTIAL_INVALID', 'COMPLETED'} or type(core['rows']) is not list:
      raise ValueError('INVALID_DURABLE_INDEX')
    seen = set()
    for item in core['rows']:
      if type(item) is not dict or set(item) != {'ordinal', 'receipt_sha256', 'frame_status'}:
        raise ValueError('INVALID_DURABLE_INDEX_ROW')
      self.row_path(item['ordinal'])
      if item['ordinal'] in seen or item['frame_status'] not in FRAME_STATES:
        raise ValueError('DUPLICATE_OR_INVALID_DURABLE_ROW')
      seen.add(item['ordinal'])
    return value

  def _write_index(self, status):
    rows = [{'ordinal': i, 'receipt_sha256': row['receipt_sha256'], 'frame_status': row['frame_status']} for i, row in sorted(self.rows.items())]
    atomic_json(self.index_path, seal({**self.binding, 'storage_status': status, 'rows': rows}))

  def recover(self, validator, *, retain=True):
    self.rows = {}
    recovered = {}
    try:
      old = self.index() if self.index_path.exists() else None
      indexed = {item['ordinal']: item for item in old['rows']} if old else {}
      if old and old['storage_status'] == 'PARTIAL_INVALID':
        raise ValueError('INVALID_CACHE_REQUIRES_SEPARATE_INVESTIGATION')
      for path in sorted(self.rows_dir.iterdir()):
        if path.name.startswith('.') and path.name.endswith('.tmp'):
          continue  # A killed pre-rename write is not a receipt.
        if len(path.name) != 10 or not path.name[:5].isdigit() or path.suffix != '.json':
          raise ValueError('UNDECLARED_OR_DUPLICATE_ROW_FILENAME')
        ordinal = int(path.stem)
        if path.name != self.row_path(ordinal).name or ordinal in self.rows:
          raise ValueError('NONCANONICAL_OR_DUPLICATE_ROW_FILENAME')
        row = self._validate(ordinal, read_json(path), validator)
        if ordinal in indexed and any(row.get(key) != value for key, value in indexed[ordinal].items()):
          raise ValueError('DURABLE_INDEX_ROW_SHA_MISMATCH')
        self.rows[ordinal] = {key: row[key] for key in ('ordinal', 'receipt_sha256', 'frame_status')}
        recovered[ordinal] = row if retain else self.rows[ordinal]
      if not set(indexed).issubset(self.rows):
        raise ValueError('MISSING_INDEXED_RECEIPT')
      if not self.marker_path.exists():
        self._write_index('INTERRUPTED_RESUMABLE' if self.rows else 'RUNNING')
      return recovered
    except Exception:
      self._write_index('PARTIAL_INVALID')
      raise

  def missing(self):
    return [i for i in range(len(self.expected)) if i not in self.rows]

  def put(self, ordinal, row, validator, *, sync_index=True):
    self._validate(ordinal, row, validator)
    path = self.row_path(ordinal)
    if self.marker_path.exists():
      raise ValueError('COMPLETED_RUN_IS_IMMUTABLE')
    if path.exists():
      if read_json(path) != row:
        raise ValueError('IMMUTABLE_FRAME_RECEIPT_MISMATCH')
    else:
      atomic_json(path, row)
    self.rows[ordinal] = {key: row[key] for key in ('ordinal', 'receipt_sha256', 'frame_status')}
    if sync_index:
      self.flush_index()

  def flush_index(self):
    self._write_index('RUNNING')

  def interrupted(self, *, invalid=False):
    self._write_index('PARTIAL_INVALID' if invalid else 'INTERRUPTED_RESUMABLE')

  def complete(self, artifacts, validator, *, before_marker=None):
    if self.marker_path.exists():
      raise ValueError('COMPLETED_RUN_IS_IMMUTABLE')
    self.recover(validator, retain=False)
    if self.missing() or any(row['frame_status'] == 'DETECTOR_FAILED' for row in self.rows.values()):
      raise ValueError('ALL_SUCCESSFUL_EXPLICIT_FRAME_RECEIPTS_REQUIRED')
    if type(artifacts) is not dict or not artifacts or any(Path(name).name != name or not name.endswith('.json') for name in artifacts):
      raise ValueError('BOUND_COMPLETION_ARTIFACTS_REQUIRED')
    if set(artifacts) & {'index.json', 'completed.json', 'storage-freeze.json'}:
      raise ValueError('RESERVED_DURABLE_ARTIFACT')
    hashes = {}
    for name, value in artifacts.items():
      atomic_json(self.root / name, value)
      hashes[name] = digest((self.root / name).read_bytes())
    self._write_index('COMPLETED')
    marker = seal(
      {
        **self.binding,
        'storage_status': 'COMPLETED',
        'processed': len(self.rows),
        'index_file_sha256': digest(self.index_path.read_bytes()),
        'artifact_file_sha256': hashes,
        'reference_promotable': False,
      }
    )
    if before_marker is not None:
      before_marker()
    atomic_json(self.marker_path, marker)  # LAST durable publication operation.
    return marker

  def verify_completed(self, validator):
    marker = read_json(self.marker_path)
    core = unseal(marker)
    if (
      set(core) != set(self.binding) | {'storage_status', 'processed', 'index_file_sha256', 'artifact_file_sha256', 'reference_promotable'}
      or any(core.get(k) != v for k, v in self.binding.items())
      or core['storage_status'] != 'COMPLETED'
      or type(core['processed']) is not int
      or core['processed'] != len(self.expected)
      or core['reference_promotable'] is not False
    ):
      raise ValueError('INVALID_COMPLETION_MARKER')
    self.recover(validator, retain=False)
    if self.missing() or any(row['frame_status'] == 'DETECTOR_FAILED' for row in self.rows.values()):
      raise ValueError('INCOMPLETE_COMPLETION_MARKER')
    if self.index()['storage_status'] != 'COMPLETED' or digest(self.index_path.read_bytes()) != core['index_file_sha256']:
      raise ValueError('COMPLETION_INDEX_SHA_MISMATCH')
    if type(core['artifact_file_sha256']) is not dict or not core['artifact_file_sha256']:
      raise ValueError('COMPLETION_ARTIFACTS_MISSING')
    for name, expected in core['artifact_file_sha256'].items():
      if Path(name).name != name or not name.endswith('.json'):
        raise ValueError('INVALID_COMPLETION_ARTIFACT_PATH')
      read_json(self.root / name)
      if digest((self.root / name).read_bytes()) != expected:
        raise ValueError('COMPLETION_ARTIFACT_SHA_MISMATCH')
    return marker
