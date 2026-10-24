"""Fixed synthetic epoch protocol. Content IDs correlate bytes, not vehicle authority."""
import copy
import json

from openpilot.tools.cyber_autotune import a1_experiment as a1, lateral_continuity as continuity
from openpilot.tools.cyber_autotune.native_protocol import (
  MAX_REQUEST_BYTES, TIMESTEP_NS, _hex, _invalid_constant, _keys, _unique_pairs, canonical, digest,
)
from openpilot.tools.cyber_autotune.native_worker import _execute_request


OVERLAY_FILES = tuple('openpilot/tools/cyber_autotune/' + name for name in
                      ('lateral_session.py', 'lateral_session_protocol.py', 'lateral_session_worker.py'))
STATUSES = {'OPEN': 'OPENED', 'ADVANCE': 'ADVANCED', 'FINISH': 'COMPLETED', 'ABORT': 'ABORTED', 'CLOSE': 'CLOSED'}


def build_epoch():
  return {'continuity': continuity.build_request([a1.FRAME_COUNT]),
          'overlay': {name: digest((a1.ROOT / name).read_bytes()) for name in OVERLAY_FILES}}


def encode_epoch(epoch):
  _keys(epoch, ('continuity', 'overlay'))
  continuity.encode_request(epoch['continuity'])
  if epoch['continuity']['chunk_sizes'] != [a1.FRAME_COUNT]:
    raise ValueError('EPOCH_MUST_ADMIT_COMPLETE_FIXED_INPUT')
  _keys(epoch['overlay'], OVERLAY_FILES)
  if not all(_hex(value, 64) for value in epoch['overlay'].values()):
    raise ValueError('INVALID_SESSION_OVERLAY')
  payload = canonical(epoch)
  if len(payload) > MAX_REQUEST_BYTES:
    raise ValueError('EPOCH_TOO_LARGE')
  return payload


def verify_epoch(epoch):
  encode_epoch(epoch)
  for name, expected in epoch['overlay'].items():
    path = (a1.ROOT / name).resolve(strict=True)
    if not path.is_relative_to(a1.ROOT) or digest(path.read_bytes()) != expected:
      raise ValueError('SESSION_SOURCE_CHANGED')
  continuity._verify_bindings(epoch['continuity'])


def make_message(session_id, sequence, epoch_id, operation, body):
  return {'version': 1, 'session_id': session_id, 'sequence': sequence,
          'epoch_id': epoch_id, 'operation': operation, 'body': body}


def encode_message(message):
  _keys(message, ('version', 'session_id', 'sequence', 'epoch_id', 'operation', 'body'))
  if (type(message['version']) is not int or message['version'] != 1 or not _hex(message['session_id'], 32) or
      any(type(message[name]) is not int or message[name] < 0 for name in ('sequence', 'epoch_id'))):
    raise ValueError('INVALID_SESSION_HEADER')
  op, body = message['operation'], message['body']
  if type(op) is not str or op not in STATUSES:
    raise ValueError('INVALID_SESSION_OPERATION')
  if op == 'OPEN':
    encode_epoch(body)
  elif op == 'CLOSE':
    _keys(body, ())
    if message['epoch_id'] != 0:
      raise ValueError('INVALID_CLOSE_EPOCH')
  else:
    _keys(body, ('epoch_sha256', 'start_index', 'count') if op == 'ADVANCE' else ('epoch_sha256',))
    if not _hex(body['epoch_sha256'], 64):
      raise ValueError('INVALID_EPOCH_BINDING')
    if op == 'ADVANCE' and (type(body['start_index']) is not int or type(body['count']) is not int or
                            not 0 <= body['start_index'] < a1.FRAME_COUNT or
                            not 0 < body['count'] <= a1.FRAME_COUNT - body['start_index']):
      raise ValueError('INVALID_ADVANCE')
  if op != 'CLOSE' and message['epoch_id'] < 1:
    raise ValueError('INVALID_EPOCH_NUMBER')
  payload = canonical(message)
  if len(payload) > MAX_REQUEST_BYTES:
    raise ValueError('SESSION_MESSAGE_TOO_LARGE')
  return payload


def decode_json(payload):
  try:
    return json.loads(payload, object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant)
  except (UnicodeError, RecursionError) as exc:
    raise ValueError('INVALID_SESSION_JSON') from exc


def decode_message(payload):
  if type(payload) is not bytes or not 0 < len(payload) <= MAX_REQUEST_BYTES:
    raise ValueError('INVALID_SESSION_MESSAGE_SIZE')
  message = decode_json(payload)
  encode_message(message)
  return message


def validate_reply(request, reply):
  _keys(reply, ('version', 'session_id', 'sequence', 'epoch_id', 'operation', 'request_sha256', 'status', 'data', *a1.AUTHORITIES))
  for name in ('version', 'session_id', 'sequence', 'epoch_id', 'operation'):
    if type(reply[name]) is not type(request[name]) or reply[name] != request[name]:
      raise ValueError('REPLY_CORRELATION_MISMATCH')
  op, data = request['operation'], reply['data']
  if (reply['request_sha256'] != digest(encode_message(request)) or reply['status'] != STATUSES[op] or
      any(reply[name] is not False for name in a1.AUTHORITIES)):
    raise ValueError('INVALID_SESSION_REPLY')
  if op == 'OPEN':
    expected = {'epoch_sha256': digest(encode_epoch(request['body'])), 'frame_count': a1.FRAME_COUNT}
    if canonical(data) != canonical(expected):
      raise ValueError('INVALID_OPEN_REPLY')
  elif op == 'ADVANCE':
    _keys(data, ('start_index', 'end_index_exclusive', 'first_time_ns', 'last_time_ns', 'end_state_sha256'))
    start, end = request['body']['start_index'], request['body']['start_index'] + request['body']['count']
    expected = {'start_index': start, 'end_index_exclusive': end, 'first_time_ns': start * TIMESTEP_NS,
                'last_time_ns': (end - 1) * TIMESTEP_NS}
    if any(type(data[name]) is not int or data[name] != value for name, value in expected.items()) or not _hex(data['end_state_sha256'], 64):
      raise ValueError('INVALID_ADVANCE_REPLY')
  elif op == 'ABORT':
    _keys(data, ('processed_frames', 'completed'))
    if type(data['processed_frames']) is not int or not 0 <= data['processed_frames'] <= a1.FRAME_COUNT or data['completed'] is not False:
      raise ValueError('INVALID_ABORT_REPLY')
  elif op == 'CLOSE':
    _keys(data, ())
  elif type(data) is not dict:
    raise ValueError('INVALID_FINISH_REPLY')


class EpochMachine:
  """Child-only fixed-source state machine; failure is terminal, never a retry."""
  def __init__(self):
    self.closed = False
    self._session_id = None
    self._sequence = self._epoch_id = self._index = 0
    self._epoch = self._epoch_sha = self._cursor = None
    self._chunks = []

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
      reply = {name: request[name] for name in ('version', 'session_id', 'sequence', 'epoch_id', 'operation')}
      reply.update(request_sha256=digest(encode_message(request)), status=STATUSES[request['operation']],
                   data=data, **dict.fromkeys(a1.AUTHORITIES, False))
      validate_reply(request, reply)
      self._sequence += 1
      return copy.deepcopy(reply)
    except BaseException:
      self.close()
      raise

  def _dispatch(self, request):
    op, body = request['operation'], request['body']
    if op == 'CLOSE':
      self.close()
      return {}
    if op == 'OPEN':
      if self._cursor is not None or request['epoch_id'] != self._epoch_id + 1:
        raise ValueError('UNFINISHED_OR_OUT_OF_ORDER_EPOCH')
      verify_epoch(body)
      identity = digest(encode_epoch(body))
      if self._epoch_sha is not None and identity != self._epoch_sha:
        raise ValueError('CHANGED_EPOCH_REQUIRES_FRESH_PROCESS')
      self._epoch, self._epoch_sha = copy.deepcopy(body), identity
      self._epoch_id, self._index, self._chunks = request['epoch_id'], 0, []
      self._native, self._table = a1.make_fixture(body['continuity']['fixture_request'])
      self._cursor = continuity._TorqueChunkCursor(self._native)
      return {'epoch_sha256': identity, 'frame_count': a1.FRAME_COUNT}
    if self._cursor is None or request['epoch_id'] != self._epoch_id or body['epoch_sha256'] != self._epoch_sha:
      raise ValueError('STALE_OR_MISSING_EPOCH')
    if op == 'ADVANCE':
      if body['start_index'] != self._index:
        raise ValueError('GAP_DUPLICATE_OR_REORDERED_INPUT')
      checkpoint = self._cursor.advance(body['count'])
      self._index += body['count']
      self._chunks.append(checkpoint)
      return checkpoint
    if op == 'ABORT':
      self._cursor.close()
      self._cursor = None
      return {'processed_frames': self._index, 'completed': False}
    candidate = self._cursor.finish()
    self._cursor = None
    baseline = _execute_request(self._native, _capture_state=True)
    request = copy.deepcopy(self._epoch['continuity'])
    request['chunk_sizes'] = [row['end_index_exclusive'] - row['start_index'] for row in self._chunks]
    fixture = request['fixture_request']
    comparison = {'status': a1.PASS, 'fixture': 'disabled', 'request_sha256': digest(a1.encode_request(fixture)),
                  'manifest': a1._manifest(fixture, self._native, self._table), 'baseline': baseline, 'candidate': candidate,
                  'unavailable_metrics': a1.UNAVAILABLE.copy(), **dict.fromkeys(a1.AUTHORITIES, False)}
    result = {'status': continuity.PASS, 'scope': continuity.SCOPE, 'request_sha256': digest(continuity.encode_request(request)),
              'comparison': comparison, 'chunks': self._chunks, 'chunks_sha256': digest(canonical(self._chunks)),
              **dict.fromkeys(a1.AUTHORITIES, False)}
    continuity.validate_response(request, result)
    return result

  def close(self):
    self.closed = True
    if self._cursor is not None:
      self._cursor.close()
      self._cursor = None

  def __enter__(self):
    return self

  def __exit__(self, *_):
    self.close()
