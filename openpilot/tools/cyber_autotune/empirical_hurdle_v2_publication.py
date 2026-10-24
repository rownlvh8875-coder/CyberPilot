"""Allowlisted aggregate publication from verified V2 runs; no private numbers."""

from pathlib import Path
import argparse
import json

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_io as io
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_execution as execution

PREFIX = 'empirical-hurdle-stage1-v2-'
LABELS = (
  'execution-authorization',
  'job-manifest',
  'threshold-results',
  'train-results',
  'development-results',
  'rollout-results',
  'candidate-gates',
  'v1-comparison',
  'selection-result',
  'repeatability',
  'retrospective-execution-readiness',
  'execution-validation',
)
FORBIDDEN_KEYS = {
  'value',
  'coefficients',
  'nominal_coefficients',
  'mean',
  'std',
  'private_build_metadata',
  'current_tick',
  'target_next_tick',
  'p_move',
  'predicted_gate',
  'projected_path',
  'actual_threshold',
}


def privacy(value, key=''):
  if isinstance(value, dict):
    io.require(not FORBIDDEN_KEYS.intersection(value), 'V2_PUBLIC_PRIVATE_VALUE_FORBIDDEN')
    for name, item in value.items():
      privacy(item, name)
  elif isinstance(value, list):
    for item in value:
      privacy(item, key)
  elif isinstance(value, str):
    io.require(not any(s in value for s in ('/mnt/', '/home/', 'C:\\', 'D:\\', 'C:/', 'D:/', 'file://')), 'V2_PUBLIC_PRIVATE_PATH_FORBIDDEN')
  if key == 'threshold':
    io.require(isinstance(value, dict), 'V2_PUBLIC_THRESHOLD_NUMBER_FORBIDDEN')


VALIDATION_CHECKS = (
  'focused',
  'combined_empirical',
  'full_autotune_controls',
  'lateral_replay',
  'ruff',
  'compileall',
  'json',
  'publication',
  'diff_check',
  'scons',
  'independent_review',
)


def validate_checks(validation):
  io.require(isinstance(validation, dict) and set(validation) == set(VALIDATION_CHECKS), 'V2_VALIDATION_SCHEMA_REQUIRED')
  for check in validation.values():
    io.require(isinstance(check, dict) and set(check) == {'status', 'tests', 'subtests'}, 'V2_VALIDATION_SCHEMA_REQUIRED')
    io.require(check['status'] == 'PASS' and all(type(check[k]) is int and check[k] >= 0 for k in ('tests', 'subtests')), 'V2_COMPLETED_VALIDATION_REQUIRED')
  return validation


def build(output, validation):
  validate_checks(validation)
  auth = io.read_json(output / 'authorization.json')
  first = execution.trapped_resume(output / 'repeat-1', auth)
  repeated = io.read_json(output / 'repeatability.json')
  io.require(repeated['status'] == 'V2_EXACT_REPEATABILITY_PASS' and repeated['run1_manifest_sha256'] == first['receipt_sha256'])
  result = io.read_json(output / 'repeat-1/results.json')
  selected = io.read_json(output / 'repeat-1/selection.json')
  jobs = result['jobs']

  def rows(*keys):
    return [{k: job[k] for k in ('candidate_id', 'fold', *keys) if k in job} for job in jobs]

  failures = {clause['id']: sum(not job['gate']['clauses'][i]['pass'] for job in jobs) for i, clause in enumerate(jobs[0]['gate']['clauses'])}
  original = io.read_json(p.PUBLIC / 'empirical-hurdle-stage1-v2-execution-readiness.json', io.READY_SHA)
  states = [
    execution.SUCCESS,
    '32_V2_FOLD_JOBS_ACCOUNTED',
    'V1_MODEL_BYTES_REUSED_EXACTLY',
    'V2_THRESHOLD_TRAIN_ONLY_VERIFIED',
    'V2_EXACT_REPEATABILITY_PASS',
    'V2_VERIFY_ONLY_RESUME_PASS',
    *selected['states'],
  ]
  bodies = {
    'execution-authorization': {
      'authorization_sha256': auth['receipt_sha256'],
      'head': auth['head'],
      'execution_policy_sha256': io.POLICY_SHA,
      'design_policy_sha256': auth['design_policy_sha256'],
      'v1_manifest_sha256': io.verified.SOURCE_SHA,
      'source_manifest_sha256': auth['source_manifest_sha256'],
      'derived_index_sha256': auth['derived_index_sha256'],
      'derived_result_sha256': auth['derived_result_sha256'],
      'executor_sources': auth['executor_sources'],
      'environment': {k: v for k, v in auth['environment'].items() if k != 'private_build_metadata'},
      'capacity_preflight': auth['capacity_preflight'],
      'job_count': 32,
    },
    'job-manifest': {
      'jobs': rows('status', 'failures', 'receipt_sha256', 'models', 'train_anchor_sha256'),
      'job_count': 32,
      'private_manifest_sha256': first['receipt_sha256'],
    },
    'threshold-results': {'jobs': rows('threshold'), 'decision': 'MOVE_IFF_P_GREATER_THAN_THRESHOLD'},
    'train-results': {'jobs': rows('train_count', 'train_metrics')},
    'development-results': {'jobs': rows('one_step', 'true_move', 'stage1_diagnostics', 'static_diagnostics')},
    'rollout-results': {'jobs': rows('rollout'), 'horizons': [25, 50, 100, 200]},
    'candidate-gates': {'jobs': rows('status', 'gate'), 'failure_counts': failures, 'clauses_per_fold': 32},
    'v1-comparison': {
      'jobs': rows('train_comparison', 'comparison'),
      'authority': 'REPORT_ONLY',
      'interpretation': 'THRESHOLD_POLICY_ISOLATED_RETROSPECTIVE_COMPARISON',
    },
    'selection-result': {'selection': selected, 'historical_v1': ['HURDLE_NO_ADMISSIBLE_CANDIDATE', 'MODEL_SELECTION_FAILED_CLOSED']},
    'repeatability': {'repeatability': repeated},
    'retrospective-execution-readiness': {
      'status': execution.SUCCESS,
      'states': states,
      'job_count': 32,
      'private_manifest_sha256': first['receipt_sha256'],
      'selected_candidate': selected['selected_candidate'],
      'admissible_count': selected['admissible_count'],
      'stage1_refit_calls': 0,
      'stage2_refit_calls': 0,
      'normalizer_refit_calls': 0,
      'threshold_selection': 'RUN_TRAIN_ONLY',
      'prediction': 'RUN_RETROSPECTIVE_ONLY',
      'rollout': 'RUN_RETROSPECTIVE_ONLY',
      'policy_readiness_preserved_sha256': original['receipt_sha256'],
      'stage2_caveat': 'STAGE2_LONG_HORIZON_RESIDUAL_RISK_REMAINS',
      'historical_v1': ['HURDLE_NO_ADMISSIBLE_CANDIDATE', 'MODEL_SELECTION_FAILED_CLOSED', 'FROZEN_HURDLE_RI_V1_FAILED_RETROSPECTIVE_GATE'],
      'preserved_authority': {
        key: original[key]
        for key in (
          'dataset',
          'S1',
          'S2',
          'S3',
          'historical_track',
          'stage_b',
          'ta',
          'sg',
          'composition',
          'future_holdout',
          'calibration_blockers',
          'sealed_reference',
          'vehicle',
          'closed_loop_bias',
          'historical_verdict',
          'historical_selection',
          'historical_s2_ri_verdict',
          'historical_attribution',
          'historical_design_trigger',
          'no_model_admitted',
          'search',
          'final_pooled_refit',
          'holdout',
          'holdout_state',
          'opening_count',
          'vehicle_authority',
          'stage2_residual_risk',
        )
      },
    },
    'execution-validation': {
      'validation': validation,
      'repeatability_sha256': repeated['receipt_sha256'],
      'historical_tracked_artifacts': 'UNCHANGED_ADDITIVE_ONLY',
    },
  }
  common = {
    'family': 'HURDLE_RI_V1',
    'decision_policy': 'HURDLE_STAGE1_DECISION_POLICY_V2',
    'change_scope': 'THRESHOLD_OBJECTIVE_ONLY',
    'model_strategy': 'REUSE_BYTE_IDENTICAL_V1_FITTED_MODELS',
    'final_pooled_refit': 'NOT_AUTHORIZED',
    'holdout': 'CLOSED',
    'opening_count': 0,
    'holdout_discovery': 0,
    'model_admission': 'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT',
    'vehicle_authority': 'NONE',
    'vehicle': ['NOT_READY', 'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED'],
  }
  bundle = {PREFIX + k + '.json': p.seal({'schema': 'EMPIRICAL_HURDLE_STAGE1_V2_' + k.upper().replace('-', '_'), **common, **v}) for k, v in bodies.items()}
  for value in bundle.values():
    privacy(value)
  return bundle


def publish(output, validation):
  bundle = build(output, validation)
  # Preflight every target before publication; never overwrite V1 or policy.
  for name, value in bundle.items():
    target = p.PUBLIC / name
    if target.exists():
      io.require(json.loads(target.read_bytes()) == value, 'V2_IMMUTABLE_PUBLICATION_CONFLICT')
  for name, value in bundle.items():
    io.write_json(p.PUBLIC / name, value)
  return bundle


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output', type=Path, required=True)
  parser.add_argument('--validation', type=Path, required=True)
  a = parser.parse_args()
  result = publish(a.output, json.loads(a.validation.read_bytes()))
  print(json.dumps({'artifacts': len(result)}))


if __name__ == '__main__':
  main()
