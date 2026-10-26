"""Read-only frozen assisted-pixel adapter and redacted conditional reporting.

Only explicitly supplied JSON receipts are opened. No log, image, video or model
execution. New per-point derivatives remain in a separate local/private store.
"""

import argparse
import gzip
import json
import math
import os
from pathlib import Path
import tempfile
import platform

import numpy as np

from openpilot.tools.cyber_autotune import declared_meter_diagnostic as m
from openpilot.tools.cyber_autotune import private_holdout_assisted_analysis as old
from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune import private_holdout_pixel_metrics as metric
from openpilot.tools.cyber_autotune.lane_tail_report import unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

EXECUTED_SOURCE_SHA = digest(Path(__file__).read_bytes())
HELPERS = {Path(x.__file__).name: digest(Path(x.__file__).read_bytes()) for x in (m, m.q, m.a, h, metric, old)}
AGGREGATE_RECEIPT = '6e15a7caf6af342696906da5add686d775578844058e6eb8dd0df10dacb14562'
SCENARIO_IDS = frozenset(s['scenario_id'] for s in m.scenarios())
PUBLIC_KEYS = (
  'status',
  'policy',
  'source_bindings',
  'coverage',
  'fixed_distance',
  'holdout_projection',
  'scenario_attribution',
  'point_derivative_set_sha256',
  'all_declared_envelopes',
  'executor_identity',
)
STAT_KEYS = frozenset(
  (
    'status',
    'p50_m',
    'p95_m',
    'p95_minus_p50_m',
    'sampled_spread_m',
    'uncertainty_m',
    'count',
    'median',
    'p90',
    'p95',
    'maximum',
    'left',
    'right',
    'center',
    'combined',
    'group',
    'mapping',
    'scenario_id',
    'distance_query_m',
    'projected_query_forward_m',
    'total_residual_samples',
    'valid_samples',
    'unavailable_samples',
    'lateral_m',
    'synthetic_query_outside_image',
    'residual_semantics',
    'total_candidate_points',
    'projected_forward_valid',
    'mapping_unavailable',
    'nonforward_horizon',
    'out_of_domain',
    'valid_in_domain',
    'unavailable_count',
    'unavailable_rate',
    'bins',
    'distance_m',
    'bin_edges_m',
    'small_sample',
    'coverage_semantics',
    'frames',
    'both_visible_frames',
    'both_matched_frames',
    'both_boundary_matching_rate',
    'available_frames',
    'unavailable_frames',
    'both_visible_denominator',
    'units',
    'schema',
    'total_frames',
    'both_visible',
    'both_matched',
    'center_unavailable',
    'left_unavailable',
    'right_unavailable',
    'factor',
    'minimum_p95_m',
    'maximum_p95_m',
    'width_m',
    'minimum_scenario',
    'maximum_scenario',
    'minimum_mapping',
    'maximum_mapping',
    'separate_not_additive',
    'candidate_count',
    'minimum_p50_m',
    'maximum_p50_m',
    'envelope_scope',
  )
)
ENUMS = frozenset(
  (
    *m.q.RULES,
    'FROZEN_RESIDUAL_SPREAD_NOT_PARAMETER_UNCERTAINTY',
    'FIXED_PRIOR_NO_INTRINSICS_SWEEP',
    'DECLARED_SAMPLED_HYPOTHESES_NOT_TOTAL_PHYSICAL_BOUND',
    'left',
    'right',
    'center',
    'combined',
    'height',
    'pitch',
    'roll',
    'yaw',
    'mapping',
    'intrinsics',
    'pixel_residual',
    'ABSOLUTE_X_MAGNITUDE_BOTH_SIGNS_MAX_PINHOLE_CONDITIONAL',
    'MATCHED_POINT_PROJECTION_COUNTS;FRAME_MATCHING_REPORTED_SEPARATELY',
    'HUMAN_PIXEL_EGO_CENTER_REFERENCE',
    'ORIGINAL_IMAGE_PIXELS',
  )
)


def checked(value, receipt):
  unseal(value)
  if value['receipt_sha256'] != receipt:
    raise ValueError('FROZEN_RECEIPT_BINDING_MISMATCH')
  return value


def read(path):
  return json.loads(Path(path).read_bytes())


def unique_ids(rows):
  ids = [r['sample_id'] for r in rows]
  if len(ids) != len(set(ids)):
    raise ValueError('DUPLICATE_FROZEN_FRAME')
  return ids


def matched_pairs(human, lanes):
  matched = metric.assignment(human, lanes)  # Existing frozen policy, never optimized here.
  out = {side: [] for side in ('left', 'right', 'center')}
  for side in ('left', 'right'):
    if side in matched:
      index, (_, ys, _) = matched[side]
      out[side] = [[x, y, px, y] for x, px, y in zip(h.interpolate(human[side], ys), h.interpolate(lanes[index]['points'], ys), ys, strict=True)]
  if human['state'] == 'BOTH_EGO_BOUNDARIES_VISIBLE' and set(matched) == {'left', 'right'}:
    hc = old.center_points(human['left'], human['right'])
    dc = old.center_points(lanes[matched['left'][0]]['points'], lanes[matched['right'][0]]['points'])
    ys = h.common_rows(hc, dc, integer=True)
    out['center'] = [[x, y, px, y] for x, px, y in zip(h.interpolate(hc, ys), h.interpolate(dc, ys), ys, strict=True)]
  return out


def load_frozen(analysis_path, reference_path, evaluation_path, detector_rows_dir):
  public = m.frozen('private-assisted-holdout-final-aggregate-v1.json', AGGREGATE_RECEIPT)
  analysis = checked(read(analysis_path), public['local_analysis_sha256'])
  # Publication identity verifies nested historical aggregates without re-evaluating them.
  if canonical(old.publication(analysis)) != canonical(public):
    raise ValueError('HISTORICAL_ANALYSIS_PUBLICATION_MISMATCH')
  ref = checked(read(reference_path), analysis['reference_sha256'])
  ev = checked(read(evaluation_path), analysis['evaluation_sha256'])
  rows = sorted([read(p) for p in Path(detector_rows_dir).glob('*.json')], key=lambda x: x['ordinal'])
  if len(rows) != 60 or len(ref['annotations']) != 60 or len(analysis['rows']) != 60:
    raise ValueError('FROZEN_SIXTY_ONLY')
  if digest(canonical([x['receipt_sha256'] for x in rows])) != ev['detector_receipts_sha256']:
    raise ValueError('FROZEN_DETECTOR_SET_CHANGED')
  if digest(canonical([x['receipt_sha256'] for x in ref['annotations']])) != analysis['human_final_set_sha256']:
    raise ValueError('FROZEN_HUMAN_SET_CHANGED')
  ids = unique_ids(analysis['rows'])
  pairs = {side: [] for side in ('left', 'right', 'center')}
  local_bindings = []
  for i, (human, pred, ar, binding) in enumerate(zip(ref['annotations'], rows, analysis['rows'], analysis['bindings'], strict=True)):
    checked(human, ar['human_sha256'])
    checked(pred, ar['detector_receipt_sha256'])
    if (
      human['sample_id'] != ids[i]
      or pred['sample_id'] != ids[i]
      or human['image_sha256'] != ar['image_sha256']
      or pred['image_sha256'] != ar['image_sha256']
      or pred['prediction_sha256'] != digest(canonical(pred['prediction']))
      or pred['prediction_sha256'] != ar['prediction_sha256']
      or binding['sample_id'] != ids[i]
      or human['width'] != 526
      or human['height'] != 330
      or pred['ordinal'] != i
    ):
      raise ValueError('FROZEN_INPUT_IDENTITY_OR_COORDINATE_MISMATCH')
    recovered = matched_pairs(human, pred['prediction']['lanes'])
    for side, points in recovered.items():
      expected = ar['center_errors'] if side == 'center' else ar['errors'][side]
      actual = [abs(p[0] - p[2]) for p in points]
      if actual != expected:
        raise ValueError('MATCHED_POINT_RECOVERY_DIFFERS_FROM_HISTORICAL_RESIDUAL')
      pairs[side].extend(points)
    local_bindings.append({'sample_id': ids[i], 'image_sha256': ar['image_sha256'], 'counts': {side: len(v) for side, v in recovered.items()}})
  coverage = {
    'total_frames': 60,
    'both_visible': ev['both_visible_denominator'],
    'both_matched': ev['both_boundary_geometry_match_frames'],
    'center_unavailable': analysis['center']['unavailable_frames'],
    'left_unavailable': ev['left_unavailable_visible_frames'],
    'right_unavailable': ev['right_unavailable_visible_frames'],
    'groups': analysis['groups'],
  }
  bindings = {
    'analysis_sha256': analysis['receipt_sha256'],
    'reference_sha256': ref['receipt_sha256'],
    'evaluation_sha256': ev['receipt_sha256'],
    'detector_set_sha256': ev['detector_receipts_sha256'],
    'manifest_binding_set_sha256': analysis['binding_set_sha256'],
    'policy_sha256': analysis['policy_sha256'],
  }
  return pairs, coverage, bindings, local_bindings


def safe_numbers(value, field=None):
  """Nested numeric-statistics allowlist; no paths, comments or private identifiers."""
  enums = {
    'group': {'left', 'right', 'center', 'combined'},
    'mapping': set(m.q.RULES),
    'scenario_id': SCENARIO_IDS,
    'minimum_scenario': SCENARIO_IDS,
    'maximum_scenario': SCENARIO_IDS,
    'minimum_mapping': set(m.q.RULES),
    'maximum_mapping': set(m.q.RULES),
    'factor': {'height', 'pitch', 'roll', 'yaw', 'mapping', 'intrinsics', 'pixel_residual'},
    'status': {'FIXED_PRIOR_NO_INTRINSICS_SWEEP', 'FROZEN_RESIDUAL_SPREAD_NOT_PARAMETER_UNCERTAINTY'},
  }
  if field in enums:
    if type(value) is not str or value not in enums[field]:
      raise ValueError('SCALAR_ENUM_REQUIRED')
    return
  if field in {'distance_m', 'distance_query_m'}:
    if type(value) not in (int, float) or value not in m.DISTANCES:
      raise ValueError('SCALAR_DECLARED_DISTANCE_REQUIRED')
    return
  if field in {'small_sample', 'synthetic_query_outside_image', 'separate_not_additive'}:
    if type(value) is not bool:
      raise ValueError('EXACT_BOOLEAN_STATISTIC_REQUIRED')
    return
  integers = {
    'count',
    'total_residual_samples',
    'valid_samples',
    'unavailable_samples',
    'total_candidate_points',
    'projected_forward_valid',
    'mapping_unavailable',
    'nonforward_horizon',
    'out_of_domain',
    'valid_in_domain',
    'unavailable_count',
    'frames',
    'both_visible_frames',
    'both_matched_frames',
    'available_frames',
    'unavailable_frames',
    'both_visible_denominator',
    'total_frames',
    'both_visible',
    'both_matched',
    'center_unavailable',
    'left_unavailable',
    'right_unavailable',
    'candidate_count',
  }
  if field in integers:
    if type(value) is not int or value < 0:
      raise ValueError('SCALAR_NONNEGATIVE_COUNT_REQUIRED')
    return
  if field in {'left', 'right', 'center', 'combined', 'lateral_m'}:
    if type(value) is not dict:
      raise ValueError('SCALAR_DISTRIBUTION_REQUIRED')
    old._distribution(value)
    return
  if field == 'bin_edges_m':
    if value not in [list(m.BIN_EDGES[i : i + 2]) for i in range(6)]:
      raise ValueError('DECLARED_DISTANCE_BIN_EDGES_REQUIRED')
    return
  if field in {
    'median',
    'p90',
    'p95',
    'maximum',
    'minimum_p95_m',
    'maximum_p95_m',
    'minimum_p50_m',
    'maximum_p50_m',
    'p50_m',
    'p95_m',
    'p95_minus_p50_m',
    'sampled_spread_m',
    'uncertainty_m',
    'width_m',
    'unavailable_rate',
    'both_boundary_matching_rate',
    'projected_query_forward_m',
  }:
    if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
      raise ValueError('SCALAR_FINITE_STATISTIC_REQUIRED')
    return
  if value is None or type(value) is bool:
    return
  if type(value) in (int, float) and math.isfinite(value):
    return
  if type(value) is str and (value in ENUMS or len(value) == 3 and value[0] == 'S' and value[1:].isdigit()):
    return
  if type(value) is list:
    if any(type(v) is not dict for v in value):
      raise ValueError('STRUCTURED_ROWS_ONLY_NO_COORDINATE_ARRAYS')
    for v in value:
      safe_numbers(v)
    return
  if type(value) is dict and set(value) <= STAT_KEYS:
    for k, v in value.items():
      safe_numbers(v, k)
    return
  raise ValueError('PUBLIC_NUMERIC_AGGREGATE_ONLY')


def table_shapes(report):
  common = {'group', 'mapping', 'scenario_id'}
  fixed = common | {
    'distance_query_m',
    'projected_query_forward_m',
    'total_residual_samples',
    'valid_samples',
    'unavailable_samples',
    'lateral_m',
    'synthetic_query_outside_image',
    'residual_semantics',
  }
  projected = common | {
    'total_candidate_points',
    'projected_forward_valid',
    'mapping_unavailable',
    'nonforward_horizon',
    'out_of_domain',
    'valid_in_domain',
    'unavailable_count',
    'unavailable_rate',
    'lateral_m',
    'bins',
    'coverage_semantics',
  }
  extrema = {
    'group',
    'distance_m',
    'factor',
    'minimum_p95_m',
    'maximum_p95_m',
    'width_m',
    'minimum_scenario',
    'maximum_scenario',
    'minimum_mapping',
    'maximum_mapping',
    'candidate_count',
    'separate_not_additive',
  }
  pixel = {'group', 'distance_m', 'factor', 'mapping', 'p50_m', 'p95_m', 'p95_minus_p50_m', 'status'}
  intrinsic = {'group', 'distance_m', 'factor', 'candidate_count', 'sampled_spread_m', 'uncertainty_m', 'status'}
  envelope = {
    'group',
    'distance_m',
    'minimum_p95_m',
    'maximum_p95_m',
    'minimum_p50_m',
    'maximum_p50_m',
    'minimum_scenario',
    'maximum_scenario',
    'minimum_mapping',
    'maximum_mapping',
    'candidate_count',
    'envelope_scope',
  }
  for name, allowed in (
    ('fixed_distance', [fixed]),
    ('holdout_projection', [projected]),
    ('scenario_attribution', [extrema, pixel, intrinsic]),
    ('all_declared_envelopes', [envelope]),
  ):
    rows = report[name]
    if type(rows) is not list or any(type(r) is not dict or set(r) not in allowed for r in rows):
      raise ValueError('EXACT_AGGREGATE_TABLE_SHAPE_REQUIRED')
  for r in report['holdout_projection']:
    if type(r['bins']) is not list or len(r['bins']) != 6:
      raise ValueError('SIX_DISTANCE_BINS_REQUIRED')
    for b in r['bins']:
      if type(b) is not dict or set(b) != {
        'distance_m',
        'bin_edges_m',
        'lateral_m',
        'small_sample',
        'candidate_count',
        'unavailable_count',
        'unavailable_rate',
      }:
        raise ValueError('EXACT_BIN_SHAPE_REQUIRED')


def publication(report):
  unseal(report)
  if report.get('executor_identity') != executor_identity():
    raise ValueError('EXECUTED_SOURCE_OR_ENVIRONMENT_CHANGED')
  if report.get('status') != 'CONDITIONAL_DIAGNOSTIC_COMPLETE':
    raise ValueError('FIXED_CONDITIONAL_DIAGNOSTIC_STATUS_REQUIRED')
  if report.get('schema') != 'DECLARED_HYPOTHESIS_APPROX_METER_ENVELOPE_V1':
    raise ValueError('CONDITIONAL_SCHEMA_REQUIRED')
  if any(report.get(k) is not False for k in m.FIREWALL):
    raise ValueError('NO_QUALIFICATION_OR_RETUNING')
  if report['policy'] != m.policy():
    raise ValueError('EXACT_FROZEN_PROBE_POLICY_REQUIRED')
  table_shapes(report)
  for key in ('fixed_distance', 'holdout_projection', 'scenario_attribution', 'all_declared_envelopes'):
    safe_numbers(report[key])
  # Coverage has only existing validated aggregate numeric groups.
  coverage = report['coverage']
  if coverage != frozen_coverage():
    raise ValueError('HISTORICAL_FRAME_COVERAGE_CHANGED')
  for k, v in coverage.items():
    if k == 'groups':
      for group in v.values():
        safe_numbers(group)
    else:
      safe_numbers(v)
  allowed_bindings = {'analysis_sha256', 'reference_sha256', 'evaluation_sha256', 'detector_set_sha256', 'manifest_binding_set_sha256', 'policy_sha256'}
  if not set(report['source_bindings']) <= allowed_bindings:
    raise ValueError('PUBLIC_BINDING_ALLOWLIST')
  if report['source_bindings'] != frozen_bindings():
    raise ValueError('ORIGINAL_EVIDENCE_BINDINGS_REQUIRED')
  for v in report['source_bindings'].values():
    m.c.sha(v)
  m.c.sha(report['point_derivative_set_sha256'])
  return m.output(
    {
      'schema': report['schema'],
      'local_report_sha256': report['receipt_sha256'],
      **{k: report[k] for k in PUBLIC_KEYS},
      'conditional_transforms': m.transforms(),
      'scenarios': m.scenarios(),
      'open_terms': list(m.OPEN_TERMS),
      'input_domain': 'AI_ASSISTED_HUMAN_PIXEL_REFERENCE',
      'fixed_semantics': 'DETECTOR_EQUIVALENT_LATERAL_DIAGNOSTIC_AT_NOMINAL_QUERY',
      'projected_semantics': 'EACH_OBSERVED_MATCHED_RAY_INTERSECTED_SEPARATELY',
      'independent_meter_validation': 'NOT_RUN',
    }
  )


def validate_public(report):
  unseal(report)
  local = m.output({'schema': 'DECLARED_HYPOTHESIS_APPROX_METER_ENVELOPE_V1', **{k: report[k] for k in PUBLIC_KEYS}})
  if local['receipt_sha256'] != report.get('local_report_sha256') or publication(local) != report:
    raise ValueError('EXACT_REDACTED_PUBLIC_REPORT_REQUIRED')
  return report


def immutable_write(path, data):
  p = Path(path)
  p.parent.mkdir(parents=True, exist_ok=True)
  if p.exists():
    if p.is_symlink() or p.read_bytes() != data:
      raise ValueError('IMMUTABLE_DERIVATIVE_CONFLICT')
    return digest(data)
  fd, name = tempfile.mkstemp(prefix='.pending-', dir=p.parent)
  try:
    with os.fdopen(fd, 'wb') as f:
      f.write(data)
      f.flush()
      os.fsync(f.fileno())
    # Single offline executor. Never overwrite a completed derivative.
    if p.exists():
      raise ValueError('IMMUTABLE_DERIVATIVE_CONFLICT')
    os.link(name, p)
    dfd = os.open(p.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
      os.fsync(dfd)
    finally:
      os.close(dfd)
  finally:
    os.unlink(name)
  return digest(data)


def _attribution(rows):
  out = []
  scenarios = m.scenarios()
  for group in ('left', 'right', 'center'):
    for distance in m.DISTANCES:
      rr = [r for r in rows if r['group'] == group and r['distance_query_m'] == distance]
      for factor in ('height', 'pitch', 'roll', 'yaw', 'mapping'):

        def include(r, factor=factor):
          s = scenarios[int(r['scenario_id'][1:])]
          if factor == 'mapping':
            return s['height_m'] == 1.385
          if r['mapping'] != 'CENTER_ALIGNED':
            return False  # Explicit contrast anchor only, never truth selection.
          hgt, rpy = s['height_m'], s['rpy_deg']
          if factor == 'height':
            return rpy == [0.0, 2.34, 0.2]
          if factor == 'pitch':
            return hgt == 1.4 and rpy[0] == 0 and rpy[2] == 0.2
          if factor == 'roll':
            return hgt == 1.4 and rpy[1:] == [2.34, 0.2]
          if factor == 'yaw':
            return hgt == 1.4 and rpy[:2] == [0.0, 2.34]
          return hgt == 1.385

        selected = [r for r in rr if include(r) and r['lateral_m']['p95'] is not None]
        if not selected:
          continue
        lo = min(selected, key=lambda r: r['lateral_m']['p95'])
        hi = max(selected, key=lambda r: r['lateral_m']['p95'])
        out.append(
          {
            'group': group,
            'distance_m': distance,
            'factor': factor,
            'minimum_p95_m': lo['lateral_m']['p95'],
            'maximum_p95_m': hi['lateral_m']['p95'],
            'width_m': hi['lateral_m']['p95'] - (lo['lateral_m']['p95']),
            'minimum_scenario': lo['scenario_id'],
            'maximum_scenario': hi['scenario_id'],
            'minimum_mapping': lo['mapping'],
            'maximum_mapping': hi['mapping'],
            'candidate_count': len(selected),
            'separate_not_additive': True,
          }
        )
      nominal_rows = [r for r in rr if scenarios[int(r['scenario_id'][1:])]['height_m'] == 1.385]
      for r in nominal_rows:
        out.append(
          {
            'group': group,
            'distance_m': distance,
            'factor': 'pixel_residual',
            'mapping': r['mapping'],
            'p50_m': r['lateral_m']['median'],
            'p95_m': r['lateral_m']['p95'],
            'p95_minus_p50_m': None if r['lateral_m']['p95'] is None else r['lateral_m']['p95'] - r['lateral_m']['median'],
            'status': 'FROZEN_RESIDUAL_SPREAD_NOT_PARAMETER_UNCERTAINTY',
          }
        )
      out.append(
        {
          'group': group,
          'distance_m': distance,
          'factor': 'intrinsics',
          'candidate_count': 1,
          'sampled_spread_m': None,
          'uncertainty_m': None,
          'status': 'FIXED_PRIOR_NO_INTRINSICS_SWEEP',
        }
      )
  return out


def executor_identity():
  if digest(Path(__file__).read_bytes()) != EXECUTED_SOURCE_SHA:
    raise ValueError('RUNNING_METER_EXECUTOR_SOURCE_CHANGED')
  m.policy()
  for x in (m, m.q, m.a, h, metric, old):
    if digest(Path(x.__file__).read_bytes()) != HELPERS[Path(x.__file__).name]:
      raise ValueError('RUNNING_METER_HELPER_SOURCE_CHANGED')
  return {
    'helper_source_sha256': dict(HELPERS),
    'math_source_sha256': m.EXECUTED_SOURCE_SHA,
    'executor_source_sha256': EXECUTED_SOURCE_SHA,
    'python_version': platform.python_version(),
    'numpy_version': np.__version__,
    'platform': 'OFFLINE_CPU_FLOAT64',
    'orientation_source_sha256': a_source(),
  }


def a_source():
  return m.q.digest(m.q.canonical(m.a.source_identity()))


def frozen_coverage():
  r = m.frozen('private-assisted-holdout-final-aggregate-v1.json', AGGREGATE_RECEIPT)
  return {
    'total_frames': 60,
    'both_visible': r['center']['both_visible_denominator'],
    'both_matched': sum(g['both_matched_frames'] for g in r['groups'].values()),
    'center_unavailable': r['center']['unavailable_frames'],
    'left_unavailable': sum(g['left_unavailable'] for g in r['confidence']['buckets'].values()),
    'right_unavailable': sum(g['right_unavailable'] for g in r['confidence']['buckets'].values()),
    'groups': r['groups'],
  }


def frozen_bindings():
  r = m.frozen('private-assisted-holdout-final-aggregate-v1.json', AGGREGATE_RECEIPT)
  return {
    'analysis_sha256': r['local_analysis_sha256'],
    'reference_sha256': r['reference_sha256'],
    'evaluation_sha256': r['evaluation_sha256'],
    'detector_set_sha256': '85b79ee6bcf9f013ca0bcd2e1f88428ff7249dcd0c899a3c881bd132a4608324',
    'manifest_binding_set_sha256': r['binding_set_sha256'],
    'policy_sha256': r['policy_sha256'],
  }


def envelopes(rows):
  out = []
  for group in ('left', 'right', 'center'):
    for d in m.DISTANCES:
      chosen = [r for r in rows if r['group'] == group and r['distance_query_m'] == d and r['lateral_m']['p95'] is not None]
      if not chosen:
        continue
      lo = min(chosen, key=lambda r: r['lateral_m']['p95'])
      hi = max(chosen, key=lambda r: r['lateral_m']['p95'])
      out.append(
        {
          'group': group,
          'distance_m': d,
          'minimum_p95_m': lo['lateral_m']['p95'],
          'maximum_p95_m': hi['lateral_m']['p95'],
          'minimum_p50_m': min(r['lateral_m']['median'] for r in chosen),
          'maximum_p50_m': max(r['lateral_m']['median'] for r in chosen),
          'minimum_scenario': lo['scenario_id'],
          'maximum_scenario': hi['scenario_id'],
          'minimum_mapping': lo['mapping'],
          'maximum_mapping': hi['mapping'],
          'candidate_count': len(chosen),
          'envelope_scope': 'DECLARED_SAMPLED_HYPOTHESES_NOT_TOTAL_PHYSICAL_BOUND',
        }
      )
  return out


def compute(pairs, coverage, bindings, local_bindings, destination):
  fixed, projected, derivatives = [], [], []
  execution = executor_identity()
  immutable_write(Path(destination) / 'execution-policy.json', canonical(m.output({'policy': m.policy(), 'executor_identity': execution})))
  ss = m.scenarios()
  for scenario in ss:
    for rule in m.q.RULES:
      for side, points in pairs.items():
        residuals = [abs(x[0] - x[2]) for x in points]
        for d in m.DISTANCES:
          fixed.append({'group': side, 'mapping': rule, 'scenario_id': scenario['scenario_id'], **m.analytic(residuals, d, scenario, rule)})
        p = m.project_pairs(points, scenario, rule)
        projected.append({'group': side, 'mapping': rule, 'scenario_id': scenario['scenario_id'], **m.summarize(p)})
        af = m.transforms()[rule]['affine']
        arr = np.array(points, dtype=float).reshape(-1, 4)
        native_h = m.q.forward(arr[:, :2], af).tolist() if len(arr) else []
        native_d = m.q.forward(arr[:, 2:], af).tolist() if len(arr) else []
        clean = {k: [None if not math.isfinite(float(v)) else float(v) for v in vals] if k != 'valid' else vals.tolist() for k, vals in p.items()}
        derivative = m.output(
          {
            'schema': 'HOLDOUT_POINT_PROJECTED_ENVELOPE_LOCAL_V1',
            'source_bindings': bindings,
            'executor_identity': execution,
            'scenario': scenario,
            'mapping': rule,
            'group': side,
            'qcamera_pairs': points,
            'native_human': native_h,
            'native_detector': native_d,
            'projection': clean,
            'frame_counts': local_bindings,
          }
        )
        data = gzip.compress(canonical(derivative), mtime=0)
        sha = immutable_write(Path(destination) / (scenario['scenario_id'] + '-' + rule + '-' + side + '.json.gz'), data)
        derivatives.append(sha)
  result = m.output(
    {
      'schema': 'DECLARED_HYPOTHESIS_APPROX_METER_ENVELOPE_V1',
      'status': 'CONDITIONAL_DIAGNOSTIC_COMPLETE',
      'policy': m.policy(),
      'source_bindings': bindings,
      'coverage': coverage,
      'fixed_distance': fixed,
      'holdout_projection': projected,
      'scenario_attribution': _attribution(fixed),
      'all_declared_envelopes': envelopes(fixed),
      'executor_identity': execution,
      'point_derivative_set_sha256': digest(canonical(derivatives)),
    }
  )
  immutable_write(Path(destination) / 'local-report.json', canonical(result))
  return publication(result)


def feasibility():
  return m.output(
    {
      'schema': 'NON_TARGET_POSE_DISTANCE_CROSSCHECK_FEASIBILITY_V1',
      'existing_inventory_sha256': m.q.AUDIT_SHA,
      'new_private_inputs_opened': False,
      'raw_imu_payload_read': False,
      'imu': {
        'status': 'IMU_CAMERA_TRANSFORM_UNAVAILABLE',
        'event_availability': 'NOT_AUDITED_PAYLOAD_READ_NOT_AUTHORIZED',
        'stationary_interval_evidence': None,
        'validated_device_to_camera_transform': None,
      },
      'stereo': {
        'status': 'STEREO_DISTANCE_DIAGNOSTIC_UNAVAILABLE',
        'synchronized_wide_narrow_pairs': 'NOT_ESTABLISHED_BY_EXISTING_INVENTORY',
        'native_qcamera_pairs_in_existing_inventory': 0,
        'pair_intrinsics_extrinsics_baseline': None,
        'triangulation_conditioning': None,
        'distances_m': list(m.DISTANCES),
      },
      'vanishing_point': {'status': 'NOT_RUN_OPTIONAL_SUPPORT_ONLY', 'physical_calibration_promotable': False},
    }
  )


def main():
  parser = argparse.ArgumentParser(description='Offline declared pinhole hypotheses, not physical meter truth')
  for name in ('analysis', 'reference', 'evaluation', 'detector-rows', 'local-output', 'public-output'):
    parser.add_argument('--' + name, required=True)
  args = parser.parse_args()
  local = Path(args.local_output).resolve()
  public = Path(args.public_output).resolve()
  if local == public or local.is_relative_to(m.c.ROOT) or public.is_relative_to(local) or local.is_relative_to(public):
    raise ValueError('SEPARATE_LOCAL_PRIVATE_AND_PUBLIC_OUTPUT_REQUIRED')
  pairs, coverage, bindings, frame_counts = load_frozen(args.analysis, args.reference, args.evaluation, args.detector_rows)
  report = compute(pairs, coverage, bindings, frame_counts, local)
  immutable_write(public / 'declared-hypothesis-meter-envelope-v1.json', canonical(report))
  prior = read(m.ROOT / 'qcamera-recorded-runtime-readiness-v1.json')
  immutable_write(public / 'declared-hypothesis-meter-readiness-v1.json', canonical(m.readiness(report, prior)))
  immutable_write(public / 'dual-camera-distance-feasibility-v1.json', canonical(feasibility()))
  print(
    json.dumps(
      {
        'status': report['status'],
        'scenarios': len(m.scenarios()),
        'mappings': len(m.q.RULES),
        'point_counts': {k: len(v) for k, v in pairs.items()},
        'receipt_sha256': report['receipt_sha256'],
      }
    )
  )


if __name__ == '__main__':
  main()
