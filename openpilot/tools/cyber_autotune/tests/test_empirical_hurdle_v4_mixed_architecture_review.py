"""Documentation/schema checks only; never imports or executes scientific code."""

import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[4]
PUBLIC = ROOT / 'docs/cyberpilot/changes'
BASE = '42541f583f39dc16609dd207c84cfd366445c0df'
PREFIX = 'empirical-hurdle-stage1-v4-mixed-architecture-'
LABELS = ('review-policy', 'evidence-ledger', 'contract', 'hypothesis-matrix', 'options', 'identifiability', 'decision', 'validation')
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
  'raw_ticks',
  'projected_path',
  'gate_sequence',
  'witness_row_indices',
  'gps',
  'commands',
  'timestamps',
  'private_root',
}
PRIVATE_PATH = re.compile(r'(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|/(?:mnt|home|Users|tmp)/|\\\\)')


def canonical(row):
  return json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def verified(path):
  row = json.loads(path.read_bytes())
  body = {k: v for k, v in row.items() if k != 'receipt_sha256'}
  if row.get('receipt_sha256') != hashlib.sha256(canonical(body)).hexdigest():
    raise ValueError('RECEIPT_CONFLICT')
  if any(row.get(k) is not False for k in FIREWALL):
    raise ValueError('AUTHORITY_CONFLICT')
  return row


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


def resolve(value, tokens):
  if not tokens:
    return
  token, *rest = tokens
  if token == '*':
    children = value.values() if isinstance(value, dict) else value
    for child in children:
      resolve(child, rest)
  else:
    resolve(value[int(token)] if isinstance(value, list) else value[token.replace('~1', '/').replace('~0', '~')], rest)


class TestV4MixedArchitectureReview(unittest.TestCase):
  def test_requested_documents_exist_and_are_sealed(self):
    for label in LABELS:
      row = document(label)
      self.assertEqual(row['component'], label)
      self.assertEqual(row['source_reference']['git_sha'], BASE)
      privacy(row)

  def test_baseline_public_file_bytes_and_receipts(self):
    for entry in document('evidence-ledger')['files'].values():
      path = ROOT / entry['path']
      raw = path.read_bytes()
      self.assertEqual(hashlib.sha256(raw).hexdigest(), entry['file_sha256'])
      self.assertEqual(raw, subprocess.check_output(['git', 'show', BASE + ':' + entry['path']], cwd=ROOT))
      if entry['receipt_sha256'] is not None:
        self.assertEqual(verified(path)['receipt_sha256'], entry['receipt_sha256'])

  def test_common_ledger_binding_and_authority(self):
    ledger = document('evidence-ledger')
    for label in LABELS:
      row = document(label)
      self.assertEqual(row['baseline_head'], BASE)
      self.assertEqual(row['execution_head'], 'bd8045ef2a0da62a92603439f38e7740f5923622')
      self.assertTrue(row['public_evidence_only'])
      self.assertEqual(row['private_array_openings'], 0)
      self.assertEqual(row['scope'], ['DESIGN_REVIEW_ONLY', 'REPORT_ONLY', 'NO_NEW_MODEL_EXECUTION'])
      if label != 'evidence-ledger':
        self.assertEqual(row['evidence_ledger_receipt_sha256'], ledger['receipt_sha256'])
      self.assertFalse(row['next_execution_authorized'])
      self.assertIsNone(row['preserved_result']['selected_candidate'])
      self.assertEqual(row['preserved_result']['selection_state'], 'MODEL_SELECTION_FAILED_CLOSED')
      self.assertEqual(row['authority']['holdout'], 'CLOSED')
      self.assertEqual(row['authority']['opening_count'], 0)
      self.assertEqual(row['authority']['holdout_discovery'], 0)
      self.assertEqual(row['authority']['vehicle_authority'], 'NONE')

  def test_all_forbidden_actual_operation_counters_zero(self):
    for label in LABELS:
      row = document(label)
      self.assertEqual(set(row['operation_counters']), set(COUNTERS))
      self.assertTrue(all(type(v) is int and v == 0 for v in row['operation_counters'].values()))

  def test_fact_references_resolve_without_private_inputs(self):
    ledger = document('evidence-ledger')
    for fact in ledger['facts'].values():
      self.assertTrue(fact['references'])
      for ref in fact['references']:
        entry = ledger['files'][ref['file']]
        self.assertEqual(entry['git_sha'], BASE)
        if 'pointer' in ref:
          resolve(json.loads((ROOT / entry['path']).read_bytes()), ref['pointer'].strip('/').split('/'))
        if 'section' in ref:
          self.assertIn(ref['section'], (ROOT / entry['path']).read_text())

  def test_exact_hit_frozen_identity(self):
    fact = document('evidence-ledger')['facts']['E1']['values']
    self.assertEqual((fact['static_hit_loss'], fact['move_hit_gain'], fact['net_hit_delta']), (571317, 228164, -343153))
    self.assertEqual(fact['candidate_exact_hit_count'], fact['hold_exact_hit_count'] - fact['static_hit_loss'] + fact['move_hit_gain'])
    self.assertEqual(fact['loss_greater_jobs'], 32)

  def test_gate_fp_is_not_realized_movement(self):
    fact = document('evidence-ledger')['facts']['E2']['values']
    self.assertEqual(fact['gate_fp'], 1662235)
    self.assertEqual(fact['gate_fp_projected_hold'], 1090918)
    self.assertEqual(fact['harmful_false_movement'], 571317)
    self.assertEqual(fact['gate_fp'], fact['gate_fp_projected_hold'] + fact['harmful_false_movement'])

  def test_transition_counts_and_fold_scope(self):
    fact = document('evidence-ledger')['facts']['E3']['values']
    self.assertEqual(fact['FOLD_A']['onset_tp'], 115422)
    self.assertEqual(fact['FOLD_B']['onset_tp'], 7707)
    self.assertEqual(fact['FOLD_B']['onset_count'], 358921)
    for fold in ('FOLD_A', 'FOLD_B'):
      self.assertEqual(fact[fold]['previous_move_static_fp_fraction'], 1.0)
    self.assertEqual(
      document('contract')['truth_populations'], ['PREV_STATIC_TRUE_STATIC', 'PREV_STATIC_MOVE_ONSET', 'PREV_MOVE_TRUE_STATIC', 'PREV_MOVE_MOVE_CONTINUATION']
    )

  def test_state_ranking_improvement_is_not_universal(self):
    fact = document('evidence-ledger')['facts']['E5']
    self.assertEqual(fact['comparison_reference'], 'V4_DEV_VS_HISTORICAL_FIXED_V1_DEV_ON_EXACT_MATCHING_ANCHORS')
    values = fact['values']
    self.assertEqual(values['PREV_STATIC']['comparison'], [13, 0, 19])
    self.assertEqual(values['PREV_MOVE']['comparison'], [32, 0, 0])
    self.assertEqual(values['OVERALL']['comparison'], [32, 0, 0])
    self.assertFalse(document('decision')['universal_within_state_improvement_claimed'])

  def test_source_symbols_and_exact_sha_are_static_only(self):
    ledger = document('evidence-ledger')
    for entry in ledger['sources'].values():
      self.assertIsInstance(entry['symbols'], list)
      self.assertTrue(all(isinstance(s['name'], str) and type(s['line']) is int for s in entry['symbols']))
      raw = (ROOT / entry['path']).read_bytes()
      self.assertEqual(hashlib.sha256(raw).hexdigest(), entry['sha256'])
      self.assertEqual(raw, subprocess.check_output(['git', 'show', BASE + ':' + entry['path']], cwd=ROOT))
    for stage in document('contract')['stages']:
      for ref in stage['source_refs']:
        entry = ledger['sources'][ref['file']]
        nodes = {n.name: n for n in ast.parse((ROOT / entry['path']).read_text()).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        self.assertEqual(nodes[ref['symbol']].lineno, ref['line'])

  def test_contract_covers_actual_branches_and_boundaries(self):
    contract = document('contract')
    self.assertEqual({s['id'] for s in contract['stages']}, {f'C{i}' for i in range(1, 11)})
    realization = contract['gate_realization']
    self.assertTrue(realization['STATIC_TO_HOLD']['permitted'])
    self.assertTrue(realization['MOVE_TO_HOLD']['permitted'])
    self.assertTrue(realization['MOVE_TO_MOVE']['permitted'])
    self.assertFalse(realization['STATIC_TO_MOVE']['permitted_on_successful_frozen_path'])
    self.assertEqual(contract['projection']['rounding'], 'NP_RINT_TIES_TO_EVEN')
    self.assertEqual(contract['projection']['range_policy'], 'FAIL_OUTSIDE_SIGNED16_NO_CLIPPING')
    self.assertFalse(contract['projection']['gate_enforces_nonzero_delta'])
    self.assertEqual(contract['recursive_feedback']['mechanical_status'], 'MECHANICALLY_DETERMINED')
    self.assertEqual(contract['recursive_feedback']['terminal_effect_status'], 'NOT_IDENTIFIABLE_FROM_FROZEN_EVIDENCE')
    self.assertFalse(contract['closed_loop_vehicle_claim'])

  def test_hypotheses_are_separate_and_complete(self):
    rows = document('hypothesis-matrix')['hypotheses']
    self.assertEqual([r['id'] for r in rows], [f'H{i}' for i in range(1, 7)])
    required = {
      'supporting_evidence',
      'contradicting_evidence',
      'missing_evidence',
      'actual_code_contract',
      'identifiability',
      'confounding_risks',
      'future_experiment_required',
    }
    for row in rows:
      self.assertTrue(required <= row.keys())
      self.assertEqual(row['kind'], 'HYPOTHESIS_NOT_ESTABLISHED_UNIQUE_CAUSE')
      self.assertFalse(row['future_execution_authorized'])
    self.assertTrue(document('hypothesis-matrix')['numerical_separation_certificate_is_distinct_from_ranking'])

  def test_architecture_options_are_not_adopted_models(self):
    rows = document('options')['options']
    self.assertEqual([r['id'] for r in rows], list('ABCDEF'))
    required = {
      'problem_addressed',
      'mechanism_hypothesis',
      'supporting_evidence',
      'contradicting_evidence',
      'evidence_gap',
      'implementation_scope',
      'integration_risk',
      'validation_requirement',
      'safety_authority_impact',
      'complexity',
      'decision',
    }
    for row in rows:
      self.assertTrue(required <= row.keys())
      self.assertTrue(all(row[k] for k in required))
      self.assertTrue(set(row['problem_addressed']) <= document('evidence-ledger')['facts'].keys())
      self.assertTrue(set(row['supporting_evidence']) <= {f'H{i}' for i in range(1, 7)})
      self.assertTrue(set(row['validation_requirement']) <= {f'V{i}' for i in range(1, 20)})
      self.assertFalse(row['adopted'])
      self.assertIn(row['decision'], ('REVIEW_SUPPORTED', 'INSUFFICIENT', 'DEFERRED'))
      self.assertIsNone(row['predicted_performance_gain'])

  def test_identifiability_answers_and_insufficient_support(self):
    rows = document('identifiability')['questions']
    self.assertEqual([r['id'] for r in rows], list(range(1, 9)))
    self.assertEqual(rows[0]['status'], 'DIRECTLY_SUPPORTED')
    self.assertEqual(rows[4]['status'], 'INPUT_INSUFFICIENT')
    self.assertEqual(rows[5]['status'], 'ASSOCIATION_ONLY')
    self.assertTrue(all(rows[i]['status'] == 'NOT_IDENTIFIABLE' for i in (1, 2, 3, 6, 7)))
    support = document('evidence-ledger')['facts']['E7']['values']
    self.assertEqual(support['100']['FULL_DESCRIPTIVE_SUPPORT'], 0)
    self.assertEqual(support['200'], {'FULL_DESCRIPTIVE_SUPPORT': 0, 'SMALL_SUPPORT_DESCRIPTIVE_ONLY': 25, 'EMPTY': 7, 'path_count_sum': 60})
    self.assertTrue(document('identifiability')['gate_perfect_selection_bias_not_removed'])

  def test_stage2_and_recursive_causal_claims_are_limited(self):
    row = document('identifiability')
    self.assertFalse(row['stage2_exclusive_failure_claimed'])
    self.assertIsNone(row['stage2_terminal_causal_share'])
    self.assertIsNone(row['context_terminal_causal_effect'])
    self.assertEqual(set(row['error_components']), {'STAGE2_MODEL', 'DELTA_INTEGRATION', 'QUANTIZATION_PROJECTION', 'RECURSIVE_CONTEXT', 'UNALLOCATED'})
    self.assertEqual(row['error_components']['STAGE2_MODEL']['status'], 'NOT_IDENTIFIABLE_FROM_FROZEN_EVIDENCE')

  def test_findings_hypotheses_recommendation_are_distinct(self):
    row = document('decision')
    self.assertTrue(all(r['kind'] == 'FINDING' for r in row['findings']))
    self.assertTrue(all(r['kind'] == 'HYPOTHESIS' for r in row['hypotheses']))
    self.assertEqual(row['recommendation']['kind'], 'RECOMMENDATION_REVIEW_TOPIC_ONLY')
    self.assertEqual(row['recommendation']['topic'], 'STAGE1_TRANSITION_AND_DECISION_CONTRACT_REVIEW')
    self.assertTrue(row['recommendation']['counterevidence_and_limits'])
    self.assertEqual(row['architectures_adopted'], [])
    self.assertEqual(row['models_selected'], [])

  def test_future_axes_without_new_acceptance_thresholds(self):
    row = document('decision')
    self.assertEqual(len(row['future_validation_requirements']), 19)
    axes = {r['axis'] for r in row['future_validation_requirements']}
    self.assertIn('25/50/100/200-step OVERALL rollout', axes)
    self.assertIn('25/50/100/200-step PATH_MOVED rollout', axes)
    self.assertEqual(row['new_acceptance_thresholds'], [])
    ledger = document('evidence-ledger')
    gate = verified(ROOT / ledger['files']['POL_GATE']['path'])
    self.assertEqual(len(gate['clauses']), 32)
    self.assertEqual(row['frozen_gate']['clauses_sha256'], hashlib.sha256(canonical(gate['clauses'])).hexdigest())
    self.assertEqual(row['frozen_gate']['clause_ids'], [c['id'] for c in gate['clauses']])
    for requirement in row['future_validation_requirements']:
      self.assertIn(
        requirement['acceptance_policy'],
        ('EXISTING_FROZEN_GATE_UNCHANGED', 'EXISTING_AUTHORITY_OR_INTEGRITY_CONTRACT_UNCHANGED', 'FUTURE_POLICY_APPROVAL_REQUIRED'),
      )
      self.assertFalse(requirement['execution_authorized'])

  def test_report_has_required_sections_and_fixed_source_links(self):
    report = (PUBLIC / (PREFIX + 'review.md')).read_text()
    self.assertTrue(report.startswith('CyberPilot V4는 학습 과정이 정상적으로 끝났지만'))
    self.assertIn('```mermaid', report)
    for number in range(1, 18):
      self.assertRegex(report, rf'(?m)^## {number}\. ')
    self.assertIn('/blob/' + BASE + '/', report)
    self.assertIn('NOT_IDENTIFIABLE_FROM_FROZEN_EVIDENCE', report)
    self.assertIn('FUTURE_POLICY_APPROVAL_REQUIRED', report)
    self.assertIn('2.147%', report)
    self.assertIn('100%', report)
    privacy(report)

  def test_new_test_has_no_scientific_imports(self):
    tree = ast.parse(Path(__file__).read_text())
    for node in ast.walk(tree):
      if isinstance(node, ast.Import):
        self.assertTrue(all(n.name.split('.')[0] in ('ast', 'hashlib', 'json', 'pathlib', 're', 'subprocess', 'unittest') for n in node.names))
      elif isinstance(node, ast.ImportFrom):
        self.assertEqual(node.module, 'pathlib')

  def test_privacy_rejects_synthetic_forbidden_payloads(self):
    for key in PRIVATE_KEYS:
      with self.subTest(key=key), self.assertRaises(ValueError):
        privacy({key: [1]})
    for value in ('E:/synthetic-private-root', '/mnt/e/synthetic', '/home/synthetic', r'\\synthetic\share'):
      with self.subTest(value=value), self.assertRaises(ValueError):
        privacy({'value': value})

  def test_privacy_accepts_pinned_public_repository_links(self):
    privacy({'source': 'https://github.com/rownlvh8875-coder/CyberPilot/blob/' + BASE + '/openpilot/tools/cyber_autotune/empirical_hurdle_v4_execution.py#L20'})

  def test_receipt_tamper_fixture_is_rejected(self):
    row = document('review-policy')
    changed = dict(row, private_array_openings=1)
    self.assertNotEqual(row['receipt_sha256'], hashlib.sha256(canonical({k: v for k, v in changed.items() if k != 'receipt_sha256'})).hexdigest())

  def test_prior_mechanism_states_preserved(self):
    states = document('evidence-ledger')['facts']['E9']['values']['states']
    self.assertEqual(len(states), 6)
    self.assertIn('V4_MIXED_GATE_AND_MAGNITUDE_FAILURE_SUPPORTED', states)
    self.assertEqual(document('decision')['prior_mechanism_states_preserved'], states)

  def test_validation_does_not_claim_unrun_ci(self):
    row = document('validation')
    self.assertIn(row['local_validation_status'], ('PENDING', 'PASS'))
    self.assertEqual(row['exact_head_ci']['resolution'], 'GITHUB_ACTIONS_ON_CONTAINING_GIT_COMMIT')
    self.assertTrue(row['exact_head_ci']['not_claimed_before_execution'])
    self.assertEqual(row['private_evidence_execution'], 'NONE')
    self.assertEqual(row['regression_scope'], 'EXISTING_SYNTHETIC_FIXTURES_ONLY')


if __name__ == '__main__':
  unittest.main()
