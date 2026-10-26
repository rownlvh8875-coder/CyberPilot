"""Fixed isolated joint-epoch worker; no device/log/profile interface."""
import contextlib
import json
import os
from pathlib import Path
import sys
import tempfile


def main():
  previous = sys.pycache_prefix, sys.dont_write_bytecode
  try:
    with tempfile.TemporaryDirectory(prefix='cyber-joint-bootstrap-') as cache:
      sys.pycache_prefix, sys.dont_write_bytecode = cache, True
      root = Path(__file__).resolve().parents[3]
      sys.path[:0] = [str(root), str(root / 'opendbc_repo'), str(Path(__file__).resolve().parent)]
      from worker_resources import apply_worker_limits
      apply_worker_limits()
      from openpilot.tools.cyber_autotune.joint_continuity import decode_request, execute_experiment
      from native_protocol import MAX_REQUEST_BYTES, canonical
      request = decode_request(sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1))
      with open(os.devnull, 'w') as quiet, contextlib.redirect_stdout(quiet):
        result = execute_experiment(request)
    sys.stdout.buffer.write(canonical(result) + b'\n')
    return 0
  except Exception:
    error = {'status': 'REJECTED', 'code': 'INVALID_OR_FAILED_JOINT_REQUEST'}
    sys.stdout.buffer.write(json.dumps(error, sort_keys=True, separators=(',', ':')).encode() + b'\n')
    return 1
  finally:
    sys.pycache_prefix, sys.dont_write_bytecode = previous


if __name__ == '__main__':
  raise SystemExit(main())
