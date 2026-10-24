"""Real synthetic children only: no driving logs, replay or vehicle access."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune import replay_supervisor


def running(pid):
  try:
    return Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()[0] != 'Z'
  except FileNotFoundError:
    return False


class TestReplaySupervisor(unittest.TestCase):
  def run_child(self, code, *, timeout_s=2., output_limit=1024):
    return replay_supervisor._run_bounded([sys.executable, '-I', '-c', code], timeout_s=timeout_s,
                                          max_output_bytes=output_limit)

  def test_normal_and_nonzero_are_not_confused(self):
    for code, expected in [('print("ok")', 0), ('print("bad"); raise SystemExit(7)', 7)]:
      with self.subTest(expected=expected):
        result = self.run_child(code)
        self.assertEqual(result.status, 'EXITED')
        self.assertEqual(result.returncode, expected)
        self.assertEqual(result.output, b'ok\n' if expected == 0 else b'bad\n')
        self.assertFalse(running(result.pid))

  def test_stdin_is_closed(self):
    result = self.run_child('import sys; print(len(sys.stdin.buffer.read()))')
    self.assertEqual((result.status, result.output), ('EXITED', b'0\n'))

  def test_exact_output_budget_is_allowed_but_extra_byte_is_not(self):
    for count, expected in [(1000, 'EXITED'), (1001, 'OUTPUT_LIMIT')]:
      with self.subTest(count=count):
        result = self.run_child(f'import os; os.write(1, b"x" * {count})', output_limit=1000)
        self.assertEqual(result.status, expected)
        self.assertEqual(result.output, b'x' * 1000)

  def test_floods_on_either_stream_are_bounded_and_stopped(self):
    for stream in (1, 2):
      with self.subTest(stream=stream):
        result = self.run_child(f'import os\nwhile True: os.write({stream}, b"x" * 65536)', output_limit=2000)
        self.assertEqual(result.status, 'OUTPUT_LIMIT')
        self.assertEqual(len(result.output), 2000)
        self.assertFalse(running(result.pid))

  def test_timeout_without_output_is_bounded(self):
    start = time.monotonic()
    result = self.run_child('import time; time.sleep(30)', timeout_s=.15)
    self.assertEqual(result.status, 'TIMEOUT')
    self.assertLess(time.monotonic() - start, 3.)
    self.assertFalse(running(result.pid))

  def test_closed_pipe_does_not_mean_process_exited(self):
    result = self.run_child('import os,time; os.close(1); os.close(2); time.sleep(30)', timeout_s=.15)
    self.assertEqual(result.status, 'TIMEOUT')
    self.assertFalse(running(result.pid))

  def test_normal_exit_and_timeout_clean_owned_descendants_only(self):
    unrelated = subprocess.Popen([sys.executable, '-I', '-c', 'import time; time.sleep(30)'])
    try:
      for parent_sleep, expected in [(0, 'EXITED'), (30, 'TIMEOUT')]:
        with self.subTest(expected=expected):
          # Child inherits pipes, so EOF alone must not be relied on for cleanup.
          code = ('import subprocess,sys,time\n' +
                  'p=subprocess.Popen([sys.executable,"-I","-c","import time; time.sleep(30)"])\n' +
                  f'print(p.pid,flush=True)\ntime.sleep({parent_sleep})\n')
          result = self.run_child(code, timeout_s=.4)
          child = int(result.output)
          try:
            self.assertEqual(result.status, expected)
            self.assertFalse(running(child))
            self.assertIsNone(unrelated.poll())
          finally:
            if running(child):
              os.kill(child, signal.SIGKILL)
    finally:
      unrelated.kill()
      unrelated.wait()

  def test_invalid_resource_limits_never_launch(self):
    for timeout, cap in [(0, 1), (float('nan'), 1), (float('inf'), 1), (True, 1), (61, 1), (1, 0), (1, True),
                         (1, 4 * 1024 * 1024 + 1)]:
      with self.subTest(timeout=timeout, cap=cap), self.assertRaises(ValueError):
        replay_supervisor._run_bounded(['/missing-must-not-launch'], timeout_s=timeout, max_output_bytes=cap)

  def test_interrupt_after_launch_cleans_real_child(self):
    # Inject an asynchronous interruption at the first status check, not Popen:
    # process creation and kernel cleanup remain real.
    captured = []

    def interrupt(kind, pid, flags):
      captured.append(pid)
      raise KeyboardInterrupt

    with patch.object(replay_supervisor.os, 'waitid', side_effect=interrupt), self.assertRaises(KeyboardInterrupt):
      self.run_child('import time; time.sleep(30)')
    self.assertEqual(len(captured), 1)
    self.assertFalse(running(captured[0]))

  def test_cleanup_confirmation_failure_cannot_report_success(self):
    # Failure injection at /proc confirmation; actual child is still killed/reaped.
    with patch.object(replay_supervisor, '_wait_owned_group_exit', side_effect=OSError):
      result = self.run_child('print("ok")')
    self.assertEqual(result.status, 'CLEANUP_UNCONFIRMED')
    self.assertFalse(running(result.pid))

  def test_nondefault_child_reaper_is_rejected_before_launch(self):
    # An ignored SIGCHLD can auto-reap the leader before killpg. A custom handler
    # could reap it too. Neither may reach Popen, even for a nonexistent command.
    original = signal.getsignal(signal.SIGCHLD)
    try:
      for disposition in (signal.SIG_IGN, lambda signum, frame: None):
        signal.signal(signal.SIGCHLD, disposition)
        with self.subTest(disposition=disposition), self.assertRaises(ValueError):
          replay_supervisor._run_bounded(['/missing-must-not-launch'], timeout_s=1., max_output_bytes=1)
    finally:
      signal.signal(signal.SIGCHLD, original)

  def test_interrupt_at_cleanup_entry_still_terminates_child(self):
    captured = []
    original_kill = replay_supervisor._kill_owned_group

    def interrupt_once(process):
      captured.append(process)
      if len(captured) == 1:
        raise KeyboardInterrupt
      original_kill(process)

    try:
      with patch.object(replay_supervisor, '_kill_owned_group', side_effect=interrupt_once), self.assertRaises(KeyboardInterrupt):
        self.run_child('import time; time.sleep(30)', timeout_s=.1)
      self.assertFalse(running(captured[0].pid))
      self.assertIsNotNone(captured[0].returncode)
    finally:
      # Preserve hygiene when this regression runs against the broken version.
      for process in captured:
        if running(process.pid):
          process.kill()
        process.wait()

  def test_only_explicit_descriptor_is_inherited(self):
    fd = os.memfd_create('synthetic-fd', os.MFD_CLOEXEC)
    try:
      os.write(fd, b'abc')
      code = f'import os; print(os.pread({fd}, 3, 0).decode())'
      result = replay_supervisor._run_bounded([sys.executable, '-I', '-c', code], timeout_s=2.,
                                               max_output_bytes=1024, pass_fds=(fd,))
      self.assertEqual((result.status, result.returncode, result.output), ('EXITED', 0, b'abc\n'))
      result = self.run_child(code)
      self.assertNotEqual(result.returncode, 0)
    finally:
      os.close(fd)


if __name__ == '__main__':
  unittest.main()
