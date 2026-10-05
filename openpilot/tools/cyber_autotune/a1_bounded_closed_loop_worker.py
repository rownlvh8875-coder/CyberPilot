"""Fixed no-input worker for the bounded A1 synthetic hypothesis.

No arbitrary profile, Params, log, source path or vehicle input is accepted.
Trusted local code only; this is not a hostile-code sandbox or promotion authority.
"""
import contextlib
import json
import os
from pathlib import Path
import sys
import tempfile


def main():
  previous = sys.pycache_prefix, sys.dont_write_bytecode
  try:
    if len(sys.argv) != 1 or sys.stdin.buffer.read(1):
      raise ValueError('NO_EXTERNAL_INPUTS')
    with tempfile.TemporaryDirectory(prefix='cyber-a1-bounded-') as cache:
      sys.pycache_prefix, sys.dont_write_bytecode = cache, True
      root = Path(__file__).resolve().parents[3]
      sys.path[:0] = [str(root), str(root / 'opendbc_repo'), str(Path(__file__).resolve().parent)]
      from worker_resources import apply_worker_limits
      apply_worker_limits()
      from native_protocol import canonical
      from openpilot.tools.cyber_autotune.a1_bounded_closed_loop import run_matrix
      from openpilot.tools.cyber_autotune.a1_experiment import _verify_bindings, build_request
      from openpilot.tools.cyber_autotune.synthetic_native_v2 import frozen_policy
      from openpilot.tools.cyber_autotune.synthetic_pipeline import source_binding, verify_worker_imports
      with open(os.devnull, 'w') as quiet, contextlib.redirect_stdout(quiet):
        request = build_request('identity')
        _verify_bindings(request)
        before = source_binding()
        policy = frozen_policy()
        report = run_matrix()
        verify_worker_imports()
        _verify_bindings(request)
        if source_binding() != before or frozen_policy() != policy:
          raise ValueError('SOURCE_CHANGED_DURING_RUN')
        result = {
          'schema': 'a1-bounded-closed-loop-evidence-v1',
          'source_head': request['source']['head'],
          'opendbc_head': request['source']['opendbc_head'],
          'binding': before,
          'report': report,
          'vehicle_activation_allowed': False,
        }
        payload = canonical(result)
        if len(payload) > 4 * 1024 * 1024:
          raise ValueError('OUTPUT_BOUND')
    sys.stdout.buffer.write(payload + b'\n')
    return 0
  except Exception:
    sys.stdout.buffer.write(json.dumps({'status': 'REJECTED', 'code': 'INVALID_OR_FAILED_BOUNDED_A1'}).encode() + b'\n')
    return 1
  finally:
    sys.pycache_prefix, sys.dont_write_bytecode = previous


if __name__ == '__main__':
  raise SystemExit(main())
