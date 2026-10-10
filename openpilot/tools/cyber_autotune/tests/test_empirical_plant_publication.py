import copy
import importlib.util
import unittest


class TestPublication(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(importlib.util.find_spec('openpilot.tools.cyber_autotune.empirical_plant_publication'))
    from openpilot.tools.cyber_autotune import empirical_plant_publication as pub, empirical_plant_policy as p

    self.pub, self.p = pub, p

  def test_pins(self):
    self.assertGreaterEqual(len(self.pub.load()), 11)

  def test_resealed_metrics_rejected(self):
    row = copy.deepcopy(self.pub.load()['empirical-plant-holdout-validation-v1.json'])
    row['results']['LOW']['one_step']['model']['RMSE'] = 0
    row = self.p.seal({k: v for k, v in row.items() if k != 'receipt_sha256'})
    self.assertRaises(ValueError, self.pub.validate_pinned, 'empirical-plant-holdout-validation-v1.json', row)

  def test_primary_gate_fails(self):
    gates = self.pub.gates(self.pub.load())
    self.assertFalse(gates['regimes']['LOW']['better_than_each_naive_primary_rule'])
    self.assertFalse(gates['full_plant_ready'])

  def test_medium_unavailable(self):
    self.assertEqual(self.pub.gates(self.pub.load())['regimes']['MEDIUM']['status'], 'UNAVAILABLE')

  def test_high_unavailable(self):
    self.assertEqual(self.pub.gates(self.pub.load())['regimes']['HIGH']['status'], 'UNAVAILABLE')

  def test_blocks_preserved(self):
    self.assertEqual(self.pub.load()['empirical-plant-readiness-v1.json']['calibration_blockers'], self.p.BLOCKERS)

  def test_no_counterfactual(self):
    r = self.pub.load()['empirical-plant-readiness-v1.json']
    self.assertFalse(r['ta_execution'])
    self.assertFalse(r['sg_execution'])
    self.assertEqual(r['counterfactual_use'], 'NOT_ADMITTED_NO_TA_SG_EXECUTION')

  def test_hist_verdicts(self):
    r = self.pub.load()['empirical-plant-readiness-v1.json']['historical']
    self.assertEqual(r['v2'], 'REJECTED')
    self.assertEqual(r['v2_violations'], 37)
    self.assertEqual(r['current'], 'BASELINE_EXACT')

  def test_local_model_pointers(self):
    x = self.pub.load()
    self.assertEqual(x['empirical-plant-selection-v1.json']['local_model_sha256'], x['empirical-plant-readiness-v1.json']['local_model_sha256'])

  def test_unknown_file_rejected(self):
    self.assertRaises(ValueError, self.pub.validate_pinned, '../bad', self.p.seal({'schema': 'UNKNOWN'}))
