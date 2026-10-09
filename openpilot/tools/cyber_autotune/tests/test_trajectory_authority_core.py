import dataclasses
import math
import unittest

from openpilot.tools.cyber_autotune import trajectory_authority_core as t
from openpilot.tools.cyber_autotune.candidate_role_contracts import TrajectoryInput


def row(i=0, **changes):
  values = {'desired_curvature_1pm': .001, 'actual_curvature_1pm': 0., 'speed_mps': 15., 'roll_rad': 0.,
                'time_s': i*.01, 'dt_s': .01, 'active': True, 'steering_pressed': False,
                'safety_limited': False, 'curvature_limited': False}
  return TrajectoryInput(**{**values, **changes})


class TestTrajectoryCore(unittest.TestCase):
  def test_disabled_exact_native(self):
    disabled, native = t.Core('DISABLED'), t.NativeBaseline()
    for i in range(40):
      r = row(i, actual_curvature_1pm=.00001*i)
      self.assertEqual(disabled.update(r).raw_requested_torque, native.update(r)[0])

  def test_canonical_repeatability(self):
    a, b = t.Core(), t.Core()
    for i in range(40):
      self.assertEqual(a.update(row(i)), b.update(row(i)))
      self.assertEqual(a.trace, b.trace)

  def test_frozen_config(self):
    with self.assertRaises(ValueError):
      t.Core('OTHER')

  def test_no_config_mutation(self):
    core = t.Core()
    with self.assertRaises(AttributeError):
      core.config = 'DISABLED'

  def test_unknown_input(self):
    with self.assertRaises(ValueError):
      t.Core().update({'modelV2': 1})

  def test_subclass_input(self):
    class Loose(TrajectoryInput):
      pass
    with self.assertRaises(ValueError):
      t.Core().update(Loose(**dataclasses.asdict(row())))

  def test_duplicate_time(self):
    core = t.Core()
    core.update(row())
    with self.assertRaises(ValueError):
      core.update(row())

  def test_future_gap(self):
    core = t.Core()
    core.update(row())
    with self.assertRaises(ValueError):
      core.update(row(2))

  def test_first_correction_zero(self):
    core = t.Core()
    core.update(row())
    self.assertEqual(core.trace['correction_mps2'], 0.)

  def test_feedback_innovation(self):
    core = t.Core()
    core.update(row())
    core.update(row(1, actual_curvature_1pm=.001))
    self.assertNotEqual(core.trace['correction_mps2'], 0.)

  def test_bounded_state(self):
    core = t.Core()
    for i in range(10):
      out = core.update(row(i, actual_curvature_1pm=(-1)**i*10))
      self.assertLessEqual(abs(core.trace['previous_clipped_error_mps2']), core.trace['authority_mps2'])
      self.assertLessEqual(abs(core.trace['correction_mps2']), core.trace['authority_mps2'])
      self.assertLessEqual(abs(out.raw_requested_torque), 1.)

  def test_prelimit_observed(self):
    core = t.Core()
    out = core.update(row())
    self.assertIsNotNone(out.pre_limit_intent)
    self.assertEqual(out.observation_status, 'OFFLINE_PROTOTYPE_OBSERVED')

  def test_friction_not_fabricated(self):
    self.assertIsNone(t.Core().update(row()).friction_component)

  def test_no_error_straight(self):
    core = t.Core()
    for i in range(20):
      self.assertEqual(core.update(row(i, desired_curvature_1pm=0.)).raw_requested_torque, 0.)

  def test_inactive_no_leak(self):
    core = t.Core()
    core.update(row())
    self.assertEqual(core.update(row(1, active=False)).raw_requested_torque, 0.)
    self.assertIsNone(core.trace['previous_clipped_error_mps2'])

  def test_pressed_zero_innovation(self):
    core = t.Core()
    core.update(row())
    core.update(row(1, steering_pressed=True))
    self.assertEqual(core.trace['correction_mps2'], 0.)

  def test_release_reset(self):
    core = t.Core()
    core.update(row(0, steering_pressed=True))
    core.update(row(1))
    self.assertIn('RELEASE', core.trace['reset_events'])
    self.assertEqual(core.trace['correction_mps2'], 0.)

  def test_reengagement_reset(self):
    core = t.Core()
    core.update(row(0, active=False))
    core.update(row(1))
    self.assertIn('REENGAGEMENT', core.trace['reset_events'])

  def test_scenario_reset(self):
    core = t.Core()
    core.update(row())
    core.reset('SCENARIO_BOUNDARY')
    core.update(row())
    self.assertEqual(core.trace['correction_mps2'], 0.)

  def test_config_change_requires_new_instance(self):
    with self.assertRaises(ValueError):
      t.Core().reset('CONFIG_CHANGE')

  def test_reset_unknown(self):
    with self.assertRaises(ValueError):
      t.Core().reset('UNKNOWN')

  def test_sign_mirror(self):
    a, b = t.Core(), t.Core()
    for i in range(40):
      x = a.update(row(i, actual_curvature_1pm=i*.00001))
      y = b.update(row(i, desired_curvature_1pm=-.001, actual_curvature_1pm=-i*.00001))
      self.assertAlmostEqual(x.raw_requested_torque, -y.raw_requested_torque, places=14)

  def test_no_hidden_delay_or_sg(self):
    core = t.Core()
    core.update(row())
    self.assertEqual(core.trace['state_fields'], ['previous_clipped_error_mps2'])
    self.assertEqual(core.trace['physical_delay_owner'], 'PLANT')

  def test_nonfinite_derived_rejected(self):
    with self.assertRaises(ValueError):
      t.Core().update(row(speed_mps=1e308))

  def test_output_finite(self):
    self.assertTrue(math.isfinite(t.Core().update(row()).raw_requested_torque))

class TestInnovationMechanism(unittest.TestCase):
  def pid(self, enabled=True):
    from openpilot.common.pid import PIDController
    return t.InnovationPID(PIDController(.8, .15, pos_limit=4., neg_limit=-4.), enabled)

  def test_constant_error_no_innovation(self):
    pid = self.pid()
    pid.update(.5)
    pid.update(.5)
    self.assertEqual(pid.correction_mps2, 0.)

  def test_first_reset_zero(self):
    self.assertIsNone(self.pid().previous_clipped_error_mps2)

  def test_known_signed_control(self):
    pid = self.pid()
    pid.update(.2)
    pid.update(.5)
    self.assertAlmostEqual(pid.correction_mps2, .3)

  def test_clipped_error_not_raw_derivative(self):
    pid = self.pid()
    pid.update(100.)
    pid.update(200.)
    self.assertEqual(pid.correction_mps2, 0.)
    self.assertEqual(pid.previous_clipped_error_mps2, 4.)

  def test_correction_inside_antiwindup(self):
    pid = self.pid()
    pid.update(-4.)
    pid.update(2.)
    self.assertEqual(pid.correction_mps2, 4.)
    self.assertEqual(pid.control, 4.)
    self.assertGreater(pid.pre_limit_accel_mps2, pid.control)
    self.assertLessEqual(pid.i, 0.)  # native antiwindup sees the additive correction

  def test_instance_local(self):
    core = t.Core()
    native = t.NativeBaseline()
    self.assertIsNot(type(core.controller.pid), type(native.controller.pid))

  def test_runtime_gain_mutation(self):
    core = t.Core()
    core.controller.pid._k_i = ([0], [1.])
    with self.assertRaisesRegex(ValueError, 'MUTATION'):
      core.update(row())

  def test_runtime_mode_mutation(self):
    core = t.Core()
    core._mode = 'DISABLED'
    with self.assertRaisesRegex(ValueError, 'MUTATION'):
      core.update(row())

  def test_disabled_state_exact(self):
    core, native = t.Core('DISABLED'), t.NativeBaseline()
    for i in range(30):
      r = row(i)
      core.update(r)
      native.update(r)
      for field in ('p', 'i', 'd', 'f', 'control'):
        self.assertEqual(getattr(core.controller.pid, field), getattr(native.controller.pid, field))
      self.assertEqual(core.controller.lat_accel_request_buffer, native.controller.lat_accel_request_buffer)

class TestRuntimeConfigDrift(unittest.TestCase):
  def test_pid_timebase_mutation(self):
    core = t.Core('DISABLED')
    core.controller.pid.i_dt = 1.
    with self.assertRaisesRegex(ValueError, 'MUTATION'):
      core.update(row())

  def test_filter_mutation(self):
    core = t.Core()
    core.controller.jerk_filter.alpha = .5
    with self.assertRaisesRegex(ValueError, 'MUTATION'):
      core.update(row())

  def test_reference_buffer_mutation(self):
    core = t.Core()
    core.controller.lookahead_frames = 1
    with self.assertRaisesRegex(ValueError, 'MUTATION'):
      core.update(row())

  def test_model_mutation(self):
    core = t.Core()
    core.model.sR = 10.
    with self.assertRaisesRegex(ValueError, 'MUTATION'):
      core.update(row())

  def test_stale_config_not_hidden_by_reset(self):
    core = t.Core()
    core.controller.pid.i_dt = 1.
    with self.assertRaisesRegex(ValueError, 'MUTATION'):
      core.update(row(active=False))
