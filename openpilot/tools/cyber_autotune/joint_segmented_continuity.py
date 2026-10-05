"""Compile predeclared segments into one immutable native epoch, without boundary resets.

No new live input, worker, actuator or tuning authority. Segment source/clock
matching is structural and does not attest real runtime parameter history.
"""
import copy

from openpilot.tools.cyber_autotune import joint_continuity as joint, joint_epoch_sequence as resets
from openpilot.tools.cyber_autotune import joint_session_protocol as protocol, native_protocol as native
from openpilot.tools.cyber_autotune.lateral_session import SessionError


JointSession = resets.JointSession
OVERLAY_FILE = 'openpilot/tools/cyber_autotune/joint_segmented_continuity.py'
PASS = 'SOFTWARE_PREDECLARED_SEGMENT_CONTINUITY_ONLY'
SCOPE = 'OFFLINE_SEGMENTS_WITHIN_ONE_NATIVE_EPOCH'
BOUNDARY = 'CONTINUE_SAME_PREADMITTED_NATIVE_EPOCH'


def encode_plan(plan):
  native._keys(plan, ('version', 'sequence', 'overlay'))
  if type(plan['version']) is not int or plan['version'] != 1:
    raise ValueError('INVALID_SEGMENT_PLAN_VERSION')
  native._keys(plan['overlay'], (OVERLAY_FILE,))
  if not native._hex(plan['overlay'][OVERLAY_FILE], 64):
    raise ValueError('INVALID_SEGMENT_PLAN_OVERLAY')
  resets.encode_sequence(plan['sequence'])
  payload = native.canonical(plan)
  if len(payload) > native.MAX_REQUEST_BYTES:
    raise ValueError('SEGMENT_PLAN_TOO_LARGE')
  return payload


def decode_plan(payload):
  plan = joint.paired_shadow._read_json(payload, native.MAX_REQUEST_BYTES)
  encode_plan(plan)
  return plan


def build_plan(segments):
  # Existing builder rejects aggregate raw bytes before any JSON allocation and
  # enforces total frames, contiguous time, exact same configuration and sources.
  sequence = resets.decode_sequence(resets.build_sequence(segments))
  return encode_plan({'version': 1, 'sequence': sequence,
                      'overlay': {OVERLAY_FILE: native.digest((joint.ROOT / OVERLAY_FILE).read_bytes())}})


def _verify(plan):
  path = (joint.ROOT / OVERLAY_FILE).resolve(strict=True)
  if not path.is_relative_to(joint.ROOT) or native.digest(path.read_bytes()) != plan['overlay'][OVERLAY_FILE]:
    raise ValueError('SEGMENT_SOURCE_CHANGED')
  resets._verify_sequence(plan['sequence'])


def _merged_epoch(plan):
  """Preserve admitted source identities; never replace old bindings with new hashes."""
  epochs = plan['sequence']['epochs']
  merged = copy.deepcopy(epochs[0])
  for axis in joint.paired_shadow.AXES:
    merged['joint']['pair']['frames'][axis] = [copy.deepcopy(frame) for epoch in epochs
                                               for frame in epoch['joint']['pair']['frames'][axis]]
  merged['joint']['chunk_sizes'] = [count for epoch in epochs for count in epoch['joint']['chunk_sizes']]
  protocol.encode_epoch(merged)
  return merged


def run_plan(payload, *, timeout_s):
  """Blocking bounded batch, one child/OPEN/FINISH for all prevalidated segments.

  Within each segment and across its artificial boundaries, state continues in
  the existing native controllers. Native off/override/reset behavior is unchanged.
  Any failure removes all comparison rows. Only normal confirmed close permits PASS.
  """
  if not native.finite(timeout_s) or not 0 < timeout_s <= resets.MAX_TIMEOUT_S:
    raise ValueError('INVALID_SEGMENT_TIMEOUT')
  deadline = resets.monotonic() + timeout_s
  plan = decode_plan(payload)
  plan_sha = native.digest(encode_plan(plan))
  stage, session = 'BINDING_REJECTED', None

  def remaining():
    budget = deadline - resets.monotonic()
    if budget <= 0:
      raise TimeoutError('SEGMENT_PLAN_DEADLINE')
    return budget

  def failure(status, info=None):
    info = resets._close_info(session) if info is None else info
    return {'status': status, 'scope': SCOPE, 'plan_sha256': plan_sha,
            'worker_returncode': info['code'], 'cleanup_confirmed': info['cleanup'],
            **dict.fromkeys(joint.AUTHORITIES, False)}

  try:
    _verify(plan)
    remaining()
    # All segments are merged BEFORE child creation, never appended to a running
    # session. Existing rejection of changed input inside a process stays intact.
    merged = _merged_epoch(plan)
    protocol.verify_epoch(merged)
    stage = 'SESSION_FAILED'
    session = JointSession(timeout_s=remaining())
    session._sequence_deadline = deadline
    with session:
      handle = session.open_epoch(merged)
      start = 0
      for count in merged['joint']['chunk_sizes']:
        stage = 'BINDING_REJECTED'
        _verify(plan)
        stage = 'SESSION_FAILED'
        session._timeout = remaining()
        session.advance(handle, start_index=start, count=count)
        start += count
      session._timeout = remaining()
      result = session.finish(handle)
      stage = 'INVALID_RESULT'
      joint.validate_response(merged['joint'], result)
      stage = 'BINDING_REJECTED'
      _verify(plan)
      session._timeout = remaining()
      stage = 'SESSION_FAILED'
    info = resets._close_info(session)
    if not info['cleanup']:
      return failure('CLEANUP_UNCONFIRMED', info)
    if not info['normal']:
      return failure('SESSION_FAILED', info)
    remaining()
    stage = 'BINDING_REJECTED'
    _verify(plan)
    stage = 'INVALID_RESULT'
    rows, start = [], 0
    for index, epoch in enumerate(plan['sequence']['epochs']):
      end = start + protocol.frame_count(epoch)
      state_ids = {}
      for axis in joint.paired_shadow.AXES:
        extension = 'a1' if axis == 'lateral' else 'continuity'
        state_ids[axis] = result['axes'][axis]['candidate'][extension]['states'][end - 1]['state_sha256']
      rows.append({'index': index, 'input_segment_sha256': native.digest(protocol.encode_epoch(epoch)),
                   'start_index': start, 'end_index_exclusive': end, 'end_state_sha256': state_ids})
      start = end
    axes = {}
    for axis in joint.paired_shadow.AXES:
      arm = result['axes'][axis]['candidate']
      extension = 'a1' if axis == 'lateral' else 'continuity'
      axes[axis] = {'ordered_trace_sha256': arm['ordered_trace_sha256'], 'states_sha256': arm[extension]['states_sha256']}
    report = {'status': PASS, 'scope': SCOPE, 'plan_sha256': plan_sha, 'segments': rows, 'axes': axes,
              'compiled_epoch_sha256': native.digest(protocol.encode_epoch(merged)),
              'native_result_sha256': native.digest(native.canonical(result)), 'frame_count': start,
              'boundary_policy': BOUNDARY, 'state_carried_between_segments': True,
              'input_alignment': joint.paired_shadow.ALIGNMENT, 'worker_returncode': info['code'],
              'cleanup_confirmed': True, **dict.fromkeys(joint.AUTHORITIES, False)}
    native.canonical(report)
    remaining()
    return report
  except TimeoutError:
    return failure('TIMEOUT')
  except SessionError as exc:
    return failure('TIMEOUT' if exc.receipt.get('status') == 'TIMEOUT' else 'SESSION_FAILED')
  except Exception:
    return failure(stage)
  except BaseException as exc:
    info = resets._close_info(session, pending_interrupt=exc)
    if not info['cleanup']:
      BaseException.add_note(exc, 'SEGMENT_CLEANUP_UNCONFIRMED')
    raise
