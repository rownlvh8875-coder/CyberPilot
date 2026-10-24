"""V2 qualification only: fixed512 A; original whole-job Q1/Q3; no Q2 calls.

Frozen selector/evaluator/reader are reused without modification. No I/O here.
"""
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_decision as decision
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_inputs as inputs

need = decision.need
JOBS = decision.JOBS
CONTEXTS = decision.CONTEXTS
Q1_FAILURE = 'E2_D0_TRAIN_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED'
Q3_FAILURE = 'E2_D2_TRAIN_SELECTED_PATH_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED'


class Phase(inputs.Phase):
  """Ordered global TRAIN barriers; inherited reader permissions only narrow."""
  def __init__(self):
    super().__init__()
    self.stage = 'PREFLIGHT'
    self.D0_jobs, self.potential_jobs, self.Q3_jobs = [], [], []
    self.proofs = {'Q1': [], 'Q3': []}
    self.decisions = 0
    self.aborted = False

  def require_stage(self, stage):
    need(not self.aborted and self.stage == stage, 'E2_V2_PHASE_ORDER')

  def begin(self):
    self.require_stage('PREFLIGHT')
    self.stage = 'D0'

  def complete(self, stage, job):
    self.require_stage(stage)
    values = self.D0_jobs if stage == 'D0' else self.potential_jobs if stage == 'POTENTIALS' else None
    need(values is not None and len(values) < 32 and job == JOBS[len(values)], 'E2_V2_JOB_ORDER')
    values.append(job)

  def advance(self, stage):
    if stage == 'POTENTIALS':
      self.require_stage('D0')
      need(tuple(self.D0_jobs) == JOBS, 'E2_ALL32_D0_BEFORE_POTENTIALS')
    elif stage == 'Q1':
      self.require_stage('POTENTIALS')
      need(tuple(self.potential_jobs) == JOBS, 'E2_ALL32_POTENTIALS_BEFORE_Q1')
    elif stage == 'SELECTION':
      self.require_stage('Q1')
      self.require_selection()
    else:
      raise ValueError('E2_V2_PHASE_ORDER')
    self.stage = stage

  def record_qualification(self, job, proof):
    kind = self.stage
    need(kind in ('Q1', 'Q3') and not self.aborted, 'E2_V2_QUALIFICATION_PHASE')
    values = self.qualified if kind == 'Q1' else self.Q3_jobs
    need(len(values) < 32 and job == JOBS[len(values)], 'E2_V2_JOB_ORDER')
    need(proof['kind'] == kind and tuple(proof['job']) == job, 'E2_V2_PROOF_BINDING')
    self.last_proof = proof
    if proof['status'] not in ('BYTE_EXACT_PASS', 'VERIFIED_EMPTY_GATE_ORIGINAL_INTEGRATED_NOOP'):
      self.aborted = True
      raise ValueError(Q1_FAILURE if kind == 'Q1' else Q3_FAILURE)
    values.append(job)
    self.proofs[kind].append(proof)

  def require_selection(self):
    need(not self.aborted and tuple(self.qualified) == JOBS, 'E2_ALL32_QUALIFICATION_PASS_BEFORE_SELECTION')

  def finish_selection(self, records):
    self.require_stage('SELECTION')
    # Use frozen original validation on a disposable capability with no reader.
    validation = inputs.Phase()
    validation.qualified = list(JOBS)
    validation.unlock(records, '0' * 64, '0' * 64)
    self.decisions = sum(len(row['contexts']) for row in records)
    need(self.decisions == 64, 'E2_ALL64_D2_REQUIRED')
    self.stage = 'Q3'

  def unlock(self, records, raw_digest, verified_digest):
    self.require_stage('Q3')
    need(tuple(self.Q3_jobs) == JOBS and self.decisions == 64, 'E2_ALL32_Q3_BEFORE_SEAL_DEV')
    need(type(raw_digest) is str and len(raw_digest) == 64, 'E2_DURABLE_TRAIN_READBACK_CONFLICT')
    super().unlock(records, raw_digest, verified_digest)
    self.stage = 'DEV'

  def require_dev(self):
    need(not self.aborted and self.stage == 'DEV', 'E2_V2_DEV_BARRIER')
    super().require_dev()

  def authorize(self, owner, member, kind):
    need(not self.aborted, 'E2_V2_ABORTED')
    if self.stage == 'DEV':
      self.require_dev()
      return super().authorize(owner, member, kind)
    if (owner in ('V4', 'V1') and member == 'manifest.json') or owner == 'V1_TOP':
      return super().authorize(owner, member, kind)
    if owner in ('CAUSAL', 'DERIVED'):
      self.require_stage('PREFLIGHT')
      return super().authorize(owner, member, kind)
    need(self.stage in ('D0', 'POTENTIALS'), 'E2_V2_NO_SOURCE_REREAD_DURING_QUALIFICATION_SELECTION')
    tail = '/'.join(member.split('/')[3:])
    train = tail.startswith('train/') or tail == 'train-finalized.json'
    need(train == (self.stage == 'D0'), 'E2_V2_TRAIN_MODEL_PHASE')
    return super().authorize(owner, member, kind)


def layout(blocks, candidate, n):
  need(0 < n <= decision.MAX_COUNT and 0 < len(blocks) <= 154, 'E2_TRAIN_POPULATION_CONFLICT')
  _, length = decision.frozen.m.parameters(candidate)
  need(sum(len(ix) for _, ix in blocks) == n, 'E2_TRAIN_POPULATION_CONFLICT')
  return 2 * length + 3


def potentials(blocks, candidate, stage2, p, y, prior, d0, counters):
  """A only. Segment-local features and original512 calls; no subset inference."""
  decision.validate(p, y, prior)
  layout(blocks, candidate, len(p))
  need(type(d0) is float and np.isfinite(d0) and 0 <= d0 <= 1)
  n = len(p)
  current, target, u, move = (np.empty(n, dtype) for dtype in (np.int64, np.int64, np.float64, np.int64))
  offset = 0
  for segment, ix in blocks:
    x = decision.frozen.m.features(segment, ix, candidate)
    size = len(ix)
    need(x.dtype == np.float64 and x.flags.c_contiguous and np.all(np.isfinite(x)), 'E2_TRAIN_DESIGN_CONFLICT')
    c, t = segment['tick'][ix].astype(np.int64), segment['tick'][ix + 1].astype(np.int64)
    need(np.array_equal(x[:, -3], prior[offset:offset + size]) and np.array_equal(t != c, y[offset:offset + size]),
         'E2_TRAIN_RECORDED_ORDER_CONFLICT')
    need(np.all((c >= -32768) & (c <= 32767) & (t >= -32768) & (t <= 32767)), 'E2_TRAIN_TICK_RANGE')
    current[offset:offset + size], target[offset:offset + size] = c, t
    for start in range(0, size, decision.frozen.m.CHUNK):
      stop = min(start + decision.frozen.m.CHUNK, size)
      part = np.ascontiguousarray(x[start:stop])
      decision.count(counters, 'TRAIN_counterfactual_Stage2_calls', len(part))
      delta = decision.frozen.m.predict_delta(part, stage2)
      need(delta.dtype == np.float64 and delta.shape == (len(part),) and np.all(np.isfinite(delta)), 'E2_TRAIN_POTENTIAL_CONFLICT')
      decision.count(counters, 'TRAIN_potential_projection_calls', len(part))
      projected = decision.frozen.m.project(c[start:stop].astype(np.float64) + delta)
      u[offset + start:offset + stop], move[offset + start:offset + stop] = delta, projected
    offset += size
    del x
  decision.count(counters, 'TRAIN_all_row_potential_jobs')
  return {'p': p, 'y': y, 'prior': prior, 'current': current, 'target': target, 'u': u, 'move_tick': move, 'D0_gate': p > d0}


def full_design(blocks, candidate, cache):
  """Rebuild only features from resident blocks. No source I/O or re-batching."""
  n = len(cache['p'])
  dim = layout(blocks, candidate, n)
  full = np.empty((n, dim), np.float64, order='C')
  offset = 0
  for segment, ix in blocks:
    part = decision.frozen.m.features(segment, ix, candidate)
    stop = offset + len(ix)
    need(part.dtype == np.float64 and part.shape == (len(ix), dim) and part.flags.c_contiguous)
    need(np.array_equal(part[:, -3], cache['prior'][offset:stop]), 'E2_TRAIN_RECORDED_ORDER_CONFLICT')
    need(np.array_equal(segment['tick'][ix], cache['current'][offset:stop])
         and np.array_equal(segment['tick'][ix + 1], cache['target'][offset:stop]), 'E2_TRAIN_RECORDED_ORDER_CONFLICT')
    full[offset:stop] = part
    offset = stop
    del part
  decision.frozen.m.finite(full)
  return full


def qualification(kind, blocks, candidate, stage2, cache, gate, identity, counters):
  need(kind in ('Q1', 'Q3') and gate.dtype == np.bool_ and gate.shape == cache['p'].shape, 'E2_V2_GATE_BINDING')
  model_keys = {'normalizer_receipt_sha256', 'model_receipt_sha256', 'coefficient_sha256'}
  need(tuple(identity['job']) in JOBS and identity['job'][0] == candidate
       and inputs.e1.b0._digest(identity['anchor_sha256']) and inputs.e1.b0._digest(identity['source_map_sha256'])
       and set(identity['stage2_receipts']) == model_keys
       and all(inputs.e1.b0._digest(v) for v in identity['stage2_receipts'].values()), 'E2_V2_IDENTITY_BINDING')
  expected = cache['u'][gate]
  need(expected.dtype == np.float64 and np.all(np.isfinite(expected)), 'E2_TRAIN_POTENTIAL_CONFLICT')
  proof = {'kind': kind, 'job': identity['job'], 'identity': identity, 'dtype': '<f8', 'Q2': 'NOT_EXECUTED_DIAGNOSTIC'}
  if np.any(gate):
    x = full_design(blocks, candidate, cache)
    decision.count(counters, 'D0_full_subset_qualification_calls' if kind == 'Q1' else 'D2_full_subset_qualification_calls', len(expected))
    result = decision.frozen.m.predict_delta(np.ascontiguousarray(x[gate]), stage2)
    passed = result.dtype == np.float64 and result.shape == expected.shape and np.all(np.isfinite(result)) and decision.byte_equal(result, expected)
    proof.update(status='BYTE_EXACT_PASS' if passed else 'BYTE_EXACT_MISMATCH', nonempty=True, numerical_calls=1)
    # Never expose rows, counts, differences, outputs or gate-dependent telemetry to public stdout.
  else:
    need(expected.shape == (0,) and expected.tobytes() == b'')
    delta = np.zeros(len(gate), np.float64)
    projected = cache['current'].copy()
    need(delta.tobytes() == np.zeros(len(gate), np.float64).tobytes() and np.array_equal(projected, cache['current']))
    # Original source is separately raw-hash pinned; integrated skips predict_delta for this exact empty gate.
    proof.update(status='VERIFIED_EMPTY_GATE_ORIGINAL_INTEGRATED_NOOP', nonempty=False, numerical_calls=0)
    decision.count(counters, kind + '_empty_gate_noop_jobs')
  need(len(inputs.e1.evaluation.canonical(proof)) <= 4096, 'E2_RESOURCE_PREFLIGHT_BLOCKED')
  return proof


def d2_gate(cache, record):
  need(record['count'] == len(cache['p']) and set(record['contexts']) == set(CONTEXTS), 'E2_V2_D2_BINDING')
  values = [record['contexts'][name]['decision'] for name in CONTEXTS]
  need(all(type(v) is float and np.isfinite(v) and 0 <= v <= 1 for v in values), 'E2_V2_D2_BINDING')
  return cache['p'] > np.where(cache['prior'] == 0, values[0], values[1])
