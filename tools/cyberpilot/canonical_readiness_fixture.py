"""Declared public synthetic provider, seed20261020; no private source analogue."""

import copy
import hashlib
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bridge as b
from openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_canonical_inputs import SyntheticProvider, output_anchor

SEED = 20261020
N = 208


def models(length):
  p = 2 * length + 3
  norm = {'mean': np.zeros(p), 'std': np.ones(p), 'constant': np.zeros(p, bool), 'effective': np.arange(p, dtype=np.int64), 'constant_reference': np.zeros(p)}
  stage1 = {'normalizer': copy.deepcopy(norm), 'heads': {}}
  for state in (0, 1):
    positions = [i for i in range(p) if state or i != p - 3]
    coeff = np.zeros(len(positions))
    coeff[0] = -0.2 if not state else 0.1
    coeff[positions.index(length)] = 0.8
    stage1['heads'][state] = {'positions': positions, 'coefficients': coeff}
  beta = np.zeros(p)
  beta[0], beta[length], beta[-3] = 0.25, 0.75, 0.25
  return stage1, {'normalizer': norm, 'coefficients': beta}


def job(index, role, n=N, rollout_n=1):
  candidate, fold = b.d1.JOBS[index]
  delay, length = b.original.m.parameters(candidate)
  first = max(delay + length, length + 1) - 1
  size = first + n + 201
  pattern = np.array([0, 0, 0, 1, 2, 2, 2, 1, 0, 0, 0, -1, -2, -2, -2, -1], np.int64)
  tick = np.resize(pattern, size)
  rng = np.random.default_rng(SEED + index + (100 if role == 'DEV' else 0))
  segment = {'tick': tick, 'command': rng.normal(0, 1, size), 'speed': np.full(size, 10.0), 'streak': np.arange(1, size + 1)}
  ix = np.arange(first, first + n, dtype=np.int64)
  x = b.original.m.features(segment, ix, candidate)
  stage1, stage2 = models(length)
  token = hashlib.sha256(f'PUBLIC_SYNTHETIC_READINESS:{SEED}:{role}:{index}'.encode()).hexdigest()
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
    'p': b.original.probability(np.ascontiguousarray(x), stage1),
    'prior': x[:, -3].astype(np.int64),
    'current': tick[ix],
    'target': tick[ix + 1],
    'y': tick[ix] != tick[ix + 1],
    'stage1': stage1 if role == 'DEV' else None,
    'stage2': stage2,
  }
  paths = {'binding': b._hash(data), 'horizons': {}}
  for h in b.HORIZONS:
    # One original eligible public synthetic anchor per horizon; support1 is
    # deliberately NOT_IDENTIFIABLE under the unchanged201 acceptance rule.
    origin = ix[:rollout_n]
    paths['horizons'][h] = {
      'initial': tick[origin[:, None] + np.arange(-length, 1)],
      'command': segment['command'][origin[:, None] + np.arange(-delay - length + 1, h - delay)],
      'speed': segment['speed'][origin[:, None] + np.arange(h)],
      'observed': tick[origin[:, None] + np.arange(h + 1)],
      'row_ids': np.arange(rollout_n, dtype=np.int64),
      'segment_ids': np.zeros(rollout_n, dtype=np.int64),
      'available_steps': np.full(rollout_n, 200, np.int64),
      'anchor': output_anchor(token, h, np.arange(rollout_n, dtype=np.int64), np.zeros(rollout_n, dtype=np.int64)),
    }
  return data, paths


def provider():
  train = [job(i, 'TRAIN')[0] for i in range(32)]
  dev = [job(i, 'DEV') for i in range(32)]
  return SyntheticProvider(train, [j[0] for j in dev], [j[1] for j in dev])
