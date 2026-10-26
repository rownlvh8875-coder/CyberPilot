"""Read-only, manifest-bound attribution of already finalized V4 science."""

import argparse
import builtins
from contextlib import contextmanager, ExitStack
from contextvars import ContextVar
import io as stdio
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import patch

import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as saved
from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_math as old
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_attribution_math as math
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_authorization as auth
from openpilot.tools.cyber_autotune import empirical_plant_policy as p

BASELINE = '3943f5c2f4ef641e673ca6a47b24b44a359765c8'
EXECUTION_HEAD = 'bd8045ef2a0da62a92603439f38e7740f5923622'
AUTH_SHA = 'a23e88b37ba1b2b57f5eb29bc37508166a6a392354826d00bb4444d8efcdc34c'
MANIFEST_SHA = 'fd3639f93944edecfdfa573818d29fbc8a91ab23208e2d561f8a69726eb0dc64'
SUCCESS = 'HURDLE_STAGE1_V4_CAUSAL_ROLLOUT_ERROR_ATTRIBUTION_COMPLETE'
PREFIX = 'empirical-hurdle-stage1-v4-'
ZERO = dict.fromkeys(
  (
    'model_refit_calls',
    'normalizer_refit_calls',
    'stage2_refit_calls',
    'threshold_reselection_calls',
    'prediction_replay_calls',
    'rollout_regeneration_calls',
    'selection_calls',
    'candidate_search_calls',
    'raw_log_openings',
    'qlog_openings',
    'holdout_openings',
    'holdout_discovery',
    'source_write_count',
  ),
  0,
)
PUBLIC_INPUTS = (
  'fit-results',
  'development-results',
  'rollout-results',
  'candidate-gates',
  'selection-result',
  'repeatability-actual',
  'resume-actual',
  'retrospective-execution-authorization',
  'retrospective-execution-readiness',
  'retrospective-execution-validation',
  'v1-v2-v3-comparison',
  'job-manifest',
)
HISTORICAL_INPUTS = (
  'empirical-hurdle-fit-cv-results-v1.json',
  'empirical-hurdle-stage1-v2-development-results.json',
  'empirical-hurdle-stage1-v3-development-results.json',
  'empirical-hurdle-mechanism-summary-v1.json',
  'empirical-hurdle-stage1-v2-mechanism-summary.json',
)
_SINK = ContextVar('v4_attribution_sink', default=None)


def require(value, message='V4_ATTRIBUTION_INPUT_CONFLICT'):
  if not value:
    raise ValueError(message)


def forbidden(*args, **kwargs):
  raise ValueError('V4_ATTRIBUTION_OPERATION_FORBIDDEN')


@contextmanager
def firewall():
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_execution as e
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_io as execution_io
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_store as store
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_certificate as certificates
  from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m
  from openpilot.tools.cyber_autotune import empirical_hurdle_v2_attribution as previous
  from openpilot.tools.cyber_autotune import empirical_hurdle_v3_execution as v3

  targets = [
    (
      e,
      (
        'run',
        'execute_job',
        'synthetic_run',
        'train',
        'probability',
        'integrated',
        'development',
        'recursive',
        'rollout',
        'select',
        'save_arrays',
        'save_train',
      ),
    ),
    (execution_io, ('load_route', 'load_models', 'admit_metadata', 'finalized')),
    (store, ('output', 'synthetic_output', 'atomic', 'write_json', 'array_write', 'finish')),
    (auth, ('preflight', 'valid')),
    (certificates, ('rank_generate', 'separation_generate', 'rank_verify', 'separation_verify')),
    (m, ('newton', 'normalizer', 'fit_stage1', 'fit_stage2', 'threshold', 'probability', 'predict_delta', 'integrated', 'recursive', 'project', 'transform')),
    (m.source, ('fit', 'normalizer', 'predict', 'one_step', 'recursive', 'project', 'transform')),
    (np.linalg, ('solve', 'lstsq', 'pinv', 'svd')),
  ]
  with previous.firewall(), ExitStack() as stack:
    for module, names in targets:
      for name in names:
        require(hasattr(module, name), 'V4_ATTRIBUTION_FIREWALL_TARGET_MISSING')
        stack.enter_context(patch.object(module, name, forbidden))
    for module in (v3, auth.prior, auth.prior.legacy):
      for name in (
        'run',
        'execute_job',
        'preflight',
        'authorize',
        'authorization',
        'load_route',
        'load_model',
        'write_json',
        'selection',
        'threshold',
        'source_array',
        'decode_bound_array',
        'permit_valid',
      ):
        if callable(getattr(module, name, None)):
          stack.enter_context(patch.object(module, name, forbidden))
    yield dict(ZERO)


@contextmanager
def access_guard(sources, output, *, allowed_reads=None, storage=None, readonly=False):
  """File-level immutable inputs and exclusive output writes; no destructive APIs."""
  sources = tuple(saved.safe(Path(x)) for x in sources)
  output = saved.safe(Path(output))
  allowed = None if allowed_reads is None else frozenset(saved.safe(Path(x)) for x in allowed_reads)
  require(all(not output.is_relative_to(x) and not x.is_relative_to(output) for x in sources))
  original_open, original_io, original_os = builtins.open, stdio.open, os.open
  original_mkdir = os.mkdir

  def checked(file, writing=False, exclusive=False):
    if isinstance(file, int):
      require(not writing, 'V4_ATTRIBUTION_OPERATION_FORBIDDEN')
      return
    raw = Path(file)
    if not writing and str(raw).startswith(('/proc/', '/sys/')):
      return  # Read-only kernel mount/volume metadata, never a private source root alias.
    path = saved.safe(raw)
    require(not any(x.lower() == 'holdout' for x in path.parts), 'V4_ATTRIBUTION_OPERATION_FORBIDDEN')
    require(not path.name.lower().startswith(('qlog', 'rlog', 'raw-log')), 'V4_ATTRIBUTION_OPERATION_FORBIDDEN')
    if writing:
      require(not readonly, 'V4_ATTRIBUTION_WRITE_FORBIDDEN')
      require(
        path.is_relative_to(output) and path != output and path.suffix == '.json' and exclusive and not path.exists(), 'V4_ATTRIBUTION_SOURCE_WRITE_FORBIDDEN'
      )
    else:
      repo = p.PUBLIC.parents[2]
      runtime = path.suffix in ('.py', '.pyc', '.so') and any(
        path.is_relative_to(x) for x in (repo, Path(sys.base_prefix), Path(sys.prefix), Path(np.__file__).parents[1])
      )
      public = path.is_relative_to(p.PUBLIC) and path.suffix == '.json'
      admitted = path in allowed if allowed is not None else any(path.is_relative_to(x) for x in sources)
      require(admitted or runtime or public or path.is_relative_to(output), 'V4_ATTRIBUTION_UNADMITTED_READ_FORBIDDEN')

  def open_file(file, mode='r', *args, **kwargs):
    checked(file, any(x in mode for x in 'wax+'), 'x' in mode and not any(x in mode for x in 'wa+'))
    return original_open(file, mode, *args, **kwargs)

  def open_io(file, mode='r', *args, **kwargs):
    checked(file, any(x in mode for x in 'wax+'), 'x' in mode and not any(x in mode for x in 'wa+'))
    return original_io(file, mode, *args, **kwargs)

  def open_os(file, flags, *args, **kwargs):
    writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
    checked(file, writing, bool(flags & os.O_EXCL) and not bool(flags & (os.O_TRUNC | os.O_APPEND)))
    return original_os(file, flags, *args, **kwargs)

  def mkdir(path, *args, **kwargs):
    require(not readonly, 'V4_ATTRIBUTION_WRITE_FORBIDDEN')
    path = saved.safe(Path(path))
    require(path == output or path.is_relative_to(output), 'V4_ATTRIBUTION_SOURCE_WRITE_FORBIDDEN')
    return original_mkdir(path, *args, **kwargs)

  with ExitStack() as stack:
    token = _SINK.set((output, storage))
    stack.callback(_SINK.reset, token)
    for module, name, function in ((builtins, 'open', open_file), (stdio, 'open', open_io), (os, 'open', open_os), (os, 'mkdir', mkdir)):
      stack.enter_context(patch.object(module, name, function))
    for name in ('unlink', 'remove', 'rename', 'replace', 'link', 'symlink', 'rmdir', 'chmod', 'truncate'):
      stack.enter_context(patch.object(os, name, forbidden))
    yield


def privacy(value):
  rejected = {
    'scores',
    'p_move',
    'raw_scores',
    'normalizer_values',
    'predicted_gate',
    'integrated_delta',
    'candidate_error',
    'tick_sequence',
    'threshold',
    'coefficients',
    'normalizer',
    'raw_basis_indices',
    'rank_row_indices',
    'gate_sequence',
    'probabilities',
    'projected_path',
    'observed_path',
    'predicted_gate_path',
    'commands',
    'timestamps',
    'gps',
    'witness',
    'active',
    'D',
    'determinant',
    'direction',
    'rank_witness',
    'separation_witness',
    'file_path',
  }
  if isinstance(value, dict):
    require(all(isinstance(k, str) and k not in rejected and k not in ARRAY_FIELDS for k in value), 'V4_ATTRIBUTION_PRIVACY_CONFLICT')
    for item in value.values():
      privacy(item)
  elif isinstance(value, list):
    for item in value:
      privacy(item)
  elif isinstance(value, str):
    require(not re.search(r'(?i)(file://|/mnt/[a-z]/|[a-z]:[\\/]|/home/|\\\\)', value), 'V4_ATTRIBUTION_PRIVACY_CONFLICT')
  else:
    require(value is None or type(value) in (bool, int, float), 'V4_ATTRIBUTION_PRIVACY_CONFLICT')
    if type(value) is float:
      require(np.isfinite(value), 'V4_ATTRIBUTION_PRIVACY_CONFLICT')


def write_json(path, row):
  p.verify(row)
  require('AUTHORIZATION' not in row.get('schema', '').upper(), 'V4_ATTRIBUTION_AUTHORIZATION_MINT_FORBIDDEN')
  require(
    not any(row.get(k) is True for k in ('numeric_access_authorized', 'stage1_train_fit_authorized', 'stage2_refit_authorized')),
    'V4_ATTRIBUTION_AUTHORIZATION_MINT_FORBIDDEN',
  )
  path = saved.safe(Path(path))
  payload = p.canonical(row)
  scope = _SINK.get()
  if scope is not None and scope[1] is not None:
    root, storage = scope
    used = sum(x.stat().st_size for x in root.rglob('*.json'))
    require(used + len(payload) <= storage['aggregate_upper_bytes'], 'V4_ATTRIBUTION_METADATA_CAPACITY_FAILURE')
    require(auth.prior.free_bytes(root) >= len(payload) + storage['reserve_bytes'], 'V4_ATTRIBUTION_STORAGE_CAPACITY_FAILURE')
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open('xb') as stream:
    stream.write(payload)
    stream.flush()
    os.fsync(stream.fileno())


def finish_store(root, fields):
  files = {x.relative_to(root).as_posix(): saved.digest(x) for x in sorted(root.rglob('*.json'))}
  row = p.seal({'schema': 'V4_ATTRIBUTION_MANIFEST', 'status': SUCCESS, 'files': files, **fields})
  write_json(root / 'manifest.json', row)
  return row


def resume(root, manifest_sha256, *, synthetic=False):
  root = saved.safe(Path(root))
  with firewall(), access_guard([], root.parent, readonly=True), ExitStack() as stack:
    for name in (
      'analyze_job',
      'analyze_rollout',
      'analyze_inputs',
      'run',
      'summarize',
      'admit',
      'array',
      'population',
      'matching',
      'snapshots',
      'group_summary',
      'path_mechanism',
      'mechanism_states',
      'write_json',
      'finish_store',
    ):
      if name in globals():
        stack.enter_context(patch(__name__ + '.' + name, forbidden))
    for name in ('one_step', 'ranking', 'rankings', 'transfer', 'rank_compare', 'PathAccumulator'):
      stack.enter_context(patch.object(math, name, forbidden))
    for name in ('load_array', 'array_chunks'):
      stack.enter_context(patch.object(saved, name, forbidden))
    if not synthetic:
      auth.prior.external.prove_authorized_external_volume(root)
      binding = validate_lock(root.parent)
    manifest = saved.read_json(root / 'manifest.json', manifest_sha256)
    require(manifest['schema'] == 'V4_ATTRIBUTION_MANIFEST' and manifest['status'] == SUCCESS)
    if not synthetic:
      require(manifest['input_identity_sha256'] == binding['receipt_sha256'] and manifest['policy_sha256'] == binding['policy_sha256'])
    require(set(manifest['files']) == {x.relative_to(root).as_posix() for x in root.rglob('*.json')} - {'manifest.json'})
    saved.verify_files(root, manifest['files'])
    for name in manifest['files']:
      privacy(saved.read_json(root / name))
    return {'status': 'PASS', 'manifest_sha256': manifest['receipt_sha256'], 'recompute_calls': 0}


def sources():
  from openpilot.tools.cyber_autotune import empirical_hurdle_v2_attribution as previous

  files = (
    Path(__file__),
    Path(math.__file__),
    Path(__file__).with_name('empirical_hurdle_v4_attribution_publication.py'),
    Path(saved.__file__),
    Path(old.__file__),
    Path(math.v2.__file__),
    Path(p.__file__),
    Path(auth.__file__),
    Path(auth.prior.external.__file__),
    Path(previous.__file__),
  )
  return {x.name: saved.digest(x) for x in files}


def policy():
  return p.seal(
    {
      'schema': 'HURDLE_STAGE1_V4_ATTRIBUTION_POLICY',
      'baseline': BASELINE,
      'execution_head': EXECUTION_HEAD,
      'authorization_sha256': AUTH_SHA,
      'actual_manifest_sha256': MANIFEST_SHA,
      'scope': 'REPORT_ONLY',
      'job_order': [list(x) for x in saved.JOBS],
      'horizons': list(saved.HORIZONS),
      'auc': 'V2_EXACT_SCORE_TIE_GROUPS_PYTHON_INTEGER_NUMERATOR; EXACT_CROSS_MULTIPLICATION',
      'one_step_error': 'CONTINUOUS_INTEGRATED_DELTA_ERROR_DISTINCT_FROM_PROJECTED_INTEGER_TICK_ERROR',
      'integer_path_reductions': 'STREAMED_EXACT_INTEGER_HISTOGRAMS; FLOAT64_FINAL_RATIOS; LINEAR_P95',
      'first_event': 'ONE_BASED_STEP; ZERO_NONE; FIRST_CONTEXT_DIVERGENCE_MINIMUM_2',
      'early_context_divergence': '4_TIMES_FIRST_DIVERGENCE_STEP_LE_HORIZON; STRUCTURAL_FIRST_QUARTER',
      'support': {'empty': 0, 'small': [1, 200], 'full_minimum': 201},
      'gate_perfect_improvement': 'SUPPORT_GE_201_AND_ALL_RMSE_MAE_P95_STRICTLY_BELOW_HOLD_AND_OVERALL_ANY_STRICTLY_ABOVE_HOLD',
      'gate_perfect_residual': 'SUPPORT_GE_201_AND_ANY_RMSE_MAE_P95_STRICTLY_ABOVE_HOLD; NONEXCLUSIVE_RISK',
      'context_drift_association': 'EARLY_AND_NO_DIVERGENCE_SUPPORT_GE_201; EARLY_ALL_RMSE_MAE_P95_GREATER; REPORT_COUNTS_NO_PREVALENCE_CUTOFF',
      'fold_opposition': 'STRICT_MAJORITY_JOB_OPERATING_BIAS_AND_MEAN_SCORE_TRANSFER_OPPOSITE_SIGNS_ACROSS_FOLDS; REPORT_ALL_COUNTS',
      'ranking_state': 'REPORT_IMPROVED_EQUAL_DECREASED_PER_CONTEXT; ANY_IMPROVED_SUPPORTED_FOR_THOSE_JOBS_ONLY; NONE_NOT_SUPPORTED',
      'next_review_precedence': [
        'MIXED_GATE_AND_MAGNITUDE',
        'SUPPORTED_MAGNITUDE_RESIDUAL',
        'SUPPORTED_CONTEXT_DRIFT',
        'BOTH_CONTEXTS_MORE_IMPROVED_THAN_DECREASED_AND_FOLD_OPPOSITION',
        'STAGE1_REPRESENTATION',
      ],
      'train_decisions': 'SAVED_AGGREGATE_CONFUSION_ONLY; ROW_GATES_INPUT_INSUFFICIENT_NO_THRESHOLD_APPLICATION',
      'missing_inputs': 'INPUT_INSUFFICIENT; NEVER_RECONSTRUCT_OR_INFER',
      'output': 'DIRECT_E_EXTERNAL_SSD_NEW_AGGREGATE_SINK_ONLY',
      'candidate_ranking': False,
      'causal_claim': 'MECHANICAL_CONTEXT_IDENTITY_AND_OTHERWISE_DESCRIPTIVE_ASSOCIATION_ONLY',
      'execution_calls': ZERO,
    }
  )


def public_lock():
  rows = {name: saved.read_json(p.PUBLIC / (PREFIX + name + '.json')) for name in PUBLIC_INPUTS}
  for row in rows.values():
    require(row['execution_head'] == EXECUTION_HEAD and row['authorization_sha256'] == AUTH_SHA)
    require(row['private_manifest_sha256'] == MANIFEST_SHA and row['holdout'] == 'CLOSED' and row['vehicle_authority'] == 'NONE')
  require(rows['retrospective-execution-validation']['publication_validation'] == 'PASS')
  selection = rows['selection-result']['selection']
  require(selection['selected_candidate'] is None and selection['admissible_count'] == 0)
  pins = {PREFIX + k + '.json': v['receipt_sha256'] for k, v in rows.items()}
  pins.update({name: saved.read_json(p.PUBLIC / name)['receipt_sha256'] for name in HISTORICAL_INPUTS})
  for name in pins:
    original = subprocess.check_output(['git', 'show', BASELINE + ':docs/cyberpilot/changes/' + name], cwd=p.PUBLIC.parents[2])
    require(p.sha(original) == saved.digest(p.PUBLIC / name))
  return rows, pins


def resolve_roots(metadata_path, actual):
  meta = saved.read_json(metadata_path)
  original = saved.read_json(actual / 'repeat-1/authorization.json', AUTH_SHA)
  amendment, migration = auth.prior.external.contracts()
  require(meta['migration_receipt_sha256'] == migration['receipt_sha256'] == original['storage_migration_receipt_sha256'])
  require(amendment['receipt_sha256'] == original['storage_amendment_receipt_sha256'])
  roots = {k: saved.safe(Path(meta[k])) for k in ('source', 'causal', 'derived')}
  roots['actual'] = saved.safe(Path(actual))
  require(all(p.sha(str(v).encode()) == original['root_identities'][k if k != 'actual' else 'output'] for k, v in roots.items()))
  require(original['head'] == EXECUTION_HEAD and original['executor_sources'] == auth.sources())
  for root in roots.values():
    auth.prior.external.prove_authorized_external_volume(root, expected_mount=original['mount_identity_sha256'])
  auth.prior.external.check_live_volume(original['volume_identity_sha256'])
  return roots, original


def snapshots(roots):
  one = saved.read_json(roots['actual'] / 'repeat-1/manifest.json', MANIFEST_SHA)
  two = saved.read_json(roots['actual'] / 'repeat-2/manifest.json', MANIFEST_SHA)
  require(one == two)
  v1 = saved.read_json(roots['source'] / 'repeat-1/manifest.json', saved.SOURCE_SHA)
  result = {}
  for name, root, manifest in (
    ('v4_repeat_1', roots['actual'] / 'repeat-1', one),
    ('v4_repeat_2', roots['actual'] / 'repeat-2', two),
    ('v1_reference', roots['source'] / 'repeat-1', v1),
  ):
    result[name] = saved.verify_files(root, manifest['files'])
    result[name + '_manifest_file_sha256'] = saved.digest(root / 'manifest.json')
  metadata = {
    'source': ('authorization.json', 'repeatability.json', 'input-pins.json'),
    'causal': ('authorization.json', 'repeat-1/manifest.json'),
    'derived': ('repeat-1/derived-index.json', 'repeat-1/results.json', 'repeat-1/admission.json'),
  }
  for key, names in metadata.items():
    for name in names:
      result[key + ':' + name] = saved.digest(saved.member(roots[key], name))
  return result


def admitted_read_files(roots, metadata):
  files = {saved.safe(Path(metadata))}
  for base, sha in (
    (roots['actual'] / 'repeat-1', MANIFEST_SHA),
    (roots['actual'] / 'repeat-2', MANIFEST_SHA),
    (roots['source'] / 'repeat-1', saved.SOURCE_SHA),
  ):
    manifest = saved.read_json(base / 'manifest.json', sha)
    files.add(base / 'manifest.json')
    files.update(saved.member(base, name) for name in manifest['files'])
  for key, names in {
    'source': ('authorization.json', 'repeatability.json', 'input-pins.json'),
    'causal': ('authorization.json', 'repeat-1/manifest.json'),
    'derived': ('repeat-1/derived-index.json', 'repeat-1/results.json', 'repeat-1/admission.json'),
  }.items():
    files.update(saved.member(roots[key], name) for name in names)
  return files


def admit(roots):
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_execution as e

  # Equality and full opaque file hash verification precede ALL analysis decoding.
  before = snapshots(roots)
  repeated = e.repeatability(roots['actual'] / 'repeat-1', MANIFEST_SHA, roots['actual'] / 'repeat-2', MANIFEST_SHA, authorization_sha256=AUTH_SHA)
  manifest = saved.read_json(roots['actual'] / 'repeat-1/manifest.json', MANIFEST_SHA)
  v1 = saved.read_json(roots['source'] / 'repeat-1/manifest.json', saved.SOURCE_SHA)
  current = saved.read_json(roots['actual'] / 'repeat-1/results.json', manifest['result_sha256'])
  historical = saved.read_json(roots['source'] / 'repeat-1/results.json', v1['results_sha256'])
  require([(j['candidate_id'], j['fold']) for j in current['jobs']] == list(saved.JOBS))
  require([(j['candidate_id'], j['fold']) for j in historical['jobs']] == list(saved.JOBS))
  require(all(j['status'] == 'EXECUTED_COMPLETE' for j in current['jobs']))
  return {
    'before': before,
    'repeatability': repeated,
    'v4_manifest': manifest,
    'v1_manifest': v1,
    'current_jobs': current['jobs'],
    'historical_jobs': historical['jobs'],
    'integrity_array_files_per_replica': sum(x.endswith('.npy.gz') for x in manifest['files']),
    'integrity_array_decoding': 'SAVED_ONLY_INCLUDING_COEFFICIENT_BYTES_FOR_IDENTITY; NO_MODEL_EXECUTION',
  }


def population(root, manifest, job, label, *, v4):
  local = root / 'repeat-1/candidates' / job['candidate_id'] / job['fold'] / label
  name = (local / 'receipt.json').relative_to(root / 'repeat-1').as_posix()
  require(name in manifest['files'] and saved.digest(local / 'receipt.json') == manifest['files'][name])
  expected = None if v4 else job['population_receipts'][label]
  receipt = saved.read_json(local / 'receipt.json', expected)
  expected_anchor = (
    job['train_anchor_sha256']
    if label == 'train'
    else (job['one_step']['anchor_sha256'] if label == 'one-step' else job['rollout'][label.split('-')[1]]['overall']['anchor_sha256'])
  )
  actual_anchor = receipt.get('anchor_sha256', receipt.get('train_anchor_sha256'))
  require(actual_anchor == expected_anchor)
  for item in receipt['arrays'].values():
    member = saved.member(local, item['filename'])
    require(manifest['files'].get(member.relative_to(root / 'repeat-1').as_posix()) == item['file_sha256'])
  return local, receipt


ARRAY_FIELDS = frozenset(
  (
    'combined_probability',
    'p_move',
    'predicted_gate',
    'integrated_delta',
    'projected_next_tick',
    'candidate_error',
    'current_tick',
    'target_next_tick',
    'comparator_error',
    'prior_delta_tick',
    'actual_delta_tick',
    'move_label',
    'true_move',
    'observed_path',
    'hold_last_path',
    'projected_path',
    'predicted_gate_path',
    'train_probability',
  )
)


def array(root, receipt, key, *, chunks=False):
  require(key in ARRAY_FIELDS, 'V4_ATTRIBUTION_ARRAY_ACCESS_FORBIDDEN')
  require(key in receipt['arrays'], 'V4_ATTRIBUTION_INPUT_INSUFFICIENT')
  if chunks:
    binding = receipt['arrays'][key]
    return saved.array_chunks(saved.member(root, binding['filename']), binding)
  result = saved.load_array(root, receipt, key)
  result.flags.writeable = False
  return result


def matching(v4, reference):
  require(v4.get('anchor_sha256', v4.get('train_anchor_sha256')) == reference['anchor_sha256'])
  primary = next(k for k in ('combined_probability', 'p_move', 'projected_path') if k in v4['arrays'])
  expected = v4['arrays'][primary]['shape'][0]
  require(
    all(
      v['shape'][0] == expected
      for k, v in reference['arrays'].items()
      if k in ('current_tick', 'target_next_tick', 'actual_delta_tick', 'prior_delta_tick', 'observed_path')
    )
  )


def analyze_rollout(roots, admitted, job, historical, horizon):
  label = f'rollout-{horizon}'
  local, current = population(roots['actual'], admitted['v4_manifest'], job, label, v4=True)
  original, reference = population(roots['source'], admitted['v1_manifest'], historical, label, v4=False)
  matching(current, reference)
  readers = [
    array(base, receipt, key, chunks=True)
    for base, receipt, key in (
      (original, reference, 'observed_path'),
      (local, current, 'projected_path'),
      (local, current, 'predicted_gate_path'),
      (local, current, 'candidate_error'),
      (original, reference, 'comparator_error'),
      (original, reference, 'prior_delta_tick'),
    )
  ]
  accumulator = math.PathAccumulator(horizon)
  for observed, projected, gate, error, hold, previous in zip(*readers, strict=True):
    accumulator.add(observed, projected, gate, error, hold, previous != 0)
  result = accumulator.finish()
  require(result['count'] == job['rollout'][str(horizon)]['overall']['count'])
  result['lineage'] = {
    'v4_population_receipt_sha256': current['receipt_sha256'],
    'reference_population_receipt_sha256': reference['receipt_sha256'],
    'anchor_sha256': current['anchor_sha256'],
  }
  result['unavailable_saved_inputs'] = {
    'step_probability': 'INPUT_INSUFFICIENT',
    'continuous_branch_delta': 'INPUT_INSUFFICIENT',
    'saved_context_path': 'INPUT_INSUFFICIENT; MECHANICAL_CONTEXT_DERIVED_FROM_SAVED_PATH_AND_INITIAL_REFERENCE',
  }
  return result


def analyze_job(roots, admitted, job, historical):
  v4root, v4train = population(roots['actual'], admitted['v4_manifest'], job, 'train', v4=True)
  trroot, tr = population(roots['source'], admitted['v1_manifest'], historical, 'train', v4=False)
  matching(v4train, tr)
  train_y, train_z = array(trroot, tr, 'move_label').astype(bool), array(trroot, tr, 'prior_delta_tick') != 0
  actual = array(trroot, tr, 'actual_delta_tick')
  require(np.array_equal(train_y, actual != 0))
  probability = array(v4root, v4train, 'combined_probability')
  require(len(probability) == job['train_count'])
  train_rank = math.rankings(probability, train_y, train_z)
  selected = v4train['threshold']  # Stored aggregate decision only; never apply its private value.
  train_decision = old.confusion_counts({k: selected[k] for k in ('TN', 'FP', 'FN', 'TP')})
  require(train_decision['count'] == len(train_y) and selected['P'] == math.count(train_y) and selected['N'] == math.count(~train_y))
  devroot, dev = population(roots['actual'], admitted['v4_manifest'], job, 'one-step', v4=True)
  refroot, ref = population(roots['source'], admitted['v1_manifest'], historical, 'one-step', v4=False)
  matching(dev, ref)
  current, target, hold, previous = (array(refroot, ref, k) for k in ('current_tick', 'target_next_tick', 'comparator_error', 'prior_delta_tick'))
  gate, projected, delta, error, score = (
    array(devroot, dev, k) for k in ('predicted_gate', 'projected_next_tick', 'integrated_delta', 'candidate_error', 'p_move')
  )
  one = math.one_step(current, target, gate, projected, delta, error, hold, previous != 0)
  require(one['confusion']['counts'] == {k: job['stage1_diagnostics'][k] for k in ('TN', 'FP', 'FN', 'TP')})
  dev_rank = math.rankings(score, target.astype(np.int64) != current.astype(np.int64), previous != 0)
  historical_rank = math.rankings(array(refroot, ref, 'p_move'), target.astype(np.int64) != current.astype(np.int64), previous != 0)
  old_gate = array(refroot, ref, 'predicted_gate')
  old_projected = array(refroot, ref, 'projected_next_tick').astype(np.int64)
  old_truth = target.astype(np.int64) != current.astype(np.int64)
  one['fixed_score_reference'] = {
    'confusion': old.confusion(old_truth, old_gate),
    'harmful_false_movement': math.count(~old_truth & (old_projected != current)),
    'exact_hit': math.v2.hit_counts(current.astype(np.int64), target.astype(np.int64), old_projected),
  }
  return p.seal(
    {
      'schema': 'V4_ATTRIBUTION_JOB',
      'candidate_id': job['candidate_id'],
      'fold': job['fold'],
      'one_step': one,
      'ranking': {
        'train': train_rank,
        'development': dev_rank,
        'historical_fixed': historical_rank,
        'comparison': {k: math.rank_compare(dev_rank[k], historical_rank[k]) for k in dev_rank},
      },
      'score_transfer': {k: math.transfer(train_rank[k], dev_rank[k]) for k in train_rank},
      'decision_transfer': {
        'train': train_decision,
        'development': one['confusion'],
        'dev_minus_train': {k: one['confusion'][k] - train_decision[k] for k in ('true_move_fraction', 'predicted_move_fraction', 'recall', 'specificity')},
        'train_rowwise_gate': 'INPUT_INSUFFICIENT; NOT_SAVED; NO_THRESHOLD_APPLICATION',
      },
      'lineage': {
        'v4_job_receipt_sha256': job['receipt_sha256'],
        'v1_job_receipt_sha256': historical['receipt_sha256'],
        'train_population_sha256': v4train['receipt_sha256'],
        'one_step_population_sha256': dev['receipt_sha256'],
        'reference_train_sha256': tr['receipt_sha256'],
        'reference_development_sha256': ref['receipt_sha256'],
      },
      'historical_gate': job['gate'],
      'historical_rollout': job['rollout'],
      'rollout': {str(h): analyze_rollout(roots, admitted, job, historical, h) for h in saved.HORIZONS},
      'execution_calls': ZERO,
    }
  )


def path_mechanism(row, *, overall_failed):
  def supported(pair):
    return pair['count'] >= 201

  subsets = row['subsets']
  metrics = ('rmse', 'mae', 'p95')
  pairs = [subsets[k] for k in ('GATE_PERFECT', 'GATE_PERFECT_PATH_MOVED')]
  improve = any(supported(x) and all(x['candidate'][k] < x['hold_last'][k] for k in metrics) for x in pairs)
  residual = any(supported(x) and any(x['candidate'][k] > x['hold_last'][k] for k in metrics) for x in pairs)
  early, same = subsets['EARLY_CONTEXT_DIVERGENCE'], subsets['NO_CONTEXT_DIVERGENCE']
  drift = supported(early) and supported(same) and all(early['candidate'][k] > same['candidate'][k] for k in metrics)
  return {'gate_mismatch_risk': bool(overall_failed and improve), 'magnitude_residual_risk': bool(residual), 'context_drift_association': bool(drift)}


def overall_excess(saved_pair):
  return any(saved_pair['candidate'][k] > saved_pair['comparator'][k] for k in ('rmse', 'mae', 'p95'))


def mechanism_states(flags, *, static_loss, fold_opposite, ranking_improved, operating_transfer):
  states = []
  if static_loss:
    states.append('V4_STATIC_FALSE_MOVEMENT_EXACT_HIT_LOSS_SUPPORTED')
  if fold_opposite:
    states.append('V4_FOLD_TRANSFER_ASYMMETRY_PERSISTS')
  states.append('V4_WITHIN_STATE_RANKING_IMPROVEMENT_SUPPORTED' if ranking_improved else 'V4_WITHIN_STATE_RANKING_IMPROVEMENT_NOT_SUPPORTED')
  for key, name in (
    ('gate_mismatch_risk', 'V4_STAGE1_GATE_MISMATCH_LONG_HORIZON_RISK_SUPPORTED'),
    ('magnitude_residual_risk', 'V4_STAGE2_OR_MAGNITUDE_RESIDUAL_RISK_SUPPORTED'),
    ('context_drift_association', 'V4_RECURSIVE_CONTEXT_DRIFT_ASSOCIATION_SUPPORTED'),
  ):
    if flags[key]:
      states.append(name)
  if flags['gate_mismatch_risk'] and flags['magnitude_residual_risk']:
    states.append('V4_MIXED_GATE_AND_MAGNITUDE_FAILURE_SUPPORTED')
    category = 'MIXED_STAGE1_STAGE2_ARCHITECTURE_REVIEW'
  elif flags['magnitude_residual_risk']:
    category = 'STAGE2_CONDITIONAL_DELTA_MODEL_REVIEW'
  elif flags['context_drift_association']:
    category = 'ROLLOUT_STATE_FEEDBACK_REDESIGN_REVIEW'
  elif operating_transfer:
    category = 'DECISION_POLICY_REVIEW'
  else:
    category = 'STAGE1_REPRESENTATION_REDESIGN_REVIEW'
  return {
    'states': states,
    'recommended_one_review': category,
    'scope': 'REPORT_ONLY',
    'next_execution_authorized': False,
    'interpretation_limit': 'SUPPORTED_JOB_SUBSETS_ONLY; NONEXCLUSIVE; CONTEXT_ASSOCIATION_NOT_INTERVENTIONAL_CAUSALITY',
  }


def ranges(values):
  values = [float(v) for v in values if v is not None]
  return {**old.summary(np.asarray(values, dtype=float)), 'mean': float(np.mean(values)) if values else None}


def historical_comparison():
  result = {}
  for family, name in zip(('V1', 'V2', 'V3'), HISTORICAL_INPUTS[:3], strict=True):
    evidence = saved.read_json(p.PUBLIC / name)
    folds = {}
    for fold in ('FOLD_A', 'FOLD_B'):
      jobs = [j for j in evidence['jobs'] if j['fold'] == fold and j.get('stage1_diagnostics', {}).get('status') == 'DEFINED']
      rows = [old.confusion_counts({k: j['stage1_diagnostics'][k] for k in ('TN', 'FP', 'FN', 'TP')}) for j in jobs]
      folds[fold] = {
        'evaluated_jobs': len(rows),
        **{key: ranges([r[key] for r in rows]) for key in ('false_move_rate', 'missed_move_rate', 'predicted_move_fraction', 'true_move_fraction')},
        'job_anchor_bindings': [{'candidate_id': j['candidate_id'], 'anchor_sha256': j['one_step']['anchor_sha256']} for j in jobs],
      }
    result[family] = {'receipt_sha256': evidence['receipt_sha256'], 'folds': folds}
  return result


def group_summary(jobs):
  result = {
    'job_count': len(jobs),
    'count_scope': 'SUM_OF_CANDIDATE_JOB_ROWS; OVERLAPPING_ANCHORS_NOT_INDEPENDENT_SAMPLES',
    'exact_hit': {
      k: sum(j['one_step']['exact_hit'][k] for j in jobs)
      for k in (
        'static_truth_count',
        'move_truth_count',
        'static_hit_loss',
        'move_hit_gain',
        'net_hit_delta',
        'candidate_exact_hit_count',
        'hold_exact_hit_count',
      )
    },
    'loss_vs_gain_jobs': {
      name: sum(compare(j['one_step']['exact_hit']['static_hit_loss'], j['one_step']['exact_hit']['move_hit_gain']) for j in jobs)
      for name, compare in (('greater', lambda a, b: a > b), ('equal', lambda a, b: a == b), ('less', lambda a, b: a < b))
    },
    'static': {k: sum(j['one_step']['static'][k] for j in jobs) for k in ('gate_fp', 'harmful_false_movement', 'gate_fp_projected_hold')},
    'one_step_rates': {
      k: ranges([j['one_step']['confusion'][k] for j in jobs])
      for k in ('false_move_rate', 'missed_move_rate', 'recall', 'specificity', 'predicted_move_fraction', 'true_move_fraction')
    },
    'ranking': {},
    'score_transfer': {},
    'rollout': {},
  }
  result['operating_bias'] = ranges([j['one_step']['confusion']['predicted_move_fraction'] - j['one_step']['confusion']['true_move_fraction'] for j in jobs])
  result['operating_bias_counts'] = {
    name: sum(compare(j['one_step']['confusion']['predicted_move_fraction'], j['one_step']['confusion']['true_move_fraction']) for j in jobs)
    for name, compare in (('over_active', lambda a, b: a > b), ('equal', lambda a, b: a == b), ('over_conservative', lambda a, b: a < b))
  }
  for context in ('OVERALL', 'PREV_STATIC', 'PREV_MOVE'):
    result['ranking'][context] = {
      population: {
        k: ranges([j['ranking'][population][context].get(k) for j in jobs])
        for k in ('auc', 'brier', 'mean_probability', 'true_move_prevalence', 'calibration_bias', 'move_score_mean', 'static_score_mean', 'score_mean_gap')
      }
      for population in ('train', 'development', 'historical_fixed')
    }
    result['ranking'][context]['comparison_counts'] = {
      state: sum(j['ranking']['comparison'][context] == state for j in jobs)
      for state in ('V4_RANK_IMPROVED', 'V4_RANK_EQUAL', 'V4_RANK_DECREASED', 'INPUT_INSUFFICIENT')
    }
    result['score_transfer'][context] = {
      k: ranges([j['score_transfer'][context].get('dev_minus_train', {}).get(k) for j in jobs])
      for k in ('auc', 'mean_probability', 'true_move_prevalence', 'calibration_bias', 'brier', 'score_mean_gap')
    }
  for h in saved.HORIZONS:
    rows = [j['rollout'][str(h)] for j in jobs]
    value = {
      'gate_false_move_rate': ranges([r['gate']['false_move_rate'] for r in rows]),
      'gate_missed_move_rate': ranges([r['gate']['missed_move_rate'] for r in rows]),
      'gate_mismatch_rate': ranges([(r['gate']['counts']['FP'] + r['gate']['counts']['FN']) / r['gate']['count'] for r in rows]),
      'movement_mismatch_rate': ranges([(r['movement']['counts']['FP'] + r['movement']['counts']['FN']) / r['movement']['count'] for r in rows]),
      'predicted_move_rate': ranges([r['gate']['predicted_move_fraction'] for r in rows]),
      'projected_move_rate': ranges([r['movement']['predicted_move_fraction'] for r in rows]),
      'true_move_rate': ranges([r['gate']['true_move_fraction'] for r in rows]),
      'context_divergence_rate': ranges([r['context_divergence']['rate'] for r in rows]),
      'terminal': {k: ranges([r['subsets']['ALL']['candidate'][k] for r in rows]) for k in ('rmse', 'mae', 'p95')},
      'subsets': {},
      'first_events': {},
      'streaks': {},
    }
    for name in rows[0]['subsets']:
      pairs = [r['subsets'][name] for r in rows]
      value['subsets'][name] = {
        'path_count_sum': sum(x['count'] for x in pairs),
        'support_job_counts': {
          state: sum(x['support_status'] == state for x in pairs) for state in ('EMPTY', 'SMALL_SUPPORT_DESCRIPTIVE_ONLY', 'FULL_DESCRIPTIVE_SUPPORT')
        },
        'candidate': {k: ranges([x['candidate'][k] if x['candidate'] else None for x in pairs]) for k in ('rmse', 'mae', 'p95')},
        'hold_last': {k: ranges([x['hold_last'][k] if x['hold_last'] else None for x in pairs]) for k in ('rmse', 'mae', 'p95')},
      }
    for family in ('first_events', 'streaks'):
      for name in rows[0][family]:
        histogram = math.IntegerHistogram()
        for row in rows:
          histogram.values.update({int(k): n for k, n in row[family][name]['histogram'].items()})
        value[family][name] = {**histogram.summary(), 'histogram': {str(k): n for k, n in sorted(histogram.values.items())}}
    result['rollout'][str(h)] = value
  return result


def summarize(jobs):
  require([(j['candidate_id'], j['fold']) for j in jobs] == list(saved.JOBS))
  overall = group_summary(jobs)
  folds = {fold: group_summary([j for j in jobs if j['fold'] == fold]) for fold in ('FOLD_A', 'FOLD_B')}
  patterns = {}
  for fold, row in folds.items():
    counts = row['operating_bias_counts']
    patterns[fold] = (
      'OVER_ACTIVE_MAJORITY' if counts['over_active'] > 8 else ('OVER_CONSERVATIVE_MAJORITY' if counts['over_conservative'] > 8 else 'MIXED_OR_EQUAL')
    )
  opposite = set(patterns.values()) == {'OVER_ACTIVE_MAJORITY', 'OVER_CONSERVATIVE_MAJORITY'}
  shifts = [folds[f]['score_transfer']['OVERALL']['mean_probability']['mean'] for f in ('FOLD_A', 'FOLD_B')]
  opposite = opposite and shifts[0] * shifts[1] < 0
  references = {k: [] for k in ('gate_mismatch_risk', 'magnitude_residual_risk', 'context_drift_association')}
  for job in jobs:
    for h in saved.HORIZONS:
      overall_failed = overall_excess(job['historical_rollout'][str(h)]['overall'])
      flags = path_mechanism(job['rollout'][str(h)], overall_failed=overall_failed)
      for k, enabled in flags.items():
        if enabled:
          references[k].append({'candidate_id': job['candidate_id'], 'fold': job['fold'], 'horizon': h})
  improved = {c: overall['ranking'][c]['comparison_counts']['V4_RANK_IMPROVED'] for c in ('PREV_STATIC', 'PREV_MOVE')}
  decreased = {c: overall['ranking'][c]['comparison_counts']['V4_RANK_DECREASED'] for c in improved}
  mechanism = mechanism_states(
    {k: bool(v) for k, v in references.items()},
    static_loss=overall['loss_vs_gain_jobs']['greater'] > 16,
    fold_opposite=opposite,
    ranking_improved=any(improved.values()),
    operating_transfer=opposite and all(improved[c] > decreased[c] for c in improved),
  )
  structure = {
    axis: {str(value): group_summary([j for j in jobs if int(j['candidate_id'].split('_')[position][1:]) == value]) for value in values}
    for axis, position, values in (('d', 1, (0, 5, 10, 20)), ('L', 2, (1, 5, 15, 45)))
  }
  for groups in structure.values():
    for group in groups.values():
      for horizon, row in group['rollout'].items():
        group['rollout'][horizon] = {
          k: row[k]
          for k in (
            'gate_mismatch_rate',
            'movement_mismatch_rate',
            'context_divergence_rate',
            'predicted_move_rate',
            'projected_move_rate',
            'true_move_rate',
            'terminal',
          )
        }
  return p.seal(
    {
      'schema': 'V4_ATTRIBUTION_SUMMARY',
      'overall': overall,
      'folds': folds,
      'fold_patterns': patterns,
      'fold_opposition_supported': opposite,
      'structure': structure,
      'mechanism': mechanism,
      'mechanism_evidence': references,
      'historical_comparison': historical_comparison(),
      'selection_state': 'MODEL_SELECTION_FAILED_CLOSED',
      'selected_candidate': None,
      'scope': 'REPORT_ONLY',
      'execution_calls': ZERO,
    }
  )


def output_identity(output, roots, original):
  output = saved.safe(Path(output))
  require(output.parent == roots['actual'].parent and not output.exists(), 'V4_ATTRIBUTION_NEW_E_SIBLING_REQUIRED')
  require(all(not output.is_relative_to(x) and not x.is_relative_to(output) for x in roots.values()))
  mount = auth.prior.external.prove_authorized_external_volume(output, expected_mount=original['mount_identity_sha256'])
  auth.prior.external.check_live_volume(original['volume_identity_sha256'])
  # Fixed modest bound: 32 jobs * 1 MiB, two replicas, plus 32 MiB public/metadata margin.
  # Reserve reuses the actual frozen E policy; this is an aggregate-only analysis, not a new certificate run.
  allowance = (2 * 32 + 32) * 1024**2
  free = auth.prior.free_bytes(output.parent)
  reserve = original['resource_budget']['reserve_bytes']
  require(free >= allowance + reserve, 'V4_ATTRIBUTION_STORAGE_CAPACITY_FAILURE')
  return {
    'output_root_identity_sha256': p.sha(str(output).encode()),
    'mount_identity_sha256': mount['mount_identity_sha256'],
    'volume_identity_sha256': original['volume_identity_sha256'],
    'aggregate_upper_bytes': allowance,
    'reserve_bytes': reserve,
    'free_bytes_before': free,
  }


def enforce_identity(lock, *, head, environment, output, repository, branch, strict_head=True):
  require(not strict_head or head == lock['analysis_head'])
  require(environment == lock['environment'])
  require(repository == lock['repository'] and branch == lock['branch'])
  require(p.sha(str(saved.safe(Path(output))).encode()) == lock['storage']['output_root_identity_sha256'])


def validate_lock(output, *, strict_head=False):
  output = saved.safe(Path(output))
  lock = saved.read_json(output / 'input-lock.json')
  repository, branch = auth.repository_identity()
  head = auth.prior.current_head()
  enforce_identity(lock, head=head, environment=auth.prior.environment(), output=output, repository=repository, branch=branch, strict_head=strict_head)
  if not strict_head:
    require(subprocess.run(['git', 'merge-base', '--is-ancestor', lock['analysis_head'], head], cwd=p.PUBLIC.parents[2], check=False).returncode == 0)
  require(lock['analysis_sources'] == sources())
  require(saved.read_json(output / 'policy.json', lock['policy_sha256']) == policy())
  require(public_lock()[1] == lock['public_receipts'])
  auth.prior.external.prove_authorized_external_volume(output, expected_mount=lock['storage']['mount_identity_sha256'])
  auth.prior.external.check_live_volume(lock['storage']['volume_identity_sha256'])
  require(
    auth.prior.free_bytes(output) >= lock['storage']['aggregate_upper_bytes'] + lock['storage']['reserve_bytes'], 'V4_ATTRIBUTION_STORAGE_CAPACITY_FAILURE'
  )
  return lock


def prepare(*, metadata, actual, output):
  rows, public = public_lock()
  roots, original = resolve_roots(metadata, actual)
  storage = output_identity(output, roots, original)
  allowed_reads = admitted_read_files(roots, metadata)
  repository, branch = auth.repository_identity()
  with firewall(), access_guard([*roots.values(), metadata.parent], output, allowed_reads=allowed_reads, storage=storage):
    output.mkdir()
    write_json(output / 'policy.json', policy())
    admitted = admit(roots)
    identity = {
      'schema': 'V4_ATTRIBUTION_INPUT_LOCK',
      'baseline': BASELINE,
      'analysis_head': auth.prior.current_head(),
      'repository': repository,
      'branch': branch,
      'analysis_sources': sources(),
      'public_receipts': public,
      'execution_head': EXECUTION_HEAD,
      'authorization_sha256': AUTH_SHA,
      'actual_manifest_sha256': MANIFEST_SHA,
      'v1_manifest_sha256': saved.SOURCE_SHA,
      'snapshot': admitted['before'],
      'actual_repeatability': admitted['repeatability'],
      'integrity_array_files_per_replica': admitted['integrity_array_files_per_replica'],
      'integrity_array_decoding': admitted['integrity_array_decoding'],
      'policy_sha256': policy()['receipt_sha256'],
      'storage': storage,
      'storage_migration_receipt_sha256': original['storage_migration_receipt_sha256'],
      'storage_amendment_receipt_sha256': original['storage_amendment_receipt_sha256'],
      'environment': auth.prior.environment(),
      'scope': 'REPORT_ONLY',
      'execution_calls': ZERO,
    }
    lock = p.seal(identity)
    write_json(output / 'input-lock.json', lock)
  return lock


def analyze_inputs(roots, admitted, output):
  jobs = []
  for current, historical in zip(admitted['current_jobs'], admitted['historical_jobs'], strict=True):
    job = analyze_job(roots, admitted, current, historical)
    privacy(job)
    write_json(output / 'jobs' / job['candidate_id'] / job['fold'] / 'receipt.json', job)
    jobs.append(job)
    print(json.dumps({'job': job['candidate_id'], 'fold': job['fold'], 'status': 'ATTRIBUTED_FROM_SAVED_ONLY'}), flush=True)
  return jobs


def run(*, metadata, actual, output, replica):
  require(replica in ('repeat-1', 'repeat-2'))
  lock = validate_lock(output, strict_head=True)
  require(lock['analysis_sources'] == sources() and lock['policy_sha256'] == policy()['receipt_sha256'])
  _, current_public = public_lock()
  require(current_public == lock['public_receipts'])
  roots, original = resolve_roots(metadata, actual)
  auth.prior.external.prove_authorized_external_volume(output, expected_mount=lock['storage']['mount_identity_sha256'])
  auth.prior.external.check_live_volume(lock['storage']['volume_identity_sha256'])
  require(not (output / replica).exists())
  require(output.parent == roots['actual'].parent)
  require(all(not output.is_relative_to(x) and not x.is_relative_to(output) for x in roots.values()))
  allowed_reads = admitted_read_files(roots, metadata)
  with firewall(), access_guard([*roots.values(), metadata.parent], output, allowed_reads=allowed_reads, storage=lock['storage']):
    admitted = admit(roots)
    require(admitted['before'] == lock['snapshot'])
    jobs = analyze_inputs(roots, admitted, output / replica)
    summary = summarize(jobs)
    privacy(summary)
    write_json(output / replica / 'summary.json', summary)
    require(snapshots(roots) == lock['snapshot'])
    require(auth.sources() == original['executor_sources'] and sources() == lock['analysis_sources'])
    validate_lock(output, strict_head=True)
    manifest = finish_store(
      output / replica,
      {
        'policy_sha256': lock['policy_sha256'],
        'input_identity_sha256': lock['receipt_sha256'],
        'summary_sha256': summary['receipt_sha256'],
        'job_count': len(jobs),
        'source_immutability': 'PASS',
        'execution_calls': ZERO,
      },
    )
  return manifest


def verify_pair(output):
  lock = validate_lock(output)
  one = saved.read_json(output / 'repeat-1/manifest.json')
  two = saved.read_json(output / 'repeat-2/manifest.json')
  require(one == two, 'V4_ATTRIBUTION_REPEATABILITY_FAILURE')
  require(one['input_identity_sha256'] == lock['receipt_sha256'])
  require(one['policy_sha256'] == lock['policy_sha256'])
  resumes = {replica: resume(output / replica, one['receipt_sha256']) for replica in ('repeat-1', 'repeat-2')}
  repeated = p.seal(
    {
      'schema': 'V4_ATTRIBUTION_REPEATABILITY',
      'status': 'BYTE_EXACT_PASS',
      'manifest_sha256': one['receipt_sha256'],
      'input_identity_sha256': lock['receipt_sha256'],
      'replicas_retained': ['repeat-1', 'repeat-2'],
      'execution_calls': ZERO,
    }
  )
  resumed = p.seal({'schema': 'V4_ATTRIBUTION_RESUME', 'status': 'PASS', 'replicas': resumes, 'recompute_calls': 0})
  with access_guard([], output, storage=lock['storage']):
    write_json(output / 'repeatability.json', repeated)
    write_json(output / 'resume.json', resumed)
  return repeated, resumed


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('mode', choices=('prepare', 'repeat-1', 'repeat-2', 'verify'))
  parser.add_argument('--metadata', type=Path, required=True)
  parser.add_argument('--actual', type=Path, required=True)
  parser.add_argument('--output', type=Path, required=True)
  args = parser.parse_args()
  if args.mode == 'prepare':
    result = prepare(metadata=args.metadata, actual=args.actual, output=args.output)
  elif args.mode == 'verify':
    result = verify_pair(args.output)[0]
  else:
    result = run(metadata=args.metadata, actual=args.actual, output=args.output, replica=args.mode)
  print(json.dumps({'status': result.get('status', 'INPUT_LOCKED'), 'receipt_sha256': result['receipt_sha256']}), flush=True)


if __name__ == '__main__':
  main()
