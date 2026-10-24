import copy
import unittest

from openpilot.tools.cyber_autotune import empirical_plant_policy as p


def samples(n=300):
  return [
    {'grid_time_ns': i*10_000_000, 'segment_id': 'a'*64, 'diagnostic_valid': True, 'speed_bin': 'LOW',
         'reasons': [], 'gyro_common_valid': True}
    for i in range(n)
  ]


class TestRouteEligibility(unittest.TestCase):
  def test_contiguous_common_history(self):
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    row=e.support(samples())
    self.assertEqual(row['bins']['LOW']['design_rows'], 256)
    self.assertTrue(row['bins']['LOW']['minimum_support_met'])

  def test_no_cross_gap_history(self):
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    rows=samples()
    for x in rows[150:]:
      x['grid_time_ns']+=10_000_000
    self.assertEqual(e.support(rows)['bins']['LOW']['design_rows'],212)

  def test_mask_and_segment_breaks(self):
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    rows=samples()
    rows[150]['diagnostic_valid']=False
    self.assertEqual(e.support(rows)['bins']['LOW']['design_rows'],211)
    rows=samples()
    for x in rows[150:]:
      x['segment_id']='b'*64
    self.assertEqual(e.support(rows)['bins']['LOW']['design_rows'],212)

  def test_bin_change_breaks_history(self):
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    rows=samples()
    for x in rows[150:]:
      x['speed_bin']='HIGH'
    result=e.support(rows)
    self.assertEqual(result['bins']['LOW']['design_rows'],106)
    self.assertEqual(result['bins']['HIGH']['design_rows'],106)
    self.assertEqual(result['bins']['MEDIUM']['design_rows'],0)

  def test_missing_limits_not_false(self):
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    m=e.signal_matrix({},False)
    self.assertIsNone(m['safety_limit'])
    self.assertIsNone(m['curvature_limit'])
    self.assertIsNone(m['direct_gyro'])

  def test_gyro_future_and_regression(self):
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    future=[{'time_ns': 1,'sensor_ns': 2,'xyz': [0.,0.,0.],'valid': True}]
    self.assertEqual(e.gyro_readiness(future)['status'],'GYRO_UNAVAILABLE')
    regression=[{'time_ns': 2,'sensor_ns': 1,'xyz': [0.,0.,0.],'valid': True},
                {'time_ns': 3,'sensor_ns': 1,'xyz': [0.,0.,0.],'valid': True}]
    self.assertEqual(e.gyro_readiness(regression)['status'],'GYRO_UNAVAILABLE')

  def test_crosschecks_require_source_provenance(self):
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    self.assertEqual(e.optional_crosschecks({})['wheel_speed_yaw'],'BLOCKED_SOURCE_UNITS_SIGN_TRACK_WIDTH')
    self.assertEqual(e.optional_crosschecks({})['lateral_accel_yaw'],'BLOCKED_SOURCE_UNITS_SIGN_FRAME')

  def test_v1_always_denied(self):
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    with self.assertRaisesRegex(ValueError,'V1'):
      e.open_gate({'route_id': 'a'*64,'v1_overlap': True},p.seal({'schema':'X'}))

  def test_holdout_closed(self):
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as v
    split=v.split_routes([{'route_id': str(i)*64,'status': 'ROUTE_METADATA_COMPATIBLE','v1_overlap': False} for i in range(3)])
    hold=next(x for x in split['routes'] if x['role']=='HOLDOUT')
    with self.assertRaisesRegex(ValueError,'HOLDOUT'):
      e.open_gate({'route_id': hold['route_id'],'v1_overlap': False},split)

  def test_unknown_fields_fail(self):
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    rows=samples(1)
    rows[0]['modelV2']=0
    with self.assertRaises(ValueError):
      e.support(rows)

  def test_repeat_exact(self):
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    self.assertEqual(e.support(samples()),e.support(copy.deepcopy(samples())))


if __name__ == '__main__':
  unittest.main()


def streams(n=300):
  return {
    'state':[{'time_ns':i*10_000_000, 'valid':True, 'speed_mps':10., 'angle_deg':1.,
              'driver_pressed':False, 'driver_torque':0., 'eps_fault':False, 'gear':'drive', 'yaw_raw':1.} for i in range(n)],
    'command':[{'time_ns':i*10_000_000, 'valid':True, 'raw':409., 'normalized':1.} for i in range(n)],
    'control':[{'time_ns':i*10_000_000, 'valid':True, 'requested':1., 'lat_active':True} for i in range(n)],
    'gyro':[{'time_ns':i*10_000_000,'sensor_ns':i*10_000_000,'valid':True,'xyz':[0.,0.,0.]} for i in range(n)],
    'settings':[{'CustomSteerMax':0}], 'gyro_rejected':0,
  }


class TestEligibilityIntegration(unittest.TestCase):
  def test_actual_reader_shape_end_to_end(self):
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    row=e.audit_segment(streams(),'a'*64,{'steer_control_type':'torque','flags':65928})
    self.assertEqual(row['command_bridge']['status'],'RAW_TO_NORMALIZED_COMMAND_CONFIRMED')
    self.assertEqual(row['support']['bins']['LOW']['design_rows'],256)

  def test_bad_gyro_does_not_discard_command_coverage(self):
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    data=streams()
    data['gyro'][100]['sensor_ns']=0
    row=e.audit_segment(data,'a'*64,{'steer_control_type':'torque','flags':65928})
    self.assertEqual(row['support']['bins']['LOW']['design_rows'],256)
    self.assertEqual(row['support']['bins']['LOW']['gyro_common_design_rows'],0)

  def test_duration_uses_timestamp_intervals_and_breaks_gaps(self):
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    self.assertEqual(e.contiguous_duration([0,10_000_000,1_000_000_000],[True,True,True]),0.01)

  def test_duration_rejects_time_regression(self):
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    with self.assertRaises(ValueError):
      e.contiguous_duration([10,9],[True,True])


class TestFrozenSupportAgreement(unittest.TestCase):
  def test_design_count_matches_frozen_model(self):
    import numpy as np
    from openpilot.tools.cyber_autotune import empirical_plant_model as m
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    data=[{'u':np.ones(245), 'y':np.ones(245)}]
    expected=len(m.design(data,p.family_policy()['candidates'][-1])[1])
    self.assertEqual(expected,201)
    self.assertEqual(e.support(samples(245))['bins']['LOW']['design_rows'],expected)


class TestNumericSourceIntegrity(unittest.TestCase):
  def test_source_changed_after_inventory_rejected(self):
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    with tempfile.TemporaryDirectory() as d:
      root=Path(d)
      path=root/'rlog.zst'
      path.write_bytes(b'original')
      segment={'source_key':'rlog.zst','source_sha256':p.sha(b'original')}
      self.assertEqual(e.exact_source(root,segment),path)
      path.write_bytes(b'changed')
      with self.assertRaisesRegex(ValueError,'SOURCE_CHANGED'):
        e.exact_source(root,segment)

  def test_outside_root_rejected(self):
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_route_eligibility as e
    with tempfile.TemporaryDirectory() as d:
      with self.assertRaises(ValueError):
        e.exact_source(Path(d),{'source_key':'../rlog.zst','source_sha256':'a'*64})
