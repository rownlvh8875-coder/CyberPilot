"""Independent, nonexecuting simulator integration contracts. No external code import."""

from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import future_empirical_publication as future

BASELINE = '46e41ad2f2e11cd4aee926b47d037c46d226108c'
IMPLEMENTATION_BASE = '3a3bec6f07fc7c217e4c8a024217e755be065261'
SERVICES = ('carState', 'carControl', 'carOutput')
SIGNALS = {
  'desired_curvature': '1/m; controller intent, never independent reference',
  'actual_curvature': '1/m; source/frame provenance required, unavailable stays null',
  'requested_torque': 'normalized controller request',
  'pre_limit_torque': 'normalized; explicit limiter entry, not inferred from final',
  'post_limit_torque': 'normalized post-CarController representation',
  'final_torque': 'normalized emitted command representation, not physical application',
  'torqueOutputCan': 'signed raw CAN command representation, runtime STEER_MAX bound',
  'runtime_STEER_MAX': 'raw command units; source/runtime provenance required',
  'steeringAngleDeg': 'steering-wheel degrees, measured',
  'steeringRateDeg': 'steering-wheel degrees/second, actual sample',
  'steeringPressed': 'nullable source boolean',
  'driver_torque': 'source-declared units, never guessed',
  'safety_limited': 'nullable source-proven boolean, unknown is null',
  'curvature_limited': 'nullable source-proven boolean, unknown is null',
}
BOOL_SIGNALS = ('steeringPressed', 'safety_limited', 'curvature_limited')
EVENTS = ('ORDINARY', 'INACTIVE', 'STEERING_PRESSED', 'RELEASE', 'REENGAGEMENT', 'SCENARIO_BOUNDARY', 'CONFIG_CHANGE')
ARMS = ('BASELINE', 'CURRENT', 'CANDIDATE')
VISUAL_FIELDS = (
  'requested_torque',
  'pre_limit_torque',
  'post_limit_torque',
  'pre_governor_torque',
  'post_governor_torque',
  'applied_torque',
  'steering_angle_deg',
  'desired_curvature',
  'actual_curvature',
  'heading_rad',
  'pose_x_m',
  'pose_y_m',
  'saturation_input',
  'saturation_output',
  'intervention',
)
TIERS = ('T0_REPLAY', 'T1_DESCRIPTIVE_COUNTERFACTUAL', 'T2_EMPIRICAL_PLANT_CLOSED_LOOP', 'T3_SENSOR_WORLD_CLOSED_LOOP')
NAMES = (
  'cyber-lateral-observability-contract-v1.json',
  'cyber-simulation-fidelity-contract-v1.json',
  'cyber-holdout-exposure-contract-v1.json',
  'cyber-visual-adapter-contract-v1.json',
)


def contract(schema, body):
  return p.seal(
    {
      'schema': schema,
      'status': 'CONTRACT_ONLY',
      'audit_baseline': BASELINE,
      'implementation_base': IMPLEMENTATION_BASE,
      'execution_allowed': False,
      'production_observer_implemented': False,
      'device_write_allowed': False,
      'calibration_blockers': p.BLOCKERS,
      'sealed_reference': 'NOT_GENERATED',
      'vehicle_states': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
      **body,
    }
  )


def artifacts():
  prior = future.load()
  source = {name: p.sha(Path(__file__).with_name(name).read_bytes()) for name in ('simulator_reuse_contracts.py', 'simulator_reuse_scaffolding.py')}
  common = {'scaffolding_sources': source, 'future_data_readiness_sha256': prior['future-empirical-data-readiness-v1.json']['receipt_sha256']}
  lateral = contract(
    'CYBER_LATERAL_OBSERVABILITY_CONTRACT_V1',
    {
      **common,
      'signals': SIGNALS,
      'services': list(SERVICES),
      'identity_fields': ['process_epoch', 'loop_sequence', 'config_sequence', 'config_sha256', 'consumed_input_snapshot_sha256', 'source_sha256'],
      'timing_fields': ['capture_time_ns', 'decision_time_ns', 'services.*.time_ns'],
      'service_masks': ['updated', 'alive', 'freqOk', 'valid'],
      'unavailable': 'NULL_NEVER_FALSE_ZERO_OR_INFERRED',
      'snapshot': 'SHA256 canonical full trace excluding its digest; capture <= decision; source <= capture',
      'configuration': 'canonical config digest indexed by process epoch and config sequence; collisions rejected',
      'sequence': 'contiguous from 1 per epoch; new epoch requires boundary; never reenter epoch',
      'loop_clock_order': 'within epoch capture/decision strictly increase; next capture >= prior decision; sequential loop ownership',
      'events': list(EVENTS),
      'reset': 'new epoch on process restart; config change explicit event and fresh sequence binding',
      'source_field_provenance': 'exact source adapter and units required before future observation; no generic fallback',
      'desired_curvature_role': 'CONTROLLER_INTENT_ONLY_NOT_INDEPENDENT_REFERENCE',
      'actual_curvature_role': 'SOURCE_DEFINED_RECONSTRUCTION_OR_MEASUREMENT_MUST_BE_LABELLED',
      'raw_command_is_physical_acknowledgement': False,
      'torque_stages': 'distinct nullable producer observations; no inferred prelimit/safety reason',
      'production_overlay': 'NOT_IMPLEMENTED',
      'schema_allocation': 'NO_CEREAL_FIELD_IDS_ALLOCATED',
      'synthetic_validation_only': True,
      'forbidden_inputs': ['modelV2', 'planner/path/lane independent reference', 'fused pose', 'private raw logs'],
    },
  )
  fidelity = contract(
    'CYBER_SIMULATION_FIDELITY_CONTRACT_V1',
    {
      **common,
      'tiers': {
        TIERS[0]: {'scope': 'recorded/process replay; no altered ego-feedback claim'},
        TIERS[1]: {'scope': 'descriptive plant or frozen-command counterfactual; feedback ordering explicitly labelled'},
        TIERS[2]: {
          'scope': 'empirical plant with own feedback',
          'requirements': [
            'admissible frozen empirical plant',
            'untouched holdout evaluation',
            'measured unit/frame provenance',
            'coverage domain',
            'per-arm feedback/state/delay proof',
          ],
        },
        TIERS[3]: {
          'scope': 'sensor/world feedback',
          'requirements': ['T2 requirements', 'sensor and interactive world feedback identities', 'separate calibration/reference validation'],
        },
      },
      'historical_claim_ceiling_only': {
        'native_process_replay': TIERS[0],
        'TA_B_descriptive_screen': TIERS[1],
        'SG_frozen_command_replay': TIERS[1],
        'SG_own_feedback_descriptive_loop': TIERS[1],
        'empirical_one_step_or_CV': 'NOT_SIMULATION_OR_CLOSED_LOOP_EVIDENCE',
      },
      'higher_tiers_available': False,
      'automatic_tier_promotion': False,
      'fidelity_is_vehicle_qualification': False,
      'plant_imported': False,
      'forbidden_claims': [
        'REAL_VEHICLE_STABLE',
        'VEHICLE_QUALIFIED',
        'HOLDOUT_VALIDATED_FROM_SYNTHETIC',
        'MODEL_V2_INDEPENDENT_REFERENCE',
        'TUNING_AUTHORITY',
      ],
      'historical_verdicts_reinterpreted': False,
    },
  )
  exposure = contract(
    'CYBER_HOLDOUT_EXPOSURE_CONTRACT_V1',
    {
      **common,
      'admission_contract_sha256': prior['future-holdout-opening-contract-v1.json']['receipt_sha256'],
      'context_schema_sha256': prior['empirical-causal-context-schema-v2.json']['receipt_sha256'],
      'required_binding': ['campaign_sha256', 'models', 'model_set_sha256', 'purpose', 'admission_sha256', 'metric_policy_sha256'],
      'future_journal_fields': ['opening_count', 'previous_receipt_sha256', 'opening_receipt_sha256', 'binding_sha256'],
      'opening_state': 'CLOSED',
      'opening_count': 0,
      'opening_allowed': False,
      'one_time': True,
      'reselection_allowed': False,
      'refit_after_opening_allowed': False,
      'model_set_drift': 'REJECT',
      'campaign_drift': 'REJECT',
      'purpose_drift': 'REJECT',
      'persistence': 'future private immutable atomic receipt; symlinks/overwrite forbidden',
      'current_package': 'CLOSED_MISSING_ADMISSIBLE_MODEL',
      'future_requirements': [
        'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
        'admissible frozen model before opening',
        'role assigned before numeric access',
        'new distinct source-compatible complete route',
        'prior analysis NONE; unknown rejected',
        'immutable one-time opening receipt',
      ],
      'actual_journal_or_opener_implemented': False,
    },
  )
  visual = contract(
    'CYBER_VISUAL_ADAPTER_CONTRACT_V1',
    {
      **common,
      'arms': list(ARMS),
      'field_map': dict.fromkeys(VISUAL_FIELDS, 'source-specific JSON pointer or null; never guessed'),
      'source_receipt_sha256_required': True,
      'source_schema_adapter_required': True,
      'source_scope': 'PUBLIC_SYNTHETIC_IMMUTABLE_JSON_RECEIPTS_ONLY',
      'time_grid': 'exact relative origin=0, integer dt/count identity; no interpolation/trimming',
      'reference_frame': 'DESCRIPTIVE_PLANT_COUNTERFACTUAL_ONLY; no GPS/map',
      'render_target': 'Carrot frame shape ego.pose / metrics / events with explicit Cyber lateral fields',
      'prohibited_legacy_mapping': 'steering command must never masquerade as steering-wheel degrees; lanes/planner omitted',
      'receipt_fields': ['source_receipt_sha256', 'frame_mapping_sha256', 'tier', 'blockers', 'verdict', 'coverage'],
      'host': '127.0.0.1',
      'external_assets_allowed': False,
      'optimizer_api_allowed': False,
      'server_implemented': False,
      'frames_converted': False,
      'actual_receipt_adapter_implemented': False,
      'current_frame_input': 'BLOCKED_PUBLIC_AGGREGATE_RECEIPTS_CONTAIN_TRACE_SHA_NOT_FULL_FRAMES',
      'future_SG_trace_mapping_design': {
        'pre_governor_torque': '/pre',
        'post_governor_torque': '/requested',
        'applied_torque': '/applied',
        'actual_curvature': '/curvature',
        'heading_rad': '/heading',
        'pose_x_m': '/pose_x',
        'pose_y_m': '/pose_y',
        'saturation_output': '/saturation',
        'intervention': '/intervention',
        'pre_limit_torque': None,
        'post_limit_torque': None,
        'steering_angle_deg': None,
      },
      'mapping_semantics': 'pre is native core output, NOT native pre-limit torque; curvature/heading/pose are post-step',
      'timing_semantics': 'command input at index k; descriptive plant observation k+1; preserve both phase identities',
      'private_trace_access_allowed': False,
      'required_labels': ['DESCRIPTIVE COUNTERFACTUAL ONLY', 'NOT VEHICLE QUALIFIED', 'TA-B / SG-A NOT COMPOSED'],
      'authority': 'read-only visualization never authorizes model/controller/vehicle acceptance',
    },
  )
  return dict(zip(NAMES, (lateral, fidelity, exposure, visual), strict=True))
