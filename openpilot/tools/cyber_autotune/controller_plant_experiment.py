"""New plant-only diagnostic inputs; never candidates, controllers or search."""

import math

from openpilot.tools.cyber_autotune import controller_plant_authority as a
from openpilot.tools.cyber_autotune.curvature_yaw_plant import (
  CurvatureYawPlantConfig, CurvatureYawPlantState, observe_curvature_yaw_step,
)


def dc_gain(plant, speed):
  return (plant['command_gain_1pm'] + plant['command_speed_gain_s_per_m2'] * speed +
          plant['command_inv_speed_gain_per_s'] / speed) / (1 - plant['curvature_ar'])


def run_input(plant, reset, speed, amplitude, mode, steps):
  amplitude = a.command(amplitude, 'NORMALIZED_TORQUE')
  if mode not in ('STEP', 'RAMP') or type(steps) is not int or steps < 2:
    raise ValueError('DECLARED_INPUT_REQUIRED')
  config = CurvatureYawPlantConfig(**plant)
  state = CurvatureYawPlantState(reset['curvature_1pm'], reset['yaw_rate_rad_s'], tuple(reset['command_history']))
  # Independent convolution oracle is limited to this declared zero/flat reset.
  if any(reset[k] != 0 for k in ('curvature_1pm', 'yaw_rate_rad_s', 'heading_rad', 'pose_y_m')) or any(reset['command_history']):
    raise ValueError('ZERO_RESET_ORACLE_REQUIRED')
  if plant['curvature_intercept_1pm'] != 0 or plant['yaw_bias_rad_s'] != 0:
    raise ValueError('ZERO_BIAS_ORACLE_REQUIRED')
  dt = plant['dt_s']
  gain = dc_gain(plant, speed) * (1 - plant['curvature_ar'])
  commands, samples = [], []
  h = x = y = 0.
  maximum_residual = 0.
  for i in range(steps):
    u = amplitude if mode == 'STEP' else amplitude * i / (steps - 1)
    commands.append(u)
    obs = observe_curvature_yaw_step(config, state, command=-u, speed_mps=speed, roll_rad=0.)
    if obs.next_state is None:
      raise ValueError('PLANT_DOMAIN_FAILURE')
    state = obs.next_state
    # k[n] = -g sum_{j=0}^{n-delay} a^(n-delay-j) u[j].
    n = i - config.delay_steps
    expected_k = -gain * math.fsum(plant['curvature_ar'] ** (n - j) * commands[j] for j in range(n + 1))
    maximum_residual = max(maximum_residual, abs(state.curvature_1pm - expected_k),
                           abs(state.yaw_rate_rad_s + speed * expected_k))
    h += state.yaw_rate_rad_s * dt
    x += speed * math.cos(h) * dt
    y += speed * math.sin(h) * dt
    samples.append({'time_s': i * dt, 'elapsed_post_step_s': (i + 1) * dt, 'requested_torque': u,
                    'applied_normalized_torque': -obs.delayed_command, 'curvature_1pm': state.curvature_1pm,
                    'yaw_rate_rps': state.yaw_rate_rad_s, 'heading_rad': h, 'pose_x_m': x, 'pose_y_m': y})
  allowance = 128 * steps * math.ulp(max(1., abs(gain * amplitude / (1 - plant['curvature_ar'])) * speed))
  return {'samples': samples, 'maximum_oracle_residual': maximum_residual, 'roundoff_allowance': allowance,
          'analytic_recurrence_agrees': maximum_residual <= allowance,
          'steady_curvature_per_requested_torque_1pm': -dc_gain(plant, speed),
          'steady_yaw_per_requested_torque_rad_s': speed * dc_gain(plant, speed),
          'saturation': False, 'clipping': 'NONE_INPUT_REJECTED_OUTSIDE_DOMAIN',
          'delay_steps': plant['delay_steps']}


def original_geometry_oracle(plant, geometric_k, speed, steps):
  """Exercise the original historical pose integration, not a duplicate helper."""
  from openpilot.tools.cyber_autotune.curvature_yaw_v2_search import plant_trace
  u = a.command(geometric_k / dc_gain(plant, speed), 'NORMALIZED_TORQUE')
  reset = {'curvature_1pm': -geometric_k, 'yaw_rate_rad_s': geometric_k * speed,
           'command_history': [-u] * plant['delay_steps'], 'heading_rad': 0., 'pose_y_m': 0.}
  frames = [{'speed_mps': speed, 'roll_rad': 0.} for _ in range(steps)]
  trace = plant_trace([u] * steps, frames, plant, reset)
  duration = steps * plant['dt_s']
  truth = a.arc(geometric_k, speed * duration)
  last = trace[-1]
  actual = {k: last[k] for k in truth}
  error = math.hypot(actual['pose_x_m'] - truth['pose_x_m'], actual['pose_y_m'] - truth['pose_y_m'])
  bound = abs(geometric_k) * speed ** 2 * duration * plant['dt_s'] / 2
  rounding = 128 * steps * math.ulp(max(1., speed * duration))
  heading_error = abs(actual['heading_rad'] - truth['heading_rad'])
  return {'actual': actual, 'analytic': truth, 'position_error_m': error, 'heading_error_rad': heading_error,
          'riemann_bound_m': bound, 'roundoff_allowance': rounding,
          'within_discrete_bound': error <= bound + rounding and heading_error <= rounding,
          'original_plant_trace_exercised': True}
