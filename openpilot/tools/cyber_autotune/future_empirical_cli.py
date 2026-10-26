"""Manual future metadata workflow. Receipts only; no raw or numeric extractor."""

import argparse
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import future_empirical_contracts as c
from openpilot.tools.cyber_autotune import future_empirical_admission as a
from openpilot.tools.cyber_autotune import future_empirical_publication as publication


def main(argv=None):
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('command', choices=('inventory', 'assign', 'inspect', 'source-template', 'extract'))
  parser.add_argument('--private-root', required=True, help='Explicit approved storage-root alias; never traversed by this command')
  parser.add_argument('--private-store', required=True, help='Explicit new future-only store outside repository')
  parser.add_argument('--metadata-receipt')
  parser.add_argument('--history-metadata')
  parser.add_argument('--source-commit')
  args = parser.parse_args(argv)
  root = a.root_id(args.private_root)
  store = a.private_store(args.private_store)
  if args.command == 'extract':
    a.numeric_open()
  publication.load()
  p.persist(store / 'generation-policy.json', c.generation_policy())
  if args.command == 'source-template':
    if args.source_commit is None:
      parser.error('--source-commit is required')
    import re

    if not re.fullmatch('[0-9a-f]{40}', args.source_commit):
      raise ValueError('EXACT_COMMIT_REQUIRED')
    row = p.seal(
      {
        'schema': 'FUTURE_SOURCE_AUDIT_TEMPLATE_V1',
        'source_commit': args.source_commit,
        'status': 'SOURCE_AUDIT_PENDING',
        'requirements': c.generation_policy()['source_template']['required'],
        'numeric_opening_allowed': False,
      }
    )
    p.persist(store / 'source-templates' / (args.source_commit + '.json'), row)
  elif args.command == 'inventory':
    if args.metadata_receipt is None or args.history_metadata is None:
      parser.error('--metadata-receipt and --history-metadata are required')
    meta = a.load_private(args.metadata_receipt, store)
    history = a.load_private(args.history_metadata, store)
    if meta.get('root_id') != root:
      raise ValueError('EXPLICIT_ROOT_METADATA_MISMATCH')
    previous = [a.load_private(path, store) for path in sorted((store / 'inventory').glob('*.json'))]
    # An exact immutable resume must not treat its own logger as a new duplicate.
    previous = [z for z in previous if z.get('metadata_sha256') != meta['receipt_sha256']]
    row = a.inventory(meta, history, previous)
    p.persist(store / 'inventory' / (row['route_id'] + '.json'), row)
  elif args.command == 'assign':
    records = [a.load_private(path, store) for path in sorted((store / 'inventory').glob('*.json'))]
    row = a.assign(records)
    p.persist(store / 'roles.json', row)
  else:
    roles = store / 'roles.json'
    if roles.exists():
      row = a.verify_roles(a.load_private(roles, store))
    else:
      row = p.seal(
        {
          'schema': 'FUTURE_ROUTE_MANUAL_INSPECTION_V1',
          'status': 'NO_NEW_ROUTE_ADMITTED',
          'inventory_count': len(list((store / 'inventory').glob('*.json'))),
          'numeric_opening_allowed': False,
        }
      )
  print(row['schema'], row['receipt_sha256'], row.get('status', 'ROLES_FROZEN_CLOSED'))
  return row


if __name__ == '__main__':
  main()
