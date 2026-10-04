"""Fixed synthetic lateral continuity experiment, not a live Shadow scheduler.

ONE preadmitted finite epoch in ONE child. No input/config changes during an epoch,
no serialized controller state, no cross-job persistence or actuator/profile API.
Source bindings are observations, not authenticated runtime configuration history.
"""
import json
from pathlib import Path
import sys

from openpilot.tools.cyber_autotune import a1_experiment as a1
from openpilot.tools.cyber_autotune.native_protocol import (
  MAX_REQUEST_BYTES, _hex, _invalid_constant, _keys, _unique_pairs, canonical, digest, finite,
  decode_request as decode_native, encode_request as encode_native,
)
from openpilot.tools.cyber_autotune.native_runner import MAX_RESPONSE_BYTES, MAX_TIMEOUT_S, _run_process
from openpilot.tools.cyber_autotune.native_worker import _execute_request, _request_steps
from openpilot.tools.cyber_autotune.source_imports import source_only_imports


ROOT = a1.ROOT
OVERLAY_FILES = tuple('openpilot/tools/cyber_autotune/' + name for name in
                      ('lateral_continuity.py', 'lateral_continuity_worker.py'))
SCOPE = 'OFFLINE_PREADMITTED_LATERAL_EPOCH_ONLY'
PASS = 'SOFTWARE_LATERAL_CONTINUITY_PASS'


def build_request(chunk_sizes):
  request = {'version': 1, 'fixture_request': a1.build_request('disabled'), 'chunk_sizes': chunk_sizes,
             'overlay': {name: digest((ROOT / name).read_bytes()) for name in OVERLAY_FILES}}
  return decode_request(encode_request(request))


def encode_request(request):
  _keys(request, ('version', 'fixture_request', 'chunk_sizes', 'overlay'))
  if type(request['version']) is not int or request['version'] != 1:
    raise ValueError('INVALID_CONTINUITY_VERSION')
  a1.encode_request(request['fixture_request'])
  if request['fixture_request']['fixture'] != 'disabled':
    raise ValueError('CONTINUITY_REQUIRES_FIXED_SYNTHETIC_FIXTURE')
  sizes = request['chunk_sizes']
  # Counts, not a physical tolerance: reuse the complete existing601-frame epoch.
  if (type(sizes) is not list or not 1 <= len(sizes) <= a1.FRAME_COUNT or
      any(type(size) is not int or not 0 < size <= a1.FRAME_COUNT for size in sizes) or sum(sizes) != a1.FRAME_COUNT):
    raise ValueError('INVALID_COMPLETE_PARTITION')
  _keys(request['overlay'], OVERLAY_FILES)
  if not all(_hex(value, 64) for value in request['overlay'].values()):
    raise ValueError('INVALID_CONTINUITY_OVERLAY')
  payload = canonical(request)
  if len(payload) > MAX_REQUEST_BYTES:
    raise ValueError('CONTINUITY_REQUEST_TOO_LARGE')
  return payload


def decode_request(payload):
  if type(payload) is not bytes or not 0 < len(payload) <= MAX_REQUEST_BYTES:
    raise ValueError('INVALID_CONTINUITY_REQUEST_SIZE')
  try:
    request = json.loads(payload, object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
    encode_request(request)
    return request
  except (UnicodeError, RecursionError) as exc:
    raise ValueError('INVALID_CONTINUITY_JSON') from exc


def _verify_bindings(request):
  a1._verify_bindings(request['fixture_request'])
  for name, expected in request['overlay'].items():
    path = (ROOT / name).resolve(strict=True)
    if not path.is_relative_to(ROOT) or digest(path.read_bytes()) != expected:
      raise ValueError('CONTINUITY_OVERLAY_CHANGED')


def _checkpoint(native, start, end, state_sha256):
  return {'start_index': start, 'end_index_exclusive': end,
          'first_time_ns': native['frames'][start]['time_ns'], 'last_time_ns': native['frames'][end - 1]['time_ns'],
          'end_state_sha256': state_sha256}


class _TorqueChunkCursor:
  """Child-only native state owner; no new input or resume token is accepted.

  Caller must use a context manager. This is not thread-safe or an active-loop API.
  An invalid advance, incomplete finish, exception or close permanently ends it.
  Native reset/override semantics are unchanged; only chunk boundaries do not reset.
  """
  def __init__(self, native):
    self._native = decode_native(encode_native(native))
    self._steps = _request_steps(self._native, _capture_state=True)
    self._index = 0
    self._closed = False

  def advance(self, count):
    if self._closed:
      raise ValueError('CONTINUITY_CLOSED')
    try:
      if type(count) is not int or not 0 < count <= len(self._native['frames']) - self._index:
        raise ValueError('INVALID_CONTINUITY_ADVANCE')
      start = self._index
      for _ in range(count):
        state_sha256 = next(self._steps)
        self._index += 1
      return _checkpoint(self._native, start, self._index, state_sha256)
    except StopIteration as exc:
      self.close()
      raise ValueError('PREMATURE_CONTINUITY_END') from exc
    except BaseException:
      self.close()
      raise

  def finish(self):
    if self._closed:
      raise ValueError('CONTINUITY_CLOSED')
    try:
      if self._index != len(self._native['frames']):
        raise ValueError('INCOMPLETE_CONTINUITY_EPOCH')
      try:
        next(self._steps)
      except StopIteration as done:
        return done.value
      raise ValueError('EXCESS_CONTINUITY_FRAME')
    finally:
      self.close()

  def close(self):
    self._closed = True
    self._steps.close()

  def __enter__(self):
    return self

  def __exit__(self, *_):
    self.close()


def execute_experiment(request):
  """Internal synchronous worker entry; public callers use run_experiment."""
  request = decode_request(encode_request(request))
  _verify_bindings(request)
  fixture = request['fixture_request']
  with source_only_imports():
    native, table = a1.make_fixture(fixture)
    baseline = _execute_request(native, _capture_state=True)
    with _TorqueChunkCursor(native) as cursor:
      chunks = [cursor.advance(count) for count in request['chunk_sizes']]
      candidate = cursor.finish()
    comparison = {'status': a1.PASS, 'fixture': 'disabled', 'request_sha256': digest(a1.encode_request(fixture)),
                  'manifest': a1._manifest(fixture, native, table), 'baseline': baseline, 'candidate': candidate,
                  'unavailable_metrics': a1.UNAVAILABLE.copy(), **dict.fromkeys(a1.AUTHORITIES, False)}
    result = {'status': PASS, 'scope': SCOPE, 'request_sha256': digest(encode_request(request)),
              'comparison': comparison, 'chunks': chunks, 'chunks_sha256': digest(canonical(chunks)),
              **dict.fromkeys(a1.AUTHORITIES, False)}
    validate_response(request, result)
  _verify_bindings(request)
  if len(canonical(result)) > MAX_RESPONSE_BYTES:
    raise ValueError('CONTINUITY_RESPONSE_TOO_LARGE')
  return result


def validate_response(request, result):
  encode_request(request)
  _keys(result, ('status', 'scope', 'request_sha256', 'comparison', 'chunks', 'chunks_sha256', *a1.AUTHORITIES))
  if (result['status'] != PASS or result['scope'] != SCOPE or result['request_sha256'] != digest(encode_request(request)) or
      any(result[name] is not False for name in a1.AUTHORITIES)):
    raise ValueError('INVALID_CONTINUITY_RESULT_BINDING')
  # Reuse existing exact one-shot trace/state/invariant validation, not a new gate.
  a1.validate_response(request['fixture_request'], result['comparison'])
  native, _ = a1.make_fixture(request['fixture_request'])
  states = result['comparison']['candidate']['a1']['states']
  expected, start = [], 0
  for count in request['chunk_sizes']:
    end = start + count
    expected.append(_checkpoint(native, start, end, states[end - 1]['state_sha256']))
    start = end
  if canonical(result['chunks']) != canonical(expected) or result['chunks_sha256'] != digest(canonical(expected)):
    raise ValueError('CONTINUITY_CHECKPOINT_MISMATCH')


def run_experiment(request, *, timeout_s):
  """Blocking PC supervisor; not a real-time or hostile-source sandbox."""
  if not finite(timeout_s) or not 0 < timeout_s <= MAX_TIMEOUT_S:
    raise ValueError('INVALID_TIMEOUT')
  payload = encode_request(request)
  request = decode_request(payload)

  def failure(status, worker_returncode=None):
    return {'status': status, 'worker_returncode': worker_returncode, 'request_sha256': digest(payload),
            **dict.fromkeys(a1.AUTHORITIES, False)}

  if sys.platform != 'linux':
    return failure('UNSUPPORTED_PLATFORM')
  try:
    _verify_bindings(request)
  except (ValueError, OSError):
    return failure('BINDING_REJECTED')
  try:
    observed = _run_process([sys.executable, '-I', str(Path(__file__).with_name('lateral_continuity_worker.py'))], payload, timeout_s)
  except OSError:
    return failure('WORKER_UNAVAILABLE')
  if observed.status == 'TIMEOUT':
    return failure('TIMEOUT', observed.returncode)
  if observed.status != 'EXITED' or observed.returncode != 0:
    return failure('WORKER_FAILED', observed.returncode)
  if not 0 < len(observed.stdout) <= MAX_RESPONSE_BYTES:
    return failure('INVALID_RESPONSE', observed.returncode)
  try:
    result = json.loads(observed.stdout, object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
    validate_response(request, result)
    _verify_bindings(request)
  except (ValueError, OSError, UnicodeError, RecursionError):
    return failure('INVALID_RESPONSE', observed.returncode)
  return result
