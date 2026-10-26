"""Public pin chains, directional gates and immutable historical evidence."""
import copy
import unittest
from openpilot.tools.cyber_autotune import empirical_grid_publication as pub
from openpilot.tools.cyber_autotune import empirical_grid_analysis as g
from openpilot.tools.cyber_autotune import empirical_grid_emission as e


class TestPublication(unittest.TestCase):
  def test_exact_public_chain(self):
    rows=pub.load()
    self.assertEqual(len(rows),4 if rows[pub.RESULT]['decision']['verdict']!='SOURCE_GRID_OBSERVATION_REVIEW_POSSIBLE' else 5)

  def test_six_scopes_same_support_and_exact_adjudication(self):
    result=pub.load()[pub.RESULT]
    g.require_scopes(result['scopes'])
    self.assertEqual(g.adjudicate(result['scopes']),result['decision'])
    self.assertEqual(sum(x['count'] for x in result['scopes']),449426)
    for x in result['scopes']:
      self.assertTrue(x['exact_same_support'])
      for a in x['arms'].values():
        self.assertEqual(a['count'],x['count'])
        self.assertEqual(a['coverage'],{'valid':x['count'],'total':x['count'],'unavailable':0})

  def test_old_pins_and_private_trees_preserved(self):
    rows=pub.load()
    self.assertEqual(rows[pub.RESULT]['input_trees_before_sha256'],rows[pub.RESULT]['input_trees_after_sha256'])
    self.assertEqual(rows[pub.RESULT]['input_trees_before_sha256'],rows[pub.POLICY]['input_tree_sha256'])
    self.assertEqual(set(rows[pub.POLICY]['input_tree_sha256']),set(e.NAMES))

  def test_all_arms_and_metrics_present(self):
    for x in pub.load()[pub.RESULT]['scopes']:
      self.assertEqual(set(x['arms']),set(g.ARMS))
      for a in x['arms'].values():
        for key in ('RMSE','MAE','P95_ABS','MEDIAN_ABS','BIAS','CORRELATION','MAX_ABS',
                    'exact_target_hit_count','exact_target_hit_rate','error_below_half_quantum_count',
                    'error_at_most_one_quantum_count'):
          self.assertIn(key,a)

  def test_closed_holdout_and_stage_b_unchanged(self):
    row=pub.load()[pub.READY]
    self.assertEqual(row['holdout_opening'],'HOLDOUT_OPENING_CLOSED')
    self.assertEqual(row['package_status'],'CLOSED_MISSING_ADMISSIBLE_MODEL')
    self.assertEqual(row['model_admission'],'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT')
    self.assertEqual(row['stage_b'],'STAGE_B_SIGNAL_ADMISSION_BLOCKED')
    self.assertEqual(row['historical_additive_states']['causal_recovery'],'CAUSAL_CONTEXT_RECOVERED_PARTIAL')
    self.assertEqual(row['historical_additive_states']['attribution'],'STAGE_A_ATTRIBUTION_MIXED_OR_UNRESOLVED')

  def test_no_forbidden_execution(self):
    row=pub.load()[pub.RESULT]
    for k in ('refit','selector','rollout','raw_opening','stage_b'):
      self.assertEqual(row[k],'NOT_RUN')
    ready=pub.load()[pub.READY]
    self.assertFalse(ready['ta_execution'])
    self.assertFalse(ready['sg_execution'])
    self.assertFalse(ready['composition_authorized'])
    self.assertFalse(ready['production_authority'])
    self.assertFalse(ready['candidate_search_authorized'])

  def test_repeatability_full_projection_and_firewall(self):
    row=pub.load()[pub.REPEAT]
    self.assertEqual(row['runs'],2)
    self.assertTrue(row['exact_repeatability'])
    for k in ('raw_decoder_forced_exception','raw_path_forced_exception','whole_process_succeeded'):
      self.assertTrue(row[k])
    self.assertIn('FLOAT32_EMISSION_BYTES',row['compared'])

  def test_equal_route_summary_exact(self):
    result=pub.load()[pub.RESULT]
    for b in g.BINS:
      self.assertEqual(result['equal_route_by_speed'][b],g.aggregate([x for x in result['scopes'] if x['speed_bin']==b]))

  def test_one_fixed_projection_no_search(self):
    row=pub.load()[pub.POLICY]
    g.require_grid(row['grid'])
    self.assertEqual(row['projection_count'],1)
    self.assertEqual(row['projection_search'],'PROHIBITED')
    self.assertFalse(row['arrays_deserialized_before_freeze'])

  def test_targets_not_changed_and_range_not_clipped(self):
    for row in pub.load()[pub.RESULT]['scopes']:
      self.assertEqual(row['target_grid']['off_grid_count'],0)
      self.assertEqual(row['emission']['source_range_violation_count'],0)

  def test_tampered_chain_rejected(self):
    for name,key in ((pub.RESULT,'policy_sha256'),(pub.READY,'result_sha256'),(pub.REPEAT,'result_sha256')):
      rows=copy.deepcopy(pub.load())
      rows[name][key]='0'*64
      with self.subTest(name=name),self.assertRaises(ValueError):
        pub.validate_chain(rows)

  def test_tampered_support_or_gate_rejected(self):
    for key,val in (('count',1),('gate',{'passed':True,'failures':[]})):
      rows=copy.deepcopy(pub.load())
      rows[pub.RESULT]['scopes'][0][key]=val
      with self.subTest(key=key),self.assertRaises(ValueError):
        pub.validate_chain(rows)

  def test_outcomes_cannot_authorize_rule_or_gate(self):
    rows=pub.load()
    for scope in rows[pub.RESULT]['scopes']:
      self.assertEqual(scope['outcome_role'],'EXPLANATION_ONLY_NEVER_RULE_SELECTION_OR_GATE')
      self.assertEqual(scope['gate'],g.gate(scope))
    self.assertEqual(rows[pub.POLICY]['metric_extension']['outcome'],'EXISTING_PARTITIONS_EXPLANATION_ONLY_NEVER_RULE_OR_GATE')

  def test_contract_conditional(self):
    rows=pub.load()
    self.assertEqual(pub.CONTRACT in rows,rows[pub.RESULT]['decision']['strict_pass_scopes']==6)


if __name__=='__main__':
  unittest.main()
