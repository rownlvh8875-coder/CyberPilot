import unittest
import numpy as np

from openpilot.tools.cyber_autotune.lane_marking_metrics import marking_frame
from openpilot.tools.cyber_autotune import lane_tail_diagnostics as t


class TestTailDiagnostics(unittest.TestCase):
  def mask(self, x=20, thickness=1):
    m = np.zeros((12, 100), dtype=bool)
    m[:, x : x + thickness] = True
    return m

  def points(self, x):
    return [[float(x), y] for y in range(12)]

  def test_analytic_shifts(self):
    for dx in (0, 5, -10):
      with self.subTest(dx=dx):
        r = marking_frame(self.mask(), self.points(20 + dx))
        self.assertEqual(r['pred_to_gt']['median'], abs(dx))
        self.assertEqual(r['gt_to_pred']['p95'], abs(dx))

  def test_thickness_midpoint_convention(self):
    self.assertEqual(marking_frame(self.mask(18, 5), self.points(20))['pred_to_gt']['maximum'], 0)
    self.assertEqual(marking_frame(self.mask(19, 2), self.points(19.5))['pred_to_gt']['maximum'], 0)

  def test_partial_outside_rejected_not_clipped(self):
    with self.assertRaisesRegex(ValueError, 'INVALID_ORIGINAL_PIXEL_POINT'):
      marking_frame(self.mask(), [[-1.0, 1], [20.0, 2]])

  def test_remote_false_positive_retained(self):
    r = t.analyze_frame(self.mask(), [self.points(20), self.points(90)], [0.8, 0.9])
    self.assertEqual(r['pred_to_gt']['p95'], 70)
    self.assertEqual(r['false_positive_components'], 1)
    self.assertEqual(r['supported_prediction_ratio'], 0.5)

  def test_missing_prediction(self):
    r = t.analyze_frame(self.mask(), [], [])
    self.assertEqual(r['failure_category'], 'NO_PREDICTION')
    self.assertIsNone(r['pred_to_gt']['p95'])
    self.assertEqual(r['missed_gt_components'], 1)

  def test_missing_gt(self):
    r = t.analyze_frame(np.zeros((12, 100), dtype=bool), [self.points(20)], [0.8])
    self.assertEqual(r['failure_category'], 'GT_UNAVAILABLE')
    self.assertIsNone(r['gt_to_pred']['median'])

  def test_dashes_are_not_one_to_one_identity(self):
    m = self.mask()
    m[4:8] = False
    r = t.analyze_frame(m, [self.points(20)], [0.8])
    self.assertEqual(r['gt_components'], 2)
    self.assertEqual(r['support_edges'], [[0, 0], [0, 1]])
    self.assertEqual(r['missed_gt_components'], 0)

  def test_row_artifact_counterfactual_does_not_replace_tail(self):
    m = np.zeros((12, 100), dtype=bool)
    m[:, 90] = True
    m[::2, 20] = True
    r = t.analyze_frame(m, [self.points(20)], [0.8])
    self.assertEqual(r['pred_to_gt']['p95'], 70)
    self.assertEqual(r['spatial_pred_to_gt']['p95'], 1)
    self.assertGreater(r['row_tail_spatially_resolved_points'], 0)

  def test_8_connectivity(self):
    m = np.zeros((3, 5), dtype=bool)
    m[0, 1] = m[1, 2] = m[2, 3] = True
    self.assertEqual(t.paint_components(m)['count'], 1)

  def test_y_bucket_boundaries(self):
    r = t.analyze_frame(self.mask(), [self.points(20)], [0.8])
    self.assertEqual([r['regions'][n]['pred_to_gt']['sample_count'] for n in ('far', 'mid', 'near')], [4, 4, 4])

  def test_determinism(self):
    args = (self.mask(), [self.points(20)], [0.8])
    self.assertEqual(t.analyze_frame(*args), t.analyze_frame(*args))

  def test_geometry_inverse_roundtrip(self):
    for w, h in ((1164, 874), (1928, 1208)):
      for x, y in ((0, 0), (w - 1, h - 1), (w / 2, h / 2)):
        u, v = t.original_to_network(x, y, w, h)
        rx, ry = t.network_to_original(u, v, w, h)
        self.assertAlmostEqual(rx, x, places=10)
        self.assertAlmostEqual(ry, y, places=10)

  def test_invalid_confidence(self):
    for scores in ([float('nan')], [1.1], [True], []):
      with self.subTest(scores=scores), self.assertRaises(ValueError):
        t.analyze_frame(self.mask(), [self.points(20)], scores)

  def test_duplicate_lanes_union_explicit(self):
    r = t.analyze_frame(self.mask(), [self.points(20), self.points(20)], [0.8, 0.9])
    self.assertEqual(r['pred_points'], 12)
    self.assertEqual(r['prediction_count'], 2)

  def test_identity_changes_with_policy(self):
    p = t.policy()
    changed = dict(p, version='test')
    self.assertNotEqual(t.policy_sha(p), t.policy_sha(changed))

  def test_gate_does_not_promote_diagnostic(self):
    self.assertFalse(
      t.promotion_gate(metric_correct=True, deterministic=True, tail_complete=True, full_complete=True, official_reproduced=False)['private_input_allowed']
    )

  def test_policy_fail_closed(self):
    with self.assertRaises(ValueError):
      t.validate_policy(dict(t.policy(), confidence_edges=[0, 1]))

  def test_empty_lane_rejected(self):
    with self.assertRaises(ValueError):
      t.analyze_frame(self.mask(), [[]], [0.8])

  def test_known_spatial_distance(self):
    self.assertEqual(t.spatial_distances([[3.0, 4]], [[0.0, 0]]), [5.0])

  def test_symmetric_keeps_directions(self):
    r = t.analyze_frame(self.mask(), [self.points(25)], [0.8])
    self.assertEqual(r['symmetric']['sample_count'], 24)
    self.assertEqual(r['symmetric']['p95'], 5)

  def test_confidence_buckets_fixed(self):
    self.assertEqual(t.confidence_bucket(0.4), '0.4:0.6')
    self.assertEqual(t.confidence_bucket(1.0), '0.8:1.0')

  def test_bad_pixel_never_filled(self):
    with self.assertRaises(ValueError):
      t.analyze_frame(self.mask(), [[[float('inf'), 1]]], [0.8])

  def test_support_is_exact_mask_not_distance_threshold(self):
    r = t.analyze_frame(self.mask(), [self.points(21)], [0.8])
    self.assertEqual(r['supported_prediction_ratio'], 0)
    self.assertEqual(r['false_positive_components'], 1)

  def test_empty_historical_record_cannot_prove_union(self):
    from openpilot.tools.cyber_autotune.lane_tail_capture import require_historical_union

    with self.assertRaises(ValueError):
      require_historical_union([{'points': [[99.0, 0]]}], [{}])

  def test_raw_score_validated_before_empty_lane_filter(self):
    for scores, count in (([True], 1), ([1.5], 1), ([0.9], -9), ([0.9], 2)):
      with self.subTest(scores=scores, count=count), self.assertRaises(ValueError):
        t.validate_raw_lanes({'lane_count': count, 'lanes': [[]], 'scores': scores, 'points': []}, self.mask())

  def test_historical_digest_bound(self):
    from openpilot.tools.cyber_autotune.lane_tail_capture import require_historical_artifact

    with self.assertRaises(ValueError):
      require_historical_artifact([{}], '0' * 64)

  def test_gate_bool_fail_closed(self):
    with self.assertRaises(ValueError):
      t.promotion_gate(metric_correct=1, deterministic=True, tail_complete=True, full_complete=True, official_reproduced=True)

  def test_report_seal_tamper(self):
    from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal

    item = seal({'metric': 1})
    item['metric'] = 2
    with self.assertRaises(ValueError):
      unseal(item)

  def test_secondary_only_declared_computed_buffers_may_be_missing(self):
    from openpilot.tools.cyber_autotune.lane_secondary_capture import validate_state_keys, DECLARED_MISSING_KEYS

    validate_state_keys(list(DECLARED_MISSING_KEYS), [])
    for missing, extra in (([], []), (list(DECLARED_MISSING_KEYS) + ['heads.fc.weight'], []), (list(DECLARED_MISSING_KEYS), ['unknown'])):
      with self.subTest(missing=missing, extra=extra), self.assertRaises(ValueError):
        validate_state_keys(missing, extra)

  def test_semantic_tail_preserves_car_and_road_samples(self):
    rgb = np.full((3, 100, 3), (64, 32, 32), dtype=np.uint8)
    rgb[:, 10] = (255, 0, 0)
    rgb[1, 90] = (204, 0, 255)
    result = t.semantic_tail(rgb, [[90.0, 0], [90.0, 1]], 70.0)
    self.assertEqual(result['road']['historic_p95_tail_count'], 1)
    self.assertEqual(result['my_car']['historic_p95_tail_count'], 1)

  def test_semantic_unknown_palette_rejects(self):
    with self.assertRaises(ValueError):
      t.semantic_tail(np.zeros((3, 3, 3), dtype=np.uint8), [], 1.0)

  def test_full_run_completion_requires_all_frames(self):
    from openpilot.tools.cyber_autotune.lane_public_batch import completion_state

    self.assertEqual(completion_state(11888, 119, 0), 'PARTIAL_NOT_QUALIFICATION')
    self.assertEqual(completion_state(11888, 11888, 0), 'COMPLETE_DIAGNOSTIC_NOT_QUALIFICATION')
    self.assertEqual(completion_state(11888, 11888, 1), 'FAILED_NOT_QUALIFICATION')
    with self.assertRaises(ValueError):
      completion_state(119, 120, 0)

  def test_full_resume_changed_identity_rejected(self):
    from openpilot.tools.cyber_autotune.lane_public_batch import verify_resume
    from openpilot.tools.cyber_autotune.lane_tail_report import seal

    with self.assertRaises(ValueError):
      verify_resume(seal({'run_sha256': 'a' * 64, 'ordinal': 0}), 'b' * 64, 0)
    with self.assertRaises(ValueError):
      verify_resume(seal({'run_sha256': 'a' * 64, 'ordinal': 1}), 'a' * 64, 0)

  def test_historical_p95_cut_bound(self):
    from openpilot.tools.cyber_autotune.lane_tail_report import historical_tail_cut

    self.assertEqual(historical_tail_cut(), 608.4058599107527)

  def capture(self):
    return {
      'schema': 'PUBLIC_LANE_CAPTURE_V1',
      'exact_repeatability': True,
      'historical_union_exact_match': True,
      'private_input_opened': False,
      'reference_promotable': False,
      'candidate_outputs_used_for_reference': False,
      'openpilot_path_lane_used': False,
    }

  def test_failed_primary_history_rejected_by_report(self):
    from openpilot.tools.cyber_autotune.lane_tail_report import validate_capture

    with self.assertRaises(ValueError):
      validate_capture(dict(self.capture(), historical_union_exact_match=False))

  def test_leakage_flags_reject(self):
    from openpilot.tools.cyber_autotune.lane_tail_report import validate_capture

    for field in ('private_input_opened', 'reference_promotable', 'candidate_outputs_used_for_reference', 'openpilot_path_lane_used'):
      with self.subTest(field=field), self.assertRaises(ValueError):
        validate_capture(dict(self.capture(), **{field: True}))

  def test_secondary_failure_retained_only_diagnostic(self):
    from openpilot.tools.cyber_autotune.lane_tail_report import validate_capture

    validate_capture(dict(self.capture(), schema='PUBLIC_CLRNET_CAPTURE_V1', exact_repeatability=False, historical_union_exact_match=None))
    self.assertFalse(
      t.promotion_gate(metric_correct=True, deterministic=False, tail_complete=True, full_complete=False, official_reproduced=False)['reference_promotable']
    )

  def test_fast_raw_point_validation_matches_legacy(self):
    cases = ([[float('nan'), 1]], [[-1.0, 1]], [[100.0, 1]], [[20.0, 12]], [[20.0, True]], [[True, 1]], [[20.0, 1.0]], [[20.0, 1], [20.0, 1]])
    for points in cases:
      with self.subTest(points=points), self.assertRaises(ValueError):
        t.validate_raw_lanes({'lane_count': 1, 'lanes': [points], 'scores': [0.8], 'points': points}, self.mask())

  def test_full_resume_incomplete_evidence_rejected(self):
    from openpilot.tools.cyber_autotune.lane_public_batch import verify_resume
    from openpilot.tools.cyber_autotune.lane_tail_report import seal

    with self.assertRaises(ValueError):
      verify_resume(seal({'run_sha256': 'a' * 64, 'ordinal': 0}), 'a' * 64, 0)

  def test_full_environment_only_inputs_may_change(self):
    from openpilot.tools.cyber_autotune.lane_public_batch import require_primary_environment
    from openpilot.tools.cyber_autotune.lane_detector_execution import COMMIT

    base = {'config_sha256': 'a' * 64, 'source_bundle_sha256': 'b' * 64, 'public_protocol_file_sha256': 'c' * 64, 'public_input_manifest_file_sha256': 'd' * 64}
    new = dict(base, public_protocol_file_sha256='e' * 64)
    require_primary_environment(new, base, COMMIT)
    for changed, head in ((dict(new, config_sha256='f' * 64), COMMIT), (dict(new, source_bundle_sha256='f' * 64), COMMIT), (new, '0' * 40)):
      with self.subTest(head=head), self.assertRaises(ValueError):
        require_primary_environment(changed, base, head)

  def test_full_resume_metric_replay_cannot_drift(self):
    from openpilot.tools.cyber_autotune.lane_public_batch import require_replayed_metric

    with self.assertRaises(ValueError):
      require_replayed_metric({'pool': {'pred': [5.0]}}, {'pool': {'pred': [0.0]}})

  def test_spatial_resource_budget_fails_instead_of_silent_skip(self):
    with self.assertRaisesRegex(ValueError, 'RESOURCE'):
      t.spatial_distances([[0.0, 0]] * 5001, [[0.0, 0]] * 5000)

  def resume_fixture(self):
    from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
    from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

    raw = {'image': 'imgs/example.png', 'image_geometry': [12, 100], 'lane_count': 1, 'lanes': [self.points(20)], 'points': self.points(20), 'scores': [0.8]}
    ledger = unseal(t.analyze_frame(self.mask(), raw['lanes'], raw['scores']))
    ledger.update({'frame_id': raw['image'], 'image_sha256': 'b' * 64, 'gt_mask_sha256': 'c' * 64, 'detector_result_sha256': digest(canonical(raw))})
    return seal(
      {'run_sha256': 'a' * 64, 'ordinal': 0, 'detector_record': raw, 'ledger': seal(ledger), 'pool': {'pred': [0.0]}, 'confidence': {}, 'regions': {}}
    )

  def test_full_resume_valid_but_requires_input_binding(self):
    from openpilot.tools.cyber_autotune.lane_public_batch import verify_resume

    fixture = self.resume_fixture()
    pair = {'image': 'imgs/example.png', 'mask': 'masks/example.png'}
    identities = {'imgs/example.png': {'sha256': 'b' * 64}, 'masks/example.png': {'sha256': 'c' * 64}}
    verify_resume(fixture, 'a' * 64, 0, pair, identities)
    with self.assertRaises(ValueError):
      verify_resume(fixture, 'a' * 64, 0, pair, dict(identities, **{'masks/example.png': {'sha256': 'd' * 64}}))

  def test_resealed_swapped_raw_frame_rejected(self):
    from openpilot.tools.cyber_autotune.lane_public_batch import verify_resume
    from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal

    core = unseal(self.resume_fixture())
    core['detector_record']['image'] = 'imgs/different.png'
    with self.assertRaises(ValueError):
      verify_resume(seal(core), 'a' * 64, 0)

  def test_resealed_metric_units_reject(self):
    from openpilot.tools.cyber_autotune.lane_public_batch import verify_resume
    from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal

    core = unseal(self.resume_fixture())
    ledger = unseal(core['ledger'])
    core['ledger'] = seal(dict(ledger, unit='m'))
    with self.assertRaises(ValueError):
      verify_resume(seal(core), 'a' * 64, 0)

  def test_worker_failure_never_complete(self):
    from openpilot.tools.cyber_autotune.lane_public_batch import completion_state

    self.assertEqual(completion_state(11888, 11887, 1), 'FAILED_NOT_QUALIFICATION')

  def test_replay_prefix_cannot_consume_new_inference_budget(self):
    from openpilot.tools.cyber_autotune.lane_public_batch import inference_budget_expired

    self.assertFalse(inference_budget_expired(None, 5000.0, 1))
    self.assertFalse(inference_budget_expired(5000.0, 5000.0, 1))
    self.assertTrue(inference_budget_expired(5000.0, 5001.0, 1))

  def test_confidence_empty_denominator_remains_unavailable(self):
    from openpilot.tools.cyber_autotune.lane_tail_report import summarize_confidence

    b = {
      'lane_count': 1,
      'samples': [],
      'off_mask_points': 12,
      'points': 12,
      'gt_eligible_lanes': 0,
      'distance_available_lanes': 0,
      'large_row_tail_lanes': 0,
      'no_row_support_lanes': 0,
    }
    self.assertIsNone(summarize_confidence({'0.8:1.0': b})['0.8:1.0']['large_row_tail_rate'])

  def test_official_normalized_lane_sampling_inverse_original_geometry(self):
    from openpilot.tools.cyber_autotune.lane_public_protocol import sample_detector_lane_diagnostics

    for width, height in ((1164, 874), (1928, 1208)):

      def lane(ys, width=width):
        return np.where(ys >= 270 / 590, 10 / width, -2.0)

      sampled = sample_detector_lane_diagnostics([lane], width=width, height=height)
      self.assertTrue(sampled['points'])
      self.assertTrue(all(abs(x - 10) < 1e-12 for x, _ in sampled['points']))
      self.assertEqual(sampled['points'][0][1], int(np.ceil(height * 270 / 590)))

  def test_merge_pools_samples_instead_of_frame_medians(self):
    from openpilot.tools.cyber_autotune.lane_public_batch import merge_frame_results

    items = [
      {'ledger': {}, 'pool': {'pred': [0.0]}, 'confidence': {}, 'regions': {}},
      {'ledger': {}, 'pool': {'pred': [10.0] * 9}, 'confidence': {}, 'regions': {}},
    ]
    _, pool, _, _ = merge_frame_results(items)
    self.assertEqual(t.distribution(pool['pred'])['median'], 10)
