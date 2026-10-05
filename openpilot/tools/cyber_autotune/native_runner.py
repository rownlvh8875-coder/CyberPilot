"""Blocking OFFLINE supervisor. Never invoke on an active control-loop thread.

Fixed trusted worker/source only, not a security sandbox. Request and trace counts
are capped; subprocess capture is not an adversarial memory/disk resource boundary.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from openpilot.tools.cyber_autotune.native_protocol import _unique_pairs, canonical, digest, encode_request, finite


MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_TIMEOUT_S = 60.
# Resource bounds for kernel exit confirmation, not control/vehicle tolerances.
CLEANUP_TIMEOUT_S = 1.
CLEANUP_POLL_S = .001
PROC_ROOT = Path('/proc')


@dataclass(frozen=True)
class ProcessOutcome:
  status: str
  returncode: int
  stdout: bytes
  pid: int


def _kill_owned_group(process):
  try:
    os.killpg(process.pid, signal.SIGKILL)
  except ProcessLookupError:
    pass


def _owned_group_running(pgid):
  for entry in PROC_ROOT.iterdir():
    if not entry.name.isdecimal():
      continue
    try:
      if os.getpgid(int(entry.name)) != pgid:
        continue
      fields = (entry / 'stat').read_text().rsplit(') ', 1)[1].split()
      # Check membership again: disappearance/reuse can race the first lookup.
      # Linux /proc state Z is zombie; X/x are dead terminal states.
      if int(fields[2]) == pgid and fields[0] not in ('Z', 'X', 'x'):
        return True
    except (ProcessLookupError, FileNotFoundError):
      continue
    except (IndexError, ValueError) as error:
      raise OSError('OWNED_GROUP_STATE_UNREADABLE') from error
  return False


def _wait_owned_group_exit(pgid):
  deadline = time.monotonic() + CLEANUP_TIMEOUT_S
  while _owned_group_running(pgid):
    if time.monotonic() >= deadline:
      raise TimeoutError('OWNED_GROUP_EXIT_UNCONFIRMED')
    time.sleep(CLEANUP_POLL_S)


def _terminate_owned_group(process):
  _kill_owned_group(process)
  stdout, _ = process.communicate()
  # Pipe EOF/direct-child wait can precede descendant kernel FD teardown.
  _wait_owned_group_exit(process.pid)
  return stdout


def _run_process(argv, payload, timeout_s):
  """Private lifecycle helper; public API never exposes arbitrary command argv."""
  process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)
  try:
    stdout, _ = process.communicate(payload, timeout=timeout_s)
    return ProcessOutcome('EXITED', process.returncode, stdout, process.pid)
  except subprocess.TimeoutExpired:
    stdout = _terminate_owned_group(process)
    return ProcessOutcome('TIMEOUT', process.returncode, stdout, process.pid)
  except BaseException:
    _terminate_owned_group(process)
    raise
  finally:
    for stream in (process.stdin, process.stdout):
      if stream is not None:
        stream.close()


def validate_response(request: dict, result: dict) -> None:
  expected = {'status', 'scope', 'request_sha256', 'source_head', 'opendbc_head',
              'car_params_sha256', 'samples', 'ordered_trace_sha256', 'runtime_accepted', 'promotable'}
  if type(result) is not dict or set(result) != expected:
    raise ValueError('INVALID_RESPONSE_FIELDS')
  bindings = {
    'status': 'COMPLETED', 'scope': 'OFFLINE_NATIVE_REQUESTED_TORQUE',
    'request_sha256': digest(encode_request(request)), 'source_head': request['source']['head'],
    'opendbc_head': request['source']['opendbc_head'], 'car_params_sha256': request['car_params_sha256'],
  }
  if any(type(result[key]) is not str or result[key] != value for key, value in bindings.items()):
    raise ValueError('RESPONSE_BINDING_MISMATCH')
  if result['runtime_accepted'] is not False or result['promotable'] is not False:
    raise ValueError('INVALID_RESPONSE_AUTHORITY')
  samples = result['samples']
  if type(samples) is not list or len(samples) != len(request['frames']):
    raise ValueError('INVALID_SAMPLE_COUNT')
  for frame, row in zip(request['frames'], samples, strict=True):
    if type(row) is not dict or set(row) != {'time_ns', 'requested_torque', 'estimated_curvature_1pm'}:
      raise ValueError('INVALID_SAMPLE_FIELDS')
    if type(row['time_ns']) is not int or row['time_ns'] != frame['time_ns']:
      raise ValueError('OUTPUT_TIME_MISMATCH')
    if not finite(row['requested_torque']) or abs(row['requested_torque']) > 1 or not finite(row['estimated_curvature_1pm']):
      raise ValueError('INVALID_NATIVE_SAMPLE')
  if result['ordered_trace_sha256'] != digest(canonical(samples)):
    raise ValueError('TRACE_DIGEST_MISMATCH')


def run_native(request: dict, *, timeout_s: float) -> dict:
  if not finite(timeout_s) or not 0 < timeout_s <= MAX_TIMEOUT_S:
    raise ValueError('INVALID_TIMEOUT')
  payload = encode_request(request)
  # Copy input before launch so an unrelated caller mutation cannot rebind output.
  request = json.loads(payload)

  def failure(status):
    return {'status': status, 'request_sha256': digest(payload), 'runtime_accepted': False, 'promotable': False}

  if sys.platform != 'linux':
    return failure('UNSUPPORTED_PLATFORM')
  worker = Path(__file__).resolve().with_name('native_worker.py')
  try:
    observed = _run_process([sys.executable, '-I', str(worker)], payload, timeout_s)
  except OSError:
    return failure('WORKER_UNAVAILABLE')
  if observed.status == 'TIMEOUT':
    return failure('TIMEOUT')
  if observed.status != 'EXITED' or observed.returncode != 0:
    return failure('WORKER_FAILED')
  if not 0 < len(observed.stdout) <= MAX_RESPONSE_BYTES:
    return failure('INVALID_RESPONSE')
  try:
    result = json.loads(observed.stdout, object_pairs_hook=_unique_pairs)
    validate_response(request, result)
  except (ValueError, UnicodeError, RecursionError):
    return failure('INVALID_RESPONSE')
  return result
