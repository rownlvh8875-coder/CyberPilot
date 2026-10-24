"""Policy consumer boundaries; deliberately never execute fitting or selection."""
import copy
import importlib
import unittest

from openpilot.tools.cyber_autotune import empirical_plant_policy as p


def api():
  return importlib.import_module('openpilot.tools.cyber_autotune.empirical_s2_ri_fitting_policy')


def item(bundle, name):
  return bundle['empirical-s2-ri-'+name+'-v1.json']


class TestS2RIFittingPolicy(unittest.TestCase):
  def test_exact_candidate_ids_and_counts(self):
    b = api().build()
    rows = item(b, 'candidate-set')['candidates']
    self.assertEqual([r['candidate_id'] for r in rows], [
      'S2RI_D00_L01', 'S2RI_D00_L05', 'S2RI_D00_L15', 'S2RI_D00_L45',
      'S2RI_D05_L01', 'S2RI_D05_L05', 'S2RI_D05_L15', 'S2RI_D05_L45',
      'S2RI_D10_L01', 'S2RI_D10_L05', 'S2RI_D10_L15', 'S2RI_D10_L45',
      'S2RI_D20_L01', 'S2RI_D20_L05', 'S2RI_D20_L15', 'S2RI_D20_L45'])
    self.assertEqual([r['parameter_count'] for r in rows], [5, 13, 33, 93]*4)
    for r in rows:
      self.assertEqual(r['Lu'], r['L'])
      self.assertEqual(r['Ldelta'], r['L'])
      self.assertEqual(r['family'], 'S2_RI_V1')
      p.verify(r)

  def test_chronological_feature_offsets(self):
    b = api().build()
    layout = item(b, 'fitting-feature-contract')['layouts']['S2RI_D05_L05']
    self.assertEqual(layout['columns'], [
      'intercept', 'command_k_minus_9', 'command_k_minus_8', 'command_k_minus_7',
      'command_k_minus_6', 'command_k_minus_5', 'delta_k_minus_5', 'delta_k_minus_4',
      'delta_k_minus_3', 'delta_k_minus_2', 'delta_k_minus_1', 'angle_tick_k', 'speed_mps_k'])
    self.assertEqual(layout['required_prior_intervals'], 9)

  def test_valid_bundle_and_exact_repeat(self):
    b = api().build()
    self.assertEqual(api().validate(b), b)
    self.assertEqual(p.canonical(b), p.canonical(api().build()))

  def test_resealed_candidate_expansion_rejected(self):
    b = api().build()
    v = item(b, 'candidate-set')
    v['candidates'].append(copy.deepcopy(v['candidates'][0]))
    b['empirical-s2-ri-candidate-set-v1.json'] = p.seal({k: x for k, x in v.items() if k != 'receipt_sha256'})
    with self.assertRaisesRegex(ValueError, 'FITTING_POLICY_CONTRACT_DRIFT'):
      api().validate(b)


class TestS2RIFittingRejections(unittest.TestCase):
  """Each mutation is a freedom a future consumer must refuse, even resealed."""
  def reject(self, name, mutate):
    b = api().build()
    key = 'empirical-s2-ri-'+name+'-v1.json'
    value = b[key]
    mutate(value)
    b[key] = p.seal({k: v for k,v in value.items() if k != 'receipt_sha256'})
    with self.assertRaisesRegex(ValueError, 'FITTING_POLICY_CONTRACT_DRIFT'):
      api().validate(b)

  def test_missing_artifact(self):
    b = api().build()
    b.pop('empirical-s2-ri-acceptance-gate-v1.json')
    with self.assertRaisesRegex(ValueError, 'COMPLETE'):
      api().validate(b)

  def test_unexpected_raw_or_model_payload(self):
    for key in ('coefficients', 'predictions', 'private_path', 'raw_rows', 'winner'):
      with self.subTest(key=key):
        self.reject('fitting-policy', lambda v, key=key: v.update({key: 'forbidden'}))

  def test_candidates_cannot_change_order_or_duplicate(self):
    self.reject('candidate-set', lambda v: v['candidates'].reverse())
    self.reject('candidate-set', lambda v: v['candidates'].__setitem__(1, copy.deepcopy(v['candidates'][0])))

  def test_offsets_histories_and_parameter_count_fixed(self):
    for key, value in (('d', 1), ('L', 2), ('Lu', 5), ('Ldelta', 15), ('parameter_count', 4), ('family', 'S1')):
      with self.subTest(key=key):
        self.reject('candidate-set', lambda v, key=key, value=value: v['candidates'][0].update({key: value}))

  def test_candidate_receipt_and_cross_contract_bindings(self):
    b = api().build()
    for r in item(b, 'candidate-set')['candidates']:
      for field, name in (('grid_policy_sha256', 'fitting-grid-contract'), ('fit_method_sha256', 'fit-method'),
                          ('normalizer_sha256', 'normalization-contract'), ('metric_sha256', 'fitting-metric-contract'),
                          ('admission_gate_sha256', 'acceptance-gate'), ('rollout_sha256', 'rollout-contract')):
        self.assertEqual(r[field], item(b, name)['receipt_sha256'])
    self.reject('candidate-set', lambda v: v['candidates'][0].update(grid_policy_sha256='0'*64))

  def test_no_secondary_scope_gate(self):
    for name, key in (('fitting-policy', 'primary_scope'), ('acceptance-gate', 'primary_scope')):
      with self.subTest(name=name):
        self.reject(name, lambda v, key=key: v.update({key: 'SCOPE_NON_RAIL_ACTIVE_NO_OVERRIDE'}))
    self.reject('selection-rule', lambda v: v['keys'].insert(0, 'NON_RAIL_RMSE'))

  def test_execution_order_all_32_jobs(self):
    v = item(api().build(), 'candidate-set')
    self.assertEqual(len(v['execution_order']), 32)
    self.assertEqual(v['execution_order'][:2], [
      {'candidate_id': 'S2RI_D00_L01', 'fold': 'FOLD_A'}, {'candidate_id': 'S2RI_D00_L01', 'fold': 'FOLD_B'}])
    self.reject('candidate-set', lambda v: v['execution_order'].pop())
    self.reject('candidate-set', lambda v: v.update(complete_accounting='STOP_AFTER_FIRST_PASS'))

  def test_future_or_rate_feature_injection(self):
    for feature in ('steeringRateDeg', 'request', 'raw_torqueOutputCan', 'angle_k_plus_1', 'command_k_plus_1',
                    'driver_torque', 'speed_one_hot', 'command_times_speed', 'gyro', 'modelV2'):
      with self.subTest(feature=feature):
        self.reject('fitting-feature-contract', lambda v, feature=feature: v['layouts']['S2RI_D00_L01']['columns'].append(feature))

  def test_feature_order_not_reversed(self):
    self.reject('fitting-feature-contract', lambda v: v['layouts']['S2RI_D05_L05']['columns'].reverse())

  def test_no_normalizer_leakage(self):
    for pop in ('DEVELOPMENT', 'POOLED_TRAIN_DEVELOPMENT', 'HOLDOUT'):
      with self.subTest(pop=pop):
        self.reject('normalization-contract', lambda v, pop=pop: v.update(population=pop))
    self.reject('normalization-contract', lambda v: v.update(development_transform='REFIT'))

  def test_intercept_and_constants_preserved(self):
    self.reject('normalization-contract', lambda v: v.update(intercept='CENTER_SCALE'))
    self.reject('normalization-contract', lambda v: v.update(constant='EPSILON_STD_FLOOR'))
    self.reject('normalization-contract', lambda v: v.update(std='SAMPLE_STD_DDOF_1'))
    v = item(api().build(), 'normalization-contract')
    self.assertEqual(v['constant'], 'FROZEN_TRAIN_ZERO_COLUMN')
    self.assertEqual(v['development_constant_drift'], 'DEVELOPMENT_CONSTANT_DRIFT_REPORT_ONLY')

  def test_solver_dtype_tolerance_and_regularization_fixed(self):
    for key,value in (('solver','scipy.optimize'), ('dtype','float32'), ('rcond', -1),
                      ('regularization','RIDGE'), ('numpy_version','unbound'), ('rng', True)):
      with self.subTest(key=key):
        self.reject('fit-method', lambda v, key=key, value=value: v.update({key:value}))
    v = item(api().build(), 'fit-method')
    self.assertEqual(v['solver'], 'numpy.linalg.lstsq')
    self.assertIsNone(v['rcond'])
    self.assertEqual(v['rank_failure'], 'FIT_PRECONDITION_RANK_FAILURE_NO_SOLVE')

  def test_exact_inverted_route_folds(self):
    v = item(api().build(), 'fitting-policy')
    self.assertEqual(v['folds'], [
      {'name':'FOLD_A','train':'7ae11bd92d924f7f4a319657595bfc9f60259f0a9b638327fd9ef6ad4edf2677',
       'development':'962f24485b27893e075f1a580f6e168a52f9a33dececfe4e82e1e2995c15c86c'},
      {'name':'FOLD_B','train':'962f24485b27893e075f1a580f6e168a52f9a33dececfe4e82e1e2995c15c86c',
       'development':'7ae11bd92d924f7f4a319657595bfc9f60259f0a9b638327fd9ef6ad4edf2677'}])
    self.reject('fitting-policy', lambda v: v['folds'][0].update(train=v['folds'][0]['development']))

  def test_no_random_segment_or_pooled_split(self):
    for split in ('RANDOM_ROW', 'RANDOM_SEGMENT', 'POOLED'):
      with self.subTest(split=split):
        self.reject('fitting-policy', lambda v, split=split: v.update(split=split))

  def test_projected_state_only(self):
    self.reject('rollout-contract', lambda v: v.update(recursive_state='CONTINUOUS'))
    self.assertEqual(item(api().build(), 'rollout-contract')['recursive_state'], 'PROJECTED_SOURCE_GRID')

  def test_no_future_measured_feedback(self):
    for key in ('measured_future_angle', 'measured_future_delta', 'steering_rate'):
      with self.subTest(key=key):
        self.reject('rollout-contract', lambda v, key=key: v.update({key:'FEATURE'}))
    self.reject('rollout-contract', lambda v: v['exogenous'].append('OBSERVED_FUTURE_ANGLE'))

  def test_rollout_steps_off_by_one_rejected(self):
    v = item(api().build(), 'rollout-contract')
    self.assertEqual(v['horizons'], [{'seconds':.25,'steps':25},{'seconds':.5,'steps':50},
                                     {'seconds':1.,'steps':100},{'seconds':2.,'steps':200}])
    self.reject('rollout-contract', lambda v: v['horizons'][0].update(steps=24))
    self.reject('rollout-contract', lambda v: v.update(endpoint='k_PLUS_H_MINUS_1'))

  def test_no_cross_boundary_or_padding(self):
    self.reject('rollout-contract', lambda v: v.update(support='ALLOW_NEXT_SEGMENT'))
    self.reject('rollout-contract', lambda v: v.update(boundary='PAD_TO_HORIZON'))

  def test_direct_tick_amendment_not_historical_rewrite(self):
    v = item(api().build(), 'fitting-grid-contract')
    self.assertFalse(v['bitwise_equivalent_to_historical_degree_roundtrip'])
    self.assertEqual(v['operation'], 'DIRECT_ROUND_HALF_TO_EVEN_TO_INTEGER_TICK')
    # Contract counterexample, not a model prediction or projection executor.
    self.assertEqual(v['synthetic_contract_counterexample'],
                     {'input_tick':14.5,'direct_tick':14,'historical_roundtrip_tick':15})
    self.reject('fitting-grid-contract', lambda v: v.update(operation='DEGREE_ROUNDTRIP'))
    self.reject('fitting-grid-contract', lambda v: v.update(tie_semantics='ROUND_HALF_AWAY_FROM_ZERO'))

  def test_range_nonfinite_no_clipping(self):
    v = item(api().build(), 'fitting-grid-contract')
    self.assertEqual(v['code_range'], [-32768,32767])
    self.reject('fitting-grid-contract', lambda v: v.update(range_failure='CLIP'))
    self.reject('rollout-contract', lambda v: v.update(numerical_failure='DROP_FAILED_ANCHORS'))

  def test_holdlast_required_and_same_population(self):
    self.reject('comparator-contract', lambda v: v.update(name='HISTORICAL_ARX'))
    self.reject('comparator-contract', lambda v: v.update(anchors='ALL_BASELINE_ROWS'))
    self.reject('comparator-contract', lambda v: v.update(rollout='USE_FUTURE_MEASURED_TICK'))
    self.assertEqual(item(api().build(), 'comparator-contract')['name'], 'HOLD_LAST_ANGLE')

  def test_duplicate_error_channels_explicit(self):
    v = item(api().build(), 'fitting-metric-contract')
    self.assertEqual(v['continuous_next_angle_error'], 'EXACT_SAME_CANONICAL_ERROR_BUFFER_AS_DELTA_ERROR')
    self.reject('fitting-metric-contract', lambda v: v.update(duplicated_metrics='INDEPENDENT_EVIDENCE'))

  def test_metric_definition_and_population_frozen(self):
    self.reject('fitting-metric-contract', lambda v: v.update(p95='NEAREST_PERCENTILE'))
    self.reject('fitting-metric-contract', lambda v: v.update(rollout_population='ALL_INTERMEDIATE_SAMPLES'))
    self.reject('fitting-metric-contract', lambda v: v.update(minimum_development_anchors_per_fold_and_horizon=1))

  def test_strict_rmse_nonworse_mae_p95(self):
    v = item(api().build(), 'acceptance-gate')
    self.assertEqual(v['one_step_next_angle'], {'RMSE':'<','MAE':'<=','P95_ABSOLUTE':'<='})
    self.reject('acceptance-gate', lambda v: v['one_step_next_angle'].update(RMSE='<='))
    self.reject('acceptance-gate', lambda v: v['one_step_next_angle'].pop('MAE'))
    self.reject('acceptance-gate', lambda v: v['one_step_next_angle'].pop('P95_ABSOLUTE'))

  def test_both_folds_and_all_horizons_mandatory(self):
    self.reject('acceptance-gate', lambda v: v.update(fold_quantifier='ANY'))
    self.reject('acceptance-gate', lambda v: v['folds'].pop())
    self.reject('acceptance-gate', lambda v: v['rollout_horizons_steps'].pop())
    self.reject('acceptance-gate', lambda v: v['rollout'].pop('ANGLE_P95_ABSOLUTE'))

  def test_grid_hit_gates_mandatory(self):
    v = item(api().build(), 'acceptance-gate')
    self.assertEqual(v['source_grid'], {'EXACT_NEXT_ANGLE_HIT_RATE':'>=','WITHIN_ONE_TICK_RATE':'>='})
    for name in v['source_grid']:
      with self.subTest(name=name):
        self.reject('acceptance-gate', lambda row, name=name: row['source_grid'].pop(name))

  def test_no_epsilon_or_pooled_gate(self):
    self.reject('acceptance-gate', lambda v: v.update(epsilon=.001))
    self.reject('acceptance-gate', lambda v: v.update(pooled_gate='PRIMARY'))
    self.reject('acceptance-gate', lambda v: v.update(all_ties='ADMIT'))

  def test_ranking_order_exact(self):
    v = item(api().build(), 'selection-rule')
    self.assertEqual(v['keys'], ['WORST_ROLLOUT_RMSE_RATIO','WORST_ONE_STEP_P95_RATIO','PARAMETER_COUNT','L','d','CANDIDATE_ID'])
    self.reject('selection-rule', lambda v: v['keys'].reverse())
    self.reject('selection-rule', lambda v: v.update(direction='DESCENDING'))

  def test_zero_denominator_contract(self):
    v = item(api().build(), 'selection-rule')
    self.assertEqual(v['ratio']['zero_over_zero'], 1.0)
    self.assertEqual(v['ratio']['positive_over_zero'], 'POSITIVE_INFINITY')
    self.reject('selection-rule', lambda v: v['ratio'].update(zero_over_zero=None))

  def test_no_candidate_fails_closed(self):
    v = item(api().build(), 'selection-rule')
    self.assertEqual(v['zero']['status'], 'S2_RI_NO_ADMISSIBLE_CANDIDATE')
    self.assertEqual(v['zero']['selection'], 'MODEL_SELECTION_FAILED_CLOSED')
    self.assertIsNone(v['zero']['selected_candidate'])
    self.reject('selection-rule', lambda v: v['zero'].update(next_action='RELAX_GATE'))

  def test_one_multiple_are_retrospective_only(self):
    v = item(api().build(), 'selection-rule')
    self.assertEqual(v['one']['status'], 'S2_RI_SINGLE_ADMISSIBLE_CANDIDATE')
    self.assertEqual(v['multiple']['status'], 'S2_RI_RETROSPECTIVE_CV_SELECTED')
    self.assertFalse(v['holdout_model_admission'])
    self.reject('selection-rule', lambda v: v.update(selected_candidate='S2RI_D00_L01'))

  def test_no_pooled_refit(self):
    self.reject('fitting-policy', lambda v: v.update(final_pooled_refit='AUTOMATIC'))
    self.reject('selection-rule', lambda v: v.update(pooled_refit='AUTHORIZED'))

  def test_no_authority_promotion(self):
    for name in ('fitting-policy', 'candidate-set', 'fit-method', 'rollout-contract', 'selection-rule', 'fitting-policy-readiness'):
      with self.subTest(name=name):
        self.reject(name, lambda v: v['authority'].update(fitting=True))
    self.reject('fitting-policy', lambda v: v.update(execution_authorized=True))

  def test_holdout_and_historical_states(self):
    v = item(api().build(), 'fitting-policy-readiness')
    self.assertEqual(v['holdout'], 'HOLDOUT_OPENING_CLOSED')
    self.assertEqual(v['opening_count'], 0)
    self.assertEqual(v['reservation'], 'NONE')
    self.assertEqual(v['dataset'], 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL')
    self.assertEqual(v['historical_grid_verdict'], 'SOURCE_GRID_OBSERVATION_REJECTED')
    self.assertEqual(v['qlog_model_support'], 0)
    for field in ('model_fitting','model_selection','cv_scoring','prediction','residual','rollout','normalizer_fitting'):
      self.assertEqual(v[field], 'NOT_RUN')
    self.reject('fitting-policy-readiness', lambda v: v.update(opening_count=1))
