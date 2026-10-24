"""Pinned public CLRNet secondary execution, never selection or private inference."""

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

from openpilot.tools.cyber_autotune import lane_detector_runner as r
from openpilot.tools.cyber_autotune import lane_tail_diagnostics as t
from openpilot.tools.cyber_autotune.lane_public_protocol import sample_detector_lane_diagnostics
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

COMMIT = '7269e9d1c1c650343b6c7febb8e764be538b1aed'
WEIGHT = '3750c1b1a93a4c77c1e159c0f76d60a1b17c7960f1a60f8dd6b4c8ea11917c7c'
CONFIG = 'configs/clrnet/clr_dla34_culane.py'
# Official release omits deterministic config-derived buffers and training-only loss weight.
DECLARED_MISSING_KEYS = {'heads.sample_x_indexs', 'heads.prior_feat_ys', 'heads.prior_ys', 'heads.criterion.weight'}


def validate_state_keys(missing, unexpected):
  if type(missing) is not list or type(unexpected) is not list or set(missing) != DECLARED_MISSING_KEYS or unexpected:
    raise ValueError('CLRNET_INFERENCE_STATE_KEY_MISMATCH')


def environment_receipt(source, protocol, manifest):
  import torch
  import numpy as np
  import mmcv

  packages = {dist.metadata['Name'].lower().replace('_', '-'): importlib.metadata.version(dist.metadata['Name']) for dist in importlib.metadata.distributions()}
  if subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() != COMMIT:
    raise ValueError('PINNED_CLRNET_SOURCE_REQUIRED')
  binary = list((source / 'clrnet/ops').glob('nms_impl*.so'))
  if len(binary) != 1:
    raise ValueError('EXACT_CLRNET_NMS_BINARY_REQUIRED')
  data = {
    'schema': 'CLRNET_SECONDARY_ENVIRONMENT_V1',
    'repo_url': 'https://github.com/Turoad/CLRNet',
    'commit': COMMIT,
    'license': 'Apache-2.0; NMS BSD-3-Clause retained upstream',
    'source_bundle_sha256': r.source_bundle(source),
    'config_sha256': digest((source / CONFIG).read_bytes()),
    'weight_sha256': WEIGHT,
    'nms_sha256': digest(binary[0].read_bytes()),
    'adapter_source_sha256': digest(Path(__file__).read_bytes()),
    'tail_validation_source_sha256': digest(Path(t.__file__).read_bytes()),
    'python': sys.version.split()[0],
    'platform': platform.platform(),
    'packages': dict(sorted(packages.items())),
    'torch': str(torch.__version__),
    'numpy': np.__version__,
    'mmcv': mmcv.__version__,
    'cuda': torch.version.cuda,
    'device': torch.cuda.get_device_name(0),
    'driver': subprocess.check_output(['/usr/lib/wsl/lib/nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader'], text=True).strip(),
    'protocol_file_sha256': digest(protocol.read_bytes()),
    'manifest_file_sha256': digest(manifest.read_bytes()),
    'input': 'BGR/255;1640x590 INTER_LINEAR stretch;crop270;official imgaug Resize800x320',
    'output': 'official NMS50 top4 confidence>=.4; official Lane spline sampled original integer rows',
    'confidence': 'softmax logits from kept proposal, NOT upstream Lane.metadata.conf positive raw logit',
    'determinism': {'seed': 0, 'torch_algorithms': True, 'tf32': False, 'cudnn_benchmark': False, 'cublas': ':4096:8'},
    'device_only': 'CUDA:0_ISOLATED_NETWORK_NAMESPACE',
    'private_input_allowed': False,
  }
  data['environment_sha256'] = digest(canonical(data))
  return data


def main():
  parser = argparse.ArgumentParser()
  for name in ('source', 'weight', 'protocol', 'manifest', 'cache', 'output'):
    parser.add_argument('--' + name, type=Path, required=True)
  parser.add_argument('--freeze-only', action='store_true')
  args = parser.parse_args()
  r.require_network_isolation(r.network_interfaces(Path('/proc/self/net/dev').read_text()))
  sys.path.insert(0, str(args.source))
  import torch
  import numpy as np
  import cv2
  from clrnet.utils.config import Config
  from clrnet.models.registry import build_net
  import clrnet.models  # noqa: F401 - Official registry population.
  from clrnet.datasets.process import Process
  from clrnet.utils.lane import Lane  # noqa: F401 - Explicit official output representation.

  env = environment_receipt(args.source, args.protocol, args.manifest)
  freeze = args.output.with_suffix('.environment.json')
  if freeze.exists():
    if json.loads(freeze.read_bytes()) != env:
      raise ValueError('SECONDARY_ENVIRONMENT_CHANGED_NEW_RUN_REQUIRED')
  else:
    freeze.write_text(json.dumps(env, indent=2, sort_keys=True) + '\n')
  if args.freeze_only:
    print(json.dumps({'environment_sha256': env['environment_sha256']}))
    return
  protocol_bytes = r.read_bound_bytes(args.protocol, env['protocol_file_sha256'])
  manifest_bytes = r.read_bound_bytes(args.manifest, env['manifest_file_sha256'])
  protocol, manifest = json.loads(protocol_bytes), json.loads(manifest_bytes)
  r.validate_protocol_pairs(protocol, manifest)
  files = r.verify_inputs(args.cache, manifest)
  if os.environ.get('CUBLAS_WORKSPACE_CONFIG') != ':4096:8':
    raise ValueError('CUBLAS_DETERMINISM_NOT_FROZEN')
  torch.manual_seed(0)
  np.random.seed(0)  # noqa: NPY002
  torch.use_deterministic_algorithms(True)
  torch.backends.cudnn.benchmark = False
  torch.backends.cudnn.allow_tf32 = False
  torch.backends.cuda.matmul.allow_tf32 = False
  config = Config.fromfile(str(args.source / CONFIG))
  model = build_net(config).cuda().eval()
  with r.sealed_weight(args.weight, WEIGHT) as snapshot:
    checkpoint = torch.load(snapshot, map_location='cpu')
  state = {k.removeprefix('module.'): v for k, v in checkpoint['net'].items()}
  initialized = {name: digest(canonical(model.state_dict()[name].cpu().tolist())) for name in sorted(DECLARED_MISSING_KEYS)}
  incompatible = model.load_state_dict(state, strict=False)
  validate_state_keys(incompatible.missing_keys, incompatible.unexpected_keys)
  if initialized != {name: digest(canonical(model.state_dict()[name].cpu().tolist())) for name in sorted(DECLARED_MISSING_KEYS)}:
    raise ValueError('COMPUTED_STATE_INITIALIZATION_CHANGED')
  pipeline = Process(config.val_process, config)
  durations = []

  def infer():
    records = []
    for pair in protocol['pairs']:
      image = cv2.imdecode(np.frombuffer(files[pair['image']], dtype=np.uint8), cv2.IMREAD_COLOR)
      if image is None:
        raise ValueError('PUBLIC_FRAME_DECODE_FAILED')
      h, w = image.shape[:2]
      canonical_image = cv2.resize(image, (1640, 590), interpolation=cv2.INTER_LINEAR)
      data = pipeline({'img': canonical_image[270:], 'lanes': []})
      torch.cuda.synchronize()
      started = time.perf_counter()
      with torch.no_grad():
        output = model(data['img'].unsqueeze(0).cuda())
        proposals = model.heads.get_lanes(output.clone(), as_lanes=False)[0]
        lanes, scores = [], []
        for proposal in proposals:
          decoded = model.heads.predictions_to_pred(proposal.unsqueeze(0))
          if decoded:
            if len(decoded) != 1:
              raise ValueError('PROPOSAL_LANE_BINDING_MISMATCH')
            lanes.extend(decoded)
            scores.append(float(torch.softmax(proposal[:2], dim=0)[1]))
      torch.cuda.synchronize()
      durations.append(time.perf_counter() - started)
      sampling = sample_detector_lane_diagnostics(lanes, width=w, height=h)
      record = {
        'image': pair['image'],
        'image_geometry': [h, w],
        'lane_count': len(lanes),
        'points': sampling['points'],
        'sampling': sampling,
        'unavailable_reason': None,
        'lanes': [sample_detector_lane_diagnostics([lane], width=w, height=h)['points'] for lane in lanes],
        'scores': scores,
      }
      t.validate_raw_lanes(record, np.zeros((h, w), dtype=bool))
      records.append(record)
    return records

  state_before = str(model.heads.prior_ys.dtype)
  first = infer()
  state_after_first = str(model.heads.prior_ys.dtype)
  second = infer()
  exact = canonical(first) == canonical(second)
  differences = [a['image'] for a, b in zip(first, second, strict=True) if canonical(a) != canonical(b)]
  args.output.with_suffix('.second-records.json').write_text(json.dumps(second, sort_keys=True) + '\n')
  report = {
    'schema': 'PUBLIC_CLRNET_CAPTURE_V1',
    'environment_sha256': env['environment_sha256'],
    'protocol_file_sha256': digest(protocol_bytes),
    'manifest_file_sha256': digest(manifest_bytes),
    'capture_source_sha256': digest(Path(__file__).read_bytes()),
    'records_sha256': digest(canonical(first)),
    'initialized_buffers_sha256': digest(canonical(initialized)),
    'exact_repeatability': exact,
    'historical_union_exact_match': None,
    'detector_status': 'DIAGNOSTIC_REPEATABLE' if exact else 'REJECTED_FOR_EXACT_REPEATABILITY',
    'repeat_differing_frames': differences,
    'prior_ys_dtype_before': state_before,
    'prior_ys_dtype_after_first': state_after_first,
    'second_records_sha256': digest(canonical(second)),
    'frames': len(first),
    'repetitions': 2,
    'private_input_opened': False,
    'candidate_outputs_used_for_reference': False,
    'openpilot_path_lane_used': False,
    'reference_promotable': False,
    'official_reproduction_status': 'NOT_RUN_CULANE_DATASET_UNAVAILABLE',
    'runtime_seconds': {'median': float(np.median(durations)), 'p95': float(np.quantile(durations, 0.95))},
  }
  report['receipt_sha256'] = digest(canonical(report))
  args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
  args.output.with_suffix('.records.json').write_text(json.dumps(first, sort_keys=True) + '\n')
  print(json.dumps(report))


if __name__ == '__main__':
  main()
