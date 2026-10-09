import unittest

from openpilot.tools.cyber_autotune import smoothness_closed_loop_policy as p
from openpilot.tools.cyber_autotune.smoothness_v0_freeze import load as frozen


class TestClosedLoopPolicy(unittest.TestCase):
  def test_exact_pre_execution_policy(self):
    self.assertEqual(p.validate(p.build()), p.build())

  def test_policy_mutation_rejected(self):
    rows = p.build()
    rows['policy']['dt_s'] = .02
    with self.assertRaises(ValueError):
      p.validate(rows)

  def test_frozen_scenarios(self):
    self.assertEqual(p.build()['policy']['scenario_rows'], frozen()['scenarios']['rows'])

  def test_frozen_metric(self):
    self.assertEqual(p.build()['policy']['metric_policy_sha256'], frozen()['metrics']['receipt_sha256'])

  def test_frozen_config(self):
    self.assertEqual(p.build()['policy']['sg_config_sha256'], frozen()['config']['receipt_sha256'])

  def test_eight_stage_timing(self):
    self.assertEqual(len(p.build()['policy']['ordering']), 8)

  def test_no_cross_arm_feedback(self):
    self.assertEqual(p.build()['policy']['feedback_source'], 'SAME_ARM_PRE_STEP_PLANT_STATE_ONLY')

  def test_alias(self):
    self.assertTrue(p.build()['matrix']['current_exact_alias'])

  def test_repeats(self):
    self.assertEqual(p.build()['matrix']['repeats'], 2)

  def test_no_ta(self):
    self.assertFalse(p.build()['matrix']['ta_enabled'])

  def test_no_composition(self):
    self.assertFalse(p.build()['matrix']['composition_authorized'])

  def test_no_search(self):
    self.assertFalse(p.build()['matrix']['search_authorized'])

  def test_no_evaluation(self):
    self.assertFalse(p.build()['matrix']['frozen_evaluation_authorized'])

  def test_no_qualification(self):
    for r in p.build().values():
      for field in ('qualification_allowed', 'sealed_reference_allowed', 'vehicle_activation_allowed'):
        self.assertIs(r[field], False)

  def test_no_threshold(self):
    self.assertIsNone(p.build()['policy']['performance_threshold'])

  def test_not_stability_proof(self):
    self.assertFalse(p.build()['policy']['stability_proof'])

  def test_replay_pin(self):
    self.assertEqual(len(p.build()['policy']['frozen_replay_receipt_sha256']), 64)
