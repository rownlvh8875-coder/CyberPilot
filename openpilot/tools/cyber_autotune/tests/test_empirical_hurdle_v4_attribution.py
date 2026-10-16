"""Hand-checked saved-evidence attribution contracts; no actual input access."""

import importlib
import numpy as np
import pytest


def math():
  return importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_v4_attribution_math')


def execution():
  return importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_v4_attribution')


def test_exact_hit_loss_gain_and_gate_fp_projected_hold():
  m = math()
  current = np.zeros(8, dtype=np.int16)
  target = np.array([0, 0, 0, 1, 2, -1, -3, 0], dtype=np.int16)
  gate = np.array([1, 1, 0, 1, 0, 0, 1, 0], dtype=bool)
  projected = np.array([1, 0, 0, 1, 0, 0, -2, 0], dtype=np.int16)
  delta = np.array([1, 0.2, 0, 1, 0, 0, -2, 0], dtype=float)
  previous = np.array([0, 1, 0, 0, 0, 1, 1, 1], dtype=bool)
  r = m.one_step(current, target, gate, projected, delta, delta - target, -target.astype(float), previous)
  assert r['exact_hit']['static_hit_loss'] == r['exact_hit']['move_hit_gain'] == 1
  assert r['exact_hit']['candidate_exact_hit_count'] == r['exact_hit']['hold_exact_hit_count'] == 4
  assert r['exact_hit']['net_hit_delta'] == 0
  assert r['static']['gate_fp'] == 2
  assert r['static']['harmful_false_movement'] == r['static']['gate_fp_projected_hold'] == 1
  assert r['static']['harmful_fraction_of_fp'] == 0.5
  assert r['move']['FN']['one_tick_count'] == r['move']['FN']['multi_tick_count'] == 1
  assert r['move']['FN']['positive_count'] == r['move']['FN']['negative_count'] == 1
  assert r['move']['FN']['hold_identity_exact']
  assert r['move']['TP']['exact_count'] == 1
  assert r['move']['TP']['within_one_tick_count'] == 2
  assert r['contexts']['PREV_STATIC_MOVE_ONSET']['count'] == 2
  assert r['contexts']['PREV_MOVE_MOVE_CONTINUATION']['confusion']['counts']['FN'] == 1


def test_fn_nonhold_rejected():
  m = math()
  with pytest.raises(ValueError):
    m.one_step(np.array([0]), np.array([1]), np.array([False]), np.array([1]), np.array([0.0]), np.array([-1.0]), np.array([-1.0]), np.array([False]))


def test_auc_exact_ties_and_missing_class():
  m = math()
  r = m.ranking(np.array([0.2, 0.2, 0.8, 0.8]), np.array([0, 1, 0, 1], bool))
  assert (r['auc_num2'], r['auc_den2'], r['auc']) == (4, 8, 0.5)
  assert m.ranking(np.array([0.2]), np.array([True]))['status'] == 'INPUT_INSUFFICIENT'
  assert m.ranking(np.array([], float), np.array([], bool))['status'] == 'INPUT_INSUFFICIENT'


def test_exact_rank_comparison_does_not_use_rounded_auc():
  m = math()
  n = 2**60
  better = {'status': 'COMPLETE', 'auc_num2': n + 1, 'auc_den2': 2 * n, 'auc': 0.5}
  old = {'status': 'COMPLETE', 'auc_num2': n, 'auc_den2': 2 * n, 'auc': 0.5}
  assert m.rank_compare(better, old) == 'V4_RANK_IMPROVED'
  assert m.rank_compare(old, better) == 'V4_RANK_DECREASED'
  assert m.rank_compare(old, old) == 'V4_RANK_EQUAL'


def test_state_conditioning_transfer_and_calibration():
  m = math()
  y = np.array([0, 1, 0, 1], bool)
  z = np.array([0, 0, 1, 1], bool)
  tr = m.rankings(np.array([0.1, 0.9, 0.2, 0.8]), y, z)
  dev = m.rankings(np.array([0.8, 0.2, 0.4, 0.6]), y, z)
  assert tr['PREV_STATIC']['auc'] == tr['PREV_MOVE']['auc'] == 1
  assert dev['PREV_STATIC']['auc'] == 0
  assert dev['PREV_MOVE']['auc'] == 1
  r = m.transfer(tr['OVERALL'], dev['OVERALL'])
  assert r['dev_minus_train_auc'] == -0.75
  assert r['development']['calibration_bias'] == 0


def paths():
  observed = np.array([[0, 0, 1, 1, 2], [0, 1, 1, 2, 2], [0, 0, 0, 0, 0]], np.int16)
  projected = np.array([[0, 0, 0, 1, 3], [0, 2, 2, 4, 4], [0, 0, 0, 0, 0]], np.int16)
  gate = np.array([[0, 0, 1, 1], [1, 0, 1, 0], [1, 0, 0, 0]], bool)
  return observed, projected, gate


def test_rollout_telescoping_events_gate_context_and_subsets():
  m = math()
  observed, projected, gate = paths()
  acc = m.PathAccumulator(4)
  acc.add(observed, projected, gate, np.array([1.0, 2.0, 0.0]), np.array([-2.0, -2.0, 0.0]), np.zeros(3, bool))
  r = acc.finish()
  assert r['terminal_error_identity_exact']
  assert r['first_events']['gate_mismatch']['histogram'] == {'0': 1, '1': 1, '2': 1}
  assert r['first_events']['context_divergence']['histogram'] == {'0': 2, '3': 1}
  assert r['first_events']['tick_path_departure']['histogram'] == {'0': 1, '1': 1, '2': 1}
  assert r['gate']['counts'] == {'TN': 6, 'FP': 2, 'FN': 1, 'TP': 3}
  assert r['movement']['counts'] == {'TN': 7, 'FP': 1, 'FN': 1, 'TP': 3}
  assert r['gate_move_projected_hold_count'] == 1
  assert r['subsets']['GATE_PERFECT']['count'] == 1
  assert r['subsets']['GATE_PERFECT']['candidate']['rmse'] == 2
  assert r['subsets']['PROJECTED_MOVEMENT_PATTERN_PERFECT']['count'] == 2
  assert r['subsets']['EARLY_CONTEXT_DIVERGENCE']['count'] == 0
  assert r['subsets']['LATE_CONTEXT_DIVERGENCE']['count'] == 1
  assert r['classes']['FN']['signed_sum'] == -1
  assert r['classes']['TP']['signed_sum'] == 3
  assert r['classes']['FP']['signed_sum'] == 1


def test_rollout_chunking_is_byte_canonical_independent():
  m = math()
  observed, projected, gate = paths()
  whole, chunked = m.PathAccumulator(4), m.PathAccumulator(4)
  error, hold, z = np.array([1.0, 2.0, 0.0]), np.array([-2.0, -2.0, 0.0]), np.zeros(3, bool)
  whole.add(observed, projected, gate, error, hold, z)
  for i in range(3):
    chunked.add(observed[i : i + 1], projected[i : i + 1], gate[i : i + 1], error[i : i + 1], hold[i : i + 1], z[i : i + 1])
  assert whole.finish() == chunked.finish()


def test_rollout_aggregate_schema_passes_privacy_without_raw_field_alias():
  m = math()
  observed, projected, gate = paths()
  acc = m.PathAccumulator(4)
  acc.add(observed, projected, gate, np.array([1.0, 2.0, 0.0]), np.array([-2.0, -2.0, 0.0]), np.zeros(3, bool))
  execution().privacy(acc.finish())


def test_compact_int16_widened_before_delta():
  m = math()
  acc = m.PathAccumulator(1)
  observed = np.array([[-32768, 32767]], np.int16)
  projected = np.array([[-32768, -32768]], np.int16)
  acc.add(observed, projected, np.array([[False]]), np.array([-65535.0]), np.array([-65535.0]), np.array([False]))
  assert acc.finish()['classes']['FN']['signed_sum'] == -65535


def test_terminal_corruption_rejected():
  m = math()
  observed, projected, gate = paths()
  with pytest.raises(ValueError):
    m.PathAccumulator(4).add(observed, projected, gate, np.zeros(3), np.array([-2.0, -2.0, 0.0]), np.zeros(3, bool))


@pytest.mark.parametrize(
  ('n', 'state'), [(0, 'EMPTY'), (1, 'SMALL_SUPPORT_DESCRIPTIVE_ONLY'), (200, 'SMALL_SUPPORT_DESCRIPTIVE_ONLY'), (201, 'FULL_DESCRIPTIVE_SUPPORT')]
)
def test_support_boundary(n, state):
  assert math().support(n) == state


def test_streaks_reset_at_path_boundary():
  m = math()
  hist = m.IntegerHistogram()
  m.add_streaks(hist, np.array([[1, 1, 0, 1], [1, 0, 0, 1]], bool))
  r = hist.summary()
  assert r['count'] == 4 and r['median'] == 1 and r['max'] == 2
  assert r['p95'] == pytest.approx(1.85)


@pytest.mark.parametrize('name', ['train', 'probability', 'development', 'recursive', 'rollout', 'select', 'run'])
def test_v4_execution_firewall(name):
  a = execution()
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_execution as e

  with a.firewall(), pytest.raises(ValueError, match='FORBIDDEN'):
    getattr(e, name)()


@pytest.mark.parametrize('operation', ['newton', 'normalizer', 'threshold', 'predict_delta'])
def test_fit_inference_threshold_normalizer_firewall(operation):
  a = execution()
  from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m

  with a.firewall(), pytest.raises(ValueError, match='FORBIDDEN'):
    getattr(m, operation)()


@pytest.mark.parametrize(
  'bad',
  [
    {'threshold': 0.2},
    {'coefficients': [1.0]},
    {'value': '/mnt/e/private/item'},
    {'scores': np.ones(2)},
    {'gate_sequence': [True, False]},
    {'location': 'E:\\private\\file'},
  ],
)
def test_private_values_rejected(bad):
  a = execution()
  with pytest.raises(ValueError, match='PRIVACY'):
    a.privacy(bad)


@pytest.mark.parametrize('bad', [{'scores': [0.1, 0.2]}, {'p_move': [0.1, 0.2]}, {'raw_scores': [1, 2]}, {'normalizer_values': [1.0]}])
def test_json_raw_vector_payloads_rejected(bad):
  with pytest.raises(ValueError, match='PRIVACY'):
    execution().privacy(bad)


def test_current_public_evidence_lock_is_consistent():
  rows, pins = execution().public_lock()
  assert len(rows) == 12 and len(pins) >= 12
  assert rows['selection-result']['selection']['selected_candidate'] is None


def test_new_sink_cannot_mint_a_private_fitting_authorization(tmp_path):
  a = execution()
  from openpilot.tools.cyber_autotune import empirical_plant_policy as p

  value = p.seal({'schema': 'HURDLE_STAGE1_V4_EXTERNAL_ONE_SHOT_AUTHORIZATION', 'numeric_access_authorized': True})
  with pytest.raises(ValueError, match='FORBIDDEN'):
    a.write_json(tmp_path / 'grant.json', value)
  assert not (tmp_path / 'grant.json').exists()


@pytest.mark.parametrize('name', ['fit_stage1', 'fit_stage2', 'project', 'transform'])
def test_copied_numerical_aliases_are_trapped(name):
  from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m

  with execution().firewall(), pytest.raises(ValueError, match='FORBIDDEN'):
    getattr(m, name)()


@pytest.mark.parametrize('name', ['source_array', 'decode_bound_array', 'permit_valid'])
def test_legacy_source_and_model_read_capabilities_trapped(name):
  a = execution()
  with a.firewall(), pytest.raises(ValueError, match='FORBIDDEN'):
    getattr(a.auth.prior, name)()


@pytest.mark.parametrize('changed', ['head', 'environment', 'output', 'branch'])
def test_bound_run_identity_rejects_drift(tmp_path, changed):
  a = execution()
  lock = {
    'analysis_head': 'a' * 40,
    'environment': {'numpy': 'pinned'},
    'repository': 'repo',
    'branch': 'feature/test',
    'storage': {'output_root_identity_sha256': a.p.sha(str(tmp_path).encode())},
  }
  inputs = {'head': 'a' * 40, 'environment': {'numpy': 'pinned'}, 'output': tmp_path, 'repository': 'repo', 'branch': 'feature/test'}
  a.enforce_identity(lock, **inputs)
  inputs[changed] = {'numpy': 'drift'} if changed == 'environment' else (tmp_path / 'copied' if changed == 'output' else 'drift')
  with pytest.raises(ValueError):
    a.enforce_identity(lock, **inputs)


def test_source_writes_and_raw_openings_blocked(tmp_path):
  a = execution()
  source = tmp_path / 'source'
  source.mkdir()
  evidence = source / 'saved.json'
  evidence.write_text('{}')
  output = tmp_path / 'output'
  with a.access_guard([source], output):
    with pytest.raises(ValueError, match='FORBIDDEN'):
      evidence.write_text('bad')
    with pytest.raises(ValueError, match='FORBIDDEN'):
      (source / 'qlog').open('rb')
    with pytest.raises(ValueError, match='FORBIDDEN'):
      (source / 'HOLDOUT' / 'manifest.json').open('rb')
  assert evidence.read_text() == '{}'


def test_authorized_metadata_parent_name_is_not_a_raw_log(tmp_path):
  a = execution()
  source = tmp_path / 'historical-rlog-only'
  source.mkdir()
  evidence = source / 'manifest.json'
  evidence.write_text('{}')
  with a.access_guard([source], tmp_path / 'output'):
    assert evidence.read_text() == '{}'


def test_read_guard_rejects_unlisted_private_member(tmp_path):
  a = execution()
  source = tmp_path / 'source'
  source.mkdir()
  evidence = source / 'manifest.json'
  evidence.write_text('{}')
  extra = source / 'unadmitted.npy.gz'
  extra.write_bytes(b'not admitted')
  with a.access_guard([source], tmp_path / 'output', allowed_reads={evidence}):
    assert evidence.read_text() == '{}'
    with pytest.raises(ValueError, match='FORBIDDEN'):
      extra.read_bytes()


def test_saved_overall_strict_equality_is_not_error_excess():
  a = execution()
  pair = {'candidate': {'rmse': 2.0, 'mae': 1.0, 'p95': 3.0}, 'comparator': {'rmse': 2.0, 'mae': 1.0, 'p95': 3.0}}
  assert not a.overall_excess(pair)
  pair['candidate']['rmse'] = 2.1
  assert a.overall_excess(pair)


def test_storage_upper_bound_is_enforced_before_write(tmp_path):
  a = execution()
  root = tmp_path / 'output'
  root.mkdir()
  value = a.p.seal({'schema': 'V4_ATTRIBUTION_SUMMARY', 'count': 1})
  with a.access_guard([], root, storage={'aggregate_upper_bytes': 8, 'reserve_bytes': 0}):
    with pytest.raises(ValueError, match='CAPACITY'):
      a.write_json(root / 'summary.json', value)
  assert not (root / 'summary.json').exists()


def test_readonly_scope_forbids_new_output_files(tmp_path):
  a = execution()
  with a.access_guard([], tmp_path, readonly=True), pytest.raises(ValueError, match='FORBIDDEN'):
    a.write_json(tmp_path / 'new.json', a.p.seal({'schema': 'V4_ATTRIBUTION_SUMMARY'}))


@pytest.mark.parametrize(
  'payload',
  [
    {'combined_probability': [0.1, 0.2]},
    {'current_tick': [1, 2]},
    {'actual_delta_tick': [1, 2]},
    {'determinant': [1, 2]},
    {'direction': [1, 2]},
    {'uri': 'file:///private/file'},
  ],
)
def test_saved_field_and_witness_payload_privacy(payload):
  with pytest.raises(ValueError, match='PRIVACY'):
    execution().privacy(payload)


def test_historical_coverage_keeps_unevaluated_job_separate():
  result = execution().historical_comparison()
  assert {k: sum(f['evaluated_jobs'] for f in v['folds'].values()) for k, v in result.items()} == {'V1': 32, 'V2': 32, 'V3': 31}


def test_publication_entire_scope_traps_saved_array_and_analysis(monkeypatch, tmp_path):
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_attribution_publication as pub

  def forbidden_consumer(*args):
    execution().array(None, None, 'current_tick')

  monkeypatch.setattr(pub, '_build', forbidden_consumer)
  with pytest.raises(ValueError, match='FORBIDDEN'):
    pub.build(tmp_path, {})


def test_resume_verifies_saved_aggregate_without_recomputation(tmp_path):
  a = execution()
  from openpilot.tools.cyber_autotune import empirical_plant_policy as p

  root = tmp_path / 'repeat-1'
  root.mkdir()
  saved = p.seal({'schema': 'V4_ATTRIBUTION_SUMMARY', 'count': 1})
  a.write_json(root / 'summary.json', saved)
  manifest = a.finish_store(root, {'policy_sha256': 'a' * 64, 'input_identity_sha256': 'b' * 64})
  result = a.resume(root, manifest['receipt_sha256'], synthetic=True)
  assert result['recompute_calls'] == 0
  (root / 'summary.json').write_text('{}')
  with pytest.raises(ValueError):
    a.resume(root, manifest['receipt_sha256'], synthetic=True)


def test_matching_train_uses_probability_population_not_head_dimension():
  a = execution()
  candidate = {'train_anchor_sha256': 'a' * 64, 'arrays': {'STATIC_coefficients': {'shape': [4]}, 'combined_probability': {'shape': [300]}}}
  reference = {'anchor_sha256': 'a' * 64, 'arrays': {'actual_delta_tick': {'shape': [300]}, 'prior_delta_tick': {'shape': [300]}}}
  a.matching(candidate, reference)
  reference['arrays']['prior_delta_tick']['shape'] = [299]
  with pytest.raises(ValueError):
    a.matching(candidate, reference)


def test_private_coefficient_array_reader_is_never_allowed(tmp_path):
  with pytest.raises(ValueError, match='FORBIDDEN'):
    execution().array(tmp_path, {'arrays': {}}, 'STATIC_coefficients')


def test_first_quarter_boundary_is_structural():
  m = math()
  acc = m.PathAccumulator(8)
  observed = np.zeros((2, 9), dtype=np.int16)
  projected = np.array([[0, 1, 1, 1, 1, 1, 1, 1, 1], [0, 0, 1, 1, 1, 1, 1, 1, 1]], dtype=np.int16)
  gate = np.diff(projected.astype(np.int64), axis=1) != 0
  acc.add(observed, projected, gate, np.ones(2), np.zeros(2), np.zeros(2, bool))
  r = acc.finish()
  assert r['first_events']['context_divergence']['histogram'] == {'2': 1, '3': 1}
  assert r['subsets']['EARLY_CONTEXT_DIVERGENCE']['count'] == 1
  assert r['subsets']['LATE_CONTEXT_DIVERGENCE']['count'] == 1


def test_mechanism_support_and_nonexclusive_trigger():
  a = execution()

  def subset(n, c, b):
    return {'count': n, 'candidate': dict.fromkeys(('rmse', 'mae', 'p95'), c), 'hold_last': dict.fromkeys(('rmse', 'mae', 'p95'), b)}

  r = {
    'subsets': {
      'GATE_PERFECT': subset(201, 1.0, 2.0),
      'GATE_PERFECT_PATH_MOVED': subset(201, 3.0, 2.0),
      'EARLY_CONTEXT_DIVERGENCE': subset(201, 5.0, 2.0),
      'NO_CONTEXT_DIVERGENCE': subset(201, 1.0, 2.0),
    }
  }
  flags = a.path_mechanism(r, overall_failed=True)
  assert flags == {'gate_mismatch_risk': True, 'magnitude_residual_risk': True, 'context_drift_association': True}
  r['subsets']['GATE_PERFECT_PATH_MOVED']['count'] = 200
  assert not a.path_mechanism(r, overall_failed=True)['magnitude_residual_risk']
  r['subsets']['GATE_PERFECT']['count'] = 0
  assert not a.path_mechanism(r, overall_failed=True)['gate_mismatch_risk']


@pytest.mark.parametrize(
  ('flags', 'expected'),
  [
    ({'gate_mismatch_risk': True, 'magnitude_residual_risk': True, 'context_drift_association': True}, 'MIXED_STAGE1_STAGE2_ARCHITECTURE_REVIEW'),
    ({'gate_mismatch_risk': False, 'magnitude_residual_risk': True, 'context_drift_association': True}, 'STAGE2_CONDITIONAL_DELTA_MODEL_REVIEW'),
    ({'gate_mismatch_risk': False, 'magnitude_residual_risk': False, 'context_drift_association': True}, 'ROLLOUT_STATE_FEEDBACK_REDESIGN_REVIEW'),
  ],
)
def test_next_review_is_one_category_and_not_implementation(flags, expected):
  a = execution()
  result = a.mechanism_states(flags, static_loss=True, fold_opposite=False, ranking_improved=False, operating_transfer=False)
  assert result['recommended_one_review'] == expected
  assert not result['next_execution_authorized']


def actual_public(label):
  a = execution()
  return a.saved.read_json(a.p.PUBLIC / (a.PREFIX + label + '.json'))


@pytest.mark.parametrize(
  'label',
  [
    'attribution-policy',
    'exact-hit-decomposition',
    'stage1-confusion-attribution',
    'state-conditional-ranking',
    'score-transfer',
    'fold-asymmetry',
    'rollout-gate-attribution',
    'rollout-context-drift',
    'rollout-step-error',
    'gate-perfect-rollout',
    'projected-movement-perfect-rollout',
    'rollout-streaks',
    'mechanism-summary',
    'next-design-trigger',
    'attribution-repeatability',
    'attribution-resume',
    'attribution-readiness',
    'attribution-validation',
  ],
)
def test_actual_public_report_only_bindings_and_privacy(label):
  a = execution()
  row = actual_public(label)
  a.privacy(row)
  assert row['scope'] == 'REPORT_ONLY' and row['status'] == a.SUCCESS
  assert row['execution_head'] == a.EXECUTION_HEAD
  assert row['baseline_result_publication_head'] == row['analysis_head'] == a.BASELINE
  assert row['authorization_sha256'] == a.AUTH_SHA and row['actual_manifest_sha256'] == a.MANIFEST_SHA
  assert row['analysis_sources'] == a.sources()
  assert row['execution_calls'] == a.ZERO
  assert row['selected_candidate'] is None and not row['next_execution_authorized']
  assert row['holdout'] == 'CLOSED' and row['opening_count'] == row['holdout_discovery'] == 0
  assert row['vehicle_authority'] == 'NONE'
  assert not row['threshold_public'] and not row['coefficients_public']
  assert len(a.p.canonical(row)) < 1024**2


def test_actual_public_exact_hit_identity_matches_original_result():
  a = execution()
  row = actual_public('exact-hit-decomposition')
  original = a.public_lock()[0]['development-results']
  assert [(j['candidate_id'], j['fold']) for j in row['jobs']] == list(a.saved.JOBS)
  for j, prior in zip(row['jobs'], original['jobs'], strict=True):
    hit, static = j['exact_hit'], j['static']
    n = hit['static_truth_count'] + hit['move_truth_count']
    assert n == prior['one_step']['count']
    assert hit['hold_exact_hit_count'] == hit['static_truth_count']
    assert hit['candidate_exact_hit_count'] == hit['hold_exact_hit_count'] - hit['static_hit_loss'] + hit['move_hit_gain']
    assert hit['net_hit_delta'] == hit['move_hit_gain'] - hit['static_hit_loss']
    assert hit['candidate_exact_hit_count'] / n == prior['one_step']['candidate']['exact_hit']
    assert hit['hold_exact_hit_count'] / n == prior['one_step']['comparator']['exact_hit']
    assert static['harmful_false_movement'] == hit['static_hit_loss']
    assert static['gate_fp'] == static['harmful_false_movement'] + static['gate_fp_projected_hold']
  assert row['summary']['exact_hit']['static_hit_loss'] == sum(j['exact_hit']['static_hit_loss'] for j in row['jobs'])


def test_actual_public_auc_exact_comparisons_and_state_populations():
  a = execution()
  row = actual_public('state-conditional-ranking')
  assert [(j['candidate_id'], j['fold']) for j in row['jobs']] == list(a.saved.JOBS)
  for j in row['jobs']:
    for population in ('train', 'development', 'historical_fixed'):
      data = j[population]
      assert data['OVERALL']['count'] == data['PREV_STATIC']['count'] + data['PREV_MOVE']['count']
      for v in data.values():
        if v['status'] == 'COMPLETE':
          assert v['auc_den2'] == 2 * v['positive_count'] * v['negative_count']
          assert 0 <= v['auc_num2'] <= v['auc_den2']
          assert v['auc'] == v['auc_num2'] / v['auc_den2']
    for context in ('OVERALL', 'PREV_STATIC', 'PREV_MOVE'):
      new, old = j['development'][context], j['historical_fixed'][context]
      assert new['count'] == old['count'] and new['positive_count'] == old['positive_count']
      if new['status'] == old['status'] == 'COMPLETE':
        diff = new['auc_num2'] * old['auc_den2'] - old['auc_num2'] * new['auc_den2']
        want = 'V4_RANK_IMPROVED' if diff > 0 else ('V4_RANK_DECREASED' if diff < 0 else 'V4_RANK_EQUAL')
        assert j['comparison'][context] == want


def test_actual_public_rollout_confusion_and_step_signed_accounting():
  gates, errors = actual_public('rollout-gate-attribution'), actual_public('rollout-step-error')
  for j, err in zip(gates['jobs'], errors['jobs'], strict=True):
    assert (j['candidate_id'], j['fold']) == (err['candidate_id'], err['fold'])
    assert set(j['rollout']) == {'25', '50', '100', '200'}
    for h, value in j['rollout'].items():
      g, m = value['gate']['counts'], value['movement']['counts']
      nsteps = value['count'] * int(h)
      assert sum(g.values()) == sum(m.values()) == nsteps
      assert m['FP'] <= g['FP'] and m['FN'] >= g['FN']
      assert value['gate_move_projected_hold_count'] == g['TP'] + g['FP'] - m['TP'] - m['FP']
      classes = err['rollout'][h]['classes']
      assert sum(v['count'] if v else 0 for v in classes.values()) == nsteps
      assert all((classes[k]['count'] if classes[k] else 0) == g[k] for k in g)
      assert err['rollout'][h]['terminal_error_identity_exact']


def test_actual_public_context_partition_and_first_event_semantics():
  row = actual_public('rollout-context-drift')
  for job, subsets in zip(row['jobs'], row['context_subsets'], strict=True):
    for h, value in job['rollout'].items():
      h = int(h)
      events = value['first_events']
      n = events['context_divergence']['count']
      for event in events.values():
        assert sum(event['histogram'].values()) == n
        assert all(0 <= int(k) <= h for k in event['histogram'])
        assert event['none_count'] == event['histogram'].get('0', 0)
      ctx = value['context_divergence']
      assert ctx['eligible_steps'] == n * (h - 1)
      assert ctx['rate'] == ctx['count'] / ctx['eligible_steps']
      assert '1' not in events['context_divergence']['histogram']
      pairs = subsets['rollout'][str(h)]['subsets']
      assert sum(p['count'] for p in pairs.values()) == n
      first = events['context_divergence']['histogram']
      assert pairs['EARLY_CONTEXT_DIVERGENCE']['count'] == sum(v for k, v in first.items() if 0 < int(k) and 4 * int(k) <= h)
      assert pairs['LATE_CONTEXT_DIVERGENCE']['count'] == sum(v for k, v in first.items() if 4 * int(k) > h)


def test_actual_public_perfect_path_support_and_terminal_partition():
  gp, mp, steps = actual_public('gate-perfect-rollout'), actual_public('projected-movement-perfect-rollout'), actual_public('rollout-step-error')
  for job, movement, error in zip(gp['jobs'], mp['jobs'], steps['jobs'], strict=True):
    for h, value in job['rollout'].items():
      pairs = {**value['subsets'], **movement['rollout'][h]['subsets']}
      for pair in pairs.values():
        n = pair['count']
        expected = 'EMPTY' if n == 0 else ('SMALL_SUPPORT_DESCRIPTIVE_ONLY' if n < 201 else 'FULL_DESCRIPTIVE_SUPPORT')
        assert pair['support_status'] == expected
        assert (pair['candidate'] is None) == (n == 0)
        if n:
          assert pair['candidate']['count'] == pair['hold_last']['count'] == n
      assert pairs['GATE_PERFECT_PATH_MOVED']['count'] <= pairs['GATE_PERFECT']['count']
      assert pairs['PROJECTED_MOVEMENT_PATTERN_PERFECT_PATH_MOVED']['count'] <= pairs['PROJECTED_MOVEMENT_PATTERN_PERFECT']['count']
      assert sum(v['signed_sum'] if v else 0 for v in error['rollout'][h]['classes'].values()) == pairs['ALL']['candidate']['signed_sum']


def test_actual_public_repeatability_resume_and_authority_unchanged():
  repeat = actual_public('attribution-repeatability')
  resumed = actual_public('attribution-resume')
  ready = actual_public('attribution-readiness')
  assert repeat['repeatability']['status'] == 'BYTE_EXACT_PASS'
  sha = repeat['attribution_manifest_sha256']
  assert repeat['repeatability']['manifest_sha256'] == sha
  assert resumed['resume']['recompute_calls'] == 0 and resumed['resume']['status'] == 'PASS'
  assert set(resumed['resume']['replicas']) == {'repeat-1', 'repeat-2'}
  assert all(v['manifest_sha256'] == sha and v['recompute_calls'] == 0 and v['status'] == 'PASS' for v in resumed['resume']['replicas'].values())
  assert ready['source_immutability'] == 'PASS' and ready['job_count'] == 32
  assert ready['validation_status'] in ('PENDING', 'PASS')
  trigger = actual_public('next-design-trigger')
  assert isinstance(trigger['recommended_one_review'], str) and trigger['recommended_one_review'].endswith('_REVIEW')
  assert not trigger['next_execution_authorized']
