"""Public-only validation of the separately authorized V3 retrospective run."""

from collections import Counter
import unittest

from openpilot.tools.cyber_autotune import empirical_hurdle_v3_io as io

PREFIX = 'empirical-hurdle-stage1-v3-'


class TestV3ActualEvidence(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.pack = io.contracts()
    cls.names = ('execution-authorization', 'job-manifest', 'threshold-results', 'train-results',
                 'development-results', 'rollout-results', 'candidate-gates', 'selection-result',
                 'repeatability', 'v1-v2-comparison', 'retrospective-execution-readiness')
    cls.evidence = {name: io.read_json(io.p.PUBLIC / (PREFIX + name + '.json')) for name in cls.names}
    cls.ready = cls.evidence['retrospective-execution-readiness']
    cls.jobs = cls.evidence['threshold-results']['jobs']
    cls.gates = cls.evidence['candidate-gates']['jobs']

  def test_public_receipts_and_same_execution_binding(self):
    auth = self.evidence['execution-authorization']
    self.assertNotEqual(auth['authorized_head'], '3acd6543eff2b88b8128f6fb71a2b60f08ac5617')
    self.assertEqual(auth['base_policy_receipts'], self.pack['receipts'])
    amendment, migration = io.external.contracts()
    for artifact in self.evidence.values():
      self.assertEqual(artifact['execution_head'], auth['authorized_head'])
      self.assertEqual(artifact['authorization_sha256'], auth['authorization_sha256'])
      self.assertEqual(artifact['storage_amendment_receipt_sha256'], amendment['receipt_sha256'])
      self.assertEqual(artifact['storage_migration_receipt_sha256'], migration['receipt_sha256'])

  def test_exact_ordered_32_jobs_across_all_public_populations(self):
    for name in ('job-manifest', 'threshold-results', 'train-results', 'development-results',
                 'rollout-results', 'candidate-gates', 'v1-v2-comparison'):
      self.assertEqual([(j['candidate_id'], j['fold']) for j in self.evidence[name]['jobs']], list(io.JOBS))

  def test_reference_tp_identity_and_floor_integer_exact(self):
    passed = 0
    for job, reference in zip(self.jobs, self.pack['references'], strict=True):
      self.assertEqual(job['reference_tp'], reference['reference_tp'])
      objective = job['threshold']['objective']
      if objective is not None:
        self.assertIs(type(objective['tp']), int)
        self.assertGreaterEqual(objective['tp'], reference['reference_tp'])
        self.assertTrue(job['tp_constraint_pass'])
        passed += 1
    self.assertEqual(passed, self.ready['summary']['tp_constraint_satisfied_job_count'])

  def test_no_feasible_has_no_fallback_or_development(self):
    dev = self.evidence['development-results']['jobs']
    rollouts = self.evidence['rollout-results']['jobs']
    total = 0
    for job, scored, rollout, gate in zip(self.jobs, dev, rollouts, self.gates, strict=True):
      if job['status'] == 'NO_FEASIBLE_THRESHOLD':
        total += 1
        self.assertEqual(job['threshold']['status'], 'V3_NO_FEASIBLE_THRESHOLD')
        self.assertEqual(job['threshold']['feasible_count'], 0)
        self.assertIsNone(job['threshold']['objective'])
        self.assertNotIn('one_step', scored)
        self.assertEqual(rollout.get('rollout', {}), {})
        self.assertFalse(gate['gate']['pass'])
        self.assertTrue(all(not c['evaluated'] and not c['pass'] for c in gate['gate']['clauses']))
    self.assertEqual(total, self.ready['summary']['no_feasible_threshold_job_count'])

  def test_frozen_32_clause_gate_and_metric_operators(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_fit_cv_gates import OPS
    dev = self.evidence['development-results']['jobs']
    rollouts = self.evidence['rollout-results']['jobs']
    for job, scored, rollout in zip(self.gates, dev, rollouts, strict=True):
      self.assertEqual([c['id'] for c in job['gate']['clauses']], [c['id'] for c in self.pack['clauses']])
      for result, clause in zip(job['gate']['clauses'], self.pack['clauses'], strict=True):
        if clause['population'] == 'ALL_ONE_STEP':
          metric = scored.get('one_step')
        elif clause['population'] == 'TRUE_MOVE_ONE_STEP_INTEGRATED':
          metric = scored.get('true_move')
        else:
          group = 'overall' if clause['population'] == 'OVERALL_ROLLOUT' else 'path_moved'
          metric = rollout.get('rollout', {}).get(str(clause['horizon_steps']), {}).get(group)
        self.assertEqual(result['evaluated'], metric is not None)
        if metric is not None:
          self.assertEqual(metric['anchor_sha256'], metric['comparator_anchor_sha256'])
          key = clause['metric'].lower()
          expected = metric['count'] >= 201 and OPS[clause['operator']](metric['candidate'][key], metric['comparator'][key])
          self.assertEqual(result['pass'], expected)
      expected = job['status'] == 'EXECUTED_COMPLETE' and all(c['pass'] for c in job['gate']['clauses'])
      self.assertEqual(job['gate']['pass'], expected)

  def test_both_fold_admission_and_selection_only_among_admissible(self):
    selected = self.evidence['selection-result']['selection']
    admitted = [io.JOBS[i][0] for i in range(0, 32, 2) if all(j['gate']['pass'] for j in self.gates[i:i + 2])]
    self.assertEqual(selected['admissible_count'], len(admitted))
    if admitted:
      self.assertIn(selected['selected_candidate'], admitted)
      self.assertEqual({r['candidate_id'] for r in selected['ranking']}, set(admitted))
    else:
      self.assertIsNone(selected['selected_candidate'])
      self.assertIn('MODEL_SELECTION_FAILED_CLOSED', selected['states'])
    for fold in ('FOLD_A', 'FOLD_B'):
      count = sum(j['gate']['pass'] for j in self.gates if j['fold'] == fold)
      self.assertEqual(count, self.ready['summary']['folds'][fold]['complete_gate_pass_count'])

  def test_clause_aggregate_reconciles_evaluated_and_unevaluated(self):
    artifact = self.evidence['candidate-gates']
    for i, clause in enumerate(self.pack['clauses']):
      rows = [j['gate']['clauses'][i] for j in self.gates]
      key = clause['id']
      self.assertEqual(artifact['failure_counts'][key], sum(not c['pass'] for c in rows))
      self.assertEqual(artifact['evaluated_failure_counts'][key], sum(c['evaluated'] and not c['pass'] for c in rows))
      self.assertEqual(artifact['evaluated_job_counts'][key], sum(c['evaluated'] for c in rows))

  def test_report_only_same_anchor_comparison(self):
    artifact = self.evidence['v1-v2-comparison']
    self.assertEqual(artifact['authority'], 'REPORT_ONLY')
    for job in artifact['jobs']:
      report = job['comparison']
      self.assertEqual(report['authority'], 'REPORT_ONLY')
      if report.get('status') == 'V3_DECISION_UNAVAILABLE':
        continue
      for key in ('one_step', 'true_move'):
        anchors = [report[key][version]['anchor_sha256'] for version in ('v1', 'v2', 'v3')]
        self.assertEqual(len(set(anchors)), 1)
      for transitions in report['clauses'].values():
        joined = sum(transitions.values(), [])
        self.assertEqual(Counter(joined), Counter(c['id'] for c in self.pack['clauses']))

    transitions = artifact['clause_transitions']
    self.assertEqual([(r['candidate_id'], r['fold']) for r in transitions], list(io.JOBS))
    for row, gate in zip(transitions, self.gates, strict=True):
      self.assertEqual(row['authority'], 'REPORT_ONLY')
      self.assertEqual(row['v3_evaluated_clause_count'], sum(c['evaluated'] for c in gate['gate']['clauses']))
      for version in ('v1', 'v2'):
        joined = sum(row[version].values(), [])
        self.assertEqual(Counter(joined), Counter(c['id'] for c in self.pack['clauses']))

  def test_repeatability_resume_and_source_immutability(self):
    artifact = self.evidence['repeatability']
    repeated = artifact['repeatability']
    self.assertEqual(repeated['status'], 'V3_EXACT_REPEATABILITY_PASS')
    self.assertEqual(repeated['run1_manifest_sha256'], repeated['run2_manifest_sha256'])
    self.assertEqual(repeated['resume'], 'V3_VERIFY_ONLY_RESUME_PASS')
    self.assertTrue(repeated['all_file_content_decoded_hashes_equal'])
    self.assertTrue(repeated['run2_scratch_retained'])
    immutable = artifact['source_immutability']
    self.assertEqual(immutable['status'], 'SOURCE_BYTES_UNCHANGED')
    for key in ('source_writes', 'causal_writes', 'derived_writes', 'model_writes'):
      self.assertEqual(immutable[key], 0)

  def test_privacy_authority_and_historical_verdict_preserved(self):
    forbidden = {'value', 'coefficients', 'normalizer', 'private_build_metadata', 'current_tick', 'target_next_tick',
                 'p_move', 'predicted_gate', 'projected_path', 'actual_threshold', 'threshold_bytes'}
    def visit(row, key=''):
      if isinstance(row, dict):
        self.assertFalse(forbidden.intersection(row))
        for child, item in row.items():
          visit(item, child)
      elif isinstance(row, list):
        for item in row:
          visit(item, key)
      elif isinstance(row, str):
        for token in ('/mnt/', '/home/', 'E:\\', 'D:\\', 'C:\\', 'file://'):
          self.assertNotIn(token, row)
      if key == 'threshold':
        self.assertTrue(row is None or isinstance(row, dict))
    for artifact in self.evidence.values():
      visit(artifact)
      self.assertEqual(artifact['holdout'], 'CLOSED')
      self.assertEqual(artifact['opening_count'], 0)
      self.assertEqual(artifact['holdout_discovery'], 0)
      self.assertEqual(artifact['vehicle_authority'], 'NONE')
      self.assertIn('HURDLE_NO_ADMISSIBLE_CANDIDATE', artifact['historical_states_preserved'])
      self.assertIn('HURDLE_STAGE1_V2_NO_ADMISSIBLE_CANDIDATE', artifact['historical_states_preserved'])
    self.assertEqual(self.ready['stage1_refit_calls'], 0)
    self.assertEqual(self.ready['stage2_refit_calls'], 0)
    self.assertEqual(self.ready['normalizer_refit_calls'], 0)
