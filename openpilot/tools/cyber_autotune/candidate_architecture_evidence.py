"""Build additive public architecture receipts from source and existing public identities only."""
from dataclasses import asdict
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune import candidate_architecture_policy as policy
from openpilot.tools.cyber_autotune import candidate_architecture_probe as probe
from openpilot.tools.cyber_autotune import candidate_role_contracts as c
from openpilot.tools.cyber_autotune.controller_plant_publication import load
from openpilot.tools.cyber_autotune.native_protocol import digest
from openpilot.tools.cyber_autotune.resolution_candidate_evidence import immutable_public

PUBLIC = a.ROOT / 'docs/cyberpilot/changes'
FILES = {
  'decision': 'candidate-architecture-decision-v1.json',
  'trajectory': 'trajectory-authority-contract-v1.json',
  'smoothness': 'smoothness-governor-contract-v1.json',
  'composed': 'composed-candidate-contract-v1.json',
  'matrix': 'candidate-experiment-matrix-v1.json',
  'probe': 'candidate-architecture-probe-v1.json',
  'readiness': 'candidate-architecture-readiness-v1.json',
}


def seal(row):
  body = {**row, 'qualification_allowed': False, 'production_authority': False,
          'vehicle_activation_allowed': False, 'sealed_reference_allowed': False,
          'actual_algorithm_implemented': False, 'parameter_search_allowed': False,
          'source_baseline_sha': a.BASELINE}
  body.pop('receipt_sha256', None)
  return {**body, 'receipt_sha256': a.hash_object(body)}


def injection_points():
  torque = 'openpilot/selfdrive/controls/lib/latcontrol_torque.py'
  worker = 'openpilot/tools/cyber_autotune/curvature_yaw_native_worker.py'
  rows = (
    ('desired_curvature', '1/m', 'EXPERIMENT', 'TA', 'FROZEN_SYNTHETIC_DEMAND_ONLY; production model input not imported', torque, 'update'),
    ('actual_curvature', '1/m', 'FEEDBACK_ADAPTER', 'TA', 'explicit simulated measurement, never hidden plant state', worker, 'execute_request'),
    ('VehicleModel_reconstruction', 'rad,deg,1/m', 'FEEDBACK_ADAPTER', 'FEEDBACK_ADAPTER',
     '-VM.calc_curvature(radians(angle-offset),speed,roll)', worker, 'execute_request'),
    ('feedforward', 'm/s^2 upstream; normalized equivalent only if observed', 'TA', 'TA', 'desired_curvature*v^2 minus roll*g and offset', torque, 'update'),
    ('PID_error', 'm/s^2 upstream', 'TA', 'TA', 'error/integrator and causal reference buffer', torque, 'update'),
    ('friction', 'm/s^2 upstream', 'TA', 'TA', 'get_friction is factor-scaled; no lane information', torque, 'update'),
    ('roll_compensation', 'rad -> m/s^2', 'EXPERIMENT', 'TA', 'roll*g, source provenance explicit', torque, 'update'),
    ('normalized_conversion', 'normalized [-1,1]', 'TA', 'TA', 'negative return torque, existing CI conversion', torque, 'update'),
    ('output_limiting', 'm/s^2 upstream', 'TA', 'TA', 'PID limits before torque conversion; pre-limit intent not historically saved',
     'openpilot/common/pid.py', 'PIDController.update'),
    ('saturation_bookkeeping', 's,bool', 'TA', 'TA', 'saturation timer is distinct from clipping and SG state',
     'openpilot/selfdrive/controls/lib/latcontrol.py', '_check_saturation'),
    ('inactive_reset', 'bool,s', 'EXPERIMENT', 'TA', 'stock controlsd invokes reset; base reset clears sat_time only',
     'openpilot/selfdrive/controls/controlsd.py', 'state_control'),
    ('steeringPressed', 'bool', 'EXPERIMENT', 'TA_AND_SG_DISTINCT_STATES',
     'upstream freezes integrator; future standalone reset policy explicitly fresh', torque, 'update'),
    ('driver_override', 'normalized driver torque/raw counts', 'EXPERIMENT', 'RAW_ACTUATOR_LIMITER', 'offline input only; raw limiter not executed',
     'opendbc_repo/opendbc/car/hyundai/carcontroller.py', 'update'),
    ('raw_Hyundai_boundary', 'raw counts', 'RAW_ACTUATOR_LIMITER', 'RAW_ACTUATOR_LIMITER', 'round(STEER_MAX*u); driver/rate/fault checks; not executed',
     'opendbc_repo/opendbc/car/hyundai/carcontroller.py', 'update'),
    ('plant_input', 'normalized [-1,1]', 'SG_OUTPUT_ADAPTER', 'PLANT', 'plant command=-requested; applied=-delayed command; sole physical delay',
     'openpilot/tools/cyber_autotune/curvature_yaw_plant.py', 'observe_curvature_yaw_step'),
  )
  return [{'boundary': name, 'units': unit, 'input_owner': inp, 'output_owner': out, 'semantics': meaning,
           'state_owner': out if out in ('TA', 'PLANT') else 'NO_NEW_CONTROLLER_STATE',
           'update_hz': 100., 'dt_s': .01, 'symbol': symbol,
           'scope': 'READ_ONLY_SOURCE_AUDIT_PRODUCTION_UNMODIFIED',
           'source_path': path, 'source_sha256': digest((a.ROOT / path).read_bytes()),
           'source_commit_sha': '4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76' if path.startswith('opendbc_repo/') else a.BASELINE}
          for name, unit, inp, out, meaning, path, symbol in rows]


def build():
  prior = load()
  a.validate_ownership(a.OWNERS)
  a.validate_resets(a.RESETS)
  a.validate_matrix(a.matrix())
  sources = {name: digest((Path(__file__).parent / name).read_bytes()) for name in
             ('candidate_architecture.py', 'candidate_role_contracts.py', 'candidate_architecture_policy.py',
              'candidate_architecture_probe.py', 'candidate_architecture_evidence.py')}
  decision = seal({'schema': 'CANDIDATE_ARCHITECTURE_DECISION_V1', 'status': 'ARCHITECTURE_DEFINED',
                   'selected_approach': 'B_CASCADED_CORE_PLUS_GOVERNOR',
                   'alternatives': [
                     {'approach': 'A_PARALLEL_WRAPPERS', 'decision': 'NOT_SELECTED',
                      'benefit': 'isolated roles', 'cost': 'duplicate LatControlTorque logic; composition unclear'},
                     {'approach': 'B_CASCADED_CORE_PLUS_GOVERNOR', 'decision': 'SELECTED',
                      'benefit': 'observable boundary and distinct state/config identity',
                      'cost': 'governor phase lag and reset discipline require standalone validation'},
                     {'approach': 'C_SINGLE_MULTI_OBJECTIVE', 'decision': 'NOT_SELECTED',
                      'benefit': 'integrated implementation', 'cost': 'role attribution and tradeoff concealment'}],
                   'injection_points': injection_points(), 'sources': sources,
                   'state_ownership': a.OWNERS, 'reset_ownership': a.RESETS,
                   'timing_owner': 'EXPERIMENT_100HZ', 'physical_delay_owner': 'PLANT',
                   'composition': 'TA -> narrow GovernorCommand -> SG -> existing offline plant adapter',
                   'authority_boundary': 'OFFLINE_ONLY_NO_RUNTIME_HOOK',
                   'historical_authority_audit_sha256': prior['audit']['receipt_sha256'],
                   'historical_findings_sha256': prior['findings']['receipt_sha256'],
                   'historical_readiness_sha256': prior['readiness']['receipt_sha256'],
                   'historical_verdicts': dict(a.HISTORY), 'historical_candidate_role': 'MIXED_HISTORICAL_NO_RETROACTIVE_RECLASSIFICATION'})
  common = {'state_ownership': a.OWNERS, 'reset_policy': a.RESETS, 'timing_owner': 'EXPERIMENT',
            'dt_s': .01, 'enabled_implementation_authorized': False, 'detectability_states': a.DETECTABILITY,
            'identity_context': 'native software and CarParams are historical first-index baseline reference, NOT executed by new probe',
            'identity_environment': 'current pure Python probe execution, NOT historical native environment',
            'plant_lifecycle': 'retain physical state/queue through interventions; config changes require a new experiment',
            'historical_pre_limit_intent': None, 'historical_signal_reconstruction_allowed': False}
  trajectory = seal({'schema': 'TRAJECTORY_AUTHORITY_CONTRACT_V1', **common,
                     'input_schema': a.schema(c.TrajectoryInput), 'output_schema': a.schema(c.TrajectoryAuthorityOutput),
                     'input_whitelist_unknown_rejected': True, 'families': policy.families(),
                     'families_algorithm_selection': 'NOT_SELECTED',
                     'allowed_mechanisms': ['causal_curvature_tracking', 'phase_response', 'bounded_error_history', 'speed_conditioned_dynamics'],
                     'forbidden': ['lane_truth', 'modelV2', 'planner_path', 'candidate_output', 'future_truth',
                                   'hidden_plant_state', 'arbitrary_scale_bias', 'governor_command_shaping', 'posthoc_acceptance_fit'],
                     'observability': ['pre_limit_intent', 'raw_requested_torque_POST_CONTROLLER_LIMIT',
                                       'tracking_error', 'feedforward_component', 'feedback_component', 'friction_component', 'saturation_intent'],
                     'observability_unavailable': 'NULL_WITH_UNAVAILABLE_STATUS_NO_ZERO_FILL',
                     'causality': 'current_or_past_timestamp_only; no future feedback',
                     'structural_checks': ['determinism', 'sign_consistency', 'amplitude_ordering', 'no_nonfinite', 'fresh_reset_no_leak'],
                     'metrics': policy.metrics('TA'), 'cross_objective_hard_constraints': policy.metrics('SG'),
                     'verdict_catalog': policy.VERDICTS['TA'], 'search_policy': a.search_policy('TA'),
                     'identity': asdict(a.identity('TA', {'status': 'ALGORITHM_PENDING'}))})
  smoothness = seal({'schema': 'SMOOTHNESS_GOVERNOR_CONTRACT_V1', **common,
                    'input_schema': {'command': a.schema(c.GovernorCommand), 'intervention': a.schema(c.InterventionInput)},
                    'output_schema': a.schema(c.FinalOfflineTorqueCommand), 'input_whitelist_unknown_rejected': True,
                    'forbidden': ['desired_curvature', 'tracking_target', 'lane', 'modelV2', 'path', 'hidden_delay_queue', 'physical_actuator_model'],
                    'state_fields': ['last_command', 'reversal_state', 'intervention_state'],
                    'state_semantics': 'COMMAND_SHAPING_STATE_NOT_PHYSICAL_ACTUATOR_DELAY',
                    'time_constant_s': None, 'maximum_retained_memory_s': None, 'phase_effect': 'IMPLEMENTATION_PENDING_MUST_MEASURE_TRACKING_TRADEOFF',
                    'pending_state_parameters_block_enabled_execution': True,
                    'inactive_behavior': 'FRESH_INSTANCE; disabled passthrough is diagnostic only',
                    'steering_pressed_behavior': 'FRESH_INSTANCE; no implicit state carry',
                    'observability': ['pre_governor', 'post_governor', 'final_requested_torque', 'saturation_reason'],
                    'structural_checks': ['determinism', 'stronger_shaping_ordering', 'phase_lag_and_tracking_tradeoff', 'no_nonfinite', 'no_leak'],
                    'metrics': policy.metrics('SG'), 'cross_objective_hard_constraints': policy.metrics('TA'),
                    'verdict_catalog': policy.VERDICTS['SG'], 'search_policy': a.search_policy('SG'),
                    'identity': asdict(a.identity('SG', a.governor_config()))})
  composed = seal({'schema': 'COMPOSED_CANDIDATE_CONTRACT_V1', 'status': 'COMPOSITION_NOT_AUTHORIZED',
                   'composed_implementation_authorized': False, 'pipeline': ['TA', 'SG', 'EXISTING_OFFLINE_COMMAND_PATH'],
                   'trajectory_contract_sha256': trajectory['receipt_sha256'], 'governor_contract_sha256': smoothness['receipt_sha256'],
                   'requirements': a.readiness()['architecture_track']['COMPOSITION'],
                   'shared_mutable_state_allowed': False, 'second_physical_delay_allowed': False,
                   'verdict_catalog': policy.VERDICTS['COMPOSED']})
  matrix = seal(a.matrix())
  controls = seal(probe.run())
  readiness = seal({**a.readiness(), 'contracts': {'decision': decision['receipt_sha256'], 'trajectory': trajectory['receipt_sha256'],
                                                 'smoothness': smoothness['receipt_sha256'], 'composed': composed['receipt_sha256'],
                                                 'matrix': matrix['receipt_sha256'], 'probe': controls['receipt_sha256']},
                    'reference_blocker_graph': prior['readiness']['blockers'],
                    'reference_blocker_graph_sha256': a.hash_object(prior['readiness']['blockers']),
                    'historical_reference_readiness_sha256': prior['readiness']['receipt_sha256']})
  return {'decision': decision, 'trajectory': trajectory, 'smoothness': smoothness,
          'composed': composed, 'matrix': matrix, 'probe': controls, 'readiness': readiness}


def write_new(folder):
  """Create-once receipts. Reruns may verify byte equality, never overwrite."""
  folder = Path(folder)
  folder.mkdir(parents=True, exist_ok=True)
  for key, row in build().items():
    payload = (json.dumps(row, indent=2, sort_keys=True) + '\n').encode()
    path = folder / FILES[key]
    immutable_public(path, payload)


def validate(reports):
  """Exact schemas/content; resealing a changed policy does not authorize it."""
  if type(reports) is not dict or a.hash_object(reports) != a.hash_object(build()):
    raise ValueError('EXACT_ARCHITECTURE_CONTRACT_SET_REQUIRED')
  return reports
