"""V3 future-authorized executor. This module never mints an authorization."""

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import argparse
import json

import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_io as io
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_store as store
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_threshold as threshold
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_data as data
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_gates as gates
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_execution as prior

p = io.p
SUCCESS = 'HURDLE_STAGE1_DECISION_POLICY_V3_RETROSPECTIVE_EXECUTION_COMPLETE'


def anchor_identity(digest, count, historical):
  io.require(digest == historical['anchor_sha256'] and count == historical['count'], 'V3_ANCHOR_IDENTITY_CONFLICT')


def require_same_array(array, binding):
  io.require(array.dtype.str == binding['dtype'] and list(array.shape) == binding['shape']
             and io.legacy.old.array_digest(array) == binding['array_sha256'], 'V3_ANCHOR_IDENTITY_CONFLICT')


def source_reference(permit, job, name, receipt):
  return {'manifest_sha256': permit.authorization['v1_manifest_sha256'],
          'member': f"candidates/{job['candidate_id']}/{job['fold']}/{name}/receipt.json",
          'receipt_sha256': receipt['receipt_sha256'], 'arrays': receipt['arrays']}


def finalized(path, permit, historical):
  row = io.read_json(path / 'threshold/receipt.json')
  replica = path.relative_to(permit.roots['output']).parts[0]
  return io.require_finalized(permit, historical, row, replica)


def comparison_history(candidate, fold):
  """Public frozen V2 aggregates only, called after V3 decision finalization."""
  result = {'candidate_id': candidate, 'fold': fold}
  index = io.JOBS.index((candidate, fold))
  for name in ('train-results', 'development-results', 'rollout-results', 'candidate-gates'):
    body = io.read_json(p.PUBLIC / ('empirical-hurdle-stage1-v2-' + name + '.json'))
    io.require([(j['candidate_id'], j['fold']) for j in body['jobs']] == list(io.JOBS))
    result.update(body['jobs'][index])
  return result


def comparison(historical, job, train_v1=None):
  if job['threshold']['status'] != 'V3_THRESHOLD_FINALIZED':
    return {'authority': 'REPORT_ONLY', 'status': 'V3_DECISION_UNAVAILABLE', 'v3_metrics': None}
  v2 = comparison_history(job['candidate_id'], job['fold'])
  io.require((v2['candidate_id'], v2['fold']) == (job['candidate_id'], job['fold']))
  io.require(v2['train_count'] == historical['train_count'], 'V3_ANCHOR_IDENTITY_CONFLICT')
  report = {'authority': 'REPORT_ONLY', 'train': {'v1': train_v1, 'v2': v2.get('train_metrics'), 'v3': job.get('train_metrics')}}
  for key in ('one_step', 'true_move', 'stage1_diagnostics', 'rollout'):
    report[key] = {'v1': historical.get(key), 'v2': v2.get(key), 'v3': job.get(key)}
  for original in (historical, v2):
    for key in ('one_step', 'true_move'):
      if job.get(key) is not None:
        anchor_identity(job[key]['anchor_sha256'], job[key]['count'], original[key])
    for h, value in job['rollout'].items():
      for population in ('overall', 'path_moved'):
        if value.get(population) is not None:
          anchor_identity(value[population]['anchor_sha256'], value[population]['count'], original['rollout'][h][population])
  second = {c['id']: c['pass'] for c in job['gate']['clauses']}
  report['clauses'] = {}
  for label, original in (('v1', historical), ('v2', v2)):
    first = {c['id']: c['pass'] for c in original['gate']['clauses']}
    io.require(first.keys() == second.keys())
    report['clauses'][label] = {name: [key for key in first if (first[key], second[key]) == pair]
                              for name, pair in (('recovered', (False, True)), ('newly_failed', (True, False)),
                                                 ('unchanged_pass', (True, True)), ('unchanged_fail', (False, False)))}
  return report


def _execute_job(permit, historical, replica):
  prefix = io.job_checked(permit, historical)
  io.require(replica in ('repeat-1', 'repeat-2'))
  path = permit.roots['output'] / replica / prefix
  io.require(not path.exists(), 'V3_NO_PARTIAL_JOB_REUSE')
  candidate, fold = historical['candidate_id'], historical['fold']
  ref = io.reference(historical, permit.pack['references'][io.JOBS.index((candidate, fold))])
  models = {stage: io.load_model(permit, historical, stage) for stage in ('stage1', 'stage2')}
  train = io.load_route(permit, historical)
  blocks, anchor, x, current, target = data.design(train, candidate)
  io.require(anchor == historical['train_anchor_sha256'] and len(x) == historical['train_count'], 'V3_ANCHOR_IDENTITY_CONFLICT')
  move = target != current
  positives, negatives = int(np.count_nonzero(move)), int(np.count_nonzero(~move))
  io.require((positives, negatives) == (ref['positive_count'], ref['negative_count']), 'V3_REFERENCE_CONFLICT')
  io.require(min(positives, negatives) >= m.SUPPORT, 'V3_NUMERICAL_FAILURE_INSUFFICIENT_SUPPORT')
  original_train = io.population(permit, historical, 'train')
  for key, value in data.context(blocks, candidate).items():
    require_same_array(value, original_train['arrays'][key])
  require_same_array((target - current).astype(np.float64), original_train['arrays']['actual_delta_tick'])
  for stage, population in (('stage1', x), ('stage2', np.ascontiguousarray(x[move]))):
    io.require(io.legacy.old.array_digest(m.transform(population, models[stage]['normalizer'])) == models[stage]['effective_x_sha256'],
               'V3_MODEL_IDENTITY_CONFLICT')
  probability = m.probability(x, models['stage1'])
  original_threshold = io.population(permit, historical, 'threshold')
  saved = original_threshold['arrays'].get('train_probability')
  if saved is not None:
    value = io.source_array(permit, historical, 'threshold', original_threshold, 'train_probability')
    io.require(value.dtype == probability.dtype and value.shape == probability.shape and value.tobytes() == probability.tobytes(),
               'V3_STAGE1_PREDICTION_IDENTITY_FAILURE')
    del value
  branch_delta = m.predict_delta(x, models['stage2'])  # ALL TRAIN; true STATIC included.
  result = threshold.sweep(probability, branch_delta, current, target, reference_tp=ref['reference_tp'], role='TRAIN')
  decision = p.seal({'schema': 'V3_PRIVATE_THRESHOLD_RECEIPT', 'candidate_id': candidate, 'fold': fold,
                     'authorization_sha256': permit.trusted_sha256, 'train_anchor_sha256': anchor,
                     'reference': ref, 'model_receipts': historical['stage1']['model_receipt_sha256'] + ':' + historical['stage2']['model_receipt_sha256'],
                     'probability_sha256': io.legacy.old.array_digest(probability), 'stage2_all_train_sha256': io.legacy.old.array_digest(branch_delta),
                     'saved_probability_comparison': 'BYTE_EXACT_PASS' if saved is not None else 'UNAVAILABLE',
                     'threshold_bytes_sha256': p.sha(np.array([result['threshold']], np.float64).tobytes()) if result['threshold'] is not None else None,
                     **result})
  store.write_json(path / 'threshold/receipt.json', decision)
  public_threshold = {k: decision[k] for k in ('status', 'candidate_count', 'feasible_count', 'objective', 'canonical_checks',
                                               'receipt_sha256', 'probability_sha256', 'stage2_all_train_sha256', 'saved_probability_comparison')}
  job = {'schema': 'V3_FOLD_RESULT', 'candidate_id': candidate, 'fold': fold, 'authorization_sha256': permit.trusted_sha256,
         'status': 'EXECUTED_COMPLETE', 'failures': [], 'train_anchor_sha256': anchor, 'train_count': len(x),
         'models': {stage: historical[stage] for stage in ('stage1', 'stage2')}, 'reference': ref, 'threshold': public_threshold,
         'rollout': {}, 'populations': {}, 'train_metrics': None}
  train_v1 = None
  if result['threshold'] is None:
    job['status'], job['failures'] = 'NO_FEASIBLE_THRESHOLD', [threshold.NO_FEASIBLE]
  else:
    decision = finalized(path, permit, historical)
    value = decision['threshold']
    metrics, gate, projected = prior.train_report(probability, branch_delta, current, target, value)
    job['train_metrics'] = metrics
    receipt = store.population(path / 'train', {'predicted_gate': gate, 'projected_next_tick': io.legacy.compact_ticks(projected)},
                               {'schema': 'V3_TRAIN_EVIDENCE', 'population': 'train', 'anchor_sha256': anchor,
                                'threshold_sha256': decision['receipt_sha256'],
                                'source_reference': source_reference(permit, historical, 'train', original_train),
                                'probability_sha256': decision['probability_sha256'], 'stage2_all_train_sha256': decision['stage2_all_train_sha256'],
                                'metrics': metrics})
    job['populations']['train'] = receipt['receipt_sha256']
    # Historical V1 value is report-only, and is read only after V3 finalization.
    v1_value = io.source_array(permit, historical, 'threshold', original_threshold, 'threshold', decision=decision, replica=replica)[0]
    train_v1, _, _ = prior.train_report(probability, branch_delta, current, target, v1_value)
    del train, blocks, x, current, target, probability, branch_delta, gate, projected
    finalized(path, permit, historical)
    development = io.load_route(permit, historical, development=True, threshold_receipt=decision, replica=replica)
    _, digest, count = data.binding(development, candidate, 1)
    anchor_identity(digest, count, historical['one_step'])
    try:
      metrics, arrays = data.one_step(development, candidate, models['stage1'], value, models['stage2'])
      job.update(metrics)
      original = io.population(permit, historical, 'one-step')
      for key in ('current_tick', 'target_next_tick', 'actual_delta_tick', 'comparator_error', 'true_move', 'anchor_index'):
        require_same_array(arrays[key], original['arrays'][key])
      payload = {key: arrays[key] for key in ('p_move', 'predicted_gate', 'integrated_delta', 'candidate_error')}
      payload['projected_next_tick'] = io.legacy.compact_ticks(arrays['projected_next_tick'])
      receipt = store.population(path / 'one-step', payload,
                                 {'schema': 'V3_DEVELOPMENT_EVIDENCE', 'population': 'one-step', 'anchor_sha256': digest,
                                  'source_reference': source_reference(permit, historical, 'one-step', original),
                                  'threshold_sha256': decision['receipt_sha256']})
      job['populations']['one-step'] = receipt['receipt_sha256']
      if metrics['stage2_oracle']['failure'] is not None or metrics['stage1_diagnostics']['status'] != 'DEFINED':
        job['failures'].append('V3_DEVELOPMENT_DIAGNOSTIC_FAILURE')
        job['status'] = 'DEVELOPMENT_FAILURE'
      del arrays, payload
    except (ValueError, FloatingPointError) as exc:
      numerical_failure(exc, job, 'DEVELOPMENT_FAILURE')
    for horizon in m.HORIZONS:
      _, digest, count = data.binding(development, candidate, horizon)
      anchor_identity(digest, count, historical['rollout'][str(horizon)]['overall'])
      try:
        metrics, arrays = data.rollout(development, candidate, models['stage1'], value, models['stage2'], horizon)
        original = io.population(permit, historical, f'rollout-{horizon}')
        for key in ('observed_path', 'hold_last_path', 'comparator_error', 'path_moved', 'anchor_index'):
          require_same_array(arrays[key], original['arrays'][key])
        payload = {'projected_path': io.legacy.compact_ticks(arrays['projected_path']), 'predicted_gate_path': arrays['predicted_gate_path'],
                   'candidate_error': arrays['candidate_error']}
        receipt = store.population(path / f'rollout-{horizon}', payload,
                                   {'schema': 'V3_ROLLOUT_EVIDENCE', 'population': f'rollout-{horizon}', 'anchor_sha256': digest,
                                    'source_reference': source_reference(permit, historical, f'rollout-{horizon}', original),
                                    'threshold_sha256': decision['receipt_sha256']})
        job['populations'][f'rollout-{horizon}'] = receipt['receipt_sha256']
        job['rollout'][str(horizon)] = metrics
        if metrics['status'] != 'COMPLETE':
          job['status'] = 'ROLLOUT_FAILURE'
          job['failures'].append('V3_NUMERICAL_FAILURE_INSUFFICIENT_SUPPORT')
        del arrays, payload
      except (ValueError, FloatingPointError) as exc:
        numerical_failure(exc, job, 'ROLLOUT_FAILURE')
  job['gate'] = gates.fold_gate(job, permit.pack['clauses'])
  job['comparison'] = comparison(historical, job, train_v1)
  receipt = p.seal(job)
  store.write_json(path / 'receipt.json', receipt)
  store.finish(path, {'schema': 'V3_JOB_MANIFEST', 'job_receipt_sha256': receipt['receipt_sha256']})
  return receipt


def numerical_failure(exc, job, status):
  if not any(token in str(exc) for token in ('NUMERICAL', 'NONFINITE', 'SIGNED16', 'INSUFFICIENT_SUPPORT', 'SUPPORT_INSUFFICIENT', 'INVALID_PROBABILITY')):
    raise exc
  job['status'] = status
  job['failures'].append('V3_NUMERICAL_FAILURE')


def execute_job(permit, historical, replica):
  io.job_checked(permit, historical)
  try:
    return _execute_job(permit, historical, replica)
  except (ValueError, FloatingPointError) as exc:
    if not any(token in str(exc) for token in ('NUMERICAL', 'NONFINITE', 'SIGNED16', 'INSUFFICIENT_SUPPORT', 'SUPPORT_INSUFFICIENT', 'INVALID_PROBABILITY')):
      raise
    path = permit.roots['output'] / replica / io.job_checked(permit, historical)
    decision_path = path / 'threshold/receipt.json'
    if not decision_path.exists():
      store.write_json(decision_path, p.seal({'schema': 'V3_PRIVATE_THRESHOLD_RECEIPT', 'candidate_id': historical['candidate_id'], 'fold': historical['fold'],
                                             'authorization_sha256': permit.trusted_sha256, 'train_anchor_sha256': historical['train_anchor_sha256'],
                                             'status': 'V3_NUMERICAL_FAILURE', 'threshold': None, 'candidate_count': 0, 'feasible_count': 0,
                                             'objective': None, 'canonical_checks': 0}))
    decision = io.read_json(decision_path)
    populations = {name: io.read_json(path / name / 'receipt.json')['receipt_sha256']
                   for name in ('train', 'one-step', *(f'rollout-{h}' for h in m.HORIZONS)) if (path / name / 'receipt.json').exists()}
    job = {'schema': 'V3_FOLD_RESULT', 'candidate_id': historical['candidate_id'], 'fold': historical['fold'], 'authorization_sha256': permit.trusted_sha256,
           'status': 'NUMERICAL_FAILURE', 'failures': ['V3_NUMERICAL_FAILURE'], 'train_anchor_sha256': historical['train_anchor_sha256'],
           'train_count': historical['train_count'], 'models': {s: historical[s] for s in ('stage1', 'stage2')},
           'reference': permit.pack['references'][io.JOBS.index((historical['candidate_id'], historical['fold']))],
           'threshold': {k: decision[k] for k in ('status', 'candidate_count', 'feasible_count', 'objective', 'canonical_checks', 'receipt_sha256')},
           'rollout': {}, 'populations': populations, 'train_metrics': None}
    job['gate'] = gates.fold_gate(job, permit.pack['clauses'])
    job['comparison'] = {'authority': 'REPORT_ONLY', 'status': 'NUMERICAL_FAILURE'}
    row = p.seal(job)
    store.write_json(path / 'receipt.json', row)
    store.finish(path, {'schema': 'V3_JOB_MANIFEST', 'job_receipt_sha256': row['receipt_sha256']})
    return row


def select(jobs, clauses):
  selected = gates.select(jobs, clauses)
  selected['status'] = selected['status'].replace('HURDLE_', 'HURDLE_STAGE1_V3_', 1)
  selected['states'] = [s.replace('HURDLE_', 'HURDLE_STAGE1_V3_', 1) if s.startswith('HURDLE_') else s for s in selected['states']]
  return p.seal({'schema': 'V3_SELECTION_RESULT', **selected})


def run(*, authorization, authorization_sha256, replica, **roots):
  permit = io.preflight(authorization=authorization, authorization_sha256=authorization_sha256, **roots)
  io.permit_valid(permit)
  io.require(replica in ('repeat-1', 'repeat-2'))
  io.require([(j['candidate_id'], j['fold']) for j in permit.jobs] == list(io.JOBS), 'V3_ANCHOR_IDENTITY_CONFLICT')
  root = permit.roots['output'] / replica
  io.require(not root.exists(), 'V3_CLEAN_INDEPENDENT_RUN_REQUIRED')
  store.ensure_json(permit.roots['output'] / 'authorization.json', permit.authorization)
  binding = p.seal({'schema': 'V3_EXECUTION_BINDINGS', 'policies': permit.pack['receipts'], 'clauses': permit.pack['clauses'],
                    'reference_rows': permit.pack['references'], 'job_order': [list(j) for j in io.JOBS],
                    'gate_policy_sha256': io.legacy.old.PINS['acceptance-gate'], 'selection_policy_sha256': io.legacy.old.PINS['selection-rule']})
  store.write_json(root / 'bindings.json', binding)
  with io.firewall():
    jobs = [execute_job(permit, original, replica) for original in permit.jobs]
    selected = select(jobs, permit.pack['clauses'])
  result = p.seal({'schema': 'V3_RESULTS', 'authorization_sha256': permit.trusted_sha256, 'job_count': 32, 'jobs': jobs,
                   'selection_sha256': selected['receipt_sha256'], 'bindings_sha256': binding['receipt_sha256'],
                   'stage1_refit_calls': 0, 'stage2_refit_calls': 0, 'normalizer_refit_calls': 0,
                   'raw_log_openings': 0, 'qlog_openings': 0, 'holdout_openings': 0, 'vehicle_authority': 'NONE'})
  store.write_json(root / 'selection.json', selected)
  store.write_json(root / 'results.json', result)
  io.verify_source_immutability(permit)
  return store.finish(root, {'schema': 'V3_RUN_MANIFEST', 'status': SUCCESS, 'authorization_sha256': permit.trusted_sha256,
                             'job_count': 32, 'results_sha256': result['receipt_sha256'], 'selection_sha256': selected['receipt_sha256'],
                             'bindings_sha256': binding['receipt_sha256'], 'source_bytes_unchanged': True})


def resume(root, authorization_sha256, manifest_sha256):
  """Own-store verification only. Trusted returned manifest identity is required."""
  try:
    root = io.safe(Path(root))
    io.require(all(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)
                   for value in (authorization_sha256, manifest_sha256)))
    manifest = io.read_json(root / 'manifest.json', manifest_sha256)
    io.require(manifest['receipt_sha256'] == manifest_sha256 and manifest['authorization_sha256'] == authorization_sha256)
    io.require(manifest['schema'] == 'V3_RUN_MANIFEST' and manifest['status'] == SUCCESS and manifest['job_count'] == 32)
    auth = io.read_json(root.parent / 'authorization.json', authorization_sha256)
    io.require(auth['root_identities']['output'] == p.sha(str(root.parent).encode()))
    io.require(store.verify_manifest(root) == manifest)
    bindings = io.read_json(root / 'bindings.json', manifest['bindings_sha256'])
    result = io.read_json(root / 'results.json', manifest['results_sha256'])
    selected = io.read_json(root / 'selection.json', manifest['selection_sha256'])
    io.require(result['authorization_sha256'] == authorization_sha256 and result['job_count'] == 32)
    io.require(result['selection_sha256'] == selected['receipt_sha256'] and result['bindings_sha256'] == bindings['receipt_sha256'])
    io.require(bindings['job_order'] == [list(j) for j in io.JOBS] and len(bindings['clauses']) == 32)
    io.require(bindings['gate_policy_sha256'] == io.legacy.old.PINS['acceptance-gate']
               and bindings['selection_policy_sha256'] == io.legacy.old.PINS['selection-rule'])
    io.require([(j['candidate_id'], j['fold']) for j in result['jobs']] == list(io.JOBS))
    ids = [c['id'] for c in bindings['clauses']]
    for number, job in enumerate(result['jobs']):
      local = root / 'candidates' / job['candidate_id'] / job['fold']
      job_manifest = store.verify_manifest(local)
      io.require(job_manifest['schema'] == 'V3_JOB_MANIFEST' and job_manifest['job_receipt_sha256'] == job['receipt_sha256'])
      io.require(io.read_json(local / 'receipt.json', job['receipt_sha256']) == job)
      io.require(job['authorization_sha256'] == authorization_sha256 and job['reference'] == bindings['reference_rows'][number])
      io.require([c['id'] for c in job['gate']['clauses']] == ids)
      decision = io.read_json(local / 'threshold/receipt.json', job['threshold']['receipt_sha256'])
      io.require(decision['authorization_sha256'] == authorization_sha256 and decision['train_anchor_sha256'] == job['train_anchor_sha256'])
      expected = {'train', 'one-step', *(f'rollout-{h}' for h in m.HORIZONS)} if job['status'] == 'EXECUTED_COMPLETE' else set(job['populations'])
      io.require(set(job['populations']) == expected)
      for name, sha in job['populations'].items():
        io.require(name in {'train', 'one-step', *(f'rollout-{h}' for h in m.HORIZONS)})
        population = io.read_json(local / name / 'receipt.json', sha)
        io.require(population['threshold_sha256'] == decision['receipt_sha256'])
        store.verify_population(local / name, population)
    return manifest
  except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
    raise ValueError('V3_RESUME_INTEGRITY_FAILURE') from exc


def trapped_resume(root, authorization_sha256, manifest_sha256):
  with ExitStack() as stack:
    for module, names in (
      (io, ('preflight', 'admit_metadata', 'load_model', 'load_route', 'population', 'source_array', 'decode_bound_array', 'environment')),
      (m, ('probability', 'predict_delta', 'integrated', 'project', 'recursive', 'metrics')),
      (data, ('design', 'one_step', 'rollout', 'binding')),
      (threshold, ('sweep', '_sweep', 'canonical')),
      (gates, ('select', 'fold_gate', 'selection_key')),
      (io.legacy.old.read, ('read_array',)),
    ):
      for name in names:
        stack.enter_context(patch.object(module, name, io.legacy.forbidden))
    with io.firewall():
      return resume(root, authorization_sha256, manifest_sha256)


def repeatability(output, authorization_sha256, run1_sha256, run2_sha256):
  output = io.safe(Path(output))
  try:
    first = trapped_resume(output / 'repeat-1', authorization_sha256, run1_sha256)
    second = trapped_resume(output / 'repeat-2', authorization_sha256, run2_sha256)
    io.require(first == second)
  except (ValueError, OSError) as exc:
    store.ensure_json(output / 'repeatability-failure.json', p.seal({'schema': 'V3_REPEATABILITY_FAILURE', 'status': 'V3_REPEATABILITY_FAILURE',
                                                                   'selected_candidate': None, 'run2_scratch_retained': True}))
    raise ValueError('V3_REPEATABILITY_FAILURE') from exc
  result = p.seal({'schema': 'V3_REPEATABILITY', 'status': 'V3_EXACT_REPEATABILITY_PASS', 'authorization_sha256': authorization_sha256,
                   'run1_manifest_sha256': first['receipt_sha256'], 'run2_manifest_sha256': second['receipt_sha256'],
                   'file_count': len(first['files']), 'all_file_content_decoded_hashes_equal': True, 'resume': 'V3_VERIFY_ONLY_RESUME_PASS',
                   'run2_scratch_retained': True})
  store.ensure_json(output / 'repeat-2-manifest.json', second)
  store.ensure_json(output / 'repeat-2-receipt.json', p.seal({'schema': 'V3_RUN2_DURABLE_RECEIPT', 'run_manifest_sha256': second['receipt_sha256'],
                                                           'result_sha256': second['results_sha256'], 'selection_sha256': second['selection_sha256']}))
  store.ensure_json(output / 'comparison-manifest.json', p.seal({'schema': 'V3_EXACT_FILE_EQUALITY', 'files': first['files'],
                                                               'run1_manifest_sha256': run1_sha256, 'run2_manifest_sha256': run2_sha256}))
  store.ensure_json(output / 'repeatability.json', result)
  return result


def cleanup_eligibility(output, authorization_sha256, run1_sha256, run2_sha256, source_roots):
  """Verify eligibility only. This module performs no scratch deletion."""
  output = io.safe(Path(output))
  io.prove_d(output)
  auth = io.read_json(output / 'authorization.json', authorization_sha256)
  io.require(set(source_roots) == {'source', 'causal', 'derived'}, 'V3_OUTPUT_ROOT_INVALID')
  scratch = io.safe(output / 'repeat-2')
  io.reject_mount_aliases(scratch)
  io.require(scratch.is_dir() and scratch.parent == output, 'V3_OUTPUT_ROOT_INVALID')
  for key, path in source_roots.items():
    root = io.safe(Path(path))
    io.reject_mount_aliases(root)
    io.require(p.sha(str(root).encode()) == auth['root_identities'][key], 'V3_OUTPUT_ROOT_INVALID')
    io.require(not scratch.is_relative_to(root) and not root.is_relative_to(scratch), 'V3_OUTPUT_ROOT_INVALID')
    io.require(not any(a.exists() and b.exists() and a.samefile(b) for a in (scratch, *scratch.parents) for b in (root,)),
               'V3_OUTPUT_ROOT_INVALID')
  first = trapped_resume(output / 'repeat-1', authorization_sha256, run1_sha256)
  second = trapped_resume(scratch, authorization_sha256, run2_sha256)
  io.require(first == second, 'V3_REPEATABILITY_FAILURE')
  repeated = io.read_json(output / 'repeatability.json')
  comparison = io.read_json(output / 'comparison-manifest.json')
  receipt = io.read_json(output / 'repeat-2-receipt.json')
  io.require(repeated['status'] == 'V3_EXACT_REPEATABILITY_PASS'
             and repeated['run1_manifest_sha256'] == run1_sha256 and repeated['run2_manifest_sha256'] == run2_sha256
             and comparison['files'] == first['files'] and io.read_json(output / 'repeat-2-manifest.json') == second
             and receipt['run_manifest_sha256'] == run2_sha256 and receipt['result_sha256'] == second['results_sha256']
             and receipt['selection_sha256'] == second['selection_sha256'], 'V3_REPEATABILITY_FAILURE')
  return p.seal({'schema': 'V3_SCRATCH_CLEANUP_ELIGIBILITY', 'eligible': True, 'deletion_performed': False,
                 'equality_sha256': comparison['receipt_sha256'], 'repeatability_sha256': repeated['receipt_sha256'],
                 'scratch_root_sha256': p.sha(str(scratch).encode())})


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--action', choices=('run', 'resume', 'repeatability'), required=True)
  parser.add_argument('--authorization', type=Path)
  parser.add_argument('--authorization-sha256', required=True)
  parser.add_argument('--source-root', type=Path)
  parser.add_argument('--causal-root', type=Path)
  parser.add_argument('--derived-root', type=Path)
  parser.add_argument('--output-root', required=True, type=Path)
  parser.add_argument('--replica', choices=('repeat-1', 'repeat-2'))
  parser.add_argument('--manifest-sha256')
  parser.add_argument('--run2-manifest-sha256')
  args = parser.parse_args()
  if args.action == 'run':
    # Only a caller-provided sealed JSON document is accepted. There is no
    # authorize command, implicit path, receipt self-trust or automatic run.
    if args.replica is None:
      parser.error('--replica is required for run')
    value = run(authorization=args.authorization, authorization_sha256=args.authorization_sha256, replica=args.replica,
                source_root=args.source_root, causal_root=args.causal_root, derived_root=args.derived_root, output_root=args.output_root)
  elif args.action == 'resume':
    if args.replica is None or args.manifest_sha256 is None:
      parser.error('--replica and --manifest-sha256 are required for resume')
    value = trapped_resume(args.output_root / args.replica, args.authorization_sha256, args.manifest_sha256)
  else:
    value = repeatability(args.output_root, args.authorization_sha256, args.manifest_sha256, args.run2_manifest_sha256)
  print(json.dumps({'status': value['status'], 'receipt_sha256': value['receipt_sha256']}))


if __name__ == '__main__':
  main()
