"""Read-only completed-cache revalidation, distinct from inference resumption.

The original executed producer and its immutable receipts stay unchanged.
Canonical JSON comparison handles Python int keys serialized as JSON strings.
Never materializes frames, loads the model, infers or rewrites a completed run.
"""
import argparse
import fcntl
import os
from contextlib import contextmanager
from pathlib import Path
import subprocess

from openpilot.tools.cyber_autotune import private_pixel_execution as p
from openpilot.tools.cyber_autotune import private_pixel_executor as executor
from openpilot.tools.cyber_autotune import lane_public_storage as storage
from openpilot.tools.cyber_autotune import lane_detector_execution as e
from openpilot.tools.cyber_autotune import lane_detector_runner as detector
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest
from openpilot.tools.cyber_autotune.lane_tail_report import seal, unseal


@contextmanager
def readonly_lease(cache):
  fd = os.open(cache / 'writer.lock', os.O_RDONLY | os.O_NOFOLLOW)
  try:
    fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
    yield
  finally:
    os.close(fd)


def require_same_aggregate(stored, recomputed):
  unseal(stored)
  unseal(recomputed)
  if canonical(stored) != canonical(recomputed):
    raise ValueError('COMPLETED_CACHE_AGGREGATE_REPLAY_MISMATCH')
  return True


def require_complete_marker(value):
  if type(value) is not dict:
    raise ValueError('COMPLETED_MARKER_REQUIRED_NO_PARTIAL_AGGREGATE')
  core = unseal(value)
  if core.get('storage_status') != 'COMPLETED' or core.get('reference_promotable') is not False or core.get('processed', 0) <= 0:
    raise ValueError('NONQUALIFYING_COMPLETED_MARKER_REQUIRED')


def verify_readonly_cache(root, manifest, auth, validator):
  p.require_execution(manifest, auth)
  root = Path(root)
  if any(path.is_symlink() for path in (root, root / 'rows', *root.parents)):
    raise ValueError('READONLY_CACHE_SYMLINK_FORBIDDEN')
  dev = [r for r in manifest['selected'] if r['role'] == 'DEVELOPMENT']
  binding = {'schema_sha256': storage.SCHEMA_SHA256, 'run_sha256': auth['receipt_sha256'],
             'input_order_sha256': digest(canonical([r['sample_id'] for r in dev])), 'expected': len(dev)}
  marker_path, index_path = root / 'completed.json', root / 'index.json'
  marker_bytes = marker_path.read_bytes()
  marker = storage.read_json(marker_path)
  require_complete_marker(marker)
  core = unseal(marker)
  if (any(core.get(k) != value for k, value in binding.items()) or core['processed'] != len(dev)
      or set(core) != set(binding) | {'storage_status', 'processed', 'index_file_sha256', 'artifact_file_sha256', 'reference_promotable'}):
    raise ValueError('READONLY_COMPLETION_BINDING_MISMATCH')
  freeze = storage.read_json(root / 'storage-freeze.json')
  if canonical(freeze) != canonical(seal({**binding, 'run': auth})):
    raise ValueError('READONLY_STORAGE_FREEZE_MISMATCH')
  index_bytes = index_path.read_bytes()
  if digest(index_bytes) != core['index_file_sha256']:
    raise ValueError('READONLY_INDEX_SHA_MISMATCH')
  index = unseal(storage.read_json(index_path))
  if (set(index) != set(binding) | {'storage_status', 'rows'} or index['storage_status'] != 'COMPLETED'
      or any(index.get(k) != value for k, value in binding.items()) or len(index['rows']) != len(dev)):
    raise ValueError('READONLY_INDEX_BINDING_MISMATCH')
  listed = {}
  for item in index['rows']:
    if (type(item) is not dict or set(item) != {'ordinal', 'receipt_sha256', 'frame_status'}
        or type(item['ordinal']) is not int or not 0 <= item['ordinal'] < len(dev)
        or item['ordinal'] in listed or item['frame_status'] not in {'COMPLETED', 'REFERENCE_UNAVAILABLE'}):
      raise ValueError('READONLY_INDEX_ROW_MISMATCH')
    listed[item['ordinal']] = item
  if {path.name for path in (root / 'rows').iterdir() if not (path.name.startswith('.') and path.name.endswith('.tmp'))} != {
    f'{i:05d}.json' for i in range(len(dev))
  }:
    raise ValueError('READONLY_MISSING_OR_EXTRA_ROW')
  rows = []
  for i in range(len(dev)):
    row = storage.read_json(root / 'rows' / f'{i:05d}.json')
    unseal(row)
    if (row['ordinal'] != i or any(row.get(k) != v for k, v in listed[i].items())
        or row['sample_id'] != dev[i]['sample_id']):
      raise ValueError('READONLY_ROW_IDENTITY_MISMATCH')
    validator(row)
    rows.append(row)
  artifacts = core['artifact_file_sha256']
  if type(artifacts) is not dict or not artifacts:
    raise ValueError('READONLY_ARTIFACTS_REQUIRED')
  for name, expected in artifacts.items():
    if Path(name).name != name or not name.endswith('.json'):
      raise ValueError('READONLY_ARTIFACT_NAME_MISMATCH')
    storage.read_json(root / name)
    if digest((root / name).read_bytes()) != expected:
      raise ValueError('READONLY_ARTIFACT_HASH_MISMATCH')
  if marker_path.read_bytes() != marker_bytes or index_path.read_bytes() != index_bytes:
    raise ValueError('COMPLETED_CACHE_CHANGED_DURING_READONLY_AUDIT')
  return marker, rows


def audit(root, cache, public_runtime):
  detector.require_network_isolation(detector.network_interfaces(Path('/proc/self/net/dev').read_text()))
  root, cache = p.private_directories(root, cache)
  manifest, auth = [storage.read_json(cache / name) for name in ('manifest.json', 'authorization.json')]
  p.require_execution(manifest, auth)
  if digest(str(root).encode()) != manifest['root_identity']:
    raise ValueError('ROOT_IDENTITY_MISMATCH')
  marker = storage.read_json(cache / 'receipts/completed.json')
  require_complete_marker(marker)
  expected = storage.read_json(p.ROOT / p.preparation.ENV_FILE)

  def runtime_guard():
    head = subprocess.check_output(['git', '-C', str(public_runtime / 'clrernet-source'), 'rev-parse', 'HEAD'], text=True).strip()
    if head != e.COMMIT:
      raise ValueError('PINNED_SOURCE_REQUIRED')
    actual = detector.runtime_environment(public_runtime / 'clrernet-source', public_runtime / 'toolchain-manifest.json',
                                          public_runtime / 'full-protocol.json', public_runtime / 'full-input-manifest.json')
    detector.require_runtime_match(e._unseal(expected, 'environment_sha256'), actual)
    detector.read_bound_bytes(public_runtime / 'clrernet_culane_dla34.pth', expected['weight_sha256'])
    p.require_execution(manifest, auth)

  runtime_guard()
  dev = [row for row in manifest['selected'] if row['role'] == 'DEVELOPMENT']
  selected_segments = {row['segment_id'] for row in dev}
  sources = 0
  for row in manifest['metadata']:
    if row['segment_id'] not in selected_segments:
      continue
    path = root / row['source_key']
    if path.stat().st_size != row['source_bytes'] or executor.hash_file(path) != row['source_sha256']:
      raise ValueError('COMPLETED_CACHE_SOURCE_DRIFT')
    sources += 1

  def validator(row):
    p.validate_frame(row, manifest, auth)
    if executor.hash_file(cache / 'images' / (row['sample_id'] + '.png')) != row['image_sha256']:
      raise ValueError('COMPLETED_CACHE_IMAGE_DRIFT')

  with readonly_lease(cache):
    verified, rows = verify_readonly_cache(cache / 'receipts', manifest, auth, validator)
    stored = storage.read_json(cache / 'aggregate.json')
    recomputed = p.progress_summary(manifest, auth, rows)
    require_same_aggregate(stored, recomputed)
    require_same_aggregate(storage.read_json(cache / 'receipts/summary.json'), recomputed)
    runtime_guard()
  return seal({
    'schema': 'PRIVATE_DIAGNOSTIC_COMPLETED_CACHE_READ_ONLY_AUDIT_V1',
    'status': 'PASS_READ_ONLY_COMPLETED_CACHE', 'cached_receipts_verified_and_reused': len(rows),
    'all_selected_source_identities_rechecked': True, 'verified_camera_sources': sources,
    'processed': len(rows), 'new_inference_frames': 0, 'frame_decode_calls': 0,
    'canonical_aggregate_equal': True, 'aggregate_sha256': stored['receipt_sha256'],
    'run_sha256': auth['receipt_sha256'], 'completion_marker_sha256': verified['receipt_sha256'],
    'audit_source_sha256': digest(Path(__file__).read_bytes()), **p.FIREWALL,
  })


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  for name in ('root', 'cache', 'public-runtime', 'report'):
    parser.add_argument('--' + name, type=Path, required=True)
  args = parser.parse_args()
  result = audit(args.root, args.cache, args.public_runtime)
  # Caller report remains private; public proof is an aggregate whitelist.
  p.immutable_json(args.report, result)
  print(result['status'], result['cached_receipts_verified_and_reused'], flush=True)


if __name__ == '__main__':
  main()
