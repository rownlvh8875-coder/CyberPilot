"""Fresh-process native requested-acceleration diagnostic. No actuator transport.

Run only through the isolated supervisor, never import into a control process.
Source/CP are trusted-local inputs, not authenticated evidence or a security sandbox.
"""
import base64
import contextlib
import inspect
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_long_protocol import EXPECTED_ACCEL_LIMITS, decode_request, encode_request
from native_protocol import MAX_REQUEST_BYTES, canonical, digest, finite
from native_worker import _verify_source
from source_imports import source_only_imports


def execute_request(request):
  with source_only_imports():
    return _execute_request(request)


def _execute_request(request):
  payload = encode_request(request)
  request = decode_request(payload)
  root = _verify_source(request['source'])
  sys.path[:0] = [str(root), str(root / 'opendbc_repo')]
  try:
    import numpy as np
    from opendbc.car import structs
    from opendbc.car.hyundai.interface import CarInterface
    from opendbc.car.interfaces import CarInterfaceBase
    import openpilot.cereal as cereal
    from openpilot.common import realtime
    from openpilot.common.constants import CV
    from openpilot.common.pid import PIDController
    from openpilot.selfdrive.controls.lib.longcontrol import LongControl

    for symbol in (structs, CarInterface, CarInterfaceBase, cereal, realtime, CV, PIDController, LongControl):
      if not Path(inspect.getfile(symbol)).resolve(strict=True).is_relative_to(root):
        raise ValueError('IMPORT_ROOT_MISMATCH')
    if realtime.DT_CTRL != .01:
      raise ValueError('TIMESTEP_MISMATCH')
    native_states = structs.CarControl.Actuators.LongControlState
    state_names = {getattr(native_states, name): name for name in ('off', 'stopping', 'pid')}
    samples = []
    with structs.CarParams.from_bytes(base64.b64decode(request['car_params_base64'])) as cp:
      if (cp.carFingerprint != request['fingerprint'] or
          cp.openpilotLongitudinalControl != request['openpilot_longitudinal_control']):
        raise ValueError('CP_IDENTITY_MISMATCH')
      bp, values = tuple(cp.longitudinalTuning.kiBP), tuple(cp.longitudinalTuning.kiV)
      if (not finite(cp.stopAccel) or not EXPECTED_ACCEL_LIMITS[0] <= cp.stopAccel <= 0 or
          not bp or len(bp) != len(values) or any(not finite(v) or v < 0 for v in (*bp, *values)) or
          any(left >= right for left, right in zip(bp, bp[1:], strict=False))):
        raise ValueError('CP_TUNING_INVALID')
      controller = LongControl(cp)
      for frame in request['frames']:
        state = structs.CarState(vEgo=frame['speed_mps'], aEgo=frame['accel_mps2'], vCruise=frame['cruise_speed_kph'],
                                 brakePressed=frame['brake_pressed'])
        state.cruiseState.standstill = frame['cruise_standstill']
        plan = cereal.log.LongitudinalPlan.new_message(aTarget=frame['a_target_mps2'], shouldStop=frame['should_stop'])
        # Native Float32 message assignment must not turn valid JSON into Inf.
        if not all(finite(v) for v in (state.vEgo, state.aEgo, state.vCruise, plan.aTarget)):
          raise ValueError('NATIVE_FIELD_OVERFLOW')
        active = frame['enabled'] and not frame['override_longitudinal'] and cp.openpilotLongitudinalControl
        state_before = state_names[controller.long_control_state]
        if not active:
          controller.reset()  # same additional inactive reset as controlsd
        limits = CarInterface.get_pid_accel_limits(cp, state.vEgo, state.vCruise * CV.KPH_TO_MS)
        if tuple(limits) != EXPECTED_ACCEL_LIMITS:
          raise ValueError('UNSUPPORTED_NATIVE_LIMITS')
        error = plan.aTarget - state.aEgo
        if not finite(error):
          raise ValueError('NATIVE_DERIVED_OVERFLOW')
        # Native PID interpolation returns NumPy scalars. Raise on intermediate
        # overflow before np.clip could hide invalid arithmetic in a finite cap.
        with np.errstate(over='raise', invalid='raise', divide='raise'):
          output = float(controller.update(active, state, plan.aTarget, plan.shouldStop, limits))
        internal = (controller.last_output_accel,
                    *(getattr(controller.pid, key) for key in ('p', 'i', 'd', 'f', 'control', 'pos_limit', 'neg_limit')))
        if not all(finite(float(v)) for v in internal) or not finite(output) or not limits[0] <= output <= limits[1]:
          raise ValueError('INVALID_NATIVE_OUTPUT')
        samples.append({'time_ns': frame['time_ns'], 'requested_accel_mps2': output, 'long_active': bool(active),
                        'state_before': state_before, 'state_after': state_names[controller.long_control_state]})
    _verify_source(request['source'])
    return {'status': 'COMPLETED', 'scope': 'OFFLINE_NATIVE_REQUESTED_ACCEL', 'request_sha256': digest(payload),
            'source_head': request['source']['head'], 'opendbc_head': request['source']['opendbc_head'],
            'car_params_sha256': request['car_params_sha256'], 'samples': samples,
            'ordered_trace_sha256': digest(canonical(samples)), 'runtime_accepted': False, 'promotable': False}
  finally:
    del sys.path[:2]


def main():
  try:
    request = decode_request(sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1))
    with open(os.devnull, 'w') as quiet, contextlib.redirect_stdout(quiet):
      result = execute_request(request)
    sys.stdout.buffer.write(canonical(result) + b'\n')
    return 0
  except Exception:
    sys.stdout.buffer.write(canonical({'status': 'REJECTED', 'code': 'INVALID_OR_FAILED_NATIVE_LONG_REQUEST'}) + b'\n')
    return 1


if __name__ == '__main__':
  raise SystemExit(main())
