from copy import deepcopy
import unittest
from openpilot.tools.cyber_autotune import smoothness_v0_publication as p


class TestPublication(unittest.TestCase):
  def test_receipts(self):
    self.assertEqual(p.load()['results']['status'], 'SG_STANDALONE_STRUCTURAL_PASS')

  def test_66_execution(self):
    r = p.load()['results']
    self.assertEqual(len(r['scenarios']), 11)
    self.assertEqual(r['exact_repeats_per_arm'], 2)
    self.assertEqual(sum(len(r['arms']) for r in r['scenarios']) * 2, 66)

  def test_no_ta_input(self):
    self.assertIs(p.load()['results']['ta_enabled'], False)
    self.assertIs(p.load()['results']['baseline_core_input_only'], True)

  def test_no_composition(self):
    r = p.load()['readiness']
    self.assertIs(r['composition_authorized'], False)
    self.assertIn(r['composition_recommendation'], ('COMPOSITION_NOT_RECOMMENDED', 'COMPOSITION_BLOCKED', 'COMPOSITION_REVIEW_POSSIBLE'))

  def test_no_search(self):
    self.assertIs(p.load()['readiness']['search_authorized'], False)

  def test_no_evaluation(self):
    self.assertIs(p.load()['readiness']['frozen_evaluation_authorized'], False)

  def test_ta_historical(self):
    self.assertEqual(p.load()['readiness']['ta_interpretation'], 'TA_STANDALONE_TRADEOFF_ONLY')

  def test_history(self):
    self.assertEqual(p.load()['readiness']['historical_verdicts'], {'CURRENT': 'BASELINE_EXACT', 'V1': 'TRADEOFF_ONLY', 'V2': 'REJECTED'})

  def test_blockers(self):
    self.assertIn('PIXEL_GEOMETRY_REGISTRATION_PENDING', p.load()['readiness']['reference_track'])

  def test_no_sealed(self):
    self.assertEqual(p.load()['readiness']['sealed_reference'], 'NOT_GENERATED')

  def test_no_vehicle(self):
    self.assertFalse(p.load()['readiness']['vehicle_activation_allowed'])

  def test_mutation(self):
    r = deepcopy(p.load()['results'])
    r['composed'] = True
    with self.assertRaises(ValueError):
      p.validate(r)

  def test_no_feedback_stability_claim(self):
    self.assertIs(p.load()['results']['feedback_loop_stability_evaluated'], False)

  def test_alias(self):
    for row in p.load()['results']['scenarios']:
      b = row['arms']['UPSTREAM_BASELINE']
      c = row['arms']['CYBER_CURRENT_ALIAS']
      self.assertEqual(b, c)

  def test_core_saturation_semantics(self):
    for row in p.load()['results']['scenarios']:
      b = row['arms']['UPSTREAM_BASELINE']['metrics']['smoothness_primary']
      c = row['arms']['SG_V0_CANDIDATE']['metrics']['smoothness_primary']
      self.assertEqual(b['pre_governor'], c['pre_governor'])

  def test_source_validation(self):
    self.assertIn('smoothness_governor_v0.py', p.load()['binding']['source_sha256'])


if __name__ == '__main__':
  unittest.main()
