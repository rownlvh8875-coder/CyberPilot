import copy
import unittest

from openpilot.tools.cyber_autotune import trajectory_v0_policy as p


class TestTrajectoryPolicy(unittest.TestCase):
  def test_selection(self):
    self.assertEqual(p.build()['selection']['status'], 'TA_B_SELECTED')

  def test_one_family(self):
    self.assertEqual(p.build()['selection']['selected_family'], 'TA-B')

  def test_canonical(self):
    self.assertEqual(p.build()['config']['horizon_samples'], 1)

  def test_search_forbidden(self):
    self.assertFalse(p.build()['config']['search_allowed'])

  def test_sources_validate(self):
    p.validate(p.build())

  def test_changed_policy_rejected(self):
    rows = copy.deepcopy(p.build())
    rows['config']['horizon_samples'] = 2
    with self.assertRaises(ValueError):
      p.validate(rows)

  def test_current_alias(self):
    self.assertTrue(p.build()['matrix']['current_is_exact_baseline_alias'])

  def test_roles(self):
    self.assertEqual(p.build()['matrix']['allowed_roles'], ['ARCHITECTURE_PROBE', 'DEVELOPMENT_SCREEN'])

  def test_historical_not_input(self):
    self.assertFalse(p.build()['selection']['historical_70_used'])

  def test_no_results_before_selection(self):
    self.assertFalse(p.build()['selection']['candidate_results_used'])

  def test_no_physical_bound(self):
    self.assertEqual(p.build()['config']['bound_semantics'], 'INHERITED_OUTPUT_AUTHORITY_PROJECTION_NOT_PHYSICAL_ERROR_BOUND')

  def test_delay_sole_owner(self):
    self.assertEqual(p.build()['config']['physical_delay_owner'], 'PLANT')
