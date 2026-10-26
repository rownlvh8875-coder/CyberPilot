"""Public aggregate-only projection of verified stored-evidence attribution."""

import argparse
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_hurdle_v2_attribution as execution
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_publication as boundary

p, io = execution.p, execution.io


def build(output, validation):
  boundary.validate_checks(validation)
  manifest = execution.trapped_resume(output / 'repeat-1')
  repeated = io.read_json(output / 'repeatability.json')
  io.require(repeated['status'] == 'BYTE_EXACT_PASS' and repeated['run1_manifest_sha256'] == manifest['receipt_sha256'])
  jobs = [io.read_json(output / f'repeat-1/jobs/{c}/{f}/receipt.json') for c, f in io.JOBS]
  summary = io.read_json(output / 'repeat-1/summary.json', manifest['summary_sha256'])
  ready = io.read_json(output / 'repeat-1/readiness.json', manifest['readiness_sha256'])

  def rows(fn):
    return [{'candidate_id': j['candidate_id'], 'fold': j['fold'], **fn(j)} for j in jobs]

  body = {
    'failure-attribution-policy': {'policy': execution.policy()},
    'exact-hit-decomposition': {'jobs': rows(lambda j: {k: j['one'][k] for k in ('exact_hit', 'v1_exact_hit', 'v1_to_v2')})},
    'move-miss-decomposition': {'jobs': rows(lambda j: {k: j['one'][k] for k in ('move', 'fn', 'tp', 'within', 'classes', 'sae_sse_partition')})},
    'score-ranking': {'jobs': rows(lambda j: {'train': j['train']['ranking'], 'development': j['one']['ranking']})},
    'score-transfer': {'jobs': rows(lambda j: j['ranking_transfer'])},
    'decision-conservatism': {
      'jobs': rows(lambda j: {'train': j['train']['decision'], 'development': j['one']['confusion'], 'selected_objective': j['train']['selected_objective']})
    },
    'feasibility-slack': {
      'jobs': rows(
        lambda j: {
          'slack': j['train']['feasibility_slack'],
          'lineage': j['train']['lineage'],
          'continuous_train_metrics': j['train']['continuous_train_metrics'],
        }
      )
    },
    'fold-asymmetry': {
      'folds': summary['folds'],
      'jobs': rows(
        lambda j: {
          'exact_hit': j['one']['exact_hit'],
          'confusion': j['one']['confusion'],
          'tp': j['one']['tp'],
          'dev_auc': j['one']['ranking']['auc'],
          'historical_gate_pass': j['historical_gate_pass'],
        }
      ),
    },
    'rollout-attribution': {'jobs': rows(lambda j: {'rollout': j['rollout']})},
    'long-horizon-attribution': {
      'jobs': rows(
        lambda j: {'rollout_200': j['rollout']['200'], 'failed_200_clauses': [k for k, v in j['historical_clauses'].items() if '_200_' in k and not v]}
      ),
      'supported_gate_perfect_long_regression_jobs': summary['supported_gate_perfect_long_regression_jobs'],
    },
    'mechanism-summary': {
      'summary': summary,
      'axes': [
        'THRESHOLD_INVARIANT_RANK_SIGNAL',
        'SELECTED_THRESHOLD_DECISION_CONSEQUENCE',
        'INTEGRATED_STAGE2_CONDITIONAL_PERFORMANCE',
        'STORED_RECURSIVE_TRAJECTORIES',
      ],
    },
    'next-design-trigger': {
      k: summary[k]
      for k in (
        'threshold_review',
        'classifier_review',
        'classifier_review_evidence_jobs',
        'stage2_review',
        'stage2_redesign_authorized',
        'redesign_authorized',
        'review_authority',
      )
    },
    'failure-attribution-repeatability': {'repeatability': repeated},
    'failure-attribution-readiness': {'readiness': ready, 'private_manifest_sha256': manifest['receipt_sha256']},
    'failure-attribution-validation': {
      'checks': validation,
      'repeatability_sha256': repeated['receipt_sha256'],
      'historical_evidence': 'UNCHANGED_ADDITIVE_ONLY',
    },
  }
  common = {
    'schema': 'HURDLE_STAGE1_V2_FAILURE_ATTRIBUTION_V1',
    'baseline': execution.BASELINE,
    'v1_manifest_sha256': io.SOURCE_SHA,
    'v2_manifest_sha256': execution.V2_SHA,
    'historical_v1': 'HURDLE_NO_ADMISSIBLE_CANDIDATE',
    'historical_v2': 'HURDLE_STAGE1_V2_NO_ADMISSIBLE_CANDIDATE',
    'selection_state': 'MODEL_SELECTION_FAILED_CLOSED',
    'execution_calls': execution.ZERO,
    'holdout': 'CLOSED',
    'opening_count': 0,
    'vehicle_authority': 'NONE',
    'final_pooled_refit': 'NOT_AUTHORIZED',
    'model_admission': 'NO_MODEL_ADMITTED_FOR_FUTURE_HOLDOUT',
    'next_execution_authorized': False,
  }
  bundle = {execution.PREFIX + name + '.json': p.seal({**common, **value}) for name, value in body.items()}
  for value in bundle.values():
    boundary.privacy(value)
    json.dumps(value, allow_nan=False)
  return bundle


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output', type=Path, required=True)
  parser.add_argument('--validation', type=Path, required=True)
  args = parser.parse_args()
  bundle = build(args.output, json.loads(args.validation.read_bytes()))
  for name in bundle:
    io.require(not (p.PUBLIC / name).exists(), 'ATTRIBUTION_PUBLIC_NO_OVERWRITE')
  for name, value in bundle.items():
    io.write_json(p.PUBLIC / name, value)
  print(json.dumps({'artifacts': len(bundle)}))


if __name__ == '__main__':
  main()
