import copy
import unittest
import numpy as np

from openpilot.tools.cyber_autotune import empirical_v2_signals as v
from openpilot.tools.cyber_autotune import empirical_plant_model as m
from openpilot.tools.cyber_autotune import empirical_signal_reader as r


def stream(n=300):
  return {
    'state': [{'time_ns': (i+1)*10_000_000, 'valid': True, 'speed_mps': 10.0, 'angle_deg': 0.1*i,
      'driver_pressed': False, 'driver_torque': 0.0, 'eps_fault': False, 'gear': 'drive', 'yaw_raw': None} for i in range(n)],
    'command': [{'time_ns': (i+1)*10_000_000, 'valid': True, 'raw': 1.0, 'normalized': float(np.float32(1/409))} for i in range(n)],
    'control': [{'time_ns': (i+1)*10_000_000, 'valid': True, 'requested': 0.1, 'lat_active': True} for i in range(n)],
    'gyro': [], 'settings': [{'CustomSteerMax': 409}], 'gyro_rejected': 0,
  }


class TestV2Signals(unittest.TestCase):
  def test_yaw_missing_does_not_mask_actuator(self):
    a = v.aligned(stream())
    self.assertEqual(sum(x['actuator_valid'] for x in a['rows']), 300)
    self.assertEqual(sum(x['diagnostic_valid'] for x in a['rows']), 0)

  def test_common_45_rows_accounting(self):
    a = v.aligned(stream())
    c = v.coverage(a)
    low = c['bins']['LOW']
    self.assertEqual(low['diagnostic_valid'], 300)
    self.assertEqual(low['common_design_rows'], 256)
    self.assertEqual(low['contiguous_45_sample_windows'], 256)
    self.assertEqual(c['total_grid_samples'],300)

  def test_invalid_breaks_history(self):
    s = stream()
    s['state'][100]['driver_pressed'] = True
    a = v.aligned(s)
    low = v.coverage(a)['bins']['LOW']
    self.assertEqual(low['common_design_rows'], (100-44)+(199-44))

  def test_speed_crossing_breaks_history(self):
    s = stream()
    for x in s['state'][150:]:
      x['speed_mps'] = 20.0
    c = v.coverage(v.aligned(s))
    self.assertEqual(c['bins']['LOW']['common_design_rows'],106)
    self.assertEqual(c['bins']['MEDIUM']['common_design_rows'],106)

  def test_timestamp_regression_rejected(self):
    s=stream()
    s['command'][1]['time_ns']=s['command'][0]['time_ns']
    with self.assertRaises(ValueError):
      v.aligned(s)

  def test_future_command_unavailable(self):
    s=stream(1)
    s['command'][0]['time_ns'] += 1
    a=v.aligned(s)
    self.assertFalse(a['rows'][0]['actuator_valid'])
    self.assertIsNone(a['rows'][0]['command_raw'])

  def test_wrong_scale_conflicts(self):
    rows=[{'raw':409., 'normalized':1., 'valid':True}]
    self.assertEqual(r.command_bridge(rows,409,True)['status'],'RAW_TO_NORMALIZED_COMMAND_CONFIRMED')
    self.assertEqual(r.command_bridge(rows,384,True)['status'],'RAW_TO_NORMALIZED_COMMAND_CONFLICT')

  def test_runtime_missing_is_partial(self):
    self.assertEqual(r.command_bridge([{'raw':0.,'normalized':0.,'valid':True}],409,False)['status'],'RAW_TO_NORMALIZED_COMMAND_PARTIAL')

  def test_no_stage_a_history_between_segments(self):
    x = v.aligned(stream(44))
    data = v.actuator_runs([{'aligned':x},{'aligned':copy.deepcopy(x)}], 'LOW')
    self.assertEqual(len(m.design(data, m.p.family_policy()['candidates'][0])[1]),0)

  def test_whitelist_does_not_open_forbidden_payload(self):
    class Forbidden:
      def which(self): return 'modelV2'
      def __getattr__(self, name): raise AssertionError('forbidden body access')
    self.assertEqual(v.numeric([Forbidden()])['state'],[])

  def test_gyro_clock_failure_not_actuator_failure(self):
    s=stream()
    s['gyro']=[{'time_ns':10,'sensor_ns':20,'valid':True,'xyz':[0.,0.,0.]}]
    self.assertEqual(sum(x['actuator_valid'] for x in v.aligned(s)['rows']),300)

  def test_gap_samples_separate_from_breaks(self):
    source=stream(300)
    for x in source['control'][50:100]:
      x['lat_active']=False
    coverage=v.coverage(v.aligned(source))
    self.assertEqual(coverage['mask_breaks'],1)
    self.assertEqual(coverage['intervention_breaks'],1)
    self.assertEqual(coverage['mask_invalid_samples'],50)

  def test_nonfinite_yaw_remains_null(self):
    source=stream(1)
    source['state'][0]['yaw_raw']=float('nan')
    result=v.aligned(source)
    self.assertIsNone(result['rows'][0]['yaw_raw'])
    self.assertTrue(result['rows'][0]['actuator_valid'])
