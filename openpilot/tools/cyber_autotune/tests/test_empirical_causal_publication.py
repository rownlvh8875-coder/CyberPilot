"""Pinned additive evidence and negative publication controls."""
import copy
import unittest
from openpilot.tools.cyber_autotune import empirical_causal_publication as c
from openpilot.tools.cyber_autotune import empirical_causal_recovery as r
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestCausalPublication(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.rows=c.load()

  def test_required_artifacts(self):
    self.assertGreaterEqual(len(self.rows),7)

  def test_exact_mapping_all_six(self):
    rows=self.rows['empirical-stage-a-row-origin-map-v1.json']['scopes']
    self.assertEqual(len(rows),6)
    self.assertEqual(sum(x['count'] for x in rows),449426)
    self.assertTrue(all(x['target_design_prediction_previous_order_exact'] for x in rows))

  def test_input_trees_unchanged(self):
    row=self.rows['empirical-stage-a-causal-condition-results-v1.json']
    self.assertEqual(row['input_trees_before_sha256'],row['input_trees_after_sha256'])

  def test_split_frozen_before_cache(self):
    self.assertIs(self.rows['empirical-stage-a-causal-recovery-policy-v1.json']['numeric_cache_deserialized_before_freeze'],False)

  def test_six_single_conditions(self):
    row=self.rows['empirical-stage-a-causal-condition-results-v1.json']
    for scope in row['route_fold_speed_results']:
      self.assertEqual(set(scope['conditions']),{'C'+str(i) for i in range(1,7)})

  def test_strict_only_selector(self):
    row=self.rows['empirical-stage-a-causal-condition-results-v1.json']
    self.assertEqual(set(row['selector_diagnostics']),set(row['decision']['strict_pass_conditions']))

  def test_rate_unavailable(self):
    self.assertEqual(self.rows['empirical-stage-a-causal-context-availability-v1.json']['source_steering_rate'],'UNAVAILABLE_NOT_PRESERVED')

  def test_limit_unknown(self):
    row=self.rows['empirical-stage-a-causal-context-availability-v1.json']
    self.assertIsNone(row['safety_limited'])
    self.assertIsNone(row['curvature_limited'])

  def test_alias_not_independent_evidence(self):
    self.assertTrue(self.rows['empirical-stage-a-causal-context-availability-v1.json']['raw_normalized_equivalence'])

  def test_model_not_admitted(self):
    self.assertEqual(self.rows['empirical-stage-a-causal-separator-readiness-v1.json']['model_admission'],'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT')

  def test_no_authority(self):
    for row in self.rows.values():
      for key in p.FIREWALL:
        self.assertFalse(row[key])

  def test_holdout_closed(self):
    self.assertEqual(self.rows['empirical-stage-a-causal-separator-readiness-v1.json']['holdout_opening'],'HOLDOUT_OPENING_CLOSED')

  def test_stage_b_unchanged(self):
    self.assertEqual(self.rows['empirical-stage-a-causal-separator-readiness-v1.json']['stage_b'],'STAGE_B_SIGNAL_ADMISSION_BLOCKED')

  def test_calibration_unchanged(self):
    self.assertEqual(self.rows['empirical-stage-a-causal-separator-readiness-v1.json']['calibration_blockers'],p.BLOCKERS)

  def test_exact_two_repeats(self):
    row=self.rows['empirical-stage-a-causal-repeatability-v1.json']
    self.assertEqual(row['runs'],2)
    self.assertIs(row['exact_repeatability'],True)

  def test_wrong_policy_result_rejected(self):
    rows=copy.deepcopy(self.rows)
    rows['empirical-stage-a-causal-condition-results-v1.json']['policy_sha256']='0'*64
    with self.assertRaisesRegex(ValueError,'CHAIN_DRIFT'):
      c.validate_chain(rows)

  def test_wrong_order_rejected(self):
    rows=copy.deepcopy(self.rows)
    rows['empirical-stage-a-causal-condition-results-v1.json']['route_fold_speed_results'].reverse()
    with self.assertRaisesRegex(ValueError,'ORDER_DRIFT'):
      c.validate_chain(rows)

  def test_selector_for_failed_condition_rejected(self):
    rows=copy.deepcopy(self.rows)
    rows['empirical-stage-a-causal-condition-results-v1.json']['selector_diagnostics']['UNKNOWN']=[]
    with self.assertRaisesRegex(ValueError,'SELECTOR'):
      c.validate_chain(rows)

  def test_public_indices_rejected(self):
    with self.assertRaises(ValueError):
      r.validate_public({'aligned_row_index':1})

  def test_private_path_rejected(self):
    with self.assertRaises(ValueError):
      r.validate_public({'private_path':'redacted'})

  def test_future_schema_does_not_rebuild_history(self):
    row=self.rows['empirical-causal-context-schema-v1.json']
    self.assertEqual(row['scope'],'FUTURE_GENERATIONS_ONLY')
    self.assertFalse(row['historical_regeneration_allowed'])
