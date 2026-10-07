"""Replay frozen public lane predictions into a metadata-only tail ledger."""

import argparse
from collections import Counter
import io
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image

from openpilot.tools.cyber_autotune import lane_detector_runner as r
from openpilot.tools.cyber_autotune import lane_tail_diagnostics as t
from openpilot.tools.cyber_autotune.lane_marking_metrics import category2_mask
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


def seal(data):
  return {**data, 'receipt_sha256': digest(canonical(data))}


def unseal(data):
  core = {k: v for k, v in data.items() if k != 'receipt_sha256'}
  if data.get('receipt_sha256') != digest(canonical(core)):
    raise ValueError('TAIL_REPORT_BINDING_MISMATCH')
  return core


def historical_tail_cut():
  path = Path(__file__).resolve().parents[3] / 'docs/cyberpilot/changes/public-lane-detector-diagnostic-result.json'
  with path.open('rb') as stream:
    report = json.load(stream)
  unseal(report)
  if report['receipt_sha256'] != '51184e4182efd3c6b2a7ee5640d4d11a9dc5f4071fabd003e617018885e97888':
    raise ValueError('IMMUTABLE_HISTORICAL_DIAGNOSTIC_REQUIRED')
  return report['localization']['pred_to_gt']['p95']


def analyze_records(files, manifest, pairs, records):
  if len(records) != len(pairs):
    raise ValueError('NO_SILENT_SKIP')
  identities = {f['path']: f for f in manifest['files']}
  ledger, pool = [], {'pred': [], 'gt': [], 'spatial_pred': [], 'spatial_gt': [], 'paired_spatial_pred': []}
  confidence = {
    f'{a:.1f}:{b:.1f}': {
      'lane_count': 0,
      'samples': [],
      'off_mask_points': 0,
      'points': 0,
      'gt_eligible_lanes': 0,
      'distance_available_lanes': 0,
      'large_row_tail_lanes': 0,
      'no_row_support_lanes': 0,
    }
    for a, b in zip(t.policy()['confidence_edges'][:-1], t.policy()['confidence_edges'][1:], strict=True)
  }
  regions = {
    name: {'pred': [], 'gt': [], 'gt_runs': 0, 'covered_runs': 0, 'unsupported_points': 0, 'missed_runs': 0, 'pred_points': 0, 'off_mask_points': 0}
    for name in ('far', 'mid', 'near')
  }
  from openpilot.tools.cyber_autotune.lane_marking_metrics import marking_frame

  for pair, record in zip(pairs, records, strict=True):
    if record['image'] != pair['image']:
      raise ValueError('FRAME_ORDER_BINDING_MISMATCH')
    rgb = np.asarray(Image.open(io.BytesIO(files[pair['mask']])).convert('RGB'))
    mask = category2_mask(rgb)
    r.require_original_geometry(record['image_geometry'], mask.shape)
    t.validate_raw_lanes(record, mask)
    observable = [(lane, score) for lane, score in zip(record['lanes'], record['scores'], strict=True) if lane]
    lanes, scores = [item[0] for item in observable], [item[1] for item in observable]
    start = time.perf_counter()
    entry = t.analyze_frame(mask, lanes, scores)
    union = [list(p) for p in sorted({tuple(p) for lane in lanes for p in lane}, key=lambda p: (p[1], p[0]))]
    if union != record['points']:
      raise ValueError('LANE_UNION_MISMATCH')
    legacy = marking_frame(mask, union)
    gt, pp, gp = t._direction_samples(mask, union)
    pool['pred'].extend(legacy['pred_errors_px'])
    pool['gt'].extend(legacy['gt_errors_px'])
    pool.setdefault('normalized_pred', []).extend(v / mask.shape[1] for v in legacy['pred_errors_px'])
    pool.setdefault('normalized_gt', []).extend(v / mask.shape[1] for v in legacy['gt_errors_px'])
    pool['spatial_pred'].extend(t.spatial_distances(union, gt))
    pool['paired_spatial_pred'].extend(t.spatial_distances([[x, y] for x, y, _ in pp], gt))
    # Retained historical aggregate p95, bound by the immutable published result; not qualification.
    historical_cut = historical_tail_cut()
    semantic = t.semantic_tail(rgb, union, historical_cut)
    for name, item in semantic.items():
      pool.setdefault('semantic_' + name, []).extend(item['samples'])
    entry = unseal(entry)
    entry['semantic_categories'] = {name: {k: v for k, v in item.items() if k != 'samples'} for name, item in semantic.items()}
    spatial_pairs = t.spatial_distances([[x, y] for x, y, _ in pp], gt)
    exact_tail = [(p, d) for p, d in zip(pp, spatial_pairs, strict=True) if p[2] >= historical_cut]
    entry['historical_p95_tail_points'] = len(exact_tail)
    entry['historical_p95_tail_spatially_resolved_points'] = sum(d <= mask.shape[1] * t.policy()['spatial_resolved_width_fraction'] for _, d in exact_tail)
    entry = seal(entry)
    pool['spatial_gt'].extend(t.spatial_distances(gt, union))
    for lane, score in observable:
      item = confidence[t.confidence_bucket(score)]
      sub = marking_frame(mask, lane)
      item['gt_eligible_lanes'] += sub['gt_runs'] > 0
      item['distance_available_lanes'] += bool(sub['pred_errors_px'])
      item['no_row_support_lanes'] += sub['gt_runs'] > 0 and not sub['pred_errors_px']
      item['large_row_tail_lanes'] += any(v > mask.shape[1] * t.policy()['tail_width_fraction'] for v in sub['pred_errors_px'])
      item['lane_count'] += 1
      item['samples'].extend(sub['pred_errors_px'])
      item['off_mask_points'] += sub['off_marking_pred_points']
      item['points'] += len(lane)
    for name, lo, hi in (('far', 0, mask.shape[0] // 3), ('mid', mask.shape[0] // 3, 2 * mask.shape[0] // 3), ('near', 2 * mask.shape[0] // 3, mask.shape[0])):
      sub = marking_frame(mask[lo:hi], [[x, y - lo] for x, y in union if lo <= y < hi])
      reg = regions[name]
      reg['pred'].extend(sub['pred_errors_px'])
      reg['gt'].extend(sub['gt_errors_px'])
      reg['gt_runs'] += sub['gt_runs']
      reg['covered_runs'] += sub['covered_gt_runs']
      reg['unsupported_points'] += sub['unsupported_pred_points']
      reg['missed_runs'] += sub['unavailable_gt_runs']
      reg['pred_points'] += sub['pred_points']
      reg['off_mask_points'] += sub['off_marking_pred_points']
    entry = unseal(entry)
    entry.update(
      {
        'frame_id': pair['image'],
        'image_sha256': identities[pair['image']]['sha256'],
        'gt_mask_sha256': identities[pair['mask']]['sha256'],
        'detector_result_sha256': digest(canonical(record)),
        'raw_prediction_count': record['lane_count'],
        'unobservable_lanes': record['lane_count'] - len(lanes),
        'raw_confidence': record['scores'],
      }
    )
    ledger.append(seal(entry))
    print(json.dumps({'frame': len(ledger), 'seconds': time.perf_counter() - start}), flush=True)
  return ledger, pool, confidence, regions


def review_manifest(ledger):
  ranked = sorted((r for r in ledger if r['pred_to_gt']['p95'] is not None), key=lambda r: (-r['pred_to_gt']['p95'], r['frame_id']))
  reasons = {}

  def choose(records, reason, limit=5):
    for record in records[:limit]:
      reasons.setdefault(record['frame_id'], []).append(reason)

  choose(ranked, 'WORST_P95')
  choose(sorted(ranked, key=lambda r: (r['pred_to_gt']['p95'], r['frame_id'])), 'LOW_ERROR_CONTROL')
  for field, reason in (('false_positive_components', 'NO_EXACT_GT_SUPPORT_COMPONENT'), ('missed_gt_components', 'MISSED_PAINT_COMPONENT')):
    choose(sorted(ledger, key=lambda r: (-r[field], r['frame_id'])), reason)
  choose([r for r in ranked if r['failure_category'] in ('ROW_ASSOCIATION_SENSITIVE', 'MIXED_ROW_AND_SPATIAL_TAIL')], 'ROW_ASSOCIATION_AMBIGUITY')
  return seal(
    {
      'scope': 'PUBLIC_HUMAN_REVIEW_PENDING_NOT_LABELS',
      'raw_images_included': False,
      'frames': [
        {
          'frame_id': r['frame_id'],
          'image_sha256': r['image_sha256'],
          'reasons': reasons[r['frame_id']],
          'pred_to_gt': r['pred_to_gt'],
          'gt_to_pred': r['gt_to_pred'],
          'failure_category': r['failure_category'],
        }
        for r in ledger
        if r['frame_id'] in reasons
      ],
    }
  )


def validate_capture(captured):
  if (
    type(captured) is not dict
    or type(captured.get('exact_repeatability')) is not bool
    or captured.get('schema') not in ('PUBLIC_LANE_CAPTURE_V1', 'PUBLIC_CLRNET_CAPTURE_V1')
    or (
      captured['schema'] == 'PUBLIC_LANE_CAPTURE_V1'
      and (captured.get('historical_union_exact_match') is not True or captured['exact_repeatability'] is not True)
    )
    or captured.get('private_input_opened') is not False
    or captured.get('reference_promotable') is not False
    or captured.get('candidate_outputs_used_for_reference') is not False
    or captured.get('openpilot_path_lane_used') is not False
  ):
    raise ValueError('CAPTURE_SCOPE_OR_REPEATABILITY_FAILED')


def summarize_confidence(buckets):
  return {
    name: {
      'lane_count': b['lane_count'],
      'pred_to_gt': t.distribution(b['samples']),
      'off_mask_point_ratio': b['off_mask_points'] / b['points'] if b['points'] else None,
      'gt_eligible_lanes': b['gt_eligible_lanes'],
      'distance_available_lanes': b['distance_available_lanes'],
      'no_row_support_lanes': b['no_row_support_lanes'],
      'large_row_tail_lanes': b['large_row_tail_lanes'],
      'large_row_tail_rate': b['large_row_tail_lanes'] / b['distance_available_lanes'] if b['distance_available_lanes'] else None,
      'rate_semantics': 'diagnostic width-quarter tail among supported-row observable lanes; NOT confidence gate or official failure rate',
    }
    for name, b in buckets.items()
  }


def make_report(ledger, pool, confidence, regions, capture):
  conf_report = summarize_confidence(confidence)
  regional = {}
  for name, reg in regions.items():
    regional[name] = {k: v for k, v in reg.items() if k not in ('pred', 'gt')}
    regional[name].update(
      {
        'pred_to_gt': t.distribution(reg['pred']),
        'gt_to_pred': t.distribution(reg['gt']),
        'coverage': reg['covered_runs'] / reg['gt_runs'] if reg['gt_runs'] else None,
      }
    )
  report = seal(
    {
      'schema': 'PUBLIC_COMMA10K_TAIL_REPORT_V1',
      'evidence_tier': 'POST_RESULT_DIAGNOSTIC_PUBLIC_GT',
      'metric_implementation_failure_observed': False,
      'legacy_result_invalidated': False,
      'frame_count': len(ledger),
      'gt_eligible_frames': sum(r['coverage'] is not None for r in ledger),
      'no_prediction_frames': sum(r['prediction_count'] == 0 for r in ledger),
      'usable_frames': sum(r['pred_to_gt']['sample_count'] > 0 and r['gt_to_pred']['sample_count'] > 0 for r in ledger),
      'unavailable_frames': sum(r['pred_to_gt']['sample_count'] == 0 or r['gt_to_pred']['sample_count'] == 0 for r in ledger),
      'mask_coverage': (
        sum(reg['covered_runs'] for reg in regions.values()) / sum(reg['gt_runs'] for reg in regions.values())
        if sum(reg['gt_runs'] for reg in regions.values())
        else None
      ),
      'detector_exact_repeatability': capture['exact_repeatability'],
      'capture_receipt_sha256': capture['receipt_sha256'],
      'source_sha256': digest(Path(__file__).read_bytes()),
      'metric_source_sha256': digest(Path(t.__file__).read_bytes()),
      'policy_sha256': t.policy_sha(t.policy()),
      'ledger_sha256': digest(canonical(ledger)),
      'directions': {name: t.distribution(values) for name, values in pool.items() if not name.startswith('normalized_')},
      'normalized_directions': {name: t.distribution(pool[name]) for name in ('normalized_pred', 'normalized_gt')},
      'direction_unit': 'px',
      'normalized_unit': 'fraction_of_original_image_width',
      'symmetric': t.distribution(pool['pred'] + pool['gt']),
      'taxonomy_counts': dict(sorted(Counter(r['failure_category'] for r in ledger).items())),
      'row_tail_points': sum(r['row_tail_points'] for r in ledger),
      'historical_p95_tail_points': sum(r['historical_p95_tail_points'] for r in ledger),
      'historical_p95_tail_spatially_resolved_points': sum(r['historical_p95_tail_spatially_resolved_points'] for r in ledger),
      'historical_p95_semantic_tail': {
        name: sum(r['semantic_categories'][name]['historic_p95_tail_count'] for r in ledger) for name in ledger[0]['semantic_categories']
      },
      'historical_cut_source': 'public-lane-detector-diagnostic-result.json: localization pred_to_gt p95; immutable 608.4058599107527px diagnostic only',
      'row_tail_spatially_resolved_points': sum(r['row_tail_spatially_resolved_points'] for r in ledger),
      'row_tail_still_spatially_remote_points': sum(r['row_tail_still_spatially_remote_points'] for r in ledger),
      'tail_frame_count': sum(r['row_tail_points'] > 0 for r in ledger),
      'confidence_buckets': conf_report,
      'spatial_sample_semantics': (
        'spatial_pred includes all points in nonempty-GT frames; ' + 'paired_spatial_pred uses EXACT legacy supported-row sample population'
      ),
      'confidence_reliability': 'UNCALIBRATED_POST_THRESHOLD_DIAGNOSTIC_NO_GATE_OPTIMIZATION',
      'regions': regional,
      'false_positive_components': sum(r['false_positive_components'] for r in ledger),
      'missed_gt_components': sum(r['missed_gt_components'] for r in ledger),
      'human_review_status': 'PENDING_SEMANTIC_CAUSAL_CATEGORIES_UNRESOLVED',
      'official_reproduction_status': 'BLOCKED_CULANE_DATASET_UNAVAILABLE',
      'private_input_opened': False,
      'reference_promotable': False,
      'meter_error': None,
      'ego_lane_association_evaluated': False,
    }
  )
  return report


def main():
  parser = argparse.ArgumentParser()
  for name in ('capture', 'protocol', 'manifest', 'cache', 'output'):
    parser.add_argument('--' + name, type=Path, required=True)
  args = parser.parse_args()
  captured = unseal(json.loads(args.capture.read_bytes()))
  protocol_bytes = r.read_bound_bytes(args.protocol, captured['protocol_file_sha256'])
  manifest_bytes = r.read_bound_bytes(args.manifest, captured['manifest_file_sha256'])
  protocol, manifest = json.loads(protocol_bytes), json.loads(manifest_bytes)
  r.validate_protocol_pairs(protocol, manifest)
  files = r.verify_inputs(args.cache, manifest)
  records = json.loads(args.capture.with_suffix('.records.json').read_bytes())
  validate_capture(captured)
  if digest(canonical(records)) != captured['records_sha256']:
    raise ValueError('CAPTURE_ARTIFACT_BINDING_MISMATCH')
  ledger, pool, confidence, regions = analyze_records(files, manifest, protocol['pairs'], records)
  report = make_report(ledger, pool, confidence, regions, json.loads(args.capture.read_bytes()))
  args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
  args.output.with_suffix('.ledger.json').write_text(json.dumps(ledger, indent=2, sort_keys=True) + '\n')
  args.output.with_suffix('.review.json').write_text(json.dumps(review_manifest(ledger), indent=2, sort_keys=True) + '\n')
  print(json.dumps(report), flush=True)


if __name__ == '__main__':
  main()
