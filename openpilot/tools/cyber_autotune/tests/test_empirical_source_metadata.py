import unittest
from types import SimpleNamespace
from openpilot.tools.cyber_autotune import empirical_source_metadata as m, empirical_plant_policy as p


class Event:
  def __init__(self, kind, clock=1):
    self.kind, self.logMonoTime = kind, clock

  def which(self):
    return self.kind

  def __getattr__(self, name):
    raise AssertionError('NO_NUMERIC_OR_FORBIDDEN_BODY_ACCESS:'+name)


class TestSourceMetadata(unittest.TestCase):
  def test_no_numeric_body_access(self):
    with self.assertRaisesRegex(ValueError, 'MISSING_MANDATORY'):
      m.metadata([Event(k) for k in ('carState', 'carOutput', 'carControl', 'gyroscope', 'modelV2', 'gpsLocation')], 'a'*40, True)

  def test_clock_regression(self):
    with self.assertRaisesRegex(ValueError, 'NONMONOTONIC'):
      m.metadata([Event('carState', 2), Event('carState', 1)], 'a'*40, True)

  def test_exact_source_mismatch(self):
    e = Event('initData')
    e.initData = SimpleNamespace(gitCommit='b'*40)
    with self.assertRaisesRegex(ValueError, 'SOURCE_COMMIT'):
      m.metadata([e], 'a'*40, True)

  def test_adapter_unknown_source(self):
    source = p.seal({'commit': 'a', 'complete': True})
    binding = p.seal({'commit': 'b', 'source_fingerprint_sha256': source['receipt_sha256']})
    with self.assertRaisesRegex(ValueError, 'ADAPTER_MISMATCH'):
      m.validate_adapter(binding, source)

  def test_generic_fallback_forbidden(self):
    source = p.seal({'commit': 'a', 'complete': True})
    binding = p.seal({'commit': 'a', 'source_fingerprint_sha256': source['receipt_sha256']})
    with self.assertRaisesRegex(ValueError, 'NO_GENERIC_FALLBACK'):
      m.validate_adapter(binding, source)

  def test_full_cp_same(self):
    self.assertTrue(m.same_profile({'full_carparams_sha256': 'a'}, {'full_carparams_sha256': 'a'}))

  def test_subset_alone_insufficient(self):
    self.assertFalse(m.same_profile({'full_carparams_sha256': 'a', 'empirical_profile_sha256': 'c'},
                                    {'full_carparams_sha256': 'b', 'empirical_profile_sha256': 'c'}))

  def test_irrelevant_difference_proof(self):
    a = {'full_carparams_sha256': 'a', 'empirical_profile_sha256': 'c'}
    b = {'full_carparams_sha256': 'b', 'empirical_profile_sha256': 'c'}
    proof = p.seal({'full_hashes': ['a', 'b'], 'changed_fields': ['uiOnly'], 'reviewed_irrelevant': True})
    self.assertTrue(m.same_profile(a, b, proof))

  def test_relevant_difference_rejected(self):
    a = {'full_carparams_sha256': 'a', 'empirical_profile_sha256': 'c'}
    b = {'full_carparams_sha256': 'b', 'empirical_profile_sha256': 'c'}
    proof = p.seal({'full_hashes': ['a', 'b'], 'changed_fields': ['steerRatio'], 'reviewed_irrelevant': True})
    self.assertFalse(m.same_profile(a, b, proof))

  def test_physical_incomplete_not_recovered(self):
    r = {'v1_overlap': False, 'status': 'ROUTE_CORRUPT_OR_INCOMPLETE'}
    self.assertEqual(m.route_classification(r, True, 'SOURCE_COMMIT_PUBLICLY_AVAILABLE'), 'ROUTE_SOURCE_AUDITED_INCOMPLETE')

  def test_ambiguous_not_automatically_recovered(self):
    r = {'v1_overlap': False, 'status': 'ROUTE_IDENTITY_AMBIGUOUS'}
    self.assertEqual(m.route_classification(r, True, 'SOURCE_COMMIT_PUBLICLY_AVAILABLE'), 'ROUTE_SOURCE_AUDITED_IDENTITY_AMBIGUOUS')

  def test_prior_unknown_pool_not_holdout(self):
    rows = [{'route_id': str(i), 'classification': 'ROUTE_SOURCE_AUDITED_IDENTITY_COMPLETE', 'signal_semantics_complete': True,
                 'profile_complete': True, 'v1_overlap': False, 'semantic_class_id': 'a', 'empirical_profile_sha256': 'b', 'full_carparams_sha256': 'same',
                 'prior_analysis': 'UNKNOWN'} for i in range(2)]
    pool = m.train_dev_pool(rows)
    self.assertEqual(pool['status'], 'SOURCE_AUDITED_TRAIN_DEV_POOL_AVAILABLE')
    self.assertFalse(pool['pools'][0]['holdout_allowed'])
    self.assertFalse(pool['numeric_split_created'])

  def test_partial_semantics_not_pool(self):
    rows = [{'route_id': str(i), 'classification': 'ROUTE_SOURCE_AUDITED_IDENTITY_COMPLETE', 'signal_semantics_complete': False,
                 'profile_complete': True, 'v1_overlap': False} for i in range(3)]
    self.assertEqual(m.train_dev_pool(rows)['pools'], [])

  def test_same_route_not_two_candidates(self):
    row = {'route_id': 'a', 'classification': 'ROUTE_SOURCE_AUDITED_IDENTITY_COMPLETE', 'signal_semantics_complete': True,
               'profile_complete': True, 'v1_overlap': False, 'semantic_class_id': 'a', 'empirical_profile_sha256': 'b', 'full_carparams_sha256': 'same'}
    self.assertEqual(m.train_dev_pool([row, row])['pools'], [])

  def test_full_cp_difference_cannot_enter_same_pool(self):
    rows = [{'route_id': str(i), 'classification': 'ROUTE_SOURCE_AUDITED_IDENTITY_COMPLETE', 'signal_semantics_complete': True,
                 'profile_complete': True, 'v1_overlap': False, 'semantic_class_id': 'a', 'empirical_profile_sha256': 'b',
                 'full_carparams_sha256': str(i)} for i in range(2)]
    self.assertEqual(m.train_dev_pool(rows)['pools'], [])

  def test_adapter_code_drift(self):
    source = p.seal({'commit': 'a', 'complete': True})
    binding = p.seal({'commit': 'a', 'source_fingerprint_sha256': source['receipt_sha256'],
                     'logger_reviewed': True, 'schema_reviewed': True, 'adapter_source_sha256': 'wrong'})
    with self.assertRaisesRegex(ValueError, 'ADAPTER_CODE_DRIFT'):
      m.validate_adapter(binding, source)
