"""Declared-equivalent native synthetic screening; never performance qualification."""
import copy
from dataclasses import asdict
import json
import math
from pathlib import Path
import platform
import subprocess

from openpilot.tools.cyber_autotune.a1_experiment import build_request, make_fixture
from openpilot.tools.cyber_autotune.curvature_yaw_candidate import effective_parameters
from openpilot.tools.cyber_autotune.curvature_yaw_closed_loop import closed_loop_state_sha256
from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import (
  ADAPTER_PATH, CANDIDATE_FILES, PLANT_PATH, SUPPORT_FILES, controller_identity_sha256,
  encode_request, producer_identity_sha256,
)
from openpilot.tools.cyber_autotune.curvature_yaw_native_runner import (
  admit_native_transcript, closed_loop_frames, initial_state, run_native_transcript,
)
from openpilot.tools.cyber_autotune.curvature_yaw_plant import (
  CurvatureYawPlantConfig, CurvatureYawPlantState, observe_curvature_yaw_step,
)
from openpilot.tools.cyber_autotune.native_protocol import FINGERPRINT, SOURCE_FILES, _hex
from openpilot.tools.cyber_autotune.lateral_closed_loop import (
  ClosedLoopBinding, ClosedLoopDomain, frames_sha256, timebase_sha256,
)
from openpilot.tools.cyber_autotune.native_protocol import _keys, canonical, digest, finite

ROOT = Path(__file__).resolve().parents[3]
UPSTREAM = 'c8fb906815530460ed156f14e09e1f312bb0f851'
OPENDBC = '4134c0d1f5e8f695e35ea5fedbe88f6d0c3afb76'
ARMS = ('UPSTREAM_BASELINE', 'CYBER_CURRENT', 'CYBER_CANDIDATE')
SCREENING_CASES = tuple(f'{shape}_{speed}_{side}' for shape in ('gentle', 'sharp')
                        for speed in ('low', 'high') for side in ('left', 'right')) + (
  's_low', 's_high', 'reengage_low', 'reengage_high', 'speed_sweep',
)
# Existing A1 bounded_combined coordinates. Frozen before measurement; no search.
CANDIDATE = {'implementation': 'SPEED_SCHEDULE', 'config': {
  'points': [[0., 4., .125], [10., 4.+1/128, .125+1/2048],
             [20., 4.+1/64, .125+1/1024], [30., 4., .125]],
}}
PLANT = {
  'dt_s': .01, 'delay_steps': 2, 'min_speed_mps': 3., 'max_speed_mps': 27.,
  'command_limit': 1., 'curvature_intercept_1pm': 0., 'curvature_ar': .92,
  'command_gain_1pm': .004, 'command_speed_gain_s_per_m2': .0002,
  'command_inv_speed_gain_per_s': .002, 'roll_gain_1pm_per_rad': .001,
  'yaw_ar': .75, 'yaw_bias_rad_s': 0.,
}
RESET = {'curvature_1pm': 0., 'yaw_rate_rad_s': 0., 'command_history': [0., 0.],
         'heading_rad': 0., 'pose_y_m': 0.}
DIAGNOSTICS = {
  'version': 1, 'dt_s': .01, 'torque': 'requested native normalized command',
  'derivative': 'adjacent difference/dt, all transitions',
  'zero_crossing': 'changes of nonzero sign, ignore exact zeros',
  'reversal': 'changes of nonzero derivative sign, ignore exact zeros',
  'tracking': 'curvature RMSE over all frames and each predetermined phase',
  'saturation': 'native saturated bool occupancy',
  'path': 'post-step pose and heading integration only; no lane metric',
  'acceptance_thresholds': None, 'selection': 'NONE',
}
BLOCKERS = ['INDEPENDENT_REFERENCE_UNAVAILABLE', 'PERFORMANCE_QUALIFICATION_BLOCKED',
            'REAL_VEHICLE_UNVERIFIED', 'VEHICLE_ACTIVATION_BLOCKED']


def _inputs(name):
  if name not in SCREENING_CASES:
    raise ValueError('UNKNOWN_SYNTHETIC_SCENARIO')
  rows, phases = [], []
  for i in range(401):
    phase = 'straight' if i < 40 else 'entry' if i < 120 else 'apex' if i < 280 else 'exit'
    envelope = 0. if i < 40 else (i-40)/80 if i < 120 else 1. if i < 280 else (400-i)/120
    curvature = (.0015 if name.startswith('sharp') else .00015) * envelope
    if name.endswith('right'):
      curvature = -curvature
    if name.startswith('s_'):
      curvature = .0005 * math.sin(2*math.pi*(i-40)/240) * envelope
      phase += '_left' if curvature >= 0 else '_right'
    speed = 5. if 'low' in name else 25.
    if name == 'speed_sweep':
      speed = 5. + i/20
    pressed = name.startswith('reengage') and 140 <= i < 170
    active = not (name.startswith('reengage') and 190 <= i < 230)
    if pressed:
      phase = 'driver_pressed'
    elif not active:
      phase = 'inactive'
    elif name.startswith('reengage') and 230 <= i < 260:
      phase = 'reengagement'
    phases.append(phase)
    rows.append({
      'time_ns': i*10_000_000, 'speed_mps': speed, 'active': active,
      'safety_limited': False, 'curvature_limited': False, 'steering_pressed': pressed,
      'accel_mps2': 0., 'angle_deg': 0., 'rate_deg_s': 0., 'driver_torque': .2 if pressed else 0.,
      'roll_rad': 0., 'angle_offset_deg': 0., 'stiffness_factor': 1., 'steer_ratio': 16.,
      'desired_curvature_1pm': curvature, 'lateral_delay_s': .15,
    })
  return rows, phases


def _verify_upstream(native):
  source = native['source']
  if source['opendbc_head'] != OPENDBC:
    raise ValueError('UPSTREAM_OPENDBC_MISMATCH')
  gitlink = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', UPSTREAM+':opendbc_repo'], timeout=5).decode().strip()
  if gitlink != OPENDBC:
    raise ValueError('UPSTREAM_GITLINK_MISMATCH')
  for name, sha in source['files'].items():
    if not name.startswith('opendbc_repo/'):
      raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', UPSTREAM+':'+name], timeout=5)
      if digest(raw) != sha:
        raise ValueError('UPSTREAM_NATIVE_CORE_DIVERGED')


def _manifest(name, requests):
  _, phases = _inputs(name)
  native = requests[0]['native']
  identities = []
  for index, request in enumerate(requests):
    sources = dict(native['source']['files'])
    if index == 2:
      sources.update({p: request['support_files'][p] for p in CANDIDATE_FILES})
    identities.append({
      'arm': ARMS[index], 'alias_of': ARMS[0] if index == 1 else None,
      'request_sha256': digest(encode_request(request)),
      'controller_sha256': controller_identity_sha256(request),
      'active_source_sha256': digest(canonical(sources)),
      'configuration_sha256': digest(canonical(request['controller'])),
      'producer_sha256': producer_identity_sha256(request),
    })
  import capnp
  import numpy
  return {
    'version': 1, 'contract': 'OFFLINE_TWO_UNIQUE_PLUS_EXACT_BASELINE_ALIAS',
    'scenario': name, 'upstream_native_anchor': UPSTREAM, 'execution_head': native['source']['head'],
    'opendbc_head': native['source']['opendbc_head'], 'native_source_files': native['source']['files'],
    'support_files': requests[0]['support_files'], 'car_params_sha256': native['car_params_sha256'],
    'frames_sha256': digest(canonical(native['frames'])), 'plant_config': requests[0]['plant_config'],
    'initial_state': requests[0]['initial_state'], 'controller_to_plant_sign': requests[0]['controller_to_plant_sign'],
    'phase_labels': phases, 'arms': identities,
    'candidate_kind': 'FIXED_BOUNDED_A1_COMBINED_NO_SEARCH', 'candidate_spec': requests[2]['controller'],
    'diagnostic_spec': copy.deepcopy(DIAGNOSTICS),
    'diagnostic_producer_sha256': digest(Path(__file__).read_bytes()),
    'environment': {'python': platform.python_version(), 'numpy': numpy.__version__,
                    'capnp': capnp.__version__, 'machine': platform.machine()},
    'synthetic_input': True, 'reference_status': 'NO INDEPENDENT LANE TRUTH',
  }


def build_screening_case(name):
  frames, _ = _inputs(name)
  native, _ = make_fixture(build_request('identity'))
  native['frames'] = frames
  _verify_upstream(native)
  baseline = {
    'version': 2, 'native': native,
    'support_files': {p: digest((ROOT/p).read_bytes()) for p in SUPPORT_FILES+CANDIDATE_FILES},
    'plant_config': copy.deepcopy(PLANT), 'initial_state': copy.deepcopy(RESET),
    'controller_to_plant_sign': -1., 'controller': {'implementation': 'NATIVE', 'config': {}},
  }
  candidate = copy.deepcopy(baseline)
  candidate['controller'] = copy.deepcopy(CANDIDATE)
  requests = [baseline, copy.deepcopy(baseline), candidate]
  return {'requests': requests, 'manifest': _manifest(name, requests)}


def _freeze_case(case, expected):
  # Canonical copy severs caller mutation before any worker is started.
  case = json.loads(canonical(case))
  _keys(case, ('requests', 'manifest'))
  manifest, requests = case['manifest'], case['requests']
  if digest(canonical(manifest)) != expected or type(requests) is not list or len(requests) != 3:
    raise ValueError('SCREENING_MANIFEST_FREEZE_MISMATCH')
  if canonical(requests[0]) != canonical(requests[1]) or requests[0]['controller'] != {'implementation': 'NATIVE', 'config': {}}:
    raise ValueError('DECLARED_ALIAS_MUST_BE_EXACT')
  common = copy.deepcopy(requests[2])
  common['controller'] = requests[0]['controller']
  if canonical(common) != canonical(requests[0]) or canonical(requests[2]['controller']) != canonical(CANDIDATE):
    raise ValueError('CANDIDATE_COMMON_BASIS_MISMATCH')
  frames, _ = _inputs(manifest['scenario'])
  if (requests[0]['native']['frames'] != frames or requests[0]['plant_config'] != PLANT
      or requests[0]['initial_state'] != RESET or requests[0]['controller_to_plant_sign'] != -1.):
    raise ValueError('FROZEN_SCENARIO_MISMATCH')
  _verify_upstream(requests[0]['native'])
  from openpilot.tools.cyber_autotune.native_worker import _verify_source
  _verify_source(requests[0]['native']['source'])
  fixture, _ = make_fixture(build_request('identity'))
  if any(requests[0]['native'][k] != fixture[k] for k in ('car_params_base64','car_params_sha256','source','fingerprint')):
    raise ValueError('OWNED_SYNTHETIC_NATIVE_BASIS_REQUIRED')
  for request in requests:
    for name, sha in request['support_files'].items():
      if digest((ROOT/name).read_bytes()) != sha:
        raise ValueError('SCREENING_SUPPORT_SOURCE_DRIFT')
    encode_request(request)
    effective_parameters(request)  # includes complete schedule/bounds before six workers
  if canonical(_manifest(manifest['scenario'], requests)) != canonical(manifest):
    raise ValueError('SCREENING_ARM_MANIFEST_MISMATCH')
  return case


def _events(values):
  previous = 0
  events = []
  for i, value in enumerate(values):
    sign = (value > 0) - (value < 0)
    if sign:
      if previous and sign != previous:
        events.append(i)
      previous = sign
  return events


def diagnose_samples(samples, dt):
  if not samples or not finite(dt) or dt <= 0:
    raise ValueError('INVALID_DIAGNOSTIC_INPUT')
  u = [r['requested_torque'] for r in samples]
  error = [r['curvature_1pm']-r['desired_curvature_1pm'] for r in samples]
  derivative = [(b-a)/dt for a,b in zip(u[:-1],u[1:],strict=True)]
  def rms(values):
    return math.sqrt(sum(x*x for x in values)/len(values)) if values else 0.
  zero = _events(u)
  reversals = [i+1 for i in _events(derivative)]
  return {
    'command_zero_crossings': len(zero), 'zero_crossing_steps': zero,
    'command_reversals': len(reversals), 'reversal_steps': reversals,
    'command_reversal_rate_hz': len(reversals)/((len(samples)-1)*dt) if len(samples)>1 else 0.,
    'command_derivative_rms_per_s': rms(derivative),
    'max_abs_command_derivative_per_s': max(map(abs,derivative),default=0.),
    'command_total_variation': sum(abs(b-a) for a,b in zip(u[:-1],u[1:],strict=True)),
    'saturation_occupancy': sum(r['saturated'] for r in samples)/len(samples),
    'curvature_tracking_rmse_1pm': rms(error),
    'phase_tracking_rmse_1pm': {phase:rms([e for e,r in zip(error,samples,strict=True) if r['phase']==phase])
                              for phase in sorted({r['phase'] for r in samples})},
    'max_abs_pose_y_m': max(abs(r['pose_y_m']) for r in samples),
  }


def _difference(a,b):
  return {
    'changed_command_frames': sum(x['requested_torque'] != y['requested_torque'] for x,y in zip(a,b,strict=True)),
    'max_abs_command_difference': max(abs(x['requested_torque']-y['requested_torque']) for x,y in zip(a,b,strict=True)),
    'max_abs_pose_difference_m': max(abs(x['pose_y_m']-y['pose_y_m']) for x,y in zip(a,b,strict=True)),
  }



def _plant_trace(commands, frames):
  config = CurvatureYawPlantConfig(**PLANT)
  state = CurvatureYawPlantState(0.,0.,(0.,0.))
  heading, x, y = 0., 0., 0.
  rows = []
  for command,frame in zip(commands,frames,strict=True):
    observation = observe_curvature_yaw_step(config,state,command=-command,
                                             speed_mps=frame['speed_mps'],roll_rad=frame['roll_rad'])
    if observation.next_state is None:
      raise ValueError('SCREENING_PLANT_REPLAY_FAILED')
    state = observation.next_state
    heading += state.yaw_rate_rad_s*.01
    x += frame['speed_mps']*math.cos(heading)*.01
    y += frame['speed_mps']*math.sin(heading)*.01
    rows.append({'curvature_1pm':state.curvature_1pm, 'yaw_rate_rps':state.yaw_rate_rad_s,
                 'lateral_accel_mps2':state.yaw_rate_rad_s*frame['speed_mps'],
                 'pose_x_m':x,'pose_y_m':y,'heading_rad':heading,
                 'applied_normalized_torque':-observation.delayed_command})
  return rows


def run_screening_case(case, *, expected_manifest_sha256, timeout_s):
  case = _freeze_case(case, expected_manifest_sha256)
  manifest = case['manifest']
  domain = ClosedLoopDomain(digest(canonical(PLANT)), .01, 3., 27., .02, 'PLANT', 1.)
  arms = []
  for index, request in enumerate(case['requests']):
    frames = closed_loop_frames(request)
    binding = ClosedLoopBinding(
      producer_identity_sha256(request), controller_identity_sha256(request),
      request['support_files'][ADAPTER_PATH], request['support_files'][PLANT_PATH],
      digest(canonical({'scope':'SYNTHETIC_DESCRIPTIVE_UNQUALIFIED','plant':PLANT})),
      domain.identity_sha256, frames_sha256(frames), closed_loop_state_sha256(initial_state(request)),
      digest(canonical(DIAGNOSTICS)), digest(canonical(manifest['environment'])), timebase_sha256(frames),
    )
    results, receipts = [], []
    for _ in range(2):
      result = run_native_transcript(request, timeout_s=timeout_s)
      if result['status'] != 'COMPLETED':
        raise ValueError('SCREENING_WORKER_FAILED:'+result['status'])
      receipt = admit_native_transcript(request,result,domain,binding,arm=ARMS[index])
      if receipt.status != 'STRUCTURAL_ADMISSION':
        raise ValueError('SCREENING_REPLAY_FAILED')
      results.append(result)
      receipts.append(receipt)
    if results[0] != results[1] or receipts[0] != receipts[1]:
      raise ValueError('SCREENING_REPEATABILITY_FAILED')
    samples = []
    physical = _plant_trace([s.requested_torque for s in receipts[0].receipt.samples],request['native']['frames'])
    for sample,frame,observation,phase,plant_row in zip(receipts[0].receipt.samples, request['native']['frames'],
                                             results[0]['metric_observations'], manifest['phase_labels'], physical, strict=True):
      values = asdict(sample)
      if any(values[key] != value for key,value in plant_row.items() if key in values):
        raise ValueError('PUBLIC_REPLAY_TRACE_MISMATCH')
      values.update(plant_row)
      values.update({
        'desired_curvature_1pm': frame['desired_curvature_1pm'],
        'speed_mps': frame['speed_mps'], 'phase': phase, 'active': frame['active'],
        'steering_pressed': frame['steering_pressed'], 'steering_angle_deg': observation['steering_angle_deg'],
        'saturated': observation['saturated'],
      })
      samples.append(values)
    arms.append({
      'arm': ARMS[index], 'structural_status': 'STRUCTURAL_ADMISSION',
      'identity': manifest['arms'][index],
      'repetition_result_sha256': [digest(canonical(r)) for r in results],
      'repetition_replay_envelope_sha256': [r.envelope_sha256 for r in receipts],
      'effective_parameters_sha256': results[0]['effective_parameters_sha256'],
      'samples': samples, 'samples_sha256': digest(canonical(samples)),
      'diagnostics': diagnose_samples(samples,.01),
    })
  if arms[0]['samples'] != arms[1]['samples']:
    raise ValueError('BASELINE_CURRENT_ALIAS_OUTPUT_MISMATCH')
  report = {
    'version': 1, 'status': 'STRUCTURAL_SYNTHETIC_SCREENING',
    'manifest': manifest, 'manifest_sha256': expected_manifest_sha256,
    'executed_runs': 6, 'exact_repeatability': True, 'baseline_current_exact_alias': True,
    'arms': arms, 'candidate_difference': _difference(arms[0]['samples'],arms[2]['samples']),
    'reference_status': 'NO INDEPENDENT LANE TRUTH',
    'physical_delay_owner': 'PLANT', 'controller_physical_delay_queue_present': False,
    'blockers': BLOCKERS.copy(), 'vehicle_status': 'NOT_READY',
    'performance_qualified': False, 'runtime_accepted': False, 'promotable': False,
  }
  report['receipt_sha256'] = digest(canonical(report))
  validate_screening_report(report)
  return report


def validate_screening_report(report):
  """Validate internal receipt consistency, not provenance authenticity or qualification."""
  fields = ('version','status','manifest','manifest_sha256','executed_runs','exact_repeatability',
            'baseline_current_exact_alias','arms','candidate_difference','reference_status',
            'physical_delay_owner','controller_physical_delay_queue_present','blockers','vehicle_status',
            'performance_qualified','runtime_accepted','promotable','receipt_sha256')
  _keys(report,fields)
  body = {k:v for k,v in report.items() if k != 'receipt_sha256'}
  if digest(canonical(body)) != report['receipt_sha256']:
    raise ValueError('SCREENING_RECEIPT_MISMATCH')
  if (type(report['version']) is not int or report['version'] != 1
      or report['status'] != 'STRUCTURAL_SYNTHETIC_SCREENING' or type(report['executed_runs']) is not int or report['executed_runs'] != 6
      or report['exact_repeatability'] is not True or report['baseline_current_exact_alias'] is not True
      or report['reference_status'] != 'NO INDEPENDENT LANE TRUTH' or report['physical_delay_owner'] != 'PLANT'
      or report['controller_physical_delay_queue_present'] is not False
      or report['blockers'] != BLOCKERS or report['vehicle_status'] != 'NOT_READY'
      or any(report[k] is not False for k in ('performance_qualified','runtime_accepted','promotable'))):
    raise ValueError('INVALID_SCREENING_SCOPE_OR_AUTHORITY')
  manifest = report['manifest']
  _keys(manifest, ('version','contract','scenario','upstream_native_anchor','execution_head',
    'opendbc_head','native_source_files','support_files','car_params_sha256','frames_sha256',
    'plant_config','initial_state','controller_to_plant_sign','phase_labels','arms',
    'candidate_kind','candidate_spec','diagnostic_spec','diagnostic_producer_sha256','environment',
    'synthetic_input','reference_status'))
  if (digest(canonical(manifest)) != report['manifest_sha256']
      or type(manifest['version']) is not int or manifest['version'] != 1
      or not _hex(manifest['execution_head'],40)
      or not all(_hex(manifest[k],64) for k in ('car_params_sha256','frames_sha256','diagnostic_producer_sha256'))
      or manifest['contract'] != 'OFFLINE_TWO_UNIQUE_PLUS_EXACT_BASELINE_ALIAS'
      or canonical(manifest['diagnostic_spec']) != canonical(DIAGNOSTICS)
      or canonical(manifest['candidate_spec']) != canonical(CANDIDATE)
      or manifest['reference_status'] != report['reference_status'] or manifest['synthetic_input'] is not True
      or manifest['upstream_native_anchor'] != UPSTREAM or manifest['opendbc_head'] != OPENDBC
      or manifest['candidate_kind'] != 'FIXED_BOUNDED_A1_COMBINED_NO_SEARCH'
      or manifest['controller_to_plant_sign'] != -1.):
    raise ValueError('INVALID_SCREENING_MANIFEST')
  frames, phases = _inputs(manifest['scenario'])
  _keys(manifest['native_source_files'],SOURCE_FILES)
  _keys(manifest['support_files'],SUPPORT_FILES+CANDIDATE_FILES)
  for files in (manifest['native_source_files'],manifest['support_files']):
    if not all(_hex(value,64) for value in files.values()):
      raise ValueError('INVALID_SCREENING_SOURCE_DIGEST')
  _keys(manifest['environment'],('python','numpy','capnp','machine'))
  if not all(type(value) is str and value for value in manifest['environment'].values()):
    raise ValueError('INVALID_SCREENING_ENVIRONMENT')
  if (manifest['phase_labels'] != phases or canonical(manifest['plant_config']) != canonical(PLANT)
      or canonical(manifest['initial_state']) != canonical(RESET)
      or manifest['frames_sha256'] != digest(canonical(frames))):
    raise ValueError('INVALID_SCREENING_INPUTS')
  if (type(manifest['arms']) is not list or len(manifest['arms']) != 3
      or type(report['arms']) is not list or len(report['arms']) != 3):
    raise ValueError('INVALID_SCREENING_ARMS')
  for index, identity in enumerate(manifest['arms']):
    _keys(identity, ('arm','alias_of','request_sha256','controller_sha256','active_source_sha256',
                     'configuration_sha256','producer_sha256'))
    if (identity['arm'] != ARMS[index] or identity['alias_of'] != (ARMS[0] if index==1 else None)
        or not all(_hex(value,64) for key,value in identity.items() if key not in ('arm','alias_of'))):
      raise ValueError('INVALID_DECLARED_ARM')
    # Independent recomputation of deterministic v2 identities. Request bytes,
    # effective CP rows and native result contents are omitted: their digests
    # remain shape-checked provenance declarations, not authenticated execution.
    spec = CANDIDATE if index == 2 else {'implementation':'NATIVE','config':{}}
    candidate_sources = {p:manifest['support_files'][p] for p in CANDIDATE_FILES}
    sources = dict(manifest['native_source_files'])
    if index == 2:
      sources.update(candidate_sources)
    controller_sha = digest(canonical({
      'source_head':manifest['execution_head'], 'opendbc_head':manifest['opendbc_head'],
      'source_files':manifest['native_source_files'], 'car_params_sha256':manifest['car_params_sha256'],
      'fingerprint':FINGERPRINT, 'controller':spec, 'candidate_sources':candidate_sources,
    }))
    expected = {
      'configuration_sha256':digest(canonical(spec)), 'active_source_sha256':digest(canonical(sources)),
      'controller_sha256':controller_sha,
      'producer_sha256':digest(canonical({'support_files':manifest['support_files'],'controller_identity_sha256':controller_sha})),
    }
    if any(identity[key] != value for key,value in expected.items()):
      raise ValueError('SCREENING_DECLARED_BINDING_DRIFT')

  if any(manifest['arms'][0][key] != manifest['arms'][1][key] for key in manifest['arms'][0] if key not in ('arm','alias_of')):
    raise ValueError('INVALID_DECLARED_ALIAS')
  if manifest['arms'][0]['active_source_sha256'] == manifest['arms'][2]['active_source_sha256']:
    raise ValueError('CANDIDATE_SOURCE_NOT_DISTINCT')
  for index, arm in enumerate(report['arms']):
    _keys(arm,('arm','structural_status','identity','repetition_result_sha256',
               'repetition_replay_envelope_sha256','effective_parameters_sha256','samples','samples_sha256','diagnostics'))
    if arm['arm'] != ARMS[index] or arm['identity'] != manifest['arms'][index] or arm['structural_status'] != 'STRUCTURAL_ADMISSION':
      raise ValueError('INVALID_SCREENING_ARM_IDENTITY')
    for key in ('repetition_result_sha256','repetition_replay_envelope_sha256'):
      values = arm[key]
      if type(values) is not list or len(values) != 2 or values[0] != values[1] or not all(_hex(v,64) for v in values):
        raise ValueError('INVALID_REPEAT_RECEIPT')
    if not _hex(arm['effective_parameters_sha256'],64):
      raise ValueError('INVALID_EFFECTIVE_PARAMETER_DIGEST')
    samples = arm['samples']
    if (type(samples) is not list or len(samples) != len(frames)
        or digest(canonical(samples)) != arm['samples_sha256']):
      raise ValueError('INVALID_SCREENING_SAMPLES')
    physical = _plant_trace([r['requested_torque'] for r in samples],frames)
    for i,(row,frame,phase,plant_row) in enumerate(zip(samples,frames,phases,physical,strict=True)):
      _keys(row,('step_index','time_s','requested_torque','applied_normalized_torque','lateral_accel_mps2',
                 'yaw_rate_rps','pose_y_m','curvature_1pm','desired_curvature_1pm','speed_mps','phase',
                 'active','steering_pressed','steering_angle_deg','saturated','heading_rad','pose_x_m'))
      numeric = ('time_s','requested_torque','applied_normalized_torque','lateral_accel_mps2','yaw_rate_rps',
                 'pose_y_m','curvature_1pm','desired_curvature_1pm','speed_mps','steering_angle_deg','heading_rad','pose_x_m')
      if (not all(finite(row[k]) for k in numeric) or type(row['step_index']) is not int or row['step_index'] != i or row['time_s'] != frame['time_ns']*1e-9
          or abs(row['requested_torque']) > 1 or abs(row['applied_normalized_torque']) > 1
          or row['phase'] != phase or row['speed_mps'] != frame['speed_mps']
          or row['desired_curvature_1pm'] != frame['desired_curvature_1pm']
          or row['active'] is not frame['active'] or row['steering_pressed'] is not frame['steering_pressed']
          or type(row['saturated']) is not bool or any(row[key] != value for key,value in plant_row.items())):
        raise ValueError('INVALID_SCREENING_SAMPLE')
    if canonical(diagnose_samples(samples,.01)) != canonical(arm['diagnostics']):
      raise ValueError('INVALID_SCREENING_DIAGNOSTICS')
  if canonical(report['arms'][0]['samples']) != canonical(report['arms'][1]['samples']):
    raise ValueError('INVALID_ALIAS_TRACE')
  if canonical(_difference(report['arms'][0]['samples'],report['arms'][2]['samples'])) != canonical(report['candidate_difference']):
    raise ValueError('INVALID_DIFFERENCE_DIAGNOSTIC')


def run_catalog(*, timeout_s=10.):
  """Freeze the complete catalog before the first execution; no selection or tuning."""
  cases = [build_screening_case(name) for name in SCREENING_CASES]
  hashes = [digest(canonical(c['manifest'])) for c in cases]
  catalog_sha = digest(canonical(hashes))
  reports = [run_screening_case(c,expected_manifest_sha256=h,timeout_s=timeout_s)
             for c,h in zip(cases,hashes,strict=True)]
  return {'catalog_sha256':catalog_sha,'reports':reports}


def main():
  import argparse
  parser = argparse.ArgumentParser(description='Synthetic native screening only; no vehicle/lane truth.')
  parser.add_argument('--scenario',choices=('all',)+SCREENING_CASES,default='all')
  parser.add_argument('--output',type=Path,required=True)
  args = parser.parse_args()
  if args.scenario == 'all':
    result = run_catalog()
  else:
    case = build_screening_case(args.scenario)
    result = {'reports':[run_screening_case(case,expected_manifest_sha256=digest(canonical(case['manifest'])),timeout_s=10.)]}
  args.output.write_bytes(canonical(result)+b'\n')


if __name__ == '__main__':
  main()
