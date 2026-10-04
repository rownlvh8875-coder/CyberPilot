"""Fixed local A1 worker; stdin fixture envelope only, no logs/Params/vehicle IO."""
import contextlib
import json
import os
from pathlib import Path
import sys
import tempfile


def main():
  previous = sys.pycache_prefix, sys.dont_write_bytecode
  try:
    # Bootstrap before the FIRST repository import. -B alone still reads .pyc.
    with tempfile.TemporaryDirectory(prefix='cyber-a1-bootstrap-') as cache:
      sys.pycache_prefix, sys.dont_write_bytecode = cache, True
      root = Path(__file__).resolve().parents[3]
      # Owned checkout only, never use a request-supplied module path.
      sys.path[:0] = [str(root), str(root / 'opendbc_repo'), str(Path(__file__).resolve().parent)]
      from worker_resources import apply_worker_limits
      apply_worker_limits()
      from native_protocol import MAX_REQUEST_BYTES, canonical
      from openpilot.tools.cyber_autotune.a1_experiment import decode_request, execute_experiment
      request = decode_request(sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1))
      with open(os.devnull, 'w') as quiet, contextlib.redirect_stdout(quiet):
        result = execute_experiment(request)
    sys.stdout.buffer.write(canonical(result) + b'\n')
    return 0
  except Exception:
    # Even a helper import failure has a fixed stdlib-only, privacy-safe receipt.
    sys.stdout.buffer.write(json.dumps({'status': 'REJECTED', 'code': 'INVALID_OR_FAILED_A1_REQUEST'}).encode() + b'\n')
    return 1
  finally:
    sys.pycache_prefix, sys.dont_write_bytecode = previous


if __name__ == '__main__':
  raise SystemExit(main())
