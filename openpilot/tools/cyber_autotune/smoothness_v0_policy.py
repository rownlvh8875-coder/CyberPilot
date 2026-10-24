"""Source-only SG selection/config freeze. No algorithm/result inputs."""
import json

from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune import trajectory_v0_publication as ta
from openpilot.tools.cyber_autotune.trajectory_v0_freeze import load as ta_policies
from openpilot.tools.cyber_autotune.native_protocol import digest
from openpilot.tools.cyber_autotune.resolution_candidate_evidence import immutable_public

BASELINE = '53506f2af49ab52490482d3961044f33b7360235'
PUBLIC = a.ROOT/'docs/cyberpilot/changes'
FILES = {'policy': 'smoothness-family-selection-policy-v1.json', 'selection': 'smoothness-family-selection-v1.json',
  'config': 'smoothness-v0-config-v1.json', 'metrics': 'smoothness-metric-execution-policy-v1.json',
  'scenarios': 'smoothness-development-scenarios-v1.json', 'matrix': 'candidate-experiment-matrix-sg-v1.json'}


def seal(row):
  body = {**row, 'source_baseline_sha': BASELINE, 'qualification_allowed': False, 'reference_promotable': False,
          'sealed_reference_allowed': False, 'vehicle_activation_allowed': False, 'production_authority': False}
  return {**body, 'receipt_sha256': a.hash_object(body)}


def build():
  prior = ta.load()
  old = ta_policies()
  sources = {p: digest((a.ROOT/p).read_bytes()) for p in (
    'openpilot/tools/cyber_autotune/candidate_role_contracts.py',
    'openpilot/tools/cyber_autotune/candidate_architecture.py',
    'openpilot/tools/cyber_autotune/candidate_architecture_policy.py',
    'openpilot/tools/cyber_autotune/trajectory_authority_core.py',
    'openpilot/selfdrive/controls/lib/latcontrol_torque.py',
    'openpilot/tools/cyber_autotune/smoothness_v0_policy.py')}
  policy = seal({'schema': 'SMOOTHNESS_FAMILY_SELECTION_POLICY_V1', 'status': 'FROZEN_BEFORE_IMPLEMENTATION',
    'families': ['SG-A', 'SG-B', 'SG-C', 'SG-D'], 'result_input_allowed': False, 'one_family_only': True,
    'criteria': ['command_intervention_only', 'no_physical_queue', 'minimal_state', 'exact_reset',
                 'bounded_no_expansion', 'steady_unity', 'no_new_sign_changes', 'no_bias',
                 'source_canonical_config', 'tracking_phase_cost_disclosed', 'not_arbitrary_scale'],
    'source_bindings': sources, 'existing_ta_receipts': {k: v['receipt_sha256'] for k, v in prior.items()}})
  selection = seal({'schema': 'SMOOTHNESS_FAMILY_SELECTION_V1', 'status': 'SG_A_SELECTED',
    'selected_family': 'SG-A', 'policy_sha256': policy['receipt_sha256'],
    'mechanism': 'UNIT_DELTA_PROJECTOR', 'candidate_results_used': False,
    'reason': 'Normalized authority radius1 supplies a geometric step; only opposing commands can differ by >1 within [-1,1]',
    'counterevidence': ['small chatter passes unchanged',
      'p95 derivative can rise despite lower peak and nonincreasing total variation', 'no physical rate justification or guarantee',
      'large reversal may require one additional sample', 'phase/plant tracking cost must be disclosed',
      'frozen command replay cannot establish feedback-loop stability'],
    'alternatives': [
      {'family': 'SG-B', 'reason': 'No independently justified general slew rate; adds arbitrary tracking cost'},
      {'family': 'SG-C', 'reason': 'No canonical time constant; generic low pass and persistent tail unwanted'},
      {'family': 'SG-D', 'reason': 'No justified deadband; potential steady bias'}]})
  config = seal({'schema': 'SMOOTHNESS_V0_CONFIG_V1', 'family': 'SG-A', 'unit_delta': 1., 'dt_s': .01,
    'unit_delta_basis': 'Minimum radius guaranteeing zero in every previous-output interval; design projection, NOT physical actuator slew limit',
    'allowed_configs': ['SG_DISABLED', 'SG_V0_CANONICAL', 'SG_TEST_ONLY_POSITIVE_CONTROL'],
    'state_fields': ['last_command'], 'state_owner': 'SG', 'state_role': 'COMMAND_SHAPING_STATE',
    'projection': 'clip(current_input, last_output-1, last_output+1); fresh=current_input',
    'physical_delay_owner': 'PLANT', 'physical_queue_allowed': False,
    'inactive': 'require baseline input exact zero; clear last_command; output exact zero',
    'pressed': 'clear stale state; current input exact passthrough; rebase last_command',
    'release_reengagement': 'clear stale state; current input exact passthrough; rebase last_command',
    'reset_events': a.EVENTS, 'reset_ownership': a.RESETS,
    'config_change_scenario_boundary': 'NEW_INSTANCE_ONLY',
    'timeline': 'contiguous .01s including interventions; explicit events must equal observed boolean transitions',
    'invariants': ['finite_bounded', 'abs_output<=abs_input', 'between_previous_output_and_input', 'constant_unity',
                   'no_new_sign_reversal', 'no_integrator', 'no_tail_on_zero'],
    'tv_claim': 'TV(output)+abs(input_final-output_final)<=TV(input), full contiguous fresh episode; event passthrough included',
    'ordinary_step_bound': 'abs(output[k]-output[k-1])<=1 ONLY ordinary projection samples; event passthrough exempt',
    'enabled_output': 'Additive SG_STANDALONE_OUTPUT_V1; original disabled-only FinalOfflineTorqueCommand unchanged',
    'search_allowed': False, 'composition_allowed': False})
  metrics = seal({'schema': 'SMOOTHNESS_METRIC_EXECUTION_POLICY_V1', 'status': 'FROZEN_BEFORE_EXECUTION',
    'base_trajectory_metric_policy_sha256': old['metrics']['receipt_sha256'],
    'base_trajectory_metrics': 'Reuse pinned source implementation, same phase/lag/distance/coverage semantics; separate new receipt',
    'dt_s': .01, 'derivative': 'backward adjacent finite .01s pairs; PRIMARY includes all interventions/reset boundaries',
    'secondary_mask': 'active not pressed contiguous pairs, never join gaps/resets; disclose separately',
    'quantiles': 'numpy linear p50/p90/p95/max; RMS separately; no weighted score',
    'zero_crossing': 'strict adjacent product<0; exact zero touch is not direct crossing',
    'sign_reversal': 'remove exact zeros within contiguous series, count nonzero sign changes',
    'spectrum': {'window': 'demeaned Hann on full contiguous command stream', 'band_hz': [1.2, 50.],
                 'band_basis': 'existing native jerk cutoff and 100Hz Nyquist', 'energy': 'sum |rFFT|^2/N^2'},
    'saturation': 'CORE_INPUT_SATURATED=abs(input)==1; OUTPUT=abs(output)==1; LIMIT_ACTIVE=output!=input',
    'saturation_transitions': 'adjacent boolean change; never infer native prelimit intent',
    'events': {'offset_samples_inclusive': [0, 99], 'expected_support': 100,
               'mask': 'all finite samples; boundary jump separately recorded'},
    'settling': 'exact final constant-input run; first sample after which output==constant input for remainder; no tolerance threshold',
    'steady_bias': 'mean(output-input) on final constant-input run, disclose length and absent run',
    'lag': old['metrics']['lag'], 'phases': old['metrics']['phases'], 'distance': old['metrics']['distance'],
    'contiguous': 'strict index/time order; gaps rejected', 'minimum_support': {'distribution': 1, 'derivative': 2, 'spectrum': 4},
    'coverage': 'valid/total/unavailable everywhere; empty=null, n<3 small_support',
    'floating_tolerance': {'time_abs_s': 1e-12, 'repeatability': 'EXACT_CANONICAL_JSON', 'sign_zero': 'EXACT_ZERO'},
    'performance_threshold': None, 'threshold_status': 'THRESHOLD_UNJUSTIFIED'})
  scenarios = seal({'schema': 'SMOOTHNESS_DEVELOPMENT_SCENARIOS_V1', 'status': 'FROZEN_BEFORE_EXECUTION',
    'rows': old['scenarios']['rows'], 'ta_scenario_receipt_sha256': old['scenarios']['receipt_sha256'],
    'source': 'REUSE_EXOGENOUS_INPUTS_ONLY_NOT_TA_OUTPUT_OR_RESULT',
    'baseline_generation': 'Direct NativeBaseline feedback from its own descriptive plant; freeze native command stream BEFORE three-arm replay',
    'candidate_feedback': 'NO_SG_PLANT_FEEDBACK_TO_CORE; identical frozen baseline core commands to all arms',
    'limitation': 'Command replay descriptive plant counterfactual, not SG-in-feedback controller stability evidence'})
  matrix = seal({'schema': 'CANDIDATE_EXPERIMENT_MATRIX_SG_V1',
    'arms': ['UPSTREAM_BASELINE', 'CYBER_CURRENT_ALIAS', 'SG_V0_CANDIDATE'], 'repeats': 2,
    'current_is_exact_baseline_alias': True, 'allowed_roles': ['ARCHITECTURE_PROBE', 'DEVELOPMENT_SCREEN'],
    'search_authorized': False, 'composition_authorized': False, 'ta_enabled': False,
    'frozen_evaluation_authorized': False, 'candidate_acceptance_authorized': False,
    'config_sha256': config['receipt_sha256'], 'metric_policy_sha256': metrics['receipt_sha256'],
    'scenario_policy_sha256': scenarios['receipt_sha256'], 'historical_verdicts': dict(a.HISTORY)})
  return {'policy': policy, 'selection': selection, 'config': config, 'metrics': metrics, 'scenarios': scenarios, 'matrix': matrix}


def validate(rows):
  if rows != build():
    raise ValueError('EXACT_PRE_EXECUTION_SG_POLICY_REQUIRED')
  return rows


def write_new():
  for key, row in build().items():
    immutable_public(PUBLIC/FILES[key], (json.dumps(row, indent=2, sort_keys=True)+'\n').encode())


if __name__ == '__main__':
  write_new()
