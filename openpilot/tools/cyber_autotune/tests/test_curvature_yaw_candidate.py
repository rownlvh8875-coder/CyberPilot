"""Synthetic-only controller selector and native-core candidate tests."""
import base64
import copy
import hashlib
import unittest

from opendbc.car import structs

from openpilot.tools.cyber_autotune.tests.test_curvature_yaw_native_runner import request_fixture, binding_for
from openpilot.tools.cyber_autotune.tests.test_native_worker import ROOT
from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import encode_request, controller_identity_sha256
from openpilot.tools.cyber_autotune.curvature_yaw_native_runner import run_native_transcript, validate_response, admit_native_transcript
from openpilot.tools.cyber_autotune.lateral_closed_loop import ClosedLoopDomain


def candidate_config():
  return {'points': [[0., 4., .125], [10., 4.+1/128, .125+1/2048],
                     [20., 4.+1/64, .125+1/1024], [30., 4., .125]]}


def v2_request(implementation='SPEED_SCHEDULE', count=180):
  from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import CANDIDATE_FILES
  request = request_fixture()
  request['version'] = 2
  request['controller'] = {'implementation': implementation, 'config': candidate_config() if implementation == 'SPEED_SCHEDULE' else {}}
  request['support_files'].update({p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in CANDIDATE_FILES})
  with structs.CarParams.from_bytes(base64.b64decode(request['native']['car_params_base64'])) as reader:
    cp = reader.as_builder()
  cp.lateralTuning.torque.latAccelFactor = 4.
  cp.lateralTuning.torque.friction = .125
  raw = cp.to_bytes()
  request['native']['car_params_base64'] = base64.b64encode(raw).decode()
  request['native']['car_params_sha256'] = hashlib.sha256(raw).hexdigest()
  frame = request['native']['frames'][0]
  request['native']['frames'] = [dict(frame, time_ns=i*10_000_000) for i in range(count)]
  return request


class TestCurvatureYawCandidate(unittest.TestCase):
  def test_v2_selector_config_and_source_binding_change_identity(self):
    native, candidate = v2_request('NATIVE'), v2_request()
    self.assertNotEqual(controller_identity_sha256(native), controller_identity_sha256(candidate))
    changed = copy.deepcopy(candidate)
    changed['controller']['config']['points'][1][1] += 1/1024
    self.assertNotEqual(controller_identity_sha256(candidate), controller_identity_sha256(changed))
    changed = copy.deepcopy(candidate)
    from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import CANDIDATE_FILES
    changed['support_files'][CANDIDATE_FILES[0]] = 'a'*64
    self.assertNotEqual(controller_identity_sha256(candidate), controller_identity_sha256(changed))

  def test_v1_remains_strict_and_native_v2_preserves_outputs(self):
    v2 = v2_request('NATIVE')
    v1 = copy.deepcopy(v2)
    v1['version'] = 1
    del v1['controller']
    from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import SUPPORT_FILES
    v1['support_files'] = {p:v1['support_files'][p] for p in SUPPORT_FILES}
    a, b = run_native_transcript(v1, timeout_s=10.), run_native_transcript(v2, timeout_s=10.)
    self.assertEqual(a['status'], 'COMPLETED')
    self.assertEqual(a['controller_transcript'], b['controller_transcript'])
    self.assertEqual(a['metric_observations'], b['metric_observations'])
    self.assertEqual(a['final_state_sha256'], b['final_state_sha256'])
    v1['controller'] = v2['controller']
    with self.assertRaises(ValueError):
      encode_request(v1)

  def test_candidate_is_repeatable_non_noop_and_public_replay_admits(self):
    request = v2_request()
    before = copy.deepcopy(request)
    candidate = run_native_transcript(request, timeout_s=10.)
    self.assertEqual(candidate['status'], 'COMPLETED')
    self.assertEqual(candidate, run_native_transcript(request, timeout_s=10.))
    self.assertEqual(before, request)
    native = run_native_transcript(v2_request('NATIVE'), timeout_s=10.)
    self.assertNotEqual(candidate['controller_transcript'], native['controller_transcript'])
    torque = [r['requested_normalized_torque'] for r in candidate['controller_transcript']]
    self.assertTrue(all(abs(v) <= 1. for v in torque))
    self.assertTrue(any(a['requested_normalized_torque'] != b['requested_normalized_torque']
                        for a,b in zip(candidate['controller_transcript'],native['controller_transcript'],strict=True)))
    self.assertEqual(candidate['controller_spec'], request['controller'])
    self.assertTrue(any(r[0] != 4. or r[2] != .125 for r in candidate['effective_parameters']))
    domain = ClosedLoopDomain('a'*64, .01, 3., 7., .02, 'PLANT', 1.)
    result = admit_native_transcript(request, candidate, domain, binding_for(request,candidate,domain))
    self.assertEqual(result.status, 'STRUCTURAL_ADMISSION')
    self.assertFalse(result.qualified_closed_loop)
    self.assertFalse(result.promotable)

  def test_selector_fields_and_nonfinite_configuration_fail_closed(self):
    request = v2_request()
    for spec in ({'implementation':'UNKNOWN','config':{}},
                 {'implementation':'NATIVE','config':candidate_config()},
                 {'implementation':'SPEED_SCHEDULE','config':{'points':[]}},
                 {'implementation':'SPEED_SCHEDULE','config':{'points':[[0.,True,.1],[10.,4.,.1]]}}):
      with self.subTest(spec=spec), self.assertRaises(ValueError):
        encode_request(dict(request,controller=spec))

  def test_invalid_late_schedule_and_forged_source_abort(self):
    request = v2_request()
    request['controller']['config']['points'][-1][1] = 5.
    self.assertEqual(run_native_transcript(request,timeout_s=10.)['status'], 'WORKER_FAILED')
    request = v2_request()
    from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import CANDIDATE_FILES
    request['support_files'][CANDIDATE_FILES[0]] = 'a'*64
    self.assertEqual(run_native_transcript(request,timeout_s=10.)['status'], 'WORKER_FAILED')

  def test_inactive_and_pressed_inputs_do_not_modify_configuration(self):
    request = v2_request()
    for f in request['native']['frames']:
      f['active'] = False
      f['steering_pressed'] = True
    result = run_native_transcript(request,timeout_s=10.)
    self.assertEqual(result['status'], 'COMPLETED')
    self.assertTrue(all(r['requested_normalized_torque']==0. for r in result['controller_transcript']))
    self.assertEqual(result['controller_spec'], request['controller'])

  def test_response_config_and_effective_readback_tamper_rejected(self):
    request = v2_request()
    result = run_native_transcript(request,timeout_s=10.)
    self.assertEqual(result['status'], 'COMPLETED')
    for key in ('controller_spec','controller_config_sha256','effective_parameters','effective_parameters_sha256'):
      changed = copy.deepcopy(result)
      changed[key] = {}
      with self.subTest(key=key), self.assertRaises(ValueError):
        validate_response(request,changed)

  def test_response_canonical_binding_rejects_boolean_and_integer_aliases(self):
    request = v2_request()
    result = run_native_transcript(request,timeout_s=10.)
    self.assertEqual(result['status'],'COMPLETED')
    for field in ('controller_spec','effective_parameters'):
      for value in (False,0):
        changed = copy.deepcopy(result)
        if field == 'controller_spec':
          changed[field]['config']['points'][0][0] = value
        else:
          changed[field][0][1] = value
        with self.subTest(field=field,value=value),self.assertRaises(ValueError):
          validate_response(request,changed)


if __name__ == '__main__':
  unittest.main()
