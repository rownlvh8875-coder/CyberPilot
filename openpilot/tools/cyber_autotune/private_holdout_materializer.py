"""Materialize ONLY the existing sixty frozen holdouts after separate authority.

No detector/model/AI invocation; no directory crawl or sample selection.
Persistent private image receipts precede a final complete package.
"""
import argparse
from pathlib import Path
import subprocess

from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune import private_pixel_execution as p
from openpilot.tools.cyber_autotune import private_pixel_executor as old
from openpilot.tools.cyber_autotune import lane_public_storage as storage
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


def guarded_decode(manifest, auth, sample_id, decoder):
  h.require_materialization(manifest, auth, sample_id)
  return decoder()


def materialize(source_root, original_cache, output, *, acknowledge=False):
  source_root, output = p.private_directories(source_root, output)
  original_cache = h.private_path(original_cache)
  if output == original_cache or output.is_relative_to(original_cache) or original_cache.is_relative_to(output):
    raise ValueError('SEPARATE_HISTORICAL_DEVELOPMENT_AND_HOLDOUT_STORES_REQUIRED')
  manifest = h.read(original_cache / 'manifest.json')
  samples = h.holdouts(manifest)
  plan = h.read(original_cache / 'holdout-plan.json')
  if canonical(plan) != canonical(old.holdout_plan(manifest)):
    raise ValueError('ORIGINAL_FROZEN_HOLDOUT_PLAN_REQUIRED')
  if digest(str(source_root).encode()) != manifest['root_identity']:
    raise ValueError('EXACT_SOURCE_ROOT_REQUIRED')
  output.mkdir(parents=True, exist_ok=True, mode=0o700)
  with storage.writer_lease(output):
    if (output / 'authorization.json').exists():
      auth = h.read(output / 'authorization.json')
    else:
      head = subprocess.check_output(['git', '-C', str(p.ROOT), 'rev-parse', 'HEAD'], text=True).strip()
      auth = h.authorize(manifest, head, old.utc(), acknowledged=acknowledge)
      h.write_immutable(output / 'authorization.json', auth)
    h.require_materialization(manifest, auth, samples[0]['sample_id'])
    h.write_immutable(output / 'evaluation-policy.json', h.seal(h.EVALUATION_POLICY))
    images_dir, rows_dir = output / 'images', output / 'materialized'
    for directory in (images_dir, rows_dir):
      h.private_path(directory)
      directory.mkdir(exist_ok=True, mode=0o700)
    expected_names = {r['sample_id'] + '.json' for r in samples}
    if {path.name for path in rows_dir.glob('*.json')} - expected_names:
      raise ValueError('UNKNOWN_HOLDOUT_CACHE_ROW')
    existing = {}
    for sample in samples:
      path = rows_dir / (sample['sample_id'] + '.json')
      if path.exists():
        row = h.read(path)
        if canonical(row) != canonical(h.image_receipt(manifest, auth, sample['sample_id'], row['image_sha256'])):
          raise ValueError('STALE_HOLDOUT_IMAGE_RECEIPT')
        if old.hash_file(images_dir / (sample['sample_id'] + '.png')) != row['image_sha256']:
          raise ValueError('HOLDOUT_CACHED_IMAGE_DRIFT')
        existing[sample['sample_id']] = row
    reused = len(existing)
    # Import decoder only after immutable selection + explicit authorization.
    import cv2
    for meta in manifest['metadata']:
      selected = [s for s in samples if s['segment_id'] == meta['segment_id']]
      if not selected:
        continue
      path = source_root / meta['source_key']
      with old.verified_video(path, meta['source_sha256'], meta['source_bytes']) as snapshot:
        missing = [s for s in selected if s['sample_id'] not in existing]
        if not missing:
          continue
        capture = guarded_decode(manifest, auth, missing[0]['sample_id'], lambda: cv2.VideoCapture(snapshot))
        try:
          needed = {s['frame_ordinal']: s for s in missing}
          for ordinal in range(max(needed) + 1):
            if not capture.grab():
              raise ValueError('FROZEN_HOLDOUT_ORDINAL_UNAVAILABLE')
            if ordinal not in needed:
              continue  # Codec traversal only; no nonselected frame retrieval/materialization.
            sample = needed[ordinal]
            h.require_materialization(manifest, auth, sample['sample_id'])
            ok, image = capture.retrieve()
            if not ok or image.shape[:2] != (meta['height'], meta['width']):
              raise ValueError('ORIGINAL_HOLDOUT_GEOMETRY_MISMATCH')
            ok, encoded = cv2.imencode('.png', image)
            if not ok:
              raise ValueError('HOLDOUT_PNG_ENCODE_FAILED')
            data = encoded.tobytes()
            old.atomic_image(images_dir / (sample['sample_id'] + '.png'), data)
            row = h.image_receipt(manifest, auth, sample['sample_id'], digest(data))
            h.write_immutable(rows_dir / (sample['sample_id'] + '.json'), row)
            existing[sample['sample_id']] = row
        finally:
          capture.release()
      print('Materialized', len(existing), '/', h.EXPECTED, flush=True)
    rows = [existing[s['sample_id']] for s in samples]
    package = h.materialization_complete(manifest, auth, rows)
    h.write_immutable(output / 'materialization.json', package)
    return {'status': package['status'], 'materialized': len(rows), 'cached_images_revalidated': reused,
            'new_frames_materialized': len(rows) - reused, 'holdout_selection_sha256': auth['holdout_selection_sha256'],
            'package_sha256': package['receipt_sha256'], 'human_annotations': 0, 'detector_inference': 'NOT_RUN',
            'ai_review': 'NOT_RUN', **h.FIREWALL}


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  for name in ('source-root', 'original-cache', 'output'):
    parser.add_argument('--' + name, type=Path, required=True)
  parser.add_argument('--authorize-original-sixty-only', action='store_true')
  args = parser.parse_args()
  import json
  print(json.dumps(materialize(args.source_root, args.original_cache, args.output,
                              acknowledge=args.authorize_original_sixty_only)), flush=True)


if __name__ == '__main__':
  main()
