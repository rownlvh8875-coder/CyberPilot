import unittest
from openpilot.tools.cyber_autotune import empirical_simulator_prior_use as s


class TestSimulatorPriorUse(unittest.TestCase):
  def test_git_blob_exact_bytes(self):
    self.assertEqual(len(s.verify_blob('hello\n', 'ce013625030ba8dba906f756967f9e9ca394464a')), 64)

  def test_git_blob_content_drift(self):
    with self.assertRaisesRegex(ValueError, 'BLOB_IDENTITY'):
      s.verify_blob('changed\n', 'ce013625030ba8dba906f756967f9e9ca394464a')

  def test_git_blob_newline_drift(self):
    with self.assertRaisesRegex(ValueError, 'BLOB_IDENTITY'):
      s.verify_blob('hello', 'ce013625030ba8dba906f756967f9e9ca394464a')

  def test_truncated_tree_not_complete(self):
    with self.assertRaisesRegex(ValueError, 'TRUNCATED'):
      s.reconcile({'repositories': [{'tree': {'truncated': True}}]}, {}, {})

  def test_commit_drift_rejected(self):
    metadata = {'repositories': [{'repository': 'repo', 'commit': 'old', 'tree': {'truncated': False, 'tree': []}}]}
    with self.assertRaisesRegex(ValueError, 'COMMIT_DRIFT'):
      s.reconcile(metadata, {'repository': 'repo', 'commit': 'new'}, {})

  def test_not_run_result_does_not_prove_consumption(self):
    x = {'sha256': s.B26_RESULT_PIN, 'body': {'state': 'NOT_RUN', 'precommit_sha256': 'p', 'route_results': [{'route_id': 'a', 'window_count': 1}]}}
    self.assertEqual(s.evaluated_routes(x, 'p'), set())

  def test_reference_without_executed_route_not_consumed(self):
    x = {
      'sha256': s.B26_RESULT_PIN,
      'body': {'state': s.B26_RESULT_STATE, 'precommit_sha256': 'p', 'route_results': [{'route_id': 'a', 'window_count': 0}]},
    }
    self.assertEqual(s.evaluated_routes(x, 'p'), set())

  def test_wrong_result_digest_not_consumed(self):
    x = {'sha256': 'wrong', 'body': {'state': s.B26_RESULT_STATE, 'precommit_sha256': 'p', 'route_results': [{'route_id': 'a', 'window_count': 1}]}}
    self.assertEqual(s.evaluated_routes(x, 'p'), set())
