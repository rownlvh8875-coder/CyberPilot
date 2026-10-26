"""Public contract/schema and synthetic truth checks; no scientific execution."""

import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[4]
PUBLIC = ROOT / 'docs/cyberpilot/changes'
BASE = '471537fc0d95d86e7b9f553af5a067a72951abdc'
PREFIX = 'empirical-hurdle-stage1-v4-transition-'
LABELS = (
  'contract-policy',
  'truth-contract',
  'feature-contract',
  'decision-contract',
  'gate-realization-contract',
  'failure-matrix',
  'identifiability',
  'future-validation',
  'review-decision',
  'review-validation',
)
COUNTERS = (
  'model_refit_calls',
  'normalizer_refit_calls',
  'stage2_refit_calls',
  'threshold_reselection_calls',
  'prediction_replay_calls',
  'rollout_regeneration_calls',
  'selection_calls',
  'candidate_search_calls',
  'raw_log_openings',
  'qlog_openings',
  'holdout_openings',
  'holdout_discovery',
  'private_array_openings',
  'source_write_count',
  'vehicle_activation_calls',
)
FIREWALL = (
  'qualification_allowed',
  'reference_promotable',
  'sealed_reference_allowed',
  'vehicle_activation_allowed',
  'production_authority',
  'ta_execution',
  'sg_execution',
  'composition_authorized',
  'candidate_search_authorized',
  'publication_raw_data',
)
PRIVATE_KEYS = {
  'threshold',
  'threshold_value',
  'coefficients',
  'normalizer_values',
  'probabilities',
  'raw_scores',
  'raw_ticks',
  'projected_path',
  'gate_sequence',
  'witness_row_indices',
  'gps',
  'commands',
  'timestamps',
  'private_root',
  'per_row_probabilities',
  'score_vector',
  'p_move',
  'predicted_gate',
  'predicted_gate_path',
  'observed_path',
  'raw_path',
  'gate_path',
}
PRIVATE_PATH = re.compile(r'(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|/(?:mnt|home|Users|tmp)/|\\\\)')


def canonical(value):
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def verify_row(row):
  body = {k: v for k, v in row.items() if k != 'receipt_sha256'}
  if row.get('receipt_sha256') != hashlib.sha256(canonical(body)).hexdigest():
    raise ValueError('RECEIPT_CONFLICT')
  if any(row.get(k) is not False for k in FIREWALL):
    raise ValueError('AUTHORITY_CONFLICT')
  return row


def verified(path):
  return verify_row(json.loads(path.read_bytes()))


def document(label):
  return verified(PUBLIC / (PREFIX + label + '.json'))


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


def causal_fields(fields):
  for field in fields:
    if field['role'] != 'INFERENCE_INPUT' or field['latest_source_offset_max'] > 0:
      raise ValueError('FUTURE_LABEL_LEAKAGE')


def resolve(value, tokens):
  if not tokens:
    return
  token, *rest = tokens
  if token == '*':
    for child in value.values() if isinstance(value, dict) else value:
      resolve(child, rest)
  else:
    resolve(value[int(token)] if isinstance(value, list) else value[token.replace('~1', '/').replace('~0', '~')], rest)


class TestV4TransitionContractReview(unittest.TestCase):
  def test_requested_contract_documents_exist(self):
    for label in LABELS:
      path = PUBLIC / (PREFIX + label + '.json')
      self.assertTrue(path.is_file(), f'MISSING_CONTRACT_DOCUMENT:{label}')
      self.assertEqual(document(label)['component'], label)

  def test_receipts_baseline_policy_and_authority_binding(self):
    policy = document('contract-policy')
    self.assertEqual(policy['baseline_head'], BASE)
    for label in LABELS:
      row = document(label)
      self.assertEqual(row['baseline_head'], BASE)
      if label != 'contract-policy':
        self.assertEqual(row['contract_policy_receipt_sha256'], policy['receipt_sha256'])
      self.assertFalse(row['next_execution_authorized'])
      self.assertIsNone(row['preserved_result']['selected_candidate'])
      self.assertEqual(row['preserved_result']['selection_state'], 'MODEL_SELECTION_FAILED_CLOSED')
      self.assertEqual(row['authority']['holdout'], 'CLOSED')
      self.assertEqual(row['authority']['opening_count'], 0)
      self.assertEqual(row['authority']['holdout_discovery'], 0)
      self.assertEqual(row['authority']['vehicle_authority'], 'NONE')

  def test_all_actual_scientific_operation_counters_zero(self):
    for label in LABELS:
      row = document(label)
      self.assertEqual(set(row['operation_counters']), set(COUNTERS))
      self.assertTrue(all(type(v) is int and v == 0 for v in row['operation_counters'].values()))

  def test_public_input_hashes_git_bytes_and_existing_seals(self):
    lock = document('contract-policy')['input_lock']
    self.assertEqual(len(lock['files']), 34)
    self.assertEqual(len(lock['sources']), 15)
    for entry in [*lock['files'].values(), *lock['sources'].values()]:
      raw = (ROOT / entry['path']).read_bytes()
      self.assertEqual(hashlib.sha256(raw).hexdigest(), entry.get('file_sha256', entry.get('sha256')))
      self.assertEqual(raw, subprocess.check_output(['git', 'show', BASE + ':' + entry['path']], cwd=ROOT))
      if entry.get('receipt_sha256'):
        self.assertEqual(verified(ROOT / entry['path'])['receipt_sha256'], entry['receipt_sha256'])

  def test_source_and_evidence_references_resolve(self):
    lock = document('contract-policy')['input_lock']
    for label in LABELS:
      row = document(label)
      for ref in row['evidence_refs']:
        entry = lock['files'][ref['file']]
        self.assertEqual(ref['git_sha'], BASE)
        self.assertEqual(ref['file_sha256'], entry['file_sha256'])
        resolve(json.loads((ROOT / entry['path']).read_bytes()), ref['pointer'].strip('/').split('/'))
      for ref in row['source_refs']:
        entry = lock['sources'][ref['file']]
        self.assertEqual(ref['git_sha'], BASE)
        self.assertEqual(ref['source_sha256'], entry['sha256'])
        source_tree = ast.parse((ROOT / entry['path']).read_text())
        nodes = {n.name: n for n in source_tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        if ref['symbol'] != '<module>':
          self.assertEqual(nodes[ref['symbol']].lineno, ref['line'])
        else:
          self.assertIn(ref['line'], {n.lineno for n in source_tree.body})

  def test_four_truth_populations_disjoint_and_complete(self):
    rows = document('truth-contract')['states']
    wanted = {(0, 0): 'STATIC_HOLD', (0, 1): 'MOVE_ONSET', (1, 0): 'MOVE_TERMINATION', (1, 1): 'MOVE_CONTINUATION'}
    self.assertEqual({(r['z_prev'], r['y_true']): r['id'] for r in rows}, wanted)
    for previous in (-2, -1, 0, 1, 2):
      for following in (-2, -1, 0, 1, 2):
        matched = [r['id'] for r in rows if r['z_prev'] == int(previous != 0) and r['y_true'] == int(following != 0)]
        self.assertEqual(matched, [wanted[(int(previous != 0), int(following != 0))]])

  def test_truth_population_mapping_and_adjacent_increment_scope(self):
    rows = document('truth-contract')['states']
    self.assertEqual(
      [r['existing_population'] for r in rows],
      [
        'PREV_STATIC_TRUE_STATIC',
        'PREV_STATIC_MOVE_ONSET',
        'PREV_MOVE_TRUE_STATIC',
        'PREV_MOVE_MOVE_CONTINUATION',
      ],
    )
    semantics = document('truth-contract')['label_limits']
    self.assertTrue(semantics['continuation_includes_sign_reversal'])
    self.assertFalse(semantics['termination_implies_sustained_stop'])
    self.assertFalse(semantics['physical_eps_state_claim'])

  def test_future_truth_excluded_from_causal_input_contract(self):
    fields = document('feature-contract')['inference_fields']
    causal_fields(fields)
    self.assertEqual({r['id'] for r in fields}, {'intercept', 'delayed_command_history', 'prior_delta_history', 'current_tick', 'speed'})
    for bad in ({'role': 'LABEL_ONLY', 'latest_source_offset_max': 1}, {'role': 'INFERENCE_INPUT', 'latest_source_offset_max': 1}):
      with self.assertRaisesRegex(ValueError, 'FUTURE_LABEL_LEAKAGE'):
        causal_fields([bad])
    self.assertFalse(document('truth-contract')['future_truth_is_inference_input'])

  def test_recursive_truth_label_does_not_select_head(self):
    routing = document('truth-contract')['routing']
    self.assertEqual(routing['head_by_bit'], {'0': 'STATIC_CONTEXT_HEAD', '1': 'MOVE_CONTEXT_HEAD'})
    self.assertEqual(routing['recursive_source'], 'LATEST_PROJECTED_DELTA_AFTER_OBSERVED_INITIALIZATION')
    self.assertFalse(routing['recursive_routing_guaranteed_equal_to_observed_truth'])
    for observed, projected, future, wanted_truth, wanted_head in (
      (1, 0, 0, 'MOVE_TERMINATION', 'STATIC_CONTEXT_HEAD'),
      (0, 1, 1, 'MOVE_ONSET', 'MOVE_CONTEXT_HEAD'),
    ):
      row = next(r for r in document('truth-contract')['states'] if (r['z_prev'], r['y_true']) == (int(observed != 0), future))
      self.assertEqual(row['id'], wanted_truth)
      self.assertEqual(routing['head_by_bit'][str(int(projected != 0))], wanted_head)

  def test_missing_history_and_segment_horizon_boundaries(self):
    boundary = document('truth-contract')['boundary_contract']
    self.assertEqual(boundary['required_history'], 'max(d+L,L+1)')
    self.assertFalse(boundary['padding_allowed'])
    self.assertFalse(boundary['default_static_context_allowed'])
    self.assertFalse(boundary['cross_segment_history_allowed'])
    self.assertEqual(boundary['horizon_continuity'], 'streak[k+H] == streak[k] + H')
    self.assertEqual(boundary['reset'], 'FRESH_OBSERVED_INITIAL_HISTORY_PER_PATH_AND_HORIZON')

  def test_feature_normalization_basis_and_existing_negative_labels(self):
    row = document('feature-contract')
    self.assertEqual(row['dimension'], 'P=2L+3')
    self.assertEqual(row['processing_order'], ['RAW_HEAD_ROUTING', 'FROZEN_V1_STAGE1_NORMALIZATION', 'HEAD_BASIS_SELECTION', 'LINEAR_SCORE_SIGMOID'])
    self.assertEqual(row['basis']['STATIC']['removed_raw_column'], 'P-3')
    self.assertEqual(row['basis']['MOVE']['retained'], 'ALL_V1_EFFECTIVE_COLUMNS')
    self.assertTrue(row['existing_information']['history_already_present'])
    self.assertTrue(row['existing_information']['termination_negative_labels_already_present'])
    self.assertFalse(row['feature_absence_or_logistic_impossibility_proven'])

  def test_per_job_global_decision_and_calibration_responsibilities(self):
    row = document('decision-contract')
    frozen = row['frozen_decision']
    self.assertEqual(frozen['scope'], 'ONE_PER_CANDIDATE_FOLD_JOB_SHARED_ACROSS_TWO_HEADS')
    self.assertFalse(frozen['one_value_pooled_across_32_jobs'])
    self.assertEqual(frozen['comparison'], 'MOVE_IFF_p_move_GT_t_job_EQUALITY_STATIC')
    self.assertEqual(frozen['objective_order'], ['BA_NUM', 'TN', 'LARGER_TRAIN_DECISION'])
    self.assertFalse(row['score_semantics']['calibration_guaranteed'])
    self.assertEqual({r['id'] for r in row['responsibilities']}, {'REPRESENTATION', 'RANKING', 'CALIBRATION', 'DECISION', 'REALIZATION'})
    self.assertEqual(row['alternative_decisions_evaluated'], [])
    self.assertEqual(
      row['fold_data_identity_policy'],
      {
        'same_anchor_values_across_folds_required': False,
        'each_fold_frozen_anchor_identity_preserved': True,
        'common_label_and_anchor_semantics': True,
      },
    )

  def test_transition_responsibility_rows_are_context_scoped(self):
    rows = document('decision-contract')['transition_responsibility']
    self.assertEqual([r['state'] for r in rows], ['STATIC_HOLD', 'MOVE_ONSET', 'MOVE_TERMINATION', 'MOVE_CONTINUATION'])
    self.assertEqual([r['one_step_head'] for r in rows], ['STATIC_CONTEXT_HEAD', 'STATIC_CONTEXT_HEAD', 'MOVE_CONTEXT_HEAD', 'MOVE_CONTEXT_HEAD'])
    self.assertTrue(all(r['recursive_head_rule'] == 'SELECT_BY_Z_ROUTE_NOT_OBSERVED_TRUTH_LABEL' for r in rows))
    self.assertEqual([r['desired_gate'] for r in rows], ['STATIC', 'MOVE', 'STATIC', 'MOVE'])

  def test_gate_static_hold_and_move_hold_are_distinct(self):
    row = document('gate-realization-contract')
    self.assertEqual(row['allowed_successful_pairs'], [['STATIC', 'HOLD'], ['MOVE', 'HOLD'], ['MOVE', 'MOVE']])
    self.assertEqual(row['forbidden_successful_pairs'], [['STATIC', 'MOVE']])
    self.assertEqual(row['movement_reference'], 'SUPPLIED_CURRENT_TICK_OBSERVED_ONE_STEP_PROJECTED_RECURSIVE')
    self.assertFalse(row['gate_move_forces_nonzero_movement'])
    self.assertFalse(row['new_deadband_introduced'])

  def test_gate_correctness_is_not_tick_correctness(self):
    cases = ((1, 1, 5, 6, False), (1, 0, 5, 5, True), (0, 0, 4, 5, False), (0, 1, 5, 5, True))
    # Synthetic fixtures: true-next bit, gate bit, projected tick, truth tick, exact hit.
    for truth_bit, gate_bit, projected, target, exact in cases:
      self.assertEqual(projected == target, exact)
      if (truth_bit, gate_bit) == (1, 1):
        self.assertFalse(exact)  # TP can have magnitude error.
      if (truth_bit, gate_bit) == (1, 0):
        self.assertTrue(exact)  # Recursive base drift can coincide with target despite FN.
    self.assertFalse(document('gate-realization-contract')['gate_correct_implies_exact_tick'])
    self.assertFalse(document('gate-realization-contract')['recursive_static_gate_implies_correct_observed_tick'])

  def test_projection_failure_and_realization_policy_unchanged(self):
    row = document('gate-realization-contract')['projection']
    self.assertEqual(row['rounding'], 'NP_RINT_TIES_TO_EVEN')
    self.assertEqual(row['range_check_order'], 'AFTER_ROUNDING')
    self.assertEqual(row['range_policy'], 'RAISE_OUTSIDE_SIGNED16_NO_CLIPPING')
    self.assertEqual(row['invalid_output_policy'], 'RAISE_REJECT_NO_FALLBACK')
    self.assertFalse(row['serialized_job_failure_guaranteed'])

  def test_recursive_full_numeric_state_and_exogenous_availability(self):
    row = document('gate-realization-contract')['recursive_state']
    self.assertEqual(row['owner'], 'LOCAL_PATH_STATE_IN_RECURSIVE')
    self.assertEqual(row['latest_delta_update'], 'projected_next_tick - supplied_current_tick')
    self.assertFalse(row['binary_context_match_implies_full_state_match'])
    self.assertFalse(row['future_observed_ticks_used_for_prediction'])
    self.assertFalse(row['initial_anchor_real_time_exogenous_availability_proven'])
    self.assertEqual(row['terminal_causal_effect'], 'NOT_IDENTIFIABLE_FROM_FROZEN_EVIDENCE')

  def test_frozen_exact_hit_fp_folds_and_ranking_evidence(self):
    policy = document('contract-policy')
    ledger = verified(ROOT / policy['input_lock']['files']['MIXED_EVIDENCE_LEDGER']['path'])
    facts = ledger['facts']
    e = facts['E1']['values']
    self.assertEqual((e['static_hit_loss'], e['move_hit_gain'], e['net_hit_delta']), (571317, 228164, -343153))
    self.assertEqual(e['candidate_exact_hit_count'], e['hold_exact_hit_count'] - e['static_hit_loss'] + e['move_hit_gain'])
    fp = facts['E2']['values']
    self.assertEqual(fp['gate_fp'], fp['gate_fp_projected_hold'] + fp['harmful_false_movement'])
    self.assertEqual((fp['gate_fp'], fp['gate_fp_projected_hold'], fp['harmful_false_movement']), (1662235, 1090918, 571317))
    self.assertEqual(facts['E3']['values']['FOLD_B']['onset_tp'], 7707)
    self.assertEqual(facts['E5']['values']['PREV_STATIC']['comparison'], [13, 0, 19])
    self.assertEqual(facts['E5']['comparison_reference'], 'V4_DEV_VS_HISTORICAL_FIXED_V1_DEV_ON_EXACT_MATCHING_ANCHORS')
    self.assertEqual(facts['E7']['values']['200']['FULL_DESCRIPTIVE_SUPPORT'], 0)
    self.assertEqual(policy['aggregation_scope'], 'OVERLAPPING_JOB_ANCHORS_NOT_INDEPENDENT_SAMPLES')

  def test_failure_modes_have_formal_conditions_limits_and_invariants(self):
    row = document('failure-matrix')
    self.assertEqual([r['id'] for r in row['failure_modes']], [f'F{i}' for i in range(1, 9)])
    required = {
      'formal_condition',
      'actual_evidence',
      'populations',
      'stage_responsibility',
      'downstream_effect',
      'known_limits',
      'invariants',
      'future_validation',
      'safety_implication',
    }
    for failure in row['failure_modes']:
      self.assertTrue(required <= failure.keys())
      self.assertTrue(all(failure[k] for k in required))
      self.assertTrue(set(failure['invariants']) <= {r['id'] for r in row['invariants']})
    self.assertEqual(row['failure_modes'][3]['classification'], 'PERMITTED_INTERFACE_CASE_NOT_INHERENTLY_A_BUG')
    self.assertEqual(row['failure_modes'][7]['actual_occurrence'], 'NOT_ESTABLISHED_FROM_PUBLIC_EVIDENCE')

  def test_identifiability_does_not_assign_unique_causes_or_new_gains(self):
    rows = document('identifiability')['questions']
    self.assertEqual([r['id'] for r in rows], list(range(1, 10)))
    self.assertEqual(rows[0]['status'], 'DIRECTLY_SUPPORTED')
    self.assertEqual(rows[4]['status'], 'DIRECTLY_SUPPORTED')
    self.assertTrue(all(rows[i]['status'] == 'NOT_IDENTIFIABLE' for i in (1, 2, 3, 5, 6, 7, 8)))
    self.assertIsNone(document('identifiability')['causal_shares'])
    self.assertIsNone(document('identifiability')['predicted_improvement'])

  def test_twenty_future_requirements_preserve_frozen_gate(self):
    row = document('future-validation')
    self.assertEqual([r['id'] for r in row['requirements']], [f'V{i}' for i in range(1, 21)])
    self.assertEqual(row['new_acceptance_cutoffs'], [])
    policy = document('contract-policy')
    gate = verified(ROOT / policy['input_lock']['files']['UPSTREAM_POL_GATE']['path'])
    self.assertEqual(len(gate['clauses']), 32)
    self.assertEqual(row['frozen_gate']['clauses_sha256'], hashlib.sha256(canonical(gate['clauses'])).hexdigest())
    self.assertEqual(
      next(r for r in row['requirements'] if r['id'] == 'V13')['gate_link_scope'],
      'ONE_STEP_TRUE_MOVE_CONTINUOUS_ERROR_INCLUDING_FN_DISTINCT_FROM_PROJECTED_GATE_TP_DIAGNOSTIC',
    )
    for requirement in row['requirements']:
      self.assertTrue({'existing_frozen_gate', 'existing_descriptive_metric', 'missing_evidence', 'approval_requirement'} <= requirement.keys())
      self.assertFalse(requirement['execution_authorized'])

  def test_alternatives_and_one_unstarted_recommendation(self):
    row = document('review-decision')
    self.assertEqual([r['id'] for r in row['alternatives']], list('ABC'))
    for alternative in row['alternatives']:
      self.assertIn(alternative['status'], ('CONTRACT_REVIEW_SUPPORTED', 'EVIDENCE_INSUFFICIENT', 'DEFERRED', 'REQUIRES_FUTURE_POLICY_APPROVAL'))
      self.assertFalse(alternative['adopted_as_model_or_policy'])
    recommendation = row['recommendation']
    self.assertIn(
      recommendation['topic'],
      (
        'STAGE1_TRANSITION_REPRESENTATION_SPEC_REVIEW',
        'STAGE1_DECISION_TRANSFER_FEASIBILITY_REVIEW',
        'STAGE1_GATE_REALIZATION_INTERFACE_REVIEW',
        'STAGE1_TRANSITION_IDENTIFIABILITY_REVIEW',
        'STAGE1_MIXED_CONTRACT_REQUIREMENTS_REVIEW',
      ),
    )
    for field in ('supporting_evidence', 'contradicting_evidence', 'required_missing_evidence', 'why_first', 'future_policy_approval', 'safety_risks'):
      self.assertTrue(recommendation[field])
    self.assertFalse(recommendation['started'])
    self.assertFalse(recommendation['execution_authorized'])
    self.assertEqual(row['models_selected'], [])
    self.assertEqual(row['decision_policies_selected'], [])

  def test_public_privacy_and_synthetic_negative_payloads(self):
    for label in LABELS:
      privacy(document(label))
    for key in PRIVATE_KEYS:
      with self.subTest(key=key), self.assertRaises(ValueError):
        privacy({key: [1]})
    for value in ('E:/synthetic-private', '/mnt/e/synthetic', '/home/synthetic', r'\\synthetic\share'):
      with self.subTest(value=value), self.assertRaises(ValueError):
        privacy({'synthetic': value})

  def test_public_links_accepted_and_tampered_receipt_rejected(self):
    privacy({'source': 'https://github.com/rownlvh8875-coder/CyberPilot/blob/' + BASE + '/openpilot/tools/cyber_autotune/empirical_hurdle_v4_execution.py#L20'})
    row = document('contract-policy')
    changed = dict(row)
    changed['next_execution_authorized'] = True
    with self.assertRaisesRegex(ValueError, 'RECEIPT_CONFLICT'):
      verify_row(changed)
    authority_changed = dict(row, vehicle_activation_allowed=True)
    authority_changed['receipt_sha256'] = hashlib.sha256(canonical({k: v for k, v in authority_changed.items() if k != 'receipt_sha256'})).hexdigest()
    with self.assertRaisesRegex(ValueError, 'AUTHORITY_CONFLICT'):
      verify_row(authority_changed)

  def test_new_test_imports_only_stdlib_and_no_scientific_functions(self):
    for node in ast.walk(ast.parse(Path(__file__).read_text())):
      if isinstance(node, ast.Import):
        self.assertTrue(all(n.name.split('.')[0] in ('ast', 'hashlib', 'json', 're', 'subprocess', 'unittest') for n in node.names))
      elif isinstance(node, ast.ImportFrom):
        self.assertEqual(node.module, 'pathlib')

  def test_korean_report_source_links_and_no_private_payload(self):
    report = (PUBLIC / (PREFIX + 'decision-contract-review.md')).read_text()
    self.assertTrue(report.startswith('CyberPilot V4는 움직여야 하는 상황과'))
    self.assertIn('```mermaid', report)
    self.assertIn('/blob/' + BASE + '/', report)
    for state in ('STATIC_HOLD', 'MOVE_ONSET', 'MOVE_TERMINATION', 'MOVE_CONTINUATION'):
      self.assertIn(state, report)
    privacy(report)

  def test_scope_allows_only_twelve_new_files_and_no_workflow_change(self):
    row = document('contract-policy')
    self.assertEqual(len(row['allowed_tracked_files']), 12)
    self.assertTrue(all(p.startswith(('docs/cyberpilot/changes/', 'openpilot/tools/cyber_autotune/tests/')) for p in row['allowed_tracked_files']))
    self.assertTrue(row['existing_workflow_change_forbidden'])
    self.assertFalse(row['new_scientific_metrics_allowed'])

  def test_validation_does_not_claim_future_ci_or_private_execution(self):
    row = document('review-validation')
    self.assertIn(row['local_validation_status'], ('PENDING', 'PASS'))
    self.assertEqual(row['regression_scope'], 'EXISTING_SYNTHETIC_FIXTURES_ONLY')
    self.assertEqual(row['private_evidence_execution'], 'NONE')
    self.assertEqual(row['exact_head_ci']['resolution'], 'GITHUB_ACTIONS_ON_CONTAINING_GIT_COMMIT')
    self.assertTrue(row['exact_head_ci']['not_claimed_before_execution'])


if __name__ == '__main__':
  unittest.main()
