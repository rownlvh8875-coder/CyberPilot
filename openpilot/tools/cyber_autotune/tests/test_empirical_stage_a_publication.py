"""Public aggregate receipts require no private cache or source checkout."""

import unittest
from openpilot.tools.cyber_autotune import empirical_stage_a_publication as publication
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestPublishedAttribution(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.rows = publication.load()
    cls.result = cls.rows['empirical-stage-a-regime-results-v1.json']

  def test_six_receipts_pinned(self):
    self.assertEqual(len(self.rows), 6)

  def test_policy_before_analysis(self):
    self.assertEqual(self.result['policy_sha256'], self.rows['empirical-stage-a-regime-policy-v1.json']['receipt_sha256'])

  def test_actual_target_grid(self):
    data = self.result['route_fold_speed_results']
    self.assertEqual(sum(x['all']['count'] for x in data), 449426)
    self.assertTrue(all(x['target_grid']['off_grid_count'] == 0 for x in data))

  def test_selected_arx_off_grid(self):
    data = self.result['route_fold_speed_results']
    self.assertTrue(all(x['arx_prediction_grid']['off_grid_count'] == x['all']['count'] for x in data))

  def test_hypotheses_not_tuned_after_results(self):
    h = self.result['decision']['hypotheses']
    self.assertTrue(h['H1'])
    self.assertFalse(h['H2'])
    self.assertFalse(h['H3'])

  def test_unavailable_causal_conditions(self):
    row = self.rows['empirical-stage-a-causal-separator-audit-v1.json']
    self.assertEqual(row['availability']['RAW_COMMAND_CHANGED']['status'], 'UNAVAILABLE')
    self.assertFalse(row['route_consistent_separator_supported'])

  def test_each_speed_separate_equal_route(self):
    for row in self.result['equal_route_by_speed'].values():
      self.assertEqual(row['primary'], 'EQUAL_ROUTE')

  def test_private_v3_unchanged(self):
    self.assertEqual(self.result['v3_private_before_sha256'], self.result['v3_private_after_sha256'])

  def test_holdout_closed_no_model(self):
    row = self.rows['empirical-stage-a-attribution-readiness-v1.json']
    self.assertEqual(row['package_status'], 'CLOSED_MISSING_ADMISSIBLE_MODEL')
    self.assertEqual(row['holdout_opening'], 'HOLDOUT_OPENING_CLOSED')
    self.assertEqual(row['model_admission'], 'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT')

  def test_stage_b_preserved(self):
    row = self.rows['empirical-stage-a-attribution-readiness-v1.json']
    self.assertEqual(row['stage_b'], 'STAGE_B_SIGNAL_ADMISSION_BLOCKED')
    self.assertEqual(row['calibration_blockers'], p.BLOCKERS)

  def test_no_v4_contract(self):
    self.assertNotIn('empirical-stage-a-v4-architecture-contract-v1.json', self.rows)
    self.assertEqual(self.result['decision']['verdict'], 'STAGE_A_ATTRIBUTION_MIXED_OR_UNRESOLVED')

  def test_exact_repeatability(self):
    row = self.rows['empirical-stage-a-repeatability-v1.json']
    self.assertTrue(row['exact_repeatability'])
    self.assertEqual(row['runs'], 2)

  def test_contributions_reconstruct_all_routes(self):
    for row in self.result['route_fold_speed_results']:
      for name in ('mae_difference_contribution', 'mse_difference_contribution', 'rmse_difference_contribution'):
        self.assertAlmostEqual(sum(row['outcome'][x][name] for x in row['partition']), row['all'][name])

  def test_no_authority(self):
    for row in self.rows.values():
      for key in p.FIREWALL:
        self.assertIs(row[key], False)
