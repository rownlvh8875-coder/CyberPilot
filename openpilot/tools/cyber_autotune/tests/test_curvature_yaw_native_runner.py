import copy
import hashlib
import unittest

from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import (
  ADAPTER_PATH,
  PLANT_PATH,
  SUPPORT_FILES,
  encode_request,
  producer_identity_sha256,
)
from openpilot.tools.cyber_autotune.curvature_yaw_native_runner import (
  admit_native_transcript,
  closed_loop_frames,
  initial_state,
  run_native_transcript,
  validate_response,
)
from openpilot.tools.cyber_autotune.curvature_yaw_closed_loop import closed_loop_state_sha256
from openpilot.tools.cyber_autotune.lateral_closed_loop import (
  ClosedLoopBinding,
  ClosedLoopDomain,
  frames_sha256,
  timebase_sha256,
)
from openpilot.tools.cyber_autotune.tests.test_native_worker import ROOT, fixture


def h(char):
  return char * 64


def request_fixture():
  native = fixture()
  for frame in native['frames']:
    frame['speed_mps'] = 5.0
    frame['steer_ratio'] = 16.0
    frame['angle_deg'] = 0.0
    frame['rate_deg_s'] = 0.0
    frame['desired_curvature_1pm'] = 0.0015
    frame['roll_rad'] = 0.0
    frame['lateral_delay_s'] = 0.15
  return {
    'version': 1,
    'native': native,
    'support_files': {
      name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
      for name in SUPPORT_FILES
    },
    'plant_config': {
      'dt_s': 0.01,
      'delay_steps': 2,
      'min_speed_mps': 2.5,
      'max_speed_mps': 8.0,
      'command_limit': 1.0,
      'curvature_intercept_1pm': 0.0,
      'curvature_ar': 0.92,
      'command_gain_1pm': 0.004,
      'command_speed_gain_s_per_m2': 0.0002,
      'command_inv_speed_gain_per_s': 0.002,
      'roll_gain_1pm_per_rad': 0.001,
      'yaw_ar': 0.75,
      'yaw_bias_rad_s': 0.0,
    },
    'initial_state': {
      'curvature_1pm': 0.0,
      'yaw_rate_rad_s': 0.0,
      'command_history': [0.0, 0.0],
      'heading_rad': 0.0,
      'pose_y_m': 0.0,
    },
    'controller_to_plant_sign': -1.0,
  }


def binding_for(request, result, domain):
  frames = closed_loop_frames(request)
  return ClosedLoopBinding(
    software_sha256=producer_identity_sha256(request),
    controller_sha256=result['controller_identity_sha256'],
    adapter_sha256=request['support_files'][ADAPTER_PATH],
    plant_sha256=request['support_files'][PLANT_PATH],
    plant_calibration_sha256=h('6'),
    domain_sha256=domain.identity_sha256,
    inputs_sha256=frames_sha256(frames),
    reset_sha256=closed_loop_state_sha256(initial_state(request)),
    metric_sha256=h('1'),
    environment_sha256=h('2'),
    timebase_sha256=timebase_sha256(frames),
  )


class TestCurvatureYawNativeProtocol(unittest.TestCase):
  def test_roundtrip_and_recorded_steering_rejection(self):
    request = request_fixture()
    self.assertTrue(encode_request(request))
    bad = copy.deepcopy(request)
    bad['native']['frames'][0]['angle_deg'] = 1.0
    with self.assertRaises(ValueError):
      encode_request(bad)
    bad = copy.deepcopy(request)
    bad['native']['frames'][0]['time_ns'] = 10_000_000
    with self.assertRaises(ValueError):
      encode_request(bad)

  def test_support_plant_and_state_bindings_are_strict(self):
    request = request_fixture()
    for mutate in ('support', 'delay', 'history', 'sign'):
      bad = copy.deepcopy(request)
      if mutate == 'support':
        bad['support_files'][PLANT_PATH] = 'bad'
      elif mutate == 'delay':
        bad['plant_config']['delay_steps'] = -1
      elif mutate == 'history':
        bad['initial_state']['command_history'] = [0.0]
      else:
        bad['controller_to_plant_sign'] = 0.0
      with self.subTest(mutate=mutate), self.assertRaises(ValueError):
        encode_request(bad)


class TestCurvatureYawNativeRunner(unittest.TestCase):
  def test_real_isolated_producer_is_repeatable_and_public_adapter_admits(self):
    request = request_fixture()
    original = copy.deepcopy(request)
    first = run_native_transcript(request, timeout_s=10.0)
    second = run_native_transcript(request, timeout_s=10.0)
    self.assertEqual(first['status'], 'COMPLETED')
    self.assertEqual(first, second)
    self.assertEqual(request, original)
    self.assertEqual(len(first['controller_transcript']), len(request['native']['frames']))
    self.assertTrue(any(abs(row['requested_normalized_torque']) > 0 for row in first['controller_transcript']))
    self.assertFalse(first['runtime_accepted'])
    self.assertFalse(first['promotable'])

    domain = ClosedLoopDomain(
      identity_sha256=h('a'),
      dt_s=0.01,
      min_speed_mps=3.0,
      max_speed_mps=7.0,
      physical_actuator_delay_s=0.02,
      physical_delay_owner='PLANT',
      normalized_command_limit=1.0,
    )
    binding = binding_for(request, first, domain)
    admitted = admit_native_transcript(request, first, domain, binding)
    self.assertEqual(admitted.status, 'STRUCTURAL_ADMISSION')
    self.assertTrue(admitted.structural_admission_pass)
    self.assertEqual(admitted.controller_transcript_sha256, first['controller_transcript_sha256'])
    self.assertEqual(admitted.final_state_sha256, first['final_state_sha256'])
    self.assertFalse(admitted.qualified_closed_loop)
    self.assertFalse(admitted.runtime_accepted)
    self.assertFalse(admitted.promotable)

  def test_inactive_native_controller_stays_zero_and_still_admits(self):
    request = request_fixture()
    for frame in request['native']['frames']:
      frame['active'] = False
    result = run_native_transcript(request, timeout_s=10.0)
    self.assertEqual(result['status'], 'COMPLETED')
    self.assertTrue(all(row['requested_normalized_torque'] == 0.0 for row in result['controller_transcript']))

    domain = ClosedLoopDomain(h('a'), 0.01, 3.0, 7.0, 0.02, 'PLANT', 1.0)
    admitted = admit_native_transcript(request, result, domain, binding_for(request, result, domain))
    self.assertEqual(admitted.status, 'STRUCTURAL_ADMISSION')

  def test_source_and_support_tamper_fail_without_completed_transcript(self):
    request = request_fixture()
    request['native']['source']['head'] = '0' * 40
    result = run_native_transcript(request, timeout_s=10.0)
    self.assertEqual(result['status'], 'WORKER_FAILED')
    self.assertNotIn('controller_transcript', result)

    request = request_fixture()
    request['support_files'][ADAPTER_PATH] = '0' * 64
    result = run_native_transcript(request, timeout_s=10.0)
    self.assertEqual(result['status'], 'WORKER_FAILED')
    self.assertNotIn('controller_transcript', result)

  def test_response_and_admission_identity_tamper_are_rejected(self):
    request = request_fixture()
    result = run_native_transcript(request, timeout_s=10.0)
    self.assertEqual(result['status'], 'COMPLETED')

    changed = copy.deepcopy(result)
    changed['controller_transcript'][0]['requested_normalized_torque'] += 0.01
    with self.assertRaises(ValueError):
      validate_response(request, changed)

    domain = ClosedLoopDomain(h('a'), 0.01, 3.0, 7.0, 0.02, 'PLANT', 1.0)
    binding = binding_for(request, result, domain)
    with self.assertRaises(ValueError):
      admit_native_transcript(
        request, result, domain,
        ClosedLoopBinding(**{**binding.__dict__, 'plant_sha256': h('9')}),
      )

  def test_timeout_and_bad_request_do_not_gain_authority(self):
    request = request_fixture()
    for timeout in (0, -1, True, float('inf'), 61):
      with self.subTest(timeout=timeout), self.assertRaises(ValueError):
        run_native_transcript(request, timeout_s=timeout)
    bad = copy.deepcopy(request)
    bad['initial_state']['command_history'] = []
    with self.assertRaises(ValueError):
      run_native_transcript(bad, timeout_s=1.0)


if __name__ == '__main__':
  unittest.main()
