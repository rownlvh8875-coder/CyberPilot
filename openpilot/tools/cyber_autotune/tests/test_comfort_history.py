"""Candidate-history coverage, not acceptance of the rejected comfort tune."""
import importlib
import unittest
from unittest.mock import patch

from openpilot.selfdrive.controls.tests.test_cyber_long_integration import FixtureSubMaster


MODULE = 'openpilot.tools.cyber_autotune.tests.comfort_history_fixture'


class TestComfortHistory(unittest.TestCase):
  def fixture(self):
    self.assertIsNotNone(importlib.util.find_spec(MODULE), 'native cap-history fixture is missing')
    return importlib.import_module(MODULE)

  def test_model_stop_really_follows_cap_and_restarts_from_standstill(self):
    result = self.fixture().run_history('model_stop_restart', arm='cap95')
    self.assertGreater(result['coverage']['cap_before_event_frames'], 0)
    self.assertEqual(result['coverage']['cap_during_demand_frames'], 0)
    self.assertEqual(result['metrics']['stop_episode_count'], 1)
    self.assertEqual(result['metrics']['unresolved_stops'], 0)
    self.assertEqual(result['metrics']['release_without_standstill_count'], 0)
    self.assertEqual(result['metrics']['unresolved_restarts'], 0)
    self.assertGreater(result['metrics']['restart_delay_s'], 0)
    self.assertIsNotNone(result['event_metrics']['stop_latency_s'])

  def test_prior_cap_cannot_override_current_stock_braking_or_stop_arbitration(self):
    fixture = self.fixture()
    for case in fixture.CASES:
      with self.subTest(case=case):
        result = fixture.run_history(case, arm='cap95', delay_s=.30)
        self.assertGreater(result['coverage']['cap_before_event_frames'], 0)
        self.assertGreater(result['coverage']['protected_planner_frames'], 0)
        self.assertEqual(result['coverage']['candidate_planner_frames'], 480)
        self.assertEqual(result['coverage']['observed_planner_frames'], 479)
        self.assertEqual(result['coverage']['initial_reset_frames'], 1)
        self.assertEqual(result['coverage']['protected_arbitration_mismatches'], 0)
        self.assertIsNotNone(result['event_metrics']['negative_request_latency_s'])
        self.assertIsNotNone(result['event_metrics']['negative_applied_latency_s'])
        self.assertFalse(result['vehicle_activation_allowed'])
        self.assertFalse(result['vehicle_qualified'])

  def test_disabled_history_is_native_identity_and_candidate_repeatable(self):
    fixture = self.fixture()
    for case in fixture.CASES:
      for delay in (.03, .15, .30):
        with self.subTest(case=case, delay=delay):
          base = fixture.run_history(case, arm='baseline', delay_s=delay)
          disabled = fixture.run_history(case, arm='disabled', delay_s=delay)
          candidate = fixture.run_history(case, arm='cap95', delay_s=delay)
          self.assertEqual(base, disabled)
          self.assertEqual(candidate, fixture.run_history(case, arm='cap95', delay_s=delay))
          self.assertNotEqual(base['native_trace_sha256'], candidate['native_trace_sha256'])
          self.assertEqual(base['scenario_identity'], candidate['scenario_identity'])

  def test_undeclared_case_arm_and_delay_are_rejected(self):
    fixture = self.fixture()
    for args in ({'case_id': 'unknown'}, {'case_id': 'model_stop_restart', 'arm': 'active'},
                 {'case_id': 'model_stop_restart', 'delay_s': True},
                 {'case_id': 'model_stop_restart', 'delay_s': .1}):
      with self.subTest(args=args), self.assertRaises(ValueError):
        fixture.run_history(**args)

  def test_missing_observation_during_demand_cannot_claim_protected_coverage(self):
    fixture = self.fixture()

    def invalid_during_demand(sm):
      return sm.logMonoTime['modelV2'] < 3_000_000_000

    with patch.object(FixtureSubMaster, 'all_checks', invalid_during_demand), self.assertRaises(ValueError):
      fixture.run_history('model_stop_restart', arm='cap95')

  def test_complete_history_report_preserves_all_cases_and_prior_rejection(self):
    fixture = self.fixture()
    self.assertTrue(hasattr(fixture, 'run_matrix'), 'bound history report is missing')
    report = fixture.run_matrix()
    self.assertEqual(report['case_count'], 9)
    self.assertEqual(report['native_runs'], 54)
    self.assertTrue(report['repeatable'])
    self.assertTrue(report['disabled_exact_identity'])
    self.assertTrue(report['intervention_before_event_covered'])
    self.assertIn('absolute_gap_check', report, 'relative improvement must not hide collision')
    self.assertEqual(report['absolute_gap_check'], 'FAIL')
    self.assertEqual(report['candidate_status'], 'REJECTED_PRIOR_EXPERIMENT')
    self.assertEqual(len(report['comparisons']), 9)
    self.assertFalse(report['vehicle_activation_allowed'])
    self.assertIn('history_fixture_sha256', report['binding'])
    self.assertIn('history_test_sha256', report['binding'])
    for arms in report['variants']:
      for result in arms.values():
        events = result['event_metrics']
        self.assertAlmostEqual(events['negative_applied_latency_s'] - events['negative_request_latency_s'],
                               result['physical_delay_s'])
    for comparison in report['comparisons']:
      if comparison['case_id'] == 'lead_stop_restart':
        self.assertEqual(comparison['absolute_gap_check'], 'FAIL')
        self.assertIn('stop_latency_s', comparison['event_metric_regressions'])
      else:
        self.assertEqual(comparison['absolute_gap_check'], 'NOT_APPLICABLE')


if __name__ == '__main__':
  unittest.main()
