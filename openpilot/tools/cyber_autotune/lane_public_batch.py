"""Bounded restartable public full-dataset inference. No downloads/private reader.

Optional CUDA environment; source/config/environment and every acquired input
are frozen before inference. A partial/failing run never grants qualification.
Per-frame sealed receipts stay in external cache, never public raw data.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing
import os
from pathlib import Path
import sys
import subprocess
import time

from openpilot.tools.cyber_autotune import lane_detector_execution as e
from openpilot.tools.cyber_autotune import lane_detector_runner as r
from openpilot.tools.cyber_autotune import lane_tail_diagnostics as t
from openpilot.tools.cyber_autotune import lane_tail_report as report
from openpilot.tools.cyber_autotune.lane_public_protocol import sample_detector_lane_diagnostics
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


def inference_budget_expired(started, now, budget):
  # Replay has a separate finite frame bound. New work receives its own window.
  return started is not None and now - started >= budget


def completion_state(expected, completed, failed):
  if any(type(x) is not int or x < 0 for x in (expected, completed, failed)) or expected == 0 or completed > expected:
    raise ValueError('INVALID_FULL_RUN_COUNTS')
  return 'FAILED_NOT_QUALIFICATION' if failed else 'COMPLETE_DIAGNOSTIC_NOT_QUALIFICATION' if completed == expected else 'PARTIAL_NOT_QUALIFICATION'


def require_primary_environment(current, primary, actual_head):
  allowed = ('public_protocol_file_sha256', 'public_input_manifest_file_sha256')
  if actual_head != e.COMMIT or any(key not in current or key not in primary for key in allowed):
    raise ValueError('ACTUAL_PINNED_PRIMARY_HEAD_REQUIRED')
  expected = dict(primary)
  for key in allowed:
    expected[key] = current[key]
  r.require_runtime_match(expected, current)


def require_replayed_metric(stored, replayed):
  if canonical(stored) != canonical(replayed):
    raise ValueError('FULL_RESUME_METRIC_REPLAY_MISMATCH')


def verify_resume(receipt, binding, ordinal, pair=None, identities=None):
  import numpy as np

  core = report.unseal(receipt)
  expected_keys = {'run_sha256', 'ordinal', 'detector_record', 'ledger', 'pool', 'confidence', 'regions'}
  if set(core) != expected_keys or core['run_sha256'] != binding or type(core['ordinal']) is not int or core['ordinal'] != ordinal:
    raise ValueError('FULL_RUN_RESUME_BINDING_MISMATCH')
  ledger = report.unseal(core['ledger'])
  record = core['detector_record']
  geometry = ledger.get('geometry')
  if (
    type(geometry) is not list
    or len(geometry) != 2
    or any(type(v) is not int or v <= 0 for v in geometry)
    or geometry[0] * geometry[1] > 6_000_000
    or ledger.get('unit') != 'px'
    or ledger.get('reference_promotable') is not False
    or ledger.get('meter_error') is not None
    or ledger.get('ego_lane_association_evaluated') is not False
  ):
    raise ValueError('FULL_RESUME_LEDGER_DOMAIN_MISMATCH')
  if (
    type(record) is not dict
    or record.get('image') != ledger.get('frame_id')
    or record.get('image_geometry') != geometry
    or ledger.get('detector_result_sha256') != digest(canonical(record))
    or any(type(core[k]) is not dict for k in ('pool', 'confidence', 'regions'))
  ):
    raise ValueError('FULL_RESUME_RAW_FRAME_BINDING_MISMATCH')
  t.validate_raw_lanes(record, np.zeros(geometry, dtype=bool))
  if pair is not None:
    if (
      identities is None
      or ledger['frame_id'] != pair['image']
      or ledger['image_sha256'] != identities[pair['image']]['sha256']
      or ledger['gt_mask_sha256'] != identities[pair['mask']]['sha256']
    ):
      raise ValueError('FULL_RESUME_PUBLIC_INPUT_IDENTITY_MISMATCH')
  return core


def metric_job(root, manifest, pair, record):
  files = r.verify_inputs(root, manifest)
  return report.analyze_records(files, manifest, [pair], [record])


def merge_frame_results(values):
  ledger, pool, confidence, regions = [], {}, {}, {}
  for core in values:
    ledger.append(core['ledger'])
    for key, samples in core['pool'].items():
      pool.setdefault(key, []).extend(samples)
    for name, buckets in (('confidence', confidence), ('regions', regions)):
      for key, entry in core[name].items():
        dest = buckets.setdefault(key, {})
        for field, value in entry.items():
          if type(value) is list:
            dest.setdefault(field, []).extend(value)
          else:
            dest[field] = dest.get(field, 0) + value
  return ledger, pool, confidence, regions


def main():
  parser = argparse.ArgumentParser()
  for name in ('source', 'weight', 'environment', 'toolchain-manifest', 'protocol', 'manifest', 'cache', 'output'):
    parser.add_argument('--' + name, type=Path, required=True)
  parser.add_argument('--max-seconds', type=int, default=1800)
  parser.add_argument('--freeze-only', action='store_true')
  args = parser.parse_args()
  if not 1 <= args.max_seconds <= 3600:
    raise ValueError('BOUNDED_RUNTIME_REQUIRED')
  r.require_network_isolation(r.network_interfaces(Path('/proc/self/net/dev').read_text()))
  protocol_bytes, manifest_bytes = args.protocol.read_bytes(), args.manifest.read_bytes()
  protocol, manifest = json.loads(protocol_bytes), json.loads(manifest_bytes)
  r.validate_protocol_pairs(protocol, manifest)
  if len(protocol['pairs']) != 11888 or protocol.get('evidence_tier') != 'DIAGNOSTIC_PUBLIC_GT_AFTER_SUBSET_INSPECTION':
    raise ValueError('EXACT_ALL_PUBLIC_ROAD_PAIRS_REQUIRED')
  primary = json.loads(args.environment.read_bytes())
  e.freeze_environment(e._unseal(primary, 'environment_sha256'))
  current = r.runtime_environment(args.source, args.toolchain_manifest, args.protocol, args.manifest)
  actual_head = subprocess.check_output(['git', '-C', str(args.source), 'rev-parse', 'HEAD'], text=True).strip()
  require_primary_environment(current, e._unseal(primary, 'environment_sha256'), actual_head)
  environment = e.freeze_environment(current)
  run = report.seal(
    {
      'schema': 'FULL_PUBLIC_RUN_FREEZE_V1',
      'environment': environment,
      'producer_source_sha256': digest(Path(__file__).read_bytes()),
      'metric_source_sha256': digest(Path(t.__file__).read_bytes()),
      'report_source_sha256': digest(Path(report.__file__).read_bytes()),
      'policy_sha256': t.policy_sha(t.policy()),
      'max_new_inference_scheduling_seconds': args.max_seconds,
      'max_replay_frames': 11888,
      'budget_semantics': 'validate stored frames first; then start independent new-inference window; drain finite pending metrics',
      'retained_primary_environment_sha256': primary['environment_sha256'],
      'metric_workers': 4,
      'full_repetitions': 1,
      'repeatability_scope': '119 historical subset x2; full frames single pass',
      'protocol_file_sha256': digest(protocol_bytes),
      'manifest_file_sha256': digest(manifest_bytes),
      'private_input_opened': False,
      'reference_promotable': False,
    }
  )
  args.output.mkdir(parents=True, exist_ok=True)
  freeze = args.output / 'run-freeze.json'
  if freeze.exists():
    if json.loads(freeze.read_bytes()) != run:
      raise ValueError('NEW_SOURCE_OR_POLICY_REQUIRES_NEW_FULL_RUN_DIRECTORY')
  else:
    freeze.write_text(json.dumps(run, indent=2, sort_keys=True) + '\n')
  if args.freeze_only:
    print(json.dumps({'run_sha256': run['receipt_sha256']}))
    return
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
  keys = model.load_state_dict(checkpoint['state_dict'], strict=False)
  r.validate_inference_state_keys(keys.missing_keys, keys.unexpected_keys)
  model.eval()
  pipeline = Compose(config.test_dataloader.dataset.pipeline)
  identities = {item['path']: item for item in manifest['files']}
  start, done, pending, failed = time.monotonic(), [], [], 0
  failure_records = []

  def collect():
    nonlocal pending
    for ordinal, destination, future, detector_record, resumed in pending:
      try:
        ledger, pool, confidence, regions = future.result()
      except Exception as exc:
        failure_records.append({'ordinal': ordinal, 'error': type(exc).__name__ + ':' + str(exc)})
        continue
      value = report.seal(
        {
          'run_sha256': run['receipt_sha256'],
          'ordinal': ordinal,
          'detector_record': detector_record,
          'ledger': ledger[0],
          'pool': pool,
          'confidence': confidence,
          'regions': regions,
        }
      )
      if resumed is not None:
        try:
          require_replayed_metric(resumed, report.unseal(value))
        except ValueError as exc:
          failure_records.append({'ordinal': ordinal, 'error': str(exc)})
          continue
      temporary = destination.with_suffix('.tmp')
      temporary.write_text(json.dumps(value, sort_keys=True) + '\n')
      temporary.replace(destination)
      done.append({'ordinal': ordinal, 'receipt_sha256': value['receipt_sha256']})
    pending = []
    state = report.seal(
      {
        'expected_frames': len(protocol['pairs']),
        'completed_frames': len(done),
        'status': completion_state(len(protocol['pairs']), len(done), failed + len(failure_records)),
        'run_sha256': run['receipt_sha256'],
        'per_frame_receipts': sorted(done, key=lambda item: item['ordinal']),
        'runtime_seconds': time.monotonic() - start,
        'failure_records': failure_records,
        'reference_promotable': False,
      }
    )
    (args.output / 'progress.json').write_text(json.dumps(state, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in state.items() if k != 'per_frame_receipts'}), flush=True)

  collect()
  with ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context('spawn')) as workers:
    try:
      resumed_ordinals = set()
      for ordinal, pair in enumerate(protocol['pairs']):
        destination = args.output / f'{ordinal:05d}.json'
        if not destination.exists():
          continue
        one_manifest = {**manifest, 'files': [identities[pair['image']], identities[pair['mask']]]}
        core = verify_resume(json.loads(destination.read_bytes()), run['receipt_sha256'], ordinal, pair, identities)
        record = core['detector_record']
        pending.append((ordinal, destination, workers.submit(metric_job, args.cache, one_manifest, pair, record), record, core))
        resumed_ordinals.add(ordinal)
        if len(pending) >= 32:
          collect()
          if failure_records:
            raise ValueError('FULL_RESUME_METRIC_FAILED')
      collect()
      if failure_records:
        raise ValueError('FULL_RESUME_METRIC_FAILED')
      inference_started = time.monotonic()
      for ordinal, pair in enumerate(protocol['pairs']):
        if ordinal in resumed_ordinals:
          continue
        if inference_budget_expired(inference_started, time.monotonic(), args.max_seconds):
          break
        destination = args.output / f'{ordinal:05d}.json'
        one_manifest = {**manifest, 'files': [identities[pair['image']], identities[pair['mask']]]}
        files = r.verify_inputs(args.cache, one_manifest)
        image = cv2.imdecode(np.frombuffer(files[pair['image']], dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
          raise ValueError('PUBLIC_FRAME_DECODE_FAILED')
        h, w = image.shape[:2]
        image = cv2.resize(image, (1640, 590), interpolation=cv2.INTER_LINEAR)
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
        with torch.no_grad():
          result = model.test_step({'inputs': [data['inputs']], 'data_samples': [data['data_samples']]})[0]
        sampling = sample_detector_lane_diagnostics(result['lanes'], width=w, height=h)
        record = {
          'image': pair['image'],
          'image_geometry': [h, w],
          'lane_count': len(result['lanes']),
          'points': sampling['points'],
          'sampling': sampling,
          'unavailable_reason': None,
          'lanes': [sample_detector_lane_diagnostics([lane], width=w, height=h)['points'] for lane in result['lanes']],
          'scores': [float(score) for score in result['scores']],
        }
        t.validate_raw_lanes(record, np.zeros((h, w), dtype=bool))
        pending.append((ordinal, destination, workers.submit(metric_job, args.cache, one_manifest, pair, record), record, None))
        if len(pending) >= 32:
          collect()
          if failure_records:
            raise ValueError('FULL_METRIC_FRAME_FAILED_NO_SILENT_SKIP')
    except Exception:
      failed += 1
      collect()
      raise
    collect()
    if failure_records:
      raise ValueError('FULL_METRIC_FRAME_FAILED_NO_SILENT_SKIP')
  if len(done) == len(protocol['pairs']) and failed == 0:

    def frames():
      for ordinal in range(len(protocol['pairs'])):
        yield verify_resume(
          json.loads((args.output / f'{ordinal:05d}.json').read_bytes()), run['receipt_sha256'], ordinal, protocol['pairs'][ordinal], identities
        )

    ledger, pool, confidence, regions = merge_frame_results(frames())
    summary = report.unseal(report.make_report(ledger, pool, confidence, regions, {'receipt_sha256': run['receipt_sha256'], 'exact_repeatability': None}))
    summary.update(
      {
        'schema': 'FULL_PUBLIC_COMMA10K_DIAGNOSTIC_V1',
        'status': 'COMPLETE_DIAGNOSTIC_NOT_QUALIFICATION',
        'evidence_tier': 'DIAGNOSTIC_PUBLIC_GT_AFTER_SUBSET_INSPECTION',
        'full_repetitions': 1,
        'repeatability_scope': run['repeatability_scope'],
        'run_sha256': run['receipt_sha256'],
        'full_producer_source_sha256': digest(Path(__file__).read_bytes()),
        'progress_receipt_sha256': json.loads((args.output / 'progress.json').read_bytes())['receipt_sha256'],
      }
    )
    (args.output / 'summary.json').write_text(json.dumps(report.seal(summary), indent=2, sort_keys=True) + '\n')
    (args.output / 'ledger.json').write_text(json.dumps(ledger, sort_keys=True) + '\n')
    (args.output / 'review.json').write_text(json.dumps(report.review_manifest(ledger), indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
  main()
