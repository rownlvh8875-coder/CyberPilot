"""Fixed TA-only synthetic development execution. No search/evaluation/activation."""
from dataclasses import asdict
import json
import math
from pathlib import Path
import platform
import sys
import subprocess

from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune import trajectory_v0_metrics as metrics
from openpilot.tools.cyber_autotune.curvature_yaw_plant import (
  CurvatureYawPlantConfig, CurvatureYawPlantState, observe_curvature_yaw_step,
)
from openpilot.tools.cyber_autotune.candidate_role_contracts import TrajectoryInput
from openpilot.tools.cyber_autotune.native_protocol import digest
from openpilot.tools.cyber_autotune.resolution_candidate_evidence import immutable_public
from openpilot.tools.cyber_autotune.trajectory_authority_core import Core, NativeBaseline
from openpilot.tools.cyber_autotune.trajectory_v0_freeze import load
from openpilot.tools.cyber_autotune.trajectory_v0_policy import seal, PUBLIC

# Existing descriptive fixture coefficients, not fitted vehicle dynamics.
PLANT = CurvatureYawPlantConfig(.01, 2, 2.5, 30., 1., 0., .92, .004, .0002, .002, .001, .75, 0.)


def authorize(role, *, sg_enabled=False, composition=False):
  if role not in load()['matrix']['allowed_roles'] or sg_enabled is not False or composition is not False:
    raise ValueError('TA_ONLY_AUTHORIZATION_REQUIRED')


def scenarios():
  rows = {}
  for spec in load()['scenarios']['rows']:
    frames = []
    for i in range(spec['samples']):
      time = i*.01
      if spec['profile'] == 'REVERSAL':
        if 1 <= time < 3:
          scale, phase = 1-abs(time-2), 'ENTRY' if time < 2 else 'EXIT'
        elif 3 <= time < 5:
          scale, phase = -(1-abs(time-4)), 'REVERSAL'
        else:
          scale, phase = 0., 'STRAIGHT'
      elif 1 <= time < 2:
        scale, phase = time-1, 'ENTRY'
      elif 2 <= time < 4:
        scale, phase = 1., 'APEX'
      elif 4 <= time < 5:
        scale, phase = 5-time, 'EXIT'
      else:
        scale, phase = 0., 'STRAIGHT'
      frames.append({'desired_curvature_1pm': spec['curvature_amplitude_1pm']*scale,
                     'speed_mps': spec['speed_mps'], 'time_s': time, 'dt_s': .01, 'roll_rad': 0.,
                     'active': not(spec['profile'] == 'DRIVER' and 5 <= time < 6),
                     'steering_pressed': spec['profile'] == 'DRIVER' and 2 <= time < 3,
                     'safety_limited': spec['profile'] == 'LIMITS' and 2 <= time < 3,
                     'curvature_limited': spec['profile'] == 'LIMITS' and 3 <= time < 4,
                     'phase': phase})
    rows[spec['id']] = frames
  return rows


def run_arm(name, mode):
  authorize('DEVELOPMENT_SCREEN')
  inputs = scenarios()
  if name not in inputs or mode not in ('DISABLED', 'CURRENT_ALIAS', 'CANONICAL_V0'):
    raise ValueError('EXACT_FROZEN_SCENARIO_CONFIG_REQUIRED')
  # Alias executes the SAME disabled core, not a different controller/config.
  core = Core('DISABLED' if mode == 'CURRENT_ALIAS' else mode)
  direct = NativeBaseline() if mode in ('DISABLED', 'CURRENT_ALIAS') else None
  state = CurvatureYawPlantState(0., 0., (0., 0.))
  x = y = heading = 0.
  result = []
  for i, frame in enumerate(inputs[name]):
    fields = {k: v for k, v in frame.items() if k != 'phase'}
    row = TrajectoryInput(actual_curvature_1pm=state.curvature_1pm, **fields)
    out = core.update(row)
    if direct is not None:
      if out.raw_requested_torque != direct.update(row)[0]:
        raise ValueError('DISABLED_NOT_EXACT_NATIVE_BASELINE')
      if any(getattr(core.controller.pid, key) != getattr(direct.controller.pid, key)
             for key in ('p', 'i', 'd', 'f', 'control')) or core.controller.lat_accel_request_buffer != direct.controller.lat_accel_request_buffer:
        raise ValueError('DISABLED_NATIVE_STATE_MISMATCH')
    if core.trace['reset_events'] and core.trace['correction_mps2'] != 0.:
      raise ValueError('RESET_INNOVATION_LEAK')
    obs = observe_curvature_yaw_step(PLANT, state, command=-out.raw_requested_torque, speed_mps=row.speed_mps, roll_rad=row.roll_rad)
    if obs.status != 'DESCRIPTIVE_ONLY':
      raise ValueError('PLANT_DOMAIN_FAILURE')
    state = obs.next_state
    heading += state.yaw_rate_rad_s*.01
    x += row.speed_mps*math.cos(heading)*.01
    y += row.speed_mps*math.sin(heading)*.01
    result.append({'index': i, 'input': asdict(row), 'phase': frame['phase'],
                   'requested': out.raw_requested_torque, 'applied': -obs.delayed_command,
                   'curvature': state.curvature_1pm, 'yaw_rate': state.yaw_rate_rad_s,
                   'heading': heading, 'pose_x': x, 'pose_y': y,
                   'saturation': out.saturation_intent, 'reset_events': core.trace['reset_events'],
                   'trace': core.trace})
  return result


def binding():
  policy = load()
  paths = ('trajectory_authority_core.py', 'trajectory_v0_screen.py', 'trajectory_v0_metrics.py', 'trajectory_v0_freeze.py')
  cp = NativeBaseline()
  support = ('openpilot/common/filter_simple.py', 'openpilot/common/constants.py',
             'openpilot/tools/cyber_autotune/native_protocol.py', 'openpilot/tools/cyber_autotune/resolution_candidate_evidence.py',
             'opendbc_repo/opendbc/car/hyundai/values.py', 'opendbc_repo/opendbc/car/torque_data/params.toml',
             'opendbc_repo/opendbc/car/torque_data/substitute.toml', 'opendbc_repo/opendbc/car/torque_data/override.toml')
  support_hashes = {p: digest((a.ROOT/p).read_bytes()) for p in support}
  return seal({'schema': 'TRAJECTORY_V0_EXECUTION_BINDING_V1', 'status': 'FROZEN_BEFORE_CLOSED_LOOP_RUN',
               'implementation_commit_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=a.ROOT, text=True).strip(),
               'policy_receipts': {k: v['receipt_sha256'] for k, v in policy.items()},
               'source_sha256': {p: digest((Path(__file__).parent/p).read_bytes()) for p in paths},
               'state_schema_sha256': a.hash_object(policy['config']['state_fields']),
               'reset_policy_sha256': a.hash_object(policy['config']['reset_policy']),
               'input_output_contract_sha256': policy['policy']['source_bindings']['openpilot/tools/cyber_autotune/candidate_role_contracts.py'],
               'native_software_sha256': a.hash_object({**policy['policy']['source_bindings'], **support_hashes}),
               'executed_support_sha256': support_hashes,
               'environment_sha256': a.hash_object({'python': platform.python_version(), 'machine': platform.machine(), 'numpy': metrics.np.__version__}),
               'car_params_sha256': cp.cp_sha256, 'profile': 'SOURCE_HYUNDAI_SANTA_FE_2022_NOT_VEHICLE_ACTIVATION',
               'plant_sha256': digest((Path(__file__).parent/'curvature_yaw_plant.py').read_bytes()),
               'plant_config': asdict(PLANT), 'plant_config_sha256': a.hash_object(asdict(PLANT)),
               'environment': {'python': platform.python_version(), 'machine': platform.machine(), 'numpy': metrics.np.__version__},
               'timebase_sha256': a.hash_object({'dt_s': .01, 'samples': 800}),
               'scenario_input_sha256': {k: a.hash_object(v) for k, v in scenarios().items()},
               'lat_delay_reference_s': .15, 'physical_delay_s': .02,
               'delay_semantics': 'native .15 reference alignment unchanged; sole physical queue PLANT .02; innovation horizon .01 is neither'})



def verify_binding(row):
  if type(row) is not dict or row != binding():
    raise ValueError('EXECUTION_IDENTITY_DRIFT')


def arm_identity(mode, context):
  if mode not in ('DISABLED', 'CURRENT_ALIAS', 'CANONICAL_V0'):
    raise ValueError('EXACT_ARM_REQUIRED')
  actual = 'DISABLED' if mode == 'CURRENT_ALIAS' else mode
  return a.hash_object({
    'role': 'TA_STANDALONE', 'family': 'TA-B', 'mode': actual,
    'source_sha256': context['source_sha256'], 'config_sha256': load()['config']['receipt_sha256'],
    **{key: context[key] for key in ('state_schema_sha256', 'reset_policy_sha256', 'input_output_contract_sha256',
                                     'native_software_sha256', 'car_params_sha256', 'plant_sha256',
                                     'plant_config_sha256', 'environment_sha256', 'timebase_sha256')},
    'policy_receipts': context['policy_receipts'],
  })


def positive_controls():
  from openpilot.tools.cyber_autotune.trajectory_authority_core import InnovationPID
  from openpilot.common.pid import PIDController
  core = Core('TEST_ONLY_SAME_MECHANISM')
  authority = core.controller.pid.pos_limit
  pid = InnovationPID(PIDController(.8, .15, pos_limit=authority, neg_limit=-authority), True)
  pid.update(-authority/2)
  first_zero = pid.correction_mps2 == 0.
  pid.update(authority/2)
  signed = pid.correction_mps2 == authority
  limited = pid.control == authority and pid.pre_limit_accel_mps2 > authority
  pid.update(100*authority)
  pid.update(200*authority)
  constant_clipped_zero = pid.correction_mps2 == 0. and pid.previous_clipped_error_mps2 == authority
  flags = {'first_sample_zero': first_zero, 'known_signed_causal_innovation': signed,
           'limiting_and_antiwindup_visible': limited, 'bounded_clipped_state': constant_clipped_zero}
  if not all(flags.values()):
    raise ValueError('TEST_ONLY_POSITIVE_CONTROL_FAILED')
  return {'scope': 'TEST_ONLY_NOT_CANDIDATE_PERFORMANCE', 'checks': flags,
          'physical_delay_owner': 'PLANT', 'gain_optimality_claim': False}

def execute(folder):
  authorize('DEVELOPMENT_SCREEN')
  if not sys.dont_write_bytecode or not sys.pycache_prefix or any(Path(sys.pycache_prefix).rglob('*.pyc')):
    raise ValueError('FRESH_SOURCE_ONLY_INTERPRETER_REQUIRED')
  folder = Path(folder)
  frozen = binding()
  payload = (json.dumps(frozen, indent=2, sort_keys=True)+'\n').encode()
  immutable_public(folder/'execution-binding.json', payload)  # MUST precede ANY run.
  controls = positive_controls()
  rows = []
  for name in scenarios():
    arms = {}
    for arm, mode in (('UPSTREAM_BASELINE', 'DISABLED'), ('CYBER_CURRENT_ALIAS', 'CURRENT_ALIAS'), ('TA_V0_CANDIDATE', 'CANONICAL_V0')):
      first, second = run_arm(name, mode), run_arm(name, mode)
      verify_binding(frozen)
      left, right = a.hash_object(first), a.hash_object(second)
      m1, m2 = metrics.evaluate(first), metrics.evaluate(second)
      if left != right or m1 != m2:
        raise ValueError('EXACT_REPEATABILITY_FAILED')
      immutable_public(folder/(name+'-'+arm+'.json'), (json.dumps(first, sort_keys=True)+'\n').encode())
      arms[arm] = {'identity_sha256': arm_identity(mode, frozen), 'trace_sha256': left, 'repeat_trace_sha256': right, 'metrics': m1,
                   'metric_sha256': a.hash_object(m1), 'repeatability': 'EXACT_PASS', 'mode': mode}
      if arm == 'UPSTREAM_BASELINE':
        baseline = first
      elif arm == 'CYBER_CURRENT_ALIAS':
        if first != baseline:
          raise ValueError('CURRENT_NOT_EXACT_ALIAS')
      else:
        arms[arm]['effect_vs_baseline'] = metrics.effects(baseline, first)
    rows.append({'scenario': name, 'arms': arms})
  verify_binding(frozen)
  report = seal({'schema': 'TRAJECTORY_V0_EXPERIMENT_RESULTS_V1', 'status': 'TA_STANDALONE_STRUCTURAL_PASS',
                 'role': 'DEVELOPMENT_SCREEN', 'execution_binding_sha256': frozen['receipt_sha256'],
                 'family': 'TA-B', 'selection_frozen_commit': '2bec29c54',
                 'scenarios': rows, 'positive_controls': controls, 'exact_repeats_per_arm': 2, 'sg_enabled': False,
                 'composed': False, 'candidate_acceptance': False, 'performance_threshold': None,
                 'threshold_status': 'THRESHOLD_UNJUSTIFIED', 'descriptive_plant_only': True})
  immutable_public(folder/'results.json', (json.dumps(report, indent=2, sort_keys=True)+'\n').encode())
  # Public summary contains only NEW synthetic metrics, no private evidence.
  immutable_public(PUBLIC/'trajectory-v0-experiment-results-v1.json', (json.dumps(report, indent=2, sort_keys=True)+'\n').encode())
  immutable_public(PUBLIC/'trajectory-v0-execution-binding-v1.json', payload)
  return report


if __name__ == '__main__':
  execute(sys.argv[1])
