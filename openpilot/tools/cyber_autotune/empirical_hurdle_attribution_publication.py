"""Aggregate-only publication of immutable attribution receipts."""

from pathlib import Path
import re

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_attribution as analysis
from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io
from openpilot.tools.cyber_autotune.empirical_hurdle_attribution_math import require
from openpilot.tools.cyber_autotune.empirical_hurdle_attribution_schema import PUBLIC_KEYS

FORBIDDEN = {
  'value',
  'threshold',
  'coefficients',
  'nominal_coefficients',
  'mean',
  'std',
  'p_move',
  'predicted_gate',
  'train_probability',
  'observed_path',
  'projected_path',
  'hold_last_path',
  'predicted_gate_path',
  'current_tick',
  'target_next_tick',
  'actual_delta_tick',
  'integrated_delta',
  'stage2_oracle_move_prediction',
  'command_current',
  'command_history',
  'timestamp',
  'timestamps',
  'gps',
  'private_path',
  'private_build_metadata',
}


VALIDATION_KEYS = frozenset(
  (
    'focused',
    'empirical',
    'full_autotune_controls',
    'lateral_replay',
    'ruff',
    'compileall',
    'json',
    'publication_privacy_authority',
    'git_diff_check',
    'scons',
    'repeatability',
    'trapped_resume',
    'independent_review',
    'status',
    'command',
    'exit_code',
    'count',
    'subtests',
    'log_sha256',
    'findings_fixed',
    'findings_open',
    'result_volume',
    'output_bytes',
    'source_write_count',
    'copied_source_arrays',
    'execution_only_source',
    'initial_run_invalidated',
    'reason',
    'scope',
    'head_before_increment',
  )
)


def validate_public(value, key=None):
  require(type(value) in (dict, list, str, int, float, bool, type(None)), 'HURDLE_ATTRIBUTION_PUBLICATION_NON_JSON_TYPE')
  if isinstance(value, dict):
    require(
      not (FORBIDDEN | set(analysis.ONE_FIELDS) | set(analysis.PATH_FIELDS) | set(analysis.CONTEXT)).intersection(value),
      'HURDLE_ATTRIBUTION_PUBLICATION_PRIVATE_FIELD',
    )
    require(set(value) <= PUBLIC_KEYS | VALIDATION_KEYS, 'HURDLE_ATTRIBUTION_PUBLICATION_SCHEMA_CONFLICT')
    for k, v in value.items():
      validate_public(v, k)
  elif isinstance(value, list):
    if any(isinstance(v, (int, float)) for v in value):
      require(key in ('horizons', 'classes_count') and all(type(v) is int and v >= 0 for v in value), 'HURDLE_ATTRIBUTION_PUBLICATION_ROW_VALUES')
      if key == 'horizons':
        require(value == [25, 50, 100, 200])
    for v in value:
      validate_public(v, key)
  elif isinstance(value, str):
    require(not re.search(r'(?i)(/mnt/[a-z]/|/home/|[CD]:[/\\]|\\\\[a-z])', value), 'HURDLE_ATTRIBUTION_PUBLICATION_PRIVATE_PATH')
  p.canonical(value)


def bundle(root, validation):
  manifest = io.resume(root / 'repeat-1')
  repeated = io.read_json(root / 'repeatability.json')
  require(
    repeated['manifest_sha256'] == manifest['receipt_sha256']
    and repeated['status'] == 'PASS'
    and repeated['trapped_resume_exact']
    and repeated['all_file_hashes_exact']
  )
  jobs = [io.read_json(root / f'repeat-1/jobs/{c}/{f}/receipt.json') for c, f in io.JOBS]
  summary = io.read_json(root / 'repeat-1/summary.json')
  ready = io.read_json(root / 'repeat-1/readiness.json')
  historical = io.public_inputs()['fit-cv-readiness']
  common = {
    'source_manifest_sha256': io.SOURCE_SHA,
    'attribution_manifest_sha256': manifest['receipt_sha256'],
    'policy_sha256': analysis.policy()['receipt_sha256'],
    'historical_verdict': 'HURDLE_NO_ADMISSIBLE_CANDIDATE',
    'historical_selection': 'MODEL_SELECTION_FAILED_CLOSED',
    'holdout': 'CLOSED',
    'opening_count': 0,
    'vehicle_authority': 'NONE',
  }

  def identity(j):
    return {k: j[k] for k in ('candidate_id', 'fold', 'original_job_receipt_sha256', 'receipt_sha256')}

  out = {'failure-attribution-policy': analysis.policy()}

  def emit(label, fields):
    out[label] = p.seal({'schema': 'EMPIRICAL_HURDLE_' + label.upper().replace('-', '_') + '_V1', **common, **fields})

  emit('exact-hit-attribution', {'jobs': [{**identity(j), **j['one_step']['exact_hit'], 'static_fraction': j['one_step']['static_fraction']} for j in jobs]})
  emit('stage1-transfer', {'jobs': [{**identity(j), **j['one_step']['transfer']} for j in jobs]})
  emit('stage1-confusion-attribution', {'jobs': [{**identity(j), **{k: j['one_step'][k] for k in ('confusion', 'fp', 'fn')}} for j in jobs]})
  emit('stage2-oracle-attribution', {'role': 'DIAGNOSTIC_ONLY', 'jobs': [{**identity(j), **j['one_step']['oracle']} for j in jobs]})
  emit(
    'one-step-error-decomposition',
    {'p95_is_additive': False, 'jobs': [{**identity(j), 'classes': j['one_step']['classes'], 'accounting': j['one_step']['accounting']} for j in jobs]},
  )
  emit(
    'rollout-gate-attribution',
    {
      'jobs': [
        {
          **identity(j),
          'horizons': {
            h: {k: v for k, v in result.items() if k not in ('first_gate_mismatch', 'first_projected_divergence', 'first_event_relation')}
            for h, result in j['rollout'].items()
          },
        }
        for j in jobs
      ]
    },
  )
  emit(
    'rollout-divergence',
    {
      'jobs': [
        {
          **identity(j),
          'horizons': {
            h: {k: result[k] for k in ('first_gate_mismatch', 'first_projected_divergence', 'first_event_relation')} for h, result in j['rollout'].items()
          },
        }
        for j in jobs
      ]
    },
  )
  paired = []
  for candidate in io.CANDIDATES:
    folds = {}
    for j in jobs:
      if j['candidate_id'] == candidate:
        folds[j['fold']] = {
          'confusion': j['one_step']['confusion'],
          'exact_hit': j['one_step']['exact_hit'],
          'integrated': j['one_step']['classes']['ALL'],
          'transfer': j['one_step']['transfer'],
          'historical_rollout_failures': [f for f in j['historical_gate']['failures'] if f.startswith(('OVERALL_', 'PATH_MOVED_'))],
        }
    paired.append({'candidate_id': candidate, 'folds': folds})
  emit('fold-asymmetry', {'fold_summaries': summary['folds'], 'paired_route_transfer_directions': paired, 'ranking_performed': False})
  emit(
    'mechanism-summary',
    {
      'one_step': summary['one_step'],
      'rollout': summary['rollout'],
      'folds': summary['folds'],
      'historical_failure_counts': summary['historical_failure_counts'],
      'causal_claim': False,
      'ranking_performed': False,
    },
  )
  emit('next-design-trigger', summary['one_step'])
  emit(
    'failure-attribution-repeatability',
    {
      'private_repeatability_receipt_sha256': repeated['receipt_sha256'],
      **{k: repeated[k] for k in ('status', 'independent_runs', 'all_file_hashes_exact', 'receipts_exact', 'trapped_resume_exact')},
    },
  )
  preserved = {
    k: historical[k]
    for k in (
      'S1',
      'S2',
      'S3',
      'calibration_blockers',
      'closed_loop_bias',
      'composition',
      'dataset',
      'family_verdict',
      'final_pooled_refit',
      'future_holdout',
      'historical_attribution',
      'historical_track',
      'no_model_admitted',
      'sealed_reference',
      'search',
      'sg',
      'stage_b',
      'ta',
      'vehicle',
    )
  }
  emit(
    'failure-attribution-readiness',
    {
      **preserved,
      'historical_s2_ri_verdict': 'S2_RI_NO_ADMISSIBLE_CANDIDATE',
      'historical_design_trigger': 'HURDLE_FAMILY_DESIGN_REVIEW_SUPPORTED',
      **{
        k: ready[k]
        for k in (
          'status',
          'states',
          'job_count',
          'one_step_populations',
          'rollout_populations',
          'execution_calls',
          'source_manifest_listed_bytes_unchanged',
          'source_write_count',
          'source_fallback',
        )
      },
      'mechanism_states': summary['one_step'],
      'holdout_state': 'HOLDOUT_OPENING_CLOSED',
    },
  )
  emit('failure-attribution-validation', validation)
  for value in out.values():
    p.verify(value)
    validate_public(value)
  return out


def publish(root, validation):
  out = bundle(Path(root), validation)
  for name, value in out.items():
    io.write_json(p.PUBLIC / f'empirical-hurdle-{name}-v1.json', value)
  return out
