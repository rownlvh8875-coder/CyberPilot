"""Contract tests reject new execution authority even after an artifact is resealed."""

import copy
import importlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from openpilot.tools.cyber_autotune import empirical_plant_policy as p

MODULE = 'openpilot.tools.cyber_autotune.empirical_hurdle_design'


class TestHurdleDesign(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(importlib.util.find_spec(MODULE), 'Hurdle public-only design builder required')
    self.d = importlib.import_module(MODULE)
    self.bundle = self.d.build()

  def row(self, label):
    return self.bundle['empirical-hurdle-' + label + '-v1.json']

  def reject(self, label, field, value):
    bundle = copy.deepcopy(self.bundle)
    name = 'empirical-hurdle-' + label + '-v1.json'
    bundle[name][field] = value
    bundle[name] = p.seal({k: v for k, v in bundle[name].items() if k != 'receipt_sha256'})
    with self.assertRaisesRegex(ValueError, 'HURDLE_DESIGN_CONTRACT_DRIFT'):
      self.d.validate(bundle)

  def test_ready_is_design_only(self):
    self.assertEqual(self.row('design-readiness')['status'], 'HURDLE_FAMILY_DESIGN_READY_FOR_SEPARATE_FITTING_POLICY')
    self.assertEqual(self.row('design-readiness')['historical_verdict'], 'S2_RI_NO_ADMISSIBLE_CANDIDATE')
    self.assertEqual(len(self.bundle), 14)

  def test_target_is_exact_zero_nonzero(self):
    self.assertEqual(self.row('move-gate-target')['label'], {'operator': 'NOT_EQUAL', 'left': 'delta_tick[k]', 'right': 0, 'true': 1, 'false': 0})
    self.reject('move-gate-target', 'label', {'operator': 'ABS_GREATER_THAN', 'right': 1})

  def test_stage2_is_true_move_train_only(self):
    self.assertEqual(self.row('conditional-delta-target')['target'], 'delta_tick[k]')
    self.assertEqual(self.row('training-population')['stage2'], 'STAGE1_TRAIN_AND_TRUE_MOVE_LABEL_EQUALS_ONE')
    self.reject('training-population', 'stage2', 'ALL_WITH_STATIC_ZERO_TARGETS')

  def test_two_distinct_classes(self):
    stages = self.row('family-contract')['stages']
    self.assertEqual(
      [(s['id'], s['model_class']) for s in stages],
      [('HURDLE_MOVE_GATE_V1', 'BINARY_LOGISTIC_MOVE_GATE'), ('HURDLE_CONDITIONAL_DELTA_V1', 'CONDITIONAL_LINEAR_DELTA_REGRESSION')],
    )
    self.reject('family-contract', 'stages', stages + [stages[0]])

  def test_old_coefficients_not_reused(self):
    self.reject('conditional-delta-target', 'historical_coefficient_reuse', True)

  def test_exact_tied_structures(self):
    rows = self.row('structural-candidates')['configurations']
    ids = [f'HRI_D{d:02d}_L{length:02d}' for d in (0, 5, 10, 20) for length in (1, 5, 15, 45)]
    self.assertEqual([r['candidate_id'] for r in rows], ids)
    for row in rows:
      self.assertEqual(row['stage1_context'], row['stage2_context'])
      self.assertEqual(row['stage1_parameter_count'], {1: 5, 5: 13, 15: 33, 45: 93}[row['L']])
      self.assertEqual(row['total_nominal_parameters'], {1: 10, 5: 26, 15: 66, 45: 186}[row['L']])
    rows[0]['stage2_context']['d'] = 5
    self.reject('structural-candidates', 'configurations', rows)

  def test_no_candidate_expansion(self):
    rows = self.row('structural-candidates')['configurations']
    self.reject('structural-candidates', 'configurations', rows + [rows[0]])

  def test_chronological_feature_indexing(self):
    layouts = self.row('feature-contract')['layouts']
    self.assertEqual(layouts['HRI_D00_L01']['columns'], ['intercept', 'command_k_minus_0', 'delta_k_minus_1', 'angle_tick_k', 'speed_mps_k'])
    cols = layouts['HRI_D20_L45']['columns']
    self.assertEqual((cols[1], cols[45], cols[46], cols[90]), ('command_k_minus_64', 'command_k_minus_20', 'delta_k_minus_45', 'delta_k_minus_1'))
    self.assertEqual(len(cols), 93)

  def test_shared_feature_schema(self):
    for row in self.row('structural-candidates')['configurations']:
      self.assertEqual(row['stage1_feature_sha256'], row['stage2_feature_sha256'])

  def test_threshold_and_equality_unset(self):
    c = self.row('composition-contract')
    self.assertEqual(c['threshold'], 'UNSET')
    self.assertEqual(c['threshold_equality'], 'UNSET')
    self.reject('composition-contract', 'threshold', 0.5)

  def test_train_normalization_stage_specific(self):
    n = self.row('normalization-policy')
    self.assertEqual(n['stage1_population'], 'STAGE1_TRAIN_ALL_ELIGIBLE')
    self.assertEqual(n['stage2_population'], 'STAGE2_TRAIN_TRUE_MOVE_ONLY')
    self.reject('normalization-policy', 'statistics_source', 'DEVELOPMENT')

  def test_static_exact_hold_move_conditional(self):
    c = self.row('composition-contract')
    self.assertEqual(c['static_branch'], {'continuous_delta': 0.0, 'next_tick': 'CURRENT_PROJECTED_TICK', 'stage2_called': False, 'projection_called': False})
    self.assertEqual(c['move_branch']['stage2_called'], True)
    self.assertEqual(c['move_branch']['projection'], 'DIRECT_ROUND_HALF_TO_EVEN_TO_INTEGER_TICK')
    self.reject('composition-contract', 'hard_composition', False)

  def test_move_does_not_force_nonzero_projection(self):
    self.reject('composition-contract', 'forced_minimum_movement', True)

  def test_no_oracle_primary_branch(self):
    self.reject('composition-contract', 'branch_selector', 'TRUE_MOVE_LABEL')

  def test_recursive_uses_predicted_ticks(self):
    r = self.row('rollout-contract')
    self.assertEqual(r['horizons_steps'], [25, 50, 100, 200])
    self.assertEqual(r['stage1_calls'], 'EACH_RECURSIVE_STEP')
    self.assertEqual(r['stage2_calls'], 'PREDICTED_MOVE_BRANCH_ONLY')
    self.assertEqual(r['steering_state'], 'PROJECTED_INTEGER_TICK')
    self.reject('rollout-contract', 'future_measured_steering_feedback', True)

  def test_oracle_diagnostics_cannot_admit(self):
    self.reject('diagnostic-contract', 'oracle_admission', True)

  def test_historical_gate_not_inherited(self):
    self.assertEqual(self.row('future-fitting-requirements')['acceptance_policy'], 'REQUIRES_SEPARATE_PREDECLARATION')
    self.reject('future-fitting-requirements', 'inherit_s2_ri_gate', True)

  def test_stage2_support_is_deferred_not_measured(self):
    self.assertEqual(self.row('training-population')['stage2_support_floor_expression'], 'max(P,201)')
    self.assertEqual(self.row('training-population')['actual_support_counts'], 'NOT_COMPUTED')
    self.assertEqual(self.row('training-population')['support_comparison_rule'], 'DEFER_TO_PREDECLARED_FITTING_POLICY')

  def test_route_cv_exact_inversion(self):
    folds = self.row('training-population')['folds']
    self.assertEqual(folds[0]['train'], '7ae11bd92d924f7f4a319657595bfc9f60259f0a9b638327fd9ef6ad4edf2677')
    self.assertEqual(folds[0]['development'], '962f24485b27893e075f1a580f6e168a52f9a33dececfe4e82e1e2995c15c86c')
    self.assertEqual(folds[1]['train'], folds[0]['development'])
    self.assertEqual(folds[1]['development'], folds[0]['train'])

  def test_actual_public_trigger_and_horizon_evidence(self):
    e = self.row('design-evidence')
    self.assertEqual(e['pattern_jobs'], 32)
    self.assertEqual(e['one_step_outcome'], 'ZERO_STATIC_TRANSITION_TRADEOFF_STRICT')
    self.assertEqual(e['rollout_by_horizon']['100']['state_counts']['PATH_MOVED_SSE_IMPROVEMENT'], 17)

  def test_hash_drift_fails_before_json_interpretation(self):
    inputs = self.d.load_inputs()
    self.assertGreater(len(inputs), 10)
    with patch.object(Path, 'read_bytes', return_value=b'{}'):
      with self.assertRaisesRegex(ValueError, 'HURDLE_DESIGN_EVIDENCE_BINDING_CONFLICT'):
        self.d.load_inputs()

  def test_state_mismatch_fails_even_if_caller_supplies_public_dict(self):
    inputs = self.d.load_inputs()
    inputs['empirical-s2-ri-hurdle-design-trigger-v2.json']['pattern_jobs'] = 31
    with self.assertRaisesRegex(ValueError, 'HURDLE_DESIGN_EVIDENCE_BINDING_CONFLICT'):
      self.d.check_evidence(inputs)

  def test_unknown_artifact_and_missing_artifact_reject(self):
    for change in ('extra', 'missing'):
      b = copy.deepcopy(self.bundle)
      if change == 'extra':
        b['unknown.json'] = {}
      else:
        b.pop(next(iter(b)))
      with self.assertRaises(ValueError):
        self.d.validate(b)

  def test_deterministic_publication_and_resume(self):
    with tempfile.TemporaryDirectory() as tmp:
      path = Path(tmp)
      self.d.publish(path)
      before = {f.name: f.read_bytes() for f in path.iterdir()}
      self.d.publish(path)
      self.assertEqual(before, {f.name: f.read_bytes() for f in path.iterdir()})
      self.assertEqual(len(before), 14)

  def test_immutable_output_conflict_has_no_partial_publication(self):
    with tempfile.TemporaryDirectory() as tmp:
      path = Path(tmp)
      (path / 'empirical-hurdle-design-readiness-v1.json').write_text('{}')
      with self.assertRaises(ValueError):
        self.d.publish(path)
      self.assertEqual(len(list(path.iterdir())), 1)

  def test_symlink_and_traversal_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      (root / 'link').symlink_to(root, target_is_directory=True)
      for target in (root / 'link' / 'out', root / '..' / 'out'):
        with self.assertRaises(ValueError):
          self.d.publish(target)

  def test_generation_with_execution_and_array_loading_trapped(self):
    import builtins
    import numpy as np

    original_import = builtins.__import__
    original_read = Path.read_bytes
    allowed = {p.PUBLIC / n for n in self.d.PINS}
    allowed.update(Path(self.d.__file__).with_name(n) for n in self.d.SOURCES)

    def blocked(*args, **kwargs):
      raise AssertionError('HURDLE_DESIGN_EXECUTION_FORBIDDEN')

    def importing(name, *args, **kwargs):
      if name.startswith(('scipy', 'sklearn', 'openpilot.tools.lib.logreader')) or any(
        t in name for t in ('fit_cv_execution', 'reconstruction', 'attribution_v2_math')
      ):
        return blocked()
      return original_import(name, *args, **kwargs)

    def reading(path):
      if path not in allowed:
        return blocked()
      return original_read(path)

    with (
      patch.object(np.linalg, 'lstsq', blocked),
      patch.object(np.linalg, 'solve', blocked),
      patch.object(np.linalg, 'pinv', blocked),
      patch.object(np, 'load', blocked),
      patch.object(builtins, '__import__', importing),
      patch.object(Path, 'read_bytes', reading),
    ):
      self.assertEqual(self.d.validate(self.d.build()), self.bundle)

  def test_no_execution_api_is_exposed(self):
    for module in (self.d, self.d.c):
      for name in ('fit', 'predict', 'rollout', 'select', 'score', 'logistic_solver', 'threshold_optimizer', 'load_arrays'):
        self.assertFalse(hasattr(module, name), name)

  def test_all_execution_authorities_are_false(self):
    for value in self.bundle.values():
      self.assertTrue(value['authority'])
      self.assertTrue(all(v is False for v in value['authority'].values()))
    r = self.row('design-readiness')
    for key in (
      'model_fitting',
      'move_gate_fitting',
      'conditional_delta_fitting',
      'normalizer_fitting',
      'threshold_selection',
      'cv_scoring',
      'model_selection',
      'prediction',
      'rollout',
    ):
      self.assertEqual(r[key], 'NOT_RUN')

  def test_generation_import_graph_excludes_execution_modules(self):
    import ast

    allowed = {'argparse', 'json', 'pathlib'}
    local = {'empirical_plant_policy', 'empirical_hurdle_contracts'}
    for name in self.d.SOURCES:
      tree = ast.parse(Path(self.d.__file__).with_name(name).read_text())
      for node in ast.walk(tree):
        if isinstance(node, ast.Import):
          self.assertTrue(all(x.name in allowed for x in node.names))
        if isinstance(node, ast.ImportFrom):
          if node.module == 'openpilot.tools.cyber_autotune':
            self.assertTrue(all(x.name in local for x in node.names))
          else:
            self.assertIn(node.module, allowed)

  def test_public_output_contains_no_runtime_arrays_or_numerical_parameters(self):
    def walk(v):
      if isinstance(v, dict):
        for key, value in v.items():
          self.assertNotIn(key, ('coefficients', 'mean', 'std', 'predictions', 'targets', 'private_path', 'anchor_indices'))
          walk(value)
      elif isinstance(v, list):
        for item in v:
          walk(item)

    walk(self.bundle)

  def test_reference_pins_are_not_replaceable_by_resealing(self):
    inputs = self.d.load_inputs()
    name = 'empirical-s2-ri-hurdle-design-trigger-v2.json'
    row = inputs[name]
    row['pattern_jobs'] = 31
    inputs[name] = p.seal({k: v for k, v in row.items() if k != 'receipt_sha256'})
    with self.assertRaisesRegex(ValueError, 'HURDLE_DESIGN_EVIDENCE_BINDING_CONFLICT'):
      self.d.check_evidence(inputs)


# Each resealed mutation would silently add a forbidden degree of freedom without closed validation.
MUTATIONS = {
  'rate_feature': ('feature-contract', 'steering_rate_dependency', 'REQUIRED'),
  'request_feature': ('feature-contract', 'controller_request_feature', True),
  'raw_duplicate': ('feature-contract', 'raw_command_feature', True),
  'future_command': ('feature-contract', 'future_command_feature', True),
  'future_angle': ('feature-contract', 'future_angle_feature', True),
  'soft_blend': ('composition-contract', 'soft_blend', True),
  'debounce': ('composition-contract', 'debounce', True),
  'hysteresis': ('composition-contract', 'hysteresis', True),
  'class_weights': ('training-population', 'class_weighting', True),
  'oversampling': ('training-population', 'resampling', True),
  'stage2_weights': ('training-population', 'stage2_weighting', True),
  'pooled_normalizer': ('normalization-policy', 'statistics_source', 'POOLED'),
  'normalizer_share': ('normalization-policy', 'forced_shared_normalizer', True),
  'development_refit': ('normalization-policy', 'development_refit', True),
  'half_threshold_equality': ('composition-contract', 'threshold_equality', 'GREATER_OR_EQUAL'),
  'model_ready': ('design-readiness', 'status', 'HURDLE_MODEL_READY'),
  'model_fitting': ('design-readiness', 'model_fitting', 'RUN'),
  'private_arrays': ('design-readiness', 'private_arrays_opened', 1),
  'holdout': ('design-readiness', 'holdout_openings', 1),
  'vehicle': ('design-readiness', 'vehicle_authority', True),
  'gate_inherit': ('future-fitting-requirements', 'acceptance_policy', 'S2_RI_GATE_COPY'),
  'threshold_search': ('future-fitting-requirements', 'threshold_search_authorized', True),
}


def mutation_test(label, field, value):
  def test(self):
    self.reject(label, field, value)

  return test


for name, args in MUTATIONS.items():
  setattr(TestHurdleDesign, 'test_resealed_' + name + '_rejected', mutation_test(*args))

if __name__ == '__main__':
  unittest.main()
