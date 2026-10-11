"""Fixed source observation emission: tests use synthetic fixtures only."""
import unittest
import numpy as np
from openpilot.tools.cyber_autotune import empirical_grid_analysis as g


class TestProjection(unittest.TestCase):
  def test_half_even_ties_and_float32_emission(self):
    x = np.array([.05, .15, .25, -.05, -.25, 0., .3], dtype=np.float64)
    before = x.tobytes()
    codes, out, ties = g.project(x)
    np.testing.assert_array_equal(codes, [0, 1, 2, 0, -2, 0, 3])
    np.testing.assert_array_equal(out, (codes.astype(np.float64) * .1).astype(np.float32))
    self.assertEqual(out.dtype, np.float32)
    self.assertEqual(x.tobytes(), before)
    self.assertEqual(int(ties.sum()), 4)

  def test_every_source_code_round_trip(self):
    codes=np.arange(-32768,32768,dtype=np.int64)
    emitted=(codes.astype(np.float64)*.1).astype(np.float32)
    recovered,out,_=g.project(emitted.astype(np.float64))
    self.assertEqual(recovered.tobytes(),codes.tobytes())
    self.assertEqual(out.tobytes(),emitted.tobytes())

  def test_half_even_negative_and_positive_binary64_ties(self):
    codes,_,ties=g.project(np.array([.05,.25,-.05,-.25],dtype=np.float64))
    np.testing.assert_array_equal(codes,[0,2,0,-2])
    self.assertTrue(ties.all())

  def test_exact_source_endpoints(self):
    codes, _, _ = g.project(np.array([-3276.8, 3276.7]))
    np.testing.assert_array_equal(codes, [-32768, 32767])

  def test_no_silent_clip(self):
    for x in (-3276.9, 3276.8, 1e100):
      with self.subTest(x=x), self.assertRaisesRegex(ValueError, 'SOURCE_GRID_RANGE_VIOLATION'):
        g.project(np.array([x]))

  def test_nonfinite_rejected(self):
    for x in (np.nan, np.inf, -np.inf):
      with self.subTest(x=x), self.assertRaises(ValueError):
        g.project(np.array([x]))

  def test_step_offset_range_and_rule_locked(self):
    for key, value in [('step_deg', .2), ('offset_deg', .1), ('code_range', [-32767,32767]),
                       ('tie_rule', 'HALF_UP'), ('dtype', 'float64')]:
      facts = g.grid_contract()
      facts[key] = value
      with self.subTest(key=key), self.assertRaises(ValueError):
        g.require_grid(facts)

  def test_exact_hits_and_half_quantum(self):
    y=np.zeros(3)
    pred=np.array([0., .05, .1])
    m=g.metrics(y,pred)
    self.assertEqual(m['exact_target_hit_count'],1)
    self.assertEqual(m['error_below_half_quantum_count'],1)
    self.assertEqual(m['coverage'],{'valid':3,'total':3,'unavailable':0})

  def test_same_support_and_grid_bytes(self):
    y=np.array([0., .1, .2],dtype=np.float32).astype(float)
    one=np.column_stack([y,[.01,.09,.21],y*0,y,y*0])
    result,codes,out=g.analyze(one)
    self.assertEqual({x['count'] for x in result['arms'].values()},{3})
    self.assertEqual(result['arms']['SOURCE_GRID_ARX']['exact_target_hit_count'],3)
    self.assertEqual(codes.tobytes(),np.array([0,1,2],dtype=np.int64).tobytes())
    self.assertEqual(out.tobytes(),y.astype(np.float32).tobytes())

  def test_bad_support_shape_and_target_grid(self):
    for one in (np.zeros((3,4)),np.zeros((0,5)),np.array([[.04,0.,0.,0.,0.]])):
      with self.subTest(shape=one.shape),self.assertRaises(ValueError):
        g.analyze(one)

  def test_projection_cannot_use_outcomes(self):
    with self.assertRaises(TypeError):
      g.project(np.array([0.]),target=np.array([1.]))

  def test_metrics_paired_length(self):
    with self.assertRaises(ValueError):
      g.metrics(np.zeros(2),np.zeros(1))


class TestGate(unittest.TestCase):
  def row(self,fold,speed,good=True):
    h={'MEDIAN_ABS':1.,'BIAS':0.,'CORRELATION':1.,'MAX_ABS':4.,'exact_target_hit_rate':0.,
       'error_below_half_quantum_rate':0.,'error_at_most_one_quantum_rate':0.,'RMSE':2.,'MAE':1.,'P95_ABS':3.,'count':201,'coverage':{'valid':201,'total':201,'unavailable':0}}
    a={**h,'RMSE':1. if good else 3.}
    return {'route_id':fold,'fold':fold,'speed_bin':speed,'count':201,
            'arms':{'HOLD_LAST_OUTPUT':h,'CONTINUOUS_ARX':h,'SOURCE_GRID_ARX':a},
            'emission':{'source_range_violation_count':0}}

  def rows(self):
    return [self.row(f,b) for f in ('FOLD_A','FOLD_B') for b in ('LOW','MEDIUM','HIGH')]

  def test_all_six_required(self):
    rows=self.rows()
    self.assertEqual(g.adjudicate(rows)['verdict'],'SOURCE_GRID_OBSERVATION_REVIEW_POSSIBLE')
    rows[0]['arms']['SOURCE_GRID_ARX']['MAE']=1.01
    self.assertEqual(g.adjudicate(rows)['verdict'],'SOURCE_GRID_OBSERVATION_TRADEOFF_ONLY')

  def test_majority_failure_rejected(self):
    rows=self.rows()
    for x in rows[:4]:
      x['arms']['SOURCE_GRID_ARX']['RMSE']=3.
    self.assertEqual(g.adjudicate(rows)['verdict'],'SOURCE_GRID_OBSERVATION_REJECTED')

  def test_missing_duplicate_or_cross_route_scope_blocked(self):
    rows=self.rows()
    for bad in (rows[:-1],rows+[rows[0]],[*rows[:-1],rows[0]]):
      with self.subTest(n=len(bad)),self.assertRaises(ValueError):
        g.adjudicate(bad)
    rows[-1]['route_id']='third'
    with self.assertRaises(ValueError):
      g.adjudicate(rows)

  def test_any_range_violation_is_hard_rejection(self):
    rows=self.rows()
    rows[0]['emission']['source_range_violation_count']=1
    self.assertEqual(g.adjudicate(rows)['verdict'],'SOURCE_GRID_OBSERVATION_REJECTED')

  def test_exact_no_epsilon(self):
    row=self.rows()[0]
    row['arms']['SOURCE_GRID_ARX']['RMSE']=2.
    self.assertFalse(g.gate(row)['passed'])
    row['arms']['SOURCE_GRID_ARX']['RMSE']=float(np.nextafter(2.,0.))
    self.assertTrue(g.gate(row)['passed'])

  def test_nonfinite_secondary_metrics_fail(self):
    for key in ('MEDIAN_ABS','BIAS','MAX_ABS','CORRELATION'):
      row=self.rows()[0]
      row['arms']['SOURCE_GRID_ARX'][key]=np.inf
      with self.subTest(key=key):
        self.assertFalse(g.gate(row)['passed'])

  def test_support_coverage_or_nonfinite_fail(self):
    for key,value in [('count',200),('RMSE',None),('MAE',np.inf),
                      ('coverage',{'valid':200,'total':201,'unavailable':1})]:
      row=self.rows()[0]
      row['arms']['SOURCE_GRID_ARX'][key]=value
      with self.subTest(key=key):
        self.assertFalse(g.gate(row)['passed'])

  def test_equal_route_not_sample_weighted_primary(self):
    rows=self.rows()[:2]
    rows[0]['arms']['SOURCE_GRID_ARX']['RMSE']=1.
    rows[1]['arms']['SOURCE_GRID_ARX']['RMSE']=3.
    rows[0]['count']=10000
    rows[1]['count']=201
    a=g.aggregate(rows)
    self.assertEqual(a['equal_route_mean']['SOURCE_GRID_ARX']['RMSE'],2.)
    self.assertNotEqual(a['sample_weighted_supporting_mean']['SOURCE_GRID_ARX']['RMSE'],2.)

  def test_contract_only_after_six_gate_pass_and_nonexecuting(self):
    with self.assertRaises(ValueError):
      g.architecture({'verdict':'SOURCE_GRID_OBSERVATION_TRADEOFF_ONLY'},'x')
    row=g.architecture(g.adjudicate(self.rows()),'x')
    for k in ('actual_algorithm_implemented','model_fitted','rollout_semantics_frozen',
              'execution_allowed','search_allowed','holdout_opening_allowed'):
      self.assertIs(row[k],False)


if __name__=='__main__':
  unittest.main()
