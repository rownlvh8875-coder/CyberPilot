import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from tools.cyberpilot_web_native.supervise import run_command


class SupervisionTests(unittest.TestCase):
  def test_success_and_failure_exit_codes(self):
    with tempfile.TemporaryDirectory() as directory:
      log = Path(directory) / 'command.log'
      self.assertEqual(run_command([sys.executable, '-c', 'print("ok")'], Path.cwd(), os.environ.copy(), log, timeout=3), 0)
      self.assertEqual(log.read_text().strip(), 'ok')
      self.assertEqual(run_command([sys.executable, '-c', 'raise SystemExit(7)'], Path.cwd(), os.environ.copy(), log, timeout=3), 7)

  def test_timeout_terminates_monitor_descendant_group(self):
    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      pidfile = root / 'child.pid'
      script = 'import subprocess,sys,time; from pathlib import Path; p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"]);Path(sys.argv[1]).write_text(str(p.pid));time.sleep(60)'
      try:
        with self.assertRaises(subprocess.TimeoutExpired):
          run_command([sys.executable, '-c', script, str(pidfile)], Path.cwd(), os.environ.copy(), root / 'timeout.log', timeout=0.5)
        pid = int(pidfile.read_text())
        status = Path(f'/proc/{pid}/stat')
        deadline = time.monotonic() + 3
        while status.exists() and status.read_text().split()[2] != 'Z' and time.monotonic() < deadline:
          time.sleep(0.01)
        self.assertTrue(not status.exists() or status.read_text().split()[2] == 'Z', 'descendant still executing')
      finally:
        if pidfile.exists():
          try:
            os.kill(int(pidfile.read_text()), 9)
          except ProcessLookupError:
            pass
