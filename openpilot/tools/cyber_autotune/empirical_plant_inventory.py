"""Fresh private-generation metadata bootstrap. No numeric signal bodies or codecs."""

import argparse
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_plant_signals as s


def metadata_receipt(segment, authorization, metadata):
  return p.seal(
    {
      'schema': 'EMPIRICAL_SEGMENT_METADATA_V1',
      'source_sha256': segment['source_sha256'],
      'segment_id': segment['segment_id'],
      'role': segment['role'],
      'metadata': metadata,
      'authorization_sha256': authorization,
    }
  )


def failure_receipt(segment, authorization, error_type):
  if error_type not in ('KjException', 'ZstdError'):
    raise ValueError('ONLY_EXPLICIT_LOG_FORMAT_FAILURE_DISPOSITION')
  return p.seal(
    {
      'schema': 'EMPIRICAL_SEGMENT_METADATA_FAILURE_V1',
      'source_sha256': segment['source_sha256'],
      'segment_id': segment['segment_id'],
      'role': segment['role'],
      'status': 'REJECTED_LOG_INTEGRITY',
      'error_type': error_type,
      'parsed_prefix_used': False,
      'authorization_sha256': authorization,
    }
  )


def bootstrap(root, store, recorded_source):
  import capnp
  import zstandard

  root = Path(root)
  store = Path(store)
  for path in (root, store):
    if any(x.is_symlink() for x in (path, *path.parents)):
      raise ValueError('NO_METADATA_PATH_SYMLINK')
  root = root.resolve(strict=True)
  if store.resolve().is_relative_to(root):
    raise ValueError('READ_ONLY_INPUT_ROOT_CANNOT_CONTAIN_STORE')
  if store.resolve().is_relative_to(p.PUBLIC.parents[2].resolve()):
    raise ValueError('PRIVATE_METADATA_STORE_OUTSIDE_REPOSITORY_REQUIRED')
  inventory = p.inventory(root)
  split = p.split(inventory['segments'])
  source = s.source_contract(recorded_source)
  auth = p.seal(
    {
      'schema': 'EMPIRICAL_METADATA_AUTHORIZATION_V1',
      'phase': 'METADATA_ONLY_NO_NUMERIC_SIGNALS',
      'inventory_sha256': inventory['receipt_sha256'],
      'split_sha256': split['receipt_sha256'],
      'source_sha256': source['receipt_sha256'],
      'data_policy_sha256': p.policy()['receipt_sha256'],
      'family_policy_sha256': p.family_policy()['receipt_sha256'],
      'metric_policy_sha256': p.metric_policy()['receipt_sha256'],
      'alignment_policy_sha256': p.alignment_policy()['receipt_sha256'],
      'reader_sha256': p.sha(Path(s.__file__).read_bytes()),
      'bootstrap_sha256': p.sha(Path(__file__).read_bytes()),
      'image_video_decode': False,
      'forbidden_payload_access': False,
    }
  )
  for name, row in [('inventory.json', inventory), ('split.json', split), ('metadata-authorization.json', auth)]:
    p.persist(store / name, row)
  schema = s.schema(recorded_source)
  results = []
  for segment in split['segments']:
    path = root / segment['source_key']
    if p.sha(path.read_bytes()) != segment['source_sha256']:
      raise ValueError('SOURCE_CHANGED_AFTER_SPLIT')
    destination = store / 'metadata' / f"{segment['segment_id']}.json"
    failure = store / 'metadata-failures' / destination.name
    for cache in (destination, failure):
      if any(x.is_symlink() for x in (cache, *cache.parents)):
        raise ValueError('NO_METADATA_CACHE_SYMLINK')
    if destination.exists() and failure.exists():
      raise ValueError('CONFLICTING_METADATA_DISPOSITION')
    if destination.exists() or failure.exists():
      receipt = p.verify(json.loads((destination if destination.exists() else failure).read_bytes()))
      if receipt['authorization_sha256'] != auth['receipt_sha256'] or receipt['source_sha256'] != segment['source_sha256']:
        raise ValueError('STALE_METADATA_CACHE')
    else:
      try:
        receipt = metadata_receipt(segment, auth['receipt_sha256'], s.metadata(s.events(path, schema)))
        p.persist(destination, receipt)
      except (capnp.KjException, zstandard.ZstdError) as e:
        receipt = failure_receipt(segment, auth['receipt_sha256'], type(e).__name__)
        p.persist(failure, receipt)
    results.append(receipt)
  all_meta = p.seal({'schema': 'EMPIRICAL_ALL_METADATA_V1', 'authorization_sha256': auth['receipt_sha256'], 'segments': results})
  p.persist(store / 'metadata-all.json', all_meta)
  return all_meta


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--private-root', required=True)
  parser.add_argument('--private-store', required=True)
  parser.add_argument('--recorded-source', required=True)
  args = parser.parse_args()
  receipt = bootstrap(args.private_root, args.private_store, args.recorded_source)
  print('METADATA_COMPLETE', len(receipt['segments']), receipt['receipt_sha256'])


if __name__ == '__main__':
  main()
