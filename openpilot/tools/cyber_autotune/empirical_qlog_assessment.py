"""Final additive completeness assessment from public aggregates, never private row data.

The execution receipt's full-route field-presence gate is preserved. This assessment
separates exact historical accounting from per-qlog joint causal observability.
"""
from pathlib import Path
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_causal_dataset_policy as base
from openpilot.tools.cyber_autotune import empirical_causal_dataset_alignment as alignment
from openpilot.tools.cyber_autotune import empirical_qlog_publication as publication

NAME = 'empirical-qlog-final-assessment-v1.json'


def causal_completeness(segments):
  if len(segments) != 2:
    raise ValueError('EXACT_TWO_QLOG_COMPLETENESS_SCOPES_REQUIRED')
  missing = sorted({k for s in segments for k in alignment.REQUIRED
                    if s['coverage']['required_field_coverage'].get(k, 0) <= 0})
  valid = sum(s['coverage']['causal_required_valid'] for s in segments)
  runs = sum(s['coverage']['causal_runs'] for s in segments)
  complete = not missing and all(s['coverage']['causal_required_valid'] > 0 and s['coverage']['causal_runs'] > 0 for s in segments)
  return {'status': 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_READY' if complete else 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_PARTIAL',
          'missing_required_fields': missing, 'added_causal_valid_rows': valid, 'added_causal_runs': runs,
          'qlog_context': 'QLOG_CAUSAL_CONTEXT_AVAILABLE' if complete else 'QLOG_CAUSAL_CONTEXT_UNAVAILABLE_AT_FROZEN_TIMEBASE'}


def assess(rows):
  publication.validate_chain(rows)
  coverage = rows[publication.FILES[5]]
  legacy = rows[publication.FILES[6]]
  merge = rows[publication.FILES[7]]
  initial = rows[publication.FILES[-1]]
  result = causal_completeness(coverage['segments'])
  if legacy['status'] != 'LEGACY_ALIGNMENT_REPRODUCED':
    result['status'] = 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_BLOCKED'
  return publication.validate_public(p.seal({'schema': 'EMPIRICAL_QLOG_FINAL_ASSESSMENT_V1',
    'generation': 'QLOG_HISTORICAL_RECONCILIATION_V1', **result,
    'inputs': {n: r['receipt_sha256'] for n, r in rows.items()},
    'executor_sha256': p.sha(Path(__file__).read_bytes()),
    'assessment_scope': 'POST_EXTRACTION_PER_QLOG_COMPLETENESS_AUDIT_NOT_A_MODEL_POLICY_OR_THRESHOLD_CHANGE',
    'reconciliation': 'QLOG_HISTORICAL_RECONCILIATION_COMPLETE',
    'historical_accounting': legacy['status'], 'initial_aggregate_gate_sha256': initial['receipt_sha256'],
    'initial_gate_scope': 'FULL_ROUTE_REQUIRED_FIELD_PRESENCE_AND_EXACT_LEGACY_ACCOUNTING_NOT_PER_SEGMENT_COMPLETENESS',
    'authoritative_final_dataset_completeness': result['status'],
    'rlog_reference_count': merge['rlog_reference_count'], 'qlog_count': 2,
    'total_aligned_rows': initial['total_aligned_rows'],
    'added_legacy_grid_samples': sum(s['coverage']['total_grid_samples'] for s in coverage['segments']),
    'added_eligible_command_pairs': sum(s['bridge']['eligible'] for s in coverage['segments']),
    'added_steering_rate_aligned_coverage': sum(s['coverage']['required_field_coverage']['state.rate'] for s in coverage['segments']),
    'source_steering_rate_finite_events': sum(s['coverage']['source_rate_finite_count'] for s in coverage['segments']),
    'aligned_coverage_is_not_independent_source_sample_count': True,
    'rlog_causal_support': 'UNCHANGED_IMMUTABLE_RICH_SUBSET',
    'qlog_training_admission': 'NO_CONTIGUOUS_CAUSAL_MODEL_SUPPORT_AT_CURRENT_TIMEBASE',
    'gap_filling': False, 'age_limit_changed': False, 'model_fitting': 'MODEL_FITTING_NOT_RUN',
    'model_selection': 'NOT_RUN', 'stage_b': initial['stage_b'], 'holdout': initial['holdout'],
    'opening_count': 0, 'reservation': 'NONE', 'future_holdout': initial['future_holdout'],
    'historical_track': initial['historical_track'], 'no_model': initial['no_model'],
    'calibration_blockers': p.BLOCKERS, 'production_authority': False, 'qualification_allowed': False,
    'vehicle_activation_allowed': False, 'reference_promotable': False,
    'execution_receipts_modified': False, 'historical_artifacts_modified': False}))


def main():
  rows = {n: base.read(p.PUBLIC/n) for n in publication.FILES}
  first, second = assess(rows), assess(rows)
  if first != second:
    raise ValueError('QLOG_ASSESSMENT_REPEATABILITY_CONFLICT')
  p.persist(p.PUBLIC/NAME, first)
  print(first['status'])


if __name__ == '__main__':
  main()
