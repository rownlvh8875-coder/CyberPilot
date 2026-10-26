"""Exact synthetic V2 sweep tests; no private evidence."""

import unittest
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_threshold as v


class TestV2Threshold(unittest.TestCase):
  def fixture(self, n):
    i = np.arange(n)
    current = (i % 31 - 15).astype(np.int64)
    delta = np.select([i % 7 == 0, i % 11 == 0], [1, -3], default=0).astype(np.int64)
    probability = (i % 13 / 12).astype(np.float64)
    branch = (np.sin(i) * 0.7 + delta * 0.6).astype(np.float64)
    return probability, branch, current, current + delta

  def test_exhaustive_threshold_equivalence(self):
    for n in (21, 22, 127, 128, 129, 257, 1001, 8193, 20001):
      with self.subTest(n=n):
        arrays = self.fixture(n)
        rows = []
        result = v.sweep(*arrays, role='TRAIN', observer=lambda t, r, rows=rows: rows.append((t, r)))
        expected = [(t, v.canonical(*arrays, t)) for t in v.candidates(arrays[0])]
        self.assertEqual(rows, expected)
        feasible = [(v.key(t, r), t) for t, r in expected if r['feasible']]
        self.assertEqual(result['threshold'], max(feasible)[1] if feasible else None)

  def test_adjacent_probability_and_error_values(self):
    p, b, c, t = self.fixture(41)
    p[:6] = [0.0, -0.0, 1.0, np.nextafter(0.5, 0.0), 0.5, np.nextafter(0.5, 1.0)]
    b[:6] = [-0.0, 0.0, np.nextafter(0.5, 0.0), 0.5, np.nextafter(0.5, 1.0), 2.5]
    rows = []
    v.sweep(p, b, c, t, role='TRAIN', observer=lambda q, r: rows.append((q, r)))
    self.assertEqual(rows, [(q, v.canonical(p, b, c, t, q)) for q in v.candidates(p)])

  def test_sum_updates_preserve_numpy_reduction(self):
    for n in (7, 8, 127, 129, 8193, 20001, 300001):
      x = np.abs(np.sin(np.arange(n))) * np.exp2(np.arange(n) % 50)
      tree = v.OrderedSum(x)
      self.assertEqual(tree.total().hex(), float(np.sum(x)).hex())
      for index in (0, n // 2, n - 1):
        x[index] = np.nextafter(x[index] / 3, np.inf)
        tree.update(index, x[index])
        self.assertEqual(tree.total().hex(), float(np.sum(x)).hex())

  def test_p95_exact_interpolation(self):
    for n in range(1, 202):
      a = np.abs(np.sin(np.arange(n))) * 7
      b = np.arange(n) % 3.0
      order = v.OrderStatistics(a, b)
      for i in (0, n // 2, n - 1):
        order.replace(a[i], b[i])
        a[i] = b[i]
        self.assertEqual(order.p95().hex(), float(np.percentile(a, 95, method='linear')).hex())

  def test_no_feasible_and_no_fallback(self):
    p, _, c, t = self.fixture(51)
    result = v.sweep(p, np.zeros(len(p)), c, t, role='TRAIN')
    self.assertEqual(result['status'], 'STAGE1_DECISION_POLICY_V2_NO_FEASIBLE_THRESHOLD')
    self.assertIsNone(result['threshold'])

  def test_projected_hold_is_not_projected_false_move(self):
    p = np.array([1.0, 1.0, 1.0])
    c = np.array([0, 2, 4], dtype=np.int64)
    t = np.array([0, 2, 5], dtype=np.int64)
    r = v.canonical(p, np.array([0.4, 0.6, 0.8]), c, t, 0.0)
    self.assertEqual(r['static_projected_false_move_count'], 1)
    self.assertEqual(r['exact_hit_count'], 2)

  def test_objective_key_order(self):
    r = {'exact_hit_count': 4, 'static_projected_false_move_count': 2, 'within_one_tick_count': 8}
    base = v.key(0.3, r)
    for field, value in (('exact_hit_count', 5), ('static_projected_false_move_count', 1), ('within_one_tick_count', 9)):
      self.assertGreater(v.key(0.3, {**r, field: value}), base)
    self.assertGreater(v.key(0.4, r), base)

  def test_leakage_and_invalid_input(self):
    arrays = self.fixture(31)
    for role in ('DEVELOPMENT', 'HOLDOUT', 'POOLED'):
      with self.assertRaises(ValueError):
        v.sweep(*arrays, role=role)
    for name in ('development', 'v1_metrics', 'attribution', 'rollout'):
      with self.assertRaises(TypeError):
        v.sweep(*arrays, role='TRAIN', **{name: {}})
    p, b, c, t = arrays
    for invalid in (np.nan, -0.01, 1.01):
      wrong = p.copy()
      wrong[0] = invalid
      with self.assertRaises(ValueError):
        v.sweep(wrong, b, c, t, role='TRAIN')

  def test_feasibility_each_constraint_and_strict_rmse(self):
    base = {'all_rmse': 2.0, 'move': {'rmse': 3.0, 'mae': 2.0, 'p95': 5.0}}
    move = dict(base['move'])
    self.assertTrue(v.describe(1.0, move, base, 1, 0, 1)['feasible'])
    for all_rmse in (2.0, np.nextafter(2.0, np.inf)):
      self.assertFalse(v.describe(all_rmse, move, base, 1, 0, 1)['feasible'])
    for key in move:
      bad = {**move, key: np.nextafter(move[key], np.inf)}
      self.assertFalse(v.describe(1.0, bad, base, 1, 0, 1)['feasible'])

  def test_unique_probability_all_thresholds(self):
    for n in (21, 129, 257):
      p, b, c, t = self.fixture(n)
      p = np.arange(n, dtype=np.float64) / (n - 1)
      rows = []
      v.sweep(p, b, c, t, role='TRAIN', observer=lambda q, r, rows=rows: rows.append((q, r)))
      self.assertEqual(rows, [(q, v.canonical(p, b, c, t, q)) for q in v.candidates(p)])
