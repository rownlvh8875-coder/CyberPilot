"""Prefrozen bounded native parameter ablations; no lane/vehicle qualification."""
import base64
import copy
from dataclasses import asdict
import itertools
import json
import math
from pathlib import Path
import platform

from openpilot.tools.cyber_autotune.a1_experiment import build_request, make_fixture
from openpilot.tools.cyber_autotune import curvature_yaw_attribution as attribution
from openpilot.tools.cyber_autotune.curvature_yaw_attribution import decorate_samples, group_diagnostics, estimate_lag
from openpilot.tools.cyber_autotune.curvature_yaw_candidate import effective_parameters
from openpilot.tools.cyber_autotune.curvature_yaw_closed_loop import closed_loop_state_sha256
from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import (
  ADAPTER_PATH, PLANT_PATH, SUPPORT_FILES, CANDIDATE_FILES, encode_request,
  controller_identity_sha256, producer_identity_sha256,
)
from openpilot.tools.cyber_autotune.curvature_yaw_native_runner import (
  run_native_transcript, admit_native_transcript, closed_loop_frames, initial_state, validate_response,
)
from openpilot.tools.cyber_autotune.curvature_yaw_plant import CurvatureYawPlantConfig, CurvatureYawPlantState, observe_curvature_yaw_step
from openpilot.tools.cyber_autotune.curvature_yaw_screening import (
  ROOT, PLANT, RESET, CANDIDATE, BLOCKERS, _inputs, _verify_upstream, diagnose_samples, _difference,
)
from openpilot.tools.cyber_autotune.lateral_closed_loop import ClosedLoopDomain, ClosedLoopBinding, frames_sha256, timebase_sha256
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest, finite, _keys, _hex, _unique_pairs, _invalid_constant

POLICY_SHA = '7bc06b4f58d72a623cc6966b2fa7e6e4048243c457276323a8961309a39ebe96'
ROLES = ('UPSTREAM_BASELINE','CYBER_CURRENT','CYBER_CANDIDATE_V1','CYBER_CANDIDATE_V2')
SOURCE = Path(__file__)
EXPERIMENT_FILES = tuple('openpilot/tools/cyber_autotune/'+name+'.py' for name in (
  'curvature_yaw_v2_search','curvature_yaw_attribution','curvature_yaw_screening','a1_experiment',
  'curvature_yaw_native_runner','native_protocol','lateral_closed_loop',
))
IDENTITY_FIELDS = ('family_sha256','policy_sha256','configuration_sha256','controller_source_sha256',
                   'car_params_sha256','software_sha256','plant_sha256','adapter_sha256','input_sha256',
                   'reset_sha256','environment_sha256','timebase_sha256')


def load_policy(raw=None):
  raw = SOURCE.with_name('candidate_v2_search_policy.json').read_bytes() if raw is None else raw
  if type(raw) is not bytes or digest(raw) != POLICY_SHA:
    raise ValueError('FROZEN_POLICY_DRIFT_NEW_VERSION_REQUIRED')
  return json.loads(raw,object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant)


def configurations():
  p=load_policy()['family']['parameters']
  return [dict(zip(('factor_high_fraction','friction_high_fraction'),values,strict=True))
          for values in itertools.product(p['factor_high_fraction']['choices'],p['friction_high_fraction']['choices'])]


def validate_config(config):
  _keys(config,('factor_high_fraction','friction_high_fraction'))
  if any(not finite(v) or v not in (0.,.5,1.) for v in config.values()):
    raise ValueError('OUTSIDE_FROZEN_FAMILY')


def candidate_spec(config,factor=4.,friction=.125):
  validate_config(config)
  family=load_policy()['family']
  points=[]
  for i,(speed,df,dr) in enumerate(zip(family['speed_breakpoints_mps'],family['v1_factor_deltas'],
                                      family['v1_friction_deltas'],strict=True)):
    high=i in family['attenuated_knot_indexes']
    points.append([speed,factor+df*(config['factor_high_fraction'] if high else 1.),
                   friction+dr*(config['friction_high_fraction'] if high else 1.)])
  return {'implementation':'SPEED_SCHEDULE','config':{'points':points}}


def case_inputs(name):
  p=load_policy()
  if name not in p['development']+p['evaluation']:
    raise ValueError('UNKNOWN_FROZEN_SCENARIO')
  frames,phases=_inputs(name.replace('mid','low') if name in p['derived_scenario_speed_mps'] else name)
  if name in p['derived_scenario_speed_mps']:
    for frame in frames:
      frame['speed_mps']=p['derived_scenario_speed_mps'][name]
  return frames,phases


def environment():
  import capnp
  import numpy
  return {'python':platform.python_version(),'numpy':numpy.__version__,'capnp':capnp.__version__,'machine':platform.machine()}


def identity(fields):
  _keys(fields,IDENTITY_FIELDS)
  if not all(_hex(v,64) for v in fields.values()):
    raise ValueError('INVALID_IDENTITY_COMPONENT')
  return digest(canonical(fields))


def verify_scoring():
  spec=attribution.SPEC
  if (spec['version']!=2 or spec['dt_s']!=.01 or attribution.DT_S!=spec['dt_s']
      or spec['speed_buckets_mps']!=[3.,10.,20.,27.]
      or (attribution.LOW_END_MPS,attribution.MID_END_MPS)!=(10.,20.)
      or attribution.REFERENCE_HISTORY_STEPS!=spec['native_history_index']
      or attribution.LAG_BOUND_STEPS!=spec['lag_bound_steps']
      or attribution.MAGNITUDE_SPLIT_1PM!=spec['magnitude_split_1pm']):
    raise ValueError('LIVE_SCORING_SPEC_DRIFT')


def _family_sha(source_sha,files,spec):
  return digest(canonical({'family':load_policy()['family'],'source_sha256':source_sha,
                           'experiment_files':files,'attribution_spec':spec}))


def _binding(request,domain,env):
  frames=closed_loop_frames(request)
  return ClosedLoopBinding(producer_identity_sha256(request),controller_identity_sha256(request),
      request['support_files'][ADAPTER_PATH],request['support_files'][PLANT_PATH],
      digest(canonical({'scope':'SYNTHETIC_DESCRIPTIVE_UNQUALIFIED','plant':request['plant_config']})),domain.identity_sha256,
      frames_sha256(frames),closed_loop_state_sha256(initial_state(request)),POLICY_SHA,
      digest(canonical(env)),timebase_sha256(frames))


def _basis(request):
  frames=closed_loop_frames(request)
  return {'controller_source_sha256':digest(canonical({
            'native':request['native']['source']['files'],
            'candidate':{p:request['support_files'][p] for p in CANDIDATE_FILES}
                         if request['controller']['implementation']=='SPEED_SCHEDULE' else {}})),
          'car_params_sha256':request['native']['car_params_sha256'],
          'software_sha256':producer_identity_sha256(request),
          'plant_sha256':digest(canonical({'source':request['support_files'][PLANT_PATH],'config':request['plant_config']})),
          'adapter_sha256':request['support_files'][ADAPTER_PATH],
          'input_sha256':digest(canonical(request['native']['frames'])),
          'reset_sha256':closed_loop_state_sha256(initial_state(request)),
          'environment_sha256':digest(canonical(environment())),'timebase_sha256':timebase_sha256(frames)}


def _manifest(case):
  r=case['requests'][0]
  verify_scoring()
  files={p:digest((ROOT/p).read_bytes()) for p in EXPERIMENT_FILES}
  family_sha=_family_sha(digest(SOURCE.read_bytes()),files,attribution.SPEC)
  identities=[]
  for role,request in zip(ROLES,case['requests'],strict=True):
    components={**_basis(request),'family_sha256':family_sha,'policy_sha256':POLICY_SHA,
                'configuration_sha256':digest(canonical({'family_config':case['config'],'controller_spec':request['controller']}))}
    identities.append({'role':role,'alias_of':ROLES[0] if role==ROLES[1] else None,
                       'components':components,'candidate_identity_sha256':identity(components),
                       'request_sha256':digest(encode_request(request)),'controller_sha256':controller_identity_sha256(request)})
  return {'version':1,'contract':'OFFLINE_FROZEN_V2_ABLATION_WITH_EXACT_CURRENT_ALIAS',
          'scenario':case['scenario'],'role':case['role'],'selection_sha256':case['selection_sha256'],'perturbation':case['perturbation'],'config':case['config'],
          'policy_sha256':POLICY_SHA,'family_sha256':family_sha,'experiment_source_sha256':digest(SOURCE.read_bytes()),'experiment_files':files,'attribution_spec':copy.deepcopy(attribution.SPEC),
          'environment':environment(),'native_source':r['native']['source'],'support_files':r['support_files'],
          'car_params_sha256':r['native']['car_params_sha256'],'frames':r['native']['frames'],'phase_labels':case['phases'],
          'plant_config':r['plant_config'],'initial_state':r['initial_state'],
          'controller_specs':[request['controller'] for request in case['requests']],'identities':identities,
          'reference_status':'NO INDEPENDENT LANE TRUTH','physical_delay_owner':'PLANT','controller_physical_delay_queue_present':False}


def build_case(name,config,*,role,perturbation=None,selection_sha256=None):
  validate_config(config)
  if selection_sha256 is not None and (not _hex(selection_sha256,64) or role=='DEVELOPMENT'):
    raise ValueError('INVALID_SELECTION_CONTEXT')
  p=load_policy()
  if role not in ('DEVELOPMENT','EVALUATION','STRESS') or (role!='STRESS' and name not in p[role.lower()]):
    raise ValueError('SCENARIO_ROLE_LEAKAGE')
  perturbation={} if perturbation is None else copy.deepcopy(perturbation)
  if (role!='STRESS' and perturbation) or len(perturbation)>1:
    raise ValueError('ONLY_FROZEN_ONE_AT_A_TIME_STRESS')
  for axis,value in perturbation.items():
    if axis not in p['robustness']['axes'] or type(value) is bool or value not in p['robustness']['axes'][axis]['choices']:
      raise ValueError('OUTSIDE_FROZEN_ROBUSTNESS_MATRIX')
  frames,phases=case_inputs(name)
  native,_=make_fixture(build_request('identity'))
  _verify_upstream(native)
  plant,reset=copy.deepcopy(PLANT),copy.deepcopy(RESET)
  for axis,value in perturbation.items():
    if axis=='delay_steps':
      plant['delay_steps']=value
      reset['command_history']=[0.]*value
    elif axis=='curvature_gain_fraction':
      for key in ('command_gain_1pm','command_speed_gain_s_per_m2','command_inv_speed_gain_per_s'):
        plant[key]*=value
    elif axis=='yaw_ar_delta':
      plant['yaw_ar']+=value
    elif axis.startswith('initial_'):
      key={'initial_curvature_1pm':'curvature_1pm','initial_yaw_rad_s':'yaw_rate_rad_s','initial_pose_y_m':'pose_y_m'}[axis]
      reset[key]=value
    elif axis in ('speed_delta_mps','roll_rad'):
      for frame in frames:
        if axis=='speed_delta_mps':
          frame['speed_mps']+=value
        else:
          frame['roll_rad']=value
    elif axis in ('pressed_shift_steps','reengage_shift_steps'):
      if name!='reengage_high':
        raise ValueError('TIMING_STRESS_REQUIRES_REENGAGEMENT')
      for i,frame in enumerate(frames):
        pressed=140+value<=i<170+value if axis=='pressed_shift_steps' else 140<=i<170
        release=230+(value if axis=='reengage_shift_steps' else 0)
        inactive=190<=i<release
        frame.update(steering_pressed=pressed,driver_torque=.2 if pressed else 0.,active=not inactive)
        phase='straight' if i<40 else 'entry' if i<120 else 'apex' if i<280 else 'exit'
        phases[i]='driver_pressed' if pressed else 'inactive' if inactive else 'reengagement' if release<=i<release+30 else phase
  from opendbc.car import structs
  with structs.CarParams.from_bytes(base64.b64decode(native['car_params_base64'])) as cp:
    cp=cp.as_builder()
  if 'cp_friction_fraction' in perturbation:
    cp.lateralTuning.torque.friction*=perturbation['cp_friction_fraction']
  raw=cp.to_bytes()
  native.update(car_params_base64=base64.b64encode(raw).decode(),car_params_sha256=digest(raw),frames=frames)
  factor,friction=float(cp.lateralTuning.torque.latAccelFactor),float(cp.lateralTuning.torque.friction)
  v1=copy.deepcopy(CANDIDATE)
  for point,original in zip(v1['config']['points'],CANDIDATE['config']['points'],strict=True):
    point[1]=factor+(original[1]-4.)
    point[2]=friction+(original[2]-.125)
  baseline={'version':2,'native':native,'support_files':{path:digest((ROOT/path).read_bytes()) for path in SUPPORT_FILES+CANDIDATE_FILES},
            'plant_config':plant,'initial_state':reset,'controller_to_plant_sign':-1.,'controller':{'implementation':'NATIVE','config':{}}}
  requests=[]
  for spec in (baseline['controller'],baseline['controller'],v1,candidate_spec(config,factor,friction)):
    request=copy.deepcopy(baseline)
    request['controller']=copy.deepcopy(spec)
    encode_request(request)
    effective_parameters(request)
    requests.append(request)
  case={'scenario':name,'role':role,'selection_sha256':selection_sha256,'perturbation':perturbation,'config':copy.deepcopy(config),'phases':phases,'requests':requests}
  case['manifest']=_manifest(case)
  return case


def freeze_case(case,expected):
  case=json.loads(canonical(case))
  _keys(case,('scenario','role','selection_sha256','perturbation','config','phases','requests','manifest'))
  if digest(canonical(case['manifest']))!=expected:
    raise ValueError('MANIFEST_FREEZE_MISMATCH')
  fresh=build_case(case['scenario'],case['config'],role=case['role'],perturbation=case['perturbation'],selection_sha256=case['selection_sha256'])
  if canonical(case)!=canonical(fresh):
    raise ValueError('SOURCE_CONFIG_INPUT_FREEZE_DRIFT')
  from openpilot.tools.cyber_autotune.native_worker import _verify_source
  _verify_source(case['requests'][0]['native']['source'])
  return case


def plant_trace(commands,frames,plant,reset):
  config=CurvatureYawPlantConfig(**plant)
  state=CurvatureYawPlantState(reset['curvature_1pm'],reset['yaw_rate_rad_s'],tuple(reset['command_history']))
  x,y,heading=0.,reset['pose_y_m'],reset['heading_rad']
  rows=[]
  for u,frame in zip(commands,frames,strict=True):
    obs=observe_curvature_yaw_step(config,state,command=-u,speed_mps=frame['speed_mps'],roll_rad=frame['roll_rad'])
    if obs.next_state is None:
      raise ValueError('PLANT_DOMAIN_FAILURE')
    state=obs.next_state
    heading+=state.yaw_rate_rad_s*plant['dt_s']
    x+=frame['speed_mps']*math.cos(heading)*plant['dt_s']
    y+=frame['speed_mps']*math.sin(heading)*plant['dt_s']
    rows.append({'curvature_1pm':state.curvature_1pm,'yaw_rate_rps':state.yaw_rate_rad_s,
                 'lateral_accel_mps2':state.yaw_rate_rad_s*frame['speed_mps'],'pose_x_m':x,'pose_y_m':y,'heading_rad':heading,
                 'applied_normalized_torque':-obs.delayed_command})
  return rows


def run_case(case,*,expected_manifest_sha256,timeout_s=10.):
  case=freeze_case(case,expected_manifest_sha256)
  m=case['manifest']
  plant=m['plant_config']
  domain=ClosedLoopDomain(digest(canonical(plant)),.01,3.,27.,.02,'PLANT',1.)
  arms=[]
  for i,request in enumerate(case['requests']):
    binding=_binding(request,domain,m['environment'])
    results,receipts=[],[]
    for _ in range(2):
      result=run_native_transcript(request,timeout_s=timeout_s)
      if result['status']!='COMPLETED':
        raise ValueError('HARD_WORKER_FAILURE:'+result['status'])
      receipt=admit_native_transcript(request,result,domain,binding,arm=ROLES[i] if i<2 else 'CYBER_CANDIDATE')
      if receipt.status!='STRUCTURAL_ADMISSION':
        raise ValueError('HARD_REPLAY_FAILURE')
      results.append(result)
      receipts.append(receipt)
    if results[0]!=results[1] or receipts[0]!=receipts[1]:
      raise ValueError('HARD_REPEATABILITY_FAILURE')
    samples=[]
    physical=plant_trace([s.requested_torque for s in receipts[0].receipt.samples],m['frames'],plant,m['initial_state'])
    for sample,frame,obs,phase,row in zip(receipts[0].receipt.samples,m['frames'],results[0]['metric_observations'],
                                         m['phase_labels'],physical,strict=True):
      values=asdict(sample)
      if any(values[k]!=v for k,v in row.items() if k in values):
        raise ValueError('PUBLIC_REPLAY_SIGN_MISMATCH')
      values.update(row)
      values.update(desired_curvature_1pm=frame['desired_curvature_1pm'],speed_mps=frame['speed_mps'],
                    phase=phase,active=frame['active'],steering_pressed=frame['steering_pressed'],
                    steering_angle_deg=obs['steering_angle_deg'],saturated=obs['saturated'])
      samples.append(values)
    samples=decorate_samples(samples,m['frames'],[o['desired_steering_angle_deg'] for o in results[0]['metric_observations']],
                             m['initial_state']['curvature_1pm'])
    arms.append({'arm':ROLES[i],'identity':m['identities'][i],
                 'repetition_result_sha256':[digest(canonical(r)) for r in results],
                 'repetition_replay_envelope_sha256':[r.envelope_sha256 for r in receipts],
                 'effective_parameters_sha256':results[0]['effective_parameters_sha256'],'native_result':results[0],
                 'samples':samples,'samples_sha256':digest(canonical(samples)),'groups':group_diagnostics(samples),
                 'diagnostics':diagnose_samples(samples,.01),
                 'lag':estimate_lag([r['desired_curvature_1pm'] for r in samples],[r['curvature_1pm'] for r in samples])})
  if _manifest(case)!=m:
    raise ValueError('EXPERIMENT_SOURCE_DRIFT_DURING_EXECUTION')
  report={'version':1,'status':'FROZEN_V2_STRUCTURAL_SYNTHETIC_EXPERIMENT','manifest':m,
          'manifest_sha256':expected_manifest_sha256,'arms':arms,'executed_runs':8,'exact_repeatability':True,
          'baseline_current_exact_alias':True,'candidate_difference':_difference(arms[0]['samples'],arms[3]['samples']),
          'reference_status':'NO INDEPENDENT LANE TRUTH','blockers':BLOCKERS.copy(),'vehicle_status':'NOT_READY',
          'performance_qualified':False,'runtime_accepted':False,'promotable':False}
  report['receipt_sha256']=digest(canonical(report))
  validate_report(report)
  return report


def validate_report(report):
  """Internal consistency, not provenance authentication or physical qualification."""
  _keys(report,('version','status','manifest','manifest_sha256','arms','executed_runs','exact_repeatability',
                'baseline_current_exact_alias','candidate_difference','reference_status','blockers','vehicle_status',
                'performance_qualified','runtime_accepted','promotable','receipt_sha256'))
  if (type(report['version']) is not int or report['version']!=1
      or report['status']!='FROZEN_V2_STRUCTURAL_SYNTHETIC_EXPERIMENT'
      or type(report['executed_runs']) is not int or report['executed_runs']!=8
      or report['exact_repeatability'] is not True or report['baseline_current_exact_alias'] is not True
      or report['reference_status']!='NO INDEPENDENT LANE TRUTH' or report['blockers']!=BLOCKERS
      or report['vehicle_status']!='NOT_READY'
      or any(report[k] is not False for k in ('performance_qualified','runtime_accepted','promotable'))
      or digest(canonical({k:v for k,v in report.items() if k!='receipt_sha256'}))!=report['receipt_sha256']):
    raise ValueError('INVALID_V2_RECEIPT_SCOPE')
  m=report['manifest']
  _keys(m,('version','contract','scenario','role','selection_sha256','perturbation','config','policy_sha256','family_sha256',
           'experiment_source_sha256','experiment_files','attribution_spec','environment','native_source','support_files','car_params_sha256',
           'frames','phase_labels','plant_config','initial_state','controller_specs','identities',
           'reference_status','physical_delay_owner','controller_physical_delay_queue_present'))
  validate_config(m['config'])
  if (type(m['version']) is not int or m['version']!=1 or digest(canonical(m))!=report['manifest_sha256']
      or m['policy_sha256']!=POLICY_SHA or not _hex(m['experiment_source_sha256'],64)
      or m['contract']!='OFFLINE_FROZEN_V2_ABLATION_WITH_EXACT_CURRENT_ALIAS'
      or m['reference_status']!='NO INDEPENDENT LANE TRUTH' or m['physical_delay_owner']!='PLANT'
      or m['controller_physical_delay_queue_present'] is not False
      or m['family_sha256']!=_family_sha(m['experiment_source_sha256'],m['experiment_files'],m['attribution_spec'])):
    raise ValueError('INVALID_V2_MANIFEST')
  verify_scoring()
  _keys(m['experiment_files'],EXPERIMENT_FILES)
  if (not all(_hex(v,64) for v in m['experiment_files'].values()) or m['attribution_spec']!=attribution.SPEC
      or m['experiment_files'][EXPERIMENT_FILES[0]]!=m['experiment_source_sha256']):
    raise ValueError('INVALID_FROZEN_SCORING_BINDING')
  fresh=build_case(m['scenario'],m['config'],role=m['role'],perturbation=m['perturbation'],selection_sha256=m['selection_sha256'])
  fm=fresh['manifest']
  if any(canonical(m[k])!=canonical(fm[k]) for k in
         ('frames','phase_labels','plant_config','initial_state','car_params_sha256','controller_specs')):
    raise ValueError('INVALID_V2_FROZEN_INPUT_OR_FAMILY')
  _keys(m['environment'],('python','numpy','capnp','machine'))
  if not all(type(v) is str and v for v in m['environment'].values()):
    raise ValueError('INVALID_V2_ENVIRONMENT')
  if type(report['arms']) is not list or len(report['arms'])!=4 or m['identities'].__class__ is not list or len(m['identities'])!=4:
    raise ValueError('INVALID_V2_ROLES')
  for i,arm in enumerate(report['arms']):
    ident=m['identities'][i]
    _keys(ident,('role','alias_of','components','candidate_identity_sha256','request_sha256','controller_sha256'))
    request=fresh['requests'][i]
    request['native']['source']=m['native_source']
    request['support_files']=m['support_files']
    components={**_basis(request),'family_sha256':m['family_sha256'],'policy_sha256':POLICY_SHA,
                'configuration_sha256':digest(canonical({'family_config':m['config'],'controller_spec':m['controller_specs'][i]}))}
    components['environment_sha256']=digest(canonical(m['environment']))
    if (ident['role']!=ROLES[i] or ident['alias_of']!=(ROLES[0] if i==1 else None)
        or ident['components']!=components or ident['candidate_identity_sha256']!=identity(components)
        or ident['request_sha256']!=digest(encode_request(request)) or ident['controller_sha256']!=controller_identity_sha256(request)
        or arm['arm']!=ROLES[i] or arm['identity']!=ident):
      raise ValueError('V2_IDENTITY_OR_SOURCE_CONFIG_BINDING_DRIFT')
    _keys(arm,('arm','identity','repetition_result_sha256','repetition_replay_envelope_sha256',
               'effective_parameters_sha256','native_result','samples','samples_sha256','groups','diagnostics','lag'))
    for k in ('repetition_result_sha256','repetition_replay_envelope_sha256'):
      if type(arm[k]) is not list or len(arm[k])!=2 or arm[k][0]!=arm[k][1] or not all(_hex(v,64) for v in arm[k]):
        raise ValueError('V2_REPEAT_RECEIPT_MISMATCH')
    result=arm['native_result']
    validate_response(request,result)
    domain=ClosedLoopDomain(digest(canonical(m['plant_config'])),.01,3.,27.,.02,'PLANT',1.)
    receipt=admit_native_transcript(request,result,domain,_binding(request,domain,m['environment']),
                                    arm=ROLES[i] if i<2 else 'CYBER_CANDIDATE')
    if (receipt.status!='STRUCTURAL_ADMISSION'
        or arm['repetition_result_sha256']!=[digest(canonical(result))]*2
        or arm['repetition_replay_envelope_sha256']!=[receipt.envelope_sha256]*2):
      raise ValueError('PERSISTED_NATIVE_REPEAT_REPLAY_BINDING_DRIFT')
    if arm['effective_parameters_sha256']!=digest(canonical([list(r) for r in effective_parameters(request)])):
      raise ValueError('V2_EFFECTIVE_PARAMETER_BINDING_DRIFT')
    samples=arm['samples']
    if type(samples) is not list or len(samples)!=len(m['frames']) or digest(canonical(samples))!=arm['samples_sha256']:
      raise ValueError('V2_SAMPLE_BINDING_DRIFT')
    if any(any(row[k]!=value for k,value in asdict(sample).items())
           for row,sample in zip(samples,receipt.receipt.samples,strict=True)):
      raise ValueError('PERSISTED_PUBLIC_REPLAY_SAMPLE_DRIFT')
    if any(row['steering_angle_deg']!=obs['steering_angle_deg'] or row['desired_steering_angle_deg']!=obs['desired_steering_angle_deg']
           or row['saturated'] is not obs['saturated']
           for row,obs in zip(samples,result['metric_observations'],strict=True)):
      raise ValueError('PERSISTED_NATIVE_OBSERVATION_DRIFT')
    physical=plant_trace([r['requested_torque'] for r in samples],m['frames'],m['plant_config'],m['initial_state'])
    from opendbc.car import structs
    from opendbc.car.vehicle_model import VehicleModel
    with structs.CarParams.from_bytes(base64.b64decode(request['native']['car_params_base64'])) as cp:
      model=VehicleModel(cp)
    pre_curvature=m['initial_state']['curvature_1pm']
    for n,(row,frame,phase,physical_row) in enumerate(zip(samples,m['frames'],m['phase_labels'],physical,strict=True)):
      _keys(row,('step_index','time_s','requested_torque','applied_normalized_torque','lateral_accel_mps2',
                 'yaw_rate_rps','pose_y_m','curvature_1pm','desired_curvature_1pm','speed_mps','phase',
                 'active','steering_pressed','steering_angle_deg','saturated','heading_rad','pose_x_m',
                 'speed_bucket','curvature_sign','curvature_magnitude','desired_steering_angle_deg',
                 'steering_angle_residual_deg','command_derivative_per_s','torque_derivative_per_s',
                 'curvature_residual_1pm','native_aligned_desired_curvature_1pm','native_aligned_residual_1pm',
                 'inactive_to_active','pressed_to_release'))
      model.update_params(frame['stiffness_factor'],frame['steer_ratio'])
      actual_angle=math.degrees(model.get_steer_from_curvature(-pre_curvature,frame['speed_mps'],frame['roll_rad']))+frame['angle_offset_deg']
      desired_angle=math.degrees(model.get_steer_from_curvature(-frame['desired_curvature_1pm'],frame['speed_mps'],frame['roll_rad']))+frame['angle_offset_deg']
      wire_state=structs.CarState()
      wire_state.steeringAngleDeg=actual_angle
      pre_curvature=row['curvature_1pm']
      if (row['steering_angle_deg']!=float(wire_state.steeringAngleDeg) or row['desired_steering_angle_deg']!=desired_angle
          or type(row['step_index']) is not int or row['step_index']!=n or row['time_s']!=frame['time_ns']*1e-9 or row['phase']!=phase
          or row['desired_curvature_1pm']!=frame['desired_curvature_1pm'] or row['speed_mps']!=frame['speed_mps']
          or row['active'] is not frame['active'] or row['steering_pressed'] is not frame['steering_pressed']
          or any(type(row[k]) is not bool for k in ('saturated','inactive_to_active','pressed_to_release'))
          or not all(finite(v) for v in row.values() if type(v) is not str and type(v) is not bool)
          or abs(row['requested_torque'])>1. or abs(row['applied_normalized_torque'])>1.
          or (not row['active'] and row['requested_torque']!=0.)
          or any(row[k]!=v for k,v in physical_row.items())):
        raise ValueError('V2_PHYSICAL_OR_HARD_FAILURE')
    decorated=decorate_samples(samples,m['frames'],[s['desired_steering_angle_deg'] for s in samples],m['initial_state']['curvature_1pm'])
    if (decorated!=samples or group_diagnostics(samples)!=arm['groups'] or diagnose_samples(samples,.01)!=arm['diagnostics']
        or estimate_lag([s['desired_curvature_1pm'] for s in samples],[s['curvature_1pm'] for s in samples])!=arm['lag']):
      raise ValueError('V2_ATTRIBUTION_DRIFT')
  if report['arms'][0]['samples']!=report['arms'][1]['samples'] or m['identities'][0]['components']!=m['identities'][1]['components']:
    raise ValueError('V2_CURRENT_ALIAS_DRIFT')
  if _difference(report['arms'][0]['samples'],report['arms'][3]['samples'])!=report['candidate_difference']:
    raise ValueError('V2_DIFFERENCE_DRIFT')


def summarize(report):
  validate_report(report)
  m=report['manifest']
  result={'scenario':m['scenario'],'role':m['role'],'selection_sha256':m['selection_sha256'],'perturbation':m['perturbation'],
          'manifest_sha256':report['manifest_sha256'],'receipt_sha256':report['receipt_sha256'],
          'config':m['config'],'identities':m['identities'],'executed_runs':report['executed_runs'],
          'groups':[a['groups'] for a in report['arms']],'diagnostics':[a['diagnostics'] for a in report['arms']],
          'lags':[a['lag'] for a in report['arms']],'candidate_difference':report['candidate_difference'],'hard_pass':True}
  result['summary_sha256']=digest(canonical(result))
  return json.loads(canonical(result))  # sever downstream mutation of admitted report


def compare_summary(summary):
  if (summary.get('hard_pass') is not True
      or digest(canonical({k:v for k,v in summary.items() if k!='summary_sha256'}))!=summary.get('summary_sha256')
      or type(summary.get('groups')) is not list or len(summary['groups'])!=4
      or not summary['groups'][0] or summary['groups'][0]!=summary['groups'][1]):
    raise ValueError('INVALID_OR_MUTATED_ADMITTED_SUMMARY')
  metrics=load_policy()['metrics']
  baseline,v1,v2=summary['groups'][0],summary['groups'][2],summary['groups'][3]
  if not (len(baseline)==len(v1)==len(v2)):
    raise ValueError('GROUP_ALIGNMENT_MISMATCH')
  failures,changes,vector=[],[],[]
  for b,a,c in zip(baseline,v1,v2,strict=True):
    cell={k:b[k] for k in ('speed_bucket','curvature_magnitude','curvature_sign','phase')}
    if any(any(row[k]!=value for k,value in cell.items()) for row in (a,c)):
      raise ValueError('GROUP_PHASE_ALIGNMENT_MISMATCH')
    reference=b if b['speed_bucket']=='HIGH' else a
    for metric in metrics:
      if not all(finite(row[metric]) and row[metric]>=0. for row in (b,a,c)):
        raise ValueError('INVALID_SCREENING_METRIC')
      vector.append(c[metric])
      if c[metric]>reference[metric]:
        failures.append({'scenario':summary['scenario'],**cell,'metric':metric,
                         'value':c[metric],'reference':reference[metric],'delta':c[metric]-reference[metric]})
      if c[metric]!=a[metric]:
        changes.append({'scenario':summary['scenario'],**cell,'metric':metric,'delta_vs_v1':c[metric]-a[metric]})
  return {'failures':failures,'v1_changes':changes,'vector':vector}


def validate_failure(report):
  _keys(report,('scenario','role','selection_sha256','perturbation','config','manifest_sha256','status','hard_pass',
                'reason','performance_qualified','receipt_sha256'))
  validate_config(report['config'])
  if (report['status']!='HARD_REJECTED' or report['hard_pass'] is not False
      or report['performance_qualified'] is not False or type(report['reason']) is not str or not report['reason']
      or not _hex(report['manifest_sha256'],64)
      or digest(canonical({k:v for k,v in report.items() if k!='receipt_sha256'}))!=report['receipt_sha256']):
    raise ValueError('INVALID_HARD_FAILURE_RECEIPT')
  return json.loads(canonical(report))


def admitted_summary(report):
  # No caller supplied summary or aggregate hard-pass flag crosses admission.
  return validate_failure(report) if report.get('status')=='HARD_REJECTED' else summarize(report)


def _pareto_choice(receipts):
  eligible=[r for r in receipts if r['eligible']]
  pareto=[a for a in eligible if not any(all(x<=y for x,y in zip(b['vector'],a['vector'],strict=True))
                                         and any(x<y for x,y in zip(b['vector'],a['vector'],strict=True)) for b in eligible)]
  chosen=min(pareto,key=lambda r:(r['config']['factor_high_fraction'],r['config']['friction_high_fraction'],
                                  digest(canonical(r['config'])))) if pareto else None
  return pareto,chosen


def select_development(entries):
  p=load_policy()
  if len(entries)!=p['candidate_count']:
    raise ValueError('INCOMPLETE_FROZEN_ENUMERATION')
  receipts=[]
  for config,entry in zip(configurations(),entries,strict=True):
    _keys(entry,('config','reports'))
    summaries=[admitted_summary(r) for r in entry['reports']]
    if entry['config']!=config or [s['scenario'] for s in summaries]!=p['development']:
      raise ValueError('FROZEN_ENUMERATION_ORDER_DRIFT')
    if any(s['role']!='DEVELOPMENT' or s['config']!=config for s in summaries):
      raise ValueError('EVALUATION_SELECTION_LEAKAGE')
    hard_pass=all(s['hard_pass'] is True for s in summaries)
    checks=[compare_summary(s) for s in summaries] if hard_pass else []
    failures=[f for check in checks for f in check['failures']]
    receipt={'config':config,'eligible':hard_pass and not failures,'hard_pass':hard_pass,
             'case_receipts':[s['receipt_sha256'] for s in summaries],'failures':failures,
             'vector':[v for check in checks for v in check['vector']]}
    receipt['receipt_sha256']=digest(canonical(receipt))
    receipts.append(receipt)
  pareto,chosen=_pareto_choice(receipts)
  result={'version':1,'policy_sha256':POLICY_SHA,'selection_role':'DEVELOPMENT_ONLY','candidate_count':len(receipts),
          'receipts':receipts,'pareto_receipts':[r['receipt_sha256'] for r in pareto],
          'selected_config':chosen['config'] if chosen else None,'selected_receipt_sha256':chosen['receipt_sha256'] if chosen else None,
          'performance_qualified':False,'real_performance_status':'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE'}
  result['receipt_sha256']=digest(canonical(result))
  return result


def _classify_admitted(summaries):
  hard=[s for s in summaries if s['hard_pass'] is not True]
  if hard:
    return {'status':'REJECTED','hard_failures':hard,'failures':[],'v1_changes':[],'performance_qualified':False}
  checks=[compare_summary(s) for s in summaries]
  failures=[f for c in checks for f in c['failures']]
  changes=[v for c in checks for v in c['v1_changes']]
  status='REJECTED' if failures else 'SCREENING_IMPROVED' if changes and all(v['delta_vs_v1']<=0 for v in changes) else 'TRADEOFF_ONLY'
  return {'status':status,'failures':failures,'v1_changes':changes,'performance_qualified':False}


def _development_vector_size():
  total=0
  for name in load_policy()['development']:
    frames,phases=case_inputs(name)
    cells=set()
    for frame,phase in zip(frames,phases,strict=True):
      k=frame['desired_curvature_1pm']
      cells.add((attribution.speed_bucket(frame['speed_mps']),
                 'ZERO' if k==0 else 'GENTLE' if abs(k)<=attribution.MAGNITUDE_SPLIT_1PM else 'SHARP',
                 'POSITIVE' if k>0 else 'NEGATIVE' if k<0 else 'ZERO',phase))
    total+=len(cells)*len(load_policy()['metrics'])
  return total


def validate_selection(selection,expected_sha256):
  _keys(selection,('version','policy_sha256','selection_role','candidate_count','receipts','pareto_receipts',
                   'selected_config','selected_receipt_sha256','performance_qualified','real_performance_status','receipt_sha256'))
  if (not _hex(expected_sha256,64) or selection['receipt_sha256']!=expected_sha256
      or digest(canonical({k:v for k,v in selection.items() if k!='receipt_sha256'}))!=expected_sha256
      or type(selection['version']) is not int or selection['version']!=1
      or selection['policy_sha256']!=POLICY_SHA or selection['selection_role']!='DEVELOPMENT_ONLY'
      or type(selection['candidate_count']) is not int or selection['candidate_count']!=9
      or selection['performance_qualified'] is not False
      or selection['real_performance_status']!='BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE'
      or type(selection['receipts']) is not list or len(selection['receipts'])!=9):
    raise ValueError('FROZEN_SELECTION_RECEIPT_DRIFT')
  lengths=set()
  for config,r in zip(configurations(),selection['receipts'],strict=True):
    _keys(r,('config','eligible','hard_pass','case_receipts','failures','vector','receipt_sha256'))
    if (r['config']!=config or type(r['hard_pass']) is not bool or type(r['eligible']) is not bool
        or r['eligible']!=(r['hard_pass'] and not r['failures'])
        or digest(canonical({k:v for k,v in r.items() if k!='receipt_sha256'}))!=r['receipt_sha256']
        or type(r['case_receipts']) is not list or len(r['case_receipts'])!=4 or not all(_hex(v,64) for v in r['case_receipts'])
        or type(r['vector']) is not list or not all(finite(v) and v>=0 for v in r['vector'])
        or (r['hard_pass'] and len(r['vector'])!=_development_vector_size()) or (not r['hard_pass'] and (r['vector'] or r['failures']))):
      raise ValueError('FROZEN_CANDIDATE_SELECTION_RECEIPT_DRIFT')
    if r['hard_pass']:
      lengths.add(len(r['vector']))
    for failure in r['failures']:
      if (failure['metric'] not in load_policy()['metrics'] or failure['scenario'] not in load_policy()['development']
          or not all(finite(failure[k]) and failure[k]>=0 for k in ('value','reference'))
          or failure['value']<=failure['reference'] or failure['delta']!=failure['value']-failure['reference']):
        raise ValueError('INVALID_SELECTION_FAILURE')
  if len(lengths)>1:
    raise ValueError('INCOMPLETE_SELECTION_METRIC_VECTOR')
  pareto,chosen=_pareto_choice(selection['receipts'])
  if (selection['pareto_receipts']!=[r['receipt_sha256'] for r in pareto]
      or selection['selected_config']!=(chosen['config'] if chosen else None)
      or selection['selected_receipt_sha256']!=(chosen['receipt_sha256'] if chosen else None)):
    raise ValueError('PARETO_OR_FROZEN_TIE_RULE_DRIFT')


def classify(reports,*,selection=None,expected_selection_sha256=None,expected_evaluation_sha256=None):
  if selection is None:
    raise ValueError('FROZEN_SELECTION_CONTEXT_REQUIRED')
  validate_selection(selection,expected_selection_sha256)
  summaries=[admitted_summary(r) for r in reports]
  if ([s['scenario'] for s in summaries]!=load_policy()['evaluation']
      or any(s['role']!='EVALUATION' or s['config']!=selection['selected_config']
             or s['selection_sha256']!=expected_selection_sha256 for s in summaries)
      or digest(canonical([s['manifest_sha256'] for s in summaries]))!=expected_evaluation_sha256):
    raise ValueError('INCOMPLETE_OR_UNSELECTED_FROZEN_EVALUATION')
  verdict=_classify_admitted(summaries)
  verdict.update(selection_sha256=expected_selection_sha256,evaluation_manifest_list_sha256=expected_evaluation_sha256)
  return verdict


def classify_case(report):
  # Explicit per-case diagnostic, never a final eleven-case evaluation verdict.
  return _classify_admitted([admitted_summary(report)])


def execute_case(case,sha):
  """Fail closed with a bounded failure receipt; hard failure cannot become a score."""
  try:
    report=run_case(case,expected_manifest_sha256=sha)
    return report,summarize(report)
  except ValueError as error:
    failure={'scenario':case['scenario'],'role':case['role'],'selection_sha256':case['selection_sha256'],'perturbation':case['perturbation'],
             'config':case['config'],'manifest_sha256':sha,'status':'HARD_REJECTED',
             'hard_pass':False,'reason':str(error),'performance_qualified':False}
    failure['receipt_sha256']=digest(canonical(failure))
    return failure,copy.deepcopy(failure)


def run_search(output_directory):
  """Freeze all DEV manifests before workers; freeze selection before opening new EVAL output."""
  out=Path(output_directory)
  out.mkdir(parents=True,exist_ok=True)
  if any(out.iterdir()):
    raise ValueError('FRESH_EXPERIMENT_DIRECTORY_REQUIRED')
  configs=configurations()
  dev=[[build_case(name,c,role='DEVELOPMENT') for name in load_policy()['development']] for c in configs]
  freeze={'policy_sha256':POLICY_SHA,'development_manifest_sha256':[[digest(canonical(c['manifest'])) for c in cases] for cases in dev]}
  (out/'development-freeze.json').write_bytes(canonical(freeze)+b'\n')
  entries,admission_entries=[],[]
  for config,cases,hashes in zip(configs,dev,freeze['development_manifest_sha256'],strict=True):
    summaries,reports=[],[]
    for case,sha in zip(cases,hashes,strict=True):
      report,summary=execute_case(case,sha)
      summaries.append(summary)
      reports.append(report)
      (out/(sha+'.json')).write_bytes(canonical(report)+b'\n')
    entries.append({'config':config,'cases':summaries,'hard_pass':all(s['hard_pass'] for s in summaries)})
    admission_entries.append({'config':config,'reports':reports})
    print('DEVELOPMENT_CONFIG_COMPLETED',config,flush=True)
  selection=select_development(admission_entries)
  selection_bytes=canonical(selection)
  (out/'selection.json').write_bytes(selection_bytes+b'\n')
  if selection['selected_config'] is None:
    result={'selection':selection,'evaluation':[],'verdict':{'status':'REJECTED','reason':'NO_DEVELOPMENT_ELIGIBLE_CONFIG'}}
  else:
    cases=[build_case(name,selection['selected_config'],role='EVALUATION',selection_sha256=selection['receipt_sha256']) for name in load_policy()['evaluation']]
    hashes=[digest(canonical(c['manifest'])) for c in cases]
    (out/'evaluation-freeze.json').write_bytes(canonical({'selection_sha256':selection['receipt_sha256'],'manifest_sha256':hashes})+b'\n')
    reports,summaries=[],[]
    for case,sha in zip(cases,hashes,strict=True):
      if canonical(json.loads((out/'selection.json').read_bytes()))!=selection_bytes:
        raise ValueError('SELECTION_CHANGED_BEFORE_EVALUATION')
      report,summary=execute_case(case,sha)
      reports.append(report)
      summaries.append(summary)
      print('EVALUATION_COMPLETED',case['scenario'],flush=True)
    (out/'evaluation.json').write_bytes(canonical({'reports':reports})+b'\n')
    result={'selection':selection,'evaluation':summaries,'verdict':classify(reports,selection=selection,expected_selection_sha256=selection['receipt_sha256'],
                                                               expected_evaluation_sha256=digest(canonical(hashes)))}
  result.update(policy_sha256=POLICY_SHA,development=entries,reference_status='NO INDEPENDENT LANE TRUTH',
                vehicle_status=load_policy()['vehicle_status'],real_performance_status='BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE')
  result['receipt_sha256']=digest(canonical(result))
  (out/'search-summary.json').write_bytes(canonical(result)+b'\n')
  return result


if __name__=='__main__':
  import argparse
  parser=argparse.ArgumentParser(description='Bounded synthetic screening only; no vehicle qualification.')
  parser.add_argument('--output-directory',type=Path,required=True)
  run_search(parser.parse_args().output_directory)
