import importlib
import math
import unittest
from dataclasses import replace

from openpilot.selfdrive.controls.lib.cyber_lateral.command_domain import OfflineTorqueCommandContract
from openpilot.selfdrive.controls.lib.cyber_lateral.metrics import LateralMetricInput, MetricSeries, compute_lateral_metrics


def metric_input():
  times = tuple(float(i) for i in range(8))

  def series(values, unit, source):
    return MetricSeries(times, tuple(values), unit, source)

  zeros = (0.,) * 8
  return LateralMetricInput(
    desired_path_offset_m=series(zeros, 'm', 'desired_path'),
    actual_path_offset_m=series((0.1,) * 8, 'm', 'plant_path'),
    cross_track_error_m=series((0.1,) * 8, 'm', 'cross_track'),
    requested_curvature_1pm=series((0., .01, .01, -.01, -.01, 0., 0., 0.), '1/m', 'requested'),
    actual_curvature_1pm=series(zeros, '1/m', 'actual'),
    lane_center_offset_m=series((0.1,) * 8, 'm', 'independent_lane'),
    steering_angle_deg=series((0., 1., 0., 1., 0., 1., 0., 1.), 'deg', 'angle'),
    saturation=series(zeros, 'bool', 'limiter'),
    driver_intervention=series(zeros, 'bool', 'driver'),
    declared_alignment_delay_s=0.,
    curve_phase_labels=('straight', 'entry', 'apex', 'entry', 'exit', 'straight', 'straight', 'straight'),
    steering_command=series((0., 1., 0., 1., 0., 1., 0., 1.), 'ratio', 'request_command'),
    applied_steering_torque=series((0., .5, 0., .5, 0., .5, 0., .5), 'ratio', 'applied_command'),
    desired_steering_angle_deg=series(zeros, 'deg', 'desired_angle'),
    lane_edge_margin_m=series((1.,) * 8, 'm', 'independent_edge'),
  )


def contracts_module():
  try:
    return importlib.import_module('openpilot.tools.cyber_autotune.contracts')
  except ModuleNotFoundError as exc:
    raise AssertionError('STEP 8.2 contracts API is not implemented') from exc


def binding(c):
  return c.MetricContract(
    pipeline_sha256='a' * 64, configuration_sha256='b' * 64,
    inputs_sha256='c' * 64, mask_sha256='d' * 64,
    reset_policy_sha256='e' * 64, reference_evidence_sha256='f' * 64,
    command=OfflineTorqueCommandContract(384, 3, 7, .01, 'synthetic fixture'),
    alignment_delay_s=0., reversal_deadband_ratio_per_s=0.,
  )


class TestContracts(unittest.TestCase):
  def test_raw_rate_contract_preserves_native_scale(self):
    c = contracts_module()
    contract = binding(c)
    self.assertEqual(contract.command.max_magnitude_increase_per_s, .78125)
    self.assertAlmostEqual(contract.command.max_magnitude_decrease_per_s, 1.8229166666666667)
    self.assertNotEqual(contract.command.max_magnitude_increase_per_s, 3.)

  def test_reversal_events_and_cycle_proxy_are_distinct(self):
    c = contracts_module()
    batch = c.compute_metrics_v2(metric_input(), binding(c))
    metrics = {item.name: item for item in batch.metrics}
    self.assertNotIn('steering_zero_crossing_frequency', metrics)
    self.assertAlmostEqual(metrics['command_reversal_events_per_s'].signed_mean, 6 / 7)
    self.assertEqual(metrics['command_reversal_events_per_s'].unit, 'events/s')
    self.assertAlmostEqual(metrics['command_reversal_cycle_proxy'].signed_mean, 3 / 7)
    self.assertEqual(metrics['command_reversal_cycle_proxy'].unit, 'Hz')
    self.assertEqual(metrics['steering_oscillation_frequency'].signed_mean, .5)

  def test_other_metrics_reuse_public_calculation(self):
    c = contracts_module()
    data = metric_input()
    legacy = compute_lateral_metrics(data)
    metrics = {item.name: item for item in c.compute_metrics_v2(data, binding(c)).metrics}
    for name, value in legacy.items():
      if name != 'steering_zero_crossing_frequency':
        self.assertEqual(metrics[name], value)

  def test_fixed_delay_and_deadband_must_match_data(self):
    c = contracts_module()
    for change in ({'alignment_delay_s': .1}, {'reversal_deadband_ratio_per_s': .1}):
      with self.subTest(change=change), self.assertRaises(ValueError):
        c.compute_metrics_v2(metric_input(), replace(binding(c), **change))

  def test_malformed_contract_is_rejected(self):
    c = contracts_module()
    for change in (
      {'version': 1}, {'version': True}, {'pipeline_sha256': ''},
      {'configuration_sha256': 'not-a-hash'}, {'alignment_delay_s': math.nan},
      {'alignment_delay_s': -.1}, {'alignment_delay_s': True},
      {'reversal_deadband_ratio_per_s': math.inf}, {'command': None},
    ):
      with self.subTest(change=change), self.assertRaises(ValueError):
        replace(binding(c), **change)

  def test_nm_is_not_implicitly_converted_to_normalized_command(self):
    c = contracts_module()
    for name, unit in (('lat_accel_factor', 'm/s^2/Nm'), ('friction', 'Nm'), ('STEER_MAX', 'ratio')):
      with self.subTest(name=name), self.assertRaises(ValueError):
        c.validate_parameter_unit(name, unit)
    c.validate_parameter_unit('lat_accel_factor', 'm/s^2/normalized_command')
    c.validate_parameter_unit('friction', 'normalized_command')

  def test_metric_batch_rejects_mutable_or_duplicate_records(self):
    c = contracts_module()
    batch = c.compute_metrics_v2(metric_input(), binding(c))
    for metrics in (list(batch.metrics), batch.metrics + (batch.metrics[0],), ()):
      with self.subTest(kind=type(metrics).__name__), self.assertRaises(ValueError):
        replace(batch, metrics=metrics)

  def test_oversized_numbers_fail_contract_validation_without_overflow(self):
    c = contracts_module()
    self.assertFalse(c.finite_number(10 ** 1000))
    with self.assertRaises(ValueError):
      replace(binding(c), alignment_delay_s=10 ** 1000)

  def test_nonfinite_derived_rates_are_not_contract_valid(self):
    c = contracts_module()
    commands = (
      OfflineTorqueCommandContract(384, 3, 7, 5e-324, 'synthetic underflow'),
      OfflineTorqueCommandContract(384, 10 ** 1000, 7, .01, 'synthetic overflow'),
    )
    for command in commands:
      with self.subTest(command=command), self.assertRaises(ValueError):
        replace(binding(c), command=command)


if __name__ == '__main__':
  unittest.main()
