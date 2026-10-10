"""Two whole-route folds, conditional pooled refit, closed future holdout package."""

import argparse
from pathlib import Path
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_plant_model as m
from openpilot.tools.cyber_autotune import empirical_source_execution as prior
from openpilot.tools.cyber_autotune import empirical_v2_generation as g2
from openpilot.tools.cyber_autotune import empirical_signal_crosscheck as cross
from openpilot.tools.cyber_autotune import empirical_v3_policy as v
from openpilot.tools.cyber_autotune import empirical_v3_cache as cache
from openpilot.tools.cyber_autotune import empirical_v3_models as cv


def refit(data, selection, identity, path):
  if not (selection.get('gate') or {}).get('passed', False):
    return None
  if selection.get('selected') is None:
    raise ValueError('GATE_WITHOUT_SELECTED_STRUCTURE')
  c = selection['selected']['config']
  model = m.fit(data, c)
  if model['status'] != 'FITTED':
    raise ValueError('POOLED_FINAL_REFIT_FAILED_NO_RESELECTION')
  result = p.seal(
    {
      'schema': 'EMPIRICAL_STAGE_V3_PRIVATE_FROZEN_MODEL_V1',
      'model': model,
      **identity,
      'coefficient_sha256': p.sha(p.canonical(model['coefficients'])),
      'development_metrics': None,
      'interpretation': 'POOLED_REFIT_FOR_FUTURE_UNTOUCHED_HOLDOUT_ONLY',
    }
  )
  p.persist(path, result)
  return result


def holdout_package(models, result_sha):
  policy = v.policy()
  return p.seal(
    {
      'schema': 'FUTURE_EMPIRICAL_PLANT_V3_HOLDOUT_PACKAGE_V1',
      'status': 'CLOSED' if models.get('STAGE_A') else 'CLOSED_MISSING_ADMISSIBLE_MODEL',
      'models': models,
      'result_sha256': result_sha,
      'route_cv_policy_sha256': policy['receipt_sha256'],
      'source_equivalence_sha256': policy['source_equivalence_sha256'],
      'empirical_profile_sha256': v.routes()[0]['empirical_profile_sha256'],
      'full_carparams_sha256': v.routes()[0]['full_carparams_sha256'],
      'metric_policy_sha256': p.metric_policy()['receipt_sha256'],
      'support_minimum': 201,
      'command_yaw_policy_sha256': policy['receipt_sha256'],
      'future_route_admission_sha256': prior.read(p.PUBLIC / 'future-empirical-holdout-admission-v1.json')['receipt_sha256'],
      'one_time_opening_state': 'CLOSED',
      'future_holdout': 'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
      'refit_allowed': False,
      'reselection_allowed': False,
      'threshold_change_allowed': False,
      'model_family_change_allowed': False,
      'old_routes_holdout_allowed': False,
      'evaluation_execution_authorized': False,
      'current_source_admission': 'EXACT_SOURCE_PROFILE_AUDIT_REQUIRED_NO_AUTOMATIC_EQUIVALENCE',
    }
  )


def stage(data, store, name, env):
  result, model_hashes = {}, {}
  for b in v.BINS:
    records = []
    for c in p.family_policy()['candidates']:
      params = c['input_taps'] + c['output_lags'] + 1
      folds = []
      for fold in v.folds()['folds']:
        train, dev = data[fold['train_route']][b], data[fold['development_route']][b]
        model = m.fit(train, c)
        static = m.static_fit(train)
        evaluation, arrays = cv.evaluate(dev, model, static)
        folder = store / 'folds' / name / b / (c['family'] + '-' + str(c['delay_samples'])) / fold['fold']
        hashes = {key: cv.save_array(folder / (key + '.npy'), value) for key, value in arrays.items()}
        # Keep separate TRAIN design as well as opposite-route DEVELOPMENT design.
        train_design = m.design(train, c)
        hashes['train_design'] = cv.save_array(folder / 'train-design.npy', train_design[0])
        hashes['train_target'] = cv.save_array(folder / 'train-target.npy', train_design[1])
        private = p.seal(
          {
            'schema': 'EMPIRICAL_PLANT_V3_PRIVATE_FOLD_RESULT_V1',
            **fold,
            'stage': name,
            'speed_bin': b,
            'config': c,
            'model': model,
            'static_gain': static,
            'evaluation': evaluation,
            'arrays': hashes,
            'policy_sha256': v.policy()['receipt_sha256'],
            'environment': env,
          }
        )
        p.persist(folder / 'receipt.json', private)
        folds.append(
          {
            **fold,
            'fit_status': model['status'],
            'train_support': model['count'],
            'coefficient_sha256': p.sha(p.canonical(model['coefficients'])) if model['coefficients'] is not None else None,
            'private_result_sha256': private['receipt_sha256'],
            'array_sha256': hashes,
            'evaluation': evaluation,
          }
        )
        print(name, b, c['family'], c['delay_samples'], fold['fold'], model['status'], flush=True)
      records.append({'config': c, 'parameter_count': params, 'folds': folds})
    selection = cv.choose(records, name)
    # Selection uses fold RMSE only. Pooled coefficients never receive DEV metrics.
    identity = {
      'stage': name,
      'speed_bin': b,
      'units': 'STEERING_WHEEL_ANGLE_DEGREES' if name == 'STAGE_A' else 'YAW_RAD_PER_S_CONDITIONAL_DEVICE_FRAME',
      'source_class_sha256': v.policy()['source_equivalence_sha256'],
      'empirical_profile_sha256': v.routes()[0]['empirical_profile_sha256'],
      'route_set_sha256': v.policy()['route_set_sha256'],
      'cv_policy_sha256': v.policy()['receipt_sha256'],
      'fold_result_sha256': p.sha(p.canonical(records)),
      'environment': env,
      'code_sha256': v.code_identity(),
      'timebase_sha256': p.alignment_policy()['receipt_sha256'],
      'mask_policy_sha256': p.policy()['receipt_sha256'],
      'metric_policy_sha256': p.metric_policy()['receipt_sha256'],
    }
    pooled = [run for route in v.routes() for run in data[route['route_id']][b]]
    final = refit(pooled, selection, identity, store / 'models' / (name + '-' + b + '.json'))
    if final:
      model_hashes[b] = final['receipt_sha256']
    result[b] = {'candidates': records, 'selection': selection, 'final_model_sha256': model_hashes.get(b)}
    p.persist(
      store / (name + '-' + b + '-cv.json'),
      p.seal({'schema': 'EMPIRICAL_PLANT_V3_BIN_CV_V1', **result[b], 'stage': name, 'speed_bin': b, 'policy_sha256': v.policy()['receipt_sha256']}),
    )
  return result, model_hashes


def yaw_admission(yaw, profile):
  folds = []
  for fold in v.folds()['folds']:
    by_route = {rid: yaw[rid] for rid in (fold['train_route'], fold['development_route'])}
    roles = {'TRAIN': by_route[fold['train_route']], 'DEVELOPMENT': by_route[fold['development_route']]}
    admission = g2.yaw_admission(roles, by_route, profile)
    support = {}
    h = admission['selection'].get('hypothesis')
    for rid, receipts in by_route.items():
      support[rid] = {b: len(m.design(cross.yaw_runs(receipts, h, profile, b), p.family_policy()['candidates'][0])[1]) if h is not None else 0 for b in v.BINS}
    folds.append({**fold, 'admission': admission, 'common_design_support': support})
  consistent = cv.yaw_consistent([x['admission'] for x in folds])
  bins = [b for b in v.BINS if consistent and all(x['common_design_support'][x['development_route']][b] >= 201 for x in folds)]
  return {
    'state': 'YAW_UNIT_SUPPORTED_FRAME_PARTIAL' if bins else 'STAGE_B_SIGNAL_ADMISSION_BLOCKED',
    'admitted': bool(bins),
    'admitted_bins': bins,
    'folds': folds,
    'kinematic_support_only': True,
    'vehicle_frame_calibrated': False,
    'continuous_scale_fitted': False,
  }


def run(old_store, store, source_store, roots):
  old_store, store = cache.distinct_stores(old_store, store)
  env = g2.environment()
  v.require_frozen(store)
  before = cache.tree_identity(old_store)
  data, yaw, profile, integrity = cache.load(old_store, store, source_store, roots)
  stage_a, a_hashes = stage(data, store, 'STAGE_A', env)
  del data
  admission = yaw_admission(yaw, profile)
  stage_b, b_hashes = {}, {}
  if admission['admitted']:
    h = admission['folds'][0]['admission']['selection']['hypothesis']
    data = {rid: {b: cross.yaw_runs(rows, h, profile, b) if b in admission['admitted_bins'] else [] for b in v.BINS} for rid, rows in yaw.items()}
    stage_b, b_hashes = stage(data, store, 'STAGE_B', env)
  after = cache.tree_identity(old_store)
  if after != before:
    raise ValueError('V2_STORE_CHANGED')
  result = p.seal(
    {
      'schema': 'EMPIRICAL_PLANT_V3_PRIVATE_RESULTS_V1',
      'policy_sha256': v.policy()['receipt_sha256'],
      'folds_sha256': v.folds()['receipt_sha256'],
      'integrity_sha256': integrity['receipt_sha256'],
      'v2_private_before_sha256': before,
      'v2_private_after_sha256': after,
      'environment': env,
      'stage_a': stage_a,
      'yaw_admission': admission,
      'stage_b': stage_b,
      'models': {'STAGE_A': a_hashes, 'STAGE_B': b_hashes},
      'holdout_opened': False,
      'stage_c': 'NOT_RUN',
      'stage_c_state': 'STAGE_C_PENDING_FUTURE_HOLDOUT',
      'candidate_execution': 'NOT_RUN',
    }
  )
  p.persist(store / 'results.json', result)
  package = holdout_package(result['models'], result['receipt_sha256'])
  p.persist(store / 'holdout-package.json', package)
  return result, package


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  for field in ('old-store', 'store', 'source-store'):
    parser.add_argument('--' + field, required=True)
  parser.add_argument('--root', action='append', required=True)
  parser.add_argument('--freeze-policy', action='store_true')
  args = parser.parse_args()
  cache.distinct_stores(args.old_store, args.store)
  if args.freeze_policy:
    v.freeze(Path(args.store))
    print(v.policy()['receipt_sha256'])
    return
  result, package = run(args.old_store, args.store, args.source_store, args.root)
  print(result['receipt_sha256'], package['receipt_sha256'], flush=True)


if __name__ == '__main__':
  main()
