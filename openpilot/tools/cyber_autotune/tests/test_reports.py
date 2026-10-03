from dataclasses import replace
import json
import unittest

from openpilot.tools.cyber_autotune.reports import build_report, render_markdown
from openpilot.tools.cyber_autotune.tests.test_comparison import change_arm, experiment


class TestComparisonReports(unittest.TestCase):
  def test_report_is_json_safe_repeatable_and_never_promotes(self):
    p, receipts = experiment()
    report = build_report(p, receipts)
    encoded = json.dumps(report, sort_keys=True, allow_nan=False)
    self.assertEqual(encoded, json.dumps(build_report(p, tuple(reversed(receipts))), sort_keys=True, allow_nan=False))
    self.assertEqual(report['schema'], 'cyber-validation-local-v1')
    self.assertEqual(report['scope'], 'ASSERTED_RECEIPTS_ONLY')
    self.assertEqual(report['status'], 'REVALIDATION_REQUIRED')
    self.assertEqual(report['runs'], {'expected': 6, 'received': 6, 'repeatable_groups': 1})
    self.assertEqual(report['authority'], {'offline_evaluable': False, 'runtime_accepted': False, 'promotable': False})
    self.assertTrue(report['checks']['local_nonregression_pass'])
    self.assertTrue(report['checks']['primary_improvement_pass'])
    self.assertEqual(report['identities']['review_sha256'], '9' * 64)
    self.assertEqual(report['identities']['group_sha256s'], ['8' * 64])
    self.assertEqual(report['identities']['source_sha256s'], ['1' * 64, '2' * 64, '3' * 64])

  def test_fail_timeout_and_invalid_input_are_explicit(self):
    p, receipts = experiment()
    failure = build_report(p, change_arm(receipts, hard_violations=('ACTUATOR_LIMIT',)))
    self.assertEqual(failure['status'], 'FAIL')
    self.assertIn('HARD_CONSTRAINT_VIOLATION', {item['code'] for item in failure['issues']})
    timeout = build_report(p, change_arm(receipts, outcome='TIMEOUT', metrics=None, trace_sha256=None, coverage=()))
    self.assertEqual(timeout['status'], 'REVALIDATION_REQUIRED')
    self.assertIn('RUN_TIMEOUT', {item['code'] for item in timeout['issues']})
    self.assertEqual(build_report(None, receipts)['issues'][0]['code'], 'INVALID_POLICY')

  def test_invalid_private_strings_are_not_echoed(self):
    p, receipts = experiment()
    secret = '/mnt/d/private/GPS/route-secret'
    for policy, inputs in ((replace(p, review_sha256=secret), receipts),
                           (p, (replace(receipts[0], arm=secret), *receipts[1:])),
                           (p, change_arm(receipts, hard_violations=(secret,)))):
      self.assertNotIn(secret, json.dumps(build_report(policy, inputs)))
      self.assertNotIn(secret, render_markdown(policy, inputs))

  def test_markdown_explains_local_limitations_and_failure_context(self):
    p, receipts = experiment()
    rendered = render_markdown(p, receipts)
    self.assertIn('REVALIDATION_REQUIRED', rendered)
    self.assertIn('ASSERTED_RECEIPTS_ONLY', rendered)
    self.assertIn('6 / 6', rendered)
    self.assertIn('runtime_accepted: false', rendered)
    self.assertIn('EVIDENCE_AUTHENTICITY_PENDING', rendered)
    self.assertIn('not native replay or vehicle qualification', rendered)
    failed = render_markdown(p, change_arm(receipts, hard_violations=('PLANT_DOMAIN',)))
    self.assertIn('Status: FAIL', failed)
    self.assertIn('CYBER_CANDIDATE', failed)
    self.assertIn('PLANT_DOMAIN', failed)

  def test_no_improvement_is_failure_not_a_successful_noop(self):
    report = build_report(*experiment(improved=False))
    self.assertEqual(report['status'], 'FAIL')
    self.assertTrue(report['checks']['local_nonregression_pass'])
    self.assertFalse(report['checks']['primary_improvement_pass'])


if __name__ == '__main__':
  unittest.main()
