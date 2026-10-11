"""Exact two-qlog extraction and virtual additive merge. No discovery or model operations."""
import argparse
from collections import Counter
import platform

import numpy as np

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_causal_dataset_policy as base
from openpilot.tools.cyber_autotune import empirical_causal_dataset_reader as reader
from openpilot.tools.cyber_autotune import empirical_causal_dataset_alignment as alignment
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage
from openpilot.tools.cyber_autotune import empirical_causal_dataset_execution as legacy
from openpilot.tools.cyber_autotune import empirical_causal_dataset_publication as historical
from openpilot.tools.cyber_autotune import empirical_source_execution as previous
from openpilot.tools.cyber_autotune import empirical_source_metadata as metadata
from openpilot.tools.cyber_autotune import empirical_cross_root_inventory as logs
from openpilot.tools.cyber_autotune import empirical_qlog_source_audit as source_audit
from openpilot.tools.cyber_autotune import empirical_qlog_reconciliation_policy as policy


def origin_overlay(records, new_digests):
  if [r['ordinal'] for r in records] != list(range(len(records))):
    raise ValueError('COMPLETE_ORDINAL_LINEAGE_REQUIRED')
  result, offset = [], 0
  for record in records:
    count = record['coverage']['total_grid_samples']
    result.append({'segment_sha256': record['segment_sha256'], 'ordinal': record['ordinal'],
      'store_key': 'new_qlog' if record['segment_sha256'] in new_digests else 'historical_rlog',
      'segment_receipt_sha256': record['receipt_sha256'], 'row_count': count,
      'original_route_global_start': record['route_global_start'], 'reconciled_route_global_start': offset,
      'overlay_rule': 'RECONCILED_START_PLUS_UNCHANGED_LOCAL_ALIGNED_ROW_INDEX'})
    offset += count
  return result


def paths(store, causal, v2, v3, source, roots):
  inputs = list(map(storage.safe, (causal, v2, v3, source)))
  approved = previous.approved_root_map(roots)
  destination = storage.external(store, [*inputs, *approved.values()])
  if len(set(inputs)) != 4 or any(a in b.parents or b in a.parents for a in inputs for b in inputs if a != b):
    raise ValueError('DISTINCT_NONOVERLAPPING_INPUT_STORES_REQUIRED')
  return destination, inputs, approved


def prepare(store, causal, v2, v3, source, source_repo, roots):
  store, (causal, v2, v3, source), approved = paths(store, causal, v2, v3, source, roots)
  public = historical.load()
  route_set = base.read(causal/'route-set.json')
  if route_set != public['empirical-causal-train-dev-route-set-v1.json']:
    raise ValueError('EXACT_PRIOR_ROUTE_SET_REQUIRED')
  old = base.read(causal/'repeat-1/manifest.json')
  repeat = public['empirical-causal-train-dev-repeatability-v1.json']
  if old['receipt_sha256'] != repeat['dataset_manifest_sha256']:
    raise ValueError('EXACT_PRIOR_RLOG_DATASET_REQUIRED')
  expected = base.read(causal/'authorization.json')['historical_tree_sha256']
  trees = {k: storage.tree_identity(path) for k, path in zip(('causal', 'v2', 'v3', 'source'), (causal, v2, v3, source), strict=True)}
  if any(trees[k] != expected[k] for k in ('v2', 'v3', 'source')):
    raise ValueError('HISTORICAL_PRIVATE_TREE_DRIFT')
  if storage.tree_identity(causal/'repeat-1') != repeat['replica_tree_sha256']:
    raise ValueError('HISTORICAL_RLOG_ARRAY_DRIFT')
  manifest = base.read(v2/'manifest.json')
  selected = policy.resolve_exclusions(route_set['routes'], manifest['routes'])
  first = route_set['routes'][0]
  fingerprint = base.read(source/'fingerprints'/(first['source_commit']+'.json'))
  adapter = base.read(source/'adapters-final'/(first['source_commit']+'.json'))
  base.validate_source(first, fingerprint, adapter, base.read(source/'public-origin.json'))
  audit = source_audit.audit(source_repo, fingerprint)
  if audit['status'] != 'QLOG_SOURCE_SEMANTICS_COMPLETE':
    raise ValueError('QLOG_SOURCE_SEMANTICS_INCOMPLETE')
  bindings, services = [], []
  for route, segment in selected:
    base.validate_source(route, fingerprint, adapter, base.read(source/'public-origin.json'))
    path = previous.source_location(segment['location'], approved)
    if path.name != 'qlog.zst' or logs.file_sha(path) != segment['source_sha256']:
      raise ValueError('EXACT_HISTORICAL_QLOG_HASH_REQUIRED')
    meta = base.read(source/'segments'/route['source_commit']/(segment['source_sha256']+'.json'))
    if meta['receipt_sha256'] != segment['metadata_sha256'] or meta['status'] != 'SOURCE_SPECIFIC_METADATA_REVALIDATED':
      raise ValueError('QLOG_METADATA_IDENTITY_CONFLICT')
    # Only historical receipt identity, not numeric cache deserialization, before authorization.
    opening = base.read(v2/'openings'/route['route_id']/(segment['source_sha256']+'.json'))
    if opening['source_sha256'] != segment['source_sha256'] or opening['authorization_sha256'] != base.read(v2/'authorization.json')['receipt_sha256']:
      raise ValueError('HISTORICAL_QLOG_OPENING_IDENTITY_CONFLICT')
    bindings.append({'route_id': route['route_id'], **segment, 'file_size': path.stat().st_size,
      'historical_opening_sha256': opening['receipt_sha256'], 'source_commit': route['source_commit'],
      'full_carparams_sha256': route['full_carparams_sha256'], 'empirical_profile_sha256': route['empirical_profile_sha256']})
    services.append({'route_id': route['route_id'], 'segment_sha256': segment['source_sha256'],
                     'envelope_counts': meta['metadata']['envelope_counts']})
  pol = policy.policy()
  p.persist(store/'policy.json', pol)
  p.persist(store/'source-audit.json', audit)
  p.persist(store/'historical-trees-before.json', p.seal({'schema': 'QLOG_HISTORICAL_TREE_PINS_V1', 'trees': trees}))
  auth = p.seal({'schema': 'EMPIRICAL_QLOG_NUMERIC_AUTHORIZATION_V1',
    'policy_sha256': pol['receipt_sha256'], 'historical_route_set_sha256': route_set['receipt_sha256'],
    'source_audit_sha256': audit['receipt_sha256'], 'source_fingerprint_sha256': fingerprint['receipt_sha256'],
    'recorded_adapter_sha256': adapter['receipt_sha256'], 'source_schema_sha256': p.sha(p.canonical({
      k: v['file_sha256'] for k, v in fingerprint['files'].items() if k.startswith('schema_')})),
    'segments': bindings, 'signal_whitelist_sha256': p.sha(p.canonical(base.WHITELIST)),
    'alignment_code_sha256': base.code_identity()['alignment'],
    'numeric_adapter_sha256': base.code_identity()['reader'],
    'output_store_identity_sha256': p.sha(str(store).encode()), 'historical_tree_sha256': trees,
    'holdout_opening_allowed': False, 'role': base.ROLE})
  p.persist(store/'authorization.json', auth)
  p.persist(store/'service-inventory.json', p.seal({'schema': 'EMPIRICAL_QLOG_SERVICE_INVENTORY_V1',
    'source_audit_sha256': audit['receipt_sha256'], 'segments': services, 'numeric_opened': False}))
  return auth


def validate_array(path, binding):
  path = storage.safe(path)
  if p.sha(path.read_bytes()) != binding['file_sha256']:
    raise ValueError('QLOG_ARRAY_BYTE_DRIFT')
  array = np.load(path, allow_pickle=False)
  if (array.dtype.str != binding['dtype'] or list(array.shape) != binding['shape']
      or p.sha(array.tobytes(order='C')) != binding['array_sha256'] or not array.flags.c_contiguous):
    raise ValueError('QLOG_ARRAY_LAYOUT_DRIFT')
  return array


def extract(store, replica, causal, v2, v3, source, roots):
  store, (causal, v2, v3, source), approved = paths(store, causal, v2, v3, source, roots)
  if replica not in ('repeat-1', 'repeat-2'):
    raise ValueError('EXACT_REPLICA_REQUIRED')
  pol, auth, audit = (base.read(store/n) for n in ('policy.json', 'authorization.json', 'source-audit.json'))
  if (pol != policy.policy() or auth['policy_sha256'] != pol['receipt_sha256']
      or auth['source_audit_sha256'] != audit['receipt_sha256'] or audit['status'] != 'QLOG_SOURCE_SEMANTICS_COMPLETE'
      or auth['output_store_identity_sha256'] != p.sha(str(store).encode())):
    raise ValueError('SEALED_QLOG_POLICY_AUTHORIZATION_DRIFT')
  for name, path in zip(('causal', 'v2', 'v3', 'source'), (causal, v2, v3, source), strict=True):
    if storage.tree_identity(path) != auth['historical_tree_sha256'][name]:
      raise ValueError('HISTORICAL_INPUT_DRIFT')
  route_set = base.read(causal/'route-set.json')
  if route_set['receipt_sha256'] != auth['historical_route_set_sha256']:
    raise ValueError('HISTORICAL_ROUTE_SET_DRIFT')
  resolved = policy.resolve_exclusions(route_set['routes'], base.read(v2/'manifest.json')['routes'])
  if [(r['route_id'], s['source_sha256'], s['ordinal'], s['location']) for r, s in resolved] != [
      (s['route_id'], s['source_sha256'], s['ordinal'], s['location']) for s in auth['segments']]:
    raise ValueError('EXACT_QLOG_SELECTION_DRIFT')
  destination = store/replica
  new_records = {}
  for route, segment in resolved:
    rid, digest = route['route_id'], segment['source_sha256']
    policy.require_segment(auth, rid, digest, segment['kind'])
    path = previous.source_location(segment['location'], approved)
    binding = next(s for s in auth['segments'] if s['source_sha256'] == digest)
    if path.name != 'qlog.zst' or path.stat().st_size != binding['file_size'] or logs.file_sha(path) != digest:
      raise ValueError('QLOG_SOURCE_DRIFT')
    fingerprint = base.read(source/'fingerprints'/(route['source_commit']+'.json'))
    adapter = base.read(source/'adapters-final'/(route['source_commit']+'.json'))
    base.validate_source(route, fingerprint, adapter, base.read(source/'public-origin.json'))
    if fingerprint['receipt_sha256'] != auth['source_fingerprint_sha256'] or adapter['receipt_sha256'] != auth['recorded_adapter_sha256']:
      raise ValueError('QLOG_ADAPTER_DRIFT')
    historic_meta = base.read(source/'segments'/route['source_commit']/(digest+'.json'))
    if historic_meta['receipt_sha256'] != segment['metadata_sha256']:
      raise ValueError('QLOG_METADATA_DRIFT')
    out = destination/'routes'/rid/'segments'/digest
    opening = p.seal({'schema': 'EMPIRICAL_QLOG_EXTRACTION_OPENING_V1', 'authorization_sha256': auth['receipt_sha256'],
      'route_id': rid, 'segment_sha256': digest, 'source_audit_sha256': audit['receipt_sha256'],
      'role': base.ROLE, 'holdout_opened': False})
    p.persist(out/'opening.json', opening)
    if (out/'receipt.json').exists():
      record = base.read(out/'receipt.json')
      if (record['authorization_sha256'] != auth['receipt_sha256'] or record['opening_sha256'] != opening['receipt_sha256']
          or record['route_id'] != rid or record['segment_sha256'] != digest or record['ordinal'] != segment['ordinal']):
        raise ValueError('QLOG_RESUME_IDENTITY_DRIFT')
      for field, array_binding in record['arrays'].items():
        validate_array(out/'arrays'/(field+'.npy'), array_binding)
      validate_array(out/'source-command.npy', record['source_command_array'])
      if base.read(out/'config.json')['receipt_sha256'] != record['config_sha256']:
        raise ValueError('QLOG_RESUME_CONFIG_DRIFT')
    else:
      schema = metadata.schema_from_source(fingerprint, source/'schemas'/route['source_commit'])
      streams = reader.numeric(logs.log_events(path, schema))
      config = reader.configuration(streams, route)
      if config['logger_start_sha256'] != historic_meta['metadata']['init']['logger_start_sha256']:
        raise ValueError('QLOG_LOGGER_IDENTITY_CONFLICT')
      p.persist(out/'config.json', config)
      arrays, coverage = alignment.build(streams, config['receipt_sha256'], segment['ordinal'], 0)
      bridge = reader.bridge(streams['command'], config['runtime_steer_max'])
      prior = base.read(v2/'segments'/rid/(digest+'.json'))
      if (prior['adapter_sha256'] != adapter['receipt_sha256'] or prior['runtime_steer_max'] != 409
          or prior['source_sha256'] != digest or prior['role'] != 'TRAIN'):
        raise ValueError('HISTORICAL_QLOG_CACHE_IDENTITY_CONFLICT')
      old_route = base.read(v2/'routes'/(rid+'.json'))
      if prior['receipt_sha256'] not in {s['receipt_sha256'] for s in old_route['segments']}:
        raise ValueError('HISTORICAL_QLOG_CACHE_RECEIPT_CONFLICT')
      checks = legacy.compare_legacy(arrays, coverage, prior, bridge)
      fields = {name: storage.array_write(out/'arrays'/(name+'.npy'), value) for name, value in sorted(arrays.items())}
      commands = np.asarray([[r['raw'], r['normalized'], r['valid']] for r in streams['command']], dtype='<f8').reshape(-1, 3)
      record = p.seal({'schema': 'EMPIRICAL_QLOG_CAUSAL_SEGMENT_V1', 'route_id': rid, 'segment_sha256': digest,
        'ordinal': segment['ordinal'], 'route_global_start': 0, 'metadata_sha256': historic_meta['receipt_sha256'],
        'historical_segment_sha256': prior['receipt_sha256'], 'authorization_sha256': auth['receipt_sha256'],
        'opening_sha256': opening['receipt_sha256'], 'config_sha256': config['receipt_sha256'], 'arrays': fields,
        'source_command_array': storage.array_write(out/'source-command.npy', commands),
        'coverage': coverage, 'bridge': bridge, 'legacy_checks': checks,
        'cadence': 'DOWNSAMPLED_RETAINED_EVENT_SEMANTICS_20MS_POLICY_UNCHANGED',
        'unavailable_fields': base.UNAVAILABLE, 'model_operations': 'NOT_RUN'})
      p.persist(out/'receipt.json', record)
    if logs.file_sha(path) != digest:
      raise ValueError('QLOG_SOURCE_CHANGED_DURING_EXTRACTION')
    new_records[digest] = record
    print(replica, 'qlog extracted or exact-resumed', len(new_records), '/ 2', flush=True)
  result = reconcile(causal, destination, route_set['routes'], new_records, auth)
  p.persist(destination/'manifest.json', result)
  return result


def reconcile(causal, destination, routes, new_records, auth):
  summaries = []
  old_manifest = base.read(causal/'repeat-1/manifest.json')
  for route in routes:
    rid = route['route_id']
    old_route = next(r for r in old_manifest['routes'] if r['route_id'] == rid)
    records, commands = [], []
    for item in sorted(base.read(causal/'source-manifest.json')['routes'][rid] + [
        s for s in auth['segments'] if s['route_id'] == rid], key=lambda s: s['ordinal']):
      digest = item['source_sha256']
      out = (destination if digest in new_records else causal/'repeat-1')/'routes'/rid/'segments'/digest
      record = new_records[digest] if digest in new_records else base.read(out/'receipt.json')
      if digest not in new_records and record['receipt_sha256'] not in old_route['segments']:
        raise ValueError('HISTORICAL_RLOG_REFERENCE_DRIFT')
      if record['config_sha256'] != old_route['config_sha256']:
        raise ValueError('ROUTE_CONFIG_DRIFT')
      if record['route_id'] != rid or record['segment_sha256'] != digest or record['ordinal'] != item['ordinal']:
        raise ValueError('RECONCILIATION_SEGMENT_IDENTITY_CONFLICT')
      values = validate_array(out/'source-command.npy', record['source_command_array'])
      commands.extend({'raw': float(x[0]), 'normalized': float(x[1]), 'valid': bool(x[2])} for x in values)
      records.append(record)
    overlay = origin_overlay(records, set(new_records))
    full_set = p.sha(p.canonical(sorted(r['segment_sha256'] for r in records)))
    counts, fields, masks, lengths, transitions = Counter(), Counter(), Counter(), Counter(), Counter()
    bins = {b: Counter() for b in alignment.BINS}
    for record in records:
      c = record['coverage']
      for key in ('total_grid_samples', 'diagnostic_valid', 'causal_required_valid', 'causal_runs', 'gyro_xyz_available',
                  'gyro_acquisition_clock_failures', 'gyro_rejected', 'simultaneous_command_coverage'):
        counts[key] += c[key]
      fields.update(c['required_field_coverage'])
      masks.update(c['mask_reason_counts'])
      lengths.update(c['causal_run_length_distribution'])
      transitions.update(c['transitions'])
      for b in alignment.BINS:
        bins[b].update({k: v for k, v in c['bins'][b].items() if k != 'longest_contiguous_samples'})
    bridge = reader.bridge(commands, 409)
    expected = next(r for r in base.inputs()['empirical-plant-v3-route-coverage-v1.json']['routes'] if r['route_id'] == rid)
    checks = {'full_source_set': full_set == route['source_set_sha256'],
      'segment_count': len(records) == route['historical_segment_count'],
      'grid_count': counts['total_grid_samples'] == expected['coverage']['total_grid_samples'],
      'diagnostic_valid': counts['diagnostic_valid'] == expected['coverage']['diagnostic_valid'],
      'bridge_counts': all(bridge[k] == expected['bridge'][k] for k in (
        'total', 'eligible', 'invalid', 'steer_max', 'exact_ratio_match_count', 'float32_expected_exact_count',
        'sign_conflicts', 'domain_conflicts', 'raw_saturated_count', 'normalized_saturated_count')),
      'per_bin_accounting': all(bins[b][k] == expected['coverage']['bins'][b][k]
        for b in alignment.BINS for k in ('total_grid_samples', 'diagnostic_valid', 'contiguous_runs', 'common_design_rows')),
      'per_segment_exact': all(all(r['legacy_checks'].values()) for r in records)}
    ready = all(checks.values()) and bridge['status'] == 'ROUTE_COMMAND_BRIDGE_CONFIRMED' and all(fields[k] > 0 for k in alignment.REQUIRED)
    summary = p.seal({'schema': 'EMPIRICAL_QLOG_RECONCILED_ROUTE_V1', 'route_id': rid,
      'source_commit': route['source_commit'], 'full_carparams_sha256': route['full_carparams_sha256'],
      'empirical_profile_sha256': route['empirical_profile_sha256'], 'config_sha256': old_route['config_sha256'],
      'source_set_sha256': full_set, 'segment_count': len(records),
      'rlog_count': sum(x['store_key'] == 'historical_rlog' for x in overlay),
      'qlog_count': sum(x['store_key'] == 'new_qlog' for x in overlay),
      'segment_origins': overlay, 'coverage': dict(counts), 'required_field_coverage': dict(fields),
      'bins': {k: dict(v) for k, v in bins.items()}, 'mask_reason_counts': dict(masks),
      'causal_run_length_distribution': dict(lengths), 'transitions': dict(transitions),
      'bridge': bridge, 'legacy_checks': checks,
      'status': 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_READY' if ready else 'RETROSPECTIVE_CAUSAL_TRAIN_DEV_DATASET_BLOCKED',
      'role': base.ROLE, 'holdout_allowed': False, 'independent_validation_allowed': False})
    p.persist(destination/'routes'/rid/'reconciled-route-receipt.json', summary)
    summaries.append(summary)
  return p.seal({'schema': 'EMPIRICAL_QLOG_RECONCILED_DATASET_MANIFEST_V1',
    'authorization_sha256': auth['receipt_sha256'], 'historical_manifest_sha256': old_manifest['receipt_sha256'],
    'routes': summaries, 'new_segments': [new_records[k] for k in sorted(new_records)],
    'environment': {'python': platform.python_version(), 'numpy': np.__version__, 'threads': 1, 'rng': 'NONE'},
    'fitting': 'NOT_RUN', 'selection': 'NOT_RUN', 'holdout_opened': False})


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  for name in ('store', 'causal', 'v2', 'v3', 'source', 'source-repo'):
    parser.add_argument('--'+name, required=True)
  parser.add_argument('--root', action='append', required=True)
  parser.add_argument('--replica', choices=('repeat-1', 'repeat-2'), required=True)
  parser.add_argument('--prepare-only', action='store_true')
  args = parser.parse_args()
  prepare(args.store, args.causal, args.v2, args.v3, args.source, args.source_repo, args.root)
  if not args.prepare_only:
    extract(args.store, args.replica, args.causal, args.v2, args.v3, args.source, args.root)


if __name__ == '__main__':
  main()
