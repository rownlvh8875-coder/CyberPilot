import unittest
import numpy as np
from openpilot.tools.cyber_autotune import empirical_v2_generation as g
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


def data(n=600):
  u=np.random.default_rng(177).normal(size=n)
  y=np.zeros(n)
  for k in range(11,n):
    y[k]=0.7*y[k-1]+0.2*u[k-10]
  return [{'u':u,'y':y,'blocks':np.zeros(n,dtype=int)}]


class TestV2Generation(unittest.TestCase):
  def test_train_development_only(self):
    with self.assertRaises(ValueError):
      g.select_stage({'TRAIN':data(),'HOLDOUT':data()},'STAGE_A','degrees')

  def test_exact_grid_eight(self):
    result=g.select_stage({'TRAIN':data(),'DEVELOPMENT':data()},'STAGE_A','degrees')
    self.assertEqual(len(result['candidates']),8)
    self.assertEqual(result['selected']['model']['config']['family'],'ARX1')
    self.assertEqual(result['selected']['model']['config']['delay_samples'],10)

  def test_small_development_no_selection(self):
    result=g.select_stage({'TRAIN':data(),'DEVELOPMENT':data(100)},'STAGE_A','degrees')
    self.assertIsNone(result['selected'])
    self.assertEqual(result['state'],'STAGE_A_MODEL_SELECTION_BLOCKED')

  def test_repeatability(self):
    args=({'TRAIN':data(),'DEVELOPMENT':data()},'STAGE_A','degrees')
    self.assertEqual(p.canonical(g.select_stage(*args)),p.canonical(g.select_stage(*args)))

  def test_all_candidate_rollouts(self):
    result=g.select_stage({'TRAIN':data(),'DEVELOPMENT':data()},'STAGE_A','degrees')
    for row in result['candidates']:
      if row['model']['status']=='FITTED':
        self.assertEqual(set(row['evaluation']['rollout']),{'25','50','100','200'})

  def test_pooled_bridge_gate(self):
    for bad in ('ROUTE_COMMAND_BRIDGE_PARTIAL','ROUTE_COMMAND_BRIDGE_CONFLICT','ROUTE_COMMAND_BRIDGE_UNAVAILABLE'):
      with self.subTest(bad=bad):
        self.assertFalse(g.pooling_allowed([{'status':'ROUTE_COMMAND_BRIDGE_CONFIRMED'},{'status':bad},{'status':'ROUTE_COMMAND_BRIDGE_CONFIRMED'}]))

  def test_exact_three_bridges_required(self):
    self.assertFalse(g.pooling_allowed([{'status':'ROUTE_COMMAND_BRIDGE_CONFIRMED'}]*2))

  def test_no_holdout_ready_state(self):
    result=g.select_stage({'TRAIN':data(),'DEVELOPMENT':data()},'STAGE_A','degrees')
    self.assertEqual(result['state'],'STAGE_A_MODEL_FROZEN_AWAITING_HOLDOUT')
    self.assertFalse(result['validated'])

  def test_stage_c_absent(self):
    self.assertNotIn('stage_c', g.select_stage({'TRAIN':data(),'DEVELOPMENT':data()},'STAGE_A','degrees'))

  def test_common_support_201_unchanged(self):
    result=g.select_stage({'TRAIN':data(),'DEVELOPMENT':data(244)},'STAGE_A','degrees')
    self.assertEqual(result['common_development_rows'],200)
    self.assertIsNone(result['selected'])

  def test_masked_yaw_row_keeps_timing(self):
    row={'diagnostic_valid':False,'gyro_common_valid':False,'grid_time_ns':123}
    receipt={'segment_id':'synthetic','aligned':{'rows':[row],'gyro_options':{'0':[None]}}}
    compact=g.compact(receipt)
    self.assertEqual(compact['aligned']['rows'][0]['grid_time_ns'],123)
