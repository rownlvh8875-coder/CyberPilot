"""Bounded passive PID observations; consistency evidence, not authentication."""
import base64
import copy
import math
import json
from pathlib import Path
import sys

from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import encode_request
from openpilot.tools.cyber_autotune.curvature_yaw_native_runner import validate_response
from openpilot.tools.cyber_autotune.curvature_yaw_candidate import effective_parameters
from openpilot.tools.cyber_autotune.native_runner import _run_process, MAX_RESPONSE_BYTES
from openpilot.tools.cyber_autotune.native_protocol import canonical,digest,finite,_hex,_keys,_unique_pairs,_invalid_constant

WORKER=Path(__file__).with_name('curvature_yaw_diagnostic_worker.py')
FIELDS=('step_index','requested_torque','active','factor','friction','measurement','setpoint','error','future_lataccel',
        'raw_jerk','filtered_jerk','feedforward','delay_frames','lookahead_index','pid_p','pid_i','pid_d','pid_f','pid_control',
        'pos_limit','neg_limit','unclipped','integrator_previous','pid_limit_clipped','integrator_frozen','kp','ki','history_sha256')



def reconstruct_observations(request,native):
  """Independent arithmetic reconstruction of the pinned stock law, no update call.

  Read-only history reconstruction is a validator, not an actuator command queue.
  Wire speed/angle, input history, filter and PID anti-windup ordering match the
  admitted native core. Any core revision needs a new diagnostic implementation.
  """
  import numpy as np
  from opendbc.car import structs
  from opendbc.car.vehicle_model import VehicleModel
  from opendbc.car.lateral import get_friction,FRICTION_THRESHOLD
  from openpilot.common.constants import ACCELERATION_DUE_TO_GRAVITY
  with structs.CarParams.from_bytes(base64.b64decode(request['native']['car_params_base64'])) as cp:
    model=VehicleModel(cp)
    params=cp.lateralTuning.torque.as_builder()
  history=[0.]*100
  alpha=.01/(1/(2*np.pi*1.2)+.01)
  filtered=0.
  p=i=d=f=control=pid_speed=0.
  rows=[]
  for n,(frame,obs,parameters) in enumerate(zip(request['native']['frames'],native['metric_observations'],
                                               effective_parameters(request),strict=True)):
    params.latAccelFactor,params.latAccelOffset,params.friction=parameters
    model.update_params(frame['stiffness_factor'],frame['steer_ratio'])
    wire=structs.CarState()
    wire.vEgo=frame['speed_mps']
    wire.steeringAngleDeg=obs['steering_angle_deg']
    speed=float(wire.vEgo)
    measurement=-model.calc_curvature(math.radians(wire.steeringAngleDeg-frame['angle_offset_deg']),speed,frame['roll_rad'])*speed**2
    future=frame['desired_curvature_1pm']*speed**2
    history=history[1:]+[future]
    delay=int(np.clip(frame['lateral_delay_s']/.01+1,1,100))
    lookahead=int(np.clip(-delay+19,-99,-2))
    setpoint=history[-delay]
    error=setpoint-measurement
    raw=(history[lookahead+1]-history[lookahead-1])/(2*.01)
    filtered=(1.-alpha)*filtered+alpha*raw
    deadzone=abs(model.calc_curvature(math.radians(params.steeringAngleDeadzoneDeg),speed,0.))*speed**2
    ff=future-frame['roll_rad']*ACCELERATION_DUE_TO_GRAVITY
    ff-=params.latAccelOffset
    ff+=get_friction(error+.3*filtered,deadzone,FRICTION_THRESHOLD,params)
    previous=i
    freeze=not frame['active'] or frame['safety_limited'] or frame['steering_pressed'] or speed<5.
    positive,negative=parameters[0],-parameters[0]
    if frame['active']:
      pid_speed=speed
      pid_error=float(np.float32(error))  # stock pid_log.error wire readback
      p=float(np.interp(pid_speed,[1,1.5,2.,3.,5,7.5,10,15,30],[250,120,65,30,11.5,5.5,3.5,2.,.8]))*pid_error
      d=0.
      f=ff
      if not freeze:
        proposed=i+.15*.01*pid_error
        trial=p+proposed+d+f
        i=float(np.clip(proposed,i if trial<negative else negative,i if trial>positive else positive))
      control=float(np.clip(p+i+d+f,negative,positive))
    kp=float(np.interp(pid_speed,[1,1.5,2.,3.,5,7.5,10,15,30],[250,120,65,30,11.5,5.5,3.5,2.,.8]))
    rows.append({'step_index':n,'requested_torque':-control/parameters[0] if frame['active'] else 0.,
      'active':frame['active'],'factor':parameters[0],'friction':parameters[2],'measurement':float(measurement),
      'setpoint':float(setpoint),'error':float(error),'future_lataccel':float(future),'raw_jerk':float(raw),
      'filtered_jerk':float(filtered),'feedforward':float(ff),'delay_frames':float(delay),'lookahead_index':float(lookahead),
      'pid_p':float(p),'pid_i':float(i),'pid_d':float(d),'pid_f':float(f),'pid_control':float(control),
      'pos_limit':positive,'neg_limit':negative,'unclipped':float(p+i+d+f),'integrator_previous':float(previous),
      'pid_limit_clipped':bool(frame['active'] and control!=p+i+d+f),'integrator_frozen':freeze,
      'kp':kp,'ki':.15,'history_sha256':digest(canonical([float(v) for v in history]))})
  return rows

def validate_diagnostics(request,native,result):
  validate_response(request,native)
  _keys(result,('scope','producer_source_sha256','supervisor_source_sha256','request_sha256','native_result','observations',
                'raw_result','repetition_sha256','physical_delay_owner','receipt_sha256'))
  raw=result['raw_result']
  _keys(raw,('producer_source_sha256','request_sha256','native_result','observations'))
  if (result['scope']!='PASSIVE_SYNTHETIC_PID_DIAGNOSTIC_NOT_QUALIFICATION'
      or result['physical_delay_owner']!='PLANT' or result['native_result']!=native or raw['native_result']!=native
      or result['observations']!=raw['observations']
      or result['producer_source_sha256']!=digest(WORKER.read_bytes())
      or result['supervisor_source_sha256']!=digest(Path(__file__).read_bytes())
      or result['producer_source_sha256']!=raw['producer_source_sha256']
      or result['request_sha256']!=raw['request_sha256'] or result['request_sha256']!=digest(encode_request(request))
      or result['repetition_sha256']!=[digest(canonical(raw))]*2
      or digest(canonical({k:v for k,v in result.items() if k!='receipt_sha256'}))!=result['receipt_sha256']):
    raise ValueError('DIAGNOSTIC_BINDING_OR_CONTAMINATION')
  rows=result['observations']
  if type(rows) is not list or len(rows)!=len(request['native']['frames']):
    raise ValueError('DIAGNOSTIC_COUNT')
  if rows!=reconstruct_observations(request,native):
    raise ValueError('DIAGNOSTIC_PINNED_STATE_RECONSTRUCTION_DRIFT')
  for i,(row,frame,parameters,step) in enumerate(zip(rows,request['native']['frames'],effective_parameters(request),
                                                   native['controller_transcript'],strict=True)):
    _keys(row,FIELDS)
    if (type(row['step_index']) is not int or row['step_index']!=i or row['active'] is not frame['active']
        or type(row['integrator_frozen']) is not bool or type(row['pid_limit_clipped']) is not bool
        or not _hex(row['history_sha256'],64)
        or not all(finite(row[k]) for k in FIELDS if k not in ('step_index','active','integrator_frozen','pid_limit_clipped','history_sha256'))
        or row['requested_torque']!=step['requested_normalized_torque'] or row['factor']!=parameters[0] or row['friction']!=parameters[2]
        or row['error']!=row['setpoint']-row['measurement']
        or row['unclipped']!=row['pid_p']+row['pid_i']+row['pid_d']+row['pid_f']
        or (i and row['integrator_previous']!=rows[i-1]['pid_i'])
        or (frame['active'] and row['pid_control']!=min(row['pos_limit'],max(row['neg_limit'],row['unclipped'])))
        or (row['integrator_frozen'] and row['pid_i']!=row['integrator_previous'])
        or (not frame['active'] and row['requested_torque']!=0.)):
      raise ValueError('DIAGNOSTIC_OBSERVATION_DRIFT')


def run_diagnostics(request,native,*,timeout_s=30.):
  validate_response(request,native)
  if sys.platform!='linux' or not finite(timeout_s) or not 0<timeout_s<=60:
    raise ValueError('DIAGNOSTIC_PLATFORM_OR_TIMEOUT')
  request=json.loads(encode_request(request))
  worker_sha=digest(WORKER.read_bytes())
  supervisor_sha=digest(Path(__file__).read_bytes())
  payload=canonical({'request':request,'producer_source_sha256':worker_sha})
  results=[]
  for _ in range(2):
    outcome=_run_process([sys.executable,'-I',str(WORKER.resolve())],payload,timeout_s)
    if outcome.status!='EXITED' or outcome.returncode!=0 or len(outcome.stdout)>MAX_RESPONSE_BYTES:
      raise ValueError('DIAGNOSTIC_WORKER_FAILURE')
    results.append(json.loads(outcome.stdout,object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant))
  if results[0]!=results[1] or results[0]['native_result']!=native:
    raise ValueError('PASSIVE_PROFILER_OUTPUT_OR_REPEAT_MISMATCH')
  result={'scope':'PASSIVE_SYNTHETIC_PID_DIAGNOSTIC_NOT_QUALIFICATION',
          'producer_source_sha256':worker_sha,'supervisor_source_sha256':supervisor_sha,
          'request_sha256':digest(encode_request(request)),'native_result':copy.deepcopy(native),
          'observations':copy.deepcopy(results[0]['observations']),'raw_result':results[0],
          'repetition_sha256':[digest(canonical(r)) for r in results],'physical_delay_owner':'PLANT'}
  result['receipt_sha256']=digest(canonical(result))
  validate_diagnostics(request,native,result)
  return result
