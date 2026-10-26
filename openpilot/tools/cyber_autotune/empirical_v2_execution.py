"""Persistent exact-route numeric extraction; no discovery, holdout or fitting."""

import argparse
from collections import defaultdict
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_execution as prior
from openpilot.tools.cyber_autotune import empirical_source_metadata as metadata
from openpilot.tools.cyber_autotune import empirical_source_publication as public
from openpilot.tools.cyber_autotune import empirical_cross_root_inventory as logs
from openpilot.tools.cyber_autotune import empirical_v2_policy as v
from openpilot.tools.cyber_autotune import empirical_v2_signals as signals


def private_store(value):
  path=Path(value).resolve()
  repo=Path(__file__).resolve().parents[3]
  if path == repo or repo in path.parents or any(x.is_symlink() for x in (Path(value),*Path(value).parents)):
    raise ValueError('PRIVATE_STORE_MUST_BE_OUTSIDE_REPOSITORY_NO_ALIAS')
  return path


def choose_sources(rows):
  grouped=defaultdict(list)
  for row in rows:
    if type(row['ordinal']) is not int or row['ordinal']<0 or row['kind'] not in logs.LOGS:
      raise ValueError('EXACT_SEGMENT_LINEAGE_REQUIRED')
    grouped[row['ordinal']].append(row)
  result=[]
  for _, group in sorted(grouped.items()):
    ranked=sorted(group,key=lambda x:(x['kind']!='rlog.zst',x['source_sha256']))
    best=ranked[0]
    if len({x['source_sha256'] for x in group if x['kind']==best['kind']}) != 1:
      raise ValueError('CONFLICTING_SEGMENT_SOURCE_HASH')
    result.append(best)
  return result


def prepare(store, source_store, historical_store, roots):
  store=private_store(store)
  source_store=Path(source_store)
  approved=prior.approved_root_map(roots)
  old=public.load()
  inv=prior.read(Path(historical_store)/'combined-inventory.json')
  if inv['receipt_sha256'] != old['empirical-source-audit-readiness-v1.json']['historical_inventory_sha256']:
    raise ValueError('EXACT_HISTORICAL_METADATA_REQUIRED')
  mapping=prior.read(source_store/'selected-file-map.json')
  if mapping['inventory_sha256'] != inv['receipt_sha256']:
    raise ValueError('EXACT_PRIVATE_FILE_MAP_REQUIRED')
  ids=old['empirical-source-route-reclassification-v1.json']['pools']['pools'][0]['route_ids']
  bindings, routes={},{}
  for rid in sorted(ids):
    original=next(x for x in inv['routes'] if x['route_id']==rid)
    commit=original['generation']['source_commit']
    candidates=[]
    for digest in original['source_hashes']:
      locations=mapping['matched'][digest]
      location=sorted(locations,key=lambda x:(x['root_id'],x['source_key']))[0]
      path=prior.source_location(location,approved)
      line=logs.segment_lineage(location['source_key'])
      info=prior.read(source_store/'segments'/commit/(digest+'.json'))
      if info['status']!='SOURCE_SPECIFIC_METADATA_REVALIDATED' or info['source_sha256']!=digest:
        raise ValueError('EXACT_METADATA_ADAPTER_RESULT_REQUIRED')
      candidates.append({'source_sha256':digest,'location':location,'ordinal':line['ordinal'],
                         'kind':path.name,'metadata_sha256':info['receipt_sha256']})
    sources=choose_sources(candidates)
    # The role receipt binds the selected stream set and immutable original lineage.
    bindings[rid]={'source_commit':commit,'lineage_sha256':original['identity_receipt_sha256'],
                   'source_set_sha256':p.sha(p.canonical(sorted(x['source_sha256'] for x in sources)))}
    routes[rid]=sources
  frozen=v.split(old,bindings)
  auth=v.authorization(frozen,{rid:sorted(x['source_sha256'] for x in rows) for rid,rows in routes.items()})
  manifest=p.seal({'schema':'EMPIRICAL_PLANT_V2_PRIVATE_SOURCE_MANIFEST_V1',
    'split_sha256':frozen['receipt_sha256'],'routes':routes, 'inventory_sha256':inv['receipt_sha256']})
  # No numeric getter occurs above. Persist split first, then exact authority and paths.
  p.persist(store/'split.json',frozen)
  p.persist(store/'policy.json',v.policy())
  p.persist(store/'authorization.json',auth)
  p.persist(store/'manifest.json',manifest)
  return frozen,auth,manifest


def authorized_segment(store, rid, segment, adapter_sha):
  return v.require_open(store,rid,segment['source_sha256'],adapter_sha)


def extract_route(store, source_store, roots, rid):
  store=private_store(store)
  source_store=Path(source_store)
  approved=prior.approved_root_map(roots)
  frozen=v.validate_split(prior.read(store/'split.json'))
  route=next((x for x in frozen['routes'] if x['route_id']==rid),None)
  if route is None:
    raise ValueError('ONLY_EXACT_ADMITTED_ROUTE')
  manifest=prior.read(store/'manifest.json')
  if manifest['split_sha256']!=frozen['receipt_sha256']:
    raise ValueError('MANIFEST_SPLIT_DRIFT')
  source=prior.read(source_store/'fingerprints'/(route['source_commit']+'.json'))
  binding=prior.read(source_store/'adapters-final'/(route['source_commit']+'.json'))
  metadata.validate_adapter(binding,source)
  if binding['receipt_sha256']!=route['adapter_sha256']:
    raise ValueError('SOURCE_SPECIFIC_ADAPTER_DRIFT')
  # Schemas already materialized by the prior audit; verify exact bytes, do not re-audit source.
  schema=metadata.schema_from_source(source,source_store/'schemas'/route['source_commit'])
  receipts=[]
  for segment in manifest['routes'][rid]:
    _,auth=authorized_segment(store,rid,segment,binding['receipt_sha256'])
    path=prior.source_location(segment['location'],approved)
    if logs.file_sha(path)!=segment['source_sha256']:
      raise ValueError('NUMERIC_SOURCE_HASH_DRIFT')
    historical=prior.read(source_store/'segments'/route['source_commit']/(segment['source_sha256']+'.json'))
    if historical['receipt_sha256']!=segment['metadata_sha256']:
      raise ValueError('IMMUTABLE_METADATA_RESULT_DRIFT')
    info=historical['metadata']
    if (info['profile']['full_carparams_sha256']!=route['full_carparams_sha256']
        or info['init']['commit']!=route['source_commit'] or info['init']['dirty']):
      raise ValueError('SOURCE_OR_FULL_PROFILE_CONFLICT')
    opening=p.seal({'schema':'EMPIRICAL_V2_NUMERIC_OPENING_V1','route_id':rid,
      'split_sha256':frozen['receipt_sha256'],'authorization_sha256':auth['receipt_sha256'],
      'source_sha256':segment['source_sha256'],'role':route['role'],'holdout_opened':False})
    destination=store/'segments'/rid/(segment['source_sha256']+'.json')
    p.persist(store/'openings'/rid/(segment['source_sha256']+'.json'),opening)
    if destination.exists():
      row=prior.read(destination)
      if row['opening_sha256']!=opening['receipt_sha256']:
        raise ValueError('STALE_NUMERIC_CACHE')
    else:
      try:
        streams=signals.numeric(logs.log_events(path,schema))
        gyro_clock=signals.validate_gyro_clock(streams)
        profile=signals.profile_for_models(info['profile']['fields'])
        maximum,known,pairs,bridge=signals.bridge_inputs(streams,profile)
        aligned=signals.aligned(streams)
        row=p.seal({'schema':'EMPIRICAL_V2_NUMERIC_SEGMENT_V1','status':'EXTRACTED',
          'segment_id':segment['source_sha256'],'route_id':rid,'role':route['role'],
          'opening_sha256':opening['receipt_sha256'],'source_sha256':segment['source_sha256'],
          'adapter_sha256':binding['receipt_sha256'],'profile':profile,
          'runtime_steer_max':maximum,'runtime_setting_known':known,'bridge':bridge,
          'command_pairs':pairs,'aligned':aligned,'coverage':signals.coverage(aligned),
          'gyro_clock':gyro_clock,'gyro_rejected':streams['gyro_rejected'],
          'auxiliary_coverage':streams.get('auxiliary_coverage',{})})
      except ValueError as error:
        row=p.seal({'schema':'EMPIRICAL_V2_NUMERIC_SEGMENT_V1','status':'REJECTED',
          'segment_id':segment['source_sha256'],'route_id':rid,'role':route['role'],
          'opening_sha256':opening['receipt_sha256'],'source_sha256':segment['source_sha256'],
          'reason_code':str(error) if str(error).isupper() and len(str(error))<128 else 'NUMERIC_VALIDATION_FAILED'})
      p.persist(destination,row)
    if logs.file_sha(path)!=segment['source_sha256']:
      raise ValueError('SOURCE_CHANGED_DURING_NUMERIC_EXTRACTION')
    receipts.append({'source_sha256':segment['source_sha256'],'receipt_sha256':row['receipt_sha256'],'status':row['status']})
    print('numeric segments',rid[:8],len(receipts),'/',len(manifest['routes'][rid]),row['status'],flush=True)
  result=p.seal({'schema':'EMPIRICAL_V2_PRIVATE_ROUTE_EXTRACTION_V1','route_id':rid,'role':route['role'],
    'split_sha256':frozen['receipt_sha256'],'segments':receipts,'numeric_payload_opened':True,
    'holdout_opened':False})
  p.persist(store/'routes'/(rid+'.json'),result)
  return result


def main():
  a=argparse.ArgumentParser(description=__doc__)
  a.add_argument('--store',required=True)
  a.add_argument('--source-store',required=True)
  a.add_argument('--root',action='append',required=True)
  a.add_argument('--route',required=True)
  args=a.parse_args()
  result=extract_route(args.store,args.source_store,args.root,args.route)
  print(result['receipt_sha256'],flush=True)


if __name__=='__main__':
  main()
