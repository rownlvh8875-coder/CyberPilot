"""Final precedence and future model-support admission regressions."""
import importlib.util
import unittest


class TestFinalPrecedence(unittest.TestCase):
  def test_execution_ready_cannot_override_final_partial(self):
    name = 'openpilot.tools.cyber_autotune.empirical_final_readiness'
    if importlib.util.find_spec(name) is None:
      self.fail('Authoritative readiness resolver not implemented')
    module = __import__(name, fromlist=['resolve'])
    result = module.resolve()
    self.assertEqual(result['final_dataset_status'], 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL')
    self.assertEqual(result['legacy_reproduction_status'], 'PASS')
    self.assertEqual(result['qlog_reconciliation_status'], 'COMPLETE')
    self.assertFalse(result['model_execution_authorized'])


class TestReadinessEvidence(unittest.TestCase):
  def setUp(self):
    from openpilot.tools.cyber_autotune import empirical_final_readiness as module
    self.module = module
    self.x = module.load()

  def test_missing_final_has_no_ready_fallback(self):
    del self.x[self.module.FINAL]
    with self.assertRaisesRegex(ValueError, 'NO_FALLBACK'):
      self.module.resolve(self.x)

  def test_execution_receipt_alone_is_not_final_evidence(self):
    with self.assertRaises(ValueError):
      self.module.resolve({self.module.EXECUTION: self.x[self.module.EXECUTION]})

  def test_intermediate_receipt_alone_is_not_final_evidence(self):
    with self.assertRaises(ValueError):
      self.module.resolve({self.module.INTERMEDIATE: self.x[self.module.INTERMEDIATE]})

  def test_untrusted_extra_assessment_rejected(self):
    self.x['newer-looking-final.json'] = self.x[self.module.EXECUTION]
    with self.assertRaises(ValueError):
      self.module.resolve(self.x)

  def test_self_sealed_final_promotion_rejected_by_pin(self):
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    row = {k: v for k, v in self.x[self.module.FINAL].items() if k != 'receipt_sha256'}
    row['status'] = 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_READY'
    self.x[self.module.FINAL] = p.seal(row)
    with self.assertRaisesRegex(ValueError, 'PIN_DRIFT'):
      self.module.resolve(self.x)

  def test_corrupt_receipt_rejected(self):
    self.x[self.module.EXECUTION]['status'] = 'OTHER'
    with self.assertRaises(ValueError):
      self.module.resolve(self.x)

  def test_resolution_cannot_be_resealed_as_ready(self):
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    result = self.module.resolve(self.x)
    result = p.seal({**{k: v for k, v in result.items() if k != 'receipt_sha256'}, 'final_dataset_status': 'READY'})
    with self.assertRaises(ValueError):
      self.module.validate_resolution(result, self.x)

  def test_rlog_grid_is_not_whole_merged_grid(self):
    x = self.module.partition(self.x)
    self.assertEqual(x['rlog_subset']['grid_count'], 916535)
    self.assertEqual(x['qlog_subset']['grid_count'], 11989)
    self.assertEqual(x['all_stream_grid_count'], 928524)

  def test_causal_counts_not_legacy_counts(self):
    x = self.module.partition(self.x)
    self.assertEqual(x['rlog_subset']['causal_valid_count'], 874568)
    self.assertEqual(x['rlog_subset']['causal_runs'], 41961)
    self.assertEqual(x['qlog_subset']['causal_valid_count'], 0)
    self.assertEqual(x['qlog_subset']['model_design_support'], 0)

  def test_qlog_fitting_selection_cv_all_denied(self):
    for segment in self.module.partition(self.x)['qlog_subset']['segments']:
      self.assertFalse(segment['model_fit_allowed'])
      self.assertFalse(segment['model_selection_allowed'])
      self.assertFalse(segment['cv_support_allowed'])

  def test_partition_retrospective_only(self):
    for route in self.module.partition(self.x)['rlog_subset']['routes']:
      self.assertEqual(route['role'], 'RETROSPECTIVE_TRAIN_DEV_CV_POOL')
      self.assertFalse(route['holdout_allowed'])
      self.assertFalse(route['independent_validation_allowed'])

  def test_exact_repeatability(self):
    self.assertEqual(self.module.resolve(self.x), self.module.resolve(self.x))
    self.assertEqual(self.module.partition(self.x), self.module.partition(self.x))

  def test_no_private_access_or_fitting(self):
    from unittest.mock import patch
    with patch('numpy.load', side_effect=AssertionError('PRIVATE_ARRAY_ACCESS')), \
         patch('numpy.linalg.lstsq', side_effect=AssertionError('FITTING')):
      result = self.module.resolve(self.x)
      self.assertEqual(result['final_dataset_status'], 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL')

  def test_history_inputs_not_mutated(self):
    import copy
    before = copy.deepcopy(self.x)
    self.module.resolve(self.x)
    self.module.partition(self.x)
    self.assertEqual(self.x, before)


class TestReadinessPublication(unittest.TestCase):
  def publisher(self):
    name = 'openpilot.tools.cyber_autotune.empirical_final_readiness_publication'
    if importlib.util.find_spec(name) is None:
      self.fail('Aggregate-only final readiness publication not implemented')
    return __import__(name, fromlist=['bundle'])

  def test_nonexecuting_development_contract(self):
    bundle = self.publisher().bundle()
    contract = bundle['empirical-development-data-admission-contract-v1.json']
    self.assertEqual(contract['family_selection'], 'NOT_RUN')
    self.assertFalse(contract['model_fitting_allowed'])
    self.assertFalse(contract['cv_scoring_allowed'])
    self.assertEqual([f['family'] for f in contract['families']], ['S1', 'S2', 'S3'])

  def test_publication_exact_repeatability_and_resume(self):
    import tempfile
    from pathlib import Path
    module = self.publisher()
    with tempfile.TemporaryDirectory() as directory:
      first = module.publish(Path(directory))
      before = {p.name: p.read_bytes() for p in Path(directory).iterdir()}
      second = module.publish(Path(directory))
      self.assertEqual(first, second)
      self.assertEqual({p.name: p.read_bytes() for p in Path(directory).iterdir()}, before)

  def test_stale_publication_not_overwritten(self):
    import tempfile
    from pathlib import Path
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    module = self.publisher()
    with tempfile.TemporaryDirectory() as directory:
      target = Path(directory)/'empirical-final-readiness-resolution-v2.json'
      p.persist(target, p.seal({'schema': 'STALE'}))
      original = target.read_bytes()
      with self.assertRaises(ValueError):
        module.publish(Path(directory))
      self.assertEqual(target.read_bytes(), original)

  def test_private_data_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    module = self.publisher()
    for key in ('rows', 'predictions', 'targets', 'local_path', 'grid_time_ns', 'row_origin'):
      with self.subTest(key=key), self.assertRaises(ValueError):
        module.validate_public(p.seal({'schema': 'BAD', key: [1, 2]}))

  def test_authority_preserved(self):
    for row in self.publisher().bundle().values():
      self.assertFalse(row['production_authority'])
      self.assertFalse(row['qualification_allowed'])
      self.assertFalse(row['ta_execution'])
      self.assertFalse(row['sg_execution'])
      self.assertFalse(row['vehicle_activation_allowed'])


if __name__ == '__main__':
  unittest.main()
