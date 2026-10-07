from dataclasses import replace
import unittest


def h(char):
  return char * 64


class TestCurvatureYawClosedLoop(unittest.TestCase):
  def api(self):
    from openpilot.tools.cyber_autotune import curvature_yaw_closed_loop as api
    return api

  def case(self, commands=(0.2, 0.2, 0.2, 0.2, 0.2)):
    api = self.api()
    from openpilot.tools.cyber_autotune.curvature_yaw_plant import (
      CurvatureYawPlantConfig,
      CurvatureYawPlantState,
      observe_curvature_yaw_step,
    )
    from openpilot.tools.cyber_autotune.lateral_closed_loop import (
      ClosedLoopBinding,
      ClosedLoopDomain,
      ClosedLoopFrame,
      frames_sha256,
      timebase_sha256,
    )

    config = CurvatureYawPlantConfig(
      dt_s=0.01,
      delay_steps=2,
      min_speed_mps=2.5,
      max_speed_mps=8.0,
      command_limit=1.0,
      curvature_intercept_1pm=0.0,
      curvature_ar=0.9,
      command_gain_1pm=0.02,
      command_speed_gain_s_per_m2=0.001,
      command_inv_speed_gain_per_s=0.03,
      roll_gain_1pm_per_rad=0.004,
      yaw_ar=0.8,
      yaw_bias_rad_s=0.0,
    )
    initial = api.CurvatureYawClosedLoopState(
      plant_state=CurvatureYawPlantState(0.0, 0.0, (0.0, 0.0)),
      heading_rad=0.0,
      pose_y_m=0.0,
    )
    domain = ClosedLoopDomain(
      identity_sha256=h('a'),
      dt_s=0.01,
      min_speed_mps=3.0,
      max_speed_mps=7.0,
      physical_actuator_delay_s=0.02,
      physical_delay_owner='PLANT',
      normalized_command_limit=1.0,
    )
    frames = tuple(
      ClosedLoopFrame(
        step_index=i,
        time_s=i * 0.01,
        speed_mps=5.0,
        accel_mps2=0.0,
        roll_rad=0.01,
        desired_curvature=0.001,
        active=True,
        steering_pressed=False,
        controller_prediction_delay_s=0.2,
      )
      for i in range(5)
    )

    state = initial
    transcript = []
    for frame, command in zip(frames, commands, strict=True):
      feedback = api.CurvatureYawControllerFeedback(
        step_index=frame.step_index,
        time_s=frame.time_s,
        curvature_1pm=state.plant_state.curvature_1pm,
        yaw_rate_rad_s=state.plant_state.yaw_rate_rad_s,
        lateral_accel_mps2=state.plant_state.yaw_rate_rad_s * frame.speed_mps,
        heading_rad=state.heading_rad,
        pose_y_m=state.pose_y_m,
      )
      transcript.append(api.CurvatureYawControllerStep(
        step_index=frame.step_index,
        time_s=frame.time_s,
        feedback_sha256=api.controller_feedback_sha256(feedback),
        requested_normalized_torque=command,
      ))
      observation = observe_curvature_yaw_step(
        config, state.plant_state,
        command=-command,
        speed_mps=frame.speed_mps,
        roll_rad=frame.roll_rad,
      )
      next_plant = observation.next_state
      next_heading = state.heading_rad + next_plant.yaw_rate_rad_s * domain.dt_s
      import math
      next_pose = state.pose_y_m + frame.speed_mps * math.sin(next_heading) * domain.dt_s
      state = api.CurvatureYawClosedLoopState(next_plant, next_heading, next_pose)

    transcript = tuple(transcript)
    plant_hash = api.plant_config_sha256(config)
    state_hash = api.closed_loop_state_sha256(initial)
    transcript_hash = api.controller_transcript_sha256(transcript)
    binding = ClosedLoopBinding(
      software_sha256=h('b'),
      controller_sha256=h('c'),
      adapter_sha256=h('d'),
      plant_sha256=h('e'),
      plant_calibration_sha256=h('6'),
      domain_sha256=domain.identity_sha256,
      inputs_sha256=frames_sha256(frames),
      reset_sha256=state_hash,
      metric_sha256=h('1'),
      environment_sha256=h('2'),
      timebase_sha256=timebase_sha256(frames),
    )
    contract = api.CurvatureYawRunContract(
      controller_identity_sha256=binding.controller_sha256,
      expected_plant_config_sha256=plant_hash,
      expected_initial_state_sha256=state_hash,
      expected_controller_transcript_sha256=transcript_hash,
      controller_to_plant_sign=-1.0,
    )
    return api, config, initial, domain, frames, binding, contract, transcript

  def test_transcript_produces_structurally_admitted_receipt(self):
    api, config, initial, domain, frames, binding, contract, transcript = self.case()
    result = api.run_curvature_yaw_closed_loop(
      domain, frames, binding, config, initial, contract, transcript,
    )

    self.assertEqual(result.status, 'STRUCTURAL_ADMISSION')
    self.assertTrue(result.structural_admission_pass)
    self.assertEqual(len(result.receipt.samples), len(frames))
    self.assertEqual(result.receipt.physical_delay_owners, ('PLANT',))
    self.assertFalse(result.receipt.controller_delay_queue_present)
    self.assertEqual(result.receipt.samples[0].applied_normalized_torque, -0.0)
    self.assertEqual(result.receipt.samples[1].applied_normalized_torque, -0.0)
    self.assertAlmostEqual(result.receipt.samples[2].applied_normalized_torque, 0.2)
    self.assertIn('CONTROLLER_PRODUCER_AUTHENTICITY_UNVERIFIED', result.blockers)
    self.assertIn('CONTROLLER_PRODUCER_NONACTUATION_UNVERIFIED', result.blockers)
    self.assertIn('CURVATURE_YAW_ADAPTER_OFFLINE_ONLY', result.blockers)
    self.assertFalse(result.qualified_closed_loop)
    self.assertFalse(result.performance_qualified)
    self.assertFalse(result.vehicle_or_can_write)
    self.assertFalse(result.parameter_write)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)

  def test_run_is_deterministic(self):
    api, config, initial, domain, frames, binding, contract, transcript = self.case()
    first = api.run_curvature_yaw_closed_loop(
      domain, frames, binding, config, initial, contract, transcript,
    )
    second = api.run_curvature_yaw_closed_loop(
      domain, frames, binding, config, initial, contract, transcript,
    )
    self.assertEqual(first, second)
    self.assertEqual(first.envelope_sha256, second.envelope_sha256)
    self.assertEqual(first.controller_transcript_sha256, second.controller_transcript_sha256)
    self.assertNotEqual(first.initial_state_sha256, first.final_state_sha256)

  def test_config_state_transcript_controller_and_reset_bindings_fail_closed(self):
    api, config, initial, domain, frames, binding, contract, transcript = self.case()
    cases = (
      (binding, replace(contract, expected_plant_config_sha256=h('9')), 'PLANT_CONFIG_BINDING_MISMATCH'),
      (binding, replace(contract, expected_initial_state_sha256=h('8')), 'INITIAL_STATE_BINDING_MISMATCH'),
      (binding, replace(contract, expected_controller_transcript_sha256=h('7')), 'CONTROLLER_TRANSCRIPT_BINDING_MISMATCH'),
      (binding, replace(contract, controller_identity_sha256=h('4')), 'CONTROLLER_BINDING_MISMATCH'),
      (replace(binding, reset_sha256=h('5')), contract, 'RESET_BINDING_MISMATCH'),
    )
    for candidate_binding, candidate_contract, reason in cases:
      with self.subTest(reason=reason):
        result = api.run_curvature_yaw_closed_loop(
          domain, frames, candidate_binding, config, initial,
          candidate_contract, transcript,
        )
        self.assertEqual(result.status, 'BLOCKED')
        self.assertIn(reason, result.blockers)

  def test_feedback_hash_mismatch_fails_before_plant_progression(self):
    api, config, initial, domain, frames, binding, contract, transcript = self.case()
    bad = (replace(transcript[0], feedback_sha256=h('9')),) + transcript[1:]
    bad_contract = replace(
      contract,
      expected_controller_transcript_sha256=api.controller_transcript_sha256(bad),
    )
    result = api.run_curvature_yaw_closed_loop(
      domain, frames, binding, config, initial, bad_contract, bad,
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertEqual(result.blockers, ('CONTROLLER_FEEDBACK_BINDING_MISMATCH',))

  def test_transcript_timebase_and_cardinality_fail_closed(self):
    api, config, initial, domain, frames, binding, contract, transcript = self.case()
    shifted = (replace(transcript[0], time_s=0.001),) + transcript[1:]
    shifted_contract = replace(
      contract,
      expected_controller_transcript_sha256=api.controller_transcript_sha256(shifted),
    )
    result = api.run_curvature_yaw_closed_loop(
      domain, frames, binding, config, initial, shifted_contract, shifted,
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('CONTROLLER_TRANSCRIPT_TIMEBASE_MISMATCH', result.blockers)

    result = api.run_curvature_yaw_closed_loop(
      domain, frames, binding, config, initial, contract, transcript[:-1],
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('INVALID_CONTROLLER_TRANSCRIPT', result.blockers)

  def test_domain_and_command_limits_fail_closed(self):
    api, config, initial, domain, frames, binding, contract, transcript = self.case()
    bad_domain = replace(domain, physical_actuator_delay_s=0.03)
    result = api.run_curvature_yaw_closed_loop(
      bad_domain, frames, binding, config, initial, contract, transcript,
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('PLANT_DOMAIN_MISMATCH', result.blockers)

    api, config, initial, domain, frames, binding, contract, transcript = self.case()
    bad = (replace(transcript[0], requested_normalized_torque=1.01),) + transcript[1:]
    bad_contract = replace(
      contract,
      expected_controller_transcript_sha256=api.controller_transcript_sha256(bad),
    )
    result = api.run_curvature_yaw_closed_loop(
      domain, frames, binding, config, initial, bad_contract, bad,
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertIn('CONTROLLER_COMMAND_OUTSIDE_DOMAIN', result.blockers)

  def test_invalid_inputs_have_no_authority(self):
    api, config, initial, domain, frames, binding, contract, transcript = self.case()
    result = api.run_curvature_yaw_closed_loop(
      domain, frames, binding, config, initial,
      replace(contract, controller_to_plant_sign=0.0), transcript,
    )
    self.assertEqual(result.status, 'BLOCKED')
    self.assertFalse(result.structural_admission_pass)
    self.assertFalse(result.vehicle_or_can_write)
    self.assertFalse(result.parameter_write)
    self.assertFalse(result.runtime_accepted)
    self.assertFalse(result.promotable)


if __name__ == '__main__':
  unittest.main()
