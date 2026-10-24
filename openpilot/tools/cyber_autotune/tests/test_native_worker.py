import base64
import copy
import hashlib
from pathlib import Path
import subprocess
import unittest

from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR

from openpilot.tools.cyber_autotune.native_protocol import decode_request, encode_request
from openpilot.tools.cyber_autotune.native_worker import execute_request


ROOT = Path(__file__).resolve().parents[4]
SOURCE_FILES = (
  'openpilot/selfdrive/controls/lib/latcontrol_torque.py',
  'openpilot/selfdrive/controls/lib/latcontrol.py',
  'openpilot/common/pid.py', 'openpilot/common/filter_simple.py',
  'opendbc_repo/opendbc/car/interfaces.py', 'opendbc_repo/opendbc/car/vehicle_model.py',
  'opendbc_repo/opendbc/car/hyundai/interface.py', 'opendbc_repo/opendbc/car/lateral.py',
  'opendbc_repo/opendbc/car/car.capnp',
)


def fixture():
  cp = CarInterface.get_non_essential_params(CAR.HYUNDAI_SANTA_FE_2022)
  raw = cp.to_bytes()
  frame = {'time_ns': 0, 'active': True, 'safety_limited': False, 'curvature_limited': False,
           'steering_pressed': False, 'speed_mps': 20., 'accel_mps2': 0., 'angle_deg': 0.,
           'rate_deg_s': 0., 'driver_torque': 0., 'roll_rad': 0., 'angle_offset_deg': 0.,
           'stiffness_factor': 1., 'steer_ratio': 16., 'desired_curvature_1pm': 0., 'lateral_delay_s': .15}
  return {'version': 1, 'source': {
    'root': str(ROOT), 'head': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
    'opendbc_head': subprocess.check_output(['git', '-C', str(ROOT / 'opendbc_repo'), 'rev-parse', 'HEAD'], text=True).strip(),
    'files': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}},
    'car_params_base64': base64.b64encode(raw).decode(), 'car_params_sha256': hashlib.sha256(raw).hexdigest(),
    'fingerprint': 'HYUNDAI_SANTA_FE_2022', 'frames': [dict(frame, time_ns=i * 10_000_000) for i in range(20)]}


class TestNativeProtocol(unittest.TestCase):
  def setUp(self):
    self.request = fixture()

  def test_roundtrip_preserves_inputs(self):
    self.assertEqual(decode_request(encode_request(self.request)), self.request)

  def test_unknown_missing_duplicate_and_nonfinite_json_rejected(self):
    for change in ({'unknown': 1}, {'version': True}, {'fingerprint': 'MAZDA'}):
      with self.subTest(change=change), self.assertRaises(ValueError):
        encode_request(dict(self.request, **change))
    for payload in (b'{"version":1,"version":1}', b'{"v":NaN}', b'[]', b'{}', b'\xff'):
      with self.subTest(payload=payload), self.assertRaises(ValueError):
        decode_request(payload)

  def test_invalid_frame_types_units_and_time_rejected(self):
    for field, value in (('speed_mps', True), ('speed_mps', -1), ('angle_deg', float('inf')),
                         ('angle_deg', 10 ** 400), ('active', 1), ('stiffness_factor', 0),
                         ('steer_ratio', -1), ('lateral_delay_s', -1), ('time_ns', True),
                         ('time_ns', -1), ('time_ns', 2 ** 63), ('time_ns', 1)):
      request = copy.deepcopy(self.request)
      request['frames'][1][field] = value
      with self.subTest(field=field, value=value), self.assertRaises(ValueError):
        encode_request(request)

  def test_size_and_cp_integrity_rejected(self):
    for frames in ([], self.request['frames'][:1], self.request['frames'] * 501):
      with self.assertRaises(ValueError):
        encode_request(dict(self.request, frames=frames))
    for change in ({'car_params_base64': '!'}, {'car_params_sha256': '0' * 64},
                   {'car_params_base64': base64.b64encode(b'x' * (1024 * 1024 + 1)).decode()}):
      with self.assertRaises(ValueError):
        encode_request(dict(self.request, **change))
    with self.assertRaises(ValueError):
      decode_request(b' ' * (4 * 1024 * 1024 + 1))

  def test_source_contract_must_be_complete_and_canonical(self):
    for key, value in (('head', 'x' * 40), ('opendbc_head', '0'), ('root', '../relative'), ('files', {})):
      with self.subTest(key=key), self.assertRaises(ValueError):
        encode_request(dict(self.request, source=dict(self.request['source'], **{key: value})))
    request = copy.deepcopy(self.request)
    request['source']['files']['../../escape'] = '0' * 64
    with self.assertRaises(ValueError):
      encode_request(request)


class TestNativeWorker(unittest.TestCase):
  def test_zero_and_nonzero_native_output_and_repeatability(self):
    request = fixture()
    saved = copy.deepcopy(request)
    result = execute_request(request)
    self.assertEqual(result['status'], 'COMPLETED')
    self.assertEqual(len(result['samples']), 20)
    self.assertTrue(all(row['requested_torque'] == 0. for row in result['samples']))
    self.assertEqual(request, saved)
    for frame in request['frames']:
      frame['desired_curvature_1pm'] = .001
    first = execute_request(request)
    second = execute_request(request)
    self.assertEqual(first, second)
    self.assertTrue(any(row['requested_torque'] < 0 for row in first['samples']))
    self.assertTrue(all(-1 <= row['requested_torque'] <= 1 for row in first['samples']))
    self.assertFalse(first['runtime_accepted'])
    self.assertFalse(first['promotable'])
    self.assertEqual(first['request_sha256'], hashlib.sha256(encode_request(request)).hexdigest())

  def test_wrong_source_revision_and_hash_rejected(self):
    for key in ('head', 'opendbc_head'):
      request = fixture()
      request['source'][key] = '0' * 40
      with self.assertRaises(ValueError):
        execute_request(request)
    request = fixture()
    request['source']['files'][SOURCE_FILES[0]] = '0' * 64
    with self.assertRaises(ValueError):
      execute_request(request)
    request = fixture()
    request['source']['root'] = '/does-not-exist-cyber-test'
    with self.assertRaises(ValueError):
      execute_request(request)

  def test_cp_mismatch_and_bad_torque_params_rejected(self):
    for fault in ('fingerprint', 'pid', 'factor', 'friction'):
      request = fixture()
      cp = CarInterface.get_non_essential_params(CAR.HYUNDAI_SANTA_FE_2022)
      if fault == 'fingerprint':
        cp.carFingerprint = 'wrong vehicle'
      elif fault == 'pid':
        cp.lateralTuning.init('pid')
      elif fault == 'factor':
        cp.lateralTuning.torque.latAccelFactor = 0.
      else:
        cp.lateralTuning.torque.friction = float('nan')
      raw = cp.to_bytes()
      request['car_params_base64'] = base64.b64encode(raw).decode()
      request['car_params_sha256'] = hashlib.sha256(raw).hexdigest()
      with self.subTest(fault=fault), self.assertRaises(ValueError):
        execute_request(request)

  def test_inactive_output_never_reuses_active_torque(self):
    request = fixture()
    for i, frame in enumerate(request['frames']):
      frame['desired_curvature_1pm'] = .002
      frame['active'] = i < 10
    result = execute_request(request)
    self.assertTrue(any(row['requested_torque'] != 0 for row in result['samples'][:10]))
    self.assertTrue(all(row['requested_torque'] == 0 for row in result['samples'][10:]))

  def test_cp_corrupt_bytes_rejected_without_default(self):
    request = fixture()
    raw = b'not a capnp car params'
    request['car_params_base64'] = base64.b64encode(raw).decode()
    request['car_params_sha256'] = hashlib.sha256(raw).hexdigest()
    with self.assertRaises(ValueError):
      execute_request(request)

  def test_invalid_cp_physics_never_completes(self):
    for field, value in (('mass', -1), ('wheelbase', -2), ('centerToFront', -1),
                         ('centerToFront', 10), ('tireStiffnessFront', -1), ('tireStiffnessRear', 0),
                         ('rotationalInertia', float('nan')), ('steerRatio', float('nan')),
                         ('steerRatioRear', float('inf')), ('steerLimitTimer', -1)):
      request = fixture()
      cp = CarInterface.get_non_essential_params(CAR.HYUNDAI_SANTA_FE_2022)
      setattr(cp, field, value)
      raw = cp.to_bytes()
      request['car_params_base64'] = base64.b64encode(raw).decode()
      request['car_params_sha256'] = hashlib.sha256(raw).hexdigest()
      with self.subTest(field=field), self.assertRaises(ValueError):
        execute_request(request)

  def test_overflow_cannot_hide_behind_inactive_or_clipped_output(self):
    for active in (False, True):
      for field, value in (('speed_mps', 1e100), ('accel_mps2', 1e100),
                           ('desired_curvature_1pm', 1e308), ('lateral_delay_s', 1e308),
                           ('stiffness_factor', 1e308), ('roll_rad', 1e308)):
        request = fixture()
        for frame in request['frames']:
          frame['active'] = active
          frame[field] = value
        with self.subTest(field=field, active=active), self.assertRaises(ValueError):
          execute_request(request)


if __name__ == '__main__':
  unittest.main()
