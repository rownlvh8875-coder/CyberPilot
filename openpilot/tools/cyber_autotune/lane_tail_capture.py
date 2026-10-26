"""Public-only confidence/lane capture; preserves the immutable legacy runner."""

import argparse
import json
import os
from pathlib import Path
import sys
import time

from openpilot.tools.cyber_autotune import lane_detector_runner as r
from openpilot.tools.cyber_autotune import lane_detector_execution as e
from openpilot.tools.cyber_autotune import lane_tail_diagnostics as t
from openpilot.tools.cyber_autotune.lane_public_protocol import sample_detector_lane_diagnostics
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


def capture_binding(environment, protocol_bytes, manifest_bytes):
  return {
    'schema': 'PUBLIC_LANE_CAPTURE_V1',
    'environment_sha256': environment['environment_sha256'],
    'protocol_file_sha256': digest(protocol_bytes),
    'manifest_file_sha256': digest(manifest_bytes),
    'capture_source_sha256': digest(Path(__file__).read_bytes()),
    'tail_validation_source_sha256': digest(Path(t.__file__).read_bytes()),
    'candidate_outputs_used_for_reference': False,
    'openpilot_path_lane_used': False,
    'private_input_opened': False,
    'reference_promotable': False,
  }


LEGACY_KEYS = {'image', 'image_geometry', 'lane_count', 'points', 'sampling', 'unavailable_reason'}


def require_historical_artifact(historical, expected):
  if (
    type(historical) is not list
    or not historical
    or any(type(item) is not dict or set(item) != LEGACY_KEYS for item in historical)
    or digest(canonical(historical)) != expected
  ):
    raise ValueError('PUBLISHED_HISTORICAL_ARTIFACT_MISMATCH')


def require_historical_union(records, historical):
  if (
    type(historical) is not list
    or not historical
    or len(records) != len(historical)
    or any(type(item) is not dict or set(item) != LEGACY_KEYS for item in historical)
  ):
    raise ValueError('EXACT_HISTORICAL_SCHEMA_REQUIRED')
  comparable = [{k: record[k] for k in LEGACY_KEYS} for record in records]
  r.require_repeatability(comparable, historical)


def main():
  parser = argparse.ArgumentParser()
  for name in ('source', 'weight', 'environment', 'toolchain-manifest', 'protocol', 'manifest', 'cache', 'historical', 'historical-report', 'output'):
    parser.add_argument('--' + name, type=Path, required=True)
  args = parser.parse_args()
  r.require_network_isolation(r.network_interfaces(Path('/proc/self/net/dev').read_text()))
  environment = json.loads(args.environment.read_bytes())
  e.freeze_environment(e._unseal(environment, 'environment_sha256'))
  r.require_runtime_match(
    e._unseal(environment, 'environment_sha256'), r.runtime_environment(args.source, args.toolchain_manifest, args.protocol, args.manifest)
  )
  protocol_bytes = r.read_bound_bytes(args.protocol, environment['public_protocol_file_sha256'])
  manifest_bytes = r.read_bound_bytes(args.manifest, environment['public_input_manifest_file_sha256'])
  protocol, manifest = json.loads(protocol_bytes), json.loads(manifest_bytes)
  r.validate_protocol_pairs(protocol, manifest)
  files = r.verify_inputs(args.cache, manifest)
  published = json.loads(args.historical_report.read_bytes())
  e._unseal(published)
  if (
    published['environment_sha256'] != environment['environment_sha256']
    or published['manifest_file_sha256'] != digest(manifest_bytes)
    or published['protocol_file_sha256'] != digest(protocol_bytes)
    or published['exact_repeatability'] is not True
  ):
    raise ValueError('PUBLISHED_HISTORICAL_RUN_BINDING_MISMATCH')
  fd = os.open(args.historical, os.O_RDONLY | os.O_NOFOLLOW)
  with os.fdopen(fd, 'rb') as stream:
    historical_bytes = stream.read(128 * 1024 * 1024 + 1)
  if len(historical_bytes) > 128 * 1024 * 1024:
    raise ValueError('HISTORICAL_ARTIFACT_RESOURCE_CAP')
  historical = json.loads(historical_bytes)
  require_historical_artifact(historical, published['prediction_artifact_sha256'])
  binding = capture_binding(environment, protocol_bytes, manifest_bytes)
  binding['historical_result_receipt_sha256'] = published['receipt_sha256']
  binding['historical_prediction_artifact_sha256'] = digest(canonical(historical))
  binding['historical_prediction_file_sha256'] = digest(historical_bytes)
  args.output.with_suffix('.freeze.json').write_text(json.dumps(binding, sort_keys=True, indent=2) + '\n')

  import cv2
  import numpy as np
  import torch
  from mmengine.config import Config
  from mmengine.runner import load_checkpoint
  from mmdet.apis import init_detector

  sys.path.insert(0, str(args.source))
  from libs.datasets.pipelines import Compose

  torch.manual_seed(0)
  np.random.seed(0)  # noqa: NPY002
  torch.use_deterministic_algorithms(True)
  torch.backends.cudnn.benchmark = False
  torch.backends.cudnn.allow_tf32 = False
  torch.backends.cuda.matmul.allow_tf32 = False
  if os.environ.get('CUBLAS_WORKSPACE_CONFIG') != ':4096:8':
    raise ValueError('CUBLAS_DETERMINISM_NOT_FROZEN')
  config = Config.fromfile(str(args.source / 'configs/clrernet/culane/clrernet_culane_dla34.py'))
  with r.sealed_weight(args.weight, environment['weight_sha256']) as snapshot:
    model = init_detector(config, snapshot, palette='random', device='cuda:0')
    checkpoint = load_checkpoint(model, snapshot, map_location='cpu', strict=False)
  incompatible = model.load_state_dict(checkpoint['state_dict'], strict=False)
  r.validate_inference_state_keys(incompatible.missing_keys, incompatible.unexpected_keys)
  pipeline = Compose(config.test_dataloader.dataset.pipeline)
  model.eval()

  def infer():
    records, durations = [], []
    for pair in protocol['pairs']:
      img = cv2.imdecode(np.frombuffer(files[pair['image']], dtype=np.uint8), cv2.IMREAD_COLOR)
      if img is None:
        raise ValueError('PUBLIC_FRAME_DECODE_FAILED')
      h, w = img.shape[:2]
      image = cv2.resize(img, (1640, 590), interpolation=cv2.INTER_LINEAR)
      data = pipeline(
        {
          'filename': pair['image'],
          'sub_img_name': pair['image'],
          'img': image,
          'gt_points': [],
          'id_classes': [],
          'id_instances': [],
          'img_shape': image.shape,
          'ori_shape': image.shape,
        }
      )
      torch.cuda.synchronize()
      started = time.perf_counter()
      with torch.no_grad():
        result = model.test_step({'inputs': [data['inputs']], 'data_samples': [data['data_samples']]})[0]
      torch.cuda.synchronize()
      durations.append(time.perf_counter() - started)
      sampling = sample_detector_lane_diagnostics(result['lanes'], width=w, height=h)
      lane_points = [sample_detector_lane_diagnostics([lane], width=w, height=h)['points'] for lane in result['lanes']]
      scores = [float(s) for s in result['scores']]
      if len(scores) != len(lane_points):
        raise ValueError('SCORE_LANE_BINDING_MISMATCH')
      records.append(
        {
          'image': pair['image'],
          'image_geometry': [h, w],
          'lane_count': len(result['lanes']),
          'points': sampling['points'],
          'sampling': sampling,
          'unavailable_reason': None,
          'lanes': lane_points,
          'scores': scores,
        }
      )
    for record in records:
      t.validate_raw_lanes(record, np.zeros(record['image_geometry'], dtype=bool))
    return records, durations

  first, durations = infer()
  second, _ = infer()
  r.require_repeatability(first, second)
  require_historical_union(first, historical)
  report = {
    **binding,
    'exact_repeatability': True,
    'historical_union_exact_match': True,
    'repetitions': 2,
    'frames': len(first),
    'records_sha256': digest(canonical(first)),
    'runtime_seconds': {'median': float(np.median(durations)), 'p95': float(np.quantile(durations, 0.95))},
  }
  report['receipt_sha256'] = digest(canonical(report))
  args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
  args.output.with_suffix('.records.json').write_text(json.dumps(first, sort_keys=True) + '\n')
  print(json.dumps(report))


if __name__ == '__main__':
  main()
