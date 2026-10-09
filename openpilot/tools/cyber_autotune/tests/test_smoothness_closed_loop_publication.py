from copy import deepcopy
import unittest

from openpilot.tools.cyber_autotune import smoothness_closed_loop_publication as p
from openpilot.tools.cyber_autotune import smoothness_closed_loop as loop
from openpilot.tools.cyber_autotune.smoothness_closed_loop_policy import seal
from openpilot.tools.cyber_autotune.smoothness_v0_publication import load as historical


class TestClosedLoopPublication(unittest.TestCase):
  def fixture(self):
    binding = loop.binding()
    result = seal({'schema': 'SG_A_CLOSED_LOOP_FEEDBACK_V1', 'status': 'SG_CLOSED_LOOP_STRUCTURAL_PASS',
                   'standalone_verdict': 'SG_CLOSED_LOOP_TRADEOFF_ONLY', 'execution_binding_sha256': binding['receipt_sha256'],
                   'feedback_interaction': 'MIXED_OR_UNRESOLVED', 'composition_recommendation': 'COMPOSITION_NOT_RECOMMENDED',
                   'scenarios': [], 'executions': 66, 'repeatability': 'EXACT_PASS'})
    return result, binding

  def test_reference_track_preserved(self):
    r, b = self.fixture()
    self.assertEqual(p.build(r, b)['readiness']['reference_track'], historical()['readiness']['reference_track'])

  def test_ta_preserved(self):
    r, b = self.fixture()
    self.assertEqual(p.build(r, b)['readiness']['ta_interpretation'], 'TA_STANDALONE_TRADEOFF_ONLY')

  def test_sg_replay_preserved(self):
    r, b = self.fixture()
    self.assertEqual(p.build(r, b)['readiness']['historical_sg_interpretation'], 'SG_STANDALONE_TRADEOFF_ONLY')

  def test_historical_verdicts(self):
    r, b = self.fixture()
    self.assertEqual(p.build(r, b)['readiness']['historical_verdicts'], historical()['readiness']['historical_verdicts'])

  def test_no_composition_authorization(self):
    r, b = self.fixture()
    self.assertFalse(p.build(r, b)['readiness']['composition_authorized'])

  def test_no_search(self):
    r, b = self.fixture()
    self.assertFalse(p.build(r, b)['readiness']['search_authorized'])

  def test_no_meter_result(self):
    r, b = self.fixture()
    self.assertIsNone(p.build(r, b)['readiness']['independent_meter_result'])

  def test_no_total_bound(self):
    r, b = self.fixture()
    self.assertIsNone(p.build(r, b)['readiness']['total_physical_bound'])

  def test_no_sealed_reference(self):
    r, b = self.fixture()
    self.assertEqual(p.build(r, b)['readiness']['sealed_reference'], 'NOT_GENERATED')

  def test_no_stability_proof(self):
    r, b = self.fixture()
    self.assertFalse(p.build(r, b)['readiness']['stability_proof'])

  def test_corrupt_receipt_rejected(self):
    r, _ = self.fixture()
    r['executions'] = 999
    with self.assertRaises(ValueError):
      p.check_receipt(r)

  def test_binding_mismatch_rejected(self):
    r, b = self.fixture()
    bad = deepcopy(b)
    bad['sg_family'] = 'TA-B'
    with self.assertRaises(ValueError):
      p.build(r, bad)

  def test_no_vehicle_authority(self):
    r, b = self.fixture()
    self.assertFalse(p.build(r, b)['readiness']['vehicle_activation_allowed'])

  def test_no_qualification(self):
    r, b = self.fixture()
    self.assertFalse(p.build(r, b)['readiness']['qualification_allowed'])

  def test_source_binding_isolated(self):
    _, b = self.fixture()
    self.assertEqual(b['physical_delay_owner'], 'EACH_ARM_PLANT_ONLY')

  def test_exact_replay_pin(self):
    _, b = self.fixture()
    self.assertEqual(b['frozen_replay_receipt_sha256'], historical()['results']['receipt_sha256'])
