"""Standalone OFFLINE requested-torque worker, never an actuator or active loop.

Trusted local sources only: process separation is not a hostile-code sandbox.
CP owns fixed parameters; no Params, live learning, plant or vehicle-controller IO.
"""
import base64
import contextlib
import inspect
import math
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

# -I intentionally removes script-directory imports. Add only this fixed trusted
# stdlib protocol directory; never preload an openpilot package before source bind.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_protocol import MAX_REQUEST_BYTES, canonical, decode_request, digest, encode_request, finite
from source_imports import source_only_imports


def _verify_source(source):
  try:
    root = Path(source['root']).resolve(strict=True)
    if not root.is_dir():
      raise ValueError('INVALID_SOURCE_ROOT')
    for directory, revision in ((root, source['head']), (root / 'opendbc_repo', source['opendbc_head'])):
      actual = subprocess.check_output(['git', '-C', str(directory), 'rev-parse', 'HEAD'],
                                       text=True, stderr=subprocess.DEVNULL, timeout=5).strip()
      if actual != revision:
        raise ValueError('SOURCE_REVISION_MISMATCH')
    for name, expected in source['files'].items():
      path = (root / name).resolve(strict=True)
      if not path.is_relative_to(root) or digest(path.read_bytes()) != expected:
        raise ValueError('SOURCE_FILE_MISMATCH')
    return root
  except (OSError, subprocess.SubprocessError) as exc:
    raise ValueError('SOURCE_UNAVAILABLE') from exc


def execute_request(request: dict) -> dict:
  with source_only_imports():
    return _execute_request(request)


def _execute_request(request: dict) -> dict:
  payload = encode_request(request)
  request = decode_request(payload)  # immutable boundary copy, never mutate caller state
  root = _verify_source(request['source'])
  # The parent interpreter's editable opendbc install may point at a different
  # checkout. Select this pinned dependency explicitly before its first import.
  sys.path[:0] = [str(root), str(root / 'opendbc_repo')]
  try:
    import numpy as np
    from opendbc.car import DT_CTRL, structs
    from opendbc.car.interfaces import CarInterfaceBase
    from opendbc.car.vehicle_model import VehicleModel
    from openpilot.common.filter_simple import FirstOrderFilter
    from openpilot.common.constants import ACCELERATION_DUE_TO_GRAVITY
    from openpilot.common.pid import PIDController
    from openpilot.selfdrive.controls.lib.latcontrol import LatControl
    from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque

    for symbol in (structs, CarInterfaceBase, VehicleModel, FirstOrderFilter, PIDController, LatControl, LatControlTorque):
      if not Path(inspect.getfile(symbol)).resolve(strict=True).is_relative_to(root):
        raise ValueError('IMPORT_ROOT_MISMATCH')
    if DT_CTRL != .01:
      raise ValueError('TIMESTEP_MISMATCH')

    class LinearConversion:
      torque_from_lateral_accel_linear = CarInterfaceBase.torque_from_lateral_accel_linear
      torque_from_lateral_accel = CarInterfaceBase.torque_from_lateral_accel
      lateral_accel_from_torque_linear = CarInterfaceBase.lateral_accel_from_torque_linear
      lateral_accel_from_torque = CarInterfaceBase.lateral_accel_from_torque

    samples = []
    with structs.CarParams.from_bytes(base64.b64decode(request['car_params_base64'])) as cp:
      if (cp.carFingerprint != request['fingerprint'] or cp.lateralTuning.which() != 'torque' or
          str(cp.steerControlType) != 'torque'):
        raise ValueError('CP_CONTROLLER_MISMATCH')
      positive_fields = ('mass', 'wheelbase', 'centerToFront', 'rotationalInertia',
                         'tireStiffnessFront', 'tireStiffnessRear', 'steerRatio', 'steerLimitTimer')
      if (any(not finite(getattr(cp, name)) or getattr(cp, name) <= 0 for name in positive_fields) or
          not cp.centerToFront < cp.wheelbase or not finite(cp.steerRatioRear)):
        raise ValueError('CP_PHYSICS_INVALID')
      tuning = cp.lateralTuning.torque
      if (not all(finite(value) for value in (tuning.latAccelFactor, tuning.latAccelOffset, tuning.friction,
                                             tuning.steeringAngleDeadzoneDeg)) or
          tuning.latAccelFactor <= 0 or tuning.friction < 0 or tuning.steeringAngleDeadzoneDeg < 0):
        raise ValueError('CP_TUNING_INVALID')
      controller = LatControlTorque(cp, LinearConversion(), DT_CTRL)
      vm = VehicleModel(cp)
      for frame in request['frames']:
        state = structs.CarState()
        state.vEgo = state.vEgoRaw = frame['speed_mps']
        state.aEgo = frame['accel_mps2']
        state.steeringAngleDeg = frame['angle_deg']
        state.steeringRateDeg = frame['rate_deg_s']
        state.steeringTorque = frame['driver_torque']
        state.steeringPressed = frame['steering_pressed']
        # Float32 wire assignment can turn finite JSON numbers into infinity.
        if not all(finite(value) for value in (state.vEgo, state.vEgoRaw, state.aEgo, state.steeringAngleDeg,
                                               state.steeringRateDeg, state.steeringTorque)):
          raise ValueError('NATIVE_FIELD_OVERFLOW')
        params = SimpleNamespace(roll=frame['roll_rad'], angleOffsetDeg=frame['angle_offset_deg'])
        vm.update_params(frame['stiffness_factor'], frame['steer_ratio'])
        if not all(finite(value) and value > 0 for value in (vm.cF, vm.cR, vm.sR)):
          raise ValueError('NATIVE_MODEL_OVERFLOW')
        with np.errstate(over='raise', invalid='raise', divide='raise'):
          curvature = -vm.calc_curvature(math.radians(state.steeringAngleDeg - params.angleOffsetDeg), state.vEgo, params.roll)
          desired_accel = frame['desired_curvature_1pm'] * state.vEgo ** 2
          measured_accel = curvature * state.vEgo ** 2
          gravity_roll = params.roll * ACCELERATION_DUE_TO_GRAVITY
          derived = (curvature, desired_accel, measured_accel, gravity_roll,
                     desired_accel - gravity_roll - tuning.latAccelOffset, frame['lateral_delay_s'] / DT_CTRL + 1,
                     *(value - measured_accel for value in (*controller.lat_accel_request_buffer, desired_accel)))
          if not all(finite(value) for value in derived):
            raise ValueError('NATIVE_DERIVED_OVERFLOW')
          torque, _, pid_log = controller.update(frame['active'], state, vm, params, frame['safety_limited'],
                                                 frame['desired_curvature_1pm'], frame['curvature_limited'], frame['lateral_delay_s'])
        native_state = (*controller.lat_accel_request_buffer, controller.jerk_filter.x, controller.sat_time,
                        *(getattr(controller.pid, name) for name in ('p', 'i', 'd', 'f', 'control', 'pos_limit', 'neg_limit')))
        if (not all(finite(float(value)) for value in native_state) or
            any(type(value) is not bool and not finite(value) for value in pid_log.to_dict().values())):
          raise ValueError('NATIVE_STATE_OVERFLOW')
        # Native PID arithmetic returns numpy.float64; normalize at this trusted
        # producer boundary, not in the strict external request validator.
        torque = float(torque)
        if not finite(torque) or abs(torque) > 1 or not finite(curvature):
          raise ValueError('INVALID_NATIVE_OUTPUT')
        samples.append({'time_ns': frame['time_ns'], 'requested_torque': float(torque), 'estimated_curvature_1pm': float(curvature)})
    _verify_source(request['source'])  # ordinary concurrent selected-file edits invalidate the run
    return {'status': 'COMPLETED', 'scope': 'OFFLINE_NATIVE_REQUESTED_TORQUE', 'request_sha256': digest(payload),
            'source_head': request['source']['head'], 'opendbc_head': request['source']['opendbc_head'],
            'car_params_sha256': request['car_params_sha256'], 'samples': samples,
            'ordered_trace_sha256': digest(canonical(samples)), 'runtime_accepted': False, 'promotable': False}
  except Exception as exc:
    raise ValueError('NATIVE_EXECUTION_REJECTED') from exc
  finally:
    del sys.path[:2]


def main():
  try:
    from worker_resources import apply_worker_limits
    apply_worker_limits()
    payload = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    request = decode_request(payload)
    with open(os.devnull, 'w') as quiet, contextlib.redirect_stdout(quiet):
      result = execute_request(request)
    sys.stdout.buffer.write(canonical(result) + b'\n')
    return 0
  except Exception:
    # Do not reflect input paths, CP contents, source exceptions or stack traces.
    sys.stdout.buffer.write(canonical({'status': 'REJECTED', 'code': 'INVALID_OR_FAILED_NATIVE_REQUEST'}) + b'\n')
    return 1


if __name__ == '__main__':
  raise SystemExit(main())
