"""Future aggregate projection must never publish private decision payloads."""

import importlib
import unittest


class TestV3ExecutorPublication(unittest.TestCase):
  def module(self):
    return importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_v3_executor_publication')

  def test_projection_discards_private_payload_and_retains_aggregate_tp(self):
    module = self.module()
    row = {'candidate_id': 'HRI_D00_L01', 'fold': 'FOLD_A', 'status': 'EXECUTED_COMPLETE',
           'train_count': 300, 'reference': {'reference_tp': 20}, 'threshold': {
             'status': 'V3_THRESHOLD_FINALIZED', 'receipt_sha256': 'a' * 64, 'candidate_count': 302, 'feasible_count': 10,
             'threshold': 0.314159, 'objective': {'tp': 23, 'exact_hit_count': 260, 'static_projected_false_move_count': 5,
                                               'within_one_tick_count': 285, 'feasible': True}},
           'coefficients': [99], 'raw_ticks': [123], 'private_path': '/not-a-real-source'}
    result = module.public_job(row)
    self.assertEqual(result['threshold']['objective']['tp'], 23)
    self.assertEqual(result['reference_tp'], 20)
    self.assertNotIn('threshold', result['threshold'])
    self.assertNotIn('coefficients', result)
    self.assertNotIn('private_path', result)

  def test_unknown_nested_metric_or_raw_sequence_is_rejected(self):
    module = self.module()
    for value in ({'candidate_id': 'HRI_D00_L01', 'threshold': 0.3}, {'predictions': [1.0]},
                  {'rmse': float('nan')}, {'rmse': '/mnt/d/secret'}, {'normalizer': {'mean': 2}}, {'tp': [1, 2]}):
      with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'V3_PUBLICATION_BOUNDARY_CONFLICT'):
        module.validate_public(value)

  def test_implementation_evidence_does_not_claim_actual_run(self):
    module = self.module()
    evidence = module.implementation_evidence({'focused': 1, 'full': 1, 'combined': 1, 'replay': 16})
    self.assertEqual(len(evidence), 13)
    for value in evidence.values():
      self.assertEqual(value['actual_private_access_count'], 0)
      self.assertEqual(value['v3_private_execution'], 'NOT_RUN')
      self.assertEqual(value['holdout'], 'CLOSED')
      self.assertEqual(value['vehicle_authority'], 'NONE')

  def test_implementation_count_schema_rejects_private_or_noncount_values(self):
    module = self.module()
    for counts in ({'private_path': '/synthetic/private'}, {'focused': [1]},
                   {'focused': True, 'full': 1, 'combined': 1, 'replay': 16},
                   {'focused': -1, 'full': 1, 'combined': 1, 'replay': 16}):
      with self.subTest(counts=counts), self.assertRaisesRegex(ValueError, 'V3_PUBLICATION_BOUNDARY_CONFLICT'):
        module.implementation_evidence(counts)
