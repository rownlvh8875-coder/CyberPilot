"""Completion-gated, sample-pooled public diagnostic distributions and strata."""

import argparse
from array import array
import json
import numpy as np
from collections import Counter
from pathlib import Path

from openpilot.tools.cyber_autotune import lane_public_storage as storage
from openpilot.tools.cyber_autotune import lane_tail_diagnostics as t
from openpilot.tools.cyber_autotune import lane_tail_review_contract as c
from openpilot.tools.cyber_autotune import lane_tail_review_ui as ui
from openpilot.tools.cyber_autotune import lane_public_batch as b
from openpilot.tools.cyber_autotune import lane_detector_runner as r
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

DIRECTIONS = ('pred', 'gt', 'paired_spatial_pred')

HISTORICAL_PROTOCOL_SHA = '1b6a1d3f3dda87a8ae173e3e1a32b9d5c86a488bb2af8a84374348ca45a14f4e'


def historical_subset_protocol(data):
  if digest(data) != HISTORICAL_PROTOCOL_SHA:
    raise ValueError('IMMUTABLE_HISTORICAL_SUBSET_PROTOCOL_REQUIRED')
  return json.loads(data)


def count_bucket(value, bins):
  if type(value) is not int or value < 0:
    raise ValueError('NONNEGATIVE_COUNT_REQUIRED')
  found = [i for i, (lo, hi) in enumerate(bins) if lo <= value and (hi is None or value <= hi)]
  if len(found) != 1:
    raise ValueError('EXACT_COUNT_BUCKET_REQUIRED')
  return found[0]


def distribution(values):
  value = t.distribution(values)
  return {**value, 'p50': value['median']}


def empty_pool():
  return {k: array('d') for k in DIRECTIONS}


def analyze(values, completion):
  marker = unseal(completion)
  if (
    marker.get('storage_status') != 'COMPLETED'
    or marker.get('processed') != marker.get('expected')
    or type(marker.get('expected')) is not int
    or marker['expected'] <= 0
    or marker.get('reference_promotable') is not False
  ):
    raise ValueError('VERIFIED_COMPLETION_REQUIRED')
  pools = empty_pool()
  counts = Counter()
  seen = set()
  ids = set()
  bins = c.selection_policy()['count_buckets']
  buckets = {k: [{'frame_count': 0, 'pool': empty_pool()} for _ in choices] for k, choices in bins.items()}
  regions = {
    k: {
      'pred': array('d'),
      'gt': array('d'),
      'gt_runs': 0,
      'covered_runs': 0,
      'pred_points': 0,
      'unsupported_points': 0,
      'off_mask_points': 0,
      'missed_runs': 0,
      'frame_count': 0,
      'unavailable_frames': 0,
      'no_prediction_frames': 0,
    }
    for k in ('far', 'mid', 'near')
  }
  coverage = Counter()
  frame_rows = 0
  for value in values:
    core = unseal(value)
    entry = unseal(core['ledger'])
    ordinal = core['ordinal']
    if (
      type(ordinal) is not int
      or not 0 <= ordinal < marker['expected']
      or ordinal in seen
      or entry['frame_id'] in ids
      or core['frame_status'] not in ('COMPLETED', 'REFERENCE_UNAVAILABLE')
      or core['run_sha256'] != marker['run_sha256']
    ):
      raise ValueError('EXACT_COMPLETED_FRAME_SET_REQUIRED')
    seen.add(ordinal)
    ids.add(entry['frame_id'])
    frame_rows += 1
    counts[entry['failure_category']] += 1
    coverage['no_prediction_frames'] += entry.get('prediction_count', entry['raw_prediction_count']) == 0
    coverage['no_raw_output_frames'] += entry['raw_prediction_count'] == 0
    coverage['gt_eligible_frames'] += entry['gt_components'] > 0
    coverage['gt_eligible_no_prediction_frames'] += entry['gt_components'] > 0 and entry.get('prediction_count', entry['raw_prediction_count']) == 0
    coverage['tail_frame_count'] += entry['row_tail_points'] > 0
    coverage['usable_frames'] += bool(core['pool']['pred']) and bool(core['pool']['gt'])
    coverage['unavailable_frames'] += not core['pool']['pred'] or not core['pool']['gt']
    coverage['false_positive_components'] += entry.get('false_positive_components', 0)
    coverage['unmatched_gt_components'] += entry.get('missed_gt_components', 0)
    frame_counts = {
      'gt_components': entry['gt_components'],
      'raw_prediction_count': entry['raw_prediction_count'],
      'mask_complexity_gt_row_runs': sum(reg['gt_runs'] for reg in core['regions'].values()),
    }
    for name, choices in bins.items():
      item = buckets[name][count_bucket(frame_counts[name], choices)]
      item['frame_count'] += 1
      for k in DIRECTIONS:
        item['pool'][k].extend(core['pool'][k])
    for k in DIRECTIONS:
      pools[k].extend(core['pool'][k])
    for name, reg in core['regions'].items():
      dest = regions[name]
      dest['frame_count'] += 1
      dest['unavailable_frames'] += not reg['pred'] or not reg['gt']
      dest['no_prediction_frames'] += reg['pred_points'] == 0
      for k in ('pred', 'gt'):
        dest[k].extend(reg[k])
      for k in ('gt_runs', 'covered_runs', 'pred_points', 'unsupported_points', 'off_mask_points', 'missed_runs'):
        dest[k] += reg[k]
  if frame_rows != marker['expected']:
    raise ValueError('NO_AGGREGATE_BEFORE_ALL_FRAMES')

  def summarize(pool):
    return {k: distribution(pool[k]) for k in DIRECTIONS}

  bucket_report = {
    k: [{'bounds': bounds, 'frame_count': item['frame_count'], 'directions': summarize(item['pool'])} for bounds, item in zip(bins[k], items, strict=True)]
    for k, items in buckets.items()
  }
  regional = {
    k: {
      **{f: v for f, v in item.items() if f not in ('pred', 'gt')},
      'pred_to_gt': distribution(item['pred']),
      'gt_to_pred': distribution(item['gt']),
      'coverage': item['covered_runs'] / item['gt_runs'] if item['gt_runs'] else None,
    }
    for k, item in regions.items()
  }
  total = {
    k: sum(item[k] for item in regions.values()) for k in ('gt_runs', 'covered_runs', 'pred_points', 'unsupported_points', 'off_mask_points', 'missed_runs')
  }
  return seal(
    {
      'schema': 'PUBLIC_FULL_DIAGNOSTIC_ANALYSIS_V1',
      'analysis_source_sha256': digest(Path(__file__).read_bytes()),
      'selection_policy_sha256': c.POLICY_SHA,
      'metric_source_sha256': digest(Path(t.__file__).read_bytes()),
      'numpy_version': np.__version__,
      'quantile_method': 'linear_sample_pooled',
      'completion_sha256': completion['receipt_sha256'],
      'processed': frame_rows,
      'expected': marker['expected'],
      'directions': summarize(pools),
      'direction_semantics': 'unchanged row pred/gt; paired_spatial_pred uses exact supported-row pred population',
      'coverage': {
        **dict(coverage),
        **total,
        'mask_coverage': total['covered_runs'] / total['gt_runs'] if total['gt_runs'] else None,
        'unsupported_prediction_ratio': total['unsupported_points'] / total['pred_points'] if total['pred_points'] else None,
        'off_mask_prediction_ratio': total['off_mask_points'] / total['pred_points'] if total['pred_points'] else None,
        'detection_failure_rate': coverage['gt_eligible_no_prediction_frames'] / coverage['gt_eligible_frames'] if coverage['gt_eligible_frames'] else None,
        'tail_frame_prevalence': coverage['tail_frame_count'] / frame_rows,
        'missed_marking_ratio': 1 - total['covered_runs'] / total['gt_runs'] if total['gt_runs'] else None,
      },
      'regions': regional,
      'count_buckets': bucket_report,
      'automatic_hypothesis_counts': dict(sorted(counts.items())),
      'human_review_status': 'TAIL_HUMAN_REVIEW_PENDING',
      'unit': 'px',
      'meter_error': None,
      'ego_lane_association_evaluated': False,
      'private_input_opened': False,
      'reference_promotable': False,
    }
  )


def subset_comparison(full, subset):
  unseal(full)
  unseal(subset)
  return seal(
    {
      'schema': 'PUBLIC_SUBSET_REPRESENTATIVENESS_V1',
      'scope': 'DIAGNOSTIC_SUBSET_NOT_QUALIFICATION',
      'full_sha256': full['receipt_sha256'],
      'subset_sha256': subset['receipt_sha256'],
      'full_frames': full['processed'],
      'subset_frames': subset['processed'],
      'direction_deltas': {
        k: {
          q: full['directions'][k][q] - subset['directions'][k][q] if full['directions'][k][q] is not None and subset['directions'][k][q] is not None else None
          for q in ('median', 'p95')
        }
        for k in DIRECTIONS
      },
      'full_coverage': full['coverage'],
      'subset_coverage': subset['coverage'],
      'full_y_regions': full['regions'],
      'subset_y_regions': subset['regions'],
      'full_count_buckets': full['count_buckets'],
      'subset_count_buckets': subset['count_buckets'],
      'qualification_granted': False,
    }
  )


def main():
  parser = argparse.ArgumentParser()
  for key in ('run', 'protocol', 'manifest', 'subset-protocol', 'output'):
    parser.add_argument('--' + key, type=Path, required=True)
  args = parser.parse_args()
  run = storage.read_json(args.run / 'run-freeze.json')
  ui.require_frozen_metric_sources(run)
  protocol = storage.read_json(args.protocol)
  inputs = storage.read_json(args.manifest)
  if digest(args.protocol.read_bytes()) != run['protocol_file_sha256'] or digest(args.manifest.read_bytes()) != run['manifest_file_sha256']:
    raise ValueError('FULL_ANALYSIS_INPUT_FREEZE_MISMATCH')
  r.validate_protocol_pairs(protocol, inputs)
  pairs = protocol['pairs']
  identities = {f['path']: f for f in inputs['files']}
  if len(pairs) != 11888:
    raise ValueError('EXACT_FULL_PUBLIC_POPULATION_REQUIRED')

  def validator(row):
    return b.verify_resume(row, run['receipt_sha256'], row['ordinal'], pairs[row['ordinal']], identities)

  durable = storage.DurableRun(args.run, run, [p['image'] for p in pairs])
  marker = durable.verify_completed(validator)

  def values():
    return (storage.read_json(durable.row_path(i)) for i in range(len(pairs)))

  full = analyze(values(), marker)
  subset_ids = {p['image'] for p in historical_subset_protocol(args.subset_protocol.read_bytes())['pairs']}
  subset_rows = [row for row in values() if row['ledger']['frame_id'] in subset_ids]
  if len(subset_rows) != 119 or {row['ledger']['frame_id'] for row in subset_rows} != subset_ids:
    raise ValueError('EXACT_HISTORICAL_DIAGNOSTIC_SUBSET_REQUIRED')
  subset_marker = seal({'storage_status': 'COMPLETED', 'processed': 119, 'expected': 119, 'run_sha256': run['receipt_sha256'], 'reference_promotable': False})
  # Retain original full ordinal provenance externally; local subset ordinals only for diagnostic pooling.
  remapped = [seal({**unseal(row), 'ordinal': i}) for i, row in enumerate(subset_rows)]
  subset = seal(
    {
      **unseal(analyze(remapped, subset_marker)),
      'schema': 'PUBLIC_HISTORICAL_SUBSET_DERIVED_FROM_COMPLETED_FULL_RUN_V1',
      'parent_full_completion_sha256': marker['receipt_sha256'],
      'historical_subset_protocol_sha256': HISTORICAL_PROTOCOL_SHA,
      'original_full_receipts_sha256': digest(canonical([row['receipt_sha256'] for row in subset_rows])),
    }
  )
  ledger = storage.read_json(args.run / 'ledger.json')
  review = c.freeze_review(ledger, marker, c.selection_policy(), ui.tool_identity())
  storage.atomic_json(args.output / 'full-analysis.json', full)
  storage.atomic_json(args.output / 'subset-analysis.json', subset)
  storage.atomic_json(args.output / 'subset-comparison.json', subset_comparison(full, subset))
  storage.atomic_json(args.output / 'human-review-manifest.json', review)
  print(full['receipt_sha256'], review['receipt_sha256'], flush=True)


if __name__ == '__main__':
  main()
