"""Hash-only audit of two declared copied-log filename layouts; no decompression."""

import argparse
from pathlib import Path
import re

from openpilot.tools.cyber_autotune import empirical_additional_root_policy as policy
from openpilot.tools.cyber_autotune import empirical_cross_root_inventory as reader
from openpilot.tools.cyber_autotune import empirical_export_metadata as export_reader
from openpilot.tools.cyber_autotune import empirical_dataset_v2_inventory as receipts
from openpilot.tools.cyber_autotune import empirical_plant_policy as p


def is_variant(name):
  return re.fullmatch(r'(?:[^/\\\\]+--)?rlog(?:-1| [(]1[)])[.]zst', name) is not None


def classify(digest, known):
  return 'IDENTICAL_BYTE_COPY_OF_ALREADY_INVENTORIED_LOG' if digest in known else 'UNRESOLVED_COPY_FILENAME_METADATA_ONLY'


def audit(roots, store):
  roots = [policy.approved_root(root) for root in roots]
  if len(roots) != 2 or {policy.root_key(root) for root in roots} != set(policy.ROOTS):
    raise ValueError('EXACT_TWO_DISTINCT_APPROVED_ROOTS_REQUIRED')
  store = policy.old.no_alias(store).resolve()
  for forbidden in (*roots, p.PUBLIC.parents[2].resolve()):
    if store.is_relative_to(forbidden) or forbidden.is_relative_to(store):
      raise ValueError('SEPARATE_PRIVATE_STORE_REQUIRED')
  parent, exports = receipts.read(store / 'inventory.json'), receipts.read(store / 'exports.json')
  binding = receipts.read(store / 'binding.json')
  if parent['binding_sha256'] != binding['receipt_sha256'] or binding['reader_sha256'] != p.sha(Path(reader.__file__).read_bytes()):
    raise ValueError('EXACT_PARENT_BINDING_REQUIRED')
  export_binding = receipts.read(store / 'export-binding.json')
  export_reader.validate_parent(parent, binding)
  export_reader.validate_extension_binding(export_binding, binding)
  if exports['binding_sha256'] != export_binding['receipt_sha256'] or exports['numeric_payloads_opened'] is not False:
    raise ValueError('EXACT_METADATA_EXPORT_PARENT_REQUIRED')
  known = set()
  for path in sorted((store / 'segments').glob('*.json')):
    row = receipts.cached(path, binding['receipt_sha256'])
    known.add(row['source_sha256'])
  known.update(x['source_sha256'] for x in [*exports['rows'], *exports['failures']])
  rows = []
  for root in sorted(roots):
    pending = [(root, 0)]
    while pending:
      folder, depth = pending.pop()
      for path in sorted(folder.iterdir()):
        policy.old.no_alias(path)
        if path.is_dir():
          if depth >= policy.root_policy()['maximum_directory_depth']:
            raise ValueError('APPROVED_ROOT_DEPTH_EXCEEDED')
          pending.append((path, depth + 1))
        elif path.is_file() and is_variant(path.name):
          before = path.stat()
          digest = reader.file_sha(path)
          after = path.stat()
          if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns or reader.file_sha(path) != digest:
            raise ValueError('COPY_SOURCE_CHANGED')
          rows.append(
            {
              'root_id': policy.root_key(root),
              'source_key': path.relative_to(root).as_posix(),
              'source_sha256': digest,
              'status': classify(digest, known),
            }
          )
  result = p.seal(
    {
      'schema': 'EMPIRICAL_COPY_FILENAME_METADATA_V2',
      'parent_inventory_sha256': parent['receipt_sha256'],
      'export_inventory_sha256': exports['receipt_sha256'],
      'source_sha256': p.sha(Path(__file__).read_bytes()),
      'root_policy_sha256': policy.root_policy()['receipt_sha256'],
      'rows': rows,
      'numeric_payloads_opened': False,
      'decompression_performed': False,
    }
  )
  p.persist(store / 'copy-variants-v2.json', result)
  return result


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--private-root', action='append', required=True)
  parser.add_argument('--private-store', required=True)
  args = parser.parse_args()
  result = audit(args.private_root, args.private_store)
  print(result['receipt_sha256'], len(result['rows']), sum(x['status'].startswith('IDENTICAL') for x in result['rows']))


if __name__ == '__main__':
  main()
