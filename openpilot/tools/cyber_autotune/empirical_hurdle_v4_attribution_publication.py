"""Explicit aggregate-only projection of repeatability-confirmed V4 attribution."""

import argparse
from contextlib import ExitStack
import json
from pathlib import Path
from unittest.mock import patch
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_attribution as a

p, saved = a.p, a.saved
LABELS = (
  'attribution-policy',
  'exact-hit-decomposition',
  'stage1-confusion-attribution',
  'state-conditional-ranking',
  'score-transfer',
  'fold-asymmetry',
  'rollout-gate-attribution',
  'rollout-context-drift',
  'rollout-step-error',
  'gate-perfect-rollout',
  'projected-movement-perfect-rollout',
  'rollout-streaks',
  'mechanism-summary',
  'next-design-trigger',
  'attribution-repeatability',
  'attribution-resume',
  'attribution-readiness',
  'attribution-validation',
)


def _build(output, validation):
  lock = a.validate_lock(output)
  a.require(lock['analysis_sources'] == a.sources())
  current_public = a.public_lock()[1]
  a.require(current_public == lock['public_receipts'])
  one = saved.read_json(output / 'repeat-1/manifest.json')
  a.resume(output / 'repeat-1', one['receipt_sha256'])
  repeated = saved.read_json(output / 'repeatability.json')
  resumed = saved.read_json(output / 'resume.json')
  a.require(repeated['status'] == 'BYTE_EXACT_PASS' and repeated['manifest_sha256'] == one['receipt_sha256'])
  a.require(repeated['input_identity_sha256'] == lock['receipt_sha256'])
  a.require(resumed['status'] == 'PASS' and resumed['recompute_calls'] == 0)
  a.require(all(r['status'] == 'PASS' and r['recompute_calls'] == 0 and r['manifest_sha256'] == one['receipt_sha256'] for r in resumed['replicas'].values()))
  jobs = [saved.read_json(output / f'repeat-1/jobs/{c}/{f}/receipt.json') for c, f in saved.JOBS]
  summary = saved.read_json(output / 'repeat-1/summary.json', one['summary_sha256'])

  def rows(function):
    return [{'candidate_id': j['candidate_id'], 'fold': j['fold'], **function(j)} for j in jobs]

  def paths(keys):
    return rows(lambda j: {'rollout': {h: {k: r[k] for k in keys} for h, r in j['rollout'].items()}})

  def subsets(names):
    return rows(lambda j: {'rollout': {h: {'subsets': {name: r['subsets'][name] for name in names}} for h, r in j['rollout'].items()}})

  common = {
    'schema': 'HURDLE_STAGE1_V4_REPORT_ONLY_ATTRIBUTION',
    'status': a.SUCCESS,
    'scope': 'REPORT_ONLY',
    'baseline_result_publication_head': a.BASELINE,
    'analysis_head': lock['analysis_head'],
    'environment': {k: lock['environment'][k] for k in ('python', 'numpy', 'blas_build_identity_sha256')},
    'execution_head': a.EXECUTION_HEAD,
    'authorization_sha256': a.AUTH_SHA,
    'actual_manifest_sha256': a.MANIFEST_SHA,
    'attribution_manifest_sha256': one['receipt_sha256'],
    'input_lock_sha256': lock['receipt_sha256'],
    'policy_sha256': lock['policy_sha256'],
    'analysis_sources': lock['analysis_sources'],
    'public_input_receipts': lock['public_receipts'],
    'storage_migration_receipt_sha256': lock['storage_migration_receipt_sha256'],
    'storage_amendment_receipt_sha256': lock['storage_amendment_receipt_sha256'],
    'storage_volume': 'E_EXTERNAL_SSD',
    'result_publication_head': {'resolution': 'CONTAINING_GIT_COMMIT'},
    'execution_calls': a.ZERO,
    'selection_result': 'HURDLE_STAGE1_V4_NO_ADMISSIBLE_CANDIDATE',
    'selection_state': 'MODEL_SELECTION_FAILED_CLOSED',
    'selected_candidate': None,
    'holdout': 'CLOSED',
    'opening_count': 0,
    'holdout_discovery': 0,
    'vehicle_authority': 'NONE',
    'authority_states': [
      'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
      'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT',
      'FINAL_POOLED_REFIT_NOT_AUTHORIZED',
      'COMPOSITION_NOT_AUTHORIZED',
      'NOT_READY',
      'REAL_VEHICLE_UNVERIFIED',
      'VEHICLE_ACTIVATION_BLOCKED',
    ],
    'threshold_public': False,
    'coefficients_public': False,
    'next_execution_authorized': False,
    'hugs': 'HUGGING_FACE_NOT_REQUIRED_NOT_USED',
    'delta_tick_semantics': 'SOURCE_GRID_TICK_INCREMENT_CHANGE_NOT_PHYSICAL_EPS_MOVEMENT',
    'logged_command_semantics': 'POST_CARCONTROLLER_NORMALIZED_COMMAND_NOT_PHYSICAL_APPLIED_EPS_TORQUE',
    'rate_semantics': ['SOURCE_NATIVE_RATE_CODE_ONLY', 'RATE_SOURCE_CONTRACT_PARTIAL'],
    'aggregation_scope': 'JOB_COUNTS_AND_JOB_RANGES; OVERLAPPING_ANCHORS_ARE_NOT_INDEPENDENT_SAMPLES; NO_POOLED_AUC',
  }
  body = {
    'attribution-policy': {'policy': a.policy()},
    'exact-hit-decomposition': {
      'jobs': rows(lambda j: {'exact_hit': j['one_step']['exact_hit'], 'static': j['one_step']['static']}),
      'summary': {k: summary['overall'][k] for k in ('exact_hit', 'loss_vs_gain_jobs', 'static')},
    },
    'stage1-confusion-attribution': {'jobs': rows(lambda j: {k: j['one_step'][k] for k in ('confusion', 'contexts', 'move', 'fixed_score_reference')})},
    'state-conditional-ranking': {
      'jobs': rows(lambda j: j['ranking']),
      'summary': summary['overall']['ranking'],
      'inference': 'NONE; SAVED_PROBABILITIES_ONLY; EXACT_RATIONAL_COMPARISONS; NO_SIGNIFICANCE_CLAIM',
    },
    'score-transfer': {
      'jobs': rows(lambda j: {'score_transfer': j['score_transfer'], 'decision_transfer': j['decision_transfer']}),
      'summary': summary['overall']['score_transfer'],
    },
    'fold-asymmetry': {'folds': summary['folds'], 'patterns': summary['fold_patterns'], 'opposite_pattern_supported': summary['fold_opposition_supported']},
    'rollout-gate-attribution': {'jobs': paths(('count', 'horizon', 'gate', 'movement', 'step_bands', 'gate_move_projected_hold_count', 'lineage'))},
    'rollout-context-drift': {
      'jobs': paths(('context_divergence', 'first_events', 'feedback', 'unavailable_saved_inputs')),
      'context_subsets': subsets(('NO_CONTEXT_DIVERGENCE', 'EARLY_CONTEXT_DIVERGENCE', 'LATE_CONTEXT_DIVERGENCE')),
      'interpretation': 'ASSOCIATED_WITH_ONLY; MOVEMENT_MISMATCH_PRECEDES_CONTEXT_DIVERGENCE_BY_ONE_STEP',
    },
    'rollout-step-error': {
      'jobs': paths(('classes', 'static_fp', 'tp_magnitude', 'terminal_error_identity_exact')),
      'interpretation': 'STEP_SAE_SSE_DESCRIPTIVE; TERMINAL_CROSS_TERMS_PREVENT_ADDITIVE_RMSE_ATTRIBUTION',
    },
    'gate-perfect-rollout': {'jobs': subsets(('ALL', 'PATH_MOVED', 'GATE_PERFECT', 'GATE_PERFECT_PATH_MOVED'))},
    'projected-movement-perfect-rollout': {'jobs': subsets(('PROJECTED_MOVEMENT_PATTERN_PERFECT', 'PROJECTED_MOVEMENT_PATTERN_PERFECT_PATH_MOVED'))},
    'rollout-streaks': {'jobs': paths(('streaks', 'feedback'))},
    'mechanism-summary': {
      'mechanism': summary['mechanism'],
      'evidence': summary['mechanism_evidence'],
      'structure': summary['structure'],
      'overall': summary['overall'],
      'historical_comparison': summary['historical_comparison'],
    },
    'next-design-trigger': summary['mechanism'],
    'attribution-repeatability': {'repeatability': repeated},
    'attribution-resume': {'resume': resumed},
    'attribution-readiness': {
      'actual_replica_equality': 'PASS',
      'attribution_repeatability': 'PASS',
      'verify_only_resume': 'PASS',
      'source_immutability': one['source_immutability'],
      'job_count': one['job_count'],
      'storage': lock['storage'],
      'validation_status': validation.get('status', 'PENDING'),
      'integrity_array_decoding': lock['integrity_array_decoding'],
      'integrity_array_files_per_replica': lock['integrity_array_files_per_replica'],
    },
    'attribution-validation': {'validation': validation, 'historical_result_files': 'UNCHANGED', 'new_model_inference': False},
  }
  a.require(set(body) == set(LABELS))
  bundle = {a.PREFIX + name + '.json': p.seal({**common, 'component': name, **value}) for name, value in body.items()}
  for value in bundle.values():
    a.privacy(value)
    json.dumps(value, allow_nan=False)
    a.require(len(p.canonical(value)) < 1024**2, 'V4_ATTRIBUTION_PUBLIC_METADATA_BOUND')
  return bundle


def build(output, validation):
  with a.firewall(), a.access_guard([], output, readonly=True), ExitStack() as stack:
    for module, names in (
      (a, ('array', 'analyze_job', 'analyze_rollout', 'analyze_inputs', 'summarize', 'historical_comparison', 'run', 'write_json', 'finish_store')),
      (saved, ('load_array', 'array_chunks')),
      (a.math, ('ranking', 'rankings', 'one_step', 'PathAccumulator', 'rank_compare', 'transfer')),
    ):
      for name in names:
        stack.enter_context(patch.object(module, name, a.forbidden))
    return _build(output, validation)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output', type=Path, required=True)
  parser.add_argument('--validation', type=Path, required=True)
  args = parser.parse_args()
  bundle = build(args.output, json.loads(args.validation.read_bytes()))
  for name in bundle:
    a.require(not (p.PUBLIC / name).exists())
  for name, row in bundle.items():
    a.write_json(p.PUBLIC / name, row)
  print(json.dumps({'public_aggregate_artifacts': len(bundle)}))


if __name__ == '__main__':
  main()
