"""Finite logical joint epochs in one isolated PC child; no live/actuator API.

Same preadmitted frames for both axes, independent native controllers, no physical
coupling. Source/config hashes are content bindings, not runtime qualification.
A failed/aborted epoch cannot resume; no joint IPC or scheduler is enabled here.
"""
import copy
from pathlib import Path
import sys
import threading

from openpilot.tools.cyber_autotune import a1_experiment as a1, lateral_continuity, paired_shadow
from openpilot.tools.cyber_autotune import native_protocol as lat, native_long_protocol as lng
from openpilot.tools.cyber_autotune import native_worker, native_long_worker
from openpilot.tools.cyber_autotune.native_long_runner import validate_response as validate_long
from openpilot.tools.cyber_autotune.native_runner import MAX_RESPONSE_BYTES, MAX_TIMEOUT_S, _run_process, validate_response as validate_lat
from openpilot.tools.cyber_autotune.source_imports import source_only_imports


ROOT = a1.ROOT
AUTHORITIES = a1.AUTHORITIES
PASS = 'SOFTWARE_JOINT_EPOCH_PARITY_ONLY'
SCOPE = 'OFFLINE_PREADMITTED_JOINT_EPOCH_ONLY'
OVERLAY_FILES = tuple('openpilot/tools/cyber_autotune/' + name for name in (
  'joint_continuity.py', 'joint_continuity_worker.py', 'lateral_continuity.py', 'paired_shadow.py',
  'native_long_worker.py', 'native_long_protocol.py', 'native_long_runner.py', 'native_worker.py',
  'native_protocol.py', 'native_runner.py', 'a1_experiment.py', 'source_imports.py', 'worker_resources.py',
))


def build_request(pair, chunk_sizes):
  request = {'version': 1, 'pair': paired_shadow.decode_request(pair), 'chunk_sizes': chunk_sizes,
             'overlay': {name: lat.digest((ROOT / name).read_bytes()) for name in OVERLAY_FILES}}
  return decode_request(encode_request(request))


def encode_request(request):
  lat._keys(request, ('version', 'pair', 'chunk_sizes', 'overlay'))
  if type(request['version']) is not int or request['version'] != 1:
    raise ValueError('INVALID_JOINT_VERSION')
  paired_shadow.encode_request(request['pair'])
  for axis in paired_shadow.AXES:
    if request['pair'][axis]['source']['root'] != str(ROOT):
      raise ValueError('JOINT_REQUIRES_OWNED_CHECKOUT')
  total = len(request['pair']['frames']['lateral'])
  sizes = request['chunk_sizes']
  if (type(sizes) is not list or not 1 <= len(sizes) <= total or
      any(type(count) is not int or not 0 < count <= total for count in sizes) or sum(sizes) != total):
    raise ValueError('INVALID_COMPLETE_JOINT_PARTITION')
  lat._keys(request['overlay'], OVERLAY_FILES)
  if not all(lat._hex(value, 64) for value in request['overlay'].values()):
    raise ValueError('INVALID_JOINT_OVERLAY')
  payload = lat.canonical(request)
  if len(payload) > lat.MAX_REQUEST_BYTES:
    raise ValueError('JOINT_REQUEST_TOO_LARGE')
  return payload


def decode_request(payload):
  request = paired_shadow._read_json(payload, lat.MAX_REQUEST_BYTES)
  encode_request(request)
  return request


def _verify_bindings(request):
  encode_request(request)
  for name, expected in request['overlay'].items():
    path = (ROOT / name).resolve(strict=True)
    if not path.is_relative_to(ROOT) or lat.digest(path.read_bytes()) != expected:
      raise ValueError('JOINT_SOURCE_CHANGED')
  for native in paired_shadow._split(request['pair']):
    native_worker._verify_source(native['source'])


class _LongChunkCursor(lateral_continuity._TorqueChunkCursor):
  """Private child-only native LongControl cursor; inherits terminal lifecycle."""
  def __init__(self, request):
    self._native = lng.decode_request(lng.encode_request(request))
    self._steps = native_long_worker._request_steps(self._native, _capture_state=True)
    self._index = 0
    self._closed = False


class _JointEpoch:
  """One owner thread, one complete immutable epoch, no partial success/resume.

  Generators enter the same source root in lateral/longitudinal order. Close and
  finalize in reverse order; source_only_imports belongs to the enclosing worker.
  Logical joint progress is not simultaneous CPU execution or a coupled plant.
  """
  def __init__(self, request):
    self._request = decode_request(encode_request(request))
    _verify_bindings(self._request)
    self._owner = threading.get_ident()
    self._cursors = (lateral_continuity._TorqueChunkCursor(paired_shadow._split(self._request['pair'])[0]),
                     _LongChunkCursor(paired_shadow._split(self._request['pair'])[1]))
    self._chunk_index = 0
    self._checkpoints = []
    self.closed = False
    self.cleanup_confirmed = True

  def _owner_check(self):
    if threading.get_ident() != self._owner:
      raise ValueError('WRONG_JOINT_OWNER')

  def _require_open(self):
    self._owner_check()
    if self.closed:
      raise ValueError('JOINT_EPOCH_CLOSED')

  def _terminate(self):
    if self.closed:
      return
    self.closed = True
    for cursor in reversed(self._cursors):
      try:
        cursor.close()
      except BaseException:
        self.cleanup_confirmed = False

  def _failed(self, exception):
    self._terminate()
    if not self.cleanup_confirmed:
      BaseException.add_note(exception, 'JOINT_CLEANUP_UNCONFIRMED')

  def advance(self, count):
    self._require_open()
    try:
      _verify_bindings(self._request)
      sizes = self._request['chunk_sizes']
      if type(count) is not int or self._chunk_index >= len(sizes) or count != sizes[self._chunk_index]:
        raise ValueError('JOINT_PARTITION_ORDER_MISMATCH')
      states = {axis: cursor.advance(count) for axis, cursor in zip(paired_shadow.AXES, self._cursors, strict=True)}
      _verify_bindings(self._request)
      checkpoint = {'chunk_index': self._chunk_index, 'axes': states}
      self._checkpoints.append(copy.deepcopy(checkpoint))
      self._chunk_index += 1
      return checkpoint
    except BaseException as exc:
      self._failed(exc)
      raise

  def finish(self):
    self._require_open()
    try:
      if self._chunk_index != len(self._request['chunk_sizes']):
        raise ValueError('INCOMPLETE_JOINT_EPOCH')
      _verify_bindings(self._request)
      results = {}
      for axis, cursor in reversed(tuple(zip(paired_shadow.AXES, self._cursors, strict=True))):
        results[axis] = cursor.finish()
      _verify_bindings(self._request)
      self._terminate()
      if not self.cleanup_confirmed:
        raise ValueError('JOINT_CLEANUP_UNCONFIRMED')
      return results
    except BaseException as exc:
      self._failed(exc)
      raise

  def close(self):
    self._owner_check()
    self._terminate()
    if not self.cleanup_confirmed:
      raise ValueError('JOINT_CLEANUP_UNCONFIRMED')

  def __enter__(self):
    self._require_open()
    return self

  def __exit__(self, exc_type, exc, _traceback):
    self._owner_check()
    if self.closed:
      return
    if exc_type is not None:
      self._failed(exc)
    else:
      self.close()


def _validate_long(request, result):
  lat._keys(result, ('status', 'scope', 'request_sha256', 'source_head', 'opendbc_head', 'car_params_sha256',
                     'samples', 'ordered_trace_sha256', 'runtime_accepted', 'promotable', 'continuity'))
  validate_long(request, {key: value for key, value in result.items() if key != 'continuity'})
  extension = result['continuity']
  lat._keys(extension, ('state_schema', 'states', 'states_sha256'))
  states = extension['states']
  if (extension['state_schema'] != 'native-long-state-v1' or type(states) is not list or
      len(states) != len(request['frames']) or extension['states_sha256'] != lat.digest(lat.canonical(states))):
    raise ValueError('INVALID_LONG_CONTINUITY_STATE')
  for state, sample in zip(states, result['samples'], strict=True):
    lat._keys(state, ('time_ns', 'state_sha256', 'snapshot'))
    snapshot = state['snapshot']
    lat._keys(snapshot, ('mode', 'last_output_accel', 'pid'))
    lat._keys(snapshot['pid'], native_long_worker.PID_STATE_FIELDS)
    if (type(state['time_ns']) is not int or state['time_ns'] != sample['time_ns'] or
        snapshot['mode'] != sample['state_after'] or not lat.finite(snapshot['last_output_accel']) or
        snapshot['last_output_accel'] != sample['requested_accel_mps2'] or
        not all(lat.finite(value) for value in snapshot['pid'].values()) or
        (snapshot['pid']['neg_limit'], snapshot['pid']['pos_limit']) != lng.EXPECTED_ACCEL_LIMITS or
        state['state_sha256'] != lat.digest(lat.canonical(snapshot))):
      raise ValueError('LONG_CONTINUITY_STATE_MISMATCH')


def _validate_lateral(request, result):
  lat._keys(result, ('status', 'scope', 'request_sha256', 'source_head', 'opendbc_head', 'car_params_sha256',
                     'samples', 'ordered_trace_sha256', 'runtime_accepted', 'promotable', 'a1'))
  validate_lat(request, {key: value for key, value in result.items() if key != 'a1'})
  state = result['a1']
  lat._keys(state, ('state_schema', 'reset', 'invariants_sha256', 'schedule', 'schedule_sha256', 'states', 'states_sha256'))
  if (state['state_schema'] != 'native-torque-state-v1' or state['reset'] != 'fresh-controller-once' or
      not lat._hex(state['invariants_sha256'], 64) or type(state['states']) is not list or type(state['schedule']) is not list or
      len(state['states']) != len(request['frames']) or len(state['schedule']) != len(request['frames']) or
      state['schedule_sha256'] != lat.digest(lat.canonical(state['schedule'])) or
      state['states_sha256'] != lat.digest(lat.canonical(state['states']))):
    raise ValueError('INVALID_LATERAL_CONTINUITY_STATE')
  for item, scheduled in zip(state['states'], state['schedule'], strict=True):
    lat._keys(item, ('state_sha256', 'factor', 'friction', 'pid_i', 'history_sha256'))
    if (not lat._hex(item['state_sha256'], 64) or not lat._hex(item['history_sha256'], 64) or
        not all(lat.finite(item[key]) for key in ('factor', 'friction', 'pid_i')) or
        type(scheduled) is not list or len(scheduled) != 5 or not all(lat.finite(value) for value in scheduled) or
        item['factor'] != scheduled[3] or item['friction'] != scheduled[4]):
      raise ValueError('INVALID_LATERAL_STATE_ROW')


def validate_response(request, result):
  encode_request(request)
  lat._keys(result, ('status', 'scope', 'request_sha256', 'input_alignment', 'axes', 'checkpoints', 'checkpoints_sha256', *AUTHORITIES))
  if (result['status'] != PASS or result['scope'] != SCOPE or result['input_alignment'] != paired_shadow.ALIGNMENT or
      result['request_sha256'] != lat.digest(encode_request(request)) or any(result[name] is not False for name in AUTHORITIES)):
    raise ValueError('INVALID_JOINT_RESPONSE_BINDING')
  lat._keys(result['axes'], paired_shadow.AXES)
  for axis, native, validator in zip(paired_shadow.AXES, paired_shadow._split(request['pair']), (_validate_lateral, _validate_long), strict=True):
    arms = result['axes'][axis]
    lat._keys(arms, ('baseline', 'candidate'))
    for arm in arms.values():
      validator(native, arm)
    if lat.canonical(arms['baseline']) != lat.canonical(arms['candidate']):
      raise ValueError('JOINT_NATIVE_PARITY_MISMATCH')
  expected, start = [], 0
  for index, count in enumerate(request['chunk_sizes']):
    end = start + count
    axes = {}
    for axis, native in zip(paired_shadow.AXES, paired_shadow._split(request['pair']), strict=True):
      extension = 'a1' if axis == 'lateral' else 'continuity'
      sha = result['axes'][axis]['candidate'][extension]['states'][end - 1]['state_sha256']
      axes[axis] = lateral_continuity._checkpoint(native, start, end, sha)
    expected.append({'chunk_index': index, 'axes': axes})
    start = end
  if lat.canonical(result['checkpoints']) != lat.canonical(expected) or result['checkpoints_sha256'] != lat.digest(lat.canonical(expected)):
    raise ValueError('JOINT_CHECKPOINT_MISMATCH')


def execute_experiment(request):
  request = decode_request(encode_request(request))
  _verify_bindings(request)
  with source_only_imports():
    lateral, longitudinal = paired_shadow._split(request['pair'])
    baselines = {'lateral': native_worker._execute_request(lateral, _capture_state=True),
                 'longitudinal': native_long_worker._execute_request(longitudinal, _capture_state=True)}
    with _JointEpoch(request) as epoch:
      checkpoints = [epoch.advance(count) for count in request['chunk_sizes']]
      candidates = epoch.finish()
    result = {'status': PASS, 'scope': SCOPE, 'request_sha256': lat.digest(encode_request(request)),
              'input_alignment': paired_shadow.ALIGNMENT,
              'axes': {axis: {'baseline': baselines[axis], 'candidate': candidates[axis]} for axis in paired_shadow.AXES},
              'checkpoints': checkpoints, 'checkpoints_sha256': lat.digest(lat.canonical(checkpoints)),
              **dict.fromkeys(AUTHORITIES, False)}
    validate_response(request, result)
  _verify_bindings(request)
  if len(lat.canonical(result)) > MAX_RESPONSE_BYTES:
    raise ValueError('JOINT_RESPONSE_TOO_LARGE')
  return result


def run_experiment(request, *, timeout_s):
  if not lat.finite(timeout_s) or not 0 < timeout_s <= MAX_TIMEOUT_S:
    raise ValueError('INVALID_TIMEOUT')
  payload = encode_request(request)
  request = decode_request(payload)

  def failure(status, returncode=None):
    return {'status': status, 'worker_returncode': returncode, 'request_sha256': lat.digest(payload), **dict.fromkeys(AUTHORITIES, False)}

  if sys.platform != 'linux':
    return failure('UNSUPPORTED_PLATFORM')
  try:
    _verify_bindings(request)
  except (ValueError, OSError):
    return failure('BINDING_REJECTED')
  try:
    outcome = _run_process([sys.executable, '-I', str(Path(__file__).with_name('joint_continuity_worker.py'))], payload, timeout_s)
  except OSError:
    return failure('WORKER_UNAVAILABLE')
  if outcome.status == 'TIMEOUT':
    return failure('TIMEOUT', outcome.returncode)
  if outcome.status != 'EXITED' or outcome.returncode != 0:
    return failure('WORKER_FAILED', outcome.returncode)
  try:
    result = paired_shadow._read_json(outcome.stdout, MAX_RESPONSE_BYTES)
    validate_response(request, result)
    _verify_bindings(request)
  except (ValueError, OSError, KeyError, TypeError):
    return failure('INVALID_RESPONSE', outcome.returncode)
  return result
