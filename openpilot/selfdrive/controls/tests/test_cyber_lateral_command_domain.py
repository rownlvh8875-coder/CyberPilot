import unittest

from openpilot.selfdrive.controls.lib.cyber_lateral.command_domain import (
  OfflineTorqueCommandContract, translate_raw_applied_command,
)


class TestOfflineTorqueCommandContract(unittest.TestCase):
  def setUp(self):
    self.recorded = OfflineTorqueCommandContract(
      steer_max=409,
      delta_up_raw=3,
      delta_down_raw=7,
      control_dt_s=0.01,
      provenance='recorded-carrot-5a970f1a-route-start-params',
    )
    self.candidate = OfflineTorqueCommandContract(
      steer_max=384,
      delta_up_raw=3,
      delta_down_raw=7,
      control_dt_s=0.01,
      provenance='cyber-candidate-ea98cdf5-opendbc',
    )

  def test_translates_through_raw_command_without_reusing_source_normalization(self):
    result = translate_raw_applied_command(-36, self.recorded, self.candidate)
    self.assertEqual(result.raw_command, -36)
    self.assertAlmostEqual(result.source_normalized, -36 / 409)
    self.assertAlmostEqual(result.target_normalized, -36 / 384)
    self.assertNotEqual(result.source_normalized, result.target_normalized)
    self.assertTrue(result.rescaled)
    self.assertEqual(result.execution_stage, 'offline_only')
    self.assertFalse(result.live_actuator_authority)

  def test_exposes_normalized_existing_controller_rates(self):
    self.assertAlmostEqual(self.recorded.max_magnitude_increase_per_s, 3 / 409 / 0.01)
    self.assertAlmostEqual(self.recorded.max_magnitude_decrease_per_s, 7 / 409 / 0.01)
    self.assertAlmostEqual(self.candidate.max_magnitude_increase_per_s, 3 / 384 / 0.01)
    self.assertAlmostEqual(self.candidate.max_magnitude_decrease_per_s, 7 / 384 / 0.01)

  def test_same_contract_preserves_normalized_value(self):
    result = translate_raw_applied_command(44, self.candidate, self.candidate)
    self.assertEqual(result.source_normalized, result.target_normalized)
    self.assertFalse(result.rescaled)

  def test_rejects_invalid_contract_and_out_of_contract_raw_command(self):
    with self.assertRaises(ValueError):
      OfflineTorqueCommandContract(0, 3, 7, 0.01, 'invalid')
    with self.assertRaises(ValueError):
      OfflineTorqueCommandContract(384, 3, 7, 0.01, '')
    with self.assertRaises(ValueError):
      translate_raw_applied_command(385, self.recorded, self.candidate)
    with self.assertRaises(ValueError):
      translate_raw_applied_command(1.5, self.recorded, self.candidate)


if __name__ == '__main__':
  unittest.main()
