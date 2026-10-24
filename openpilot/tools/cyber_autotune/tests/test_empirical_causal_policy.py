"""Policy provenance and authorization are public, not private-cache dependent."""
import unittest
from openpilot.tools.cyber_autotune import empirical_causal_policy as c
from openpilot.tools.cyber_autotune import empirical_v3_policy as v
from openpilot.tools.cyber_autotune import empirical_stage_a_publication as old


class TestFrozenScope(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.pol=c.static_policy()

  def test_exact_two_routes(self):
    self.assertEqual(self.pol['routes'],v.routes())

  def test_v2_excluded_development(self):
    excluded=next(x for x in v.inputs()['empirical-plant-v2-train-dev-split-v1.json']['routes'] if x['role']=='DEVELOPMENT')
    self.assertNotIn(excluded['route_id'],[x['route_id'] for x in self.pol['routes']])

  def test_condition_count(self):
    self.assertEqual(len(self.pol['condition_policy']['conditions']),6)

  def test_minimum201(self):
    self.assertEqual(self.pol['condition_policy']['minimum_per_branch_per_route_bin'],201)

  def test_no_combinations(self):
    self.assertFalse(self.pol['condition_policy']['combined_rules_allowed'])

  def test_no_threshold_search(self):
    self.assertFalse(self.pol['condition_policy']['threshold_search_allowed'])

  def test_no_raw_rehash(self):
    self.assertIn('NO_CURRENT_RAW_FILE_REHASH',self.pol['raw_source_integrity'])

  def test_steering_rate_unavailable(self):
    self.assertEqual(self.pol['source_steering_rate'],'UNAVAILABLE_NOT_PRESERVED')

  def test_selected_only(self):
    self.assertEqual(self.pol['config'],{'family':'ARX1','delay_samples':5,'input_taps':1,'output_lags':1,'intercept':True})

  def test_history45(self):
    self.assertEqual(self.pol['history'],45)

  def test_no_tolerance(self):
    self.assertIn('NO_TOLERANCE',self.pol['mapping'])

  def test_prior_attribution_immutable_input(self):
    self.assertEqual(self.pol['attribution_result_sha256'],old.PINS['empirical-stage-a-regime-results-v1.json'])

  def test_model_branch_distinct(self):
    self.assertEqual(self.pol['condition_policy']['C6_role'],'MODEL_DERIVED_CAUSAL_ARCHITECTURE_DIAGNOSTIC')

  def test_numerical_authority_firewall(self):
    for key in ('raw_logs_opening_allowed','fitting_allowed','stage_b_analysis_allowed','rollout_allowed','holdout_opening_allowed'):
      self.assertFalse(self.pol[key])

  def test_code_bound(self):
    self.assertEqual(set(self.pol['executor_sha256']),set(c.CODE))

  def test_metric_unchanged(self):
    self.assertEqual(self.pol['metric_policy_sha256'],v.policy()['metric_policy']['receipt_sha256'])

  def test_source_profile_bound(self):
    self.assertEqual(self.pol['empirical_profile_sha256'],v.routes()[0]['empirical_profile_sha256'])

  def test_source_dbc_bound(self):
    self.assertEqual(self.pol['exact_dbc_sha256'],'1590039abb51cbfc3dc8ab4151ab78e7f549088fec878480ab4d6f850b18898a')

  def test_future_holdout_closed(self):
    self.assertEqual(self.pol['future_holdout'],'CLOSED_MISSING_ADMISSIBLE_MODEL')

  def test_calibration_unchanged(self):
    self.assertEqual(len(self.pol['calibration_blockers']),5)


if __name__=='__main__':
  unittest.main()

class TestExactConfigRepair(unittest.TestCase):
  def test_every_existing_selected_config_exact(self):
    pol=c.static_policy()
    for row in pol['selected']:
      self.assertEqual(pol['config'],row['config'])
      self.assertIs(pol['config']['intercept'],True)
