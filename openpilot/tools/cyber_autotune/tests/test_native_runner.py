import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune.native_protocol import encode_request
from openpilot.tools.cyber_autotune.native_runner import _run_process, run_native, validate_response
from openpilot.tools.cyber_autotune.tests.test_native_worker import fixture


class TestOwnedProcess(unittest.TestCase):
  def test_exit_and_nonzero_are_preserved(self):
    result = _run_process([sys.executable, '-c', 'print("ok")'], b'', 5.)
    self.assertEqual((result.status, result.returncode, result.stdout), ('EXITED', 0, b'ok\n'))
    result = _run_process([sys.executable, '-c', 'import sys; print("private", file=sys.stderr); sys.exit(3)'], b'', 5.)
    self.assertEqual((result.status, result.returncode, result.stdout), ('EXITED', 3, b''))

  def test_timeout_reaps_owned_process_without_touching_unrelated(self):
    unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'], start_new_session=True)
    try:
      result = _run_process([sys.executable, '-c', 'import time; time.sleep(10)'], b'', .1)
      self.assertEqual(result.status, 'TIMEOUT')
      self.assertIsNotNone(result.returncode)
      with self.assertRaises(ProcessLookupError):
        os.kill(result.pid, 0)
      self.assertIsNone(unrelated.poll())
    finally:
      unrelated.kill()
      unrelated.wait(timeout=3)

  def test_timeout_terminates_owned_descendant(self):
    code = ('import subprocess,sys,time; ' +
            'child=subprocess.Popen([sys.executable,"-c","import time; time.sleep(10)"]); ' +
            'print(child.pid,flush=True); time.sleep(10)')
    result = _run_process([sys.executable, '-c', code], b'', .3)
    self.assertEqual(result.status, 'TIMEOUT')
    child_pid = int(result.stdout.strip())
    stat = Path(f'/proc/{child_pid}/stat')
    # A descendant may briefly remain a reparented zombie; it must not be executing.
    self.assertTrue(not stat.exists() or stat.read_text().split(') ')[1].startswith('Z'))

  def test_interruption_cleans_owned_process(self):
    actual = subprocess.Popen.communicate
    children = []

    def interrupt_once(process, *args, **kwargs):
      if not children:
        children.append(process.pid)
        raise KeyboardInterrupt
      return actual(process, *args, **kwargs)

    with patch.object(subprocess.Popen, 'communicate', interrupt_once), self.assertRaises(KeyboardInterrupt):
      _run_process([sys.executable, '-c', 'import time; time.sleep(10)'], b'', 5.)
    with self.assertRaises(ProcessLookupError):
      os.kill(children[0], 0)


class TestNativeRunner(unittest.TestCase):
  def test_real_native_process_repeatability(self):
    request = fixture()
    for frame in request['frames']:
      frame['desired_curvature_1pm'] = .001
    original = copy.deepcopy(request)
    first = run_native(request, timeout_s=10.)
    second = run_native(request, timeout_s=10.)
    self.assertEqual(first['status'], 'COMPLETED')
    self.assertEqual(first, second)
    self.assertEqual(request, original)
    self.assertTrue(any(row['requested_torque'] < 0 for row in first['samples']))
    self.assertFalse(first['runtime_accepted'])
    self.assertFalse(first['promotable'])

  def test_bad_request_timeout_and_source_fail_without_native_success(self):
    request = fixture()
    for timeout in (0, -1, True, float('inf'), 61):
      with self.subTest(timeout=timeout), self.assertRaises(ValueError):
        run_native(request, timeout_s=timeout)
    with self.assertRaises(ValueError):
      run_native({}, timeout_s=1.)
    request['source']['head'] = '0' * 40
    result = run_native(request, timeout_s=10.)
    self.assertEqual(result['status'], 'WORKER_FAILED')
    self.assertNotIn('samples', result)
    self.assertFalse(result['promotable'])

  def test_stale_binding_tampered_trace_and_invalid_output_rejected(self):
    request = fixture()
    result = run_native(request, timeout_s=10.)
    self.assertEqual(result['status'], 'COMPLETED')
    for key, value in (('request_sha256', '0' * 64), ('source_head', '0' * 40),
                       ('car_params_sha256', '0' * 64), ('ordered_trace_sha256', '0' * 64),
                       ('runtime_accepted', True), ('promotable', 0), ('scope', 'SHADOW_READY')):
      with self.subTest(key=key), self.assertRaises(ValueError):
        validate_response(request, dict(result, **{key: value}))
    for key, value in (('time_ns', 1), ('time_ns', False), ('requested_torque', 2),
                       ('requested_torque', True), ('estimated_curvature_1pm', float('nan'))):
      changed = copy.deepcopy(result)
      changed['samples'][0][key] = value
      with self.subTest(key=key, value=value), self.assertRaises(ValueError):
        validate_response(request, changed)
    with self.assertRaises(ValueError):
      validate_response(request, dict(result, samples=result['samples'][:-1]))

  def test_nonzero_and_malformed_worker_results_never_complete(self):
    request = fixture()
    # Controlled real child output exercises parsing/failure mapping without
    # introducing test-only worker switches into production.
    def child_result(body):
      return _run_process([sys.executable, '-c', body], b'', 5.)

    for body, expected in (('print("not JSON")', 'INVALID_RESPONSE'),
                           ('print(\'{"status":"COMPLETED","status":"COMPLETED"}\')', 'INVALID_RESPONSE'),
                           ('import sys; sys.exit(3)', 'WORKER_FAILED')):
      observed = child_result(body)
      with patch('openpilot.tools.cyber_autotune.native_runner._run_process', return_value=observed):
        result = run_native(request, timeout_s=10.)
      self.assertEqual(result['status'], expected)
      self.assertNotIn('samples', result)
      self.assertEqual(result['request_sha256'], hashlib.sha256(encode_request(request)).hexdigest())

  def test_cli_rejects_private_invalid_input_without_echo(self):
    worker = Path(__file__).resolve().parents[1] / 'native_worker.py'
    result = _run_process([sys.executable, '-I', str(worker)], b'{"secret":"PRIVATE_INPUT_SENTINEL"}', 10.)
    self.assertEqual(result.returncode, 1)
    self.assertNotIn(b'PRIVATE_INPUT_SENTINEL', result.stdout)
    self.assertEqual(json.loads(result.stdout)['status'], 'REJECTED')


if __name__ == '__main__':
  unittest.main()
