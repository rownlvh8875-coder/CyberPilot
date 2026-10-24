"""Public schema, receipt and symbolic contracts only; no scientific execution."""

import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[4]
PUBLIC = ROOT / 'docs/cyberpilot/changes'
BASE = '3d2e77897f385565fe504937d77766dd73c4c6a9'
PREFIX = 'empirical-hurdle-stage1-v4-decision-transfer-'
LABELS = (
  'feasibility-policy',
  'evidence-inventory',
  'observability-matrix',
  'train-dev-matrix',
  'transition-matrix',
  'fold-risk',
  'identifiability',
  'next-evidence-gate',
  'validation',
)
COUNTERS = (
  'model_refit_calls',
  'normalizer_refit_calls',
  'stage2_refit_calls',
  'calibration_fit_calls',
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
  'p_move',
  'score_vector',
  'raw_scores',
  'raw_ticks',
  'projected_path',
  'predicted_gate',
  'predicted_gate_path',
  'gate_sequence',
  'observed_path',
  'commands',
  'gps',
  'timestamps',
  'private_root',
  'witness_row_indices',
  'calibration_parameters',
  'row_scores',
  'row_gates',
}
PRIVATE_PATH = re.compile(r'(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|/(?:mnt|home|Users|tmp)/|\\\\)')


def canonical(value):
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def verify(row):
  if row.get('receipt_sha256') != hashlib.sha256(canonical({k: v for k, v in row.items() if k != 'receipt_sha256'})).hexdigest():
    raise ValueError('RECEIPT_CONFLICT')
  if any(row.get(key) is not False for key in FIREWALL):
    raise ValueError('AUTHORITY_CONFLICT')
  return row


def document(label):
  return verify(json.loads((PUBLIC / (PREFIX + label + '.json')).read_bytes()))


def input_row(key):
  return verify(json.loads((ROOT / document('feasibility-policy')['input_lock']['files'][key]['path']).read_bytes()))


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


def resolve(value, tokens):
  if tokens:
    token, *rest = tokens
    if token == '*':
      for child in value.values() if isinstance(value, dict) else value:
        resolve(child, rest)
    else:
      resolve(value[int(token)] if isinstance(value, list) else value[token.replace('~1', '/').replace('~0', '~')], rest)


def references(value):
  if isinstance(value, dict):
    if {'file', 'git_sha'} <= value.keys():
      yield value
    for child in value.values():
      yield from references(child)
  elif isinstance(value, list):
    for child in value:
      yield from references(child)


class TestDecisionTransferFeasibility(unittest.TestCase):
  def test_requested_documents_exist(self):
    for label in LABELS:
      self.assertEqual(document(label)['component'], label)

  def test_baseline_seals_and_common_policy_binding(self):
    policy = document('feasibility-policy')
    for label in LABELS:
      row = document(label)
      self.assertEqual(row['baseline_head'], BASE)
      self.assertEqual(row['scope'], ['FEASIBILITY_REVIEW_ONLY', 'REPORT_ONLY', 'READ_ONLY_SCIENTIFIC_EVIDENCE', 'NO_NEW_MODEL_EXECUTION'])
      if label != 'feasibility-policy':
        self.assertEqual(row['feasibility_policy_receipt_sha256'], policy['receipt_sha256'])
      self.assertTrue(row['public_evidence_only'])
      self.assertFalse(row['next_execution_authorized'])

  def test_public_input_receipts_git_bytes_and_source_pins(self):
    lock = document('feasibility-policy')['input_lock']
    self.assertEqual(len(lock['files']), 45)
    self.assertEqual(len(lock['sources']), 17)
    self.assertEqual(lock['previous_lock_counts'], {'public_files': 34, 'sealed_json': 32, 'static_sources': 15})
    seals = 0
    for entry in [*lock['files'].values(), *lock['sources'].values(), lock['workflow_pin']]:
      raw = (ROOT / entry['path']).read_bytes()
      self.assertEqual(hashlib.sha256(raw).hexdigest(), entry.get('file_sha256', entry.get('sha256')))
      self.assertEqual(raw, subprocess.check_output(['git', 'show', BASE + ':' + entry['path']], cwd=ROOT))
      if entry.get('receipt_sha256'):
        self.assertEqual(verify(json.loads(raw))['receipt_sha256'], entry['receipt_sha256'])
        seals += 1
    self.assertEqual(seals, 42)

  def test_all_evidence_and_static_source_references_resolve(self):
    lock = document('feasibility-policy')['input_lock']
    for label in LABELS:
      for ref in references(document(label)):
        self.assertEqual(ref['git_sha'], BASE)
        if 'pointer' in ref:
          entry = lock['files'][ref['file']]
          self.assertEqual(ref['file_sha256'], entry['file_sha256'])
          resolve(json.loads((ROOT / entry['path']).read_bytes()), ref['pointer'].strip('/').split('/'))
        elif 'symbol' in ref:
          entry = lock['sources'][ref['file']]
          self.assertEqual(ref['source_sha256'], entry['sha256'])
          body = ast.parse((ROOT / entry['path']).read_text()).body
          if ref['symbol'] == '<module>':
            self.assertIn(ref['line'], {n.lineno for n in body})
          else:
            nodes = {n.name: n for n in body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
            self.assertEqual(ref['line'], nodes[ref['symbol']].lineno)

  def test_original_scientific_sources_unchanged(self):
    row = document('feasibility-policy')
    for name in row['input_lock']['original_execution_scientific_files']:
      relative = row['input_lock']['sources'][name]['path']
      self.assertEqual((ROOT / relative).read_bytes(), subprocess.check_output(['git', 'show', row['execution_head'] + ':' + relative], cwd=ROOT))

  def test_sixteen_actual_operation_counters_are_zero(self):
    self.assertEqual(len(COUNTERS), 16)
    for label in LABELS:
      counters = document(label)['operation_counters']
      self.assertEqual(set(counters), set(COUNTERS))
      self.assertTrue(all(type(v) is int and v == 0 for v in counters.values()))

  def test_four_truth_populations_preserved(self):
    rows = document('transition-matrix')['states']
    wanted = {(0, 0): 'STATIC_HOLD', (0, 1): 'MOVE_ONSET', (1, 0): 'MOVE_TERMINATION', (1, 1): 'MOVE_CONTINUATION'}
    self.assertEqual({(r['z_truth'], r['y_true']): r['id'] for r in rows}, wanted)
    for previous in (-1, 0, 1):
      for following in (-1, 0, 1):
        self.assertEqual(sum((r['z_truth'], r['y_true']) == (int(previous != 0), int(following != 0)) for r in rows), 1)
    self.assertFalse(document('transition-matrix')['future_truth_is_inference_input'])

  def test_inventory_has_fourteen_explicit_train_dev_items(self):
    rows = document('evidence-inventory')['items']
    self.assertEqual(len(rows), 14)
    states = {'AVAILABLE_PUBLIC_AGGREGATE', 'AVAILABLE_PUBLIC_JOB_LEVEL', 'NOT_PUBLIC', 'NOT_SAVED', 'INPUT_INSUFFICIENT', 'NOT_IDENTIFIABLE'}
    for row in rows:
      self.assertIn(row['train']['public_status'], states)
      self.assertIn(row['development']['public_status'], states)
      self.assertTrue(row['train']['evidence_refs'] or row['train']['source_refs'])
      self.assertTrue(row['development']['evidence_refs'] or row['development']['source_refs'])

  def test_overall_train_confusion_is_available(self):
    row = next(r for r in document('evidence-inventory')['items'] if r['id'] == 'overall_confusion')
    self.assertEqual(row['train']['public_status'], 'AVAILABLE_PUBLIC_JOB_LEVEL')
    source = input_row('UPSTREAM_score-transfer')
    self.assertEqual(len(source['jobs']), 32)
    self.assertTrue(all({'counts', 'recall', 'specificity'} <= j['decision_transfer']['train'].keys() for j in source['jobs']))

  def test_missing_train_row_gates_not_invented(self):
    row = next(r for r in document('evidence-inventory')['items'] if r['id'] == 'rowwise_gate')
    self.assertEqual(row['train']['public_status'], 'INPUT_INSUFFICIENT')
    self.assertEqual(row['train']['saved_status'], 'NOT_SAVED_IN_V4_TRAIN_OUTPUT_CONTRACT')
    self.assertFalse(row['train']['reconstruction_authorized'])
    for job in input_row('UPSTREAM_score-transfer')['jobs']:
      self.assertEqual(job['decision_transfer']['train_rowwise_gate'], 'INPUT_INSUFFICIENT; NOT_SAVED; NO_THRESHOLD_APPLICATION')

  def test_private_saved_scores_are_distinct_from_missing_gates(self):
    rows = {r['id']: r for r in document('evidence-inventory')['items']}
    for split in ('train', 'development'):
      self.assertEqual(rows['rowwise_scores'][split]['public_status'], 'NOT_PUBLIC')
      self.assertEqual(rows['rowwise_scores'][split]['saved_status'], 'SAVED_PRIVATE_BY_SOURCE_CONTRACT_NOT_REOPENED')
    self.assertEqual(rows['rowwise_gate']['development']['public_status'], 'NOT_PUBLIC')
    self.assertFalse(document('evidence-inventory')['private_saved_existence_reverified'])

  def test_context_confusion_not_inferred_from_overall_counts(self):
    row = next(r for r in document('evidence-inventory')['items'] if r['id'] == 'context_confusion')
    self.assertEqual(row['train']['public_status'], 'INPUT_INSUFFICIENT')
    self.assertEqual(row['development']['public_status'], 'AVAILABLE_PUBLIC_JOB_LEVEL')
    self.assertFalse(document('observability-matrix')['overall_counts_identify_context_confusion'])

  def test_reliability_and_boundary_distributions_unavailable(self):
    rows = {r['id']: r for r in document('evidence-inventory')['items']}
    for name in ('reliability_bins', 'boundary_distribution'):
      for split in ('train', 'development'):
        self.assertEqual(rows[name][split]['public_status'], 'INPUT_INSUFFICIENT')
        self.assertFalse(rows[name][split]['new_summary_authorized'])
    self.assertFalse(document('observability-matrix')['job_metric_ranges_are_score_distributions'])

  def test_single_truth_cell_auc_and_undefined_ratios(self):
    rows = document('transition-matrix')['states']
    for row in rows:
      self.assertEqual(row['auc_scope'], 'PREVIOUS_STATE_PAIR_NOT_PURE_TRUTH_CELL')
      self.assertEqual(row['pure_truth_cell_auc'], 'INPUT_INSUFFICIENT_SINGLE_CLASS')
      self.assertEqual(row['train_gate_transfer_status'], 'INPUT_INSUFFICIENT')
      self.assertIn('specificity' if row['y_true'] else 'recall', row['undefined_metrics'])
    self.assertEqual(document('observability-matrix')['undefined_ratio_semantics'], 'NULL_NOT_ZERO')

  def test_nine_source_contract_responsibilities(self):
    rows = document('train-dev-matrix')['responsibilities']
    self.assertEqual(
      {r['id'] for r in rows},
      {
        'REPRESENTATION',
        'HEAD_ROUTING',
        'SCORE_RANKING',
        'CALIBRATION',
        'FROZEN_DECISION',
        'GATE_CLASSIFICATION',
        'STAGE2_MAGNITUDE',
        'TICK_REALIZATION',
        'RECURSIVE_STATE',
      },
    )
    self.assertTrue(all(r['source_refs'] and r['limit'] for r in rows))

  def test_existing_policy_audit_is_per_job_and_strict(self):
    row = document('train-dev-matrix')['policy_audit']
    self.assertEqual(row['decision_scope'], 'ONE_PER_CANDIDATE_FOLD_SHARED_BY_TWO_HEADS')
    self.assertEqual(row['comparison'], 'MOVE_IFF_SCORE_GT_FROZEN_T_EQUALITY_STATIC')
    self.assertEqual(row['objective_order'], ['BA_NUM', 'TN', 'LARGER_TRAIN_DECISION'])
    self.assertEqual(row['dev_application'], 'SAME_IN_MEMORY_FIT_DECISION_AFTER_DURABLE_TRAIN_FINALIZATION')
    self.assertFalse(row['dev_reselection'])
    self.assertFalse(row['binary_ba_objective_equals_tick_exact_hit_objective'])

  def test_existing_job_transfer_fields_copied_without_new_statistics(self):
    original = input_row('UPSTREAM_score-transfer')['jobs']
    copied = document('train-dev-matrix')['job_transfer_rows']
    self.assertEqual(len(copied), 32)
    for current, old in zip(copied, original, strict=True):
      self.assertEqual((current['candidate_id'], current['fold']), (old['candidate_id'], old['fold']))
      self.assertEqual(current['score_shift'], old['score_transfer']['OVERALL']['dev_minus_train']['mean_probability'])
      self.assertEqual(current['bias_shift'], old['score_transfer']['OVERALL']['dev_minus_train']['calibration_bias'])
      self.assertEqual(current['decision_differences'], old['decision_transfer']['dev_minus_train'])
    self.assertFalse(document('train-dev-matrix')['new_performance_metrics_computed'])

  def test_ranking_calibration_decision_remain_separate(self):
    row = document('observability-matrix')
    self.assertFalse(row['auc_improvement_guarantees_decision_improvement'])
    self.assertFalse(row['mean_bias_establishes_conditional_reliability'])
    self.assertFalse(row['brier_identifies_optimal_operating_point'])
    self.assertEqual(row['symbolic_nonidentification']['scope'], 'GENERAL_SYMBOLIC_ARGUMENT_NOT_V4_COUNTERFACTUAL')
    self.assertFalse(row['symbolic_nonidentification']['actual_values_reconstructed'])

  def test_fold_risks_and_population_identity_preserved(self):
    row = document('fold-risk')
    self.assertEqual([r['fold'] for r in row['folds']], ['FOLD_A', 'FOLD_B'])
    self.assertFalse(row['identical_train_dev_rows_assumed'])
    self.assertFalse(row['opposite_shift_proves_unique_cause'])
    self.assertFalse(row['fold_correction_efficacy_established'])
    self.assertTrue(all(r['supporting_evidence'] and r['confounding'] and r['missing_evidence'] for r in row['folds']))

  def test_original_facts_and_overlapping_scope_unchanged(self):
    facts = input_row('MIXED_EVIDENCE_LEDGER')['facts']
    hit = facts['E1']['values']
    self.assertEqual((hit['static_hit_loss'], hit['move_hit_gain'], hit['net_hit_delta']), (571317, 228164, -343153))
    self.assertEqual(hit['candidate_exact_hit_count'], hit['hold_exact_hit_count'] - hit['static_hit_loss'] + hit['move_hit_gain'])
    fp = facts['E2']['values']
    self.assertEqual(fp['gate_fp'], fp['gate_fp_projected_hold'] + fp['harmful_false_movement'])
    self.assertEqual(facts['E5']['values']['PREV_STATIC']['comparison'], [13, 0, 19])
    self.assertEqual(
      document('feasibility-policy')['aggregation_scope'], 'EXISTING_JOB_MEANS_AND_OVERLAPPING_JOB_COUNTS_NO_POOLED_AUC_NO_INDEPENDENT_SAMPLE_CLAIM'
    )

  def test_identifiability_keeps_policy_effect_unknown(self):
    rows = {r['id']: r for r in document('identifiability')['questions']}
    self.assertEqual(rows['current_overall_decision']['status'], 'IDENTIFIABLE_FROM_PUBLIC_EVIDENCE')
    self.assertEqual(rows['train_context_gate_transfer']['status'], 'INPUT_INSUFFICIENT')
    for key in ('alternate_decision_effect', 'calibration_correction_effect', 'downstream_counterfactual_effect', 'unique_decision_cause'):
      self.assertEqual(rows[key]['status'], 'NOT_IDENTIFIABLE')
    self.assertIsNone(document('identifiability')['predicted_policy_gain'])

  def test_minimum_evidence_requests_do_not_grant_access(self):
    row = document('next-evidence-gate')
    self.assertFalse(row['data_access_authorized'])
    self.assertFalse(row['evidence_generation_authorized'])
    self.assertEqual({r['category'] for r in row['minimum_evidence']}, set('ABCDE'))
    for request in row['minimum_evidence']:
      self.assertTrue(
        {'why', 'question', 'existing_status', 'privacy', 'minimum_unit', 'repeatability', 'missing_status', 'approval', 'holdout_impact'} <= request.keys()
      )
      self.assertFalse(request['execution_authorized'])

  def test_five_options_complete_and_unadopted(self):
    options = document('next-evidence-gate')['options']
    self.assertEqual([r['id'] for r in options], list('ABCDE'))
    for row in options:
      self.assertTrue(
        {
          'target_problem',
          'supporting_evidence',
          'contradicting_evidence',
          'data_sufficiency',
          'identifiability',
          'integration_risks',
          'future_authorization',
          'validation',
          'review_feasibility',
        }
        <= row.keys()
      )
      self.assertFalse(row['adopted_as_policy'])
      self.assertIsNone(row['predicted_gain'])

  def test_final_feasibility_states_are_limited(self):
    row = document('identifiability')
    self.assertEqual(
      set(row['feasibility_states']),
      {
        'PUBLIC_EVIDENCE_SUFFICIENT_FOR_DESCRIPTIVE_TRANSFER_REVIEW',
        'POLICY_EFFECT_NOT_IDENTIFIABLE_FROM_PUBLIC_AGGREGATES',
        'ADDITIONAL_EVIDENCE_AUTHORIZATION_REQUIRED',
        'DECISION_POLICY_DESIGN_REVIEW_FEASIBLE_WITH_LIMITS',
        'NO_POLICY_IMPLEMENTATION_AUTHORIZED',
      },
    )
    self.assertEqual(row['public_only_next_scope'], 'REQUIREMENTS_AND_EVIDENCE_GATES_ONLY_NO_CUTOFF_OR_POLICY_SELECTION')
    self.assertFalse(row['private_evidence_required_for_requirements_review'])

  def test_one_next_recommendation_unstarted(self):
    row = document('next-evidence-gate')['recommendation']
    self.assertEqual(row['topic'], 'STAGE1_DECISION_POLICY_REQUIREMENTS_REVIEW')
    for key in ('why_this_review', 'why_now', 'supporting_evidence', 'contradicting_evidence', 'remaining_uncertainty', 'required_approval', 'stop_boundary'):
      self.assertTrue(row[key])
    self.assertFalse(row['started'])
    self.assertFalse(row['execution_authorized'])

  def test_future_axes_preserve_exact_frozen_gate(self):
    row = document('next-evidence-gate')
    gate = input_row('UPSTREAM_POL_GATE')
    self.assertEqual(len(gate['clauses']), 32)
    self.assertEqual(row['frozen_gate']['clauses_sha256'], hashlib.sha256(canonical(gate['clauses'])).hexdigest())
    self.assertEqual(len(row['validation_axes']), 19)
    self.assertEqual(row['new_acceptance_cutoffs'], [])
    allowed = {
      'EXISTING_FROZEN_GATE_UNCHANGED',
      'EXISTING_DESCRIPTIVE_DIAGNOSTIC',
      'FUTURE_POLICY_APPROVAL_REQUIRED',
      'FUTURE_EXECUTION_AUTHORIZATION_REQUIRED',
    }
    self.assertTrue(all(set(axis['classifications']) <= allowed for axis in row['validation_axes']))

  def test_no_alternative_scientific_computation_or_policy_selection(self):
    row = document('feasibility-policy')
    self.assertEqual(row['alternative_decisions_evaluated'], [])
    self.assertEqual(row['calibration_corrections_fitted'], [])
    self.assertEqual(row['models_selected'], [])
    self.assertEqual(row['policies_selected'], [])
    self.assertFalse(row['new_scientific_metrics_allowed'])

  def test_public_privacy_and_negative_synthetic_payloads(self):
    for label in LABELS:
      privacy(document(label))
    for key in PRIVATE_KEYS:
      with self.subTest(key=key), self.assertRaises(ValueError):
        privacy({key: [1]})
    for value in ('E:/synthetic', '/mnt/e/synthetic', '/home/synthetic', r'\\synthetic\share'):
      with self.subTest(value=value), self.assertRaises(ValueError):
        privacy({'synthetic': value})

  def test_authority_and_original_result_preserved(self):
    for label in LABELS:
      row = document(label)
      self.assertIsNone(row['preserved_result']['selected_candidate'])
      self.assertEqual(row['preserved_result']['selection_state'], 'MODEL_SELECTION_FAILED_CLOSED')
      self.assertEqual(row['authority']['holdout'], 'CLOSED')
      self.assertEqual(row['authority']['opening_count'], 0)
      self.assertEqual(row['authority']['holdout_discovery'], 0)
      self.assertEqual(row['authority']['vehicle_authority'], 'NONE')

  def test_imports_only_stdlib_and_scope_eleven_new_files(self):
    for node in ast.walk(ast.parse(Path(__file__).read_text())):
      if isinstance(node, ast.Import):
        self.assertTrue(all(n.name in ('ast', 'hashlib', 'json', 're', 'subprocess', 'unittest') for n in node.names))
      elif isinstance(node, ast.ImportFrom):
        self.assertEqual(node.module, 'pathlib')
    policy = document('feasibility-policy')
    self.assertEqual(len(policy['allowed_tracked_files']), 11)
    self.assertTrue(policy['existing_workflow_change_forbidden'])

  def test_korean_report_and_honest_validation_resolution(self):
    text = (PUBLIC / (PREFIX + 'feasibility-review.md')).read_text()
    self.assertTrue(text.startswith('CyberPilot V4는 움직임을 구분하는 점수가'))
    self.assertEqual(len(re.findall(r'^## \d+\.', text, re.M)), 18)
    self.assertIn('```mermaid', text)
    self.assertIn('E3 summed-count ratios', text)
    self.assertIn('job-mean rate가 아니다', text)
    self.assertIn('Existing job-mean metric', text)
    privacy(text)
    row = document('validation')
    self.assertIn(row['local_validation_status'], ('PENDING', 'PASS'))
    self.assertEqual(row['regression_scope'], 'EXISTING_SYNTHETIC_FIXTURES_ONLY')
    self.assertEqual(row['private_evidence_execution'], 'NONE')
    self.assertTrue(row['exact_head_ci']['not_claimed_before_execution'])


if __name__ == '__main__':
  unittest.main()
