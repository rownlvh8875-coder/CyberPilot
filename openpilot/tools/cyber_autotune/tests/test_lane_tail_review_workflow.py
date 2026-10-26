"""Synthetic annotation fixtures only; never saved to public human review."""

import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error

from openpilot.tools.cyber_autotune import lane_tail_review_contract as c
from openpilot.tools.cyber_autotune import lane_tail_review_ui as ui
from openpilot.tools.cyber_autotune import lane_tail_diagnostics as t
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.native_protocol import digest
from openpilot.tools.cyber_autotune.tests.test_lane_tail_review_ui import make_session

try:
  from openpilot.tools.cyber_autotune import lane_tail_review_workflow as w
except ImportError:
  w = None

ROOT = Path(__file__).resolve().parents[4]
MANIFEST_SHA = '82d9c2163afe5bc8d22c6afc534f3a293723625b1072776f41604082f82cea10'


def synthetic_manifest():
  core = unseal(json.loads((ROOT / 'docs/cyberpilot/changes/comma10k-completed-full-human-review-manifest.json').read_text()))
  core['scope'] = 'TEST_ONLY_BROWSER_VALIDATION'
  for frame in core['frames']:
    frame['pred_to_gt'] = t.distribution([0, 10])
    frame['gt_to_pred'] = t.distribution([1, 3])
  return seal(core)


def rows(m, label='COMPONENT_MATCHING_ERROR'):
  return [
    c.make_annotation(
      m, f['frame_id'], label=label, reviewable=True, comment='TEST ONLY', timestamp='2026-10-08T00:00:00Z', human_ack=True, tool_sha256=m['review_tool_sha256']
    )
    for f in m['frames']
  ]


def loader(m):
  def trace(frame):
    return seal(
      {
        'schema': 'BOUND_REVIEW_METRIC_TRACE_V1',
        'run_sha256': m['run_sha256'],
        'frame': frame,
        'original_row_sha256': digest(frame['frame_id'].encode()),
        'pool': {'pred': [0, 10], 'gt': [1, 3], 'paired_spatial_pred': [1, 9]},
      }
    )

  return trace


class TestTailReviewWorkflow(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(w, 'Missing isolated frozen-manifest workflow')
    self.m = synthetic_manifest()

  def test_original_29_manifest_and_tool_unchanged(self):
    m = json.loads((ROOT / 'docs/cyberpilot/changes/comma10k-completed-full-human-review-manifest.json').read_text())
    c.validate_manifest(m)
    self.assertEqual(m['receipt_sha256'], MANIFEST_SHA)
    self.assertEqual(len(m['frames']), 29)
    self.assertEqual(m['review_tool_sha256'], ui.tool_identity())
    self.assertEqual(m['selection_policy_sha256'], c.POLICY_SHA)

  def test_not_started_progress(self):
    result = w.progress(self.m, [])
    self.assertEqual((result['state'], result['reviewed'], result['unreviewed']), ('NOT_STARTED', 0, 29))
    self.assertEqual(result['status'], 'TAIL_HUMAN_REVIEW_PENDING')

  def test_28_of_29_cannot_finalize_or_load_metrics(self):
    a = rows(self.m)[:-1]
    self.assertEqual(w.progress(self.m, a)['state'], 'IN_PROGRESS')
    with self.assertRaisesRegex(ValueError, 'HUMAN_REVIEW_INCOMPLETE'):
      w.aggregate(self.m, a, lambda _: self.fail('Incomplete review opened metric input'))

  def test_29_complete_test_scope_never_human_evidence(self):
    a = rows(self.m)
    self.assertEqual(w.progress(self.m, a)['state'], 'COMPLETE')
    r = w.aggregate(self.m, a, loader(self.m))
    self.assertEqual(r['status'], 'TEST_ONLY_NOT_HUMAN_EVIDENCE')
    self.assertEqual(r['tail_verdict'], 'TAIL_UNRESOLVED')
    self.assertFalse(r['private_input_allowed'])

  def test_duplicate_unknown_and_invalid_label_fail_closed(self):
    a = rows(self.m)
    bad = unseal(a[0])
    bad['frame_id'] = 'imgs/unknown.png'
    label = unseal(a[0])
    label['reviewer_label'] = 'AUTO_PREDICTED'
    for items in ([a[0], a[0]], [seal(bad)], [seal(label)]):
      with self.subTest(items=items), self.assertRaises(ValueError):
        w.progress(self.m, items)

  def test_all_frame_hash_and_schema_tool_bindings_rejected(self):
    a = rows(self.m)[0]
    for key in (
      'image_sha256',
      'mask_sha256',
      'prediction_sha256',
      'metric_result_sha256',
      'review_manifest_sha256',
      'review_schema_sha256',
      'review_tool_sha256',
    ):
      bad = unseal(a)
      bad[key] = 'f' * 64
      with self.subTest(key=key), self.assertRaises(ValueError):
        w.export_review(self.m, [seal(bad)])

  def test_export_deterministic_preserves_original_rows_and_no_fabricated_confidence(self):
    a = rows(self.m)[:3]
    x = w.export_review(self.m, a)
    self.assertEqual(x, w.export_review(self.m, list(reversed(a))))
    self.assertEqual([r['annotation'] for r in x['review_rows']], a)
    self.assertTrue(all(r['reviewer_confidence'] is None for r in x['review_rows']))
    self.assertEqual(x['selection_policy_sha256'], c.POLICY_SHA)
    self.assertEqual(x['review_schema_sha256'], c.SCHEMA_SHA)
    self.assertEqual(x['completed_row_count'], 3)

  def test_aggregation_uses_pooled_samples_not_average_frame_quantiles(self):
    r = w.aggregate(self.m, rows(self.m), loader(self.m))
    cat = r['categories']['COMPONENT_MATCHING_ERROR']
    self.assertEqual((cat['frame_count'], cat['percentage']), (29, 100.0))
    self.assertEqual(cat['metrics']['pred']['sample_count'], 58)
    self.assertEqual(cat['metrics']['pred']['p95'], 10.0)
    self.assertEqual(cat['metrics']['paired_spatial_pred']['p95'], 9.0)
    self.assertEqual(sum(v['frame_count'] for v in r['categories'].values()), 29)
    self.assertEqual(r, w.aggregate(self.m, list(reversed(rows(self.m))), loader(self.m)))
    self.assertNotIn('matching_error_px', r)

  def test_metric_drift_nonfinite_and_stale_trace_rejected(self):
    for mode in ('frame', 'run', 'samples', 'nan'):

      def bad(frame, mode=mode):
        data = unseal(loader(self.m)(frame))
        if mode == 'frame':
          data['frame'] = {**frame, 'metric_result_sha256': 'f' * 64}
        if mode == 'run':
          data['run_sha256'] = 'f' * 64
        if mode == 'samples':
          data['pool']['pred'] = [1, 11]
        if mode == 'nan':
          data['pool']['pred'] = [float('nan')]
        return seal(data)

      with self.subTest(mode=mode), self.assertRaises(ValueError):
        w.aggregate(self.m, rows(self.m), bad)

  def test_descriptive_verdict_rules_no_performance_threshold(self):
    self.assertEqual(w.descriptive_tail({'COMPONENT_MATCHING_ERROR': 15, 'DETECTOR_MISS': 14}, 29), 'TAIL_EXPLAINED_MATCHING_DOMINANT')
    self.assertEqual(w.descriptive_tail({'DETECTOR_MISS': 14, 'GT_EXTRA_MARKING': 15}, 29), 'TAIL_EXPLAINED_GT_AMBIGUITY_DOMINANT')
    self.assertEqual(w.descriptive_tail({'DETECTOR_MISS': 15, 'OTHER': 14}, 29), 'TAIL_UNRESOLVED')
    self.assertEqual(w.descriptive_tail({'DETECTOR_MISS': 10, 'COMPONENT_MATCHING_ERROR': 10, 'REPRESENTATION_MISMATCH': 9}, 29), 'TAIL_EXPLAINED_MIXED')
    self.assertEqual(w.descriptive_tail({'DETECTOR_LOCALIZATION_ERROR': 29}, 29), 'TAIL_EXPLAINED_DETECTOR_DOMINANT')

  def test_public_cardinality_cannot_be_reduced(self):
    m = seal({**unseal(self.m), 'scope': 'PUBLIC_COMMA10K_HUMAN_REVIEW', 'frames': self.m['frames'][:-1]})
    with self.assertRaises(ValueError):
      w.progress(m, [])

  def test_guide_all_taxonomy_and_no_real_truth_claim(self):
    self.assertEqual(set(w.GUIDE), set(c.LABELS))
    self.assertIn('NO INDEPENDENT LANE TRUTH', w.guide_html())
    self.assertIn('not a painted-mask miss automatically', w.guide_html())

  def test_public_29_completion_and_reviewable_accounting_in_memory_only(self):
    # Explicit synthetic unit rows in memory, not public annotation artifacts.
    m = json.loads((ROOT / 'docs/cyberpilot/changes/comma10k-completed-full-human-review-manifest.json').read_text())
    a = rows(m, label='UNRESOLVED')
    bad = unseal(a[0])
    bad['reviewable'] = False
    a[0] = seal(bad)
    result = w.progress(m, a)
    self.assertEqual(result['state'], 'COMPLETE')
    self.assertEqual((result['reviewed'], result['reviewable'], result['unreviewable']), (29, 28, 1))
    self.assertFalse(result['private_input_allowed'])
    self.assertEqual(w.progress(m, a[:-1])['status'], 'TAIL_HUMAN_REVIEW_PENDING')

  def test_public_manifest_cannot_replace_one_frame_or_selection_reason(self):
    m = json.loads((ROOT / 'docs/cyberpilot/changes/comma10k-completed-full-human-review-manifest.json').read_text())
    for key, value in [('image_sha256', 'f' * 64), ('reasons', ['EXTREME_TAIL'])]:
      core = unseal(copy.deepcopy(m))
      core['frames'][0][key] = value
      with self.subTest(key=key), self.assertRaises(ValueError):
        w.progress(seal(core), [])

  def test_unreviewable_wrong_label_and_missing_ack_rejected(self):
    a = unseal(rows(self.m)[0])
    for patch in ({'reviewable': False}, {'human_ack': False}):
      with self.subTest(patch=patch), self.assertRaises(ValueError):
        w.progress(self.m, [seal({**a, **patch})])

  def test_empty_metrics_null_not_zero_and_no_gt_success_claim(self):
    core = unseal(self.m)
    for f in core['frames']:
      f['pred_to_gt'] = t.distribution([])
      f['gt_to_pred'] = t.distribution([])
    m = seal(core)

    def empty(frame):
      d = unseal(loader(m)(frame))
      d['pool'] = {key: [] for key in d['pool']}
      return seal(d)

    result = w.aggregate(m, rows(m), empty)
    metric = result['categories']['COMPONENT_MATCHING_ERROR']['metrics']['pred']
    self.assertEqual(metric['sample_count'], 0)
    self.assertIsNone(metric['p95'])

  def test_score_bins_inherited_and_category_denominators_explicit(self):
    r = w.aggregate(self.m, rows(self.m), loader(self.m))
    self.assertEqual(sum(sum(counts.values()) for counts in r['confidence_category_counts'].values()), 29)
    for values in r['confidence_category_rates'].values():
      self.assertEqual(sum(values.values()), 1.0)
    self.assertEqual(w.POLICY['confidence'], 'UNCHANGED_PUBLIC_SCORE_BINS_FRAME_MEDIAN_SCORE_NOT_THRESHOLD_SELECTION')

  def test_unknown_category_and_incorrect_accounting_rejected(self):
    for counts, total in [({'AUTO': 29}, 29), ({'DETECTOR_MISS': 28}, 29), ({'DETECTOR_MISS': True}, 1)]:
      with self.subTest(counts=counts), self.assertRaises(ValueError):
        w.descriptive_tail(counts, total)

  def test_bound_pool_loader_rejects_index_and_row_drift_and_uses_no_follow(self):
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune import lane_public_storage as s
    from openpilot.tools.cyber_autotune.native_protocol import canonical

    with tempfile.TemporaryDirectory() as directory:
      root = Path(directory)
      run_dir, cache = root / 'run', root / 'cache'
      run_dir.mkdir()
      (run_dir / 'rows').mkdir()
      cache.mkdir()
      frame = self.m['frames'][0]
      protocol = {'pairs': [{'image': f['frame_id'], 'mask': 'masks/' + f['frame_id'].split('/')[1]} for f in self.m['frames']]}
      inputs = {'files': []}
      s.atomic_json(root / 'full-protocol.json', protocol)
      s.atomic_json(root / 'full-input-manifest.json', inputs)
      run = seal(
        {
          'protocol_file_sha256': digest((root / 'full-protocol.json').read_bytes()),
          'manifest_file_sha256': digest((root / 'full-input-manifest.json').read_bytes()),
        }
      )
      s.atomic_json(run_dir / 'run-freeze.json', run)
      record = {'image': frame['frame_id']}
      f = copy.deepcopy(frame)
      f['prediction_sha256'] = digest(canonical(record))
      raw = seal({'value': 1})
      s.atomic_json(run_dir / 'rows/00000.json', raw)
      index = seal({'rows': [{'receipt_sha256': raw['receipt_sha256']}]})
      s.atomic_json(run_dir / 'index.json', index)
      marker = seal({'run_sha256': run['receipt_sha256'], 'index_file_sha256': digest((run_dir / 'index.json').read_bytes())})
      s.atomic_json(run_dir / 'completed.json', marker)
      m = seal({**unseal(self.m), 'run_sha256': run['receipt_sha256'], 'full_completion_sha256': marker['receipt_sha256']})
      core = {
        'ledger': {'receipt_sha256': f['metric_result_sha256']},
        'detector_record': record,
        'pool': {'pred': [0, 10], 'gt': [1, 3], 'paired_spatial_pred': [1, 9]},
      }
      with patch.object(ui, 'require_frozen_metric_sources'), patch.object(w.b, 'verify_resume', return_value=core):
        load = w.bound_metric_loader(run_dir, cache, m)
        self.assertEqual(load(f)['original_row_sha256'], raw['receipt_sha256'])
        s.atomic_json(run_dir / 'rows/00000.json', seal({'value': 2}))
        with self.assertRaises(ValueError):
          load(f)
        s.atomic_json(run_dir / 'rows/00000.json', raw)
        index_bytes = (run_dir / 'index.json').read_bytes()
        (run_dir / 'index.json').unlink()
        (root / 'external-index.json').write_bytes(index_bytes)
        (run_dir / 'index.json').symlink_to(root / 'external-index.json')
        with self.assertRaises(ValueError):
          load(f)

  def test_runtime_workflow_freeze_deletion_is_value_error(self):
    with tempfile.TemporaryDirectory() as temp:
      legacy, _ = make_session(Path(temp))
      session = w.WorkflowSession(legacy)
      (Path(temp) / 'workflow-freeze.json').unlink()
      with self.assertRaises(ValueError):
        session.progress()


class TestTailWorkflowServer(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(w, 'Missing workflow server')
    self.temp = tempfile.TemporaryDirectory()
    self.base_session, _ = make_session(Path(self.temp.name))
    self.session = w.WorkflowSession(self.base_session)
    self.server = w.make_server(self.session)
    self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
    self.thread.start()
    self.base = 'http://127.0.0.1:' + str(self.server.server_port)

  def tearDown(self):
    self.server.shutdown()
    self.server.server_close()
    self.thread.join()
    self.temp.cleanup()

  def get(self, path):
    return urllib.request.urlopen(self.base + path, timeout=5)

  def test_progress_export_guide_and_navigation_controls(self):
    self.assertEqual(json.load(self.get('/api/progress'))['state'], 'NOT_STARTED')
    self.assertEqual(json.load(self.get('/api/export'))['completed_row_count'], 0)
    page = self.get('/').read().decode()
    for element_id in ('progress', 'unresolved', 'worst', 'export'):
      self.assertIn(f'id="{element_id}"', page)
    self.assertIn('REPRESENTATION_MISMATCH', self.get('/guide').read().decode())

  def test_final_attribution_pending_http400(self):
    with self.assertRaises(urllib.error.HTTPError) as error:
      self.get('/api/final-attribution')
    self.assertEqual(error.exception.code, 400)

  def test_session_restart_keeps_freeze_and_progress(self):
    self.base_session.save({'index': 0, 'label': 'UNRESOLVED', 'reviewable': True, 'comment': 'TEST', 'human_ack': True, 'token': self.base_session.token})
    freeze = (Path(self.temp.name) / 'workflow-freeze.json').read_bytes()
    again = w.WorkflowSession(self.base_session)
    self.assertEqual(again.progress()['reviewed'], 1)
    self.assertEqual((Path(self.temp.name) / 'workflow-freeze.json').read_bytes(), freeze)

  def test_workflow_source_drift_and_manifest_drift_rejected(self):
    from unittest.mock import patch

    with patch.object(w, 'workflow_identity', return_value='f' * 64), self.assertRaises(ValueError):
      self.session.progress()
    path = Path(self.temp.name) / 'workflow-freeze.json'
    data = unseal(json.loads(path.read_text()))
    data['review_manifest_sha256'] = 'f' * 64
    path.write_text(json.dumps(seal(data)))
    with self.assertRaises(ValueError):
      w.WorkflowSession(self.base_session)

  def test_origin_rebinding_and_nonloopback_rejected(self):
    with self.assertRaises(ValueError):
      w.make_server(self.session, host='0.0.0.0')
    with self.assertRaises(urllib.error.HTTPError) as error:
      urllib.request.urlopen(urllib.request.Request(self.base + '/api/export', headers={'Host': 'evil.test'}), timeout=5)
    self.assertEqual(error.exception.code, 403)

  def test_persistent_legacy_manifest_deletion_blocks_progress_export_and_save(self):
    (Path(self.temp.name) / 'review-freeze.json').unlink()
    for operation in (self.session.progress, self.session.export, self.session.finalize):
      with self.subTest(operation=operation.__name__), self.assertRaises(ValueError):
        operation()
    with self.assertRaises(urllib.error.HTTPError) as error:
      self.get('/api/progress')
    self.assertEqual(error.exception.code, 400)

  def test_persistent_legacy_manifest_tamper_blocks_workflow(self):
    path = Path(self.temp.name) / 'review-freeze.json'
    original = json.loads(path.read_text())
    core = unseal(original)
    core['review_tool_sha256'] = 'f' * 64
    path.write_text(json.dumps(seal(core)))
    with self.assertRaises(ValueError):
      self.session.export()
