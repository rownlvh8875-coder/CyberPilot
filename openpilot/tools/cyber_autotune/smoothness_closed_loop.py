"""SG-A standalone own-feedback execution. No production integration or TA invocation."""

from dataclasses import asdict, dataclass
from fractions import Fraction
import json
import math
from pathlib import Path
import subprocess
import sys

from openpilot.common.pid import PIDController
from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune import smoothness_v0_metrics as metrics
from openpilot.tools.cyber_autotune import smoothness_v0_publication as historical
from openpilot.tools.cyber_autotune.candidate_role_contracts import GovernorCommand, InterventionInput, TrajectoryInput
from openpilot.tools.cyber_autotune.curvature_yaw_plant import CurvatureYawPlantState
from openpilot.tools.cyber_autotune.native_protocol import digest
from openpilot.tools.cyber_autotune.smoothness_closed_loop_policy import ARMS, PUBLIC, load as policy, seal
from openpilot.tools.cyber_autotune.smoothness_governor_v0 import Governor
from openpilot.tools.cyber_autotune.smoothness_v0_freeze import load as frozen
from openpilot.tools.cyber_autotune.smoothness_v0_screen import baseline_identity, binding as replay_binding, step, write
from openpilot.tools.cyber_autotune.trajectory_authority_core import NativeBaseline
from openpilot.tools.cyber_autotune.trajectory_v0_screen import PLANT, scenarios


def authorize(role, *, ta_enabled=False, composition=False):
  if role not in policy()['matrix']['allowed_roles'] or ta_enabled is not False or composition is not False:
    raise ValueError('SG_CLOSED_LOOP_STANDALONE_ONLY')


@dataclass(frozen=True)
class Feedback:
  owner: object
  scenario: str
  index: int
  time_s: float
  state: CurvatureYawPlantState


def native_state(core):
  pid = core.controller.pid
  row = {
    'pid': [float(getattr(pid, k)) for k in ('p', 'i', 'd', 'f', 'control')],
    'reference_buffer': list(map(float, core.controller.lat_accel_request_buffer)),
    'jerk_filter_x': float(core.controller.jerk_filter.x),
    'jerk_filter_initialized': bool(core.controller.jerk_filter.initialized),
    'sat_time': float(core.controller.sat_time),
    'prior_input': None if core._prior is None else asdict(core._prior),
    'pending_events': list(core._pending_events),
  }
  finite_tree(row)
  return row


def finite_tree(value):
  if type(value) is float and not math.isfinite(value):
    raise ValueError('NONFINITE_NATIVE_OR_PLANT_STATE')
  if isinstance(value, dict):
    for v in value.values():
      finite_tree(v)
  elif isinstance(value, (list, tuple)):
    for v in value:
      finite_tree(v)


class Arm:
  """Caller provides only frozen sample ordinal, never any feedback value."""
  def __init__(self, scenario, arm):
    authorize('DEVELOPMENT_SCREEN')
    if arm not in ARMS or scenario not in scenarios():
      raise ValueError('EXACT_FROZEN_ARM_SCENARIO_REQUIRED')
    self.scenario, self.arm = scenario, arm
    self.frames = scenarios()[scenario]
    self._frame_hashes = tuple(a.hash_object(f) for f in self.frames)
    self.core = NativeBaseline()
    self.identity = baseline_identity(self.core)
    self.governor = Governor('SG_V0_CANONICAL' if arm == ARMS[2] else 'SG_DISABLED',
                             self.identity['source_sha256'], self.identity['config_sha256'])
    self.state = CurvatureYawPlantState(0., 0., tuple(0. for _ in range(PLANT.delay_steps)))
    self.pose = (0., 0., 0.)
    self.owner = object()
    self.index = 0
    self.prior = None

  def _feedback(self):
    return Feedback(self.owner, self.scenario, self.index, self.index * .01, self.state)

  def _accept_feedback(self, token):
    if (type(token) is not Feedback or token.owner is not self.owner or token.scenario != self.scenario
        or token.index != self.index or token.time_s != self.index * .01 or token.state is not self.state):
      raise ValueError('OWN_PRE_STEP_FEEDBACK_REQUIRED')
    return token.state.curvature_1pm

  def advance(self, index):
    if type(index) is not int or index != self.index or not 0 <= index < len(self.frames):
      raise ValueError('EXACT_NEXT_SAMPLE_REQUIRED')
    if type(self.core) is not NativeBaseline or type(self.core.controller.pid) is not PIDController:
      raise ValueError('UNCHANGED_NATIVE_BASELINE_ONLY')
    frame = self.frames[index]
    if a.hash_object(frame) != self._frame_hashes[index]:
      raise ValueError('FROZEN_SCENARIO_INPUT_DRIFT')
    actual = self._accept_feedback(self._feedback())
    ti = TrajectoryInput(actual_curvature_1pm=actual, **{k: v for k, v in frame.items() if k != 'phase'})
    before = asdict(self.state)
    nb = native_state(self.core)
    u = float(self.core.update(ti)[0])
    inter = InterventionInput(ti.time_s, ti.dt_s, ti.active, ti.steering_pressed,
                              self.prior is not None and self.prior.steering_pressed and not ti.steering_pressed,
                              self.prior is not None and not self.prior.active and ti.active)
    out = self.governor.update(GovernorCommand(u, self.identity['source_sha256'], self.identity['config_sha256']), inter)
    state, pose, obs = step(self.state, out.final_requested_torque, frame, self.pose)
    result = {'index': index, 'input': asdict(ti), 'phase': frame['phase'], 'pre': u, **obs,
              'saturation': out.governor_output_saturated, 'reset_events': list(out.reset_events),
              'trace': asdict(out), 'intervention': asdict(inter),
              'plant_state_before': before, 'plant_state_after': asdict(state),
              'timing': {'sample_index': index, 'pre_state_time_s': index * .01, 'post_state_time_s': (index + 1) * .01},
              'native_state_before': nb, 'native_state_after': native_state(self.core),
              'feedback': {'source': 'OWN_PRE_STEP_PLANT', 'state_index': index, 'state_time_s': index * .01,
                           'state_sha256': a.hash_object(before), 'native_input_sha256': a.hash_object(asdict(ti))}}
    finite_tree(result)
    self.state, self.pose = state, pose
    self.prior = ti
    self.index += 1
    return result


def assert_isolated(arms):
  evolving = []
  for arm in arms:
    evolving.extend([arm, arm.core, arm.core._cp_builder, arm.core.model, arm.core.controller,
                     arm.core.controller.pid, arm.core.controller.jerk_filter, arm.core.controller.lat_accel_request_buffer,
                     arm.governor, arm.governor.timeline, arm.owner, arm.state, arm.state.command_history])
  if len({id(v) for v in evolving}) != len(evolving):
    raise ValueError('CROSS_ARM_STATE_SHARING')


def validate_trace(name, rows, arm):
  frames = scenarios()[name]
  if len(rows) != len(frames):
    raise ValueError('FULL_FROZEN_HORIZON_REQUIRED')
  state = CurvatureYawPlantState(0., 0., tuple(0. for _ in range(PLANT.delay_steps)))
  pose = (0., 0., 0.)
  if arm not in ARMS:
    raise ValueError('EXACT_EXPECTED_ARM_REQUIRED')
  core = NativeBaseline()
  identity = baseline_identity(core)
  sg = Governor('SG_V0_CANONICAL' if arm == ARMS[2] else 'SG_DISABLED', identity['source_sha256'], identity['config_sha256'])
  prior = None
  fields = {'index', 'input', 'phase', 'pre', 'requested', 'applied', 'curvature', 'yaw_rate', 'heading', 'pose_x', 'pose_y',
            'saturation', 'reset_events', 'trace', 'intervention', 'plant_state_before', 'plant_state_after', 'timing',
            'native_state_before', 'native_state_after', 'feedback'}
  for i, (frame, row) in enumerate(zip(frames, rows, strict=True)):
    if type(row) is not dict or set(row) != fields:
      raise ValueError('EXACT_CLOSED_LOOP_TRACE_SCHEMA')
    ti = TrajectoryInput(actual_curvature_1pm=state.curvature_1pm, **{k: v for k, v in frame.items() if k != 'phase'})
    inter = InterventionInput(ti.time_s, ti.dt_s, ti.active, ti.steering_pressed,
                              prior is not None and prior.steering_pressed and not ti.steering_pressed,
                              prior is not None and not prior.active and ti.active)
    if (row['index'] != i or a.hash_object(row['input']) != a.hash_object(asdict(ti))
        or a.hash_object(row['plant_state_before']) != a.hash_object(asdict(state)) or row['intervention'] != asdict(inter)):
      raise ValueError('PRE_STEP_INPUT_OR_STATE_BINDING')
    if row['timing'] != {'sample_index': i, 'pre_state_time_s': i * .01, 'post_state_time_s': (i + 1) * .01}:
      raise ValueError('PRE_POST_TIME_BINDING')
    if row['feedback'] != {'source': 'OWN_PRE_STEP_PLANT', 'state_index': i, 'state_time_s': i * .01,
                           'state_sha256': a.hash_object(asdict(state)), 'native_input_sha256': a.hash_object(asdict(ti))}:
      raise ValueError('FEEDBACK_BINDING')
    if a.hash_object(row['native_state_before']) != a.hash_object(native_state(core)):
      raise ValueError('NATIVE_PRE_STATE_BINDING')
    requested = float(core.update(ti)[0])
    if row['pre'] != requested or a.hash_object(row['native_state_after']) != a.hash_object(native_state(core)):
      raise ValueError('EXACT_OWN_FEEDBACK_NATIVE_EXECUTION_REQUIRED')
    out = sg.update(GovernorCommand(row['pre'], sg._source, sg._config), inter)
    if (row['phase'] != frame['phase'] or row['reset_events'] != list(out.reset_events)
        or type(row['saturation']) is not bool or row['saturation'] != out.governor_output_saturated):
      raise ValueError('EXACT_METRIC_MASK_PHASE_SATURATION_BINDING')
    # JSON roundtrip canonicalizes tuples; require the complete trace, not just output.
    if a.hash_object(asdict(out)) != a.hash_object(row['trace']):
      raise ValueError('GOVERNOR_TRACE_BINDING')
    state, pose, obs = step(state, out.final_requested_torque, frame, pose)
    if any(row[k] != v for k, v in obs.items()) or a.hash_object(row['plant_state_after']) != a.hash_object(asdict(state)):
      raise ValueError('EXACT_PLANT_ORDERING_REQUIRED')
    finite_tree(row)
    prior = ti

  def tv(key):
    return sum(abs(Fraction(b[key]) - Fraction(a[key])) for a, b in zip(rows, rows[1:], strict=False))
  if tv('requested') + abs(Fraction(rows[-1]['pre']) - Fraction(rows[-1]['requested'])) > tv('pre'):
    raise ValueError('LOCAL_GOVERNOR_TV_EXPANSION')
  def reversals(key):
    signs = [r[key] > 0. for r in rows if r[key] != 0.]
    return sum(a != b for a, b in zip(signs, signs[1:], strict=False))
  if reversals('requested') > reversals('pre'):
    raise ValueError('LOCAL_GOVERNOR_NEW_REVERSAL')


def run_arm(name, arm):
  runtime = Arm(name, arm)
  rows = [runtime.advance(i) for i in range(len(runtime.frames))]
  validate_trace(name, rows, arm)
  return rows


def binding():
  policies = policy()
  old = historical.load()
  rb = replay_binding()
  paths = ('smoothness_closed_loop.py', 'smoothness_closed_loop_policy.py', 'smoothness_feedback_metrics.py')
  return seal({
    'schema': 'SMOOTHNESS_CLOSED_LOOP_EXECUTION_BINDING_V1', 'status': 'FROZEN_BEFORE_ANY_CLOSED_LOOP_EXECUTION',
    'implementation_commit_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=a.ROOT, text=True).strip(),
    'policy_receipts': {k: v['receipt_sha256'] for k, v in policies.items()},
    'executor_sources': {p: digest((Path(__file__).parent / p).read_bytes()) for p in paths},
    'sg_family': 'SG-A', 'sg_config_sha256': frozen()['config']['receipt_sha256'],
    'sg_source_sha256': rb['source_sha256']['smoothness_governor_v0.py'],
    'baseline_core_identity': rb['baseline_core_identity'], 'native_support_sha256': rb['native_support_sha256'],
    'native_software_sha256': rb['native_software_sha256'], 'plant_source_sha256': rb['plant_source_sha256'],
    'plant_config': asdict(PLANT), 'environment': rb['environment'], 'environment_sha256': rb['environment_sha256'],
    'timebase_sha256': rb['timebase_sha256'], 'scenario_input_sha256': rb['scenario_input_sha256'],
    'car_params_sha256': rb['baseline_core_identity']['car_params_sha256'],
    'feedback_adapter_sha256': policies['policy']['unchanged_sources']['trajectory_authority_core.py'],
    'loop_timing_policy_sha256': policies['policy']['receipt_sha256'],
    'reset_intervention_policy_sha256': frozen()['config']['receipt_sha256'],
    'metric_policy_sha256': frozen()['metrics']['receipt_sha256'],
    'scenario_policy_sha256': frozen()['scenarios']['receipt_sha256'],
    'matrix_sha256': policies['matrix']['receipt_sha256'],
    'frozen_replay_receipt_sha256': old['results']['receipt_sha256'],
    'physical_delay_owner': 'EACH_ARM_PLANT_ONLY', 'ta_enabled': False,
    'composition_authorized': False, 'search_authorized': False})


def execute(folder, replay_folder):
  from openpilot.tools.cyber_autotune import smoothness_feedback_metrics as fm
  authorize('DEVELOPMENT_SCREEN')
  if not sys.dont_write_bytecode or not sys.pycache_prefix or any(Path(sys.pycache_prefix).rglob('*.pyc')):
    raise ValueError('FRESH_SOURCE_ONLY_INTERPRETER_REQUIRED')
  context = binding()
  folder = Path(folder)
  write(folder / 'execution-binding.json', context)
  records = []
  history = historical.load()['results']
  for name in scenarios():
    runtimes = [Arm(name, arm) for arm in ARMS]
    assert_isolated(runtimes)
    traces = {}
    arms = {}
    for arm, runtime in zip(ARMS, runtimes, strict=True):
      first = [runtime.advance(i) for i in range(800)]
      validate_trace(name, first, arm)
      second = run_arm(name, arm)
      m1, m2 = metrics.evaluate(first), metrics.evaluate(second)
      if first != second or m1 != m2:
        raise ValueError('EXACT_CLOSED_LOOP_REPEATABILITY_FAILURE')
      if binding() != context:
        raise ValueError('CLOSED_LOOP_EXECUTION_IDENTITY_DRIFT')
      write(folder / (name + '-' + arm + '.json'), first)
      arms[arm] = {'trace_sha256': a.hash_object(first), 'repeat_trace_sha256': a.hash_object(second),
                   'metric_sha256': a.hash_object(m1), 'repeat_metric_sha256': a.hash_object(m2),
                   'metrics': m1, 'repeatability': 'EXACT_PASS',
                   'diagnostics': fm.diagnostics(first)}
      traces[arm] = first
    if traces[ARMS[0]] != traces[ARMS[1]]:
      raise ValueError('CURRENT_ALIAS_MISMATCH')
    old = next(r for r in history['scenarios'] if r['scenario'] == name)
    replay = json.loads((Path(replay_folder) / (name + '-SG_V0_CANDIDATE.json')).read_bytes())
    if a.hash_object(replay) != old['arms']['SG_V0_CANDIDATE']['trace_sha256']:
      raise ValueError('HISTORICAL_REPLAY_TRACE_MISMATCH')
    # Historical metrics are READ, never recalculated. Full trace used only for aligned deltas/markers.
    records.append({'scenario': name, 'arms': arms, 'alias_exact': True,
                    'effect_vs_baseline': metrics.effects(traces[ARMS[0]], traces[ARMS[2]]),
                    'interaction': fm.compare(traces[ARMS[0]], traces[ARMS[2]], replay, old)})
  if binding() != context:
    raise ValueError('CLOSED_LOOP_EXECUTION_IDENTITY_DRIFT')
  result = seal({'schema': 'SG_A_CLOSED_LOOP_FEEDBACK_V1', 'status': 'SG_CLOSED_LOOP_STRUCTURAL_PASS',
                 'execution_binding_sha256': context['receipt_sha256'], 'execution_semantics': 'OWN_FEEDBACK_NATIVE_CORE_SG_PLANT',
                 'role': 'DEVELOPMENT_SCREEN', 'scenarios': records, 'executions': 66,
                 'repeatability': 'EXACT_PASS', 'ta_enabled': False, 'composed': False,
                 'feedback_loop_stability_proof': False, 'candidate_acceptance': False,
                 'threshold_status': 'THRESHOLD_UNJUSTIFIED', 'standalone_verdict': fm.standalone_verdict(records),
                 'feedback_interaction': fm.classify_interaction(next(r['interaction'] for r in records if r['scenario'] == 'high_speed')),
                 'composition_recommendation': 'COMPOSITION_REVIEW_POSSIBLE'
                   if (fm.standalone_verdict(records) == 'SG_CLOSED_LOOP_SCREENING_IMPROVED'
                       and fm.classify_interaction(next(r['interaction'] for r in records if r['scenario'] == 'high_speed'))
                         == 'FEEDBACK_COMPENSATES_GOVERNOR_LAG') else 'COMPOSITION_NOT_RECOMMENDED'})
  write(folder / 'results.json', result)
  write(PUBLIC / 'smoothness-closed-loop-execution-binding-v1.json', context)
  write(PUBLIC / 'smoothness-closed-loop-results-v1.json', result)
  return result


if __name__ == '__main__':
  execute(sys.argv[1], sys.argv[2])
