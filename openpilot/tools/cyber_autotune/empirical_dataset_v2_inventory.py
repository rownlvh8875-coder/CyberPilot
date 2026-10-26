"""Exact-root metadata inventory; media and numeric signal bodies are never accessed."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import subprocess

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_plant_signals as s
from openpilot.tools.cyber_autotune import empirical_signal_policy as q
from openpilot.tools.cyber_autotune import empirical_signal_publication as historical
from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as v


def read(path):
  return p.verify(json.loads(v.no_alias(path).read_bytes()))


def cached(path, binding):
  path = v.no_alias(path)
  atomic = v.no_alias(path.with_name(path.name + '.atomic'))
  for candidate in (atomic, path):
    if candidate.exists():
      row = read(candidate)
      if row.get('binding_sha256') != binding:
        raise ValueError('STALE_METADATA_CACHE')
      p.persist(path, row)
      return row
  return None


def lineage(relative):
  directory = Path(relative).parent
  match = re.fullmatch(r'(.+)--([0-9]+)', directory.name)
  if match is None:
    raise ValueError('SEGMENT_LINEAGE_REQUIRED')
  key = directory.parent.as_posix() + '/' + match[1]
  return p.sha(key.encode()), int(match[2])


def scan_tree(root):
  root = v.no_alias(root)
  counts, segments = Counter(), []
  # Deliberately bounded traversal. No parent scan and no following links.
  pending = [(root, 0)]
  while pending:
    directory, depth = pending.pop()
    for path in sorted(directory.iterdir()):
      v.no_alias(path)
      if path.is_dir():
        if depth >= v.root_policy()['maximum_directory_depth']:
          raise ValueError('APPROVED_DEPTH_EXCEEDED')
        pending.append((path, depth + 1))
      elif path.is_file():
        counts[path.name] += 1
        if path.name not in ('rlog.zst', 'qlog.zst'):
          continue
        relative = path.relative_to(root).as_posix()
        key, ordinal = lineage(relative)
        segments.append({
          'source_key': relative, 'lineage_sha256': key, 'ordinal': ordinal,
          'source_sha256': p.sha(path.read_bytes()), 'bytes': path.stat().st_size,
        })
      else:
        raise ValueError('NONREGULAR_SOURCE_REJECTED')
  return {'file_counts': dict(sorted(counts.items())), 'segments': sorted(segments, key=lambda x: x['source_key'])}


def metadata(iterator):
  counts = Counter()
  starts, profiles, clocks = [], [], []
  previous_clocks = {}
  for event in iterator:
    kind = event.which()
    counts[kind] += 1
    if kind in ('carState', 'carOutput', 'carControl'):
      clock = int(event.logMonoTime)
      if kind in previous_clocks and clock <= previous_clocks[kind]:
        raise ValueError('METADATA_STREAM_CLOCK_REGRESSION')
      previous_clocks[kind] = clock
      clocks.append(clock)  # Envelope only; no body access.
    elif kind == 'initData':
      x = event.initData
      if int(event.logMonoTime) <= 0 or int(x.wallTimeNanos) <= 0:
        raise ValueError('LOGGER_START_IDENTITY_UNAVAILABLE')
      starts.append({
        'commit': x.gitCommit, 'os': x.osVersion, 'dirty': bool(x.dirty),
        'logger_start_sha256': p.sha(p.canonical({
          'init_envelope_ns': int(event.logMonoTime), 'wall_ns': int(x.wallTimeNanos),
          'boot_sha256': p.sha(x.bootlogId.encode()), 'device_sha256': p.sha(x.dongleId.encode()),
        })),
      })
    elif kind == 'carParams':
      x = event.carParams
      profiles.append({
        'fingerprint': x.carFingerprint, 'carparams_sha256': p.sha(x.as_builder().to_bytes()),
        'control_type': str(x.steerControlType), 'flags': int(x.flags),
      })
  unique_starts = {p.sha(p.canonical(x)) for x in starts}
  unique_profiles = {p.sha(p.canonical(x)) for x in profiles}
  if len(unique_starts) != 1 or len(unique_profiles) != 1 or not clocks:
    raise ValueError('AMBIGUOUS_METADATA_GENERATION')
  start, profile = starts[0], profiles[0]
  if start['dirty']:
    raise ValueError('DIRTY_RECORDED_SOURCE')
  generation = {
    **profile, 'source_commit': start['commit'], 'os_version': start['os'],
    'software_profile_sha256': p.sha(p.canonical({
      'source': start['commit'], 'carparams': profile['carparams_sha256'], 'os': start['os'],
    })),
  }
  return {
    'generation': generation, 'logger_start_sha256': start['logger_start_sha256'],
    'first_ns': min(clocks), 'last_ns': max(clocks), 'envelope_counts': dict(counts),
  }


def group_routes(rows, v1_sources, v1_lineages, v1_starts=()):
  groups = defaultdict(list)
  for row in rows:
    groups[row['metadata']['logger_start_sha256']].append(row)
  result = []
  for start, members in sorted(groups.items()):
    generations = {p.sha(p.canonical(x['metadata']['generation'])) for x in members}
    ordered = sorted(members, key=lambda x: (x['metadata']['first_ns'], x['source_sha256']))
    distinct = len({x['source_sha256'] for x in members}) == len(members)
    contiguous = all(a['metadata']['last_ns'] < b['metadata']['first_ns'] for a, b in zip(ordered, ordered[1:], strict=False))
    # A lineage referring to multiple logger starts cannot prove independent routes.
    ambiguous_lineage = any(
      x['lineage_sha256'] == y['lineage_sha256'] and y['metadata']['logger_start_sha256'] != start for x in members for y in rows
    )
    overlap = start in v1_starts or any(x['source_sha256'] in v1_sources or x['lineage_sha256'] in v1_lineages for x in members)
    status = 'ROUTE_METADATA_COMPATIBLE'
    if overlap:
      status = 'V1_PLANNING_CONTEXT_ONLY'
    elif len(generations) != 1 or not distinct or not contiguous or ambiguous_lineage:
      status = 'ROUTE_IDENTITY_AMBIGUOUS'
    elif not v.compatible(members[0]['metadata']['generation']):
      status = 'ROUTE_REJECTED_INCOMPATIBLE_SOURCE'
    elif any(not all(x['metadata']['envelope_counts'].get(k, 0) for k in ('carState', 'carOutput', 'carControl')) for x in members):
      status = 'ROUTE_REJECTED_INSUFFICIENT_SIGNALS'
    identity = {
      'generation': sorted(generations), 'logger_start_sha256': start,
      'segment_lineage_sha256': sorted({x['lineage_sha256'] for x in members}),
      'monotonic_group_sha256': p.sha(p.canonical([
        [x['metadata']['first_ns'], x['metadata']['last_ns'], x['ordinal']] for x in ordered
      ])),
    }
    result.append({
      'route_id': p.sha(p.canonical({'generation': sorted(generations), 'logger_start_sha256': start})),
      'identity': identity, 'status': status,
      'v1_overlap': overlap, 'segment_count': len(members),
      'segments': sorted(x['source_sha256'] for x in members),
      'segment_completeness': 'ORDINAL_ZERO_CONTIGUOUS' if sorted(x['ordinal'] for x in members) == list(range(len(members))) else 'PARTIAL',
    })
  return result



def merge_v1_routes(routes, old_rows, anchors, source_anchors=None):
  source_anchors = source_anchors or {}
  output = [x for x in routes if x.get('identity', {}).get('logger_start_sha256') not in set(anchors.values())]
  for start in sorted(set(anchors.values())):
    members = [x for x in old_rows if anchors.get(x['lineage_sha256'], source_anchors.get(x['source_sha256'])) == start]
    copies = [x for x in routes if x.get('identity', {}).get('logger_start_sha256') == start]
    sources = sorted({x['source_sha256'] for x in members} | {source for route in copies for source in route['segments']})
    if not sources:
      continue
    generation = p.sha(p.canonical(v.expected_generation()))
    output.append({
      'route_id': p.sha(p.canonical({'generation': [generation], 'logger_start_sha256': start})),
      'status': 'V1_PLANNING_CONTEXT_ONLY', 'v1_overlap': True,
      'segment_count': len(sources), 'segments': sources,
      'identity_status': 'V1_EXCLUSION_ONLY_NO_NEW_ROUTE_CLAIM',
      'source_profile_sha256': generation, 'logger_start_sha256': start,
      'lineage_hashes': sorted({x['lineage_sha256'] for x in members}),
    })
  return sorted(output, key=lambda x: x['route_id'])


def bootstrap(root, store, v1_store, recorded_source):
  root = v.approved_root(root)
  store, v1_store = v.no_alias(store), v.no_alias(v1_store)
  for forbidden in (root, v1_store.resolve(), p.PUBLIC.parents[2].resolve()):
    if store.resolve().is_relative_to(forbidden) or forbidden.is_relative_to(store.resolve()):
      raise ValueError('SEPARATE_PRIVATE_STORE_REQUIRED')
  historical.load()
  inventory = read(v1_store / 'inventory.json')
  oldmeta = read(v1_store / 'metadata-all.json')
  if inventory['receipt_sha256'] != v.V1_INVENTORY or oldmeta['receipt_sha256'] != v.V1_METADATA or inventory['root'] != str(root):
    raise ValueError('EXACT_PUBLICLY_PINNED_V1_METADATA_REQUIRED')
  source = q.source_contract(recorded_source)
  logger_name = 'openpilot/system/loggerd/logger.cc'
  logger_blob = subprocess.check_output([
    'git', '-c', f'safe.directory={recorded_source}', '-C', str(recorded_source), 'show', f'{s.RECORDED_COMMIT}:{logger_name}',
  ])
  if (Path(recorded_source) / logger_name).read_bytes() != logger_blob:
    raise ValueError('LOGGER_ROUTE_IDENTITY_SOURCE_DRIFT')
  snapshot = scan_tree(root)
  binding = p.seal({
    'schema': 'EMPIRICAL_DATASET_V2_METADATA_BINDING', 'snapshot_sha256': p.sha(p.canonical(snapshot)),
    'source_sha256': source['receipt_sha256'], 'root_policy_sha256': v.root_policy()['receipt_sha256'],
    'homogeneity_sha256': v.homogeneity_policy()['receipt_sha256'],
    'split_policy_sha256': v.split_policy()['receipt_sha256'],
    'eligibility_policy_sha256': v.eligibility_policy()['receipt_sha256'],
    'reader_sha256': p.sha(Path(__file__).read_bytes()), 'v1_inventory_sha256': v.V1_INVENTORY,
    'logger_source_sha256': p.sha(logger_blob),
  })
  p.persist(store / 'metadata-binding.json', binding)
  old_by_key = {x['source_key']: x for x in inventory['segments']}
  old_sources = {x['source_sha256'] for x in inventory['segments']}
  old_lineages = {lineage(x['source_key'])[0] for x in inventory['segments']}
  # V1 metadata is context only. Do not reopen its numeric payload, even for eligibility.
  old_rows, fresh_rows, failures = [], [], []
  schema = None
  v1_starts = set()
  v1_anchors = {}
  # Only initData/CarParams and envelopes are accessed. This metadata anchor
  # excludes recompressed or renamed segments from the already opened V1 route.
  for key in sorted(old_lineages):
    candidates = [x for x in inventory['segments'] if lineage(x['source_key'])[0] == key and x['ordinal'] == 0]
    if len(candidates) != 1:
      raise ValueError('V1_ROUTE_START_METADATA_REQUIRED')
    anchor = candidates[0]
    raw_path = v.no_alias(root / anchor['source_key'])
    if p.sha(raw_path.read_bytes()) != anchor['source_sha256']:
      raise ValueError('V1_ANCHOR_SOURCE_CHANGED')
    destination = store / 'v1-exclusion' / (anchor['source_sha256'] + '.json')
    receipt = cached(destination, binding['receipt_sha256'])
    if receipt is None:
      if schema is None:
        schema = s.schema(recorded_source)
      info = metadata(s.events(raw_path, schema))
      if not v.compatible(info['generation']):
        raise ValueError('V1_METADATA_ANCHOR_GENERATION_CONFLICT')
      receipt = p.seal({'schema': 'EMPIRICAL_V1_ROUTE_EXCLUSION_METADATA',
                        'binding_sha256': binding['receipt_sha256'],
                        'logger_start_sha256': info['logger_start_sha256'], 'numeric_payload_opened': False})
      p.persist(destination, receipt)
    v1_starts.add(receipt['logger_start_sha256'])
    v1_anchors[key] = receipt['logger_start_sha256']
  for segment in snapshot['segments']:
    old = old_by_key.get(segment['source_key'])
    if old is not None and old['source_sha256'] != segment['source_sha256']:
      raise ValueError('V1_SOURCE_CHANGED')
    if old is not None or segment['source_sha256'] in old_sources or segment['lineage_sha256'] in old_lineages:
      old_rows.append(segment)
      continue
    destination = store / 'segments' / (segment['source_sha256'] + '.json')
    row = cached(destination, binding['receipt_sha256'])
    if row is None:
      if Path(segment['source_key']).name != 'rlog.zst':
        # qlog subsampling is not a source of reliable 100 Hz continuity.
        row = p.seal({'schema': 'EMPIRICAL_V2_METADATA', 'binding_sha256': binding['receipt_sha256'],
                      **segment, 'status': 'QLOG_ONLY_UNSUPPORTED_CONTINUITY', 'metadata': None})
      else:
        import capnp
        import zstandard
        if schema is None:
          schema = s.schema(recorded_source)
        try:
          info = metadata(s.events(root / segment['source_key'], schema))
          row = p.seal({'schema': 'EMPIRICAL_V2_METADATA', 'binding_sha256': binding['receipt_sha256'],
                        **segment, 'status': 'METADATA_PARSED', 'metadata': info})
        except (capnp.KjException, zstandard.ZstdError, ValueError) as error:
          row = p.seal({'schema': 'EMPIRICAL_V2_METADATA', 'binding_sha256': binding['receipt_sha256'],
                        **segment, 'status': 'ROUTE_REJECTED_CORRUPT', 'error_type': type(error).__name__, 'metadata': None})
      p.persist(destination, row)
    if row['metadata'] is None:
      failures.append(row)
    else:
      fresh_rows.append(row)
  routes = group_routes(fresh_rows, old_sources, old_lineages, v1_starts)
  source_anchors = {x['source_sha256']: v1_anchors[lineage(x['source_key'])[0]] for x in inventory['segments']}
  routes = merge_v1_routes(routes, old_rows, v1_anchors, source_anchors)
  eligible = [{k: row[k] for k in ('route_id', 'status', 'v1_overlap')} for row in routes if row['status'] == 'ROUTE_METADATA_COMPATIBLE']
  split = v.split_routes(eligible)
  if scan_tree(root) != snapshot:
    raise ValueError('SOURCE_CHANGED_DURING_METADATA_INVENTORY')
  result = p.seal({
    'schema': 'EMPIRICAL_DATASET_V2_PRIVATE_INVENTORY', 'binding_sha256': binding['receipt_sha256'],
    'snapshot': snapshot, 'routes': routes, 'failures': failures, 'split': split,
    'numeric_payloads_opened': False, 'new_numeric_route_count': 0,
  })
  p.persist(store / 'route-inventory.json', result)
  if split['status'] == 'EMPIRICAL_DATASET_V2_SPLIT_FROZEN':
    p.persist(store / 'route-split.json', split)
  return result


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--private-root', required=True)
  parser.add_argument('--private-store', required=True)
  parser.add_argument('--v1-store', required=True)
  parser.add_argument('--recorded-source', required=True)
  args = parser.parse_args()
  row = bootstrap(args.private_root, args.private_store, args.v1_store, args.recorded_source)
  print(row['schema'], row['receipt_sha256'], len(row['routes']), row['split']['status'])


if __name__ == '__main__':
  main()
