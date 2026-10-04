"""Persistent fixed-source PC child. No device/input-log/profile interface."""
import contextlib
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time


# Bootstrap must arm before importing repository modules. Checked against the
# inherited supervisor limit once imports complete; never a vehicle tolerance.
BOOTSTRAP_WALL_LIMIT_S = 60.


def _arm_lifetime():
  now = time.monotonic_ns()
  if len(sys.argv) > 2:
    raise ValueError('INVALID_WORKER_LIFETIME_ARGUMENT')
  deadline = int(sys.argv[1]) if len(sys.argv) == 2 else now + int(BOOTSTRAP_WALL_LIMIT_S * 1e9)
  remaining = min(BOOTSTRAP_WALL_LIMIT_S, (deadline - now) / 1e9)
  if remaining <= 0:
    raise TimeoutError('SESSION_LIFETIME_EXPIRED')

  # Kernel termination cannot fall back into a blocking error-output write.
  # Expiry is fail-stop; Python/finally/temp-directory cleanup is not promised.
  signal.signal(signal.SIGALRM, signal.SIG_DFL)
  signal.setitimer(signal.ITIMER_REAL, remaining)


def main(*, _joint=False):
  previous = sys.pycache_prefix, sys.dont_write_bytecode
  output = sys.stdout.buffer
  try:
    _arm_lifetime()
    with tempfile.TemporaryDirectory(prefix='cyber-session-bootstrap-') as cache:
      sys.pycache_prefix, sys.dont_write_bytecode = cache, True
      root = Path(__file__).resolve().parents[3]
      sys.path[:0] = [str(root), str(root / 'opendbc_repo'), str(Path(__file__).resolve().parent)]
      from worker_resources import apply_worker_limits
      apply_worker_limits()
      from openpilot.tools.cyber_autotune.native_runner import MAX_RESPONSE_BYTES, MAX_TIMEOUT_S
      # Only fixed internal entries select a protocol; no user module/path input.
      if _joint is True:
        from openpilot.tools.cyber_autotune.joint_session_protocol import MAX_REQUEST_BYTES, EpochMachine, canonical, decode_message
      elif _joint is False:
        from openpilot.tools.cyber_autotune.lateral_session_protocol import MAX_REQUEST_BYTES, EpochMachine, canonical, decode_message
      else:
        raise ValueError('INVALID_INTERNAL_SESSION_MODE')

      if MAX_TIMEOUT_S != BOOTSTRAP_WALL_LIMIT_S:
        raise ValueError('BOOTSTRAP_LIMIT_MISMATCH')
      with EpochMachine() as machine, open(os.devnull, 'w') as quiet:
        while True:
          payload = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 2)
          if not payload.endswith(b'\n') or len(payload) > MAX_REQUEST_BYTES + 1:
            raise ValueError('INCOMPLETE_OR_OVERSIZED_MESSAGE')
          with contextlib.redirect_stdout(quiet):
            result = machine.dispatch(decode_message(payload[:-1]))
          encoded = canonical(result)
          if len(encoded) > MAX_RESPONSE_BYTES:
            raise ValueError('SESSION_RESPONSE_TOO_LARGE')
          output.write(encoded + b'\n')
          output.flush()
          if machine.closed:
            return 0
  except Exception:
    encoded = json.dumps({'status': 'REJECTED', 'code': 'INVALID_OR_FAILED_SESSION'}, sort_keys=True, separators=(',', ':')).encode()
    try:
      output.write(encoded + b'\n')
      output.flush()
    except OSError:
      pass
    return 1
  finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
    sys.pycache_prefix, sys.dont_write_bytecode = previous


if __name__ == '__main__':
  raise SystemExit(main())
