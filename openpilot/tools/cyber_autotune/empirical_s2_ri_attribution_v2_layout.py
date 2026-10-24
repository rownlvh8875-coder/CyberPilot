"""Lossless publication layout within the existing scanner's 1 MiB file limit.

This is a JSON-only serialization stage after the frozen attribution executor.
It never loads numeric arrays, changes analysis values, or weakens scanning.
"""
import argparse
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_causal_dataset_store as storage

MAX_BYTES = 1_048_576  # tools/cyberpilot/check_publication.py MAX_TEXT_BYTES, unchanged.
CONTEXT = 'empirical-s2-ri-context-attribution-v2.json'
NAMES = tuple('empirical-s2-ri-'+name+'-v2.json' for name in (
  'failure-attribution-policy','one-step-attribution','movement-confusion','error-decomposition',
  'projection-boundary','rollout-attribution','rollout-divergence','context-attribution',
  'mechanism-summary','hurdle-design-trigger','failure-attribution-repeatability','failure-attribution-readiness'))


def compact(value):
  p.verify(value)
  return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'


def context_shards(name,value,limit):
  p.verify(value)
  expected = [(f'S2RI_D{d:02d}_L{length:02d}',fold) for d in (0,5,10,20) for length in (1,5,15,45) for fold in ('FOLD_A','FOLD_B')]
  if name!=CONTEXT or [(j['candidate_id'],j['fold']) for j in value['jobs']]!=expected:
    raise ValueError('PUBLIC_LAYOUT_CONTEXT_IDENTITY')
  files, shards, recovered = {}, [], []
  for fold in ('FOLD_A','FOLD_B'):
    jobs = [j for j in value['jobs'] if j['fold']==fold]
    filename = 'empirical-s2-ri-context-attribution-v2-'+fold.lower().replace('_','-')+'.json'
    shard = p.seal({'schema':'EMPIRICAL_S2_RI_CONTEXT_ATTRIBUTION_SHARD_V2','fold':fold,'job_count':16,'jobs':jobs,
                   'source_bundle_receipt_sha256':value['receipt_sha256'],
                   'input_manifest_sha256':value['input_manifest_sha256'],
                   'output_manifest_sha256':value['output_manifest_sha256']})
    data = compact(shard)
    files[filename] = data
    shards.append({'file':filename,'fold':fold,'job_count':16,'receipt_sha256':shard['receipt_sha256'],'file_sha256':p.sha(data)})
    recovered.extend(jobs)
  if sorted(recovered,key=lambda j:(j['candidate_id'],j['fold']))!=value['jobs']:
    raise ValueError('PUBLIC_LAYOUT_VALUE_DRIFT')
  index = p.seal({**{k:v for k,v in value.items() if k not in ('jobs','receipt_sha256')},
    'encoding':'FOLD_SHARDED_PUBLIC_AGGREGATES','job_count':32,'source_bundle_receipt_sha256':value['receipt_sha256'],'shards':shards})
  files[name] = compact(index)
  if any(len(data)>limit for data in files.values()):
    raise ValueError('PUBLIC_LAYOUT_SIZE')
  return files


def document(name,value,limit=MAX_BYTES):
  if name not in NAMES:
    raise ValueError('PUBLIC_LAYOUT_NAME')
  p.verify(value)
  pretty = json.dumps(value,sort_keys=True,indent=2,allow_nan=False).encode()+b'\n'
  if len(pretty)<=limit:
    return {name:pretty}
  data = compact(value)
  if len(data)<=limit:
    return {name:data}
  if name!=CONTEXT:
    raise ValueError('PUBLIC_LAYOUT_SIZE')
  return context_shards(name,value,limit)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--source',required=True,type=Path)
  parser.add_argument('--output',required=True,type=Path)
  args = parser.parse_args()
  from openpilot.tools.cyber_autotune import empirical_s2_ri_attribution_v2_publication as publication
  bundle = publication.complete(args.source,args.output)
  files = {}
  for name,value in bundle.items():
    files.update(document(name,value))
  for name,data in files.items():
    storage.atomic_bytes(p.PUBLIC/name,data)
  print('PUBLISHED_LOSSLESS_SCANNABLE_FILES',len(files))


if __name__=='__main__':
  main()
