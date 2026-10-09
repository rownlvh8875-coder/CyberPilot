"""Post-freeze analysis must preserve assisted provenance and observed support."""
import copy
import unittest

from openpilot.tools.cyber_autotune import private_holdout_assisted as a
from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune import private_holdout_hidden as hidden
from openpilot.tools.cyber_autotune.tests import test_private_holdout_assisted_metrics as fixtures
from openpilot.tools.cyber_autotune.tests.test_private_pixel_execution import STAMP


class TestAnalysis(unittest.TestCase):
  def setUp(self):
    self.fixture = fixtures.TestAssistedMetrics()
    self.fixture.setUp()
    self.addCleanup(self.fixture.temp.cleanup)
    try:
      from openpilot.tools.cyber_autotune import private_holdout_assisted_analysis as m
    except ImportError:
      self.fail('Separate post-freeze assisted analysis not implemented')
    self.m = m
    f = self.fixture
    human = h.unseal(f.finals[0])
    body = {k: human[k] for k in ('action', 'state', 'left', 'right', 'reviewer_id', 'acknowledged_assisted', 'comment')}
    body['action'] = 'MODIFY_AI'
    body['left'] = [[x + 2, y] for x, y in body['left']]
    f.finals[0] = a.human_row(f.package, f.auth, 0, f.ai[0], body, STAMP)
    f.reference = a.freeze(f.package, f.auth, f.ai, f.finals, STAMP)

  def analyze(self, **changes):
    f = self.fixture
    kwargs = {'package': f.package, 'auth': f.auth, 'ai_rows': f.ai, 'reference': f.reference,
              'detector_auth': f.detector_auth, 'predictions': f.predictions}
    kwargs.update(changes)
    evaluation = a.evaluate(**kwargs)
    return self.m.analyze(**kwargs, evaluation=evaluation)

  def test_group_metrics_and_matching(self):
    r = self.analyze()
    self.assertEqual(r['groups']['ACCEPT_AI']['frames'], 59)
    self.assertEqual(r['groups']['ACCEPT_AI']['left']['median'], 5)
    self.assertEqual(r['groups']['MODIFY_AI']['left']['median'], 3)
    self.assertEqual(r['groups']['MODIFY_AI']['right']['p95'], 10)
    self.assertEqual(r['groups']['MODIFY_AI']['both_boundary_matching_rate'], 1)

  def test_modification_is_not_detector_error(self):
    r = self.analyze()
    self.assertEqual(r['modifications']['geometry_change_counts']['LEFT_ONLY'], 1)
    self.assertEqual(r['modifications']['original_to_final_px']['median'], 2)
    self.assertIn('NOT_DETECTOR_ERROR', r['modifications']['semantics'])

  def test_centers_observed_only(self):
    r = self.analyze()
    center = r['rows'][0]['human_pixel_center']
    self.assertEqual(min(pt[1] for pt in center), 100)
    self.assertEqual(max(pt[1] for pt in center), 300)
    self.assertEqual(r['center']['median'], 7.5)
    self.assertEqual(r['center']['both_visible_denominator'], 59)

  def test_no_output_is_missing_not_zero_confidence(self):
    f = self.fixture
    empty = {'image_geometry': [330, 526], 'lane_count': 0, 'points': [], 'lanes': []}
    rows = [hidden.detector_row(f.package, f.detector_auth, i, empty, empty, STAMP) for i in range(60)]
    r = self.analyze(predictions=rows)
    self.assertEqual(r['failure_counts']['BOTH_MISS'], 59)
    self.assertEqual(r['confidence']['buckets']['NO_OUTPUT']['frames'], 60)
    self.assertEqual(r['center']['unavailable_frames'], 59)
    self.assertIsNone(r['combined']['median'])

  def test_confidence_boundaries_frozen(self):
    self.assertEqual(self.m.confidence_bucket(None), 'NO_OUTPUT')
    self.assertEqual(self.m.confidence_bucket(.5), '0.50_TO_0.75')
    self.assertEqual(self.m.confidence_bucket(.75), '0.75_TO_0.90')
    self.assertEqual(self.m.confidence_bucket(.9), '0.90_TO_1.00')
    self.assertEqual(self.m.confidence_bucket(1), '0.90_TO_1.00')
    for value in (float('nan'), -1, 1.1):
      with self.assertRaises(ValueError):
        self.m.confidence_bucket(value)

  def test_missing_ai_boundary_not_zero_magnitude(self):
    f = self.fixture
    original = h.unseal(f.ai[0])
    body = {k: original[k] for k in ('state', 'left', 'right', 'reason', 'confidence')}
    body.update(state='RIGHT_ONLY_VISIBLE', left=[])
    f.ai[0] = a.ai_row(f.package, f.auth, 0, body, STAMP, observation_id='synthetic')
    human = h.unseal(f.finals[0])
    final = {k: human[k] for k in ('action', 'state', 'left', 'right', 'reviewer_id', 'acknowledged_assisted', 'comment')}
    f.finals[0] = a.human_row(f.package, f.auth, 0, f.ai[0], final, STAMP)
    f.reference = a.freeze(f.package, f.auth, f.ai, f.finals, STAMP)
    r = self.analyze()
    self.assertEqual(r['modifications']['added_boundary_count'], 1)
    self.assertEqual(r['modifications']['state_changes'], 1)
    self.assertEqual(r['modifications']['original_to_final_px']['count'], 0)

  def test_partial_set_rejected(self):
    with self.assertRaises(ValueError):
      self.analyze(reference=h.seal({**h.unseal(self.fixture.reference), 'annotations': self.fixture.finals[:59]}))

  def test_historical_evaluation_mismatch_rejected(self):
    f = self.fixture
    e = a.evaluate(f.package, f.auth, f.ai, f.reference, f.detector_auth, f.predictions)
    e = h.seal({**h.unseal(e), 'both_boundary_geometry_match_frames': 0})
    with self.assertRaises(ValueError):
      self.m.analyze(f.package, f.auth, f.ai, f.reference, f.detector_auth, f.predictions, e)

  def test_prediction_drift_rejected(self):
    rows = copy.deepcopy(self.fixture.predictions)
    rows[0] = h.seal({**h.unseal(rows[0]), 'prediction_sha256': 'b' * 64})
    with self.assertRaises(ValueError):
      self.analyze(predictions=rows)

  def test_deterministic(self):
    self.assertEqual(h.canonical(self.analyze()), h.canonical(self.analyze()))

  def test_publication_excludes_private_rows(self):
    r = self.analyze()
    public = self.m.publication(r)
    text = h.canonical(public).decode()
    for im in self.fixture.package['images']:
      self.assertNotIn(im['sample_id'], text)
    for key in ('rows', 'bindings', 'human_pixel_center', 'failure_ledger', 'comment'):
      self.assertNotIn(key, public)
    self.assertFalse(public['qualification_allowed'])
    self.assertFalse(public['sealed_reference_allowed'])
    self.assertFalse(public['blind_human'])

  def test_publication_refuses_promotion(self):
    r = self.analyze()
    r = h.seal({**h.unseal(r), 'qualification_allowed': True})
    with self.assertRaises(ValueError):
      self.m.publication(r)

  def test_publication_rejects_nested_private_content(self):
    r = self.analyze()
    for key, value in (('comment', 'private-path-secret'), ('frames', 'private-path-secret')):
      bad = copy.deepcopy(h.unseal(r))
      bad['groups']['ACCEPT_AI'][key] = value
      with self.subTest(key=key), self.assertRaises(ValueError):
        self.m.publication(h.seal(bad))

  def test_publication_rejects_fake_identity_or_resolved_blocker(self):
    r = self.analyze()
    for key in ('reference_sha256', 'status', 'blockers', 'vehicle_status'):
      bad = copy.deepcopy(h.unseal(r))
      bad[key] = 'private-path-or-false-ready'
      with self.subTest(key=key), self.assertRaises(ValueError):
        self.m.publication(h.seal(bad))

  def test_disjoint_center_support_is_unavailable(self):
    self.assertEqual(self.m.center_points([[10, 30], [10, 20], [10, 10]],
                                         [[50, 90], [50, 80], [50, 70]]), [])

  def test_one_sided_reference_has_no_center_or_modification_distance(self):
    f = self.fixture
    human = h.unseal(f.finals[0])
    body = {k: human[k] for k in ('action', 'state', 'left', 'right', 'reviewer_id', 'acknowledged_assisted', 'comment')}
    body.update(action='MODIFY_AI', state='RIGHT_ONLY_VISIBLE', left=[])
    f.finals[0] = a.human_row(f.package, f.auth, 0, f.ai[0], body, STAMP)
    f.reference = a.freeze(f.package, f.auth, f.ai, f.finals, STAMP)
    r = self.analyze()
    self.assertEqual(r['rows'][0]['human_pixel_center'], [])
    self.assertEqual(r['center']['both_visible_denominator'], 58)
    self.assertEqual(r['modifications']['removed_boundary_count'], 1)
    self.assertEqual(r['modifications']['original_to_final_px']['count'], 0)

  def test_publication_rejects_integer_provenance_flags(self):
    r = self.analyze()
    for key, value in (('blind_human', 0), ('assisted_human', 1), ('qualification_allowed', 0)):
      bad = copy.deepcopy(h.unseal(r))
      bad[key] = value
      with self.subTest(key=key), self.assertRaises(ValueError):
        self.m.publication(h.seal(bad))

  def test_admitted_unknown_confidence_empty_support(self):
    f = self.fixture
    prediction = {'image_geometry': [330, 526], 'lane_count': 1, 'points': [],
                  'lanes': [{'confidence': None, 'points': []}]}
    rows = [hidden.detector_row(f.package, f.detector_auth, i, prediction, prediction, STAMP) for i in range(60)]
    r = self.analyze(predictions=rows)
    self.assertEqual(r['confidence']['buckets']['UNKNOWN_CONFIDENCE']['frames'], 60)
    self.assertEqual(r['confidence']['buckets']['NO_OUTPUT']['frames'], 0)
    self.assertEqual(r['prediction_only']['unknown_confidence_lanes'], 60)
    self.assertEqual(r['prediction_only']['empty_geometry_lanes'], 60)
    self.assertIsNone(r['prediction_only']['per_lane_confidence']['median'])
    self.m.publication(r)

  def test_publication_cross_checks_center_and_confidence(self):
    r = self.analyze()
    bad = copy.deepcopy(h.unseal(r))
    bad['center']['both_visible_denominator'] = 600
    bad['center']['unavailable_frames'] = 541
    with self.assertRaises(ValueError):
      self.m.publication(h.seal(bad))
    bad = copy.deepcopy(h.unseal(r))
    bucket = bad['confidence']['buckets']['0.75_TO_0.90']
    bucket['both_visible_frames'] = 0
    bucket['both_matched_frames'] = 0
    bucket['both_boundary_matching_rate'] = None
    with self.assertRaises(ValueError):
      self.m.publication(h.seal(bad))

  def test_blocker_critical_path_unchanged(self):
    r = self.analyze()
    for name in ('CALIBRATION_MEASUREMENT_PENDING', 'INDEPENDENT_CALIBRATION_VALIDATION_PENDING',
                 'METRIC_CALIBRATION_UNAVAILABLE', 'EGO_ASSOCIATION_VALIDATION_PENDING', 'INDEPENDENT_REFERENCE_UNAVAILABLE'):
      self.assertEqual(r['blockers'][name]['status'], 'BLOCKED')
    self.assertEqual(r['detector_status'], 'PRIVATE_REFERENCE_CANDIDATE_DIAGNOSTIC_ONLY')


if __name__ == '__main__':
  unittest.main()
