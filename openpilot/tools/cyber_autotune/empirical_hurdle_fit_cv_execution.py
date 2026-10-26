"""Authorized frozen Hurdle retrospective execution, with complete private evidence."""

import argparse
from contextlib import contextmanager, ExitStack
import json
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_identifiability_execution as read
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_store as store
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_data as data
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_gates as gates

SUCCESS = 'HURDLE_RETROSPECTIVE_FIT_AND_CV_COMPLETE'


def forbidden(*args, **kwargs):
  raise ValueError('HURDLE_EXECUTION_FORBIDDEN')


@contextmanager
def firewall():
  with ExitStack() as stack:
    stack.enter_context(patch.object(np.linalg, 'pinv', forbidden))
    stack.enter_context(
      patch.dict(
        sys.modules,
        dict.fromkeys(
          (
            'scipy.optimize',
            'sklearn',
            'openpilot.tools.lib.logreader',
            'tools.lib.logreader',
            'openpilot.tools.cyber_autotune.empirical_s2_ri_fit_cv_execution',
          ),
          None,
        ),
      )
    )
    yield


def save_arrays(root, arrays):
  return {k: store.compressed_array_write(root / (read.array_name(k) + '.gz'), np.ascontiguousarray(v)) for k, v in arrays.items()}


def population(root, arrays, fields):
  bindings = save_arrays(root, arrays)
  receipt = p.seal({**fields, 'arrays': bindings})
  store.write_json(root / 'receipt.json', receipt)
  return receipt


def save_model(root, model, candidate, fold, train_sha, count, auth, stage):
  norm = population(
    root / 'normalizer',
    model['normalizer'],
    {
      'schema': 'EMPIRICAL_HURDLE_TRAIN_NORMALIZER_V1',
      'stage': stage,
      'candidate_id': candidate,
      'fold': fold['fold'],
      'train_route': fold['train'],
      'train_anchor_sha256': train_sha,
      'count': count,
      'authorization_sha256': auth['receipt_sha256'],
    },
  )
  arrays = {k: model[k] for k in ('coefficients', 'nominal_coefficients')}
  if 'singular_values' in model:
    arrays['singular_values'] = model['singular_values']
  receipt = population(
    root / 'model',
    arrays,
    {
      'schema': 'EMPIRICAL_HURDLE_FOLD_STAGE_MODEL_V1',
      'stage': stage,
      'candidate_id': candidate,
      'fold': fold['fold'],
      'train_anchor_sha256': train_sha,
      'train_count': count,
      'normalizer_sha256': norm['receipt_sha256'],
      'policy_sha256': store.PINS['fitting-policy'],
      'rank': model['rank'],
      'effective_columns': len(model['normalizer']['effective']),
      'nominal_columns': len(model['nominal_coefficients']),
      'constant_columns': int(model['normalizer']['constant'].sum()),
      'effective_x_sha256': p.sha(model['effective_x_sha_input'].tobytes()),
      'convergence': model.get('convergence'),
      'condition': model.get('condition'),
      'interpretation': 'EMPIRICAL_PREDICTIVE_PARAMETERS',
      'authorization_sha256': auth['receipt_sha256'],
    },
  )
  return {
    'model_receipt_sha256': receipt['receipt_sha256'],
    'normalizer_receipt_sha256': norm['receipt_sha256'],
    'coefficient_sha256': receipt['arrays']['coefficients']['array_sha256'],
    'rank': model['rank'],
    'effective_columns': receipt['effective_columns'],
    'nominal_columns': receipt['nominal_columns'],
    'constant_columns': receipt['constant_columns'],
    'train_anchor_sha256': train_sha,
    'count': count,
    'convergence': model.get('convergence'),
    'condition': model.get('condition'),
  }


def classified(error):
  reason = str(error)
  allowed = ('NUMERICAL', 'NONCONVERGENCE', 'LINE_SEARCH_FAILURE', 'RANK', 'INSUFFICIENT', 'CLASS_MISSING')
  if isinstance(error, np.linalg.LinAlgError):
    return 'HURDLE_NUMERICAL_FAILURE_LINEAR_ALGEBRA'
  if isinstance(error, FloatingPointError):
    return 'HURDLE_NUMERICAL_FAILURE_FLOATING_POINT'
  if not any(v in reason for v in allowed):
    raise error
  return reason


def execute_job(root, candidate, fold, records, auth, clauses):
  store.storage_headroom(root)
  path = root / 'candidates' / candidate / fold['fold']
  if path.exists():
    raise ValueError('INCOMPLETE_JOB_REQUIRES_SEPARATE_CLEAN_RUN_NO_PARTIAL_REUSE')
  result = {
    'schema': 'EMPIRICAL_HURDLE_FOLD_RESULT_V1',
    'candidate_id': candidate,
    'fold': fold['fold'],
    'train_route': fold['train'],
    'development_route': fold['development'],
    'authorization_sha256': auth['receipt_sha256'],
    'policy_sha256': store.PINS['fitting-policy'],
    'status': 'EXECUTED_COMPLETE',
    'failures': [],
    'stage1': None,
    'threshold': None,
    'stage2': None,
    'one_step': None,
    'true_move': None,
    'rollout': {},
    'population_receipts': {},
    'train_only_threshold_verified': False,
    'stage2_move_only_verified': False,
  }
  train = data.load_route(records, fold['train'], auth)
  blocks, train_sha, x, current, target = data.design(train, candidate)
  delta = (target - current).astype(np.float64)
  labels = delta != 0
  result.update(train_count=len(x), train_static_count=int((~labels).sum()), train_move_count=int(labels.sum()), train_anchor_sha256=train_sha)
  train_receipt = population(
    path / 'train',
    {**data.context(blocks, candidate), 'actual_delta_tick': delta, 'move_label': labels},
    {'schema': 'EMPIRICAL_HURDLE_TRAIN_POPULATION_V1', 'anchor_sha256': train_sha},
  )
  result['population_receipts']['train'] = train_receipt['receipt_sha256']
  stage1, stage2, decision = None, None, None
  try:
    stage1 = m.fit_stage1(x, labels, role='TRAIN')
    result['stage1'] = save_model(path / 'stage1', stage1, candidate, fold, train_sha, len(x), auth, 'STAGE1')
    probabilities = m.probability(x, stage1)
    decision = m.threshold(probabilities, labels, role='TRAIN')
    receipt = population(
      path / 'threshold',
      {'train_probability': probabilities, 'threshold': np.array([decision['value']], dtype=np.float64)},
      {
        'schema': 'EMPIRICAL_HURDLE_TRAIN_THRESHOLD_V1',
        'candidate_id': candidate,
        'fold': fold['fold'],
        'stage1_model_sha256': result['stage1']['model_receipt_sha256'],
        'train_anchor_sha256': train_sha,
        'threshold_policy_sha256': store.PINS['threshold-policy'],
        'selection': decision,
      },
    )
    result['threshold'] = {k: v for k, v in decision.items() if k != 'value'}
    result['threshold']['receipt_sha256'] = receipt['receipt_sha256']
    result['train_only_threshold_verified'] = True
    del probabilities
  except (ValueError, np.linalg.LinAlgError, FloatingPointError) as error:
    result['failures'].append(classified(error))
  try:
    stage2 = m.fit_stage2(x, delta, role='TRAIN')
    result['stage2'] = save_model(path / 'stage2', stage2, candidate, fold, data.subset_sha(train_sha, labels), int(labels.sum()), auth, 'STAGE2')
    result['stage2_move_only_verified'] = bool(np.array_equal(stage2['train_mask'], labels))
  except (ValueError, np.linalg.LinAlgError, FloatingPointError) as error:
    result['failures'].append(classified(error))
  # No DEVELOPMENT arrays have been loaded or passed to either fitting/threshold API.
  del train, blocks, x, current, target, delta, labels
  for model in (stage1, stage2):
    if model is not None:
      model.pop('effective_x_sha_input', None)
      model.pop('train_mask', None)
  if stage1 is not None and stage2 is not None and decision is not None:
    dev = data.load_route(records, fold['development'], auth)
    try:
      aggregates, arrays = data.one_step(dev, candidate, stage1, decision['value'], stage2)
      result.update(aggregates)
      receipt = population(
        path / 'one-step',
        arrays,
        {
          'schema': 'EMPIRICAL_HURDLE_ONE_STEP_EVIDENCE_V1',
          'candidate_id': candidate,
          'fold': fold['fold'],
          'anchor_sha256': aggregates['one_step']['anchor_sha256'],
          'model_lineage': [result['stage1']['model_receipt_sha256'], result['threshold']['receipt_sha256'], result['stage2']['model_receipt_sha256']],
        },
      )
      result['population_receipts']['one-step'] = receipt['receipt_sha256']
      del arrays
      if result['stage2_oracle']['failure'] is not None:
        result['failures'].append(result['stage2_oracle']['failure'])
      if result['stage1_diagnostics']['status'] != 'DEFINED':
        result['failures'].append('STAGE1_DIAGNOSTIC_UNDEFINED')
    except (ValueError, np.linalg.LinAlgError, FloatingPointError) as error:
      result['failures'].append(classified(error))
    # Gate failure or undefined precision never skips numerically executable horizons.
    for horizon in m.HORIZONS:
      try:
        aggregates, arrays = data.rollout(dev, candidate, stage1, decision['value'], stage2, horizon)
        result['rollout'][str(horizon)] = aggregates
        receipt = population(
          path / f'rollout-{horizon}',
          arrays,
          {
            'schema': 'EMPIRICAL_HURDLE_ROLLOUT_EVIDENCE_V1',
            'candidate_id': candidate,
            'fold': fold['fold'],
            'horizon': horizon,
            'anchor_sha256': aggregates['overall']['anchor_sha256'],
            'comparator_anchor_sha256': aggregates['overall']['comparator_anchor_sha256'],
            'exogenous': 'LOGGED_EXOGENOUS_COMMAND_CONDITIONED_ROLLOUT',
          },
        )
        result['population_receipts'][f'rollout-{horizon}'] = receipt['receipt_sha256']
        del arrays
        if aggregates['status'] != 'COMPLETE':
          result['failures'].append(aggregates['status'] + '_' + str(horizon))
      except (ValueError, np.linalg.LinAlgError, FloatingPointError) as error:
        result['failures'].append(classified(error) + '_ROLLOUT_' + str(horizon))
  if result['failures']:
    result['status'] = 'EXECUTION_FAILURE'
  result['gate'] = gates.fold_gate(result, clauses)
  receipt = p.seal(result)
  store.write_json(path / 'receipt.json', receipt)
  names = [f.relative_to(path).as_posix() for f in path.rglob('*') if f.is_file()]
  store.finish(
    path,
    names,
    {'schema': 'EMPIRICAL_HURDLE_JOB_MANIFEST_V1', 'receipt_sha256_binding': receipt['receipt_sha256'], 'authorization_sha256': auth['receipt_sha256']},
  )
  return receipt


def verify_run(path, auth):
  """Verification uses hashes and sealed saved results, never scoring or selection."""
  manifest = store.verify_manifest(path)
  results, selection = read.read_json(path / 'results.json'), read.read_json(path / 'selection.json')
  if (
    manifest['schema'] != 'EMPIRICAL_HURDLE_FIT_CV_MANIFEST_V1'
    or manifest['authorization_sha256'] != auth['receipt_sha256']
    or manifest['results_sha256'] != results['receipt_sha256']
    or manifest['selection_sha256'] != selection['receipt_sha256']
    or results['authorization_sha256'] != auth['receipt_sha256']
    or results['job_count'] != 32
  ):
    raise ValueError('HURDLE_RESUME_IDENTITY_CONFLICT')
  jobs = []
  for candidate in m.CANDIDATES:
    for fold in ('FOLD_A', 'FOLD_B'):
      root = path / 'candidates' / candidate / fold
      local = store.verify_manifest(root)
      receipt = read.read_json(root / 'receipt.json')
      if (
        receipt['candidate_id'] != candidate
        or receipt['fold'] != fold
        or receipt['authorization_sha256'] != auth['receipt_sha256']
        or local['receipt_sha256_binding'] != receipt['receipt_sha256']
      ):
        raise ValueError('HURDLE_RESUME_JOB_CONFLICT')
      jobs.append(receipt)
  if jobs != results['jobs'] or selection['receipt_sha256'] != results['selection_sha256']:
    raise ValueError('HURDLE_RESUME_RESULT_CONFLICT')
  return manifest


def run(source, derived, output, replica):
  if replica not in ('repeat-1', 'repeat-2'):
    raise ValueError('EXACT_TWO_REPLICAS_REQUIRED')
  auth, bundle, records, source_files, derived_files = store.admit(source, derived, output)
  store.verify_files(source, source_files)
  store.verify_files(derived, derived_files)
  store.verify_files(p.PUBLIC, auth['public_input_files'])
  path = output / replica
  if (path / 'manifest.json').exists():
    return verify_run(path, auth)
  jobs = []
  clauses = bundle['acceptance-gate']['clauses']
  with firewall():
    for candidate in m.CANDIDATES:
      for fold in bundle['route-cv-contract']['folds']:
        receipt = execute_job(path, candidate, fold, records, auth, clauses)
        jobs.append(receipt)
        print(
          json.dumps(
            {'candidate': candidate, 'fold': fold['fold'], 'status': receipt['status'], 'reasons': receipt['failures'], 'gate': receipt['gate']['pass']}
          ),
          flush=True,
        )
  selection = p.seal({'schema': 'EMPIRICAL_HURDLE_SELECTION_RESULT_V1', **gates.select(jobs, clauses)})
  result = p.seal(
    {
      'schema': 'EMPIRICAL_HURDLE_FIT_CV_RESULTS_V1',
      'authorization_sha256': auth['receipt_sha256'],
      'policy_sha256': store.PINS['fitting-policy'],
      'jobs': jobs,
      'job_count': len(jobs),
      'selection_sha256': selection['receipt_sha256'],
      'raw_log_openings': 0,
      'qlog_openings': 0,
      'holdout_openings': 0,
      'pooled_refit': False,
      'rate_dependency': 'NONE',
      'vehicle_authority': 'NONE',
    }
  )
  store.write_json(path / 'results.json', result)
  store.write_json(path / 'selection.json', selection)
  store.verify_files(source, source_files)
  store.verify_files(derived, derived_files)
  store.verify_files(p.PUBLIC, auth['public_input_files'])
  names = [f.relative_to(path).as_posix() for f in path.rglob('*') if f.is_file()]
  return store.finish(
    path,
    names,
    {
      'schema': 'EMPIRICAL_HURDLE_FIT_CV_MANIFEST_V1',
      'status': SUCCESS,
      'authorization_sha256': auth['receipt_sha256'],
      'results_sha256': result['receipt_sha256'],
      'selection_sha256': selection['receipt_sha256'],
      'job_count': 32,
      'input_bytes_unchanged': True,
    },
  )


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  for key in ('source', 'derived', 'output'):
    parser.add_argument('--' + key, required=True, type=Path)
  parser.add_argument('--replica', choices=('repeat-1', 'repeat-2'), required=True)
  args = parser.parse_args()
  receipt = run(args.source, args.derived, args.output, args.replica)
  print(json.dumps({'status': receipt['status'], 'manifest_sha256': receipt['receipt_sha256']}))


if __name__ == '__main__':
  main()
