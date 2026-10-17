"""Public requirements/schema and synthetic truth contracts; no scientific imports."""

import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[4]
PUBLIC = ROOT / 'docs/cyberpilot/changes'
BASE = 'cb344b0d1e738baa780c503bee838386ff21865b'
PREFIX = 'empirical-hurdle-stage1-v4-decision-policy-'
LABELS = ('requirements-policy', 'requirements-spec', 'protection-matrix', 'tradeoff-matrix', 'fold-requirements',
          'evidence-gate', 'approval-matrix', 'future-validation', 'review-decision', 'review-validation')
FIELDS = {'requirement_id', 'name', 'normative_level', 'description', 'responsible_component', 'failure_mode',
          'supporting_evidence', 'counterevidence', 'source_contract', 'observable_metric', 'existing_acceptance_gate',
          'missing_evidence', 'future_validation_method', 'approval_required', 'privacy_constraint', 'safety_impact', 'verification_status'}
COUNTERS = ('model_refit_calls', 'normalizer_refit_calls', 'stage2_refit_calls', 'calibration_fit_calls', 'threshold_reselection_calls',
            'prediction_replay_calls', 'rollout_regeneration_calls', 'selection_calls', 'candidate_search_calls', 'raw_log_openings',
            'qlog_openings', 'holdout_openings', 'holdout_discovery', 'private_array_openings', 'source_write_count', 'vehicle_activation_calls')
FIREWALL = ('qualification_allowed', 'reference_promotable', 'sealed_reference_allowed', 'vehicle_activation_allowed', 'production_authority',
            'ta_execution', 'sg_execution', 'composition_authorized', 'candidate_search_authorized', 'publication_raw_data')
PRIVATE_KEYS = {'threshold', 'threshold_value', 'coefficients', 'normalizer_values', 'probabilities', 'p_move', 'score_vector', 'raw_scores',
                'raw_ticks', 'projected_path', 'predicted_gate', 'predicted_gate_path', 'gate_sequence', 'observed_path', 'commands', 'gps',
                'timestamps', 'private_root', 'witness_row_indices', 'calibration_parameters', 'row_scores', 'row_gates'}
PRIVATE_PATH = re.compile(r'(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|/(?:mnt|home|Users|tmp)/|\\\\)')


def canonical(value):
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def verify(value):
  body = {k: v for k, v in value.items() if k != 'receipt_sha256'}
  if value.get('receipt_sha256') != hashlib.sha256(canonical(body)).hexdigest():
    raise ValueError('RECEIPT_CONFLICT')
  if any(value.get(key) is not False for key in FIREWALL):
    raise ValueError('AUTHORITY_CONFLICT')
  return value


def doc(label):
  return verify(json.loads((PUBLIC / (PREFIX + label + '.json')).read_bytes()))


def privacy(value):
  if isinstance(value, dict):
    if any(k.lower() in PRIVATE_KEYS for k in value):
      raise ValueError('PRIVATE_PAYLOAD')
    for child in value.values():
      privacy(child)
  elif isinstance(value, list):
    for child in value:
      privacy(child)
  elif isinstance(value, str) and PRIVATE_PATH.search(value):
    raise ValueError('PRIVATE_PATH')


def refs(value):
  if isinstance(value, dict):
    if {'file', 'git_sha'} <= value.keys():
      yield value
    for child in value.values():
      yield from refs(child)
  elif isinstance(value, list):
    for child in value:
      yield from refs(child)


def resolve(value, tokens):
  if tokens == ['']:
    return
  if tokens:
    token, *rest = tokens
    if token == '*':
      for child in value.values() if isinstance(value, dict) else value:
        resolve(child, rest)
    else:
      resolve(value[int(token)] if isinstance(value, list) else value[token.replace('~1', '/').replace('~0', '~')], rest)


class TestDecisionPolicyRequirements(unittest.TestCase):
  def test_requested_artifacts_and_common_scope(self):
    policy = doc('requirements-policy')
    for label in LABELS:
      row = doc(label)
      self.assertEqual(row['component'], label)
      self.assertEqual(row['baseline_head'], BASE)
      self.assertEqual(row['scope'], ['REQUIREMENTS_REVIEW_ONLY', 'REPORT_ONLY', 'PUBLIC_EVIDENCE_ONLY', 'NO_NEW_MODEL_EXECUTION'])
      self.assertFalse(row['next_execution_authorized'])
      if label != 'requirements-policy':
        self.assertEqual(row['requirements_policy_receipt_sha256'], policy['receipt_sha256'])

  def test_public_input_seals_and_git_identity(self):
    lock = doc('requirements-policy')['input_lock']
    self.assertEqual(len(lock['files']), 55)
    self.assertEqual(len(lock['sources']), 17)
    self.assertEqual(lock['previous_lock_counts'], {'public_files': 45, 'sealed_json': 42, 'static_sources': 17})
    sealed = 0
    for entry in [*lock['files'].values(), *lock['sources'].values(), lock['workflow_pin']]:
      raw = (ROOT / entry['path']).read_bytes()
      self.assertEqual(hashlib.sha256(raw).hexdigest(), entry.get('file_sha256', entry.get('sha256')))
      self.assertEqual(raw, subprocess.check_output(['git', 'show', BASE + ':' + entry['path']], cwd=ROOT))
      if entry.get('receipt_sha256'):
        self.assertEqual(verify(json.loads(raw))['receipt_sha256'], entry['receipt_sha256'])
        sealed += 1
    self.assertEqual(sealed, 51)

  def test_references_resolve_with_source_symbols(self):
    lock = doc('requirements-policy')['input_lock']
    for label in LABELS:
      for ref in refs(doc(label)):
        self.assertEqual(ref['git_sha'], BASE)
        if 'pointer' in ref:
          entry = lock['files'][ref['file']]
          self.assertEqual(ref['file_sha256'], entry['file_sha256'])
          resolve(json.loads((ROOT / entry['path']).read_bytes()), ref['pointer'].strip('/').split('/'))
        elif 'symbol' in ref:
          entry = lock['sources'][ref['file']]
          self.assertEqual(ref['source_sha256'], entry['sha256'])
          body = ast.parse((ROOT / entry['path']).read_text()).body
          nodes = {n.name: n for n in body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
          self.assertEqual(ref['line'], nodes[ref['symbol']].lineno)

  def test_original_execution_scientific_sources_immutable(self):
    row = doc('requirements-policy')
    for name in row['input_lock']['original_execution_scientific_files']:
      relative = row['input_lock']['sources'][name]['path']
      self.assertEqual((ROOT / relative).read_bytes(), subprocess.check_output(['git', 'show', row['execution_head'] + ':' + relative], cwd=ROOT))

  def test_requirement_ids_and_all_required_fields(self):
    rows = doc('requirements-spec')['requirements']
    self.assertEqual([r['requirement_id'] for r in rows], [f'R{i:02}' for i in range(1, 18)])
    for row in rows:
      self.assertEqual(set(row), FIELDS)
      self.assertTrue(row['supporting_evidence'])
      self.assertTrue(row['source_contract'])
      self.assertTrue(row['future_validation_method'])
      self.assertTrue(row['approval_required'])
      self.assertEqual(row['verification_status'], 'DOCUMENT_TRACEABILITY_VERIFIED_NOT_FUTURE_POLICY_COMPLIANCE')

  def test_normative_distribution_and_narrow_unresolved_scope(self):
    row = doc('requirements-spec')
    self.assertEqual(row['normative_distribution'], {'MUST': 14, 'SHOULD': 1, 'FUTURE_APPROVAL_REQUIRED': 1, 'UNRESOLVED': 1})
    levels = {r['requirement_id']: r['normative_level'] for r in row['requirements']}
    self.assertEqual(levels['R02'], 'FUTURE_APPROVAL_REQUIRED')
    self.assertEqual(levels['R11'], 'UNRESOLVED')
    self.assertEqual(levels['R17'], 'SHOULD')
    self.assertTrue(row['mandatory_diagnostic_reporting_independent_of_level'])
    self.assertFalse(row['future_policy_performance_compliance_verified'])
    self.assertIn('CAUSAL_SHARE', row['requirements'][10]['description'])

  def test_truth_populations_are_disjoint_and_complete_synthetic(self):
    states = doc('protection-matrix')['transitions']
    actual = {(r['z_truth'], r['y_true']): r['state'] for r in states}
    self.assertEqual(actual, {(0, 0): 'STATIC_HOLD', (0, 1): 'MOVE_ONSET', (1, 0): 'MOVE_TERMINATION', (1, 1): 'MOVE_CONTINUATION'})
    for prev in (0, 1):
      for future in (0, 1):
        self.assertEqual(sum((r['z_truth'], r['y_true']) == (prev, future) for r in states), 1)

  def test_truth_is_not_routing_or_inference_input(self):
    row = doc('protection-matrix')
    self.assertFalse(row['future_truth_is_inference_input'])
    self.assertEqual(row['recursive_routing'], 'PROJECTED_PRIOR_DELTA_NOT_FUTURE_TRUTH_CELL')
    for state in row['transitions']:
      self.assertEqual(state['one_step_head'], ('STATIC_CONTEXT_HEAD', 'MOVE_CONTEXT_HEAD')[state['z_truth']])
      self.assertEqual(state['desired_gate'], ('STATIC', 'MOVE')[state['y_true']])
      self.assertTrue(state['correct_projected_tick_requirement'])

  def test_existing_policy_contract_preserved(self):
    row = doc('requirements-policy')['existing_contract']
    self.assertEqual(row['decision_scope'], 'ONE_PER_CANDIDATE_FOLD_SHARED_BY_TWO_HEADS')
    self.assertEqual(row['routing'], 'RAW_PRIOR_DELTA_NONZERO_BEFORE_NORMALIZATION')
    self.assertEqual(row['comparison'], 'STRICT_SCORE_GT_FROZEN_DECISION_EQUALITY_STATIC')
    self.assertEqual(row['objective_order'], ['BA_NUM', 'TN', 'LARGER_TRAIN_DECISION'])
    self.assertEqual(row['projection'], 'FINITE_THEN_TIES_TO_EVEN_THEN_SIGNED16_RANGE_CHECK_NO_CLIP')
    self.assertFalse(row['binary_ba_objective_equals_tick_exact_hit_objective'])

  def test_gate_and_realization_allowed_states(self):
    row = doc('protection-matrix')['gate_realization']
    self.assertEqual(row['successful_allowed_pairs'], [['STATIC', 'HOLD'], ['MOVE', 'HOLD'], ['MOVE', 'MOVE']])
    self.assertFalse(row['force_nonzero_movement_authorized'])
    self.assertFalse(row['gate_correct_implies_exact_tick_correct'])
    self.assertEqual(row['invalid_projection'], 'RAISE_FAIL_CLOSED_NO_CLIP_OR_FALLBACK')

  def test_frozen_exact_hit_identity(self):
    facts = doc('requirements-policy')['frozen_facts']
    lock = doc('requirements-policy')['input_lock']
    original = json.loads((ROOT / lock['files']['MIXED_EVIDENCE_LEDGER']['path']).read_bytes())['facts']['E1']['values']
    self.assertEqual(facts['exact_hit'], {'static_loss': 571317, 'move_gain': 228164, 'net_delta': -343153, 'jobs_loss_gt_gain': 32})
    self.assertEqual(facts['exact_hit']['static_loss'], original['static_hit_loss'])
    self.assertEqual(facts['exact_hit']['move_gain'], original['move_hit_gain'])
    self.assertEqual(facts['exact_hit']['move_gain'] - facts['exact_hit']['static_loss'], facts['exact_hit']['net_delta'])

  def test_frozen_gate_fp_identity_and_no_forced_move(self):
    facts = doc('requirements-policy')['frozen_facts']['gate_fp']
    self.assertEqual(facts, {'count': 1662235, 'projected_hold': 1090918, 'harmful_movement': 571317, 'harmful_fraction_percent_display': '34.37'})
    self.assertEqual(facts['projected_hold'] + facts['harmful_movement'], facts['count'])

  def test_frozen_transition_and_fold_facts(self):
    row = doc('requirements-policy')['frozen_facts']
    self.assertEqual(row['transition_percent_display']['onset_recall'], {'FOLD_A': '40.195', 'FOLD_B': '2.147'})
    self.assertEqual(row['transition_percent_display']['termination_fp'], {'FOLD_A': '100', 'FOLD_B': '100'})
    self.assertEqual(row['fold_job_means']['score_shift'], {'FOLD_A': 0.017882, 'FOLD_B': -0.009916})
    self.assertEqual(row['fold_job_means']['calibration_bias_shift'], {'FOLD_A': 0.022050, 'FOLD_B': -0.014084})

  def test_rank_calibration_decision_and_statistic_scopes(self):
    row = doc('requirements-policy')['frozen_facts']
    self.assertEqual(row['historical_auc_counts'], {'OVERALL': [32, 0, 0], 'PREV_STATIC': [13, 0, 19], 'PREV_MOVE': [32, 0, 0]})
    self.assertEqual(row['auc_job_means']['OVERALL'], {'train': 0.707438, 'development': 0.702174})
    self.assertIn('OVERLAPPING', row['transition_statistic_scope'])
    self.assertIn('JOB_MEANS', row['auc_statistic_scope'])
    self.assertFalse(row['overall_rank_improvement_guarantees_state_decision_improvement'])
    self.assertFalse(row['mean_calibration_bias_is_conditional_reliability'])

  def test_both_folds_and_no_averaging_away_failure(self):
    row = doc('fold-requirements')
    self.assertEqual([r['fold'] for r in row['folds']], ['FOLD_A', 'FOLD_B'])
    self.assertTrue(row['both_fold_requirement_unchanged'])
    self.assertFalse(row['train_dev_rows_assumed_identical'])
    self.assertEqual(len(row['required_domains']), 10)
    self.assertFalse(row['new_fold_acceptance_cutoffs'])

  def test_32_clause_gate_binding_and_comparator_preserved(self):
    row = doc('requirements-policy')['frozen_gate']
    self.assertEqual(row['clause_count'], 32)
    self.assertTrue(row['inequalities_anchors_support_comparator_both_folds_unchanged'])
    self.assertTrue(row['policy_ref'])
    self.assertFalse(row['new_diagnostic_promoted_to_acceptance'])

  def test_no_new_policy_cutoffs_or_efficacy(self):
    row = doc('requirements-policy')
    for key in ('new_acceptance_cutoffs', 'policies_selected', 'alternative_decisions_evaluated', 'calibration_corrections_fitted'):
      self.assertEqual(row[key], [])
    self.assertFalse(row['policy_efficacy_established'])
    self.assertFalse(row['new_scientific_metrics_allowed'])

  def test_all_tradeoffs_are_possible_not_intervention_proven(self):
    rows = doc('tradeoff-matrix')['tradeoffs']
    self.assertEqual([r['id'] for r in rows], list('ABCDEFG'))
    for row in rows:
      self.assertEqual(row['effect_state'], 'POSSIBLE_TRADEOFF_NOT_PROVEN')
      self.assertFalse(row['changed_policy_tradeoff_confirmed'])
      self.assertTrue(row['observed_coexistence'])
      self.assertTrue(row['evidence_missing'])
      self.assertTrue(row['authorization_needed'])

  def test_m1_m9_availability_and_authority_classes(self):
    rows = doc('evidence-gate')['requirements']
    self.assertEqual([r['id'] for r in rows], [f'M{i}' for i in range(1, 10)])
    for row in rows[:3]:
      self.assertEqual(row['availability'], 'PUBLIC_ONLY_AVAILABLE')
      self.assertTrue(row['feasible_without_private_data'])
    for row in rows[3:7]:
      self.assertEqual(row['authorization_class'], 'SEPARATE_DATA_AND_PROCESSING_APPROVAL_REQUIRED')
      self.assertFalse(row['feasible_without_private_data'])
    for row in rows[7:]:
      self.assertEqual(row['authorization_class'], 'SEPARATE_POLICY_AND_EXECUTION_APPROVAL_REQUIRED')

  def test_missing_train_gates_never_invented(self):
    row = doc('evidence-gate')
    self.assertEqual(row['train_rowwise_gate'], 'NOT_SAVED_INPUT_INSUFFICIENT_NO_THRESHOLD_APPLICATION')
    self.assertFalse(row['train_transition_confusion_available'])
    self.assertFalse(row['private_saved_existence_reverified'])
    self.assertFalse(row['new_bins_or_boundary_statistics_generated'])

  def test_approval_a_f_nontransitive_and_ungranted(self):
    row = doc('approval-matrix')
    self.assertFalse(row['any_approval_implies_another'])
    self.assertEqual([r['approval_id'] for r in row['approvals']], list('ABCDEF'))
    self.assertEqual([r['granted_for_current_increment'] for r in row['approvals']], [True, False, False, False, False, False])
    for approval in row['approvals']:
      for key in ('prerequisites', 'expected_artifact', 'privacy_condition', 'stop_condition'):
        self.assertTrue(approval[key])
    self.assertEqual(row['approvals'][5]['separate_subauthorities'], ['INDEPENDENT_HOLDOUT_ADMISSION', 'VEHICLE_ACTIVATION'])

  def test_future_blueprint_all_22_domains_non_omittable(self):
    row = doc('future-validation')
    self.assertEqual([d['order'] for d in row['domains']], list(range(1, 23)))
    for domain in row['domains']:
      self.assertTrue(domain['required_in_any_separately_approved_experiment'])
      for key in ('existing_frozen_gate', 'descriptive_diagnostic', 'missing_evidence', 'required_future_approval',
                  'fail_closed_condition', 'evidence_refs', 'source_refs'):
        self.assertTrue(domain[key])
    self.assertFalse(row['execution_authorized'])
    self.assertFalse(row['new_acceptance_cutoffs'])

  def test_support_limits_and_stage2_recursive_uncertainty(self):
    row = doc('future-validation')['interpretation_limits']
    self.assertEqual(row['moved_gate_perfect_full_support_jobs'], {'25': 32, '50': 5, '100': 0, '200': 0})
    self.assertFalse(row['stage2_unique_cause_identified'])
    self.assertFalse(row['context_divergence_independent_causal_share_identified'])
    self.assertTrue(row['full_projected_numeric_history_not_only_context_bit'])
    self.assertTrue(row['undefined_ratios_remain_null'])

  def test_all_12_completeness_answers_and_performance_limits(self):
    row = doc('review-decision')
    self.assertEqual([r['id'] for r in row['completeness_answers']], [f'Q{i:02}' for i in range(1, 13)])
    self.assertEqual(row['requirements_completeness'], 'PASS_DOCUMENTATION_NOT_POLICY_PERFORMANCE')
    for answer in row['completeness_answers']:
      self.assertTrue(answer['answer'])
      self.assertTrue(answer['evidence_refs'])
    self.assertFalse(row['policy_effect_identified'])

  def test_options_not_adopted_and_gaps_explicit(self):
    rows = doc('review-decision')['options']
    self.assertEqual([r['id'] for r in rows], list('ABCDE'))
    for row in rows:
      self.assertFalse(row['policy_adopted'])
      self.assertTrue(row['contradicting_evidence'])
      self.assertTrue(row['required_authorization'])
      self.assertTrue(row['known_limitations'])

  def test_next_action_concrete_draft_not_access_ready(self):
    row = doc('review-decision')['next_action']
    self.assertEqual(row['id'], 'STAGE1_DECISION_EVIDENCE_ACCESS_AUTHORIZATION_REVIEW')
    self.assertFalse(row['started'])
    self.assertFalse(row['authorized'])
    self.assertEqual(row['package_state'], 'REVIEWABLE_DRAFT_NOT_ACCESS_READY')
    self.assertEqual(row['canonical_private_roots'], 'UNRESOLVED_NO_DISCOVERY_AUTHORIZED')
    for key in ('purpose', 'minimum_input', 'allowed_execution', 'forbidden_execution', 'expected_artifact',
                'approval_required', 'exit_condition', 'safety_boundary', 'counterevidence'):
      self.assertTrue(row[key])

  def test_zero_actual_counters_and_synthetic_separation(self):
    for label in LABELS:
      row = doc(label)
      self.assertEqual(row['operation_counters'], dict.fromkeys(COUNTERS, 0))
      self.assertIn('SYNTHETIC', row['operation_counter_scope'])
    self.assertTrue(doc('review-validation')['counter_verification_method'])

  def test_public_privacy_and_negative_payload_examples(self):
    for label in LABELS:
      privacy(doc(label))
    fake_drive_path = 'E:' + '/secret/data.npz'
    fake_home_path = '/' + 'home/' + 'private/data'
    for payload in ({'threshold': 0.1}, {'coefficients': [1]}, {'row_scores': [0.2]}, {'raw_ticks': [1]}, fake_drive_path, fake_home_path):
      with self.subTest(payload=payload), self.assertRaises(ValueError):
        privacy(payload)

  def test_receipt_corruption_and_authority_negative(self):
    row = doc('requirements-policy')
    with self.assertRaisesRegex(ValueError, 'RECEIPT_CONFLICT'):
      verify({**row, 'baseline_head': 'tampered'})
    body = {k: v for k, v in {**row, 'vehicle_activation_allowed': True}.items() if k != 'receipt_sha256'}
    with self.assertRaisesRegex(ValueError, 'AUTHORITY_CONFLICT'):
      verify({**body, 'receipt_sha256': hashlib.sha256(canonical(body)).hexdigest()})

  def test_preserved_result_authority_and_semantics(self):
    previous = json.loads((ROOT / doc('requirements-policy')['input_lock']['files']['FEASIBILITY_FEASIBILITY_POLICY']['path']).read_bytes())
    for label in LABELS:
      row = doc(label)
      for key in ('preserved_result', 'authority', 'semantics'):
        self.assertEqual(row[key], previous[key])
      self.assertIsNone(row['preserved_result']['selected_candidate'])

  def test_only_documentation_and_one_schema_test_allowed(self):
    row = doc('requirements-policy')
    self.assertEqual(len(row['allowed_tracked_files']), 12)
    test = 'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_decision_policy_requirements.py'
    self.assertTrue(all(p.startswith('docs/cyberpilot/changes/' + PREFIX) or p == test for p in row['allowed_tracked_files']))
    self.assertTrue(row['runtime_model_policy_workflow_change_forbidden'])

  def test_korean_report_sections_links_and_stop(self):
    text = (PUBLIC / (PREFIX + 'requirements-review.md')).read_text()
    self.assertEqual(len(re.findall(r'^## \d+\.', text, re.MULTILINE)), 18)
    self.assertIn('CyberPilot V4는 모델 학습에는 문제가 없었지만', text)
    self.assertIn('```mermaid', text)
    self.assertIn('  T --> Q', text)
    self.assertNotIn('  T --> P', text)
    self.assertIn(BASE, text)
    self.assertIn('NO_FUTURE_EXECUTION_AUTHORIZED', text)
    privacy(text)

  def test_no_scientific_test_import_or_private_dependency(self):
    tree = ast.parse(Path(__file__).read_text())
    allowed = {'ast', 'hashlib', 'json', 'pathlib', 're', 'subprocess', 'unittest'}
    for node in ast.walk(tree):
      if isinstance(node, ast.Import):
        self.assertTrue(all(n.name in allowed for n in node.names))
      elif isinstance(node, ast.ImportFrom):
        self.assertIn(node.module, allowed)

  def test_final_status_and_feasibility_not_model_approval(self):
    row = doc('review-decision')
    self.assertEqual(row['status'], 'HURDLE_STAGE1_V4_STAGE1_DECISION_POLICY_REQUIREMENTS_REVIEW_COMPLETE')
    self.assertEqual(len(row['preserved_feasibility_states']), 5)
    self.assertIn('NO_POLICY_IMPLEMENTATION', row['final_states'])
    self.assertIn('NO_FUTURE_EXECUTION_AUTHORIZED', row['final_states'])


if __name__ == '__main__':
  unittest.main()
