"""Additive SG-A own-feedback policy. Freeze before implementation and execution."""

import json

from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune import smoothness_v0_publication as historical
from openpilot.tools.cyber_autotune.native_protocol import digest
from openpilot.tools.cyber_autotune.resolution_candidate_evidence import immutable_public
from openpilot.tools.cyber_autotune.smoothness_v0_freeze import load as frozen

BASELINE = 'cd5561b6c8ee568917fc6a5d2c53a6396d4544fe'
PUBLIC = a.ROOT / 'docs/cyberpilot/changes'
FILES = {'policy': 'smoothness-closed-loop-policy-v1.json', 'matrix': 'smoothness-closed-loop-matrix-v1.json'}
ARMS = ('UPSTREAM_BASELINE_CLOSED_LOOP', 'CYBER_CURRENT_ALIAS_CLOSED_LOOP', 'SG_A_V0_CLOSED_LOOP')


def seal(body):
  row = {**body, 'source_baseline_sha': BASELINE, 'qualification_allowed': False, 'reference_promotable': False,
         'sealed_reference_allowed': False, 'vehicle_activation_allowed': False, 'production_authority': False}
  return {**row, 'receipt_sha256': a.hash_object(row)}


def build():
  old = frozen()
  past = historical.load()
  paths = ('smoothness_governor_v0.py', 'smoothness_v0_baseline.py', 'smoothness_v0_metrics.py',
           'smoothness_v0_screen.py', 'trajectory_v0_screen.py', 'trajectory_authority_core.py',
           'trajectory_v0_metrics.py', 'curvature_yaw_plant.py', 'candidate_role_contracts.py')
  policy = seal({
    'schema': 'SMOOTHNESS_CLOSED_LOOP_EXECUTION_POLICY_V1', 'status': 'FROZEN_BEFORE_IMPLEMENTATION_AND_EXECUTION',
    'dt_s': .01, 'samples': 800, 'scenario_rows': old['scenarios']['rows'],
    'scenario_policy_sha256': old['scenarios']['receipt_sha256'], 'sg_config_sha256': old['config']['receipt_sha256'],
    'metric_policy_sha256': old['metrics']['receipt_sha256'], 'intervention_policy_sha256': old['config']['receipt_sha256'],
    'frozen_replay_receipt_sha256': past['results']['receipt_sha256'],
    'historical_receipts': {k: v['receipt_sha256'] for k, v in past.items()},
    'unchanged_sources': {p: digest((a.ROOT / 'openpilot/tools/cyber_autotune' / p).read_bytes()) for p in paths},
    'feedback_source': 'SAME_ARM_PRE_STEP_PLANT_STATE_ONLY',
    'ordering': ['provide_frozen_exogenous_input_k', 'read_own_plant_state_k',
                 'update_own_unchanged_native_core_k', 'baseline_current_exact_passthrough',
                 'sg_arm_only_existing_canonical_governor', 'deliver_post_command_to_own_plant',
                 'advance_own_delay_curvature_yaw_pose_to_k_plus_1', 'next_core_reads_same_arm_state_k_plus_1'],
    'feedback_token': 'instance-local owner, exact next index and current plant state; no caller-supplied feedback API',
    'isolation': 'new exact NativeBaseline, Governor, plant state/delay tuple and pose per arm/repeat/scenario',
    'feedback_adapter': 'same NativeBaseline VehicleModel reconstruction all arms; no extra physical delay',
    'physical_delay_owner': 'EACH_ARM_PLANT_ONLY', 'sg_state': 'unchanged last_command only',
    'reset': 'unchanged native and SG event policy; new instances for scenario/config boundary',
    'blocks': {'quarter_ranges_half_open': [[0, 200], [200, 400], [400, 600], [600, 800]],
               'constant_tail_blocks': 3, 'constant_tail_block_samples': 100,
               'equivalence': 'exact exogenous desired/speed/roll/active/pressed/limit sequence equality',
               'growth': 'strict increase of absolute peak and RMS across equivalent blocks; descriptive flag only',
               'unequal_input_blocks': 'report values; growth attribution unavailable',
               'state_drift': 'report first/last native PID, reference buffer, jerk filter, saturation timer; no convergence claim'},
    'boundedness': 'source-derived per-step triangle recurrence envelope on curvature/yaw/heading/pose; finite only, not asymptotic stability',
    'bound_rounding': 'round each nonnegative envelope toward +infinity with math.nextafter; no fitted tolerance',
    'stability_proof': False, 'finite_horizon_status': 'FINITE_HORIZON_CLOSED_LOOP_STABILITY_DIAGNOSTIC',
    'primary_metrics': 'reuse existing exact metric implementation and policy; do not redefine windows or masks',
    'comparison': 'existing immutable aggregate and trace SHA only; do not rerun or re-evaluate historical replay',
    'pose_comparison': 'same-time peak and observed-monotonic-x interpolation separated; no extrapolation or meter-envelope classification',
    'high_speed_markers': 'first exact inequality in own stage; feedback/curvature pre/post timestamps explicit; phase uses frozen phase metrics',
    'interaction_rule': {
      'compensates': 'high-speed tracking p95 <= baseline AND phase absolute lag not higher on all identified common supports',
      'amplifies': 'high-speed tracking p95 > replay AND common identified phase lag cost not lower; contradictory evidence => mixed',
      'preserves': 'high-speed tracking p95 > baseline and <= replay; other axes still separate',
      'artifact': 'closed-loop SG trace exactly baseline while replay has nonzero effect',
      'otherwise': 'MIXED_OR_UNRESOLVED',
      'no_numeric_threshold': True},
    'hard_failures': ['nonfinite', 'source_bound_violation', 'command_contract', 'wrong_feedback_source', 'future_feedback',
                      'cross_arm_state', 'duplicate_delay', 'alias_mismatch', 'repeatability', 'source_config_metric_drift',
                      'ta_input', 'composition', 'search', 'production_mutation'],
    'screening_improved': 'all affected smoothness axes nonworse, tracking/phase/coverage nonworse and no contradictory direction; else tradeoff',
    'composition': 'recommendation only; never authorization',
    'performance_threshold': None, 'threshold_status': 'THRESHOLD_UNJUSTIFIED',
  })
  matrix = seal({
    'schema': 'SMOOTHNESS_CLOSED_LOOP_MATRIX_V1', 'arms': ARMS, 'repeats': 2,
    'current_exact_alias': True, 'allowed_roles': ['ARCHITECTURE_PROBE', 'DEVELOPMENT_SCREEN'],
    'source': 'UNCHANGED_NATIVE_BASELINE', 'sg_mode': 'SG_V0_CANONICAL',
    'policy_sha256': policy['receipt_sha256'], 'ta_enabled': False, 'composition_authorized': False,
    'search_authorized': False, 'frozen_evaluation_authorized': False, 'candidate_acceptance_authorized': False})
  return {'policy': policy, 'matrix': matrix}


def validate(rows):
  if rows != build():
    raise ValueError('EXACT_PRE_EXECUTION_CLOSED_LOOP_POLICY_REQUIRED')
  return rows


def load():
  return validate({k: json.loads((PUBLIC / name).read_bytes()) for k, name in FILES.items()})


if __name__ == '__main__':
  for key, row in build().items():
    immutable_public(PUBLIC / FILES[key], (json.dumps(row, sort_keys=True, indent=2) + '\n').encode())
