"""AI fixture rows are TEST_ONLY; never human evidence."""

from pathlib import Path
import tempfile
import unittest

from openpilot.tools.cyber_autotune import lane_tail_review_workflow as w
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.tests.test_lane_tail_review_workflow import synthetic_manifest
from openpilot.tools.cyber_autotune.tests.test_lane_tail_review_ui import make_session

try:
  from openpilot.tools.cyber_autotune import lane_tail_ai_review as a
except ImportError:
  a = None


def vision(m):
  return [{'frame': f, 'views': dict.fromkeys(a.VIEWS, 'a' * 64), 'same_point_error': {'p95': 2.0}} for f in m['frames']]


def suggestion(m, experiment, index=0, label='UNRESOLVED'):
  return a.make_suggestion(
    m,
    experiment,
    index,
    label=label,
    secondary=[],
    confidence='LOW',
    reason='TEST ONLY visible evidence placeholder',
    observations=['TEST_ONLY'],
    answers=dict.fromkeys(a.QUESTIONS, 'UNRESOLVED'),
    model={'provider': 'TEST_ONLY', 'model': 'TEST_ONLY', 'version': None, 'invocation': 'TEST_ONLY'},
    timestamp='2026-10-08T12:00:00Z',
  )


class TestAIReview(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(a, 'Missing isolated AI suggestion tier')
    self.temp = tempfile.TemporaryDirectory()
    self.root = Path(self.temp.name)
    self.legacy, self.m = make_session(self.root / 'human')
    self.ex = a.freeze_experiment(self.m, vision(self.m), 'AI_REVIEW_TEST')
    self.store = a.SuggestionStore(self.m, self.ex, self.root / 'ai')
    self.workflow = w.WorkflowSession(self.legacy)
    self.session = a.AIReviewSession(self.workflow, self.store)

  def tearDown(self):
    self.temp.cleanup()

  def save(self, index=0, label='UNRESOLVED'):
    return self.session.save({'index': index, 'label': label, 'reviewable': True, 'comment': 'TEST ONLY', 'human_ack': True, 'token': self.legacy.token})

  def reveal(self, index=0, allow=False):
    return self.session.reveal({'index': index, 'allow_assisted': allow, 'token': self.legacy.token})

  def test_ai_29_zero_human_stays_pending(self):
    m = synthetic_manifest()
    ex = a.freeze_experiment(m, vision(m), 'AI_REVIEW_TEST')
    store = a.SuggestionStore(m, ex, self.root / '29')
    for i in range(29):
      store.append(suggestion(m, ex, i))
    self.assertEqual(store.status()['suggestions'], 29)
    self.assertEqual(w.progress(m, [])['status'], 'TAIL_HUMAN_REVIEW_PENDING')
    with self.assertRaisesRegex(ValueError, 'HUMAN_REVIEW_INCOMPLETE'):
      w.aggregate(m, [], lambda _: self.fail('AI must not replace human rows'))

  def test_immutable_ai_rows_and_stale_binding(self):
    row = suggestion(self.m, self.ex)
    self.store.append(row)
    with self.assertRaises(FileExistsError):
      self.store.append(row)
    for field in ('image_sha256', 'mask_sha256', 'prediction_sha256', 'metric_result_sha256', 'review_manifest_sha256'):
      bad = unseal(row)
      bad[field] = 'f' * 64
      with self.subTest(field=field), self.assertRaises(ValueError):
        a.validate_suggestion(self.m, self.ex, seal(bad))

  def test_unknown_label_unknown_frame_human_leak_and_metric_only_rejected(self):
    row = suggestion(self.m, self.ex)
    for key, value in (('frame_id', 'imgs/unknown.png'), ('suggested_label', 'LANE_CENTERED'), ('human_label', 'UNRESOLVED'), ('visual_evidence', [])):
      bad = unseal(row)
      bad[key] = value
      with self.subTest(key=key), self.assertRaises(ValueError):
        a.validate_suggestion(self.m, self.ex, seal(bad))
    bad = unseal(row)
    bad['secondary_possible_labels'] = ['UNRESOLVED', 'UNRESOLVED']
    with self.assertRaises(ValueError):
      a.validate_suggestion(self.m, self.ex, seal(bad))

  def test_missing_vision_view_and_private_frame_forbidden(self):
    v = vision(self.m)
    del v[0]['views']['original']
    with self.assertRaises(ValueError):
      a.freeze_experiment(self.m, v, 'AI_REVIEW_TEST')
    v = vision(self.m)
    v[0]['frame']['frame_id'] = '/private/route.png'
    with self.assertRaises(ValueError):
      a.freeze_experiment(self.m, v, 'AI_REVIEW_TEST')

  def test_hidden_by_default_and_warning_before_save(self):
    self.store.append(suggestion(self.m, self.ex))
    with self.assertRaisesRegex(ValueError, 'ASSISTED_WARNING_ACK_REQUIRED'):
      self.reveal()
    self.assertEqual(self.session.provenance()['exposures'], [])
    self.assertNotIn('suggested_label', str(self.session.public_state()))

  def test_before_save_assisted_persists_and_cannot_launder_on_restart(self):
    self.store.append(suggestion(self.m, self.ex))
    out = self.reveal(allow=True)
    self.assertEqual(out['provenance']['mode'], 'ASSISTED_HUMAN_REVIEW')
    saved = self.save()
    restarted = a.AIReviewSession(self.workflow, self.store)
    self.assertEqual(restarted.provenance()['exposures'][0]['mode'], 'ASSISTED_HUMAN_REVIEW')
    self.assertEqual(self.reveal()['provenance']['mode'], 'ASSISTED_HUMAN_REVIEW')
    self.assertEqual(self.legacy.annotations(), [])
    self.assertEqual(self.session.assisted_rows(), [saved['annotation']])

  def test_save_before_reveal_blind_and_human_immutable(self):
    self.store.append(suggestion(self.m, self.ex))
    saved = self.save()
    result = self.reveal()
    self.assertEqual(result['provenance']['mode'], 'BLIND_HUMAN_REVIEW')
    self.assertEqual(result['provenance']['human_annotation_sha256'], saved['annotation']['receipt_sha256'])
    with self.assertRaises(FileExistsError):
      self.save(label='DETECTOR_MISS')
    self.assertEqual(self.legacy.annotations()[0]['reviewer_label'], 'UNRESOLVED')

  def test_human_save_without_ai_and_missing_ai_no_exposure(self):
    self.save()
    with self.assertRaisesRegex(ValueError, 'AI_SUGGESTION_UNAVAILABLE'):
      self.reveal()
    self.assertEqual(self.session.provenance()['exposures'], [])

  def test_missing_or_corrupt_exposure_index_fails_closed(self):
    self.store.append(suggestion(self.m, self.ex))
    self.reveal(allow=True)
    index = self.legacy.output / 'ai-exposure-index.json'
    original = index.read_bytes()
    index.unlink()
    with self.assertRaises(ValueError):
      self.session.provenance()
    index.write_bytes(original)
    path = self.legacy.output / 'ai-exposures' / '00000.json'
    path.unlink()
    with self.assertRaises(ValueError):
      a.AIReviewSession(self.workflow, self.store)

  def test_missing_ai_row_index_and_experiment_drift(self):
    self.store.append(suggestion(self.m, self.ex))
    (self.store.output / 'rows' / '00000.json').unlink()
    with self.assertRaises(ValueError):
      self.store.rows()
    other = a.freeze_experiment(self.m, vision(self.m), 'AI_REVIEW_OTHER')
    with self.assertRaises(ValueError):
      a.SuggestionStore(self.m, other, self.store.output)

  def test_comparison_incomplete_never_finalize(self):
    self.store.append(suggestion(self.m, self.ex))
    r = self.session.comparison()
    self.assertEqual(r['status'], 'TAIL_HUMAN_REVIEW_PENDING')
    self.assertFalse(r['reference_promotable'])
    with self.assertRaisesRegex(ValueError, 'HUMAN_REVIEW_INCOMPLETE'):
      self.session.finalize()

  def test_comparison_confusion_accounting_and_determinism(self):
    for i in range(len(self.m['frames'])):
      self.store.append(suggestion(self.m, self.ex, i, 'DETECTOR_MISS'))
      self.save(i, 'DETECTOR_MISS' if i == 0 else 'UNRESOLVED')
    r = self.session.comparison()
    self.assertEqual(r, self.session.comparison())
    n = len(self.m['frames'])
    self.assertEqual(r['exact_agreements'], 1)
    self.assertEqual(sum(sum(v.values()) for v in r['confusion_matrix'].values()), n)
    self.assertEqual(r['exact_agreement_rate'], 1 / n)
    self.assertEqual(len(r['unresolved_disagreements']), n - 1)
    self.assertFalse(r['human_replacement_allowed'])
    self.assertFalse(r['private_input_allowed'])

  def test_assisted_cannot_be_independent_final_attribution(self):
    self.store.append(suggestion(self.m, self.ex))
    self.reveal(allow=True)
    for i in range(len(self.m['frames'])):
      self.save(i)
    with self.assertRaisesRegex(ValueError, 'ASSISTED_HUMAN_NOT_BLIND'):
      self.session.finalize()

  def test_ai_freeze_symlink_tamper_and_extra_row_rejected(self):
    path = self.store.output / 'experiment-freeze.json'
    original = path.read_bytes()
    path.unlink()
    target = self.root / 'copy.json'
    target.write_bytes(original)
    path.symlink_to(target)
    with self.assertRaises(ValueError):
      self.store.rows()


class TestAIReviewHTTP(unittest.TestCase):
  def test_no_suggestion_get_and_reveal_origin_nonce_required(self):
    import json
    import threading
    import urllib.request
    import urllib.error

    with tempfile.TemporaryDirectory() as tmp:
      legacy, m = make_session(Path(tmp) / 'human')
      ex = a.freeze_experiment(m, vision(m), 'AI_REVIEW_TEST')
      store = a.SuggestionStore(m, ex, Path(tmp) / 'ai')
      store.append(suggestion(m, ex))
      session = a.AIReviewSession(w.WorkflowSession(legacy), store)
      server = a.make_server(session)
      thread = threading.Thread(target=server.serve_forever)
      thread.start()
      base = 'http://127.0.0.1:' + str(server.server_port)

      def request(path, body=None, origin=None):
        return urllib.request.urlopen(
          urllib.request.Request(
            base + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={'Content-Type': 'application/json', **({'Origin': origin} if origin else {})},
          ),
          timeout=5,
        )

      try:
        state = json.load(request('/api/ai-state'))
        self.assertNotIn('suggested_label', str(state))
        with self.assertRaises(urllib.error.HTTPError):
          request('/api/ai-reveal/0')
        body = {'index': 0, 'allow_assisted': True, 'token': legacy.token}
        with self.assertRaises(urllib.error.HTTPError) as cm:
          request('/api/ai-reveal', body)
        self.assertEqual(cm.exception.code, 403)
        with self.assertRaises(urllib.error.HTTPError) as cm:
          request('/api/ai-reveal', {**body, 'token': 'wrong'}, base)
        self.assertEqual(cm.exception.code, 403)
        out = json.load(request('/api/ai-reveal', body, base))
        self.assertEqual(out['provenance']['mode'], 'ASSISTED_HUMAN_REVIEW')
        with self.assertRaises(ValueError):
          a.make_server(session, host='0.0.0.0')
      finally:
        server.shutdown()
        server.server_close()
        thread.join()


class TestExposureIsolation(unittest.TestCase):
  setUp = TestAIReview.setUp
  tearDown = TestAIReview.tearDown
  reveal = TestAIReview.reveal

  def test_entire_exposure_state_deletion_does_not_reset_assisted(self):
    self.store.append(suggestion(self.m, self.ex))
    self.reveal(allow=True)
    body = {'index': 0, 'label': 'DETECTOR_MISS', 'reviewable': True, 'comment': 'TEST ONLY', 'human_ack': True, 'token': self.legacy.token}
    self.session.save(body)
    for name in ('ai-exposure-freeze.json', 'ai-exposure-index.json'):
      (self.legacy.output / name).unlink()
    (self.legacy.output / 'ai-exposures/00000.json').unlink()
    with self.assertRaises(ValueError):
      a.AIReviewSession(self.workflow, self.store)

  def test_assisted_never_enters_legacy_human_completion_export(self):
    self.store.append(suggestion(self.m, self.ex))
    self.reveal(allow=True)
    self.session.save({'index': 0, 'label': 'DETECTOR_MISS', 'reviewable': True, 'comment': 'TEST ONLY', 'human_ack': True, 'token': self.legacy.token})
    self.assertEqual(self.legacy.annotations(), [])
    self.assertEqual(self.workflow.export()['completed_row_count'], 0)
    out = self.session.export()
    self.assertEqual(len(out['assisted_human_rows']), 1)
    self.assertEqual(self.session.public_state()['human_counts'], {'blind_canonical': 0, 'assisted': 1, 'total': 1, 'expected': len(self.m['frames'])})
    self.assertEqual(out['provenance']['exposures'][0]['mode'], 'ASSISTED_HUMAN_REVIEW')
    self.assertFalse(out['blind_independent_complete'])
    with self.assertRaisesRegex(ValueError, 'HUMAN_REVIEW_INCOMPLETE'):
      self.workflow.finalize()

  def test_unbound_existing_human_rows_cannot_initialize_ai_provenance(self):
    with tempfile.TemporaryDirectory() as tmp:
      legacy, m = make_session(Path(tmp) / 'human')
      legacy.save({'index': 0, 'label': 'UNRESOLVED', 'reviewable': False, 'comment': 'TEST ONLY', 'human_ack': True, 'token': legacy.token})
      ex = a.freeze_experiment(m, vision(m), 'AI_REVIEW_NEW_TEST')
      store = a.SuggestionStore(m, ex, Path(tmp) / 'ai')
      with self.assertRaises(ValueError):
        a.AIReviewSession(w.WorkflowSession(legacy), store)


class TestAIAdmissionEdges(unittest.TestCase):
  setUp = TestAIReview.setUp
  tearDown = TestAIReview.tearDown
  reveal = TestAIReview.reveal

  def test_legacy_manual_save_of_assisted_frame_quarantines_companion(self):
    self.store.append(suggestion(self.m, self.ex))
    self.reveal(allow=True)
    self.legacy.save({'index': 0, 'label': 'UNRESOLVED', 'reviewable': True, 'comment': 'TEST ONLY', 'human_ack': True, 'token': self.legacy.token})
    with self.assertRaises(ValueError):
      self.session.export()

  def test_writer_lease_conflict_never_creates_blind_or_assisted_row(self):
    from openpilot.tools.cyber_autotune import lane_public_storage as s

    with s.writer_lease(self.legacy.output):
      with self.assertRaises(ValueError):
        self.session.save({'index': 0, 'label': 'UNRESOLVED', 'reviewable': True, 'comment': 'TEST ONLY', 'human_ack': True, 'token': self.legacy.token})
    self.assertEqual(self.session.all_human_rows(), [])

  def test_invalid_human_ack_does_not_mutate_any_store(self):
    with self.assertRaises(ValueError):
      self.session.save({'index': 0, 'label': 'UNRESOLVED', 'reviewable': True, 'comment': 'TEST ONLY', 'human_ack': False, 'token': self.legacy.token})
    self.assertEqual(self.session.all_human_rows(), [])

  def test_ai_and_exposure_orphans_recover_but_indexed_loss_blocks(self):
    from openpilot.tools.cyber_autotune import lane_public_storage as s

    row = suggestion(self.m, self.ex)
    s.atomic_json(self.store.output / 'rows/00000.json', row)
    reopened = a.SuggestionStore(self.m, self.ex, self.store.output)
    self.assertEqual(reopened.rows(), [row])
    self.session.store = reopened
    self.reveal(allow=True)
    self.assertEqual(a.AIReviewSession(self.workflow, reopened).provenance()['exposures'][0]['mode'], 'ASSISTED_HUMAN_REVIEW')

  def test_store_inside_repo_is_rejected_even_relative_path(self):
    with self.assertRaises(ValueError):
      a.SuggestionStore(self.m, self.ex, 'docs/cyberpilot/changes/no-ai-store')

  def test_high_confidence_disagreement_accounted_without_human_change(self):
    for i in range(len(self.m['frames'])):
      row = unseal(suggestion(self.m, self.ex, i, 'DETECTOR_MISS'))
      row['ai_confidence'] = 'HIGH'
      self.store.append(seal(row))
      self.session.save({'index': i, 'label': 'UNRESOLVED', 'reviewable': True, 'comment': 'TEST ONLY', 'human_ack': True, 'token': self.legacy.token})
    result = self.session.comparison()
    self.assertEqual(result['exact_agreement_rate'], 0.0)
    self.assertEqual(len(result['high_confidence_disagreements']), len(self.m['frames']))
    self.assertTrue(all(r['reviewer_label'] == 'UNRESOLVED' for r in self.legacy.annotations()))
