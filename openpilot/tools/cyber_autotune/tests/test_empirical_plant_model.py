import importlib.util
import unittest
import numpy as np


class TestModel(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(importlib.util.find_spec('openpilot.tools.cyber_autotune.empirical_plant_model'))
    from openpilot.tools.cyber_autotune import empirical_plant_model as m

    self.m = m

  def run_data(self, n=1200):
    rng = np.random.default_rng(8)
    u = rng.normal(size=n)
    y = np.zeros(n)
    for k in range(6, n):
      y[k] = 0.7 * y[k - 1] + 0.2 * u[k - 5]
    return {'u': u, 'y': y}

  def config(self):
    return {'family': 'ARX1', 'delay_samples': 5, 'input_taps': 1, 'output_lags': 1, 'intercept': True}

  def test_delay_recovery(self):
    fit = self.m.fit([self.run_data()], self.config())
    np.testing.assert_allclose(fit['coefficients'], [0.7, 0.2, 0], atol=1e-14)

  def test_exact_fit_repeat(self):
    self.assertEqual(self.m.fit([self.run_data()], self.config()), self.m.fit([self.run_data()], self.config()))

  def test_unstable_rejected(self):
    self.assertFalse(self.m.stable('ARX1', [1.01, 0.2, 0]))

  def test_fir_stable(self):
    self.assertTrue(self.m.stable('FIR25', [0.1] * 26))

  def test_stats(self):
    r = self.m.statistics([1, -1], [2, 0])
    self.assertEqual(r['RMSE'], 1)
    self.assertEqual(r['BIAS'], 0)
    self.assertEqual(r['count'], 2)

  def test_empty_null(self):
    self.assertIsNone(self.m.statistics([], [])['RMSE'])

  def test_constant_correlation_null(self):
    self.assertIsNone(self.m.statistics([0, 0], [1, 1])['CORRELATION'])

  def test_rollouts(self):
    d = self.run_data()
    f = self.m.fit([d], self.config())
    r = self.m.evaluate([d], f, self.m.static_fit([d]))
    self.assertEqual(set(r['rollout']), {'25', '50', '100', '200'})
    self.assertLess(r['rollout']['100']['model']['RMSE'], 1e-12)

  def test_naives_same_support(self):
    d = self.run_data()
    r = self.m.evaluate([d], self.m.fit([d], self.config()), self.m.static_fit([d]))
    for group in [r['one_step'], *r['rollout'].values()]:
      self.assertEqual(len({x['count'] for x in group.values()}), 1)

  def test_select_development_only(self):
    self.assertRaises(ValueError, self.m.select, {'HOLDOUT': []}, [])

  def test_gap_splits_history(self):
    rows = [{'diagnostic_valid': i != 60, 'speed_bin': 'MEDIUM', 'command_raw': 1, 'angle_deg': 2} for i in range(120)]
    runs = self.m.runs(rows, 'MEDIUM')
    self.assertEqual([len(x['u']) for x in runs], [60, 59])

  def test_bin_boundary(self):
    rows = [{'diagnostic_valid': True, 'speed_bin': 'LOW' if i < 4 else 'HIGH', 'command_raw': 1, 'angle_deg': 2} for i in range(8)]
    self.assertEqual(len(self.m.runs(rows, 'LOW')[0]['u']), 4)

  def test_rank_deficient_unavailable(self):
    self.assertEqual(self.m.fit([{'u': np.ones(400), 'y': np.ones(400)}], self.config())['status'], 'RANK_DEFICIENT')

  def test_insufficient_support(self):
    self.assertEqual(self.m.fit([self.run_data(100)], self.config())['status'], 'INSUFFICIENT_SUPPORT')

  def test_invalid_config_rejected(self):
    c = self.config()
    c['delay_samples'] = 999
    self.assertRaises(ValueError, self.m.fit, [self.run_data()], c)

  def test_residual_correlation(self):
    r = self.m.correlate(np.arange(30), np.arange(30))
    self.assertAlmostEqual(r, 1)

  def test_no_future_target(self):
    d = self.run_data()
    c = self.config()
    a = self.m.design([d], c)[0]
    d['y'][-1] = 1e10
    b = self.m.design([d], c)[0]
    np.testing.assert_array_equal(a, b)

  def test_wrong_sign_worsens(self):
    d = self.run_data()
    f = self.m.fit([d], self.config())
    good = self.m.evaluate([d], f, self.m.static_fit([d]))['one_step']['model']['RMSE']
    d['u'] = -d['u']
    bad = self.m.evaluate([d], f, self.m.static_fit([d]))['one_step']['model']['RMSE']
    self.assertGreater(bad, good)

  def test_dt_is_not_fitted(self):
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    self.assertEqual(p.policy()['dt_ns'], 10_000_000)

  def test_quartile_boundaries_train_only(self):
    d = self.run_data()
    selected = self.m.select({'TRAIN': [d], 'DEVELOPMENT': [d]}, [self.config()])
    cuts = list(selected['train_amplitude_quartiles'])
    other = self.run_data()
    other['u'] *= 100
    self.m.evaluate([other], selected['selected']['model'], selected['static_gain'], cuts)
    self.assertEqual(cuts, selected['train_amplitude_quartiles'])

  def test_correlation_support(self):
    d = self.run_data()
    r = self.m.evaluate([d], self.m.fit([d], self.config()), self.m.static_fit([d]), [0.2, 0.5, 1])
    pair = r['residual_diagnostics']['residual_autocorrelation']['1']
    self.assertEqual(pair['count'], len(d['u']) - 45)

  def test_segment_quarters(self):
    rows = [{'diagnostic_valid': True, 'speed_bin': 'LOW', 'command_raw': i, 'angle_deg': i * 0.1} for i in range(800)]
    blocks = self.m.runs(rows, 'LOW')[0]['blocks']
    self.assertEqual(np.bincount(blocks).tolist(), [200] * 4)

  def test_constant_holdout_serializes(self):
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    f = {'status': 'FITTED', 'config': self.config(), 'coefficients': [0.5, 0.2, 0]}
    d = {'u': np.zeros(400), 'y': np.zeros(400)}
    result = self.m.evaluate([d], f, [0, 0], [0, 0, 0])
    self.assertIsNone(result['residual_diagnostics']['condition_number'])
    p.seal({'schema': 'SYNTHETIC_VALIDATION', 'result': result})

  def test_no_holdout_support_serializes(self):
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    f = {'status': 'FITTED', 'config': self.config(), 'coefficients': [0.5, 0.2, 0]}
    r = self.m.evaluate([], f, [0, 0], [0, 0, 0])
    self.assertEqual(r['one_step']['model']['count'], 0)
    p.seal({'schema': 'SYNTHETIC_VALIDATION', 'result': r})

  def test_rank_deficient_fir_holdout_serializes(self):
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p

    c = p.family_policy()['candidates'][4]
    f = {'status': 'FITTED', 'config': c, 'coefficients': [0.1] * 26}
    d = {'u': np.zeros(400), 'y': np.zeros(400)}
    r = self.m.evaluate([d], f, [0, 0], [0, 0, 0])
    p.seal({'schema': 'SYNTHETIC_VALIDATION', 'result': r})
