"""Synthetic rejection tests; no accepted calibration or live writeback."""
import unittest
from dataclasses import FrozenInstanceError, replace

from openpilot.selfdrive.controls.lib.cyber_long.types import ParameterBinding, ParameterProposal
from openpilot.selfdrive.controls.lib.cyber_long.params import PARAMETER_METADATA, assess_tuning_proposal


DELAY_NAME = 'vehicle.longitudinal_actuator_delay'


class TestCyberLongAdmission(unittest.TestCase):
  def setUp(self):
    self.binding = ParameterBinding(vehicle='synthetic-car', firmware='synthetic-fw', model='synthetic-model', configuration_epoch=0)
    self.proposal = ParameterProposal(name=DELAY_NAME, value=0.2, unit='s', binding=self.binding,
                                      evidence_id='synthetic-artifact-only', confidence=0.9)

  def assess(self, **changes):
    proposal = replace(self.proposal, **changes)
    result = assess_tuning_proposal(proposal, self.binding)
    self.assertFalse(result.accepted)
    return result

  def test_apparently_valid_proposal_is_rejected_with_unreviewed_bounds(self):
    self.assertEqual(self.assess().reason, 'unreviewed_bounds')

  def test_nonfinite_value_cannot_be_admitted(self):
    for value in (float('nan'), float('inf'), float('-inf'), True, '0.2', 10**1000):
      with self.subTest(value=value):
        self.assertEqual(self.assess(value=value).reason, 'invalid_value')

  def test_invalid_confidence_cannot_be_admitted(self):
    for confidence in (float('nan'), float('inf'), -0.1, 1.1, None, True, 10**1000):
      with self.subTest(confidence=confidence):
        self.assertEqual(self.assess(confidence=confidence).reason, 'invalid_confidence')

  def test_wrong_units_cannot_be_admitted(self):
    for unit in ('ms', 'percent', ''):
      self.assertEqual(self.assess(unit=unit).reason, 'unit_mismatch')

  def test_unknown_parameter_has_no_authority(self):
    self.assertEqual(self.assess(name='unknown.gain').reason, 'unknown_parameter')

  def test_malformed_name_has_no_authority(self):
    for name in ([], {}, None, 1):
      self.assertEqual(self.assess(name=name).reason, 'unknown_parameter')

  def test_safety_and_user_preferences_are_forbidden(self):
    for name in ('safety.accel_min', 'safety.accel_max', 'user.personality'):
      with self.subTest(name=name):
        self.assertEqual(self.assess(name=name).reason, 'forbidden_category')

  def test_wrong_vehicle_firmware_model_or_epoch_is_rejected(self):
    for changes in ({'vehicle': 'other'}, {'firmware': 'other'}, {'model': 'other'}, {'configuration_epoch': 1}):
      with self.subTest(changes=changes):
        self.assertEqual(self.assess(binding=replace(self.binding, **changes)).reason, 'binding_mismatch')

  def test_missing_identity_or_evidence_cannot_be_admitted(self):
    for changes in ({'vehicle': None}, {'firmware': ''}, {'model': None}, {'configuration_epoch': -1}):
      with self.subTest(changes=changes):
        self.assertEqual(self.assess(binding=replace(self.binding, **changes)).reason, 'incomplete_binding')
    self.assertEqual(self.assess(evidence_id='').reason, 'missing_evidence')
    self.assertFalse(assess_tuning_proposal(self.proposal, ParameterBinding()).accepted)

  def test_metadata_cannot_be_replaced_or_mutated(self):
    metadata = PARAMETER_METADATA[DELAY_NAME]
    with self.assertRaises(TypeError):
      PARAMETER_METADATA[DELAY_NAME] = replace(metadata, read_only=False, offline_allowed=True)
    with self.assertRaises(FrozenInstanceError):
      metadata.offline_allowed = True
    with self.assertRaises(TypeError):
      assess_tuning_proposal(self.proposal, self.binding, metadata=replace(metadata, read_only=False, offline_allowed=True))
    self.assertFalse(self.assess().accepted)

  def test_all_registry_entries_have_no_application_permission(self):
    for name, metadata in PARAMETER_METADATA.items():
      with self.subTest(name=name):
        self.assertTrue(metadata.read_only)
        self.assertFalse(metadata.online_allowed)
        self.assertFalse(metadata.offline_allowed)
        self.assertIsNone(metadata.min)
        self.assertIsNone(metadata.max)
        self.assertIsNone(metadata.rate_of_change_limit)
        self.assertIsNone(metadata.confidence_requirement)
        self.assertFalse(self.assess(name=name, unit=metadata.unit).accepted)

  def test_admission_does_not_mutate_input_or_binding(self):
    original = replace(self.proposal)
    assessment = assess_tuning_proposal(self.proposal, self.binding)
    self.assertEqual(self.proposal, original)
    self.assertEqual(self.binding, original.binding)
    with self.assertRaises(FrozenInstanceError):
      assessment.accepted = True


if __name__ == '__main__':
  unittest.main()
