"""Additive S2-RI design contracts. No fitting policy or runtime controller."""
import json
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_final_readiness as final
from openpilot.tools.cyber_autotune import empirical_s2_ri_math as m

PINS = {
  'empirical-steering-rate-semantics-v1.json': '109bc9159d06db8ba696922b93a7dea5d5f265f2bbc0dcbf4d22aade51e2f388',
  'empirical-source-grid-emission-policy-v1.json': '77d99c602047b7bda5a47e8ac6d5c869884d049bac9dcc397b05fdde98876339',
  'empirical-model-family-identifiability-readiness-v1.json': 'a9c6e3cb39aa498bdbdd2f42f249d5a5e351d623bab51047838c651b838a31f4',
}
AUTHORITY = dict.fromkeys(('fitting', 'selection', 'prediction', 'residual', 'cv_scoring', 'optimizer', 'candidate',
                          'rollout', 'raw_opening', 'qlog_support', 'holdout_opening', 'ta', 'sg', 'composition',
                          'production', 'device', 'vehicle'), False)
MODULES = ('policy', 'math', 'admission', 'execution', 'publication', 'schema')


def historical():
  x = final.load()
  for name, digest in PINS.items():
    path = p.PUBLIC/name
    if any(v.is_symlink() for v in (path, *path.parents)):
      raise ValueError('NO_SYMLINK_HISTORICAL_INPUT')
    v = p.verify(json.loads(path.read_bytes()))
    if v['receipt_sha256'] != digest:
      raise ValueError('HISTORICAL_S2_RI_INPUT_DRIFT')
    x[name] = v
  return x


def validate_model_spec(spec):
  text = json.dumps(spec, sort_keys=True).lower().replace('_', '').replace('.', '')
  if any(name in text for name in ('steeringrate', 'staterate', 'ratenative', 'sasspeed')):
    raise ValueError('S2_RI_RATE_DEPENDENCY_FORBIDDEN')
  expected = {'features': ['logged_normalized_command_history', 'past_angle_tick_increments',
                          'current_angle_tick', 'current_speed_mps', 'intercept'],
              'target': 'MEASURED_ANGLE_GRID_INCREMENT_PER_SAMPLE'}
  if spec != expected:
    raise ValueError('EXACT_S2_RI_MODEL_SPEC_REQUIRED_NO_FUTURE_OR_EXTRA_FEATURES')
  return spec


def contracts():
  x = historical()
  ids = sorted(r['route_id'] for r in x[final.RLOG_ROUTES]['routes'])
  source = x['empirical-steering-rate-semantics-v1.json']
  oldgrid = x['empirical-source-grid-emission-policy-v1.json']
  spec = validate_model_spec({'features': ['logged_normalized_command_history', 'past_angle_tick_increments',
                                         'current_angle_tick', 'current_speed_mps', 'intercept'],
                              'target': 'MEASURED_ANGLE_GRID_INCREMENT_PER_SAMPLE'})
  bodies = {
    'signal': {'schema': 'EMPIRICAL_S2_RI_SIGNAL_CONTRACT_V1', 'family': 'S2_RI_V1', **spec,
      'name': 'RATE_INDEPENDENT_DELTA_ANGLE_CAUSAL_MODEL', 'steering_rate_dependency': 'NONE',
      'semantic_boundary': 'LOGGED_COMMAND_REPRESENTATION_TO_MEASURED_STEERING_WHEEL_ANGLE_CHANGE',
      'command': 'LOGGED_POST_CARCONTROLLER_NORMALIZED_COMMAND', 'command_source': 'carOutput.actuatorsOutput.torque',
      'raw_command': 'PROVENANCE_ONLY_NOT_FEATURE', 'controller_request': 'CONTEXT_ONLY_NOT_FEATURE',
      'physical_eps': 'PHYSICAL_EPS_APPLICATION_UNAVAILABLE', 'transaction': 'REQUEST_OUTPUT_TRANSACTION_LINK_UNAVAILABLE',
      'angle': source['angle'], 'source_contract_sha256': source['receipt_sha256'],
      'source_files': {k: source['files'][k] for k in ('dbc', 'parser', 'carstate', 'controller', 'card')},
      'units': {'command': 'NORMALIZED_LOGGED_REPRESENTATION', 'angle': 'SIGNED_INTEGER_SOURCE_TICKS',
                'past_increment': 'SIGNED_SOURCE_GRID_STEPS_PER_SAMPLE_NOT_PHYSICAL_RATE', 'speed': 'M_PER_S', 'intercept': 'DIMENSIONLESS'},
      'driver_torque_feature': False, 'speed_interaction': False, 'speed_bin_models': False},
    'angle-grid': {'schema': 'EMPIRICAL_S2_RI_ANGLE_GRID_V1', 'step_deg': .1, 'offset_deg': 0.,
      'codes': [-32768, 32767], 'source': 'SAS11.SAS_Angle', 'status': 'SOURCE_PROVEN_0P1_DEG',
      'validation': 'FINITE_SIGNED16_CODE_FLOAT64_TIMES_POINT_ONE_FLOAT32_THEN_EXACT_FLOAT64_EQUALITY',
      'invalid': 'ANGLE_SOURCE_GRID_INCONSISTENT', 'tolerance': None, 'clipping': False,
      'target_replacement': False, 'prediction_executed': False,
      'emission_rule': oldgrid['grid'], 'historical_emission_policy_sha256': oldgrid['receipt_sha256'],
      'reuse': 'GENERIC_RULE_DEFINITION_ONLY_NOT_HISTORICAL_MODEL_RESULT_OR_EXECUTION',
      'future_channels': ['LATENT_CONTINUOUS_DELTA_PREDICTION', 'SOURCE_GRID_NEXT_ANGLE_PROJECTION'],
      'future_next_angle': 'NEXT_ANGLE_DEG=FLOAT64_POINT_ONE*(CURRENT_TICK+CONTINUOUS_DELTA_TICK);THEN_HISTORICAL_DEGREE_GRID_RULE',
      'rollout_state_semantics': 'PENDING_SEPARATE_FITTING_POLICY',
      'historical_verdict': 'SOURCE_GRID_OBSERVATION_REJECTED'},
    'target': {'schema': 'EMPIRICAL_S2_RI_TARGET_CONTRACT_V1', 'name': spec['target'],
      'equation': 'delta_tick[k]=angle_tick[k+1]-angle_tick[k]', 'dtype': 'INT64_EXACT',
      'conditions': ['SAME_ROUTE', 'SAME_RLOG_SEGMENT', 'SAME_CAUSAL_RUN', 'NEXT_EXACT_10_MS_GRID',
                     'BOTH_ROWS_ELIGIBLE_SOURCE_GRID', 'NO_RESET_GAP_OR_INTERVENTION'],
      'last_run_or_segment_row': 'UNAVAILABLE_NO_PADDING', 'physical_rate': False,
      'target_values_in_X': False, 'distribution_changes': 'NO_JITTER_SMOOTHING_INTERPOLATION_DEQUANTIZATION_OR_REWEIGHTING'},
    'history-reset': {'schema': 'EMPIRICAL_S2_RI_HISTORY_RESET_V1',
      'equation': 'y[k]=beta0+sum(a_i*u[k-d-i])+sum(b_j*delta_tick[k-j])+c*angle_tick[k]+s*vEgo[k]',
      'past_delta_j_starts_at': 1, 'command_offset_semantics': 'COMMAND_HISTORY_OFFSET_SAMPLES_NOT_PHYSICAL_DELAY',
      'allowed_envelope': {'d': [0, 20], 'L_u': [1, 45], 'L_delta': [1, 45]},
      'boundary_forms': [list(f) for f in m.FORMS], 'scopes': list(m.SCOPES),
      'selected_d': None, 'selected_L_u': None, 'selected_L_delta': None, 'selected_scope': None,
      'reset': ['ROUTE', 'SEGMENT', 'CAUSAL_RUN_BREAK', 'GAP', 'INACTIVE', 'STEERING_PRESSED', 'EPS_FAULT',
                'REENGAGEMENT_HISTORY_RESET'],
      'history': 'EVERY_ROW_ELIGIBLE_SAME_RUN_NO_PADDING_NO_CARRY_NO_FUTURE_SOURCE',
      'candidate_set': 'CANDIDATE_SET_MUST_BE_PREDECLARED_BEFORE_FITTING'},
    'route-cv': {'schema': 'EMPIRICAL_S2_RI_ROUTE_CV_CONTRACT_V1',
      'role': final.ROLE, 'interpretation': 'RETROSPECTIVE_ROUTE_LEVEL_DEVELOPMENT',
      'prior_numeric_exposure': True, 'folds': [{'name': 'FOLD_A', 'train': ids[0], 'development': ids[1]},
                                               {'name': 'FOLD_B', 'train': ids[1], 'development': ids[0]}],
      'normalization': 'TRAIN_ROUTE_ONLY_NO_POOLED_OR_DEVELOPMENT_STATISTICS',
      'normalizer': {'nonconstant': 'TRAIN_POPULATION_MEAN_AND_STD', 'constant': 'FROZEN_TRAIN_ZERO_COLUMN',
                     'intercept': 'ONE_UNSCALED', 'development_constant_drift': 'REPORT_NO_REFIT',
                     'actual_normalizer_fitted': False},
      'row_random_split': False, 'segment_random_split': False, 'holdout_allowed': False,
      'independent_validation_allowed': False, 'qualification_allowed': False, 'minimum_route_support': 201},
    'future-metric': {'schema': 'EMPIRICAL_S2_RI_FUTURE_METRIC_CONTRACT_V1',
      'metric_values': 'NOT_COMPUTED', 'one_step_delta': ['RMSE', 'MAE', 'P95_ABSOLUTE'],
      'next_angle': ['RMSE', 'MAE', 'P95_ABSOLUTE'], 'source_grid': ['EXACT_NEXT_ANGLE_HIT_RATE', 'WITHIN_ONE_TICK_RATE'],
      'rollout_seconds': [.25, .5, 1., 2.], 'rollout_metrics': ['ANGLE_RMSE', 'ANGLE_MAE', 'ANGLE_P95_ABSOLUTE'],
      'comparator': 'HOLD_LAST_ANGLE', 'comparator_equation': 'next_angle=present_angle',
      'historical_ARX_FIR': 'NOT_AUTOMATIC_COMPARATOR_OR_ADMISSION_TARGET',
      'direction': 'RMSE_MAE_P95_ROLLOUT_CONSISTENCY_REQUIRED_SINGLE_METRIC_INSUFFICIENT',
      'exact_acceptance_rule': 'SEPARATE_FITTING_POLICY_BEFORE_PERFORMANCE',
      'aggregation': 'ROUTE_SPECIFIC_THEN_EQUAL_ROUTE_PRIMARY_SAMPLE_WEIGHTED_SUPPORTING_ONLY'}}
  from openpilot.tools.cyber_autotune.empirical_s2_ri_admission import identity_contract
  for key in ('target', 'history-reset'):
    bodies[key]['causal_identity_sha256'] = identity_contract()['receipt_sha256']
    bodies[key]['historical_generic_causal_identity'] = 'RATE_DEPENDENT_IMMUTABLE_REFERENCE_ONLY'
    bodies[key]['s2_ri_causal_identity'] = 'RATE_FREE_FAMILY_SPECIFIC_IDENTITY'
  return {k: p.seal({**v, 'authority': AUTHORITY}) for k, v in bodies.items()}


def policy():
  from pathlib import Path
  import numpy as np
  from openpilot.tools.cyber_autotune.empirical_s2_ri_admission import identity_contract, row_contract, FIELDS
  x = final.load()
  resolved = final.resolve(x)
  contracts_ = contracts()
  sources = ['empirical_s2_ri_'+n+'.py' for n in MODULES]
  sources += ['empirical_identifiability_'+n+'.py' for n in ('execution', 'math', 'policy', 'schema')]
  sources += ['empirical_final_readiness.py', 'empirical_causal_support_guard.py', 'empirical_causal_dataset_store.py',
              'empirical_plant_policy.py', 'empirical_causal_dataset_alignment.py']
  return p.seal({'schema': 'EMPIRICAL_S2_RI_DESIGN_POLICY_V1', 'generation': 'S2_RATE_INDEPENDENT_MODEL_DESIGN_V1',
    'family': 'S2_RI_V1', 'baseline': '7d0fa0223888e49dc2e17f002e10e24ef1aabdbf',
    'resolution': resolved, 'partition_sha256': final.partition(x)['receipt_sha256'],
    'route_ids': sorted(r['route_id'] for r in x[final.RLOG_ROUTES]['routes']),
    'stream_count': 154, 'role': final.ROLE,
    'excluded_qlog_content_sha256': sorted(s['segment_sha256'] for s in x[final.QLOG_COVERAGE]['segments']),
    'historical_pins': PINS, 'contracts': {k: v['receipt_sha256'] for k, v in contracts_.items()},
    'causal_identity_sha256': identity_contract()['receipt_sha256'],
    'row_admission_sha256': row_contract()['receipt_sha256'], 'numeric_fields': list(FIELDS),
    'adversarial_auxiliary_read_fields': ['state.rate', 'state.rate.available'],
    'auxiliary_read_purpose': 'ORIGINAL_VIEW_ONLY_EXCLUDED_FROM_ALL_DERIVED_IDENTITIES_FEATURES_AND_READINESS',
    'source_segment_sets': x[final.RLOG_AUTH]['segment_sets'],
    'executor_sha256': {n: p.sha(Path(__file__).with_name(n).read_bytes()) for n in sources},
    'forms': [list(f) for f in m.FORMS], 'scopes': list(m.SCOPES), 'minimum_route_support': 201,
    'rate_independence': 'DELETED_ORIGINAL_NAN_AND_ARBITRARY_RATE_VIEWS_IDENTICAL_DERIVED_BYTES_AND_X',
    'request_independence': 'MISSING_REQUEST_DOES_NOT_BREAK_CAUSAL_OR_MODEL_CONTINUITY',
    'rank': {'method': 'NUMPY_DIRECT_SVD_COMPUTE_UV_FALSE',
      'normalization': 'AUDIT_ONLY_SCOPE_INPUT_POPULATION_CENTER_STD_NOT_A_FUTURE_TRAIN_NORMALIZER',
      'constant': 'CENTER_TO_ZERO_EXCEPT_INTERCEPT_ONE',
      'tolerance': 'S_MAX_TIMES_MAX_M_N_TIMES_FLOAT64_EPS', 'condition_acceptance_threshold': None,
      'target_used': False, 'selected_form': None},
    'environment': {'numpy': np.__version__, 'blas_threads': 1, 'rng': False},
    'authority': AUTHORITY, 'privacy': 'AGGREGATES_AND_OPAQUE_HASHES_ONLY_NO_ROWS_OR_PATHS',
    'closed_loop_bias': 'CLOSED_LOOP_IDENTIFICATION_BIAS_RISK',
    'future_parameters': 'EMPIRICAL_PREDICTIVE_PARAMETERS_NO_CAUSAL_PHYSICAL_INTERPRETATION',
    'holdout': 'HOLDOUT_OPENING_CLOSED', 'opening_count': 0})


def freeze(output):
  from openpilot.tools.cyber_autotune.empirical_causal_dataset_store import safe
  value = policy()
  p.persist(safe(output)/'policy.json', value)
  return value
