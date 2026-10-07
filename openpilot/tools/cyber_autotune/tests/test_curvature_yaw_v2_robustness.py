"""Deterministic synthetic sensitivity, not calibrated vehicle uncertainty."""
import unittest
from unittest.mock import patch

from openpilot.tools.cyber_autotune.curvature_yaw_v2_robustness import matrix, freeze_matrix, aggregate_case
from openpilot.tools.cyber_autotune.curvature_yaw_v2_search import configurations, build_case, run_case, load_policy
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


class TestV2Robustness(unittest.TestCase):
  def test_matrix_prefrozen_bounded_deterministic(self):
    cases=matrix()
    self.assertEqual(cases,matrix())
    self.assertEqual(len(cases),23)
    self.assertEqual(cases[0]['perturbation'],{})
    self.assertEqual(len({canonical(c) for c in cases}),23)
    for case in cases[1:]:
      self.assertEqual(len(case['perturbation']),1)
      axis,value=next(iter(case['perturbation'].items()))
      self.assertIn(value,load_policy()['robustness']['axes'][axis]['choices'])

  def test_every_stress_changes_full_candidate_identity(self):
    cases,hashes=freeze_matrix(configurations()[0])
    nominal=cases[0]['manifest']['identities'][3]['candidate_identity_sha256']
    self.assertEqual(len(set(hashes)),23)
    for case in cases[1:]:
      self.assertNotEqual(case['manifest']['identities'][3]['candidate_identity_sha256'],nominal)

  def test_delay_owner_and_reset_fifo_length_agree(self):
    cases,_=freeze_matrix(configurations()[0])
    for case in cases:
      r=case['requests'][0]
      self.assertEqual(len(r['initial_state']['command_history']),r['plant_config']['delay_steps'])
      self.assertEqual(case['manifest']['physical_delay_owner'],'PLANT')
      self.assertFalse(case['manifest']['controller_physical_delay_queue_present'])

  def test_pose_offset_never_enters_controller_inputs(self):
    c=configurations()[0]
    nominal=build_case('sharp_high_left',c,role='STRESS')
    shifted=build_case('sharp_high_left',c,role='STRESS',perturbation={'initial_pose_y_m':.01})
    self.assertEqual(nominal['requests'][3]['native']['frames'],shifted['requests'][3]['native']['frames'])
    self.assertEqual(nominal['requests'][3]['controller'],shifted['requests'][3]['controller'])
    self.assertNotEqual(nominal['manifest']['identities'][3]['components']['reset_sha256'],
                        shifted['manifest']['identities'][3]['components']['reset_sha256'])

  def test_cp_software_friction_reanchors_both_candidates(self):
    case=build_case('sharp_high_left',configurations()[0],role='STRESS',
                    perturbation={'cp_friction_fraction':1+1/128})
    self.assertEqual(case['requests'][2]['controller']['config']['points'][0][2],
                     case['requests'][3]['controller']['config']['points'][0][2])
    self.assertNotEqual(case['manifest']['car_params_sha256'],
                        build_case('sharp_high_left',configurations()[0],role='STRESS')['manifest']['car_params_sha256'])

  def test_hard_failure_dominates_aggregate(self):
    failure={'scenario':'sharp_high_left','role':'STRESS','selection_sha256':None,'perturbation':{},
             'config':configurations()[0],'manifest_sha256':'a'*64,'status':'HARD_REJECTED',
             'hard_pass':False,'reason':'TIMEOUT','performance_qualified':False}
    failure['receipt_sha256']=digest(canonical(failure))
    result=aggregate_case(failure)
    self.assertEqual(result['hard_pass_count'],0)
    self.assertEqual(result['hard_failure_count'],1)
    self.assertEqual(result['status'],'REJECTED')
    self.assertFalse(result['performance_qualified'])

  def test_actual_perturbed_native_repeatability_public_replay(self):
    case=build_case('reengage_high',configurations()[0],role='STRESS',perturbation={'pressed_shift_steps':1})
    report=run_case(case,expected_manifest_sha256=digest(canonical(case['manifest'])))
    result=aggregate_case(report)
    self.assertEqual(result['hard_pass_count'],1)
    self.assertEqual(report['arms'][0]['samples'],report['arms'][3]['samples'])
    self.assertTrue(any(r['pressed_to_release'] for r in report['arms'][3]['samples']))

  def test_non_nominal_delay_native_repeat_and_persisted_admission(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_v2_search import validate_report
    for delay in (1,3):
      with self.subTest(delay=delay):
        case=build_case('sharp_high_left',configurations()[0],role='STRESS',perturbation={'delay_steps':delay})
        report=run_case(case,expected_manifest_sha256=digest(canonical(case['manifest'])))
        validate_report(report)
        self.assertEqual(aggregate_case(report)['hard_pass_count'],1)
        self.assertEqual(report['arms'][0]['samples'],report['arms'][3]['samples'])

  def test_stress_cannot_promote_final_evaluation_rejection(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_v2_robustness import bind_evaluation, bind_final_status
    from openpilot.tools.cyber_autotune.curvature_yaw_v2_search import POLICY_SHA, _development_vector_size
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
    reports=[]
    for name in load_policy()['evaluation']:
      r={'scenario':name,'role':'EVALUATION','selection_sha256':selection['receipt_sha256'],
         'perturbation':{},'config':configurations()[0],'manifest_sha256':'b'*64,
         'status':'HARD_REJECTED','hard_pass':False,'reason':'UNIT_SIMULATED_TIMEOUT','performance_qualified':False}
      r['receipt_sha256']=digest(canonical(r))
      reports.append(r)
    freeze={'selection_sha256':selection['receipt_sha256'],'manifest_sha256':['b'*64]*11}
    context=bind_evaluation(selection,reports,freeze)
    diagnostic={'status':'SCREENING_IMPROVED','hard_failure_count':0,'receipt_sha256':'c'*64}
    result=bind_final_status(diagnostic,context)
    self.assertEqual(result['status'],'REJECTED')
    self.assertEqual(result['stress_screen_status'],'SCREENING_IMPROVED')
    self.assertEqual(result['selected_candidate_status'],'REJECTED')
    for bad in (dict(freeze,selection_sha256='c'*64),dict(freeze,manifest_sha256=['b'*64]*10)):
      with self.assertRaises(ValueError):
        bind_evaluation(selection,reports,bad)
    with self.assertRaises(ValueError):
      bind_evaluation(selection,list(reversed(reports)),freeze)

  def test_matrix_missing_reordered_and_anchor_drift_fail_closed(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_v2_robustness import aggregate
    # Boundary rejects caller summaries before they can claim matrix completeness.
    with patch('openpilot.tools.cyber_autotune.curvature_yaw_v2_robustness.bind_evaluation',return_value={}),patch(
      'openpilot.tools.cyber_autotune.curvature_yaw_v2_robustness.validate_selection'):
      for reports in ([],[{}]):
        with self.assertRaises(ValueError):
          aggregate(reports,selection={'selected_config':configurations()[0]},expected_selection_sha256='a'*64,
                    expected_matrix_sha256='b'*64,evaluation_reports=[],evaluation_freeze={})

  def test_full_failure_matrix_requires_exact_order_coverage_and_anchor(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_v2_robustness import aggregate
    # Synthetic failure receipts exercise completeness without inventing successful metrics.
    config=configurations()[0]
    sha='a'*64
    reports=[]
    for i,case in enumerate(matrix()):
      r={**case,'role':'STRESS','selection_sha256':sha,'config':config,
         'manifest_sha256':digest(canonical({'case':case,'index':i})),
         'status':'HARD_REJECTED','hard_pass':False,'reason':'UNIT_SIMULATED_TIMEOUT','performance_qualified':False}
      r['receipt_sha256']=digest(canonical(r))
      reports.append(r)
    anchor=digest(canonical([r['manifest_sha256'] for r in reports]))
    selection={'selected_config':config}
    context={'evaluation_verdict':{'status':'REJECTED'}}
    kwargs={'selection':selection,'expected_selection_sha256':sha,'expected_matrix_sha256':anchor,
            'evaluation_reports':[],'evaluation_freeze':{}}
    # Only selection/EVAL admission mocked; matrix scope, ordering, config and anchor are real.
    with patch('openpilot.tools.cyber_autotune.curvature_yaw_v2_robustness.bind_evaluation',return_value=context),patch(
      'openpilot.tools.cyber_autotune.curvature_yaw_v2_robustness.validate_selection'):
      self.assertEqual(aggregate(reports,**kwargs)['hard_failure_count'],23)
      for bad in (reports[:-1],list(reversed(reports))):
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_OR_UNSELECTED'):
          aggregate(bad,**kwargs)
      with self.assertRaisesRegex(ValueError,'INCOMPLETE_OR_UNSELECTED'):
        aggregate(reports,**{**kwargs,'expected_matrix_sha256':'b'*64})
      with self.assertRaisesRegex(ValueError,'INCOMPLETE_OR_UNSELECTED'):
        aggregate(reports,**{**kwargs,'expected_selection_sha256':'b'*64})

  def test_timing_shift_updates_phase_and_controls_together(self):
    p=build_case('reengage_high',configurations()[0],role='STRESS',perturbation={'reengage_shift_steps':1})
    self.assertFalse(p['requests'][0]['native']['frames'][230]['active'])
    self.assertEqual(p['phases'][230],'inactive')
    self.assertTrue(p['requests'][0]['native']['frames'][231]['active'])
    self.assertEqual(p['phases'][231],'reengagement')

if __name__=='__main__':
  unittest.main()
