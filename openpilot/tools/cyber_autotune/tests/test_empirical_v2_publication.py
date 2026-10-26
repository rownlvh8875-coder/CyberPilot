import unittest
from openpilot.tools.cyber_autotune import empirical_v2_publication as pub
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_publication as old


class TestV2Publication(unittest.TestCase):
  def test_no_private_coefficients(self):
    model={'model':{'config':{'family':'ARX1','delay_samples':10},'count':300,'status':'FITTED','coefficients':[.7,.2,0.],'singular_values':[1.]},
           'development':{'RMSE':.1},'evaluation':{'status':'EVALUATED'}}
    result=pub.candidate(model)
    self.assertNotIn('coefficients',str(result))
    self.assertNotIn('singular_values',str(result))

  def test_all_blockers_preserved(self):
    historical=old.load()['empirical-source-audit-readiness-v1.json']
    result=pub.readiness({'stage_a':{},'stage_b_state':'STAGE_B_SIGNAL_ADMISSION_BLOCKED','yaw_admission':{'state':'YAW_SIGNAL_UNUSABLE'},
                          'routes':[{}, {}, {}],'stage_a_pooling_allowed':False},'0'*64,'1'*64,historical)
    self.assertEqual(result['calibration_blockers'],p.BLOCKERS)
    self.assertEqual(result['historical'],historical['historical'])
    self.assertFalse(result['holdout_opened'])
    self.assertEqual(result['future_holdout'],'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED')

  def test_no_fake_frozen_model(self):
    result=pub.stage({'LOW':{'state':'STAGE_A_MODEL_SELECTION_BLOCKED','selected':None,'candidates':[],'common_development_rows':0,'units':'degrees'}},'STAGE_A',{})
    self.assertIsNone(result['bins']['LOW']['selected_model_sha256'])

  def test_authority_firewall(self):
    result=p.seal({'schema':'fixture'})
    self.assertFalse(result['ta_execution'])
    self.assertFalse(result['sg_execution'])
    self.assertFalse(result['vehicle_activation_allowed'])
    self.assertFalse(result['production_authority'])

  def test_unpinned_publication_rejected(self):
    if not pub.PINS:
      with self.assertRaises(ValueError):
        pub.load()

  def test_empty_development_does_not_claim_bounded_validation(self):
    model={'model':{'config':{'family':'ARX1','delay_samples':0},'count':201,'status':'FITTED','coefficients':[.7,.2,0.]},
      'development':{'count':0,'RMSE':None},'evaluation':{'status':'EVALUATED','finite_horizon_bounded':True,
      'one_step':{'model':{'count':0,'RMSE':None}},'rollout':{'25':{'model':{'count':0,'RMSE':None},'finite_bounded':True}}}}
    result=pub.candidate(model)
    self.assertEqual(result['evaluation']['status'],'UNAVAILABLE_NO_DEVELOPMENT_SUPPORT')
    self.assertIsNone(result['evaluation']['finite_horizon_bounded'])
    self.assertIsNone(result['evaluation']['rollout']['25']['finite_bounded'])
    self.assertTrue(model['evaluation']['finite_horizon_bounded'])
