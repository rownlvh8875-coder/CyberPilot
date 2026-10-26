"""Synthetic private-shaped stores only; no authoritative private path is used.

Core execution tests register an in-memory fixture permit after constructing
its own sealed source. Actual public admission is tested separately and rejects
these synthetic source identities. This helper is never imported by production.
"""

from unittest.mock import patch
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_io as io
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_store as store
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_data as data
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as m
from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_gates as gates

p = io.p


def fixture(root, *, all_jobs=False):
  roots = {key: root / key for key in io.ROOT_KEYS}
  for key, path in roots.items():
    if key != 'output':
      path.mkdir()
  records, routes, pins = [], [], {'causal': {}, 'derived': {}}
  segments = {}
  for number, route in enumerate(('a' * 64, 'c' * 64)):
    rid = p.sha(f'synthetic-segment-{number}'.encode())
    n = 1600
    index = np.arange(n, dtype=np.int64)
    tick = index // 5
    command = ((index + 1) % 5 == 0).astype(np.float64)
    base, derived = roots['causal'] / route, roots['derived'] / route
    (base / 'arrays').mkdir(parents=True)
    derived.mkdir(parents=True)
    a = {'command.normalized': command, 'state.speed_mps': np.full(n, 15.0), 'grid_time_ns': index * 10_000_000}
    d = {'angle_tick': tick, 'streak_all': index + 1, 'model_eligible': np.ones(n, bool), 'rail': np.zeros(n, bool),
         's2_ri_causal_run_id': np.zeros(n, np.int64), 'within_s2_ri_causal_run_index': index}
    bound = {}
    for label, values, directory, owner in (('source', a, base / 'arrays', 'causal'), ('derived', d, derived, 'derived')):
      bindings = {}
      for name, array in values.items():
        path = directory / io.legacy.old.read.array_name(name)
        np.save(path, array, allow_pickle=False)
        bindings[name] = {'dtype': array.dtype.str, 'shape': list(array.shape), 'order': 'C',
                          'file_sha256': io.digest(path), 'array_sha256': io.legacy.old.array_digest(array)}
        pins[owner][path.relative_to(roots[owner]).as_posix()] = io.digest(path)
      bound[label] = p.seal({'schema': 'SYNTHETIC_SEGMENT', 'route_id': route, 'segment_sha256': rid, 'arrays': bindings})
    records.append((base, bound['source'], derived, bound['derived']))
    routes.append(route)
    segments[route] = [{'route_id': route, 'segment_sha256': rid, 'tick': tick, 'streak': index + 1, 'command': command,
                        'speed': a['state.speed_mps'], 'rail': d['rail'], 'eligible': d['model_eligible'],
                        'run': d['s2_ri_causal_run_id'], 'within': index}]
  pack = io.contracts()
  jobs, references = [], []
  identities = io.JOBS if all_jobs else io.JOBS[:1]
  with patch.object(io.legacy, 'output_path', side_effect=lambda path, excluded=(): io.safe(path)), patch.object(io.legacy, 'headroom'):
    for candidate, fold in identities:
      _, length = m.parameters(candidate)
      size = 2 * length + 3
      train_route, dev_route = routes if fold == 'FOLD_A' else routes[::-1]
      jobroot = roots['source'] / 'repeat-1/candidates' / candidate / fold
      blocks, anchor, x, current, target = data.design(segments[train_route], candidate)
      labels = target != current
      positives, negatives = int(labels.sum()), int((~labels).sum())
      models, receipts = {}, {}
      for stage in ('stage1', 'stage2'):
        norm = {'effective': np.arange(size), 'mean': np.zeros(size), 'std': np.ones(size), 'constant': np.zeros(size, bool),
                'constant_reference': np.zeros(size)}
        coefficient = np.zeros(size)
        coefficient[0] = -1.0 if stage == 'stage1' else 0.0
        coefficient[length] = 2.0 if stage == 'stage1' else 1.0
        models[stage] = {'normalizer': norm, 'coefficients': coefficient}
        normalizer = io.legacy.population(jobroot / stage / 'normalizer', norm, {'schema': 'SYNTHETIC_NORMALIZER', 'stage': stage})
        effective = m.transform(x if stage == 'stage1' else np.ascontiguousarray(x[labels]), norm)
        model = io.legacy.population(jobroot / stage / 'model', {'coefficients': coefficient},
                                    {'schema': 'SYNTHETIC_MODEL', 'normalizer_sha256': normalizer['receipt_sha256'],
                                     'effective_x_sha256': io.legacy.old.array_digest(effective)})
        receipts[stage] = {'model_receipt_sha256': model['receipt_sha256'], 'normalizer_receipt_sha256': normalizer['receipt_sha256'],
                           'coefficient_sha256': model['arrays']['coefficients']['array_sha256']}
      train = io.legacy.population(jobroot / 'train', {**data.context(blocks, candidate), 'actual_delta_tick': (target - current).astype(float)},
                                   {'schema': 'SYNTHETIC_TRAIN'})
      confusion = {'TP': positives, 'FN': 0, 'FP': negatives, 'TN': 0, 'P': positives, 'N': negatives}
      threshold = io.legacy.population(jobroot / 'threshold', {'train_probability': m.probability(x, models['stage1']), 'threshold': np.array([0.0])},
                                       {'schema': 'SYNTHETIC_THRESHOLD', 'selection': confusion})
      job = {'schema': 'SYNTHETIC_V1_JOB', 'candidate_id': candidate, 'fold': fold, 'status': 'EXECUTED_COMPLETE',
             'train_route': train_route, 'development_route': dev_route, 'train_count': len(x), 'train_move_count': positives,
             'train_static_count': negatives, 'train_anchor_sha256': anchor, **receipts,
             'threshold': {**confusion, 'receipt_sha256': threshold['receipt_sha256']},
             'population_receipts': {'train': train['receipt_sha256']}, 'rollout': {}}
      metrics, arrays = data.one_step(segments[dev_route], candidate, models['stage1'], 0.0, models['stage2'])
      job.update(metrics)
      pop = io.legacy.population(jobroot / 'one-step', arrays, {'schema': 'SYNTHETIC_ONE_STEP'})
      job['population_receipts']['one-step'] = pop['receipt_sha256']
      for horizon in m.HORIZONS:
        metrics, arrays = data.rollout(segments[dev_route], candidate, models['stage1'], 0.0, models['stage2'], horizon)
        job['rollout'][str(horizon)] = metrics
        pop = io.legacy.population(jobroot / f'rollout-{horizon}', arrays, {'schema': 'SYNTHETIC_ROLLOUT'})
        job['population_receipts'][f'rollout-{horizon}'] = pop['receipt_sha256']
      job['gate'] = gates.fold_gate(job, pack['clauses'])
      sealed = p.seal(job)
      store.write_json(jobroot / 'receipt.json', sealed)
      store.finish(jobroot, {'schema': 'SYNTHETIC_SOURCE_JOB'})
      jobs.append(sealed)
      references.append({'candidate_id': candidate, 'fold': fold, 'reference_tp': positives, 'positive_count': positives,
                         'negative_count': negatives, 'v1_confusion_receipt_sha256': threshold['receipt_sha256'],
                         'train_anchor_sha256': anchor, 'stage1_model_sha256': receipts['stage1']['model_receipt_sha256'],
                         'stage1_coefficient_sha256': receipts['stage1']['coefficient_sha256'],
                         'stage1_normalizer_sha256': receipts['stage1']['normalizer_receipt_sha256']})
  source_manifest = store.finish(roots['source'] / 'repeat-1', {'schema': 'SYNTHETIC_SOURCE_RUN'})
  pins['v1'] = source_manifest['files']
  pack = {**pack, 'jobs': jobs, 'references': references, 'source_policy': {**pack['source_policy'], 'route_ids': routes}}
  auth = p.seal({'schema': 'SYNTHETIC_CORE_FIXTURE_NOT_ACTUAL_AUTHORIZATION', 'head': io.current_head(), 'executor_sources': io.sources(),
                 'v1_manifest_sha256': source_manifest['receipt_sha256'],
                 'root_identities': {k: p.sha(str(v).encode()) for k, v in roots.items()}, 'jobs': [io.job_identity(j) for j in jobs],
                 'source_manifests': {'v1_file_set': p.sha(p.canonical(pins['v1'])), 'source_file_set': p.sha(p.canonical(pins['causal'])),
                                      'derived_file_set': p.sha(p.canonical(pins['derived']))}})
  permit = io.Permit(roots, auth, auth['receipt_sha256'], pack, tuple(jobs), tuple(records), pins, io.records_identity(records))
  io._PERMITS[permit] = permit.trusted_sha256  # Core-only test double; cannot pass the actual admission validator.
  return permit
