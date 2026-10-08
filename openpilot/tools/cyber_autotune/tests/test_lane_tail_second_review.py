"""TEST_ONLY opaque reviewer registrations and rows; not actual human evidence."""

from pathlib import Path
import tempfile
import unittest

from openpilot.tools.cyber_autotune import lane_public_storage as storage
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.tests.test_lane_tail_review_workflow import synthetic_manifest

try:
  from openpilot.tools.cyber_autotune import lane_tail_second_review as b
except ImportError:
  b = None


ATTEST = {
  'explicit_human_ack': True,
  'not_original_assisted_reviewer': True,
  'prior_ai_suggestion_access': False,
  'prior_assisted_label_access': False,
  'prior_stratum_hypothesis_access': False,
}


class TestSecondReview(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(b, 'Missing isolated blind reviewer contract')
    self.m = synthetic_manifest()
    self.temp = tempfile.TemporaryDirectory()
    self.root = Path(self.temp.name)
    self.p = b.protocol(self.m)

  def tearDown(self):
    self.temp.cleanup()

  def store(self, name='blind'):
    reg = b.register(self.p, 'a' * 64, ATTEST)
    return b.BlindStore(self.m, reg, self.root / name)

  def save(self, store, index=0, label='DETECTOR_MISS', reviewable=True):
    return store.append(index, label=label, reviewable=reviewable, comment='TEST ONLY', timestamp='2026-10-08T00:00:00Z', human_ack=True)

  def test_no_reviewer_means_unavailable_not_fabricated_rows(self):
    pending = b.pending(self.p)
    self.assertEqual(pending['status'], 'INDEPENDENT_BLIND_REVIEWER_UNAVAILABLE')
    self.assertEqual(pending['completed_rows'], 0)
    self.assertIsNone(pending['reviewer_id'])
    self.assertFalse(pending['private_input_allowed'])

  def test_prior_exposure_or_original_reviewer_cannot_register(self):
    for key in ATTEST:
      bad = {**ATTEST, key: not ATTEST[key]}
      with self.subTest(key=key), self.assertRaises(ValueError):
        b.register(self.p, 'a' * 64, bad)
    with self.assertRaises(ValueError):
      b.register(self.p, 'my.name@example.com', ATTEST)

  def test_integer_attestations_are_not_explicit_human_booleans(self):
    for key in ATTEST:
      bad = {**ATTEST, key: int(ATTEST[key])}
      with self.subTest(key=key), self.assertRaises(ValueError):
        b.register(self.p, 'a' * 64, bad)

  def test_complete_blind_test_attribution_uses_separate_rows(self):
    from openpilot.tools.cyber_autotune.tests.test_lane_tail_review_workflow import loader

    store = self.store()
    for i in range(29):
      self.save(store, i, label='COMPONENT_MATCHING_ERROR')
    result = store.finalize(loader(self.m))
    self.assertEqual(result['attribution']['status'], 'TEST_ONLY_NOT_HUMAN_EVIDENCE')
    self.assertEqual(result['attribution']['categories']['COMPONENT_MATCHING_ERROR']['frame_count'], 29)
    self.assertFalse(result['reference_promotable'])

  def test_presentation_whitelist_hides_old_labels_metrics_and_strata(self):
    store = self.store()
    frame = store.presentation(0)
    self.assertEqual(set(frame), {'frame_id', 'image_sha256', 'mask_sha256', 'prediction_sha256'})
    self.assertEqual(frame['frame_id'], self.m['frames'][0]['frame_id'])
    self.assertNotIn('reasons', frame)
    self.assertNotIn('confidence', frame)
    self.assertNotIn('suggested_label', frame)
    self.assertNotIn('reviewer_label', frame)
    self.assertNotIn('pred_to_gt', frame)

  def test_same_store_cannot_import_assisted_artifacts(self):
    legacy = self.root / 'assisted'
    storage.durable_mkdir(legacy)
    storage.atomic_json(legacy / 'ai-assisted-index.json', {'unexpected': True})
    with self.assertRaises(ValueError):
      reg = b.register(self.p, 'a' * 64, ATTEST)
      b.BlindStore(self.m, reg, legacy)

  def test_immutable_save_restart_and_duplicate_rejection(self):
    store = self.store()
    row = self.save(store)
    with self.assertRaises(FileExistsError):
      self.save(store)
    restarted = self.store()
    self.assertEqual(restarted.export()['rows'], [row])
    self.assertFalse(row['ai_suggestion_exposed_before_human_decision'])
    self.assertTrue(row['blind_human_review'])
    self.assertEqual(row['reviewer_id'], 'a' * 64)

  def test_registration_id_and_source_drift_rejected(self):
    store = self.store()
    self.save(store)
    different = b.register(self.p, 'b' * 64, ATTEST)
    with self.assertRaises(ValueError):
      b.BlindStore(self.m, different, store.root)
    bad = unseal(store.registration)
    bad['protocol_sha256'] = 'f' * 64
    with self.assertRaises(ValueError):
      b.BlindStore(self.m, seal(bad), self.root / 'other')

  def test_extra_old_labels_in_registration_rejected(self):
    reg = unseal(b.register(self.p, 'a' * 64, ATTEST))
    reg['assisted_labels'] = ['DETECTOR_MISS']
    with self.assertRaises(ValueError):
      b.BlindStore(self.m, seal(reg), self.root / 'blind')

  def test_unknown_frame_invalid_taxonomy_and_no_human_ack_rejected(self):
    store = self.store()
    for index in (-1, 29, True):
      with self.subTest(index=index), self.assertRaises(ValueError):
        self.save(store, index)
    with self.assertRaises(ValueError):
      self.save(store, label='LANE_CENTERED')
    with self.assertRaises(ValueError):
      store.append(0, label='DETECTOR_MISS', reviewable=True, comment='', timestamp='2026-10-08T00:00:00Z', human_ack=False)

  def test_incomplete_blind_export_cannot_finalize(self):
    store = self.store()
    for i in range(28):
      self.save(store, i)
    self.assertEqual(store.export()['status'], 'INDEPENDENT_BLIND_REVIEW_PENDING')
    with self.assertRaisesRegex(ValueError, 'BLIND_REVIEW_INCOMPLETE'):
      store.finalize(lambda _: self.fail('Incomplete blind review opened metric data'))

  def test_stale_or_missing_indexed_row_rejected(self):
    store = self.store()
    row = self.save(store)
    file = store.root / 'rows/00000.json'
    bad = unseal(row)
    bad['annotation'] = {**bad['annotation'], 'image_sha256': 'f' * 64}
    storage.atomic_json(file, seal(bad))
    with self.assertRaises(ValueError):
      store.export()
    storage.atomic_json(file, row)
    file.unlink()
    with self.assertRaises(ValueError):
      store.export()

  def test_assisted_annotation_cannot_be_blind_row(self):
    store = self.store()
    self.save(store)
    file = store.root / 'rows/00000.json'
    core = unseal(storage.read_json(file))
    core['ai_suggestion_exposed_before_human_decision'] = True
    storage.atomic_json(file, seal(core))
    with self.assertRaises(ValueError):
      store.export()

  def test_complete_test_rows_are_not_actual_blind_evidence(self):
    store = self.store()
    for i in range(29):
      self.save(store, i)
    result = store.export()
    self.assertEqual(result['completed_rows'], 29)
    self.assertEqual(result['status'], 'TEST_ONLY_NOT_HUMAN_EVIDENCE')
    self.assertFalse(result['reference_promotable'])
    self.assertEqual(result, store.export())


if __name__ == '__main__':
  unittest.main()
