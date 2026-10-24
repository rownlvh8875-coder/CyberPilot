"""Fixed private native synthetic worker. Never invoked by onroad processes."""
import json
from pathlib import Path
import sys


def main():
  root = Path(__file__).resolve().parents[3]
  sys.path[:0] = [str(root), str(root / 'opendbc_repo')]
  from openpilot.tools.cyber_autotune.worker_resources import apply_worker_limits
  apply_worker_limits()
  from openpilot.tools.cyber_autotune.native_protocol import _unique_pairs, canonical
  from openpilot.tools.cyber_autotune.synthetic_native_v2 import run_batch
  from openpilot.tools.cyber_autotune.synthetic_pipeline import MAX_OUTPUT, source_binding, validate_arm, verify_worker_imports
  payload = sys.stdin.buffer.read(16385)
  if not 0 < len(payload) <= 16384:
    raise ValueError('INPUT_BOUND')
  request = json.loads(payload, object_pairs_hook=_unique_pairs)
  if type(request) is not dict or set(request) != {'tune_id', 'binding'}:
    raise ValueError('INVALID_REQUEST')
  before = source_binding()
  if before != request['binding']:
    raise ValueError('SOURCE_BINDING_MISMATCH')
  result = {'schema': 'synthetic-arm-v2', 'status': 'COMPLETED_SYNTHETIC_ONLY', 'tune_id': request['tune_id'],
            'binding': before, 'results': run_batch(request['tune_id']), 'vehicle_activation_allowed': False}
  verify_worker_imports()
  validate_arm(result, request['tune_id'], before)
  if source_binding() != before:
    raise ValueError('SOURCE_CHANGED')
  output = canonical(result)
  if len(output) > MAX_OUTPUT:
    raise ValueError('OUTPUT_BOUND')
  sys.stdout.buffer.write(output)
  return 0


if __name__ == '__main__':
  try:
    raise SystemExit(main())
  except Exception:
    # No raw exceptions, local paths, CP or partial traces cross this boundary.
    raise SystemExit(1) from None
