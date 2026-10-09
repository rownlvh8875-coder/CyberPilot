import copy
import unittest

from openpilot.tools.cyber_autotune import controller_plant_evidence as e
from openpilot.tools.cyber_autotune import controller_plant_authority as a


class TestAuthorityEvidence(unittest.TestCase):
  def fixture(self):
    base = []
    for i in range(5):
      row = dict.fromkeys(e.SIGNALS.values(), 0.0)
      row.update(time_s=i * .01, pose_x_m=(i + 1) * .1, speed_mps=10., phase='entry', saturated=False)
      base.append(row)
    candidate = copy.deepcopy(base)
    candidate[0]['requested_torque'] = .01
    candidate[2]['applied_normalized_torque'] = .01
    return base, candidate

  def test_stage_accounting(self):
    base, candidate = self.fixture()
    r = e.decompose(base, candidate, .01, 2)
    self.assertEqual(len(r['signals']), len(e.SIGNALS) + 1)
    self.assertEqual(r['delay_aligned_applied_residual_max'], 0.)

  def test_current_alias_zero(self):
    base, _ = self.fixture()
    r = e.decompose(base, base, .01, 2)
    self.assertTrue(all(x['maximum_absolute'] == 0 for x in r['signals'].values()))

  def test_desired_identical(self):
    base, candidate = self.fixture()
    self.assertEqual(e.decompose(base, candidate, .01, 2)['signals']['desired_curvature']['maximum_absolute'], 0.)

  def test_delay_failure_visible(self):
    base, candidate = self.fixture()
    candidate[2]['applied_normalized_torque'] = 0.
    self.assertEqual(e.decompose(base, candidate, .01, 2)['delay_aligned_applied_residual_max'], .01)

  def test_time_mismatch(self):
    base, candidate = self.fixture()
    candidate[2]['time_s'] = .03
    with self.assertRaises(ValueError):
      e.decompose(base, candidate, .01, 2)

  def test_pose_integral(self):
    base, candidate = self.fixture()
    for i, row in enumerate(candidate):
      row['pose_y_m'] = (i + 1) * .02
    r = e.decompose(base, candidate, .01, 2)
    self.assertAlmostEqual(r['signals']['pose_velocity']['signed_integral'], .1)

  def test_policy_source_mismatch(self):
    policy = a.seal({'schema': 'TEST', 'sources': {}})
    with self.assertRaises(ValueError):
      e.validate_policy(policy)

  def test_readiness_gates(self):
    r = e.readiness('a' * 64)
    self.assertEqual(r['reference_status'], 'INDEPENDENT_REFERENCE_UNAVAILABLE')
    self.assertEqual(r['candidate_verdicts']['V2'], 'REJECTED')
    self.assertFalse(r['candidate_acceptance_allowed'])
    self.assertIsNone(r['independent_meter_result'])

  def test_model_source_not_input(self):
    self.assertEqual(e.SIGNALS['requested_torque'], 'requested_torque')
    self.assertNotIn('modelV2', e.SIGNALS.values())

  def test_positive_control_is_not_candidate(self):
    self.assertEqual(e.CONTROL_ROLE, 'TEST_DIAGNOSTIC_ONLY_NOT_CANDIDATE')

  def test_policy_historical_binding(self):
    policy = e.prepare_policy()
    self.assertEqual(len(policy['recoveries']), 70)
    self.assertEqual(policy['speeds_mps'], [5., 17.5, 25.])
    self.assertEqual(policy['steps'], 401)
    self.assertEqual(policy['amplitudes'][0], 0.)
    e.validate_policy(policy)

  def test_coordinated_amplitude_tamper_rejected(self):
    policy = e.prepare_policy()
    policy['historical_delta_distribution']['p95'] = .1
    policy['amplitudes'][2] = .1
    with self.assertRaises(ValueError):
      e.validate_policy(a.seal(policy))
