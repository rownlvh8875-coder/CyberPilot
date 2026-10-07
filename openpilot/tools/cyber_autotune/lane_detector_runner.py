"""Public-only CLRerNet diagnostic runner. Optional external dependencies only.

Run in an isolated Linux network namespace. No private route input interface,
network acquisition, confidence search, training, reference serializer or
production dependency changes. All public bytes are verified before decoding.
"""

import argparse
from contextlib import contextmanager
import fcntl
import ctypes
import hashlib
import io
import importlib.metadata
import importlib.util
import json
import os
import platform
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import time

from openpilot.tools.cyber_autotune import lane_detector_execution as e
from openpilot.tools.cyber_autotune.lane_marking_metrics import category2_mask, marking_frame
from openpilot.tools.cyber_autotune.lane_public_protocol import region_reports, sample_detector_lane_diagnostics
from openpilot.tools.cyber_autotune.contracts import is_sha256
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

COMMA10K_COMMIT = '6c205fe4c43cc53b2b1befafb1060d0606555027'
TRAINING_ONLY_MISSING_KEYS = {'bbox_head.loss_seg.criterion.weight', 'bbox_head.seg_decoder.conv.weight', 'bbox_head.seg_decoder.conv.bias'}
# Official release omits these three training-only keys; predict() never calls loss()/forward_seg().


def validate_inference_state_keys(missing, unexpected):
  if type(missing) is not list or type(unexpected) is not list or set(missing) != TRAINING_ONLY_MISSING_KEYS or unexpected:
    raise ValueError('INFERENCE_STATE_KEYS_MISMATCH')


MAX_PUBLIC_FILE_BYTES = 20 * 1024 * 1024  # Acquisition cap, not error/coverage threshold.


def validate_manifest(manifest):
  if (type(manifest) is not dict or set(manifest) != {'schema', 'dataset_commit', 'protocol_file_sha256', 'files', 'semantic_content_opened'}
      or manifest['schema'] != 'PUBLIC_DIAGNOSTIC_INPUT_MANIFEST_V1' or manifest['dataset_commit'] != COMMA10K_COMMIT
      or not is_sha256(manifest['protocol_file_sha256']) or manifest['semantic_content_opened'] is not False
      or type(manifest['files']) is not list or not manifest['files']):
    raise ValueError('PINNED_PUBLIC_MANIFEST_BEFORE_SEMANTIC_OPEN_REQUIRED')
  seen = set()
  for item in manifest['files']:
    if type(item) is not dict or set(item) != {'path', 'sha256', 'size', 'git_blob_sha1'}:
      raise ValueError('EXACT_PUBLIC_FILE_IDENTITY_REQUIRED')
    path = item['path']
    if (type(path) is not str or len(PurePosixPath(path).parts) != 2 or path.split('/')[0] not in ('imgs', 'imgs2', 'masks', 'masks2')
        or str(PurePosixPath(path)) != path or not path.endswith('.png') or '..' in path or '\\' in path or path in seen
        or not is_sha256(item['sha256']) or type(item['size']) is not int or not 0 < item['size'] <= MAX_PUBLIC_FILE_BYTES
        or type(item['git_blob_sha1']) is not str or len(item['git_blob_sha1']) != 40
        or any(c not in '0123456789abcdef' for c in item['git_blob_sha1'])):
      raise ValueError('INVALID_OR_DUPLICATE_PUBLIC_FILE_IDENTITY')
    seen.add(path)


def verify_inputs(root, manifest):
  validate_manifest(manifest)
  root = Path(root).absolute()
  if any(p.is_symlink() for p in (root, *root.parents)):
    raise ValueError('PUBLIC_CACHE_SYMLINK_REJECTED')
  verified = {}
  for item in manifest['files']:
    path = root / item['path']
    if any(p.is_symlink() for p in (path, path.parent)):
      raise ValueError('PUBLIC_CACHE_SYMLINK_REJECTED')
    try:
      fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
      with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
          raise ValueError('REGULAR_PUBLIC_INPUT_REQUIRED')
        data = stream.read(MAX_PUBLIC_FILE_BYTES + 1)
    except OSError as exc:
      raise ValueError('PUBLIC_INPUT_NO_FOLLOW_READ_FAILED') from exc
    blob = hashlib.sha1(('blob ' + str(len(data)) + '\0').encode() + data).hexdigest()
    if len(data) != item['size'] or digest(data) != item['sha256'] or blob != item['git_blob_sha1']:
      raise ValueError('PUBLIC_INPUT_FILE_BINDING_MISMATCH')
    verified[item['path']] = data
  return verified


def network_interfaces(proc_net_dev):
  return ' '.join(sorted(line.split(':')[0].strip() for line in proc_net_dev.splitlines()[2:] if ':' in line))


def require_network_isolation(interfaces):
  if interfaces.split() != ['lo']:
    raise ValueError('NETWORK_NAMESPACE_WITH_LOOPBACK_ONLY_REQUIRED')


def require_repeatability(first, second):
  if canonical(first) != canonical(second):
    raise ValueError('DETECTOR_EXACT_REPEATABILITY_FAILED')
  return True


def source_bundle(source):
  paths = subprocess.check_output(['git', '-C', str(source), 'ls-files'], text=True).splitlines()
  return digest(canonical({p: digest((source / p).read_bytes()) for p in sorted(paths)}))


def require_runtime_match(expected, actual):
  if canonical(expected) != canonical(actual):
    raise ValueError('FROZEN_RUNTIME_IDENTITY_MISMATCH')
  return True


def runtime_environment(source, toolchain_manifest, protocol_path, manifest_path):
  """Inspect packages/source/compiled kernels without loading any input/weight."""
  import torch
  from mmengine.config import Config

  sys.path.insert(0, str(source))
  config = Config.fromfile(str(source / 'configs/clrernet/culane/clrernet_culane_dla34.py'))
  packages = {dist.metadata['Name'].lower().replace('_', '-'): dist.version for dist in importlib.metadata.distributions()}
  nms_binary = Path(importlib.util.find_spec('nms.details').origin)
  helpers = Path(__file__).parent
  preprocess = [Path(__file__), helpers / 'lane_public_protocol.py', source / 'libs/datasets/pipelines/alaug.py',
                source / 'libs/datasets/pipelines/compose.py', source / 'libs/datasets/pipelines/lane_formatting.py']
  postprocess = [helpers / 'lane_public_protocol.py', source / 'libs/models/dense_heads/clrernet_head.py', source / 'libs/utils/lane_utils.py']
  toolchain = json.loads(toolchain_manifest.read_bytes())
  return {
    'schema': 'LANE_DETECTOR_ENVIRONMENT_V1', 'detector': 'CLRerNet', 'repository_url': e.REPOSITORY, 'repository_commit': e.COMMIT,
    'license': 'Apache-2.0', 'python': sys.version.split()[0], 'packages': dict(sorted(packages.items())),
    'platform': platform.platform(), 'device': 'cuda:0', 'device_name': torch.cuda.get_device_name(0),
    'cuda_runtime': torch.version.cuda,
    'driver': subprocess.check_output(['/usr/lib/wsl/lib/nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader'], text=True).strip(),
    'compiler': toolchain['compiler'],
    'source_bundle_sha256': source_bundle(source), 'config_sha256': digest(config.pretty_text.encode()), 'weight_sha256': e.WEIGHT,
    'preprocessing_sha256': digest(canonical([digest(path.read_bytes()) for path in preprocess])),
    'postprocessing_sha256': digest(canonical([digest(path.read_bytes()) for path in postprocess])),
    'nms_binary_sha256': digest(nms_binary.read_bytes()), 'package_manifest_sha256': digest(canonical(dict(sorted(packages.items())))),
    'toolchain_manifest_sha256': digest(toolchain_manifest.read_bytes()), 'determinism': e.DETERMINISM,
    'public_protocol_file_sha256': digest(protocol_path.read_bytes()), 'public_input_manifest_file_sha256': digest(manifest_path.read_bytes()),
    'diagnostic_source_sha256': digest(canonical({name: digest((helpers / name).read_bytes()) for name in
      ('lane_detector_runner.py', 'lane_detector_execution.py', 'lane_public_protocol.py', 'lane_marking_metrics.py', 'native_protocol.py', 'contracts.py')})),
  }


def validate_revision_chain(protocol, protocol_sha256, initial_protocol_sha256):
  if protocol_sha256 == initial_protocol_sha256:
    return
  if (protocol.get('initial_protocol_file_sha256') != initial_protocol_sha256
      or not is_sha256(protocol.get('prior_result_file_sha256'))
      or protocol.get('semantic_GT_outputs_seen_before_this_revision') is not True
      or protocol.get('evidence_tier') != 'POST_RESULT_ADAPTER_CORRECTION_DIAGNOSTIC_NOT_QUALIFICATION'):
    raise ValueError('UNDECLARED_POST_RESULT_PROTOCOL_REVISION')


def read_bound_bytes(path, expected):
  if not is_sha256(expected):
    raise ValueError('EXPECTED_FILE_SHA256_REQUIRED')
  try:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
      if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
        raise ValueError('REGULAR_BOUND_FILE_REQUIRED')
      # CLRerNet 63,464,485-byte checkpoint; bounded public artifact reader.
      data = stream.read(128 * 1024 * 1024 + 1)
  except OSError as exc:
    raise ValueError('BOUND_NO_FOLLOW_READ_FAILED') from exc
  if len(data) > 128 * 1024 * 1024 or digest(data) != expected:
    raise ValueError('BOUND_FILE_SHA256_MISMATCH')
  return data


@contextmanager
def sealed_weight(path, expected):
  data = read_bound_bytes(path, expected)
  # Linux UAPI: MFD_CLOEXEC=1, MFD_ALLOW_SEALING=2; F_ADD/GET_SEALS=1033/1034.
  # Bundled portable CPython 3.11 lacks os.memfd_create; call host glibc directly.
  libc = ctypes.CDLL(None, use_errno=True)
  create = libc.memfd_create
  create.argtypes, create.restype = [ctypes.c_char_p, ctypes.c_uint], ctypes.c_int
  fd = create(b'public-clrernet-weight', 3)
  if fd < 0:
    raise OSError(ctypes.get_errno(), 'MEMFD_CREATE_FAILED')
  try:
    with os.fdopen(os.dup(fd), 'wb') as stream:
      stream.write(data)
    # WRITE=8, GROW=4, SHRINK=2, SEAL=1. Verify all immutable-copy seals.
    fcntl.fcntl(fd, 1033, 15)
    if fcntl.fcntl(fd, 1034) != 15:
      raise ValueError('PUBLIC_WEIGHT_MEMFD_SEAL_MISMATCH')
    yield '/proc/self/fd/' + str(fd)
  finally:
    os.close(fd)


def validate_protocol_pairs(protocol, manifest):
  files = {item['path']: item for item in manifest['files']}
  pairs = protocol.get('pairs')
  if type(pairs) is not list or not pairs:
    raise ValueError('NONEMPTY_PUBLIC_PAIRS_REQUIRED')
  seen = set()
  for pair in pairs:
    if type(pair) is not dict or set(pair) != {'image', 'mask', 'image_git_blob_sha1', 'mask_git_blob_sha1'}:
      raise ValueError('EXACT_PUBLIC_PAIR_IDENTITY_REQUIRED')
    image, mask = pair['image'], pair['mask']
    if (type(image) is not str or type(mask) is not str or image.split('/')[0] not in ('imgs', 'imgs2')
        or mask != image.replace('imgs2/', 'masks2/').replace('imgs/', 'masks/')
        or image in seen or image not in files or mask not in files
        or pair['image_git_blob_sha1'] != files[image]['git_blob_sha1'] or pair['mask_git_blob_sha1'] != files[mask]['git_blob_sha1']):
      raise ValueError('PUBLIC_PAIR_BINDING_MISMATCH')
    seen.add(image)
  if set(files) != {pair[k] for pair in pairs for k in ('image', 'mask')}:
    raise ValueError('PUBLIC_PAIR_FILE_SET_MISMATCH')


def require_original_geometry(image_geometry, mask_geometry):
  if tuple(image_geometry) != tuple(mask_geometry):
    raise ValueError('ORIGINAL_IMAGE_MASK_GEOMETRY_MISMATCH')


def require_unchanged_declaration(initial, revision):
  changed_allowed = {'schema', 'geometry_adapter'}
  revision_fields = {'revision_reason', 'prior_result_file_sha256', 'initial_protocol_file_sha256',
                     'semantic_GT_outputs_seen_before_this_revision', 'evidence_tier'}
  if (set(revision) - set(initial) - revision_fields or set(initial) - set(revision)
      or any(canonical(initial[k]) != canonical(revision[k]) for k in initial if k not in changed_allowed)):
    raise ValueError('ADAPTER_REVISION_CHANGED_FROZEN_SELECTION_OR_DETECTOR')


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  for name in ('source', 'cache', 'manifest', 'protocol', 'environment', 'toolchain-manifest', 'weight', 'output'):
    parser.add_argument('--' + name, required=True, type=Path)
  parser.add_argument('--initial-protocol', type=Path)
  parser.add_argument('--prior-result', type=Path)
  args = parser.parse_args()
  require_network_isolation(network_interfaces(Path('/proc/self/net/dev').read_text()))
  environment = json.loads(args.environment.read_bytes())
  if e.freeze_environment(e._unseal(environment, 'environment_sha256')) != environment:
    raise ValueError('ENVIRONMENT_BINDING_MISMATCH')
  if subprocess.check_output(['git', '-C', str(args.source), 'rev-parse', 'HEAD'], text=True).strip() != e.COMMIT:
    raise ValueError('DETECTOR_SOURCE_COMMIT_MISMATCH')
  if source_bundle(args.source) != environment['source_bundle_sha256']:
    raise ValueError('DETECTOR_SOURCE_BUNDLE_MISMATCH')
  require_runtime_match(e._unseal(environment, 'environment_sha256'), runtime_environment(args.source, args.toolchain_manifest, args.protocol, args.manifest))
  manifest_bytes = read_bound_bytes(args.manifest, environment['public_input_manifest_file_sha256'])
  protocol_bytes = read_bound_bytes(args.protocol, environment['public_protocol_file_sha256'])
  manifest, protocol = json.loads(manifest_bytes), json.loads(protocol_bytes)
  validate_revision_chain(protocol, digest(protocol_bytes), manifest['protocol_file_sha256'])
  if digest(protocol_bytes) != manifest['protocol_file_sha256']:
    if args.initial_protocol is None or args.prior_result is None:
      raise ValueError('RETAINED_INITIAL_PROTOCOL_AND_RESULT_REQUIRED')
    initial = json.loads(read_bound_bytes(args.initial_protocol, manifest['protocol_file_sha256']))
    prior = json.loads(read_bound_bytes(args.prior_result, protocol['prior_result_file_sha256']))
    e._unseal(prior)
    if prior['protocol_file_sha256'] != manifest['protocol_file_sha256'] or prior['manifest_file_sha256'] != digest(manifest_bytes):
      raise ValueError('PRIOR_RESULT_LINEAGE_MISMATCH')
    require_unchanged_declaration(initial, protocol)
  validate_manifest(manifest)
  validate_protocol_pairs(protocol, manifest)
  files = verify_inputs(args.cache, manifest)
  if set(files) != {p[k] for p in protocol['pairs'] for k in ('image', 'mask')}:
    raise ValueError('FROZEN_SUBSET_FILE_SET_MISMATCH')

  # No heavyweight imports in the normal CyberPilot environment.
  import cv2
  import numpy as np
  from PIL import Image
  import torch
  from mmengine.config import Config
  from mmengine.runner import load_checkpoint
  from mmdet.apis import init_detector

  sys.path.insert(0, str(args.source))
  from libs.datasets.pipelines import Compose

  if sys.version.split()[0] != environment['python'] or str(torch.__version__) != environment['packages']['torch']:
    raise ValueError('INFERENCE_RUNTIME_VERSION_MISMATCH')
  torch.manual_seed(0)
  np.random.seed(0)  # noqa: NPY002 - Freeze the legacy RNG used by the external official pipeline.
  torch.use_deterministic_algorithms(True)
  torch.backends.cudnn.benchmark = False
  torch.backends.cudnn.allow_tf32 = False
  torch.backends.cuda.matmul.allow_tf32 = False
  if os.environ.get('CUBLAS_WORKSPACE_CONFIG') != ':4096:8':
    raise ValueError('CUBLAS_DETERMINISM_NOT_FROZEN')
  config = Config.fromfile(str(args.source / 'configs/clrernet/culane/clrernet_culane_dla34.py'))
  if digest(config.pretty_text.encode()) != environment['config_sha256']:
    raise ValueError('RESOLVED_CONFIG_BINDING_MISMATCH')
  with sealed_weight(args.weight, environment['weight_sha256']) as snapshot:
    model = init_detector(config, snapshot, palette='random', device='cuda:0')
    checkpoint = load_checkpoint(model, snapshot, map_location='cpu', strict=False)
  incompatible = model.load_state_dict(checkpoint['state_dict'], strict=False)
  validate_inference_state_keys(incompatible.missing_keys, incompatible.unexpected_keys)
  pipeline = Compose(config.test_dataloader.dataset.pipeline)
  model.eval()

  def infer():
    records = []
    for pair in protocol['pairs']:
      img = cv2.imdecode(np.frombuffer(files[pair['image']], dtype=np.uint8), cv2.IMREAD_COLOR)
      if img is None:
        raise ValueError('PUBLIC_FRAME_DECODE_FAILED')
      h, w = img.shape[:2]
      canonical_image = cv2.resize(img, (1640, 590), interpolation=cv2.INTER_LINEAR)
      data = pipeline({'filename': pair['image'], 'sub_img_name': pair['image'], 'img': canonical_image,
                       'gt_points': [], 'id_classes': [], 'id_instances': [], 'img_shape': canonical_image.shape, 'ori_shape': canonical_image.shape})
      torch.cuda.synchronize()
      started = time.perf_counter()
      with torch.no_grad():
        result = model.test_step({'inputs': [data['inputs']], 'data_samples': [data['data_samples']]})[0]
      torch.cuda.synchronize()
      elapsed = time.perf_counter() - started
      try:
        sampling = sample_detector_lane_diagnostics(result['lanes'], width=w, height=h)
        points, reason = sampling['points'], None
      except ValueError as exc:
        points, reason, sampling = [], str(exc), None
      records.append({'image': pair['image'], 'points': points, 'unavailable_reason': reason, 'lane_count': len(result['lanes']),
                      'runtime_seconds': elapsed, 'sampling': sampling, 'image_geometry': [h, w]})
    return records

  first, second = infer(), infer()
  def comparable(records):
    return [{k: v for k, v in record.items() if k != 'runtime_seconds'} for record in records]
  require_repeatability(comparable(first), comparable(second))
  reports, region_sets = [], {name: [] for name in ('far', 'mid', 'near')}
  for pair, result in zip(protocol['pairs'], first, strict=True):
    rgb = np.asarray(Image.open(io.BytesIO(files[pair['mask']])).convert('RGB'))
    mask = category2_mask(rgb)
    require_original_geometry(result['image_geometry'], mask.shape)
    reports.append(marking_frame(mask, result['points']))
    for name, report in region_reports(mask, result['points']).items():
      region_sets[name].append(report)
  report = {
    'schema': 'PUBLIC_CLRERNET_DIAGNOSTIC_RUN_V1', 'scope': 'INCOMPLETE_PUBLIC_DIAGNOSTIC_NOT_QUALIFICATION',
    'environment_sha256': environment['environment_sha256'], 'manifest_file_sha256': digest(manifest_bytes),
    'protocol_file_sha256': digest(protocol_bytes), 'runner_source_sha256': digest(Path(__file__).read_bytes()),
    'exact_repeatability': True, 'repetitions': 2, 'frames_per_repetition': len(first),
    'candidate_outputs_used_for_reference': False, 'openpilot_path_lane_used': False, 'private_input_opened': False,
    'official_reproduction_status': 'DETECTOR_REPRODUCTION_BLOCKED',
    'evidence_tier': protocol.get('evidence_tier', 'INITIAL_FROZEN_PUBLIC_DIAGNOSTIC_NOT_QUALIFICATION'),
    'prior_result_file_sha256': protocol.get('prior_result_file_sha256'),
    'localization': e.localization_summary(reports), 'regions': {name: e.localization_summary(items) for name, items in region_sets.items()},
    'runtime_seconds': {'median': float(np.median([r['runtime_seconds'] for r in first])),
                        'p95': float(np.quantile([r['runtime_seconds'] for r in first], .95))},
    'geometry_unavailable_frames': sum(r['unavailable_reason'] is not None for r in first),
    'prediction_artifact_sha256': digest(canonical(comparable(first))), 'reference_promotable': False,
  }
  report['receipt_sha256'] = digest(canonical(report))
  args.output.parent.mkdir(parents=True, exist_ok=True)
  args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
  args.output.with_suffix('.predictions.json').write_text(json.dumps(comparable(first), sort_keys=True) + '\n')
  print(json.dumps({'frames': len(first), 'repeatability': True, 'report': str(args.output), 'receipt_sha256': report['receipt_sha256']}))


if __name__ == '__main__':
  main()
