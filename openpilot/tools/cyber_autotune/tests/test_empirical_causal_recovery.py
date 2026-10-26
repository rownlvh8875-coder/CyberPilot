"""Origin and clock negative controls; raw decoders are never required."""
import unittest
import numpy as np
from openpilot.tools.cyber_autotune import empirical_causal_recovery as r


def rows(n=50):
  return [{'actuator_valid': True, 'speed_bin': 'LOW', 'command_raw': float(i % 5),
           'angle_deg': float(i), 'speed_mps': 10., 'grid_time_ns': i*10_000_000,
           'state_time_ns': i*10_000_000, 'command_time_ns': i*10_000_000-1,
           'control_time_ns': i*10_000_000-2, 'reasons': []} for i in range(n)]


class TestOrigins(unittest.TestCase):
  def test_history45(self):
    x,y,context,origin=r.reconstruct(rows(), 'LOW')
    self.assertEqual(x.shape,(6,3))
    self.assertEqual(y[0],44)
    self.assertEqual(origin[0,0],44)
    np.testing.assert_array_equal(context[0,:6],[3,2,4,3,43,42])

  def test_speed_boundary(self):
    data=rows(100)
    data[49]['speed_bin']='MEDIUM'
    self.assertEqual(len(r.reconstruct(data,'LOW')[1]),11)

  def test_mask_boundary(self):
    data=rows(100)
    data[49]['actuator_valid']=False
    self.assertEqual(len(r.reconstruct(data,'LOW')[1]),11)

  def test_wrong_history(self):
    with self.assertRaises(ValueError):
      r.reconstruct(rows(),'LOW',history=44)

  def test_future_command(self):
    data=rows()
    data[43]['command_time_ns']=data[43]['state_time_ns']+1
    with self.assertRaises(ValueError):
      r.reconstruct(data,'LOW')

  def test_control_future(self):
    data=rows()
    data[43]['control_time_ns']=data[43]['state_time_ns']+1
    with self.assertRaises(ValueError):
      r.reconstruct(data,'LOW')

  def test_clock_regression(self):
    data=rows()
    data[43]['state_time_ns']=data[42]['state_time_ns']
    with self.assertRaises(ValueError):
      r.reconstruct(data,'LOW')

  def test_mapping_exact(self):
    x,y,_,_=r.reconstruct(rows(),'LOW')
    coef=np.array([.9,.2,.1])
    one=np.column_stack([y,x@coef,np.zeros(len(y)),x[:,0],np.zeros(len(y))])
    r.prove(x,y,x,one,coef)

  def test_mapping_wrong_order(self):
    x,y,_,_=r.reconstruct(rows(),'LOW')
    coef=np.array([.9,.2,.1])
    one=np.column_stack([y,x@coef,np.zeros(len(y)),x[:,0],np.zeros(len(y))])
    with self.assertRaises(ValueError):
      r.prove(x[::-1],y[::-1],x,one,coef)

  def test_target_leak_not_context(self):
    data=rows()
    a=r.reconstruct(data,'LOW')[2][0].copy()
    data[44]['angle_deg']=999
    np.testing.assert_array_equal(a,r.reconstruct(data,'LOW')[2][0])


if __name__=='__main__':
  unittest.main()


class TestRecoveryContracts(unittest.TestCase):
  def test_no_current_command(self):
    data=rows()
    before=r.reconstruct(data,'LOW')[2][0].copy()
    data[44]['command_raw']=409
    np.testing.assert_array_equal(before,r.reconstruct(data,'LOW')[2][0])

  def test_wrong_config_prediction(self):
    x,y,_,_=r.reconstruct(rows(),'LOW')
    coef=np.array([.9,.2,.1])
    one=np.column_stack([y,x@coef,np.zeros(len(y)),x[:,0],np.zeros(len(y))])
    with self.assertRaises(ValueError):
      r.prove(x,y,x,one,coef+1)

  def test_wrong_previous_measurement(self):
    x,y,_,_=r.reconstruct(rows(),'LOW')
    coef=np.array([.9,.2,.1])
    one=np.column_stack([y,x@coef,np.zeros(len(y)),x[:,0]+1,np.zeros(len(y))])
    with self.assertRaises(ValueError):
      r.prove(x,y,x,one,coef)

  def test_dtype_exact(self):
    self.assertFalse(r.exact(np.zeros(2,dtype=np.float32),np.zeros(2,dtype=np.float64)))

  def test_negative_zero_byte_mismatch(self):
    self.assertFalse(r.exact(np.array([0.]),np.array([-0.])))

  def test_shape_exact(self):
    self.assertFalse(r.exact(np.zeros((1,2)),np.zeros(2)))

  def test_missing_steering_rate_not_inferred(self):
    self.assertNotIn('steeringRateDeg',r.CONTEXT_COLUMNS)

  def test_future_schema_only(self):
    x=r.context_schema()
    self.assertEqual(x['scope'],'FUTURE_GENERATIONS_ONLY')
    self.assertFalse(x['historical_regeneration_allowed'])

  def test_future_rate_requires_authorization(self):
    x=r.context_schema()
    self.assertIn('EXPLICIT_FUTURE_READER_AUTHORIZATION',x['optional_private_fields']['steeringRateDeg'])

  def test_private_context_schema_no_rows(self):
    r.validate_public(r.context_schema())

  def test_private_index_publication_rejected(self):
    with self.assertRaises(ValueError):
      r.validate_public({'origin_rows':[]})

  def test_private_timestamp_publication_rejected(self):
    with self.assertRaises(ValueError):
      r.validate_public({'state_time_ns':0})

  def test_prediction_publication_rejected(self):
    with self.assertRaises(ValueError):
      r.validate_public({'predictions':[]})

  def test_symlink_store_rejected(self):
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_causal_policy as p
    with tempfile.TemporaryDirectory() as d:
      root=Path(d)
      (root/'actual').mkdir()
      (root/'link').symlink_to(root/'actual')
      with self.assertRaises(ValueError):
        p.stores({'v2':root/'link','v3':root/'v3','attribution':root/'att'},root/'out')

  def test_store_overlap_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_causal_policy as p
    with self.assertRaises(ValueError):
      p.stores({'v2':'/tmp/test-overlap','v3':'/tmp/test-overlap/v3','attribution':'/tmp/test-att'},'/tmp/test-out')

  def test_raw_decoder_not_used_for_mapping(self):
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune import empirical_plant_signals, empirical_signal_reader
    with patch.object(empirical_plant_signals,'events',side_effect=AssertionError('RAW_FORBIDDEN')), \
         patch.object(empirical_signal_reader,'read_numeric',side_effect=AssertionError('RAW_FORBIDDEN')):
      self.assertEqual(len(r.reconstruct(rows(),'LOW')[1]),6)


class TestEntireRunClock(unittest.TestCase):
  def test_early_gap_cannot_hide_before_history(self):
    data=rows()
    data[10]['grid_time_ns']+=1
    with self.assertRaises(ValueError):
      r.reconstruct(data,'LOW')

  def test_segment_restart_no_cross_history(self):
    self.assertEqual(len(r.reconstruct(rows(30),'LOW')[1]),0)
    self.assertEqual(len(r.reconstruct(rows(30),'LOW')[1]),0)
