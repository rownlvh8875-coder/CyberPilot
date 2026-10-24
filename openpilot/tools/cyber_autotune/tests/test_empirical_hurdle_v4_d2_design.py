"""Public-only D2 contracts and <=8-row invented arithmetic witnesses; no runner."""
import ast
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[4]
DOCS = ROOT / 'docs/cyberpilot/changes'
PREFIX = 'empirical-hurdle-stage1-v4-'
POLICY = PREFIX + 'd2-loss-aware-policy.json'
EVAL = PREFIX + 'd2-evaluation-contract.json'
BASE = 'f09caa202032c5d1f23c9d82a61589bcd8ed7137'


def load(name):
  return json.loads((DOCS / name).read_bytes())


def digest(body):
  return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def toy_project(c, u):
  if not math.isfinite(u) or not math.isfinite(c + u):
    raise ValueError('NONFINITE')
  value = round(c + u)
  if not -32768 <= value <= 32767:
    raise ValueError('SIGNED16_RANGE')
  return value


def toy_candidates(scores):
  # Hard bound prevents this test witness becoming a scientific data selector.
  if not 0 < len(scores) <= 8 or any(type(v) is not float or not math.isfinite(v) or not 0 <= v <= 1 for v in scores):
    raise ValueError('TINY_FLOAT64_FIXTURE_ONLY')
  return sorted({0.0, 1.0, *(0.0 if p == 0 else p for p in scores)})


def toy_tree(values):
  if not 0 < len(values) <= 8:
    raise ValueError('TINY_FIXTURE_ONLY')
  width = 1 << (len(values) - 1).bit_length()
  tree = [0.0] * (2 * width)
  tree[width:width + len(values)] = values
  for j in range(width - 1, 0, -1):
    tree[j] = tree[2 * j] + tree[2 * j + 1]
    if not math.isfinite(tree[j]):
      raise ValueError('NONFINITE_REDUCTION')
  return tree


def toy_losses(rows, gates):
  # rows=(score,current,target,signed_stage2_delta); arbitrary invented fixtures.
  if not 0 < len(rows) <= 8 or len(rows) != len(gates):
    raise ValueError('TINY_FIXTURE_ONLY')
  toy_candidates([r[0] for r in rows])
  if not any(t != c for _, c, t, _ in rows) or not any(t == c for _, c, t, _ in rows):
    raise ValueError('CLASS_MISSING')
  errors, abs_errors, true_sq, true_abs = [], [], [], []
  gain = tp = harm = hits = hold_hits = 0
  for (p, c, t, u), gate in zip(rows, gates, strict=True):
    del p
    move = toy_project(c, u)  # Validate even when this synthetic gate holds.
    predicted = move if gate else c
    e = (u if gate else 0.0) - float(t - c)
    sq = e * e
    if not math.isfinite(sq):
      raise ValueError('NONFINITE_LOSS')
    errors.append(sq)
    abs_errors.append(abs(e))
    true_sq.append(sq if t != c else 0.0)
    true_abs.append(abs(e) if t != c else 0.0)
    hits += int(predicted == t)
    hold_hits += int(c == t)
    gain += int(predicted == t) - int(c == t)
    tp += int(t != c and gate)
    harm += int(t == c and predicted != c)
  return {'gain': gain, 'tp': tp, 'harm': harm, 'hits': hits, 'hold_hits': hold_hits,
          'sse': toy_tree(errors)[1], 'sae': toy_tree(abs_errors)[1],
          'true_sse': toy_tree(true_sq)[1], 'true_sae': toy_tree(true_abs)[1]}


class TestD2PublicContract(unittest.TestCase):
  def test_design_files_exist(self):
    for name in (POLICY, EVAL, PREFIX + 'd2-design.md'):
      self.assertTrue((DOCS / name).is_file(), name)

  def test_canonical_receipts(self):
    for name in (POLICY, EVAL):
      body = load(name)
      receipt = body.pop('receipt_sha256')
      self.assertEqual(receipt, digest(body))

  def test_baseline_and_source_lock(self):
    p = load(POLICY)
    self.assertEqual(p['baseline_head'], BASE)
    self.assertEqual(p['original_execution_head'], 'bd8045ef2a0da62a92603439f38e7740f5923622')
    for entry in p['input_lock'] + p['source_lock']:
      path = ROOT / entry['path']
      self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry['raw_sha256'])
      if 'receipt_sha256' in entry:
        body = json.loads(path.read_bytes())
        self.assertEqual(body.pop('receipt_sha256'), entry['receipt_sha256'])
        self.assertEqual(digest(body), entry['receipt_sha256'])

  def test_exact_three_arms(self):
    p, e = load(POLICY), load(EVAL)
    self.assertEqual(list(p['policies']), ['D0', 'D1', 'D2'])
    self.assertEqual(e['policy_arms'], ['D0', 'D1', 'D2'])
    self.assertEqual(p['policies']['D2']['identity'], 'V4_TWO_CONTEXT_PROJECTED_TICK_LOSS_AWARE_TRAIN_DECISION')
    self.assertEqual(p['new_policy_families'], ['D2'])

  def test_D0_D1_unchanged(self):
    old = load(PREFIX + 'd-transition-aware-policy.json')
    for arm in ('D0', 'D1'):
      self.assertEqual(load(POLICY)['policies'][arm], old['policies'][arm])

  def test_exact_jobs(self):
    p = load(POLICY)
    self.assertEqual(p['jobs']['d'], [0, 5, 10, 20])
    self.assertEqual(p['jobs']['L'], [1, 5, 15, 45])
    self.assertEqual(p['jobs']['folds'], ['FOLD_A', 'FOLD_B'])
    self.assertEqual(p['jobs']['count'], 32)
    self.assertEqual(p['selection']['decisions_per_job'], 2)

  def test_strict_equality_and_context(self):
    s = load(POLICY)['selection']
    self.assertEqual(s['comparison'], 'score > decision')
    self.assertEqual(s['equality'], 'STATIC')
    self.assertEqual(s['contexts'], {'PREVIOUS_STATIC': 'raw_prior_delta_tick == 0', 'PREVIOUS_MOVE': 'raw_prior_delta_tick != 0'})
    self.assertFalse(0.5 > 0.5)

  def test_train_only(self):
    s = load(POLICY)['selection']
    self.assertEqual(s['role'], 'TRAIN')
    self.assertFalse(s['DEV_input_allowed'])
    self.assertTrue(s['seal_all_64_before_DEV'])
    self.assertEqual(s['row_order'], 'IMMUTABLE_ORIGINAL_TRAIN')

  def test_objectives_and_guards(self):
    p = load(POLICY)
    self.assertEqual(p['objective']['lexicographic'], [
      'MAX_NET_TICK_EXACT_HIT_GAIN', 'MIN_OVERALL_CONTINUOUS_SSE', 'MIN_OVERALL_CONTINUOUS_SAE',
      'MIN_HARMFUL_STATIC_REALIZATION', 'MAX_TRAIN_DECISION'])
    self.assertEqual([x['comparison'] for x in p['guards']], ['D2 >= D0', 'D2 <= D0', 'D2 <= D0', 'D2 <= D0'])
    self.assertEqual(p['selection']['float_tolerance'], 0)
    self.assertFalse(p['guards_are_DEV_acceptance'])

  def test_D0_reconstruction_is_new_and_separate(self):
    p = load(POLICY)['D0_reconstruction']
    self.assertEqual(p['historical_TRAIN_rowwise_gate'], 'NOT_SAVED')
    self.assertEqual(p['objective'], 'TP*N_negative + TN*P')
    self.assertEqual(p['ties'], ['MAX_TN', 'MAX_DECISION'])
    self.assertFalse(p['original_private_threshold_read_allowed'])
    self.assertFalse(p['original_threshold_byte_equality_claimed'])

  def test_fixed_tree_reduction_contract(self):
    n = load(POLICY)['numerics']
    self.assertEqual(n['reduction'], 'ORIGINAL_ROW_FIXED_BINARY_TREE')
    self.assertEqual(n['rounding'], 'IEEE754_BINARY64_ROUND_TO_NEAREST_TIES_EVEN_EACH_OPERATION_NO_FMA')
    self.assertFalse(n['subtractive_running_loss_sum'])
    self.assertEqual(n['loss_tree_channels'], ['overall_sse', 'overall_sae', 'true_move_sse', 'true_move_sae'])

  def test_bounded_algorithm(self):
    a = load(POLICY)['algorithm']
    self.assertEqual(a['time'], 'O(N log N)')
    self.assertEqual(a['memory'], 'O(N)')
    self.assertFalse(a['candidate_row_matrix_allowed'])
    self.assertTrue(a['group_equals_before_evaluation'])
    self.assertIn('128*N', a['tree_memory_bound'])

  def test_feasibility_preconditions(self):
    p = load(POLICY)['feasibility_proof']
    self.assertEqual(p['witness'], 'max({0} UNION {p_i in context : p_i <= D0_decision})')
    self.assertIn('ALL_ROW_POTENTIAL_OUTCOMES_VALID', p['preconditions'])
    self.assertIn('BOTH_CLASSES_IN_EACH_CONTEXT', p['preconditions'])
    self.assertFalse(p['invalid_outcome_may_be_skipped'])

  def test_invalid_input_fail_closed(self):
    p = load(POLICY)['failure_behavior']
    for key in ('missing_class', 'invalid_stage2_or_projection', 'identity_conflict', 'nonfinite_loss', 'empty_feasible_set'):
      self.assertIn('FAIL_CLOSED', p[key])
    self.assertFalse(p['repair_or_fallback_allowed'])

  def test_causal_routing(self):
    c = load(POLICY)['causal_state']
    self.assertEqual(c['one_step'], 'OBSERVED_RAW_PRIOR_DELTA')
    self.assertEqual(c['recursive'], 'REALIZED_PROJECTED_PRIOR_DELTA')
    self.assertFalse(c['future_truth_input'])
    self.assertFalse(c['gate_bit_as_realized_delta'])
    self.assertTrue(c['full_history_update'])

  def test_frozen_projection(self):
    p = load(POLICY)['projection']
    self.assertEqual(p['rounding'], 'TIES_TO_EVEN')
    self.assertEqual(p['range'], [-32768, 32767])
    self.assertFalse(p['clip_or_force_movement'])
    self.assertEqual(p['range_validation'], 'AFTER_ROUNDING')

  def test_requirement_traceability(self):
    p = load(POLICY)
    old = load(PREFIX + 'decision-policy-requirements-spec.json')['requirements']
    self.assertEqual([x['requirement_id'] for x in p['requirements_traceability']], [x['requirement_id'] for x in old])
    for item in p['requirements_traceability']:
      self.assertTrue(item['design_pointers'])
      self.assertTrue(item['evaluation_domains'])
      self.assertEqual(item['status'], 'DESIGN_TRACEABLE_NOT_EMPIRICAL_COMPLIANCE')
      for ptr in item['design_pointers']:
        value = p
        for part in ptr.lstrip('/').split('/'):
          value = value[part]
        self.assertIsNotNone(value)

  def test_all_22_domains_preserved(self):
    old = load(PREFIX + 'd-offline-evaluation-contract.json')['validation_domains']
    e = load(EVAL)
    self.assertEqual(len(e['validation_domains']), 22)
    for new, previous in zip(e['validation_domains'], old, strict=True):
      for field in ('order', 'source_pointer', 'verification', 'failure_behavior'):
        self.assertEqual(new[field], previous[field])
      self.assertTrue(new['D2_addendum'])

  def test_acceptance_unchanged(self):
    old = load(PREFIX + 'd-offline-evaluation-contract.json')['acceptance']
    self.assertEqual(load(EVAL)['acceptance'], old)
    self.assertEqual(old['clause_count'], 32)
    self.assertEqual(old['epsilon'], 0)
    self.assertEqual(old['raw_sha256'], '606d5d3f46677d0107298f8b94e0a6d5a73da62f01db0164c4812a9fa2cccee1')

  def test_full_horizons_and_folds(self):
    e = load(EVAL)
    self.assertEqual(e['rollout']['horizons'], [25, 50, 100, 200])
    self.assertEqual(e['rollout']['populations'], ['OVERALL', 'PATH_MOVED'])
    self.assertTrue(e['rollout']['both_folds_required'])
    self.assertEqual(e['rollout']['PATH_MOVED'], 'OBSERVED_PATH_DIFFERS_FROM_INITIAL_AT_ANY_STEP')

  def test_inputs_not_yet_verified(self):
    e = load(EVAL)
    self.assertEqual(e['input_status'], 'E2_TRAIN_COUNTERFACTUAL_INPUT_NOT_YET_VERIFIED')
    self.assertFalse(e['private_access_granted'])
    self.assertFalse(e['E2_execution_authorized'])
    self.assertEqual(len(e['additional_TRAIN_inputs']), 8)
    for x in e['additional_TRAIN_inputs']:
      self.assertIn('source', x)
      self.assertIn('future_verification', x)
      self.assertEqual(x['live_status'], 'NOT_OPENED_NOT_VERIFIED_IN_D2')

  def test_explicit_future_authorization(self):
    e = load(EVAL)
    self.assertIn('ALL_TRAIN_STAGE2_POTENTIAL_OUTCOMES_INCLUDING_STATIC', e['future_grant_operations'])
    self.assertIn('D0_TRAIN_GATE_RECONSTRUCTION', e['future_grant_operations'])
    self.assertIn('64_D2_TRAIN_DECISIONS', e['future_grant_operations'])
    self.assertFalse(e['automatic_adoption'])

  def test_repeats_and_resume(self):
    r = load(EVAL)['repeats']
    self.assertEqual(r['independent_full_runs'], 2)
    self.assertTrue(r['canonical_payload_byte_exact'])
    self.assertEqual(r['verify_only'], {'source_rereads': 0, 'inference_calls': 0, 'recompute_calls': 0, 'source_writes': 0})

  def test_joint_privacy(self):
    p = load(EVAL)['publication']
    self.assertEqual(p['minimum_support'], 201)
    self.assertEqual(p['joint_arms'], ['D0', 'D1', 'D2'])
    self.assertTrue(p['historical_C_E_complementary_suppression'])
    self.assertFalse(p['gate_dependent_invocation_counts_public'])
    self.assertEqual(p['onset_continuation_details'], 'INHERITED_SUPPRESSION_NOT_BYPASSED')

  def test_no_private_or_scientific_operations(self):
    p = load(POLICY)
    self.assertTrue(all(v == 0 for v in p['actual_private_operation_counters'].values()))
    self.assertEqual(len(p['actual_private_operation_counters']), 23)
    self.assertEqual(p['scope'], 'DESIGN_ONLY_PUBLIC_EVIDENCE_SYNTHETIC_CONTRACTS')
    self.assertFalse(p['E2_granted'])

  def test_no_production_runner_or_import(self):
    tree = ast.parse(Path(__file__).read_text())
    imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    self.assertFalse(any('empirical_' in ast.unparse(n) for n in imports))
    self.assertFalse((ROOT / 'openpilot/tools/cyber_autotune/empirical_hurdle_v4_d2_evaluation.py').exists())
    for node in ast.walk(tree):
      if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == 'walk' and isinstance(node.func.value, ast.Name) and node.func.value.id == 'ast':
          continue
        self.assertNotIn(node.func.attr, ('glob', 'rglob', 'walk', 'iterdir'))

  def test_public_artifacts_no_private_paths_or_values(self):
    for name in (POLICY, EVAL, PREFIX + 'd2-design.md'):
      text = (DOCS / name).read_text()
      self.assertNotRegex(text, r'/home/[^\s<>\"/]+/')
      for forbidden in ('/mnt/e/', '/mnt/d/', 'E:\\', 'decision_previous_static_value', 'decision_previous_move_value'):
        self.assertNotIn(forbidden, text)

  def test_closed_authority(self):
    p = load(POLICY)['preserved']
    self.assertIsNone(p['selected_candidate'])
    self.assertEqual(p['holdout'], 'CLOSED')
    self.assertEqual(p['vehicle_authority'], 'NONE')
    self.assertEqual(p['D2'], 'DESIGN_ONLY_NOT_EVALUATED')
    self.assertEqual(p['Hugging_Face'], 'NOT_REQUIRED / NOT_USED')

  def test_observed_E_not_causal_or_efficacy_claim(self):
    p = load(POLICY)['evidence_interpretation']
    self.assertEqual(p['D1_status'], 'E_EXECUTION_COMPLETE_D1_NOT_ADMISSIBLE')
    self.assertFalse(p['D2_improvement_proven'])
    self.assertFalse(p['Stage2_causal_share_identified'])
    self.assertEqual(p['future_E2_validation'], 'EXPLORATORY_RETROSPECTIVE_NOT_BLINDED')


class TestD2SyntheticWitnesses(unittest.TestCase):
  def test_D0_gate_representable_in_every_context(self):
    scores = [-0.0, 0.0, 0.2, 0.2, 0.7, 1.0]
    for mask in itertools.product((False, True), repeat=len(scores)):
      context = [p for p, keep in zip(scores, mask, strict=True) if keep]
      if not context:
        continue
      for original in toy_candidates(scores) + [0.1, 0.5, 0.9]:
        witness = max([0.0] + [p for p in context if p <= original])
        self.assertIn(witness, toy_candidates(context))
        self.assertEqual([p > original for p in context], [p > witness for p in context])

  def test_duplicate_zero_and_endpoint_candidates(self):
    self.assertEqual(toy_candidates([-0.0, 0.0, 0.5, 0.5, 1.0]), [0.0, 0.5, 1.0])
    self.assertEqual(struct.pack('d', toy_candidates([-0.0])[0]), struct.pack('d', 0.0))

  def test_invalid_scores_rejected(self):
    for bad in (float('nan'), float('inf'), -0.1, 1.1, 1):
      with self.subTest(bad=bad), self.assertRaises(ValueError):
        toy_candidates([bad])

  def test_no_class_support_rejected(self):
    for target in (0, 1):
      with self.assertRaisesRegex(ValueError, 'CLASS_MISSING'):
        toy_losses([(0.5, 0, target, 0.0)], [False])

  def test_ties_to_even(self):
    self.assertEqual([toy_project(0, v) for v in (-2.5, -1.5, 0.5, 1.5, 2.5)], [-2, -2, 0, 2, 2])

  def test_range_checked_after_round(self):
    self.assertEqual(toy_project(32767, 0.4), 32767)
    with self.assertRaises(ValueError):
      toy_project(32767, 0.5)

  def test_stage2_nonfinite_rejected(self):
    for value in (float('nan'), float('inf')):
      with self.assertRaises(ValueError):
        toy_project(0, value)

  def test_invalid_move_on_held_row_still_fails(self):
    with self.assertRaisesRegex(ValueError, 'SIGNED16_RANGE'):
      toy_losses([(0.1, 32767, 32767, 1.0), (0.9, 0, 1, 1.0)], [False, True])

  def test_gate_move_projected_hold_and_harm(self):
    rows = [(0.5, 0, 0, 0.4), (0.9, 0, 1, 1.0)]
    result = toy_losses(rows, [True, True])
    self.assertEqual(result['harm'], 0)
    self.assertEqual(result['hits'], 2)
    self.assertGreater(result['sse'], 0.0)
    rows[0] = (0.5, 0, 0, 0.6)
    self.assertEqual(toy_losses(rows, [True, True])['harm'], 1)

  def test_exact_hit_gain_identity(self):
    rows = [(0.2, 0, 0, 1.0), (0.7, 0, 1, 1.0)]
    for gates in itertools.product((False, True), repeat=2):
      r = toy_losses(rows, gates)
      self.assertEqual(r['hits'], r['hold_hits'] + r['gain'])
      loss = int(gates[0])
      gain = int(gates[1])
      self.assertEqual(r['gain'], gain - loss)

  def test_true_move_uses_continuous_not_quantized_error(self):
    r = toy_losses([(0.2, 0, 0, 0.0), (0.8, 0, 1, 0.6)], [False, True])
    self.assertEqual(r['hits'], 2)
    self.assertAlmostEqual(r['true_sse'], 0.16)
    self.assertAlmostEqual(r['true_sae'], 0.4)

  def test_D0_witness_guards_equal(self):
    rows = [(0.1, 0, 0, 1.0), (0.8, 0, 1, 0.6), (0.8, 2, 1, -1.0)]
    original = 0.5
    witness = max([0.0] + [r[0] for r in rows if r[0] <= original])
    a = toy_losses(rows, [r[0] > original for r in rows])
    b = toy_losses(rows, [r[0] > witness for r in rows])
    self.assertEqual(a, b)
    self.assertTrue(b['tp'] >= a['tp'] and b['true_sse'] <= a['true_sse'] and b['true_sae'] <= a['true_sae'] and b['harm'] <= a['harm'])

  def test_fixed_tree_update_is_history_independent(self):
    initial = [1e16, 1.0, 1.0, 1.0, 0.0]
    changed = [0.0, 1.0, 1.0, 1.0, 0.0]
    tree = toy_tree(initial)
    width = len(tree) // 2
    tree[width] = 0.0
    j = width // 2
    while j:
      tree[j] = tree[2*j] + tree[2*j+1]
      j //= 2
    self.assertEqual(tree, toy_tree(changed))
    self.assertEqual(tree[1], 3.0)
    self.assertNotEqual(toy_tree(initial)[1] - 1e16, tree[1])

  def test_exact_count_and_lexicographic_tie(self):
    huge = 2**70
    self.assertGreater(huge + 1, huge)
    keys = [(1, -2.0, -1.0, -1, 0.1), (1, -2.0, -1.0, -1, 0.7)]
    self.assertEqual(max(keys)[-1], 0.7)
    self.assertGreater((1, -100.0, -100.0, -100, 0.0), (0, 0.0, 0.0, 0, 1.0))

  def test_context_is_realized_delta_not_gate(self):
    previous, current = 0, toy_project(0, 0.4)
    gate_move = True
    self.assertTrue(gate_move)
    self.assertEqual(current - previous, 0)
    self.assertFalse(current - previous != 0)

  def test_truth_does_not_change_routing(self):
    current, prior = 4, 4
    contexts = [current - prior != 0 for _future in (-10, 4, 100)]
    self.assertEqual(contexts, [False, False, False])

  def test_feasible_lexicographic_choice_protects_D0(self):
    rows = [(0.1, 0, 0, 0.6), (0.3, 0, 0, 0.4), (0.7, 0, 1, 0.6), (0.9, 1, 2, 1.0)]
    baseline = toy_losses(rows, [r[0] > 0.5 for r in rows])
    feasible = []
    for decision in toy_candidates([r[0] for r in rows]):
      v = toy_losses(rows, [r[0] > decision for r in rows])
      if v['tp'] >= baseline['tp'] and v['true_sse'] <= baseline['true_sse'] and v['true_sae'] <= baseline['true_sae'] and v['harm'] <= baseline['harm']:
        feasible.append((v['gain'], -v['sse'], -v['sae'], -v['harm'], decision))
    self.assertTrue(feasible)
    selected = max(feasible)
    self.assertGreaterEqual(selected[0], baseline['gain'])
    self.assertEqual(selected[-1], 0.3)

  def test_full_equal_score_group_removed_before_evaluation(self):
    scores = [0.0, 0.5, 0.5, 1.0]
    for decision in toy_candidates(scores):
      group_gate = [True] * len(scores)
      for score, row in sorted((p, i) for i, p in enumerate(scores)):
        if score <= decision:
          group_gate[row] = False
      self.assertEqual(group_gate, [p > decision for p in scores])
    self.assertEqual([p > 0.5 for p in scores], [False, False, False, True])

  def test_leaf_update_order_does_not_change_bits(self):
    final = [0.1, 1e16, 0.2, 1.0, 0.3]
    for order in ((0, 1, 2, 3, 4), (4, 3, 2, 1, 0)):
      tree = toy_tree([0.0]*5)
      width = len(tree)//2
      for row in order:
        tree[width+row] = final[row]
        j = (width+row)//2
        while j:
          tree[j] = tree[2*j] + tree[2*j+1]
          j //= 2
      self.assertEqual(struct.pack('d', tree[1]), struct.pack('d', toy_tree(final)[1]))

  def test_nonfinite_reduction_rejected(self):
    with self.assertRaisesRegex(ValueError, 'NONFINITE_REDUCTION'):
      toy_tree([1e308, 1e308])

  def test_four_truth_states_are_post_observation_only(self):
    states = {(False, False): 'STATIC_HOLD', (False, True): 'MOVE_ONSET',
              (True, False): 'MOVE_TERMINATION', (True, True): 'MOVE_CONTINUATION'}
    self.assertEqual(len(states), 4)
    self.assertEqual(states[(True, False)], 'MOVE_TERMINATION')
    # Prior context is identical for both future outcomes.
    self.assertEqual([z for z, y in states if z], [True, True])

  def test_tiny_oracle_refuses_scientific_scale(self):
    with self.assertRaises(ValueError):
      toy_candidates([0.5]*9)


if __name__ == '__main__':
  unittest.main()
