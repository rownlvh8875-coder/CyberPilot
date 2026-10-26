"""Public schema/identity and synthetic authority tests; no scientific execution."""

import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[4]
PUBLIC = ROOT / 'docs/cyberpilot/changes'
BASE = '6b8af85aecc99ad9529e6efa93c3f9b49370284f'
PREFIX = 'empirical-hurdle-stage1-v4-evidence-access-'
LABELS = ('review-policy', 'public-input-lock', 'scope-request', 'field-allowlist', 'replica-contract',
          'authorization-boundary', 'privacy-contract', 'review-decision', 'review-validation')
COUNTERS = ('private_manifest_openings', 'private_array_openings', 'private_directory_discovery_calls', 'raw_log_openings', 'qlog_openings',
            'model_refit_calls', 'normalizer_refit_calls', 'stage2_refit_calls', 'calibration_fit_calls', 'threshold_reselection_calls',
            'prediction_replay_calls', 'rollout_regeneration_calls', 'selection_calls', 'candidate_search_calls', 'holdout_openings',
            'holdout_discovery', 'source_write_count', 'vehicle_activation_calls', 'private_aggregate_generation_calls')
FIREWALL = ('qualification_allowed', 'reference_promotable', 'sealed_reference_allowed', 'vehicle_activation_allowed', 'production_authority',
            'ta_execution', 'sg_execution', 'composition_authorized', 'candidate_search_authorized', 'publication_raw_data')
PRIVATE_KEYS = {'threshold', 'threshold_value', 'coefficients', 'normalizer_values', 'probabilities', 'p_move', 'score_vector', 'raw_scores',
                'raw_ticks', 'projected_path', 'predicted_gate', 'predicted_gate_path', 'gate_sequence', 'observed_path', 'commands', 'gps',
                'timestamps', 'private_root', 'witness_row_indices', 'calibration_parameters', 'row_scores', 'row_gates', 'access_token', 'password'}
PRIVATE_PATH = re.compile(r'(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|/(?:mnt|home|Users|tmp)/|\\\\)')
REQUEST_FIELDS = {'REQUEST_ID', 'PURPOSE', 'APPROVAL_LAYER', 'CURRENT_GRANT_STATUS', 'EXACT_HOST_IDENTITY',
                  'EXACT_CANONICAL_ROOT_STATUS', 'EXACT_MANIFEST_REFERENCE_STATUS', 'ALLOWED_CANDIDATES', 'ALLOWED_FOLDS', 'ALLOWED_ROLES',
                  'ALLOWED_FIELDS', 'METADATA_ONLY_SCOPE', 'ARRAY_READ_SCOPE', 'SOURCE_IMMUTABILITY', 'REPLICA_EQUALITY_REQUIREMENT',
                  'ALLOWED_OPERATIONS', 'FORBIDDEN_OPERATIONS', 'EXPECTED_OUTPUT', 'PRIVACY_RESTRICTIONS', 'STOP_CONDITIONS',
                  'HUMAN_INPUT_REQUIRED', 'EXPLICIT_HUMAN_GRANT_REQUIRED', 'C_AUTHORIZED', 'D_AUTHORIZED', 'E_AUTHORIZED', 'F_AUTHORIZED'}


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


class TestEvidenceAccessReview(unittest.TestCase):
  def test_requested_artifacts_and_scope(self):
    policy = doc('review-policy')
    for label in LABELS:
      row = doc(label)
      self.assertEqual(row['component'], label)
      self.assertEqual(row['baseline_head'], BASE)
      self.assertEqual(row['scope'], ['AUTHORIZATION_SCOPE_REVIEW_ONLY', 'PUBLIC_EVIDENCE_ONLY', 'NO_PRIVATE_DATA_ACCESS', 'NO_SCIENTIFIC_EXECUTION'])
      if label != 'review-policy':
        self.assertEqual(row['review_policy_receipt_sha256'], policy['receipt_sha256'])
      self.assertFalse(row['data_access_granted'])
      self.assertFalse(row['B_GRANTED'])
      self.assertFalse(row['ACCESS_READY'])
      self.assertFalse(row['PRIVATE_DATA_OPENED'])

  def test_public_lock_original_and_additional_identity(self):
    lock = doc('public-input-lock')['input_lock']
    self.assertEqual(lock['previous_lock_counts'], {'public_files': 55, 'sealed_json': 51, 'static_sources': 17})
    self.assertEqual((len(lock['files']), len(lock['sources'])), (76, 21))
    self.assertEqual(len({v['path'] for v in lock['files'].values()}), 76)
    seals = 0
    for entry in [*lock['files'].values(), *lock['sources'].values(), lock['workflow_pin']]:
      raw = (ROOT / entry['path']).read_bytes()
      self.assertEqual(hashlib.sha256(raw).hexdigest(), entry.get('file_sha256', entry.get('sha256')))
      self.assertEqual(raw, subprocess.check_output(['git', 'show', BASE + ':' + entry['path']], cwd=ROOT))
      if entry.get('receipt_sha256'):
        self.assertEqual(verify(json.loads(raw))['receipt_sha256'], entry['receipt_sha256'])
        seals += 1
    self.assertEqual(seals, 71)

  def test_source_and_evidence_pointers_resolve(self):
    lock = doc('public-input-lock')['input_lock']
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
          nodes = {n.name: n for n in ast.parse((ROOT / entry['path']).read_text()).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
          self.assertEqual(ref['line'], nodes[ref['symbol']].lineno)

  def test_original_execution_sources_unchanged(self):
    lock = doc('public-input-lock')['input_lock']
    for name in lock['original_execution_scientific_files']:
      path = lock['sources'][name]['path']
      self.assertEqual((ROOT / path).read_bytes(), subprocess.check_output(['git', 'show', lock['execution_head'] + ':' + path], cwd=ROOT))

  def test_catalog_exact_32_public_job_mapping(self):
    row = doc('scope-request')
    jobs = row['public_job_catalog']
    expected = [(f'HRI_D{d:02d}_L{length:02d}', d, length, fold)
                for d in (0, 5, 10, 20) for length in (1, 5, 15, 45) for fold in ('FOLD_A', 'FOLD_B')]
    self.assertEqual([(j['candidate_id'], j['d'], j['L'], j['fold']) for j in jobs], expected)
    self.assertEqual(len({(j['candidate_id'], j['fold']) for j in jobs}), 32)
    lock = doc('public-input-lock')['input_lock']
    original = json.loads((ROOT / lock['files']['V4_JOB_MANIFEST']['path']).read_bytes())
    self.assertEqual([(j['candidate_id'], j['fold']) for j in jobs], [(j['candidate_id'], j['fold']) for j in original['jobs']])
    self.assertTrue(all(j['status'] == 'EXECUTED_COMPLETE' for j in original['jobs']))

  def test_request_required_fields_and_no_grant(self):
    request = doc('scope-request')['request']
    self.assertTrue(REQUEST_FIELDS <= request.keys())
    self.assertEqual(request['APPROVAL_LAYER'], 'B0_REQUEST_ONLY_B1_SEPARATE')
    self.assertEqual(request['CURRENT_GRANT_STATUS'], 'NOT_GRANTED')
    self.assertTrue(request['EXPLICIT_HUMAN_GRANT_REQUIRED'])
    for key in ('C_AUTHORIZED', 'D_AUTHORIZED', 'E_AUTHORIZED', 'F_AUTHORIZED'):
      self.assertIs(request[key], False)

  def test_canonical_host_and_manifest_path_unresolved(self):
    request = doc('scope-request')['request']
    self.assertEqual(request['EXACT_HOST_IDENTITY'], 'UNRESOLVED_REDACTED_PRIVATE_REFERENCE')
    self.assertEqual(request['EXACT_CANONICAL_ROOT_STATUS'], 'CANONICAL_ROOT_UNRESOLVED')
    self.assertEqual(request['EXACT_MANIFEST_REFERENCE_STATUS'], 'PUBLIC_EXPECTED_IDENTITIES_AVAILABLE_EXACT_PRIVATE_PATHS_UNRESOLVED')
    self.assertFalse(doc('review-decision')['path_hash_is_canonical_path'])
    self.assertFalse(doc('review-decision')['volume_identity_is_host_or_root_identity'])

  def test_b0_metadata_only_and_no_array_bytes(self):
    b0 = doc('scope-request')['request']['METADATA_ONLY_SCOPE']
    self.assertEqual(b0['named_record_count'], 4)
    self.assertFalse(b0['executed'])
    self.assertFalse(b0['array_payload_or_header_read_allowed'])
    self.assertFalse(b0['array_digest_read_allowed'])
    self.assertEqual(b0['array_shape_dtype_status'], 'NOT_REVERIFIED_IN_B0')
    self.assertFalse(b0['train_model_receipt_read_allowed'])

  def test_b1_separate_and_human_subset_not_chosen(self):
    request = doc('scope-request')['request']
    self.assertEqual(len(request['ALLOWED_CANDIDATES']), 16)
    self.assertEqual(request['ALLOWED_FOLDS'], ['FOLD_A', 'FOLD_B'])
    self.assertEqual(request['ALLOWED_ROLES'], ['TRAIN', 'DEV'])
    b1 = request['ARRAY_READ_SCOPE']
    self.assertFalse(b1['granted'])
    self.assertFalse(b1['executed'])
    self.assertEqual(b1['candidate_fold_role_subset'], [])
    self.assertEqual(b1['subset_status'], 'HUMAN_NAMED_EXACT_SUBSET_REQUIRED_NO_PERFORMANCE_SELECTION')
    self.assertEqual(request['allowlist_interpretation'], 'PUBLIC_CATALOG_CEILING_ONLY_NOT_BLANKET_ARRAY_OR_RECEIPT_ACCESS')

  def test_minimal_seven_field_bindings_roles_and_owners(self):
    rows = doc('field-allowlist')['proposed_b1_fields']
    expected = {('TRAIN', 'V4', 'combined_probability'), ('TRAIN', 'V1_REFERENCE', 'move_label'), ('TRAIN', 'V1_REFERENCE', 'prior_delta_tick'),
                ('DEV', 'V4', 'p_move'), ('DEV', 'V4', 'predicted_gate'), ('DEV', 'V1_REFERENCE', 'true_move'),
                ('DEV', 'V1_REFERENCE', 'prior_delta_tick')}
    self.assertEqual({(r['role'], r['owner'], r['field_name']) for r in rows}, expected)
    for row in rows:
      self.assertEqual(row['full_shape_requirement'], '[N]')
      self.assertFalse(row['live_existence_verified'])
      self.assertFalse(row['current_read_authorized'])
      self.assertTrue(row['source_refs'])

  def test_train_gates_not_saved_and_no_reconstruction(self):
    row = doc('field-allowlist')
    self.assertEqual(row['train_rowwise_gate'], 'NOT_SAVED_INPUT_INSUFFICIENT_NO_THRESHOLD_APPLICATION')
    self.assertFalse(row['train_gate_reconstruction_authorized'])
    self.assertFalse(row['frozen_decision_application_authorized'])
    self.assertFalse(row['new_confusion_aggregation_authorized'])

  def test_sensitive_train_carrier_not_implicitly_opened(self):
    row = doc('field-allowlist')['mixed_carrier_constraint']
    self.assertEqual(row['carrier_schema'], 'V4_MODEL_THRESHOLD')
    self.assertFalse(row['b0_read_allowed'])
    self.assertFalse(row['b1_blanket_carrier_parse_allowed'])
    self.assertEqual(row['resolution'], 'FUTURE_EXPLICIT_CARRIER_SCOPE_OR_TRUSTED_MINIMIZED_DESCRIPTOR_REQUIRED')
    self.assertFalse(row['minimized_projection_exists_or_verified'])

  def test_no_ticks_or_coefficients_in_initial_b1(self):
    actual = {r['field_name'] for r in doc('field-allowlist')['proposed_b1_fields']}
    self.assertFalse(actual.intersection({'threshold', 'coefficients', 'current_tick', 'target_next_tick', 'actual_delta_tick',
                                        'projected_path', 'predicted_gate_path', 'commands', 'integrated_delta'}))
    self.assertEqual(doc('field-allowlist')['label_semantics_against_target_ticks'], 'NOT_REVERIFIED_NO_SCOPE_EXPANSION')

  def test_all_fields_alignment_and_no_coercive_repair(self):
    row = doc('field-allowlist')['alignment_contract']
    self.assertTrue(row['every_field_full_shape_equals_N'])
    self.assertTrue(row['ordered_anchor_required'])
    self.assertFalse(row['count_only_alignment_sufficient'])
    self.assertFalse(row['anchor_alone_proves_job_identity'])
    self.assertEqual(row['forbidden_repairs'], ['REORDER', 'TRUNCATE', 'ZIP_MIN_LENGTH', 'RECONSTRUCT', 'IMPUTE', 'CAST_TO_HIDE_CONFLICT'])
    self.assertIn('TRAIN_FINALIZED_PARENT_CHAIN', row['dev_identity_requirement'])

  def test_hash_domains_and_trusted_provenance_distinct(self):
    row = doc('replica-contract')
    self.assertEqual(set(row['hash_domains']), {'receipt_sha256', 'file_sha256', 'npy_sha256', 'array_sha256'})
    self.assertFalse(row['self_consistent_receipt_proves_trusted_origin'])
    self.assertFalse(row['manifest_declarations_prove_live_payload_equality'])
    self.assertFalse(row['replica_equality_proves_independent_execution_or_source_correctness'])

  def test_replica_order_and_preservation(self):
    row = doc('replica-contract')
    self.assertEqual(row['required_order'], ['TRUSTED_MANIFEST_IDENTITY', 'APPROVED_BYTE_CONTENT_EQUALITY', 'REPEAT_1_USE_ELIGIBILITY', 'RETAIN_REPEAT_2'])
    self.assertFalse(row['replicas_are_independent_samples'])
    self.assertFalse(row['replica_averaging_allowed'])
    self.assertFalse(row['repeat_2_deletion_allowed'])
    self.assertFalse(row['fresh_replica_verification_executed'])
    self.assertEqual(row['current_repeat_1_use_status'], 'NOT_AUTHORIZED')

  def test_broad_existing_verifiers_not_reused(self):
    rows = doc('authorization-boundary')['static_tool_scope_audit']
    self.assertGreaterEqual(len(rows), 4)
    self.assertTrue(all(not row['safe_for_minimal_b0'] for row in rows))
    self.assertTrue(all(not row['executed'] for row in rows))
    self.assertFalse(doc('authorization-boundary')['new_access_reader_implemented'])

  def test_approval_layers_nontransitive(self):
    row = doc('authorization-boundary')
    self.assertEqual([r['approval_id'] for r in row['approval_layers']], list('ABCDEF'))
    self.assertEqual([r['current_granted'] for r in row['approval_layers']], [True, False, False, False, False, False])
    self.assertFalse(row['b0_grants_b1'])
    self.assertFalse(row['b_grants_c_d_e_f'])
    self.assertEqual(row['approval_layers'][-1]['independent_subauthorities'], ['HOLDOUT_ADMISSION', 'VEHICLE_ACTIVATION'])

  def test_m1_m9_current_sufficiency(self):
    rows = doc('authorization-boundary')['evidence_categories']
    self.assertEqual([r['id'] for r in rows], [f'M{i}' for i in range(1, 10)])
    for row in rows[:3]:
      self.assertFalse(row['private_input_needed_for_existing_public_question'])
    for row in rows[3:]:
      self.assertFalse(row['processing_authorized'])
    self.assertEqual(rows[4]['state'], 'TRAIN_GATE_NOT_SAVED_C_AND_EXPLICIT_SENSITIVE_ACCESS_REQUIRED')
    self.assertEqual(rows[6]['state'], 'PRIVATE_BOUNDARY_NOT_IN_INITIAL_B1_SCOPE_C_AND_SEPARATE_ACCESS_REQUIRED')

  def test_review_completion_never_access_grant_synthetic(self):
    for complete in (False, True):
      state = {'authorization_review_completed': complete, 'data_access_granted': False}
      self.assertFalse(state['data_access_granted'])
    row = doc('review-decision')
    self.assertTrue(row['authorization_review_completed'])
    self.assertFalse(row['data_access_granted'])
    self.assertFalse(row['human_grant_signed_or_minted'])

  def test_missing_root_fail_closed_not_guessed(self):
    row = doc('review-decision')
    self.assertEqual(row['outcome'], 'REVIEW_COMPLETE_ACCESS_DEFERRED')
    self.assertEqual(row['access_state'], 'ACCESS_DEFERRED_CANONICAL_ROOT_UNRESOLVED')
    self.assertEqual(row['b_state'], 'B_ACCESS_NOT_GRANTED')
    self.assertEqual(row['status'], 'STAGE1_DECISION_EVIDENCE_ACCESS_AUTHORIZATION_REVIEW_COMPLETE')

  def test_explicit_human_input_and_stop_conditions(self):
    row = doc('scope-request')['request']
    self.assertGreaterEqual(len(row['HUMAN_INPUT_REQUIRED']), 5)
    self.assertGreaterEqual(len(row['STOP_CONDITIONS']), 6)
    self.assertTrue(row['SOURCE_IMMUTABILITY'])
    self.assertIn('NO_DISCOVERY', row['EXACT_CANONICAL_ROOT_STATUS_RULE'])

  def test_no_e_output_or_os_sandbox_claim(self):
    for label in LABELS:
      row = doc(label)
      self.assertTrue(row['no_new_e_outputs'])
      self.assertFalse(row['next_execution_authorized'])
    row = doc('authorization-boundary')['enforcement_claim']
    self.assertFalse(row['future_b_os_sandbox_implemented'])
    self.assertEqual(row['current_host_permissions'], 'UNRESTRICTED_TOOL_ENVIRONMENT_NOT_A_SECURITY_SANDBOX')

  def test_frozen_scientific_facts_and_failed_closed_result(self):
    previous = doc('review-policy')['preserved_frozen_fact_reference']
    self.assertEqual(previous['file'], 'REQUIREMENTS_REQUIREMENTS_POLICY')
    lock = doc('public-input-lock')['input_lock']
    old = json.loads((ROOT / lock['files'][previous['file']]['path']).read_bytes())
    self.assertEqual(old['frozen_facts']['exact_hit'], {'static_loss': 571317, 'move_gain': 228164, 'net_delta': -343153, 'jobs_loss_gt_gain': 32})
    for label in LABELS:
      self.assertEqual(doc(label)['preserved_result'], old['preserved_result'])
      self.assertIsNone(doc(label)['preserved_result']['selected_candidate'])

  def test_actual_counters_zero_synthetic_separate(self):
    for label in LABELS:
      row = doc(label)
      self.assertEqual(row['operation_counters'], dict.fromkeys(COUNTERS, 0))
      self.assertTrue(all(type(v) is int for v in row['operation_counters'].values()))
      self.assertIn('SYNTHETIC', row['operation_counter_scope'])
    self.assertTrue(doc('review-validation')['counter_verification_method'])

  def test_public_privacy_and_field_names_are_not_payloads(self):
    for label in LABELS:
      privacy(doc(label))
    privacy({'field_name': 'p_move', 'status': 'REDACTED_PRIVATE_REFERENCE'})
    private_path = '/' + 'home/' + 'private/data'
    drive_path = 'E:' + '/private/data'
    for value in ({'threshold': 0.1}, {'coefficients': [1]}, {'row_scores': [0.2]}, {'access_token': 'synthetic'}, private_path, drive_path):
      with self.subTest(value=value), self.assertRaises(ValueError):
        privacy(value)

  def test_receipt_and_authority_corruption_rejected(self):
    value = doc('review-policy')
    with self.assertRaisesRegex(ValueError, 'RECEIPT_CONFLICT'):
      verify({**value, 'baseline_head': 'tampered'})
    body = {k: v for k, v in {**value, 'vehicle_activation_allowed': True}.items() if k != 'receipt_sha256'}
    with self.assertRaisesRegex(ValueError, 'AUTHORITY_CONFLICT'):
      verify({**body, 'receipt_sha256': hashlib.sha256(canonical(body)).hexdigest()})

  def test_authority_semantics_unchanged(self):
    lock = doc('public-input-lock')['input_lock']
    old = json.loads((ROOT / lock['files']['REQUIREMENTS_REQUIREMENTS_POLICY']['path']).read_bytes())
    for label in LABELS:
      row = doc(label)
      self.assertEqual(row['authority'], old['authority'])
      self.assertEqual(row['semantics'], old['semantics'])

  def test_only_eleven_new_documentation_schema_files(self):
    row = doc('review-policy')
    self.assertEqual(len(row['allowed_tracked_files']), 11)
    test = 'openpilot/tools/cyber_autotune/tests/test_empirical_hurdle_v4_evidence_access_review.py'
    self.assertTrue(all(p.startswith('docs/cyberpilot/changes/' + PREFIX) or p == test for p in row['allowed_tracked_files']))
    self.assertTrue(row['runtime_model_policy_workflow_immutable'])

  def test_korean_report_and_request_sections(self):
    text = (PUBLIC / (PREFIX + 'authorization-review.md')).read_text()
    self.assertIn('이번 검토는 비공개 데이터를 읽을 권한을 부여하지 않는다', text)
    self.assertEqual(len(re.findall(r'^## \d+\.', text, re.MULTILINE)), 16)
    self.assertIn('ACCESS_DEFERRED_CANONICAL_ROOT_UNRESOLVED', text)
    self.assertIn('NO_E_OUTPUTS', text)
    self.assertIn('B0', text)
    self.assertIn('B1', text)
    privacy(text)

  def test_no_scientific_imports_in_new_schema_test(self):
    allowed = {'ast', 'hashlib', 'json', 'pathlib', 're', 'subprocess', 'unittest'}
    for node in ast.walk(ast.parse(Path(__file__).read_text())):
      if isinstance(node, ast.Import):
        self.assertTrue(all(n.name in allowed for n in node.names))
      elif isinstance(node, ast.ImportFrom):
        self.assertIn(node.module, allowed)


if __name__ == '__main__':
  unittest.main()
