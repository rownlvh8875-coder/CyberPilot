import math
import unittest
from dataclasses import FrozenInstanceError

from openpilot.selfdrive.controls.lib.cyber_lateral import (
  CyberLateralConfig, CyberLateralCoordinator, LateralBinding,
)
from openpilot.selfdrive.controls.lib.cyber_lateral.params import (
  LATERAL_PARAMETER_REGISTRY, LateralParameterProposal, assess_lateral_proposal,
)


def binding(**changes):
  values = {
    'vehicle': 'santafe-tm',
    'firmware': 'eps-fw-1',
    'model': 'model-1',
    'controller_type': 'torque',
    'configuration_epoch': 0,
  }
  values.update(changes)
  return LateralBinding(**values)


def proposal(**changes):
  values = {
    'name': 'lat_accel_factor',
    'value': 2.5,
    'unit': 'm/s^2/Nm',
    'binding': binding(),
    'evidence_identity': 'evidence-sha256',
    'confidence': 0.99,
  }
  values.update(changes)
  return LateralParameterProposal(**values)


class TestCyberLateralParameterAdmission(unittest.TestCase):
  def assertRejected(self, expected_reason, candidate):
    result = assess_lateral_proposal(candidate, binding())
    self.assertFalse(result.accepted)
    self.assertEqual(result.reason, expected_reason)

  def test_unknown_and_forged_metadata_are_rejected(self):
    self.assertRejected('unknown_parameter', proposal(name='made_up_gain'))
    with self.assertRaises(TypeError):
      LateralParameterProposal(**{**proposal().__dict__, 'metadata': {'minimum': -math.inf}})

  def test_every_forbidden_class_is_explicitly_rejected(self):
    forbidden = (
      'steering_limit', 'curvature_limit', 'lateral_jerk_limit', 'torque_limit',
      'can_driver_allowance', 'driver_override_gate', 'engagement_gate', 'user_lane_offset',
    )
    for name in forbidden:
      with self.subTest(name=name):
        metadata = LATERAL_PARAMETER_REGISTRY[name]
        self.assertTrue(metadata.safety_related or metadata.parameter_class == 'user_preference')
        self.assertRejected('forbidden_parameter', proposal(name=name, unit=metadata.unit))

  def test_bool_nan_inf_wrong_unit_and_confidence_fail_closed(self):
    for value in (True, math.nan, math.inf, -math.inf):
      with self.subTest(value=value):
        self.assertRejected('invalid_number', proposal(value=value))
    self.assertRejected('unit_mismatch', proposal(unit='Nm'))
    for confidence in (True, math.nan, -0.1, 1.1):
      with self.subTest(confidence=confidence):
        self.assertRejected('invalid_confidence', proposal(confidence=confidence))
    self.assertRejected('insufficient_confidence', proposal(confidence=0.2))

  def test_incomplete_and_mismatched_binding_are_rejected(self):
    incomplete = binding(model=None)
    self.assertRejected('incomplete_binding', proposal(binding=incomplete))
    for field, value in (
      ('vehicle', 'other-car'), ('firmware', 'other-fw'), ('model', 'other-model'),
      ('controller_type', 'pid'), ('configuration_epoch', 1),
    ):
      with self.subTest(field=field):
        self.assertRejected('binding_mismatch', proposal(binding=binding(**{field: value})))

  def test_parameter_controller_binding_and_malformed_name_fail_closed(self):
    pid_binding = binding(controller_type='pid')
    result = assess_lateral_proposal(
      proposal(binding=pid_binding), pid_binding,
    )
    self.assertFalse(result.accepted)
    self.assertEqual(result.reason, 'parameter_controller_mismatch')
    malformed = assess_lateral_proposal(proposal(name=[]), binding())
    self.assertFalse(malformed.accepted)
    self.assertEqual(malformed.reason, 'invalid_proposal')

  def test_missing_evidence_unreviewed_bounds_and_disabled_tuning_are_distinct(self):
    self.assertRejected('missing_evidence', proposal(evidence_identity=''))
    self.assertRejected('unreviewed_bounds', proposal(
      name='sunny_future_jerk_persistence', unit='m/s^3', value=1.0,
    ))
    self.assertRejected('out_of_bounds', proposal(value=20.0))
    self.assertRejected('tuning_disabled', proposal())

  def test_registry_metadata_and_assessments_are_immutable(self):
    required = {
      'steer_ratio', 'stiffness_factor', 'angle_offset_deg', 'roll_rad',
      'lat_accel_factor', 'lat_accel_offset', 'friction', 'lateral_delay_s',
      'torque_kp', 'torque_ki', 'jerk_gain_s', 'jerk_lookahead_s',
      'jerk_filter_cutoff_hz', 'sunny_future_jerk_persistence',
      'carrot_path_quality_bias',
    }
    self.assertTrue(required.issubset(LATERAL_PARAMETER_REGISTRY))
    with self.assertRaises(TypeError):
      LATERAL_PARAMETER_REGISTRY['new'] = LATERAL_PARAMETER_REGISTRY['lat_accel_factor']
    with self.assertRaises(FrozenInstanceError):
      LATERAL_PARAMETER_REGISTRY['lat_accel_factor'].minimum = 0.
    result = assess_lateral_proposal(proposal(), binding())
    with self.assertRaises(FrozenInstanceError):
      result.accepted = True

  def test_assessment_has_no_controller_or_coordinator_side_effect(self):
    expected_binding = binding()
    coordinator = CyberLateralCoordinator(CyberLateralConfig(), expected_binding)
    native_state = {'integral': 0.25, 'buffer': (1., 2.)}
    coordinator_before = dict(coordinator.__dict__)
    native_before = dict(native_state)

    self.assertRejected('tuning_disabled', proposal())

    self.assertEqual(coordinator.__dict__, coordinator_before)
    self.assertEqual(native_state, native_before)


if __name__ == '__main__':
  unittest.main()
