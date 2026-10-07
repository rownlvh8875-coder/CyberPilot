"""Isolated native LatControlTorque producer for curvature/yaw transcripts.

The child process executes only the native lateral controller and descriptive
offline plant. It has no CAN, Params, car-controller, device, profile, network,
or runtime activation path. Process isolation is a fault-containment boundary,
not a hostile-code sandbox or vehicle qualification.
"""
import base64
import contextlib
from dataclasses import asdict
import hashlib
import inspect
import math
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from curvature_yaw_native_protocol import (
  MAX_REQUEST_BYTES,
  SUPPORT_FILES,
  controller_identity_sha256,
  decode_request,
  encode_request,
)
from native_protocol import canonical, digest, finite
from native_worker import _verify_source
from source_imports import source_only_imports


def _verify_support_files(root: Path, expected: dict) -> None:
  if set(expected) != set(SUPPORT_FILES):
    raise ValueError('SUPPORT_FILE_SET_MISMATCH')
  for name in SUPPORT_FILES:
    path = (root / name).resolve(strict=True)
    if not path.is_relative_to(root):
      raise ValueError('SUPPORT_FILE_ESCAPE')
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected[name]:
      raise ValueError('SUPPORT_FILE_MISMATCH')


def execute_request(request: dict) -> dict:
  payload = encode_request(request)
  request = decode_request(payload)
  native = request['native']
  root = _verify_source(native['source'])
  _verify_support_files(root, request['support_files'])

  with source_only_imports():
    sys.path[:0] = [str(root), str(root / 'opendbc_repo')]
    try:
      import numpy as np
      from opendbc.car import DT_CTRL, structs
      from opendbc.car.interfaces import CarInterfaceBase
      from opendbc.car.vehicle_model import VehicleModel
      from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
      from openpilot.tools.cyber_autotune.curvature_yaw_closed_loop import (
        CurvatureYawClosedLoopState,
        CurvatureYawControllerFeedback,
        CurvatureYawControllerStep,
        closed_loop_state_sha256,
        controller_feedback_sha256,
        controller_transcript_sha256,
        plant_config_sha256,
      )
      from openpilot.tools.cyber_autotune.curvature_yaw_plant import (
        CurvatureYawPlantConfig,
        CurvatureYawPlantState,
        observe_curvature_yaw_step,
      )

      for symbol in (
        structs, CarInterfaceBase, VehicleModel, LatControlTorque,
        CurvatureYawClosedLoopState, CurvatureYawPlantConfig,
      ):
        if not Path(inspect.getfile(symbol)).resolve(strict=True).is_relative_to(root):
          raise ValueError('IMPORT_ROOT_MISMATCH')
      if DT_CTRL != 0.01:
        raise ValueError('TIMESTEP_MISMATCH')

      class LinearConversion:
        torque_from_lateral_accel_linear = CarInterfaceBase.torque_from_lateral_accel_linear
        torque_from_lateral_accel = CarInterfaceBase.torque_from_lateral_accel
        lateral_accel_from_torque_linear = CarInterfaceBase.lateral_accel_from_torque_linear
        lateral_accel_from_torque = CarInterfaceBase.lateral_accel_from_torque

      config = CurvatureYawPlantConfig(**request['plant_config'])
      initial = request['initial_state']
      state = CurvatureYawClosedLoopState(
        plant_state=CurvatureYawPlantState(
          curvature_1pm=initial['curvature_1pm'],
          yaw_rate_rad_s=initial['yaw_rate_rad_s'],
          command_history=tuple(initial['command_history']),
        ),
        heading_rad=initial['heading_rad'],
        pose_y_m=initial['pose_y_m'],
      )
      config_hash = plant_config_sha256(config)
      initial_hash = closed_loop_state_sha256(state)
      transcript = []
      metric_observations = []
      sign = float(request['controller_to_plant_sign'])

      with structs.CarParams.from_bytes(base64.b64decode(native['car_params_base64'])) as cp:
        if (
          cp.carFingerprint != native['fingerprint']
          or cp.lateralTuning.which() != 'torque'
          or str(cp.steerControlType) != 'torque'
        ):
          raise ValueError('CP_CONTROLLER_MISMATCH')
        positive_fields = (
          'mass', 'wheelbase', 'centerToFront', 'rotationalInertia',
          'tireStiffnessFront', 'tireStiffnessRear', 'steerRatio', 'steerLimitTimer',
        )
        if (
          any(not finite(getattr(cp, name)) or getattr(cp, name) <= 0 for name in positive_fields)
          or not cp.centerToFront < cp.wheelbase
          or not finite(cp.steerRatioRear)
        ):
          raise ValueError('CP_PHYSICS_INVALID')
        tuning = cp.lateralTuning.torque
        if (
          not all(finite(value) for value in (
            tuning.latAccelFactor, tuning.latAccelOffset,
            tuning.friction, tuning.steeringAngleDeadzoneDeg,
          ))
          or tuning.latAccelFactor <= 0
          or tuning.friction < 0
          or tuning.steeringAngleDeadzoneDeg < 0
        ):
          raise ValueError('CP_TUNING_INVALID')

        controller = LatControlTorque(cp, LinearConversion(), DT_CTRL)
        model = VehicleModel(cp)
        prior_angle = None

        for index, frame in enumerate(native['frames']):
          feedback = CurvatureYawControllerFeedback(
            step_index=index,
            time_s=frame['time_ns'] * 1e-9,
            curvature_1pm=float(state.plant_state.curvature_1pm),
            yaw_rate_rad_s=float(state.plant_state.yaw_rate_rad_s),
            lateral_accel_mps2=float(state.plant_state.yaw_rate_rad_s) * float(frame['speed_mps']),
            heading_rad=float(state.heading_rad),
            pose_y_m=float(state.pose_y_m),
          )
          feedback_hash = controller_feedback_sha256(feedback)

          car_state = structs.CarState()
          car_state.vEgo = car_state.vEgoRaw = frame['speed_mps']
          car_state.aEgo = frame['accel_mps2']
          car_state.steeringTorque = frame['driver_torque']
          car_state.steeringPressed = frame['steering_pressed']
          model.update_params(frame['stiffness_factor'], frame['steer_ratio'])
          if not all(finite(value) and value > 0 for value in (model.cF, model.cR, model.sR)):
            raise ValueError('NATIVE_MODEL_OVERFLOW')

          with np.errstate(over='raise', invalid='raise', divide='raise'):
            angle_no_offset_rad = model.get_steer_from_curvature(
              -float(state.plant_state.curvature_1pm),
              frame['speed_mps'],
              frame['roll_rad'],
            )
            angle_deg = math.degrees(angle_no_offset_rad) + frame['angle_offset_deg']
            car_state.steeringAngleDeg = angle_deg
            car_state.steeringRateDeg = 0.0 if prior_angle is None else (angle_deg - prior_angle) / DT_CTRL
            prior_angle = angle_deg
            reconstructed = -model.calc_curvature(
              math.radians(car_state.steeringAngleDeg - frame['angle_offset_deg']),
              car_state.vEgo,
              frame['roll_rad'],
            )
          if (
            not all(finite(value) for value in (
              car_state.vEgo, car_state.vEgoRaw, car_state.aEgo,
              car_state.steeringAngleDeg, car_state.steeringRateDeg,
              car_state.steeringTorque, reconstructed,
            ))
            or not math.isclose(
              reconstructed,
              float(state.plant_state.curvature_1pm),
              rel_tol=2e-6,
              abs_tol=2e-10,
            )
          ):
            raise ValueError('FEEDBACK_INVERSION_MISMATCH')

          params = type('ParamsView', (), {})()
          params.roll = frame['roll_rad']
          params.angleOffsetDeg = frame['angle_offset_deg']
          with np.errstate(over='raise', invalid='raise', divide='raise'):
            requested, _, pid_log = controller.update(
              frame['active'],
              car_state,
              model,
              params,
              frame['safety_limited'],
              frame['desired_curvature_1pm'],
              frame['curvature_limited'],
              frame['lateral_delay_s'],
            )
          requested = float(requested)
          with np.errstate(over='raise', invalid='raise', divide='raise'):
            desired_angle_deg = math.degrees(model.get_steer_from_curvature(
              -frame['desired_curvature_1pm'], frame['speed_mps'], frame['roll_rad'],
            )) + frame['angle_offset_deg']
          native_state = (
            *controller.lat_accel_request_buffer,
            controller.jerk_filter.x,
            controller.sat_time,
            *(getattr(controller.pid, name) for name in (
              'p', 'i', 'd', 'f', 'control', 'pos_limit', 'neg_limit',
            )),
          )
          if (
            not finite(requested)
            or abs(requested) > config.command_limit
            or not all(finite(float(value)) for value in native_state)
            or any(
              type(value) is not bool and not finite(value)
              for value in pid_log.to_dict().values()
            )
          ):
            raise ValueError('INVALID_NATIVE_OUTPUT')

          transcript.append(CurvatureYawControllerStep(
            step_index=index,
            time_s=frame['time_ns'] * 1e-9,
            feedback_sha256=feedback_hash,
            requested_normalized_torque=requested,
          ))
          metric_observations.append({
            'step_index': index,
            'time_s': frame['time_ns'] * 1e-9,
            'steering_angle_deg': float(car_state.steeringAngleDeg),
            'desired_steering_angle_deg': float(desired_angle_deg),
            'saturated': bool(pid_log.saturated),
          })
          observation = observe_curvature_yaw_step(
            config,
            state.plant_state,
            command=sign * requested,
            speed_mps=frame['speed_mps'],
            roll_rad=frame['roll_rad'],
          )
          if observation.status != 'DESCRIPTIVE_ONLY' or observation.next_state is None:
            raise ValueError('PLANT_STEP_REJECTED')
          next_plant = observation.next_state
          next_heading = state.heading_rad + next_plant.yaw_rate_rad_s * config.dt_s
          next_pose = state.pose_y_m + frame['speed_mps'] * math.sin(next_heading) * config.dt_s
          if not all(finite(value) for value in (next_heading, next_pose)):
            raise ValueError('POSE_OBSERVER_INVALID')
          state = CurvatureYawClosedLoopState(next_plant, next_heading, next_pose)

      transcript_t = tuple(transcript)
      _verify_source(native['source'])
      _verify_support_files(root, request['support_files'])
      result = {
        'status': 'COMPLETED',
        'scope': 'OFFLINE_NATIVE_CURVATURE_YAW_TRANSCRIPT',
        'request_sha256': digest(payload),
        'source_head': native['source']['head'],
        'opendbc_head': native['source']['opendbc_head'],
        'car_params_sha256': native['car_params_sha256'],
        'controller_identity_sha256': controller_identity_sha256(request),
        'plant_config_sha256': config_hash,
        'initial_state_sha256': initial_hash,
        'support_files_sha256': digest(canonical(request['support_files'])),
        'controller_transcript': [asdict(step) for step in transcript_t],
        'controller_transcript_sha256': controller_transcript_sha256(transcript_t),
        'metric_observations': metric_observations,
        'metric_observations_sha256': digest(canonical(metric_observations)),
        'final_state_sha256': closed_loop_state_sha256(state),
        'runtime_accepted': False,
        'promotable': False,
      }
      return result
    except Exception as exc:
      raise ValueError('NATIVE_CURVATURE_YAW_EXECUTION_REJECTED') from exc
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
    sys.stdout.buffer.write(canonical({
      'status': 'REJECTED',
      'code': 'INVALID_OR_FAILED_NATIVE_CURVATURE_YAW_REQUEST',
    }) + b'\n')
    return 1


if __name__ == '__main__':
  raise SystemExit(main())