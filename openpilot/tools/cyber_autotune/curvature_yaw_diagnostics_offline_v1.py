"""Bounded passive PID observations; consistency evidence, not authentication."""
import base64
import copy
import math
import json
from dataclasses import dataclass
from typing import TypedDict, TypeGuard
from pathlib import Path
from threading import Lock
import sys

from openpilot.tools.cyber_autotune.curvature_yaw_native_protocol import encode_request, MAX_REQUEST_BYTES
from openpilot.tools.cyber_autotune.curvature_yaw_native_runner import validate_response
from openpilot.tools.cyber_autotune.curvature_yaw_candidate import effective_parameters
from openpilot.tools.cyber_autotune.native_runner import _run_process, MAX_RESPONSE_BYTES
from openpilot.tools.cyber_autotune.native_protocol import canonical,digest,finite,_hex,_keys,_unique_pairs,_invalid_constant

WORKER=Path(__file__).with_name('curvature_yaw_diagnostic_worker.py')
FIELDS=('step_index','requested_torque','active','factor','friction','measurement','setpoint','error','future_lataccel',
        'raw_jerk','filtered_jerk','feedforward','delay_frames','lookahead_index','pid_p','pid_i','pid_d','pid_f','pid_control',
        'pos_limit','neg_limit','unclipped','integrator_previous','pid_limit_clipped','integrator_frozen','kp','ki','history_sha256')



def _require_offline(offline_publication_v1: object) -> None:
  if type(offline_publication_v1) is not bool or offline_publication_v1 is not True:
    raise ValueError('OFFLINE_PUBLICATION_OPT_IN_REQUIRED')


class _Observation(TypedDict):
  step_index: int
  requested_torque: int | float
  active: bool
  factor: int | float
  friction: int | float
  measurement: int | float
  setpoint: int | float
  error: int | float
  future_lataccel: int | float
  raw_jerk: int | float
  filtered_jerk: int | float
  feedforward: int | float
  delay_frames: int | float
  lookahead_index: int | float
  pid_p: int | float
  pid_i: int | float
  pid_d: int | float
  pid_f: int | float
  pid_control: int | float
  pos_limit: int | float
  neg_limit: int | float
  unclipped: int | float
  integrator_previous: int | float
  pid_limit_clipped: bool
  integrator_frozen: bool
  kp: int | float
  ki: int | float
  history_sha256: str


@dataclass(frozen=True, slots=True)
class VerifiedObservation:
  """Owned scalar observation; published only after complete validation."""
  step_index: int
  requested_torque: int | float
  active: bool
  factor: int | float
  friction: int | float
  measurement: int | float
  setpoint: int | float
  error: int | float
  future_lataccel: int | float
  raw_jerk: int | float
  filtered_jerk: int | float
  feedforward: int | float
  delay_frames: int | float
  lookahead_index: int | float
  pid_p: int | float
  pid_i: int | float
  pid_d: int | float
  pid_f: int | float
  pid_control: int | float
  pos_limit: int | float
  neg_limit: int | float
  unclipped: int | float
  integrator_previous: int | float
  pid_limit_clipped: bool
  integrator_frozen: bool
  kp: int | float
  ki: int | float
  history_sha256: str


def _checked_fields(value: object, expected: tuple[str, ...]) -> dict[object, object]:
  # The historical exact-fields validator retains first refusal and its message.
  _keys(value, expected)
  if isinstance(value, dict):
    return value
  raise ValueError('INVALID_FIELDS')


def _observation_prefix(row: dict[object, object], i: int, active: object) -> TypeGuard[_Observation]:
  # Narrow this owned dictionary, never a different alias.
  if type(row) is not dict or set(row)!=set(FIELDS) or not all(isinstance(k, str) for k in row):
    return False
  if (type(row['step_index']) is not int or row['step_index']!=i or row['active'] is not active
      or type(row['integrator_frozen']) is not bool or type(row['pid_limit_clipped']) is not bool
      or not _hex(row['history_sha256'],64)
      or not all(finite(row[k]) for k in FIELDS
                 if k not in ('step_index','active','integrator_frozen','pid_limit_clipped','history_sha256'))):
    return False
  # Validated frame identity implies bool; also prove it for direct callers.
  return type(row['active']) is bool


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

def _checked_owned_view(request, native, result: object) -> tuple[VerifiedObservation, ...]:
  validate_response(request,native)
  result=_checked_fields(result,('scope','producer_source_sha256','supervisor_source_sha256','request_sha256','native_result','observations',
                'raw_result','repetition_sha256','physical_delay_owner','receipt_sha256'))
  raw=result['raw_result']
  raw=_checked_fields(raw,('producer_source_sha256','request_sha256','native_result','observations'))
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
  verified: list[VerifiedObservation] = []
  for i,(raw_row,frame,parameters,step) in enumerate(zip(rows,request['native']['frames'],effective_parameters(request),
                                                   native['controller_transcript'],strict=True)):
    row=_checked_fields(raw_row,FIELDS).copy()
    if not _observation_prefix(row,i,frame['active']):
      raise ValueError('DIAGNOSTIC_OBSERVATION_DRIFT')
    if (row['requested_torque']!=step['requested_normalized_torque'] or row['factor']!=parameters[0] or row['friction']!=parameters[2]
        or row['error']!=row['setpoint']-row['measurement']
        or row['unclipped']!=row['pid_p']+row['pid_i']+row['pid_d']+row['pid_f']
        or (i and row['integrator_previous']!=verified[i-1].pid_i)
        or (frame['active'] and row['pid_control']!=min(row['pos_limit'],max(row['neg_limit'],row['unclipped'])))
        or (row['integrator_frozen'] and row['pid_i']!=row['integrator_previous'])
        or (not frame['active'] and row['requested_torque']!=0.)):
      raise ValueError('DIAGNOSTIC_OBSERVATION_DRIFT')
    verified.append(VerifiedObservation(**row))
  return tuple(verified)


def validate_diagnostics(request,native,result,*,offline_publication_v1: object = False):
  _require_offline(offline_publication_v1)
  _checked_owned_view(request,native,result)



def run_diagnostics(request,native,*,timeout_s=30.,offline_publication_v1: object = False):
  _require_offline(offline_publication_v1)
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
  validate_diagnostics(request,native,result,offline_publication_v1=True)
  return result


# New packet cap derives from unchanged request/native/two diagnostic response caps.
# This is an additional offline interface limit, not an E2 resource-cap amendment.
MAX_SNAPSHOT_BYTES = MAX_REQUEST_BYTES + 3 * MAX_RESPONSE_BYTES + 1024


def checked_diagnostics_snapshot(payload: bytes, *, offline_publication_v1: object = False) -> tuple[VerifiedObservation, ...]:
  """Validate exactly one immutable packet; no caller-owned tree is consumed.

  This does not certify how a producer captured its original mutable state.
  No decoded mutable object escapes the boundary.
  """
  _require_offline(offline_publication_v1)
  if type(payload) is not bytes or not 0 < len(payload) <= MAX_SNAPSHOT_BYTES:
    raise ValueError('DIAGNOSTIC_SNAPSHOT_BYTES_REQUIRED')
  decoded: object = json.loads(payload,object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant)
  envelope = _checked_fields(decoded,('request','native','result'))
  if canonical(envelope)!=payload:
    raise ValueError('DIAGNOSTIC_SNAPSHOT_NONCANONICAL')
  return _checked_owned_view(envelope['request'],envelope['native'],envelope['result'])


def checked_diagnostics_view(request, native, result: object, *, offline_publication_v1: object = False) -> tuple[VerifiedObservation, ...]:
  """Legacy raw adapter: preserve stable-input errors, then check owned bytes.

  Capture of caller-owned mutable trees is NOT ATOMIC. For concurrent use,
  producers must supply a privately constructed immutable packet instead.
  The preliminary live validation supplies no safety claim or published view.
  """
  _require_offline(offline_publication_v1)
  _checked_owned_view(request,native,result)
  payload = canonical({'request':request,'native':native,'result':result})
  return checked_diagnostics_snapshot(payload,offline_publication_v1=True)


@dataclass(frozen=True, slots=True)
class PublishedDiagnostics:
  """A complete immutable publication, not a raw-input ownership certificate."""
  generation: int
  packet_sha256: str
  observations: tuple[VerifiedObservation, ...]


class DiagnosticSnapshotOwner:
  """Publish/read only checked immutable packets under one shared lock.

  All supported writers use publish(); consumers use read(). No mutable input
  tree is returned. Generation orders publication, not original acquisition.
  """
  def __init__(self, payload: bytes, *, offline_publication_v1: object = False):
    _require_offline(offline_publication_v1)
    self._lock = Lock()
    observations = checked_diagnostics_snapshot(payload,offline_publication_v1=True)
    self._current = PublishedDiagnostics(0,digest(payload),observations)

  def publish(self, payload: bytes, *, offline_publication_v1: object = False) -> PublishedDiagnostics:
    _require_offline(offline_publication_v1)
    observations = checked_diagnostics_snapshot(payload,offline_publication_v1=True)
    with self._lock:
      publication = PublishedDiagnostics(self._current.generation+1,digest(payload),observations)
      self._current = publication
      return publication

  def read(self) -> PublishedDiagnostics:
    with self._lock:
      return self._current
