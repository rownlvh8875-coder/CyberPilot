"""Fixed built-in IPC for immutable joint epochs; no live-data qualification."""
import copy

from openpilot.tools.cyber_autotune import joint_continuity as joint, lateral_session_protocol as legacy
from openpilot.tools.cyber_autotune import native_protocol as native, paired_shadow
from openpilot.tools.cyber_autotune.source_imports import source_only_imports


MAX_REQUEST_BYTES = native.MAX_REQUEST_BYTES
canonical, digest, decode_json = native.canonical, native.digest, legacy.decode_json
make_message, STATUSES = legacy.make_message, legacy.STATUSES
OVERLAY_FILES = tuple('openpilot/tools/cyber_autotune/' + name for name in (
  'joint_session.py', 'joint_session_protocol.py', 'joint_session_worker.py', 'joint_shadow.py',
  'lateral_session.py', 'lateral_session_protocol.py', 'lateral_session_worker.py', 'shadow.py',
))


def build_epoch(pair, chunk_sizes):
  return {'joint': joint.build_request(pair, chunk_sizes),
          'overlay': {name: digest((joint.ROOT / name).read_bytes()) for name in OVERLAY_FILES}}


def frame_count(epoch):
  return len(epoch['joint']['pair']['frames']['lateral'])


def encode_epoch(epoch):
  native._keys(epoch, ('joint', 'overlay'))
  joint.encode_request(epoch['joint'])
  native._keys(epoch['overlay'], OVERLAY_FILES)
  if not all(native._hex(value, 64) for value in epoch['overlay'].values()):
    raise ValueError('INVALID_JOINT_SESSION_OVERLAY')
  payload = canonical(epoch)
  if len(payload) > MAX_REQUEST_BYTES:
    raise ValueError('JOINT_EPOCH_TOO_LARGE')
  return payload


def verify_epoch(epoch):
  encode_epoch(epoch)
  for name, expected in epoch['overlay'].items():
    path = (joint.ROOT / name).resolve(strict=True)
    if not path.is_relative_to(joint.ROOT) or digest(path.read_bytes()) != expected:
      raise ValueError('JOINT_SESSION_SOURCE_CHANGED')
  joint._verify_bindings(epoch['joint'])


def encode_message(message):
  native._keys(message, ('version', 'session_id', 'sequence', 'epoch_id', 'operation', 'body'))
  if (type(message['version']) is not int or message['version'] != 1 or not native._hex(message['session_id'], 32) or
      any(type(message[key]) is not int or not 0 <= message[key] < 2**63 for key in ('sequence', 'epoch_id'))):
    raise ValueError('INVALID_JOINT_MESSAGE_HEADER')
  op, body = message['operation'], message['body']
  if type(op) is not str or op not in STATUSES:
    raise ValueError('INVALID_JOINT_OPERATION')
  if op == 'OPEN':
    encode_epoch(body)
  elif op == 'CLOSE':
    native._keys(body, ())
    if message['epoch_id'] != 0:
      raise ValueError('INVALID_CLOSE_EPOCH')
  else:
    native._keys(body, ('epoch_sha256', 'start_index', 'count') if op == 'ADVANCE' else ('epoch_sha256',))
    if not native._hex(body['epoch_sha256'], 64):
      raise ValueError('INVALID_EPOCH_BINDING')
    if op == 'ADVANCE' and (type(body['start_index']) is not int or type(body['count']) is not int or
                            not 0 <= body['start_index'] < native.MAX_FRAMES or
                            not 0 < body['count'] <= native.MAX_FRAMES - body['start_index']):
      raise ValueError('INVALID_JOINT_ADVANCE')
  if op != 'CLOSE' and message['epoch_id'] < 1:
    raise ValueError('INVALID_EPOCH_NUMBER')
  payload = canonical(message)
  if len(payload) > MAX_REQUEST_BYTES:
    raise ValueError('JOINT_MESSAGE_TOO_LARGE')
  return payload


def decode_message(payload):
  if type(payload) is not bytes or not 0 < len(payload) <= MAX_REQUEST_BYTES:
    raise ValueError('INVALID_JOINT_MESSAGE_BYTES')
  result = decode_json(payload)
  encode_message(result)
  return result


def validate_reply(request, reply):
  native._keys(reply, ('version', 'session_id', 'sequence', 'epoch_id', 'operation', 'request_sha256', 'status', 'data', *joint.AUTHORITIES))
  for key in ('version', 'session_id', 'sequence', 'epoch_id', 'operation'):
    if type(reply[key]) is not type(request[key]) or reply[key] != request[key]:
      raise ValueError('JOINT_REPLY_REBOUND')
  op, data = request['operation'], reply['data']
  if (reply['request_sha256'] != digest(encode_message(request)) or reply['status'] != STATUSES[op] or
      any(reply[key] is not False for key in joint.AUTHORITIES)):
    raise ValueError('INVALID_JOINT_REPLY')
  if op == 'OPEN':
    expected = {'epoch_sha256': digest(encode_epoch(request['body'])), 'frame_count': frame_count(request['body'])}
    if canonical(data) != canonical(expected):
      raise ValueError('INVALID_OPEN_REPLY')
  elif op == 'ADVANCE':
    native._keys(data, ('start_index', 'end_index_exclusive', 'checkpoint'))
    start, end = request['body']['start_index'], request['body']['start_index'] + request['body']['count']
    if (type(data['start_index']) is not int or data['start_index'] != start or
        type(data['end_index_exclusive']) is not int or data['end_index_exclusive'] != end):
      raise ValueError('JOINT_PROGRESS_MISMATCH')
    checkpoint = data['checkpoint']
    native._keys(checkpoint, ('chunk_index', 'axes'))
    native._keys(checkpoint['axes'], paired_shadow.AXES)
    if type(checkpoint['chunk_index']) is not int or checkpoint['chunk_index'] < 0:
      raise ValueError('INVALID_CHECKPOINT_INDEX')
    for item in checkpoint['axes'].values():
      native._keys(item, ('start_index', 'end_index_exclusive', 'first_time_ns', 'last_time_ns', 'end_state_sha256'))
      if (any(type(item[key]) is not int for key in ('start_index', 'end_index_exclusive', 'first_time_ns', 'last_time_ns')) or
          item['start_index'] != start or item['end_index_exclusive'] != end or
          item['last_time_ns'] - item['first_time_ns'] != (end - start - 1) * native.TIMESTEP_NS or
          not native._hex(item['end_state_sha256'], 64)):
        raise ValueError('INVALID_JOINT_CHECKPOINT')
  elif op == 'ABORT':
    native._keys(data, ('processed_frames', 'completed'))
    if type(data['processed_frames']) is not int or not 0 <= data['processed_frames'] <= native.MAX_FRAMES or data['completed'] is not False:
      raise ValueError('INVALID_ABORT_REPLY')
  elif op == 'CLOSE':
    native._keys(data, ())
  elif type(data) is not dict:
    raise ValueError('INVALID_FINISH_REPLY')


class EpochMachine:
  """Single child owner; sequence/source/epoch errors permanently end the session."""
  def __init__(self):
    self.closed = False
    self._session_id = self._epoch = self._epoch_sha = self._joint = None
    self._sequence = self._epoch_id = self._index = 0
    self._checkpoints = []

  def dispatch(self, message):
    try:
      request = decode_message(encode_message(message))
      if self.closed or request['sequence'] != self._sequence:
        raise ValueError('INVALID_SESSION_SEQUENCE')
      if self._session_id is None:
        if request['operation'] != 'OPEN':
          raise ValueError('SESSION_REQUIRES_OPEN')
        self._session_id = request['session_id']
      if request['session_id'] != self._session_id:
        raise ValueError('SESSION_ID_CHANGED')
      if self._epoch is not None:
        verify_epoch(self._epoch)
      data = self._dispatch(request)
      if self._epoch is not None:
        verify_epoch(self._epoch)
      reply = {key: request[key] for key in ('version', 'session_id', 'sequence', 'epoch_id', 'operation')}
      reply.update(request_sha256=digest(encode_message(request)), status=STATUSES[request['operation']],
                   data=data, **dict.fromkeys(joint.AUTHORITIES, False))
      validate_reply(request, reply)
      self._sequence += 1
      return copy.deepcopy(reply)
    except BaseException as exc:
      try:
        self.close()
      except BaseException:
        BaseException.add_note(exc, 'JOINT_SESSION_CLEANUP_UNCONFIRMED')
      raise

  def _dispatch(self, request):
    op, body = request['operation'], request['body']
    if op == 'CLOSE':
      self.close()
      return {}
    if op == 'OPEN':
      if self._joint is not None or request['epoch_id'] != self._epoch_id + 1:
        raise ValueError('UNFINISHED_OR_OUT_OF_ORDER_EPOCH')
      verify_epoch(body)
      identity = digest(encode_epoch(body))
      if self._epoch_sha is not None and identity != self._epoch_sha:
        raise ValueError('CHANGED_EPOCH_REQUIRES_FRESH_PROCESS')
      self._epoch, self._epoch_sha = copy.deepcopy(body), identity
      self._epoch_id, self._index, self._checkpoints = request['epoch_id'], 0, []
      self._joint = joint._JointEpoch(self._epoch['joint'])
      return {'epoch_sha256': identity, 'frame_count': frame_count(body)}
    if self._joint is None or request['epoch_id'] != self._epoch_id or body['epoch_sha256'] != self._epoch_sha:
      raise ValueError('STALE_OR_MISSING_JOINT_EPOCH')
    if op == 'ADVANCE':
      if body['start_index'] != self._index:
        raise ValueError('NONCONTIGUOUS_JOINT_INPUT')
      start = self._index
      checkpoint = self._joint.advance(body['count'])
      self._checkpoints.append(checkpoint)
      self._index += body['count']
      return {'start_index': start, 'end_index_exclusive': self._index, 'checkpoint': checkpoint}
    if op == 'ABORT':
      self._joint.close()
      self._joint = None
      return {'processed_frames': self._index, 'completed': False}
    candidates = self._joint.finish()
    self._joint = None
    native_lat, native_long = paired_shadow._split(self._epoch['joint']['pair'])
    with source_only_imports():
      baselines = {'lateral': joint.native_worker._execute_request(native_lat, _capture_state=True),
                   'longitudinal': joint.native_long_worker._execute_request(native_long, _capture_state=True)}
    result = {'status': joint.PASS, 'scope': joint.SCOPE, 'request_sha256': digest(joint.encode_request(self._epoch['joint'])),
              'input_alignment': paired_shadow.ALIGNMENT,
              'axes': {axis: {'baseline': baselines[axis], 'candidate': candidates[axis]} for axis in paired_shadow.AXES},
              'checkpoints': self._checkpoints, 'checkpoints_sha256': digest(canonical(self._checkpoints)),
              **dict.fromkeys(joint.AUTHORITIES, False)}
    joint.validate_response(self._epoch['joint'], result)
    return result

  def close(self):
    self.closed = True
    if self._joint is not None:
      self._joint.close()
      self._joint = None

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc, _traceback):
    try:
      self.close()
    except BaseException:
      if exc_type is None:
        raise
      BaseException.add_note(exc, 'JOINT_SESSION_CLEANUP_UNCONFIRMED')
