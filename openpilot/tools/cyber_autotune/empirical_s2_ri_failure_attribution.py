"""Fail-closed input audit for frozen S2-RI failure attribution.

The historical store lacks explicit target/current and trajectory/context arrays.
STEP 2 prohibits a reconstruction fallback: no numerical attribution runs here.
No execution, selection, private array decoder or prediction module is imported.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage

INPUT_SHA = '9466e4578842b4c8a300bb843338e53b42a2fc75200879360f8212c7c2605c97'
HORIZONS = (25, 50, 100, 200)
CANDIDATES = tuple(f'S2RI_D{d:02d}_L{length:02d}' for d in (0, 5, 10, 20) for length in (1, 5, 15, 45))
PUBLIC_PINS = {
  'fit-cv-results': 'cdbdbd8c511d7eeb135990eb57f56098c34b34cc7a7d4e7f0b9cce39c24e9107',
  'candidate-gates': '7413b012048254a8bf7c5e0ba8b51429f1720c4924c1fd91d54bf269a12abd78',
  'selection-result': '706a1e318660f9875d49d558d39f77736003669dd137dce9eeb20146f18a6f32',
  'fit-cv-readiness': 'da10e0b46a0f183d77929fdb79ad82bec36231603258dfa9c480ee9c3f197aa9',
  'fit-cv-job-manifest': '24ff4b983f5b944cca8c5c65e904660b25836741692f3fb81021ba40926c88af',
  'fit-cv-authorization': '18330eeb0ec0b638589fdace76f868234ec336f9a3ee065eebf11e45175797b7',
}
EXPECTED_FAILURES = {
  'ONE_STEP_RMSE': 0, 'ONE_STEP_MAE': 32, 'ONE_STEP_P95': 27,
  'ONE_STEP_EXACT_HIT': 32, 'ONE_STEP_WITHIN_ONE_TICK': 4,
  'ROLLOUT_25_RMSE': 8, 'ROLLOUT_25_MAE': 23, 'ROLLOUT_25_P95': 32,
  'ROLLOUT_50_RMSE': 14, 'ROLLOUT_50_MAE': 25, 'ROLLOUT_50_P95': 29,
  'ROLLOUT_100_RMSE': 16, 'ROLLOUT_100_MAE': 26, 'ROLLOUT_100_P95': 28,
  'ROLLOUT_200_RMSE': 25, 'ROLLOUT_200_MAE': 28, 'ROLLOUT_200_P95': 28,
}


def read_json(path):
  return p.verify(json.loads(storage.safe(path).read_bytes()))


def relative_file(root, name):
  if (not isinstance(name, str) or not name or '\\' in name or ':' in name
      or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts
      or PurePosixPath(name).as_posix() != name):
    raise ValueError('RELATIVE_NO_TRAVERSAL_REQUIRED')
  return storage.safe(storage.safe(root)/name)


def digest_file(path):
  digest = hashlib.sha256()
  with storage.safe(path).open('rb') as stream:
    for block in iter(lambda: stream.read(1024*1024), b''):
      digest.update(block)
  return digest.hexdigest()


def verify_files(root, manifest):
  p.verify(manifest)
  for name, digest in manifest['files'].items():
    path = relative_file(root, name)
    if not path.is_file():
      raise ValueError('ATTRIBUTION_INPUT_INCOMPLETE')
    if digest_file(path) != digest:
      raise ValueError('ATTRIBUTION_INPUT_IMMUTABILITY_FAILURE')
  return p.sha(p.canonical(manifest['files']))


def require_manifest(manifest):
  p.verify(manifest)
  if manifest['receipt_sha256'] != INPUT_SHA:
    raise ValueError('EXACT_A50D_FIT_MANIFEST_REQUIRED')
  if manifest.get('job_count') != 32:
    raise ValueError('ATTRIBUTION_INPUT_INCOMPLETE')


def require_jobs(jobs):
  expected = [(candidate, fold) for candidate in CANDIDATES for fold in ('FOLD_A', 'FOLD_B')]
  if [(j['candidate_id'], j['fold']) for j in jobs] != expected:
    raise ValueError('ATTRIBUTION_INPUT_INCOMPLETE')


def verify_anchors(job):
  if job['one_step']['anchor_sha256'] != job['one_step']['comparator_anchor_sha256']:
    raise ValueError('ATTRIBUTION_ANCHOR_MISMATCH')
  if set(job['rollout']) != {str(h) for h in HORIZONS}:
    raise ValueError('ATTRIBUTION_INPUT_INCOMPLETE')
  for pop in job['rollout'].values():
    if pop['anchor_sha256'] != pop['comparator_anchor_sha256']:
      raise ValueError('ATTRIBUTION_ANCHOR_MISMATCH')


def failure_counts(jobs):
  counts = Counter(name for job in jobs for name in job['gate']['failed'])
  return {'ONE_STEP_RMSE': 0, **dict(sorted(counts.items()))}


def public_inputs():
  values = {}
  for name, digest in PUBLIC_PINS.items():
    path = p.PUBLIC/f'empirical-s2-ri-{name}-v1.json'
    if digest_file(path) != digest:
      raise ValueError('ATTRIBUTION_PUBLIC_INPUT_DRIFT')
    values[name] = read_json(path)
  jobs = values['fit-cv-results']['jobs']
  require_jobs(jobs)
  if failure_counts(jobs) != EXPECTED_FAILURES:
    raise ValueError('HISTORICAL_GATE_ACCOUNTING_CONFLICT')
  if any(v['private_manifest_sha256'] != INPUT_SHA for v in values.values()):
    raise ValueError('EXACT_A50D_FIT_MANIFEST_REQUIRED')
  if values['selection-result']['admissible_count'] != 0 or values['selection-result']['selected_candidate'] is not None:
    raise ValueError('HISTORICAL_VERDICT_CONFLICT')
  return values


def policy():
  return p.seal({
    'schema': 'EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_POLICY_V1',
    'input_manifest_sha256': INPUT_SHA, 'public_file_sha256': PUBLIC_PINS,
    'candidate_order': list(CANDIDATES), 'fold_order': ['FOLD_A', 'FOLD_B'],
    'horizons': list(HORIZONS), 'input_mode': 'READ_ONLY_HASH_AND_SEALED_METADATA',
    'authorized': dict.fromkeys(('fit', 'predict', 'rollout', 'select', 'causal_arrays', 'raw_logs', 'qlog', 'holdout', 'hurdle'), False),
    'missing_required_arrays': 'ATTRIBUTION_INPUT_INSUFFICIENT',
    'fallback': 'NONE_NO_TARGET_RECOVERY_FROM_ERRORS_NO_RECOMPUTATION',
    'array_decode_before_complete_input': False,
    'output': 'INPUT_AUDIT_ONLY_WHEN_REQUIRED_STORED_TARGETS_ARE_ABSENT',
    'hypotheses': ['STATIC_FALSE_MOVEMENT', 'MOVE_SSE_REDUCTION', 'RECURSIVE_DRIFT'],
    'hypotheses_confirmed_in_advance': False,
    'new_thresholds': False, 'candidate_ranking': False, 'counterfactual_gate': False,
    'p95_additive': False, 'holdout': 'CLOSED', 'opening_count': 0,
    'future_design_authorized': False,
  })


def availability(job):
  """Inventory the exact stored representation; never invert error buffers."""
  one = job.get('one_step_buffers', {})
  roll = job.get('rollout_buffers', {})
  reasons = []
  if not {'current_tick', 'target_next_tick'} <= set(one):
    reasons.append('ONE_STEP_CURRENT_AND_TARGET_NOT_PERSISTED')
  if any(not {'initial_tick', 'target_endpoint_tick'} <= set(roll.get(str(h), {})) for h in HORIZONS):
    reasons.append('ROLLOUT_INITIAL_AND_TARGET_NOT_PERSISTED')
  if any(not {'observed_path', 'projected_path'} <= set(roll.get(str(h), {})) for h in HORIZONS):
    reasons.append('ROLLOUT_FULL_PATHS_NOT_PERSISTED')
  if not {'command', 'speed', 'rail', 'prior_delta'} <= set(one):
    reasons.append('FROZEN_CONTEXT_NOT_PERSISTED')
  return {
    'status': 'ATTRIBUTION_INPUT_INSUFFICIENT' if reasons else 'ATTRIBUTION_NOT_EXECUTED',
    'reasons': reasons, 'one_step_stored_fields': sorted(one),
    'rollout_stored_fields': {str(h): sorted(roll.get(str(h), {})) for h in HORIZONS},
    'target_sha256': one.get('target_next_tick'), 'recover_target_from_error': False,
    'numeric_attribution_allowed': False, 'analyses': None,
    'hurdle_trigger': 'NOT_EVALUATED_INSUFFICIENT_INPUT', 'hurdle_implementation_authorized': False,
  }


def inspect_store(root):
  root = storage.safe(root)
  public = public_inputs()
  manifest = read_json(root/'manifest.json')
  require_manifest(manifest)  # Reject an alternate store before hashing any arrays.
  manifest_file_before = digest_file(root/'manifest.json')
  before = verify_files(root, manifest)
  result = read_json(root/'results.json')
  require_jobs(result['jobs'])
  if manifest['results_sha256'] != result['receipt_sha256']:
    raise ValueError('ATTRIBUTION_INPUT_INCOMPLETE')
  jobs = []
  expected_files = {'results.json', 'selection.json'}
  for source, historical in zip(result['jobs'], public['fit-cv-results']['jobs'], strict=True):
    candidate, fold = source['candidate_id'], source['fold']
    prefix = f'candidates/{candidate}/{fold}/'
    local = read_json(root/prefix/'manifest.json')
    receipt = read_json(root/prefix/'receipt.json')
    if receipt != source or receipt['receipt_sha256'] != historical['receipt_sha256']:
      raise ValueError('ATTRIBUTION_JOB_RECEIPT_CONFLICT')
    if local['receipt_sha'] != receipt['receipt_sha256']:
      raise ValueError('ATTRIBUTION_JOB_RECEIPT_CONFLICT')
    for name, digest in local['files'].items():
      relative_file(root/prefix, name)
      if manifest['files'].get(prefix+name) != digest:
        raise ValueError('ATTRIBUTION_JOB_FILE_CONFLICT')
    expected_files.update(prefix+n for n in [*local['files'], 'manifest.json'])
    verify_anchors(receipt)
    for name in ('normalizer', 'model'):
      item = read_json(root/prefix/name/'receipt.json')
      if item['receipt_sha256'] != receipt[name+'_receipt_sha256']:
        raise ValueError('ATTRIBUTION_MODEL_LINEAGE_CONFLICT')
    job_availability = availability(receipt)
    jobs.append({
      'candidate_id': candidate, 'fold': fold, 'job_receipt_sha256': receipt['receipt_sha256'],
      'model_receipt_sha256': receipt['model_receipt_sha256'],
      'normalizer_receipt_sha256': receipt['normalizer_receipt_sha256'],
      'one_step_array_sha256': receipt['one_step_buffers'],
      'rollout_array_sha256': receipt['rollout_buffers'],
      'one_step_anchor_sha256': receipt['one_step']['anchor_sha256'],
      'rollout_anchor_sha256': {h: v['anchor_sha256'] for h, v in receipt['rollout'].items()},
      'candidate_comparator_anchors_equal': True, 'availability': job_availability,
    })
  if set(manifest['files']) != expected_files:
    raise ValueError('ATTRIBUTION_COMPLETE_FILE_SET_REQUIRED')
  selection = read_json(root/'selection.json')
  if selection['receipt_sha256'] != manifest['selection_sha256'] or selection['admissible_count'] != 0:
    raise ValueError('HISTORICAL_VERDICT_CONFLICT')
  after = verify_files(root, manifest)
  if after != before or digest_file(root/'manifest.json') != manifest_file_before:
    raise ValueError('ATTRIBUTION_INPUT_IMMUTABILITY_FAILURE')
  return p.seal({
    'schema': 'EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_INPUT_AUDIT_V1',
    'status': 'ATTRIBUTION_INPUT_INSUFFICIENT', 'descriptive_outcome': 'ATTRIBUTION_INSUFFICIENT',
    'policy_sha256': policy()['receipt_sha256'], 'executor_sha256': digest_file(Path(__file__)),
    'input_manifest_sha256': INPUT_SHA, 'manifest_file_sha256': manifest_file_before,
    'input_files_sha256': before, 'input_files_after_sha256': after,
    'input_files_verified': len(manifest['files']), 'input_bytes_unchanged': True,
    'job_count': len(jobs), 'jobs': jobs, 'historical_failure_counts': failure_counts(result['jobs']),
    'array_decodes': 0, 'new_fit_calls': 0, 'prediction_generations': 0, 'rollout_generations': 0,
    'candidate_selection_calls': 0, 'numerical_attribution': 'NOT_RUN',
    'target_reconstruction': 'NOT_RUN', 'readiness': 'ATTRIBUTION_INPUT_INSUFFICIENT',
    'hurdle_design_review_supported': None, 'hurdle_trigger': 'NOT_EVALUATED_INSUFFICIENT_INPUT',
    'hurdle_implementation_authorized': False, 'gate_reevaluation': False,
    'preserved_verdict': 'S2_RI_NO_ADMISSIBLE_CANDIDATE', 'holdout': 'CLOSED', 'opening_count': 0,
  })


def write(path, value):
  p.verify(value)
  storage.atomic_bytes(path, json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode()+b'\n')


def finish(root, names, fields):
  files = {name: digest_file(relative_file(root, name)) for name in sorted(names)}
  value = p.seal({**fields, 'files': files})
  write(root/'manifest.json', value)
  return value


def resume(root):
  """Verify stored audit bytes only; do not revisit fit inputs or decode arrays."""
  value = read_json(root/'manifest.json')
  verify_files(root, value)
  return value



def verified_saved(root):
  """Exact saved evidence invariants, without revisiting the fit input store."""
  manifest = resume(root)
  if (manifest.get('schema') != 'EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_MANIFEST_V1'
      or set(manifest['files']) != {'audit.json', 'policy.json'}
      or manifest.get('policy_sha256') != policy()['receipt_sha256']
      or manifest.get('executor_sha256') != digest_file(Path(__file__))
      or manifest.get('input_manifest_sha256') != INPUT_SHA
      or manifest.get('status') != 'ATTRIBUTION_INPUT_INSUFFICIENT'
      or read_json(root/'policy.json') != policy()):
    raise ValueError('ATTRIBUTION_STALE_RESUME')
  audit = read_json(root/'audit.json')
  if (audit.get('schema') != 'EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_INPUT_AUDIT_V1'
      or audit['receipt_sha256'] != manifest.get('audit_sha256')
      or audit.get('policy_sha256') != manifest['policy_sha256']
      or audit.get('executor_sha256') != manifest['executor_sha256']
      or audit.get('input_manifest_sha256') != INPUT_SHA
      or audit.get('input_files_verified') != 834 or audit.get('job_count') != 32
      or audit.get('input_bytes_unchanged') is not True
      or audit.get('input_files_sha256') != audit.get('input_files_after_sha256')
      or audit.get('historical_failure_counts') != EXPECTED_FAILURES
      or audit.get('status') != 'ATTRIBUTION_INPUT_INSUFFICIENT'
      or audit.get('numerical_attribution') != 'NOT_RUN'
      or any(audit.get(k) != 0 for k in ('array_decodes', 'new_fit_calls', 'prediction_generations',
                                       'rollout_generations', 'candidate_selection_calls'))):
    raise ValueError('ATTRIBUTION_SAVED_EVIDENCE_CONFLICT')
  require_jobs(audit['jobs'])
  return manifest, audit


def run(source, output):
  source = storage.safe(source)
  output = storage.external(output, [source.parent])
  # Task-specific sibling output layout excludes raw/causal/model source stores
  # without embedding any operator's private location in published code.
  if (source.name != 'repeat-1' or source.parent.name != 'empirical-s2-ri-retrospective-fit-cv-v1'
      or output.parent.parent != source.parent.parent
      or not output.parent.name.startswith('empirical-s2-ri-failure-attribution-')
      or output.name not in ('repeat-1', 'repeat-2')):
    raise ValueError('ATTRIBUTION_OUTPUT_LAYOUT_REQUIRED')
  if (output/'manifest.json').exists():
    value, _ = verified_saved(output)
    if value.get('source_identity') != p.sha(str(source).encode()):
      raise ValueError('ATTRIBUTION_STALE_RESUME')
    return value
  audit = inspect_store(source)
  write(output/'audit.json', audit)
  write(output/'policy.json', policy())
  return finish(output, ['audit.json', 'policy.json'], {
    'schema': 'EMPIRICAL_S2_RI_FAILURE_ATTRIBUTION_MANIFEST_V1',
    'policy_sha256': policy()['receipt_sha256'], 'executor_sha256': digest_file(Path(__file__)),
    'source_identity': p.sha(str(source).encode()), 'input_manifest_sha256': INPUT_SHA,
    'audit_sha256': audit['receipt_sha256'], 'status': audit['status'],
  })


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--source', type=Path, required=True)
  parser.add_argument('--output', type=Path, required=True)
  args = parser.parse_args()
  result = run(args.source, args.output)
  print(result['status'], result['receipt_sha256'])


if __name__ == '__main__':
  main()
