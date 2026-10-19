"""Logical live owners, not allocator/RSS guarantees. No private resource probe."""

import math
import sys
import weakref
import numpy as np

AS_CAP = 8 * 1024**3
CPU_CAP = 21600
WALL_CAP = 43200
N_MAX = 336941
P_MAX = 93
SOURCE_MAX = 916535
CHUNK = 512
# The code uses these leases at the actual allocation/use boundaries.
LIVE_LIMITS = {'feature': 1, 'selected': 1, 'horizon': 1, 'trace': 1, 'dev_vectors': 1, 'cache': 32}


def need(v, reason='CANONICAL_BOUNDED_RESOURCE_CONFLICT'):
  if not v:
    raise ValueError(reason)


def arrays(value):
  if type(value) is np.ndarray:
    yield value
  elif type(value) is dict:
    for item in value.values():
      yield from arrays(item)
  elif type(value) in (tuple, list):
    for item in value:
      yield from arrays(item)


def owner(a):
  base = a
  while isinstance(base.base, np.ndarray):
    base = base.base
  final = base.base if isinstance(base.base, bytes) else base
  return id(final), len(final) if isinstance(final, bytes) else final.nbytes


class Lifetime:
  """Weak references make a retained alias observable; counters hold no arrays."""

  def __init__(self, byte_limit=AS_CAP):
    need(type(byte_limit) is int and 0 < byte_limit <= AS_CAP, 'CANONICAL_BOUNDED_HARD_CAP_CONFLICT')
    self.byte_limit, self.live, self.serial = byte_limit, {}, 0
    need(sys.implementation.name == "cpython", "CANONICAL_BOUNDED_OWNER_RUNTIME_UNQUALIFIED")
    self.peak_counts, self.peak_bytes, self.allocations = {}, 0, {}
    self._byte_owners = {}

  def add(self, kind, value):
    refs = []
    for a in arrays(value):
      root = a
      while isinstance(root.base, np.ndarray):
        root = root.base
      identity, size = owner(a)
      if isinstance(root.base, bytes):
        self._byte_owners.setdefault(identity, root.base)
      refs.append((weakref.ref(a), weakref.ref(root), identity, size))
    self.serial += 1
    token = self.serial
    self.live[token] = (kind, refs)
    self.allocations[kind] = self.allocations.get(kind, 0) + 1
    counts, owned = {}, {}
    for name, tracked in self.live.values():
      counts[name] = counts.get(name, 0) + 1
      for ref, root, identity, size in tracked:
        if ref() is not None or root() is not None or identity in self._byte_owners:
          owned[identity] = size
    self.peak_bytes = max(self.peak_bytes, sum(owned.values()))
    for name, count in counts.items():
      self.peak_counts[name] = max(self.peak_counts.get(name, 0), count)
      need(count <= LIVE_LIMITS.get(name, 256), 'CANONICAL_BOUNDED_LIVE_COUNT_EXCEEDED')
    need(sum(owned.values()) <= self.byte_limit, 'CANONICAL_BOUNDED_OWNER_BUDGET_EXCEEDED')
    return token

  def release(self, token):
    _, refs = self.live[token]
    need(all(ref() is None for ref, _, _, _ in refs), 'CANONICAL_BOUNDED_RETAINED_ALIAS')
    borrowed = {identity for other, (_, tracked) in self.live.items() if other != token for _, _, identity, _ in tracked}
    for _, root, identity, _ in refs:
      if identity in borrowed:
        continue
      need(root() is None, 'CANONICAL_BOUNDED_RETAINED_BASE_OWNER')
      if identity in self._byte_owners:
        # CPython only: one registry reference plus the temporary getrefcount
        # argument. No raw-byte alias may survive the final owning lease.
        need(sys.getrefcount(self._byte_owners[identity]) == 2, 'CANONICAL_BOUNDED_RETAINED_BYTES_OWNER')
    for identity in {item[2] for item in refs} - borrowed:
      self._byte_owners.pop(identity, None)
    del self.live[token]

  def snapshot(self):
    counts, owned = {}, {}
    for kind, tracked in self.live.values():
      counts[kind] = counts.get(kind, 0) + 1
      for ref, root, identity, size in tracked:
        if ref() is not None or root() is not None or identity in self._byte_owners:
          owned[identity] = size
    return {
      'live_counts': counts,
      'peak_counts': dict(self.peak_counts),
      'live_owner_bytes': sum(owned.values()),
      'peak_tracked_owner_bytes': self.peak_bytes,
      'allocations': dict(self.allocations),
      'allocator_return_claimed': False,
    }


def resource_contract(n=N_MAX, p=P_MAX, source_rows=SOURCE_MAX):
  need(type(n) is int and 0 < n <= N_MAX and p in (5, 13, 33, 93) and type(source_rows) is int and n <= source_rows <= SOURCE_MAX)
  x = n * p * 8
  # Admission may briefly own both caller source vectors and immutable snapshot.
  retained = {
    'source_snapshot_and_admission_copy': source_rows * 32 * 2,
    'TRAIN_metadata_and_indices_32': 32 * n * 49,
    'DEV_source_indices_32': 32 * n * 8,
    'DEV_horizon_anchor_indices_32': 32 * 4 * n * 8,
    'TRAIN_cache_32': 32 * n * 16,
    'models_receipts': 8 * 1024**2,
    'result_and_serialization': 384 * 1024**2,
    'Python_native_allocator_reserve_assumption': 2 * 1024**3,
  }
  phases = {
    'C_POTENTIAL': {
      'feature': x,
      'feature_chunk': CHUNK * p * 8,
      'feature_hash_copy': x,
      'history_validation_upper': n * 45 * 32,
      'finite_boolean': n * p,
      'potential_projection_vectors': n * 64,
    },
    'D_G_QUALIFICATION': {
      'feature': x,
      'selected': x,
      'feature_hash_copy': x,
      'history_validation_upper': n * 45 * 32,
      'finite_boolean': n * p,
      'reference_expected_projection_vectors': n * 80,
    },
    'F_SELECTION': {'context_copies': n * 96, 'four_channel_tree_sort_sweep': 256 * (1 << (n - 1).bit_length())},
    'J_ONE_STEP': {
      'feature': x,
      'selected': x,
      'feature_hash_copy': x,
      'history_validation_upper': n * 45 * 32,
      'normalization_and_Stage1_workspace': 4 * x,
      'DEV_vectors': n * 80,
    },
    'J_RECURSIVE': {
      'metric_vectors_and_original_P95_copies': n * 96,
      'horizon_chunk': CHUNK * (46 + 244 + 200 + 201) * 8,
      'trace': CHUNK * 200 * (45 * 8 + 8 + 2 + 16),
      'drift_and_validation': CHUNK * 200 * 128,
      'recursive_feature_workspace': CHUNK * p * 8 * 8,
      'DEV_metadata': n * 80,
    },
  }
  totals = {phase: sum(retained.values()) + sum(buffers.values()) for phase, buffers in phases.items()}
  calls = 32 * 3 * math.ceil(n / CHUNK) * 375
  row_steps = 32 * 3 * n * 375
  return {
    'status': 'CANONICAL_E2_RESOURCE_PREFLIGHT_UNPROVEN',
    'memory_status': 'CANONICAL_E2_RESOURCE_PREFLIGHT_UNPROVEN',
    'runtime_status': 'CANONICAL_E2_RUNTIME_BOUND_UNPROVEN',
    'logical_buffer_scenario_bytes': max(totals.values()),
    'retained': retained,
    'phase_buffers': phases,
    'phase_totals': totals,
    'lease_limits': LIVE_LIMITS,
    'hard_caps': {
      'AS_bytes': AS_CAP,
      'CPU_seconds': CPU_CAP,
      'wall_seconds': WALL_CAP,
      'input_opens': 3000,
      'input_bytes': 64 * 1024**3,
      'output_bytes': 384 * 1024**2,
      'disk_reserve_bytes': 2 * 1024**3,
      'workers': 1,
      'BLAS_threads': 1,
    },
    'worst_case': {
      'recursive_Stage1_calls': calls,
      'recursive_Stage2_calls_upper': calls,
      'recursive_row_steps': row_steps,
      'recursive_Stage2_terms_upper': row_steps * p,
      'D2_sorted_sweep_node_channel_work_upper': 32 * n * math.ceil(math.log2(n)) * 8,
      'all_row_calls_upper': 25984,
      'Q1_selected_calls_upper': 32,
      'Q3_selected_calls_upper': 32,
    },
    'not_proven': [
      'Native/BLAS/allocator retention is not bounded by logical lease counts.',
      'Actual private source/model/member/anchor counts and I/O chain have not been opened.',
      'Measured synthetic throughput is not a worst-case CPU/wall guarantee.',
    ],
    'private_execution_ready': False,
  }
