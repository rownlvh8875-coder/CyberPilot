"""Synthetic-only tests; no empirical arrays or real development metrics."""
import unittest
from unittest.mock import patch

import numpy as np

from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as m


class TestFitCVMath(unittest.TestCase):
  def fixture(self, n=320):
    k = np.arange(n, dtype=np.int64)
    return {'tick': (k*k % 71)-35, 'command': np.sin(k*.13), 'speed': 15+np.cos(k*.07),
            'streak': k+1}

  def test_exact_candidates(self):
    self.assertEqual(m.CANDIDATES, tuple(f'S2RI_D{d:02d}_L{length:02d}' for d in (0,5,10,20) for length in (1,5,15,45)))

  def test_17th_or_mutated_candidate_rejected(self):
    for value in ('S2RI_D01_L01', 'S2RI_D00_L02', 'S2RI_D00_L01 ', '../S2RI_D00_L01'):
      with self.subTest(value=value), self.assertRaises(ValueError):
        m.parameters(value)

  def test_chronological_layout(self):
    a = self.fixture()
    ix = np.array([100], dtype=np.int64)
    x = m.features(a, ix, 'S2RI_D05_L05')
    expected = [1, *a['command'][91:96], *np.diff(a['tick'][95:101]), a['tick'][100], a['speed'][100]]
    np.testing.assert_array_equal(x[0], expected)
    self.assertEqual(x.shape, (1,13))

  def test_current_features_ignore_future_state_and_command(self):
    a = self.fixture()
    before = m.features(a, np.array([100]), 'S2RI_D00_L05')
    a['tick'][101:] = -123
    a['command'][101:] = 23
    np.testing.assert_array_equal(before, m.features(a, np.array([100]), 'S2RI_D00_L05'))

  def test_rate_request_and_generic_run_are_not_inputs(self):
    a = self.fixture()
    b = dict(a, rate=np.full(320,np.nan), requested=np.full(320,np.nan), causal_run_id=np.full(320,-1))
    ix = m.anchors(a, 'S2RI_D00_L05', 25)
    np.testing.assert_array_equal(ix, m.anchors(b, 'S2RI_D00_L05', 25))
    np.testing.assert_array_equal(m.features(a,ix,'S2RI_D00_L05'), m.features(b,ix,'S2RI_D00_L05'))

  def test_history_needs_full_past_and_endpoint(self):
    a = self.fixture()
    ix = m.anchors(a, 'S2RI_D20_L45', 200)
    np.testing.assert_array_equal(ix, np.arange(64,120))
    with self.assertRaises(ValueError):
      m.features(a,np.array([63]),'S2RI_D20_L45')

  def test_reset_crossing_rejected(self):
    a = self.fixture()
    a['streak'][100:] = np.arange(220)+1
    ix = m.anchors(a,'S2RI_D00_L05',25)
    self.assertFalse(np.any((ix>=75)&(ix<105)))

  def test_final_row_no_target_and_no_short_padding(self):
    self.assertEqual(m.anchors(self.fixture(10),'S2RI_D00_L01',25).size,0)
    self.assertEqual(m.anchors(self.fixture(10),'S2RI_D00_L01',1).tolist(), list(range(1,9)))

  def test_invalid_index_rejected(self):
    for ix in (np.array([-1]), np.array([400]),np.array([3.2]),np.array([7,7])):
      with self.subTest(ix=ix.tolist()), self.assertRaises(ValueError):
        m.features(self.fixture(),ix,'S2RI_D00_L01')

  def test_nonfinite_eligible_feature_rejected(self):
    a=self.fixture()
    a['command'][10]=np.nan
    with self.assertRaises(ValueError):
      m.features(a,np.array([10]),'S2RI_D00_L01')

  def test_direct_half_even_projection(self):
    np.testing.assert_array_equal(m.project(np.array([14.5,15.5,-14.5,-15.5])),[14,16,-14,-16])

  def test_projection_failure_is_not_clipping_or_drop(self):
    for value in (np.nan,np.inf,-np.inf,32767.5,-32768.6):
      with self.subTest(value=value), self.assertRaises(ValueError):
        m.project(np.array([0.,value]))

  def test_train_only_normalization_and_constant_drop(self):
    x=np.column_stack((np.ones(50),np.arange(50.),np.full(50,2.)))
    norm=m.normalizer(x, role='TRAIN')
    np.testing.assert_array_equal(norm['effective'],[0,1])
    dev=np.array([[1.,100.,99.]])
    z=m.transform(dev,norm)
    self.assertEqual(z[0,0],1)
    self.assertEqual(z[0,1],(100-np.mean(x[:,1]))/np.std(x[:,1]))
    self.assertEqual(z.shape,(1,2))

  def test_development_and_pooled_normalizers_forbidden(self):
    for role in ('DEVELOPMENT','POOLED','HOLDOUT'):
      with self.subTest(role=role),self.assertRaises(ValueError):
        m.normalizer(np.ones((30,5)),role=role)

  def test_rank_failure_never_calls_solver(self):
    v=np.arange(50.)
    x=np.column_stack((np.ones(50),v,v))
    with patch.object(np.linalg,'lstsq',side_effect=AssertionError('SOLVE_FORBIDDEN')), self.assertRaisesRegex(ValueError,'RANK'):
      m.fit(x,v,role='TRAIN')

  def test_synthetic_exact_ols_and_nominal_zero(self):
    v=np.arange(50.)
    x=np.column_stack((np.ones(50),v,np.full(50,2.)))
    model=m.fit(x,3+2*v,role='TRAIN')
    self.assertEqual(model['nominal_coefficients'][2],0.)
    self.assertEqual(model['rank'],2)
    np.testing.assert_allclose(m.predict(x,model),3+2*v,rtol=0,atol=1e-12)

  def test_solver_rank_conflict(self):
    v=np.arange(50.)
    x=np.column_stack((np.ones(50),v))
    with patch.object(np.linalg,'lstsq',return_value=(np.ones(2),np.array([]),1,np.ones(2))), self.assertRaisesRegex(ValueError,'NUMERICAL_RANK_CONFLICT'):
      m.fit(x,v,role='TRAIN')

  def test_nonfinite_coefficient_rejected(self):
    v=np.arange(50.)
    x=np.column_stack((np.ones(50),v))
    with patch.object(np.linalg,'lstsq',return_value=(np.array([np.nan,1]),np.array([]),2,np.ones(2))), self.assertRaises(ValueError):
      m.fit(x,v,role='TRAIN')

  def test_nonfinite_target_or_prediction_whole_call_failure(self):
    v=np.arange(50.)
    x=np.column_stack((np.ones(50),v))
    y=v.copy()
    y[5]=np.nan
    with self.assertRaises(ValueError):
      m.fit(x,y,role='TRAIN')
    model=m.fit(x,v,role='TRAIN')
    model['coefficients'][0]=np.nan
    with self.assertRaises(ValueError):
      m.predict(x,model)


if __name__ == '__main__':
  unittest.main()
