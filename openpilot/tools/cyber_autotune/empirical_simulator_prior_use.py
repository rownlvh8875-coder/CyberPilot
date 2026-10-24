"""Exact GitHub metadata/aggregate receipt reconciliation, never signal extraction."""

from collections import defaultdict
import hashlib
import json

from openpilot.tools.cyber_autotune import empirical_plant_policy as p


B26_RESULT_PIN = '6db7f95ce02c286e1288df0445b1b1df74d65515047f939cfb0bd223ce2f009a'
B26_RESULT_STATE = 'CURRENT_SETTINGS_LANE_MPC_B26_COMMA_CROSS_AXIS_SUPPLEMENTAL_CONFIRMED_REVALIDATION_REQUIRED'


def evaluated_routes(result, precommit_sha):
  body = result['body']
  if result['sha256'] != B26_RESULT_PIN or body.get('state') != B26_RESULT_STATE or body.get('precommit_sha256') != precommit_sha:
    return set()
  return {
    x['route_id']
    for x in body.get('route_results', [])
    if isinstance(x.get('route_id'), str) and type(x.get('window_count')) is int and x['window_count'] > 0
  }


def verify_blob(content, expected):
  raw = content.encode()
  actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
  if actual != expected:
    raise ValueError('SIMULATOR_GIT_BLOB_IDENTITY_CONFLICT')
  return p.sha(raw)


def reconcile(metadata, selected, inventory):
  if any(x['tree'].get('truncated') is not False for x in metadata['repositories']):
    raise ValueError('SIMULATOR_TREE_TRUNCATED')
  repository = next(x for x in metadata['repositories'] if x['repository'] == selected['repository'])
  if repository['commit'] != selected['commit']:
    raise ValueError('SIMULATOR_COMMIT_DRIFT')
  objects = {x['path']: x['sha'] for x in repository['tree']['tree'] if x['type'] == 'blob'}
  receipts, connections, uses = {}, [], defaultdict(list)
  source_routes = defaultdict(set)
  for route in inventory['routes']:
    for digest in route['source_hashes']:
      source_routes[digest].add(route['route_id'])
  for item in selected['receipts']:
    if objects.get(item['path']) != item['sha']:
      raise ValueError('SIMULATOR_TREE_BLOB_DRIFT')
    digest = verify_blob(item['content'], item['sha'])
    receipts[item['path']] = {'sha256': digest, 'body': json.loads(item['content']), 'blob_sha': item['sha']}
  for name, item in receipts.items():
    body = item['body']
    linked = None
    evidence = 'SIMULATOR_PRECOMMIT_REFERENCE_NUMERIC_STATUS_UNRESOLVED'
    if 'b26_holdout_precommit' in name:
      candidate = receipts.get('evidence/current_settings_lane_mpc_b26_result_20260919.json')
      if candidate and candidate['body'].get('precommit_sha256') == item['sha256']:
        linked = candidate
        evidence = 'SIMULATOR_HISTORICAL_EVALUATION_USED'
    # B25 result does not carry an exact expanded-precommit digest. Never infer a join from dates.
    for row in body.get('cohort', []):
      matches = defaultdict(list)
      for source_hash in (row.get('raw_sha256') or {}).values():
        for rid in source_routes.get(source_hash, ()):
          matches[rid].append(source_hash)
      for rid, matched in sorted(matches.items()):
        consumed = linked is not None and row.get('route_id') in evaluated_routes(linked, item['sha256'])
        use = {
          'project': 'CARROT_SIMULATOR_PRIVATE',
          'generation': body.get('state', 'UNKNOWN'),
          'role': 'HISTORICAL_PRECOMMITTED_COHORT',
          'metadata_opened': True,
          'numeric_opened': True if consumed else None,
          'fitting_used': None,
          'selection_used': None,
          'evaluation_used': True if consumed else None,
          'holdout_used': None,
          'receipt_sha256': item['sha256'],
          'source_file_hash_match_count': len(matched),
          'source_file_hash_set_sha256': p.sha(p.canonical(sorted(matched))),
          'source_identity': selected['commit'],
          'use_verdict': evidence if consumed else 'SIMULATOR_PRECOMMIT_REFERENCE_NUMERIC_STATUS_UNRESOLVED',
          'linked_result_sha256': linked['sha256'] if consumed else None,
        }
        uses[rid].append(use)
    connections.append(
      {
        'receipt_sha256': item['sha256'],
        'blob_sha': item['blob_sha'],
        'state': body.get('state', 'METADATA_INVENTORY'),
        'linked_result_sha256': linked['sha256'] if linked else None,
      }
    )
  return p.seal(
    {
      'schema': 'EMPIRICAL_SIMULATOR_PRIOR_USE_SUPPLEMENT_V1',
      'repositories': [
        {
          'repository': x['repository'],
          'commit': x['commit'],
          'tree_sha256': p.sha(p.canonical(x['tree'])),
          'tree_entries': len(x['tree']['tree']),
          'tree_truncated': False,
          'evidence_json_count': sum(
            y['type'] == 'blob' and y['path'].startswith('evidence/') and y['path'].endswith('.json') for y in x['tree']['tree']
          ),
        }
        for x in metadata['repositories']
      ],
      'selected_receipts_audited': len(receipts),
      'receipt_connections': connections,
      'route_uses': [{'route_id': rid, 'uses': rows} for rid, rows in sorted(uses.items())],
      'matched_route_count': len(uses),
      'matched_source_hash_reference_count': sum(x['source_file_hash_match_count'] for rows in uses.values() for x in rows),
      'historical_evaluation_route_count': sum(any(x['evaluation_used'] is True for x in rows) for rows in uses.values()),
      'private_store_closure_complete': False,
      'remaining_blockers': [
        'DELETED_OR_UNLOCATED_LOCAL_SIMULATOR_STORE_HISTORY_UNATTESTED',
        'UNMAPPED_SIMULATOR_RECEIPTS_REMAIN',
        'NOT_ALL_ROUTE_ALIASES_HAVE_EXACT_CONTENT_HASH_PROOF',
      ],
      'untouched_promotions': 0,
      'reservation_created': False,
      'holdout_opening': 'CLOSED',
      'opening_count': 0,
      'numeric_payloads_opened': False,
      'model_metrics_imported': False,
      'candidate_verdicts_imported': False,
      'pipeline_untouched_not_global': True,
    }
  )
