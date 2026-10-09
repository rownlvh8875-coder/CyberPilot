import unittest

from openpilot.tools.cyber_autotune import declared_meter_evidence as e
from openpilot.tools.cyber_autotune import declared_meter_diagnostic as m
from openpilot.tools.cyber_autotune import camera_calibration_evidence as c


class TestDeclaredMeterEvidence(unittest.TestCase):
  def test_immutable_hash_binding(self):
    x = c.seal({'a': 1})
    self.assertEqual(e.checked(x, x['receipt_sha256']), x)
    x['a'] = 2
    with self.assertRaises(ValueError):
      e.checked(x, x['receipt_sha256'])

  def test_wrong_receipt_rejected(self):
    x = c.seal({'a': 1})
    with self.assertRaises(ValueError):
      e.checked(x, '0' * 64)

  def test_public_no_coordinates(self):
    r = m.output(
      {
        'schema': 'DECLARED_HYPOTHESIS_APPROX_METER_ENVELOPE_V1',
        'status': 'CONDITIONAL_DIAGNOSTIC_COMPLETE',
        'policy': m.policy(),
        'source_bindings': e.frozen_bindings(),
        'coverage': e.frozen_coverage(),
        'fixed_distance': [],
        'holdout_projection': [],
        'scenario_attribution': [],
        'point_derivative_set_sha256': '0' * 64,
        'all_declared_envelopes': [],
        'executor_identity': e.executor_identity(),
      }
    )
    p = e.publication(r)
    self.assertNotIn('points', p)
    self.assertFalse(p['qualification_allowed'])

  def test_unknown_nested_field_rejected(self):
    with self.assertRaises(ValueError):
      e.safe_numbers({'leak': '/private/path'})

  def test_nan_rejected(self):
    with self.assertRaises(ValueError):
      e.safe_numbers({'median': float('nan')})

  def test_coordinate_field_rejected(self):
    with self.assertRaises(ValueError):
      e.safe_numbers({'qcamera_coordinate': [1, 2]})

  def test_ids_not_public(self):
    with self.assertRaises(ValueError):
      e.safe_numbers({'sample_id': 'a' * 64})

  def test_sealed_and_qualification_forbidden(self):
    r = m.output({'schema': 'DECLARED_HYPOTHESIS_APPROX_METER_ENVELOPE_V1'})
    r = c.seal({**{k: v for k, v in r.items() if k != 'receipt_sha256'}, 'qualification_allowed': True})
    with self.assertRaises(ValueError):
      e.publication(r)

  def test_empty_group_stays_null(self):
    self.assertIsNone(m.distribution([])['p95'])

  def test_pose_crosschecks_never_truth(self):
    f = e.feasibility()
    self.assertEqual(f['stereo']['status'], 'STEREO_DISTANCE_DIAGNOSTIC_UNAVAILABLE')
    self.assertEqual(f['imu']['status'], 'IMU_CAMERA_TRANSFORM_UNAVAILABLE')
    self.assertFalse(f['qualification_allowed'])

  def test_readiness_preserves_blockers(self):
    prior = c.seal({'blockers': {'MAPPING': {'status': 'BLOCKED'}}})
    r = m.output({})
    x = m.readiness(r, prior)
    self.assertEqual(x['blockers'], prior['blockers'])
    self.assertIsNone(x['independent_meter_result'])

  def test_frame_matched_pair_restoration(self):
    human = {'left': [[10, 30], [10, 10]], 'right': [[30, 30], [30, 10]], 'state': 'BOTH_EGO_BOUNDARIES_VISIBLE'}
    lanes = [{'points': [[15, 30], [15, 10]]}, {'points': [[35, 30], [35, 10]]}]
    pairs = e.matched_pairs(human, lanes)
    self.assertEqual(len(pairs['center']), 21)
    self.assertEqual(pairs['center'][0], [20.0, 10, 25.0, 10])
    self.assertEqual(pairs['left'][0], [10.0, 10, 15.0, 10])

  def test_one_side_no_center(self):
    human = {'left': [[10, 30], [10, 10]], 'right': [], 'state': 'LEFT_ONLY_VISIBLE'}
    x = e.matched_pairs(human, [{'points': [[15, 30], [15, 10]]}])
    self.assertEqual(x['center'], [])
    self.assertEqual(x['right'], [])

  def test_no_overlap_unavailable(self):
    human = {'left': [[10, 30], [10, 10]], 'right': [], 'state': 'LEFT_ONLY_VISIBLE'}
    x = e.matched_pairs(human, [{'points': [[15, 60], [15, 40]]}])
    self.assertEqual(x['left'], [])

  def test_public_field_whitelist(self):
    self.assertNotIn('sample_id', e.PUBLIC_KEYS)
    self.assertNotIn('coordinates', e.PUBLIC_KEYS)

  def test_duplicate_source_ids(self):
    with self.assertRaises(ValueError):
      e.unique_ids([{'sample_id': 'x'}, {'sample_id': 'x'}])

  def test_small_sample_flag(self):
    uv = m.fixed_query(10, 'ZERO_ORIGIN')
    x = m.summarize(m.project_pairs([[*uv, *uv]], m.nominal(), 'ZERO_ORIGIN'))
    self.assertTrue(x['bins'][1]['small_sample'])

  def test_count_cannot_hide_coordinate_arrays(self):
    with self.assertRaises(ValueError):
      e.safe_numbers({'count': [[123, 234], [124, 235]]})

  def test_statistic_cannot_hide_arrays(self):
    with self.assertRaises(ValueError):
      e.safe_numbers({'median': [1, 2]})

  def test_distribution_exact_shape(self):
    with self.assertRaises(ValueError):
      e.safe_numbers({'lateral_m': {'count': 1, 'median': 1, 'p90': 1, 'p95': 1, 'maximum': 1, 'extra': 1}})

  def test_unknown_coverage_keys_rejected(self):
    x = m.output(
      {
        'schema': 'DECLARED_HYPOTHESIS_APPROX_METER_ENVELOPE_V1',
        'status': 'CONDITIONAL_DIAGNOSTIC_COMPLETE',
        'executor_identity': e.executor_identity(),
        'policy': m.policy(),
        'fixed_distance': [],
        'holdout_projection': [],
        'scenario_attribution': [],
        'all_declared_envelopes': [],
        'coverage': {'/synthetic/private/key': 1},
      }
    )
    with self.assertRaises(ValueError):
      e.publication(x)

  def test_status_cannot_leak(self):
    x = m.output({'schema': 'DECLARED_HYPOTHESIS_APPROX_METER_ENVELOPE_V1', 'status': '/synthetic/private/status', 'executor_identity': e.executor_identity()})
    with self.assertRaises(ValueError):
      e.publication(x)

  def test_frozen_detector_binding_present(self):
    self.assertEqual(len(e.frozen_bindings()['detector_set_sha256']), 64)

  def test_immutable_derivative_conflict(self):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
      p = Path(d) / 'row.json'
      sha = e.immutable_write(p, b'one')
      self.assertEqual(e.immutable_write(p, b'one'), sha)
      with self.assertRaises(ValueError):
        e.immutable_write(p, b'two')

  def test_group_cannot_hide_coordinate_arrays(self):
    with self.assertRaises(ValueError):
      e.safe_numbers([{'group': [[123, 234], [124, 235]]}])

  def test_bare_row_arrays_rejected(self):
    with self.assertRaises(ValueError):
      e.safe_numbers([[123, 234], [124, 235]])

  def test_distance_requires_scalar_declared_query(self):
    with self.assertRaises(ValueError):
      e.safe_numbers({'distance_m': [5, 10]})

  def test_invalid_mapping_scalar_rejected(self):
    with self.assertRaises(ValueError):
      e.safe_numbers({'mapping': 'center'})


if __name__ == '__main__':
  unittest.main()
