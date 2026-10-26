import math
import unittest
from itertools import pairwise
from dataclasses import replace


class TestSyntheticLateralScenarioMatrix(unittest.TestCase):
  def matrix(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_scenarios import (
      build_default_matrix,
    )
    return build_default_matrix()

  def test_default_matrix_covers_required_strata_and_stress_axes(self):
    from openpilot.tools.cyber_autotune.preflight import REQUIRED_STRATA
    from openpilot.tools.cyber_autotune.synthetic_lateral_scenarios import (
      REQUIRED_STRESS_AXES,
      assess_scenario_matrix,
    )

    result = assess_scenario_matrix(self.matrix())
    self.assertEqual(result.status, 'SYNTHETIC_MATRIX_READY')
    self.assertTrue(result.structural_pass)
    self.assertEqual(set(result.covered_strata), set(REQUIRED_STRATA))
    self.assertEqual(set(result.covered_stress_axes), set(REQUIRED_STRESS_AXES))
    self.assertGreaterEqual(result.nominal_scenario_count, 8)
    self.assertGreaterEqual(result.fault_scenario_count, 2)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_default_matrix_and_frames_are_deterministic(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_scenarios import (
      generate_frames,
      matrix_sha256,
    )

    first = self.matrix()
    second = self.matrix()
    self.assertEqual(first, second)
    self.assertEqual(matrix_sha256(first), matrix_sha256(second))
    for left, right in zip(first, second, strict=True):
      self.assertEqual(generate_frames(left), generate_frames(right))

  def test_nominal_frames_are_uniform_finite_and_in_domain(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_scenarios import (
      generate_frames,
    )

    for scenario in self.matrix():
      if scenario.expected_outcome != 'COMPLETED':
        continue
      frames = generate_frames(scenario)
      self.assertGreaterEqual(len(frames), 2)
      for index, frame in enumerate(frames):
        self.assertEqual(frame.step_index, index)
        self.assertAlmostEqual(frame.time_s, index * scenario.dt_s)
        self.assertTrue(math.isfinite(frame.speed_mps))
        self.assertTrue(math.isfinite(frame.desired_curvature_1pm))
        self.assertTrue(math.isfinite(frame.lateral_delay_s))
        self.assertTrue(math.isfinite(frame.plant_friction_scale))
        self.assertTrue(frame.sensor_valid)

  def test_left_right_curves_are_sign_symmetric(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_scenarios import (
      generate_frames,
    )

    scenarios = {item.scenario_id: item for item in self.matrix()}
    for left_id, right_id in (
      ('gentle_left', 'gentle_right'),
      ('tight_left', 'tight_right'),
    ):
      left = generate_frames(scenarios[left_id])
      right = generate_frames(scenarios[right_id])
      self.assertEqual(len(left), len(right))
      for a, b in zip(left, right, strict=True):
        self.assertAlmostEqual(a.speed_mps, b.speed_mps)
        self.assertAlmostEqual(a.desired_curvature_1pm, -b.desired_curvature_1pm)

  def test_s_curve_crosses_zero_and_ramp_has_entry_apex_exit(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_scenarios import (
      generate_frames,
    )

    scenarios = {item.scenario_id: item for item in self.matrix()}
    s_values = [f.desired_curvature_1pm for f in generate_frames(scenarios['s_curve'])]
    self.assertLess(min(s_values), 0.0)
    self.assertGreater(max(s_values), 0.0)
    ramp = generate_frames(scenarios['ramp_curve'])
    thirds = len(ramp) // 3
    self.assertLess(abs(ramp[0].desired_curvature_1pm), abs(ramp[thirds].desired_curvature_1pm))
    self.assertGreaterEqual(abs(ramp[thirds].desired_curvature_1pm), abs(ramp[2 * thirds].desired_curvature_1pm))
    self.assertLess(abs(ramp[-1].desired_curvature_1pm), abs(ramp[2 * thirds].desired_curvature_1pm))

  def test_override_release_and_reengagement_are_explicit(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_scenarios import (
      generate_frames,
    )

    scenario = next(item for item in self.matrix() if item.scenario_id == 'driver_override')
    frames = generate_frames(scenario)
    pressed = [frame for frame in frames if frame.steering_pressed]
    released = [frame for frame in frames if not frame.steering_pressed]
    inactive = [frame for frame in frames if not frame.active]
    reengaged = [frame for frame in frames if frame.active and frame.step_index > pressed[-1].step_index]
    self.assertTrue(pressed)
    self.assertTrue(released)
    self.assertTrue(inactive)
    self.assertTrue(reengaged)

  def test_fault_scenarios_are_separated_from_performance_inputs(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_scenarios import (
      generate_frames,
    )

    scenarios = {item.scenario_id: item for item in self.matrix()}
    dropout = scenarios['sensor_dropout']
    self.assertEqual(dropout.expected_outcome, 'REJECTED_INPUT')
    self.assertTrue(any(not frame.sensor_valid for frame in generate_frames(dropout)))

    gap = scenarios['timebase_gap']
    gap_frames = generate_frames(gap)
    deltas = [b.time_s - a.time_s for a, b in pairwise(gap_frames)]
    self.assertEqual(sum(abs(delta - gap.dt_s) > 1e-12 for delta in deltas), 1)
    self.assertEqual(gap.expected_outcome, 'REJECTED_INPUT')

  def test_invalid_matrix_shape_and_duplicate_ids_fail_closed(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_scenarios import (
      assess_scenario_matrix,
    )

    matrix = self.matrix()
    for bad in (
      [],
      matrix[:-1],
      matrix + (matrix[0],),
      tuple(replace(item, scenario_id='duplicate') if index < 2 else item
            for index, item in enumerate(matrix)),
    ):
      with self.subTest(bad_type=type(bad).__name__):
        result = assess_scenario_matrix(bad)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertFalse(result.structural_pass)
        self.assertFalse(result.runtime_accepted)
        self.assertFalse(result.promotable)

  def test_nonfinite_or_out_of_domain_parameters_are_blocked(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_scenarios import (
      assess_scenario_matrix,
    )

    matrix = self.matrix()
    mutations = (
      replace(matrix[0], duration_s=math.nan),
      replace(matrix[0], dt_s=0.0),
      replace(matrix[0], speed_mps=-1.0),
      replace(matrix[0], lateral_delay_s=-0.1),
      replace(matrix[0], plant_friction_scale=0.0),
      replace(matrix[0], curvature_amplitude_1pm=1.0),
    )
    for mutation in mutations:
      result = assess_scenario_matrix((mutation,) + matrix[1:])
      self.assertEqual(result.status, 'BLOCKED')

  def test_matrix_hash_is_order_sensitive_and_coverage_is_counted(self):
    from openpilot.tools.cyber_autotune.preflight import REQUIRED_STRATA
    from openpilot.tools.cyber_autotune.synthetic_lateral_scenarios import (
      coverage_counts,
      matrix_sha256,
    )

    matrix = self.matrix()
    self.assertNotEqual(matrix_sha256(matrix), matrix_sha256(tuple(reversed(matrix))))
    counts = dict(coverage_counts(matrix))
    self.assertEqual(set(counts), set(REQUIRED_STRATA))
    self.assertTrue(all(type(value) is int and value > 0 for value in counts.values()))

  def test_matrix_report_never_grants_execution_or_vehicle_authority(self):
    from openpilot.tools.cyber_autotune.synthetic_lateral_scenarios import (
      assess_scenario_matrix,
    )

    result = assess_scenario_matrix(self.matrix())
    self.assertFalse(result.controller_executed)
    self.assertFalse(result.plant_executed)
    self.assertFalse(result.vehicle_or_can_write)
    self.assertFalse(result.performance_qualified)
    self.assertFalse(result.candidate_generation_allowed)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)


if __name__ == '__main__':
  unittest.main()
