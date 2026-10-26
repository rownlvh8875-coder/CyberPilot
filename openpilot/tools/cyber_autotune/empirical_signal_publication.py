"""Immutable redacted provenance evidence. No private extraction on import."""

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_signal_run as r

PINS = {
  'empirical-signal-provenance-adjudication-v1.json': '337a44c7fc945f091260fd4af8b8315ffcd175b540669e76c4f4cf577e4d7aa5',
  'empirical-command-bridge-v1.json': '272f6b3823d20007b7bfe0dfb935685b3ad7dcee89ae5e70cc3bf788331dd69f',
  'empirical-gyro-crosscheck-v1.json': 'b1754320646ce256fb1d056671b4a4d8b131862894f2f01e22c6f9cd04379db0',
  'empirical-kinematic-yaw-crosscheck-v1.json': 'eb70e459275d8d5511791c6d540c58c367107dfd1832d3d0e31caccbc04cfd3d',
  'empirical-limit-observability-v1.json': '0e3723e530855ee1666cc6002f5a740860c75f78582144b047a8fd0ec6cbbbbc',
  'empirical-signal-provenance-readiness-v1.json': '1c5ec9186e649f15efd3c7dabdd8ff61da242e122e66de8ba2dd02ad0c4e52b8',
  'empirical-two-stage-readiness-v1.json': 'c880ea0ce50f2bfae6c392976116559f2f8cce8e130d716bf2f2e4b83bc7fc96',
  'empirical-yaw-family-policy-v1.json': 'ed3c4d3f5eb59ac7c8cc4213825e91042224db65f3d775129240194142ab563d',
  'empirical-yaw-holdout-validation-v1.json': '43aad47d90d2889666e1ecb3207b9678e98295928ac91fcc8e1c3d6797e81896',
  'empirical-yaw-hypothesis-policy-v1.json': '6e7bafc60c6ff3181ee948a1111dfd59f3660a018601ba927d32307a27393147',
  'empirical-yaw-selection-v1.json': '7c66341a6711c0b5ff8df4cd5337a120aac1b763267237741102ce2a3bbfeb28',
  'empirical-yaw-source-audit-v1.json': 'bf903fa6f10ceaa0fd4529436f151f110580dd98ac8b43610886f0289a487f08',
  'empirical-yaw-verdict-v1.json': 'fcfb05bbadb007731bf089a6fa13203479bf18d7d931f6be0aeab6fc3d4130d3',
}
EXECUTORS = {
  'empirical_signal_policy.py': 'adcc374cbc0886464d9eb47c786deec37e6436adac6901b403ec71c3e992bc90',
  'empirical_signal_reader.py': '17d16ec35d8cfd968f189dab7bccc6e71ecaa23694c39d9e1f72ec32f66854fa',
  'empirical_signal_crosscheck.py': '890ab0222b2ac5a0e40a4fc24d1ba7343ee810a265eaae66c18cd12994b85b1f',
  'empirical_plant_policy.py': '3961101927faca0e64a731ff92484d563082390c001988a156056275743034df',
  'empirical_plant_signals.py': '0f018b5682f9309f3a913f0e1e8fac6a4a487b2de036c1dadeb50b3ee4a5effd',
  'empirical_plant_model.py': 'd412012da7a3d3f077b7ecb2c9c9efe64040596d57a64b5b5e46d2d8508bb44a',
  'empirical_plant_run.py': 'd0d8d310d978cc6da022759584601aaa584e8bb1f12e13901df108bb05e07dda',
  'empirical_plant_publication.py': 'ecabb2a847241b57c8c0bb3a525936ef47ec78c68c891ae7fc67dd4def064ad7',
  'empirical_signal_run.py': '840a5ce1df4d621ff92e5ee63afd9727423954e46ed320feeee45c90e386a236',
}


def validate_sources():
  r.historical()
  if r.source_identity() != EXECUTORS:
    raise ValueError('IMMUTABLE_PROVENANCE_EXECUTOR_DRIFT')


def validate_row(name, row):
  p.verify(row)
  if name not in PINS or row['receipt_sha256'] != PINS[name]:
    raise ValueError('IMMUTABLE_PROVENANCE_PUBLIC_RECEIPT_DRIFT')
  if name in r.shapes():
    r.publication_guard(name, row)
  elif name == 'empirical-yaw-hypothesis-policy-v1.json':
    if row != r.q.policy():
      raise ValueError('IMMUTABLE_HYPOTHESIS_POLICY_DRIFT')
  elif name != ADJUDICATION:
    r.source_gate(row)
  return row


def load():
  validate_sources()
  rows = {name: validate_row(name, r.read(p.PUBLIC / name)) for name in PINS}
  bindings = {row['binding_sha256'] for name, row in rows.items() if name in r.shapes()}
  if len(bindings) != 1:
    raise ValueError('ONE_PROVENANCE_EXECUTION_REQUIRED')
  return rows


ADJUDICATION = 'empirical-signal-provenance-adjudication-v1.json'


def derive_adjudication(rows):
  inputs = {name: row['receipt_sha256'] for name, row in rows.items() if name != ADJUDICATION}
  for name in inputs:
    validate_row(name, rows[name])
  selection = rows['empirical-yaw-selection-v1.json']['selection']
  records = [record for group in selection.values() for record in group['candidate_dispositions']]
  if any(group['selected_config'] is not None for group in selection.values()) or any(record['fit_status'] != 'INSUFFICIENT_SUPPORT' for record in records):
    raise ValueError('ADJUDICATION_ONLY_FOR_FROZEN_UNFITTED_GENERATION')
  readiness = rows['empirical-signal-provenance-readiness-v1.json']
  gyro = rows['empirical-gyro-crosscheck-v1.json']
  return p.seal(
    {
      'schema': 'EMPIRICAL_SIGNAL_PROVENANCE_ADJUDICATION_V1',
      'status': 'CONSERVATIVE_INTERPRETATION_OF_FROZEN_OUTPUTS',
      'input_receipts': inputs,
      'command_bridge': readiness['command_bridge'],
      'yaw_signal': 'EMPIRICAL_YAW_SIGNAL_PARTIAL',
      'yaw_verdict': 'YAW_UNIT_LIKELY_NOT_CONFIRMED',
      'raw_policy_unit_gate': 'MAGNITUDE_DOMINANCE_ONLY_NOT_DYNAMIC_CORRESPONDENCE',
      'axis_correspondence_established': False,
      'independent_unit_confirmation': False,
      'vehicle_frame_calibrated': False,
      'gyro_correlation_by_role': {role: row['gyro']['CORRELATION'] for role, row in gyro['roles'].items()},
      'kinematic_support': 'DEG_PER_SECOND_HYPOTHESIS_SUPPORT_ONLY_NOT_TRUTH',
      'yaw_model': 'EMPIRICAL_YAW_MODEL_BLOCKED',
      'model_reason': 'BLOCKED_NO_CONTIGUOUS_SUPPORT',
      'raw_model_verdict_preserved': readiness['yaw_model'],
      'max_training_design_rows': max(record['train_count'] for record in records),
      'minimum_training_design_rows': 201,
      'development_model_scoring_performed': False,
      'development_support_count': None,
      'development_zero_is_placeholder_not_measured_support': True,
      'holdout_model_evaluation_performed': False,
      'fitted_coefficients_available': False,
      'model_reselected': False,
      'threshold_changed': False,
      'stage_a': 'EMPIRICAL_ACTUATOR_MODEL_ONLY_UNCHANGED',
      'stage_c': 'BLOCKED_STAGE_A_AND_YAW_ADMISSION',
      'full_plant_ready': False,
      'calibration_blockers': p.BLOCKERS,
      'sealed_reference': 'NOT_GENERATED',
      'vehicle': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
      'next_generation': 'NEW_ROUTE_SPLIT_AND_PREDECLARED_GAP_SUPPORT_POLICY_REQUIRED_NO_SAME_HOLDOUT_REFIT',
    }
  )
