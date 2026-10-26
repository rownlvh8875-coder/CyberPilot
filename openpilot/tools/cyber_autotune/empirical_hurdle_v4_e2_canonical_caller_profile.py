"""Explicit synthetic profiling/audit contexts; no function replacement.

Profile costs include instrumentation overhead. Cumulative times overlap;
exclusive values cover only the selected nested targets, not an OS CPU bound.
ScientificAudit hashes real returned arrays immediately and stores no row data.
"""

import hashlib
import json
import sys
import time
import numpy as np

SYNTHETIC_FILES = {'empirical_hurdle_v4_e2_canonical_bridge.py', 'empirical_hurdle_v4_e2_canonical_native_bounded.py'}
SOURCE_FILE = 'empirical_hurdle_v4_e2_canonical_bounded_inputs.py'


def _arrays(value):
  if type(value) is np.ndarray:
    return (1, value.nbytes)
  if type(value) in (dict, tuple, list):
    values = value.values() if type(value) is dict else value
    count = size = 0
    for child in values:
      c, s = _arrays(child)
      count += c
      size += s
    return count, size
  return (0, 0)


def _fingerprint(value):
  if type(value) is np.ndarray:
    return {'dtype': value.dtype.str, 'shape': list(value.shape), 'raw_sha256': hashlib.sha256(value.tobytes(order='C')).hexdigest()}
  if type(value) is dict:
    return {str(key): _fingerprint(item) for key, item in value.items()}
  if type(value) in (tuple, list):
    return [_fingerprint(item) for item in value]
  if type(value) is float:
    return {'binary64': value.hex()}
  return value


class ScientificAudit:
  def __init__(self):
    self._witness = {}
    self._previous = None
    self._entered = False

  def __enter__(self):
    if self._entered or sys.getprofile() is not None:
      raise ValueError('NATIVE_BOUNDED_PROFILE_ALREADY_ACTIVE')
    self._entered = True
    self._previous = sys.getprofile()
    sys.setprofile(self._event)
    return self

  def __exit__(self, *unused):
    sys.setprofile(self._previous)
    self._entered = False

  def _event(self, frame, event, result):
    if event != 'return' or type(result) is not dict:
      return
    name = frame.f_code.co_name
    if name not in ('infer', 'recursive', 'potential_cache'):
      return
    file = frame.f_code.co_filename.rsplit('/', 1)[-1]
    if file not in SYNTHETIC_FILES:
      return
    local = frame.f_locals
    if name == 'infer':
      value = {'arm': local['arm'], 'x': local['x'], 'current': local['current'], 'output': result}
    elif name == 'recursive':
      value = {key: local[key] for key in ('initial', 'command', 'speed', 'candidate', 'decisions', 'arm', 'horizon', 'available_steps')}
      value['output'] = result
    else:
      value = result
    raw = json.dumps(_fingerprint(value), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    count, digest = self._witness.setdefault(name, [0, hashlib.sha256()])
    digest.update(len(raw).to_bytes(8, 'little'))
    digest.update(raw)
    self._witness[name][0] = count + 1

  def snapshot(self):
    return {key: {'calls': count, 'ordered_raw_array_witness_sha256': digest.hexdigest()} for key, (count, digest) in self._witness.items()}


class CallerProfile(ScientificAudit):
  def __init__(self):
    super().__init__()
    self._active, self._stack = {}, []
    self.functions = {}
    self.source_checks = {'fast': 0, 'full': 0, 'live_original_arrays_observed': 0, 'dead_original_arrays_observed': 0, 'live_original_bytes_observed': 0}
    self.hashing = {
      'array_hash_calls': 0,
      'array_count': 0,
      'array_bytes': 0,
      'source_alias_array_bytes': 0,
      'source_snapshot_array_bytes': 0,
      'source_admission_array_bytes': 0,
      'metadata_spec_array_bytes': 0,
      'metadata_JSON_bytes': 0,
      'metadata_JSON_calls': 0,
    }
    self.numpy_C_calls = {}
    self._grain_active, self._job_codes = {}, {}
    self._grain_jobs, self._grain_shared, self._grain_chunks, self._grain_horizon = {}, {}, {}, {}
    self._grain_totals = {}
    self._grain_horizon_totals = {kind: {} for kind in ('CHUNK', 'NONCHUNK')}
    self._grain_horizon_keys = {kind: set() for kind in ('CHUNK', 'NONCHUNK')}

  def _label(self, frame):
    file, name = frame.f_code.co_filename.rsplit('/', 1)[-1], frame.f_code.co_name
    qual = frame.f_code.co_qualname
    if file == SOURCE_FILE:
      if qual == 'SourceBlock.check':
        return 'SourceBlock.check'
      if qual == 'SourceBlock.__init__':
        return 'source_admission'
      if qual == 'BoundedSyntheticProvider.__init__':
        return 'provider_admission'
      if name in ('_spec_hash', '_spec_stamp', 'assemble'):
        return name
    if file in SYNTHETIC_FILES and name in ('infer', 'recursive', 'potential_cache'):
      return name
    if file == 'empirical_hurdle_v4_execution.py' and name == 'probability':
      return 'Stage1.probability'
    if file == 'empirical_s2_ri_fit_cv_math.py' and name in ('transform', 'project', 'metrics'):
      return name
    if file == 'empirical_hurdle_v4_e_evaluation.py' and name == 'drift_chunk':
      return 'drift_chunk'
    if file == 'empirical_hurdle_v4_e2_decision.py' and name == 'select_context':
      return 'D2.select_context'
    if file == 'empirical_hurdle_v4_e2_canonical_native_candidate.py' and name in ('predict', '_prepare'):
      return 'NativeWrapper.' + name
    if file == 'empirical_hurdle_v4_e2_canonical_native_bounded.py' and qual == 'VerifiedNativeBackend.predict':
      return 'NativeAdapter.predict'
    if file == 'empirical_hurdle_v4_e2_canonical_stage2.py' and name == 'canonical_predict_delta':
      return 'PythonStage2'
    if file == 'empirical_hurdle_v4_e2_canonical_output.py' and name == 'write':
      return 'durable_serialization'
    if name == 'column_stack' and file.endswith('_shape_base_impl.py'):
      return 'np.column_stack'
    if name == '_hash' and file == 'empirical_hurdle_v4_e2_canonical_bridge.py':
      return 'digest'
    return None

  def _context(self, frame):
    """Inspect metadata frames only; fast-locals snapshots can retain arrays.

    Never request f_locals from feature/selected/trace-owning scientific frames.
    Such dictionaries can retain stale fast-local array values until frame exit.
    """
    job, phase, rollout, chunk_frame = None, 'SOURCE_QUALIFICATION', None, None
    current = frame
    while current is not None:
      file = current.f_code.co_filename.rsplit('/', 1)[-1]
      name, qual = current.f_code.co_name, current.f_code.co_qualname
      if name == 'advance' and file in {'empirical_hurdle_v4_e2_canonical_bounded.py', 'empirical_hurdle_v4_e2_canonical_native_bounded.py'}:
        phase = getattr(current.f_locals.get('completed'), 'value', 'UNKNOWN_PHASE')
      if file in SYNTHETIC_FILES | {'empirical_hurdle_v4_e2_canonical_bounded.py'} and name == 'rollout':
        rollout = current.f_locals
      if file == 'canonical_bounded_fixture.py' and name in ('spec', 'segmented_spec'):
        local = current.f_locals
        index, role = local.get('index'), local.get('role')
        data = local.get('base', {})
        candidate, fold = local.get('candidate', data.get('candidate')), local.get('fold', data.get('fold'))
        if type(index) is int and role in ('TRAIN', 'DEV') and type(candidate) is str and type(fold) is str:
          self._job_codes[candidate, fold] = index
          if job is None:
            job = (role, index, candidate, fold)
      if file == SOURCE_FILE and name in ('_check', '_spec_hash', '_spec_stamp', 'horizon_chunk', '__init__'):
        # Constructor/provider/spec frames contain persistent admitted metadata;
        # horizon_chunk is inspected only during pre-yield source checks.
        local = current.f_locals
        if qual == 'BoundedSyntheticProvider.__init__' and phase == 'SOURCE_QUALIFICATION':
          phase = 'PROVIDER_ADMISSION'
        if name == 'horizon_chunk':
          chunk_frame = local
        value = local.get('s')
        if type(value) is dict and all(k in value for k in ('candidate', 'fold', 'role')) and value['role'] in ('TRAIN', 'DEV'):
          pair = value['candidate'], value['fold']
          known = self._job_codes.get(pair)
          if known is not None and job is None:
            job = (value['role'], known, *pair)
      current = current.f_back
    chunk = horizon = None
    if rollout is not None:
      index, arm, h = (rollout.get(k) for k in ('index', 'arm', 'h'))
      if type(index) is int and arm in ('D0', 'D1', 'D2') and h in (25, 50, 100, 200):
        if chunk_frame is not None:
          first = chunk_frame['first']
          count = len(rollout['provider']._specs['DEV'][index]['horizon_rows'][h])
          chunk = (index, arm, h, first, min(512, count - first))
        else:
          horizon = (index, arm, h, 'SETUP' if 'first' not in rollout else 'POST_CHUNK_NONCHUNK')
    return job, phase, chunk, horizon

  def _grain_begin(self, frame, label):
    if label not in GRANULAR_LABELS:
      return
    job, phase, chunk, horizon = self._context(frame)
    values = cost_record()
    if label == 'digest':
      count, size = _arrays(frame.f_locals['value'])
      values.update(array_hash_calls=int(count > 0), array_count=count, array_bytes=size)
    if label == 'source_admission':
      _, values['constructor_input_bytes'] = _arrays(frame.f_locals['arrays'])
    if label == 'SourceBlock.check':
      local = frame.f_locals
      values['fast_checks' if local['fast'] else 'full_checks'] = 1
      for ref, _ in local['self']._original.values():
        array = ref()
        if array is None:
          values['dead_original_arrays_observed'] += 1
        else:
          values['live_original_arrays_observed'] += 1
          values['live_original_bytes_observed'] += array.nbytes
    self._grain_active[id(frame)] = (job, phase, chunk, horizon, values, time.process_time_ns(), time.perf_counter_ns())

  def _grain_end(self, frame, label):
    item = self._grain_active.pop(id(frame), None)
    if item is None:
      return
    job, phase, chunk, horizon, values, cpu, wall = item
    values['calls'] = 1
    values['CPU_nanoseconds'] = time.process_time_ns() - cpu
    values['wall_nanoseconds'] = time.perf_counter_ns() - wall
    add_cost(self._grain_totals.setdefault(label, cost_record()), values)
    if job is None or label == 'provider_admission':
      target = self._grain_shared.setdefault((phase, label), cost_record())
    else:
      target = self._grain_jobs.setdefault((*job, phase, label), cost_record())
    add_cost(target, values)
    if chunk is not None:
      self._grain_horizon_keys['CHUNK'].add(chunk)
      add_cost(self._grain_horizon_totals['CHUNK'].setdefault(label, cost_record()), values)
      add_cost(self._grain_chunks.setdefault(chunk, {}).setdefault(label, cost_record()), values)
    elif horizon is not None:
      self._grain_horizon_keys['NONCHUNK'].add(horizon)
      add_cost(self._grain_horizon_totals['NONCHUNK'].setdefault(label, cost_record()), values)
      add_cost(self._grain_horizon.setdefault(horizon, {}).setdefault(label, cost_record()), values)

  def _granularity(self):
    jobs, metadata, other = [], [], []
    for key, value in sorted(self._grain_jobs.items()):
      role, index, candidate, fold, phase, function = key
      entry = {'role': role, 'job_index': index, 'candidate': candidate, 'fold': fold, 'phase': phase, 'function': function, 'cost': dict(value)}
      if function == 'source_admission':
        jobs.append(entry)
      elif function in ('digest', '_spec_hash', '_spec_stamp'):
        metadata.append(entry)
      else:
        other.append(entry)
    return {
      'schema': 'PUBLIC_SYNTHETIC_JOB_PHASE_CHUNK_COSTS_V1',
      'job_source_admission': jobs,
      'metadata_spec_by_job_phase': metadata,
      'other_job_phase_costs': other,
      'shared_global_costs': [{'phase': phase, 'function': label, 'cost': dict(v)} for (phase, label), v in sorted(self._grain_shared.items())],
      'horizon_chunks': [
        {'job_index': key[0], 'arm': key[1], 'horizon': key[2], 'first': key[3], 'row_count': key[4], 'costs': complete_costs(value)}
        for key, value in sorted(self._grain_chunks.items())
      ],
      'horizon_nonchunk_costs': [
        {'job_index': key[0], 'arm': key[1], 'horizon': key[2], 'position': key[3], 'costs': complete_costs(value)}
        for key, value in sorted(self._grain_horizon.items())
      ],
      'function_totals': {key: dict(v) for key, v in self._grain_totals.items()},
      'horizon_event_totals': {key: complete_costs(v) for key, v in self._grain_horizon_totals.items()},
      'horizon_event_keys': {key: [list(v) for v in sorted(keys)] for key, keys in self._grain_horizon_keys.items()},
      'metadata_spec_scope': 'NAMED_SPEC_HASH_AND_SPEC_STAMP_ARE_SPEC_COSTS;_GENERIC_DIGEST_INCLUDES_ARRAY_SOURCE_AND_SPEC_HASHES',
      'source_admission_boundary': 'ACTUAL_SOURCEBLOCK_CONSTRUCTORS_PER_JOB;_PROVIDER_JOB_LOOP_SHARED_GLOBAL_NOT_DIVIDED',
      'cost_views': 'INCLUSIVE_TIMES_OVERLAP;_JOB_AND_CHUNK_ARE_ALTERNATIVE_VIEWS_NOT_ADDITIVE',
      'clock': 'PROCESS_TIME_NS_AND_PERF_COUNTER_NS;_NOT_THE_LEGACY_FLOAT_CLOCK_BOUNDARY',
      'active_records_at_snapshot': len(self._grain_active),
    }

  def _event(self, frame, event, result):
    # Audit and profiling are a single explicit context; functions are never patched.
    super()._event(frame, event, result)
    if event == 'c_call':
      name = getattr(result, '__name__', '')
      if name in ('copy', 'ascontiguousarray', 'array', 'empty', 'column_stack', 'concatenate'):
        self.numpy_C_calls[name] = self.numpy_C_calls.get(name, 0) + 1
      return
    if event not in ('call', 'return'):
      return
    label = self._label(frame)
    if event == 'return':
      if frame.f_code.co_name == 'dumps' and type(result) is str and frame.f_back is not None:
        parent = frame.f_back
        if parent.f_code.co_name == '_hash' and parent.f_code.co_filename.rsplit('/', 1)[-1] == 'empirical_hurdle_v4_e2_canonical_bridge.py':
          self.hashing['metadata_JSON_bytes'] += len(result.encode())
          self.hashing['metadata_JSON_calls'] += 1
          grain = self._grain_active.get(id(parent))
          if grain is not None:
            grain[4]['metadata_JSON_bytes'] += len(result.encode())
            grain[4]['metadata_JSON_calls'] += 1
      entry = self._active.pop(id(frame), None)
      if entry is None:
        return
      self._grain_end(frame, entry[0])
      cpu, wall = time.process_time() - entry[1], time.perf_counter() - entry[2]
      item = self.functions.setdefault(
        entry[0],
        {'calls': 0, 'cumulative_CPU_seconds_not_additive': 0.0, 'cumulative_wall_seconds_not_additive': 0.0, 'exclusive_selected_targets_CPU_seconds': 0.0},
      )
      item['calls'] += 1
      item['cumulative_CPU_seconds_not_additive'] += cpu
      item['cumulative_wall_seconds_not_additive'] += wall
      item['exclusive_selected_targets_CPU_seconds'] += max(0.0, cpu - entry[3])
      if self._stack and self._stack[-1] == id(frame):
        self._stack.pop()
      if self._stack and self._stack[-1] in self._active:
        self._active[self._stack[-1]][3] += cpu
      return
    if label is None:
      return
    if label == 'SourceBlock.check':
      local = frame.f_locals
      self.source_checks['fast' if local['fast'] else 'full'] += 1
      for ref, _ in local['self']._original.values():
        array = ref()
        if array is None:
          self.source_checks['dead_original_arrays_observed'] += 1
        else:
          self.source_checks['live_original_arrays_observed'] += 1
          self.source_checks['live_original_bytes_observed'] += array.nbytes
    if label == 'digest':
      count, size = _arrays(frame.f_locals['value'])
      self.hashing['array_hash_calls'] += int(count > 0)
      self.hashing['array_count'] += count
      self.hashing['array_bytes'] += size
      ancestors = [self._active[token][0] for token in self._stack if token in self._active]
      if 'SourceBlock.check' in ancestors:
        key = 'source_alias_array_bytes' if type(frame.f_locals['value']) is np.ndarray else 'source_snapshot_array_bytes'
      elif 'source_admission' in ancestors:
        key = 'source_admission_array_bytes'
      elif '_spec_hash' in ancestors:
        key = 'metadata_spec_array_bytes'
      else:
        key = None
      if key:
        self.hashing[key] += size
    self._grain_begin(frame, label)
    self._active[id(frame)] = [label, time.process_time(), time.perf_counter(), 0.0]
    self._stack.append(id(frame))

  def snapshot(self):
    return {
      'functions': self.functions,
      'source_checks': self.source_checks,
      'hashing': self.hashing,
      'numpy_C_calls': self.numpy_C_calls,
      'scientific_witness': super().snapshot(),
      'instrumentation': 'EXPLICIT_SYS_PROFILE_OVERHEAD_INCLUDED_CUMULATIVE_TIMES_OVERLAP',
      'granularity': self._granularity(),
      'source_hash_checks_removed': 0,
      'source_integrity_optimization': 'SOURCE_INTEGRITY_OPTIMIZATION_UNPROVEN',
    }


def capacity_assessment(measurements):
  # Synthetic throughput cannot certify unspecified source/model/I/O lifetimes.
  return {
    'runtime': 'CANONICAL_E2_RUNTIME_BOUND_UNPROVEN',
    'memory': 'CANONICAL_E2_RESOURCE_PREFLIGHT_UNPROVEN',
    'private_execution_authorized': False,
    'production_runtime_integration_authorized': False,
    'CPU_upper_bound_seconds': None,
    'wall_upper_bound_seconds': None,
    'AS_upper_bound_bytes': None,
    'observed_measurements_supplied': bool(measurements),
    'unproven': [
      'actual input binding and I/O',
      'full source/model/alias lifetimes',
      'worst-case Stage1 and wrapper distributions',
      'D2 Nmax sweeps',
      'history/drift/P95/serialization',
      'allocator retention and host capacity',
    ],
  }


GRANULAR_LABELS = frozenset(('source_admission', 'provider_admission', 'SourceBlock.check', 'digest', '_spec_hash', '_spec_stamp'))
COST_FIELDS = (
  'calls',
  'CPU_nanoseconds',
  'wall_nanoseconds',
  'constructor_input_bytes',
  'array_hash_calls',
  'array_count',
  'array_bytes',
  'metadata_JSON_calls',
  'metadata_JSON_bytes',
  'fast_checks',
  'full_checks',
  'live_original_arrays_observed',
  'dead_original_arrays_observed',
  'live_original_bytes_observed',
)


def cost_record():
  return dict.fromkeys(COST_FIELDS, 0)


def add_cost(target, values):
  for key in COST_FIELDS:
    target[key] += values[key]


def complete_costs(values):
  return {label: dict(values.get(label, cost_record())) for label in sorted(GRANULAR_LABELS)}


def validate_granularity(snapshot, fixture):
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_bridge as bridge

  def need(ok):
    if not ok:
      raise ValueError('NATIVE_BOUNDED_GRANULAR_MEASUREMENT_INCOMPLETE')

  need(fixture in ('primary', 'segmented') and type(snapshot) is dict and type(snapshot.get('granularity')) is dict)
  g = snapshot['granularity']
  need(g['active_records_at_snapshot'] == 0)
  expected_jobs = {(role, i, *pair) for role in ('TRAIN', 'DEV') for i, pair in enumerate(bridge.d1.JOBS)}
  jobs = g['job_source_admission']
  need(len(jobs) == 64 and {(v['role'], v['job_index'], v['candidate'], v['fold']) for v in jobs} == expected_jobs)
  need(all(v['cost']['calls'] == (1 if fixture == 'primary' else 2) for v in jobs))
  need({(v['role'], v['job_index'], v['candidate'], v['fold']) for v in g['metadata_spec_by_job_phase']} == expected_jobs)
  records = jobs + g['metadata_spec_by_job_phase'] + g['other_job_phase_costs'] + g['shared_global_costs']
  total = {label: cost_record() for label in GRANULAR_LABELS}
  for record in records:
    need(record['function'] in GRANULAR_LABELS)
    value = record['cost']
    need(set(value) == set(COST_FIELDS) and all(type(v) is int and v >= 0 for v in value.values()))
    add_cost(total[record['function']], value)
  need(total == complete_costs(g['function_totals']))
  need(total['source_admission']['calls'] == (64 if fixture == 'primary' else 128))
  need(not any(v['function'] == 'source_admission' for v in g['shared_global_costs']))
  for label in GRANULAR_LABELS:
    need(total[label]['calls'] == snapshot['functions'][label]['calls'])
  digest = total['digest']
  for key in ('array_hash_calls', 'array_count', 'array_bytes', 'metadata_JSON_calls', 'metadata_JSON_bytes'):
    need(digest[key] == snapshot['hashing'][key])
  checks = total['SourceBlock.check']
  for key, legacy in (
    ('fast_checks', 'fast'),
    ('full_checks', 'full'),
    ('live_original_arrays_observed', 'live_original_arrays_observed'),
    ('dead_original_arrays_observed', 'dead_original_arrays_observed'),
    ('live_original_bytes_observed', 'live_original_bytes_observed'),
  ):
    need(checks[key] == snapshot['source_checks'][legacy])
  expected = set()
  for i in range(32):
    for arm in ('D0', 'D1', 'D2'):
      for h in (25, 50, 100, 200):
        count = 1 if fixture == 'primary' else 2 * (417 - h)
        expected.update((i, arm, h, first, min(512, count - first)) for first in range(0, count, 512))
  chunks = g['horizon_chunks']
  need(len(chunks) == len(expected) and {(v['job_index'], v['arm'], v['horizon'], v['first'], v['row_count']) for v in chunks} == expected)
  nonchunks = g['horizon_nonchunk_costs']
  nonchunk_keys = [(v['job_index'], v['arm'], v['horizon'], v['position']) for v in nonchunks]
  expected_setup = {(i, arm, h, 'SETUP') for i in range(32) for arm in ('D0', 'D1', 'D2') for h in (25, 50, 100, 200)}
  need(len(nonchunk_keys) == len(set(nonchunk_keys)) and expected_setup <= set(nonchunk_keys))
  need(all((i, arm, h, 'SETUP') in expected_setup and position in ('SETUP', 'POST_CHUNK_NONCHUNK') for i, arm, h, position in nonchunk_keys))
  # These totals and key sets are independently accumulated at observed events,
  # never computed from the serialized per-chunk records being validated.
  need(set(g['horizon_event_totals']) == {'CHUNK', 'NONCHUNK'} and set(g['horizon_event_keys']) == {'CHUNK', 'NONCHUNK'})
  for kind, records, keys in (
    ('CHUNK', chunks, expected),
    ('NONCHUNK', nonchunks, set(nonchunk_keys)),
  ):
    observed_keys = g['horizon_event_keys'][kind]
    need(len(observed_keys) == len(keys) and {tuple(v) for v in observed_keys} == keys)
    observed_totals = g['horizon_event_totals'][kind]
    need(set(observed_totals) == GRANULAR_LABELS)
    for value in observed_totals.values():
      need(set(value) == set(COST_FIELDS) and all(type(v) is int and v >= 0 for v in value.values()))
    summed = complete_costs({})
    for record in records:
      need(set(record['costs']) == GRANULAR_LABELS)
      for label, value in record['costs'].items():
        need(set(value) == set(COST_FIELDS) and all(type(v) is int and v >= 0 for v in value.values()))
        add_cost(summed[label], value)
      if kind == 'CHUNK':
        checks = record['costs']['SourceBlock.check']
        need(checks['calls'] == checks['fast_checks'] == (2 if fixture == 'primary' else 4) and checks['full_checks'] == 0)
    need(summed == observed_totals)
  return {
    'job_role_admission_records': 64,
    'source_constructor_calls': total['source_admission']['calls'],
    'horizon_chunks': len(chunks),
    'array_hash_bytes': digest['array_bytes'],
    'metadata_JSON_bytes': digest['metadata_JSON_bytes'],
    'reconciliation': 'EXACT_CALLS_BYTES_AND_SAME_GRANULAR_CLOCK_BOUNDARIES',
    'capacity_proven': False,
  }
