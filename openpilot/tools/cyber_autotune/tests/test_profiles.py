from dataclasses import FrozenInstanceError, fields, replace
import math
import unittest

from openpilot.tools.cyber_autotune.profiles import (
  ProposalBinding, ProposalInput, UpdateReview, inspect_proposal,
)


def proposal():
  """Synthetic numbers only; these are NOT reviewed vehicle bounds."""
  binding = ProposalBinding('SYNTHETIC_VEHICLE', 'a' * 64, 'synthetic-v1', 'b' * 64, 'b' * 64, 'b' * 64,
                            'c' * 64, 'd' * 64, 'e' * 64, 'f' * 64)
  review = UpdateReview(2., 3., .1, 100, .9, .01, 10., '1' * 64)
  return ProposalInput(binding, 'lat_accel_factor', 'm/s^2/normalized_command', 2.3, 2.31, 100, .95, 10., review)


class TestProposalProfile(unittest.TestCase):
  def assert_blocked(self, value, reason=None):
    result = inspect_proposal(value)
    self.assertFalse(result.contracts_ready)
    self.assertIsNone(result.profile_sha256)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.offline_evaluable)
    if reason:
      self.assertIn(reason, result.reasons)

  def test_structural_success_does_not_authorize_evaluation_or_runtime(self):
    result = inspect_proposal(proposal())
    self.assertTrue(result.contracts_ready)
    self.assertEqual(len(result.profile_sha256), 64)
    self.assertEqual(result.reasons, ('EVIDENCE_VALIDATION_PENDING',))
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.offline_evaluable)
    with self.assertRaises(FrozenInstanceError):
      result.runtime_accepted = True
    with self.assertRaises(ValueError):
      replace(result, offline_evaluable=True)

  def test_exact_delta_and_rate_boundary_pass_but_next_float_does_not(self):
    at_limit = replace(proposal(), proposed_value=2.4)
    self.assertTrue(inspect_proposal(at_limit).contracts_ready)
    self.assert_blocked(replace(at_limit, proposed_value=math.nextafter(2.4, math.inf)))
    slow = replace(at_limit, review=replace(at_limit.review, max_delta=.2, max_rate_per_s=.01))
    self.assert_blocked(replace(slow, proposed_value=2.40000001), 'RATE_LIMIT_EXCEEDED')

  def test_range_bounds_checked_for_baseline_and_proposal(self):
    p = proposal()
    review = replace(p.review, minimum=2.3, maximum=2.31)
    self.assertTrue(inspect_proposal(replace(p, review=review)).contracts_ready)
    self.assert_blocked(replace(p, review=review, proposed_value=2.3100000001), 'OUTSIDE_REVIEWED_RANGE')
    self.assert_blocked(replace(p, review=review, baseline_value=2.2999999999), 'OUTSIDE_REVIEWED_RANGE')

  def test_change_direction_does_not_bypass_rate(self):
    p = replace(proposal(), proposed_value=2.2)
    self.assertTrue(inspect_proposal(p).contracts_ready)
    self.assert_blocked(replace(p, proposed_value=2.1999999999))

  def test_sample_confidence_and_interval_minima(self):
    p = proposal()
    self.assertTrue(inspect_proposal(replace(p, confidence=.9)).contracts_ready)
    self.assert_blocked(replace(p, sample_count=99), 'INSUFFICIENT_SAMPLES')
    self.assert_blocked(replace(p, confidence=.899999999), 'INSUFFICIENT_CONFIDENCE')
    self.assert_blocked(replace(p, elapsed_since_previous_s=9.99999999), 'UPDATE_TOO_SOON')

  def test_missing_or_forged_contract_shape_is_blocked(self):
    for value in (None, {}, [], True, 'candidate'):
      self.assert_blocked(value, 'INVALID_PROPOSAL')
      self.assert_blocked(replace(proposal(), binding=value), 'INVALID_BINDING')
      self.assert_blocked(replace(proposal(), review=value), 'INVALID_REVIEW')

  def test_identity_is_nonempty_and_no_invisible_whitespace(self):
    for name in ('fingerprint', 'parameter_revision'):
      for value in ('', ' ', ' x', 'x ', 'x\ny', None, 3, []):
        with self.subTest(name=name, value=value):
          p = proposal()
          self.assert_blocked(replace(p, binding=replace(p.binding, **{name: value})), 'INVALID_BINDING')

  def test_all_digest_bindings_mandatory(self):
    p = proposal()
    for item in fields(p.binding):
      if item.name.endswith('_sha256'):
        for value in (None, '', 'a' * 63, 'A' * 64, [], 'g' * 64):
          with self.subTest(field=item.name, value=value):
            self.assert_blocked(replace(p, binding=replace(p.binding, **{item.name: value})), 'INVALID_BINDING')
    self.assert_blocked(replace(p, review=replace(p.review, review_sha256=None)), 'INVALID_REVIEW')

  def test_initial_previous_and_rollback_must_bind_baseline(self):
    p = proposal()
    for name in ('previous_profile_sha256', 'rollback_profile_sha256'):
      self.assert_blocked(replace(p, binding=replace(p.binding, **{name: '9' * 64})), 'INVALID_INITIAL_HISTORY')

  def test_noncanonical_units_and_locked_or_unsupported_names_rejected(self):
    p = proposal()
    for name in ('steer_max', 'torque_kp', 'lateral_delay_s', 'user.personality', 'wheelbase', 'latAccelFactor', [], None):
      self.assert_blocked(replace(p, name=name), 'PARAMETER_NOT_PERMITTED')
    for unit in ('Nm', '', None, [], 'm/s^2'):
      self.assert_blocked(replace(p, unit=unit), 'NONCANONICAL_UNIT')

  def test_proposal_numeric_values_are_strict_and_finite(self):
    p = proposal()
    for name in ('baseline_value', 'proposed_value', 'sample_count', 'confidence', 'elapsed_since_previous_s'):
      for value in (True, False, None, '2.31', [], float('nan'), float('inf'), -float('inf'), 10 ** 400):
        with self.subTest(name=name, kind=type(value).__name__):
          self.assert_blocked(replace(p, **{name: value}), 'INVALID_NUMERIC_INPUT')
    self.assert_blocked(replace(p, sample_count=100.))
    self.assert_blocked(replace(p, confidence=1.01))
    self.assert_blocked(replace(p, confidence=-.01))
    self.assert_blocked(replace(p, elapsed_since_previous_s=0.))

  def test_review_numeric_values_are_strict_and_finite(self):
    p = proposal()
    for name in ('minimum', 'maximum', 'max_delta', 'minimum_samples', 'minimum_confidence', 'max_rate_per_s', 'minimum_interval_s'):
      for value in (True, None, '1', [], float('nan'), float('inf'), 10 ** 400):
        with self.subTest(name=name, kind=type(value).__name__):
          self.assert_blocked(replace(p, review=replace(p.review, **{name: value})), 'INVALID_REVIEW')
    for updates in ({'minimum': 3., 'maximum': 2.}, {'minimum': 2., 'maximum': 2.}, {'max_delta': -.1},
                    {'minimum_samples': 0}, {'minimum_samples': 1.5}, {'minimum_confidence': -1.},
                    {'minimum_confidence': 1.01}, {'max_rate_per_s': 0.}, {'minimum_interval_s': 0.}):
      self.assert_blocked(replace(p, review=replace(p.review, **updates)), 'INVALID_REVIEW')

  def test_physical_domain_and_friction_zero(self):
    p = proposal()
    self.assert_blocked(replace(p, review=replace(p.review, minimum=0.)), 'INVALID_PARAMETER_DOMAIN')
    friction = replace(p, name='friction', unit='normalized_command', baseline_value=.01, proposed_value=0.,
                       review=replace(p.review, minimum=0., maximum=.1))
    self.assertTrue(inspect_proposal(friction).contracts_ready)
    self.assert_blocked(replace(friction, review=replace(friction.review, minimum=-.01)), 'INVALID_PARAMETER_DOMAIN')
    self.assert_blocked(replace(friction, proposed_value=-.001))

  def test_digest_repeatable_and_binds_provenance_and_values(self):
    p = proposal()
    original = inspect_proposal(p).profile_sha256
    self.assertEqual(original, inspect_proposal(p).profile_sha256)
    for name in ('fingerprint', 'parameter_revision', 'software_sha256', 'configuration_sha256',
                 'evidence_sha256', 'metric_sha256', 'adapter_sha256'):
      changed = replace(p, binding=replace(p.binding, **{name: '2' * 64}))
      self.assertNotEqual(original, inspect_proposal(changed).profile_sha256)
    for changed in (replace(p, proposed_value=2.32), replace(p, confidence=.96),
                    replace(p, review=replace(p.review, review_sha256='2' * 64))):
      self.assertNotEqual(original, inspect_proposal(changed).profile_sha256)

  def test_equivalent_numeric_types_have_one_identity(self):
    p = replace(proposal(), elapsed_since_previous_s=10)
    self.assertEqual(inspect_proposal(p).profile_sha256, inspect_proposal(proposal()).profile_sha256)
    q = replace(p, review=replace(p.review, minimum=2, maximum=3, minimum_interval_s=10))
    self.assertEqual(inspect_proposal(p).profile_sha256, inspect_proposal(q).profile_sha256)

  def test_tiny_interval_and_huge_finite_values_cannot_overflow_rate_check(self):
    p = proposal()
    tiny = replace(p, elapsed_since_previous_s=1e-300, review=replace(p.review, minimum_interval_s=1e-300))
    self.assert_blocked(tiny, 'RATE_LIMIT_EXCEEDED')
    huge = replace(p, baseline_value=1e308, proposed_value=1.1e308,
                   review=replace(p.review, minimum=1e307, maximum=1.7e308, max_delta=1e308))
    self.assert_blocked(huge, 'RATE_LIMIT_EXCEEDED')

  def test_canonically_equal_range_endpoints_cannot_form_search_space(self):
    p = proposal()
    p = replace(p, baseline_value=1e23, proposed_value=1e23,
                review=replace(p.review, minimum=1e23, maximum=10 ** 23))
    self.assert_blocked(p, 'INVALID_REVIEW')

  def test_equivalent_integer_float_intervals_get_same_decision_and_identity(self):
    p = proposal()
    p = replace(p, elapsed_since_previous_s=10 ** 23, review=replace(p.review, minimum_interval_s=10 ** 23))
    integer_result = inspect_proposal(p)
    decimal_result = inspect_proposal(replace(p, elapsed_since_previous_s=1e23))
    self.assertTrue(integer_result.contracts_ready)
    self.assertTrue(decimal_result.contracts_ready)
    self.assertEqual(integer_result.profile_sha256, decimal_result.profile_sha256)

  def test_zero_confidence_threshold_cannot_disable_existing_guard(self):
    p = proposal()
    self.assert_blocked(replace(p, confidence=0., review=replace(p.review, minimum_confidence=0.)), 'INVALID_REVIEW')


if __name__ == '__main__':
  unittest.main()
