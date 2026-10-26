import importlib
import importlib.util
from dataclasses import asdict
import json
import unittest

from openpilot.tools.cyber_autotune import a1_closed_loop as original
from openpilot.tools.cyber_autotune.a1_experiment import BASELINE_FACTOR, BASELINE_FRICTION, build_request, make_fixture
from openpilot.tools.cyber_autotune.a1_schedule import MAX_FRAME_DELTAS, prepare_schedule
from openpilot.tools.cyber_autotune.native_protocol import canonical
from openpilot.tools.cyber_autotune.synthetic_native_v2 import POLICY_SHA256
from openpilot.tools.cyber_autotune.synthetic_pipeline import AUTHORITY
from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog, frames


class TestA1BoundedClosedLoop(unittest.TestCase):
  def api(self):
    name = 'openpilot.tools.cyber_autotune.a1_bounded_closed_loop'
    self.assertIsNotNone(importlib.util.find_spec(name), 'Bounded A1 candidate experiment not implemented')
    return importlib.import_module(name)

  def test_scale_and_tables_are_predeclared_and_schedule_admits_every_valid_case(self):
    api = self.api()
    self.assertEqual(api.BOUNDED_SCALE, .5)
    expected = {
      'bounded_factor': ((0., 0.), (1 / 128, 0.), (1 / 64, 0.), (0., 0.)),
      'bounded_friction': ((0., 0.), (0., 1 / 2048), (0., 1 / 1024), (0., 0.)),
      'bounded_combined': ((0., 0.), (1 / 128, 1 / 2048), (1 / 64, 1 / 1024), (0., 0.)),
    }
    for arm, offsets in expected.items():
      table = api.bounded_table(arm)
      self.assertEqual(tuple((p.lat_accel_factor - BASELINE_FACTOR, p.friction - BASELINE_FRICTION) for p in table.points), offsets)
      for case in catalog():
        if case.axis != 'lateral' or case.expected_input_status != 'VALID':
          continue
        schedule = prepare_schedule(table, tuple(row.speed_mps for row in frames(case)), BASELINE_FACTOR, BASELINE_FRICTION)
        self.assertEqual(len(schedule), len(frames(case)))
        prior = (BASELINE_FACTOR, BASELINE_FRICTION)
        for row in schedule:
          effective = row[3:5]
          self.assertLessEqual(abs(effective[0] - prior[0]), MAX_FRAME_DELTAS[0])
          self.assertLessEqual(abs(effective[1] - prior[1]), MAX_FRAME_DELTAS[1])
          prior = effective

  def test_full_matrix_has_complete_valid_coverage_without_changing_policy(self):
    api = self.api()
    result = api.run_matrix()
    self.assertEqual(result['schema'], 'a1-bounded-generic-closed-loop-v1')
    self.assertEqual(result['policy_sha256'], POLICY_SHA256)
    self.assertEqual(result['case_delay_count'], 29)
    self.assertEqual(set(result['arms']), {'baseline', *api.CANDIDATES})
    self.assertEqual(result['bounded_scale'], .5)
    for _name, rows in result['arms'].items():
      self.assertEqual(len(rows), 29)
      self.assertEqual(sum(row['status'] == 'REJECTED_INPUT' for row in rows), 3)
      self.assertEqual(sum(row['status'] == 'BLOCKED' for row in rows), 0)
      self.assertEqual(sum(row['status'] == 'COMPLETED_SYNTHETIC_ONLY' for row in rows), 26)
      for row in rows:
        self.assertFalse(row['vehicle_activation_allowed'])
        self.assertTrue(all(row[key] is False for key in AUTHORITY))
    for name in api.CANDIDATES:
      self.assertIn(result['comparisons'][name]['status'], ('REJECTED', 'PASS_SYNTHETIC_ONLY'))
      if result['comparisons'][name]['status'] == 'PASS_SYNTHETIC_ONLY':
        self.assertEqual(result['comparisons'][name]['reasons'], [])
    self.assertFalse(result['vehicle_activation_allowed'])
    self.assertEqual(result['readiness'], 'NOT_READY')

  def test_baseline_is_existing_disabled_arm_and_old_candidates_remain_blocked(self):
    api = self.api()
    result = api.run_matrix()
    expected = [original.run_case(case.case_id, 'disabled', delay)
                for case in catalog() if case.axis == 'lateral' for delay in case.physical_delays_s]
    self.assertEqual(canonical(result['arms']['baseline']), canonical(expected))
    for fixture in ('factor', 'friction', 'combined'):
      blocked = original.run_case('lat_constant_left', fixture, .03)
      self.assertEqual(blocked['status'], 'BLOCKED')
      self.assertEqual(blocked['reason'], 'A1_TRANSITION_EXCEEDED')
      self.assertFalse(blocked['controller_executed'])

  def test_candidates_are_not_noops_and_do_not_mutate_existing_fixture(self):
    api = self.api()
    _, old_table = make_fixture(build_request('combined'))
    old = canonical(asdict(old_table))
    result = api.run_matrix()
    for name in api.CANDIDATES:
      changed = [row for base, row in zip(result['arms']['baseline'], result['arms'][name], strict=True)
                 if row['metrics'] is not None and base['metrics']['trace_sha256'] != row['metrics']['trace_sha256']]
      self.assertTrue(changed, name)
    _, after = make_fixture(build_request('combined'))
    self.assertEqual(canonical(asdict(after)), old)

  def test_report_is_sanitized_and_has_no_vehicle_authority(self):
    api = self.api()
    result = api.run_matrix()
    encoded = canonical(result)
    for forbidden in (b'car_params_base64', b'"frames"', b'"samples"', b'"snapshot"', str(api.ROOT).encode()):
      self.assertNotIn(forbidden, encoded)
    self.assertNotIn(': "accepted"', json.dumps(result).lower())
    self.assertFalse(result['vehicle_activation_allowed'])
    self.assertTrue(all(result[key] is False for key in AUTHORITY))

  def test_worker_repeats_and_rejects_external_input(self):
    api = self.api()
    from pathlib import Path
    import sys
    from openpilot.tools.cyber_autotune.native_runner import _run_process

    worker = Path(api.__file__).with_name('a1_bounded_closed_loop_worker.py')
    self.assertTrue(worker.is_file(), 'bounded A1 worker not implemented')
    command = [sys.executable, '-I', str(worker)]
    first = _run_process(command, b'', 90.)
    second = _run_process(command, b'', 90.)
    self.assertEqual(first.returncode, 0, first.stdout)
    self.assertEqual(second.returncode, 0, second.stdout)
    self.assertEqual(first.stdout, second.stdout)
    report = json.loads(first.stdout)
    self.assertEqual(report['report']['case_delay_count'], 29)
    self.assertEqual(report['report']['bounded_scale'], .5)
    self.assertFalse(report['vehicle_activation_allowed'])
    for args, payload in ((command, b'PRIVATE_A1_INPUT'), (command + ['PRIVATE_A1_ARG'], b'')):
      rejected = _run_process(args, payload, 10.)
      self.assertEqual(rejected.returncode, 1)
      self.assertEqual(json.loads(rejected.stdout), {'status': 'REJECTED', 'code': 'INVALID_OR_FAILED_BOUNDED_A1'})
      self.assertNotIn(b'PRIVATE_A1', rejected.stdout)


if __name__ == '__main__':
  unittest.main()
