import copy
import unittest
from openpilot.tools.cyber_autotune import curvature_yaw_rejection as rejection
from openpilot.tools.cyber_autotune.curvature_yaw_v2_search import build_case, run_case
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


class TestRejection(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.case=build_case('sharp_mid_left',{'factor_high_fraction':0.,'friction_high_fraction':0.},role='STRESS')
    cls.report=run_case(cls.case,expected_manifest_sha256=digest(canonical(cls.case['manifest'])))

  def test_case_ledger_is_complete_and_repeatable(self):
    rows=rejection.case_ledger(self.report)
    self.assertEqual(len(rows),21)
    self.assertEqual(rows,rejection.case_ledger(copy.deepcopy(self.report)))
    self.assertEqual(len({r['violation_id'] for r in rows}),21)
    for r in rows:
      self.assertEqual(r['values']['UPSTREAM_BASELINE'],r['values']['CYBER_CURRENT'])
      self.assertGreater(r['violation_magnitude'],0)
      self.assertEqual(r['threshold'],r['values']['CYBER_CANDIDATE_V1'])
      self.assertTrue(r['step_indexes'])
      self.assertEqual(r['speed_range_mps'],[17.5,17.5])
      self.assertEqual(len(r['dynamics']),4)
      self.assertTrue(all('zero_crossing_steps' in context and 'reversal_steps' in context for context in r['dynamics'].values()))

  def test_clusters_cover_every_violation_without_metric_direction_change(self):
    rows=rejection.case_ledger(self.report)
    clusters=rejection.cluster(rows)
    self.assertEqual(clusters,rejection.cluster(rows))
    self.assertEqual(set(sum((c['violation_ids'] for c in clusters),[])),{r['violation_id'] for r in rows})
    self.assertTrue(all(r['delta_vs_v1']==r['violation_magnitude'] for r in rows))

  def test_rehashed_native_tamper_and_summary_only_fail_closed(self):
    bad=copy.deepcopy(self.report)
    bad['arms'][3]['samples'][80]['requested_torque']*=.99
    bad['arms'][3]['samples_sha256']=digest(canonical(bad['arms'][3]['samples']))
    bad['receipt_sha256']=digest(canonical({k:v for k,v in bad.items() if k!='receipt_sha256'}))
    with self.assertRaises(ValueError):
      rejection.case_ledger(bad)
    with self.assertRaises((ValueError,KeyError)):
      rejection.build_ledger([],{},{})

  def test_policy_and_ablation_manifest_freeze(self):
    policy=rejection.load_policy()
    cases,freeze=rejection.freeze_ablations()
    self.assertEqual(len(cases),8)
    self.assertEqual(freeze['native_runs'],64)
    self.assertEqual(len(set(freeze['manifest_sha256'])),8)
    self.assertEqual(len(policy['ablations']),4)
    with self.assertRaises(ValueError):
      rejection.load_policy(b'{}')

  def test_family_decision_requires_complete_ordered_admitted_cases(self):
    with self.assertRaises(ValueError):
      rejection.decide_family([self.report],{})

  def test_each_passive_observation_must_match_prefrozen_source(self):
    freeze={'diagnostic_producer_source_sha256':'a'*64,'diagnostic_supervisor_source_sha256':'b'*64}
    observed={'producer_source_sha256':'a'*64,'supervisor_source_sha256':'b'*64}
    rejection.validate_observation_freeze(observed,freeze)
    for key in observed:
      bad=dict(observed,**{key:'c'*64})
      with self.assertRaises(ValueError):
        rejection.validate_observation_freeze(bad,freeze)
