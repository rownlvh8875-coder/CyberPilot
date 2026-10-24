import base64
import copy
import hashlib
import unittest

from openpilot.tools.cyber_autotune.native_long_protocol import decode_request, encode_request


SOURCE_FILES = (
  'openpilot/selfdrive/controls/controlsd.py',
  'openpilot/selfdrive/controls/lib/longcontrol.py',
  'openpilot/selfdrive/controls/lib/drive_helpers.py',
  'openpilot/selfdrive/modeld/constants.py',
  'openpilot/common/pid.py', 'openpilot/common/realtime.py', 'openpilot/common/constants.py',
  'openpilot/cereal/__init__.py', 'openpilot/cereal/log.capnp', 'openpilot/cereal/custom.capnp',
  'opendbc_repo/opendbc/car/__init__.py', 'opendbc_repo/opendbc/car/structs.py',
  'opendbc_repo/opendbc/car/car.capnp', 'opendbc_repo/opendbc/car/interfaces.py',
  'opendbc_repo/opendbc/car/hyundai/interface.py',
)


def protocol_fixture():
  # Only the byte envelope is validated here. This is NOT valid native CP.
  raw = b'synthetic opaque cp for protocol tests'
  frame = {'time_ns': 0, 'enabled': True, 'override_longitudinal': False, 'brake_pressed': False,
           'cruise_standstill': False, 'should_stop': False, 'speed_mps': 20., 'accel_mps2': 0.,
           'cruise_speed_kph': 72., 'a_target_mps2': .2}
  return {'version': 1, 'kind': 'longcontrol', 'source': {'root': '/tmp/synthetic-source', 'head': 'a' * 40,
          'opendbc_head': 'b' * 40, 'files': dict.fromkeys(SOURCE_FILES, 'c' * 64)},
          'car_params_base64': base64.b64encode(raw).decode(), 'car_params_sha256': hashlib.sha256(raw).hexdigest(),
          'fingerprint': 'HYUNDAI_SANTA_FE_2022', 'openpilot_longitudinal_control': True,
          'frames': [dict(frame, time_ns=i * 10_000_000) for i in range(2)]}


class TestNativeLongProtocol(unittest.TestCase):
  def test_roundtrip_preserves_typed_fields_without_mutation(self):
    request = protocol_fixture()
    before = copy.deepcopy(request)
    self.assertEqual(decode_request(encode_request(request)), before)
    self.assertEqual(request, before)
    request['openpilot_longitudinal_control'] = False
    self.assertFalse(decode_request(encode_request(request))['openpilot_longitudinal_control'])

  def test_mode_identity_and_unknown_overrides_are_rejected(self):
    for key, value in (('version', True), ('kind', 'torque'), ('fingerprint', 'OTHER'),
                       ('openpilot_longitudinal_control', 1), ('accel_limits', [-10, 10]),
                       ('active', True), ('delay_s', .1)):
      with self.subTest(key=key), self.assertRaises(ValueError):
        encode_request(dict(protocol_fixture(), **{key: value}))
    for key, value in (('head', 'A' * 40), ('opendbc_head', 'z' * 40), ('root', '../relative'), ('files', {})):
      request = protocol_fixture()
      request['source'][key] = value
      with self.subTest(source=key), self.assertRaises(ValueError):
        encode_request(request)
    for name in SOURCE_FILES:
      request = protocol_fixture()
      del request['source']['files'][name]
      with self.subTest(missing=name), self.assertRaises(ValueError):
        encode_request(request)

  def test_frame_domain_precision_time_and_count_are_strict(self):
    for key, value in (('enabled', 1), ('should_stop', 'false'), ('speed_mps', -1),
                       ('cruise_speed_kph', -1), ('accel_mps2', True), ('a_target_mps2', float('inf')),
                       ('a_target_mps2', float('nan')), ('a_target_mps2', 10 ** 400),
                       ('time_ns', True), ('time_ns', 0), ('time_ns', 10_000_001), ('time_ns', 2 ** 63),
                       ('accel_limits', [-3.5, 2.0]), ('active', True)):
      request = protocol_fixture()
      request['frames'][1][key] = value
      with self.subTest(key=key, value=value), self.assertRaises(ValueError):
        encode_request(request)
    request = protocol_fixture()
    for frames in ([], request['frames'][:1], request['frames'] * 5001, tuple(request['frames'])):
      with self.assertRaises(ValueError):
        encode_request(dict(request, frames=frames))

  def test_cp_bytes_and_digest_must_be_canonical_and_bounded(self):
    request = protocol_fixture()
    for fields in ({'car_params_base64': '!'}, {'car_params_base64': request['car_params_base64'] + '\n'},
                   {'car_params_base64': ''}, {'car_params_sha256': '0' * 64},
                   {'car_params_base64': base64.b64encode(b'x' * (1024 * 1024 + 1)).decode()}):
      with self.subTest(fields=list(fields)), self.assertRaises(ValueError):
        encode_request(dict(request, **fields))

  def test_untrusted_json_rejects_duplicate_nonfinite_mutable_and_oversize(self):
    raw = encode_request(protocol_fixture())
    for payload in (b'', bytearray(raw), b' ' * (4 * 1024 * 1024 + 1), b'\xff',
                    raw.replace(b'"version":1', b'"version":1,"version":1'),
                    raw.replace(b'"a_target_mps2":0.2', b'"a_target_mps2":NaN'),
                    b'[]', b'null'):
      with self.subTest(payload_type=type(payload)), self.assertRaises(ValueError):
        decode_request(payload)


if __name__ == '__main__':
  unittest.main()
