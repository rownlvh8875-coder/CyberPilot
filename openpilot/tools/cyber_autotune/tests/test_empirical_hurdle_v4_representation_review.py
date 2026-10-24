"""Architecture algebra and synthetic witnesses only; no coefficient fitting."""

import unittest
from unittest.mock import patch

import numpy as np


class TestRepresentation(unittest.TestCase):
  def module(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_representation_review as r
    return r

  def test_all_source_dimensions_and_order(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as old
    r = self.module()
    k = np.arange(400, dtype=np.int64)
    data = {'tick': k * k % 101, 'command': (k % 17) / 17., 'speed': 10. + k % 7, 'streak': k + 1}
    for candidate in old.CANDIDATES:
      d, length = old.parameters(candidate)
      x = old.features(data, np.array([100, 101]), candidate)
      self.assertEqual(x.shape[1], r.counts(candidate)['P'])
      self.assertEqual(len(r.feature_names(candidate)), 2 * length + 3)
      np.testing.assert_array_equal(x[:, 1:length + 1], data['command'][np.array([100, 101])[:, None] - np.arange(d + length - 1, d - 1, -1)])
      np.testing.assert_array_equal(x[:, 2 * length], data['tick'][[100, 101]] - data['tick'][[99, 100]])
      self.assertEqual(x.dtype, np.float64)
      self.assertTrue(x.flags.c_contiguous)

  def test_future_truth_not_in_features_or_context(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as old
    r = self.module()
    k = np.arange(300, dtype=np.int64)
    data = {'tick': k % 13, 'command': (k % 7) / 7., 'speed': 10. + k % 3, 'streak': k + 1}
    for candidate in old.CANDIDATES:
      before = old.features(data, np.array([100]), candidate)
      changed = {name: a.copy() for name, a in data.items()}
      changed['tick'][101:] = -999
      changed['command'][101:] = .99
      changed['speed'][101:] = 99
      after = old.features(changed, np.array([100]), candidate)
      np.testing.assert_array_equal(before, after)
      np.testing.assert_array_equal(r.context(before, scope=r.SCOPE), r.context(after, scope=r.SCOPE))

  def test_raw_context_before_normalization(self):
    r = self.module()
    x = np.array([[1., 0., 0., 0., 10.], [1., 0., 1., 0., 10.]])
    np.testing.assert_array_equal(r.context(x, scope=r.SCOPE), [0, 1])
    centered_delta = x[:, 2] - .5
    self.assertEqual((centered_delta != 0).tolist(), [True, True])

  def test_state_intercept_two_threshold_equivalence(self):
    r = self.module()
    w = r.witnesses()['state_intercept']
    self.assertEqual(w['transformed_decisions'], w['equivalent_logit_cut_decisions'])
    self.assertEqual(w['within_state_order_preserved'], True)

  def test_positive_affine_preserves_order_negative_reverses(self):
    w = self.module().witnesses()['state_affine']
    self.assertEqual(w['positive_order'], w['old_order'])
    self.assertEqual(w['negative_order'], list(reversed(w['old_order'])))
    self.assertFalse(w['negative_slope_usefulness_established'])

  def test_dual_head_changes_within_state_order(self):
    w = self.module().witnesses()['dual_head']
    self.assertLess(w['old_logits'][2], w['old_logits'][3])
    self.assertGreater(w['new_logits'][2], w['new_logits'][3])

  def test_dual_head_strictly_new_global_affine_class(self):
    w = self.module().witnesses()['dual_head']
    self.assertEqual(w['static_command_contrast'], 2.)
    self.assertEqual(w['move_command_contrast'], -2.)
    self.assertNotEqual(w['static_command_contrast'], w['move_command_contrast'])

  def test_quadratic_changes_within_state_order(self):
    w = self.module().witnesses()['quadratic']
    self.assertLess(w['old_logits'][0], w['old_logits'][2])
    self.assertGreater(w['new_logits'][0], w['new_logits'][2])

  def test_mlp_nonmonotonic_witness_not_a_width_choice(self):
    w = self.module().witnesses()['mlp']
    self.assertEqual(w['new_logits'], [1., 0., .5])
    self.assertEqual(w['illustrative_hidden_width'], 2)
    self.assertFalse(w['actual_width_selected'])

  def test_exact_parameter_counts(self):
    r = self.module()
    for length, p, dual, effective, quad in ((1, 5, 10, 9, 15), (5, 13, 26, 25, 91),
                                           (15, 33, 66, 65, 561), (45, 93, 186, 185, 4371)):
      for d in (0, 5, 10, 20):
        row = r.counts(f'HRI_D{d:02d}_L{length:02d}')
        self.assertEqual((row['P'], row['dual_nominal'], row['dual_generic_identifiable_upper'], row['quadratic_total']),
                         (p, dual, effective, quad))
        self.assertEqual(row['quadratic_new_products'], quad - p)

  def test_mlp_symbolic_counts_exclude_input_intercept(self):
    r = self.module()
    for p in (5, 13, 33, 93):
      for h in (1, 2, 7):
        row = r.mlp_counts(p, h)
        self.assertEqual(row['global'], h * (p - 1) + h + h + 1)
        self.assertEqual(row['state_concat'], h * p + h + h + 1)
        self.assertEqual(row['dual_heads'], 2 * row['global'])

  def test_polynomial_basis_no_duplicate_intercept_products(self):
    r = self.module()
    x = np.array([[1., 2., 0., 3., 10.]])
    basis = r.quadratic_basis(x, scope=r.SCOPE)
    self.assertEqual(basis.shape, (1, 15))
    np.testing.assert_array_equal(basis[0, :5], x[0])
    self.assertEqual(basis[0, 5:].tolist(), [4., 0., 6., 20., 0., 0., 0., 9., 30., 100.])

  def test_structural_null_column_and_generic_rank(self):
    r = self.module()
    x = r.rank_fixture()
    z = r.context(x, scope=r.SCOPE)
    block = r.block_design(x, scope=r.SCOPE)
    self.assertTrue(np.all(block[:, 2] == 0))
    self.assertEqual(np.linalg.matrix_rank(x[z == 0]), 4)
    self.assertEqual(np.linalg.matrix_rank(x[z == 1]), 5)
    self.assertEqual(np.linalg.matrix_rank(block), 9)
    np.testing.assert_array_equal(x[:, 2], (z[:, None] * x)[:, 2])

  def test_shared_centering_preserves_static_collinearity(self):
    r = self.module()
    x = r.rank_fixture()
    z = r.context(x, scope=r.SCOPE)
    transformed = x.copy()
    transformed[:, 2] -= .5  # Declared coordinate change, not fitted normalization.
    block = np.column_stack(((1 - z[:, None]) * transformed, z[:, None] * transformed))
    np.testing.assert_array_equal(block[:, 2], -.5 * block[:, 0])
    self.assertEqual(np.linalg.matrix_rank(block), 9)

  def test_block_and_base_delta_logits(self):
    r = self.module()
    w = r.witnesses()['training_algebra']
    self.assertEqual(w['head_logits'], w['block_logits'])
    self.assertEqual(w['head_logits'], w['base_delta_logits'])
    self.assertTrue(w['sum_hessian_off_block_zero'])
    self.assertFalse(w['optimizer_byte_equivalence_claim'])

  def test_original_row_loss_preserved_not_context_sum_identity(self):
    w = self.module().witnesses()['training_algebra']
    self.assertEqual(w['head_per_row_nll'], w['block_per_row_nll'])
    self.assertEqual(w['head_original_order_sum'], w['block_original_order_sum'])
    self.assertFalse(w['context_float_subtotals_assumed_equal'])

  def test_mean_gradient_stopping_not_equivalent(self):
    w = self.module().witnesses()['mean_stopping']
    self.assertGreater(w['local_gradient'], w['current_tolerance'])
    self.assertLess(w['joint_mean_scaled_gradient'], w['current_tolerance'])

  def test_full_rank_two_classes_not_finite_mle_certificate(self):
    w = self.module().witnesses()['separation']
    self.assertEqual(w['design_rank'], 2)
    self.assertEqual(w['class_counts'], [201, 201])
    self.assertFalse(w['finite_mle_exists'])
    self.assertLess(w['illustrative_gradient_magnitude'], w['current_tolerance'])
    self.assertFalse(w['fit_executed'])

  def test_boundary_and_projected_context_contract(self):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_state_contract import Frame, ProjectedContext
    a = Frame('R', 'S', 'RUN', 0, 0, 0, True, 1)
    b = Frame('R', 'S', 'RUN', 1, 1, 10_000_000, True, 2)
    s = ProjectedContext(previous=a, current=b, previous_tick=-1, current_tick=0, scope='SYNTHETIC_ONLY')
    self.assertEqual(s.context(), 1)
    self.assertEqual(s.advance(projected_tick=0, provenance='PROJECTED_INFERENCE'), 0)
    s.boundary('SEGMENT')
    with self.assertRaises(ValueError):
      s.context()
    with self.assertRaises(ValueError):
      s.advance(projected_tick=1, provenance='FUTURE_MEASURED')

  def test_synthetic_scope_and_nonfinite_reject(self):
    r = self.module()
    for scope in ('PRIVATE', 'DEVELOPMENT', 'HOLDOUT'):
      with self.assertRaises(ValueError):
        r.context(r.rank_fixture(), scope=scope)
    x = r.rank_fixture()
    x[0, 1] = 1e308
    with self.assertRaises(ValueError):
      r.quadratic_basis(x, scope=r.SCOPE)
    x[0, 1] = np.nan
    with self.assertRaises(ValueError):
      r.context(x, scope=r.SCOPE)

  def test_no_fit_prediction_threshold_private_or_hf_calls(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as old
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_two_context_exact as exact
    with patch('numpy.load', side_effect=AssertionError('private/HOLDOUT')), \
         patch('numpy.linalg.solve', side_effect=AssertionError('optimizer')), \
         patch('numpy.linalg.lstsq', side_effect=AssertionError('optimizer')), \
         patch.object(old, 'fit_stage1', side_effect=AssertionError('fit')), \
         patch.object(old, 'fit_stage2', side_effect=AssertionError('fit')), \
         patch.object(old, 'normalizer', side_effect=AssertionError('normalizer fit')), \
         patch.object(old, 'probability', side_effect=AssertionError('real prediction')), \
         patch.object(old, 'threshold', side_effect=AssertionError('threshold')), \
         patch.object(old, 'recursive', side_effect=AssertionError('rollout')), \
         patch.object(exact, 'fit', side_effect=AssertionError('threshold pair')):
      self.module().witnesses()


class TestArchitectureDecision(unittest.TestCase):
  def test_unique_eligible_minimum(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_representation_review as r
    options = r.options()
    got = r.select(options)
    self.assertEqual(got['selected_option'], 'C')
    self.assertEqual(got['status'], 'STAGE1_V4_REPRESENTATION_ARCHITECTURE_SELECTED')

  def test_inconclusive_when_minimum_not_unique(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_representation_review as r
    options = [dict(r.options()[2]), dict(r.options()[2])]
    options[1]['id'] = 'OTHER'
    self.assertEqual(r.select(options)['status'], 'STAGE1_V4_REPRESENTATION_REVIEW_INCONCLUSIVE')

  def test_negative_control_cannot_win_by_small_count(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_representation_review as r
    self.assertIsNone(r.select(r.options()[:2])['selected_option'])

  def test_unknown_eligibility_not_pass(self):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_representation_review as r
    option = dict(r.options()[2])
    option['eligibility'] = (None,) + option['eligibility'][1:]
    self.assertIsNone(r.select([option])['selected_option'])


class TestPublicRepresentation(unittest.TestCase):
  def test_input_file_and_receipt_lock_mutation(self):
    from tools.cyberpilot.build_hurdle_v4_representation_review import locked_inputs, PINS
    self.assertEqual(len(locked_inputs()), 20)
    key = next(iter(PINS))
    with patch.dict(PINS, {key: ('0' * 64, PINS[key][1])}), self.assertRaisesRegex(ValueError, 'INPUT_CONFLICT'):
      locked_inputs()

  def test_source_lock_mutation(self):
    from tools.cyberpilot.build_hurdle_v4_representation_review import locked_inputs, SOURCE_PINS
    key = next(iter(SOURCE_PINS))
    with patch.dict(SOURCE_PINS, {key: '0' * 64}), self.assertRaisesRegex(ValueError, 'INPUT_CONFLICT'):
      locked_inputs()

  def test_fourteen_public_artifacts_exact(self):
    import json
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    from tools.cyberpilot.build_hurdle_v4_representation_review import build
    for name, row in build().items():
      self.assertEqual(p.verify(row), json.loads((p.PUBLIC / name).read_bytes()))
      self.assertEqual(row['private_numeric_array_opens'], 0)
      self.assertFalse(row['actual_execution_authorized'])
      self.assertFalse(row['fitting_policy_frozen'])
      self.assertEqual(set(row['v4'].values()), {'NOT_RUN'})
    self.assertEqual(len(build()), 14)

  def test_architecture_not_fitting_or_registry_authority(self):
    from tools.cyberpilot.build_hurdle_v4_representation_review import build, PREFIX
    rows = build()
    contract = rows[PREFIX + 'representation-design-contract.json']
    self.assertFalse(contract['coefficient_generation_authorized'])
    self.assertEqual(contract['normalization'], 'FITTING_POLICY_UNRESOLVED')
    self.assertEqual(contract['support_minimum'], 'FITTING_POLICY_UNRESOLVED_NO_SILENT_201_PER_HEAD')
    self.assertEqual(contract['hugging_face'], {'setup': 'NOT_RUN', 'login': 'NOT_RUN', 'repo': 'NOT_CREATED', 'upload': 0, 'download': 0})
    self.assertEqual(contract['holdout'], 'CLOSED')
    self.assertEqual(contract['vehicle_authority'], 'NONE')
    self.assertIn('GRID', contract['boundaries'])
    self.assertIn('SOURCE_AND_WITHIN_CAUSAL_RUN_INDICES_PLUS_1', contract['predecessor_admission'])
    self.assertIn('PENULTIMATE[-2]', contract['initial_history_array_indices'])
    self.assertIn('TRAIN_TARGET_y_LABEL_ALLOWED', contract['future_truth_use'])

  def test_privacy_no_private_paths_actual_scores_or_weights(self):
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    from tools.cyberpilot.build_hurdle_v4_representation_review import build
    data = p.canonical(build()).decode()
    for forbidden in ('/mnt/e/', '/mnt/d/', 'D:\\', 'E:\\', 'actual_threshold_value', 'normalizer_values', 'actual_coefficients'):
      self.assertNotIn(forbidden, data)

  def test_math_has_no_io_fitting_or_network_api(self):
    import ast
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / 'empirical_hurdle_v4_representation_review.py'
    tree = ast.parse(path.read_text())
    forbidden = {'open', 'read_bytes', 'read_text', 'load', 'fit', 'exhaustive', 'probability', 'normalizer', 'recursive',
                 'fit_stage1', 'fit_stage2', 'lstsq', 'solve', 'threshold', 'requests', 'urlopen', 'huggingface_hub'}
    calls = {n.func.id if isinstance(n.func, ast.Name) else n.func.attr for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, (ast.Name, ast.Attribute))}
    self.assertFalse(calls & forbidden)


if __name__ == '__main__':
  unittest.main()
