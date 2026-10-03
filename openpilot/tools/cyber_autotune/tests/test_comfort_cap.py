"""Offline positive-acceleration hypothesis; never vehicle qualification."""
from dataclasses import replace
import importlib
from pathlib import Path
import unittest
from unittest.mock import patch

from openpilot.selfdrive.controls.lib.cyber_long.types import LongContext, ParameterBinding, StockCandidate
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.selfdrive.controls.tests.test_cyber_long_feedback import simulate
from openpilot.selfdrive.controls.tests.test_cyber_long_integration import FixtureSubMaster, car_params


MODULE = 'openpilot.tools.cyber_autotune.comfort_cap'


def context():
  return LongContext((StockCandidate(2., 'lead0', False), StockCandidate(1.2, 'cruise', False)),
                     True, False, False, False, True, 1, 1, 1, 10., 0., 20., False, 'standard',
                     ParameterBinding(vehicle='SYNTHETIC_PARITY_ONLY'))


class TestComfortCap(unittest.TestCase):
  def implementation(self):
    self.assertIsNotNone(importlib.util.find_spec(MODULE), 'approved offline cap implementation is missing')
    return importlib.import_module(MODULE)

  def test_positive_cap_uses_stock_speed_envelope_without_mutating_inputs(self):
    module = self.implementation()
    data = context()
    self.assertAlmostEqual(module.positive_accel_cap(data), 1.14)
    self.assertEqual(data, context())
    for accel in (-2., 0., .5, 1.14):
      with self.subTest(accel=accel):
        self.assertIsNone(module.positive_accel_cap(replace(data, candidates=(StockCandidate(accel, 'lead0', False),))))

  def test_stop_override_reset_force_decel_and_invalid_data_cannot_create_cap(self):
    module = self.implementation()
    data = context()
    changes = ({'input_valid': False}, {'reset_state': True}, {'brake_pressed': True}, {'gas_pressed': True},
               {'long_active': False}, {'force_decel': True}, {'v_ego_mps': .2}, {'v_ego_mps': -1.},
               {'v_ego_mps': float('nan')}, {'a_ego_mps2': float('inf')}, {'input_valid': 1},
               {'candidates': ()}, {'candidates': (StockCandidate(float('nan'), 'lead0', False),)},
               {'candidates': (StockCandidate(2., 'lead0', False), StockCandidate(3., 'e2e', True))})
    for change in changes:
      with self.subTest(change=change):
        self.assertIsNone(module.positive_accel_cap(replace(data, **change)))

  def test_native_candidate_is_synthetic_only_and_disabled_by_default(self):
    module = self.implementation()
    cp = car_params()
    original = cp.to_bytes()
    cp.clear_write_flag()
    candidate = module.OfflineComfortPlanner(cp)
    stock = LongitudinalPlanner(cp)
    sm = FixtureSubMaster()
    sm['carState'].vEgo = 10.
    for _ in range(50):
      sm.advance()
      stock.update(sm)
      candidate.update(sm)
      self.assertEqual(stock.output_a_target, candidate.output_a_target)
      self.assertEqual(stock.output_should_stop, candidate.output_should_stop)
      self.assertEqual(stock.v_desired_filter.x, candidate.v_desired_filter.x)
    self.assertEqual(cp.to_bytes(), original)
    cp.carFingerprint = 'HYUNDAI_SANTA_FE_2022'
    with self.assertRaises(ValueError):
      module.OfflineComfortPlanner(cp, experiment_enabled=True)
    with self.assertRaises(ValueError):
      module.OfflineComfortPlanner(car_params(), experiment_enabled=1)

  def test_native_cap_changes_feedback_before_next_mpc_and_repeated_input_drops_cap(self):
    module = self.implementation()
    planner = module.OfflineComfortPlanner(car_params(), init_v=10., experiment_enabled=True)
    sm = FixtureSubMaster()
    sm['carState'].vEgo = 10.
    selected = 0
    for _ in range(100):
      sm.advance()
      previous_target = planner.output_a_target
      planner.update(sm)
      if planner.last_cap is not None:
        selected += 1
        self.assertAlmostEqual(planner.output_a_target, 1.14)
        self.assertFalse(planner.output_should_stop)
        # Feedback integration must consume the selected cap on this same tick.
        self.assertAlmostEqual(planner.v_desired_filter.x,
                               planner.pre_feedback_speed + .05 * (planner.output_a_target + previous_target) / 2)
    self.assertGreater(selected, 0)
    planner.update(sm)  # Same timestamps: no held cap.
    self.assertIsNone(planner.last_cap)
    for service, field, value in (('controlsState', 'forceDecel', True), ('carState', 'brakePressed', True),
                                   ('carState', 'gasPressed', True), ('carControl', 'longActive', False)):
      before = getattr(sm[service], field)
      setattr(sm[service], field, value)
      sm.advance()
      planner.update(sm)
      self.assertIsNone(planner.last_cap)
      setattr(sm[service], field, before)

  def test_existing_feedback_fixtures_disabled_exact_parity(self):
    module = self.implementation()
    for scenario in ('lead_transition', 'stop_start', 'driver_cancel'):
      with self.subTest(scenario=scenario):
        self.assertEqual(simulate(scenario)['trace'], simulate(scenario, module.OfflineComfortPlanner)['trace'])

  def test_experiment_runs_native_feedback_with_effect_and_unchanged_disabled_arm(self):
    self.assertIsNotNone(importlib.util.find_spec('openpilot.tools.cyber_autotune.comfort_experiment'),
                         'native comparison is missing')
    experiment = importlib.import_module('openpilot.tools.cyber_autotune.comfort_experiment')
    base = experiment.run_case('open_road', arm='baseline')
    disabled = experiment.run_case('open_road', arm='disabled')
    candidate = experiment.run_case('open_road', arm='cap95')
    repeated = experiment.run_case('open_road', arm='cap95')
    self.assertEqual(base, disabled)
    self.assertEqual(candidate, repeated)
    self.assertGreater(candidate['cap_frames'], 0)
    self.assertNotEqual(base['metrics']['trace_sha256'], candidate['metrics']['trace_sha256'])
    self.assertGreater(candidate['speed_tracking_rms_mps'], base['speed_tracking_rms_mps'])
    for key in ('vehicle_activation_allowed', 'vehicle_qualified'):
      self.assertIs(candidate[key], False)
    with self.assertRaises(ValueError):
      experiment.run_case('open_road', arm='unknown')
    with self.assertRaises(ValueError):
      experiment.run_case('unknown')

  def test_regression_gate_rejects_response_loss_and_does_not_reward_no_effect(self):
    self.assertIsNotNone(importlib.util.find_spec('openpilot.tools.cyber_autotune.comfort_experiment'),
                         'native comparison is missing')
    experiment = importlib.import_module('openpilot.tools.cyber_autotune.comfort_experiment')
    base = experiment.run_case('open_road')
    candidate = experiment.run_case('open_road', arm='cap95')
    result = experiment.compare_case(base, candidate)
    self.assertIn('speed_tracking_rms_mps:REGRESSION', result['reasons'])
    self.assertEqual(result['status'], 'REJECTED')
    self.assertEqual(experiment.compare_case(base, base)['status'], 'NO_EFFECT')
    corrupt = {**candidate, 'physical_delay_s': .99}
    self.assertEqual(experiment.compare_case(base, corrupt)['status'], 'BLOCKED')

  def test_complete_matrix_has_repeatability_and_disabled_identity_before_any_verdict(self):
    self.assertIsNotNone(importlib.util.find_spec('openpilot.tools.cyber_autotune.comfort_experiment'))
    experiment = importlib.import_module('openpilot.tools.cyber_autotune.comfort_experiment')
    self.assertTrue(hasattr(experiment, 'run_matrix'), 'complete bound matrix is missing')
    report = experiment.run_matrix()
    self.assertEqual(report['case_count'], 30)
    self.assertEqual(report['native_runs'], 180)
    self.assertTrue(report['repeatable'])
    self.assertTrue(report['disabled_exact_identity'])
    self.assertEqual(report['candidate_status'], 'REJECTED')
    self.assertFalse(report['vehicle_activation_allowed'])
    self.assertEqual(len(report['comparisons']), 30)

  def test_cruise_dependency_changes_invalidate_evidence_binding(self):
    experiment = importlib.import_module('openpilot.tools.cyber_autotune.comfort_experiment')
    before = experiment._binding()
    read_bytes = Path.read_bytes

    def changed_cruise(path):
      original = read_bytes(path)
      return original + b'\n# synthetic changed cruise input\n' if path.as_posix().endswith('/selfdrive/car/cruise.py') else original

    with patch.object(Path, 'read_bytes', changed_cruise):
      self.assertNotEqual(before, experiment._binding())


if __name__ == '__main__':
  unittest.main()
