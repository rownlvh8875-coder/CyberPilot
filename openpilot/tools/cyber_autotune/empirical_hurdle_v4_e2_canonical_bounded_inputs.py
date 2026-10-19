"""Exact in-memory synthetic source leases and pure future capability schema.

No private reader or trusted issuer exists here. Names/digests authenticate
mutation consistency only; they never authorize an OS file open.
"""

from contextlib import contextmanager
import re
import weakref
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bridge as b
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_inputs as old
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_output as out
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_resources as resources

need = b.need
CAPABILITY = 'V4_E2_CANONICAL_EXACT_INPUT_CAPABILITY_PLAN_V1'
PENDING = 'INPUT_CONTRACT_UNRESOLVED_ACTUAL_BINDING_PENDING'


def execute_private(*args, **kwargs):
  raise ValueError('CANONICAL_E2_PRIVATE_EXECUTION_NOT_AUTHORIZED')


def digest(value):
  return b._hash(value)


def immutable(value):
  if type(value) is np.ndarray:
    need(value.dtype.kind in 'bifu', 'CANONICAL_BOUNDED_ARRAY_TYPE')
    return np.frombuffer(value.tobytes(order='C'), dtype=value.dtype).reshape(value.shape)
  if type(value) is dict:
    return {k: immutable(v) for k, v in value.items()}
  if type(value) is tuple:
    return tuple(immutable(v) for v in value)
  if type(value) is list:
    return [immutable(v) for v in value]
  need(type(value) in (str, int, float, bool, type(None)), 'CANONICAL_BOUNDED_VALUE_TYPE')
  return value


def hash64(value):
  return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


class SourceBlock:
  def __init__(self, arrays, identity):
    need(type(arrays) is dict and set(arrays) == {'tick', 'command', 'speed', 'streak'} and hash64(identity), 'CANONICAL_SOURCE_BLOCK_SCHEMA')
    n = len(arrays['tick'])
    need(0 < n <= resources.SOURCE_MAX, 'CANONICAL_SOURCE_BLOCK_CAP')
    for k, v in arrays.items():
      need(type(v) is np.ndarray and v.shape == (n,) and v.dtype == (np.int64 if k in ('tick', 'streak') else np.float64), 'CANONICAL_SOURCE_BLOCK_DTYPE')
      need(bool(np.all(np.isfinite(v))), 'CANONICAL_SOURCE_BLOCK_NONFINITE')
    need(np.array_equal(arrays['streak'], np.arange(1, n + 1)), 'CANONICAL_SOURCE_BLOCK_CONTINUITY')
    need(bool(np.all((arrays['tick'] >= -32768) & (arrays['tick'] <= 32767))), 'CANONICAL_SOURCE_BLOCK_TICK_RANGE')
    self.identity, self._source_hash = identity, digest(arrays)
    self._original = {k: (weakref.ref(v), digest(v)) for k, v in arrays.items()}
    self.arrays = immutable(arrays)
    self._sealed = digest(self.arrays)
    self._owners = {k: (id(a), resources.owner(a)[0], a.strides) for k, a in self.arrays.items()}

  def check(self, *, fast=False):
    need({k: (id(a), resources.owner(a)[0], a.strides) for k, a in self.arrays.items()} == self._owners, 'CANONICAL_SOURCE_OWNER_CHANGED')
    if not fast:
      need(digest(self.arrays) == self._sealed, 'CANONICAL_SOURCE_BLOCK_CHANGED')
    for ref, h in self._original.values():
      if ref() is not None:
        need(digest(ref()) == h, 'CANONICAL_SOURCE_ALIAS_CHANGED')
    need(all(not a.flags.writeable for a in self.arrays.values()), 'CANONICAL_SOURCE_WRITABLE_ALIAS')

  def verify_array(self, name, array):
    self.check()
    need(name in self.arrays and type(array) is np.ndarray and digest(array) == digest(self.arrays[name]), 'CANONICAL_SOURCE_COPY_CONFLICT')


def seal_capability(plan):
  return out.sealed({k: v for k, v in plan.items() if k != 'receipt_sha256'})


def validate_capability(plan):
  out.checked(plan)
  need(set(plan) == {'schema', 'scope', 'grant', 'root', 'output', 'entries', 'metadata_receipt', 'receipt_sha256'}, 'CANONICAL_CAPABILITY_FIELDS')
  need(plan['schema'] == CAPABILITY and plan['scope'] == 'PUBLIC_SYNTHETIC_CAPABILITY_ONLY', 'CANONICAL_CAPABILITY_SCOPE')
  grant = plan['grant']
  need(
    set(grant) == {'mission', 'head', 'protocol_raw', 'protocol_receipt', 'source_map_sha256', 'issuer', 'private_authority'},
    'CANONICAL_CAPABILITY_GRANT_FIELDS',
  )
  need(
    grant['mission'] == 'SYNTHETIC_FAKE_FUTURE_GRANT'
    and grant['issuer'] == 'SYNTHETIC_FIXTURE_NOT_TRUSTED_PRIVATE_ISSUER'
    and grant['private_authority'] is False,
    'CANONICAL_CAPABILITY_NO_ISSUER',
  )
  need(
    type(grant['head']) is str
    and re.fullmatch('[0-9a-f]{40}', grant['head'])
    and all(hash64(grant[k]) for k in ('protocol_raw', 'protocol_receipt', 'source_map_sha256')),
    'CANONICAL_CAPABILITY_SOURCE_BINDING',
  )
  root = plan['root']
  need(
    set(root) == {'identity', 'volume', 'device', 'inode', 'receipt'}
    and all(hash64(root[k]) for k in ('identity', 'volume', 'receipt'))
    and all(type(root[k]) is int and root[k] > 0 for k in ('device', 'inode')),
    'CANONICAL_CAPABILITY_ROOT',
  )
  output = plan['output']
  need(
    set(output) == {'identity', 'exclusive', 'outside_git', 'directory_mode', 'file_mode'}
    and hash64(output['identity'])
    and output['exclusive'] is output['outside_git'] is True
    and output['directory_mode'] == 0o700
    and output['file_mode'] == 0o600,
    'CANONICAL_CAPABILITY_OUTPUT',
  )
  need(type(plan['entries']) is list and 0 < len(plan['entries']) <= 3000, 'CANONICAL_CAPABILITY_MEMBER_CAP')
  seen = set()
  physical = {}
  for entry in plan['entries']:
    need(
      set(entry)
      == {
        'candidate',
        'fold',
        'role',
        'owner',
        'member',
        'kind',
        'root_identity',
        'anchor',
        'route',
        'segment',
        'manifest_chain',
        'model_lineage',
        'descriptor',
      },
      'CANONICAL_CAPABILITY_ENTRY_FIELDS',
    )
    need((entry['candidate'], entry['fold']) in b.d1.JOBS and entry['role'] in ('TRAIN', 'DEV'), 'CANONICAL_CAPABILITY_JOB_ROLE')
    old.member_allowed(entry['role'], entry['owner'], entry['member'], entry['kind'])
    if entry['owner'] in ('V1', 'V4') and entry['member'] != 'manifest.json':
      need(entry['member'].startswith('candidates/' + entry['candidate'] + '/' + entry['fold'] + '/'), 'CANONICAL_CAPABILITY_MEMBER_JOB')
    need(
      entry['root_identity'] == root['identity'] and all(hash64(entry[k]) for k in ('anchor', 'route', 'segment', 'model_lineage')),
      'CANONICAL_CAPABILITY_RECEIPT_BINDING',
    )
    chain = entry['manifest_chain']
    need(
      type(chain) is list and 2 <= len(chain) <= 16 and len(set(chain)) == len(chain) and all(hash64(v) for v in chain) and chain[0] == root['receipt'],
      'CANONICAL_CAPABILITY_RECEIPT_CHAIN',
    )
    key = (entry['root_identity'], entry['candidate'], entry['fold'], entry['role'], entry['owner'], entry['member'], entry['kind'])
    need(key not in seen, 'CANONICAL_CAPABILITY_DUPLICATE_MEMBER')
    seen.add(key)
    d = entry['descriptor']
    need(
      set(d) == {'dtype', 'shape', 'order', 'content_sha256', 'row_count', 'storage'} and hash64(d['content_sha256']) and d['order'] == 'C',
      'CANONICAL_CAPABILITY_DESCRIPTOR',
    )
    if entry['kind'] == 'array':
      if entry['owner'] in ('V1', 'V4'):
        need(type(d['row_count']) is int and 0 < d['row_count'] <= resources.N_MAX, 'CANONICAL_CAPABILITY_JOB_ROW_CAP')
      old.validate_future_plan(
        [
          {
            'role': entry['role'],
            'owner': entry['owner'],
            'member': entry['member'],
            'kind': 'array',
            'raw_sha256': d['content_sha256'],
            'anchor': entry['anchor'],
            'count': d['row_count'],
            'dtype': d['dtype'],
            'shape': d['shape'],
            'root_identity': root['identity'],
          }
        ]
      )
      need(d['storage'] == ('npy.gz' if entry['member'].endswith('.npy.gz') else 'npy'), 'CANONICAL_CAPABILITY_STORAGE')
    else:
      need(d['dtype'] is None and d['shape'] == [] and d['row_count'] == 0 and d['storage'] == 'canonical-json', 'CANONICAL_CAPABILITY_METADATA_DESCRIPTOR')
    physical_key = (entry['root_identity'], entry['owner'], entry['member'], entry['kind'])
    physical_value = out.canonical((d, entry['route'], entry['segment']))
    need(physical_key not in physical or physical[physical_key] == physical_value, 'CANONICAL_CAPABILITY_PHYSICAL_MEMBER_CONFLICT')
    physical[physical_key] = physical_value
  metadata = out.checked(plan['metadata_receipt'])
  need(
    metadata['entries_sha256'] == out.sha(out.canonical(plan['entries'])) and metadata['root_receipt'] == root['receipt'],
    'CANONICAL_CAPABILITY_METADATA_BINDING',
  )
  return 'STRUCTURE_VALIDATED_NO_PRIVATE_AUTHORITY'


def fail_terminal(method):
  def checked(self, *args, **kwargs):
    try:
      return method(self, *args, **kwargs)
    except Exception:
      self.phase = 'FAILED_TERMINAL'
      raise

  return checked


class SyntheticCapabilitySession:
  def __init__(self, plan):
    validate_capability(plan)
    self.plan, self.digest, self.phase, self.train = plan, out.sha(out.canonical(plan)), 'CREATED', None

  def _advance(self, expected, next_phase):
    need(self.phase == expected and out.sha(out.canonical(self.plan)) == self.digest, 'CANONICAL_CAPABILITY_LIFECYCLE')
    self.phase = next_phase

  @fail_terminal
  def grant(self):
    self._advance('CREATED', 'GRANT_CHECKED')

  @fail_terminal
  def root(self):
    self._advance('GRANT_CHECKED', 'ROOT_DECLARATION_CHECKED')

  @fail_terminal
  def metadata(self, receipt):
    need(receipt == self.plan['metadata_receipt'], 'CANONICAL_CAPABILITY_METADATA_CONFLICT')
    self._advance('ROOT_DECLARATION_CHECKED', 'METADATA_CHECKED')

  @fail_terminal
  def seal_plan(self, store):
    need(self.phase == 'METADATA_CHECKED', 'CANONICAL_CAPABILITY_PLAN_ORDER')
    digest = store.write('capability.json', {'scope': 'SYNTHETIC_ONLY', 'plan': self.plan})
    need(store.read('capability.json', digest)['plan'] == self.plan, 'CANONICAL_CAPABILITY_PLAN_READBACK')
    self._advance('METADATA_CHECKED', 'PLAN_DURABLE_READBACK')

  @fail_terminal
  def enable_numeric(self):
    self._advance('PLAN_DURABLE_READBACK', 'SYNTHETIC_NUMERIC_DESCRIPTORS_ENABLED')

  @fail_terminal
  def train_sealed(self, digest, record=None):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_canonical_execution import validate_train

    need(
      self.phase == 'SYNTHETIC_NUMERIC_DESCRIPTORS_ENABLED' and self.train is None and hash64(digest) and type(record) is dict,
      'CANONICAL_CAPABILITY_TRAIN_SEAL',
    )
    out.checked(record)
    need(out.sha(out.canonical(record)) == digest, 'CANONICAL_CAPABILITY_TRAIN_READBACK')
    validate_train(record, record['binding'])
    grant = self.plan['grant']
    binding = record['binding']
    need(
      binding['head'] == grant['head']
      and binding['protocol_sha256'] == grant['protocol_raw']
      and binding['protocol_receipt'] == grant['protocol_receipt']
      and out.sha(out.canonical(binding['source_sha256'])) == grant['source_map_sha256'],
      'CANONICAL_CAPABILITY_TRAIN_GRANT_BINDING',
    )
    self.train = digest

  @fail_terminal
  def permit(self, index):
    need(self.phase == 'SYNTHETIC_NUMERIC_DESCRIPTORS_ENABLED' and out.sha(out.canonical(self.plan)) == self.digest, 'CANONICAL_NUMERIC_ALLOWLIST_NOT_ENABLED')
    validate_capability(self.plan)
    need(type(index) is int and 0 <= index < len(self.plan['entries']), 'CANONICAL_CAPABILITY_MEMBER_INDEX')
    entry = self.plan['entries'][index]
    need(entry['role'] == 'TRAIN' or self.train is not None, 'CANONICAL_CAPABILITY_DEV_BEFORE_SEAL')
    return entry  # Descriptor only, no path open or real authority.


def assemble(parts, candidate):
  n = sum(len(indices) for _, indices in parts)
  dimension = 2 * b.original.m.parameters(candidate)[1] + 3
  x = np.empty((n, dimension), np.float64)
  offset = 0
  for block, indices in parts:
    block.check()
    for first in range(0, len(indices), resources.CHUNK):
      stop = min(first + resources.CHUNK, len(indices))
      x[offset + first : offset + stop] = b.original.m.features(block.arrays, indices[first:stop], candidate)
    offset += len(indices)
  return x


def source_vectors(parts):
  current = np.concatenate([block.arrays['tick'][ix] for block, ix in parts])
  target = np.concatenate([block.arrays['tick'][ix + 1] for block, ix in parts])
  prior = np.concatenate([block.arrays['tick'][ix] - block.arrays['tick'][ix - 1] for block, ix in parts])
  return current, target, prior


class BoundedSyntheticProvider:
  """Exact type, no callbacks/readers, no private capability; one feature lease."""

  def __init__(self, train_specs, dev_specs, *, byte_limit=resources.AS_CAP):
    need(type(train_specs) is list and type(dev_specs) is list and len(train_specs) == len(dev_specs) == 32, 'CANONICAL_BOUNDED_MANIFEST')
    self.lifetime = resources.Lifetime(byte_limit)
    self._specs = {'TRAIN': train_specs, 'DEV': dev_specs}
    self._spec_hashes = {}
    self._spec_stamps = {}
    self._horizon_cache = {}
    self._dev_key, self._active_dev, self.failed = None, None, False
    self._dev_score_token = None
    self._train_tokens = []
    self.counters = {}
    unique = {}
    logical_sources = {}
    for role, specs in self._specs.items():
      for index, s in enumerate(specs):
        need(
          set(s)
          == {
            'candidate',
            'fold',
            'role',
            'source_id',
            'anchor',
            'parts',
            'stage1',
            'stage2',
            'expected_binding',
            'score_sha256',
            'horizon_rows',
            'train_meta',
          },
          'CANONICAL_BOUNDED_SPEC_FIELDS',
        )
        need((s['candidate'], s['fold']) == b.d1.JOBS[index] and s['role'] == role, 'CANONICAL_BOUNDED_JOB_ORDER')
        need(all(hash64(s[k]) for k in ('source_id', 'anchor', 'expected_binding', 'score_sha256')), 'CANONICAL_BOUNDED_SPEC_HASH')
        need(type(s['parts']) is tuple and 0 < len(s['parts']) <= 154, 'CANONICAL_BOUNDED_PARTS')
        first = max(sum(b.original.m.parameters(s['candidate'])), b.original.m.parameters(s['candidate'])[1] + 1) - 1
        part_ids = set()
        for block, ix in s['parts']:
          need(type(block) is SourceBlock and type(ix) is np.ndarray and ix.dtype == np.int64 and ix.ndim == 1 and len(ix) > 0, 'CANONICAL_BOUNDED_SOURCE_PART')
          need(np.all(ix[1:] > ix[:-1]) and np.all((ix >= first) & (ix + 1 < len(block.arrays['tick']))), 'CANONICAL_BOUNDED_SOURCE_ORDER')
          need(not ix.flags.writeable, 'CANONICAL_BOUNDED_INDEX_ALIAS')
          need(block.identity not in part_ids, 'CANONICAL_BOUNDED_DUPLICATE_SOURCE')
          need(block.identity not in logical_sources or logical_sources[block.identity] is block, 'CANONICAL_BOUNDED_DUPLICATE_SOURCE_OWNER')
          logical_sources[block.identity] = block
          part_ids.add(block.identity)
          unique[id(block)] = block
        n = sum(len(ix) for _, ix in s['parts'])
        need(0 < n <= resources.N_MAX, 'CANONICAL_BOUNDED_ROW_CAP')
        if role == 'DEV':
          need(type(s['horizon_rows']) is dict and set(s['horizon_rows']) == set(b.HORIZONS), 'CANONICAL_BOUNDED_HORIZON_ROWS')
          for rows in s['horizon_rows'].values():
            need(
              type(rows) is np.ndarray
              and rows.dtype == np.int64
              and rows.ndim == 1
              and len(rows) > 0
              and not rows.flags.writeable
              and np.all((rows >= 0) & (rows < n))
              and np.all(rows[1:] > rows[:-1]),
              'CANONICAL_BOUNDED_HORIZON_ROW_ORDER',
            )
        else:
          need(s['horizon_rows'] is None, 'CANONICAL_BOUNDED_TRAIN_PATH_PAYLOAD')
        if role == 'TRAIN':
          need(s['stage1'] is None and set(s['train_meta']) == b.JOB_FIELDS - {'x'} | {'binding'}, 'CANONICAL_BOUNDED_TRAIN_META')
        else:
          need(s['train_meta'] is None, 'CANONICAL_BOUNDED_DEV_PRELOAD')
        self._spec_hashes[role, index] = self._spec_hash(s)
        self._spec_stamps[role, index] = self._spec_stamp(s)
    need(len(unique) <= 154 and sum(len(block.arrays['tick']) for block in unique.values()) <= resources.SOURCE_MAX, 'CANONICAL_BOUNDED_SOURCE_GLOBAL_CAP')
    for block in unique.values():
      self.lifetime.add('source', block.arrays)
    for role, specs in self._specs.items():
      for s in specs:
        self.lifetime.add('indices_models', ([ix for _, ix in s['parts']], s['stage1'], s['stage2'], s['horizon_rows']))
        if role == 'TRAIN':
          self._train_tokens.append(self.lifetime.add('train_vectors', s['train_meta']))

  def _spec_hash(self, s):
    plain = {k: v for k, v in s.items() if k != 'parts'}
    plain['parts'] = [(block.identity, block._sealed, ix) for block, ix in s['parts']]
    return digest(plain)

  def _spec_stamp(self, s):
    def stamp(v):
      if type(v) is np.ndarray:
        need(not v.flags.writeable, 'CANONICAL_BOUNDED_WRITABLE_SPEC')
        return (id(v), resources.owner(v)[0], v.dtype.str, v.shape, v.strides)
      if type(v) is dict:
        return tuple((str(k), stamp(item)) for k, item in v.items())
      if type(v) in (tuple, list):
        return tuple(stamp(item) for item in v)
      return v

    plain = {k: v for k, v in s.items() if k != 'parts'}
    plain['parts'] = [(block.identity, block._sealed, ix) for block, ix in s['parts']]
    return stamp(plain)

  def _check(self, index, role, *, fast=False):
    need(not self.failed and type(index) is int and 0 <= index < 32 and role in self._specs, 'CANONICAL_BOUNDED_TERMINAL_OR_JOB')
    s = self._specs[role][index]
    need(self._spec_stamp(s) == self._spec_stamps[role, index], 'CANONICAL_BOUNDED_METADATA_OWNER_CHANGED')
    if not fast:
      need(self._spec_hash(s) == self._spec_hashes[role, index], 'CANONICAL_BOUNDED_METADATA_CHANGED')
    for block, _ in s['parts']:
      block.check(fast=fast)
    return s

  def train_meta(self, index):
    need(self._dev_key is None, 'CANONICAL_BOUNDED_TRAIN_AFTER_DEV')
    return self._check(index, 'TRAIN')['train_meta']

  @contextmanager
  def features(self, index, role='TRAIN'):
    data, x, token = None, None, None
    try:
      s = self._check(index, role)
      need(not any(kind == 'feature' for kind, _ in self.lifetime.live.values()), 'CANONICAL_BOUNDED_FEATURE_OVERLAP')
      if role == 'TRAIN':
        need(self._dev_key is None, 'CANONICAL_BOUNDED_TRAIN_AFTER_DEV')
        data = s['train_meta']
      else:
        need(self._active_dev is not None and self._active_dev[0] == index, 'CANONICAL_BOUNDED_DEV_BEFORE_SEAL')
        data = self._active_dev[1]
      x = assemble(s['parts'], s['candidate'])
      token = self.lifetime.add('feature', x)
      self.counters['feature_materializations'] = self.counters.get('feature_materializations', 0) + 1
      self.counters['feature_rows'] = self.counters.get('feature_rows', 0) + len(x)
      data['x'] = x
      if role == 'TRAIN':
        b._bound(data)
      else:
        need(data['p'] is None, 'CANONICAL_BOUNDED_DEV_NO_RETRY')
        data['p'] = b.original.probability(np.ascontiguousarray(x), data['stage1'])
        self._dev_score_token = self.lifetime.add('dev_score', data['p'])
        self.counters['DEV_probability_validation_calls'] = self.counters.get('DEV_probability_validation_calls', 0) + 2
        need(digest(data['p']) == s['score_sha256'], 'CANONICAL_BOUNDED_DEV_SCORE_IDENTITY')
        need(old.validate_dev(data) == s['expected_binding'], 'CANONICAL_BOUNDED_DEV_BINDING')
      yield data
    except Exception:
      self.failed = True
      raise
    finally:
      if data is not None:
        data.pop('x', None)
      x = None
      if token is not None:
        try:
          self.lifetime.release(token)
        except Exception:
          self.failed = True
          raise

  def unlock(self, train_digest, record=None):
    from openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_canonical_execution import validate_train

    need(not self.failed and self._dev_key is None and hash64(train_digest) and type(record) is dict, 'CANONICAL_BOUNDED_DEV_BEFORE_SEAL')
    out.checked(record)
    need(out.sha(out.canonical(record)) == train_digest, 'CANONICAL_BOUNDED_TRAIN_READBACK')
    validate_train(record, record['binding'])
    need(all(row['identity'] == self._specs['TRAIN'][i]['expected_binding'] for i, row in enumerate(record['jobs'])), 'CANONICAL_BOUNDED_TRAIN_SOURCE_SEAL')
    self._dev_key = train_digest

  def retire_train(self):
    need(not self.failed and self._dev_key is not None, 'CANONICAL_BOUNDED_RETIRE_BEFORE_SEAL')
    for s in self._specs['TRAIN']:
      s['train_meta'].clear()
    for token in self._train_tokens:
      self.lifetime.release(token)
    self._train_tokens.clear()

  @contextmanager
  def dev_job(self, index, key):
    data = None
    token = None
    try:
      need(self._dev_key is not None and key == self._dev_key and self._active_dev is None, 'CANONICAL_BOUNDED_DEV_BEFORE_SEAL')
      s = self._check(index, 'DEV')
      need(digest(s['stage2']) == digest(self._specs['TRAIN'][index]['stage2']), 'CANONICAL_BOUNDED_MODEL_ROLE_CONFLICT')
      current, target, prior = source_vectors(s['parts'])
      n = len(current)
      data = {k: s[k] for k in ('candidate', 'fold', 'role', 'source_id', 'anchor', 'stage1', 'stage2')}
      data.update(
        scope=b.SCOPE,
        current=current,
        target=target,
        prior=prior,
        y=target != current,
        row_ids=np.arange(n, dtype=np.int64),
        segment_stops=tuple(np.cumsum([len(ix) for _, ix in s['parts']]).tolist()),
        p=None,
      )
      current = target = prior = None
      self._active_dev = (index, data)
      token = self.lifetime.add('dev_vectors', {k: data[k] for k in ('current', 'target', 'prior', 'y', 'row_ids')})
      yield data
    except Exception:
      self.failed = True
      raise
    finally:
      if data is not None:
        # The caller must not retain row arrays past the job. Shared model
        # owners remain admitted; feature and horizon leases enforce hard limits.
        data.clear()
      self._active_dev = None
      self._horizon_cache.clear()
      if token is not None:
        try:
          self.lifetime.release(token)
          if self._dev_score_token is not None:
            self.lifetime.release(self._dev_score_token)
        except Exception:
          self.failed = True
          raise
        finally:
          self._dev_score_token = None

  def horizon_metadata(self, index, horizon, *, fast=False):
    need(self._active_dev is not None and self._active_dev[0] == index, 'CANONICAL_BOUNDED_HORIZON_ROLE')
    s = self._check(index, 'DEV', fast=fast)
    need(horizon in b.HORIZONS, 'CANONICAL_BOUNDED_HORIZON')
    if (index, horizon) in self._horizon_cache:
      return self._horizon_cache[index, horizon]
    rows = s['horizon_rows'][horizon]
    count = len(rows)
    stops = np.cumsum([len(ix) for _, ix in s['parts']])
    segments = np.searchsorted(stops, rows, side='right').astype(np.int64)
    self._horizon_cache[index, horizon] = (count, old.output_anchor(s['anchor'], horizon, rows, segments))
    return self._horizon_cache[index, horizon]

  @contextmanager
  def horizon_chunk(self, index, horizon, first):
    values = None
    token = None
    try:
      count, _ = self.horizon_metadata(index, horizon, fast=True)
      need(type(first) is int and first >= 0 and first < count and first % resources.CHUNK == 0, 'CANONICAL_BOUNDED_CHUNK_ORDER')
      s = self._check(index, 'DEV', fast=True)
      delay, length = b.original.m.parameters(s['candidate'])
      rows = s['horizon_rows'][horizon][first : min(first + resources.CHUNK, count)]
      n = len(rows)
      stops = np.cumsum([len(ix) for _, ix in s['parts']])
      segments = np.searchsorted(stops, rows, side='right').astype(np.int64)
      values = {
        'initial': np.empty((n, length + 1), np.int64),
        'command': np.empty((n, length + horizon - 1), np.float64),
        'speed': np.empty((n, horizon), np.float64),
        'observed': np.empty((n, horizon + 1), np.int64),
        'row_ids': rows,
        'segment_ids': segments,
        'available_steps': np.minimum(200, stops[segments] - rows).astype(np.int64),
      }
      for part, (block, indices) in enumerate(s['parts']):
        take = np.flatnonzero(segments == part)
        if not len(take):
          continue
        local = rows[take] - (0 if part == 0 else stops[part - 1])
        ix = indices[local]
        need(np.all(local + horizon <= len(indices)) and np.all(ix + horizon < len(block.arrays['tick'])), 'CANONICAL_BOUNDED_SEGMENT_CROSSING')
        need(np.all(indices[local + horizon - 1] == ix + horizon - 1), 'CANONICAL_BOUNDED_SOURCE_CONTINUITY')
        values['initial'][take] = block.arrays['tick'][ix[:, None] + np.arange(-length, 1)]
        values['command'][take] = block.arrays['command'][ix[:, None] + np.arange(-delay - length + 1, horizon - delay)]
        values['speed'][take] = block.arrays['speed'][ix[:, None] + np.arange(horizon)]
        values['observed'][take] = block.arrays['tick'][ix[:, None] + np.arange(horizon + 1)]
      token = self.lifetime.add('horizon', values)
      yield values
    except Exception:
      self.failed = True
      raise
    finally:
      if values is not None:
        values.clear()
      rows = segments = None
      if token is not None:
        try:
          self.lifetime.release(token)
        except Exception:
          self.failed = True
          raise
