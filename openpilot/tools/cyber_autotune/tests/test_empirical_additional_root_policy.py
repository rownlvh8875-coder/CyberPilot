import unittest

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as old


class TestAdditionalRootPolicy(unittest.TestCase):
  def module(self):
    from openpilot.tools.cyber_autotune import empirical_additional_root_policy as v

    return v

  def test_only_two_root_hashes_are_approved(self):
    v = self.module()
    for key in v.ROOTS:
      self.assertEqual(v.require_root_hash(key), key)
    with self.assertRaises(ValueError):
      v.require_root_hash('0' * 64)
    self.assertEqual(len(v.ROOTS), 2)

  def test_generic_windows_alias_matches_wsl(self):
    v = self.module()
    self.assertEqual(v.canonical_alias('E:\\example'), '/mnt/e/example')
    self.assertEqual(v.canonical_alias('/mnt/e/example'), '/mnt/e/example')
    with self.assertRaises(ValueError):
      v.canonical_alias('\\\\server\\share')

  def test_broad_parent_and_relative_roots_rejected(self):
    v = self.module()
    for value in ('/mnt/d', '/', '.', '/tmp/not-approved', 'D:\\'):
      with self.subTest(value=value), self.assertRaises(ValueError):
        v.root_key(value)

  def test_new_policy_preserves_old_receipt(self):
    v = self.module()
    self.assertEqual(v.root_policy()['previous_policy_sha256'], old.root_policy()['receipt_sha256'])
    self.assertFalse(v.root_policy()['numeric_signal_values_opened'])
    self.assertFalse(v.root_policy()['archives_opened'])

  def test_unknown_prior_analysis_never_gets_holdout(self):
    v = self.module()
    rows = [{'route_id': x * 64, 'compatible': True, 'v1_overlap': False, 'prior_analysis': 'UNKNOWN'} for x in 'abc']
    self.assertEqual(v.metadata_split(rows)['status'], 'ROUTE_DISJOINT_SPLIT_UNAVAILABLE')

  def test_three_proven_untouched_routes_split_whole_routes(self):
    v = self.module()
    rows = [{'route_id': x * 64, 'compatible': True, 'v1_overlap': False, 'prior_analysis': 'ATTESTED_NOT_USED'} for x in 'cba']
    result = v.metadata_split(rows)
    self.assertEqual([(r['route_id'][0], r['role']) for r in result['routes']], [('a', 'TRAIN'), ('b', 'DEVELOPMENT'), ('c', 'HOLDOUT')])
    self.assertEqual(result['status'], 'ROUTE_DISJOINT_SPLIT_POSSIBLE')
    self.assertFalse(result['numeric_extraction_authorized'])

  def test_used_v1_or_duplicate_route_cannot_cross_roles(self):
    v = self.module()
    row = {'route_id': 'a' * 64, 'compatible': True, 'v1_overlap': False, 'prior_analysis': 'ATTESTED_NOT_USED'}
    with self.assertRaises(ValueError):
      v.metadata_split([row, row])
    self.assertEqual(v.metadata_split([{**row, 'v1_overlap': True}])['routes'], [])

  def test_source_and_carparams_mismatches_separate(self):
    v = self.module()
    g = old.expected_generation()
    self.assertEqual(v.compatibility(g), 'ROUTE_COMPATIBLE_WITH_V1_GENERATION')
    self.assertEqual(v.compatibility({**g, 'source_commit': 'b' * 40}), 'ROUTE_DIFFERENT_SOURCE_GENERATION')
    self.assertEqual(v.compatibility({**g, 'carparams_sha256': 'b' * 64}), 'ROUTE_DIFFERENT_CARPARAMS')
    self.assertEqual(v.compatibility({**g, 'control_type': 'angle'}), 'ROUTE_INCOMPATIBLE_CONTROL_TYPE')

  def test_incompatible_and_ambiguous_routes_do_not_split(self):
    v = self.module()
    rows = [{'route_id': x * 64, 'compatible': False, 'v1_overlap': False, 'prior_analysis': 'ATTESTED_NOT_USED'} for x in 'abc']
    self.assertEqual(v.metadata_split(rows)['routes'], [])

  def test_firewall_and_minimum_support_unchanged(self):
    row = self.module().root_policy()
    self.assertEqual(row['calibration_blockers'], p.BLOCKERS)
    self.assertFalse(row['ta_execution'])
    self.assertFalse(row['sg_execution'])
    self.assertEqual(old.eligibility_policy()['minimum_design_rows'], 201)
    self.assertFalse(row['production_authority'])
