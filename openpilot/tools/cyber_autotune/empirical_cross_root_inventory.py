"""Read only initData/CarParams and event envelopes inside two approved roots."""

import argparse
from collections import Counter, defaultdict
import hashlib
from pathlib import Path
import re
import subprocess

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_plant_signals as signals
from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as old
from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as previous
from openpilot.tools.cyber_autotune import empirical_dataset_v2_publication as history
from openpilot.tools.cyber_autotune import empirical_additional_root_policy as policy

LOGS = ('rlog.zst', 'qlog.zst')
MEDIA = ('.ts', '.hevc', '.mp4', '.jpg', '.jpeg', '.png', '.gif', '.webp')
ARCHIVES = ('.zip', '.7z', '.tar', '.gz', '.bz2', '.rar')


def segment_lineage(relative):
  path = Path(relative).parent
  match = re.fullmatch(r'(.+)--([0-9]+)', path.name)
  if match:
    key, ordinal = str(path.parent / match[1]), int(match[2])
  elif path.name.isdecimal():
    key, ordinal = str(path.parent), int(path.name)
  else:
    key, ordinal = str(path), None
  return {'lineage_sha256': p.sha(key.encode()), 'ordinal': ordinal}


def enumerate_directory(root):
  root = old.no_alias(root)
  pending = [(root, 0)]
  logs, counts, sizes = [], Counter(), Counter()
  total = media = archives = 0
  while pending:
    folder, depth = pending.pop()
    for path in sorted(folder.iterdir()):
      old.no_alias(path)
      if path.is_dir():
        if depth >= policy.root_policy()['maximum_directory_depth']:
          raise ValueError('APPROVED_ROOT_DEPTH_EXCEEDED')
        pending.append((path, depth + 1))
      elif path.is_file():
        stat = path.stat()
        total += 1
        media += path.suffix.lower() in MEDIA
        archives += path.suffix.lower() in ARCHIVES
        if path.name in LOGS:
          relative = path.relative_to(root).as_posix()
          logs.append({'source_key': relative, **segment_lineage(relative), 'kind': path.name, 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns})
          counts[path.name] += 1
          sizes[path.name] += stat.st_size
      else:
        raise ValueError('NONREGULAR_SOURCE_REJECTED')
  return {
    'logs': sorted(logs, key=lambda x: x['source_key']),
    'file_count': total,
    'media_file_count_metadata_only': media,
    'archive_count': archives,
    'log_counts': dict(counts),
    'log_bytes': dict(sizes),
  }


def file_sha(path):
  digest = hashlib.sha256()
  with old.no_alias(path).open('rb') as stream:
    while chunk := stream.read(1024 * 1024):
      digest.update(chunk)
  return digest.hexdigest()


def metadata(iterator):
  starts, profiles, times = [], [], []
  counts = Counter()
  previous_clocks = {}
  for event in iterator:
    kind = event.which()
    counts[kind] += 1
    if kind in ('carState', 'carOutput', 'carControl'):
      clock = int(event.logMonoTime)
      if kind in previous_clocks and clock <= previous_clocks[kind]:
        raise ValueError('METADATA_STREAM_CLOCK_REGRESSION')
      previous_clocks[kind] = clock
      times.append(clock)
    elif kind == 'initData':
      x = event.initData
      if int(event.logMonoTime) <= 0 or int(x.wallTimeNanos) <= 0:
        raise ValueError('LOGGER_START_IDENTITY_UNAVAILABLE')
      starts.append(
        {
          'source_commit': str(x.gitCommit),
          'os_version': str(x.osVersion),
          'dirty': bool(x.dirty),
          'logger_start_sha256': p.sha(
            p.canonical(
              {
                'init_envelope_ns': int(event.logMonoTime),
                'wall_ns': int(x.wallTimeNanos),
                'boot_sha256': p.sha(x.bootlogId.encode()),
                'device_sha256': p.sha(x.dongleId.encode()),
              }
            )
          ),
        }
      )
    elif kind == 'carParams':
      x = event.carParams
      profiles.append(
        {
          'fingerprint': str(x.carFingerprint),
          'carparams_sha256': p.sha(x.as_builder().to_bytes()),
          'control_type': str(x.steerControlType),
          'flags': int(x.flags),
        }
      )
  if len({p.sha(p.canonical(x)) for x in starts}) != 1 or len({p.sha(p.canonical(x)) for x in profiles}) != 1 or not times:
    raise ValueError('INCOMPLETE_OR_MIXED_METADATA')
  start, profile = starts[0], profiles[0]
  generation = {
    **profile,
    'source_commit': start['source_commit'],
    'os_version': start['os_version'],
    'software_profile_sha256': p.sha(
      p.canonical(
        {
          'source': start['source_commit'],
          'carparams': profile['carparams_sha256'],
          'os': start['os_version'],
        }
      )
    ),
  }
  return {
    'generation': generation,
    'logger_start_sha256': start['logger_start_sha256'],
    'source_dirty': start['dirty'],
    'first_ns': min(times),
    'last_ns': max(times),
    'envelope_counts': dict(counts),
  }


def log_events(path, schema):
  import zstandard

  path = old.no_alias(path)
  if path.name not in LOGS:
    raise ValueError('ONLY_CANONICAL_LOGS_ALLOWED')
  with path.open('rb') as raw, zstandard.ZstdDecompressor().stream_reader(raw) as stream:
    data = stream.read()
  yield from schema.Event.read_multiple_bytes(data)


def group(rows, v1_starts, failures=()):
  by_start = defaultdict(list)
  for row in rows:
    by_start[row['metadata']['logger_start_sha256']].append(row)
  result = []
  for start, members in sorted(by_start.items()):
    generations = {p.sha(p.canonical(x['metadata']['generation'])) for x in members}
    unique = {}
    seen_signatures = set()
    ordinal_conflict = False
    for x in members:
      m = x['metadata']
      signature = (p.sha(p.canonical(m['generation'])), m['first_ns'], m['last_ns'], p.sha(p.canonical(m['envelope_counts'])))
      if signature in seen_signatures:
        continue
      seen_signatures.add(signature)
      key = (signature[0], x['ordinal']) if x['ordinal'] is not None else signature
      if key in unique:
        a, b = unique[key]['metadata'], m
        ordinal_conflict |= a['last_ns'] < b['first_ns'] or b['last_ns'] < a['first_ns']
        if b['last_ns'] - b['first_ns'] > a['last_ns'] - a['first_ns']:
          unique[key] = x
      else:
        unique[key] = x
    ordered = sorted(unique.values(), key=lambda x: x['metadata']['first_ns'])
    overlap = any(a['metadata']['last_ns'] >= b['metadata']['first_ns'] for a, b in zip(ordered, ordered[1:], strict=False))
    missing = any(not all(x['metadata']['envelope_counts'].get(k, 0) for k in ('carState', 'carOutput')) for x in ordered)
    missing |= any(x['lineage_sha256'] == failed['lineage_sha256'] and x['root_id'] == failed['root_id'] for x in members for failed in failures)
    lineage_conflict = any(
      x['lineage_sha256'] == other['lineage_sha256'] and other['metadata']['logger_start_sha256'] != start for x in members for other in rows
    )
    generation = ordered[0]['metadata']['generation']
    compatibility = policy.compatibility(generation)
    v1 = start in v1_starts
    if v1:
      status = 'ROUTE_DUPLICATE_EXISTING_V1'
    elif len(generations) != 1 or overlap or ordinal_conflict or lineage_conflict or any(x['metadata'].get('source_dirty', False) for x in members):
      status = 'ROUTE_IDENTITY_AMBIGUOUS'
    elif missing:
      status = 'ROUTE_CORRUPT_OR_INCOMPLETE'
    else:
      status = compatibility
    observed = {p.sha(p.canonical(x['metadata']['generation'])): x['metadata']['generation'] for x in members}
    bucket_generation = (
      generation if len(observed) == 1 else {'status': 'MIXED_METADATA_GENERATIONS', 'observed_generations': [observed[key] for key in sorted(observed)]}
    )
    result.append(
      {
        'route_id': p.sha(p.canonical({'generation': sorted(generations), 'logger_start_sha256': start})),
        'status': status,
        'compatibility': compatibility,
        'generation': bucket_generation,
        'compatible': status == 'ROUTE_COMPATIBLE_WITH_V1_GENERATION',
        'untouched': False,
        'prior_analysis': 'V1_PLANNING_CONTEXT_ONLY' if v1 else 'ROUTE_PRIOR_ANALYSIS_STATUS_UNKNOWN',
        'v1_overlap': v1,
        'segment_count': len(ordered),
        'duplicate_file_count': len(members) - len(ordered),
        'root_count': len({x['root_id'] for x in members}),
        'available_log_kinds': sorted({kind for x in members for kind in x.get('available_log_kinds', [x['kind']])}),
        'source_hashes': sorted({x['source_sha256'] for x in members}),
        'identity_receipt_sha256': p.sha(
          p.canonical(
            {
              'logger_start_sha256': start,
              'generation_hashes': sorted(generations),
              'lineages': sorted({x['lineage_sha256'] for x in members}),
              'monotonic_ranges': [[x['metadata']['first_ns'], x['metadata']['last_ns'], x['ordinal']] for x in ordered],
            }
          )
        ),
      }
    )
  return result


def buckets(routes):
  groups = defaultdict(list)
  for route in routes:
    groups[p.sha(p.canonical(route['generation']))].append(route)
  return [
    {
      'generation_id': key,
      'generation': members[0]['generation'],
      'route_count': len(members),
      'segment_count': sum(x['segment_count'] for x in members),
      'v1_route_count': sum(x['v1_overlap'] for x in members),
      'compatible_routes': sum(x['compatible'] for x in members),
      'untouched_routes': sum(x['untouched'] for x in members),
      'log_availability': dict(Counter(kind for x in members for kind in x['available_log_kinds'])),
      'prior_analysis_unknown_routes': sum(x['prior_analysis'] == 'ROUTE_PRIOR_ANALYSIS_STATUS_UNKNOWN' for x in members),
      'status_counts': dict(Counter(x['status'] for x in members)),
      'runtime_steer_max': None,
      'steer_max_provenance': 'SOURCE_DEFAULT_AND_OVERRIDE_PATH_KNOWN_RUNTIME_UNOBSERVED'
      if members[0]['generation'] == old.expected_generation()
      else 'NEW_SOURCE_AUDIT_REQUIRED',
      'signal_schema_generation': 'PINNED_READER_METADATA_PARSE_ONLY_NOT_SIGNAL_SEMANTICS_VALIDATION',
    }
    for key, members in sorted(groups.items())
  ]


def public_routes(routes):
  keys = (
    'route_id',
    'status',
    'compatibility',
    'compatible',
    'untouched',
    'prior_analysis',
    'v1_overlap',
    'segment_count',
    'duplicate_file_count',
    'root_count',
    'identity_receipt_sha256',
  )
  return [{**{key: x[key] for key in keys}, 'generation_id': p.sha(p.canonical(x['generation']))} for x in routes]


def inventory(roots, store, recorded_source, previous_store):
  roots = [policy.approved_root(root) for root in roots]
  if len(roots) != 2 or {policy.root_key(root) for root in roots} != set(policy.ROOTS):
    raise ValueError('EXACT_TWO_DISTINCT_APPROVED_ROOTS_REQUIRED')
  store = old.no_alias(store).resolve()
  previous_store = old.no_alias(previous_store).resolve()
  for forbidden in (*roots, previous_store, p.PUBLIC.parents[2].resolve()):
    if store.is_relative_to(forbidden) or forbidden.is_relative_to(store):
      raise ValueError('SEPARATE_PRIVATE_STORE_REQUIRED')
  history.load()
  old_inventory = previous.read(previous_store / 'route-inventory.json')
  if old_inventory['receipt_sha256'] != 'ea213824ccaefd075bbd29c1fa8ade47ac0494e91c84d6fd8c00732049969d61':
    raise ValueError('EXACT_PREVIOUS_INVENTORY_REQUIRED')
  starts = {x.get('logger_start_sha256', x.get('identity', {}).get('logger_start_sha256')) for x in old_inventory['routes']}
  if None in starts:
    raise ValueError('V1_EXCLUSION_ANCHOR_REQUIRED')
  source_contract = signals.source_contract(recorded_source)
  logger_name = 'openpilot/system/loggerd/logger.cc'
  blob = subprocess.check_output(
    ['git', '-c', f'safe.directory={recorded_source}', '-C', str(recorded_source), 'show', f'{signals.RECORDED_COMMIT}:{logger_name}']
  )
  if (Path(recorded_source) / logger_name).read_bytes() != blob:
    raise ValueError('LOGGER_IDENTITY_SOURCE_DRIFT')
  snapshot = {policy.root_key(root): enumerate_directory(root) for root in roots}
  binding = p.seal(
    {
      'schema': 'EMPIRICAL_CROSS_ROOT_METADATA_BINDING_V1',
      'root_policy_sha256': policy.root_policy()['receipt_sha256'],
      'snapshot_sha256': p.sha(p.canonical(snapshot)),
      'previous_inventory_sha256': old_inventory['receipt_sha256'],
      'reader_sha256': p.sha(Path(__file__).read_bytes()),
      'policy_source_sha256': p.sha(Path(policy.__file__).read_bytes()),
      'schema_source_sha256': p.sha(Path(signals.__file__).read_bytes()),
      'recorded_schema_source': signals.RECORDED_COMMIT,
      'source_contract_sha256': source_contract['receipt_sha256'],
      'logger_source_sha256': p.sha(blob),
    }
  )
  p.persist(store / 'binding.json', binding)
  p.persist(store / 'filesystem.json', p.seal({'schema': 'PRIVATE_FILESYSTEM_METADATA_V1', 'snapshot': snapshot, 'binding_sha256': binding['receipt_sha256']}))
  rows, failures = [], []
  schema = None
  total = sum(len(x['logs']) for x in snapshot.values())
  completed = 0
  for root in sorted(roots):
    root_id = policy.root_key(root)
    by_directory = defaultdict(list)
    for item in snapshot[root_id]['logs']:
      by_directory[str(Path(item['source_key']).parent)].append(item)
    for members in by_directory.values():
      # qlog and rlog are alternative metadata envelopes from one segment.
      # Prefer qlog; no support/rate/100 Hz inference is made in this increment.
      selected = min(members, key=lambda x: (x['kind'] != 'qlog.zst', x['source_key']))
      source = old.no_alias(root / selected['source_key'])
      digest = file_sha(source)
      destination = store / 'segments' / (digest + '.json')
      receipt = previous.cached(destination, binding['receipt_sha256'])
      if receipt is None:
        if schema is None:
          schema = signals.schema(recorded_source)
        import capnp
        import zstandard

        try:
          info = metadata(log_events(source, schema))
          receipt = p.seal(
            {
              'schema': 'EMPIRICAL_CROSS_ROOT_SEGMENT_METADATA_V1',
              'binding_sha256': binding['receipt_sha256'],
              'source_sha256': digest,
              'status': 'METADATA_PARSED',
              'metadata': info,
            }
          )
        except (capnp.KjException, zstandard.ZstdError, ValueError, AttributeError) as error:
          receipt = p.seal(
            {
              'schema': 'EMPIRICAL_CROSS_ROOT_SEGMENT_METADATA_V1',
              'binding_sha256': binding['receipt_sha256'],
              'source_sha256': digest,
              'status': 'ROUTE_CORRUPT_OR_INCOMPLETE',
              'metadata': None,
              'error_type': type(error).__name__,
            }
          )
        p.persist(destination, receipt)
      if file_sha(source) != digest:
        raise ValueError('SOURCE_CHANGED_DURING_METADATA_PARSE')
      item = {
        **selected,
        'root_id': root_id,
        'source_sha256': digest,
        'metadata': receipt['metadata'],
        'available_log_kinds': sorted({x['kind'] for x in members}),
      }
      (rows if receipt['metadata'] is not None else failures).append(item)
      completed += len(members)
      if completed % 100 < len(members):
        print('metadata files accounted', completed, '/', total, flush=True)
  routes = group(rows, starts, failures)
  split = policy.metadata_split(
    [
      {
        'route_id': x['route_id'],
        'compatible': x['compatible'],
        'v1_overlap': x['v1_overlap'],
        'prior_analysis': 'UNKNOWN',
      }
      for x in routes
    ]
  )
  if {policy.root_key(root): enumerate_directory(root) for root in roots} != snapshot:
    raise ValueError('SOURCE_FILESYSTEM_CHANGED_DURING_INVENTORY')
  result = p.seal(
    {
      'schema': 'EMPIRICAL_CROSS_ROOT_PRIVATE_INVENTORY_V1',
      'binding_sha256': binding['receipt_sha256'],
      'snapshot': snapshot,
      'routes': routes,
      'generation_buckets': buckets(routes),
      'failed_file_count': len(failures),
      'failure_source_hashes': [x['source_sha256'] for x in failures],
      'selected_metadata_files': len(rows) + len(failures),
      'alternative_log_files_not_parsed': total - len(rows) - len(failures),
      'split': split,
      'numeric_payloads_opened': False,
      'numeric_coverage': None,
      'holdout_opened': False,
    }
  )
  p.persist(store / 'inventory.json', result)
  if split['status'] == 'ROUTE_DISJOINT_SPLIT_POSSIBLE':
    p.persist(store / 'metadata-split.json', split)
  return result


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--private-root', action='append', required=True)
  parser.add_argument('--private-store', required=True)
  parser.add_argument('--recorded-source', required=True)
  parser.add_argument('--previous-store', required=True)
  args = parser.parse_args()
  result = inventory(args.private_root, args.private_store, args.recorded_source, args.previous_store)
  print(result['receipt_sha256'], len(result['routes']), result['split']['status'])


if __name__ == '__main__':
  main()
