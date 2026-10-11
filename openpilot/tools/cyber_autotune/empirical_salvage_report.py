"""Manual receipt-only salvage report. No default private path or numeric reader."""

import argparse
from collections import Counter
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_prior_use as u
from openpilot.tools.cyber_autotune import empirical_salvage_execution as e
from openpilot.tools.cyber_autotune import empirical_salvage_policy as policy
from openpilot.tools.cyber_autotune import empirical_salvage_publication as publication

REPEATABILITY_INITIAL = 'SEPARATE_VERIFIED_REPEATABILITY_RECEIPT_REQUIRED'

NAMES = {
  'policy': 'empirical-route-prior-use-policy-v1.json',
  'ledger': 'empirical-route-prior-use-ledger-v1.json',
  'selection': 'empirical-additional-source-audit-selection-v1.json',
  'sources': 'empirical-additional-source-classes-v1.json',
  'pools': 'empirical-existing-route-pools-v1.json',
  'readiness': 'empirical-existing-data-readiness-v1.json',
  'mapping': 'empirical-causal-h1-salvage-mapping-v1.json',
}


def load(root, name):
  root = u.no_alias(root)
  path = u.safe_path(root, [root], name)
  return p.verify(json.loads(path.read_bytes()))


def source_summary(row):
  result = {k: v for k, v in row.items() if k != 'source_results'}
  result['source_results'] = []
  for item in row['source_results']:
    public = {k: v for k, v in item.items() if k not in ('files', 'closure_entries', 'licenses')}

    def compact(entry):
      return {
        'path': entry['path'],
        'file_sha256': entry['file_sha256'],
        'normalized_source_sha256': entry['normalized_source_sha256'],
        'symbol_table_sha256': p.sha(p.canonical(entry.get('symbols', {}))),
      }

    public['files'] = {k: compact(v) for k, v in item['files'].items()}
    public['closure_entries'] = {k: compact(v) for k, v in item['closure_entries'].items()}
    public['license_manifest_sha256'] = p.sha(p.canonical(item['licenses']))
    public['equivalence_interpretation'] = 'STRICT_FULL_MANIFEST_POLICY_NOT_A_PHYSICAL_INCOMPATIBILITY_CLAIM'
    result['source_results'].append(public)
  result.pop('receipt_sha256')
  result['private_source_report_sha256'] = row['receipt_sha256']
  return p.seal(result)


def report(store, output):
  store, output = u.no_alias(store), u.no_alias(output)
  if store == output or store in output.parents or output in store.parents:
    raise ValueError('SEPARATE_REPORT_OUTPUT_REQUIRED')
  if p.PUBLIC.parents[2] == output or p.PUBLIC.parents[2] in output.parents:
    raise ValueError('PRIVATE_EXECUTION_STORE_OUTSIDE_REPOSITORY_REQUIRED')
  derived = e.derive(store, output / 'derived')
  fs = load(store, 'store-filesystem-inventory.json')
  registry = load(store, 'registry.json')
  roots = [load(store, x.name) for x in sorted(store.glob('log-root-*.json'))]
  before_after = []
  for item in fs['stores']:
    if item['status'] != 'FILESYSTEM_METADATA_INVENTORIED':
      before_after.append({'store_sha256': p.sha(item['path'].encode()), 'status': item['status']})
      continue
    current = u.file_inventory(item['path'])
    if current != {k: item[k] for k in ('files', 'excluded_non_evidence_directories')}:
      raise ValueError('HISTORICAL_STORE_FILESYSTEM_CHANGED')
    before_after.append({'store_sha256': p.sha(item['path'].encode()), 'status': 'FILE_METADATA_IDENTICAL', 'file_count': len(current['files'])})
  rows = {
    'policy': load(store, 'policy.json'),
    'selection': load(store, 'selection.json'),
    'sources': source_summary(load(store, 'additional-source-classes.json')),
    'mapping': e.future_mapping(),
    **derived,
  }
  code = {x.name: p.sha(x.read_bytes()) for x in sorted(Path(__file__).parent.glob('empirical_salvage*.py'))}
  code['empirical_prior_use.py'] = p.sha(Path(u.__file__).read_bytes())
  readiness = {k: v for k, v in rows['readiness'].items() if k != 'receipt_sha256'}
  readiness.update(
    {
      'schema': 'EMPIRICAL_EXISTING_DATA_READINESS_V1',
      'increment': 'EXISTING_PRIVATE_LOG_SALVAGE_AND_HOLDOUT_AUDIT_V1',
      'execution_status': 'AUTHORIZED_AUDIT_EXECUTED_PRIVATE_STORE_CLOSURE_PARTIAL',
      'source_classes_sha256': rows['sources']['receipt_sha256'],
      'additional_public_sources_audited': len(rows['sources']['source_results']),
      'additional_source_complete_count': rows['sources']['complete_source_count'],
      'additional_source_partial_count': rows['sources']['partial_source_count'],
      'additional_source_comparison_counts': dict(Counter(x['status_against_existing_source_reference'] for x in rows['sources']['source_results'])),
      'source_adapter_executor_implemented': False,
      'source_adapter_preparation': 'FINGERPRINT_BOUND_CONTRACTS_ONLY',
      'registered_project_store_count': len(registry['stores']),
      'store_integrity': before_after,
      'approved_log_root_file_count': sum(len(x['files']) for x in roots),
      'approved_log_root_payloads_opened': False,
      'approved_log_root_metadata_receipts_sha256': [x['receipt_sha256'] for x in roots],
      'simulator_store_closure': 'EXACT_LOCAL_EVIDENCE_FOLDER_NOT_YET_IDENTIFIED',
      'strict_independent_holdout_created': False,
      'reservation_created': False,
      'opening_executor_implemented': False,
      'engineering_holdout_contract': policy.engineering_contract(),
      'source_code_sha256': code,
      'repeatability': REPEATABILITY_INITIAL,
      'ta_sg_execution': 'NOT_RUN',
      'composition_authorized': False,
    }
  )
  rows['readiness'] = p.seal(readiness)
  for key, name in NAMES.items():
    publication.write(output / 'public' / name, rows[key])
  receipt = p.seal(
    {
      'schema': 'EMPIRICAL_SALVAGE_EXECUTION_RECEIPT_V1',
      'result_sha256': {key: row['receipt_sha256'] for key, row in rows.items()},
      'code_sha256': code,
      'numeric_opened': False,
      'holdout_opened': False,
    }
  )
  p.persist(output / 'execution.json', receipt)
  return receipt


def repeatability(first, second):
  p.verify(first)
  p.verify(second)
  if first != second:
    raise ValueError('SALVAGE_REPEATABILITY_CONFLICT')
  return p.seal(
    {
      'schema': 'EMPIRICAL_SALVAGE_REPEATABILITY_V1',
      'status': 'TWO_COMPLETE_EXECUTIONS_EXACT',
      'executions': 2,
      'execution_receipt_sha256': first['receipt_sha256'],
    }
  )


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--audit-store', type=Path, required=True)
  parser.add_argument('--output-store', type=Path, required=True)
  args = parser.parse_args()
  result = report(args.audit_store, args.output_store)
  print(result['receipt_sha256'])


if __name__ == '__main__':
  main()
