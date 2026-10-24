"""Single-condition semantics and admission, independent of private data."""
import unittest
import numpy as np
from openpilot.tools.cyber_autotune import empirical_causal_analysis as c


class TestConditions(unittest.TestCase):
  def setUp(self):
    self.context = np.array([[1, 1, 2, 1, 0, 0], [-1, 1, 2, 2, .1, 0], [409, 408, 1, 1, 0, .1]], dtype=float)
    self.prediction = np.array([0, .15, 0])

  def test_six_conditions(self):
    self.assertEqual(tuple(c.conditions(self.context, self.prediction)), tuple('C'+str(i) for i in range(1, 7)))

  def test_command_changed(self):
    np.testing.assert_array_equal(c.conditions(self.context, self.prediction)['C1'], [False, True, True])

  def test_delayed_changed(self):
    np.testing.assert_array_equal(c.conditions(self.context, self.prediction)['C2'], [True, False, False])

  def test_reversal_nonzero(self):
    np.testing.assert_array_equal(c.conditions(self.context, self.prediction)['C3'], [False, True, False])

  def test_angle_changed(self):
    np.testing.assert_array_equal(c.conditions(self.context, self.prediction)['C4'], [False, True, True])

  def test_rail(self):
    np.testing.assert_array_equal(c.conditions(self.context, self.prediction)['C5'], [False, False, True])

  def test_half_quantum_inclusive(self):
    np.testing.assert_array_equal(c.conditions(np.zeros((1, 6)), np.array([.05]))['C6'], [True])

  def test_future_fields_rejected(self):
    with self.assertRaises(ValueError):
      c.conditions(np.zeros((1, 7)), np.zeros(1))

  def test_normalized_equivalence(self):
    self.assertTrue(c.command_equivalence(np.arange(-409, 410, dtype=float)))

  def test_selector_requires_strict_pass(self):
    with self.assertRaises(ValueError):
      c.selector(np.zeros((4, 5)), np.zeros(4, dtype=bool), False)


if __name__ == '__main__':
  unittest.main()


def branch(count=201, arx=(1.,1.,1.), hold=(2.,2.,2.)):
  def metrics(v):
    return dict(zip(('RMSE','MAE','P95_ABS'),v,strict=True))
  return {'count':count,'arx':metrics(arx),'hold_last':metrics(hold)}


class TestStrictAdmission(unittest.TestCase):
  def test_strict_scope_pass(self):
    self.assertTrue(c.scope_gate(branch(),branch(arx=(2.,2.,2.),hold=(1.,1.,1.)))['passed'])

  def test_true_rmse_tie_fails(self):
    self.assertFalse(c.scope_gate(branch(arx=(2.,1.,1.)),branch(arx=(2.,2.,2.),hold=(1.,1.,1.)))['passed'])

  def test_201_inclusive(self):
    self.assertTrue(c.scope_gate(branch(201),branch(201,arx=(2.,2.,2.),hold=(1.,1.,1.)))['passed'])

  def test_200_rejected(self):
    self.assertEqual(c.scope_gate(branch(200),branch())['status'],'INSUFFICIENT_BRANCH_SUPPORT')

  def test_no_epsilon(self):
    self.assertFalse(c.scope_gate(branch(arx=(1.,2.+1e-12,1.)),branch(arx=(2.,2.,2.),hold=(1.,1.,1.)))['passed'])

  def test_false_branch_all_three(self):
    self.assertFalse(c.scope_gate(branch(),branch(arx=(2.,2.,2.),hold=(1.,3.,1.)))['passed'])

  def test_nonfinite(self):
    self.assertEqual(c.scope_gate(branch(arx=(float('nan'),1.,1.)),branch())['status'],'NONFINITE_METRIC')

  def scopes(self,passed=True):
    gate={'passed':passed,'status':'PASS' if passed else 'DIRECTIONAL_CRITERION_FAILED'}
    return [{'route_id':route,'speed_bin':speed,'conditions':{name:{'gate':gate.copy()} for name in c.CONDITIONS}}
            for route in ('a','b') for speed in ('LOW','MEDIUM','HIGH')]

  def test_all_six_pass(self):
    self.assertEqual(c.adjudicate(self.scopes())['verdict'],'CAUSAL_HYBRID_REVIEW_POSSIBLE')

  def test_single_scope_failure(self):
    rows=self.scopes()
    rows[0]['conditions']['C1']['gate']={'passed':False,'status':'DIRECTIONAL_CRITERION_FAILED'}
    self.assertNotIn('C1',c.adjudicate(rows)['strict_pass_conditions'])

  def test_insufficient_prevents_closure(self):
    rows=self.scopes(False)
    rows[0]['conditions']['C3']['gate']={'passed':False,'status':'INSUFFICIENT_BRANCH_SUPPORT'}
    result=c.adjudicate(rows)
    self.assertEqual(result['context'],'CAUSAL_CONTEXT_RECOVERED_PARTIAL')
    self.assertEqual(result['track'],'NOT_CLOSED_PARTIAL_OR_UNAVAILABLE_EVIDENCE')

  def test_all_supported_fail_closes_narrow_track(self):
    self.assertEqual(c.adjudicate(self.scopes(False))['track'],'CURRENT_ARX1_FIR25_PLUS_PREDECLARED_SINGLE_CONDITION_TRACK_CLOSED')

  def test_wrong_scope_count(self):
    with self.assertRaises(ValueError):
      c.adjudicate(self.scopes()[:-1])

  def test_duplicate_scope(self):
    rows=self.scopes()
    rows[-1]=rows[0]
    with self.assertRaises(ValueError):
      c.adjudicate(rows)

  def test_common_support_metrics(self):
    one=np.column_stack([np.arange(500),np.arange(500)+.1,np.zeros(500),np.arange(500)+.2,np.zeros(500)])
    result=c.audit(one,np.zeros((500,6)))
    for value in result.values():
      self.assertEqual(sum(x['count'] for x in value['branches'].values()),500)
      self.assertEqual(value['coverage']['valid'],500)

  def test_absolute_contribution_reconstructs(self):
    one=np.column_stack([np.arange(500),np.arange(500)+.1,np.zeros(500),np.arange(500)+.2,np.zeros(500)])
    context=np.zeros((500,6))
    context[::2,0]=1
    result=c.audit(one,context)['C1']['branches']
    contribution=sum(x['mae_difference_contribution'] for x in result.values())
    self.assertAlmostEqual(contribution,np.mean(abs(one[:,1]-one[:,0]))-np.mean(abs(one[:,3]-one[:,0])))

  def test_squared_contribution_reconstructs(self):
    one=np.column_stack([np.arange(500),np.arange(500)+.1,np.zeros(500),np.arange(500)+.2,np.zeros(500)])
    result=c.audit(one,np.zeros((500,6)))['C1']['branches']
    self.assertAlmostEqual(sum(x['mse_difference_contribution'] for x in result.values()),-.03)

  def test_selector_no_fit(self):
    one=np.array([[0.,1.,0.,0.,0.],[2.,2.,0.,0.,0.]])
    result=c.selector(one,np.array([False,True]),True)
    self.assertEqual(result['RMSE'],0.)

  def test_noninteger_raw_rejected(self):
    with self.assertRaises(ValueError):
      c.command_equivalence(np.array([.5]))

  def test_wrong_raw_scale_rejected(self):
    with self.assertRaises(ValueError):
      c.command_equivalence(np.array([410.]))

  def test_no_target_dependency(self):
    context=np.zeros((10,6))
    prediction=np.ones(10)
    self.assertEqual(list(c.conditions(context,prediction)),list(c.CONDITIONS))


class TestConservativePartial(unittest.TestCase):
  def test_one_scope_pass_cannot_close_track(self):
    base=TestStrictAdmission()
    rows=base.scopes(False)
    rows[0]['conditions']['C1']['gate']={'passed':True,'status':'PASS'}
    self.assertEqual(c.adjudicate(rows)['context'],'CAUSAL_CONTEXT_RECOVERED_PARTIAL')
    self.assertNotIn('CLOSED_NO_ADMISSIBLE',c.adjudicate(rows)['track'])

  def test_nonfinite_cannot_close_track(self):
    rows=TestStrictAdmission().scopes(False)
    rows[0]['conditions']['C1']['gate']={'passed':False,'status':'NONFINITE_METRIC'}
    self.assertEqual(c.adjudicate(rows)['context'],'CAUSAL_CONTEXT_RECOVERED_PARTIAL')
