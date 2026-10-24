"""OFFLINE input-only namespace coordinator. No decoder, learner or replay."""
import hashlib
import json
from pathlib import Path

from openpilot.tools.cyber_autotune.native_protocol import _unique_pairs
from openpilot.tools.cyber_autotune.replay_input import _sealed_bytes, retain_replay_input
from openpilot.tools.cyber_autotune.replay_supervisor import _run_bounded, MAX_TIMEOUT_S


MAX_ASSET_BYTES = 256 * 1024
MAX_PROBE_OUTPUT_BYTES = 16 * 1024


def _asset(name):
  with Path(__file__).with_name(name).open('rb') as stream:
    data = stream.read(MAX_ASSET_BYTES + 1)
  if not 0 < len(data) <= MAX_ASSET_BYTES:
    raise ValueError('INVALID_LAUNCHER_ASSET')
  return data


def run_input_probe(request, *, grants, authority_sha256, timeout_s):
  """Return aggregate evidence about an admitted, retained input only.

Trusted local grant/source and shipped launcher assets; not an adversarial-code
sandbox. Initial-state hashes are opaque request binding, not CP/cache validation.
Never publishes captured child output. Unknown child response fails closed.
"""
  if type(timeout_s) not in (float, int) or not 0 < timeout_s <= MAX_TIMEOUT_S:
    raise ValueError('INVALID_RESOURCE_LIMIT')
  with retain_replay_input(request, grants=grants, authority_sha256=authority_sha256) as (input_fd, receipt):
    result = dict(receipt, status='ISOLATED_INPUT_CHECK_FAILED', replay_executed=False)
    try:
      launcher = _asset('replay_input_namespace.sh')
      worker = _asset('replay_input_worker.py')
      with _sealed_bytes(launcher) as launcher_fd, _sealed_bytes(worker) as worker_fd:
        outcome = _run_bounded([
          '/usr/bin/unshare', '--user', '--map-root-user', '--mount', '--pid', '--fork', '--kill-child=KILL', '--net', '--ipc',
          '/usr/bin/bash', f'/proc/self/fd/{launcher_fd}', str(input_fd), str(worker_fd),
          str(receipt['input_size_bytes']), receipt['input_sha256'],
        ], timeout_s=timeout_s, max_output_bytes=MAX_PROBE_OUTPUT_BYTES,
          pass_fds=(input_fd, launcher_fd, worker_fd), env={'PATH': '/usr/sbin:/usr/bin:/bin', 'LC_ALL': 'C'})
      if outcome.status == 'EXITED' and outcome.returncode == 0:
        response = json.loads(outcome.output, object_pairs_hook=_unique_pairs)
        expected = {'status': 'SEALED_INPUT_VERIFIED', 'sha256': receipt['input_sha256'],
                    'size_bytes': receipt['input_size_bytes'], 'seals': 15, 'isolation_checked': True,
                    'replay_executed': False, 'runtime_accepted': False, 'promotable': False}
        if (type(response) is dict and set(response) == set(expected) and
            all(type(response[k]) is type(v) and response[k] == v for k, v in expected.items())):
          result.update(status='ISOLATED_INPUT_VERIFIED', launcher_sha256=hashlib.sha256(launcher).hexdigest(),
                        worker_sha256=hashlib.sha256(worker).hexdigest())
    except (OSError, ValueError, UnicodeError, RecursionError):
      # Do not leak private filenames, raw output or exception chains into reports.
      pass
  # Context exit rechecks source before any result is returned.
  return result
