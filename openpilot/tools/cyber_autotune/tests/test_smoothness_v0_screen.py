from copy import deepcopy
import unittest
from unittest.mock import patch
from openpilot.tools.cyber_autotune import smoothness_v0_screen as s
from openpilot.tools.cyber_autotune import candidate_architecture as a


class TestScreen(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.commands = s.baseline_commands('gentle_left')

  def test_baseline_only(self):
    self.assertEqual(self.commands['role'], 'UNCHANGED_NATIVE_BASELINE')

  def test_command_repeat(self):
    self.assertEqual(self.commands, s.baseline_commands('gentle_left'))

  def test_disabled_reproduces_generation(self):
    r = s.run_arm(self.commands, 'SG_DISABLED', self.commands['receipt_sha256'])
    self.assertEqual(
      a.hash_object([{k: r[k] for k in ('requested', 'applied', 'curvature', 'yaw_rate', 'heading', 'pose_x', 'pose_y')} for r in r]),
      self.commands['plant_trace_sha256'],
    )

  def test_current_alias(self):
    self.assertEqual(
      s.run_arm(self.commands, 'CURRENT_ALIAS', self.commands['receipt_sha256']), s.run_arm(self.commands, 'SG_DISABLED', self.commands['receipt_sha256'])
    )

  def test_sg_repeat(self):
    self.assertEqual(
      s.run_arm(self.commands, 'SG_V0_CANONICAL', self.commands['receipt_sha256']), s.run_arm(self.commands, 'SG_V0_CANONICAL', self.commands['receipt_sha256'])
    )

  def test_identical_core_input(self):
    rows = s.run_arm(self.commands, 'SG_V0_CANONICAL', self.commands['receipt_sha256'])
    self.assertEqual([r['pre'] for r in rows], [r['command']['normalized_torque'] for r in self.commands['rows']])

  def test_no_feedback_to_core(self):
    with patch.object(s.NativeBaseline, 'update', side_effect=AssertionError('NO_CORE_EXECUTION_DURING_REPLAY')):
      s.run_arm(self.commands, 'SG_V0_CANONICAL', self.commands['receipt_sha256'])

  def test_input_mutation(self):
    row = deepcopy(self.commands)
    row['rows'][0]['command']['normalized_torque'] = 0.3
    with self.assertRaises(ValueError):
      s.run_arm(row, 'SG_V0_CANONICAL', self.commands['receipt_sha256'])

  def test_ta_identity_rejected(self):
    row = deepcopy(self.commands)
    row['role'] = 'TA-B'
    row = s.seal({k: v for k, v in row.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      s.run_arm(row, 'SG_V0_CANONICAL', row['receipt_sha256'])

  def test_intervention_time_binding(self):
    row = deepcopy(self.commands)
    for r in row['rows']:
      r['intervention']['time_s'] += 10.0
    row = s.seal({k: v for k, v in row.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      s.verify_commands(row, row['receipt_sha256'])

  def test_intervention_flag_binding(self):
    for field in ('active', 'steering_pressed', 'release', 'reengagement'):
      row = deepcopy(self.commands)
      row['rows'][5]['intervention'][field] = not row['rows'][5]['intervention'][field]
      row = s.seal({k: v for k, v in row.items() if k != 'receipt_sha256'})
      with self.assertRaises(ValueError):
        s.verify_commands(row, row['receipt_sha256'])

  def test_command_core_binding(self):
    row = deepcopy(self.commands)
    row['rows'][5]['command']['core_source_sha256'] = '9' * 64
    row = s.seal({k: v for k, v in row.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      s.verify_commands(row, row['receipt_sha256'])

  def test_index_binding(self):
    row = deepcopy(self.commands)
    row['rows'][5]['index'] = 999
    row = s.seal({k: v for k, v in row.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      s.verify_commands(row, row['receipt_sha256'])

  def test_ta_config_rejected(self):
    with self.assertRaises(ValueError):
      s.run_arm(self.commands, 'TA_V0_CANDIDATE', self.commands['receipt_sha256'])

  def test_unknown_scenario(self):
    with self.assertRaises(ValueError):
      s.baseline_commands('NEW_BEST_SCENARIO')

  def test_search_denied(self):
    with self.assertRaises(ValueError):
      s.authorize('SEARCH')

  def test_evaluation_denied(self):
    with self.assertRaises(ValueError):
      s.authorize('FROZEN_EVALUATION')

  def test_composition_denied(self):
    with self.assertRaises(ValueError):
      s.authorize('DEVELOPMENT_SCREEN', composition=True)

  def test_ta_enabled_denied(self):
    with self.assertRaises(ValueError):
      s.authorize('DEVELOPMENT_SCREEN', ta_enabled=True)

  def test_exact_negative_control(self):
    self.assertTrue(s.positive_controls()['checks']['disabled_exact'])

  def test_positive_controls(self):
    self.assertTrue(all(s.positive_controls()['checks'].values()))

  def test_binding_drift(self):
    row = s.binding()
    row['baseline_core_identity']['role'] = 'TA-B'
    with self.assertRaises(ValueError):
      s.verify_binding(row)

  def test_arm_alias_identity(self):
    ctx = s.binding()
    self.assertEqual(s.arm_identity('SG_DISABLED', ctx), s.arm_identity('CURRENT_ALIAS', ctx))

  def test_plant_only_delay(self):
    self.assertEqual(s.binding()['physical_delay_owner'], 'PLANT')

  def test_no_extra_state(self):
    row = s.run_arm(self.commands, 'SG_V0_CANONICAL', self.commands['receipt_sha256'])[0]
    self.assertIn('state_after', row['trace'])
    self.assertNotIn('tracking_error', row['trace'])

  def test_metric_policy_bound(self):
    self.assertEqual(
      s.metrics.evaluate(s.run_arm(self.commands, 'SG_DISABLED', self.commands['receipt_sha256']))['metric_policy_sha256'],
      s.load()['metrics']['receipt_sha256'],
    )


if __name__ == '__main__':
  unittest.main()
