import importlib.util
from pathlib import Path
import tempfile
import unittest


class TestSignals(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(importlib.util.find_spec('openpilot.tools.cyber_autotune.empirical_plant_signals'), 'signal adapter missing')
    from openpilot.tools.cyber_autotune import empirical_plant_signals as s

    self.s = s

  def streams(self):
    return {
      'state': [
        {
          'time_ns': i * 10_000_000,
          'valid': True,
          'speed_mps': 20.0,
          'angle_deg': i * 0.1,
          'driver_pressed': False,
          'driver_torque': 0.0,
          'eps_fault': False,
          'gear': 'drive',
          'yaw_raw': 0.0,
        }
        for i in range(6)
      ],
      'command': [{'time_ns': i * 10_000_000, 'valid': True, 'command_raw': 10.0} for i in range(6)],
      'control': [{'time_ns': i * 10_000_000, 'valid': True, 'lat_active': True} for i in range(6)],
    }

  def test_alignment(self):
    r = self.s.align(self.streams())
    self.assertEqual(len(r['rows']), 6)
    self.assertEqual(r['rows'][2]['angle_deg'], 0.2)

  def test_command_must_precede_target_not_grid(self):
    x = self.streams()
    x['state'][1]['time_ns'] = 5_000_000
    x['command'][1]['time_ns'] = 9_000_000
    r = self.s.align(x)
    self.assertEqual(r['rows'][1]['command_time_ns'], 0)
    self.assertLessEqual(r['rows'][1]['command_time_ns'], r['rows'][1]['state_time_ns'])

  def test_no_future_first_command(self):
    x = self.streams()
    x['command'] = x['command'][1:]
    r = self.s.align(x)
    self.assertIn('MISSING_OR_GAP', r['rows'][0]['reasons'])

  def test_gap_mask(self):
    x = self.streams()
    x['command'] = x['command'][:1]
    r = self.s.align(x)
    self.assertIn('MISSING_OR_GAP', r['rows'][-1]['reasons'])

  def test_duplicate_rejected(self):
    x = self.streams()
    x['state'][1]['time_ns'] = 0
    with self.assertRaises(ValueError):
      self.s.align(x)

  def test_pressed_mask(self):
    x = self.streams()
    x['state'][2]['driver_pressed'] = True
    self.assertIn('DRIVER_OVERRIDE', self.s.align(x)['rows'][2]['reasons'])

  def test_inactive_mask(self):
    x = self.streams()
    x['control'][2]['lat_active'] = False
    self.assertIn('INACTIVE', self.s.align(x)['rows'][2]['reasons'])

  def test_eps_mask(self):
    x = self.streams()
    x['state'][2]['eps_fault'] = True
    self.assertIn('EPS_FAULT', self.s.align(x)['rows'][2]['reasons'])

  def test_low_speed_mask(self):
    x = self.streams()
    x['state'][2]['speed_mps'] = 2.0
    self.assertIn('LOW_SPEED', self.s.align(x)['rows'][2]['reasons'])

  def test_unknown_input_rejected(self):
    x = self.streams()
    x['candidate'] = []
    with self.assertRaises(ValueError):
      self.s.align(x)

  def test_yaw_unit_unknown_blocks_stage(self):
    self.assertEqual(self.s.yaw_provenance('')['status'], 'BLOCKED_UNIT_UNVERIFIED')

  def test_no_unit_inference_from_magnitude(self):
    with self.assertRaises(ValueError):
      self.s.yaw_provenance('rad/s inferred from small values')

  def test_wrong_command_units(self):
    with self.assertRaises(ValueError):
      self.s.validate_units('NORMALIZED_TORQUE', 'DEGREES_SOURCE_SAS11')

  def test_video_open_rejected(self):
    with tempfile.TemporaryDirectory() as t:
      p = Path(t) / 'qcamera.ts'
      p.write_bytes(b'never decode')
      with self.assertRaises(ValueError):
        list(self.s.events(p, object()))

  def test_forbidden_payload_untouched(self):
    class Event:
      logMonoTime = 0

      def which(self):
        return 'modelV2'

      def __getattr__(self, name):
        raise AssertionError('payload accessed')

    result = self.s.metadata([Event()])
    self.assertEqual(result['message_counts']['modelV2'], 1)

  def test_numeric_forbidden_untouched(self):
    class Event:
      logMonoTime = 0

      def which(self):
        return 'gpsLocationExternal'

      def __getattr__(self, name):
        raise AssertionError('GPS payload accessed')

    r = self.s.numeric([Event()])
    self.assertEqual(r, {'state': [], 'command': [], 'control': []})

  def test_speed_bins(self):
    self.assertEqual([self.s.speed_bin(v) for v in (4, 5, 14.9, 15, 25, 40)], [None, 'LOW', 'LOW', 'MEDIUM', 'HIGH', 'HIGH'])

  def test_nonfinite_mask(self):
    x = self.streams()
    x['state'][2]['angle_deg'] = float('nan')
    self.assertIn('NONFINITE', self.s.align(x)['rows'][2]['reasons'])

  def test_source_gap_break_at_new_event(self):
    x = self.streams()
    x['command'] = [x['command'][0], x['command'][3], x['command'][4], x['command'][5]]
    self.assertIn('SOURCE_EVENT_GAP', self.s.align(x)['rows'][3]['reasons'])

  def test_numeric_gate_requires_binding(self):
    with self.assertRaises(ValueError):
      self.s.validate_generation({}, {}, {})

  def test_numeric_gate_rejects_dirty(self):
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    source = p.seal({'schema': 'EMPIRICAL_SIGNAL_SOURCE_BINDING_V1', 'commit': self.s.RECORDED_COMMIT})
    meta = p.seal(
      {
        'schema': 'EMPIRICAL_SEGMENT_METADATA_V1',
        'source_sha256': 'a' * 64,
        'metadata': {
          'init': [{'commit': self.s.RECORDED_COMMIT, 'dirty': True}],
          'profiles': [
            {'fingerprint': 'HYUNDAI_SANTA_FE_2022', 'brand': 'hyundai', 'flags': 65928, 'steer_control_type': 'torque', 'full_carparams_sha256': 'b' * 64}
          ],
        },
      }
    )
    with self.assertRaises(ValueError):
      self.s.validate_generation({'source_sha256': 'a' * 64}, meta, source)
