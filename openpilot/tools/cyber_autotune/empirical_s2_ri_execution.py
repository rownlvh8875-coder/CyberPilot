"""Read sealed rlog caches only; additive rate-free identities and input-only audit."""
import argparse
import os
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as store
from openpilot.tools.cyber_autotune import empirical_identifiability_execution as read
from openpilot.tools.cyber_autotune import empirical_identifiability_policy as old_policy
from openpilot.tools.cyber_autotune.empirical_identifiability_math import rank_diagnostic
from openpilot.tools.cyber_autotune import empirical_s2_ri_policy as policy
from openpilot.tools.cyber_autotune import empirical_s2_ri_admission as admission
from openpilot.tools.cyber_autotune import empirical_s2_ri_math as m

COUNTS = ('base_rows', 'causal_valid_rows', 'model_eligible_rows', 'grid_compliant_rows', 'grid_inconsistent_available_rows',
          'segments', 'causal_runs', 'excluded_pressed_rows', 'excluded_inactive_rows', 'excluded_fault_rows',
          'release_count', 'reengagement_count')


def preflight(root, pol):
  if pol != policy.policy():
    raise ValueError('FROZEN_S2_RI_POLICY_DRIFT')
  # Reuse metadata-only exact final resolver and guard, not rate-dependent row admission.
  return read.preflight(root, old_policy.policy())


def numerical_view(a, d, scope):
  return {'tick': d['angle_tick'], 'command': a['command.normalized'], 'speed': a['state.speed_mps'],
          'streak': d['streak_all' if scope == m.SCOPES[0] else 'streak_non_rail']}


def independence_proof(a):
  """Original, deleted, NaN and arbitrary rate/request/generic identity overlays."""
  expected = admission.derive(a)
  n = len(a['grid_time_ns'])
  base = {k: v for k, v in a.items() if k not in ('state.rate', 'state.rate.available')}
  overlays = [base]
  for value, available in ((np.full(n, np.nan), np.zeros(n, bool)), (np.arange(n, dtype=float)+1000, np.ones(n, bool))):
    overlays.append({**base, 'state.rate': value, 'state.rate.available': available,
      'causal_required_valid': np.zeros(n, bool), 'causal_run_id': np.full(n, -1),
      'within_causal_run_index': np.full(n, -1), 'run_boundary': np.ones(n, bool),
      'consumed_input_snapshot_sha256': np.full(n, '0'*64)})
  overlays.append({**base, 'control.requested': np.full(n, np.nan), 'control.requested.available': np.zeros(n, bool)})
  for overlay in overlays:
    actual = admission.derive(overlay)
    if set(actual) != set(expected) or any(actual[k].tobytes() != expected[k].tobytes() for k in expected):
      raise ValueError('S2_RI_HIDDEN_RATE_DEPENDENCY_OR_REQUEST_DEPENDENCY')
    for scope in m.SCOPES:
      left, right = numerical_view(a, expected, scope), numerical_view(overlay, actual, scope)
      for form in m.FORMS:
        ix, iy = m.feature_indices(left, form), m.feature_indices(right, form)
        if ix.tobytes() != iy.tobytes() or m.feature_matrix(left, ix, form)[0].tobytes() != m.feature_matrix(right, iy, form)[0].tobytes():
          raise ValueError('S2_RI_HIDDEN_RATE_DEPENDENCY_IN_HISTORY_OR_X')
  return True


def scope_support(data):
  s = data['streak']
  ids = m.target_indices(data)
  delta = data['tick'][ids+1]-data['tick'][ids]
  good = s > 0
  return {'eligible_rows': int(good.sum()), 'target_available_rows': len(ids),
    'target_zero_count': int(np.count_nonzero(delta == 0)), 'target_positive_count': int(np.count_nonzero(delta > 0)),
    'target_negative_count': int(np.count_nonzero(delta < 0)),
    'target_zero_fraction': float(np.mean(delta == 0)) if len(delta) else None,
    'unique_delta_level_count': len(np.unique(delta)), 'contributing_segments': len(np.unique(data['segment'][ids])),
    'contributing_causal_runs': len(np.unique(data['causal'][ids])),
    'longest_eligible_history': int(s.max()) if len(s) else 0,
    'eligible_speed_bins': read.speed_counts(data['speed'][good]),
    'target_speed_bins': read.speed_counts(data['speed'][ids]),
    'history_support_L1_to_L45': [int(np.count_nonzero(s[ids] >= length+1)) for length in range(1, 46)]}


def run(root, output, replica):
  root = store.safe(root)
  output = store.external(output, [root, '/mnt/d/carrotlog', '/mnt/d/CarrotLogs'])
  if replica not in ('repeat-1', 'repeat-2'):
    raise ValueError('EXACT_TWO_REPLICA_NAMES_REQUIRED')
  if any(os.environ.get(k) != '1' for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS')):
    raise ValueError('SINGLE_THREAD_ENVIRONMENT_REQUIRED')
  pol = policy.freeze(output)
  _, _, manifest, records, files = preflight(root, pol)
  destination = output/replica
  receipt = p.seal({'schema': 'EMPIRICAL_S2_RI_INPUT_ADMISSION_V1', 'policy_sha256': pol['receipt_sha256'],
    'manifest_sha256': manifest['receipt_sha256'], 'segment_receipts': [s['receipt_sha256'] for _, s in records],
    'segment_bindings': [{'content_sha256': s['segment_sha256'], 'receipt_sha256': s['receipt_sha256'],
                         'route_id': s['route_id'], 'rows': s['arrays']['grid_time_ns']['shape'][0]} for _, s in records],
    'input_file_set_sha256': p.sha(p.canonical(files)), 'array_access_before_admission': False})
  p.persist(destination/'admission.json', receipt)
  read.verify_files(root, files)
  routes = {rid: {scope: [] for scope in m.SCOPES} for rid in pol['route_ids']}
  counts = {rid: dict.fromkeys(COUNTS, 0) for rid in routes}
  derived_receipts = []
  derived_index = []
  causal_offset = 0
  for number, (base, segment) in enumerate(records):
    # Rate read only for the requested adversarial original/NaN/finite views.
    fields = (*pol['numeric_fields'], *pol['adversarial_auxiliary_read_fields'])
    a = {k: read.read_array(base/'arrays'/read.array_name(k), segment['arrays'][k]) for k in fields}
    d = admission.derive(a)
    independence_proof(a)
    derived = dict(d)
    for label, scope in (('all', m.SCOPES[0]), ('non_rail', m.SCOPES[1])):
      data = numerical_view(a, d, scope)
      indices = m.target_indices(data)
      target_valid = np.zeros(len(data['tick']), bool)
      target_valid[indices] = True
      delta = np.zeros(len(data['tick']), dtype=np.int64)
      delta[indices] = data['tick'][indices+1]-data['tick'][indices]
      derived['target_available_'+label], derived['delta_tick_'+label] = target_valid, delta
      data.update({'segment': np.full(len(delta), number, dtype=np.int64),
                   'causal': np.where(d['s2_ri_causal_run_id'] >= 0, d['s2_ri_causal_run_id']+causal_offset, -1)})
      routes[segment['route_id']][scope].append(data)
    causal_offset += max(0, int(d['s2_ri_causal_run_id'].max())+1)
    c = counts[segment['route_id']]
    c['base_rows'] += len(d['model_eligible'])
    c['causal_valid_rows'] += int(d['s2_ri_causal_valid'].sum())
    c['model_eligible_rows'] += int(d['model_eligible'].sum())
    available = a['state.angle_deg.available']
    c['grid_compliant_rows'] += int(np.count_nonzero(available & d['angle_grid_valid']))
    c['grid_inconsistent_available_rows'] += int(np.count_nonzero(available & ~d['angle_grid_valid']))
    c['segments'] += 1
    c['causal_runs'] += max(0, int(d['s2_ri_causal_run_id'].max())+1)
    for key, field, value in (('excluded_pressed_rows', 'state.driver_pressed', 1), ('excluded_inactive_rows', 'control.lat_active', 0)):
      c[key] += int(np.count_nonzero(a[field+'.available'] & (a[field] == value)))
    c['excluded_fault_rows'] += int(np.count_nonzero(
      (a['state.fault_temporary.available'] & (a['state.fault_temporary'] == 1))
      | (a['state.fault_permanent.available'] & (a['state.fault_permanent'] == 1))))
    for key, field, old, new in (('release_count', 'state.driver_pressed', 1, 0), ('reengagement_count', 'control.lat_active', 0, 1)):
      pair = a[field+'.available'][:-1] & a[field+'.available'][1:]
      c[key] += int(np.count_nonzero(pair & (a[field][:-1] == old) & (a[field][1:] == new)))
    path = destination/'segments'/segment['segment_sha256']
    bindings = {k: store.array_write(path/(k+'.npy'), np.ascontiguousarray(v)) for k, v in derived.items()}
    local = p.seal({'schema': 'EMPIRICAL_S2_RI_DERIVED_SEGMENT_V1', 'policy_sha256': pol['receipt_sha256'],
      'source_receipt_sha256': segment['receipt_sha256'], 'arrays': bindings,
      'rate_and_request_adversarial_exact': True})
    p.persist(path/'receipt.json', local)
    derived_receipts.append(local['receipt_sha256'])
    derived_index.append({'content_sha256': segment['segment_sha256'], 'receipt_sha256': local['receipt_sha256']})
    if (number+1) % 20 == 0:
      print('s2_ri_admitted_segments', number+1, flush=True)
  datasets = {rid: {scope: {k: np.concatenate([v[k] for v in parts]) for k in parts[0]}
                   for scope, parts in scopes.items()} for rid, scopes in routes.items()}
  datasets['POOLED'] = {scope: {k: np.concatenate([datasets[rid][scope][k] for rid in pol['route_ids']])
                               for k in datasets[pol['route_ids'][0]][scope]} for scope in m.SCOPES}
  counts['POOLED'] = {k: sum(counts[r][k] for r in pol['route_ids']) for k in COUNTS}
  support = {rid: {scope: scope_support(data) for scope, data in scopes.items()} for rid, scopes in datasets.items()}
  forms = []
  for scope in m.SCOPES:
    for form in m.FORMS:
      diagnostics = {}
      for rid in [*pol['route_ids'], 'POOLED']:
        data = datasets[rid][scope]
        indices = m.feature_indices(data, form)
        matrix, names = m.feature_matrix(data, indices, form)
        value = rank_diagnostic(matrix, names)
        # All adversarial views already proved exact X bytes per segment.
        # Independently repeat SVD on their identical concatenated X, no cached rank.
        for _ in range(2):
          if rank_diagnostic(matrix, names) != value:
            raise ValueError('S2_RI_ADVERSARIAL_RANK_REPEATABILITY_FAILURE')
        diagnostics[rid] = {**value, 'next_state_available': len(indices),
          'speed_bins_at_feature_endpoint': read.speed_counts(data['speed'][indices]),
          'feature_order_sha256': p.sha(p.canonical(names))}
        del matrix
      forms.append({'scope': scope, 'form': list(form), 'diagnostics': diagnostics})
      print('s2_ri_completed_boundary_form', scope, form, flush=True)
  read.verify_files(root, files)
  result = p.seal({'schema': 'EMPIRICAL_S2_RI_AUDIT_RESULTS_V1', 'policy_sha256': pol['receipt_sha256'],
    'admission_sha256': receipt['receipt_sha256'], 'derived_receipt_set_sha256': p.sha(p.canonical(derived_receipts)),
    'stream_count': len(records), 'counts': counts, 'support': support, 'forms': forms,
    'rate_dependency': 'NONE', 'request_dependency': 'NONE',
    'rate_views': ['ORIGINAL', 'DELETED', 'ALL_NAN_UNAVAILABLE', 'ARBITRARY_FINITE_AVAILABLE'],
    'generic_id_and_snapshot_overlays': 'EXACT_INVARIANT_NOT_GATES',
    'adversarial_derived_arrays_and_X_bytes_exact': True, 'adversarial_rank_executions_per_form': 3,
    'input_bytes_unchanged': True, 'qlog_arrays_opened': 0, 'raw_logs_opened': 0,
    'authority': policy.AUTHORITY})
  p.persist(destination/'derived-index.json', p.seal({'schema': 'EMPIRICAL_S2_RI_DERIVED_INDEX_V1', 'segments': derived_index}))
  p.persist(destination/'results.json', result)
  return result


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--input-store', required=True)
  parser.add_argument('--output-store', required=True)
  parser.add_argument('--replica', required=True, choices=['repeat-1', 'repeat-2'])
  args = parser.parse_args()
  run(args.input_store, args.output_store, args.replica)


if __name__ == '__main__':
  main()
