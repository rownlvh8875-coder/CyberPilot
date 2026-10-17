"""Public design/schema assertions and synthetic semantics; no policy runtime."""

import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[4]
PUBLIC = ROOT / 'docs/cyberpilot/changes'
BASE = 'd30b61668dce158237b3f008a351b679c785eb6e'
PREFIX = 'empirical-hurdle-stage1-v4-d-'
POLICY = PREFIX + 'transition-aware-policy.json'
EVALUATION = PREFIX + 'offline-evaluation-contract.json'
COUNTERS = ('private_manifest_openings', 'private_array_openings', 'threshold_readings', 'threshold_application_calls',
            'train_gate_reconstruction_calls', 'model_refit_calls', 'normalizer_refit_calls', 'stage2_refit_calls', 'calibration_fit_calls',
            'prediction_replay_calls', 'rollout_regeneration_calls', 'candidate_search_calls', 'selection_calls',
            'new_scientific_aggregate_calls', 'raw_log_openings', 'qlog_openings', 'holdout_openings', 'holdout_discovery',
            'vehicle_activation_calls', 'source_writes')
FIREWALL = ('qualification_allowed', 'reference_promotable', 'sealed_reference_allowed', 'vehicle_activation_allowed',
            'production_authority', 'ta_execution', 'sg_execution', 'composition_authorized', 'candidate_search_authorized', 'publication_raw_data')
SENSITIVE = {'threshold_value', 'coefficients', 'score_vector', 'row_scores', 'row_gates', 'raw_ticks', 'raw_commands', 'gps',
             'timestamps', 'private_root', 'private_manifest', 'witness_row_indices', 'calibration_parameters'}
PRIVATE_PATH = re.compile(r'(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|/(?:mnt|home|Users|tmp)/|\\\\)')


def canonical(value):
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def load(name):
  value = json.loads((PUBLIC / name).read_bytes())
  body = {k: v for k, v in value.items() if k != 'receipt_sha256'}
  if value['receipt_sha256'] != hashlib.sha256(canonical(body)).hexdigest():
    raise ValueError('RECEIPT_CONFLICT')
  return value


def resolve(value, pointer):
  for token in pointer.strip('/').split('/') if pointer != '/' else ():
    token = token.replace('~1', '/').replace('~0', '~')
    value = value[int(token)] if isinstance(value, list) else value[token]
  return value


def privacy(value):
  if isinstance(value, dict):
    if SENSITIVE.intersection(value):
      raise ValueError('PRIVATE_PAYLOAD')
    for child in value.values():
      privacy(child)
  elif isinstance(value, list):
    for child in value:
      privacy(child)
  elif isinstance(value, str) and PRIVATE_PATH.search(value):
    raise ValueError('PRIVATE_PATH')


class TestTransitionAwareDesign(unittest.TestCase):
  def test_seals_baseline_and_design_only_authority(self):
    for name in (POLICY, EVALUATION):
      row = load(name)
      self.assertEqual(row['baseline_head'], BASE)
      self.assertEqual(row['scope'], 'D_POLICY_DESIGN_AND_EVALUATION_CONTRACT_ONLY')
      self.assertTrue(row['authorization']['D_design_only'])
      for key in ('private_access', 'policy_adoption', 'runtime_implementation', 'E_execution', 'F_holdout', 'F_vehicle', 'V5'):
        self.assertFalse(row['authorization'][key])
      self.assertTrue(all(row[key] is False for key in FIREWALL))
      self.assertEqual(row['operation_counters'], dict.fromkeys(COUNTERS, 0))

  def test_public_input_hash_seal_and_exact_git_binding(self):
    lock = load(POLICY)['input_lock']
    for pin in lock.values():
      path = pin['path']
      raw = (ROOT / path).read_bytes()
      self.assertEqual(hashlib.sha256(raw).hexdigest(), pin['raw_sha256'])
      self.assertEqual(raw, subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT))
      if 'receipt_sha256' in pin:
        self.assertEqual(load(Path(path).name)['receipt_sha256'], pin['receipt_sha256'])

  def test_original_execution_sources_and_symbols(self):
    row = load(POLICY)
    for pin in row['source_lock'].values():
      raw = (ROOT / pin['path']).read_bytes()
      self.assertEqual(hashlib.sha256(raw).hexdigest(), pin['raw_sha256'])
      self.assertEqual(raw, subprocess.check_output(['git', 'show', BASE + ':' + pin['path']], cwd=ROOT))
      if pin.get('original_execution_source'):
        self.assertEqual(raw, subprocess.check_output(['git', 'show', row['execution_head'] + ':' + pin['path']], cwd=ROOT))
      if 'symbols' in pin:
        nodes = {n.name: n.lineno for n in ast.parse(raw).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        self.assertEqual({k: nodes[k] for k in pin['symbols']}, pin['symbols'])

  def test_c_protocol_and_observation_status_preserved(self):
    c = load('empirical-hurdle-stage1-v4-c-diagnostic-results.json')
    policy = load(POLICY)
    self.assertEqual(c['status'], 'C_DIAGNOSTIC_AGGREGATION_COMPLETE')
    self.assertEqual(c['processed_jobs'], 32)
    self.assertEqual(policy['c_evidence']['protocol_raw_sha256'], '0549292dd5101c39b118839d881720a23037cc6db6e516c6fa5d8bcda04b742f')
    self.assertFalse(policy['c_evidence']['new_policy_effect_proven'])
    self.assertFalse(policy['c_evidence']['suppressed_results_inferred'])

  def test_exact_policy_and_candidate_fold_scope(self):
    row = load(POLICY)
    self.assertEqual(list(row['policies']), ['D0', 'D1'])
    self.assertEqual(row['policies']['D0']['id'], 'V4_FROZEN_SINGLE_SHARED_DECISION')
    self.assertEqual(row['policies']['D1']['id'], 'V4_TWO_CONTEXT_TRAIN_ONLY_DECISION')
    self.assertEqual(row['jobs'], {'delays': [0, 5, 10, 20], 'history_lengths': [1, 5, 15, 45],
                                  'folds': ['FOLD_A', 'FOLD_B'], 'count': 32, 'order': 'PUBLIC_FROZEN_V4_JOB_MANIFEST'})
    self.assertIsNone(row['selected_policy'])
    self.assertFalse(row['automatic_additional_policy_search'])

  def test_d0_unchanged_and_d1_two_private_values_per_job(self):
    policies = load(POLICY)['policies']
    self.assertEqual(policies['D0']['decision_scope'], 'ONE_PER_CANDIDATE_FOLD_SHARED_ACROSS_TWO_HEADS')
    self.assertEqual(policies['D1']['decision_scope'], 'ONE_PER_CANDIDATE_FOLD_CONTEXT')
    self.assertEqual(policies['D1']['decision_names'], ['decision_previous_static', 'decision_previous_move'])
    self.assertFalse(policies['D1']['global_numeric_value_across_jobs'])
    self.assertFalse(policies['D1']['actual_values_generated'])

  def test_train_only_selection_recipe_is_exact(self):
    r = load(POLICY)['selection_recipe']
    self.assertEqual(r['input_role'], 'TRAIN')
    self.assertEqual(r['score_field'], 'V4/combined_probability')
    self.assertEqual(r['label_field'], 'V1_REFERENCE/move_label')
    self.assertEqual(r['context_field'], 'V1_REFERENCE/prior_delta_tick')
    self.assertEqual(r['candidate_set'], '{0,1} UNION UNIQUE_FINITE_CONTEXT_TRAIN_SCORES')
    self.assertEqual(r['objective'], 'TP*N_negative + TN*N_positive')
    self.assertEqual(r['maximize_lexicographic'], ['BA_NUM', 'TN', 'LARGER_TRAIN_DECISION'])
    self.assertEqual(r['support_guard'], 'P>0 AND N_negative>0; OTHERWISE FAIL_CLOSED_NO_FALLBACK')
    self.assertEqual(r['float_tolerance'], 0)
    self.assertFalse(r['computed_in_D'])
    self.assertFalse(r['DEV_input_allowed'])
    self.assertTrue(r['freeze_both_decisions_before_DEV_access'])

  def test_strict_comparison_synthetic_only(self):
    r = load(POLICY)['gate_contract']
    self.assertEqual(r['comparison'], 'STRICT_SCORE_GT_CONTEXT_DECISION')
    self.assertEqual(r['equality'], 'STATIC')
    # Arbitrary synthetic scalar semantics, never a selector or private decision.
    self.assertFalse(3 / 4 > 3 / 4)
    self.assertTrue(1 > 3 / 4)
    self.assertFalse(1 / 4 > 3 / 4)

  def test_lexicographic_tie_priority_synthetic_only(self):
    self.assertGreater((9, 0, 0), (8, 99, 99))
    self.assertGreater((9, 4, 0), (9, 3, 99))
    self.assertGreater((9, 4, 2), (9, 4, 1))
    self.assertEqual(load(POLICY)['selection_recipe']['integer_comparison'], 'PYTHON_EXACT_INTEGERS_NO_BA_FLOAT_DIVISION')

  def test_four_truth_states_not_inference_inputs(self):
    row = load(POLICY)
    self.assertEqual(row['truth_transitions'], {'STATIC_HOLD': [0, 0], 'MOVE_ONSET': [0, 1],
                                              'MOVE_TERMINATION': [1, 0], 'MOVE_CONTINUATION': [1, 1]})
    self.assertFalse(row['causal_state']['future_truth_is_input'])
    self.assertEqual(row['causal_state']['one_step_context'], 'OBSERVED_PRIOR_DELTA_NE_ZERO')
    self.assertEqual(row['causal_state']['recursive_context'], 'ACTUAL_PROJECTED_PRIOR_DELTA_NE_ZERO')
    self.assertFalse(row['causal_state']['saved_gate_is_routing_input'])

  def test_shared_head_and_decision_routing_before_normalization(self):
    row = load(POLICY)['causal_state']
    self.assertEqual(row['routing_order'], 'RAW_PRIOR_DELTA_THEN_HEAD_AND_DECISION_CONTEXT_THEN_FROZEN_NORMALIZATION')
    self.assertTrue(row['same_context_for_head_and_decision'])
    self.assertEqual(row['initialization'], 'OBSERVED_FULL_ELIGIBLE_HISTORY; LAST_OBSERVED_DELTA_AT_STEP_ZERO')
    self.assertEqual(row['boundary'], 'NO_PADDING_OR_CROSS_SEGMENT_HISTORY; RESET_EACH_PATH_AND_HORIZON')

  def test_gate_realization_and_full_state_ownership(self):
    row = load(POLICY)['gate_contract']
    self.assertEqual(row['allowed_success_pairs'], [['STATIC', 'HOLD'], ['MOVE', 'HOLD'], ['MOVE', 'MOVE']])
    self.assertFalse(row['force_nonzero_move'])
    state = load(POLICY)['causal_state']
    self.assertEqual(state['history_update'], 'SHIFT_FULL_DELTA_HISTORY_APPEND_NEW_PROJECTED_TICK_MINUS_OLD_PROJECTED_TICK')
    self.assertTrue(state['full_projected_tick_and_history_feed_next_features'])
    self.assertEqual(state['missing_or_invalid_context'], 'FAIL_CLOSED_NO_FALLBACK')

  def test_frozen_stage2_and_projection(self):
    row = load(POLICY)['unchanged_interfaces']
    self.assertEqual(row['projection'], 'FINITE_THEN_TIES_TO_EVEN_THEN_SIGNED16_CHECK_NO_CLIP')
    self.assertTrue(all(row[k] for k in ('stage1_coefficients', 'stage2', 'normalizers', 'feature_order',
                                       'delayed_command_normalization', 'history_window', 'overflow_fail_closed')))
    self.assertEqual(round(2.5), 2)
    self.assertEqual(round(3.5), 4)
    self.assertEqual(load(POLICY)['gate_contract']['invalid_projection'], 'WHOLE_FOLD_INVALID_NO_PARTIAL_CHERRY_PICK')

  def test_17_requirement_traceability_without_rewriting_requirements(self):
    row = load(POLICY)
    original = load('empirical-hurdle-stage1-v4-decision-policy-requirements-spec.json')['requirements']
    self.assertEqual([t['requirement_id'] for t in row['requirements_traceability']], [r['requirement_id'] for r in original])
    for i, item in enumerate(row['requirements_traceability']):
      self.assertEqual(item['source_pointer'], f'/requirements/{i}')
      self.assertEqual(set(item), {'requirement_id', 'source_pointer', 'design_pointers', 'evaluation_domains', 'status'})
      self.assertEqual(item['status'], 'DESIGN_TRACEABLE_NOT_EMPIRICAL_COMPLIANCE')
      self.assertTrue(item['evaluation_domains'])
      for pointer in item['design_pointers']:
        self.assertIsNotNone(resolve(row, pointer))
    self.assertEqual(row['unresolved_requirements'], ['R02_NEW_CONDITIONAL_CUTOFF_REQUIRES_APPROVAL', 'R11_CAUSAL_SHARE_NOT_IDENTIFIED'])

  def test_e_contract_binds_design_and_all_22_domains(self):
    row = load(EVALUATION)
    self.assertEqual(row['policy_receipt_sha256'], load(POLICY)['receipt_sha256'])
    old = load('empirical-hurdle-stage1-v4-decision-policy-future-validation.json')['domains']
    self.assertEqual([d['order'] for d in row['validation_domains']], list(range(1, 23)))
    for a, b in zip(row['validation_domains'], old, strict=True):
      self.assertEqual(a['source_pointer'], f'/domains/{b["order"] - 1}')
      self.assertTrue(a['verification'])
      self.assertTrue(a['failure_behavior'])
    self.assertEqual(row['policy_arms'], ['D0', 'D1'])

  def test_acceptance_uses_hold_last_and_d0_comparison_is_separate(self):
    row = load(EVALUATION)['acceptance']
    old = load('empirical-hurdle-acceptance-gate-v1.json')
    self.assertEqual(row['receipt_sha256'], old['receipt_sha256'])
    self.assertEqual(row['clause_count'], len(old['clauses']))
    self.assertEqual(row['clause_count'], 32)
    self.assertEqual(row['comparator'], 'HOLD_LAST_SAME_ANCHORS')
    self.assertEqual(row['D0_comparison'], 'MANDATORY_PAIRED_DESCRIPTIVE_REFERENCE_NOT_REPLACEMENT_ACCEPTANCE_COMPARATOR')
    self.assertEqual(row['folds'], old['required_folds'])
    self.assertEqual(row['epsilon'], old['epsilon'])
    self.assertEqual(row['clauses_body_sha256'], hashlib.sha256(canonical(old['clauses'])).hexdigest())
    self.assertEqual(row['support'], 'EXISTING_SUPPORT_201; SAME_ANCHORS_AND_COMPARATOR_ANCHORS; NO_RELAXATION')
    self.assertFalse(row['new_numeric_cutoffs'])
    self.assertFalse(row['diagnostics_replace_gate'])

  def test_horizons_populations_and_error_definitions(self):
    row = load(EVALUATION)
    self.assertEqual(row['rollout']['horizons'], [25, 50, 100, 200])
    self.assertEqual(row['rollout']['populations'], ['OVERALL', 'PATH_MOVED'])
    self.assertEqual(row['rollout']['path_moved_definition'], 'ANY_OBSERVED_PATH_TICK_DIFFERS_FROM_INITIAL_OBSERVED_TICK')
    self.assertEqual(row['rollout']['error'], 'TERMINAL_PROJECTED_TICK_MINUS_OBSERVED_TARGET_TICK')
    self.assertEqual(row['one_step']['continuous_error'], 'INTEGRATED_DELTA_MINUS_TRUE_SOURCE_GRID_DELTA')
    self.assertEqual(row['one_step']['exact_hit'], 'PROJECTED_NEXT_TICK_EQUALS_OBSERVED_TARGET')
    self.assertEqual(row['one_step']['true_move'], 'INTEGRATED_GATED_DELTA_ON_TRUE_MOVE_NOT_ORACLE_STAGE2')
    self.assertEqual(row['rollout']['insufficient_support'], 'NOT_IDENTIFIABLE_AND_REQUIRED_CLAUSE_NONPASS')

  def test_future_e_input_and_authorization_prerequisites(self):
    row = load(EVALUATION)['execution_gate']
    self.assertFalse(row['currently_authorized'])
    for item in ('EXACT_E_CODE_AND_PROTOCOL_FROZEN', 'EXPLICIT_E_IMPLEMENTATION_AND_EXECUTION_GRANT',
                 'EXACT_PRIVATE_INPUT_AND_OUTPUT_ALLOWLIST', 'CAPACITY_RESERVE_AND_RESOURCE_LIMITS_FIXED',
                 'TWO_INDEPENDENT_PRE_ACCESS_REVIEWS', 'PUBLICATION_COMPOSITION_PRIVACY_REVIEW'):
      self.assertIn(item, row['prerequisites'])
    self.assertEqual(row['missing_inputs'], 'E_INPUT_INSUFFICIENT_NO_FALLBACK_OR_RAW_RECONSTRUCTION')
    self.assertFalse(load(EVALUATION)['inputs']['seven_C_fields_suffice_for_rollout'])

  def test_dev_already_observed_and_no_automatic_admission(self):
    row = load(EVALUATION)
    self.assertFalse(row['interpretation']['blinded_independent_DEV_validation'])
    self.assertFalse(row['interpretation']['jobs_are_independent_experiments'])
    self.assertFalse(row['outcomes']['automatic_policy_adoption'])
    self.assertFalse(row['outcomes']['automatic_candidate_selection'])
    self.assertEqual(row['outcomes']['required_clause_failure'], 'NOT_ADMISSIBLE')
    self.assertEqual(row['outcomes']['all_fail'], 'NO_ADMISSIBLE_CANDIDATE; MODEL_SELECTION_FAILED_CLOSED')
    self.assertEqual(row['outcomes']['complete_gate_pass'], 'RETROSPECTIVE_GATE_PASS_ONLY_NO_ADOPTION_OR_HOLDOUT_ADMISSION')

  def test_privacy_inherits_c_and_extends_joint_arm_suppression(self):
    c = load('empirical-hurdle-stage1-v4-c-diagnostic-protocol.json')['privacy']
    row = load(EVALUATION)['publication']
    self.assertEqual(row['inherited_minimum_support'], c['minimum_support'])
    self.assertEqual(row['public_bins'], 'ALL_WITHHELD')
    self.assertEqual(row['public_scientific_cell_counts'], 'ALL_WITHHELD')
    self.assertTrue(row['joint_D0_D1_cross_fold_context_suppression'])
    self.assertTrue(row['no_inference_of_C_suppressed_results'])
    for name in (POLICY, EVALUATION):
      privacy(load(name))

  def test_synthetic_privacy_rejections(self):
    for value in ({'threshold_value': 0.7}, {'coefficients': [1]}, {'score_vector': [0.1]}, 'E:/synthetic-private', '/mnt/e/synthetic-private'):
      with self.assertRaises(ValueError):
        privacy(value)

  def test_future_policy_extensions_remain_out_of_scope(self):
    row = load(POLICY)
    for name in ('HYSTERESIS', 'DWELL_TIME', 'SCORE_SMOOTHING', 'NEW_HEAD', 'REPRESENTATION_CHANGE', 'CALIBRATION_FITTING', 'NEW_CONTEXT_MEMORY'):
      self.assertIn(name, row['excluded_extensions'])
    self.assertFalse(load(EVALUATION)['post_hoc_recipe_changes_allowed'])

  def test_original_result_replica_and_authority(self):
    for name in (POLICY, EVALUATION):
      row = load(name)
      self.assertEqual(row['preserved']['scientific_result'], 'HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE')
      self.assertEqual(row['preserved']['selection'], 'MODEL_SELECTION_FAILED_CLOSED')
      self.assertIsNone(row['preserved']['selected_candidate'])
      self.assertEqual(row['preserved']['train_rowwise_gate'], 'NOT_SAVED')
      self.assertEqual(row['preserved']['replica'], 'REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED')
      self.assertEqual(row['preserved']['holdout'], 'CLOSED')
      self.assertEqual(row['preserved']['vehicle_authority'], 'NONE')
      self.assertEqual(row['preserved']['hugging_face'], 'NOT_REQUIRED_NOT_USED')

  def test_this_test_has_no_scientific_import_or_private_reader(self):
    tree = ast.parse(Path(__file__).read_text())
    modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    modules.update(alias.name for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names)
    self.assertEqual(modules, {'ast', 'hashlib', 'json', 'pathlib', 're', 'subprocess', 'unittest'})
    self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ('glob', 'rglob', 'iterdir')
                         for n in ast.walk(tree)))


if __name__ == '__main__':
  unittest.main()
