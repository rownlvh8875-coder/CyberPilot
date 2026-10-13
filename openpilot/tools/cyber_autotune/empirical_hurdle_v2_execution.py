"""Authorized retrospective V2 replay. Fitted V1 models are immutable inputs."""

import argparse
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import json

import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_io as io
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_threshold as threshold
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_data as data
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_gates as gates

SUCCESS = 'HURDLE_STAGE1_DECISION_POLICY_V2_RETROSPECTIVE_EXECUTION_COMPLETE'


def require_same_array(array, binding):
  io.require(
    array.dtype.str == binding['dtype'] and list(array.shape) == binding['shape'] and io.old.array_digest(array) == binding['array_sha256'],
    'V2_SOURCE_IDENTITY_CONFLICT',
  )


def anchor_identity(digest, count, historical):
  io.require(digest == historical['anchor_sha256'] and count == historical['count'], 'V2_SOURCE_ANCHOR_IDENTITY_CONFLICT')


def train_report(probability, delta, current, target, value):
  gate = probability > value
  final_delta = np.zeros(len(gate), dtype=np.float64)
  final_delta[gate] = delta[gate]
  projected = current.copy()
  projected[gate] = m.project(current[gate].astype(np.float64) + delta[gate])
  truth = target - current
  move = truth != 0
  error = final_delta - truth.astype(np.float64)
  diagnostic = m.diagnostics(move, gate)
  return (
    {
      'all': m.metrics(error, projected, target),
      'true_move': m.metrics(error[move]),
      'stage1': diagnostic,
      'predicted_move_fraction': float(gate.mean()),
      'static_projected_false_move_count': int(np.count_nonzero(~move & (projected != current))),
    },
    gate,
    projected,
  )


def finalized(path, auth, historical):
  receipt = io.read_json(path / 'threshold/receipt.json')
  io.require(
    receipt['authorization_sha256'] == auth['receipt_sha256']
    and receipt['train_anchor_sha256'] == historical['train_anchor_sha256']
    and receipt['status'] == 'V2_THRESHOLD_FINALIZED',
    'V2_THRESHOLD_FINALIZATION_REQUIRED',
  )
  return receipt


def compare(historical, current):
  keys = ('one_step', 'true_move', 'stage1_diagnostics', 'static_diagnostics', 'rollout')
  report = {key: {'v1': historical.get(key), 'v2': current.get(key)} for key in keys}
  for key in ('one_step', 'true_move'):
    if current.get(key) is not None:
      anchor_identity(current[key]['anchor_sha256'], current[key]['count'], historical[key])
  for h, value in current['rollout'].items():
    for population in ('overall', 'path_moved'):
      if value.get(population) is not None:
        anchor_identity(value[population]['anchor_sha256'], value[population]['count'], historical['rollout'][h][population])
  first = {c['id']: c['pass'] for c in historical['gate']['clauses']}
  second = {c['id']: c['pass'] for c in current['gate']['clauses']}
  io.require(first.keys() == second.keys(), 'V2_COMPARISON_CLAUSE_CONFLICT')
  report['clauses'] = {
    name: [key for key in first if (first[key], second[key]) == pair]
    for name, pair in (('recovered', (False, True)), ('newly_failed', (True, False)), ('unchanged_pass', (True, True)), ('unchanged_fail', (False, False)))
  }
  report['authority'] = 'REPORT_ONLY'
  return report


def _execute_job(run_root, source, historical, records, auth, clauses):
  candidate, fold = historical['candidate_id'], historical['fold']
  path = run_root / 'candidates' / candidate / fold
  source_job = source / 'repeat-1/candidates' / candidate / fold
  io.require(not path.exists(), 'V2_NO_PARTIAL_JOB_REUSE')
  stage1 = io.load_model(source_job, 'stage1', historical['stage1'], auth)
  stage2 = io.load_model(source_job, 'stage2', historical['stage2'], auth)
  train = io.load_route(records, historical['train_route'], auth)
  blocks, anchor, x, current, target = data.design(train, candidate)
  io.require(anchor == historical['train_anchor_sha256'] and len(x) == historical['train_count'], 'V2_SOURCE_ANCHOR_IDENTITY_CONFLICT')
  original_train = io.read_json(source_job / 'train/receipt.json', historical['population_receipts']['train'])
  context = data.context(blocks, candidate)
  for key, value in context.items():
    require_same_array(value, original_train['arrays'][key])
  require_same_array((target - current).astype(np.float64), original_train['arrays']['actual_delta_tick'])
  io.require(np.count_nonzero(target != current) == historical['train_move_count'])
  for model, population in ((stage1, x), (stage2, np.ascontiguousarray(x[target != current]))):
    io.require(io.old.array_digest(m.transform(population, model['normalizer'])) == model['effective_x_sha256'], 'V2_TRAIN_FEATURE_IDENTITY_CONFLICT')
  probability = m.probability(x, stage1)
  # Read only the probability array here. Historical threshold is not an input
  # to selection; its numeric field is used only after finalization below.
  original_threshold = io.read_json(source_job / 'threshold/receipt.json', historical['threshold']['receipt_sha256'])
  saved_binding = original_threshold['arrays'].get('train_probability')
  if saved_binding is not None:
    saved = io.verified.load_array(source_job / 'threshold', original_threshold, 'train_probability')
    io.require(
      saved.dtype == probability.dtype and saved.shape == probability.shape and saved.tobytes() == probability.tobytes(),
      'V2_STAGE1_TRAIN_PREDICTION_IDENTITY_FAILURE',
    )
    del saved
  branch_delta = m.predict_delta(x, stage2)  # ALL TRAIN, including STATIC.
  result = threshold.sweep(probability, branch_delta, current, target, role='TRAIN')
  private = p.seal(
    {
      'schema': 'HURDLE_STAGE1_V2_PRIVATE_THRESHOLD_RECEIPT',
      'candidate_id': candidate,
      'fold': fold,
      'authorization_sha256': auth['receipt_sha256'],
      'train_anchor_sha256': anchor,
      'stage1_model_sha256': historical['stage1']['model_receipt_sha256'],
      'stage2_model_sha256': historical['stage2']['model_receipt_sha256'],
      'probability_sha256': io.old.array_digest(probability),
      'stage2_all_train_sha256': io.old.array_digest(branch_delta),
      'saved_probability_comparison': 'BYTE_EXACT_PASS' if saved_binding is not None else 'UNAVAILABLE',
      'execution_policy_sha256': io.POLICY_SHA,
      **result,
    }
  )
  io.write_json(path / 'threshold/receipt.json', private)
  public_threshold = {k: result[k] for k in ('status', 'candidate_count', 'feasible_count', 'objective', 'canonical_checks')}
  public_threshold.update(
    receipt_sha256=private['receipt_sha256'],
    probability_sha256=private['probability_sha256'],
    stage2_all_train_sha256=private['stage2_all_train_sha256'],
    saved_probability_comparison=private['saved_probability_comparison'],
  )
  job = {
    'schema': 'HURDLE_STAGE1_V2_FOLD_RESULT',
    'candidate_id': candidate,
    'fold': fold,
    'authorization_sha256': auth['receipt_sha256'],
    'status': 'EXECUTED_COMPLETE',
    'failures': [],
    'train_anchor_sha256': anchor,
    'train_count': len(x),
    'models': {s: historical[s] for s in ('stage1', 'stage2')},
    'threshold': public_threshold,
    'rollout': {},
    'populations': {},
    'train_comparison': None,
  }
  if result['threshold'] is None:
    job['status'] = 'NO_FEASIBLE_THRESHOLD'
    job['failures'].append(threshold.NO_FEASIBLE)
  else:
    finalized(path, auth, historical)
    value = result['threshold']
    train_metrics, train_gate, train_projected = train_report(probability, branch_delta, current, target, value)
    stored = io.population(
      path / 'train',
      {'predicted_gate': train_gate, 'projected_next_tick': io.compact_ticks(train_projected)},
      {
        'schema': 'V2_TRAIN_EVIDENCE',
        'threshold_sha256': private['receipt_sha256'],
        'anchor_sha256': anchor,
        'source_reference': io.reference(historical, 'train', original_train),
        'probability_sha256': private['probability_sha256'],
        'stage2_all_train_sha256': private['stage2_all_train_sha256'],
        'metrics': train_metrics,
      },
    )
    job['populations']['train'] = stored['receipt_sha256']
    job['train_metrics'] = train_metrics
    # V1 report only, after V2 immutable finalization.
    v1_value = io.verified.load_array(source_job / 'threshold', original_threshold, 'threshold')[0]
    v1_metrics, _, _ = train_report(probability, branch_delta, current, target, v1_value)
    job['train_comparison'] = {
      'authority': 'REPORT_ONLY',
      'v1': v1_metrics,
      'v2': train_metrics,
      'v1_threshold_receipt_sha256': original_threshold['receipt_sha256'],
      'v2_threshold_receipt_sha256': private['receipt_sha256'],
    }
    del train, x, blocks, context, probability, branch_delta, current, target, train_gate, train_projected
    # The only numerical DEVELOPMENT loader follows durable finalization.
    finalized(path, auth, historical)
    development = io.load_route(records, historical['development_route'], auth)
    _, digest, count = data.binding(development, candidate, 1)
    anchor_identity(digest, count, historical['one_step'])
    try:
      metrics, arrays = data.one_step(development, candidate, stage1, value, stage2)
      job.update(metrics)
      original = io.read_json(source_job / 'one-step/receipt.json', historical['population_receipts']['one-step'])
      for key in ('current_tick', 'target_next_tick', 'actual_delta_tick', 'comparator_error', 'true_move', 'anchor_index'):
        require_same_array(arrays[key], original['arrays'][key])
      payload = {key: arrays[key] for key in ('p_move', 'predicted_gate', 'integrated_delta', 'candidate_error')}
      payload['projected_next_tick'] = io.compact_ticks(arrays['projected_next_tick'])
      receipt = io.population(
        path / 'one-step',
        payload,
        {
          'schema': 'V2_DEVELOPMENT_EVIDENCE',
          'anchor_sha256': digest,
          'source_reference': io.reference(historical, 'one-step', original),
          'threshold_sha256': private['receipt_sha256'],
        },
      )
      job['populations']['one-step'] = receipt['receipt_sha256']
      del arrays, payload
      if metrics['stage2_oracle']['failure'] is not None:
        job['failures'].append(metrics['stage2_oracle']['failure'])
        job['status'] = 'DEVELOPMENT_FAILURE'
      if metrics['stage1_diagnostics']['status'] != 'DEFINED':
        job['failures'].append('STAGE1_DIAGNOSTIC_UNDEFINED')
        job['status'] = 'DEVELOPMENT_FAILURE'
    except (ValueError, FloatingPointError) as exc:
      numerical_failure(exc, job, 'DEVELOPMENT_FAILURE')
    # Performance or diagnostic failure does not short-circuit valid rollouts.
    for horizon in m.HORIZONS:
      _, digest, count = data.binding(development, candidate, horizon)
      anchor_identity(digest, count, historical['rollout'][str(horizon)]['overall'])
      try:
        metrics, arrays = data.rollout(development, candidate, stage1, value, stage2, horizon)
        original = io.read_json(source_job / f'rollout-{horizon}/receipt.json', historical['population_receipts'][f'rollout-{horizon}'])
        for key in ('observed_path', 'hold_last_path', 'comparator_error', 'path_moved', 'anchor_index'):
          require_same_array(arrays[key], original['arrays'][key])
        payload = {
          'projected_path': io.compact_ticks(arrays['projected_path']),
          'predicted_gate_path': arrays['predicted_gate_path'],
          'candidate_error': arrays['candidate_error'],
        }
        receipt = io.population(
          path / f'rollout-{horizon}',
          payload,
          {
            'schema': 'V2_ROLLOUT_EVIDENCE',
            'anchor_sha256': digest,
            'source_reference': io.reference(historical, f'rollout-{horizon}', original),
            'threshold_sha256': private['receipt_sha256'],
          },
        )
        job['populations'][f'rollout-{horizon}'] = receipt['receipt_sha256']
        job['rollout'][str(horizon)] = metrics
        if metrics['status'] != 'COMPLETE':
          job['failures'].append('HURDLE_ROLLOUT_SUPPORT_INSUFFICIENT')
          job['status'] = 'ROLLOUT_FAILURE'
        del arrays, payload
      except (ValueError, FloatingPointError) as exc:
        numerical_failure(exc, job, 'ROLLOUT_FAILURE')
  job['gate'] = gates.fold_gate(job, clauses)
  job['comparison'] = compare(historical, job)
  receipt = p.seal(job)
  io.write_json(path / 'receipt.json', receipt)
  names = [f.relative_to(path).as_posix() for f in path.rglob('*') if f.is_file()]
  io.old.finish(path, names, {'schema': 'V2_JOB_MANIFEST', 'receipt_sha256_binding': receipt['receipt_sha256']})
  return receipt


def execute_job(run_root, source, historical, records, auth, clauses):
  try:
    return _execute_job(run_root, source, historical, records, auth, clauses)
  except (ValueError, FloatingPointError) as exc:
    if not any(token in str(exc) for token in ('NUMERICAL', 'NONFINITE', 'SIGNED16', 'INSUFFICIENT_SUPPORT', 'SUPPORT_INSUFFICIENT', 'INVALID_PROBABILITY')):
      raise
    candidate, fold = historical['candidate_id'], historical['fold']
    path = run_root / 'candidates' / candidate / fold
    decision_path = path / 'threshold/receipt.json'
    if not decision_path.exists():
      io.write_json(
        decision_path,
        p.seal(
          {
            'schema': 'HURDLE_STAGE1_V2_PRIVATE_THRESHOLD_RECEIPT',
            'authorization_sha256': auth['receipt_sha256'],
            'candidate_id': candidate,
            'fold': fold,
            'status': 'V2_THRESHOLD_NUMERICAL_FAILURE',
            'threshold': None,
            'candidate_count': 0,
            'feasible_count': 0,
            'objective': None,
            'canonical_checks': 0,
          }
        ),
      )
    decision = io.read_json(decision_path)
    populations = {}
    for name in ('train', 'one-step', *(f'rollout-{h}' for h in m.HORIZONS)):
      if (path / name / 'receipt.json').exists():
        populations[name] = io.read_json(path / name / 'receipt.json')['receipt_sha256']
    job = {
      'schema': 'HURDLE_STAGE1_V2_FOLD_RESULT',
      'candidate_id': candidate,
      'fold': fold,
      'authorization_sha256': auth['receipt_sha256'],
      'status': 'NUMERICAL_FAILURE',
      'failures': [str(exc)],
      'train_anchor_sha256': historical['train_anchor_sha256'],
      'train_count': historical['train_count'],
      'models': {s: historical[s] for s in ('stage1', 'stage2')},
      'threshold': {k: decision[k] for k in ('status', 'candidate_count', 'feasible_count', 'objective', 'canonical_checks', 'receipt_sha256')},
      'rollout': {},
      'populations': populations,
      'train_comparison': None,
    }
    job['gate'] = gates.fold_gate(job, clauses)
    job['comparison'] = compare(historical, job)
    receipt = p.seal(job)
    io.write_json(path / 'receipt.json', receipt)
    names = [f.relative_to(path).as_posix() for f in path.rglob('*') if f.is_file()]
    io.old.finish(path, names, {'schema': 'V2_JOB_MANIFEST', 'receipt_sha256_binding': receipt['receipt_sha256']})
    return receipt


def numerical_failure(exc, job, status):
  if not any(x in str(exc) for x in ('NUMERICAL', 'NONFINITE', 'INSUFFICIENT_SUPPORT', 'SUPPORT_INSUFFICIENT', 'SIGNED16', 'INVALID_PROBABILITY')):
    raise exc
  job['status'] = status
  job['failures'].append(str(exc))


def selection(jobs, clauses):
  value = gates.select(jobs, clauses)
  value['status'] = value['status'].replace('HURDLE_', 'HURDLE_STAGE1_V2_', 1)
  value['states'] = [s.replace('HURDLE_', 'HURDLE_STAGE1_V2_', 1) if s.startswith('HURDLE_') else s for s in value['states']]
  return p.seal({'schema': 'HURDLE_STAGE1_V2_SELECTION_RESULT', **value})


def run(source, causal, derived, output, replica):
  io.require(replica in ('repeat-1', 'repeat-2'), 'V2_EXACT_TWO_REPLICAS_REQUIRED')
  auth = io.verify_inputs(source, causal, derived, output)
  _, _, historical, records, _, _ = io.metadata(source, causal, derived, output, remaining_runs=2 if replica == 'repeat-1' else 1)
  root = output / replica
  io.require(not root.exists(), 'V2_CLEAN_INDEPENDENT_RUN_REQUIRED')
  clauses = io.old.contracts()['acceptance-gate']['clauses']
  jobs = []
  with io.firewall():
    for original in historical:
      job = execute_job(root, source, original, records, auth, clauses)
      jobs.append(job)
      print(
        json.dumps(
          {
            'candidate': job['candidate_id'],
            'fold': job['fold'],
            'status': job['status'],
            'feasible_count': job['threshold']['feasible_count'],
            'gate_pass': job['gate']['pass'],
          }
        ),
        flush=True,
      )
  selected = selection(jobs, clauses)
  result = p.seal(
    {
      'schema': 'HURDLE_STAGE1_V2_RESULTS',
      'authorization_sha256': auth['receipt_sha256'],
      'job_count': 32,
      'jobs': jobs,
      'selection_sha256': selected['receipt_sha256'],
      'stage1_refit_calls': 0,
      'stage2_refit_calls': 0,
      'normalizer_refit_calls': 0,
      'raw_log_openings': 0,
      'qlog_openings': 0,
      'holdout_openings': 0,
      'vehicle_authority': 'NONE',
    }
  )
  io.write_json(root / 'selection.json', selected)
  io.write_json(root / 'results.json', result)
  io.verify_inputs(source, causal, derived, output, complete=True)
  names = [f.relative_to(root).as_posix() for f in root.rglob('*') if f.is_file()]
  return io.old.finish(
    root,
    names,
    {
      'schema': 'HURDLE_STAGE1_V2_RUN_MANIFEST',
      'status': SUCCESS,
      'authorization_sha256': auth['receipt_sha256'],
      'job_count': 32,
      'results_sha256': result['receipt_sha256'],
      'selection_sha256': selected['receipt_sha256'],
      'source_bytes_unchanged': True,
    },
  )


def resume(root, auth):
  """Saved V2 payload verification only. External references are never followed."""
  manifest = io.old.verify_manifest(root)
  result, selected = io.read_json(root / 'results.json'), io.read_json(root / 'selection.json')
  io.require(manifest['schema'] == 'HURDLE_STAGE1_V2_RUN_MANIFEST' and manifest['status'] == SUCCESS)
  io.require(manifest['authorization_sha256'] == auth['receipt_sha256'] and manifest['job_count'] == 32)
  io.require(result['receipt_sha256'] == manifest['results_sha256'] and selected['receipt_sha256'] == manifest['selection_sha256'])
  io.require(result['selection_sha256'] == selected['receipt_sha256'] and result['job_count'] == 32)
  io.require([(j['candidate_id'], j['fold']) for j in result['jobs']] == list(io.JOBS), 'V2_RESUME_JOB_SET_CONFLICT')
  for j in result['jobs']:
    jobroot = root / 'candidates' / j['candidate_id'] / j['fold']
    local = io.old.verify_manifest(jobroot)
    receipt = io.read_json(jobroot / 'receipt.json', j['receipt_sha256'])
    io.require(receipt == j and local['receipt_sha256_binding'] == j['receipt_sha256'])
    decision = io.read_json(jobroot / 'threshold/receipt.json', j['threshold']['receipt_sha256'])
    io.require(decision['authorization_sha256'] == auth['receipt_sha256'])
    expected = {'train', 'one-step', *(f'rollout-{h}' for h in m.HORIZONS)} if j['status'] == 'EXECUTED_COMPLETE' else set(j['populations'])
    io.require(set(j['populations']) == expected)
    for name, sha in j['populations'].items():
      population = io.read_json(jobroot / name / 'receipt.json', sha)
      io.require(population['threshold_sha256'] == decision['receipt_sha256'])
      for binding in population['arrays'].values():
        rel = name + '/' + binding['filename']
        io.require(local['files'][rel] == binding['file_sha256'])
        # Verify compressed file AND decoded content without a model/source loader.
        for _ in io.verified.array_chunks(io.member(jobroot, rel), binding):
          pass
  return manifest


def trapped_resume(root, auth):
  with ExitStack() as stack:
    for module, names in (
      (io, ('load_model', 'load_route', 'verify_inputs', 'metadata')),
      (m, ('probability', 'predict_delta', 'integrated', 'project', 'recursive', 'metrics')),
      (threshold, ('sweep', 'canonical')),
      (data, ('one_step', 'rollout', 'design', 'load_route')),
      (gates, ('select', 'selection_key', 'fold_gate')),
      (io.old.read, ('read_array',)),
    ):
      for name in names:
        stack.enter_context(patch.object(module, name, io.forbidden))
    with io.firewall():
      return resume(root, auth)


def repeatability(output):
  auth = io.read_json(output / 'authorization.json')
  first = trapped_resume(output / 'repeat-1', auth)
  second = trapped_resume(output / 'repeat-2', auth)
  if first != second:
    failure = p.seal(
      {
        'schema': 'HURDLE_STAGE1_V2_REPEATABILITY',
        'status': 'HURDLE_STAGE1_V2_REPEATABILITY_FAILURE',
        'selected_candidate': None,
        'run2_scratch_retained': True,
      }
    )
    io.write_json(output / 'repeatability-failure.json', failure)
    raise ValueError(failure['status'])
  receipt = p.seal(
    {
      'schema': 'HURDLE_STAGE1_V2_REPEATABILITY',
      'status': 'V2_EXACT_REPEATABILITY_PASS',
      'run1_manifest_sha256': first['receipt_sha256'],
      'run2_manifest_sha256': second['receipt_sha256'],
      'file_count': len(first['files']),
      'all_file_content_decoded_hashes_equal': True,
      'resume': 'V2_VERIFY_ONLY_RESUME_PASS',
      'run2_scratch_retained': True,
    }
  )
  io.write_json(output / 'repeatability.json', receipt)
  return receipt


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output', required=True, type=Path)
  parser.add_argument('--source', type=Path)
  parser.add_argument('--causal', type=Path)
  parser.add_argument('--derived', type=Path)
  parser.add_argument('--action', choices=('authorize', 'repeat-1', 'repeat-2', 'verify'), required=True)
  a = parser.parse_args()
  if a.action == 'verify':
    value = repeatability(a.output)
  else:
    if any(x is None for x in (a.source, a.causal, a.derived)):
      parser.error('explicit source/causal/derived paths required')
    if a.action == 'authorize':
      value, _, _ = io.authorize(a.source, a.causal, a.derived, a.output)
    else:
      value = run(a.source, a.causal, a.derived, a.output, a.action)
  print(json.dumps({'receipt_sha256': value['receipt_sha256'], 'status': value.get('status', 'AUTHORIZED')}), flush=True)


if __name__ == '__main__':
  main()
