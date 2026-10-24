"""Source vectors for the frozen208-row readiness fixture, no path preload."""

import hashlib
import numpy as np
from tools.cyberpilot.canonical_readiness_fixture import models, SEED, N
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bridge as b
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bounded_inputs as q


def spec(index, role, n=N, rollout_n=1, *, periodic=False, horizon_rows=None):
  candidate, fold = b.d1.JOBS[index]
  delay, length = b.original.m.parameters(candidate)
  first = max(delay + length, length + 1) - 1
  size = first + n + 201
  pattern = np.array([0, 0, 0, 1, 2, 2, 2, 1, 0, 0, 0, -1, -2, -2, -2, -1], np.int64)
  tick = np.resize(pattern, size)
  rng = np.random.default_rng(SEED + index + (100 if role == 'DEV' else 0))
  command = np.resize(np.array([-0.75, -0.25, 0, 0.25, 0.75, 1.0], np.float64), size) if periodic else rng.normal(0, 1, size)
  segment = {'tick': tick, 'command': command, 'speed': np.full(size, 10.0), 'streak': np.arange(1, size + 1, dtype=np.int64)}
  token = hashlib.sha256(f'PUBLIC_SYNTHETIC_READINESS:{SEED}:{role}:{index}'.encode()).hexdigest()
  block = q.SourceBlock(segment, token)
  indices = q.immutable(np.arange(first, first + n, dtype=np.int64))
  parts = ((block, indices),)
  stage1, stage2 = models(length)
  x = q.assemble(parts, candidate)
  p = b.original.probability(np.ascontiguousarray(x), stage1)
  current, target, prior = q.source_vectors(parts)
  data = {
    'candidate': candidate,
    'fold': fold,
    'scope': b.SCOPE,
    'role': role,
    'source_id': token,
    'anchor': token,
    'row_ids': np.arange(n, dtype=np.int64),
    'segment_stops': (n,),
    'x': x,
    'p': p,
    'prior': prior,
    'current': current,
    'target': target,
    'y': target != current,
    'stage1': stage1 if role == 'DEV' else None,
    'stage2': stage2,
  }
  identity = b._hash(data)
  data.pop('x')
  del x
  train_meta = q.immutable({**data, 'binding': identity}) if role == 'TRAIN' else None
  return {
    'candidate': candidate,
    'fold': fold,
    'role': role,
    'source_id': token,
    'anchor': token,
    'parts': parts,
    'stage1': q.immutable(stage1) if role == 'DEV' else None,
    'stage2': q.immutable(stage2),
    'expected_binding': identity,
    'score_sha256': q.digest(p),
    'horizon_rows': {h: q.immutable(np.arange(rollout_n, dtype=np.int64) if horizon_rows is None else horizon_rows[h]) for h in b.HORIZONS}
    if role == 'DEV'
    else None,
    'train_meta': train_meta,
  }


def provider(n=N, rollout_n=1, *, horizon_rows=None):
  train = [spec(i, 'TRAIN', n, rollout_n) for i in range(32)]
  dev = [spec(i, 'DEV', n, rollout_n, horizon_rows=horizon_rows) for i in range(32)]
  return q.BoundedSyntheticProvider(train, dev)


out = q.out
CAPABILITY = q.CAPABILITY


def capability_fixture():
  """Declared public fake, never a current private grant or observed identity."""
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_execution as reference

  binding = reference.synthetic_binding('1' * 40)

  def h(c):
    return c * 64

  entries = []
  for role, member in (('TRAIN', 'stage2/model/coefficients.npy.gz'), ('DEV', 'train/MOVE_coefficients.npy.gz')):
    entries.append(
      {
        'candidate': 'HRI_D00_L01',
        'fold': 'FOLD_A',
        'role': role,
        'owner': 'V1' if role == 'TRAIN' else 'V4',
        'member': 'candidates/HRI_D00_L01/FOLD_A/' + member,
        'kind': 'array',
        'root_identity': h('a'),
        'anchor': h('b'),
        'route': h('c'),
        'segment': h('d'),
        'manifest_chain': [h('e'), h('f')],
        'model_lineage': h('1'),
        'descriptor': {'dtype': '<f8', 'shape': [5], 'order': 'C', 'content_sha256': h('2'), 'row_count': 5, 'storage': 'npy.gz'},
      }
    )
  metadata = out.sealed({'schema': 'SYNTHETIC_METADATA_ONLY', 'entries_sha256': out.sha(out.canonical(entries)), 'root_receipt': h('e')})
  return out.sealed(
    {
      'schema': CAPABILITY,
      'scope': 'PUBLIC_SYNTHETIC_CAPABILITY_ONLY',
      'grant': {
        'mission': 'SYNTHETIC_FAKE_FUTURE_GRANT',
        'head': '1' * 40,
        'protocol_raw': binding['protocol_sha256'],
        'protocol_receipt': binding['protocol_receipt'],
        'source_map_sha256': out.sha(out.canonical(binding['source_sha256'])),
        'issuer': 'SYNTHETIC_FIXTURE_NOT_TRUSTED_PRIVATE_ISSUER',
        'private_authority': False,
      },
      'root': {'identity': h('a'), 'volume': h('6'), 'device': 1, 'inode': 2, 'receipt': h('e')},
      'output': {'identity': h('7'), 'exclusive': True, 'outside_git': True, 'directory_mode': 0o700, 'file_mode': 0o600},
      'entries': entries,
      'metadata_receipt': metadata,
    }
  )


def segmented_spec(index, role):
  base = spec(index, role, n=416)
  first, ix = base['parts'][0]
  second = q.SourceBlock(first.arrays, hashlib.sha256((base['source_id'] + ':segment2').encode()).hexdigest())
  parts = ((first, ix), (second, q.immutable(ix.copy())))
  x = np.concatenate([b.original.m.features(block.arrays, positions, base['candidate']) for block, positions in parts])
  stage1, stage2 = models(b.original.m.parameters(base['candidate'])[1])
  current, target, prior = q.source_vectors(parts)
  n = len(current)
  data = {
    'candidate': base['candidate'],
    'fold': base['fold'],
    'scope': b.SCOPE,
    'role': role,
    'source_id': base['source_id'],
    'anchor': base['anchor'],
    'row_ids': np.arange(n, dtype=np.int64),
    'segment_stops': (416, 832),
    'x': x,
    'p': b.original.probability(np.ascontiguousarray(x), stage1),
    'prior': prior,
    'current': current,
    'target': target,
    'y': target != current,
    'stage1': stage1 if role == 'DEV' else None,
    'stage2': stage2,
  }
  base['expected_binding'] = b._hash(data)
  base['score_sha256'] = q.digest(data['p'])
  data.pop('x')
  del x
  base['parts'] = parts
  base['train_meta'] = q.immutable({**data, 'binding': base['expected_binding']}) if role == 'TRAIN' else None
  base['horizon_rows'] = (
    {h: q.immutable(np.concatenate((np.arange(417 - h, dtype=np.int64), 416 + np.arange(417 - h, dtype=np.int64)))) for h in b.HORIZONS}
    if role == 'DEV'
    else None
  )
  return base


def segmented_provider():
  return q.BoundedSyntheticProvider([segmented_spec(i, 'TRAIN') for i in range(32)], [segmented_spec(i, 'DEV') for i in range(32)])
