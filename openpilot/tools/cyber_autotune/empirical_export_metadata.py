"""Additive metadata-only coverage of exported rlog filenames; never numeric signals."""

import argparse
from collections import defaultdict
from pathlib import Path
import re

from openpilot.tools.cyber_autotune import empirical_additional_root_policy as policy
from openpilot.tools.cyber_autotune import empirical_cross_root_inventory as reader
from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as receipts
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_plant_signals as signals


def is_export(name):
  return name not in reader.LOGS and name.endswith('rlog.zst')


def export_lineage(relative):
  path = Path(relative)
  match = re.fullmatch(r'(.+)--([0-9]+)--rlog[.]zst', path.name)
  key = str(path.parent / match[1]) if match else str(path)
  return {'lineage_sha256': p.sha(key.encode()), 'ordinal': int(match[2]) if match else None}


def discover(root):
  root = policy.approved_root(root)
  pending, rows = [(root, 0)], []
  while pending:
    folder, depth = pending.pop()
    for path in sorted(folder.iterdir()):
      policy.old.no_alias(path)
      if path.is_dir():
        if depth >= policy.root_policy()['maximum_directory_depth']:
          raise ValueError('APPROVED_ROOT_DEPTH_EXCEEDED')
        pending.append((path, depth + 1))
      elif path.is_file() and is_export(path.name):
        stat = path.stat()
        relative = path.relative_to(root).as_posix()
        rows.append({'source_key': relative, **export_lineage(relative), 'kind': 'rlog.zst', 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns})
  return sorted(rows, key=lambda x: x['source_key'])


def export_events(path, schema):
  import zstandard

  path = policy.old.no_alias(path)
  if not is_export(path.name):
    raise ValueError('ONLY_EXPORTED_RLOG_ALLOWED')
  with path.open('rb') as raw, zstandard.ZstdDecompressor().stream_reader(raw) as stream:
    data = stream.read()
  yield from schema.Event.read_multiple_bytes(data)


def source_identity():
  return p.sha(Path(__file__).read_bytes())


def validate_parent(parent, binding):
  p.verify(parent)
  if (
    parent.get('schema') != 'EMPIRICAL_CROSS_ROOT_PRIVATE_INVENTORY_V1'
    or parent.get('binding_sha256') != binding.get('receipt_sha256')
    or parent.get('numeric_payloads_opened') is not False
    or binding.get('reader_sha256') != p.sha(Path(reader.__file__).read_bytes())
    or binding.get('policy_source_sha256') != p.sha(Path(policy.__file__).read_bytes())
  ):
    raise ValueError('EXACT_METADATA_PARENT_REQUIRED')


def validate_extension_binding(extension, parent):
  p.verify(extension)
  if extension.get('extension_source_sha256') != source_identity() or any(
    extension.get(key) != parent.get(key) for key in ('reader_sha256', 'root_policy_sha256', 'source_contract_sha256')
  ):
    raise ValueError('EXPORTED_METADATA_BINDING_DRIFT')


def validate_export_sources(roots, rows):
  by_id = {policy.root_key(root): root for root in roots}
  for row in rows:
    relative = Path(row['source_key'])
    if relative.is_absolute() or '..' in relative.parts:
      raise ValueError('EXPORTED_SOURCE_OUTSIDE_ROOT')
    source = policy.old.no_alias(by_id[row['root_id']] / relative)
    if not source.is_relative_to(by_id[row['root_id']]) or not is_export(source.name):
      raise ValueError('EXPORTED_SOURCE_OUTSIDE_ROOT')
    if reader.file_sha(source) != row['source_sha256']:
      raise ValueError('EXPORTED_CONTENT_DRIFT')


def audit_exports(roots, store, recorded_source):
  roots = [policy.approved_root(root) for root in roots]
  if len(roots) != 2 or {policy.root_key(root) for root in roots} != set(policy.ROOTS):
    raise ValueError('EXACT_TWO_DISTINCT_APPROVED_ROOTS_REQUIRED')
  store = policy.old.no_alias(store).resolve()
  for forbidden in (*roots, p.PUBLIC.parents[2].resolve()):
    if store.is_relative_to(forbidden) or forbidden.is_relative_to(store):
      raise ValueError('SEPARATE_PRIVATE_STORE_REQUIRED')
  contract = signals.source_contract(recorded_source)
  snapshot = {policy.root_key(root): discover(root) for root in roots}
  binding = p.seal(
    {
      'schema': 'EMPIRICAL_EXPORTED_LOG_METADATA_BINDING_V1',
      'snapshot_sha256': p.sha(p.canonical(snapshot)),
      'root_policy_sha256': policy.root_policy()['receipt_sha256'],
      'extension_source_sha256': source_identity(),
      'reader_sha256': p.sha(Path(reader.__file__).read_bytes()),
      'source_contract_sha256': contract['receipt_sha256'],
    }
  )
  p.persist(store / 'export-binding.json', binding)
  schema = signals.schema(recorded_source)
  import capnp
  import zstandard

  rows, failures = [], []
  for root in sorted(roots):
    root_id = policy.root_key(root)
    for selected in snapshot[root_id]:
      source = policy.old.no_alias(root / selected['source_key'])
      digest = reader.file_sha(source)
      destination = store / 'exports' / (digest + '.json')
      receipt = receipts.cached(destination, binding['receipt_sha256'])
      if receipt is None:
        try:
          info = reader.metadata(export_events(source, schema))
          error = None
        except (capnp.KjException, zstandard.ZstdError, ValueError, AttributeError) as exception:
          info, error = None, type(exception).__name__
        receipt = p.seal(
          {
            'schema': 'EMPIRICAL_EXPORT_SEGMENT_METADATA_V1',
            'binding_sha256': binding['receipt_sha256'],
            'source_sha256': digest,
            'metadata': info,
            'error_type': error,
          }
        )
        p.persist(destination, receipt)
      if reader.file_sha(source) != digest:
        raise ValueError('EXPORTED_SOURCE_CHANGED')
      row = {**selected, 'root_id': root_id, 'source_sha256': digest, 'metadata': receipt['metadata']}
      (rows if row['metadata'] is not None else failures).append(row)
  if {policy.root_key(root): discover(root) for root in roots} != snapshot:
    raise ValueError('EXPORTED_FILESYSTEM_CHANGED')
  result = p.seal(
    {
      'schema': 'EMPIRICAL_EXPORTED_LOG_METADATA_V1',
      'binding_sha256': binding['receipt_sha256'],
      'snapshot': snapshot,
      'rows': rows,
      'failures': failures,
      'numeric_payloads_opened': False,
    }
  )
  p.persist(store / 'exports.json', result)
  return result


def combine(roots, store, previous_store):
  roots = [policy.approved_root(root) for root in roots]
  if len(roots) != 2 or {policy.root_key(root) for root in roots} != set(policy.ROOTS):
    raise ValueError('EXACT_TWO_DISTINCT_APPROVED_ROOTS_REQUIRED')
  store = policy.old.no_alias(store).resolve()
  for forbidden in (*roots, p.PUBLIC.parents[2].resolve()):
    if store.is_relative_to(forbidden) or forbidden.is_relative_to(store):
      raise ValueError('SEPARATE_PRIVATE_STORE_REQUIRED')
  parent, binding = receipts.read(store / 'inventory.json'), receipts.read(store / 'binding.json')
  validate_parent(parent, binding)
  exports, extension_binding = receipts.read(store / 'exports.json'), receipts.read(store / 'export-binding.json')
  if exports['binding_sha256'] != extension_binding['receipt_sha256']:
    raise ValueError('EXPORTED_METADATA_BINDING_DRIFT')
  validate_extension_binding(extension_binding, binding)
  validate_export_sources(roots, [*exports['rows'], *exports['failures']])
  if exports['numeric_payloads_opened'] is not False:
    raise ValueError('METADATA_ONLY_EXTENSION_REQUIRED')
  rows, failures = list(exports['rows']), list(exports['failures'])
  for root in sorted(roots):
    root_id = policy.root_key(root)
    if reader.enumerate_directory(root) != parent['snapshot'][root_id] or discover(root) != exports['snapshot'][root_id]:
      raise ValueError('PARENT_FILESYSTEM_DRIFT')
    by_directory = defaultdict(list)
    for item in parent['snapshot'][root_id]['logs']:
      by_directory[str(Path(item['source_key']).parent)].append(item)
    for members in by_directory.values():
      selected = min(members, key=lambda x: (x['kind'] != 'qlog.zst', x['source_key']))
      digest = reader.file_sha(root / selected['source_key'])
      cached = receipts.cached(store / 'segments' / (digest + '.json'), binding['receipt_sha256'])
      if cached is None or cached['source_sha256'] != digest:
        raise ValueError('MISSING_EXACT_PARENT_SEGMENT')
      item = {
        **selected,
        'root_id': root_id,
        'source_sha256': digest,
        'metadata': cached['metadata'],
        'available_log_kinds': sorted({x['kind'] for x in members}),
      }
      (rows if item['metadata'] is not None else failures).append(item)
  previous = receipts.read(policy.old.no_alias(previous_store) / 'route-inventory.json')
  if previous['receipt_sha256'] != binding['previous_inventory_sha256']:
    raise ValueError('EXACT_PREVIOUS_INVENTORY_REQUIRED')
  starts = {x.get('logger_start_sha256', x.get('identity', {}).get('logger_start_sha256')) for x in previous['routes']}
  if None in starts:
    raise ValueError('V1_EXCLUSION_ANCHOR_REQUIRED')
  if any(
    reader.enumerate_directory(root) != parent['snapshot'][policy.root_key(root)] or discover(root) != exports['snapshot'][policy.root_key(root)]
    for root in roots
  ):
    raise ValueError('SOURCE_FILESYSTEM_CHANGED_DURING_COMBINATION')
  routes = reader.group(rows, starts, failures)
  count = sum(len(x) for x in exports['snapshot'].values())
  result = p.seal(
    {
      **{key: value for key, value in parent.items() if key != 'receipt_sha256'},
      'parent_inventory_sha256': parent['receipt_sha256'],
      'export_inventory_sha256': exports['receipt_sha256'],
      'export_binding_sha256': extension_binding['receipt_sha256'],
      'export_log_file_count': count,
      'routes': routes,
      'generation_buckets': reader.buckets(routes),
      'failed_file_count': len(failures),
      'failure_source_hashes': sorted(x['source_sha256'] for x in failures),
      'selected_metadata_files': parent['selected_metadata_files'] + count,
    }
  )
  p.persist(store / 'combined-inventory.json', result)
  return result


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--private-root', action='append', required=True)
  parser.add_argument('--private-store', required=True)
  parser.add_argument('--recorded-source', required=True)
  parser.add_argument('--combine', action='store_true')
  parser.add_argument('--previous-store', required=True)
  args = parser.parse_args()
  result = (
    combine(args.private_root, args.private_store, args.previous_store)
    if args.combine
    else audit_exports(args.private_root, args.private_store, args.recorded_source)
  )
  print(result['receipt_sha256'])


if __name__ == '__main__':
  main()
