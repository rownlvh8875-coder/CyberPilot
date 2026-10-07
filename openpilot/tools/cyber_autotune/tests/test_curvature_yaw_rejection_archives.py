import copy
import tempfile
import unittest
from pathlib import Path
from openpilot.tools.cyber_autotune.curvature_yaw_rejection_export import read,request_for_report
from openpilot.tools.cyber_autotune.curvature_yaw_v2_search import ROOT,build_case,POLICY_SHA
from openpilot.tools.cyber_autotune.curvature_yaw_candidate_history import validate_history
from openpilot.tools.cyber_autotune.native_protocol import canonical,digest


class TestRejectionArchives(unittest.TestCase):
  def artifact(self,name):
    return read(ROOT/'docs/cyberpilot/changes'/name)

  def test_all_37_original_violations_and_clusters_are_preserved(self):
    ledger=self.artifact('candidate-v2-violation-ledger.json')
    self.assertEqual(ledger['violation_count'],37)
    self.assertEqual(len(ledger['violations']),37)
    self.assertEqual(len({r['violation_id'] for r in ledger['violations']}),37)
    self.assertEqual(sum(c['count'] for c in ledger['clusters']),37)
    self.assertEqual(ledger['original_policy_sha256'],POLICY_SHA)
    self.assertEqual(ledger['receipt_sha256'],digest(canonical({k:v for k,v in ledger.items() if k!='receipt_sha256'})))
    for r in ledger['violations']:
      self.assertEqual(r['values']['UPSTREAM_BASELINE'],r['values']['CYBER_CURRENT'])
      self.assertEqual(r['values']['CYBER_CANDIDATE_V2']-r['threshold'],r['violation_magnitude'])

  def test_family_no_go_and_stress_do_not_resurrect_rejection(self):
    decision=self.artifact('candidate-family-decision.json')
    self.assertEqual(decision['verdict'],'FAMILY_REDESIGN')
    self.assertEqual([r['failure_count'] for r in decision['ablation_results']],[37,39,17,8])
    self.assertEqual(decision['v2_status'],'REJECTED')
    self.assertFalse(decision['v3_created'])
    self.assertFalse(decision['selection_permitted'])

  def test_immutable_history_and_capability_boundary(self):
    ledger=self.artifact('candidate-history-ledger.json')
    validate_history(ledger['history'])
    self.assertEqual([r['entry']['candidate'] for r in ledger['history']],['BASELINE','CURRENT','V1','V2'])
    self.assertEqual(ledger['history'][-1]['entry']['status'],'REJECTED')
    analysis=self.artifact('candidate-v2-dynamics-attribution.json')
    self.assertFalse(analysis['capability_boundary']['model_planner_executed'])
    self.assertEqual(len(analysis['root_cause_assessments']),15)
    self.assertTrue(all(all(e['unchanged_observables'].values()) for e in analysis['dynamics_evidence']))

  def test_historical_request_restores_source_without_mutating_report(self):
    case=build_case('sharp_mid_left',{'factor_high_fraction':0.,'friction_high_fraction':0.},role='STRESS')
    report={'manifest':copy.deepcopy(case['manifest'])}
    request=request_for_report(report,3)
    self.assertEqual(request,case['requests'][3])
    request['controller']['config']['points'][0][1]+=1
    self.assertEqual(report['manifest'],case['manifest'])

  def test_export_json_duplicates_nonfinite_and_size_fail_closed(self):
    with tempfile.TemporaryDirectory() as directory:
      path=Path(directory)/'input.json'
      for raw in (b'{"a":1,"a":2}',b'{"a":NaN}',b'',b'x'*(32*1024*1024+1)):
        path.write_bytes(raw)
        with self.assertRaises(ValueError):
          read(path)

  def test_matrix_and_original_ledger_must_be_linked(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_rejection_export import validate_evidence_linkage
    ledger={'receipt_sha256':'a'*64}
    matrix={'original_ledger_sha256':'b'*64,'native_runs':64,'scope':'POST_EVALUATION_EXPLANATORY_DIAGNOSTICS_NOT_SELECTION'}
    with self.assertRaises(ValueError):
      validate_evidence_linkage(ledger,matrix,[],[])

  def test_persisted_ablation_cannot_replace_historical_dynamics(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_rejection_export import validate_evidence_linkage
    ledger={'receipt_sha256':'a'*64}
    matrix={'original_ledger_sha256':'a'*64,'native_runs':64,'scope':'POST_EVALUATION_EXPLANATORY_DIAGNOSTICS_NOT_SELECTION'}
    original=[{'manifest':{'scenario':name},'arms':[{'samples':[0]}]*4} for name in ('sharp_mid_left','speed_sweep')]
    changed=copy.deepcopy(original)
    changed[0]['arms'][3]['samples']=[1]
    with self.assertRaises(ValueError):
      validate_evidence_linkage(ledger,matrix,original,changed)
