"""TA-B offline V0. Instance-local native PID extension; no production hooks or IO.

Innovation predicts ONE STEP of the clipped native delayed-demand acceleration error.
Clipping inherits output authority, NOT a physical error bound. No physical delay queue.
"""
from dataclasses import asdict
import math
from pathlib import Path

import numpy as np
from opendbc.car import structs
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR
from opendbc.car.interfaces import CarInterfaceBase
from opendbc.car.vehicle_model import VehicleModel

from openpilot.common.pid import PIDController
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune.candidate_role_contracts import TrajectoryInput, TrajectoryAuthorityOutput
from openpilot.tools.cyber_autotune.native_protocol import digest
from openpilot.tools.cyber_autotune.trajectory_v0_freeze import load

MODES = ('DISABLED', 'CANONICAL_V0', 'TEST_ONLY_SAME_MECHANISM')


class LinearConversion:
  torque_from_lateral_accel_linear = CarInterfaceBase.torque_from_lateral_accel_linear
  torque_from_lateral_accel = CarInterfaceBase.torque_from_lateral_accel
  lateral_accel_from_torque_linear = CarInterfaceBase.lateral_accel_from_torque_linear
  lateral_accel_from_torque = CarInterfaceBase.lateral_accel_from_torque


class InnovationPID(PIDController):
  """Native antiwindup/limit arithmetic is delegated unchanged to super()."""
  def __init__(self, original, enabled):
    super().__init__(original._k_p, original._k_i, original._k_d, original.pos_limit, original.neg_limit, rate=100)
    self.innovation_enabled = enabled
    self.previous_clipped_error_mps2 = None
    self.correction_mps2 = 0.
    self.native_feedforward_mps2 = None
    self.pre_limit_accel_mps2 = None

  def update(self, error, error_rate=0., speed=0., feedforward=0., freeze_integrator=False):
    if not all(math.isfinite(float(v)) for v in (error, speed, feedforward, self.pos_limit, self.neg_limit)):
      raise ValueError('NONFINITE_NATIVE_PID_INPUT')
    clipped = float(np.clip(error, self.neg_limit, self.pos_limit))
    correction = 0.
    if self.innovation_enabled and self.previous_clipped_error_mps2 is not None:
      correction = float(np.clip(clipped - self.previous_clipped_error_mps2, self.neg_limit, self.pos_limit))
    self.previous_clipped_error_mps2 = clipped if self.innovation_enabled else None
    self.correction_mps2 = correction
    self.native_feedforward_mps2 = float(feedforward)
    # Disabled/first sample leaves original feedforward value EXACTLY unchanged.
    combined = feedforward if correction == 0. else feedforward + correction
    output = super().update(error, error_rate, speed, combined, freeze_integrator)
    # Exact operands used by super, not reverse reconstruction from limited torque.
    self.pre_limit_accel_mps2 = float(self.p + self.i + self.d + self.f)
    if not math.isfinite(self.pre_limit_accel_mps2):
      raise ValueError('NONFINITE_PRE_LIMIT')
    return output


class NativeBaseline:
  """Direct native baseline with the NEW experiment's explicit fresh-instance reset policy."""
  def __init__(self):
    self.policy = load()
    self._cp_builder = CarInterface.get_non_essential_params(CAR.HYUNDAI_SANTA_FE_2022)
    self.cp = self._cp_builder.as_reader()
    self.cp_sha256 = self._profile_sha()
    self.model = VehicleModel(self.cp)
    self._prior = None
    self._pending_events = ['EXPERIMENT_START']
    self.controller = self._new_native()
    self._initial_signature = self._signature()

  def _profile_sha(self):
    payload = self._cp_builder.to_bytes()
    self._cp_builder.clear_write_flag()
    return digest(payload)

  def _signature(self):
    pid = self.controller.pid
    return a.hash_object({'gains': [pid._k_p, pid._k_i, pid._k_d], 'limits': [pid.neg_limit, pid.pos_limit],
                          'tuning': self.controller.torque_params.to_dict(), 'dt': self.controller.dt,
                          'pid_i_dt': pid.i_dt, 'filter_alpha': self.controller.jerk_filter.alpha,
                          'filter_dt': self.controller.jerk_filter.dt,
                          'filter_initialized': self.controller.jerk_filter.initialized,
                          'reference_buffer': [self.controller.lat_accel_request_buffer_len,
                                               self.controller.lat_accel_request_buffer.maxlen,
                                               len(self.controller.lat_accel_request_buffer)],
                          'lookahead_frames': self.controller.lookahead_frames,
                          'deadzone_deg': self.controller.steering_angle_deadzone_deg,
                          'steer_max': self.controller.steer_max, 'sat_limit': self.controller.sat_limit,
                          'sat_check_min_speed': self.controller.sat_check_min_speed,
                          'vehicle_model_static_parameters': vars(self.model)})

  def _new_native(self):
    return LatControlTorque(self.cp, LinearConversion(), .01)

  def reset(self, event):
    if event not in a.EVENTS or event == 'CONFIG_CHANGE':
      raise ValueError('NEW_INSTANCE_REQUIRED_OR_UNKNOWN_RESET')
    self.controller = self._new_native()
    self._prior = None
    self._pending_events = [event]

  def _prepare(self, row):
    if type(row) is not TrajectoryInput:
      raise ValueError('EXACT_TRAJECTORY_INPUT_REQUIRED')
    if self._prior is not None and not math.isclose(row.time_s-self._prior.time_s, .01, abs_tol=1e-12, rel_tol=0.):
      raise ValueError('CAUSAL_CONTIGUOUS_TIME_REQUIRED')
    if self._profile_sha() != self.cp_sha256 or self._signature() != self._initial_signature:
      raise ValueError('RUNTIME_PROFILE_OR_CONFIG_MUTATION')
    events = list(self._pending_events)
    self._pending_events = []
    if self._prior is not None:
      old = self._prior
      if old.active and not row.active:
        events.append('INACTIVE')
      if not old.steering_pressed and row.steering_pressed:
        events.append('STEERING_PRESSED')
      if old.steering_pressed and not row.steering_pressed:
        events.append('RELEASE')
      if not old.active and row.active:
        events.append('REENGAGEMENT')
    if events and 'EXPERIMENT_START' not in events:
      self.controller = self._new_native()
    self._prior = row
    return events

  def _call(self, row):
    try:
      accel = row.desired_curvature_1pm * row.speed_mps ** 2
      actual_accel = row.actual_curvature_1pm * row.speed_mps ** 2
    except OverflowError as exc:
      raise ValueError('NONFINITE_DERIVED_INPUT') from exc
    if not all(math.isfinite(v) for v in (accel, actual_accel)):
      raise ValueError('NONFINITE_DERIVED_INPUT')
    state = structs.CarState()
    state.vEgo = state.vEgoRaw = row.speed_mps
    state.steeringPressed = row.steering_pressed
    with np.errstate(over='raise', invalid='raise', divide='raise'):
      state.steeringAngleDeg = math.degrees(self.model.get_steer_from_curvature(
        -row.actual_curvature_1pm, row.speed_mps, row.roll_rad))
      params = type('OfflineParameters', (), {'roll': row.roll_rad, 'angleOffsetDeg': 0.})()
      result = self.controller.update(row.active, state, self.model, params, row.safety_limited,
                                      row.desired_curvature_1pm, row.curvature_limited, .15)
    if not math.isfinite(float(result[0])) or abs(result[0]) > 1.:
      raise ValueError('NATIVE_OUTPUT_OUTSIDE_DOMAIN')
    return result

  def update(self, row):
    self._prepare(row)
    return self._call(row)


class Core(NativeBaseline):
  def __init__(self, config='CANONICAL_V0'):
    if type(config) is not str or config not in MODES:
      raise ValueError('ONLY_FROZEN_CONFIGS_ALLOWED')
    self._mode = config
    self._initial_mode = config
    self.trace = None
    super().__init__()
    self.source_sha256 = digest(Path(__file__).read_bytes())
    self.config_sha256 = a.hash_object({'mode': config, 'policy': self.policy['config']['receipt_sha256']})

  @property
  def config(self):
    return self._mode

  def _new_native(self):
    native = super()._new_native()
    native.pid = InnovationPID(native.pid, self._mode != 'DISABLED')
    return native

  def update(self, row):
    if self._mode != self._initial_mode or not isinstance(self.controller.pid, InnovationPID):
      raise ValueError('RUNTIME_CONFIG_MUTATION')
    events = self._prepare(row)
    pid = self.controller.pid
    enabled = self._mode != 'DISABLED' and row.active and not row.steering_pressed
    pid.innovation_enabled = enabled
    if not enabled:
      pid.previous_clipped_error_mps2 = None
      pid.correction_mps2 = 0.
    requested, _, log = self._call(row)
    observed = row.active
    factor_conversion = self.controller.torque_from_lateral_accel
    tuning = self.controller.torque_params
    def normalize(value):
      return -float(factor_conversion(value, tuning))
    pre = normalize(pid.pre_limit_accel_mps2) if observed else None
    feedback = normalize(pid.p + pid.i + pid.d + pid.correction_mps2) if observed else None
    output = TrajectoryAuthorityOutput(
      float(requested), row.desired_curvature_1pm-row.actual_curvature_1pm if observed else None,
      None, feedback, None,
      bool(pid.pre_limit_accel_mps2 > pid.pos_limit or pid.pre_limit_accel_mps2 < pid.neg_limit) if observed else None,
      pre, 'OFFLINE_PROTOTYPE_OBSERVED' if observed else 'UNAVAILABLE',
      self.source_sha256, self.config_sha256)
    self.trace = {
      'state_fields': ['previous_clipped_error_mps2'], 'state_owner': 'TA', 'physical_delay_owner': 'PLANT',
      'previous_clipped_error_mps2': pid.previous_clipped_error_mps2, 'correction_mps2': pid.correction_mps2,
      'authority_mps2': float(pid.pos_limit), 'native_delayed_error_mps2': float(log.error) if observed else None,
      'native_ff_including_friction_mps2': pid.native_feedforward_mps2 if observed else None,
      'pre_limit_accel_mps2': pid.pre_limit_accel_mps2 if observed else None,
      'controller_limited_accel_mps2': float(pid.control) if observed else None,
      'pre_governor_torque': float(requested), 'final_requested_torque': float(requested),
      'upstream_saturation_timer_flag': bool(log.saturated) if observed else None,
      'reset_events': events, 'output': asdict(output),
      'native_state': [*map(float, self.controller.lat_accel_request_buffer),
                       float(self.controller.jerk_filter.x), float(self.controller.sat_time),
                       *[float(getattr(pid, key)) for key in ('p', 'i', 'd', 'f', 'control', 'pos_limit', 'neg_limit')]],
    }
    return output
