"""Discrete source/unit crosschecks. Device correspondence is never physical calibration."""

import math
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_model as m
from openpilot.tools.cyber_autotune import empirical_signal_policy as q


def kinematic(angle_deg, speed_mps, wheelbase_m, steer_ratio):
  if not all(math.isfinite(v) for v in (angle_deg, speed_mps, wheelbase_m, steer_ratio)) or wheelbase_m <= 0 or steer_ratio <= 0 or speed_mps < 0:
    raise ValueError('FINITE_FORWARD_STATIC_KINEMATIC_GEOMETRY_REQUIRED')
  return speed_mps / wheelbase_m * math.tan(math.radians(angle_deg) / steer_ratio)


def _values(receipt, hypothesis, candidate, profile):
  if hypothesis not in q.policy()['hypotheses'] or candidate not in q.policy()['gyro_candidates']:
    raise ValueError('ONLY_FROZEN_DISCRETE_CORRESPONDENCE')
  rows = receipt['aligned']['rows']
  options = receipt['aligned']['gyro_options'][str(candidate['lag_samples'])]
  if len(rows) != len(options):
    raise ValueError('EXACT_TARGET_OPTION_LENGTH')
  records = []
  for index, (row, vector) in enumerate(zip(rows, options, strict=True)):
    if not row['diagnostic_valid'] or not row['gyro_common_valid'] or vector is None:
      continue
    yaw = q.convert_yaw(row['yaw_raw'], hypothesis)
    gyro = vector[candidate['axis']] * candidate['sign']
    kin = kinematic(row['angle_deg'], row['speed_mps'], profile['wheelbase'], profile['steer_ratio'])
    if not np.isfinite([yaw, gyro, kin]).all():
      continue
    records.append((index, yaw, gyro, kin, row['speed_bin'], min(3, 4 * index // max(1, len(rows)))))
  return records


def _metric(truth, predicted):
  truth, predicted = np.asarray(truth), np.asarray(predicted)
  result = m.statistics(predicted - truth, truth)
  denominator = float(np.sqrt(np.mean(truth * truth))) if len(truth) else 0.0
  result['SCALE_RATIO_RMS_DIAGNOSTIC_ONLY'] = float(np.sqrt(np.mean(predicted * predicted)) / denominator) if denominator else None
  return result


def analyze(receipts, hypothesis, candidate, profile):
  records = [_values(x, hypothesis, candidate, profile) for x in receipts]
  flat = [x for group in records for x in group]

  def stats(rows):
    a = np.asarray([[x[1], x[2], x[3]] for x in rows], dtype=float).reshape(-1, 3)
    return {'gyro': _metric(a[:, 1], a[:, 0]), 'kinematic': _metric(a[:, 2], a[:, 0])}

  overall = stats(flat)
  autocorr = {}
  for lag in range(1, 21):
    now = []
    past = []
    for group in records:
      residual = {x[0]: x[1] - x[2] for x in group}
      for index, value in residual.items():
        if index - lag in residual and all(index - j in residual for j in range(lag + 1)):
          now.append(value)
          past.append(residual[index - lag])
    autocorr[str(lag)] = {'correlation': m.correlate(now, past), 'count': len(now)}
  total = sum(len(x['aligned']['rows']) for x in receipts)
  return {
    **overall,
    'coverage': {
      'total': total,
      'valid': len(flat),
      'unavailable': total - len(flat),
      'segment_count': len(receipts),
      'supported_segments': sum(bool(x) for x in records),
      'minimum_support_met': len(flat) >= 201,
    },
    'speed_bins': {name: stats([x for x in flat if x[4] == name]) for name in ['LOW', 'MEDIUM', 'HIGH']},
    'turn_sign': {name: stats([x for x in flat if (x[1] > 0 if name == 'POSITIVE' else x[1] < 0)]) for name in ['POSITIVE', 'NEGATIVE']},
    'time_blocks': {str(i): stats([x for x in flat if x[5] == i]) for i in range(4)},
    'segments': [{'segment_id': r['segment_id'], **stats(group)} for r, group in zip(receipts, records, strict=True)],
    'residual_autocorrelation': autocorr,
    'vehicle_frame_calibrated': False,
    'unit': 'RAD_PER_S_CONDITIONAL',
  }


def _vectors(receipts, profile):
  yaw = []
  kin = []
  gyro = {str(lag): [] for lag in q.policy()['lag_samples']}
  for receipt in receipts:
    rows = receipt['aligned']['rows']
    for i, row in enumerate(rows):
      if not row['diagnostic_valid'] or not row['gyro_common_valid']:
        continue
      yaw.append(row['yaw_raw'])
      kin.append(kinematic(row['angle_deg'], row['speed_mps'], profile['wheelbase'], profile['steer_ratio']))
      for lag in gyro:
        gyro[lag].append(receipt['aligned']['gyro_options'][lag][i])
  return {
    'yaw': np.asarray(yaw, dtype=float),
    'kinematic': np.asarray(kin, dtype=float),
    'gyro': {lag: np.asarray(values, dtype=float).reshape(-1, 3) for lag, values in gyro.items()},
  }


def _fast_metric(vectors, hypothesis, candidate):
  yaw = vectors['yaw'] * q.convert_yaw(1.0, hypothesis)
  gyro = vectors['gyro'][str(candidate['lag_samples'])][:, candidate['axis']] * candidate['sign']
  return {'gyro': _metric(gyro, yaw), 'kinematic': _metric(vectors['kinematic'], yaw)}


def select(roles, profile):
  if set(roles) != {'TRAIN', 'DEVELOPMENT'}:
    raise ValueError('NO_HOLDOUT_IN_CORRESPONDENCE_SELECTION')
  vectors = {role: _vectors(rows, profile) for role, rows in roles.items()}
  candidates = {}
  for hypothesis in q.policy()['hypotheses']:
    table = []
    for option in q.policy()['gyro_candidates']:
      metric = _fast_metric(vectors['DEVELOPMENT'], hypothesis, option)
      table.append({'candidate': option, **metric})
    eligible = [x for x in table if x['gyro']['count'] >= 201]
    best = min(eligible, key=lambda x: (x['gyro']['RMSE'], x['candidate']['axis'], x['candidate']['sign'], x['candidate']['lag_samples'])) if eligible else None
    candidates[hypothesis] = {'best': best, 'all_development': table}
  eligible = [(h, x['best']) for h, x in candidates.items() if x['best'] is not None]
  if not eligible:
    return {
      'hypothesis': None,
      'gyro_candidate': None,
      'unit_supported': False,
      'candidates': candidates,
      'vehicle_frame': 'DEVICE_AXIS_CORRESPONDENCE_ONLY',
      'vehicle_frame_calibrated': False,
    }
  h, best = min(eligible, key=lambda x: (x[1]['kinematic']['RMSE'], x[0]))
  train = {name: _fast_metric(vectors['TRAIN'], name, x['best']['candidate']) if x['best'] else None for name, x in candidates.items()}
  support = True
  # Unit dominance is directional, never a calibration acceptance threshold.
  other = [name for name in candidates if (name in ('YAW_H1', 'YAW_H2')) != (h in ('YAW_H1', 'YAW_H2'))]
  for split in ('TRAIN', 'DEVELOPMENT'):
    metrics = train if split == 'TRAIN' else {name: x['best'] for name, x in candidates.items()}
    selected = metrics[h]
    support &= selected is not None and selected['gyro']['count'] >= 201
    if not support:
      break
    for group in ('gyro', 'kinematic'):
      for metric in ('RMSE', 'MAE', 'P95_ABS'):
        alternatives = [metrics[name][group][metric] for name in other if metrics[name] is not None]
        support &= bool(alternatives) and selected[group][metric] < min(alternatives)
  return {
    'hypothesis': h,
    'gyro_candidate': best['candidate'],
    'unit_supported': bool(support),
    'candidates': candidates,
    'train': train,
    'vehicle_frame': 'DEVICE_AXIS_CORRESPONDENCE_ONLY',
    'vehicle_frame_calibrated': False,
    'continuous_scale_fitted': False,
    'bias_corrected': False,
  }


def yaw_runs(receipts, hypothesis, profile, regime):
  result = []
  for receipt in receipts:
    u = []
    y = []
    blocks = []
    rows = receipt['aligned']['rows']
    previous = None

    def finish(u, y, blocks):
      if u:
        result.append({'u': np.asarray(u, dtype=float), 'y': np.asarray(y, dtype=float), 'blocks': np.asarray(blocks, dtype=int)})

    for index, row in enumerate(rows):
      eligible = row['diagnostic_valid'] and row['gyro_common_valid'] and row['speed_bin'] == regime
      if previous is not None and row['grid_time_ns'] - previous != 10_000_000:
        finish(u, y, blocks)
        u = []
        y = []
        blocks = []
      previous = row['grid_time_ns']
      if eligible:
        u.append(kinematic(row['angle_deg'], row['speed_mps'], profile['wheelbase'], profile['steer_ratio']))
        y.append(q.convert_yaw(row['yaw_raw'], hypothesis))
        blocks.append(min(3, 4 * index // max(1, len(rows))))
      else:
        finish(u, y, blocks)
        u = []
        y = []
        blocks = []
    finish(u, y, blocks)
  return result
