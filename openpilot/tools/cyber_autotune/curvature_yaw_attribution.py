"""Descriptive synthetic controller attribution; never lane/vehicle truth or unique causality."""
import base64
from collections import defaultdict
import math
from pathlib import Path

from openpilot.tools.cyber_autotune.a1_experiment import build_request, make_fixture
from openpilot.tools.cyber_autotune.curvature_yaw_screening import _events, _inputs, validate_screening_report
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest, finite

DT_S = .01
LOW_END_MPS, MID_END_MPS = 10., 20.
MAGNITUDE_SPLIT_1PM = .0005  # existing S-curve amplitude; descriptive grouping only
LAG_BOUND_STEPS = 20  # 0.19 s native lookahead plus one 10 ms frame
REFERENCE_HISTORY_STEPS = 16  # int(.15/.01+1), native buffer index after append
SPEC = {'version':1,'speed_buckets_mps':[3.,10.,20.,27.],
        'magnitude_split_1pm':MAGNITUDE_SPLIT_1PM,'lag_bound_steps':LAG_BOUND_STEPS,
        'native_history_index':REFERENCE_HISTORY_STEPS,'derivative':'adjacent frame before grouping; first vs zero',
        'lag':'minimum demeaned squared error, integer [-20,20], smallest absolute lag then signed',
        'phase_residual':'pre-step curvature minus delayed accel reference/current speed squared',
        'truth':'SYNTHETIC_NOT_VEHICLE_TRUTH'}


def rms(values):
  return math.sqrt(sum(v*v for v in values)/len(values)) if values else 0.


def speed_bucket(speed):
  if not finite(speed) or not 3. <= speed <= 27.:
    raise ValueError('ATTRIBUTION_SPEED_DOMAIN')
  return 'LOW' if speed < LOW_END_MPS else 'MID' if speed < MID_END_MPS else 'HIGH'


def estimate_lag(desired,actual):
  if (type(desired) is not list or type(actual) is not list or len(desired)!=len(actual)
      or len(desired)<2 or not all(finite(v) for v in desired+actual)):
    raise ValueError('INVALID_LAG_INPUT')
  if max(desired)==min(desired):
    return {'status':'INSUFFICIENT_EXCITATION','lag_steps':None,'physical_delay_estimate':False}
  # Fixed central window compares exactly the same target samples for every lag.
  if len(desired)<=2*LAG_BOUND_STEPS:
    return {'status':'INSUFFICIENT_WINDOW','lag_steps':None,'physical_delay_estimate':False}
  scored=[]
  indexes=range(LAG_BOUND_STEPS,len(desired)-LAG_BOUND_STEPS)
  for lag in range(-LAG_BOUND_STEPS,LAG_BOUND_STEPS+1):
    errors=[actual[i]-desired[i-lag] for i in indexes]
    mean=sum(errors)/len(errors)
    score=sum((e-mean)**2 for e in errors)/len(errors)
    scored.append((score,abs(lag),lag))
  score,_,lag=min(scored)
  return {'status':'DESCRIPTIVE_LAG','lag_steps':lag,'demeaned_mse':score,'physical_delay_estimate':False}


def desired_angles(frames,cp_sha256):
  from opendbc.car import structs
  from opendbc.car.vehicle_model import VehicleModel
  fixture,_=make_fixture(build_request('identity'))
  if fixture['car_params_sha256']!=cp_sha256:
    raise ValueError('ATTRIBUTION_CP_MISMATCH')
  with structs.CarParams.from_bytes(base64.b64decode(fixture['car_params_base64'])) as cp:
    model=VehicleModel(cp)
    angles=[]
    for frame in frames:
      model.update_params(frame['stiffness_factor'],frame['steer_ratio'])
      angles.append(math.degrees(model.get_steer_from_curvature(
        -frame['desired_curvature_1pm'],frame['speed_mps'],frame['roll_rad']))+frame['angle_offset_deg'])
  return angles


def decorate_samples(samples,frames,angles,initial_curvature=0.):
  if not (len(samples)==len(frames)==len(angles)):
    raise ValueError('ATTRIBUTION_LENGTH_MISMATCH')
  rows=[]
  prior_u,prior_applied,pre_curvature=0.,0.,initial_curvature
  for i,(sample,frame,angle) in enumerate(zip(samples,frames,angles,strict=True)):
    row=dict(sample)
    j=i-(REFERENCE_HISTORY_STEPS-1)
    target=0. if j<0 else frames[j]['desired_curvature_1pm']*frames[j]['speed_mps']**2/frame['speed_mps']**2
    row.update({
      'speed_bucket':speed_bucket(frame['speed_mps']),
      'curvature_sign':'POSITIVE' if frame['desired_curvature_1pm']>0 else 'NEGATIVE' if frame['desired_curvature_1pm']<0 else 'ZERO',
      'curvature_magnitude':'ZERO' if frame['desired_curvature_1pm']==0 else 'GENTLE' if abs(frame['desired_curvature_1pm'])<=MAGNITUDE_SPLIT_1PM else 'SHARP',
      'desired_steering_angle_deg':angle,
      'steering_angle_residual_deg':sample['steering_angle_deg']-angle,
      'command_derivative_per_s':(sample['requested_torque']-prior_u)/DT_S,
      'torque_derivative_per_s':(sample['applied_normalized_torque']-prior_applied)/DT_S,
      'curvature_residual_1pm':sample['curvature_1pm']-frame['desired_curvature_1pm'],
      'native_aligned_desired_curvature_1pm':target,
      'native_aligned_residual_1pm':pre_curvature-target,
      'inactive_to_active':i>0 and frame['active'] and not frames[i-1]['active'],
      'pressed_to_release':i>0 and not frame['steering_pressed'] and frames[i-1]['steering_pressed'],
    })
    rows.append(row)
    prior_u,prior_applied,pre_curvature=sample['requested_torque'],sample['applied_normalized_torque'],sample['curvature_1pm']
  return rows


def group_diagnostics(rows):
  groups=defaultdict(list)
  for row in rows:
    groups[(row['speed_bucket'],row['curvature_magnitude'],row['curvature_sign'],row['phase'])].append(row)
  result=[]
  for key,values in sorted(groups.items()):
    indices={r['step_index'] for r in values}
    # Count events from the original complete sequence, never across disconnected group gaps.
    crossings=[i for i in _events([r['requested_torque'] for r in rows]) if i in indices]
    reversals=[i for i in _events([r['command_derivative_per_s'] for r in rows]) if i in indices]
    result.append({
      **dict(zip(('speed_bucket','curvature_magnitude','curvature_sign','phase'),key,strict=True)),
      'count':len(values),'command_rms':rms([r['requested_torque'] for r in values]),
      'applied_torque_rms':rms([r['applied_normalized_torque'] for r in values]),
      'command_derivative_rms_per_s':rms([r['command_derivative_per_s'] for r in values]),
      'applied_torque_derivative_rms_per_s':rms([r['torque_derivative_per_s'] for r in values]),
      'saturation_occupancy':sum(r['saturated'] for r in values)/len(values),
      'zero_crossings':len(crossings),'reversals':len(reversals),
      'reversal_frequency_hz':len(reversals)/(len(values)*DT_S),
      'curvature_residual_rmse_1pm':rms([r['curvature_residual_1pm'] for r in values]),
      'native_aligned_residual_rmse_1pm':rms([r['native_aligned_residual_1pm'] for r in values]),
      'steering_residual_rmse_deg':rms([r['steering_angle_residual_deg'] for r in values]),
      'max_abs_pose_y_m':max(abs(r['pose_y_m']) for r in values),
      'inactive_to_active_count':sum(r['inactive_to_active'] for r in values),
      'pressed_to_release_count':sum(r['pressed_to_release'] for r in values),
    })
  return result


def attribute_report(report):
  validate_screening_report(report)
  frames,_=_inputs(report['manifest']['scenario'])
  angles=desired_angles(frames,report['manifest']['car_params_sha256'])
  arms=[]
  for arm in report['arms']:
    rows=decorate_samples(arm['samples'],frames,angles)
    arms.append({'arm':arm['arm'],'rows':rows,'groups':group_diagnostics(rows),
                 'lag':estimate_lag([r['desired_curvature_1pm'] for r in rows],[r['curvature_1pm'] for r in rows])})
  result={'version':1,'status':'DESCRIPTIVE_ATTRIBUTION','input_receipt_sha256':report['receipt_sha256'],
          'spec_sha256':digest(canonical(SPEC)),'producer_source_sha256':digest(Path(__file__).read_bytes()),
          'scenario':report['manifest']['scenario'],'arms':arms,
          'reference_status':'NO INDEPENDENT LANE TRUTH','performance_qualified':False}
  result['receipt_sha256']=digest(canonical(result))
  return result
