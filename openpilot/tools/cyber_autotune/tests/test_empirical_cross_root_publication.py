import copy
import unittest

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as old


def fixture():
  from openpilot.tools.cyber_autotune import empirical_cross_root_inventory as reader

  generation = {**old.expected_generation(), 'source_commit': 'f' * 40}
  routes = reader.group(
    [
      {
        'source_sha256': 'b' * 64,
        'root_id': 'c' * 64,
        'lineage_sha256': 'd' * 64,
        'ordinal': 0,
        'kind': 'rlog.zst',
        'metadata': {
          'generation': generation,
          'logger_start_sha256': 'a' * 64,
          'first_ns': 100,
          'last_ns': 199,
          'envelope_counts': {'carState': 2, 'carOutput': 2},
        },
      }
    ],
    set(),
  )
  return p.seal(
    {
      'schema': 'EMPIRICAL_CROSS_ROOT_PRIVATE_INVENTORY_V1',
      'binding_sha256': 'e' * 64,
      'snapshot': {
        'c' * 64: {
          'logs': [{}],
          'file_count': 3,
          'media_file_count_metadata_only': 1,
          'archive_count': 0,
          'log_counts': {'rlog.zst': 1},
          'log_bytes': {'rlog.zst': 10},
        }
      },
      'routes': routes,
      'generation_buckets': reader.buckets(routes),
      'failed_file_count': 0,
      'failure_source_hashes': [],
      'selected_metadata_files': 1,
      'alternative_log_files_not_parsed': 0,
      'numeric_payloads_opened': False,
      'numeric_coverage': None,
      'holdout_opened': False,
      'split': {'status': 'ROUTE_DISJOINT_SPLIT_UNAVAILABLE', 'routes': []},
    }
  )


class TestCrossRootPublication(unittest.TestCase):
  def module(self):
    from openpilot.tools.cyber_autotune import empirical_cross_root_publication as pub

    return pub

  def test_distinct_other_generation_requires_audit_not_merge(self):
    docs = self.module().derive(fixture())
    ready = docs['empirical-dataset-v2-route-readiness-v1.json']
    self.assertEqual(ready['status'], 'ADDITIONAL_ROUTES_FOUND_DIFFERENT_GENERATION')
    self.assertEqual(ready['next'], 'EMPIRICAL_DATASET_V2_NEW_SOURCE_AUDIT_REQUIRED')
    self.assertIsNone(ready['numeric_coverage'])

  def test_unknown_prior_analysis_is_not_untouched(self):
    docs = self.module().derive(fixture())
    inv = docs['empirical-dataset-v2-cross-root-inventory-v1.json']
    self.assertEqual(inv['compatible_untouched_routes'], 0)
    self.assertEqual(inv['prior_analysis_unknown_routes'], 1)

  def test_private_fields_do_not_escape_projection(self):
    private = fixture()
    body = {k: v for k, v in private.items() if k != 'receipt_sha256'}
    body['operator_private_note'] = 'PRIVATE_NOTE'
    docs = self.module().derive(p.seal(body))
    text = p.canonical(docs)
    for key in (b'PRIVATE_NOTE', b'logger_start_sha256', b'first_ns', b'source_key', b'mtime_ns'):
      self.assertNotIn(key, text)

  def test_numeric_or_holdout_access_receipt_is_rejected(self):
    for field, value in (('numeric_payloads_opened', True), ('numeric_coverage', {}), ('holdout_opened', True)):
      private = fixture()
      body = {k: v for k, v in private.items() if k != 'receipt_sha256'}
      body[field] = value
      with self.subTest(field=field), self.assertRaises(ValueError):
        self.module().derive(p.seal(body))

  def test_historical_states_and_authority_preserved(self):
    docs = self.module().derive(fixture())
    ready = docs['empirical-dataset-v2-route-readiness-v1.json']
    self.assertEqual(ready['calibration_blockers'], p.BLOCKERS)
    self.assertEqual(ready['historical']['v2'], 'REJECTED')
    self.assertEqual(ready['historical']['v2_violations'], 37)
    self.assertFalse(ready['ta_execution'])
    self.assertFalse(ready['sg_execution'])
    self.assertFalse(ready['production_authority'])
    self.assertFalse(ready['holdout_opened'])

  def test_no_numeric_split_or_model_artifacts_created(self):
    docs = self.module().derive(fixture())
    self.assertEqual(
      set(docs),
      {
        'empirical-dataset-v2-root-policy-v2.json',
        'empirical-dataset-v2-cross-root-inventory-v1.json',
        'empirical-dataset-v2-generation-buckets-v1.json',
        'empirical-dataset-v2-route-readiness-v1.json',
      },
    )

  def test_tampered_private_receipt_rejected(self):
    private = copy.deepcopy(fixture())
    private['failed_file_count'] = 9
    with self.assertRaises(ValueError):
      self.module().derive(private)


class TestPublicMetadataRedaction(unittest.TestCase):
  def test_malformed_source_commit_cannot_escape_distribution(self):
    from openpilot.tools.cyber_autotune import empirical_cross_root_publication as pub

    private = fixture()
    body = {k: v for k, v in private.items() if k != 'receipt_sha256'}
    body['routes'][0]['generation']['source_commit'] = 'PRIVATE_SOURCE_IDENTIFIER'
    body['generation_buckets'][0]['generation']['source_commit'] = 'PRIVATE_SOURCE_IDENTIFIER'
    result = pub.derive(p.seal(body))
    self.assertNotIn(b'PRIVATE_SOURCE_IDENTIFIER', p.canonical(result))

  def test_fake_ready_counts_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_cross_root_publication as pub

    private = fixture()
    body = {k: v for k, v in private.items() if k != 'receipt_sha256'}
    body['routes'][0]['untouched'] = True
    with self.assertRaises(ValueError):
      pub.derive(p.seal(body))

  def test_nested_bucket_note_cannot_escape_whitelist(self):
    from openpilot.tools.cyber_autotune import empirical_cross_root_publication as pub

    private = fixture()
    body = {k: v for k, v in private.items() if k != 'receipt_sha256'}
    body['generation_buckets'][0]['operator_note'] = 'PRIVATE_NESTED_NOTE'
    result = pub.derive(p.seal(body))
    self.assertNotIn(b'PRIVATE_NESTED_NOTE', p.canonical(result))

  def test_unknown_public_status_is_rejected(self):
    from openpilot.tools.cyber_autotune import empirical_cross_root_publication as pub

    private = fixture()
    body = {k: v for k, v in private.items() if k != 'receipt_sha256'}
    body['routes'][0]['status'] = 'PRIVATE_STATUS_NOTE'
    with self.assertRaises(ValueError):
      pub.derive(p.seal(body))

  def test_export_public_counts_and_hashes_validated(self):
    from openpilot.tools.cyber_autotune import empirical_cross_root_publication as pub

    for key, value in (
      ('export_log_file_count', 'PRIVATE'),
      ('export_log_file_count', -1),
      ('export_inventory_sha256', 'PRIVATE'),
      ('parent_inventory_sha256', 'PRIVATE'),
    ):
      body = {k: v for k, v in fixture().items() if k != 'receipt_sha256'}
      body[key] = value
      with self.subTest(key=key), self.assertRaises(ValueError):
        pub.derive(p.seal(body))

  def test_combined_unknown_routes_cannot_inherit_ready_split(self):
    from openpilot.tools.cyber_autotune import empirical_cross_root_publication as pub

    body = {k: v for k, v in fixture().items() if k != 'receipt_sha256'}
    body['split'] = {'status': 'ROUTE_DISJOINT_SPLIT_POSSIBLE', 'routes': []}
    with self.assertRaises(ValueError):
      pub.derive(p.seal(body))
