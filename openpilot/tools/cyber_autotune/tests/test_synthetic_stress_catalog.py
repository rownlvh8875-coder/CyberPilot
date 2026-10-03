import unittest


def test_pose_timestamp_jitter_rejected_separately_from_pose_value_stress():
  from dataclasses import replace
  from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog, frames, validate_frames
  case = next(c for c in catalog() if c.case_id == 'lat_pose_jitter')
  rows = frames(case)
  assert validate_frames(rows, case.dt_s) == 'VALID'
  jittered = (*rows[:100], replace(rows[100], time_ns=rows[100].time_ns + 1), *rows[101:])
  assert validate_frames(jittered, case.dt_s) == 'INVALID_TIMEBASE'


class TestSyntheticStressCatalog(unittest.TestCase):
  def test_catalog_has_required_axes_and_unique_cases(self):
    from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog
    cases = catalog()
    self.assertEqual(sum(case.axis == 'lateral' for case in cases), 26)
    self.assertEqual(sum(case.axis == 'longitudinal' for case in cases), 18)
    self.assertEqual(len({case.case_id for case in cases}), 44)
    self.assertTrue(all(case.dt_s == .01 for case in cases))

  def test_left_right_inputs_are_exact_mirrors(self):
    from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog, frames
    cases = {case.case_id: case for case in catalog()}
    for prefix in ('constant', 'increasing'):
      left = frames(cases['lat_' + prefix + '_left'])
      right = frames(cases['lat_' + prefix + '_right'])
      self.assertEqual(tuple(row.curvature for row in left), tuple(-row.curvature for row in right))
      self.assertGreater(max(row.curvature for row in left), 0.)

  def test_faults_are_actual_input_faults_not_only_expected_labels(self):
    from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog, frames, validate_frames
    for case in catalog():
      result = validate_frames(frames(case), case.dt_s)
      with self.subTest(case=case.case_id):
        self.assertEqual(result, case.expected_input_status)

  def test_pose_lane_override_and_speed_inputs_change(self):
    from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog, frames
    cases = {case.case_id: case for case in catalog()}
    checks = (
      ('lat_pose_jitter', 'pose_yaw_bias'), ('lat_lane_loss', 'lane_visible'),
      ('lat_laneless_transition', 'lane_visible'), ('lat_override_recovery', 'active'),
      ('lat_speed_sweep', 'speed_mps'), ('lat_friction_gain', 'friction_scale'),
      ('lat_friction_gain', 'gain_scale'), ('lat_edge_bias', 'path_bias_m'),
      ('long_cut_in', 'lead_available'), ('long_cut_out', 'lead_available'),
      ('long_grade', 'grade_accel'), ('long_signal_stop', 'should_stop'),
      ('long_stop_start', 'should_stop'), ('long_false_stop', 'should_stop'),
    )
    for case_id, field in checks:
      with self.subTest(case=case_id, field=field):
        self.assertGreater(len({getattr(row, field) for row in frames(cases[case_id])}), 1)

  def test_unknown_case_and_excessive_duration_fail_closed(self):
    from dataclasses import replace
    from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog, frames
    for case in (replace(catalog()[0], case_id='unknown'), replace(catalog()[0], duration_s=1e9)):
      with self.assertRaises(ValueError):
        frames(case)

  def test_catalog_and_normal_inputs_repeat_exactly(self):
    from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog, frames, catalog_digest
    self.assertEqual(catalog_digest(), catalog_digest())
    for case in catalog():
      if case.expected_input_status == 'VALID':
        self.assertEqual(frames(case), frames(case))

  def test_supplied_reference_cases_are_not_aliases(self):
    from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog, frames
    cases = {case.case_id: case for case in catalog()}
    avoidance = frames(cases['lat_provided_avoidance'])
    self.assertTrue(avoidance != frames(cases['lat_s_curve']))
    self.assertGreater(max(row.path_bias_m for row in avoidance), .5)
    signal = frames(cases['long_signal_stop'])
    self.assertFalse(any(row.lead_available for row in signal))
    self.assertTrue(signal != frames(cases['long_stopped_lead']))
    wrong_stop = frames(cases['long_false_stop'])
    self.assertTrue(any(row.should_stop for row in wrong_stop))
    self.assertFalse(any(row.stop_required for row in wrong_stop))

  def test_native_timestamp_and_reset_gap_domains(self):
    from dataclasses import replace
    from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog, frames, validate_frames
    rows = frames(catalog()[0])
    self.assertEqual(validate_frames(tuple(replace(row, time_ns=row.time_ns + 2 ** 100) for row in rows), .01), 'INVALID_TIMEBASE')
    self.assertEqual(validate_frames((replace(rows[0], lead_distance_reset_m=-1.), *rows[1:]), .01), 'INVALID_FRAME_DOMAIN')

  def test_catalog_identity_changes_when_generated_inputs_change(self):
    from dataclasses import replace
    from unittest.mock import patch
    from openpilot.tools.cyber_autotune import synthetic_stress_catalog as module
    baseline = module.catalog_digest()
    original = module.frames

    def changed(case):
      rows = original(case)
      return (replace(rows[0], speed_mps=rows[0].speed_mps + .1), *rows[1:])

    with patch.object(module, 'frames', side_effect=changed):
      self.assertNotEqual(module.catalog_digest(), baseline)

  def test_distinguishing_reference_inputs_are_frozen(self):
    from openpilot.tools.cyber_autotune.synthetic_stress_catalog import catalog, input_digest
    expected = {
      'lat_provided_avoidance': '787da1f3de3f7942009f351ad052a2fcf23c0612271c6b6d6651be7f5b777766',
      'long_signal_stop': 'e22bf64fb9940c05506ffe3a4cd0eb1fc06e594c8c4ee7c1c03f372a3ba1691d',
      'long_false_stop': '4f1238a5ecbef5b01bd2676ab8229be894c18b25a948e603bbeba3a72f0251cc',
    }
    for case in catalog():
      if case.case_id in expected:
        self.assertEqual(input_digest(case), expected[case.case_id])
