"""V4 future-authorized executor. This module cannot mint trusted authorization."""

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_authorization as a
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_certificate as c
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_fitting_policy as f
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_io as io
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_store as store
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_data as data
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_gates as gates

m, p = f.old, a.p
FAIL = 'V4_STAGE1_FIT_FAILED_CLOSED'


def probability(x, model):
  f.matrix(x)
  z = x[:, -3] != 0
  transformed = m.transform(x, model['normalizer'])
  result = np.empty(len(x), dtype=np.float64)
  for state in (0, 1):
    mask = z == state
    head = model['heads'][state]
    result[mask] = m.sigmoid(np.ascontiguousarray(transformed[mask][:, head['positions']]) @ head['coefficients'])
  m.validate_probability(result)
  return result


def train(x, y, norm, *, candidate, normalizer_sha, certificate_bits=None):
  """Pure numeric TRAIN implementation; no readers, no private authority grant."""
  try:
    f.matrix(x)
    y = f.labels(y, len(x))
    dim = f.validate_normalizer(norm, candidate)
    a.need(x.shape[1] == dim and np.all(x[:, 0] == 1), 'V4_FEATURE_IDENTITY_CONFLICT')
    a.need(
      f.normalizer_identity(norm) == normalizer_sha and not np.any(norm['constant']) and np.array_equal(norm['effective'], np.arange(dim)),
      'V4_NORMALIZER_IDENTITY_CONFLICT',
    )
    transformed = np.ascontiguousarray(m.transform(x, norm))
    z = (x[:, -3] != 0).astype(np.int64)
    prepared = {}
    # Certify BOTH heads before fitting either one.
    for state in (0, 1):
      mask = z == state
      positions = f.basis(norm, candidate, state)
      design = np.ascontiguousarray(transformed[mask][:, positions])
      target = y[mask]
      positive, negative = int(target.sum()), int(np.count_nonzero(target == 0))
      a.need(min(positive, negative) >= m.SUPPORT and len(target) > len(positions), 'V4_STAGE1_HEAD_SUPPORT_FAILURE')
      rank = c.rank_generate(design, binding={'basis': positions, 'normalizer_sha256': normalizer_sha})
      a.need(
        rank['status'] == 'RANK_CERTIFICATE_PASS' and c.rank_verify(design, rank, binding={'basis': positions, 'normalizer_sha256': normalizer_sha}),
        'V4_STAGE1_HEAD_RANK_FAILURE',
      )
      separation = c.separation_generate(design, target)
      a.need(separation['status'] == 'NO_SEPARATION' and c.separation_verify(design, target, separation)['status'] == 'NO_SEPARATION', separation['status'])
      if certificate_bits is not None:
        proof_ints = [int(v) for v in rank['determinant']] + [separation['D']] + [v for row in separation['active'] for v in row]
        a.need(all(abs(v).bit_length() <= certificate_bits for v in proof_ints), 'V4_CERTIFICATE_RESOURCE_BOUND')
      prepared[state] = {
        'design': design,
        'target': target,
        'positions': positions,
        'rank': rank,
        'separation': separation,
        'support': {'positive': positive, 'negative': negative, 'count': len(target)},
      }
    heads = {}
    for state in (0, 1):
      row = prepared[state]
      coefficients, convergence = m.newton(row['design'], row['target'].astype(np.float64))
      heads[state] = {k: v for k, v in row.items() if k not in ('design', 'target')}
      heads[state].update(coefficients=coefficients, convergence=convergence)
    model = {'normalizer': norm, 'heads': heads}
    prob = probability(x, model)  # Exactly one assignment per original TRAIN row.
    threshold = m.threshold(prob, y, role='TRAIN')
    return {
      'status': 'TRAIN_COMPLETE',
      'heads': heads,
      'model': model,
      'probabilities': prob,
      'threshold': threshold,
      'normalizer_sha256': normalizer_sha,
      'row_order': 'ORIGINAL_TRAIN',
      'fallback': False,
    }
  except (ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
    return {'status': FAIL, 'cause': str(exc), 'fallback': False}


def integrated(x, current, model, threshold, stage2):
  prob = probability(x, model)
  a.need(type(threshold) is float and np.isfinite(threshold) and 0 <= threshold <= 1, 'V4_THRESHOLD_IDENTITY_CONFLICT')
  gate = prob > threshold
  delta = np.zeros(len(x), dtype=np.float64)
  projected = current.astype(np.int64).copy()
  if np.any(gate):
    delta[gate] = m.predict_delta(np.ascontiguousarray(x[gate]), stage2)
    projected[gate] = m.project(current[gate].astype(np.float64) + delta[gate])
  return delta, projected, prob, gate


def development(segments, candidate, model, threshold, stage2):
  _, anchor, x, current, target = data.design(segments, candidate)
  current, target = current.astype(np.int64), target.astype(np.int64)
  actual = target - current
  move = actual != 0
  a.need(min(int(move.sum()), int((~move).sum())) >= m.SUPPORT, 'V4_DEVELOPMENT_SUPPORT_FAILURE')
  delta, projected, prob, gate = integrated(x, current, model, threshold, stage2)
  error, baseline = delta - actual.astype(np.float64), -actual.astype(np.float64)
  return {
    'one_step': data.pair(error, baseline, anchor, projected, target, current),
    'true_move': data.pair(error[move], baseline[move], data.subset_sha(anchor, move), projected[move], target[move], current[move]),
    'stage1_diagnostics': m.diagnostics(move, gate),
  }, {
    'p_move': prob,
    'predicted_gate': gate,
    'integrated_delta': delta,
    'projected_next_tick': a.prior.legacy.compact_ticks(projected),
    'candidate_error': error,
  }


def recursive(initial, command, speed, candidate, model, threshold, stage2, horizon):
  _, length = m.parameters(candidate)
  n = len(initial)
  a.need(
    horizon in m.HORIZONS
    and initial.dtype == np.int64
    and initial.shape == (n, length + 1)
    and command.shape == (n, length + horizon - 1)
    and speed.shape == (n, horizon),
    'V4_ROLLOUT_CONTEXT_CONFLICT',
  )
  m.finite(initial, command, speed)
  current = initial[:, -1].copy()
  past = np.diff(initial, axis=1)
  path, gate_path, context_path = np.empty((n, horizon + 1), np.int64), np.empty((n, horizon), bool), np.empty((n, horizon), bool)
  path[:, 0] = current
  for step in range(horizon):
    x = np.ascontiguousarray(np.column_stack((np.ones(n), command[:, step : step + length], past, current, speed[:, step])), dtype=np.float64)
    context_path[:, step] = past[:, -1] != 0
    _, new, _, gate = integrated(x, current, model, threshold, stage2)
    path[:, step + 1], gate_path[:, step] = new, gate
    past[:, :-1] = past[:, 1:]
    past[:, -1] = new - current  # PROJECTED movement, never gate or future truth.
    current = new
  return path, gate_path, context_path


def rollout(segments, candidate, model, threshold, stage2, horizon):
  blocks, anchor, count = data.binding(segments, candidate, horizon)
  a.need(count >= m.SUPPORT, 'V4_ROLLOUT_SUPPORT_FAILURE')
  delay, length = m.parameters(candidate)
  paths, truth, gate_paths = [], [], []
  for segment, indices in blocks:
    for start in range(0, len(indices), m.CHUNK):
      ix = indices[start : start + m.CHUNK]
      initial = segment['tick'][ix[:, None] + np.arange(-length, 1)].astype(np.int64)
      command = segment['command'][ix[:, None] + np.arange(-delay - length + 1, horizon - delay)]
      speed = segment['speed'][ix[:, None] + np.arange(horizon)]
      path, gate, _ = recursive(initial, command, speed, candidate, model, threshold, stage2, horizon)
      paths.append(path)
      gate_paths.append(gate)
      truth.append(segment['tick'][ix[:, None] + np.arange(horizon + 1)].astype(np.int64))
  path, observed, gate = map(np.concatenate, (paths, truth, gate_paths))
  initial, target = observed[:, 0], observed[:, -1]
  error, baseline = (path[:, -1] - target).astype(np.float64), (initial - target).astype(np.float64)
  moved = np.any(observed != initial[:, None], axis=1)
  protected = data.pair(error[moved], baseline[moved], data.subset_sha(anchor, moved)) if int(moved.sum()) >= m.SUPPORT else None
  return {
    'overall': data.pair(error, baseline, anchor),
    'path_moved': protected,
    'path_moved_count': int(moved.sum()),
    'status': 'COMPLETE' if protected else 'V4_ROLLOUT_SUPPORT_FAILURE',
  }, {'projected_path': a.prior.legacy.compact_ticks(path), 'predicted_gate_path': gate, 'candidate_error': error}


def save_arrays(root, arrays, body):
  receipts = {key: store.array_write(root / (key + '.npy.gz'), value) for key, value in sorted(arrays.items())}
  row = p.seal({**body, 'arrays': receipts})
  store.write_json(root / 'receipt.json', row)
  return row


def save_train(root, fit, body):
  arrays = {'combined_probability': fit['probabilities']}
  details = {}
  for state, label in ((0, 'STATIC'), (1, 'MOVE')):
    head = fit['heads'][state]
    arrays[label + '_coefficients'] = head['coefficients']
    details[label] = {
      **{k: v for k, v in head.items() if k != 'coefficients'},
      'raw_basis_indices': head['positions'],
      'transformed_basis_indices': head['positions'],
    }
    if 'feature_names' in body:
      details[label]['feature_names'] = [body['feature_names'][j] for j in head['positions']]
  row = save_arrays(
    root, arrays, {**body, 'schema': 'V4_MODEL_THRESHOLD', 'heads': details, 'threshold': fit['threshold'], 'normalizer_sha256': fit['normalizer_sha256']}
  )
  manifest = store.finish(root, {'schema': 'V4_TRAIN_MANIFEST', 'train_receipt_sha256': row['receipt_sha256']})
  return row, manifest


def execute_job(permit, historical):
  prefix = io.job_valid(permit, historical)
  root = permit.roots['output'] / permit.replica / prefix
  a.need(not root.exists(), 'V4_CLEAN_JOB_REQUIRED')
  candidate, fold = historical['candidate_id'], historical['fold']
  models = io.load_models(permit, historical)
  segments = io.load_route(permit, historical)
  _, anchor, x, current, target = data.design(segments, candidate)
  a.need(anchor == historical['train_anchor_sha256'] and len(x) == historical['train_count'], 'V4_ANCHOR_IDENTITY_CONFLICT')
  y = target.astype(np.int64) != current.astype(np.int64)
  a.need(int(y.sum()) == historical['train_move_count'], 'V4_ANCHOR_IDENTITY_CONFLICT')
  norm = models['stage1']['normalizer']
  fit = train(
    x,
    y,
    norm,
    candidate=candidate,
    normalizer_sha=f.normalizer_identity(norm),
    certificate_bits=permit.authorization['resource_budget']['certificate_integer_bits'],
  )
  result = {
    'schema': 'V4_FOLD_RESULT',
    'candidate_id': candidate,
    'fold': fold,
    'rollout': {},
    'status': FAIL if fit['status'] != 'TRAIN_COMPLETE' else 'EXECUTED_COMPLETE',
    'normalizer_receipt_sha256': models['stage1']['normalizer_receipt_sha256'],
    'stage2_receipts': historical['stage2'],
    'train_anchor_sha256': anchor,
    'train_count': len(x),
    'authorization_sha256': permit.trusted_sha256,
    'failure': fit.get('cause'),
    'fallback': False,
  }
  if fit['status'] == 'TRAIN_COMPLETE':
    row, manifest = save_train(
      root / 'train',
      fit,
      {
        'candidate_id': candidate,
        'fold': fold,
        'authorization_sha256': permit.trusted_sha256,
        'train_anchor_sha256': anchor,
        'policy_receipts': permit.pack['policies'],
        'normalizer_receipt_sha256': models['stage1']['normalizer_receipt_sha256'],
        'normalizer_array_identities': {k: f.array_identity(v) for k, v in norm.items()},
        'feature_names': permit.pack['bodies']['empirical-hurdle-stage1-v4-current-feature-contract.json']['feature_names_by_candidate'][candidate],
        'v1_manifest_sha256': a.prior.verified.SOURCE_SHA,
        'v1_authorization_sha256': a.prior.verified.AUTH_SHA,
        'stage2_receipts': historical['stage2'],
      },
    )
    finalized = p.seal(
      {
        'schema': 'V4_TRAIN_FINALIZED',
        'status': 'TRAIN_COMPLETE',
        'candidate_id': candidate,
        'fold': fold,
        'train_anchor_sha256': anchor,
        'authorization_sha256': permit.trusted_sha256,
        'train_manifest_sha256': manifest['receipt_sha256'],
        'model_threshold_receipt_sha256': row['receipt_sha256'],
      }
    )
    store.write_json(root / 'train-finalized.json', finalized)
    io.finalized(permit, historical, finalized)
    del segments, x, current, target, y
    segments = io.load_route(permit, historical, development=True, receipt=finalized)
    _, anchor_dev, count = data.binding(segments, candidate, 1)
    a.need(anchor_dev == historical['one_step']['anchor_sha256'] and count == historical['one_step']['count'], 'V4_ANCHOR_IDENTITY_CONFLICT')
    try:
      metrics, arrays = development(segments, candidate, fit['model'], fit['threshold']['value'], models['stage2'])
      result.update(metrics)
      save_arrays(root / 'one-step', arrays, {'schema': 'V4_DEVELOPMENT', 'train_finalized_sha256': finalized['receipt_sha256'], 'anchor_sha256': anchor_dev})
      for h in m.HORIZONS:
        _, digest, count = data.binding(segments, candidate, h)
        expected = historical['rollout'][str(h)]['overall']
        a.need(digest == expected['anchor_sha256'] and count == expected['count'], 'V4_ANCHOR_IDENTITY_CONFLICT')
        metric, arrays = rollout(segments, candidate, fit['model'], fit['threshold']['value'], models['stage2'], h)
        result['rollout'][str(h)] = metric
        save_arrays(
          root / f'rollout-{h}', arrays, {'schema': 'V4_ROLLOUT', 'horizon': h, 'train_finalized_sha256': finalized['receipt_sha256'], 'anchor_sha256': digest}
        )
        if metric['status'] != 'COMPLETE':
          result['status'] = 'ROLLOUT_FAILURE'
    except (ValueError, FloatingPointError) as exc:
      if 'ANCHOR_IDENTITY' in str(exc):
        raise
      result['status'], result['failure'] = 'DEVELOPMENT_OR_ROLLOUT_FAILURE', str(exc)
  result['gate'] = gates.fold_gate(result, permit.pack['clauses'])
  row = p.seal(result)
  store.write_json(root / 'receipt.json', row)
  store.finish(root, {'schema': 'V4_JOB_MANIFEST', 'job_receipt_sha256': row['receipt_sha256']})
  return row


def select(jobs, clauses):
  return p.seal({'schema': 'V4_SELECTION', **gates.select(jobs, clauses)})


def run(*, authorization, trusted_sha256, replica, roots):
  permit = a.preflight(authorization, trusted_sha256, replica=replica, roots=roots)
  root = permit.roots['output'] / replica
  a.need(not root.exists(), 'V4_CLEAN_INDEPENDENT_RUN_REQUIRED')
  with store.output(permit), io.firewall():
    store.write_json(root / 'authorization.json', authorization)
    jobs = [execute_job(permit, job) for job in permit.lineage['jobs']]
    selection = select(jobs, permit.pack['clauses'])
    store.write_json(root / 'selection.json', selection)
    results = p.seal(
      {
        'schema': 'V4_RESULTS',
        'jobs': jobs,
        'job_count': len(jobs),
        'selection_sha256': selection['receipt_sha256'],
        'source_writes': 0,
        'stage2_fit_calls': 0,
        'normalizer_fit_calls': 0,
        'holdout_openings': 0,
        'vehicle_authority': 'NONE',
      }
    )
    store.write_json(root / 'results.json', results)
    unchanged = io.immutability(permit)
    return store.finish(
      root,
      {
        'schema': 'V4_RUN_MANIFEST',
        'synthetic': False,
        'authorization_sha256': trusted_sha256,
        'result_sha256': results['receipt_sha256'],
        'selection_sha256': selection['receipt_sha256'],
        **unchanged,
      },
    )


def synthetic_run(root, x, y, norm):
  """Separate labelled in-memory fixture path. No source reader or actual permit."""
  with store.synthetic_output(root), io.firewall():
    fit = train(x, y, norm, candidate='HRI_D00_L01', normalizer_sha=f.normalizer_identity(norm))
    a.need(fit['status'] == 'TRAIN_COMPLETE')
    row, _ = save_train(root / 'train', fit, {'synthetic': True, 'authorization': 'SYNTHETIC_AUTHORIZATION_ONLY'})
    model = fit['model']
    stage2 = {'normalizer': norm, 'coefficients': np.zeros(5)}
    path, gate, context = recursive(
      np.zeros((1, 2), np.int64), np.zeros((1, 25)), np.ones((1, 25)), 'HRI_D00_L01', model, fit['threshold']['value'], stage2, 25
    )
    save_arrays(root / 'rollout', {'path': path, 'gate': gate, 'context': context}, {'schema': 'SYNTHETIC_ROLLOUT', 'train_sha256': row['receipt_sha256']})
    return store.finish(root, {'schema': 'V4_RUN_MANIFEST', 'synthetic': True, 'actual_private_execution': False})


def resume(root, manifest_sha256, *, synthetic=False, authorization_sha256=None):
  """Saved store only. Never loads source, models or recomputes any scientific artifact."""
  root = a.prior.safe(Path(root))
  if not synthetic:
    a.need(
      type(authorization_sha256) is str and __import__('re').fullmatch('[0-9a-f]{64}', authorization_sha256) is not None, 'V4_PRIVATE_EXECUTION_NOT_AUTHORIZED'
    )
    auth = a.prior.read_json(root / 'authorization.json', authorization_sha256)
    a.need(auth['schema'] == a.SCHEMA and auth['storage_volume'] == 'E_EXTERNAL_SSD')
    a.prior.external.prove_authorized_external_volume(root, expected_mount=auth['mount_identity_sha256'])
    a.prior.external.check_live_volume(auth['volume_identity_sha256'])
    a.need(p.sha(str(root.parent).encode()) == auth['root_identities']['output'] and root.name in auth['replicas'])
  with ExitStack() as stack:
    for module, names in (
      (c, ('rank_generate', 'separation_generate')),
      (m, ('newton', 'threshold')),
      (io, ('load_models', 'load_route')),
      (globals_module(), ('train', 'probability', 'development', 'recursive', 'rollout', 'select')),
    ):
      for name in names:
        stack.enter_context(patch.object(module, name, io.forbidden))
    manifest = store.verify(root, manifest_sha256)
    a.need(manifest.get('synthetic') is synthetic and (synthetic or manifest['authorization_sha256'] == authorization_sha256), 'V4_RESUME_INTEGRITY_FAILURE')
    return manifest


def globals_module():
  import sys

  return sys.modules[__name__]


def repeatability(first, first_sha, second, second_sha, *, synthetic=False, authorization_sha256=None):
  one = resume(first, first_sha, synthetic=synthetic, authorization_sha256=authorization_sha256)
  two = resume(second, second_sha, synthetic=synthetic, authorization_sha256=authorization_sha256)
  a.need(one == two, 'V4_EXACT_REPEATABILITY_FAILURE')
  return p.seal({'schema': 'V4_REPEATABILITY', 'all_file_hashes_equal': True, 'manifest_sha256': first_sha, 'recompute_calls': 0})
