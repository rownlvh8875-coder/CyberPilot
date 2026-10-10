"""Whitelist extraction and segment-local support; no vehicle/candidate executor."""

from collections import Counter
import math
import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_model as m
from openpilot.tools.cyber_autotune import empirical_signal_reader as r


def numeric(iterator):
  auxiliary=Counter()

  def selected():
    for event in iterator:
      kind=event.which()
      if kind not in ('initData','carState','carControl','carOutput','gyroscope'):
        continue
      if kind=='carState':
        state=event.carState
        for name in ('steeringRateDeg','wheelSpeeds'):
          if name not in state.schema.fields:
            continue
          if name=='wheelSpeeds':
            wheel=state.wheelSpeeds
            for field in ('fl','fr','rl','rr'):
              auxiliary['wheelSpeeds.'+field+'.finite'] += math.isfinite(float(getattr(wheel,field)))
          else:
            auxiliary[name+'.finite'] += math.isfinite(float(getattr(state,name)))
      yield event
  result=r.read_numeric(selected(),True)
  result['auxiliary_coverage']=dict(auxiliary)
  return result


def aligned(streams):
  result = r.aligned({k:val for k,val in streams.items() if k != 'auxiliary_coverage'})
  for row in result['rows']:
    row['actuator_valid'] = not (set(row['reasons']) - {'YAW_UNAVAILABLE'})
    if row['yaw_raw'] is not None and not math.isfinite(row['yaw_raw']):
      row['yaw_raw']=None
  return result


def actuator_runs(receipts, regime):
  result = []
  for receipt in receipts:
    rows = [{**x, 'diagnostic_valid': x['actuator_valid']} for x in receipt['aligned']['rows']]
    result.extend(m.runs(rows, regime))
  return result


def coverage(alignment):
  rows = alignment['rows']
  counts = Counter(reason for row in rows for reason in row['reasons'] if reason != 'YAW_UNAVAILABLE')
  bins = {}
  for regime in ('LOW', 'MEDIUM', 'HIGH'):
    matching = [x for x in rows if x['speed_bin'] == regime]
    data = actuator_runs([{'aligned': alignment}], regime)
    lengths = [len(x['y']) for x in data]
    common = sum(max(0, n - 44) for n in lengths)
    bins[regime] = {
      'total_grid_samples': len(matching), 'diagnostic_valid': sum(x['actuator_valid'] for x in matching),
      'unavailable': sum(not x['actuator_valid'] for x in matching),
      'continuous_valid_duration_s': sum(lengths)*0.01, 'longest_contiguous_samples': max(lengths,default=0),
      'contiguous_runs': len(lengths), 'contiguous_45_sample_windows': common, 'common_design_rows': common,
      'ARX1_design_rows': common, 'FIR25_design_rows': common, 'development_minimum': 201,
    }
  gap=[bool(set(x['reasons']) & {'MISSING_OR_GAP','SOURCE_EVENT_GAP','REPEATED_OUTPUT_EVENT'}) for x in rows]
  invalid=[not x['actuator_valid'] for x in rows]
  intervention=[bool(set(x['reasons']) & {'DRIVER_OVERRIDE','INACTIVE'}) for x in rows]

  def starts(mask):
    return sum(value and (i==0 or not mask[i-1]) for i,value in enumerate(mask))
  return {
    'total_grid_samples': len(rows), 'diagnostic_valid': sum(x['actuator_valid'] for x in rows),
    'unavailable': sum(not x['actuator_valid'] for x in rows), 'unbinned': sum(x['speed_bin'] is None for x in rows),
    'bins': bins, 'mask_reason_counts_overlapping': dict(counts),
    'gap_breaks': starts(gap), 'gap_masked_samples':sum(gap),
    'mask_breaks': starts(invalid), 'mask_invalid_samples':sum(invalid),
    'speed_bin_breaks': sum(a['speed_bin'] != b['speed_bin'] for a,b in zip(rows,rows[1:],strict=False)),
    'intervention_breaks': starts(intervention), 'intervention_masked_samples':sum(intervention),
    'segment_boundary_breaks': 0, 'segment_reset_count':1,
    'safety_limited': None, 'curvature_limited': None, 'clean_primary_valid': 0,
    'gyro_common_valid': sum(x['gyro_common_valid'] and x['diagnostic_valid'] for x in rows),
    'clock': 'PUBLISH_TIME_ONLY_NOT_SENSOR_ACQUISITION_TRUTH',
  }


def route_bridge(segments):
  statuses = [x['bridge']['status'] for x in segments]
  pairs = [pair for x in segments for pair in x['command_pairs']]
  settings = {x['runtime_steer_max'] for x in segments}
  if len(settings) != 1 or any(x['runtime_setting_known'] is not True for x in segments):
    return {'status':'ROUTE_COMMAND_BRIDGE_PARTIAL', 'reason':'RUNTIME_SETTING_UNAVAILABLE_OR_CHANGED', 'pair_count':len(pairs)}
  result = r.command_bridge(pairs, next(iter(settings)), True)
  status = result.pop('status').replace('RAW_TO_NORMALIZED_COMMAND_', 'ROUTE_COMMAND_BRIDGE_')
  if any(x == 'RAW_TO_NORMALIZED_COMMAND_CONFLICT' for x in statuses):
    status='ROUTE_COMMAND_BRIDGE_CONFLICT'
  result['status'] = status
  result['float32_exact_rate'] = result['float32_expected_exact_count']/result['eligible'] if result['eligible'] else None
  result['pair_count'] = result['eligible']
  return result


def finite_or_none(value):
  return float(value) if math.isfinite(value) else None


def profile_for_models(fields):
  return {'steer_control_type':fields['steerControlType'], 'flags':fields['flags'],
          'wheelbase':fields['wheelbase'], 'steer_ratio':fields['steerRatio']}


def validate_gyro_clock(streams):
  # Optional gyro source failure is explicit; it must not erase actuator support.
  try:
    r.validate_times(streams['gyro'])
    r.validate_times(streams['gyro'], 'sensor_ns')
    return 'GYRO_CLOCK_MONOTONIC'
  except ValueError:
    streams['gyro_rejected'] += len(streams['gyro'])
    streams['gyro'] = []
    return 'GYRO_CLOCK_REJECTED_NOT_USED'


def bridge_inputs(streams, profile):
  settings = streams['settings']
  if not settings or len({str(sorted(x.items())) for x in settings}) != 1:
    raise ValueError('RUNTIME_SETTINGS_MISSING_OR_MIXED')
  maximum, known = r.effective_steer_max(profile, settings[0])
  pairs = [{'raw':finite_or_none(x['raw']), 'normalized':finite_or_none(x['normalized']),
            'valid':bool(x['valid'] and math.isfinite(x['raw']) and math.isfinite(x['normalized']))} for x in streams['command']]
  bridge = r.command_bridge(pairs, maximum, known)
  return maximum, known, pairs, bridge


def checked_rollout(evaluation, total):
  if evaluation['status'] != 'EVALUATED':
    return evaluation
  for metrics in evaluation['rollout'].values():
    count=metrics['model']['count']
    metrics['coverage']={'valid':count,'candidate_grid_samples':total,'unavailable':total-count}
    metrics['finite_bounded'] = all(v is None or np.isfinite(v) for v in metrics['model'].values())
  return evaluation
