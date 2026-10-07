"""Frozen native search gates, identities and diagnostic signs."""
import copy
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune.curvature_yaw_v2_search import (
  POLICY_SHA, IDENTITY_FIELDS, load_policy, configurations, candidate_spec, identity,
  build_case, run_case, validate_report, summarize, compare_summary, select_development, classify,
)
from openpilot.tools.cyber_autotune.curvature_yaw_candidate import effective_parameters
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


class TestV2Search(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.config=configurations()[0]
    cls.case=build_case('gentle_high_left',cls.config,role='DEVELOPMENT')
    cls.report=run_case(cls.case,expected_manifest_sha256=digest(canonical(cls.case['manifest'])))

  def test_policy_is_prefrozen_and_roles_disjoint(self):
    policy=load_policy()
    self.assertEqual(POLICY_SHA, '7bc06b4f58d72a623cc6966b2fa7e6e4048243c457276323a8961309a39ebe96')
    self.assertEqual(len(configurations()),9)
    self.assertFalse(set(policy['development'])&set(policy['evaluation']))
    with self.assertRaises(ValueError):
      load_policy(b'{}')

  def test_full_identity_every_component_changes(self):
    fields=dict.fromkeys(IDENTITY_FIELDS,'a'*64)
    for field in fields:
      other=dict(fields,**{field:'b'*64})
      self.assertNotEqual(identity(fields),identity(other))
    with self.assertRaises(ValueError):
      identity({**fields,'unexpected':'c'*64})

  def test_low_mid_retained_high_is_native_parameters(self):
    low=build_case('gentle_low_left',self.config,role='DEVELOPMENT')
    mid=build_case('gentle_mid_left',self.config,role='DEVELOPMENT')
    for case in (low,mid):
      self.assertEqual(effective_parameters(case['requests'][2]),effective_parameters(case['requests'][3]))
    self.assertEqual(effective_parameters(self.case['requests'][0]),effective_parameters(self.case['requests'][3]))

  def test_v1_preserved_and_no_artificial_output_or_physical_queue(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_screening import CANDIDATE
    self.assertEqual(self.case['requests'][2]['controller'],CANDIDATE)
    self.assertEqual(self.case['manifest']['physical_delay_owner'],'PLANT')
    self.assertFalse(self.case['manifest']['controller_physical_delay_queue_present'])
    self.assertNotEqual(candidate_spec(self.config),candidate_spec(configurations()[-1]))

  def test_native_repeat_and_alias_and_diagnostic_delta(self):
    r=self.report
    self.assertEqual(r['executed_runs'],8)
    self.assertEqual(r['arms'][0]['samples'],r['arms'][1]['samples'])
    self.assertEqual(r['arms'][0]['samples'],r['arms'][3]['samples'])
    self.assertNotEqual(r['arms'][0]['samples'],r['arms'][2]['samples'])
    self.assertTrue(all(a['repetition_result_sha256'][0]==a['repetition_result_sha256'][1] for a in r['arms']))
    self.assertFalse(compare_summary(summarize(r))['failures'])

  def test_no_workers_on_config_manifest_drift(self):
    bad=copy.deepcopy(self.case)
    bad['requests'][3]['controller']['config']['points'][3][1]+=1/128
    with patch('openpilot.tools.cyber_autotune.curvature_yaw_v2_search.run_native_transcript') as worker:
      with self.assertRaises(ValueError):
        run_case(bad,expected_manifest_sha256=digest(canonical(bad['manifest'])))
      worker.assert_not_called()

  def test_source_identity_and_diagnostics_tamper_rejected(self):
    for edit in ('physical','identity','metric','truth'):
      r=copy.deepcopy(self.report)
      if edit=='physical':
        r['arms'][3]['samples'][200]['applied_normalized_torque']*=-1
        r['arms'][3]['samples_sha256']=digest(canonical(r['arms'][3]['samples']))
      elif edit=='identity':
        r['manifest']['identities'][3]['components']['plant_sha256']='a'*64
        r['manifest_sha256']=digest(canonical(r['manifest']))
      elif edit=='metric':
        r['arms'][3]['groups'][0]['command_derivative_rms_per_s']=-1
      else:
        r['performance_qualified']=True
      r['receipt_sha256']=digest(canonical({k:v for k,v in r.items() if k!='receipt_sha256'}))
      with self.assertRaises(ValueError):
        validate_report(r)

  def test_selection_rejects_eval_leakage_and_incomplete_enumeration(self):
    with self.assertRaises(ValueError):
      select_development([])
    policy=load_policy()
    entries=[]
    summary=summarize(self.report)
    for config in configurations():
      cases=[dict(copy.deepcopy(summary),scenario=name,config=config,role='EVALUATION') for name in policy['development']]
      entries.append({'config':config,'cases':cases,'hard_pass':True})
    with self.assertRaises(ValueError):
      select_development(entries)

  def test_metric_orientation_no_weighted_compensation(self):
    s=summarize(self.report)
    self.assertIsNot(s['groups'][3],self.report['arms'][3]['groups'])
    s['groups'][3][0]['reversals']=s['groups'][0][0]['reversals']+1
    with self.assertRaises(ValueError):
      compare_summary(s)
    with self.assertRaises(ValueError):
      classify([s])

  def test_deterministic_pareto_ties_and_hard_failure_not_compensated(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_v2_search import _pareto_choice
    receipts=[{'config':c,'vector':[1.,2.],'eligible':True,'receipt_sha256':digest(canonical(c))}
              for c in configurations()]
    self.assertEqual(_pareto_choice(receipts),_pareto_choice(copy.deepcopy(receipts)))
    self.assertEqual(_pareto_choice(receipts)[1]['config'],configurations()[0])
    receipts[0]['eligible']=False
    self.assertNotEqual(_pareto_choice(receipts)[1]['config'],configurations()[0])
    receipts[2]['vector']=[0.,2.]
    self.assertEqual(_pareto_choice(receipts)[1]['config'],configurations()[2])

  def test_hard_worker_failure_is_immediate(self):
    with patch('openpilot.tools.cyber_autotune.curvature_yaw_v2_search.run_native_transcript',
               return_value={'status':'TIMEOUT'}) as worker:
      with self.assertRaisesRegex(ValueError,'HARD_WORKER_FAILURE'):
        run_case(self.case,expected_manifest_sha256=digest(canonical(self.case['manifest'])))
      self.assertEqual(worker.call_count,1)

  def test_repeat_hashes_must_bind_retained_native_response_and_replay(self):
    r=copy.deepcopy(self.report)
    r['arms'][3]['repetition_result_sha256']=['a'*64]*2
    r['arms'][3]['repetition_replay_envelope_sha256']=['b'*64]*2
    r['receipt_sha256']=digest(canonical({k:v for k,v in r.items() if k!='receipt_sha256'}))
    with self.assertRaises(ValueError):
      validate_report(r)

  def test_classification_cannot_trust_mutable_or_empty_summary_groups(self):
    s=summarize(self.report)
    s['groups']=[[],[],[],[]]
    with self.assertRaises(ValueError):
      classify([s])

  def test_attribution_dependency_and_live_spec_are_frozen(self):
    from openpilot.tools.cyber_autotune import curvature_yaw_attribution as attribution
    with patch.object(attribution,'DT_S',.02),patch('openpilot.tools.cyber_autotune.curvature_yaw_v2_search.run_native_transcript') as worker:
      with self.assertRaises(ValueError):
        run_case(self.case,expected_manifest_sha256=digest(canonical(self.case['manifest'])))
      worker.assert_not_called()

  def test_final_classification_requires_frozen_selection_context(self):
    with self.assertRaisesRegex(ValueError,'FROZEN_SELECTION_CONTEXT_REQUIRED'):
      classify([self.report])
    with self.assertRaises(ValueError):
      build_case('gentle_high_right',self.config,role='EVALUATION',selection_sha256='invalid')

  def test_complete_selection_and_evaluation_context_cannot_mix_configs(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_v2_search import _development_vector_size, validate_selection
    receipts=[]
    for i,c in enumerate(configurations()):
      r={'config':c,'eligible':i==0,'hard_pass':i==0,'case_receipts':['a'*64]*4,
         'failures':[],'vector':[1.]*_development_vector_size() if i==0 else []}
      r['receipt_sha256']=digest(canonical(r))
      receipts.append(r)
    selection={'version':1,'policy_sha256':POLICY_SHA,'selection_role':'DEVELOPMENT_ONLY','candidate_count':9,
               'receipts':receipts,'pareto_receipts':[receipts[0]['receipt_sha256']],
               'selected_config':configurations()[0],'selected_receipt_sha256':receipts[0]['receipt_sha256'],
               'performance_qualified':False,'real_performance_status':'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE'}
    selection['receipt_sha256']=digest(canonical(selection))
    validate_selection(selection,selection['receipt_sha256'])
    failures=[]
    for name in load_policy()['evaluation']:
      r={'scenario':name,'role':'EVALUATION','selection_sha256':selection['receipt_sha256'],
         'perturbation':{},'config':configurations()[0],'manifest_sha256':'b'*64,
         'status':'HARD_REJECTED','hard_pass':False,'reason':'UNIT_SIMULATED_TIMEOUT','performance_qualified':False}
      r['receipt_sha256']=digest(canonical(r))
      failures.append(r)
    kwargs={'selection':selection,'expected_selection_sha256':selection['receipt_sha256'],
            'expected_evaluation_sha256':digest(canonical(['b'*64]*11))}
    self.assertEqual(classify(failures,**kwargs)['status'],'REJECTED')
    failures[0]['config']=configurations()[1]
    failures[0]['receipt_sha256']=digest(canonical({k:v for k,v in failures[0].items() if k!='receipt_sha256'}))
    with self.assertRaisesRegex(ValueError,'UNSELECTED'):
      classify(failures,**kwargs)
    bad=copy.deepcopy(selection)
    bad['receipts'][0]['vector']=[1.]
    bad['receipts'][0]['receipt_sha256']=digest(canonical({k:v for k,v in bad['receipts'][0].items() if k!='receipt_sha256'}))
    bad['receipt_sha256']=digest(canonical({k:v for k,v in bad.items() if k!='receipt_sha256'}))
    with self.assertRaises(ValueError):
      validate_selection(bad,bad['receipt_sha256'])

  def test_stress_and_role_outside_policy_rejected(self):
    for arguments in (
      {'role':'DEVELOPMENT','perturbation':{'delay_steps':1}},
      {'role':'STRESS','perturbation':{'delay_steps':9}},
      {'role':'STRESS','perturbation':{'delay_steps':1,'roll_rad':.002}},
      {'role':'EVALUATION'},
    ):
      with self.assertRaises(ValueError):
        build_case('gentle_high_left',self.config,**arguments)

if __name__=='__main__':
  unittest.main()
