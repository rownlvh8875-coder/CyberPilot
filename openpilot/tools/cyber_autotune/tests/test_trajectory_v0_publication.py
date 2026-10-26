import copy
import unittest

from openpilot.tools.cyber_autotune import trajectory_v0_publication as p


class TestTrajectoryPublication(unittest.TestCase):
  def test_exact_receipts(self):
    p.load()

  def test_structural_not_acceptance(self):
    r = p.load()['readiness']
    self.assertEqual(r['structural_status'], 'TA_STANDALONE_STRUCTURAL_PASS')
    self.assertFalse(r['candidate_acceptance_authorized'])

  def test_tradeoff(self):
    self.assertEqual(p.load()['readiness']['standalone_verdict'], 'TA_STANDALONE_TRADEOFF_ONLY')

  def test_composition_still_blocked(self):
    self.assertIn('COMPOSITION_NOT_AUTHORIZED', p.load()['readiness']['states'])

  def test_sg_pending(self):
    self.assertIn('SMOOTHNESS_IMPLEMENTATION_PENDING', p.load()['readiness']['states'])

  def test_reference_unchanged(self):
    self.assertIn('INDEPENDENT_REFERENCE_UNAVAILABLE', p.load()['readiness']['reference_track'])

  def test_v2_preserved(self):
    r = p.load()['readiness']
    self.assertEqual(r['historical_verdicts']['V2'], 'REJECTED')
    self.assertEqual(r['v2_historical_violations'], 37)

  def test_v1_mixed(self):
    self.assertEqual(p.load()['readiness']['historical_roles'], ['MIXED_HISTORICAL', 'MIXED_HISTORICAL'])

  def test_no_vehicle(self):
    self.assertFalse(p.load()['readiness']['vehicle_activation_allowed'])

  def test_sealed_not_generated(self):
    self.assertEqual(p.load()['readiness']['sealed_reference'], 'NOT_GENERATED')

  def test_drift_rejected(self):
    row = copy.deepcopy(p.load()['results'])
    row['status'] = 'VEHICLE_READY'
    with self.assertRaises(ValueError):
      p.validate(row)

  def test_reseal_cannot_promote(self):
    from openpilot.tools.cyber_autotune import candidate_architecture as a
    row = copy.deepcopy(p.load()['results'])
    row['qualification_allowed'] = True
    row['receipt_sha256'] = a.hash_object({k: v for k, v in row.items() if k != 'receipt_sha256'})
    with self.assertRaises(ValueError):
      p.validate(row)

  def test_no_search(self):
    self.assertIn('SEARCH_NOT_AUTHORIZED', p.load()['readiness']['states'])

  def test_no_frozen_evaluation(self):
    self.assertIn('FROZEN_EVALUATION_NOT_AUTHORIZED', p.load()['readiness']['states'])

  def test_full_arm_count(self):
    self.assertEqual(p.load()['readiness']['executions'], 66)

  def test_alias(self):
    for r in p.load()['results']['scenarios']:
      a, b = r['arms']['UPSTREAM_BASELINE'], r['arms']['CYBER_CURRENT_ALIAS']
      self.assertEqual(a['trace_sha256'], b['trace_sha256'])
      self.assertEqual(a['identity_sha256'], b['identity_sha256'])
