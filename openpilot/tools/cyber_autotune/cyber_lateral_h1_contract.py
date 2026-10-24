"""Offline H1 V1 extension; immutable simulator contracts remain authoritative."""

from pathlib import Path

from openpilot.tools.cyber_autotune.native_protocol import SOURCE_FILES

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import simulator_reuse_publication as reuse

BASE = 'dd054f21443fbe02ee2fb585b76bec070bb56269'
DT_NS = 10_000_000  # Existing frozen 100 Hz experiment grid.
DECISION_TICK_NS = 1  # Logical phase ordinal, NOT measured computation/actuator latency.
SCENARIO = 'driver_events'
TIER = 'T1_DESCRIPTIVE_COUNTERFACTUAL'
EVENTS = ('ORDINARY', 'INACTIVE', 'STEERING_PRESSED', 'RELEASE', 'REENGAGEMENT', 'SCENARIO_BOUNDARY', 'CONFIG_CHANGE')
SERVICES = ('carState', 'carControl', 'carOutput')
INPUTS = (
  'desired_curvature_1pm',
  'actual_curvature_1pm',
  'speed_mps',
  'roll_rad',
  'time_s',
  'dt_s',
  'active',
  'steering_pressed',
  'safety_limited',
  'curvature_limited',
)
INPUT_MAP = {
  'desired_curvature': 'desired_curvature_1pm',
  'actual_curvature': 'actual_curvature_1pm',
  'speed_mps': 'speed_mps',
  'roll_rad': 'roll_rad',
  'active': 'active',
  'steeringPressed': 'steering_pressed',
  'safety_limited': 'safety_limited',
  'curvature_limited': 'curvature_limited',
}
UNAVAILABLE = {
  'requested_torque': 'PRE_LIMIT_NATIVE_INTENT_NOT_OBSERVED',
  'pre_limit_torque': 'PRE_LIMIT_NATIVE_INTENT_NOT_OBSERVED',
  'torqueOutputCan': 'NO_CARCONTROLLER_OR_CAN_IN_OFFLINE_EXPERIMENT',
  'steering_angle_deg': 'NO_MEASURED_STEERING_SENSOR_IN_DESCRIPTIVE_PLANT',
  'steering_rate_deg_s': 'NO_MEASURED_STEERING_RATE_IN_DESCRIPTIVE_PLANT',
  'driver_torque': 'NO_DRIVER_TORQUE_SENSOR_IN_SYNTHETIC_SCENARIO',
}
PROVENANCE = {
  'desired_curvature': 'FROZEN_SCENARIO_CONTROLLER_INTENT_NOT_REFERENCE',
  'actual_curvature': 'OWN_DESCRIPTIVE_PLANT_PRE_STEP_NATIVE_INPUT',
  'requested_torque': 'UNAVAILABLE_PRE_LIMIT_NATIVE_INTENT',
  'pre_limit_torque': 'UNAVAILABLE_PRE_LIMIT_NATIVE_INTENT',
  'controller_limited_torque': 'NATIVE_BASELINE_RETURN_NORMALIZED_POST_CONTROLLER_LIMIT',
  'pre_governor_torque': 'NATIVE_BASELINE_RETURN_NOT_PRE_LIMIT_INTENT',
  'post_governor_torque': 'EXISTING_DISABLED_GOVERNOR_EXACT_PASSTHROUGH',
  'final_requested_torque': 'NORMALIZED_PLANT_REQUEST_NOT_PHYSICAL_ACK',
  'applied_torque': 'DESCRIPTIVE_PLANT_DELAYED_COMMAND_POST_STEP_NOT_EPS_ACK',
  'torqueOutputCan': 'UNAVAILABLE_LOGGED_REPRESENTATION_WOULD_NOT_PROVE_PHYSICAL_ACK',
  'steering_angle_deg': 'UNAVAILABLE_MEASURED_SENSOR',
  'steering_rate_deg_s': 'UNAVAILABLE_MEASURED_SENSOR',
  'speed_mps': 'FROZEN_SCENARIO_INPUT_MPS',
  'roll_rad': 'FROZEN_SCENARIO_INPUT_RAD',
  'active': 'FROZEN_SCENARIO_INPUT',
  'steeringPressed': 'FROZEN_SCENARIO_INPUT',
  'driver_torque': 'UNAVAILABLE_MEASURED_SENSOR',
  'safety_limited': 'EXPLICIT_SYNTHETIC_SCENARIO_FLAG_NOT_VEHICLE_SAFETY_OBSERVATION',
  'curvature_limited': 'EXPLICIT_SYNTHETIC_SCENARIO_FLAG_NOT_VEHICLE_LIMIT_OBSERVATION',
  'saturation_state': 'EXACT_NORMALIZED_OUTPUT_RAIL_OCCUPANCY_NOT_EPS_SATURATION',
}
BOOLS = ('active', 'steeringPressed', 'safety_limited', 'curvature_limited', 'saturation_state')
TORQUES = ('controller_limited_torque', 'pre_governor_torque', 'post_governor_torque', 'final_requested_torque', 'applied_torque')
ROW_FIELDS = (
  'schema',
  'sample_index',
  'process_epoch',
  'loop_sequence',
  'config_sequence',
  'config_sha256',
  'source_sha256',
  'experiment_sha256',
  'capture_time_ns',
  'decision_time_ns',
  'completion_time_ns',
  'dt_ns',
  'consumed_input_snapshot',
  'consumed_input_snapshot_sha256',
  'native_input_sha256',
  'signals',
  'provenance',
  'unavailable',
  'service_health',
  'plant_output',
  'event',
  'reset_events',
  'row_sha256',
)
OWN_FILES = ('cyber_lateral_h1_contract.py', 'cyber_lateral_h1_producer.py', 'cyber_lateral_h1_experiment.py', 'cyber_lateral_h1_inspector.py')
EXPERIMENT_FILES = (
  'smoothness_closed_loop.py',
  'smoothness_closed_loop_policy.py',
  'smoothness_v0_screen.py',
  'smoothness_governor_v0.py',
  'trajectory_authority_core.py',
  'trajectory_v0_screen.py',
  'candidate_role_contracts.py',
  'curvature_yaw_plant.py',
)


def sources():
  root = Path(__file__).resolve().parents[3]
  relative = ['openpilot/tools/cyber_autotune/' + name for name in (*OWN_FILES, *EXPERIMENT_FILES)]
  relative += list(SOURCE_FILES) + [
    'opendbc_repo/opendbc/car/hyundai/values.py',
    'opendbc_repo/opendbc/car/torque_data/params.toml',
    'opendbc_repo/opendbc/car/torque_data/substitute.toml',
    'opendbc_repo/opendbc/car/torque_data/override.toml',
  ]
  result = {}
  for name in relative:
    path = root / name
    if path.is_symlink():
      raise ValueError('H1_SOURCE_SYMLINK')
    result[name] = p.sha(path.read_bytes())
  return result


def service_health():
  return {
    name: {'time_ns': None, 'updated': None, 'alive': None, 'freqOk': None, 'valid': None, 'unavailable_reason': 'SYNTHETIC_DIRECT_CALL_NO_MESSAGE_BUS'}
    for name in SERVICES
  }


def schema():
  return p.seal(
    {
      'schema': 'CYBER_LATERAL_H1_SCHEMA_V1',
      'trace_schema': 'CYBER_LATERAL_H1_TRACE_V1',
      'row_fields': list(ROW_FIELDS),
      'signal_provenance': PROVENANCE,
      'unavailable_fields': UNAVAILABLE,
      'native_input_fields': list(INPUTS),
      'consumed_snapshot_fields': ['native_input', 'source_time_ns', 'service_health'],
      'consumed_snapshot_excludes_outputs': True,
      'row_digest_includes_outputs': True,
      'services': service_health(),
      'events': list(EVENTS),
      'units': {
        'curvature': '1/m',
        'torque': 'normalized',
        'steering_angle': 'steering-wheel deg',
        'steering_rate': 'steering-wheel deg/s',
        'speed': 'm/s',
        'roll': 'rad',
        'clock': 'relative ns',
      },
      'historical_contract_sha256': reuse.PINS['cyber-lateral-observability-contract-v1.json'],
      'extension_reason': 'Versioned actual offline trace with separate consumed-input and complete-row digests; no historical schema mutation',
      'no_cereal_ids': True,
      'missing_is_null': True,
      'production_observer_implemented': False,
    }
  )


def policy():
  source = sources()
  return p.seal(
    {
      'schema': 'CYBER_LATERAL_H1_POLICY_V1',
      'baseline': BASE,
      'scenario': SCENARIO,
      'arm': 'UPSTREAM_BASELINE_CLOSED_LOOP',
      'governor': 'SG_DISABLED',
      'samples': 800,
      'dt_ns': DT_NS,
      'decision_tick_ns': DECISION_TICK_NS,
      'clock': 'DETERMINISTIC_EXPERIMENT_RELATIVE_NOT_WALL_CLOCK',
      'ordering': [
        'capture_own_pre_step_input_k',
        'native_baseline_update_k',
        'disabled_passthrough_k',
        'descriptive_plant_step_k_to_k_plus_1',
        'detached_observation_no_feedback',
      ],
      'completion': 'plant_output.state_time_ns = capture + dt; not consumed by current native update',
      'input_digest': 'canonical consumed_input_snapshot only; outputs excluded',
      'row_digest': 'canonical complete row excluding row_sha256',
      'schema_sha256': schema()['receipt_sha256'],
      'sources': source,
      'source_sha256': p.sha(p.canonical(source)),
      'producer_sha256': source['openpilot/tools/cyber_autotune/cyber_lateral_h1_producer.py'],
      'fidelity': TIER,
      'raw_access_allowed': False,
      'holdout_opening': 'CLOSED',
      'opening_count': 0,
      'holdout_opener_implemented': False,
      'production_observer_implemented': False,
      'observer_feedback_allowed': False,
      'calibration_blockers': p.BLOCKERS,
      'historical_reuse_pins': reuse.PINS,
    }
  )


def binding(experiment_sha, source_sha, count):
  return {
    'experiment_sha256': experiment_sha,
    'source_sha256': source_sha,
    'expected_rows': count,
    'data_class': 'SYNTHETIC_ONLY',
    'tier': TIER,
    'dt_ns': DT_NS,
  }
