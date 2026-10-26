import importlib.util
import unittest
from types import SimpleNamespace as NS
import numpy as np


class TestProvenanceReader(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(importlib.util.find_spec('openpilot.tools.cyber_autotune.empirical_signal_reader'), 'provenance reader missing')
    from openpilot.tools.cyber_autotune import empirical_signal_reader as r

    self.r = r

  def test_raw_normalized_float32_relation(self):
    rows = [{'raw': x, 'normalized': float(np.float32(x / 409)), 'valid': True} for x in [-409.0, -17.0, 0.0, 17.0, 409.0]]
    x = self.r.command_bridge(rows, 409, True)
    self.assertEqual(x['status'], 'RAW_TO_NORMALIZED_COMMAND_CONFIRMED')
    self.assertEqual(x['float32_expected_exact_count'], 5)
    self.assertEqual(x['sign_conflicts'], 0)
    self.assertEqual(x['raw_saturated_count'], 2)

  def test_wrong_384_rejected(self):
    x = self.r.command_bridge([{'raw': 409.0, 'normalized': 1.0, 'valid': True}], 384, True)
    self.assertEqual(x['status'], 'RAW_TO_NORMALIZED_COMMAND_CONFLICT')

  def test_missing_runtime_setting_partial(self):
    x = self.r.command_bridge([{'raw': 409.0, 'normalized': 1.0, 'valid': True}], 409, False)
    self.assertEqual(x['status'], 'RAW_TO_NORMALIZED_COMMAND_PARTIAL')

  def test_sign_conflict(self):
    x = self.r.command_bridge([{'raw': -409.0, 'normalized': 1.0, 'valid': True}], 409, True)
    self.assertEqual(x['sign_conflicts'], 1)

  def test_nonfinite_not_silent_zero(self):
    x = self.r.command_bridge([{'raw': float('nan'), 'normalized': 0.0, 'valid': True}], 409, True)
    self.assertEqual(x['eligible'], 0)
    self.assertEqual(x['invalid'], 1)
    self.assertEqual(x['residual']['RMSE'], None)

  def test_unknown_command_field(self):
    with self.assertRaises(ValueError):
      self.r.command_bridge([{'raw': 1.0, 'normalized': 1.0, 'valid': True, 'lane': 0}], 409, True)

  def test_torque_only_profile(self):
    with self.assertRaises(ValueError):
      self.r.effective_steer_max({'flags': 1 << 24, 'steer_control_type': 'angle'}, {'CustomSteerMax': 0})

  def test_runtime_override_bound(self):
    value, known = self.r.effective_steer_max({'flags': 65928, 'steer_control_type': 'torque'}, {'CustomSteerMax': 384})
    self.assertEqual((value, known), (384, True))

  def test_no_override_default409(self):
    self.assertEqual(self.r.effective_steer_max({'flags': 65928, 'steer_control_type': 'torque'}, {'CustomSteerMax': 0}), (409, True))

  def test_unknown_setting_not_false(self):
    self.assertEqual(self.r.effective_steer_max({'flags': 65928, 'steer_control_type': 'torque'}, {}), (409, False))

  def test_direct_gyro_source_and_unit(self):
    event = NS(
      which=lambda: 'gyroscope',
      valid=True,
      logMonoTime=100,
      gyroscope=NS(timestamp=90, source='lsm6ds3trc', which=lambda: 'gyroUncalibrated', gyroUncalibrated=NS(v=[1.0, 2.0, 3.0])),
    )
    x = self.r.read_numeric([event], True)
    self.assertEqual(x['gyro'][0]['xyz'], [1.0, 2.0, 3.0])

  def test_fused_gyro_never_dereferenced(self):
    class Event:
      def which(self):
        return 'livePose'

      def __getattr__(self, key):
        raise AssertionError('forbidden payload')

    self.assertEqual(self.r.read_numeric([Event()], True)['gyro'], [])

  def test_bridge_only_does_not_read_yaw_gyro(self):
    class Event:
      def which(self):
        return 'gyroscope'

      def __getattr__(self, key):
        raise AssertionError('old holdout yaw opened')

    self.assertEqual(self.r.read_numeric([Event()], False)['gyro'], [])

  def test_unknown_sensor_rejected_as_unavailable(self):
    event = NS(
      which=lambda: 'gyroscope',
      valid=True,
      logMonoTime=100,
      gyroscope=NS(timestamp=90, source='android', which=lambda: 'gyroUncalibrated', gyroUncalibrated=NS(v=[1.0, 2.0, 3.0])),
    )
    x = self.r.read_numeric([event], True)
    self.assertEqual(x['gyro'], [])
    self.assertEqual(x['gyro_rejected'], 1)

  def test_gyro_publish_future_rejected(self):
    rows = [{'time_ns': 200, 'sensor_ns': 100, 'xyz': [1.0, 2.0, 3.0], 'valid': True}]
    self.assertIsNone(self.r.past_gyro(rows, 150, 0))

  def test_gyro_sensor_future_rejected(self):
    rows = [{'time_ns': 100, 'sensor_ns': 200, 'xyz': [1.0, 2.0, 3.0], 'valid': True}]
    self.assertIsNone(self.r.past_gyro(rows, 150, 0))

  def test_gyro_source_age(self):
    rows = [{'time_ns': 0, 'sensor_ns': 0, 'xyz': [1.0, 2.0, 3.0], 'valid': True}]
    self.assertIsNone(self.r.past_gyro(rows, 30_000_000, 0))

  def test_lag_is_past_not_future(self):
    rows = [{'time_ns': i * 10_000_000, 'sensor_ns': i * 10_000_000, 'xyz': [float(i), 0.0, 0.0], 'valid': True} for i in range(5)]
    self.assertEqual(self.r.past_gyro(rows, 40_000_000, 2)['xyz'][0], 2.0)

  def test_duplicate_time_rejected(self):
    with self.assertRaises(ValueError):
      self.r.validate_times([{'time_ns': 1}, {'time_ns': 1}])

  def test_request_difference_not_limit_reason(self):
    x = self.r.limit_verdict(True)
    self.assertEqual(x['status'], 'POST_CONTROLLER_LIMITING_ONLY_OBSERVABLE')
    self.assertIsNone(x['safety_limited'])
    self.assertIsNone(x['curvature_limited'])
    self.assertEqual(x['reason'], 'LIMIT_REASON_UNOBSERVED')

  def test_acquisition_cannot_follow_its_publish(self):
    rows = [{'time_ns': 100, 'sensor_ns': 150, 'xyz': [1.0, 2.0, 3.0], 'valid': True}]
    self.assertIsNone(self.r.past_gyro(rows, 200, 0))

  def test_unknown_aligned_field_rejected(self):
    x = {
      'state': [],
      'command': [{'time_ns': 0, 'valid': True, 'raw': 1.0, 'normalized': 0.1, 'modelV2': 0}],
      'control': [],
      'gyro': [],
      'settings': [],
      'gyro_rejected': 0,
    }
    with self.assertRaises(ValueError):
      self.r.aligned(x)
