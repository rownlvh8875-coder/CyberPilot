"""Exact public CLRerNet on already-materialized private sixty; hidden outputs.

No sample selection, human labels, thresholds, external network or new decode
from source videos. Actual GPU entrypoint requires the original public runtime.
"""
import argparse
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

from openpilot.tools.cyber_autotune import private_holdout_contract as h
from openpilot.tools.cyber_autotune import private_holdout_hidden as hidden
from openpilot.tools.cyber_autotune import private_pixel_execution as p
from openpilot.tools.cyber_autotune import private_pixel_executor as original
from openpilot.tools.cyber_autotune import lane_public_storage as storage
from openpilot.tools.cyber_autotune import lane_detector_runner as detector
from openpilot.tools.cyber_autotune import lane_detector_execution as e
from openpilot.tools.cyber_autotune.lane_public_protocol import sample_detector_lane_diagnostics


def read_image(root, package, auth, ordinal):
  def read():
    im = hidden.image(package, ordinal)
    path = h.private_path(Path(root) / 'images' / (im['sample_id'] + '.png'))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
      if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
        raise ValueError('REGULAR_BOUND_IMAGE_REQUIRED')
      data = stream.read(64 * 1024 * 1024 + 1)
    if len(data) > 64 * 1024 * 1024 or h.digest(data) != im['image_sha256']:
      raise ValueError('EXACT_EXISTING_IMAGE_SHA_REQUIRED')
    return data
  return hidden.guarded_input(package, auth, ordinal, read)


def run_engine(raw, output, infer, guard, head, *, acknowledge):
  raw, output = p.private_directories(raw, output)
  package = h.read(raw / 'materialization.json')
  hidden.validate_package(package)
  output.mkdir(parents=True, exist_ok=True, mode=0o700)
  with storage.writer_lease(output):
    if (output / 'authorization.json').exists():
      auth = h.read(output / 'authorization.json')
    else:
      auth = hidden.authorize(package, head, original.utc(), acknowledged=acknowledge)
      h.write_immutable(output / 'authorization.json', auth)
    hidden.require_execution(package, auth)
    guard()  # Must precede opening any frame, including cached-only re-entry.
    directory = h.private_path(output / 'rows')
    directory.mkdir(exist_ok=True, mode=0o700)
    names = {im['sample_id'] + '.json' for im in package['images']}
    if {path.name for path in directory.glob('*.json')} - names:
      raise ValueError('UNKNOWN_HIDDEN_RECEIPT')
    existing = {}
    # Validate every cached row before any fresh inference, not only when visited.
    for ordinal, im in enumerate(package['images']):
      path = directory / (im['sample_id'] + '.json')
      if path.exists():
        row = h.read(path)
        hidden.validate_detector_row(package, auth, ordinal, row)
        read_image(raw, package, auth, ordinal)
        existing[ordinal] = row
    reused = len(existing)
    for ordinal, im in enumerate(package['images']):
      if ordinal in existing:
        continue
      guard()
      data = read_image(raw, package, auth, ordinal)
      first, second = infer(data), infer(data)
      row = hidden.detector_row(package, auth, ordinal, first, second, original.utc())
      h.write_immutable(directory / (im['sample_id'] + '.json'), row)
      existing[ordinal] = row
      # Technical execution progress only; no confidence/output/category leakage.
      print(json.dumps({'processed': len(existing), 'expected': h.EXPECTED}), flush=True)
    guard()
    completion = hidden.complete(package, auth, [existing[i] for i in range(h.EXPECTED)])
    h.write_immutable(output / 'execution-complete.json', completion)
    return {'status': completion['status'], 'processed': h.EXPECTED, 'reused': reused,
            'completion_sha256': completion['receipt_sha256'], 'human_evaluation': 'NOT_RUN',
            'ai_prereview': 'NOT_RUN_OPTIONAL_LOCAL_VISION_ENVIRONMENT_NOT_FROZEN', **h.FIREWALL}


def frozen_engine(public):
  """Adapt the exact original private/public pipeline, not private-specific tuning."""
  detector.require_network_isolation(detector.network_interfaces(Path('/proc/self/net/dev').read_text()))
  expected = storage.read_json(p.ROOT / p.preparation.ENV_FILE)

  def guard():
    head = subprocess.check_output(['git', '-C', str(public / 'clrernet-source'), 'rev-parse', 'HEAD'], text=True).strip()
    if head != e.COMMIT:
      raise ValueError('EXACT_PUBLIC_DETECTOR_COMMIT_REQUIRED')
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
  np.random.seed(0)  # noqa: NPY002 - unchanged frozen public legacy RNG.
  torch.use_deterministic_algorithms(True)
  torch.backends.cudnn.benchmark = False
  torch.backends.cudnn.allow_tf32 = False
  torch.backends.cuda.matmul.allow_tf32 = False
  if os.environ.get('CUBLAS_WORKSPACE_CONFIG') != ':4096:8':
    raise ValueError('FROZEN_CUBLAS_DETERMINISM_REQUIRED')
  config = Config.fromfile(str(public / 'clrernet-source/configs/clrernet/culane/clrernet_culane_dla34.py'))
  with detector.sealed_weight(public / 'clrernet_culane_dla34.pth', expected['weight_sha256']) as snapshot:
    model = init_detector(config, snapshot, palette='random', device='cuda:0')
    checkpoint = load_checkpoint(model, snapshot, map_location='cpu', strict=False)
  incompatible = model.load_state_dict(checkpoint['state_dict'], strict=False)
  detector.validate_inference_state_keys(incompatible.missing_keys, incompatible.unexpected_keys)
  pipeline = Compose(config.test_dataloader.dataset.pipeline)
  model.eval()

  def infer(data):
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
      raise ValueError('EXISTING_RAW_PNG_UNDECODABLE')
    height, width = image.shape[:2]
    canonical_image = cv2.resize(image, (1640, 590), interpolation=cv2.INTER_LINEAR)
    batch = pipeline({'filename': 'private-opaque-frame', 'sub_img_name': 'private-opaque-frame', 'img': canonical_image,
                      'gt_points': [], 'id_classes': [], 'id_instances': [], 'img_shape': canonical_image.shape,
                      'ori_shape': canonical_image.shape})
    with torch.no_grad():
      lanes = model.test_step({'inputs': [batch['inputs']], 'data_samples': [batch['data_samples']]})[0]['lanes']
    sampled = sample_detector_lane_diagnostics(lanes, width=width, height=height)
    return {'image_geometry': [height, width], 'lane_count': len(lanes), 'points': sampled['points'],
            'lanes': [{'confidence': float(lane.metadata['conf'].item()),
                       'points': sample_detector_lane_diagnostics([lane], width=width, height=height)['points']} for lane in lanes]}
  return infer, guard


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  for name in ('raw-cache', 'output', 'public-runtime'):
    parser.add_argument('--' + name, type=Path, required=True)
  parser.add_argument('--authorize-hidden-inference', action='store_true')
  args = parser.parse_args()
  # Pin/authorize output before model initialization or any private image open.
  raw, output = p.private_directories(args.raw_cache, args.output)
  package = h.read(raw / 'materialization.json')
  head = subprocess.check_output(['git', '-C', str(p.ROOT), 'rev-parse', 'HEAD'], text=True).strip()
  output.mkdir(parents=True, exist_ok=True, mode=0o700)
  with storage.writer_lease(output):
    if not (output / 'authorization.json').exists():
      h.write_immutable(output / 'authorization.json',
                        hidden.authorize(package, head, original.utc(), acknowledged=args.authorize_hidden_inference))
    hidden.require_execution(package, h.read(output / 'authorization.json'))
  infer, guard = frozen_engine(args.public_runtime)
  print(json.dumps(run_engine(raw, output, infer, guard, head, acknowledge=args.authorize_hidden_inference)), flush=True)


if __name__ == '__main__':
  main()
