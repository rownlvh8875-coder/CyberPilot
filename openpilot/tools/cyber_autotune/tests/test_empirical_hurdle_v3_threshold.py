"""Exact V3 TP-floor sweep parity; deterministic fixtures, no private inputs."""

import importlib
import unittest
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_scaffold as oracle
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_threshold as v2


def fixture(n=37):
  i = np.arange(n, dtype=np.int64)
  current = (i % 7 - 3).astype(np.int64)
  actual = np.where(i % 4 == 0, (i % 5 + 1) * np.where(i % 8 == 0, 1, -1), 0)
  probability = ((i * 17 % 31) / 31).astype(np.float64)
  delta = np.where(actual != 0, actual * 0.8, np.where(i % 3 == 0, 0.5, 0.125)).astype(np.float64)
  return probability, delta, current, current + actual


class TestV3Threshold(unittest.TestCase):
  def setUp(self):
    try:
      self.t = importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_v3_threshold')
    except ImportError:
      self.fail('bounded V3 threshold engine not implemented')

  def parity(self, arrays, reference=None):
    if reference is None:
      reference = int(np.count_nonzero(arrays[3] != arrays[2])) // 20 + 1
    expected = oracle.evaluate(probability=arrays[0], branch_delta=arrays[1], current=arrays[2], target=arrays[3],
                               reference_tp=reference, role='SYNTHETIC_TRAIN')
    seen = []
    result = self.t.sweep(*arrays, reference_tp=reference, role='TRAIN', observer=lambda t, r: seen.append((t, r)))
    self.assertEqual(seen, expected['rows'])
    self.assertEqual(result['threshold'], expected['threshold'])
    self.assertEqual(result['objective'], expected['selected'])
    self.assertEqual(result['candidate_count'], expected['candidate_count'])
    self.assertEqual(result['feasible_count'], expected['feasible_count'])
    self.assertEqual(result['status'], 'V3_THRESHOLD_FINALIZED' if expected['threshold'] is not None else 'V3_NO_FEASIBLE_THRESHOLD')

  def test_each_threshold_matches_exhaustive_at_reduction_boundaries(self):
    for n in (7, 37, 127, 128, 129, 257, 513):
      with self.subTest(n=n):
        self.parity(fixture(n))

  def test_ties_zero_one_adjacent_probability_and_half_even(self):
    a = list(fixture())
    a[0][:8] = [0.0, -0.0, 1.0, 0.5, 0.5, np.nextafter(0.5, 1), np.nextafter(0.5, 0), 0.0]
    a[1][:8] = [0.5, 1.5, 2.5, -0.5, -1.5, -2.5, -0.0, 0.0]
    self.parity(a)

  def test_all_equal_scores_and_reverse_order(self):
    for reverse in (False, True):
      a = list(fixture())
      a[0][:] = 0.5
      if reverse:
        a = [np.ascontiguousarray(x[::-1]) for x in a]
      self.parity(a)

  def test_tp_boundary_one_below_and_collapse(self):
    a = fixture()
    observed = []
    self.t.sweep(*a, reference_tp=4, role='TRAIN', observer=lambda t, r: observed.append((t, r)))
    for value, row in observed:
      tp = int(np.count_nonzero((a[3] != a[2]) & (a[0] > value)))
      self.assertEqual(row['tp'], tp)
      self.assertEqual(row['feasible'], v2.canonical(*a, value)['feasible'] and tp >= 4)
    self.assertFalse(observed[-1][1]['feasible'])

  def test_real_reference_guard(self):
    a = fixture(101)
    for ref in (0, -1, True, 1000, 1):
      with self.subTest(ref=ref), self.assertRaisesRegex(ValueError, 'V3_REFERENCE_CONFLICT'):
        self.t.sweep(*a, reference_tp=ref, role='TRAIN')

  def test_zero_reference_internal_synthetic_parity_with_v2(self):
    a = fixture(129)
    expected = v2.sweep(*a, role='TRAIN')
    result = self.t._sweep(*a, reference_tp=0)
    self.assertEqual(result['threshold'], expected['threshold'])
    self.assertEqual(result['feasible_count'], expected['feasible_count'])
    objective = dict(result['objective']) if result['objective'] else None
    if objective:
      objective.pop('tp')
    self.assertEqual(objective, expected['objective'])

  def test_no_development_holdout_or_extra_inputs(self):
    for role in ('DEVELOPMENT', 'HOLDOUT', 'TRAIN_DEV'):
      with self.assertRaisesRegex(ValueError, 'TRAIN_ONLY'):
        self.t.sweep(*fixture(), reference_tp=1, role=role)
    with self.assertRaises(TypeError):
      self.t.sweep(*fixture(), reference_tp=1, role='TRAIN', development=[])

  def test_all_static_or_move_fail_without_fallback(self):
    for actual in (0, 1):
      a = list(fixture())
      a[3] = a[2] + actual
      with self.assertRaises(ValueError):
        self.t.sweep(*a, reference_tp=1, role='TRAIN')

  def test_widened_ticks_range_rejected_before_subtraction(self):
    a = list(fixture())
    a[2][0] = np.iinfo(np.int64).max
    with self.assertRaisesRegex(ValueError, 'V3_NUMERICAL_FAILURE'):
      self.t.sweep(*a, reference_tp=1, role='TRAIN')

  def test_exact_tp_floor_boundary_and_all_move_vs_all_static(self):
    arrays = (np.array([.2, .6, .8, .9]), np.array([0., 1., 1., 1.]), np.zeros(4, np.int64), np.array([0, 1, 1, 1], np.int64))
    rows = {}
    result = self.t.sweep(*arrays, reference_tp=2, role='TRAIN', observer=lambda value, row: rows.update({value: row}))
    self.assertTrue(rows[.6]['feasible'])
    self.assertEqual(rows[.6]['tp'], 2)
    self.assertFalse(rows[.8]['feasible'])
    self.assertEqual(rows[.8]['tp'], 1)
    self.assertTrue(rows[0.]['feasible'])
    self.assertFalse(rows[1.]['feasible'])
    self.assertEqual(result['threshold'], .2)

  def test_observer_cannot_mutate_selected_metrics(self):
    arrays = fixture()
    expected = self.t.sweep(*arrays, reference_tp=4, role='TRAIN')
    actual = self.t.sweep(*arrays, reference_tp=4, role='TRAIN', observer=lambda _, row: row.clear())
    self.assertEqual(actual, expected)

  def test_deterministic_rank_calibration_and_move_patterns(self):
    for pattern in ('rare', 'burst', 'isolated'):
      index = np.arange(83)
      move = index % (17 if pattern == 'rare' else 5) == 0 if pattern != 'burst' else index % 13 < 4
      current = np.zeros(83, np.int64)
      target = np.where(move, np.where(index % 2, -2, 1), 0).astype(np.int64)
      for shift in (-.15, 0., .15):
        for reverse in (False, True):
          probability = np.clip(.2 + .5 * (move if not reverse else ~move) + shift + (index % 7) / 100, 0, 1)
          with self.subTest(pattern=pattern, shift=shift, reverse=reverse):
            self.parity((probability, target.astype(np.float64), current, target))

  def test_no_threshold_matrix_allocation(self):
    from contextlib import ExitStack
    from unittest.mock import patch
    arrays = fixture(4099)
    with ExitStack() as stack:
      for name in ('empty', 'zeros', 'ones', 'full'):
        original = getattr(np, name)

        def bounded(shape, *args, _original=original, **kwargs):
          self.assertFalse(isinstance(shape, tuple) and len(shape) > 1)
          return _original(shape, *args, **kwargs)

        stack.enter_context(patch.object(np, name, side_effect=bounded))
      result = self.t.sweep(*arrays, reference_tp=300, role='TRAIN')
    self.assertGreater(result['candidate_count'], 2)
