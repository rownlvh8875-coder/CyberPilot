"""Frozen read-only empirical structure audit contract; no model authority."""
import subprocess
import json
from pathlib import Path
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_final_readiness as readiness

COMMIT = '18c07cfae4a35786955d5c7fa8bcbe4bfaee0c29'
REPOSITORY = "https://github.com/ajouatom/openpilot"
FILES = {'can_builder': {'file_sha256': '341f8321a597f8aafc23f64fc3177173cacd2f86f73f8b9951eb6aafa1c21c89',
                 'path': 'opendbc_repo/opendbc/car/hyundai/hyundaican.py',
                 'reviewed_ranges': [],
                 'reviewed_slice_sha256': '341f8321a597f8aafc23f64fc3177173cacd2f86f73f8b9951eb6aafa1c21c89'},
 'car_schema': {'file_sha256': 'db5444005dcff5fdbbecf617ea031eb90852e51a848a9d832a02756ddc6bc024',
                'path': 'opendbc_repo/opendbc/car/car.capnp',
                'reviewed_ranges': [],
                'reviewed_slice_sha256': 'db5444005dcff5fdbbecf617ea031eb90852e51a848a9d832a02756ddc6bc024'},
 'card': {'file_sha256': '6630e7c50f016112e7591e980a68b7cfd223a5d9fee8f15bb4466cda9ab78e4f',
          'path': 'openpilot/selfdrive/car/card.py',
          'reviewed_ranges': [],
          'reviewed_slice_sha256': '6630e7c50f016112e7591e980a68b7cfd223a5d9fee8f15bb4466cda9ab78e4f'},
 'carstate': {'file_sha256': '018ba9c239f8ab378de26354e3dd9c7eafe40ac513be1213d38f59a4c3a9e374',
              'path': 'opendbc_repo/opendbc/car/hyundai/carstate.py',
              'reviewed_ranges': [(311, 331)],
              'reviewed_slice_sha256': '08ab7088ce9030f3f5875222e0a80d5558f9c9a4f9ccd353047f2a3298c2734f'},
 'controller': {'file_sha256': 'ced1c209e3ef5661add16a97e5b1ff7af7d5f8f96438f6ce9cb56c02c54b87f6',
                'path': 'opendbc_repo/opendbc/car/hyundai/carcontroller.py',
                'reviewed_ranges': [(192, 220), (235, 340), (555, 565)],
                'reviewed_slice_sha256': 'badf6c8cc1fa1569b9e8b68ef8b5c8af3934471d1131ad003a61dbff16316ca1'},
 'dbc': {'file_sha256': '1590039abb51cbfc3dc8ab4151ab78e7f549088fec878480ab4d6f850b18898a',
         'path': 'opendbc_repo/opendbc/dbc/hyundai_kia_generic.dbc',
         'reviewed_ranges': [(155, 159)],
         'reviewed_slice_sha256': '8d2488af220de6765bfd8dd7e4a624ada5a08f4d516cfe17ffb849294b7427b9'},
 'dbc_parser': {'file_sha256': '07a586ae153665f2a1f7a19ecda33db6480652f143d98ef03fd9e0dcd9d19da8',
                'path': 'opendbc_repo/opendbc/can/dbc.py',
                'reviewed_ranges': [(113, 139)],
                'reviewed_slice_sha256': 'b0ff03a2b0490dba3d24edf10323f767dac7fddba3bd1f44cb605db5c62a07f6'},
 'helpers': {'file_sha256': 'f56a23742d37395f5869f9c63a367375e038e2b47966efaed7a9679307c01e5e',
             'path': 'opendbc_repo/opendbc/car/__init__.py',
             'reviewed_ranges': [(38, 45), (112, 132), (281, 299)],
             'reviewed_slice_sha256': 'a7fb23055e8c787604bf9cba3b7c87d8ebfa37c879a22d1bade87cc14a8cc99a'},
 'interface': {'file_sha256': '123f14680dfb50c9133bbda35e309c93ed57ae81dec12dd28835e5e6a3dd1e8b',
               'path': 'opendbc_repo/opendbc/car/hyundai/interface.py',
               'reviewed_ranges': [],
               'reviewed_slice_sha256': '123f14680dfb50c9133bbda35e309c93ed57ae81dec12dd28835e5e6a3dd1e8b'},
 'interface_base': {'file_sha256': '9a7787c3450da2a0677023246b4a6770470b797f82e9a15db8f83f001b5a5d7f',
                    'path': 'opendbc_repo/opendbc/car/interfaces.py',
                    'reviewed_ranges': [(509, 513), (552, 565), (580, 590)],
                    'reviewed_slice_sha256': '252f9417640dac12ffb70e9aa3dd8f2abfdebfbaddee74cdfbbbe50b55ffb9d0'},
 'latcontrol': {'file_sha256': '67fb6ecafc4d0ce999e2bbf1b729b5f6cf58a5f787c054e770162e7f2f3629cc',
                'path': 'openpilot/selfdrive/controls/lib/latcontrol_torque.py',
                'reviewed_ranges': [(70, 85), (169, 196), (260, 305)],
                'reviewed_slice_sha256': '5b4c009baa200173a54456a80c4b03eba981451d9a06df1504b2ab8b8f6dde14'},
 'limits': {'file_sha256': '2310c5ba7aa8d2b201915a4a392bd18615da3c00b3e5223b268699ae20b57c02',
            'path': 'opendbc_repo/opendbc/car/hyundai/values.py',
            'reviewed_ranges': [],
            'reviewed_slice_sha256': '2310c5ba7aa8d2b201915a4a392bd18615da3c00b3e5223b268699ae20b57c02'},
 'parser': {'file_sha256': '2e99d9e065a0758453becc55f886d90a33960be08ea5e4f9b6bf3202275063af',
            'path': 'opendbc_repo/opendbc/can/parser.py',
            'reviewed_ranges': [(15, 27), (54, 91)],
            'reviewed_slice_sha256': '17280fa4b1fb6790fb36a87b0de46dab413e4d3b2bb6b4bd749f03def1ee157a'}}
LICENSES = {'LICENSE': '716ce815a0467219c59ec2433e6bce7f32efc45240725c6d3141a52b111d2558'}

MODULES = ('policy', 'math', 'execution', 'publication', 'schema')
AUTHORITY = dict.fromkeys((
  'model_fitting', 'model_selection', 'cv_scoring', 'parameter_search', 'prediction_generation',
  'residual_calculation', 'family_selection', 'qlog_support', 'raw_reopening', 'holdout_opening',
  'ta_execution', 'sg_execution', 'composition', 'candidate_execution', 'production', 'vehicle'), False)

GENERATION = 'EMPIRICAL_MODEL_FAMILY_IDENTIFIABILITY_AUDIT_V1'


def git_blob(repo, path):
  return subprocess.check_output(['git', '-c', f'safe.directory={repo}', '-C', str(repo), 'show', COMMIT+':'+path])


def source_contract():
  return p.seal({'schema': 'EMPIRICAL_STEERING_RATE_SEMANTICS_V1', 'repository': REPOSITORY, 'commit': COMMIT,
    'git_tree_sha1': '91c84e4febe748dbf8f1c074683c1f57641b6a1a',
    'prior_source_provenance_receipt_sha256': 'a9df216a7766b073f5fe55734e679fa3f4bbae029727b0d31227e9f7cde5a719',
    'files': json.loads(p.canonical(FILES)), 'licenses': LICENSES, 'source_execution': False,
    'rate': {'assignment': 'carState.steeringRateDeg <- SAS11.SAS_Speed', 'layout': '16|8@1+',
      'endian': 'LITTLE_ENDIAN', 'signed': False, 'factor': 4.0, 'offset': 0., 'unit': '',
      'dbc_declared_range': [0., 1016.], 'encoded_numeric_range': [0., 1020.],
      'reserved_code_meaning': 'UNPROVEN', 'decoder': 'unsigned_integer * factor + offset',
      'later_sign_reconstruction_in_measured_field': 'NONE_IN_REVIEWED_ASSIGNMENT_CHAIN',
      'downstream_latcontrol': 'RADIANS_CONSUMPTION_IS_AN_ASSUMPTION_NOT_SENSOR_UNIT_PROOF',
      'classification': 'SOURCE_NATIVE_RATE_CODE_ONLY', 'contract': 'RATE_SOURCE_CONTRACT_PARTIAL',
      'signed_physical_rate_proven': False, 'unsigned_physical_magnitude_proven': False,
      'numeric_diagnostic_authority': 'CANNOT_PROMOTE_SOURCE_SEMANTICS'},
    'angle': {'signal': 'SAS11.SAS_Angle', 'layout': '0|16@1-', 'factor': .1, 'offset': 0., 'unit': 'Deg',
              'storage': 'FLOAT32_CARSTATE_THEN_EXACT_FLOAT64_CACHE'},
    's3': {'status': 'S3_SOURCE_MECHANISM_BLOCKED',
      'observed_mechanisms': ['CONTROLLER_DEADZONE_ONLY', 'COMMAND_LIMIT_REGIME_ONLY'],
      'physical_deadzone_proven': False, 'physical_hysteresis_proven': False,
      'scope': 'NO_SOURCE_DEFINED_ACTUATOR_REGIME_PROVEN_BY_REVIEWED_SOURCE',
      'facts': ['steeringAngleDeadzoneDeg converts to controller curvature/lateral-acceleration error deadzone',
                'get_friction applies controller compensation; no physical deadzone measurement',
                'apply_driver_steer_torque_limits clamps driver allowance and command slew',
                'CustomSteerMax/Delta settings affect command limits, not EPS hysteresis proof',
                'apply_hysteresis in interface_base is vEgoCluster display-speed behavior',
                'measurement quantization is not an actuator regime'],
      'numeric_regime_discovery_allowed': False}})


def validate_source(value):
  if value != source_contract():
    raise ValueError('SOURCE_RATE_OR_MECHANISM_CONTRACT_DRIFT')
  return value


def audit_source(repo):
  for row in FILES.values():
    data = git_blob(repo, row['path'])
    if p.sha(data) != row['file_sha256']:
      raise ValueError('EXACT_SOURCE_BLOB_DRIFT')
    lines = data.decode().splitlines(keepends=True)
    spans = row['reviewed_ranges']
    sliced = ''.join(''.join(lines[a-1:b]) for a, b in spans).encode() if spans else data
    if p.sha(sliced) != row['reviewed_slice_sha256']:
      raise ValueError('REVIEWED_SOURCE_SLICE_DRIFT')
  for path, digest in LICENSES.items():
    if p.sha(git_blob(repo, path)) != digest:
      raise ValueError('EXACT_LICENSE_BLOB_DRIFT')
  return source_contract()


def code_identity():
  result = {}
  for name in MODULES:
    path = Path(__file__).with_name('empirical_identifiability_'+name+'.py')
    if path.exists():
      result[name] = p.sha(path.read_bytes())
  return result


def policy():
  x = readiness.load()
  resolution = readiness.resolve(x)
  if any(r['source_commit'] != COMMIT for r in x[readiness.RLOG_ROUTES]['routes']):
    raise ValueError('EXACT_RECORDED_SOURCE_COMMIT_REQUIRED')
  return p.seal({'schema': 'EMPIRICAL_MODEL_FAMILY_IDENTIFIABILITY_POLICY_V1', 'generation': GENERATION,
    'resolution': resolution, 'partition_sha256': readiness.partition(x)['receipt_sha256'],
    'stream_count': 154, 'role': readiness.ROLE, 'prior_numeric_exposure': True,
    'route_ids': sorted(r['route_id'] for r in x[readiness.RLOG_ROUTES]['routes']),
    'excluded_qlog_content_sha256': sorted(s['segment_sha256'] for s in x[readiness.QLOG_COVERAGE]['segments']),
    'source_contract_sha256': source_contract()['receipt_sha256'], 'executor_sha256': code_identity(),
    'guard_sha256': p.sha(Path(__file__).with_name('empirical_causal_support_guard.py').read_bytes()),
    'histories': list(range(1, 46)), 'lags': list(range(21)), 'minimum_route_development_support': 201,
    'dt_ns': 10_000_000, 'max_source_age_ns': 20_000_000,
    's1_layout': ['angle[k]', 'rate_native[k]', 'logged_normalized_command[k-d]', 'speed[k]', 'intercept=1'],
    's2_layout': ['command[k-L+1:k] chronological inclusive', 'angle[k-L+1:k] chronological inclusive',
                  'rate_native[k]', 'speed[k]'],
    'next_state_availability': 'SEPARATE_ADJACENT_ADMITTED_SAME_RUN_NO_TARGET_VALUE_IN_X',
    'rank': {'dtype': 'float64', 'center': 'POPULATION_MEAN_NONCONSTANT_INPUTS_ONLY',
             'scale': 'POPULATION_STD_DDOF_ZERO', 'constant': 'ZERO_AFTER_CENTERING_EXCEPT_INTERCEPT_ONE',
             'method': 'NUMPY_DIRECT_SVD_COMPUTE_UV_FALSE',
             'tolerance': 'S_MAX_TIMES_MAX_M_N_TIMES_FLOAT64_EPS',
             'reference': 'https://numpy.org/doc/stable/reference/generated/numpy.linalg.matrix_rank.html',
             'target_used': False, 'condition_threshold': None, 'symbolic_identifiability_proof': False},
    'route_aggregation': 'BOTH_ROUTES_SEPARATE_THEN_POOLED_NO_ROUTE_QUALITY_WEIGHTING',
    'quantiles': [0., .5, .95, 1.], 'quantiles_are_thresholds': False,
    'rate_diagnostic': 'LATER_RATE_VS_ADJACENT_ANGLE_DIFFERENCE_OVER_SELECTED_STATE_TIME_DIFFERENCE',
    'environment': {'numpy': np.__version__, 'blas_threads': 1, 'rng': False},
    'authority': AUTHORITY, 'holdout': 'HOLDOUT_OPENING_CLOSED', 'opening_count': 0,
    'privacy': 'AGGREGATES_ONLY_NO_PRIVATE_ROWS_PATHS_TIMESTAMPS_FEATURE_MATRICES',
    'closed_loop_bias': 'CLOSED_LOOP_IDENTIFICATION_BIAS_RISK',
    'transaction': 'REQUEST_OUTPUT_TRANSACTION_LINK_UNAVAILABLE',
    'physical_eps': 'PHYSICAL_EPS_APPLICATION_UNAVAILABLE'})


def freeze(store):
  from openpilot.tools.cyber_autotune.empirical_causal_dataset_store import safe
  store = safe(store)
  value = policy()
  p.persist(store/'policy.json', value)
  return value


def leakage_reset():
  return p.seal({'schema': 'EMPIRICAL_IDENTIFIABILITY_LEAKAGE_RESET_CONTRACT_V1',
    'runtime_implemented': False, 'prohibited': ['future_command', 'future_state', 'next_segment', 'next_causal_run',
      'other_route', 'qlog', 'next_target_in_X', 'post_target_event', 'development_feedback_into_policy', 'HOLDOUT'],
    'history': 'SAME_ROUTE_SEGMENT_CAUSAL_RUN_STRICT_CURRENT_OR_PAST_SOURCE_TIME',
    'families': {family: {'reset_at': ['route_boundary', 'segment_boundary', 'causal_run_break', 'inactive', 'driver_override',
                                      'fault', 'reengagement_before_new_valid_history'],
                          'initialization': 'ONLY_AVAILABLE_CURRENT_PAST_DATA_FUTURE_FITTING_POLICY_MUST_FREEZE',
                          'latent_state_carry_across_boundary': False,
                          'parameterization': 'NOT_SELECTED_NO_FITTING'} for family in ('S1', 'S2', 'S3')},
    's1_ambiguity': 'STATE_COORDINATE_SCALE_SIGN_LATENT_OBSERVATION_AND_INPUT_DELAY_NOT_IDENTIFIED_BY_X_RANK',
    's2_ambiguity': 'FEATURE_COLLINEARITY_QUANTIZED_TARGET_CLOSED_LOOP_BIAS_NOT_RESOLVED_BY_X_RANK',
    's3_ambiguity': 'NO_SOURCE_PROVEN_PHYSICAL_REGIME_NO_NUMERIC_BOUNDARY_SEARCH',
    'bias_correction': 'NOT_RUN', 'holdout': 'HOLDOUT_OPENING_CLOSED', 'authority': AUTHORITY})
