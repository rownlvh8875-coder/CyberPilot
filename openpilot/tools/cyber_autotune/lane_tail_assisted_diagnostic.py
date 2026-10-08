"""Public assisted-review associations, never independent attribution or qualification."""

from collections import Counter
from datetime import datetime
import math
from pathlib import Path

from openpilot.tools.cyber_autotune import lane_tail_ai_review as a
from openpilot.tools.cyber_autotune import lane_public_storage as s
from openpilot.tools.cyber_autotune import lane_tail_review_contract as c
from openpilot.tools.cyber_autotune import lane_tail_review_workflow as w
from openpilot.tools.cyber_autotune import lane_tail_diagnostics as t
from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

METRICS = {'pred': 'pred_to_gt', 'paired_spatial_pred': 'same_point_2d', 'gt': 'gt_to_pred'}
REGIONS = ('far', 'mid', 'near')  # Existing normalized image thirds; not calibrated ground distances.
REPRESENTATIVES = 3  # Existing diagnostic convention, deterministic frame-ID order.
ASSOCIATIONS = {
  'DETECTOR_FAILURE_ASSOCIATION': c.LABELS[:3],
  'MARKING_GT_AMBIGUITY_ASSOCIATION': ('GT_MASK_AMBIGUOUS', 'GT_EXTRA_MARKING'),
  'REPRESENTATION_MISMATCH_ASSOCIATION': ('REPRESENTATION_MISMATCH',),
  'COMPONENT_MATCHING_ASSOCIATION': ('COMPONENT_MATCHING_ERROR',),
  'FAR_FIELD_MULTI_LANE_ASSOCIATION': ('FAR_FIELD_AMBIGUOUS', 'INTERSECTION_OR_MERGE', 'MULTI_LANE_AMBIGUOUS'),
  'OTHER_OR_UNRESOLVED_ASSOCIATION': ('OTHER', 'UNRESOLVED'),
}
# Historical V1 replay of the exact frozen29 original vectors, not a detector threshold.
# Published independently of this producer identity to avoid a self-referential hash.
PUBLIC_METRIC_SUMMARY_SHA = '8a874a753197042ee53ccd1acb9cef1ea37b48c1ce332fcc4adc6868a6e6e2f0'
POLICY = {
  'schema': 'ASSISTED_TAIL_DIAGNOSTIC_POLICY_V1',
  'historical_public_metric_summary_sha256': PUBLIC_METRIC_SUMMARY_SHA,
  'labels': list(c.LABELS),
  'aggregation': 'ORIGINAL_POINT_WEIGHTED_LINEAR_QUANTILES_PX_NO_FILTER_OR_IMPUTATION',
  'availability': 'EMPTY_VECTORS_NULL_NOT_ZERO; report_available_frame_and_sample_counts',
  'regions': list(REGIONS),
  'detector_confidence': 'EXISTING_BINS_OF_FRAME_MEDIAN_SCORE_NOT_AI_OR_REVIEWER_CONFIDENCE',
  'associations': ASSOCIATIONS,
  'other': 'MAY_INCLUDE_CORRECT_DETECTION_NOT_A_FAILURE_LABEL',
  'scope': 'SELECTED_29_DIAGNOSTIC_SAMPLE_NOT_CAUSAL_POPULATION_PERCENTAGE',
  'concordance': 'ASSISTED_REVIEW_CONCORDANCE_NOT_INDEPENDENT_AI_ACCURACY',
  'detector_verdict': 'DETECTOR_QUALIFICATION_BLOCKED_NO_JUSTIFIED_ACCEPTANCE_THRESHOLD',
  'private_input_allowed': False,
  'reference_promotable': False,
}
POLICY_SHA = digest(canonical(POLICY))


def identity():
  return digest(canonical({'source': digest(Path(__file__).read_bytes()), 'ai_tool': a.tool_identity(), 'policy': POLICY_SHA}))


def utc(value):
  if type(value) is not str or not value.endswith('Z'):
    raise ValueError('CANONICAL_UTC_TIMESTAMP_REQUIRED')
  parsed = datetime.fromisoformat(value[:-1] + '+00:00')
  if parsed.isoformat().replace('+00:00', 'Z') != value:
    raise ValueError('CANONICAL_UTC_TIMESTAMP_REQUIRED')
  return parsed


def validate_assisted(manifest, human_export, experiment, suggestions):
  """Validate immutable evidence relationships before any metric loader is called."""
  w.require_manifest(manifest)
  a.validate_experiment(manifest, experiment)
  n = len(manifest['frames'])
  core = unseal(human_export)
  expected_keys = {
    'schema',
    'blind_human_export',
    'assisted_human_rows',
    'provenance',
    'ai_progress',
    'review_manifest_sha256',
    'blind_independent_complete',
    'private_input_allowed',
    'reference_promotable',
  }
  if (
    set(core) != expected_keys
    or core['schema'] != 'AI_AWARE_HUMAN_EXPORT_V1'
    or core['review_manifest_sha256'] != manifest['receipt_sha256']
    or core['blind_independent_complete'] is not False
    or core['private_input_allowed'] is not False
    or core['reference_promotable'] is not False
    or core['blind_human_export'] != w.export_review(manifest, [])
  ):
    raise ValueError('EXACT_ASSISTED_EXPORT_REQUIRED')
  rows = w.ordered_rows(manifest, core['assisted_human_rows'])
  if len(rows) != n:
    raise ValueError('ASSISTED_REVIEW_INCOMPLETE')
  if type(suggestions) is not list or len(suggestions) != n:
    raise ValueError('EXACT_AI_SUGGESTIONS_REQUIRED')
  ai = {}
  for suggestion in suggestions:
    a.validate_suggestion(manifest, experiment, suggestion)
    if suggestion['frame_id'] in ai:
      raise ValueError('DUPLICATE_AI_SUGGESTION')
    ai[suggestion['frame_id']] = suggestion
  expected_progress = seal(
    {
      'schema': 'AI_PREREVIEW_PROGRESS_V1',
      'status': 'AI_PREREVIEW_COMPLETE',
      'suggestions': n,
      'expected': n,
      'human_label': None,
      'experiment_sha256': experiment['receipt_sha256'],
      'tier': 'SUPPORTING_DIAGNOSTIC_ONLY',
      'private_input_allowed': False,
      'reference_promotable': False,
    }
  )
  if core['ai_progress'] != expected_progress:
    raise ValueError('ASSISTED_AI_PROGRESS_DRIFT')
  provenance = unseal(core['provenance'])
  if (
    set(provenance) != {'schema', 'review_manifest_sha256', 'exposures', 'scope_limit', 'reference_promotable'}
    or provenance['schema'] != 'AI_HUMAN_PROVENANCE_V1'
    or provenance['review_manifest_sha256'] != manifest['receipt_sha256']
    or provenance['scope_limit'] != a.POLICY['scope_limit']
    or provenance['reference_promotable'] is not False
    or type(provenance['exposures']) is not list
    or len(provenance['exposures']) != n
  ):
    raise ValueError('ASSISTED_PROVENANCE_REQUIRED')
  exposures = {}
  for raw in provenance['exposures']:
    e = unseal(raw)
    if (
      set(e)
      != {
        'schema',
        'frame',
        'manifest_sha256',
        'tool_sha256',
        'first_suggestion_sha256',
        'first_experiment_sha256',
        'human_annotation_sha256',
        'mode',
        'timestamp',
      }
      or e['schema'] != 'AI_FIRST_EXPOSURE_V1'
      or e['frame'] not in manifest['frames']
      or e['manifest_sha256'] != manifest['receipt_sha256']
      or e['tool_sha256'] != a.tool_identity()
      or e['mode'] != 'ASSISTED_HUMAN_REVIEW'
      or e['human_annotation_sha256'] is not None
      or e['first_experiment_sha256'] != experiment['receipt_sha256']
    ):
      raise ValueError('ASSISTED_EXPOSURE_BINDING_MISMATCH')
    key = e['frame']['frame_id']
    if key in exposures or e['first_suggestion_sha256'] != ai[key]['receipt_sha256']:
      raise ValueError('DUPLICATE_OR_STALE_ASSISTED_EXPOSURE')
    exposures[key] = raw
  bindings = []
  for row in rows:
    exposure = exposures[row['frame_id']]
    suggestion = ai[row['frame_id']]
    if utc(suggestion['timestamp']) > utc(exposure['timestamp']):
      raise ValueError('SUGGESTION_NOT_AVAILABLE_AT_EXPOSURE')
    if utc(exposure['timestamp']) > utc(row['review_timestamp']):
      raise ValueError('AI_EXPOSURE_NOT_BEFORE_HUMAN_DECISION')
    bindings.append(
      seal(
        {
          'schema': 'ASSISTED_HUMAN_ROW_RELATION_V1',
          'frame_id': row['frame_id'],
          **{key: row[key] for key in ('image_sha256', 'mask_sha256', 'prediction_sha256', 'metric_result_sha256')},
          'manifest_sha256': manifest['receipt_sha256'],
          'human_annotation_sha256': row['receipt_sha256'],
          'ai_suggestion_sha256': suggestion['receipt_sha256'],
          'first_exposure_sha256': exposure['receipt_sha256'],
          'ai_suggestion_exposed_before_human_decision': True,
          'blind_human_review': False,
          'assisted_human_review': True,
          'timestamp_precision': 'RECORDED_UTC_SECONDS_EQUAL_TIMES_PERMITTED_BY_DURABLE_FIRST_EXPOSURE_ORDER',
          'scope_limit': a.POLICY['scope_limit'],
          'reference_promotable': False,
        }
      )
    )
  return rows, ai, bindings


def concordance(rows, ai):
  """Categorical comparison; never calibrates AI confidence or changes labels."""
  matrix = {label: dict.fromkeys(c.LABELS, 0) for label in c.LABELS}
  by_conf = {label: {'frame_count': 0, 'agreements': 0} for label in a.CONFIDENCE}
  details = []
  for row in rows:
    suggestion = ai[row['frame_id']]
    same = row['reviewer_label'] == suggestion['suggested_label']
    matrix[row['reviewer_label']][suggestion['suggested_label']] += 1
    bucket = by_conf[suggestion['ai_confidence']]
    bucket['frame_count'] += 1
    bucket['agreements'] += same
    details.append(
      {
        'frame_id': row['frame_id'],
        'human_label': row['reviewer_label'],
        'ai_label': suggestion['suggested_label'],
        'ai_confidence': suggestion['ai_confidence'],
        'agreement': same,
        'human_annotation_sha256': row['receipt_sha256'],
        'ai_suggestion_sha256': suggestion['receipt_sha256'],
      }
    )
  for bucket in by_conf.values():
    bucket['agreement_rate'] = bucket['agreements'] / bucket['frame_count'] if bucket['frame_count'] else None
  count = sum(row['agreement'] for row in details)
  return seal(
    {
      'schema': 'ASSISTED_REVIEW_CONCORDANCE_V1',
      'status': 'SUPPORTING_DIAGNOSTIC_ONLY',
      'exact_agreements': count,
      'exact_agreement_rate': count / len(rows),
      'confusion_matrix': matrix,
      'by_ai_confidence': by_conf,
      'frames': details,
      'high_confidence_disagreements': [r for r in details if r['ai_confidence'] == 'HIGH' and not r['agreement']],
      'human_unresolved_frame_ids': [r['frame_id'] for r in details if r['human_label'] == 'UNRESOLVED'],
      'ai_unresolved_frame_ids': [r['frame_id'] for r in details if r['ai_label'] == 'UNRESOLVED'],
      'independent_ai_accuracy_estimate': False,
      'human_replacement_allowed': False,
      'reference_promotable': False,
    }
  )


def metric_trace(manifest, frame, raw, same_point):
  trace = unseal(raw)
  if (
    set(trace) != {'schema', 'run_sha256', 'frame', 'original_row_sha256', 'pool'}
    or trace['schema'] != 'BOUND_REVIEW_METRIC_TRACE_V1'
    or trace['run_sha256'] != manifest['run_sha256']
    or trace['frame'] != frame
    or not is_sha256(trace['original_row_sha256'])
    or type(trace['pool']) is not dict
    or set(trace['pool']) != set(METRICS)
  ):
    raise ValueError('BOUND_ORIGINAL_REVIEW_METRIC_REQUIRED')
  for key, summary in (('pred', frame['pred_to_gt']), ('gt', frame['gt_to_pred']), ('paired_spatial_pred', same_point)):
    if t.distribution(trace['pool'][key]) != summary:
      raise ValueError('ORIGINAL_METRIC_SUMMARY_MISMATCH')
  return trace


def aggregate(manifest, human_export, experiment, suggestions, metric_loader):
  rows, ai, bindings = validate_assisted(manifest, human_export, experiment, suggestions)
  categories = {
    label: {
      'frame_count': 0,
      'reviewable': 0,
      'unreviewable': 0,
      'pools': {k: [] for k in METRICS},
      'available_frames': dict.fromkeys(METRICS.values(), 0),
      'detector_confidence_distribution': Counter(),
      'y_region_distribution': dict.fromkeys(REGIONS, 0),
      'frame_ids': [],
    }
    for label in c.LABELS
  }
  total_pools = {k: [] for k in METRICS}
  traces = []
  for row, frame in zip(rows, manifest['frames'], strict=True):
    raw = metric_loader(frame)
    trace = metric_trace(manifest, frame, raw, ai[row['frame_id']]['metric_context']['same_point_error'])
    traces.append({'frame_id': frame['frame_id'], 'trace_sha256': raw['receipt_sha256'], 'original_row_sha256': trace['original_row_sha256']})
    cat = categories[row['reviewer_label']]
    cat['frame_count'] += 1
    cat['reviewable'] += row['reviewable']
    cat['unreviewable'] += not row['reviewable']
    cat['frame_ids'].append(row['frame_id'])
    for key, values in trace['pool'].items():
      cat['pools'][key].extend(values)
      total_pools[key].extend(values)
      cat['available_frames'][METRICS[key]] += bool(values)
    score = frame['confidence']['median']
    cat['detector_confidence_distribution']['UNAVAILABLE' if score is None else t.confidence_bucket(score)] += 1
    if set(frame['regions']) != set(REGIONS):
      raise ValueError('FROZEN_Y_REGIONS_REQUIRED')
    for name in REGIONS:
      count = frame['regions'][name]['pred_to_gt']['sample_count']
      if type(count) is not int or count < 0:
        raise ValueError('INVALID_Y_REGION_COUNT')
      cat['y_region_distribution'][name] += count
  n = len(rows)
  for cat in categories.values():
    cat['percentage'] = 100 * cat['frame_count'] / n
    cat['metrics'] = {METRICS[key]: t.distribution(pool) for key, pool in cat.pop('pools').items()}
    cat['unavailable_frames'] = {key: cat['frame_count'] - count for key, count in cat['available_frames'].items()}
    cat['detector_confidence_distribution'] = dict(sorted(cat['detector_confidence_distribution'].items()))
    cat['representative_frame_ids'] = sorted(cat['frame_ids'])[:REPRESENTATIVES]
  associations = {
    group: {
      'labels': list(labels),
      'frame_count': sum(categories[k]['frame_count'] for k in labels),
      'percentage': 100 * sum(categories[k]['frame_count'] for k in labels) / n,
      'evidence': 'ASSOCIATION_WITH_PRIMARY_ASSISTED_LABEL_NOT_CAUSAL_MAGNITUDE',
    }
    for group, labels in ASSOCIATIONS.items()
  }
  if sum(x['frame_count'] for x in categories.values()) != n or sum(x['frame_count'] for x in associations.values()) != n:
    raise ValueError('EXACT_CATEGORY_ACCOUNTING_REQUIRED')
  return seal(
    {
      'schema': 'ASSISTED_HUMAN_TAIL_DIAGNOSTIC_V1',
      'status': 'TEST_ONLY_NOT_HUMAN_EVIDENCE' if manifest['scope'] == c.SCOPES[1] else 'ASSISTED_TAIL_DIAGNOSTIC_COMPLETE',
      'reviewed': n,
      'reviewable': sum(r['reviewable'] for r in rows),
      'unreviewable': sum(not r['reviewable'] for r in rows),
      'categories': categories,
      'metrics': {METRICS[k]: t.distribution(pool) for k, pool in total_pools.items()},
      'metric_availability': {
        key: {
          'available_frames': sum(cat['available_frames'][key] for cat in categories.values()),
          'unavailable_frames': sum(cat['unavailable_frames'][key] for cat in categories.values()),
        }
        for key in METRICS.values()
      },
      'associations': associations,
      'concordance': concordance(rows, ai),
      'row_provenance': bindings,
      'y_distribution_semantics': 'PRED_TO_GT_SAMPLE_COUNTS_BY_FROZEN_IMAGE_THIRDS_NOT_METERS',
      'empty_metric_semantics': POLICY['availability'],
      'metric_unit': 'px',
      'metric_trace_receipts': traces,
      'human_export_sha256': human_export['receipt_sha256'],
      'experiment_sha256': experiment['receipt_sha256'],
      'manifest_sha256': manifest['receipt_sha256'],
      'manifest_scope': manifest['scope'],
      'policy_sha256': POLICY_SHA,
      'tool_sha256': identity(),
      'scope': POLICY['scope'],
      'blind_independent_complete': False,
      'detector_verdict': 'DETECTOR_QUALIFICATION_BLOCKED',
      'diagnostic_use': 'PUBLIC_DIAGNOSTIC_RETAINED',
      'full_result_changed': False,
      'causal_metric_difference_computed': False,
      'ego_lane_identity': False,
      'meter_conversion': False,
      'qualification': 'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE',
      'private_input_allowed': False,
      'reference_promotable': False,
    }
  )


def validate_public_metric_binding(core):
  """Authenticates original pooled values, not only their shape or count."""
  summary = {k: core[k] for k in ('manifest_sha256', 'human_export_sha256', 'metric_unit', 'metrics', 'metric_availability', 'metric_trace_receipts')}
  summary['category_metrics'] = {label: {k: cat[k] for k in ('metrics', 'available_frames', 'unavailable_frames')} for label, cat in core['categories'].items()}
  if digest(canonical(summary)) != PUBLIC_METRIC_SUMMARY_SHA:
    raise ValueError('FROZEN_ORIGINAL_METRIC_SUMMARY_MISMATCH')


def validate_public_binding(core):
  """This V1 binds the exact historical public inputs, not a caller's scope assertion."""
  docs = Path(__file__).resolve().parents[3] / 'docs/cyberpilot/changes'
  manifest = s.read_json(docs / 'comma10k-completed-full-human-review-manifest.json')
  human = s.read_json(docs / 'comma10k-assisted-human-review-v1.json')
  ai = s.read_json(docs / 'comma10k-ai-prereview-results-v1.json')
  unseal(ai)
  if (
    human['receipt_sha256'] != '311a5940a8bccd2c2c6be9acafea8bb189c57b3460bc01670d8a7e7b07735453'
    or ai['receipt_sha256'] != '2ad2ca1d3b88c208831b467215bca1329c8963065db37d5423bcc835720e314c'
    or core['human_export_sha256'] != human['receipt_sha256']
    or core['experiment_sha256'] != ai['experiment']['receipt_sha256']
  ):
    raise ValueError('EXACT_HISTORICAL_PUBLIC_INPUTS_REQUIRED')
  rows, suggestions, bindings = validate_assisted(manifest, human, ai['experiment'], ai['suggestions'])
  if core['row_provenance'] != bindings or core['concordance'] != concordance(rows, suggestions):
    raise ValueError('PUBLIC_ROW_INPUT_BINDING_MISMATCH')
  for label, cat in core['categories'].items():
    members = [row for row in rows if row['reviewer_label'] == label]
    frames = [f for f in manifest['frames'] if f['frame_id'] in {row['frame_id'] for row in members}]
    scores = Counter('UNAVAILABLE' if f['confidence']['median'] is None else t.confidence_bucket(f['confidence']['median']) for f in frames)
    if (
      cat['frame_ids'] != [row['frame_id'] for row in members]
      or cat['reviewable'] != sum(row['reviewable'] for row in members)
      or cat['detector_confidence_distribution'] != dict(sorted(scores.items()))
      or cat['y_region_distribution'] != {key: sum(f['regions'][key]['pred_to_gt']['sample_count'] for f in frames) for key in REGIONS}
    ):
      raise ValueError('PUBLIC_CATEGORY_INPUT_BINDING_MISMATCH')


def validate_result(value):
  """Admit complete diagnostic shape/accounting, never a subset of promotion flags."""
  core = unseal(value)
  constants = {
    'schema': 'ASSISTED_HUMAN_TAIL_DIAGNOSTIC_V1',
    'reviewed': 29,
    'policy_sha256': POLICY_SHA,
    'tool_sha256': identity(),
    'scope': POLICY['scope'],
    'y_distribution_semantics': 'PRED_TO_GT_SAMPLE_COUNTS_BY_FROZEN_IMAGE_THIRDS_NOT_METERS',
    'empty_metric_semantics': POLICY['availability'],
    'metric_unit': 'px',
    'blind_independent_complete': False,
    'detector_verdict': 'DETECTOR_QUALIFICATION_BLOCKED',
    'diagnostic_use': 'PUBLIC_DIAGNOSTIC_RETAINED',
    'full_result_changed': False,
    'causal_metric_difference_computed': False,
    'ego_lane_identity': False,
    'meter_conversion': False,
    'qualification': 'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE',
    'private_input_allowed': False,
    'reference_promotable': False,
  }
  variable_fields = {
    'status',
    'manifest_scope',
    'reviewable',
    'unreviewable',
    'categories',
    'metrics',
    'metric_availability',
    'associations',
    'concordance',
    'row_provenance',
    'metric_trace_receipts',
    'human_export_sha256',
    'experiment_sha256',
    'manifest_sha256',
  }
  if set(core) != set(constants) | variable_fields or any(type(core[k]) is not type(v) or core[k] != v for k, v in constants.items()):
    raise ValueError('EXACT_ASSISTED_DIAGNOSTIC_REQUIRED')
  if core['manifest_scope'] not in c.SCOPES or core['status'] != (
    'TEST_ONLY_NOT_HUMAN_EVIDENCE' if core['manifest_scope'] == c.SCOPES[1] else 'ASSISTED_TAIL_DIAGNOSTIC_COMPLETE'
  ):
    raise ValueError('DIAGNOSTIC_SCOPE_STATUS_MISMATCH')
  if core['manifest_scope'] == c.SCOPES[0] and core['manifest_sha256'] != w.MANIFEST_SHA:
    raise ValueError('EXACT_FROZEN_PUBLIC_29_MANIFEST_REQUIRED')
  if any(not is_sha256(core[k]) for k in ('human_export_sha256', 'experiment_sha256', 'manifest_sha256')):
    raise ValueError('DIAGNOSTIC_INPUT_IDENTITIES_REQUIRED')

  def count(v):
    if type(v) is not int or v < 0:
      raise ValueError('NONNEGATIVE_DIAGNOSTIC_COUNT_REQUIRED')
    return v

  def distribution(v):
    fields = ('median', 'p90', 'p95', 'p99', 'maximum')
    if type(v) is not dict or set(v) != {'sample_count', *fields}:
      raise ValueError('EXACT_DISTRIBUTION_REQUIRED')
    n = count(v['sample_count'])
    if n == 0:
      if any(v[k] is not None for k in fields):
        raise ValueError('EMPTY_DISTRIBUTION_MUST_BE_UNAVAILABLE')
    else:
      values = [v[k] for k in fields]
      if any(type(x) not in (int, float) or not math.isfinite(x) or x < 0 for x in values) or values != sorted(values):
        raise ValueError('FINITE_ORDERED_PIXEL_DISTRIBUTION_REQUIRED')
    return n

  concord = unseal(core['concordance'])
  if type(concord.get('frames')) is not list or len(concord['frames']) != 29:
    raise ValueError('EXACT_CONCORDANCE_FRAMES_REQUIRED')
  rows, ai = [], {}
  for pair in concord['frames']:
    if (
      set(pair) != {'frame_id', 'human_label', 'ai_label', 'ai_confidence', 'agreement', 'human_annotation_sha256', 'ai_suggestion_sha256'}
      or pair['human_label'] not in c.LABELS
      or pair['ai_label'] not in c.LABELS
      or pair['ai_confidence'] not in a.CONFIDENCE
      or type(pair['agreement']) is not bool
      or not is_sha256(pair['human_annotation_sha256'])
      or not is_sha256(pair['ai_suggestion_sha256'])
      or type(pair['frame_id']) is not str
      or pair['frame_id'] in ai
    ):
      raise ValueError('EXACT_CONCORDANCE_FRAME_REQUIRED')
    rows.append({'frame_id': pair['frame_id'], 'reviewer_label': pair['human_label'], 'receipt_sha256': pair['human_annotation_sha256']})
    ai[pair['frame_id']] = {
      'suggested_label': pair['ai_label'],
      'ai_confidence': pair['ai_confidence'],
      'receipt_sha256': pair['ai_suggestion_sha256'],
    }
  if core['concordance'] != concordance(rows, ai):
    raise ValueError('CONCORDANCE_ACCOUNTING_MISMATCH')
  frame_ids = [r['frame_id'] for r in rows]
  if type(core['categories']) is not dict or set(core['categories']) != set(c.LABELS):
    raise ValueError('EXACT_FROZEN_CATEGORY_SET_REQUIRED')
  for label, cat in core['categories'].items():
    if set(cat) != {
      'frame_count',
      'reviewable',
      'unreviewable',
      'available_frames',
      'unavailable_frames',
      'detector_confidence_distribution',
      'y_region_distribution',
      'frame_ids',
      'percentage',
      'metrics',
      'representative_frame_ids',
    }:
      raise ValueError('EXACT_CATEGORY_SHAPE_REQUIRED')
    n = count(cat['frame_count'])
    ids = [r['frame_id'] for r in rows if r['reviewer_label'] == label]
    if cat['frame_ids'] != ids or n != len(ids) or cat['percentage'] != 100 * n / 29 or cat['representative_frame_ids'] != sorted(ids)[:REPRESENTATIVES]:
      raise ValueError('CATEGORY_FRAME_ACCOUNTING_MISMATCH')
    if count(cat['reviewable']) + count(cat['unreviewable']) != n:
      raise ValueError('CATEGORY_REVIEWABILITY_MISMATCH')
    for field in ('metrics', 'available_frames', 'unavailable_frames'):
      if type(cat[field]) is not dict or set(cat[field]) != set(METRICS.values()):
        raise ValueError('EXACT_CATEGORY_METRICS_REQUIRED')
    for key in METRICS.values():
      samples = distribution(cat['metrics'][key])
      available = count(cat['available_frames'][key])
      if available + count(cat['unavailable_frames'][key]) != n or samples < available or (samples == 0) != (available == 0):
        raise ValueError('METRIC_AVAILABILITY_MISMATCH')
    confidence = cat['detector_confidence_distribution']
    allowed = {'UNAVAILABLE'} | {t.confidence_bucket(i / 5) for i in range(5)}
    if type(confidence) is not dict or set(confidence) - allowed or sum(count(v) for v in confidence.values()) != n:
      raise ValueError('DETECTOR_CONFIDENCE_ACCOUNTING_MISMATCH')
    regions = cat['y_region_distribution']
    if type(regions) is not dict or set(regions) != set(REGIONS):
      raise ValueError('EXACT_Y_REGIONS_REQUIRED')
    # Frozen row regions include all predicted points; pred->GT may exclude GT-empty rows.
    if sum(count(v) for v in regions.values()) < cat['metrics']['pred_to_gt']['sample_count']:
      raise ValueError('Y_REGION_SAMPLE_ACCOUNTING_MISMATCH')
  if any(count(core[field]) != sum(cat[field] for cat in core['categories'].values()) for field in ('reviewable', 'unreviewable')):
    raise ValueError('REVIEWABILITY_TOTAL_MISMATCH')
  if type(core['metrics']) is not dict or set(core['metrics']) != set(METRICS.values()) or set(core['metric_availability']) != set(METRICS.values()):
    raise ValueError('EXACT_GLOBAL_METRICS_REQUIRED')
  for key in METRICS.values():
    if distribution(core['metrics'][key]) != sum(cat['metrics'][key]['sample_count'] for cat in core['categories'].values()):
      raise ValueError('GLOBAL_SAMPLE_COUNT_MISMATCH')
    expected = {
      'available_frames': sum(cat['available_frames'][key] for cat in core['categories'].values()),
      'unavailable_frames': sum(cat['unavailable_frames'][key] for cat in core['categories'].values()),
    }
    if core['metric_availability'][key] != expected:
      raise ValueError('GLOBAL_AVAILABILITY_MISMATCH')
  expected_associations = {
    group: {
      'labels': list(labels),
      'frame_count': sum(core['categories'][k]['frame_count'] for k in labels),
      'percentage': 100 * sum(core['categories'][k]['frame_count'] for k in labels) / 29,
      'evidence': 'ASSOCIATION_WITH_PRIMARY_ASSISTED_LABEL_NOT_CAUSAL_MAGNITUDE',
    }
    for group, labels in ASSOCIATIONS.items()
  }
  if core['associations'] != expected_associations:
    raise ValueError('ASSOCIATION_ACCOUNTING_MISMATCH')
  if type(core['row_provenance']) is not list or len(core['row_provenance']) != 29:
    raise ValueError('EXACT_ROW_RELATIONS_REQUIRED')
  for pair, raw in zip(concord['frames'], core['row_provenance'], strict=True):
    relation = unseal(raw)
    expected = {
      'schema': 'ASSISTED_HUMAN_ROW_RELATION_V1',
      'frame_id': pair['frame_id'],
      'manifest_sha256': core['manifest_sha256'],
      'human_annotation_sha256': pair['human_annotation_sha256'],
      'ai_suggestion_sha256': pair['ai_suggestion_sha256'],
      'ai_suggestion_exposed_before_human_decision': True,
      'blind_human_review': False,
      'assisted_human_review': True,
      'timestamp_precision': 'RECORDED_UTC_SECONDS_EQUAL_TIMES_PERMITTED_BY_DURABLE_FIRST_EXPOSURE_ORDER',
      'scope_limit': a.POLICY['scope_limit'],
      'reference_promotable': False,
    }
    hashes = {'image_sha256', 'mask_sha256', 'prediction_sha256', 'metric_result_sha256', 'first_exposure_sha256'}
    if (
      set(relation) != set(expected) | hashes
      or any(type(relation[k]) is not type(v) or relation[k] != v for k, v in expected.items())
      or any(not is_sha256(relation[k]) for k in hashes)
    ):
      raise ValueError('ASSISTED_ROW_RELATION_MISMATCH')
  traces = core['metric_trace_receipts']
  if type(traces) is not list or len(traces) != 29:
    raise ValueError('EXACT_METRIC_TRACE_RECEIPTS_REQUIRED')
  for key, trace in zip(frame_ids, traces, strict=True):
    if (
      set(trace) != {'frame_id', 'trace_sha256', 'original_row_sha256'}
      or trace['frame_id'] != key
      or any(not is_sha256(trace[k]) for k in ('trace_sha256', 'original_row_sha256'))
    ):
      raise ValueError('METRIC_TRACE_RECEIPT_MISMATCH')
  if core['manifest_scope'] == c.SCOPES[0]:
    validate_public_binding(core)
    validate_public_metric_binding(core)
  return core


def inter_rater(manifest, human_export, experiment, suggestions, blind_export):
  """Future categorical agreement only. Absent/incomplete second review creates no statistic."""
  from openpilot.tools.cyber_autotune import lane_tail_second_review as b

  assisted, _, _ = validate_assisted(manifest, human_export, experiment, suggestions)
  result = {
    'schema': 'ASSISTED_VS_BLIND_INTER_RATER_V1',
    'assisted_export_sha256': human_export['receipt_sha256'],
    'manifest_sha256': manifest['receipt_sha256'],
    'status': 'INDEPENDENT_BLIND_REVIEWER_UNAVAILABLE',
    'statistics': None,
    'blind_export_sha256': None,
    'private_input_allowed': False,
    'reference_promotable': False,
  }
  if blind_export is None:
    return seal(result)
  blind = b.validate_export(manifest, blind_export)
  result['blind_export_sha256'] = blind_export['receipt_sha256']
  if len(blind) != len(assisted):
    result['status'] = 'INDEPENDENT_BLIND_REVIEW_PENDING'
    return seal(result)
  matrix = {label: dict.fromkeys(c.LABELS, 0) for label in c.LABELS}
  disagreements = []
  for left, right in zip(assisted, blind, strict=True):
    if left['frame_id'] != right['frame_id']:
      raise ValueError('INTER_RATER_FRAME_ALIGNMENT_REQUIRED')
    matrix[left['reviewer_label']][right['reviewer_label']] += 1
    if left['reviewer_label'] != right['reviewer_label']:
      disagreements.append(left['frame_id'])
  n = len(assisted)
  agreements = n - len(disagreements)
  # Unweighted nominal Cohen kappa: (observed - chance)/(1 - chance).
  # https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html
  expected_numerator = sum(sum(matrix[k].values()) * sum(row[k] for row in matrix.values()) for k in c.LABELS)
  denominator = n * n - expected_numerator
  result.update(
    {
      'status': 'TEST_ONLY_NOT_HUMAN_EVIDENCE' if manifest['scope'] == c.SCOPES[1] else 'INTER_RATER_DIAGNOSTIC_COMPLETE',
      'statistics': {
        'frame_count': n,
        'exact_agreements': agreements,
        'exact_agreement_rate': agreements / n,
        'confusion_matrix': matrix,
        'disagreement_frame_ids': disagreements,
        'cohens_kappa': (agreements * n - expected_numerator) / denominator if denominator else None,
        'kappa_status': 'DEFINED' if denominator else 'UNDEFINED_EXPECTED_AGREEMENT_ONE',
        'semantics': 'CATEGORICAL_RATER_CONCORDANCE_NOT_TRUTH_OR_QUALIFICATION',
      },
    }
  )
  return seal(result)
