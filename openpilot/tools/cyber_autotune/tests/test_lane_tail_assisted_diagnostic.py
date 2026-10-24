"""Synthetic public-contract fixtures only; no actual human annotations are created."""

import copy
import unittest

from openpilot.tools.cyber_autotune import lane_tail_ai_review as a
from openpilot.tools.cyber_autotune import lane_tail_diagnostics as t
from openpilot.tools.cyber_autotune import lane_tail_review_contract as c
from openpilot.tools.cyber_autotune import lane_tail_review_workflow as w
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.tests.test_lane_tail_ai_review import vision
from openpilot.tools.cyber_autotune.tests.test_lane_tail_review_workflow import synthetic_manifest, rows, loader

try:
  from openpilot.tools.cyber_autotune import lane_tail_assisted_diagnostic as d
except ImportError:
  d = None


def fixture():
  m = synthetic_manifest()
  inputs = vision(m)
  for v in inputs:
    v['same_point_error'] = t.distribution([1, 9])
  ex = a.freeze_experiment(m, inputs, 'AI_REVIEW_TEST')
  human = rows(m, 'DETECTOR_MISS')
  suggestions, exposures = [], []
  for i, f in enumerate(m['frames']):
    suggestions.append(
      a.make_suggestion(
        m,
        ex,
        i,
        label='DETECTOR_MISS',
        secondary=[],
        confidence='HIGH' if i < 10 else 'MEDIUM' if i < 20 else 'LOW',
        reason='TEST ONLY',
        observations=['TEST ONLY'],
        answers=dict.fromkeys(a.QUESTIONS, 'UNRESOLVED'),
        model=a.TEST_MODEL,
        timestamp='2026-10-07T23:00:00Z',
      )
    )
    exposures.append(
      seal(
        {
          'schema': 'AI_FIRST_EXPOSURE_V1',
          'frame': f,
          'manifest_sha256': m['receipt_sha256'],
          'tool_sha256': a.tool_identity(),
          'first_suggestion_sha256': suggestions[-1]['receipt_sha256'],
          'first_experiment_sha256': ex['receipt_sha256'],
          'human_annotation_sha256': None,
          'mode': 'ASSISTED_HUMAN_REVIEW',
          'timestamp': '2026-10-07T23:00:00Z',
        }
      )
    )
  provenance = seal(
    {
      'schema': 'AI_HUMAN_PROVENANCE_V1',
      'review_manifest_sha256': m['receipt_sha256'],
      'exposures': exposures,
      'scope_limit': a.POLICY['scope_limit'],
      'reference_promotable': False,
    }
  )
  ai_progress = seal(
    {
      'schema': 'AI_PREREVIEW_PROGRESS_V1',
      'status': 'AI_PREREVIEW_COMPLETE',
      'suggestions': 29,
      'expected': 29,
      'human_label': None,
      'experiment_sha256': ex['receipt_sha256'],
      'tier': 'SUPPORTING_DIAGNOSTIC_ONLY',
      'private_input_allowed': False,
      'reference_promotable': False,
    }
  )
  export = seal(
    {
      'schema': 'AI_AWARE_HUMAN_EXPORT_V1',
      'blind_human_export': w.export_review(m, []),
      'assisted_human_rows': human,
      'provenance': provenance,
      'ai_progress': ai_progress,
      'review_manifest_sha256': m['receipt_sha256'],
      'blind_independent_complete': False,
      'private_input_allowed': False,
      'reference_promotable': False,
    }
  )
  return m, export, ex, suggestions


class TestAssistedDiagnostic(unittest.TestCase):
  def setUp(self):
    self.assertIsNotNone(d, 'Missing isolated assisted diagnostic aggregation')
    self.m, self.export, self.ex, self.ai = fixture()

  def aggregate(self, export=None, metric_loader=None):
    return d.aggregate(self.m, export or self.export, self.ex, self.ai, metric_loader or loader(self.m))

  def test_exact_29_accounting_and_zero_blind_completion(self):
    result = self.aggregate()
    self.assertEqual(result['schema'], 'ASSISTED_HUMAN_TAIL_DIAGNOSTIC_V1')
    self.assertEqual((result['reviewed'], result['reviewable'], result['unreviewable']), (29, 29, 0))
    self.assertEqual(set(result['categories']), set(c.LABELS))
    self.assertEqual(sum(x['frame_count'] for x in result['categories'].values()), 29)
    self.assertEqual(result['categories']['DETECTOR_MISS']['percentage'], 100.0)
    self.assertFalse(result['blind_independent_complete'])

  def test_metrics_preserve_three_pooled_directions(self):
    result = self.aggregate()
    metric = result['categories']['DETECTOR_MISS']['metrics']
    self.assertEqual(metric['pred_to_gt']['sample_count'], 58)
    self.assertEqual((metric['pred_to_gt']['median'], metric['pred_to_gt']['p95']), (5.0, 10.0))
    self.assertEqual((metric['same_point_2d']['median'], metric['same_point_2d']['p95']), (5.0, 9.0))
    self.assertEqual((metric['gt_to_pred']['median'], metric['gt_to_pred']['p95']), (2.0, 3.0))

  def test_not_mean_of_frame_percentiles(self):
    core = unseal(self.m)
    for i, f in enumerate(core['frames']):
      f['pred_to_gt'] = t.distribution([1000] if i == 0 else [0] * 9)
    self.m = seal(core)
    inputs = vision(self.m)
    for v in inputs:
      v['same_point_error'] = t.distribution([1, 9])
    self.ex = a.freeze_experiment(self.m, inputs, 'AI_REVIEW_POOL_TEST')
    # Rebind synthetic rows/exposures by constructing the real fixture with this manifest.
    other = fixture_for_manifest(self.m, self.ex)
    self.export, self.ai = other

    def load(f):
      i = self.m['frames'].index(f)
      x = unseal(loader(self.m)(f))
      x['pool']['pred'] = [1000] if i == 0 else [0] * 9
      return seal(x)

    metric = self.aggregate(metric_loader=load)['metrics']['pred_to_gt']
    self.assertEqual((metric['sample_count'], metric['median'], metric['p95']), (253, 0.0, 0.0))

  def test_incomplete_cannot_open_metric_input(self):
    bad = unseal(copy.deepcopy(self.export))
    bad['assisted_human_rows'] = bad['assisted_human_rows'][:-1]
    with self.assertRaisesRegex(ValueError, 'ASSISTED_REVIEW_INCOMPLETE'):
      self.aggregate(seal(bad), lambda _: self.fail('Incomplete review opened metric input'))

  def test_stale_duplicate_and_unknown_human_rows_rejected(self):
    for field in ('image_sha256', 'prediction_sha256', 'metric_result_sha256', 'review_manifest_sha256', 'frame_id'):
      bad = unseal(copy.deepcopy(self.export))
      row = unseal(bad['assisted_human_rows'][0])
      row[field] = 'imgs/unknown.png' if field == 'frame_id' else 'f' * 64
      bad['assisted_human_rows'][0] = seal(row)
      with self.subTest(field=field), self.assertRaises(ValueError):
        self.aggregate(seal(bad))
    bad = unseal(copy.deepcopy(self.export))
    bad['assisted_human_rows'][-1] = bad['assisted_human_rows'][0]
    with self.assertRaises(ValueError):
      self.aggregate(seal(bad))

  def test_exposure_after_decision_or_missing_or_duplicate_rejected(self):
    for mode in ('late', 'missing', 'duplicate', 'blind', 'stale'):
      bad = unseal(copy.deepcopy(self.export))
      p = unseal(bad['provenance'])
      e = unseal(p['exposures'][0])
      if mode == 'late':
        e['timestamp'] = '2026-10-09T00:00:00Z'
      if mode == 'blind':
        e['mode'] = 'BLIND_HUMAN_REVIEW'
      if mode == 'stale':
        e['first_suggestion_sha256'] = 'f' * 64
      p['exposures'][0] = seal(e)
      if mode == 'missing':
        p['exposures'].pop()
      if mode == 'duplicate':
        p['exposures'][-1] = p['exposures'][0]
      bad['provenance'] = seal(p)
      with self.subTest(mode=mode), self.assertRaises(ValueError):
        self.aggregate(seal(bad))

  def test_metric_run_summary_and_nonfinite_drift_rejected(self):
    for field in ('run_sha256', 'frame', 'samples', 'same_point'):

      def bad(f, field=field):
        x = unseal(loader(self.m)(f))
        if field == 'run_sha256':
          x[field] = 'f' * 64
        elif field == 'frame':
          x[field] = {**f, 'mask_sha256': 'f' * 64}
        elif field == 'samples':
          x['pool']['pred'] = [float('nan')]
        else:
          x['pool']['paired_spatial_pred'] = [1, 100]
        return seal(x)

      with self.subTest(field=field), self.assertRaises(ValueError):
        self.aggregate(metric_loader=bad)

  def test_no_detector_promotion_private_or_sealed_gate(self):
    result = self.aggregate()
    self.assertEqual(result['detector_verdict'], 'DETECTOR_QUALIFICATION_BLOCKED')
    self.assertFalse(result['reference_promotable'])
    self.assertFalse(result['private_input_allowed'])
    self.assertFalse(result['meter_conversion'])
    self.assertFalse(result['causal_metric_difference_computed'])
    self.assertEqual(result['qualification'], 'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE')

  def test_all_bindings_assisted_not_blind_and_no_source_mutation(self):
    before = copy.deepcopy((self.export, self.ai))
    result = self.aggregate()
    self.assertEqual(before, (self.export, self.ai))
    self.assertEqual(len(result['row_provenance']), 29)
    for row in result['row_provenance']:
      self.assertTrue(row['ai_suggestion_exposed_before_human_decision'])
      self.assertTrue(row['assisted_human_review'])
      self.assertFalse(row['blind_human_review'])
      self.assertEqual(len(row['human_annotation_sha256']), 64)

  def test_assisted_concordance_confidence_accounting(self):
    bad = unseal(copy.deepcopy(self.export))
    row = unseal(bad['assisted_human_rows'][-1])
    row['reviewer_label'] = 'UNRESOLVED'
    bad['assisted_human_rows'][-1] = seal(row)
    result = self.aggregate(seal(bad))['concordance']
    self.assertEqual(result['schema'], 'ASSISTED_REVIEW_CONCORDANCE_V1')
    self.assertEqual((result['exact_agreements'], result['exact_agreement_rate']), (28, 28 / 29))
    self.assertEqual(result['by_ai_confidence']['HIGH']['agreements'], 10)
    self.assertEqual(result['by_ai_confidence']['MEDIUM']['agreements'], 10)
    self.assertEqual(result['by_ai_confidence']['LOW']['agreements'], 8)
    self.assertEqual(len(result['human_unresolved_frame_ids']), 1)
    self.assertEqual(result['ai_unresolved_frame_ids'], [])
    self.assertEqual(sum(sum(v.values()) for v in result['confusion_matrix'].values()), 29)
    self.assertFalse(result['independent_ai_accuracy_estimate'])

  def test_empty_category_unavailability_is_null_not_zero_error(self):
    result = self.aggregate()
    empty = result['categories']['GT_EXTRA_MARKING']
    self.assertEqual(empty['frame_count'], 0)
    self.assertIsNone(empty['metrics']['pred_to_gt']['median'])
    self.assertEqual(empty['metrics']['pred_to_gt']['sample_count'], 0)

  def test_unreviewable_row_not_filtered_or_promoted_to_blind(self):
    core = unseal(copy.deepcopy(self.export))
    row = unseal(core['assisted_human_rows'][0])
    row.update(reviewer_label='UNRESOLVED', reviewable=False)
    core['assisted_human_rows'][0] = seal(row)
    result = self.aggregate(seal(core))
    self.assertEqual((result['reviewable'], result['unreviewable']), (28, 1))
    self.assertEqual(result['categories']['UNRESOLVED']['metrics']['pred_to_gt']['sample_count'], 2)
    self.assertEqual(result['metrics']['pred_to_gt']['sample_count'], 58)
    self.assertFalse(result['blind_independent_complete'])

  def test_forged_promotion_unknown_fields_and_ai_row_collision_rejected(self):
    for field, value in [
      ('blind_independent_complete', True),
      ('reference_promotable', True),
      ('private_input_allowed', True),
      ('automatic_human_label', 'OTHER'),
    ]:
      core = unseal(self.export)
      core[field] = value
      with self.subTest(field=field), self.assertRaises(ValueError):
        self.aggregate(seal(core))
    self.ai[-1] = self.ai[0]
    with self.assertRaises(ValueError):
      self.aggregate()

  def test_suggestion_cannot_be_created_after_first_exposure(self):
    suggestion = unseal(self.ai[0])
    suggestion['timestamp'] = '2099-10-08T00:00:00Z'
    self.ai[0] = seal(suggestion)
    core = unseal(copy.deepcopy(self.export))
    provenance = unseal(core['provenance'])
    exposure = unseal(provenance['exposures'][0])
    exposure['first_suggestion_sha256'] = self.ai[0]['receipt_sha256']
    provenance['exposures'][0] = seal(exposure)
    core['provenance'] = seal(provenance)
    with self.assertRaisesRegex(ValueError, 'SUGGESTION_NOT_AVAILABLE_AT_EXPOSURE'):
      self.aggregate(seal(core))

  def test_empty_original_vectors_report_unavailable_frame_without_imputation(self):
    core = unseal(copy.deepcopy(self.m))
    core['frames'][0]['pred_to_gt'] = t.distribution([])
    core['frames'][0]['gt_to_pred'] = t.distribution([])
    self.m = seal(core)
    inputs = vision(self.m)
    for i, v in enumerate(inputs):
      v['same_point_error'] = t.distribution([] if i == 0 else [1, 9])
    self.ex = a.freeze_experiment(self.m, inputs, 'AI_REVIEW_EMPTY_TEST')
    self.export, self.ai = fixture_for_manifest(self.m, self.ex)

    def load(frame):
      core = unseal(loader(self.m)(frame))
      if frame == self.m['frames'][0]:
        core['pool'] = {'pred': [], 'gt': [], 'paired_spatial_pred': []}
      return seal(core)

    result = self.aggregate(metric_loader=load)
    self.assertEqual(result['reviewed'], 29)
    self.assertEqual(result['metric_availability']['pred_to_gt'], {'available_frames': 28, 'unavailable_frames': 1})
    self.assertEqual(result['metrics']['pred_to_gt']['sample_count'], 56)

  def test_concordance_and_provenance_deterministic(self):
    result = self.aggregate()
    self.assertEqual(result, self.aggregate())
    self.assertEqual(self.export['receipt_sha256'], result['human_export_sha256'])


def fixture_for_manifest(m, ex):
  _, template, _, _ = fixture()
  human = rows(m, 'DETECTOR_MISS')
  suggestions = [
    a.make_suggestion(
      m,
      ex,
      i,
      label='DETECTOR_MISS',
      secondary=[],
      confidence='LOW',
      reason='TEST ONLY',
      observations=['TEST ONLY'],
      answers=dict.fromkeys(a.QUESTIONS, 'UNRESOLVED'),
      model=a.TEST_MODEL,
      timestamp='2026-10-07T23:00:00Z',
    )
    for i in range(29)
  ]
  exposures = []
  for i, f in enumerate(m['frames']):
    x = unseal(template['provenance']['exposures'][i])
    x.update(
      frame=f, manifest_sha256=m['receipt_sha256'], first_suggestion_sha256=suggestions[i]['receipt_sha256'], first_experiment_sha256=ex['receipt_sha256']
    )
    exposures.append(seal(x))
  p = unseal(template['provenance'])
  p.update(review_manifest_sha256=m['receipt_sha256'], exposures=exposures)
  progress = unseal(template['ai_progress'])
  progress['experiment_sha256'] = ex['receipt_sha256']
  x = unseal(template)
  x.update(
    review_manifest_sha256=m['receipt_sha256'],
    assisted_human_rows=human,
    provenance=seal(p),
    ai_progress=seal(progress),
    blind_human_export=w.export_review(m, []),
  )
  return seal(x), suggestions


class TestInterRater(unittest.TestCase):
  def setUp(self):
    self.assertTrue(hasattr(d, 'inter_rater'), 'Missing gated categorical inter-rater analysis')
    self.m, self.export, self.ex, self.ai = fixture()
    from openpilot.tools.cyber_autotune import lane_tail_second_review as b

    self.b = b

  def test_no_second_reviewer_does_not_create_statistics(self):
    result = d.inter_rater(self.m, self.export, self.ex, self.ai, None)
    self.assertEqual(result['status'], 'INDEPENDENT_BLIND_REVIEWER_UNAVAILABLE')
    self.assertIsNone(result['statistics'])

  def test_28_blind_rows_cannot_create_kappa(self):
    import tempfile

    with tempfile.TemporaryDirectory() as root:
      store = self.b.BlindStore(self.m, self.b.register(self.b.protocol(self.m), 'a' * 64, self.b.ATTESTATIONS), root)
      for i in range(28):
        store.append(i, label='DETECTOR_MISS', reviewable=True, comment='TEST ONLY', timestamp='2026-10-08T00:00:00Z', human_ack=True)
      result = d.inter_rater(self.m, self.export, self.ex, self.ai, store.export())
      self.assertEqual(result['status'], 'INDEPENDENT_BLIND_REVIEW_PENDING')
      self.assertIsNone(result['statistics'])

  def test_known_29_pair_categorical_kappa_not_accuracy(self):
    import tempfile

    core = unseal(copy.deepcopy(self.export))
    for i in range(29):
      row = unseal(core['assisted_human_rows'][i])
      row['reviewer_label'] = 'DETECTOR_MISS' if i < 15 else 'REPRESENTATION_MISMATCH'
      core['assisted_human_rows'][i] = seal(row)
    export = seal(core)
    with tempfile.TemporaryDirectory() as root:
      store = self.b.BlindStore(self.m, self.b.register(self.b.protocol(self.m), 'a' * 64, self.b.ATTESTATIONS), root)
      for i in range(29):
        label = 'REPRESENTATION_MISMATCH' if 10 <= i < 15 or i >= 20 else 'DETECTOR_MISS'
        store.append(i, label=label, reviewable=True, comment='TEST ONLY', timestamp='2026-10-08T00:00:00Z', human_ack=True)
      blind = store.export()
      result = d.inter_rater(self.m, export, self.ex, self.ai, blind)
      self.assertEqual(result['status'], 'TEST_ONLY_NOT_HUMAN_EVIDENCE')
      self.assertEqual(result['statistics']['exact_agreements'], 19)
      self.assertAlmostEqual(result['statistics']['cohens_kappa'], 13 / 42)
      self.assertEqual(len(result['statistics']['disagreement_frame_ids']), 10)
      self.assertFalse(result['reference_promotable'])
      self.assertEqual(result, d.inter_rater(self.m, export, self.ex, self.ai, blind))

  def test_constant_category_has_undefined_kappa(self):
    import tempfile

    with tempfile.TemporaryDirectory() as root:
      store = self.b.BlindStore(self.m, self.b.register(self.b.protocol(self.m), 'a' * 64, self.b.ATTESTATIONS), root)
      for i in range(29):
        store.append(i, label='DETECTOR_MISS', reviewable=True, comment='TEST ONLY', timestamp='2026-10-08T00:00:00Z', human_ack=True)
      result = d.inter_rater(self.m, self.export, self.ex, self.ai, store.export())
      self.assertIsNone(result['statistics']['cohens_kappa'])
      self.assertEqual(result['statistics']['kappa_status'], 'UNDEFINED_EXPECTED_AGREEMENT_ONE')
