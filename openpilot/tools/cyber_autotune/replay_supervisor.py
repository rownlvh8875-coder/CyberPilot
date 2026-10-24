"""Bounded Linux process lifecycle for a future OFFLINE replay coordinator.

Private trusted argv only. This is not a sandbox, admission decision, or replay
adapter. Process-group cleanup cannot contain setsid descendants; the caller
must supply a verified PID namespace launcher for that guarantee. Never call
from an active control-loop thread. No stdin payload, no raw output logging.
"""
from dataclasses import dataclass
import math
import os
import selectors
import signal
import subprocess
import time

from openpilot.tools.cyber_autotune.native_runner import _kill_owned_group, _wait_owned_group_exit


# Infrastructure budgets, not control tuning or scientific acceptance thresholds.
MAX_TIMEOUT_S = 60.
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
READ_BYTES = 64 * 1024
POLL_S = .02
REAP_TIMEOUT_S = 1.
# Complete cleanup despite one KeyboardInterrupt, then propagate it to caller.
CLEANUP_ATTEMPTS = 2


@dataclass(frozen=True)
class BoundedOutcome:
  status: str
  returncode: int | None
  output: bytes
  pid: int


def _cleanup(process, killed):
  interrupted = None
  confirmed = False
  try:
    for _ in range(CLEANUP_ATTEMPTS):
      try:
        if not killed:
          _kill_owned_group(process)
          killed = True
        _wait_owned_group_exit(process.pid)
        confirmed = True
        break
      except KeyboardInterrupt as error:
        if interrupted is not None:
          raise
        interrupted = error
      except (OSError, TimeoutError):
        break
  finally:
    process.stdout.close()
    # Never signal after this point: wait may reap even when interrupted.
    for _ in range(CLEANUP_ATTEMPTS):
      try:
        process.wait(timeout=REAP_TIMEOUT_S)
        break
      except KeyboardInterrupt as error:
        if interrupted is not None:
          raise
        interrupted = error
      except subprocess.TimeoutExpired:
        confirmed = False
        break
  if interrupted is not None:
    raise interrupted
  return confirmed


def _run_bounded(argv, *, timeout_s, max_output_bytes, env=None, pass_fds=()):
  """Own the new group; retain its leader until signaling/exit confirmation.

Output is capped across stdout AND stderr; bytes are untrusted and may contain
private paths. Caller must validate/aggregate them, never publish indiscriminately.
Deadline includes pipe draining. Failure to confirm cleanup overrides success.
Ordinary errors/interruptions also clean the owned group before propagating.
Caller must preserve default SIGCHLD disposition and sole-waiter ownership for
the whole run. Supervisor SIGKILL/crash or repeated interrupts are not covered.
"""
  if (type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) or not 0 < timeout_s <= MAX_TIMEOUT_S or
      type(max_output_bytes) is not int or not 0 < max_output_bytes <= MAX_OUTPUT_BYTES):
    raise ValueError('INVALID_RESOURCE_LIMIT')
  if signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL:
    raise ValueError('UNSUPPORTED_CHILD_REAPER')
  deadline = time.monotonic() + timeout_s
  process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             start_new_session=True, close_fds=True, env=env, pass_fds=pass_fds)
  output = bytearray()
  status = 'EXITED'
  killed = False
  cleanup_ok = False
  try:
    os.set_blocking(process.stdout.fileno(), False)
    with selectors.DefaultSelector() as selector:
      selector.register(process.stdout, selectors.EVENT_READ)
      while True:
        # Unlike poll()/wait(), WNOWAIT preserves the leader PID until killpg.
        # This helper must be the sole waiter for the process it created.
        exited = os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
        if exited and not killed:
          _kill_owned_group(process)
          killed = True
        if exited and not selector.get_map():
          break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
          status = 'TIMEOUT'
          break
        for key, _ in selector.select(min(POLL_S, remaining)):
          try:
            block = os.read(key.fd, min(READ_BYTES, max_output_bytes - len(output) + 1))
          except BlockingIOError:
            continue
          if not block:
            selector.unregister(key.fileobj)
          elif len(output) + len(block) > max_output_bytes:
            output.extend(block[:max_output_bytes - len(output)])
            status = 'OUTPUT_LIMIT'
            break
          else:
            output.extend(block)
        if status == 'OUTPUT_LIMIT':
          break
  finally:
    cleanup_ok = _cleanup(process, killed)
  return BoundedOutcome(status if cleanup_ok else 'CLEANUP_UNCONFIRMED', process.returncode, bytes(output), process.pid)
