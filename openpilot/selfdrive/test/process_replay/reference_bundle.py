"""Pinned replay reference metadata and bytes; stdlib only, no process imports."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess


SOURCE_PATHS = ('openpilot', 'SConstruct', 'pyproject.toml', 'uv.lock', '.gitmodules', 'msgq_repo',
                'opendbc_repo', 'panda', 'rednose_repo', 'teleoprtc_repo', 'tinygrad_repo', 'system', 'scripts', 'tools')
EXCLUDED = ('openpilot/selfdrive/test/process_replay/', 'tools/cyberlateral_dev/', 'tools/cyberlateral_cloud/')
LOCK_KEYS = {'schema_version', 'producer_commit', 'artifact_commit', 'source_scope', 'source_fingerprint_sha256',
             'opendbc_commit', 'opendbc_schema_git_blob', 'artifacts'}


class ReferenceBundleError(ValueError):
  pass


def _unique_pairs(pairs):
  result = {}
  for key, value in pairs:
    if key in result:
      raise ReferenceBundleError('INVALID_REFERENCE_LOCK:duplicate_key')
    result[key] = value
  return result


def _hex(value, size):
  return isinstance(value, str) and re.fullmatch('[0-9a-f]{' + str(size) + '}', value) is not None


def _git(root: Path, *args: str) -> bytes:
  try:
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True, check=True, timeout=30).stdout
  except (OSError, subprocess.SubprocessError) as error:
    raise ReferenceBundleError('CHECKOUT_METADATA_UNAVAILABLE') from error


def _blob(raw: bytes) -> str:
  return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


@dataclass(frozen=True)
class ReferenceBundle:
  record: dict

  @classmethod
  def load(cls, path: Path) -> 'ReferenceBundle':
    try:
      record = json.loads(path.read_text(), object_pairs_hook=_unique_pairs)
    except OSError as error:
      raise ReferenceBundleError('REFERENCE_LOCK_UNAVAILABLE') from error
    except (ValueError, UnicodeError) as error:
      raise ReferenceBundleError('INVALID_REFERENCE_LOCK') from error
    valid = (isinstance(record, dict) and set(record) == LOCK_KEYS and type(record['schema_version']) is int
             and record['schema_version'] == 1 and record['source_scope'] == 'replay-producer-v1'
             and _hex(record['source_fingerprint_sha256'], 64)
             and all(_hex(record[k], 40) for k in ('producer_commit', 'artifact_commit', 'opendbc_commit', 'opendbc_schema_git_blob'))
             and isinstance(record['artifacts'], dict) and bool(record['artifacts']))
    if not valid:
      raise ReferenceBundleError('INVALID_REFERENCE_LOCK:metadata')
    for name, entry in record['artifacts'].items():
      valid = (re.fullmatch(r'[A-Za-z0-9_-]+_' + record['producer_commit'] + r'\.zst', name) is not None
               and isinstance(entry, dict) and set(entry) == {'byte_size', 'sha256', 'git_blob_sha1'}
               and type(entry['byte_size']) is int and 0 < entry['byte_size'] <= 5_000_000
               and _hex(entry['sha256'], 64) and _hex(entry['git_blob_sha1'], 40))
      if not valid:
        raise ReferenceBundleError('INVALID_REFERENCE_LOCK:artifact')
    return cls(record)

  @property
  def producer_commit(self) -> str:
    return self.record['producer_commit']

  def reference_name(self, segment: str, process: str) -> str:
    name = f'{segment}_{process}_{self.producer_commit}.zst'.replace('|', '_')
    if name not in self.record['artifacts']:
      raise ReferenceBundleError('REFERENCE_NOT_LISTED:' + name)
    return name

  def reference_url(self, name: str) -> str:
    if name not in self.record['artifacts']:
      raise ReferenceBundleError('REFERENCE_NOT_LISTED:' + name)
    return f'https://raw.githubusercontent.com/commaai/ci-artifacts/{self.record["artifact_commit"]}/{name}'

  def verify_bytes(self, name: str, raw: bytes) -> bytes:
    if name not in self.record['artifacts']:
      raise ReferenceBundleError('REFERENCE_NOT_LISTED:' + name)
    entry = self.record['artifacts'][name]
    if (len(raw) != entry['byte_size'] or hashlib.sha256(raw).hexdigest() != entry['sha256'] or _blob(raw) != entry['git_blob_sha1']):
      raise ReferenceBundleError('REFERENCE_BYTES_MISMATCH:' + name)
    return raw

  def validate_legacy_pin(self, path: Path) -> None:
    try:
      legacy = path.read_text().strip()
    except FileNotFoundError:
      return
    except (OSError, UnicodeError) as error:
      raise ReferenceBundleError('LEGACY_REFERENCE_OVERRIDE_UNREADABLE') from error
    if legacy != self.producer_commit:
      raise ReferenceBundleError('LEGACY_REFERENCE_OVERRIDE_MISMATCH')

  def validate_checkout(self, root: Path) -> None:
    entries = _git(root, 'ls-tree', '-r', '-z', 'HEAD', '--', *SOURCE_PATHS).split(b'\0')
    projection = b''.join(e + b'\0' for e in entries if e and not e.split(b'\t', 1)[1].decode().startswith(EXCLUDED))
    if hashlib.sha256(projection).hexdigest() != self.record['source_fingerprint_sha256']:
      raise ReferenceBundleError('PRODUCER_SOURCE_MISMATCH')
    excluded = tuple(':(exclude)' + name.rstrip('/') for name in EXCLUDED)
    changed = _git(root, 'diff', '--name-only', 'HEAD', '--', *SOURCE_PATHS, *excluded)
    if changed:
      raise ReferenceBundleError('PRODUCER_SOURCE_DIRTY')
    dbc = root / 'opendbc_repo'
    if not (dbc / '.git').exists():
      raise ReferenceBundleError('OPENDBC_CHECKOUT_UNAVAILABLE')
    if _git(dbc, 'rev-parse', 'HEAD').decode().strip() != self.record['opendbc_commit']:
      raise ReferenceBundleError('OPENDBC_COMMIT_MISMATCH')
    try:
      schema = (dbc / 'opendbc/car/car.capnp').read_bytes()
    except OSError as error:
      raise ReferenceBundleError('OPENDBC_SCHEMA_UNAVAILABLE') from error
    if _blob(schema) != self.record['opendbc_schema_git_blob']:
      raise ReferenceBundleError('OPENDBC_SCHEMA_MISMATCH')

  def prepare_references(self, pairs: Iterable[tuple[str, str]], cache: Path, fetch: Callable[[str], bytes]) -> dict[str, bytes]:
    names = sorted({self.reference_name(segment, process) for segment, process in pairs})
    verified = {}
    for name in names:
      path = cache / name
      try:
        raw = path.read_bytes() if path.exists() or path.is_symlink() else fetch(self.reference_url(name))
      except Exception as error:
        raise ReferenceBundleError('REFERENCE_FETCH_FAILED:' + name) from error
      verified[name] = self.verify_bytes(name, raw)
    return verified
