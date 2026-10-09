from dataclasses import asdict, replace
import itertools
import unittest

from openpilot.tools.cyber_autotune import smoothness_governor_v0 as g
from openpilot.tools.cyber_autotune.candidate_role_contracts import GovernorCommand, InterventionInput
from openpilot.tools.cyber_autotune import candidate_architecture as a

SOURCE, CONFIG = g.BASELINE_IDENTITY['source_sha256'], g.BASELINE_IDENTITY['config_sha256']


def command(u):
  return GovernorCommand(u, SOURCE, CONFIG)


def event(i, **kw):
  return InterventionInput(i * 0.01, 0.01, **{'active': True, 'steering_pressed': False, 'release': False, 'reengagement': False, **kw})


def run(values, mode='SG_V0_CANONICAL'):
  obj = g.Governor(mode, SOURCE, CONFIG)
  return [obj.update(command(v), event(i)).post_governor for i, v in enumerate(values)]


class TestGovernor(unittest.TestCase):
  def test_positive_bridge(self):
    self.assertEqual(run([1.0, -1.0, -1.0]), [1.0, 0.0, -1.0])

  def test_negative_bridge(self):
    self.assertEqual(run([-1.0, 1.0, 1.0]), [-1.0, 0.0, 1.0])

  def test_intermediate_projection(self):
    self.assertEqual(run([0.75, -0.75, -0.75]), [0.75, -0.25, -0.75])

  def test_disabled_exact(self):
    u = [1.0, -1.0, 0.123, -0.999, 0.0]
    self.assertEqual(run(u, 'SG_DISABLED'), u)

  def test_zero_no_tail(self):
    for v in (-1.0, -0.25, 0.25, 1.0):
      self.assertEqual(run([v, 0.0]), [v, 0.0])

  def test_constant_unity(self):
    for v in (-1.0, -0.2, 0.0, 0.2, 1.0):
      self.assertEqual(run([v] * 8), [v] * 8)

  def test_small_chatter_unchanged(self):
    self.assertEqual(run([0.01, -0.01] * 4), [0.01, -0.01] * 4)

  def test_smooth_ramp_unchanged(self):
    self.assertEqual(run([-0.8, -0.4, 0.0, 0.4, 0.8]), [-0.8, -0.4, 0.0, 0.4, 0.8])

  def test_authority_tv_sign_exhaustive(self):
    def tv(x):
      return sum(abs(b - a) for a, b in zip(x, x[1:], strict=False))

    def count(x):
      signs = [v > 0 for v in x if v != 0]
      return sum(a != b for a, b in zip(signs, signs[1:], strict=False))

    for u in itertools.product((-1.0, -0.5, 0.0, 0.5, 1.0), repeat=4):
      y = run(u)
      self.assertTrue(all(abs(b) <= abs(v) and b * v >= 0 for v, b in zip(u, y, strict=True)))
      self.assertLessEqual(tv(y) + abs(u[-1] - y[-1]), tv(u))
      self.assertLessEqual(count(y), count(u))

  def test_overshoot(self):
    u = [1.0, -0.6, 0.2, -1.0, 1.0]
    y = run(u)
    for old, v, out in zip(y, u[1:], y[1:], strict=False):
      self.assertTrue(min(old, v) <= out <= max(old, v))

  def test_pressed_passthrough(self):
    o = g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG)
    o.update(command(1.0), event(0))
    self.assertEqual(o.update(command(-1.0), event(1, steering_pressed=True)).post_governor, -1.0)
    self.assertEqual(o.update(command(1.0), event(2, release=True)).post_governor, 1.0)

  def test_inactive_zero_reset(self):
    o = g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG)
    o.update(command(1.0), event(0))
    r = o.update(command(0.0), event(1, active=False))
    self.assertEqual(r.post_governor, 0.0)
    self.assertIsNone(r.state_after)
    self.assertEqual(o.update(command(-1.0), event(2, reengagement=True)).post_governor, -1.0)

  def test_inactive_nonzero_rejected(self):
    with self.assertRaises(ValueError):
      g.Governor('SG_DISABLED', SOURCE, CONFIG).update(command(0.1), event(0, active=False))

  def test_event_flag_mismatch(self):
    o = g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG)
    o.update(command(0.0), event(0))
    with self.assertRaises(ValueError):
      o.update(command(0.0), event(1, release=True))

  def test_missing_release_rejected(self):
    o = g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG)
    o.update(command(1.0), event(0, steering_pressed=True))
    with self.assertRaises(ValueError):
      o.update(command(0.0), event(1))

  def test_timeline_rejected(self):
    o = g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG)
    o.update(command(0.0), event(0))
    with self.assertRaises(ValueError):
      o.update(command(0.0), event(2))

  def test_exact_types(self):
    o = g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG)
    with self.assertRaises(ValueError):
      o.update(asdict(command(0.0)), event(0))

  def test_ta_source_rejected(self):
    with self.assertRaises(ValueError):
      g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG).update(GovernorCommand(0.0, '3' * 64, CONFIG), event(0))

  def test_core_config_drift_rejected(self):
    o = g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG)
    o.update(command(0.0), event(0))
    with self.assertRaises(ValueError):
      o.update(GovernorCommand(0.0, SOURCE, '3' * 64), event(1))

  def test_constructor_cannot_select_ta_identity(self):
    with self.assertRaises(ValueError):
      g.Governor('SG_V0_CANONICAL', 'a' * 64, 'b' * 64)

  def test_config_unknown(self):
    with self.assertRaises(ValueError):
      g.Governor('SEARCH', SOURCE, CONFIG)

  def test_config_mutation(self):
    o = g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG)
    o._mode = 'SG_DISABLED'
    with self.assertRaises(ValueError):
      o.update(command(0.0), event(0))

  def test_state_owner(self):
    r = g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG).update(command(0.2), event(0))
    self.assertEqual(r.governor_state, (0.2,))
    self.assertEqual(r.state_owner, 'SG')
    self.assertEqual(r.physical_delay_owner, 'PLANT')

  def test_saturation_separation(self):
    o = g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG)
    o.update(command(1.0), event(0))
    r = o.update(command(-1.0), event(1))
    self.assertTrue(r.core_input_saturated)
    self.assertFalse(r.governor_output_saturated)
    self.assertTrue(r.governor_limit_active)

  def test_repeat_exact(self):
    self.assertEqual(run([1.0, -1.0, 0.5, -0.9] * 5), run([1.0, -1.0, 0.5, -0.9] * 5))

  def test_final_equals_post(self):
    r = g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG).update(command(0.5), event(0))
    self.assertEqual(r.final_requested_torque, r.post_governor)
    with self.assertRaises(ValueError):
      replace(r, final_requested_torque=0.7)

  def test_output_action_rejected(self):
    r = g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG).update(command(0.5), event(0))
    with self.assertRaises(ValueError):
      replace(r, action='FABRICATED')

  def test_output_reason_rejected(self):
    r = g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG).update(command(0.5), event(0))
    with self.assertRaises(ValueError):
      replace(r, saturation_reason='FABRICATED')

  def test_output_state_drop_rejected(self):
    r = g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG).update(command(0.5), event(0))
    with self.assertRaises(ValueError):
      replace(r, state_after=None, governor_state=())

  def test_output_reset_rejected(self):
    r = g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG).update(command(0.5), event(0))
    with self.assertRaises(ValueError):
      replace(r, reset_events=('PHYSICAL_DELAY',))

  def test_output_fake_projection_rejected(self):
    o = g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG)
    o.update(command(1.0), event(0))
    r = o.update(command(-1.0), event(1))
    with self.assertRaises(ValueError):
      replace(r, post_governor=-0.25, final_requested_torque=-0.25, state_after=-0.25, governor_state=(-0.25,))

  def test_nonfinite(self):
    for v in (float('nan'), float('inf'), -float('inf'), True, 1.01):
      with self.assertRaises(ValueError):
        command(v)

  def test_unknown_fields(self):
    for key in ('desired_curvature_1pm', 'tracking_error', 'modelV2', 'lane', 'path', 'plant_state', 'candidate_output'):
      with self.assertRaises(ValueError):
        GovernorCommand.parse({**asdict(command(0.0)), key: 0.0})

  def test_input_subclass(self):
    class Extended(GovernorCommand):
      pass

    with self.assertRaises(ValueError):
      g.Governor('SG_V0_CANONICAL', SOURCE, CONFIG).update(Extended(0.0, SOURCE, CONFIG), event(0))

  def test_history_unchanged(self):
    self.assertEqual(dict(a.HISTORY), {'CURRENT': 'BASELINE_EXACT', 'V1': 'TRADEOFF_ONLY', 'V2': 'REJECTED'})

  def test_reset_ownership(self):
    self.assertTrue(all(owner == 'PLANT' for name, owner in a.OWNERS if name == 'physical_delay'))


if __name__ == '__main__':
  unittest.main()
