import copy
import unittest
from openpilot.tools.cyber_autotune import resolution_candidate_evidence as e
from openpilot.tools.cyber_autotune import resolution_candidate_audit as a


class TestCandidateResolutionEvidence(unittest.TestCase):
  def fixture(self):
    samples = [
      {'pose_x_m': x, 'pose_y_m': 0.0, 'time_s': x / 10, 'phase': 'entry', 'speed_mps': 10.0, 'desired_curvature_1pm': 0.001} for x in (1.0, 10.0, 30.0)
    ]
    arms = [{'samples': copy.deepcopy(samples), 'arm': name} for name in e.ROLES]
    for p in arms[2]['samples']:
      p['pose_y_m'] = 0.01
    return {
      'manifest': {
        'scenario': 'synthetic_left',
        'role': 'EVALUATION',
        'config': {'factor_high_fraction': 0.0, 'friction_high_fraction': 0.0},
        'perturbation': {},
        'selection_sha256': None,
      },
      'arms': arms,
      'exact_repeatability': True,
    }

  def test_exact_meter_binding(self):
    m = e.meter()
    self.assertEqual(m['receipt_sha256'], e.METER_SHA)
    self.assertEqual(m['coverage']['both_matched'], 44)
    self.assertEqual(m['coverage']['center_unavailable'], 11)

  def test_all_six_envelopes(self):
    self.assertEqual(set(e.envelopes()), set(a.DISTANCES_M))

  def test_all_mapping_candidates(self):
    for row in e.envelopes().values():
      self.assertEqual(row['candidate_count'], 78)

  def test_meter_not_recomputed(self):
    self.assertEqual(e.meter()['total_physical_bound_m'], None)
    self.assertIsNone(e.meter()['actual_forward_mapping'])

  def test_ledger_old_verdicts(self):
    ledger = e.ledger()
    self.assertEqual(ledger['V2']['status'], 'REJECTED')
    self.assertEqual(ledger['V1']['status'], 'TRADEOFF_ONLY')
    self.assertEqual(ledger['CURRENT']['alias_of'], 'BASELINE')

  def test_case_distance_rows(self):
    rows = e.case_rows(self.fixture(), e.envelopes())
    self.assertEqual(len(rows), 18)
    self.assertEqual(sum(r['candidate'] == 'CURRENT' and r['absolute_effect_m'] == 0 for r in rows), 6)

  def test_alias_drift_rejected(self):
    r = self.fixture()
    r['arms'][1]['samples'][0]['pose_y_m'] = 0.01
    with self.assertRaises(ValueError):
      e.case_rows(r, e.envelopes())

  def test_repeated_failure(self):
    r = self.fixture()
    r['exact_repeatability'] = False
    self.assertTrue(all(x['classification'] == 'REPEATABILITY_FAILED' for x in e.case_rows(r, e.envelopes())))

  def test_missing_distance(self):
    r = self.fixture()
    for arm in r['arms']:
      arm['samples'] = arm['samples'][:2]
    rows = e.case_rows(r, e.envelopes())
    self.assertTrue(all(x['classification'] == 'DISTANCE_NOT_REACHED' for x in rows if x['distance_m'] > 10))

  def test_missing_reference_coverage(self):
    rows = e.case_rows(self.fixture(), {})
    self.assertTrue(all(r['classification'] == 'COVERAGE_UNAVAILABLE' for r in rows))

  def test_summary_deterministic(self):
    rows = e.case_rows(self.fixture(), e.envelopes())
    self.assertEqual(e.summarize(rows), e.summarize(list(reversed(rows))))

  def test_summary_counting(self):
    rows = e.case_rows(self.fixture(), e.envelopes())
    summary = e.summarize(rows)
    self.assertEqual(sum(summary['classification_counts'].values()), 18)

  def test_existing_blockers_preserved(self):
    d = e.readiness('0' * 64)
    self.assertEqual(d['blockers'], e.previous_readiness()['blockers'])
    self.assertFalse(d['candidate_accepted'])
    self.assertEqual(d['reference_status'], 'INDEPENDENT_REFERENCE_UNAVAILABLE')

  def test_public_coordinates_private_paths_rejected(self):
    d = a.seal({'schema': 'TEST', 'path': '/home/private'})
    with self.assertRaises(ValueError):
      e.validate_public(d)

  def test_public_privacy_only_declared_fields(self):
    d = a.seal({'schema': 'TEST', 'human_polyline': [[1, 2]]})
    with self.assertRaises(ValueError):
      e.validate_public(d)

  def test_nested_coordinates_rejected_after_reseal(self):
    d = a.seal({'schema': 'MEASUREMENT_RESOLUTION_AWARE_CANDIDATE_AUDIT_V1', 'rows': [{'human_polyline': [[1, 2]]}]})
    with self.assertRaises(ValueError):
      e.validate_public(d)

  def test_nested_path_rejected_after_reseal(self):
    d = a.seal({'schema': 'MEASUREMENT_RESOLUTION_CANDIDATE_SUMMARY_V1', 'source_identity': {'path': '/private/example'}})
    with self.assertRaises(ValueError):
      e.validate_public(d)

  def test_no_available_rows_not_below_resolution(self):
    self.assertEqual(e.supporting_state([]), 'UNCOMPARABLE')
    self.assertEqual(e.supporting_state([{'classification': 'DISTANCE_NOT_REACHED'}]), 'UNCOMPARABLE')

  def test_partial_available_explicit(self):
    self.assertEqual(
      e.supporting_state([{'classification': 'EFFECT_BELOW_DECLARED_ENVELOPE', 'absolute_effect_m': 0.0}, {'classification': 'DISTANCE_NOT_REACHED'}]),
      'EFFECT_BELOW_CURRENT_DIAGNOSTIC_RESOLUTION_WHERE_AVAILABLE',
    )

  def test_phase_context_matches_direct_interpolation(self):
    fixture = self.fixture()
    for row in e.phase_effects(fixture):
      expected = []
      arm = fixture['arms'][2 if row['candidate'] == 'V1' else 3]
      for p in fixture['arms'][0]['samples']:
        q = a.at_distance(arm['samples'], p['pose_x_m'], a.BASIS)
        if q['status'] == 'AVAILABLE':
          expected.append(abs(q['pose_y_m'] - p['pose_y_m']))
      self.assertEqual(row['absolute_effect_m'], a.stats(expected))
      self.assertIsNone(row['classification'])

  def test_public_writer_symlink_rejected(self):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
      target = Path(tmp) / 'original'
      target.write_bytes(b'same')
      link = Path(tmp) / 'link'
      link.symlink_to(target)
      with self.assertRaises(ValueError):
        e.immutable_public(link, b'same')
