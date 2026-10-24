"""Publish insufficient-input evidence; never fabricate numerical attribution."""
import argparse
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_s2_ri_failure_attribution as a

ANALYSES = (
  'one-step-attribution', 'movement-confusion', 'error-decomposition',
  'rollout-attribution', 'rollout-divergence', 'context-attribution',
)


def unavailable(name, audit):
  p.verify(audit)
  if audit['status'] != 'ATTRIBUTION_INPUT_INSUFFICIENT':
    raise ValueError('INSUFFICIENT_INPUT_EVIDENCE_REQUIRED')
  return p.seal({
    'schema': 'EMPIRICAL_S2_RI_'+name.upper().replace('-', '_')+'_V1',
    'input_manifest_sha256': audit['input_manifest_sha256'],
    'input_audit_sha256': audit['receipt_sha256'],
    'status': 'ATTRIBUTION_INPUT_INSUFFICIENT', 'analysis': None,
    'attribution_complete': False, 'array_decodes': 0,
    'reason': 'REQUIRED_STORED_TARGET_ARRAYS_ABSENT_NO_RECOMPUTATION_FALLBACK',
    'numeric_attribution': 'NOT_RUN', 'counterfactual_gate': False,
    'candidate_ranking': False, 'new_fit': False, 'prediction_generation': False,
    'rollout_generation': False,
  })



def digest(value):
  if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
    raise ValueError('OPAQUE_SHA256_REQUIRED')
  return value


def public_job(job, historical):
  """Whitelist nested fields too; never copy arbitrary private audit extensions."""
  expected = {
    'candidate_id': historical['candidate_id'], 'fold': historical['fold'],
    'job_receipt_sha256': historical['receipt_sha256'],
    'model_receipt_sha256': historical['model_receipt_sha256'],
    'normalizer_receipt_sha256': historical['normalizer_receipt_sha256'],
    'one_step_anchor_sha256': historical['one_step']['anchor_sha256'],
    'rollout_anchor_sha256': {h: v['anchor_sha256'] for h, v in historical['rollout'].items()},
    'candidate_comparator_anchors_equal': True,
  }
  if any(job.get(k) != v for k, v in expected.items()):
    raise ValueError('ATTRIBUTION_PUBLIC_JOB_IDENTITY_CONFLICT')
  one, roll = job['one_step_array_sha256'], job['rollout_array_sha256']
  if set(one) != {'prediction', 'projected', 'error', 'comparator_error'} or set(roll) != {str(h) for h in a.HORIZONS}:
    raise ValueError('ATTRIBUTION_BUFFER_SCHEMA_CONFLICT')
  if any(set(v) != {'projected', 'error', 'comparator_error'} for v in roll.values()):
    raise ValueError('ATTRIBUTION_BUFFER_SCHEMA_CONFLICT')
  one = {k: digest(v) for k, v in one.items()}
  roll = {h: {k: digest(v) for k, v in fields.items()} for h, fields in roll.items()}
  return {**expected, 'one_step_array_sha256': one, 'rollout_array_sha256': roll,
          'availability': a.availability({'one_step_buffers': one, 'rollout_buffers': roll})}


def build(root, expected_manifest_sha256):
  # Caller pins the independently recorded audit run, not a hash read back from
  # an untrusted bundle immediately before publication.
  digest(expected_manifest_sha256)
  pairs = [a.verified_saved(root/name) for name in ('repeat-1', 'repeat-2')]
  manifests = [v[0] for v in pairs]
  first, second = [v[1] for v in pairs]
  if any(v['receipt_sha256'] != expected_manifest_sha256 for v in manifests):
    raise ValueError('ATTRIBUTION_PUBLICATION_MANIFEST_PIN_REQUIRED')
  if p.canonical(manifests[0]) != p.canonical(manifests[1]) or first != second:
    raise ValueError('ATTRIBUTION_INPUT_AUDIT_REPEATABILITY_FAILURE')
  public = a.public_inputs()
  jobs = [public_job(job, old) for job, old in zip(first['jobs'], public['fit-cv-results']['jobs'], strict=True)]
  resume = a.read_json(root/'resume-verification.json')
  if (resume['manifest_sha256'] != manifests[0]['receipt_sha256']
      or resume['source_reinspection_trapped'] is not True or resume['array_decode_trapped'] is not True):
    raise ValueError('ATTRIBUTION_VERIFIED_RESUME_REQUIRED')
  historical = public['fit-cv-readiness']
  preserve = ('dataset', 'S1', 'S2', 'S3', 'historical_track', 'historical_grid_verdict', 'stage_b', 'ta', 'sg',
              'composition', 'future_holdout', 'calibration_blockers', 'sealed_reference', 'vehicle', 'closed_loop_bias')
  common = {
    'input_manifest_sha256': a.INPUT_SHA, 'input_audit_sha256': first['receipt_sha256'],
    'status': 'ATTRIBUTION_INPUT_INSUFFICIENT', 'descriptive_outcome': 'ATTRIBUTION_INSUFFICIENT',
    'attribution_complete': False, 'numeric_attribution': 'NOT_RUN',
    'new_model_fit': 'NOT_RUN', 'model_selection': 'NOT_RUN', 'policy_change': False,
    'preserved_verdict': 'S2_RI_NO_ADMISSIBLE_CANDIDATE', 'selection_state': 'MODEL_SELECTION_FAILED_CLOSED',
    'family_verdict': 'FROZEN_S2_RI_LINEAR_FAMILY_FAILED_RETROSPECTIVE_DIRECTIONAL_GATE',
    'hurdle_design_review_supported': None, 'hurdle_trigger': 'NOT_EVALUATED_INSUFFICIENT_INPUT',
    'hurdle_implementation_authorized': False, 'holdout': 'CLOSED', 'opening_count': 0,
    'qlog_access': 0, 'raw_causal_array_access': 0, 'final_pooled_refit': 'NOT_AUTHORIZED',
    'no_model_admitted_for_future_holdout': True,
  }
  values = {'failure-attribution-policy': a.policy()}
  values.update({name: unavailable(name, first) for name in ANALYSES})
  values['failure-attribution-summary'] = p.seal({
    'schema': 'EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_SUMMARY_V1', **common,
    'historical_failure_counts': first['historical_failure_counts'],
    'historical_counts_basis': 'SEALED_RECEIPTS_ONLY_NOT_GATE_REEVALUATION',
    'input_jobs_verified': 32, 'input_files_verified': first['input_files_verified'],
    'input_bytes_unchanged': first['input_bytes_unchanged'],
    'jobs': jobs,
    'mechanism_hypotheses': {'static_false_movement': 'NOT_EVALUATED',
                            'move_sse_reduction': 'NOT_EVALUATED', 'recursive_drift': 'NOT_EVALUATED'},
    'missing_data_are_not_zero': True,
  })
  values['failure-attribution-repeatability'] = p.seal({
    'schema': 'EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_REPEATABILITY_V1',
    'status': 'ATTRIBUTION_INPUT_AUDIT_EXACT_REPEATABILITY_PASS',
    'numeric_attribution_repeatability': 'NOT_RUN_INSUFFICIENT_INPUT',
    'replicas': 2, 'manifest_sha256': [v['receipt_sha256'] for v in manifests],
    'audit_sha256': [first['receipt_sha256'], second['receipt_sha256']],
    'input_file_set_sha256': first['input_files_sha256'],
    'input_bytes_unchanged': first['input_bytes_unchanged'],
    'verified_resume_sha256': resume['receipt_sha256'],
    'decode_compute_trapped_resume_pass': True,
  })
  values['failure-attribution-readiness'] = p.seal({
    'schema': 'EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_READINESS_V1', **common,
    'states': ['ATTRIBUTION_INPUT_INSUFFICIENT', 'NO_NEW_MODEL_FIT', 'NO_MODEL_SELECTION',
               'NO_POLICY_CHANGE', 'S2_RI_NO_ADMISSIBLE_CANDIDATE_PRESERVED'],
    'required_for_full_attribution': [
      'EXACT_ANCHOR_BOUND_STORED_CURRENT_AND_TARGET_TICKS',
      'EXACT_ANCHOR_BOUND_OBSERVED_AND_PROJECTED_PATHS',
      'EXACT_ANCHOR_BOUND_FROZEN_CONTEXT',
    ],
    'future_reconstruction_or_regeneration_authorized': False,
    **{k: historical[k] for k in preserve},
  })
  return {f'empirical-s2-ri-{name}-v1.json': value for name, value in values.items()}


def publish(root, output, expected_manifest_sha256):
  bundle = build(root, expected_manifest_sha256)
  for name, value in bundle.items():
    a.write(output/name, value)
  return bundle


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--store', type=Path, required=True)
  parser.add_argument('--output', type=Path, required=True)
  parser.add_argument('--manifest-sha256', required=True)
  args = parser.parse_args()
  print('published', len(publish(args.store, args.output, args.manifest_sha256)))


if __name__ == '__main__':
  main()
