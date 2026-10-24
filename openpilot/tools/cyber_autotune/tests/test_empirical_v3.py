"""V3 retrospective route development: policies and numerical gates."""

import copy
import tempfile
import unittest
from pathlib import Path
import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_v2_publication as old
from openpilot.tools.cyber_autotune import empirical_v3_policy as v
from openpilot.tools.cyber_autotune import empirical_v3_models as cv


class TestV3Policy(unittest.TestCase):
  def test_route_allowlist_from_immutable_split(self):
    split = old.load()['empirical-plant-v2-train-dev-split-v1.json']
    self.assertEqual(v.routes(), [x for x in split['routes'] if x['role'] == 'TRAIN'])

  def test_fold_exact_inversion(self):
    a, b = [x['route_id'] for x in v.routes()]
    folds = v.folds()['folds']
    self.assertEqual(folds, [{'fold': 'FOLD_A', 'train_route': a, 'development_route': b}, {'fold': 'FOLD_B', 'train_route': b, 'development_route': a}])

  def test_excluded_development(self):
    row = v.policy()
    dev = next(x for x in old.load()['empirical-plant-v2-train-dev-split-v1.json']['routes'] if x['role'] == 'DEVELOPMENT')
    self.assertEqual(row['excluded_context']['route_id'], dev['route_id'])
    self.assertEqual(row['excluded_context']['state'], 'V2_ZERO_SUPPORT_DEVELOPMENT_CONTEXT_ONLY')
    with self.assertRaises(ValueError):
      v.require_route(dev['route_id'])

  def test_minimum_and_grid_unchanged(self):
    row = v.policy()
    self.assertEqual(row['minimum_development_rows'], 201)
    self.assertEqual(row['family_policy'], p.family_policy())
    self.assertEqual(len(row['family_policy']['candidates']), 8)

  def test_policy_authority_and_history(self):
    row = v.policy()
    self.assertEqual(row['limitation'], 'RETROSPECTIVE_MODEL_DEVELOPMENT')
    self.assertFalse(row['holdout_opening_allowed'])
    self.assertEqual(row['stage_c'], 'STAGE_C_PENDING_FUTURE_HOLDOUT')
    self.assertEqual(row['calibration_blockers'], p.BLOCKERS)

  def test_freeze_required_before_results(self):
    with tempfile.TemporaryDirectory() as tmp:
      with self.assertRaises((ValueError, FileNotFoundError)):
        v.require_frozen(Path(tmp))
      v.freeze(Path(tmp))
      self.assertEqual(v.require_frozen(Path(tmp)), v.policy())

  def test_frozen_policy_mutation_rejected(self):
    with tempfile.TemporaryDirectory() as tmp:
      v.freeze(Path(tmp))
      row = v.policy()
      row['minimum_development_rows'] = 82
      with self.assertRaises(ValueError):
        p.persist(Path(tmp) / 'policy.json', p.seal(row))

  def test_code_identity_separate_from_publication(self):
    self.assertIn('empirical_v3_models.py', v.code_identity())
    self.assertNotIn('empirical_v3_publication.py', v.code_identity())


def evaluation(rmse=1.0, mae=0.5, p95=2.0, count=300):
  def stats(r, a, q):
    return {'count': count, 'RMSE': r, 'MAE': a, 'P95_ABS': q, 'BIAS': 0.0, 'MEDIAN_ABS': a, 'CORRELATION': 0.9}

  group = {
    'model': stats(rmse, mae, p95),
    'HOLD_LAST_OUTPUT': stats(2.0, 1.0, 3.0),
    'ZERO_RESPONSE': stats(4.0, 2.0, 5.0),
    'TRAIN_STATIC_GAIN': stats(3.0, 1.5, 4.0),
  }
  return {
    'status': 'EVALUATED',
    'one_step': copy.deepcopy(group),
    'rollout': {str(h): copy.deepcopy(group) for h in (25, 50, 100, 200)},
    'finite_horizon_bounded': True,
  }


def record(c, errors):
  return {
    'config': c,
    'parameter_count': 3 if c['family'] == 'ARX1' else 26,
    'folds': [{'fold': f, 'fit_status': 'FITTED', 'evaluation': evaluation(e)} for f, e in zip(('FOLD_A', 'FOLD_B'), errors, strict=True)],
  }


class TestV3Selection(unittest.TestCase):
  def test_worst_route_primary(self):
    configs = p.family_policy()['candidates']
    a, b = record(configs[0], [0.1, 1.9]), record(configs[1], [1.2, 1.2])
    self.assertEqual(cv.choose([a, b])['selected']['config'], configs[1])

  def test_equal_route_mean_secondary(self):
    configs = p.family_policy()['candidates']
    a, b = record(configs[0], [1.5, 1.0]), record(configs[1], [1.5, 0.9])
    self.assertEqual(cv.choose([a, b])['selected']['config'], configs[1])

  def test_parameter_family_delay_ties(self):
    rows = [record(c, [1.0, 1.0]) for c in reversed(p.family_policy()['candidates'])]
    self.assertEqual(cv.choose(rows)['selected']['config'], p.family_policy()['candidates'][0])

  def test_directional_gate_both_folds(self):
    c = p.family_policy()['candidates'][0]
    row = record(c, [1.0, 1.0])
    self.assertTrue(cv.directional_gate(row)['passed'])
    row['folds'][1]['evaluation']['one_step']['model']['MAE'] = 1.1
    self.assertFalse(cv.directional_gate(row)['passed'])
    self.assertEqual(cv.choose([row])['state'], 'STAGE_A_CV_TRADEOFF_ONLY')

  def test_rmse_must_strictly_beat_hold_last(self):
    row = record(p.family_policy()['candidates'][0], [2.0, 2.0])
    self.assertFalse(cv.directional_gate(row)['passed'])

  def test_other_naive_primary_not_worse(self):
    row = record(p.family_policy()['candidates'][0], [1.0, 1.0])
    row['folds'][0]['evaluation']['one_step']['ZERO_RESPONSE']['RMSE'] = 0.5
    self.assertFalse(cv.directional_gate(row)['passed'])

  def test_same_support_required(self):
    row = record(p.family_policy()['candidates'][0], [1.0, 1.0])
    row['folds'][0]['evaluation']['one_step']['HOLD_LAST_OUTPUT']['count'] = 299
    with self.assertRaises(ValueError):
      cv.directional_gate(row)

  def test_missing_rollout_not_finite_evidence(self):
    row = record(p.family_policy()['candidates'][0], [1.0, 1.0])
    for metric in row['folds'][0]['evaluation']['rollout']['200'].values():
      metric['count'] = 0
    self.assertFalse(cv.directional_gate(row)['passed'])

  def test_insufficient_support(self):
    row = record(p.family_policy()['candidates'][0], [1.0, 1.0])
    for f in row['folds']:
      f['evaluation'] = evaluation(count=200)
    self.assertIsNone(cv.choose([row])['selected'])

  def test_unstable_fit_not_selected(self):
    row = record(p.family_policy()['candidates'][0], [0.1, 0.1])
    row['folds'][0]['fit_status'] = 'UNSTABLE_REJECTED'
    self.assertIsNone(cv.choose([row])['selected'])

  def test_prediction_shared_support_and_repeatability(self):
    n = 400
    u = np.sin(np.arange(n) * 0.1)
    y = np.zeros(n)
    for k in range(1, n):
      y[k] = 0.8 * y[k - 1] + u[k - 5] + 0.1
    data = [{'u': u, 'y': y, 'blocks': np.zeros(n, dtype=int)}]
    c = p.family_policy()['candidates'][1]
    first = cv.predictions(data, {'config': c, 'coefficients': [0.8, 1.0, 0.1]}, [0.0, 0.0])
    second = cv.predictions(data, {'config': c, 'coefficients': [0.8, 1.0, 0.1]}, [0.0, 0.0])
    for key in first:
      np.testing.assert_array_equal(first[key], second[key])
    self.assertEqual(first['one_step'].shape, (n - 44, 5))
    self.assertEqual(first['endpoint_200'].shape, (n - 44 - 199, 5))
    np.testing.assert_allclose(first['one_step'][:, 0], first['one_step'][:, 1], atol=1e-14)

  def test_no_cross_run_history(self):
    data = [{'u': np.ones(40), 'y': np.ones(40), 'blocks': np.zeros(40)}] * 2
    out = cv.predictions(data, {'config': p.family_policy()['candidates'][0], 'coefficients': [0.5, 0.5, 0.0]}, [1.0, 0.0])
    self.assertEqual(out['one_step'].shape, (0, 5))

  def test_private_array_immutable(self):
    with tempfile.TemporaryDirectory() as tmp:
      path = Path(tmp) / 'x.npy'
      a = np.array([1.0, 2.0])
      self.assertEqual(cv.save_array(path, a), cv.save_array(path, a))
      with self.assertRaises(ValueError):
        cv.save_array(path, a + 1.0)

  def test_weak_gyro_blocks_even_good_kinematics(self):
    self.assertFalse(cv.yaw_consistent([{'admitted': False}, {'admitted': False}]))
    self.assertFalse(
      cv.yaw_consistent(
        [
          {'admitted': True, 'selection': {'hypothesis': 'YAW_H1', 'gyro_candidate': {'axis': 2}}},
          {'admitted': True, 'selection': {'hypothesis': 'YAW_H2', 'gyro_candidate': {'axis': 2}}},
        ]
      )
    )


class TestV3Execution(unittest.TestCase):
  def test_selected_gate_required_for_refit(self):
    from openpilot.tools.cyber_autotune import empirical_v3_generation as g

    selection = cv.choose([record(p.family_policy()['candidates'][0], [2.0, 2.0])])
    self.assertIsNone(g.refit([], selection, {}, None))

  def test_holdout_package_closed_without_models(self):
    from openpilot.tools.cyber_autotune import empirical_v3_generation as g

    package = g.holdout_package({}, 'synthetic')
    self.assertEqual(package['status'], 'CLOSED_MISSING_ADMISSIBLE_MODEL')
    self.assertEqual(package['one_time_opening_state'], 'CLOSED')
    for key in ('refit_allowed', 'reselection_allowed', 'threshold_change_allowed', 'model_family_change_allowed', 'old_routes_holdout_allowed'):
      self.assertFalse(package[key])

  def test_separate_private_store(self):
    from openpilot.tools.cyber_autotune import empirical_v3_cache as cache

    with tempfile.TemporaryDirectory() as tmp:
      with self.assertRaises(ValueError):
        cache.distinct_stores(tmp, tmp)

  def test_cache_binding_rejects_profile_and_adapter(self):
    from openpilot.tools.cyber_autotune import empirical_v3_cache as cache

    route = v.routes()[0]
    opening = p.seal(
      {
        'route_id': route['route_id'],
        'source_sha256': 'source',
        'split_sha256': 'split',
        'authorization_sha256': 'auth',
        'role': 'TRAIN',
        'holdout_opened': False,
      }
    )
    row = {
      'route_id': route['route_id'],
      'role': 'TRAIN',
      'source_sha256': 'source',
      'segment_id': 'source',
      'opening_sha256': opening['receipt_sha256'],
      'adapter_sha256': route['adapter_sha256'],
      'status': 'EXTRACTED',
      'runtime_steer_max': 409,
      'runtime_setting_known': True,
      'profile': {'steer_control_type': 'torque'},
      'bridge': {
        'status': 'RAW_TO_NORMALIZED_COMMAND_CONFIRMED',
        'float32_expected_exact_count': 10,
        'eligible': 10,
        'sign_conflicts': 0,
        'domain_conflicts': 0,
      },
    }
    cache.validate_segment(row, opening, route, 'source', 'split', 'auth')
    for key, value in (('adapter_sha256', 'other'), ('runtime_steer_max', 384), ('role', 'DEVELOPMENT')):
      changed = copy.deepcopy(row)
      changed[key] = value
      with self.assertRaises(ValueError):
        cache.validate_segment(changed, opening, route, 'source', 'split', 'auth')

  def test_projection_matches_original_rollout_oracle(self):
    from openpilot.tools.cyber_autotune import empirical_plant_model as m

    u = np.sin(np.arange(600) * 0.1) + np.cos(np.arange(600) * 0.137)
    y = np.sin(np.arange(600) * 0.012)
    data = [{'u': u, 'y': y, 'blocks': np.zeros(600, dtype=int)}]
    for c in p.family_policy()['candidates']:
      coeff = [0.3, 0.2, 0.1] if c['family'] == 'ARX1' else [float(i) * 0.001 for i in range(26)]
      model = {'config': c, 'coefficients': coeff, 'status': 'FITTED'}
      oracle = m.evaluate(data, model, [0.2, 0.1])
      actual, _ = cv.evaluate(data, model, [0.2, 0.1])
      self.assertEqual(actual['one_step'], oracle['one_step'])
      self.assertEqual(actual['rollout'], oracle['rollout'])


class TestV3ReviewRegression(unittest.TestCase):
  def test_no_eligible_selection_never_refits(self):
    from openpilot.tools.cyber_autotune import empirical_v3_generation as g

    row = record(p.family_policy()['candidates'][0], [1.0, 1.0])
    for f in row['folds']:
      f['evaluation'] = evaluation(count=200)
    self.assertIsNone(g.refit([], cv.choose([row]), {}, None))

  def test_resealed_cache_cannot_replace_pinned_v2_route(self):
    from openpilot.tools.cyber_autotune import empirical_v3_cache as cache

    route = v.routes()[0]
    result = p.seal({'routes': [{'route_id': route['route_id'], 'receipt_sha256': 'original'}]})
    public = {'empirical-plant-v2-model-freeze-v1.json': {'result_sha256': result['receipt_sha256']}}
    receipt = {'route_id': route['route_id'], 'receipt_sha256': 'altered'}
    with self.assertRaises(ValueError):
      cache.validate_parent(result, public, receipt)

  def test_unpinned_v2_result_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_v3_cache as cache

    result = p.seal({'routes': []})
    public = {'empirical-plant-v2-model-freeze-v1.json': {'result_sha256': 'other'}}
    with self.assertRaises(ValueError):
      cache.validate_parent(result, public, {'route_id': 'x', 'receipt_sha256': 'y'})


class TestV3MissingScopeReview(unittest.TestCase):
  def test_missing_primary_rollout_fail_closed(self):
    for horizons in ({}, {'25': evaluation()['rollout']['25']}):
      row = record(p.family_policy()['candidates'][0], [1.0, 1.0])
      row['folds'][0]['evaluation']['rollout'] = horizons
      self.assertFalse(cv.directional_gate(row)['passed'])

  def test_missing_naive_fail_closed(self):
    row = record(p.family_policy()['candidates'][0], [1.0, 1.0])
    row['folds'][0]['evaluation']['one_step'].pop('TRAIN_STATIC_GAIN')
    self.assertFalse(cv.directional_gate(row)['passed'])


class TestV3FiniteReview(unittest.TestCase):
  def test_infinite_reference_cannot_pass(self):
    row = record(p.family_policy()['candidates'][0], [1.0, 1.0])
    row['folds'][0]['evaluation']['one_step']['ZERO_RESPONSE']['RMSE'] = float('inf')
    self.assertFalse(cv.directional_gate(row)['passed'])


class TestV3EndpointFiniteReview(unittest.TestCase):
  def test_nonprimary_endpoint_reference_nonfinite_rejected(self):
    row = record(p.family_policy()['candidates'][0], [1.0, 1.0])
    row['folds'][1]['evaluation']['rollout']['200']['ZERO_RESPONSE']['MAE'] = float('inf')
    self.assertFalse(cv.directional_gate(row)['passed'])


class TestV3IsolationAndAdmission(unittest.TestCase):
  def test_large_route_sample_count_cannot_dominate(self):
    configs = p.family_policy()['candidates']
    a, b = record(configs[0], [0.01, 1.9]), record(configs[1], [1.0, 1.0])
    for row in (a, b):
      row['folds'][0]['evaluation'] = evaluation(row['folds'][0]['evaluation']['one_step']['model']['RMSE'], count=100000)
    self.assertEqual(cv.choose([a, b])['selected']['config'], configs[1])

  def test_unknown_route_never_admitted(self):
    with self.assertRaises(ValueError):
      v.require_route('f' * 64)

  def test_yaw_axis_lag_conflict_blocks(self):
    base = {'admitted': True, 'selection': {'hypothesis': 'YAW_H1', 'gyro_candidate': {'axis': 2, 'sign': 1, 'lag_samples': 0}}}
    for key, value in (('axis', 1), ('sign', -1), ('lag_samples', 5)):
      changed = copy.deepcopy(base)
      changed['selection']['gyro_candidate'][key] = value
      self.assertFalse(cv.yaw_consistent([base, changed]))

  def test_identical_yaw_interpretation_required(self):
    x = {'admitted': True, 'selection': {'hypothesis': 'YAW_H1', 'gyro_candidate': {'axis': 2, 'sign': 1, 'lag_samples': 0}}}
    self.assertTrue(cv.yaw_consistent([x, copy.deepcopy(x)]))

  def test_scoring_never_promotes_holdout(self):
    selection = cv.choose([record(p.family_policy()['candidates'][0], [1.0, 1.0])])
    self.assertEqual(selection['state'], 'STAGE_A_CV_MODEL_SELECTED_DEVELOPMENT_ONLY')
    self.assertNotIn('holdout', selection)
