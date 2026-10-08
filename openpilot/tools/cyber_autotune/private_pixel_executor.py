"""Read-only camera source, isolated GPU inference, local private persistent store.

Plan only reads file metadata/container headers and hashes encoded bytes.
Execution requires a separately frozen manifest and explicit authorization.
No log-message parser, model output, reference admission or production hooks.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from datetime import datetime, UTC

from openpilot.tools.cyber_autotune import private_pixel_execution as p
from openpilot.tools.cyber_autotune import private_camera_metadata as metadata_parser
from openpilot.tools.cyber_autotune import lane_public_storage as storage
from openpilot.tools.cyber_autotune import lane_detector_runner as detector
from openpilot.tools.cyber_autotune import lane_detector_execution as e
from openpilot.tools.cyber_autotune.lane_public_protocol import sample_detector_lane_diagnostics
from openpilot.tools.cyber_autotune.lane_tail_report import seal
from openpilot.tools.cyber_autotune.native_protocol import digest


def utc():
  return datetime.now(UTC).isoformat().replace('+00:00', 'Z')


def guarded_open(manifest, authorization, sample_id, opener):
  p.require_frame(manifest, authorization, sample_id)
  return opener()


@contextmanager
def verified_video(path, expected_sha, expected_bytes):
  """No-follow verified immutable copy protects source races before decoding."""
  path = Path(path)
  if any(v.is_symlink() for v in (path, *path.parents)):
    raise ValueError('VIDEO_SYMLINK_FORBIDDEN')
  try:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
      if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode) or not 0 < expected_bytes <= 128 * 1024 * 1024:
        raise ValueError('BOUNDED_REGULAR_VIDEO_REQUIRED')
      data = stream.read(expected_bytes + 1)
    if len(data) != expected_bytes or digest(data) != expected_sha:
      raise ValueError('SOURCE_VIDEO_IDENTITY_MISMATCH')
  except OSError as exc:
    raise ValueError('SOURCE_NO_FOLLOW_READ_FAILED') from exc
  with sealed_bytes(data) as snapshot:
    yield snapshot


@contextmanager
def sealed_bytes(data):
  import ctypes
  import fcntl
  libc = ctypes.CDLL(None, use_errno=True)
  libc.memfd_create.argtypes, libc.memfd_create.restype = [ctypes.c_char_p, ctypes.c_uint], ctypes.c_int
  fd = libc.memfd_create(b'private-qcamera', 3)
  if fd < 0:
    raise ValueError('VIDEO_MEMFD_FAILED')
  try:
    with os.fdopen(os.dup(fd), 'wb') as stream:
      stream.write(data)
    fcntl.fcntl(fd, 1033, 15)
    if fcntl.fcntl(fd, 1034) != 15:
      raise ValueError('VIDEO_SEAL_FAILED')
    yield '/proc/self/fd/' + str(fd)
  finally:
    os.close(fd)


def hash_file(path):
  if any(v.is_symlink() for v in (path, *path.parents)):
    raise ValueError('PRIVATE_SOURCE_SYMLINK_FORBIDDEN')
  fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
  with os.fdopen(fd, 'rb') as stream:
    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
      raise ValueError('REGULAR_CAMERA_FILE_REQUIRED')
    value = hashlib.sha256()
    while block := stream.read(1024 * 1024):
      value.update(block)
    return value.hexdigest()


def holdout_plan(manifest):
  p.validate_manifest(manifest)
  return seal({
    'schema': 'PRIVATE_FROZEN_HUMAN_HOLDOUT_V1', 'manifest_sha256': manifest['receipt_sha256'],
    'samples': [r for r in manifest['selected'] if r['role'] == 'HOLDOUT'],
    'status': 'PRIVATE_HUMAN_HOLDOUT_PENDING', 'labels': [],
    'image_materialization_allowed_this_run': False, 'inference_allowed_this_run': False,
    'review_workflow': 'ORIGINAL_IMAGE_BLIND_FIRST_THEN_OPTIONAL_DETECTOR_DIAGNOSTIC_OVERLAY',
    'taxonomy': ['CLEAR_TWO_BOUNDARIES', 'ONE_BOUNDARY_VISIBLE', 'MARKING_AMBIGUOUS', 'INTERSECTION_MERGE',
                 'DETECTOR_MISS_SUSPECTED', 'DETECTOR_FALSE_POSITIVE_SUSPECTED', 'UNREVIEWABLE'],
    'model_and_candidate_overlay_allowed': False, 'publish_this_artifact': False, **p.FIREWALL,
  })


def plan(root, output, *, acknowledged):
  if acknowledged is not True:
    raise ValueError('EXPLICIT_DIAGNOSTIC_EXCEPTION_ACKNOWLEDGMENT_REQUIRED')
  root, output = p.private_directories(root, output)
  output.mkdir(parents=True, exist_ok=True, mode=0o700)
  if (output / 'manifest.json').exists():
    raise ValueError('FROZEN_PLAN_ALREADY_EXISTS_USE_RUN_OR_NEW_DECLARED_EXPERIMENT')
  policy = p.sampling_policy(utc())
  p.immutable_json(output / 'sampling-policy.json', policy)  # Before selecting/probing any frames.
  files = sorted(root.rglob('qcamera.ts'))
  if not files:
    raise ValueError('PRIVATE_INPUT_UNUSABLE_NO_AUDITED_ROAD_CAMERA')
  metadata, unavailable = [], []
  for path in files:
    # Encoded TS packet/SPS/AUD metadata only; no decoder library invocation.
    if path.is_symlink() or '--' not in path.parent.name or not path.parent.name.rsplit('--', 1)[1].isdigit():
      raise ValueError('UNSUPPORTED_PRIVATE_SEGMENT_NAMING')
    source_sha = hash_file(path)
    try:
      with verified_video(path, source_sha, path.stat().st_size) as snapshot:
        camera_metadata = metadata_parser.ts_metadata(Path(snapshot).read_bytes())
      if camera_metadata['frame_count'] < 10:
        raise ValueError('SEGMENT_TOO_SHORT')
    except ValueError as exc:
      unavailable.append({'source_sha256': source_sha, 'source_bytes': path.stat().st_size,
                          'status': 'PRIVATE_CAMERA_SOURCE_UNUSABLE', 'reason': str(exc)})
      continue  # Explicit bound disposition; unknown errors reject at manifest validation.
    relative = path.relative_to(root).as_posix()
    metadata.append({
      'route_id': digest((str(path.parent.parent.relative_to(root)) + '/' + path.parent.name.rsplit('--', 1)[0]).encode()),
      'segment_id': digest(str(path.parent.relative_to(root)).encode()), 'source_sha256': source_sha,
      'source_bytes': path.stat().st_size, **camera_metadata, 'camera_role': 'NARROW_ROAD', 'source_key': relative,
    })
  manifest = p.freeze_manifest(metadata, policy, digest(str(root).encode()), utc(), unavailable_sources=unavailable)
  p.immutable_json(output / 'manifest.json', manifest)
  head = subprocess.check_output(['git', '-C', str(p.ROOT), 'rev-parse', 'HEAD'], text=True).strip()
  authorization = p.authorize(manifest, head, utc(), acknowledged=True)
  p.immutable_json(output / 'authorization.json', authorization)
  p.immutable_json(output / 'holdout-plan.json', holdout_plan(manifest))
  print(json.dumps({'selected': len(manifest['selected']), 'development': sum(r['role'] == 'DEVELOPMENT' for r in manifest['selected']),
                    'holdout': sum(r['role'] == 'HOLDOUT' for r in manifest['selected']),
                    'segments': len(metadata), 'manifest_sha256': manifest['receipt_sha256']}), flush=True)


def atomic_image(path, data):
  # O_NOFOLLOW on directory handles prevents redirecting raw bytes via cache symlinks.
  if any(v.is_symlink() for v in (path, *path.parents)):
    raise ValueError('PRIVATE_IMAGE_SYMLINK_FORBIDDEN')
  path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
  directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
  name = '.' + path.name + '.pending'
  try:
    if path.exists():
      if hash_file(path) != digest(data):
        raise ValueError('IMMUTABLE_DECODED_IMAGE_MISMATCH')
      return
    try:
      os.unlink(name, dir_fd=directory)  # Only our unfinished pre-rename file.
    except FileNotFoundError:
      pass
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    with os.fdopen(fd, 'wb') as stream:
      stream.write(data)
      stream.flush()
      os.fsync(stream.fileno())
    os.rename(name, path.name, src_dir_fd=directory, dst_dir_fd=directory)
    os.fsync(directory)
  finally:
    os.close(directory)


def run(args):
  detector.require_network_isolation(detector.network_interfaces(Path('/proc/self/net/dev').read_text()))
  root, output = p.private_directories(args.root, args.output)
  manifest, auth = [storage.read_json(output / name) for name in ('manifest.json', 'authorization.json')]
  p.require_execution(manifest, auth)
  if digest(str(root).encode()) != manifest['root_identity']:
    raise ValueError('EXACT_PRIVATE_ROOT_REQUIRED')
  public = args.public_runtime
  expected = storage.read_json(p.ROOT / p.preparation.ENV_FILE)
  # Complete exact public environment, including immutable public protocol/input SHA.
  def guard():
    p.require_execution(manifest, auth)
    head = subprocess.check_output(['git', '-C', str(public / 'clrernet-source'), 'rev-parse', 'HEAD'], text=True).strip()
    if head != e.COMMIT:
      raise ValueError('PINNED_DETECTOR_COMMIT_REQUIRED')
    actual = detector.runtime_environment(public / 'clrernet-source', public / 'toolchain-manifest.json',
                                          public / 'full-protocol.json', public / 'full-input-manifest.json')
    detector.require_runtime_match(e._unseal(expected, 'environment_sha256'), actual)
    detector.read_bound_bytes(public / 'clrernet_culane_dla34.pth', expected['weight_sha256'])
  guard()
  import cv2
  import numpy as np
  import torch
  from mmengine.config import Config
  from mmengine.runner import load_checkpoint
  from mmdet.apis import init_detector
  sys.path.insert(0, str(public / 'clrernet-source'))
  from libs.datasets.pipelines import Compose
  torch.manual_seed(0)
  np.random.seed(0)  # noqa: NPY002 - exact existing public legacy RNG setting.
  torch.use_deterministic_algorithms(True)
  torch.backends.cudnn.benchmark = False
  torch.backends.cudnn.allow_tf32 = False
  torch.backends.cuda.matmul.allow_tf32 = False
  if os.environ.get('CUBLAS_WORKSPACE_CONFIG') != ':4096:8':
    raise ValueError('CUBLAS_DETERMINISM_REQUIRED')
  config = Config.fromfile(str(public / 'clrernet-source/configs/clrernet/culane/clrernet_culane_dla34.py'))
  with detector.sealed_weight(public / 'clrernet_culane_dla34.pth', expected['weight_sha256']) as snapshot:
    model = init_detector(config, snapshot, palette='random', device='cuda:0')
    checkpoint = load_checkpoint(model, snapshot, map_location='cpu', strict=False)
  incompatible = model.load_state_dict(checkpoint['state_dict'], strict=False)
  detector.validate_inference_state_keys(incompatible.missing_keys, incompatible.unexpected_keys)
  pipeline = Compose(config.test_dataloader.dataset.pipeline)
  model.eval()

  def infer(image):
    h, w = image.shape[:2]
    canonical_image = cv2.resize(image, (1640, 590), interpolation=cv2.INTER_LINEAR)
    data = pipeline({'filename': 'private-opaque-frame', 'sub_img_name': 'private-opaque-frame', 'img': canonical_image,
                     'gt_points': [], 'id_classes': [], 'id_instances': [], 'img_shape': canonical_image.shape,
                     'ori_shape': canonical_image.shape})
    with torch.no_grad():
      lanes = model.test_step({'inputs': [data['inputs']], 'data_samples': [data['data_samples']]})[0]['lanes']
    sampled = sample_detector_lane_diagnostics(lanes, width=w, height=h)
    return {
      'image_geometry': [h, w], 'lane_count': len(lanes), 'points': sampled['points'],
      'lanes': [{'confidence': float(lane.metadata['conf'].item()),
                 'points': sample_detector_lane_diagnostics([lane], width=w, height=h)['points']} for lane in lanes],
    }

  dev = [r for r in manifest['selected'] if r['role'] == 'DEVELOPMENT']
  images = output / 'images'
  if images.is_symlink():
    raise ValueError('PRIVATE_IMAGE_DIRECTORY_SYMLINK_FORBIDDEN')
  images.mkdir(exist_ok=True, mode=0o700)
  def validator(row):
    p.validate_frame(row, manifest, auth)
    path = images / (row['sample_id'] + '.png')
    if hash_file(path) != row['image_sha256']:
      raise ValueError('CACHED_IMAGE_IDENTITY_MISMATCH')
  with storage.writer_lease(output):
    store = storage.DurableRun(output / 'receipts', auth, [r['sample_id'] for r in dev])
    existing = store.recover(validator)
    reused = len(existing)
    # Even completed/cache-only reuse revalidates every selected source video.
    for metadata in manifest['metadata']:
      selected = [r for r in dev if r['segment_id'] == metadata['segment_id']]
      if not selected:
        continue
      path = root / metadata['source_key']
      with verified_video(path, metadata['source_sha256'], metadata['source_bytes']) as snapshot:
        missing = [r for r in selected if dev.index(r) not in existing]
        if not missing:
          continue
        guard()
        capture = guarded_open(manifest, auth, missing[0]['sample_id'], lambda: cv2.VideoCapture(snapshot))
        try:
          needed = {r['frame_ordinal']: r for r in missing}
          for ordinal in range(max(needed) + 1):
            if not capture.grab():
              raise ValueError('FRAME_ORDINAL_DECODE_UNAVAILABLE')
            if ordinal not in needed:
              continue  # Codec traverses earlier packets; only frozen samples materialized.
            sample = needed[ordinal]
            p.require_frame(manifest, auth, sample['sample_id'])
            ok, image = capture.retrieve()
            if not ok or image.shape[:2] != (metadata['height'], metadata['width']):
              raise ValueError('DECODED_CAMERA_GEOMETRY_MISMATCH')
            first, second = infer(image), infer(image)
            detector.require_repeatability(first, second)
            ok, encoded = cv2.imencode('.png', image)
            if not ok:
              raise ValueError('PRIVATE_FRAME_CACHE_ENCODE_FAILED')
            payload = encoded.tobytes()
            atomic_image(images / (sample['sample_id'] + '.png'), payload)
            row = p.frame_receipt(manifest, auth, sample['sample_id'], digest(payload), first)
            store.put(row['ordinal'], row, validator)
            existing[row['ordinal']] = row
        finally:
          capture.release()
      print(json.dumps({'processed': len(existing), 'expected': len(dev)}), flush=True)
    guard()
    rows = [existing[i] for i in sorted(existing)]
    summary = p.progress_summary(manifest, auth, rows)
    if store.marker_path.exists():
      store.verify_completed(validator)
    else:
      store.complete({'summary.json': summary}, validator, before_marker=guard)
    p.immutable_json(output / 'aggregate.json', summary)
    storage.atomic_json(output / 'latest-resume-audit.json', seal({
      'schema': 'PRIVATE_DIAGNOSTIC_RESUME_AUDIT_V1', 'run_sha256': auth['receipt_sha256'],
      'cached_receipts_verified_and_reused': reused, 'processed': len(existing),
      'all_selected_source_identities_rechecked': True, 'exact_repeatability_new_frames': True, **p.FIREWALL,
    }))
    print(json.dumps({'status': summary['status'], 'processed': len(rows), 'reused': reused}), flush=True)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('operation', choices=('plan', 'run'))
  parser.add_argument('--root', type=Path, required=True)
  parser.add_argument('--output', type=Path, required=True)
  parser.add_argument('--public-runtime', type=Path)
  parser.add_argument('--authorize-diagnostic', action='store_true')
  args = parser.parse_args()
  if args.operation == 'plan':
    plan(args.root, args.output, acknowledged=args.authorize_diagnostic)
  elif args.public_runtime is None:
    raise ValueError('EXACT_PUBLIC_RUNTIME_REQUIRED')
  else:
    run(args)


if __name__ == '__main__':
  main()
