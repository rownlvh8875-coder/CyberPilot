"""Pure one-to-one paired H1 visual mapping; no execution, interpolation or fitting."""

import math

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_h1_pairing as q
from openpilot.tools.cyber_autotune import cyber_h1_visual_adapter as single

DELTAS = (
  'actual_curvature_pre_step_1pm',
  'controller_limited_torque',
  'pre_governor_torque',
  'post_governor_torque',
  'final_requested_torque',
  'applied_torque',
  'curvature_post_step_1pm',
  'yaw_rate_post_step_rad_s',
  'heading_post_step_rad',
  'pose_x_post_step_m',
  'pose_y_post_step_m',
)


def delta(field, baseline, candidate):
  if field not in DELTAS:
    raise ValueError('PAIR_SAME_PHASE_DELTA_FIELDS_ONLY')
  a, b = baseline[field], candidate[field]
  return None if a is None or b is None else b - a


def schema():
  return q.seal(
    {
      'schema': 'CYBER_H1_PAIRED_FRAME_SCHEMA_V1',
      'frame_schema': 'CYBER_H1_PAIRED_VISUAL_FRAME_V1',
      'fields': [
        'schema',
        'frame_index',
        'scenario',
        'shared_stimulus_sha256',
        'baseline_row_sha256',
        'candidate_row_sha256',
        'pair_sha256',
        'capture_time_ns',
        'decision_time_ns',
        'completion_time_ns',
        'relative_time_s',
        'dt_s',
        'shared',
        'baseline',
        'candidate',
        'delta',
        'evidence_tier',
      ],
      'arm_mapping': single.mapping(),
      'delta_fields': list(DELTAS),
      'null_delta': 'NULL_IF_EITHER_ARM_UNAVAILABLE',
      'phase_semantics': 'PRE_STEP/COMMAND K; PLANT COMPLETION K+1',
      'copy_semantics': 'NO_INTERPOLATION_SMOOTHING_RESAMPLING_FILL_OR_POSE_RECONSTRUCTION',
      'no_shared_input_delta': True,
      'tier': q.TIER,
    }
  )


def quantile(values, fraction):
  values = sorted(values)
  index = (len(values) - 1) * fraction
  low, high = math.floor(index), math.ceil(index)
  return values[low] + (values[high] - values[low]) * (index - low)


def statistics(frames):
  result = {}
  for key in DELTAS:
    values = [f['delta'][key] for f in frames if f['delta'][key] is not None]
    absolute = [abs(v) for v in values]
    result[key] = {
      'count': len(values),
      'unavailable': len(frames) - len(values),
      'coverage': len(values) / len(frames),
      'max_absolute': max(absolute) if values else None,
      'p50_absolute': quantile(absolute, 0.5) if values else None,
      'p95_absolute': quantile(absolute, 0.95) if values else None,
      'final': frames[-1]['delta'][key],
    }
  return result


def convert(baseline, candidate):
  manifest = q.pair(baseline, candidate)
  frames = []
  for i, (a, b) in enumerate(zip(baseline['rows'], candidate['rows'], strict=True)):
    left, right = single.frame(a), single.frame(b)
    shared = q.stimulus(a, manifest['scenario'], manifest['scenario_sha256'])
    frame = {
      'schema': 'CYBER_H1_PAIRED_VISUAL_FRAME_V1',
      'frame_index': i,
      'scenario': manifest['scenario'],
      'shared_stimulus_sha256': p.sha(p.canonical(shared)),
      'baseline_row_sha256': a['row_sha256'],
      'candidate_row_sha256': b['row_sha256'],
      **{k: a[k] for k in single.TIMING},
      'relative_time_s': a['capture_time_ns'] / 1e9,
      'dt_s': a['dt_ns'] / 1e9,
      'shared': shared,
      'baseline': left,
      'candidate': right,
      'delta': {key: delta(key, left, right) for key in DELTAS},
      'evidence_tier': q.TIER,
    }
    frame['pair_sha256'] = p.sha(p.canonical(frame))
    frames.append(frame)
  return q.seal(
    {
      'schema': 'CYBER_H1_PAIRED_VISUAL_FRAMESET_V1',
      'run_id': p.sha(p.canonical({'pair': manifest['receipt_sha256'], 'schema': schema()['receipt_sha256']})),
      'pair_manifest_sha256': manifest['receipt_sha256'],
      'frame_schema_sha256': schema()['receipt_sha256'],
      'campaign_id': manifest['campaign_id'],
      'scenario': manifest['scenario'],
      'arm_count': 2,
      'arms': [q.BASELINE, manifest['candidate_arm']],
      'evidence_tier': q.TIER,
      'frame_count': len(frames),
      'origin_time_ns': 0,
      'dt_ns': manifest['dt_ns'],
      'duration_ns': manifest['duration_ns'],
      'frames_sha256': p.sha(p.canonical(frames)),
      'frames': frames,
      'coverage': {'input_pairs': len(frames), 'output_frames': len(frames), 'dropped': 0, 'filled': 0, 'interpolated': 0},
      'unavailable_fields': left['unavailable'],
      'service_health': left['service_health'],
      'delta_statistics': statistics(frames),
      'comparison_ready': True,
      'historical_verdict': manifest['historical_verdict'],
      'verdict_recomputed': False,
      'blockers': p.BLOCKERS,
      'holdout_opening': 'CLOSED',
      'opening_count': 0,
    }
  )


def validate(fs, baseline, candidate):
  q.verify(fs)
  expected = convert(baseline, candidate)
  if p.canonical(fs) != p.canonical(expected):
    raise ValueError('PAIR_FRAME_PHASE_VALUE_OR_METADATA_DRIFT')
  return fs
