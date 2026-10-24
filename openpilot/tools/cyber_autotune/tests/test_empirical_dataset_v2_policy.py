import unittest

from openpilot.tools.cyber_autotune import empirical_plant_policy as p


class TestDatasetV2Policy(unittest.TestCase):
  def test_missing_implementation(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as v
    self.assertEqual(v.split_policy()['minimum_routes'], 3)

  def test_route_split_is_disjoint_and_deterministic(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as v
    routes = [{'route_id': p.sha(str(i).encode()), 'status': 'ROUTE_METADATA_COMPATIBLE', 'v1_overlap': False} for i in range(10)]
    a = v.split_routes(routes)
    self.assertEqual(a, v.split_routes(list(reversed(routes))))
    self.assertEqual(len(a['routes']), 10)
    self.assertEqual([sum(x['role'] == role for x in a['routes']) for role in ('TRAIN', 'DEVELOPMENT', 'HOLDOUT')], [6, 2, 2])

  def test_insufficient_routes_do_not_split(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as v
    self.assertEqual(v.split_routes([])['status'], 'ROUTE_DISJOINT_SPLIT_UNAVAILABLE')

  def test_v1_cannot_enter_split(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as v
    with self.assertRaisesRegex(ValueError, 'V1'):
      v.split_routes([{'route_id': 'a'*64, 'status': 'ROUTE_METADATA_COMPATIBLE', 'v1_overlap': True}])

  def test_policies_preserve_frozen_support_and_families(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as v
    self.assertEqual(v.eligibility_policy()['minimum_design_rows'], 201)
    self.assertEqual(v.eligibility_policy()['candidates'], p.family_policy()['candidates'])
    self.assertFalse(v.eligibility_policy()['model_fitting'])

  def test_only_declared_root(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as v
    for name in ('/', '/home', '/unapproved-similar-log', '/unapproved-child', '//server/logs'):
      with self.subTest(name=name), self.assertRaises(ValueError):
        v.approved_root(name)

  def test_command_generation_exact(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as v
    m = v.expected_generation()
    self.assertTrue(v.compatible(m))
    for key, bad in [('source_commit', 'f'*40), ('control_type', 'angle'), ('fingerprint', 'OTHER'), ('carparams_sha256', 'f'*64)]:
      with self.subTest(key=key):
        self.assertFalse(v.compatible({**m, key: bad}))

  def test_unknown_generation_fields_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as v
    with self.assertRaises(ValueError):
      v.compatible({**v.expected_generation(), 'modelV2': True})


if __name__ == '__main__':
  unittest.main()
