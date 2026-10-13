"""Exact replicas, trapped verify-only resume, aggregate-only publication."""

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_identifiability_execution as read
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_store as store
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_execution as execution
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_data as data
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_gates as gates


def repeated(output):
  auth = read.read_json(output / 'authorization.json')
  first = execution.verify_run(output / 'repeat-1', auth)
  second = execution.verify_run(output / 'repeat-2', auth)
  if first != second:
    invalid = p.seal(
      {
        'schema': 'EMPIRICAL_HURDLE_FIT_CV_REPEATABILITY_FAILURE_V1',
        'status': 'HURDLE_FIT_CV_REPEATABILITY_FAILURE',
        'selected_candidate': None,
        'selection_valid': False,
        'replica_manifests': [first['receipt_sha256'], second['receipt_sha256']],
        'preserved_replica_evidence': True,
        'holdout': 'CLOSED',
        'opening_count': 0,
        'vehicle_authority': 'NONE',
      }
    )
    store.write_json(output / 'execution-invalid.json', invalid)
    raise ValueError('HURDLE_FIT_CV_REPEATABILITY_FAILURE')
  # Manifest file hashes bind every coefficient, threshold, probability and path byte.
  with ExitStack() as stack:
    for module, names in (
      (read, ('read_array',)),
      (store, ('compressed_array_read',)),
      (data, ('load_route', 'design', 'one_step', 'rollout')),
      (m, ('fit_stage1', 'fit_stage2', 'threshold', 'probability', 'predict_delta', 'integrated', 'project', 'recursive', 'metrics')),
      (gates, ('select', 'fold_gate')),
    ):
      for name in names:
        stack.enter_context(patch.object(module, name, execution.forbidden))
    resumed = execution.verify_run(output / 'repeat-1', auth)
  if resumed != first:
    raise ValueError('HURDLE_EXACT_RESUME_FAILURE')
  value = p.seal(
    {
      'schema': 'EMPIRICAL_HURDLE_FIT_CV_REPEATABILITY_V1',
      'status': 'HURDLE_FIT_CV_EXACT_REPEATABILITY_PASS',
      'manifest_sha256': first['receipt_sha256'],
      'authorization_sha256': auth['receipt_sha256'],
      'independent_replicas': 2,
      'all_file_hashes_equal': True,
      'all_receipts_equal': True,
      'trapped_resume_exact': True,
      'scope': 'ALL_32_JOBS_MODELS_NORMALIZERS_THRESHOLDS_PREDICTIONS_PATHS_GATES_SELECTION',
      'files_per_replica': len(first['files']),
    }
  )
  store.write_json(output / 'repeatability.json', value)
  return value


def bundle(output):
  auth = read.read_json(output / 'authorization.json')
  if (output / 'execution-invalid.json').exists():
    invalid = read.read_json(output / 'execution-invalid.json')
    return {
      'empirical-hurdle-fit-cv-readiness-v1.json': invalid,
      'empirical-hurdle-selection-result-v1.json': p.seal(
        {
          'schema': 'EMPIRICAL_HURDLE_INVALID_SELECTION_V1',
          'selected_candidate': None,
          'selection_valid': False,
          'status': 'HURDLE_FIT_CV_EXECUTION_INVALID',
          'failure_sha256': invalid['receipt_sha256'],
          'holdout': 'CLOSED',
          'opening_count': 0,
        }
      ),
    }
  repeat = read.read_json(output / 'repeatability.json')
  manifest = execution.verify_run(output / 'repeat-1', auth)
  if (
    repeat['manifest_sha256'] != manifest['receipt_sha256']
    or repeat['status'] != 'HURDLE_FIT_CV_EXACT_REPEATABILITY_PASS'
    or not repeat['trapped_resume_exact']
  ):
    raise ValueError('HURDLE_VERIFIED_REPEATABILITY_REQUIRED')
  result = read.read_json(output / 'repeat-1/results.json')
  selection = read.read_json(output / 'repeat-1/selection.json')
  jobs = result['jobs']
  values = {}

  def add(name, **fields):
    values['empirical-hurdle-' + name + '-v1.json'] = p.seal(
      {
        'schema': 'EMPIRICAL_HURDLE_' + name.upper().replace('-', '_') + '_V1',
        'private_manifest_sha256': manifest['receipt_sha256'],
        'authorization_sha256': auth['receipt_sha256'],
        **fields,
      }
    )

  add(
    'fit-cv-authorization',
    head=auth['head'],
    policy_receipts=auth['policy_receipts'],
    design_readiness_sha256=auth['design_readiness_sha256'],
    source_manifest_sha256=auth['source_manifest_sha256'],
    derived_index_sha256=auth['derived_index_sha256'],
    executor_sources=auth['executor_sources'],
    blas_build_identity_sha256=auth['environment']['blas_build_identity_sha256'],
    python=auth['environment']['python'],
    numpy=auth['environment']['numpy'],
    thread_environment={'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'},
    private_array_storage=auth['private_array_storage'],
    array_access_before_seal=False,
    raw_log_openings=0,
    qlog_openings=0,
    holdout_openings=0,
  )
  add('fit-cv-job-manifest', job_count=32, jobs=[{k: j[k] for k in ('candidate_id', 'fold', 'receipt_sha256', 'status', 'population_receipts')} for j in jobs])
  # These job receipts were constructed from aggregate/opaque identity fields only.
  add('fit-cv-results', job_count=32, jobs=jobs, rate_dependency='NONE', interpretation='RETROSPECTIVE_DEVELOPMENT_ONLY')
  add(
    'stage1-results',
    jobs=[
      {
        'candidate_id': j['candidate_id'],
        'fold': j['fold'],
        'stage1': j['stage1'],
        'diagnostics': j.get('stage1_diagnostics'),
        'train_static_count': j['train_static_count'],
        'train_move_count': j['train_move_count'],
      }
      for j in jobs
    ],
  )
  add(
    'threshold-results',
    jobs=[
      {'candidate_id': j['candidate_id'], 'fold': j['fold'], 'threshold': j['threshold'], 'train_only_verified': j['train_only_threshold_verified']}
      for j in jobs
    ],
    actual_threshold_published=False,
  )
  add(
    'stage2-diagnostics',
    jobs=[
      {
        'candidate_id': j['candidate_id'],
        'fold': j['fold'],
        'stage2': j['stage2'],
        'oracle': j.get('stage2_oracle'),
        'move_only_verified': j['stage2_move_only_verified'],
      }
      for j in jobs
    ],
    oracle_role='DIAGNOSTIC_ONLY',
  )
  add(
    'candidate-gates',
    jobs=[{'candidate_id': j['candidate_id'], 'fold': j['fold'], 'gate': j['gate']} for j in jobs],
    failure_counts={c['id']: sum(not j['gate']['clauses'][i]['pass'] for j in jobs) for i, c in enumerate(jobs[0]['gate']['clauses'])},
  )
  add('selection-result', selection=selection, historical_s2ri_verdict='S2_RI_NO_ADMISSIBLE_CANDIDATE')
  add('fit-cv-repeatability', repeatability=repeat)
  old = store.contracts()['fitting-policy-readiness']
  preserved = {
    key: old[key]
    for key in (
      'S1',
      'S2',
      'S3',
      'dataset',
      'historical_track',
      'stage_b',
      'ta',
      'sg',
      'composition',
      'search',
      'final_pooled_refit',
      'future_holdout',
      'calibration_blockers',
      'sealed_reference',
      'vehicle',
      'historical_verdict',
      'historical_selection',
      'historical_attribution',
      'closed_loop_bias',
      'no_model_admitted',
    )
  }
  add(
    'fit-cv-readiness',
    **preserved,
    status=execution.SUCCESS,
    states=[
      execution.SUCCESS,
      '32_FOLD_JOBS_ACCOUNTED',
      'HURDLE_FIT_CV_EXACT_REPEATABILITY_PASS',
      *(['THRESHOLD_TRAIN_ONLY_VERIFIED'] if all(j['train_only_threshold_verified'] for j in jobs) else []),
      *(['STAGE2_MOVE_ONLY_VERIFIED'] if all(j['stage2_move_only_verified'] for j in jobs) else []),
      *selection['states'],
    ],
    move_gate_fitting='RUN_RETROSPECTIVE_ONLY',
    conditional_delta_fitting='RUN_RETROSPECTIVE_ONLY',
    threshold_selection='RUN_TRAIN_ONLY',
    cv_scoring='RUN_RETROSPECTIVE_ONLY',
    model_selection='RETROSPECTIVE_ONLY' if selection['admissible_count'] else 'FAILED_CLOSED',
    holdout='CLOSED',
    opening_count=0,
    vehicle_authority='NONE',
    pooled_refit_run=False,
    raw_log_openings=0,
    qlog_openings=0,
    holdout_discovery=0,
    interpretation='RETROSPECTIVE_ROUTE_LEVEL_DEVELOPMENT',
    family_verdict='FROZEN_HURDLE_RI_V1_FAILED_RETROSPECTIVE_GATE' if not selection['admissible_count'] else 'RETROSPECTIVE_CONFIGURATION_SELECTED',
  )
  validate_public(values)
  return values


def validate_public(values):
  forbidden_keys = {
    'value',
    'coefficients',
    'nominal_coefficients',
    'mean',
    'std',
    'private_build_metadata',
    'train_probability',
    'p_move',
    'predicted_gate',
    'projected_path',
    'observed_path',
    'target_next_tick',
    'current_tick',
    'command_current',
    'command_history',
    'timestamp',
    'gps',
  }

  def visit(value):
    if isinstance(value, dict):
      if set(value) & forbidden_keys:
        raise ValueError('HURDLE_PUBLIC_PRIVATE_VALUE_FORBIDDEN')
      for item in value.values():
        visit(item)
    elif isinstance(value, list):
      for item in value:
        visit(item)
    elif isinstance(value, str) and (value.startswith(('/home/', '/mnt/', 'C:', 'D:'))):
      raise ValueError('HURDLE_PUBLIC_PRIVATE_PATH_FORBIDDEN')

  visit(values)
  p.canonical(values)


def publish(output, public=p.PUBLIC):
  values = bundle(output)
  for name, value in values.items():
    store.write_json(Path(public) / name, value)
  return values
