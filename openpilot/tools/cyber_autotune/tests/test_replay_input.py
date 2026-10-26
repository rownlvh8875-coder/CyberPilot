import errno
import fcntl
import os
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import replay_input
from openpilot.tools.cyber_autotune.replay_admission import inspect_replay_input
from openpilot.tools.cyber_autotune.tests import test_replay_admission as fixtures


class TestReplayInput(unittest.TestCase):
  setUp = fixtures.TestReplayAdmission.setUp
  git = fixtures.TestReplayAdmission.git
  def retain(self, grants=None):
    return replay_input.retain_replay_input(self.request, grants=(self.grant,) if grants is None else grants,
                                            authority_sha256='a' * 64)

  def test_snapshot_is_immutable_even_if_original_replaced(self):
    with self.retain() as (fd, receipt):
      (self.data / 'input').write_bytes(b'xyz')
      (self.data / 'input').unlink()
      self.assertEqual(os.pread(fd, 10, 0), b'abc')
      self.assertEqual(receipt['input_sha256'], 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
      for operation in (lambda: os.pwrite(fd, b'x', 0), lambda: os.ftruncate(fd, 0), lambda: os.ftruncate(fd, 9)):
        with self.assertRaises(OSError) as error:
          operation()
        self.assertEqual(error.exception.errno, errno.EPERM)
      self.assertEqual(fcntl.fcntl(fd, 1034), 15)  # Linux F_GET_SEALS
      for key in ('replay_allowed', 'runtime_accepted', 'promotable'):
        self.assertIs(receipt[key], False)
    with self.assertRaises(OSError):
      os.fstat(fd)

  def test_context_closes_snapshot_on_consumer_error(self):
    with self.assertRaisesRegex(RuntimeError, 'consumer'):
      with self.retain() as (fd, _):
        raise RuntimeError('consumer')
    with self.assertRaises(OSError):
      os.fstat(fd)

  def test_mismatch_leaks_no_descriptor(self):
    before = set(os.listdir('/proc/self/fd'))
    for change in ({'sha256': '0' * 64}, {'size_bytes': 2}, {'size_bytes': 4}):
      with self.subTest(change=change), self.assertRaises(ValueError), self.retain((dict(self.grant, **change),)):
        self.fail('invalid input yielded')
    self.assertEqual(set(os.listdir('/proc/self/fd')), before)

  def test_denied_input_never_opens(self):
    for change in ({'role': 'holdout'}, {'segment': 53}, {'segment': 71}):
      with self.subTest(change=change), patch('os.open', side_effect=AssertionError('denied bytes opened')):
        with self.assertRaises(ValueError), self.retain((dict(self.grant, **change),)):
          self.fail('denied input yielded')

  def test_symlink_rejected_in_snapshot_open(self):
    (self.data / 'link').symlink_to(self.data / 'input')
    with self.assertRaises(ValueError), self.retain((dict(self.grant, path='link'),)):
      self.fail('symlink yielded')

  def test_observation_needs_no_fabricated_initial_state_but_cannot_enter_replay(self):
    request = {key: value for key, value in self.request.items() if key != 'initial_state'}
    request['purpose'] = 'OBSERVE_INITIAL_STATE'
    with replay_input.retain_observation_input(request, grants=(self.grant,), authority_sha256='a' * 64) as (fd, receipt):
      self.assertEqual(os.pread(fd, 3, 0), b'abc')
      self.assertEqual(receipt['purpose'], 'OBSERVE_INITIAL_STATE')
      self.assertIs(receipt['replay_allowed'], False)
    with self.assertRaises(ValueError):
      inspect_replay_input(request, grants=(self.grant,), authority_sha256='a' * 64)
    for change in ({'initial_state': self.request['initial_state']}, {'purpose': 'REPLAY'}, {'version': True}):
      with self.subTest(change=change), self.assertRaises(ValueError):
        with replay_input.retain_observation_input(dict(request, **change), grants=(self.grant,), authority_sha256='a' * 64):
          self.fail('invalid observation yielded')

  def test_observation_retains_protected_input_gate(self):
    request = {key: value for key, value in self.request.items() if key != 'initial_state'}
    request['purpose'] = 'OBSERVE_INITIAL_STATE'
    for change in ({'role': 'holdout'}, {'role': 'validation'}, {'segment': 53}, {'segment': 71}):
      with self.subTest(change=change), patch('os.open', side_effect=AssertionError('protected bytes opened')):
        with self.assertRaises(ValueError):
          with replay_input.retain_observation_input(request, grants=(dict(self.grant, **change),), authority_sha256='a' * 64):
            self.fail('protected observation yielded')
