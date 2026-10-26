import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from openpilot.tools.cyber_autotune.a1_experiment import build_request, make_fixture
from openpilot.tools.cyber_autotune.native_protocol import canonical
from openpilot.tools.cyber_autotune.native_runner import _run_process
from openpilot.tools.cyber_autotune.synthetic_native_v2 import _lateral_trace
from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog, frames


class TestA1ClosedLoop(unittest.TestCase):
  def api(self):
    try:
      return importlib.import_module('openpilot.tools.cyber_autotune.a1_closed_loop')
    except ModuleNotFoundError:
      self.fail('A1 closed-loop comparison not implemented')

  def fixture(self, variant):
    import base64
    from opendbc.car import structs
    native, table = make_fixture(build_request(variant))
    with structs.CarParams.from_bytes(base64.b64decode(native['car_params_base64'])) as cp:
      return cp.as_builder(), table

  def test_every_valid_identity_trace_matches_unchanged_v2_loop(self):
    api = self.api()
    cp, table = self.fixture('identity')
    original = cp.to_bytes()
    cp.clear_write_flag()  # permit a second serialization for the immutability assertion
    for case in catalog():
      if case.axis != 'lateral' or case.expected_input_status != 'VALID':
        continue
      rows = frames(case)
      for delay in case.physical_delays_s:
        with self.subTest(case=case.case_id, delay=delay):
          reference, config = _lateral_trace(case, rows, cp, 1., delay)
          for tune in (None, table):
            actual, actual_config, receipt = api._trace(case, rows, cp, tune, delay)
            self.assertEqual(canonical(actual), canonical(reference))
            self.assertEqual(config, actual_config)
            self.assertEqual(receipt['physical_delay_owner'], 'PLANT')
            self.assertFalse(receipt['controller_delay_queue_present'])
    self.assertEqual(cp.to_bytes(), original)

  def test_admitted_variants_change_own_plant_feedback(self):
    api = self.api()
    base = api.run_case('lat_speed_sweep', 'disabled', .03)
    for variant in ('factor', 'friction', 'combined'):
      result = api.run_case('lat_speed_sweep', variant, .03)
      self.assertEqual(result['status'], 'COMPLETED_SYNTHETIC_ONLY')
      self.assertNotEqual(base['metrics']['trace_sha256'], result['metrics']['trace_sha256'])
      self.assertNotEqual(base['receipt']['feedback_sha256'], result['receipt']['feedback_sha256'])
      self.assertEqual(base['input_sha256'], result['input_sha256'])
      self.assertEqual(base['plant_sha256'], result['plant_sha256'])
      self.assertEqual(base['base_car_params_sha256'], result['base_car_params_sha256'])

  def test_middle_speed_start_is_blocked_without_candidate_construction(self):
    api = self.api()
    for variant in ('factor', 'friction', 'combined'):
      result = api.run_case('lat_constant_left', variant, .03)
      self.assertEqual(result['status'], 'BLOCKED')
      self.assertEqual(result['reason'], 'A1_TRANSITION_EXCEEDED')
      self.assertIsNone(result['metrics'])
      self.assertFalse(result['controller_executed'])

  def test_invalid_inputs_reject_and_undeclared_inputs_raise(self):
    api = self.api()
    for case, reason in (('lat_nonfinite', 'NONFINITE_INPUT'), ('lat_out_of_order', 'INVALID_TIMEBASE'),
                         ('lat_sensor_dropout', 'INVALID_SENSOR')):
      result = api.run_case(case, 'combined', .03)
      self.assertEqual(result['status'], 'REJECTED_INPUT')
      self.assertEqual(result['reason'], reason)
      self.assertFalse(result['controller_executed'])
    for args in (('long_stopped_lead', 'identity', .03), ('lat_straight', 'custom', .03),
                 ('lat_straight', 'identity', True), ('lat_straight', 'identity', .031)):
      with self.assertRaises(ValueError):
        api.run_case(*args)

  def test_full_matrix_reports_missing_coverage_not_success(self):
    api = self.api()
    result = api.run_matrix()
    self.assertEqual(result['identity_parity'], 'PASS')
    self.assertEqual(result['case_delay_count'], 29)
    self.assertEqual(set(result['arms']), {'disabled', 'identity', 'factor', 'friction', 'combined'})
    for name, rows in result['arms'].items():
      self.assertEqual(len(rows), 29)
      self.assertEqual(sum(r['status'] == 'REJECTED_INPUT' for r in rows), 3)
      for row in rows:
        self.assertIs(row['vehicle_activation_allowed'], False)
      if name in ('factor', 'friction', 'combined'):
        self.assertEqual(result['comparisons'][name]['status'], 'REJECTED')
        self.assertIn('INCOMPLETE_VALID_COVERAGE', result['comparisons'][name]['reasons'])
    self.assertEqual(result['readiness'], 'NOT_READY')
    self.assertFalse(result['vehicle_activation_allowed'])
    self.assertEqual(result['deterministic_repeats'], 'NOT_CHECKED_IN_SINGLE_RUN')

  def test_worker_repeats_with_source_binding_and_rejects_external_input(self):
    api = self.api()
    worker = Path(api.__file__).with_name('a1_closed_loop_worker.py')
    self.assertTrue(worker.is_file(), 'bounded A1 closed-loop worker not implemented')
    command = [sys.executable, '-I', str(worker)]
    first = _run_process(command, b'', 60.)
    second = _run_process(command, b'', 60.)
    self.assertEqual(first.returncode, 0, first.stdout)
    self.assertEqual(second.returncode, 0, second.stdout)
    self.assertEqual(first.stdout, second.stdout)
    result = json.loads(first.stdout)
    self.assertEqual(result['report']['identity_parity'], 'PASS')
    self.assertEqual(len(result['source_head']), 40)
    self.assertGreater(result['binding']['file_count'], 100)
    self.assertFalse(result['vehicle_activation_allowed'])
    for args, payload in ((command, b'PRIVATE_A1_INPUT'), (command + ['PRIVATE_A1_ARG'], b'')):
      rejected = _run_process(args, payload, 10.)
      self.assertEqual(rejected.returncode, 1)
      self.assertEqual(json.loads(rejected.stdout), {'status': 'REJECTED', 'code': 'INVALID_OR_FAILED_A1_CLOSED_LOOP'})
      self.assertNotIn(b'PRIVATE_A1', rejected.stdout)

  def test_policy_mutation_after_run_rejects_receipt(self):
    api = self.api()
    from openpilot.tools.cyber_autotune import synthetic_native_v2
    with tempfile.TemporaryDirectory() as directory:
      policy = Path(directory) / 'policy.json'
      policy.write_bytes(synthetic_native_v2.POLICY_PATH.read_bytes())
      # Real isolated child avoids loading the test runner's unbound namespace
      # modules into the worker. Mutate only a temporary policy copy, after the
      # real native matrix; no worker/resource/hash checker is mocked.
      script = '''
import sys
from pathlib import Path
root, policy = Path(sys.argv[1]), Path(sys.argv[2])
sys.pycache_prefix, sys.dont_write_bytecode = str(policy.parent / 'empty-cache'), True
sys.path[:0] = [str(root), str(root / 'opendbc_repo')]
from openpilot.tools.cyber_autotune import a1_closed_loop, a1_closed_loop_worker, synthetic_native_v2
synthetic_native_v2.POLICY_PATH = policy
original = a1_closed_loop.run_matrix
def run_then_mutate():
  result = original()
  policy.write_bytes(b'{"PRIVATE_POLICY_MUTATION":true}')
  return result
a1_closed_loop.run_matrix = run_then_mutate
sys.argv = ['a1_closed_loop_worker.py']
raise SystemExit(a1_closed_loop_worker.main())
'''
      result = _run_process([sys.executable, '-I', '-c', script, str(Path(api.__file__).resolve().parents[3]), str(policy)], b'', 60.)
      self.assertEqual(result.returncode, 1)
      self.assertEqual(json.loads(result.stdout), {'status': 'REJECTED', 'code': 'INVALID_OR_FAILED_A1_CLOSED_LOOP'})
      self.assertNotIn(b'PRIVATE_POLICY_MUTATION', result.stdout)


if __name__ == '__main__':
  unittest.main()
