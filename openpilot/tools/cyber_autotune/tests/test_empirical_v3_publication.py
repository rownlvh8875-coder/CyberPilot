"""Aggregate privacy and future-holdout authority are independent of model quality."""

import copy
import unittest
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_v3_policy as v
from openpilot.tools.cyber_autotune import empirical_v3_publication as pub
from openpilot.tools.cyber_autotune import empirical_v3_generation as g


class TestV3Publication(unittest.TestCase):
  def test_public_policy(self):
    pub.validate_public(v.policy())

  def test_private_coefficients_rejected(self):
    for key in pub.FORBIDDEN:
      with self.subTest(key=key), self.assertRaises(ValueError):
        pub.validate_public(p.seal({'schema': 'TEST', 'nested': [{key: []}]}))

  def test_private_path_rejected(self):
    for path in ('/mnt/d/private', '/home/private', 'D:\\private'):
      with self.subTest(path=path), self.assertRaises(ValueError):
        pub.validate_public(p.seal({'value': path}))

  def test_historical_v2_pins_unchanged(self):
    self.assertEqual(v.inputs()['empirical-plant-v2-train-dev-readiness-v1.json']['stage_a_state'], 'STAGE_A_MODEL_SELECTION_BLOCKED')

  def test_holdout_contract_not_execution_authority(self):
    x = g.holdout_package({}, 'result')
    self.assertFalse(x['evaluation_execution_authorized'])
    self.assertFalse(x['old_routes_holdout_allowed'])
    self.assertEqual(x['support_minimum'], 201)

  def test_no_candidate_authority(self):
    for key in p.FIREWALL:
      self.assertIs(v.policy()[key], False)

  def test_no_policy_result_circular_binding(self):
    self.assertNotIn('PINS', v.code_identity())
    self.assertNotIn('empirical_v3_publication.py', v.code_identity())

  def test_exact_receipt_tampering(self):
    x = copy.deepcopy(v.policy())
    x['stage_c'] = 'RUN'
    with self.assertRaises(ValueError):
      pub.validate_public(x)

  def test_old_v2_has_no_selected_model(self):
    self.assertEqual(v.inputs()['empirical-plant-v2-model-freeze-v1.json']['models'], {'STAGE_A': {}, 'STAGE_B': {}})

  def test_future_new_source_not_automatically_admitted(self):
    self.assertEqual(g.holdout_package({}, 'result')['current_source_admission'], 'EXACT_SOURCE_PROFILE_AUDIT_REQUIRED_NO_AUTOMATIC_EQUIVALENCE')


class TestV3PrivacyReview(unittest.TestCase):
  def test_other_windows_drive_and_unc_rejected(self):
    for path in ('C:\\Users\\private', '\\\\server\\share\\private', 'E:/private'):
      with self.subTest(path=path), self.assertRaises(ValueError):
        pub.validate_public(p.seal({'value': path}))
