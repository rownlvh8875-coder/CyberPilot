"""In-memory exact synthetic adapter and future field plan; no private reader API."""

import copy
import re
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bridge as b
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_inputs as old

need = b.need
SCOPE = 'CANONICAL_E2_IMPLEMENTATION_AND_SYNTHETIC_READINESS_ONLY'
NORMALIZER = old.NORMALIZER_FIELDS


def member_allowed(role, owner, member, kind):
  need(role in ('TRAIN', 'DEV') and kind in ('metadata', 'array'), 'CANONICAL_MEMBER_ROLE_CONFLICT')
  need(type(member) is str and not member.startswith('/') and '..' not in member.split('/'), 'CANONICAL_MEMBER_SCOPE')
  old.member_allowed(owner, member, kind)
  if kind == 'metadata' and (
    (owner in ('V4', 'V1') and member == 'manifest.json') or (owner == 'V1_TOP' and member in ('authorization.json', 'input-pins.json'))
  ):
    return
  if owner in ('CAUSAL', 'DERIVED'):
    return  # Still requires exact receipt-bound member and role in future binding.
  match = re.fullmatch(r'candidates/(HRI_D[0-9]{2}_L[0-9]{2})/(FOLD_[AB])/(.+)', member)
  need(match is not None and (match[1], match[2]) in b.d1.JOBS, 'CANONICAL_MEMBER_JOB_CONFLICT')
  tail = match[3]
  train = {
    'V4': {'train/combined_probability.npy.gz', 'train/manifest.json', 'train-finalized.json'},
    'V1': {
      'train/move_label.npy.gz',
      'train/prior_delta_tick.npy.gz',
      'stage2/model/receipt.json',
      'stage2/model/coefficients.npy.gz',
      'stage2/normalizer/receipt.json',
      *('stage2/normalizer/' + f + '.npy.gz' for f in NORMALIZER),
    },
  }
  dev = {
    'V4': {
      'one-step/p_move.npy.gz',
      'one-step/receipt.json',
      'train/STATIC_coefficients.npy.gz',
      'train/MOVE_coefficients.npy.gz',
      'train/manifest.json',
      'train-finalized.json',
    },
    'V1': {
      'one-step/true_move.npy.gz',
      'one-step/prior_delta_tick.npy.gz',
      'stage1/normalizer/receipt.json',
      *('stage1/normalizer/' + f + '.npy.gz' for f in NORMALIZER),
    },
  }
  need(tail in (train if role == 'TRAIN' else dev).get(owner, set()), 'CANONICAL_MEMBER_NOT_ADMITTED')


def validate_future_plan(entries):
  need(type(entries) is list and bool(entries), 'INPUT_CONTRACT_UNRESOLVED')
  seen = set()
  for entry in entries:
    need(set(entry) == {'role', 'owner', 'member', 'kind', 'raw_sha256', 'anchor', 'count', 'dtype', 'shape', 'root_identity'}, 'INPUT_CONTRACT_UNRESOLVED')
    member_allowed(entry['role'], entry['owner'], entry['member'], entry['kind'])
    key = entry['owner'], entry['member']
    need(key not in seen and all(re.fullmatch('[0-9a-f]{64}', entry[k]) for k in ('raw_sha256', 'anchor', 'root_identity')), 'CANONICAL_EXACT_MEMBER_BINDING')
    need(type(entry['count']) is int and entry['count'] > 0 and type(entry['shape']) is list, 'CANONICAL_DESCRIPTOR_CONFLICT')
    if entry['kind'] == 'array':
      need(
        entry['dtype'] in ('<f8', '<i8', '|b1', '<i2')
        and all(type(n) is int and 0 < n <= 916535 for n in entry['shape'])
        and len(entry['shape']) == 1
        and entry['count'] == entry['shape'][0],
        'CANONICAL_DESCRIPTOR_CONFLICT',
      )
      leaf = entry['member'].split('/')[-1].split('.npy')[0]
      boolean = {'constant', 'move_label', 'true_move', 'model_eligible', 'rail'}
      integer = {'effective', 'prior_delta_tick', 'angle_tick', 'streak_all', 's2_ri_causal_run_id', 'within_s2_ri_causal_run_index'}
      expected = '|b1' if leaf in boolean else '<i8' if leaf in integer else '<f8'
      need(entry['dtype'] == expected, 'CANONICAL_FIELD_DTYPE_CONFLICT')
      if '/normalizer/' in entry['member'] or leaf.endswith('coefficients'):
        candidate = entry['member'].split('/')[1]
        dimension = 2 * b.original.m.parameters(candidate)[1] + 3
        need(entry['count'] <= dimension, 'CANONICAL_MODEL_DIMENSION_CONFLICT')
      old.caps(tuple(entry['shape']), entry['dtype'])
    seen.add(key)
  return 'FIELD_SCHEMA_VALIDATED_ACTUAL_INPUT_BINDING_UNRESOLVED'


def decode_array(raw, descriptor, *, shape, dtype, compressed):
  # Original bounded gzip/NPY parser; no path open/model loader.
  return old.decode(raw, descriptor, shape=shape, dtype=dtype, compressed=compressed)


def validate_dev(data):
  need(type(data) is dict and data.get('role') == 'DEV' and data.get('scope') == b.SCOPE, 'CANONICAL_DEV_ROLE_CONFLICT')
  need(set(data) == b.JOB_FIELDS, 'CANONICAL_DEV_FIELDS_CONFLICT')
  # Common structural checks only. Original role remains DEV in its digest;
  # this temporary validation view grants no TRAIN or DEV authority.
  b._validate_rows({**data, 'role': 'TRAIN'})
  b.require_bytes(b.original.probability(np.ascontiguousarray(data['x']), data['stage1']), data['p'], 'CANONICAL_DEV_SCORE_CONFLICT')
  b.canonical.canonical_predict_delta(data['x'][:0], data['stage2'])
  return b._hash(data)


def validate_paths(data, paths):
  need(
    set(paths) == {'binding', 'horizons'} and paths['binding'] == b._hash(data) and set(paths['horizons']) == set(b.HORIZONS), 'CANONICAL_PATH_SOURCE_BINDING'
  )
  _, length = b.original.m.parameters(data['candidate'])
  for h, values in paths['horizons'].items():
    need(set(values) == {'initial', 'command', 'speed', 'observed', 'available_steps', 'anchor', 'row_ids', 'segment_ids'}, 'CANONICAL_PATH_FIELDS')
    rows, segments = values['row_ids'], values['segment_ids']
    need(
      type(rows) is np.ndarray
      and rows.dtype == np.int64
      and rows.ndim == 1
      and len(rows) > 0
      and np.all((rows >= 0) & (rows < len(data['p'])))
      and np.all(rows[1:] > rows[:-1]),
      'CANONICAL_PATH_ORDER',
    )
    expected_segments = np.searchsorted(data['segment_stops'], rows, side='right')
    need(type(segments) is np.ndarray and segments.dtype == np.int64 and np.array_equal(segments, expected_segments), 'CANONICAL_PATH_SEGMENT')
    remaining = np.asarray(data['segment_stops'])[expected_segments] - rows
    need(
      values['available_steps'].dtype == np.int64
      and values['available_steps'].shape == rows.shape
      and np.all((values['available_steps'] >= h) & (values['available_steps'] <= remaining)),
      'CANONICAL_PATH_BOUNDARY',
    )
    need(
      values['initial'].dtype == np.int64
      and values['initial'].shape == (len(rows), length + 1)
      and np.array_equal(values['initial'][:, -1], data['current'][rows]),
      'CANONICAL_PATH_INITIAL',
    )
    need(np.array_equal(np.diff(values['initial'], axis=1), data['x'][rows, length + 1 : 2 * length + 1]), 'CANONICAL_PATH_INITIAL_HISTORY')
    need(
      values['command'].dtype == values['speed'].dtype == np.float64
      and values['command'].shape == (len(rows), length + h - 1)
      and values['speed'].shape == (len(rows), h),
      'CANONICAL_PATH_EXOGENOUS_SHAPE',
    )
    need(
      np.array_equal(values['command'][:, :length], data['x'][rows, 1 : length + 1]) and np.array_equal(values['speed'][:, 0], data['x'][rows, -1]),
      'CANONICAL_PATH_CAUSAL_FEATURE_JOIN',
    )
    observed = values['observed']
    need(type(observed) is np.ndarray and observed.dtype == np.int64 and observed.shape == (len(rows), h + 1), 'CANONICAL_PATH_REFERENCE_SHAPE')
    for step in range(h):
      source_rows = rows + step
      need(
        np.array_equal(observed[:, step], data['current'][source_rows]) and np.array_equal(observed[:, step + 1], data['target'][source_rows]),
        'CANONICAL_PATH_REFERENCE_JOIN',
      )
      need(
        np.array_equal(values['command'][:, step : step + length], data['x'][source_rows, 1 : length + 1])
        and np.array_equal(values['speed'][:, step], data['x'][source_rows, -1]),
        'CANONICAL_PATH_EXOGENOUS_JOIN',
      )
    expected = output_anchor(data['anchor'], h, rows, segments)
    need(values['anchor'] == expected, 'CANONICAL_PATH_ANCHOR')
    b.original.m.finite(values['command'], values['speed'])


def output_anchor(anchor, horizon, rows, segments):
  return b._hash((anchor, horizon, rows, segments))


class SyntheticProvider:
  """Already-in-memory mock data only. A label/digest is not private authority."""

  def __init__(self, train_jobs, dev_jobs, paths):
    need(tuple((j['candidate'], j['fold']) for j in train_jobs) == b.d1.JOBS, 'CANONICAL_EXACT32_MANIFEST_CONFLICT')
    need(len(dev_jobs) == len(paths) == 32, 'CANONICAL_DEV_MANIFEST_CONFLICT')
    self.train_jobs, self._dev_jobs, self._paths = train_jobs, dev_jobs, paths
    self._train_hashes = tuple(b._hash(j) for j in train_jobs)
    self._dev_hashes = tuple(b._hash(j) for j in dev_jobs)
    self._path_hashes = tuple(b._hash(j) for j in paths)
    self._dev_key, self.counters = None, {}

  def train(self):
    need(self._dev_key is None, 'CANONICAL_TRAIN_AFTER_DEV')
    need(tuple(b._hash(j) for j in self.train_jobs) == self._train_hashes, 'CANONICAL_TRAIN_SOURCE_CHANGED')
    return tuple(b.make_job(j) for j in self.train_jobs)

  def unlock(self, durable_train_receipt):
    need(self._dev_key is None and re.fullmatch('[0-9a-f]{64}', durable_train_receipt or ''), 'CANONICAL_DEV_BEFORE_DURABLE_SEAL')
    self._dev_key = durable_train_receipt

  def dev(self, index, key):
    need(key is not None and key == self._dev_key, 'CANONICAL_DEV_BEFORE_DURABLE_SEAL')
    need(type(index) is int and 0 <= index < 32, 'CANONICAL_DEV_JOB_CONFLICT')
    need(b._hash(self._dev_jobs[index]) == self._dev_hashes[index] and b._hash(self._paths[index]) == self._path_hashes[index], 'CANONICAL_DEV_SOURCE_CHANGED')
    need(
      b._hash(self.train_jobs[index]['stage2']) == b._hash(self._dev_jobs[index]['stage2']),
      'CANONICAL_TRAIN_DEV_MODEL_CONFLICT',
    )
    data = copy.deepcopy(self._dev_jobs[index])
    need((data['candidate'], data['fold']) == b.d1.JOBS[index], 'CANONICAL_DEV_JOB_CONFLICT')
    identity = validate_dev(data)
    paths = copy.deepcopy(self._paths[index])
    need(type(paths) is dict and paths['binding'] == identity, 'CANONICAL_DEV_PATH_BINDING_CONFLICT')
    validate_paths(data, paths)
    self.counters['DEV_reads'] = self.counters.get('DEV_reads', 0) + 1
    return data, paths, identity
