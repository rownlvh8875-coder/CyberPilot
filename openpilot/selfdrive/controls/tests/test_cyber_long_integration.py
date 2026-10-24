"""Actual native planner/LongControl parity, NOT replaced with mocked solvers.

Copyright (c) 2018, Comma.ai, Inc. Frozen planner loaded under root MIT LICENSE.
Inputs are synthetic cereal fixtures; passing these tests is not replay evidence.
"""
import subprocess
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from opendbc.car.structs import car
from opendbc.car.interfaces import ACCEL_MIN, ACCEL_MAX
from openpilot.cereal import log
from openpilot.cereal import messaging
from openpilot.selfdrive.controls.lib import longitudinal_planner as current
from openpilot.selfdrive.controls.lib.longcontrol import LongControl, LongCtrlState
from openpilot.selfdrive.controls.lib.cyber_long.types import CyberLongConfig, CyberLongMode

BASELINE_SHA = 'c8fb906815530460ed156f14e09e1f312bb0f851'
ROOT = Path(__file__).resolve().parents[4]


def load_baseline(filename='longitudinal_planner.py'):
  # Load the actual Git object, not a reimplementation of expected arbitration.
  source = subprocess.check_output(
    ['git', 'show', f'{BASELINE_SHA}:openpilot/selfdrive/controls/lib/{filename}'], cwd=ROOT, text=True,
  )
  module = types.ModuleType(f'cyber_long_frozen_{filename}')
  exec(compile(source, f'{BASELINE_SHA}:{filename}', 'exec'), module.__dict__)
  return module


class FixtureSubMaster:
  """Test-local cereal messages; no sockets, Params, sendcan or controller apply."""
  def __init__(self):
    services = ('carState', 'carControl', 'controlsState', 'selfdriveState', 'modelV2', 'radarState', 'vehicleParameters')
    self.messages = {name: getattr(messaging.new_message(name), name) for name in services}
    self.logMonoTime = dict.fromkeys(services, 1)
    self.valid = True
    self['selfdriveState'].enabled = True
    self['selfdriveState'].personality = log.LongitudinalPersonality.standard
    self['controlsState'].longControlState = LongCtrlState.pid
    self['carControl'].longActive = True
    self['carState'].vCruise = 60.
    self['carControl'].orientationNED = [0., 0., 0.]
    self['modelV2'].meta.disengagePredictions.gasPressProbs = [1., 1.]

  def __getitem__(self, name):
    return self.messages[name]

  def all_checks(self):
    return self.valid

  def advance(self):
    for name in self.logMonoTime:
      self.logMonoTime[name] += 1


def car_params():
  cp = car.CarParams.new_message()
  cp.carFingerprint = 'SYNTHETIC_PARITY_ONLY'
  cp.openpilotLongitudinalControl = True
  cp.longitudinalActuatorDelay = 0.2  # Synthetic fixture seconds, not an approved vehicle calibration.
  cp.steerRatio = 15.
  cp.wheelbase = 2.7
  cp.stopAccel = -0.5
  cp.longitudinalTuning.kiBP = [0.]
  cp.longitudinalTuning.kiV = [0.1]
  return cp


class TestCyberLongNativeParity(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.baseline = load_baseline()
    cls.baseline_longcontrol = load_baseline('longcontrol.py')

  def compare(self, stock, candidate):
    for attr in ('output_a_target', 'output_should_stop', 'a_cruise', 'fcw', 'allow_throttle'):
      self.assertEqual(getattr(stock, attr), getattr(candidate, attr), attr)
    self.assertEqual(stock.v_desired_filter.x, candidate.v_desired_filter.x)
    self.assertEqual(stock.mpc.source, candidate.mpc.source)
    for attr in ('v_desired_trajectory', 'a_desired_trajectory', 'j_desired_trajectory'):
      self.assertTrue(np.array_equal(getattr(stock, attr), getattr(candidate, attr)), attr)
    for attr in ('v_solution', 'a_solution', 'j_solution'):
      self.assertTrue(np.array_equal(getattr(stock.mpc, attr), getattr(candidate.mpc, attr)), attr)
    self.assertEqual(stock.mpc.crash_cnt, candidate.mpc.crash_cnt)
    # solve_time and publish wall-clock/processingDelay are nondeterministic,
    # not control values; do not modify upstream replay ignore lists.

  def run_sequence(self, config):
    cp = car_params()
    stock = self.baseline.LongitudinalPlanner(cp)
    candidate = current.LongitudinalPlanner(cp, cyber_long_config=config)
    stock_control, candidate_control = self.baseline_longcontrol.LongControl(cp), LongControl(cp)
    sm = FixtureSubMaster()
    # lead cruise → lead braking → stop → restart → loss, all with native MPC.
    for experimental in (False, True):
      sm['selfdriveState'].experimentalMode = experimental
      for speed, lead_speed, present, model_stop in ((15., 15., True, False), (10., 0., True, False),
                                                   (0., 0., True, True), (0.5, 2., True, False), (8., 8., False, False)):
        sm['carState'].vEgo = speed
        sm['carState'].standstill = speed == 0.
        sm['carState'].cruiseState.standstill = speed == 0.
        sm['modelV2'].action.desiredAcceleration = -0.4 if model_stop else 0.2
        sm['modelV2'].action.shouldStop = model_stop
        lead = sm['radarState'].leadOne
        lead.present, lead.dRel, lead.vLead, lead.aLeadK, lead.aLeadTau = present, 25., lead_speed, 0., 1.5
        for _ in range(4):  # Repeat synthetic samples to exercise state feedback.
          sm.advance()
          stock.update(sm)
          candidate.update(sm)
          self.compare(stock, candidate)
          a_stock = stock_control.update(True, sm['carState'], stock.output_a_target, stock.output_should_stop, (ACCEL_MIN, ACCEL_MAX))
          a_candidate = candidate_control.update(True, sm['carState'], candidate.output_a_target,
                                                 candidate.output_should_stop, (ACCEL_MIN, ACCEL_MAX))
          self.assertEqual(a_stock, a_candidate)
          self.assertEqual(stock_control.long_control_state, candidate_control.long_control_state)
          self.assertEqual(stock_control.pid.i, candidate_control.pid.i)
    return stock, candidate, sm

  def test_default_disabled_matches_native_baseline(self):
    self.run_sequence(None)

  def test_observation_only_matches_native_baseline_and_longcontrol(self):
    _, candidate, _ = self.run_sequence(CyberLongConfig(mode=CyberLongMode.OBSERVE_ONLY))
    self.assertIsNotNone(candidate.cyber_long_policy.last_observation)
    self.assertFalse(candidate.cyber_long_policy.last_observation.provenance_complete)

  def test_stock_resets_overrides_force_decel_curve_coast_and_invalid_inputs(self):
    stock, candidate, sm = self.run_sequence(CyberLongConfig(mode=CyberLongMode.OBSERVE_ONLY))
    variations = (
      ('controlsState', 'forceDecel', True), ('carState', 'steeringAngleDeg', 20.),
      ('carState', 'vCruise', current.V_CRUISE_UNSET), ('carState', 'brakePressed', True),
      ('carState', 'gasPressed', True), ('carControl', 'longActive', False),
      ('controlsState', 'longControlState', LongCtrlState.off), ('selfdriveState', 'enabled', False),
    )
    for service, field, value in variations:
      with self.subTest(service=service, field=field):
        old = getattr(sm[service], field)
        setattr(sm[service], field, value)
        sm.advance()
        stock.update(sm)
        candidate.update(sm)
        self.compare(stock, candidate)
        setattr(sm[service], field, old)
    sm['selfdriveState'].experimentalMode = False
    sm['carControl'].orientationNED = [0., -0.1, 0.]
    sm['modelV2'].meta.disengagePredictions.gasPressProbs = [0., 0.]
    sm.valid = False
    sm.advance()
    stock.update(sm)
    candidate.update(sm)
    self.compare(stock, candidate)
    self.assertIsNone(candidate.cyber_long_policy.last_observation)

  def test_observer_exception_falls_back_to_current_stock_cycle(self):
    stock, candidate, sm = self.run_sequence(CyberLongConfig(mode=CyberLongMode.OBSERVE_ONLY))
    sm.advance()
    with patch.object(candidate.cyber_long_policy, 'observe', side_effect=RuntimeError('synthetic observer fault')):
      stock.update(sm)
      candidate.update(sm)
    self.compare(stock, candidate)
    self.assertIsNone(candidate.cyber_long_policy.last_observation)
    self.assertEqual(candidate.cyber_long_fault, 'RuntimeError')

  def test_nonwinning_stop_and_tie_preserve_stock_arbitration(self):
    # Isolated boundary characterization only, NOT native whole-planner proof.
    cp, sm = car_params(), FixtureSubMaster()
    sm['carState'].vEgo = 10.  # Winning MPC candidate must NOT trigger stock low-speed stop.
    self.assertFalse(current.should_stop(sm['carState'].vEgo, -0.4))
    sm['selfdriveState'].experimentalMode = True
    sm['modelV2'].action.desiredAcceleration = 0.2
    sm['modelV2'].action.shouldStop = True
    for cruise_accel in (0.2, -0.4):
      stock = self.baseline.LongitudinalPlanner(cp)
      candidate = current.LongitudinalPlanner(cp, cyber_long_config=CyberLongConfig(mode=CyberLongMode.OBSERVE_ONLY))
      with patch.object(self.baseline, 'get_accel_from_plan', return_value=-0.4), \
           patch.object(current, 'get_accel_from_plan', return_value=-0.4), \
           patch.object(self.baseline, 'get_cruise_accel', return_value=cruise_accel), \
           patch.object(current, 'get_cruise_accel', return_value=cruise_accel):
        stock.update(sm)
        candidate.update(sm)
      self.compare(stock, candidate)
      self.assertEqual(candidate.output_a_target, -0.4)
      self.assertTrue(candidate.output_should_stop)


if __name__ == '__main__':
  unittest.main()
