"""Public-only checks of the two authorized V4 retrospective replicas."""
from collections import Counter
import hashlib
import re
import unittest

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_execution as e

PREFIX = 'empirical-hurdle-stage1-v4-'
NAMES = (
  'retrospective-execution-readiness', 'retrospective-execution-authorization',
  'job-manifest', 'fit-results', 'development-results', 'rollout-results',
  'candidate-gates', 'selection-result', 'repeatability-actual', 'resume-actual',
  'v1-v2-v3-comparison', 'retrospective-execution-validation',
)
HEAD = 'bd8045ef2a0da62a92603439f38e7740f5923622'
AUTH = 'a23e88b37ba1b2b57f5eb29bc37508166a6a392354826d00bb4444d8efcdc34c'
MANIFEST = 'fd3639f93944edecfdfa573818d29fbc8a91ab23208e2d561f8a69726eb0dc64'
GROUPS = ('EXECUTED_COMPLETE', 'V4_STAGE1_FIT_FAILED_CLOSED',
          'DEVELOPMENT_OR_ROLLOUT_FAILURE', 'ROLLOUT_FAILURE')


class TestV4ActualEvidence(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.pack = e.a.contracts()
    cls.artifacts = {n: e.a.prior.read_json(e.p.PUBLIC / (PREFIX + n + '.json')) for n in NAMES}
    cls.ready = cls.artifacts['retrospective-execution-readiness']
    cls.expected = [(j['candidate_id'], j['fold']) for j in cls.pack['jobs']]
    cls.gates = cls.artifacts['candidate-gates']['jobs']
    cls.dev = cls.artifacts['development-results']['jobs']
    cls.roll = cls.artifacts['rollout-results']['jobs']
    cls.combined = [{**g, **{k: v for k, v in d.items() if k in ('one_step', 'true_move')},
                     'rollout': r.get('rollout', {})}
                    for g, d, r in zip(cls.gates, cls.dev, cls.roll, strict=True)]

  def test_canonical_receipts_and_exact_execution_binding(self):
    for artifact in self.artifacts.values():
      self.assertEqual(e.p.verify(artifact), artifact)
      self.assertEqual(artifact['execution_head'], HEAD)
      self.assertEqual(artifact['authorization_sha256'], AUTH)
      self.assertEqual(artifact['private_manifest_sha256'], MANIFEST)
      self.assertEqual(artifact['result_publication_head'], {'resolution': 'CONTAINING_GIT_COMMIT'})
    auth = self.artifacts['retrospective-execution-authorization']
    self.assertEqual(auth['executor_sources'], e.a.sources())
    self.assertEqual(auth['policies'], self.pack['policies'])
    self.assertEqual(auth['executor_contract_receipts'], self.pack['executor_contract_receipts'])
    self.assertTrue(auth['execution_snapshot_verified_against_git'])
    self.assertEqual(self.ready['execution_ci']['head'], HEAD)
    self.assertEqual(self.ready['execution_ci']['conclusion'], 'success')

  def test_exact_32_job_populations_and_status_accounting(self):
    for name in ('job-manifest', 'fit-results', 'development-results', 'rollout-results',
                 'candidate-gates', 'v1-v2-v3-comparison'):
      rows = self.artifacts[name]['jobs']
      self.assertEqual([(j['candidate_id'], j['fold']) for j in rows], self.expected)
    actual = Counter(j['status'] for j in self.gates)
    expected = {k: actual[k] for k in GROUPS}
    self.assertEqual(expected, self.ready['summary']['status_distribution'])
    self.assertEqual(sum(expected.values()), 32)
    self.assertEqual(expected['EXECUTED_COMPLETE'], 32)
    self.assertEqual(self.ready['summary']['evaluated_job_count'], len([j for j in self.dev if 'one_step' in j]))

  def test_both_head_preconditions_and_frozen_dimensions(self):
    rows = self.artifacts['fit-results']['jobs']
    for head in ('STATIC', 'MOVE'):
      for phase in ('support', 'rank', 'separation', 'convergence'):
        counts = dict(Counter(j['head_checks'][head][phase]['status'] for j in rows))
        self.assertEqual(counts, self.ready['summary']['head_preconditions'][head][phase])
      for job in rows:
        checks = job['head_checks'][head]
        length = int(job['candidate_id'].split('_L')[1])
        self.assertEqual(checks['support']['parameters'], 2 * length + (2 if head == 'STATIC' else 3))
        self.assertEqual(checks['support']['status'], 'PASS')
        self.assertTrue(checks['support']['class_minimum_pass'])
        self.assertTrue(checks['support']['rows_exceed_parameters'])
        self.assertEqual(checks['rank']['status'], 'RANK_CERTIFICATE_PASS')
        self.assertEqual(checks['separation']['status'], 'NO_SEPARATION')
        self.assertEqual(checks['convergence']['status'], 'CONVERGED')
        self.assertLessEqual(checks['convergence']['updates'], 100)
        for phase in ('rank', 'separation'):
          self.assertRegex(checks[phase]['certificate_sha256'], r'^[0-9a-f]{64}$')

  def test_no_fallback_v1_reuse_and_train_finalize_before_dev(self):
    for job, old in zip(self.artifacts['job-manifest']['jobs'], self.pack['jobs'], strict=True):
      self.assertFalse(job['fallback'])
      self.assertTrue(job['train_finalized_before_dev'])
      self.assertTrue(job['combined_original_order_train_score_saved'])
      self.assertTrue(job['single_global_train_only_threshold_saved'])
      self.assertEqual(job['v1_stage1_normalizer_receipt_sha256'], old['stage1']['normalizer_receipt_sha256'])
      self.assertEqual(job['v1_stage2_receipts_sha256'], e.p.sha(e.p.canonical(old['stage2'])))
      for key in ('job_receipt_sha256', 'train_finalized_sha256', 'train_manifest_sha256', 'train_receipt_sha256'):
        self.assertRegex(job[key], r'^[0-9a-f]{64}$')
    self.assertEqual(self.ready['stage2_refit_calls'], 0)
    self.assertEqual(self.ready['normalizer_refit_calls'], 0)
    self.assertEqual(self.ready['pooled_refit_calls'], 0)
    self.assertEqual(self.artifacts['fit-results']['threshold_policy'], 'ONE_GLOBAL_NEW_COMBINED_V4_TRAIN_SCORE_PER_JOB_V1_BA')
    self.assertEqual(self.artifacts['fit-results']['regularization'], 'NONE')

  def test_frozen_32_clause_gate_and_exact_saved_selection(self):
    for job in self.combined:
      self.assertEqual([c['id'] for c in job['gate']['clauses']], [c['id'] for c in self.pack['clauses']])
      self.assertEqual(e.gates.fold_gate(job, self.pack['clauses']), job['gate'])
    selected = self.artifacts['selection-result']
    self.assertEqual(e.select(self.combined, self.pack['clauses']), selected['selection'])
    self.assertEqual(selected['outcome_status'], 'HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE')
    self.assertIsNone(selected['selection']['selected_candidate'])
    self.assertEqual(selected['selection']['admissible_count'], 0)
    for fold in ('FOLD_A', 'FOLD_B'):
      self.assertEqual(sum(j['gate']['pass'] for j in self.gates if j['fold'] == fold),
                       self.ready['summary']['folds'][fold]['complete_gate_pass_count'])

  def test_clause_counts_separate_evaluated_failures_from_closed_failures(self):
    artifact = self.artifacts['candidate-gates']
    for i, clause in enumerate(self.pack['clauses']):
      rows = [j['gate']['clauses'][i] for j in self.gates]
      key = clause['id']
      self.assertEqual(artifact['failure_counts'][key], sum(not c['pass'] for c in rows))
      self.assertEqual(artifact['evaluated_failure_counts'][key], sum(c['evaluated'] and not c['pass'] for c in rows))
      self.assertEqual(artifact['evaluated_job_counts'][key], sum(c['evaluated'] for c in rows))

  def test_metrics_use_frozen_same_anchor_denominators(self):
    for dev, roll in zip(self.dev, self.roll, strict=True):
      metrics = [dev[k] for k in ('one_step', 'true_move') if k in dev]
      for horizon in ('25', '50', '100', '200'):
        metrics.extend(roll.get('rollout', {}).get(horizon, {}).get(k) for k in ('overall', 'path_moved'))
      for metric in metrics:
        if metric is not None:
          self.assertEqual(metric['anchor_sha256'], metric['comparator_anchor_sha256'])
          self.assertGreaterEqual(metric['count'], 201)

  def test_actual_repeatability_resume_and_source_immutability(self):
    repeated = self.artifacts['repeatability-actual']
    self.assertEqual(repeated['status'], 'V4_EXACT_REPEATABILITY_PASS')
    self.assertTrue(repeated['all_file_hashes_equal'])
    self.assertTrue(repeated['decoded_array_identities_verified'])
    self.assertEqual(repeated['run1_manifest_sha256'], repeated['run2_manifest_sha256'])
    self.assertEqual(repeated['replicas_retained'], ['repeat-1', 'repeat-2'])
    self.assertFalse(repeated['telemetry_participates_in_scientific_identity'])
    resumed = self.artifacts['resume-actual']
    self.assertEqual(resumed['status'], 'V4_VERIFY_ONLY_RESUME_PASS')
    self.assertEqual(resumed['recompute_calls'], 0)
    self.assertEqual([r['replica'] for r in resumed['replicas']], ['repeat-1', 'repeat-2'])
    self.assertTrue(all(r['status'] == 'PASS' and r['recompute_calls'] == 0 for r in resumed['replicas']))
    self.assertEqual(set(resumed['trapped_functions']), {
      'load_route', 'load_models', 'rank_generate', 'separation_generate', 'newton',
      'threshold', 'train', 'probability', 'development', 'recursive', 'rollout', 'select',
    })
    immutable = repeated['source_immutability']
    self.assertEqual(immutable['status'], 'PASS')
    self.assertEqual(immutable['source_writes'], 0)
    for key in ('source_bytes_unchanged', 'causal_bytes_unchanged', 'derived_bytes_unchanged',
                'v1_models_unchanged', 'v1_normalizers_unchanged', 'full_authorized_manifest_members_verified'):
      self.assertTrue(immutable[key])

  def test_capacity_environment_and_external_authorization(self):
    auth = self.artifacts['retrospective-execution-authorization']
    capacity = auth['capacity_preflight']
    self.assertGreaterEqual(capacity['free_bytes'], capacity['required_bytes'])
    self.assertEqual(capacity['required_bytes'], 42704404308)
    self.assertEqual(capacity['free_bytes'], 51654926336)
    self.assertEqual(self.ready['free_bytes_after'], 51017584640)
    self.assertEqual(auth['resource_budget'], {
      'certificate_integer_bits': 395253, 'metadata_bytes_per_job': 134217728, 'reserve_bytes': 2147483648,
    })
    self.assertEqual(auth['environment']['python'], '3.12.13')
    self.assertEqual(auth['environment']['numpy'], '2.5.3')
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS'):
      self.assertEqual(str(auth['environment'][key]), '1')
    self.assertEqual(auth['environment']['dtype'], 'float64')
    self.assertEqual(auth['environment']['order'], 'C')
    self.assertEqual(auth['environment']['rng'], 'NONE')
    self.assertTrue(auth['external_one_shot_minter'])
    self.assertFalse(auth['executor_minted_authorization'])
    allowed = {'numeric_access_authorized', 'stage1_train_fit_authorized', 'train_only_decision_authorized'}
    for key, flag in auth['authorization_flags'].items():
      self.assertIs(flag, key in allowed)
    processes = [r['process_identity_sha256'] for r in self.ready['replicas']]
    self.assertEqual(len(set(processes)), 2)

  def test_historical_sources_and_common_comparison_are_preserved(self):
    artifact = self.artifacts['v1-v2-v3-comparison']
    self.assertEqual(artifact['authority'], 'REPORT_ONLY')
    for name, expected in artifact['historical_artifact_sha256'].items():
      self.assertEqual(hashlib.sha256((e.p.PUBLIC / name).read_bytes()).hexdigest(), expected)
    versions = ('v1', 'v2', 'v3', 'v4')
    for row in artifact['jobs']:
      for population in ('one_step', 'true_move'):
        metrics = [row['versions'][v].get(population) for v in versions]
        available = [m for m in metrics if m is not None]
        self.assertEqual(len({(m['anchor_sha256'], m['count']) for m in available}), 1)
        self.assertTrue(all(m['comparator'] == available[0]['comparator'] for m in available))
    for i, clause in enumerate(self.pack['clauses']):
      common = [r for r in artifact['jobs'] if all(r['versions'][v]['gate']['clauses'][i]['evaluated'] for v in versions)]
      saved = artifact['common_evaluated'][clause['id']]
      self.assertEqual(saved['job_count'], len(common))
      for version in versions:
        self.assertEqual(saved['failures'][version], sum(not r['versions'][version]['gate']['clauses'][i]['pass'] for r in common))
    self.assertEqual(artifact['family_summaries']['v3']['evaluated_job_count'], 31)
    self.assertEqual(artifact['family_summaries']['v4']['evaluated_job_count'], 32)

  def test_publication_privacy_authority_and_historical_states(self):
    forbidden = {
      'coefficients', 'normalizer', 'private_build_metadata', 'actual_threshold', 'threshold',
      'combined_probability', 'p_move', 'predicted_gate', 'projected_path', 'raw_basis_indices',
      'transformed_basis_indices', 'direction', 'active', 'determinant', 'rank_row_indices',
      'current_tick', 'target_next_tick', 'gps', 'timestamps',
    }
    def visit(value):
      if isinstance(value, dict):
        self.assertFalse(forbidden.intersection(value))
        for child in value.values():
          visit(child)
      elif isinstance(value, list):
        for child in value:
          visit(child)
      elif isinstance(value, str):
        self.assertIsNone(re.search(r'(?i)(?:[cdef]:[\\/]|/mnt/|/home/|file://|\\\\wsl)', value))
    for artifact in self.artifacts.values():
      visit(artifact)
      self.assertEqual(artifact['holdout'], 'CLOSED')
      self.assertEqual(artifact['opening_count'], 0)
      self.assertEqual(artifact['holdout_discovery'], 0)
      self.assertEqual(artifact['vehicle_authority'], 'NONE')
      self.assertEqual(artifact['model_admission'], 'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT')
      self.assertEqual(artifact['final_pooled_refit'], 'NOT_AUTHORIZED')
      self.assertFalse(artifact['threshold_values_public'])
      self.assertFalse(artifact['coefficients_public'])
      self.assertIn('HURDLE_STAGE1_V3_NO_ADMISSIBLE_CANDIDATE', artifact['historical_states_preserved'])
    self.assertEqual(self.ready['hugging_face'], 'NOT_REQUIRED_NOT_USED')

  def test_validation_status_never_claims_unperformed_checks(self):
    validation = self.artifacts['retrospective-execution-validation']
    self.assertIn(validation['publication_validation'], ('PENDING', 'PASS'))
    if validation['publication_validation'] == 'PASS':
      required = {'actual_focused', 'v4_executor', 'prior', 'combined', 'full', 'lateral',
                  'ruff', 'compileall', 'json', 'publication', 'diff-check', 'scons'}
      self.assertTrue(required.issubset(validation['checks']))
      self.assertTrue(all(row['exit_code'] == 0 for row in validation['checks'].values()))
      self.assertEqual({k: v['status'] for k, v in validation['reviews'].items()},
                       {'numerical': 'APPROVED', 'authority': 'APPROVED'})


if __name__ == '__main__':
  unittest.main()
