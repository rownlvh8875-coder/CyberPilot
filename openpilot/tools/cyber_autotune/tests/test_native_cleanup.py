import os
from pathlib import Path
import resource
import sys
import tempfile
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import native_runner as runner
from openpilot.tools.cyber_autotune import native_long_runner as long_runner
from openpilot.tools.cyber_autotune.tests.test_native_worker import fixture as lateral_fixture
from openpilot.tools.cyber_autotune.tests.test_native_long_worker import fixture as longitudinal_fixture


class TestNativeCleanup(unittest.TestCase):
  def test_timeout_waits_for_descendant_kernel_fd_cleanup(self):
    limit = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
    count = min(10000, limit - 64) if limit != resource.RLIM_INFINITY else 10000
    self.assertGreater(count, 0)
    child = f'import os,time; fds=[os.open("/dev/null",os.O_RDONLY) for _ in range({count})]; time.sleep(10)'
    code = ('import subprocess,sys,time; child=subprocess.Popen([sys.executable,"-c",' + repr(child) + ']); ' +
            'print(child.pid,flush=True); time.sleep(10)')
    for repetition in range(8):
      result = runner._run_process([sys.executable, '-c', code], b'', .3)
      self.assertEqual(result.status, 'TIMEOUT')
      child_pid = int(result.stdout.strip())
      try:
        state = Path(f'/proc/{child_pid}/stat').read_text().rsplit(') ', 1)[1].split()[0]
      except (FileNotFoundError, ProcessLookupError):
        state = 'ABSENT'
      with self.subTest(repetition=repetition):
        self.assertIn(state, ('ABSENT', 'Z'))
      with self.assertRaises(ProcessLookupError):
        os.kill(result.pid, 0)

  def test_membership_selection_terminal_states_and_disappearance(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      for name in ('101', '102', '103', 'self'):
        (root / name).mkdir()
      stat = root / '101' / 'stat'
      stat.write_text('101 (synthetic ) tricky) Z 1 323 323 0 -1 0\n')

      def group(pid):
        if pid == 103:
          raise ProcessLookupError
        return 323 if pid == 101 else 999

      with patch.object(runner, 'PROC_ROOT', root), patch.object(runner.os, 'getpgid', group):
        self.assertFalse(runner._owned_group_running(323))
        stat.write_text('101 (synthetic ) tricky) R 1 323 323 0 -1 0\n')
        self.assertTrue(runner._owned_group_running(323))
        stat.unlink()  # only this test-owned temporary fixture
        self.assertFalse(runner._owned_group_running(323))

  def test_group_confirmation_is_bounded_and_condition_driven(self):
    with patch.object(runner, '_owned_group_running', side_effect=[True, True, False]) as check, \
         patch.object(runner.time, 'monotonic', side_effect=[0., 0., .001]), patch.object(runner.time, 'sleep') as sleep:
      runner._wait_owned_group_exit(323)
      self.assertEqual(check.call_count, 3)
      self.assertEqual(sleep.call_count, 2)
    with patch.object(runner, '_owned_group_running', return_value=True), \
         patch.object(runner.time, 'monotonic', side_effect=[0., 2.]), self.assertRaises(TimeoutError):
      runner._wait_owned_group_exit(323)

  def test_unconfirmed_cleanup_cannot_be_successful_native_response(self):
    for native, request in ((runner.run_native, lateral_fixture()), (long_runner.run_native, longitudinal_fixture())):
      with self.subTest(native=native.__module__), \
           patch.object(runner, '_wait_owned_group_exit', side_effect=TimeoutError('PRIVATE_CLEANUP_DETAIL')):
        result = native(request, timeout_s=.000001)
        self.assertEqual(result['status'], 'WORKER_UNAVAILABLE')
        self.assertFalse(result['runtime_accepted'])
        self.assertFalse(result['promotable'])
        self.assertNotIn('samples', result)
        self.assertNotIn('PRIVATE_CLEANUP_DETAIL', str(result))


if __name__ == '__main__':
  unittest.main()
