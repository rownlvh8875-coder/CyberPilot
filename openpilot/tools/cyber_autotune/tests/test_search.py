from dataclasses import replace
import unittest

from openpilot.tools.cyber_autotune.search import GridReview, preview_grid
from openpilot.tools.cyber_autotune.tests.test_profiles import proposal


def grid():
  return GridReview((2.2, 2.3, 2.4), .1, 3, '2' * 64)


class TestGridPreview(unittest.TestCase):
  def assert_blocked(self, template, review, reason=None):
    result = preview_grid(template, review)
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.entries, ())
    self.assertIsNone(result.preview_sha256)
    self.assertFalse(result.candidate_generation_allowed)
    self.assertFalse(result.offline_evaluable)
    self.assertFalse(result.runtime_accepted)
    if reason:
      self.assertIn(reason, result.reasons)

  def test_ordered_all_or_nothing_preview_keeps_baseline(self):
    result = preview_grid(proposal(), grid())
    self.assertEqual(result.status, 'STRUCTURAL_PREVIEW')
    self.assertEqual(tuple(entry.value for entry in result.entries), (2.2, 2.3, 2.4))
    self.assertEqual(tuple(entry.changed for entry in result.entries), (True, False, True))
    self.assertEqual(len({entry.profile_sha256 for entry in result.entries}), 3)
    self.assertEqual(result.reasons, ('EVIDENCE_VALIDATION_PENDING',))
    self.assertFalse(result.candidate_generation_allowed)
    self.assertFalse(result.offline_evaluable)
    self.assertFalse(result.runtime_accepted)

  def test_identity_repeats_and_binds_grid_review_and_provenance(self):
    p, g = proposal(), grid()
    first = preview_grid(p, g).preview_sha256
    self.assertEqual(first, preview_grid(p, g).preview_sha256)
    for changed in (replace(g, max_proposals=4), replace(g, review_sha256='3' * 64), replace(g, step=.05)):
      result = preview_grid(p, changed)
      self.assertEqual(result.status, 'STRUCTURAL_PREVIEW')
      self.assertNotEqual(first, result.preview_sha256)
    changed = replace(p, binding=replace(p.binding, evidence_sha256='4' * 64))
    self.assertNotEqual(first, preview_grid(changed, g).preview_sha256)

  def test_malformed_input_does_not_raise_or_iterate(self):
    for value in (None, {}, [], 'grid', True):
      self.assert_blocked(value, grid(), 'INVALID_TEMPLATE')
      self.assert_blocked(proposal(), value, 'INVALID_GRID_REVIEW')
    def forbidden_iterator():
      raise AssertionError('Iterable must not be consumed')
      yield 2.3
    self.assert_blocked(proposal(), replace(grid(), values=forbidden_iterator()), 'INVALID_GRID_VALUES')
    for values in ([], [2.3], {}, (), (2.3, '2.4'), (2.3, None)):
      self.assert_blocked(proposal(), replace(grid(), values=values))

  def test_budget_and_hard_ceiling_precede_value_checks(self):
    for budget in (0, -1, True, 3., 257, 10 ** 400, None):
      self.assert_blocked(proposal(), replace(grid(), max_proposals=budget), 'INVALID_GRID_BUDGET')
    self.assert_blocked(proposal(), replace(grid(), max_proposals=2), 'GRID_BUDGET_EXCEEDED')
    self.assert_blocked(proposal(), replace(grid(), values=(None,) * 257, max_proposals=256), 'GRID_BUDGET_EXCEEDED')

  def test_nonfinite_bool_and_unrepresentable_values_are_blocked(self):
    for value in (True, float('nan'), float('inf'), 10 ** 400):
      self.assert_blocked(proposal(), replace(grid(), values=(2.3, value)), 'INVALID_GRID_VALUES')
      self.assert_blocked(proposal(), replace(grid(), step=value), 'INVALID_GRID_STEP')

  def test_values_must_be_strictly_ascending_and_unique(self):
    for values in ((2.3, 2.2, 2.4), (2.3, 2.3), (2, 2., 2.3), (1e23, 10 ** 23)):
      self.assert_blocked(proposal(), replace(grid(), values=values), 'GRID_NOT_STRICTLY_ASCENDING')

  def test_review_baseline_and_step_are_mandatory(self):
    self.assert_blocked(proposal(), replace(grid(), values=(2.2, 2.4)), 'BASELINE_MISSING')
    for value in (None, '', 'A' * 64):
      self.assert_blocked(proposal(), replace(grid(), review_sha256=value), 'INVALID_GRID_REVIEW')
    for step in (0., -.1, '0.1', None):
      self.assert_blocked(proposal(), replace(grid(), step=step), 'INVALID_GRID_STEP')
    for values in ((2.3, 2.31), (2.3, 2.4000000000000004)):
      self.assert_blocked(proposal(), replace(grid(), values=values), 'OFF_GRID_VALUE')

  def test_invalid_value_blocks_entire_grid_instead_of_silent_filtering(self):
    result = preview_grid(proposal(), replace(grid(), values=(2.3, 2.4, 2.5)))
    self.assertEqual(result.entries, ())
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('DELTA_LIMIT_EXCEEDED', result.reasons)
    self.assertIn('RATE_LIMIT_EXCEEDED', result.reasons)
    self.assertIsNone(result.preview_sha256)

  def test_forbidden_parameter_never_produces_preview(self):
    for name in ('steer_max', 'safety.accel_min', 'lateral_delay_s', 'user.personality'):
      self.assert_blocked(replace(proposal(), name=name), grid(), 'PARAMETER_NOT_PERMITTED')

  def test_range_only_violation_blocks_entire_grid_at_either_end(self):
    p = proposal()
    bounded = replace(p, review=replace(p.review, minimum=2.25, maximum=2.35))
    # Both outside values still meet the unchanged delta/rate/step limits.
    for values in ((2.2, 2.3), (2.3, 2.4)):
      with self.subTest(values=values):
        review = replace(grid(), values=values)
        self.assert_blocked(bounded, review, 'OUTSIDE_REVIEWED_RANGE')
        self.assertEqual(preview_grid(bounded, review).reasons, ('OUTSIDE_REVIEWED_RANGE',))
    endpoints = replace(p, review=replace(p.review, minimum=2.2, maximum=2.4))
    result = preview_grid(endpoints, grid())
    self.assertEqual(result.status, 'STRUCTURAL_PREVIEW')
    self.assertEqual(tuple(entry.value for entry in result.entries), (2.2, 2.3, 2.4))
    self.assertFalse(result.offline_evaluable)
    self.assertFalse(result.candidate_generation_allowed)
    self.assertFalse(result.runtime_accepted)


if __name__ == '__main__':
  unittest.main()
