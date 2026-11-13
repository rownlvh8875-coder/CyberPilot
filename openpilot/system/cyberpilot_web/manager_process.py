"""Optional monitor lifecycle without a driving-health dependency."""

import time

from openpilot.system.manager.process import PythonProcess


class OptionalStatusProcess(PythonProcess):
  # This is a retry policy for the website, never a control period.
  next_start = 0.0
  retry_s = 30.0

  def get_process_state_msg(self):
    state = super().get_process_state_msg()
    # Keep running/pid/exitCode observable, but failure of this optional website
    # must not enter selfdrived's required-process NO_ENTRY/SOFT_DISABLE set.
    state.shouldBeRunning = False
    return state

  def start(self):
    if self.proc is not None and self.proc.exitcode is not None:
      self.stop()  # reap an already-exited child; no signal/wait on a live child
    now = time.monotonic()
    if self.proc is None and now >= self.next_start:
      self.next_start = now + self.retry_s
      super().start()
