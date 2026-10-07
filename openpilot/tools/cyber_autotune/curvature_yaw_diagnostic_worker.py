"""Passive isolated profiler. No controller/state/output mutation or new delay."""
import contextlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from curvature_yaw_native_worker import execute_request
from curvature_yaw_native_protocol import MAX_REQUEST_BYTES, decode_request, encode_request
from native_protocol import canonical, digest, _unique_pairs, _invalid_constant
from worker_resources import apply_worker_limits


def execute(envelope):
  request=envelope['request']
  source=Path(__file__).resolve()
  if envelope['producer_source_sha256']!=digest(source.read_bytes()):
    raise ValueError('DIAGNOSTIC_SOURCE_DRIFT')
  target=Path(request['native']['source']['root'])/'openpilot/selfdrive/controls/lib/latcontrol_torque.py'
  rows=[]
  previous_integral=0.
  def observe(frame,event,arg):
    nonlocal previous_integral
    if frame.f_code.co_name!='update' or Path(frame.f_code.co_filename).resolve()!=target.resolve():
      return
    loc=frame.f_locals
    controller=loc['self']
    if event=='call':
      previous_integral=float(controller.pid.i)
      return
    if event!='return':
      return
    if arg is None:
      raise ValueError('INCOMPLETE_CONTROLLER_RETURN')
    numeric={'measurement':'measurement','setpoint':'setpoint','error':'error','future_lataccel':'future_desired_lateral_accel',
             'raw_jerk':'raw_lateral_jerk','filtered_jerk':'desired_lateral_jerk','feedforward':'ff',
             'delay_frames':'delay_frames','lookahead_index':'lookahead_idx'}
    row={k:float(loc[v]) for k,v in numeric.items()}
    row.update(step_index=len(rows),requested_torque=float(arg[0]),active=bool(loc['active']),
               factor=float(controller.torque_params.latAccelFactor),friction=float(controller.torque_params.friction),
               integrator_previous=previous_integral,
               pid_limit_clipped=bool(loc['active'] and controller.pid.control!=controller.pid.p+controller.pid.i+controller.pid.d+controller.pid.f),
               pid_p=float(controller.pid.p),pid_i=float(controller.pid.i),pid_d=float(controller.pid.d),
               pid_f=float(controller.pid.f),pid_control=float(controller.pid.control),
               pos_limit=float(controller.pid.pos_limit),neg_limit=float(controller.pid.neg_limit),
               unclipped=float(controller.pid.p+controller.pid.i+controller.pid.d+controller.pid.f),
               integrator_frozen=bool(loc.get('freeze_integrator',True)),
               kp=float(controller.pid.k_p),ki=float(controller.pid.k_i),
               history_sha256=digest(canonical([float(v) for v in controller.lat_accel_request_buffer])))
    rows.append(row)
  sys.setprofile(observe)
  try:
    result=execute_request(request)
  finally:
    sys.setprofile(None)
  if digest(source.read_bytes())!=envelope['producer_source_sha256'] or len(rows)!=len(request['native']['frames']):
    raise ValueError('DIAGNOSTIC_SOURCE_OR_COUNT_DRIFT')
  return {'request_sha256':digest(encode_request(request)),'producer_source_sha256':envelope['producer_source_sha256'],
          'native_result':result,'observations':rows}


def main():
  try:
    apply_worker_limits()
    payload=sys.stdin.buffer.read(MAX_REQUEST_BYTES+1025)
    if len(payload)>MAX_REQUEST_BYTES+1024:
      raise ValueError('OVERSIZED_DIAGNOSTIC_REQUEST')
    envelope=json.loads(payload,object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant)
    if set(envelope)!={'request','producer_source_sha256'}:
      raise ValueError('INVALID_DIAGNOSTIC_ENVELOPE')
    envelope['request']=decode_request(encode_request(envelope['request']))
    with open(os.devnull,'w') as quiet,contextlib.redirect_stdout(quiet):
      result=execute(envelope)
    sys.stdout.buffer.write(canonical(result))
    return 0
  except Exception:
    return 1


if __name__=='__main__':
  raise SystemExit(main())
