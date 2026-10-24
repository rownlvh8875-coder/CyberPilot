import base64
import copy
import hashlib
from pathlib import Path
import subprocess
import unittest

from opendbc.car import structs
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR
from openpilot.cereal import log
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.tools.cyber_autotune.native_long_runner import run_native
from openpilot.tools.cyber_autotune.tests.test_native_long_protocol import SOURCE_FILES, protocol_fixture


ROOT = Path(__file__).resolve().parents[4]


def fixture():
  request = protocol_fixture()
  cp = CarInterface.get_non_essential_params(CAR.HYUNDAI_SANTA_FE_2022)
  cp.openpilotLongitudinalControl = True  # synthetic CP only, never a vehicle setting
  cp.stopAccel = -2.
  cp.longitudinalTuning.kiBP = [0.]
  cp.longitudinalTuning.kiV = [0.]
  bind_cp(request, cp.to_bytes())
  request['source'] = {'root': str(ROOT),
                       'head': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
                       'opendbc_head': subprocess.check_output(['git', '-C', str(ROOT / 'opendbc_repo'), 'rev-parse', 'HEAD'],
                                                               text=True).strip(),
                       'files': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}}
  initial = dict(request['frames'][0], a_target_mps2=1.)
  request['frames'] = [dict(initial, time_ns=i * 10_000_000) for i in range(11)]
  request['frames'][0]['enabled'] = request['frames'][10]['enabled'] = False
  request['frames'][2]['should_stop'] = request['frames'][3]['should_stop'] = True
  request['frames'][4]['cruise_standstill'] = True
  request['frames'][5]['brake_pressed'] = True
  request['frames'][7]['override_longitudinal'] = True
  request['frames'][8]['a_target_mps2'] = 100.
  request['frames'][9]['a_target_mps2'] = -100.
  return request


def bind_cp(request, raw):
  request['car_params_base64'] = base64.b64encode(raw).decode()
  request['car_params_sha256'] = hashlib.sha256(raw).hexdigest()


class TestNativeLongWorker(unittest.TestCase):
  def test_stock_states_requests_clipping_and_repeatability(self):
    request = fixture()
    before = copy.deepcopy(request)
    first, second = (run_native(request, timeout_s=10) for _ in range(2))
    self.assertEqual(first['status'], 'COMPLETED')
    self.assertEqual(first, second)
    self.assertEqual(request, before)
    rows = first['samples']
    for row, expected in zip(rows, (0., 1., -.01, -.02, -.03, -.04, 1., 0., 2., -3.5, 0.), strict=True):
      self.assertAlmostEqual(row['requested_accel_mps2'], expected, places=12)
    self.assertEqual(tuple(r['state_after'] for r in rows),
                     ('off', 'pid', 'stopping', 'stopping', 'stopping', 'stopping', 'pid', 'off', 'pid', 'pid', 'off'))
    self.assertEqual(tuple(r['state_before'] for r in rows), ('off', *(r['state_after'] for r in rows[:-1])))
    self.assertFalse(first['runtime_accepted'])
    self.assertFalse(first['promotable'])

  def test_wire_normalized_native_pid_matches_direct_reference(self):
    request = fixture()
    with structs.CarParams.from_bytes(base64.b64decode(request['car_params_base64'])) as reader:
      cp = reader.as_builder()
    cp.longitudinalTuning.kiBP = [0., 30.]
    cp.longitudinalTuning.kiV = [.1, .2]
    bind_cp(request, cp.to_bytes())
    request['frames'] = [dict(request['frames'][1], time_ns=i * 10_000_000,
                              a_target_mps2=.123456789, accel_mps2=.023456789) for i in range(20)]
    result = run_native(request, timeout_s=10)
    self.assertEqual(result['status'], 'COMPLETED')
    controller = LongControl(cp)
    expected = []
    for frame in request['frames']:
      state = structs.CarState(vEgo=frame['speed_mps'], aEgo=frame['accel_mps2'])
      plan = log.LongitudinalPlan.new_message(aTarget=frame['a_target_mps2'], shouldStop=False)
      expected.append(float(controller.update(True, state, plan.aTarget, plan.shouldStop, (-3.5, 2.0))))
    self.assertEqual([r['requested_accel_mps2'] for r in result['samples']], expected)
    self.assertGreater(expected[-1], expected[0])

  def test_cp_longitudinal_owner_false_keeps_every_command_off(self):
    request = fixture()
    with structs.CarParams.from_bytes(base64.b64decode(request['car_params_base64'])) as reader:
      cp = reader.as_builder()
    cp.openpilotLongitudinalControl = False
    bind_cp(request, cp.to_bytes())
    request['openpilot_longitudinal_control'] = False
    result = run_native(request, timeout_s=10)
    self.assertEqual(result['status'], 'COMPLETED')
    self.assertTrue(all(not r['long_active'] and r['requested_accel_mps2'] == 0. and r['state_after'] == 'off'
                        for r in result['samples']))

  def test_cp_identity_mode_and_invalid_tuning_are_rejected(self):
    changes = (
      lambda cp: setattr(cp, 'openpilotLongitudinalControl', False),
      lambda cp: setattr(cp, 'carFingerprint', 'OTHER'),
      lambda cp: setattr(cp, 'stopAccel', -4.),
      lambda cp: setattr(cp, 'stopAccel', float('nan')),
      lambda cp: setattr(cp.longitudinalTuning, 'kiV', [-1.]),
      lambda cp: setattr(cp.longitudinalTuning, 'kiV', [float('inf')]),
      lambda cp: setattr(cp.longitudinalTuning, 'kiBP', []),
      lambda cp: setattr(cp.longitudinalTuning, 'kiBP', [1., 0.]),
    )
    for change in changes:
      request = fixture()
      with structs.CarParams.from_bytes(base64.b64decode(request['car_params_base64'])) as reader:
        cp = reader.as_builder()
      change(cp)
      bind_cp(request, cp.to_bytes())
      with self.subTest(change=changes.index(change)):
        self.assertEqual(run_native(request, timeout_s=10)['status'], 'WORKER_FAILED')

  def test_wire_overflow_and_source_drift_fail_without_successful_samples(self):
    for field in ('speed_mps', 'accel_mps2', 'cruise_speed_kph', 'a_target_mps2'):
      request = fixture()
      request['frames'][1][field] = 1e39
      with self.subTest(field=field):
        result = run_native(request, timeout_s=10)
        self.assertEqual(result['status'], 'WORKER_FAILED')
        self.assertNotIn('samples', result)
    request = fixture()
    request['source']['files'][SOURCE_FILES[1]] = '0' * 64
    self.assertEqual(run_native(request, timeout_s=10)['status'], 'WORKER_FAILED')


if __name__ == '__main__':
  unittest.main()
