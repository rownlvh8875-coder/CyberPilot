"""Restartable source-bound metadata revalidation. No numeric execution API."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import subprocess

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_policy as policy
from openpilot.tools.cyber_autotune import empirical_source_metadata as adapter
from openpilot.tools.cyber_autotune import empirical_additional_root_policy as roots
from openpilot.tools.cyber_autotune import empirical_cross_root_inventory as old_reader
from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as receipts


def read(path):
  return p.verify(json.loads(Path(path).read_bytes()))


def approved_root_map(values):
  if values is None:
    raise ValueError('EXPLICIT_APPROVED_ROOTS_REQUIRED')
  approved = {}
  for value in values:
    root = roots.approved_root(value)
    approved[roots.root_key(root)] = root
  if set(approved) != set(roots.ROOTS):
    raise ValueError('EXACT_TWO_APPROVED_ROOTS_REQUIRED')
  return approved


def map_selected_files(inventory, selected, approved_roots, store):
  p.verify(inventory)
  if inventory['receipt_sha256'] != policy.INVENTORY_SHA:
    raise ValueError('EXACT_IMMUTABLE_INVENTORY_REQUIRED')
  approved_roots = approved_root_map(approved_roots)
  targets = {sha for r in inventory['routes'] if p.sha(p.canonical(r['generation'])) in selected for sha in r['source_hashes']}
  matched = defaultdict(list)
  total = sum(len(s['logs']) for s in inventory['snapshot'].values())
  completed = 0
  for root_id, snapshot in sorted(inventory['snapshot'].items()):
    for item in snapshot['logs']:
      relative = Path(item['source_key'])
      if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('PRIVATE_SOURCE_PATH_ESCAPE')
      source = approved_roots[root_id] / relative
      from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as old_policy
      old_policy.no_alias(source)
      stat = source.stat()
      if stat.st_size != item['bytes'] or stat.st_mtime_ns != item['mtime_ns']:
        raise ValueError('PRIVATE_SOURCE_SNAPSHOT_CHANGED')
      key = p.sha(p.canonical({'root_id': root_id, 'source_key_sha256': p.sha(item['source_key'].encode()),
                              'bytes': item['bytes'], 'mtime_ns': item['mtime_ns']}))
      destination = Path(store) / 'file-hashes' / (key + '.json')
      cached = receipts.cached(destination, inventory['receipt_sha256'])
      if cached is None:
        digest = old_reader.file_sha(source)
        cached = p.seal({'schema': 'PRIVATE_METADATA_FILE_HASH_V1', 'binding_sha256': inventory['receipt_sha256'],
                         'source_sha256': digest, 'snapshot_key_sha256': key})
        p.persist(destination, cached)
      if source.stat() != stat:
        raise ValueError('SOURCE_CHANGED_DURING_HASH')
      if cached['source_sha256'] in targets:
        matched[cached['source_sha256']].append({'root_id': root_id, 'source_key': item['source_key'],
                                               'path': str(source), 'snapshot_key_sha256': key})
      completed += 1
      if completed % 100 == 0:
        print('compressed-file metadata hashes', completed, '/', total, flush=True)
  missing = targets - set(matched)
  result = p.seal({'schema': 'PRIVATE_SELECTED_SOURCE_FILE_MAP_V1', 'inventory_sha256': inventory['receipt_sha256'],
                   'selected_generations': sorted(selected), 'matched': dict(matched),
                   'missing_source_hashes': sorted(missing), 'numeric_payloads_opened': False})
  p.persist(Path(store) / 'selected-file-map.json', result)
  return result


def source_location(location, approved):
  root_id = roots.require_root_hash(location['root_id'])
  if root_id not in approved:
    raise ValueError('APPROVED_SOURCE_ROOT_UNAVAILABLE')
  relative = Path(location['source_key'])
  if relative.is_absolute() or '..' in relative.parts:
    raise ValueError('PRIVATE_SOURCE_PATH_ESCAPE')
  from openpilot.tools.cyber_autotune import empirical_dataset_v2_policy as old_policy
  expected = old_policy.no_alias(approved[root_id] / relative)
  if Path(location['path']) != expected:
    raise ValueError('PRIVATE_FILE_MAP_PATH_MISMATCH')
  return expected


def materialize_schemas(repo, source, store):
  directory = Path(store) / 'schemas' / source['commit']
  for role, row in source['files'].items():
    if not role.startswith('schema_'):
      continue
    data = subprocess.check_output(['git', '-c', f'safe.directory={repo}', '-C', str(repo),
                                    'show', f"{source['commit']}:{row['path']}"])
    if p.sha(data) != row['file_sha256']:
      raise ValueError('PUBLIC_SOURCE_SCHEMA_DRIFT')
    path = directory / row['path']
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
      if path.read_bytes() != data:
        raise ValueError('IMMUTABLE_SCHEMA_CONFLICT')
    else:
      with path.open('xb') as stream:
        stream.write(data)
  return directory


def revalidate_commit(store, historical_store, repo, commit, approved_roots=None):
  approved = approved_root_map(approved_roots)
  store, historical_store = Path(store), Path(historical_store)
  public = read(store / 'public-origin.json')
  if commit not in public['commits']:
    raise ValueError('PUBLIC_COMMIT_ATTESTATION_REQUIRED')
  source = read(store / 'fingerprints' / (commit + '.json'))
  binding = read(store / 'adapters-final' / (commit + '.json'))
  adapter.validate_adapter(binding, source)
  directory = materialize_schemas(repo, source, store)
  schema = None
  mapping = read(store / 'selected-file-map.json')
  if mapping['inventory_sha256'] != policy.INVENTORY_SHA or mapping.get('missing_source_hashes'):
    raise ValueError('EXACT_COMPLETE_FILE_MAP_REQUIRED')
  rows = []
  for digest, locations in sorted(mapping['matched'].items()):
    historic = read(historical_store / 'segments' / (digest + '.json'))
    if historic['metadata']['generation']['source_commit'] != commit:
      continue
    source_path = source_location(locations[0], approved)
    destination = store / 'segments' / commit / (digest + '.json')
    cached = receipts.cached(destination, binding['receipt_sha256'])
    if old_reader.file_sha(source_path) != digest:
      raise ValueError('SOURCE_HASH_MISMATCH')
    if cached is None:
      if schema is None:
        schema = adapter.schema_from_source(source, directory)
      try:
        info = adapter.metadata(old_reader.log_events(source_path, schema), commit, True)
        old = historic['metadata']
        if (info['init']['logger_start_sha256'] != old['logger_start_sha256']
            or info['profile']['full_carparams_sha256'] != old['generation']['carparams_sha256']
            or info['first_ns'] != old['first_ns'] or info['last_ns'] != old['last_ns']
            or info['envelope_counts'] != old['envelope_counts']):
          raise ValueError('SOURCE_SPECIFIC_METADATA_IDENTITY_CONFLICT')
        cached = p.seal({'schema': 'SOURCE_SPECIFIC_METADATA_ADAPTER_RESULT_V1',
                         'binding_sha256': binding['receipt_sha256'], 'source_sha256': digest,
                         'metadata': info, 'status': 'SOURCE_SPECIFIC_METADATA_REVALIDATED'})
      except (ValueError, AttributeError) as error:
        cached = p.seal({'schema': 'SOURCE_SPECIFIC_METADATA_ADAPTER_RESULT_V1',
                         'binding_sha256': binding['receipt_sha256'], 'source_sha256': digest,
                         'metadata': None, 'status': 'SOURCE_SPECIFIC_METADATA_UNRESOLVED',
                         'reason': str(error)})
      p.persist(destination, cached)
    if old_reader.file_sha(source_path) != digest:
      raise ValueError('SOURCE_CHANGED_DURING_ADAPTER')
    rows.append({'source_sha256': digest, 'receipt_sha256': cached['receipt_sha256'],
                 'status': cached['status'], 'metadata': cached['metadata']})
    if len(rows) % 20 == 0:
      print('source-specific metadata segments', commit[:8], len(rows), flush=True)
  result = p.seal({'schema': 'PRIVATE_SOURCE_METADATA_REVALIDATION_V1', 'commit': commit,
                   'binding_sha256': binding['receipt_sha256'], 'file_map_sha256': mapping['receipt_sha256'],
                   'rows': rows, 'numeric_payloads_opened': False})
  p.persist(store / 'metadata-results' / (commit + '.json'), result)
  return result


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--store', required=True)
  parser.add_argument('--historical-store', required=True)
  parser.add_argument('--source-repo', required=True)
  parser.add_argument('--commit', required=True)
  parser.add_argument('--root', action='append', required=True, help='Explicit approved root; repeat for both roots')
  args = parser.parse_args()
  result = revalidate_commit(args.store, args.historical_store, args.source_repo, args.commit, args.root)
  print(result['receipt_sha256'], len(result['rows']))


if __name__ == '__main__':
  main()
