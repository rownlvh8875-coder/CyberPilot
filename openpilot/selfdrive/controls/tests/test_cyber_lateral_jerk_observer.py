import unittest
from dataclasses import FrozenInstanceError

from openpilot.selfdrive.controls.lib.cyber_lateral.jerk_observer import (
  FutureLateralProfile, observe_jerk_persistence,
)


class TestFutureLateralJerkObserver(unittest.TestCase):
  def test_constant_positive_and_negative_jerk(self):
    positive = observe_jerk_persistence(
      FutureLateralProfile((0., 1., 2.), (0., 2., 4.)), (0., 1., 2.),
    )
    negative = observe_jerk_persistence(
      FutureLateralProfile((0., 1., 2.), (0., -3., -6.)), (0., 1., 2.),
    )
    self.assertTrue(positive.valid)
    self.assertEqual(positive.jerk_mps3, (2., 2.))
    self.assertTrue(positive.sign_consistent)
    self.assertEqual(positive.minimum_abs_jerk_mps3, 2.)
    self.assertTrue(negative.valid)
    self.assertEqual(negative.jerk_mps3, (-3., -3.))
    self.assertEqual(negative.minimum_abs_jerk_mps3, 3.)

  def test_mixed_sign_jerk_is_invalid_not_averaged(self):
    observation = observe_jerk_persistence(
      FutureLateralProfile((0., 1., 2.), (0., 1., 0.)), (0., 1., 2.),
    )
    self.assertFalse(observation.valid)
    self.assertEqual(observation.reason, 'mixed_sign_jerk')
    self.assertEqual(observation.jerk_mps3, (1., -1.))
    self.assertFalse(observation.sign_consistent)
    self.assertIsNone(observation.minimum_abs_jerk_mps3)

  def test_profile_rejects_duplicate_time_or_nonzero_origin(self):
    with self.assertRaises(ValueError):
      FutureLateralProfile((0., 0.), (0., 1.))
    with self.assertRaises(ValueError):
      FutureLateralProfile((0.1, 1.), (0., 1.))

  def test_out_of_range_query_fails_closed(self):
    observation = observe_jerk_persistence(
      FutureLateralProfile((0., 1., 2.), (0., 1., 2.)), (0., 1., 3.),
    )
    self.assertFalse(observation.valid)
    self.assertEqual(observation.reason, 'query_outside_profile')
    self.assertEqual(observation.jerk_mps3, ())

  def test_too_few_samples_or_queries_fail_closed(self):
    profile = FutureLateralProfile((0.,), (0.,))
    self.assertEqual(observe_jerk_persistence(profile, (0., 1.)).reason, 'insufficient_profile')
    profile = FutureLateralProfile((0., 1.), (0., 1.))
    self.assertEqual(observe_jerk_persistence(profile, (0.,)).reason, 'insufficient_queries')

  def test_query_contract_and_results_are_immutable(self):
    profile = FutureLateralProfile((0., 1.), (0., 1.))
    invalid_queries = ((0., 0.), (0., float('nan')), [0., 1.])
    for query in invalid_queries:
      with self.subTest(query=query):
        self.assertEqual(observe_jerk_persistence(profile, query).reason, 'invalid_queries')

    result = observe_jerk_persistence(profile, (0., 1.))
    with self.assertRaises(FrozenInstanceError):
      result.valid = False
    with self.assertRaises(FrozenInstanceError):
      profile.time_s = (0.,)


if __name__ == '__main__':
  unittest.main()
