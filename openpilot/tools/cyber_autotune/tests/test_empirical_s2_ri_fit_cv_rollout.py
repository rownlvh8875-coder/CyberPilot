import unittest
from unittest.mock import patch

import numpy as np

from openpilot.tools.cyber_autotune import empirical_s2_ri_fit_cv_math as m


def synthetic_model(coefficient):
  return {'coefficients':np.array(coefficient,dtype=np.float64),
    'normalizer':{'effective':np.arange(len(coefficient)),'mean':np.zeros(len(coefficient)),
                  'std':np.ones(len(coefficient)),'constant':np.zeros(len(coefficient),bool)}}


class TestProjectedRecursion(unittest.TestCase):
  def test_projected_state_recurses_not_continuous(self):
    model=synthetic_model([.6,0,0,0,0])
    result=m.recursive(np.zeros((1,2),np.int64),np.zeros((1,25)),np.zeros((1,25)),
                       'S2RI_D00_L01',model,25)
    self.assertEqual(result[0],25)

  def test_projected_delta_history_recurses(self):
    model=synthetic_model([0,0,1,0,0])
    result=m.recursive(np.array([[0,1]],np.int64),np.zeros((1,25)),np.zeros((1,25)),
                       'S2RI_D00_L01',model,25)
    self.assertEqual(result[0],26)

  def test_recorded_exogenous_advance(self):
    model=synthetic_model([0,1,0,0,0])
    commands=np.arange(25,dtype=float).reshape(1,25)
    result=m.recursive(np.zeros((1,2),np.int64),commands,np.zeros((1,25)),
                       'S2RI_D00_L01',model,25)
    self.assertEqual(result[0],sum(range(25)))

  def test_no_future_measured_state_argument(self):
    with self.assertRaises(TypeError):
      m.recursive(np.zeros((1,2),np.int64),np.zeros((1,25)),np.zeros((1,25)),
                  'S2RI_D00_L01',synthetic_model([0]*5),25,future_angle=np.zeros((1,25)))

  def test_no_short_rollout_padding(self):
    with self.assertRaises(ValueError):
      m.recursive(np.zeros((1,2),np.int64),np.zeros((1,24)),np.zeros((1,25)),
                  'S2RI_D00_L01',synthetic_model([0]*5),25)

  def test_rollout_nonfinite_or_range_whole_call_failure(self):
    for coeff in (float('nan'),32767.):
      with self.subTest(coeff=coeff),self.assertRaises(ValueError):
        m.recursive(np.zeros((2,2),np.int64),np.zeros((2,25)),np.zeros((2,25)),
                    'S2RI_D00_L01',synthetic_model([coeff,0,0,0,0]),25)

  def test_canonical_error_is_original_delta_primitive(self):
    current=np.full(201,30000,np.int64)
    target=current+1
    delta=np.full(201,.1,dtype=np.float64)
    with patch.object(m,'predict',return_value=delta):
      _,buffers=m.one_step(np.ones((201,5)),current,target,synthetic_model([0]*5))
    np.testing.assert_array_equal(buffers['error'],delta-1.)
    self.assertFalse(np.array_equal(buffers['error'],(current+delta)-target))

  def test_p95_linear_and_identical_hold_last_population(self):
    error=np.arange(201,dtype=np.float64)
    result=m.metrics(error)
    self.assertEqual(result['p95'],190.)
    self.assertEqual(result['mae'],100.)
    with self.assertRaises(ValueError):
      m.metrics(error[:200])

  def test_one_step_exact_grid_hit_not_continuous_hit(self):
    current=np.zeros(201,np.int64)
    target=np.ones(201,np.int64)
    with patch.object(m,'predict',return_value=np.full(201,.6)):
      result,_=m.one_step(np.ones((201,5)),current,target,synthetic_model([0]*5))
    self.assertEqual(result['candidate']['exact_hit'],1.)
    self.assertEqual(result['comparator']['exact_hit'],0.)
