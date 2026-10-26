import copy
import unittest
from openpilot.tools.cyber_autotune import curvature_yaw_diagnostics as diagnostic
from openpilot.tools.cyber_autotune.curvature_yaw_v2_search import build_case
from openpilot.tools.cyber_autotune.curvature_yaw_native_runner import run_native_transcript
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


class TestPassiveDiagnostics(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.request=build_case('speed_sweep',{'factor_high_fraction':0.,'friction_high_fraction':0.},role='STRESS')['requests'][3]
    cls.native=run_native_transcript(cls.request,timeout_s=30.)
    cls.result=diagnostic.run_diagnostics(cls.request,cls.native)

  def test_passive_profile_exact_output_and_repeat(self):
    self.assertEqual(self.result['native_result'],self.native)
    self.assertEqual(self.result['repetition_sha256'][0],self.result['repetition_sha256'][1])
    self.assertEqual(len(self.result['observations']),401)
    self.assertEqual(self.result['observations'][0]['step_index'],0)
    self.assertEqual(self.result['physical_delay_owner'],'PLANT')

  def test_pid_and_schedule_observables_are_finite_bound_to_output(self):
    diagnostic.validate_diagnostics(self.request,self.native,self.result)
    rows=self.result['observations']
    self.assertTrue(any(r['pid_i']!=0 for r in rows))
    self.assertEqual(rows[0]['factor'],4.00390625)
    self.assertEqual(rows[-1]['factor'],4.)
    self.assertTrue(all(abs(r['requested_torque'])<=1 for r in rows))

  def test_rehashed_pid_or_identity_tamper_rejected(self):
    for field in ('pid_i','requested_torque'):
      bad=copy.deepcopy(self.result)
      bad['observations'][80][field]+=.01
      bad['receipt_sha256']=digest(canonical({k:v for k,v in bad.items() if k!='receipt_sha256'}))
      with self.assertRaises(ValueError):
        diagnostic.validate_diagnostics(self.request,self.native,bad)
    bad=copy.deepcopy(self.result)
    bad['producer_source_sha256']='a'*64
    with self.assertRaises(ValueError):
      diagnostic.validate_diagnostics(self.request,self.native,bad)

  def test_wrong_native_result_and_mutated_request_rejected(self):
    bad=copy.deepcopy(self.native)
    bad['request_sha256']='a'*64
    with self.assertRaises(ValueError):
      diagnostic.run_diagnostics(self.request,bad)

  def test_nested_rehash_cannot_forge_controller_dynamics(self):
    for field,value in (('delay_frames',-2.5),('history_sha256','a'*64),('kp',-999.),('feedforward',999.),
                        ('filtered_jerk',999.),('integrator_frozen',True)):
      bad=copy.deepcopy(self.result)
      bad['observations'][80][field]=value
      bad['raw_result']['observations'][80][field]=value
      bad['repetition_sha256']=[digest(canonical(bad['raw_result']))]*2
      bad['receipt_sha256']=digest(canonical({k:v for k,v in bad.items() if k!='receipt_sha256'}))
      with self.assertRaises(ValueError):
        diagnostic.validate_diagnostics(self.request,self.native,bad)

  def test_inactive_pressed_and_release_state_is_stock_not_implicit_reset(self):
    request=build_case('reengage_low',{'factor_high_fraction':0.,'friction_high_fraction':0.},role='STRESS')['requests'][3]
    native=run_native_transcript(request,timeout_s=30.)
    result=diagnostic.run_diagnostics(request,native)
    rows=result['observations']
    self.assertTrue(all(r['integrator_frozen'] for r in rows[140:170]))
    self.assertTrue(all(r['requested_torque']==0 for r in rows[190:230]))
    self.assertTrue(all(r['pid_i']==rows[189]['pid_i'] for r in rows[190:230]))
    self.assertEqual(rows,diagnostic.reconstruct_observations(request,native))
