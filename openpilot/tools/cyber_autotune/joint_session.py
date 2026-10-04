"""Joint preadmitted IPC using the existing owned lateral-session transport."""
import copy
from pathlib import Path

from openpilot.tools.cyber_autotune import joint_continuity as joint, joint_session_protocol as protocol
from openpilot.tools.cyber_autotune.lateral_session import LateralSession
from openpilot.tools.cyber_autotune.native_protocol import canonical


WORKER_PATH = Path(__file__).resolve().with_name('joint_session_worker.py')
build_epoch = protocol.build_epoch


class JointSession(LateralSession):
  """One child, fixed source/input/partition; state survives separate chunk jobs.

  New completed/aborted epochs start both controllers fresh. No arbitrary live
  frames, automatic retry, hot reload, actuator output or qualification authority.
  Creating thread owns all calls; inherited timeout and cleanup contracts apply.
  """
  _protocol = protocol
  _worker_name = 'joint_session_worker.py'

  def advance(self, handle, *, start_index, count):
    with self._guard():
      self._require_handle(handle)
      index = len(self._checkpoints)
      sizes = self._epoch['joint']['chunk_sizes']
      if (type(start_index) is not int or start_index != self._index or type(count) is not int or
          index >= len(sizes) or sizes[index] != count):
        raise ValueError('INVALID_JOINT_PROGRESS')
      data = self._request('ADVANCE', handle.epoch_id,
                           {'epoch_sha256': handle.epoch_sha256, 'start_index': start_index, 'count': count})
      checkpoint = data['checkpoint']
      if checkpoint['chunk_index'] != index:
        raise ValueError('JOINT_CHECKPOINT_ORDER_MISMATCH')
      for axis, item in checkpoint['axes'].items():
        frames = self._epoch['joint']['pair']['frames'][axis]
        if item['first_time_ns'] != frames[start_index]['time_ns'] or item['last_time_ns'] != frames[start_index + count - 1]['time_ns']:
          raise ValueError('JOINT_CHECKPOINT_TIME_MISMATCH')
      self._checkpoints.append(copy.deepcopy(checkpoint))
      self._index = data['end_index_exclusive']
      return data

  def finish(self, handle):
    with self._guard():
      self._require_handle(handle)
      if self._index != protocol.frame_count(self._epoch) or len(self._checkpoints) != len(self._epoch['joint']['chunk_sizes']):
        raise ValueError('INCOMPLETE_JOINT_EPOCH')
      result = self._request('FINISH', handle.epoch_id, {'epoch_sha256': handle.epoch_sha256})
      joint.validate_response(self._epoch['joint'], result)
      if canonical(result['checkpoints']) != canonical(self._checkpoints):
        raise ValueError('JOINT_CHECKPOINT_HISTORY_MISMATCH')
      protocol.verify_epoch(self._epoch)
      self._handle = None
      return result
