"""Additive metadata/receipt-only salvage authority, never an opening permit."""

from openpilot.tools.cyber_autotune import empirical_plant_policy as p

BASELINE = 'e4e53408d4bb2bf6f215332f0dc6c03ac69a929c'
MAX_ADDITIONAL = 10
USE_FIELDS = (
  'project',
  'generation',
  'role',
  'metadata_opened',
  'numeric_opened',
  'fitting_used',
  'selection_used',
  'evaluation_used',
  'holdout_used',
  'receipt_sha256',
  'source_identity_sha256',
)


def policy():
  return p.seal(
    {
      'schema': 'EMPIRICAL_ROUTE_PRIOR_USE_POLICY_V1',
      'baseline': BASELINE,
      'maximum_additional_generations': MAX_ADDITIONAL,
      'source_ranking': ['metadata_complete_route_count_DESC', 'segment_count_DESC', 'source_commit_ASC', 'generation_id_ASC'],
      'already_audited_sources_excluded': True,
      'metadata_complete_status': 'ROUTE_DIFFERENT_SOURCE_GENERATION',
      'reservation_ranking': [
        'metadata_complete',
        'required_signals_available',
        'segment_count_DESC',
        'exact_source_compatibility_first',
        'opaque_route_id_ASC',
      ],
      'untouched_scope': 'CYBERPILOT_PIPELINE_UNTOUCHED',
      'global_never_analyzed_claim': False,
      'public_absence_sufficient': False,
      'complete_private_store_closure_required': True,
      'unmapped_receipt_blocks_untouched': True,
      'unknown_is_not_false': True,
      'numeric_opening_allowed': False,
      'holdout_opening_allowed': False,
      'numeric_coverage': None,
      'fitting': 'NOT_RUN',
      'model_selection': 'NOT_RUN',
      'store_reading': 'EXPLICIT_REGISTRY_METADATA_AND_ALLOWLISTED_RECEIPTS_ONLY',
      'raw_events': 'NO_READER_NO_DECODE',
      'images_video_gps': 'NOT_OPENED',
      'symlinks': 'REJECT',
      'outside_store': 'REJECT',
      'archives': 'NOT_OPENED',
      'historical_artifacts': 'IMMUTABLE',
      'calibration_blockers': p.BLOCKERS,
    }
  )


def select_sources(buckets, audited):
  choices = []
  for b in buckets:
    commit = b['generation']['source_commit']
    if commit in audited:
      continue
    choices.append(
      {
        'generation_id': b['generation_id'],
        'source_commit': commit,
        'metadata_complete_routes': b['status_counts'].get('ROUTE_DIFFERENT_SOURCE_GENERATION', 0),
        'segment_count': b['segment_count'],
      }
    )
  choices.sort(key=lambda x: (-x['metadata_complete_routes'], -x['segment_count'], x['source_commit'], x['generation_id']))
  # One generation per commit; no audit-result-based reranking or replacement.
  seen, result = set(), []
  for x in choices:
    if x['source_commit'] not in seen:
      seen.add(x['source_commit'])
      result.append(x)
  return result[:MAX_ADDITIONAL]


def prior_state(records, closure_complete, identity_complete):
  if any(x.get('holdout_used') is True for x in records):
    return 'USED_HOLDOUT'
  if any(x.get('evaluation_used') is True for x in records):
    return 'USED_NUMERIC_EVALUATION'
  if any(x.get('selection_used') is True or (x.get('numeric_opened') is True and x.get('role') == 'DEVELOPMENT') for x in records):
    return 'USED_NUMERIC_DEVELOPMENT'
  if any(x.get('fitting_used') is True or (x.get('numeric_opened') is True and x.get('role') == 'TRAIN') for x in records):
    return 'USED_NUMERIC_TRAIN'
  if any(x.get('numeric_opened') is True for x in records):
    return 'USED_NUMERIC_EVALUATION'
  if not identity_complete:
    return 'SOURCE_IDENTITY_AMBIGUOUS'
  if not records:
    return 'PRIOR_USE_UNKNOWN'
  if closure_complete is not True:
    return 'PRIOR_USE_UNKNOWN'
  if any(
    any(type(x.get(k)) is not bool for k in ('numeric_opened', 'fitting_used', 'selection_used', 'evaluation_used', 'holdout_used')) for x in records
  ):
    return 'PRIOR_USE_UNKNOWN'
  return 'PIPELINE_UNTOUCHED_PROVABLE'


def engineering_contract():
  return p.seal(
    {
      'schema': 'PIPELINE_UNTOUCHED_ENGINEERING_HOLDOUT_CONTRACT_V1',
      'tier': 'PIPELINE_UNTOUCHED_ENGINEERING_HOLDOUT',
      'scope': 'CYBERPILOT_PIPELINE_UNTOUCHED_NOT_GLOBALLY_NEVER_ANALYZED',
      'engineering_evaluation_allowed': 'FUTURE_CONDITIONAL_SEPARATE_AUTHORIZATION',
      'independent_qualification_allowed': False,
      'opening_state': 'CLOSED',
      'opening_count': 0,
      'opening_executor_implemented': False,
      'required_prior_state': 'PIPELINE_UNTOUCHED_PROVABLE',
      'role_frozen_before_numeric': True,
      'one_time_opening_receipt_required': True,
      'model_config_metrics_support_frozen_before_opening': True,
      'reselection_refit_threshold_change_after_opening': False,
    }
  )
