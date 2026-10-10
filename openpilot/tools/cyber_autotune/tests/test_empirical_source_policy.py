import unittest
from openpilot.tools.cyber_autotune import empirical_source_policy as policy


class TestSourcePolicy(unittest.TestCase):
  def test_frozen_triage_schema(self):
    self.assertEqual(policy.triage_policy().get('schema'), 'EMPIRICAL_SOURCE_AUDIT_TRIAGE_POLICY_V1')

  def test_numeric_forbidden(self):
    self.assertIs(policy.triage_policy().get('numeric_payload_access'), False)

  def test_primary_all_clean_generations(self):
    b = [{'generation_id': 'a', 'route_count': 2, 'segment_count': 5,
          'status_counts': {'ROUTE_DIFFERENT_SOURCE_GENERATION': 2}}]
    self.assertEqual(policy.selection(b)['primary'], ['a'])

  def test_secondary_ranking(self):
    b = [{'generation_id': k, 'route_count': n, 'segment_count': s,
          'status_counts': {'ROUTE_IDENTITY_AMBIGUOUS': n}} for k, n, s in [('z', 3, 5), ('a', 3, 5), ('b', 4, 1), ('c', 1, 99)]]
    self.assertEqual(policy.selection(b)['secondary_predeclared'], ['b', 'a', 'z'])

  def test_secondary_not_executed_when_primary_pool(self):
    s = policy.selection([{'generation_id': 'a', 'route_count': 1, 'segment_count': 1,
                           'status_counts': {'ROUTE_IDENTITY_AMBIGUOUS': 1}}])
    self.assertEqual(policy.execution_set(s, 2), [])

  def test_schema_only_tertiary(self):
    def bucket(k, reasons):
      return {'generation_id': k, 'route_count': 1, 'segment_count': 1,
              'status_counts': {'ROUTE_CORRUPT_OR_INCOMPLETE': 1}, 'failure_reasons': reasons}
    s = policy.selection([bucket('a', ['UNKNOWN_SOURCE_SCHEMA']), bucket('b', ['TRUNCATED']), bucket('c', [])])
    self.assertEqual(s['tertiary_predeclared'], ['a'])

  def test_primary_limit(self):
    b = [{'generation_id': str(i), 'route_count': 1, 'segment_count': 1,
          'status_counts': {'ROUTE_DIFFERENT_SOURCE_GENERATION': 1}} for i in range(6)]
    with self.assertRaises(ValueError):
      policy.selection(b)

  def test_invalid_pool_count(self):
    with self.assertRaises(ValueError):
      policy.execution_set(policy.selection([]), True)

  def test_future_unknown_not_admitted(self):
    x = dict.fromkeys(policy.future_holdout_contract()['requirements'], True)
    x['no_prior_analysis'] = False
    self.assertFalse(policy.admit_future_holdout(x))

  def test_future_exact_positive(self):
    x = dict.fromkeys(policy.future_holdout_contract()['requirements'], True)
    self.assertTrue(policy.admit_future_holdout(x))

  def test_future_unknown_field(self):
    with self.assertRaises(ValueError):
      policy.admit_future_holdout({'guess': True})

  def test_manifest_scopes(self):
    self.assertEqual(len(policy.manifest()['scope']), 7)
    self.assertFalse(policy.triage_policy()['generic_parser_fallback'])

  def test_forged_policy_receipt_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    row = policy.selection([])
    row['policy_sha256'] = '0' * 64
    with self.assertRaisesRegex(ValueError, 'EXACT_TRIAGE'):
      policy.execution_set(p.seal({k: v for k, v in row.items() if k != 'receipt_sha256'}), 0)

  def test_external_tier_limit_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    row = policy.selection([])
    row['secondary_predeclared'] = list('abcd')
    with self.assertRaisesRegex(ValueError, 'TIER_LIMIT'):
      policy.execution_set(p.seal({k: v for k, v in row.items() if k != 'receipt_sha256'}), 0)

  def test_corrupt_selection_rejected(self):
    row = policy.selection([])
    row['primary'] = ['changed']
    with self.assertRaises(ValueError):
      policy.execution_set(row, 0)

  def test_duplicate_across_tiers_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_plant_policy as p
    row = policy.selection([])
    row['primary'], row['secondary_predeclared'] = ['a'], ['a']
    with self.assertRaisesRegex(ValueError, 'DUPLICATE'):
      policy.execution_set(p.seal({k: v for k, v in row.items() if k != 'receipt_sha256'}), 0)

  def test_maximum_ten_generations(self):
    self.assertEqual(policy.triage_policy()['maximum_generations'], 10)

  def test_old_route_never_holdout(self):
    self.assertFalse(policy.future_holdout_contract()['old_prior_unknown_allowed'])

  def test_future_no_numeric_authorization(self):
    self.assertFalse(policy.future_holdout_contract()['numeric_opening_authorized'])
