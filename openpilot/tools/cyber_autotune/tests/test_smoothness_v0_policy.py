import unittest
from openpilot.tools.cyber_autotune import smoothness_v0_policy as p

class TestPolicy(unittest.TestCase):
  def test_one_family_source_only(self):
    r = p.build()
    self.assertEqual(r['selection']['status'], 'SG_A_SELECTED')
    self.assertFalse(r['policy']['result_input_allowed'])
    self.assertEqual(r['config']['unit_delta'], 1.)
  def test_search_composition_forbidden(self):
    r = p.build()
    for k in ('search_authorized', 'composition_authorized', 'frozen_evaluation_authorized'):
      self.assertIs(r['matrix'][k], False)
  def test_scenarios_exact_frozen(self):
    from openpilot.tools.cyber_autotune.trajectory_v0_freeze import load
    self.assertEqual(p.build()['scenarios']['rows'], load()['scenarios']['rows'])
  def test_config_only(self):
    self.assertEqual(p.build()['config']['allowed_configs'], ['SG_DISABLED', 'SG_V0_CANONICAL', 'SG_TEST_ONLY_POSITIVE_CONTROL'])
  def test_policy_mutation(self):
    r = p.build()
    r['config']['unit_delta'] = .5
    with self.assertRaises(ValueError):
      p.validate(r)

if __name__ == '__main__':
  unittest.main()
