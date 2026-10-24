"""Read exact immutable causal caches, compute input-only diagnostics, never decode logs."""
import argparse
import io
import json
import os
import re

import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_final_readiness as readiness
from openpilot.tools.cyber_autotune import empirical_causal_support_guard as guard
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage
from openpilot.tools.cyber_autotune import empirical_identifiability_policy as policy
from openpilot.tools.cyber_autotune import empirical_identifiability_math as math


def read_json(path):
  value = json.loads(storage.safe(path).read_bytes())
  p.verify(value)
  return value


def array_name(name):
  if not re.fullmatch(r'[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*', name):
    raise ValueError('EXACT_ARRAY_FIELD_NAME_REQUIRED')
  return name+'.npy'


def read_array(path, binding):
  path = storage.safe(path)
  if path.suffix != '.npy':
    raise ValueError('NO_RAW_LOG_OPENING')
  data = path.read_bytes()
  if p.sha(data) != binding['file_sha256']:
    raise ValueError('ARRAY_FILE_HASH_CONFLICT')
  array = np.load(io.BytesIO(data), allow_pickle=False)
  if (array.dtype.hasobject or array.dtype.str != binding['dtype'] or list(array.shape) != binding['shape']
      or not array.flags.c_contiguous or binding['order'] != 'C'
      or p.sha(array.tobytes()) != binding['array_sha256']):
    raise ValueError('ARRAY_BINDING_CONFLICT')
  array.flags.writeable = False
  return array


def preflight(root, pol):
  """Check the entire exact source-set before the first numeric array access."""
  if pol != policy.policy():
    raise ValueError('FROZEN_POLICY_DRIFT')
  root = storage.safe(root)
  x = readiness.load()
  resolved = readiness.resolve(x)
  manifest = read_json(root/'repeat-1/manifest.json')
  auth = read_json(root/'authorization.json')
  excluded = set(pol['excluded_qlog_content_sha256'])
  digests = [s for ids in auth['segments'].values() for s in ids]
  if excluded.intersection(digests):
    raise ValueError('QLOG_CAUSAL_ADMISSION_FORBIDDEN')
  if (len(digests) != 154 or len(set(digests)) != 154 or set(auth['segments']) != set(pol['route_ids'])
      or auth['receipt_sha256'] != x[readiness.RLOG_AUTH]['private_authorization_sha256']
      or manifest['receipt_sha256'] != resolved['rlog_dataset_manifest_sha256']):
    raise ValueError('EXACT_154_RLOG_MANIFEST_REQUIRED')
  records, files = [], {}
  for relative in ('repeat-1/manifest.json', 'authorization.json'):
    files[relative] = p.sha((root/relative).read_bytes())
  for rid in sorted(auth['segments']):
    if not re.fullmatch('[0-9a-f]{64}', rid):
      raise ValueError('OPAQUE_ROUTE_ID_REQUIRED')
    route_records = []
    for digest in auth['segments'][rid]:
      if not re.fullmatch('[0-9a-f]{64}', digest):
        raise ValueError('EXACT_SEGMENT_CONTENT_ID_REQUIRED')
      base = root/'repeat-1/routes'/rid/'segments'/digest
      segment = read_json(base/'receipt.json')
      if segment['route_id'] != rid or segment['segment_sha256'] != digest:
        raise ValueError('SEGMENT_PATH_IDENTITY_CONFLICT')
      guard.require_segment(resolved, manifest, segment, x)
      config = read_json(base/'config.json')
      if config['receipt_sha256'] != segment['config_sha256']:
        raise ValueError('CONFIG_IDENTITY_DRIFT')
      for name in ('receipt.json', 'config.json'):
        files[(base/name).relative_to(root).as_posix()] = p.sha((base/name).read_bytes())
      for field, binding in segment['arrays'].items():
        path = storage.safe(base/'arrays'/array_name(field))
        files[path.relative_to(root).as_posix()] = binding['file_sha256']
      route_records.append((base, segment))
    route_records.sort(key=lambda pair: pair[1]['ordinal'])
    if len({s['ordinal'] for _, s in route_records}) != len(route_records):
      raise ValueError('DUPLICATE_SEGMENT_ORDINAL')
    records.extend(route_records)
  return x, resolved, manifest, records, files


def verify_files(root, pins):
  for relative, expected in pins.items():
    path = storage.safe(root/relative)
    if p.sha(path.read_bytes()) != expected:
      raise ValueError('IMMUTABLE_INPUT_CHANGED')


def next_pairs(data):
  s = data['streak']
  return np.flatnonzero((s[:-1] > 0) & (s[1:] == s[:-1]+1))


def speed_counts(speed):
  return {name: int(np.count_nonzero(mask)) for name, mask in (
    ('LOW', (speed >= 5) & (speed < 15)), ('MEDIUM', (speed >= 15) & (speed < 25)), ('HIGH', speed >= 25))}


def history_report(data):
  streak = data['streak']
  ends = (streak > 0) & np.r_[streak[1:] != streak[:-1]+1, True]
  lengths = streak[ends]
  results = []
  pairs = next_pairs(data)
  for length in math.HISTORIES:
    idx = np.flatnonzero(streak >= length)
    used = lengths[lengths >= length]
    windows_per_streak = used-length+1
    # Causal ids are globally namespaced by the receipt-bound segment loop.
    results.append({'history': length, 'eligible_windows': len(idx),
      'next_state_available': int(np.count_nonzero(streak[pairs] >= length)),
      'causal_runs_contributing': len(np.unique(data['causal'][idx])),
      'admitted_streaks_contributing': len(used), 'segments_contributing': len(np.unique(data['segment'][idx])),
      'usable_run_lengths_min_median_max': [float(v) for v in np.quantile(used, [0, .5, 1])] if len(used) else None,
      'windows_per_usable_run_min_median_max': [float(v) for v in np.quantile(windows_per_streak, [0, .5, 1])] if len(used) else None,
      'speed_bins_at_window_endpoint': speed_counts(data['speed'][idx]),
      'minimum_route_support_pass': len(idx) >= math.MIN_SUPPORT})
  return results


def excitation(data):
  idx = np.flatnonzero(data['streak'] > 0)
  pairs = next_pairs(data)
  raw, angle, rate, speed = (data[k][idx] for k in ('raw', 'angle', 'rate', 'speed'))
  delta = data['angle'][pairs+1]-data['angle'][pairs]
  a, b = data['raw'][pairs], data['raw'][pairs+1]
  quantized = np.rint(angle/.1)*.1
  grid = quantized.astype(np.float32).astype(np.float64)
  return {'base_rows': len(data['streak']), 'guard_admitted_rows': len(idx), 'adjacent_pairs': len(pairs),
    'command': {'finite': len(raw), 'unique_raw_levels': len(np.unique(raw)),
      'unique_normalized_levels': len(np.unique(data['command'][idx])), 'request_finite': len(idx),
      'zero_count': int(np.count_nonzero(raw == 0)), 'positive': int(np.count_nonzero(raw > 0)),
      'negative': int(np.count_nonzero(raw < 0)), 'rail_count': int(np.count_nonzero(abs(raw) == 409)),
      'transition_count': int(np.count_nonzero(a != b)), 'reversal_count': int(np.count_nonzero(a*b < 0))},
    'angle': {'finite': len(angle), 'unique_float_levels': len(np.unique(angle)),
      'unique_source_grid_codes': len(np.unique(np.rint(angle/.1))), 'float32_source_grid_compliant': int(np.count_nonzero(angle == grid)),
      'unchanged_adjacent_count': int(np.count_nonzero(delta == 0)),
      'unchanged_adjacent_fraction': float(np.mean(delta == 0)) if len(delta) else None,
      'positive_delta': int(np.count_nonzero(delta > 0)), 'negative_delta': int(np.count_nonzero(delta < 0))},
    'rate_native': {'finite': len(rate), 'unique_levels': len(np.unique(rate)), 'zero_count': int(np.count_nonzero(rate == 0)),
      'zero_fraction': float(np.mean(rate == 0)) if len(rate) else None, 'nonzero_count': int(np.count_nonzero(rate != 0)),
      'negative_count': int(np.count_nonzero(rate < 0)), 'positive_count': int(np.count_nonzero(rate > 0))},
    'speed': {'bins': speed_counts(speed), 'unique_levels': len(np.unique(speed)),
      'quantiles_0_50_95_100_mps': np.quantile(speed, [0, .5, .95, 1]).tolist() if len(speed) else None},
    'delta_angle': math.target_diagnostic(data, pairs),
    'rate_diagnostic': math.rate_diagnostic(data, pairs),
    'target_by_speed': {name: math.target_diagnostic(data, pairs[mask]) for name, mask in (
      ('LOW', (data['speed'][pairs] >= 5) & (data['speed'][pairs] < 15)),
      ('MEDIUM', (data['speed'][pairs] >= 15) & (data['speed'][pairs] < 25)),
      ('HIGH', data['speed'][pairs] >= 25))}}


def run(root, output, source_repo, replica):
  root = storage.safe(root)
  output = storage.external(output, [root, source_repo, '/mnt/d/carrotlog', '/mnt/d/CarrotLogs'])
  if replica not in ('repeat-1', 'repeat-2'):
    raise ValueError('EXACT_TWO_REPLICA_NAMES_REQUIRED')
  if any(os.environ.get(k) != '1' for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS')):
    raise ValueError('SINGLE_THREAD_ENVIRONMENT_REQUIRED')
  # Freeze precedes all cache arrays. Exact immutable source audit is also pre-array.
  pol = policy.freeze(output)
  source = policy.audit_source(source_repo)
  p.persist(output/'source-contract.json', source)
  x, resolved, manifest, records, files = preflight(root, pol)
  destination = output/replica
  admission = p.seal({'schema': 'EMPIRICAL_IDENTIFIABILITY_INPUT_ADMISSION_V1',
    'policy_sha256': pol['receipt_sha256'], 'manifest_sha256': manifest['receipt_sha256'],
    'source_contract_sha256': source['receipt_sha256'], 'segment_receipts': [s['receipt_sha256'] for _, s in records],
    'input_file_set_sha256': p.sha(p.canonical(files)), 'array_access_before_admission': False})
  p.persist(destination/'admission.json', admission)
  verify_files(root, files)
  routes = {rid: [] for rid in pol['route_ids']}
  coverage = {rid: {'segments': 0, 'fields': {}, 'context': {}, 'snapshot_sets': []} for rid in routes}
  run_base = 0
  for number, (base, segment) in enumerate(records):
    arrays = {name: read_array(base/'arrays'/array_name(name), b) for name, b in segment['arrays'].items()}
    mask = guard.eligible_rows(resolved, manifest, segment, arrays, x, history=1)
    streak = math.streaks(mask, arrays['causal_run_id'], arrays['within_causal_run_index'], arrays['grid_time_ns'])
    n = len(mask)
    data = {label: arrays[key] for label, key in (
      ('angle', 'state.angle_deg'), ('rate', 'state.rate'), ('command', 'command.normalized'), ('raw', 'command.raw'),
      ('request', 'control.requested'), ('speed', 'state.speed_mps'), ('state_time', 'state.time_ns'))}
    data.update({'streak': streak, 'segment': np.full(n, number, dtype=np.int64),
                 'causal': np.where(arrays['causal_run_id'] >= 0, arrays['causal_run_id']+run_base, -1)})
    run_base += int(max(0, arrays['causal_run_id'].max()+1))
    rid = segment['route_id']
    routes[rid].append(data)
    c = coverage[rid]
    c['segments'] += 1
    for name in ('control.requested', 'command.normalized', 'command.raw', 'state.angle_deg', 'state.rate',
                 'state.speed_mps', 'control.lat_active', 'state.driver_pressed', 'state.driver_torque', 'state.eps_fault'):
      c['fields'][name] = c['fields'].get(name, 0)+int(np.count_nonzero(arrays[name+'.available']))
    for name in ('active_rising', 'active_falling', 'pressed_rising', 'pressed_falling', 'run_boundary', 'segment_boundary'):
      c['context'][name] = c['context'].get(name, 0)+int(np.count_nonzero(arrays[name]))
    for key, field, value in (('active', 'control.lat_active', 1), ('inactive', 'control.lat_active', 0),
                              ('steering_pressed', 'state.driver_pressed', 1), ('eps_fault', 'state.eps_fault', 1)):
      c['context'][key] = c['context'].get(key, 0)+int(np.count_nonzero(arrays[field+'.available'] & (arrays[field] == value)))
    c['snapshot_sets'].append(segment['arrays']['consumed_input_snapshot_sha256']['array_sha256'])
    del arrays
    if (number+1) % 20 == 0:
      print('admitted_segments', number+1, flush=True)
  datasets = {rid: {k: np.concatenate([part[k] for part in parts]) for k in parts[0]} for rid, parts in routes.items()}
  datasets['POOLED'] = {k: np.concatenate([datasets[rid][k] for rid in pol['route_ids']]) for k in datasets[pol['route_ids'][0]]}
  summaries, histories = {}, {}
  for rid, data in datasets.items():
    summaries[rid] = excitation(data)
    histories[rid] = history_report(data)
  for c in coverage.values():
    c['snapshot_set_sha256'] = p.sha(p.canonical(c.pop('snapshot_sets')))
  results = {'policy_sha256': pol['receipt_sha256'], 'admission_sha256': admission['receipt_sha256'],
    'source_contract_sha256': source['receipt_sha256'], 'coverage': coverage, 'excitation': summaries,
    'history_support': histories, 'families': {}}
  for family, envelope in (('S1', math.LAGS), ('S2', math.HISTORIES)):
    forms = []
    for parameter in envelope:
      length = parameter+1 if family == 'S1' else parameter
      scopes, support = {}, []
      for rid, data in datasets.items():
        indices = np.flatnonzero(data['streak'] >= length)
        features, names = math.features(data, indices, family, parameter)
        scopes[rid] = math.rank_diagnostic(features, names)
        pairs = next_pairs(data)
        count = int(np.count_nonzero(data['streak'][pairs] >= length))
        scopes[rid]['next_state_available'] = count
        scopes[rid]['speed_bins_at_feature_endpoint'] = speed_counts(data['speed'][indices])
        scopes[rid]['feature_order_sha256'] = p.sha(p.canonical(names))
        if rid != 'POOLED':
          support.append(count)
        del features
      forms.append({'lag' if family == 'S1' else 'history': parameter, 'scopes': scopes,
                    'both_routes_next_state_support_at_least_201': math.support_gate(support)})
      print('completed_input_only_form', family, parameter, flush=True)
    results['families'][family] = forms
  verify_files(root, files)
  result = p.seal({'schema': 'EMPIRICAL_MODEL_FAMILY_IDENTIFIABILITY_RESULTS_V1', **results,
                   'historical_inputs_byte_identical': True, 'qlog_arrays_opened': 0, 'raw_logs_opened': 0,
                   'authority': policy.AUTHORITY})
  p.persist(destination/'results.json', result)
  return result


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--input-store', required=True)
  parser.add_argument('--output-store', required=True)
  parser.add_argument('--source-repo', required=True)
  parser.add_argument('--replica', required=True, choices=['repeat-1', 'repeat-2'])
  args = parser.parse_args()
  run(args.input_store, args.output_store, args.source_repo, args.replica)


if __name__ == '__main__':
  main()
