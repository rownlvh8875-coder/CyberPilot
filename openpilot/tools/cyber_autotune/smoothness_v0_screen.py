"""SG-only frozen baseline command replay. Not SG closed-loop stability evidence."""

from dataclasses import asdict
from fractions import Fraction
import json
import math
from pathlib import Path
import platform
import subprocess
import sys

from openpilot.common.pid import PIDController
from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune import smoothness_v0_metrics as metrics
from openpilot.tools.cyber_autotune import trajectory_v0_publication as ta_public
from openpilot.tools.cyber_autotune.candidate_role_contracts import GovernorCommand, InterventionInput, TrajectoryInput
from openpilot.tools.cyber_autotune.curvature_yaw_plant import CurvatureYawPlantState, observe_curvature_yaw_step
from openpilot.tools.cyber_autotune.native_protocol import digest
from openpilot.tools.cyber_autotune.resolution_candidate_evidence import immutable_public
from openpilot.tools.cyber_autotune.smoothness_governor_v0 import Governor
from openpilot.tools.cyber_autotune.smoothness_v0_baseline import BASELINE_IDENTITY
from openpilot.tools.cyber_autotune.smoothness_v0_freeze import load
from openpilot.tools.cyber_autotune.smoothness_v0_policy import PUBLIC, seal
from openpilot.tools.cyber_autotune.trajectory_authority_core import NativeBaseline
from openpilot.tools.cyber_autotune.trajectory_v0_screen import PLANT, scenarios

MODES = ('SG_DISABLED', 'CURRENT_ALIAS', 'SG_V0_CANONICAL')
STAGES = ('requested', 'applied', 'curvature', 'yaw_rate', 'heading', 'pose_x', 'pose_y')


def authorize(role, *, composition=False, ta_enabled=False):
  if role not in load()['matrix']['allowed_roles'] or composition is not False or ta_enabled is not False:
    raise ValueError('SG_STANDALONE_ONLY_AUTHORIZATION_REQUIRED')


def baseline_identity(core=None):
  core = NativeBaseline() if core is None else core
  if type(core) is not NativeBaseline or type(core.controller.pid) is not PIDController:
    raise ValueError('UNCHANGED_NATIVE_BASELINE_ONLY')
  source = digest((Path(__file__).parent / 'trajectory_authority_core.py').read_bytes())
  config = a.hash_object(
    {
      'class': 'NativeBaseline',
      'native_signature': core._initial_signature,
      'car_params_sha256': core.cp_sha256,
      'native_reference_alignment_s': 0.15,
      'reset_policy': load()['config']['reset_ownership'],
      'dt_s': 0.01,
    }
  )
  return {'role': 'UNCHANGED_NATIVE_BASELINE', 'source_sha256': source, 'config_sha256': config, 'car_params_sha256': core.cp_sha256}


def step(state, command, frame, pose):
  obs = observe_curvature_yaw_step(PLANT, state, command=-command, speed_mps=frame['speed_mps'], roll_rad=frame['roll_rad'])
  if obs.status != 'DESCRIPTIVE_ONLY':
    raise ValueError('PLANT_DOMAIN_FAILURE')
  x, y, heading = pose
  heading += obs.next_state.yaw_rate_rad_s * 0.01
  x += frame['speed_mps'] * math.cos(heading) * 0.01
  y += frame['speed_mps'] * math.sin(heading) * 0.01
  return (
    obs.next_state,
    (x, y, heading),
    {
      'requested': command,
      'applied': -obs.delayed_command,
      'curvature': obs.next_state.curvature_1pm,
      'yaw_rate': obs.next_state.yaw_rate_rad_s,
      'heading': heading,
      'pose_x': x,
      'pose_y': y,
    },
  )


def baseline_commands(name):
  inputs = scenarios()
  if name not in inputs:
    raise ValueError('FROZEN_SCENARIO_REQUIRED')
  native = NativeBaseline()
  identity = baseline_identity(native)
  state = CurvatureYawPlantState(0.0, 0.0, (0.0, 0.0))
  pose = (0.0, 0.0, 0.0)
  prior = None
  rows = []
  plant = []
  for i, frame in enumerate(inputs[name]):
    flags = {k: v for k, v in frame.items() if k != 'phase'}
    ti = TrajectoryInput(actual_curvature_1pm=state.curvature_1pm, **flags)
    u = float(native.update(ti)[0])
    intervention = InterventionInput(
      ti.time_s,
      ti.dt_s,
      ti.active,
      ti.steering_pressed,
      prior is not None and prior.steering_pressed and not ti.steering_pressed,
      prior is not None and not prior.active and ti.active,
    )
    cmd = GovernorCommand(u, identity['source_sha256'], identity['config_sha256'])
    state, pose, obs = step(state, u, frame, pose)
    plant.append(obs)
    pid = native.controller.pid
    rows.append(
      {
        'index': i,
        'frame': frame,
        'intervention': asdict(intervention),
        'command': asdict(cmd),
        'native_state': {
          'pid': [float(getattr(pid, k)) for k in ('p', 'i', 'd', 'f', 'control')],
          'reference_buffer': list(map(float, native.controller.lat_accel_request_buffer)),
          'jerk_filter_x': float(native.controller.jerk_filter.x),
          'sat_time': float(native.controller.sat_time),
        },
      }
    )
    prior = ti
  return seal(
    {
      'schema': 'SG_FROZEN_BASELINE_COMMANDS_V1',
      'role': 'UNCHANGED_NATIVE_BASELINE',
      'scenario': name,
      'core_identity': identity,
      'rows': rows,
      'plant_trace_sha256': a.hash_object(plant),
      'scenario_input_sha256': a.hash_object(inputs[name]),
      'sg_feedback_used': False,
      'ta_output_used': False,
    }
  )


def verify_commands(row, expected_sha):
  if (
    type(row) is not dict
    or row.get('receipt_sha256') != expected_sha
    or a.hash_object({k: v for k, v in row.items() if k != 'receipt_sha256'}) != expected_sha
    or row.get('role') != 'UNCHANGED_NATIVE_BASELINE'
    or row.get('core_identity') != baseline_identity()
    or row.get('ta_output_used') is not False
    or row.get('sg_feedback_used') is not False
    or row.get('scenario') not in scenarios()
    or row.get('scenario_input_sha256') != a.hash_object(scenarios()[row['scenario']])
  ):
    raise ValueError('EXACT_FROZEN_BASELINE_COMMANDS_REQUIRED')
  if [r['frame'] for r in row['rows']] != scenarios()[row['scenario']]:
    raise ValueError('FROZEN_BASELINE_INPUT_DRIFT')

  prior = None
  identity = row['core_identity']
  for i, r in enumerate(row['rows']):
    if set(r) != {'index', 'frame', 'intervention', 'command', 'native_state'} or type(r['index']) is not int or r['index'] != i:
      raise ValueError('EXACT_BASELINE_ROW_SCHEMA_REQUIRED')
    frame = r['frame']
    expected = InterventionInput(
      frame['time_s'],
      frame['dt_s'],
      frame['active'],
      frame['steering_pressed'],
      prior is not None and prior['steering_pressed'] and not frame['steering_pressed'],
      prior is not None and not prior['active'] and frame['active'],
    )
    if InterventionInput.parse(r['intervention']) != expected:
      raise ValueError('FRAME_INTERVENTION_BINDING_REQUIRED')
    command = GovernorCommand.parse(r['command'])
    if (command.core_source_sha256, command.core_config_sha256) != (identity['source_sha256'], identity['config_sha256']):
      raise ValueError('PER_COMMAND_BASELINE_CORE_BINDING_REQUIRED')
    prior = frame


def run_arm(commands, mode, expected_sha):
  authorize('DEVELOPMENT_SCREEN')
  if mode not in MODES:
    raise ValueError('SG_EXACT_ARM_REQUIRED')
  verify_commands(commands, expected_sha)
  actual = 'SG_DISABLED' if mode == 'CURRENT_ALIAS' else mode
  ident = commands['core_identity']
  sg = Governor(actual, ident['source_sha256'], ident['config_sha256'])
  state = CurvatureYawPlantState(0.0, 0.0, (0.0, 0.0))
  pose = (0.0, 0.0, 0.0)
  rows = []
  for r in commands['rows']:
    cmd = GovernorCommand.parse(r['command'])
    inter = InterventionInput.parse(r['intervention'])
    output = sg.update(cmd, inter)
    ti = TrajectoryInput(actual_curvature_1pm=state.curvature_1pm, **{k: v for k, v in r['frame'].items() if k != 'phase'})
    state, pose, obs = step(state, output.final_requested_torque, r['frame'], pose)
    rows.append(
      {
        'index': r['index'],
        'input': asdict(ti),
        'phase': r['frame']['phase'],
        'pre': cmd.normalized_torque,
        **obs,
        'saturation': output.governor_output_saturated,
        'reset_events': list(output.reset_events),
        'trace': asdict(output),
        'intervention': r['intervention'],
      }
    )

  # Exact rational arithmetic avoids an arbitrary epsilon hiding a TV/sign defect.
  def tv(values):
    return sum(abs(Fraction(b) - Fraction(a)) for a, b in zip(values, values[1:], strict=False))

  u = [r['pre'] for r in rows]
  y = [r['requested'] for r in rows]
  if tv(y) + abs(Fraction(u[-1]) - Fraction(y[-1])) > tv(u):
    raise ValueError('TOTAL_VARIATION_EXPANSION')

  def nonzero(x):
    return [v > 0 for v in x if v != 0.0]

  def reversals(x):
    z = nonzero(x)
    return sum(a != b for a, b in zip(z, z[1:], strict=False))

  if reversals(y) > reversals(u):
    raise ValueError('NEW_SIGN_REVERSAL')
  if mode in ('SG_DISABLED', 'CURRENT_ALIAS'):
    if a.hash_object([{k: r[k] for k in STAGES} for r in rows]) != commands['plant_trace_sha256']:
      raise ValueError('BASELINE_REPLAY_NOT_EXACT')
  return rows


def binding():
  prior = ta_public.load()
  policies = load()
  for path, sha in policies['policy']['source_bindings'].items():
    if digest((a.ROOT / path).read_bytes()) != sha:
      raise ValueError('SG_PREFROZEN_SOURCE_DRIFT')
  if baseline_identity() != dict(BASELINE_IDENTITY):
    raise ValueError('SOURCE_BASELINE_IDENTITY_DRIFT')
  paths = (
    'smoothness_governor_v0.py',
    'smoothness_v0_screen.py',
    'smoothness_v0_metrics.py',
    'smoothness_v0_freeze.py',
    'smoothness_v0_policy.py',
    'smoothness_v0_baseline.py',
    'trajectory_v0_screen.py',
    'trajectory_v0_metrics.py',
  )
  return seal(
    {
      'schema': 'SMOOTHNESS_V0_EXECUTION_BINDING_V1',
      'status': 'FROZEN_BEFORE_COMMAND_GENERATION_AND_ARM_REPLAY',
      'implementation_commit_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=a.ROOT, text=True).strip(),
      'policy_receipts': {k: v['receipt_sha256'] for k, v in policies.items()},
      'source_sha256': {p: digest((Path(__file__).parent / p).read_bytes()) for p in paths},
      'native_support_sha256': {**prior['binding']['executed_support_sha256'], **policies['policy']['source_bindings']},
      'baseline_core_identity': baseline_identity(),
      'baseline_core_identity_sha256': a.hash_object(baseline_identity()),
      'native_software_sha256': a.hash_object({**prior['binding']['executed_support_sha256'], **policies['policy']['source_bindings']}),
      'environment_sha256': a.hash_object({'python': platform.python_version(), 'machine': platform.machine(), 'numpy': metrics.np.__version__}),
      'profile': 'SOURCE_HYUNDAI_SANTA_FE_2022_DESCRIPTIVE_ONLY_NOT_ACTIVATION',
      'state_schema_sha256': a.hash_object(policies['config']['state_fields']),
      'reset_policy_sha256': a.hash_object(policies['config']['reset_ownership']),
      'intervention_policy_sha256': policies['config']['receipt_sha256'],
      'input_output_contract_sha256': digest((Path(__file__).parent / 'candidate_role_contracts.py').read_bytes()),
      'enabled_output_contract_sha256': digest((Path(__file__).parent / 'smoothness_governor_v0.py').read_bytes()),
      'plant_config': asdict(PLANT),
      'plant_source_sha256': digest((Path(__file__).parent / 'curvature_yaw_plant.py').read_bytes()),
      'physical_delay_owner': 'PLANT',
      'environment': {'python': platform.python_version(), 'machine': platform.machine(), 'numpy': metrics.np.__version__},
      'timebase_sha256': a.hash_object({'dt_s': 0.01, 'samples': 800}),
      'scenario_input_sha256': {k: a.hash_object(v) for k, v in scenarios().items()},
      'historical_ta_receipts': {k: v['receipt_sha256'] for k, v in prior.items()},
      'ta_enabled': False,
      'composition_authorized': False,
      'search_authorized': False,
    }
  )


def verify_binding(row):
  if row != binding():
    raise ValueError('SG_EXECUTION_IDENTITY_DRIFT')


def arm_identity(mode, context):
  if mode not in MODES:
    raise ValueError('SG_EXACT_ARM_REQUIRED')
  return a.hash_object(
    {
      'role': 'SG_STANDALONE',
      'family': 'SG-A',
      'mode': 'SG_DISABLED' if mode == 'CURRENT_ALIAS' else mode,
      'execution_binding_sha256': context['receipt_sha256'],
    }
  )


def positive_controls():
  source, config = BASELINE_IDENTITY['source_sha256'], BASELINE_IDENTITY['config_sha256']

  def run(values, mode='SG_V0_CANONICAL', events=None):
    sg = Governor(mode, source, config)
    return [
      sg.update(
        GovernorCommand(u, source, config),
        InterventionInput(i * 0.01, 0.01, **(events[i] if events else {'active': True, 'steering_pressed': False, 'release': False, 'reengagement': False})),
      ).post_governor
      for i, u in enumerate(values)
    ]

  fixtures = {
    'constant_zero': [0.0] * 4,
    'constant_positive': [0.5] * 4,
    'constant_negative': [-0.5] * 4,
    'positive_reversal': [1.0, -1.0, -1.0],
    'negative_reversal': [-1.0, 1.0, 1.0],
    'alternating_rails': [1.0, -1.0] * 4,
    'small_chatter': [0.01, -0.01] * 4,
    'smooth_ramp': [-1.0, -0.5, 0.0, 0.5, 1.0],
  }
  expected = {
    **fixtures,
    'positive_reversal': [1.0, 0.0, -1.0],
    'negative_reversal': [-1.0, 0.0, 1.0],
    'alternating_rails': [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0],
  }
  checks = {name: run(values) == expected[name] for name, values in fixtures.items()}
  checks['disabled_exact'] = all(run(v, 'SG_DISABLED') == v for v in fixtures.values())
  flags = [
    {'active': True, 'steering_pressed': False, 'release': False, 'reengagement': False},
    {'active': True, 'steering_pressed': True, 'release': False, 'reengagement': False},
    {'active': True, 'steering_pressed': False, 'release': True, 'reengagement': False},
    {'active': False, 'steering_pressed': False, 'release': False, 'reengagement': False},
    {'active': True, 'steering_pressed': False, 'release': False, 'reengagement': True},
  ]
  checks['pressed_release_inactive_reengagement'] = run([1.0, -1.0, 1.0, 0.0, -1.0], events=flags) == [1.0, -1.0, 1.0, 0.0, -1.0]
  if not all(checks.values()):
    raise ValueError('SG_TEST_ONLY_CONTROL_FAILED')
  return {'scope': 'TEST_ONLY_NOT_CANDIDATE_PERFORMANCE', 'checks': checks, 'config_search': False}


def write(path, row):
  immutable_public(path, (json.dumps(row, indent=2, sort_keys=True) + '\n').encode())


def execute(folder):
  authorize('DEVELOPMENT_SCREEN')
  if not sys.dont_write_bytecode or not sys.pycache_prefix or any(Path(sys.pycache_prefix).rglob('*.pyc')):
    raise ValueError('FRESH_SOURCE_ONLY_INTERPRETER_REQUIRED')
  folder = Path(folder)
  frozen = binding()
  write(folder / 'execution-binding.json', frozen)
  controls = positive_controls()
  rows = []
  for name in scenarios():
    commands = baseline_commands(name)
    if commands != baseline_commands(name):
      raise ValueError('BASELINE_COMMAND_REPEATABILITY_FAILED')
    write(folder / (name + '-frozen-baseline.json'), commands)  # BEFORE ANY arm for this scenario.
    arms = {}
    for arm, mode in zip(load()['matrix']['arms'], MODES, strict=True):
      first = run_arm(commands, mode, commands['receipt_sha256'])
      second = run_arm(commands, mode, commands['receipt_sha256'])
      m1, m2 = metrics.evaluate(first), metrics.evaluate(second)
      verify_binding(frozen)
      if first != second or m1 != m2:
        raise ValueError('SG_EXACT_REPEATABILITY_FAILED')
      write(folder / (name + '-' + arm + '.json'), first)
      arms[arm] = {
        'identity_sha256': arm_identity(mode, frozen),
        'trace_sha256': a.hash_object(first),
        'repeat_trace_sha256': a.hash_object(second),
        'metric_sha256': a.hash_object(m1),
        'repeat_metric_sha256': a.hash_object(m2),
        'metrics': m1,
        'repeatability': 'EXACT_PASS',
      }
      if arm == 'UPSTREAM_BASELINE':
        baseline = first
      elif arm == 'CYBER_CURRENT_ALIAS':
        if first != baseline:
          raise ValueError('CURRENT_NOT_EXACT_BASELINE_ALIAS')
      else:
        arms[arm]['effect_vs_baseline'] = metrics.effects(baseline, first)
    rows.append(
      {
        'scenario': name,
        'frozen_core_commands_sha256': commands['receipt_sha256'],
        'baseline_generation_plant_sha256': commands['plant_trace_sha256'],
        'arms': arms,
      }
    )
  verify_binding(frozen)
  result = seal(
    {
      'schema': 'SMOOTHNESS_V0_EXPERIMENT_RESULTS_V1',
      'status': 'SG_STANDALONE_STRUCTURAL_PASS',
      'family': 'SG-A',
      'selection_frozen_commit': '8cdb4476f',
      'execution_binding_sha256': frozen['receipt_sha256'],
      'role': 'DEVELOPMENT_SCREEN',
      'baseline_core_input_only': True,
      'scenarios': rows,
      'positive_controls': controls,
      'exact_repeats_per_arm': 2,
      'ta_enabled': False,
      'composed': False,
      'candidate_acceptance': False,
      'feedback_loop_stability_evaluated': False,
      'execution_semantics': 'FROZEN_NATIVE_COMMAND_REPLAY_DESCRIPTIVE_PLANT',
      'performance_threshold': None,
      'threshold_status': 'THRESHOLD_UNJUSTIFIED',
    }
  )
  write(folder / 'results.json', result)
  write(PUBLIC / 'smoothness-v0-execution-binding-v1.json', frozen)
  write(PUBLIC / 'smoothness-v0-experiment-results-v1.json', result)
  return result


if __name__ == '__main__':
  execute(sys.argv[1])
