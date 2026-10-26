from dataclasses import FrozenInstanceError
import importlib
import inspect
from pathlib import Path
import unittest

from openpilot.tools.cyber_autotune.policy import (
  PARAMETER_POLICIES, ParameterClass, lookup_policy, offline_proposal_permitted,
)


class TestParameterPolicy(unittest.TestCase):
  def test_wheelbase_source_reference_resolves_to_actual_consumer(self):
    policy = lookup_policy('wheelbase')
    source_path, symbol = policy.source_symbol.split(':')
    source_file = Path(__file__).resolve().parents[4] / source_path
    self.assertTrue(source_file.is_file(), 'Policy must refer to an existing reviewed source file')
    module_name = source_path.removeprefix('opendbc_repo/').removesuffix('.py').replace('/', '.')
    consumer = getattr(importlib.import_module(module_name), symbol)
    from opendbc.car.vehicle_model import VehicleModel
    self.assertIs(consumer, VehicleModel)
    self.assertEqual(Path(inspect.getfile(consumer)).resolve(), source_file.resolve())
    self.assertEqual(policy.classification, ParameterClass.STATIC)
    self.assertFalse(offline_proposal_permitted('wheelbase'))

  def test_only_canonical_torque_families_are_representable(self):
    for name, unit in (('lat_accel_factor', 'm/s^2/normalized_command'), ('friction', 'normalized_command')):
      with self.subTest(name=name):
        policy = lookup_policy(name)
        self.assertEqual(policy.unit, unit)
        self.assertEqual(policy.classification, ParameterClass.AUTO_ALLOWED)
        self.assertEqual(policy.owner, 'torqued')
        self.assertTrue(offline_proposal_permitted(name))
    self.assertEqual({name for name in PARAMETER_POLICIES if offline_proposal_permitted(name)}, {'lat_accel_factor', 'friction'})

  def test_safety_limits_and_authority_cannot_be_proposed(self):
    for name in ('steering_limit', 'torque_limit', 'curvature_limit', 'lateral_jerk_limit', 'can_driver_allowance',
                 'driver_override_gate', 'engagement_gate', 'safety.accel_min', 'safety.accel_max', 'safety_flags',
                 'can_authority', 'steer_max', 'steer_delta_up', 'steer_delta_down'):
      with self.subTest(name=name):
        self.assertEqual(lookup_policy(name).classification, ParameterClass.SAFETY_LOCKED)
        self.assertFalse(offline_proposal_permitted(name))

  def test_existing_online_owners_are_not_offline_tunable(self):
    for name in ('lateral_delay_s', 'steer_ratio', 'stiffness_factor', 'angle_offset_deg', 'roll_rad'):
      with self.subTest(name=name):
        self.assertEqual(lookup_policy(name).classification, ParameterClass.ONLINE_ONLY)
        self.assertFalse(offline_proposal_permitted(name))

  def test_future_offline_families_are_not_initially_enabled(self):
    for name in ('torque_kp', 'torque_ki', 'vehicle.longitudinal_actuator_delay', 'controller.acceleration_integral_gain'):
      with self.subTest(name=name):
        self.assertEqual(lookup_policy(name).classification, ParameterClass.OFFLINE_ONLY)
        self.assertFalse(offline_proposal_permitted(name))

  def test_user_intent_and_identity_are_protected(self):
    for name in ('user.personality', 'user_lane_offset'):
      self.assertEqual(lookup_policy(name).classification, ParameterClass.USER_PREFERENCE)
      self.assertFalse(offline_proposal_permitted(name))
    for name in ('vehicle_fingerprint', 'software_revision', 'model_revision', 'configuration_revision', 'wheelbase'):
      self.assertEqual(lookup_policy(name).classification, ParameterClass.STATIC)
      self.assertFalse(offline_proposal_permitted(name))
    self.assertEqual({item.classification.value for item in PARAMETER_POLICIES.values()},
                     {'AUTO_ALLOWED', 'ONLINE_ONLY', 'OFFLINE_ONLY', 'USER_PREFERENCE', 'SAFETY_LOCKED', 'STATIC'})

  def test_aliases_and_malformed_names_fail_closed(self):
    for name in ('latAccelFactor', ' lat_accel_factor', 'FRICTION', '', None, [], {}, True, 12):
      with self.subTest(name=name):
        self.assertIsNone(lookup_policy(name))
        self.assertFalse(offline_proposal_permitted(name))

  def test_registry_and_records_cannot_be_reclassified(self):
    with self.assertRaises(TypeError):
      PARAMETER_POLICIES['steer_max'] = PARAMETER_POLICIES['friction']
    with self.assertRaises(FrozenInstanceError):
      PARAMETER_POLICIES['steer_max'].classification = ParameterClass.AUTO_ALLOWED
    self.assertFalse(offline_proposal_permitted('steer_max'))


if __name__ == '__main__':
  unittest.main()
