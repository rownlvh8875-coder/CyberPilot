"""Synthetic-only V3 reference evaluator and storage primitives.

There is deliberately no private source loader or authorized private runner.
The exhaustive evaluator is a small-fixture oracle, not the future large-data
implementation. An authorization-shaped dictionary cannot enable execution.
"""

import gzip
import io as streams
import math
from pathlib import Path

import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_threshold as old
from openpilot.tools.cyber_autotune import empirical_hurdle_attribution_io as io
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune.empirical_hurdle_fit_cv_store import array_digest

IDENTITY_FIELDS = (
  'stage1_model',
  'stage1_coefficient',
  'stage1_normalizer',
  'stage2_model',
  'stage2_coefficient',
  'stage2_normalizer',
  'train_anchors',
  'development_anchors',
  'rollout_25_anchors',
  'rollout_50_anchors',
  'rollout_100_anchors',
  'rollout_200_anchors',
  'v1_confusion_receipt',
)
DURABLE_FIELDS = ('run2_manifest', 'run2_receipt', 'comparison_manifest', 'file_equality_summary', 'threshold_identity', 'result_identity')
objective_key = old.key


def execute_private(*, authorization):
  del authorization
  raise ValueError('V3_PRIVATE_EXECUTION_NOT_IMPLEMENTED_REQUIRES_SEPARATE_AUTHORIZATION')


def validate_reference(reference_tp, positives):
  if type(reference_tp) is not int or type(positives) is not int or not 0 < reference_tp <= positives or 20 * reference_tp <= positives:
    raise ValueError('V3_REFERENCE_CONFLICT')


def gate(probability, threshold):
  old.candidates(probability)
  if type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
    raise ValueError('V3_INVALID_FROZEN_THRESHOLD')
  return probability > threshold


def evaluate(*, probability, branch_delta, current, target, reference_tp, role):
  if role != 'SYNTHETIC_TRAIN':
    raise ValueError('V3_SYNTHETIC_TRAIN_ONLY')
  for ticks in (current, target):
    if ticks.dtype != np.int64 or ticks.ndim != 1 or not np.all((ticks >= -32768) & (ticks <= 32767)):
      raise ValueError('V3_TICK_RANGE_CONFLICT')
  move, _, _, _ = old.prepare(probability, branch_delta, current, target)
  validate_reference(reference_tp, int(np.count_nonzero(move)))
  rows, best, selected = [], None, None
  for threshold in old.candidates(probability):
    value = float(threshold)
    row = old.canonical(probability, branch_delta, current, target, value)
    row['tp'] = int(np.count_nonzero(move & gate(probability, value)))
    row['feasible'] = bool(row['feasible'] and row['tp'] >= reference_tp)
    rows.append((value, row))
    if row['feasible'] and (best is None or objective_key(value, row) > best):
      best, selected = objective_key(value, row), row
  return {
    'status': 'V3_SYNTHETIC_THRESHOLD_FINALIZED' if best is not None else 'V3_NO_FEASIBLE_THRESHOLD',
    'threshold': best[-1] if best is not None else None,
    'selected': selected,
    'rows': rows,
    'candidate_count': len(rows),
    'feasible_count': sum(row['feasible'] for _, row in rows),
  }


def check_identity(expected, actual):
  if set(expected) != set(IDENTITY_FIELDS) or expected != actual:
    raise ValueError('V3_MODEL_OR_ANCHOR_IDENTITY_CONFLICT')
  if any(type(x) is not str or len(x) != 64 or any(c not in '0123456789abcdef' for c in x) for x in actual.values()):
    raise ValueError('V3_MODEL_OR_ANCHOR_IDENTITY_CONFLICT')


def synthetic_gate(job, *, role):
  if role != 'SYNTHETIC':
    raise ValueError('V3_SYNTHETIC_ONLY')
  from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_gates as gates

  frozen = io.read_json(p.PUBLIC / 'empirical-hurdle-acceptance-gate-v1.json', '1a5198475b7a3843381762078475915a389b2898e950effc171a3df58219ca60')
  return gates.fold_gate(job, frozen['clauses'])


def compress(array):
  if array.dtype.hasobject or array.dtype.kind not in 'bifu' or not np.isfinite(array).all():
    raise ValueError('V3_ARRAY_SCHEMA_CONFLICT')
  array = np.ascontiguousarray(array)
  buffer = streams.BytesIO()
  np.save(buffer, array, allow_pickle=False)
  decoded = buffer.getvalue()
  compressed = streams.BytesIO()
  with gzip.GzipFile(fileobj=compressed, mode='wb', filename='', mtime=0, compresslevel=1) as stream:
    stream.write(decoded)
  payload = compressed.getvalue()
  receipt = p.seal(
    {
      'schema': 'V3_COMPRESSED_ARRAY',
      'compressed_file_sha256': p.sha(payload),
      'decoded_npy_sha256': p.sha(decoded),
      'array_content_sha256': array_digest(array),
      'dtype': array.dtype.str,
      'shape': list(array.shape),
      'order': 'C',
    }
  )
  return payload, receipt


def decode(payload, receipt):
  p.verify(receipt)
  io.require(receipt['schema'] == 'V3_COMPRESSED_ARRAY' and p.sha(payload) == receipt['compressed_file_sha256'], 'V3_CONTENT_CONFLICT')
  decoded = gzip.decompress(payload)
  io.require(p.sha(decoded) == receipt['decoded_npy_sha256'], 'V3_CONTENT_CONFLICT')
  array = np.load(streams.BytesIO(decoded), allow_pickle=False)
  io.require(
    array_digest(array) == receipt['array_content_sha256']
    and array.dtype.str == receipt['dtype']
    and list(array.shape) == receipt['shape']
    and receipt['order'] == 'C'
    and array.flags.c_contiguous,
    'V3_CONTENT_CONFLICT',
  )
  return array


def check_output(root, source):
  return io.output_root(root, source)


def validate_aggregate(value):
  if type(value) is not dict or set(value) != {'readiness', 'gate_count'} or value['readiness'] != 'SYNTHETIC_ONLY' or value['gate_count'] != 32:
    raise ValueError('V3_SYNTHETIC_AGGREGATE_ALLOWLIST')
  return value


def write_store(root, source, aggregate):
  check_output(root, source)
  validate_aggregate(aggregate)
  root = io.safe(root)
  io.require(not root.exists(), 'V3_NO_OVERWRITE')
  row = p.seal({'schema': 'V3_SYNTHETIC_AGGREGATE', 'aggregate': aggregate})
  io.write_json(root / 'aggregate.json', row)
  return io.finish(
    root, ['aggregate.json'], {'schema': 'V3_SYNTHETIC_MANIFEST', 'aggregate_sha256': row['receipt_sha256'], 'actual_private_execution': 'NOT_RUN'}
  )


def resume(root):
  root = io.safe(Path(root))
  manifest = io.read_json(root / 'manifest.json')
  io.require(manifest['schema'] == 'V3_SYNTHETIC_MANIFEST' and manifest['actual_private_execution'] == 'NOT_RUN')
  io.require(set(manifest['files']) == {'aggregate.json'})
  io.verify_files(root, manifest['files'])
  row = io.read_json(root / 'aggregate.json', manifest['aggregate_sha256'])
  io.require(row['schema'] == 'V3_SYNTHETIC_AGGREGATE')
  validate_aggregate(row['aggregate'])
  return manifest


def cleanup_eligible(first, second, durable):
  # Predicate only: this scaffold never deletes source, result, or scratch files.
  io.require(first == second and set(durable) == set(DURABLE_FIELDS), 'V3_REPEATABILITY_OR_DURABILITY_CONFLICT')
  io.require(
    all(type(v) is str and len(v) == 64 and all(c in '0123456789abcdef' for c in v) for v in durable.values()), 'V3_REPEATABILITY_OR_DURABILITY_CONFLICT'
  )
  io.require(durable['run2_manifest'] == first['manifest_sha256'], 'V3_REPEATABILITY_OR_DURABILITY_CONFLICT')
  return True
