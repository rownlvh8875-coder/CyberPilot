import copy
import importlib
import json
from pathlib import Path
import py_compile
import sys
import tempfile
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.native_runner import _run_process, validate_response as validate_v1
from openpilot.tools.cyber_autotune.native_worker import execute_request


class TestA1Experiment(unittest.TestCase):
  def api(self):
    try:
      return importlib.import_module('openpilot.tools.cyber_autotune.a1_experiment')
    except ModuleNotFoundError:
      self.fail('A1 synthetic native experiment is not implemented')

  def test_disabled_identity_exact_native_and_state_parity(self):
    api = self.api()
    for fixture in ('disabled', 'identity'):
      request = api.build_request(fixture)
      result = api.execute_experiment(request)
      self.assertEqual(result['baseline'], result['candidate'])
      native, _ = api.make_fixture(request)
      original = execute_request(native)
      baseline = dict(result['baseline'])
      del baseline['a1']
      validate_v1(native, baseline)
      self.assertEqual(original, baseline)
      self.assertEqual(result['status'], 'SOFTWARE_NATIVE_A1_INTEGRATION_PASS')
      self.assertFalse(result['vehicle_authority'])

  def test_real_parameter_application_non_noop_and_history(self):
    api = self.api()
    for fixture in ('factor', 'friction', 'combined'):
      request = api.build_request(fixture)
      native, _ = api.make_fixture(request)
      cp_before = native['car_params_sha256']
      result = api.execute_experiment(request)
      baseline, candidate = result['baseline'], result['candidate']
      self.assertNotEqual(baseline['ordered_trace_sha256'], candidate['ordered_trace_sha256'])
      self.assertEqual(baseline['car_params_sha256'], cp_before)
      self.assertEqual(candidate['car_params_sha256'], cp_before)
      records = candidate['a1']['states']
      self.assertEqual(len(records), 601)
      self.assertEqual(records[200]['factor'], 4.03125 if fixture != 'friction' else 4.)
      self.assertEqual(records[200]['friction'], .126953125 if fixture != 'factor' else .125)
      history = [0.] * 100
      for index, (row, frame) in enumerate(zip(records, native['frames'], strict=True)):
        # Independently derive retained history: resetting at a speed knot fails.
        from openpilot.tools.cyber_autotune.a1_schedule import float32
        history.append(frame['desired_curvature_1pm'] * float32(frame['speed_mps']) ** 2)
        history = history[-100:]
        self.assertEqual(row['history_sha256'], digest(canonical(history)))
        if not frame['active']:
          self.assertEqual(candidate['samples'][index]['requested_torque'], 0.)
        if index and (not frame['active'] or frame['safety_limited'] or frame['steering_pressed'] or frame['speed_mps'] < 5):
          self.assertEqual(row['pid_i'], records[index - 1]['pid_i'])
      self.assertEqual(candidate['a1']['invariants_sha256'], baseline['a1']['invariants_sha256'])

  def test_fresh_process_reports_repeat_and_never_grant_authority(self):
    api = self.api()
    for fixture in ('disabled', 'identity', 'factor', 'friction', 'combined'):
      request = api.build_request(fixture)
      first = api.run_experiment(request, timeout_s=20.)
      second = api.run_experiment(request, timeout_s=20.)
      self.assertEqual(first['status'], 'SOFTWARE_NATIVE_A1_INTEGRATION_PASS', first)
      self.assertEqual(first, second)
      for name in ('runtime_accepted', 'promotable', 'vehicle_authority', 'profile_authority', 'can_authority'):
        self.assertIs(first[name], False)
      self.assertEqual(first['unavailable_metrics'], ['center_deviation', 'lane_edge_margin', 'physical_steering_jerk'])

  def test_request_rejects_unowned_inputs_duplicate_fields_and_stale_bindings(self):
    api = self.api()
    request = api.build_request('combined')
    for change in ({'fixture': 'real'}, {'version': True}, {'frames': []}, {'qualified': True}):
      with self.subTest(change=change), self.assertRaises(ValueError):
        api.encode_request(dict(request, **change))
    for payload in (b'{"fixture":"identity","fixture":"identity"}', b'{"version":NaN}', b'[]', b'{}'):
      with self.assertRaises(ValueError):
        api.decode_request(payload)
    for target in ('source', 'overlay'):
      changed = copy.deepcopy(request)
      files = changed[target]['files'] if target == 'source' else changed[target]
      files[next(iter(files))] = '0' * 64
      self.assertEqual(api.run_experiment(changed, timeout_s=20.)['status'], 'WORKER_FAILED')

  def test_corrupt_response_cannot_become_success(self):
    api = self.api()
    request = api.build_request('combined')
    result = api.execute_experiment(request)
    for key, value in (('request_sha256', '0' * 64), ('vehicle_authority', True), ('profile_authority', 0),
                       ('fixture', 'identity'), ('status', 'READY_FOR_SHADOW')):
      with self.subTest(key=key), self.assertRaises(ValueError):
        api.validate_response(request, dict(result, **{key: value}))
    for target in ('car_params_sha256', 'ordered_trace_sha256'):
      changed = copy.deepcopy(result)
      changed['candidate'][target] = '0' * 64
      with self.assertRaises(ValueError):
        api.validate_response(request, changed)
    changed = copy.deepcopy(result)
    changed['candidate']['a1']['states'][10]['factor'] = 100.
    with self.assertRaises(ValueError):
      api.validate_response(request, changed)

  def test_worker_failure_timeout_and_private_input_not_echoed(self):
    api = self.api()
    request = api.build_request('identity')
    for body, status in (('print("invalid")', 'INVALID_RESPONSE'), ('raise SystemExit(3)', 'WORKER_FAILED'),
                         ('print(\'{"status":"x","status":"x"}\')', 'INVALID_RESPONSE')):
      observed = _run_process([sys.executable, '-c', body], b'', 5.)
      with patch.object(api, '_run_process', return_value=observed):
        result = api.run_experiment(request, timeout_s=10.)
      self.assertEqual(result['status'], status)
      self.assertNotIn('candidate', result)
    self.assertEqual(api.run_experiment(request, timeout_s=.000001)['status'], 'TIMEOUT')
    worker = Path(api.__file__).with_name('a1_worker.py')
    bad = _run_process([sys.executable, '-I', str(worker)], b'{"secret":"PRIVATE_A1_SENTINEL"}', 10.)
    self.assertEqual(bad.returncode, 1)
    self.assertNotIn(b'PRIVATE_A1_SENTINEL', bad.stdout)
    self.assertEqual(json.loads(bad.stdout)['status'], 'REJECTED')

  def test_bootstrap_helpers_ignore_stale_bytecode(self):
    api = self.api()
    # Real isolated worker with stale copies, never poison the working checkout.
    source = Path(api.__file__).parent
    for helper in ('native_protocol.py', 'source_imports.py', 'worker_resources.py'):
      with self.subTest(helper=helper), tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / 'openpilot' / 'tools' / 'cyber_autotune'
        root.mkdir(parents=True)
        for name in ('a1_worker.py', 'native_protocol.py', 'source_imports.py', 'worker_resources.py'):
          (root / name).write_bytes((source / name).read_bytes())
        poisoned = root / helper
        clean = poisoned.read_bytes()
        poisoned.write_bytes(clean + b'\nprint("STALE_A1_BOOTSTRAP")\n')
        py_compile.compile(str(poisoned), doraise=True, invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
        poisoned.write_bytes(clean)
        result = _run_process([sys.executable, '-I', str(root / 'a1_worker.py')], b'{}', 5.)
        self.assertNotIn(b'STALE_A1_BOOTSTRAP', result.stdout)
        self.assertEqual(json.loads(result.stdout)['status'], 'REJECTED')


class TestA1FailureTransport(unittest.TestCase):
  def setUp(self):
    from openpilot.tools.cyber_autotune import a1_experiment
    self.api = a1_experiment
    self.request = self.api.build_request('identity')

  def check_failure(self, result, status, returncode):
    self.assertEqual(result, {
      'status': status, 'worker_returncode': returncode,
      'request_sha256': digest(self.api.encode_request(self.request)),
      **dict.fromkeys(self.api.AUTHORITIES, False),
    })

  def test_real_exit_codes_are_retained_without_child_output(self):
    for code, status in ((0, 'INVALID_RESPONSE'), (7, 'WORKER_FAILED')):
      with self.subTest(code=code):
        body = f'print("PRIVATE_A1_TRANSPORT_SENTINEL"); raise SystemExit({code})'
        observed = _run_process([sys.executable, '-c', body], b'', 5.)
        self.assertEqual((observed.status, observed.returncode), ('EXITED', code))
        with patch.object(self.api, '_run_process', return_value=observed):
          result = self.api.run_experiment(self.request, timeout_s=5.)
        self.check_failure(result, status, code)

  def test_real_signal_exit_is_retained(self):
    import signal
    observed = _run_process([sys.executable, '-c',
                             'import os, signal; os.kill(os.getpid(), signal.SIGTERM)'], b'', 5.)
    self.assertEqual((observed.status, observed.returncode), ('EXITED', -signal.SIGTERM))
    with patch.object(self.api, '_run_process', return_value=observed):
      result = self.api.run_experiment(self.request, timeout_s=5.)
    self.check_failure(result, 'WORKER_FAILED', -signal.SIGTERM)

  def test_timeout_keeps_status_and_observed_cleanup_returncode(self):
    observed = _run_process([sys.executable, '-c', 'import time; time.sleep(30)'], b'', .1)
    self.assertEqual(observed.status, 'TIMEOUT')
    self.assertIs(type(observed.returncode), int)
    with patch.object(self.api, '_run_process', return_value=observed):
      result = self.api.run_experiment(self.request, timeout_s=5.)
    self.check_failure(result, 'TIMEOUT', observed.returncode)

  def test_unobserved_returncode_is_null_without_exception_details(self):
    with patch.object(self.api.sys, 'platform', 'unsupported'), \
         patch.object(self.api, '_run_process', side_effect=AssertionError('must not launch')):
      result = self.api.run_experiment(self.request, timeout_s=5.)
    self.check_failure(result, 'UNSUPPORTED_PLATFORM', None)
    with patch.object(self.api, '_run_process', side_effect=OSError('PRIVATE_A1_TRANSPORT_SENTINEL')):
      result = self.api.run_experiment(self.request, timeout_s=5.)
    self.check_failure(result, 'WORKER_UNAVAILABLE', None)

  def test_invalid_zero_exit_responses_remain_failures(self):
    from openpilot.tools.cyber_autotune.native_runner import ProcessOutcome
    payloads = (b'', b'[]', b'{"status":"x","status":"x"}', b'{"vehicle_authority":true}',
                b'X' * (self.api.MAX_RESPONSE_BYTES + 1))
    for index, payload in enumerate(payloads):
      with self.subTest(case=index):
        observed = ProcessOutcome('EXITED', 0, payload, 0)
        with patch.object(self.api, '_run_process', return_value=observed):
          result = self.api.run_experiment(self.request, timeout_s=5.)
        self.check_failure(result, 'INVALID_RESPONSE', 0)


if __name__ == '__main__':
  unittest.main()
