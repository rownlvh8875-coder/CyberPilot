"""Fresh one-job TRAIN capability; exact identity comes from a sealed abort.

Metadata planning precedes a durable exact array allowlist. No original V2
run/preflight is called. Current grant/reviews/CI are checked before root reads.
"""

import argparse
from contextlib import ExitStack
import ctypes
import json
import os
from pathlib import Path, PurePosixPath
import re
import resource
import signal
import sys
import time
import types
from unittest.mock import patch
import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_execution as control
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_v2_execution as v2
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_v2_q1_diagnostic as diagnostic

need = control.need
BASELINE = '45d1425047c725aab27f3075964f881190929f1a'
MISSION = 'STAGE1_V4_E2_V2_Q1_REFERENCE_PATH_DIAGNOSTIC'
PROTOCOL = 'empirical-hurdle-stage1-v4-e2-v2-q1-diagnostic-protocol.json'
FAILED_HEAD = '2335a8d618530185f09781ea6cb44bceb921516c'
FORBIDDEN = (
  'D2_TRAIN_DECISION_SELECTION',
  'D2_NEW_GATES',
  'D2_DEV_ONE_STEP',
  'D2_RECURSIVE_ROLLOUT',
  'E2_FULL_REEXECUTION',
  'E2_V2_RESUME',
  'STAGE1_REFIT',
  'STAGE2_REFIT',
  'NORMALIZER_REFIT',
  'CALIBRATION_FIT',
  'NEW_POLICY_SEARCH',
  'POSTHOC_TUNING',
  'NUMERICAL_TOLERANCE_RELAXATION',
  'REBATCHING_TO_FORCE_PASS',
  'RAW_LOG_QLOG_OPENINGS',
  'HOLDOUT_OPENINGS',
  'HOLDOUT_DISCOVERY',
  'VEHICLE_ACTIVATION',
  'ORIGINAL_SOURCE_WRITES',
)
BOOTSTRAP = {
  'V4': {'manifest.json'},
  'V1': {'manifest.json'},
  'V1_TOP': {'authorization.json', 'input-pins.json'},
  'CAUSAL': {'authorization.json', 'repeat-1/manifest.json'},
  'DERIVED': {'repeat-1/derived-index.json', 'repeat-1/results.json', 'repeat-1/admission.json'},
}
NORMALIZER = ('mean', 'std', 'constant', 'effective', 'constant_reference')
CAUSAL = ('command.normalized', 'state.speed_mps')
DERIVED = ('angle_tick', 'streak_all', 'model_eligible', 'rail', 's2_ri_causal_run_id', 'within_s2_ri_causal_run_index')


class Phase:
  def __init__(self, job, route):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_decision as decision

    need(tuple(job) in decision.JOBS and re.fullmatch('[0-9a-f]{64}', route), 'Q1_DIAGNOSTIC_JOB_ROUTE')
    self.job, self.route = tuple(job), route
    self.train_sha256 = None
    self.source_members, self.plan = set(), {}
    self.enabled = False
    self.segment_ids = None

  def bind_segments(self, identities):
    need(self.segment_ids is None and not self.enabled)
    need(type(identities) is list and 0 < len(identities) <= 154 and len(set(identities)) == len(identities))
    need(all(type(i) is str and re.fullmatch('[0-9a-f]{64}', i) for i in identities))
    self.segment_ids = frozenset(identities)

  def register(self, owner, member, kind):
    # A receipt-bound source identity is accepted only under this exact route.
    need(not self.enabled and owner in ('CAUSAL', 'DERIVED') and kind in ('array', 'metadata'))
    prefix = 'repeat-1/routes/' + self.route + '/segments/' if owner == 'CAUSAL' else 'repeat-1/segments/'
    need(member.startswith(prefix), 'Q1_DIAGNOSTIC_EXACT_TRAIN_ROUTE')
    tail = member[len(prefix) :].split('/')
    need(self.segment_ids is not None and tail[0] in self.segment_ids, 'Q1_DIAGNOSTIC_EXACT_TRAIN_SEGMENT')
    allowed = len(tail) == 2 and tail[1] == 'receipt.json' and kind == 'metadata'
    allowed |= owner == 'CAUSAL' and len(tail) == 3 and tail[1] == 'arrays' and tail[2] in {f + '.npy' for f in CAUSAL} and kind == 'array'
    allowed |= owner == 'DERIVED' and len(tail) == 2 and tail[1] in {f + '.npy' for f in DERIVED} and kind == 'array'
    need(allowed, 'Q1_DIAGNOSTIC_SOURCE_FIELD')
    self.source_members.add((owner, member, kind))

  def authorize(self, owner, member, kind):
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_inputs as inp

    inp.member_allowed(owner, member, kind)
    if kind == 'array':
      need(self.enabled and (owner, member) in self.plan, 'Q1_DIAGNOSTIC_DURABLE_ALLOWLIST_REQUIRED')
    if kind == 'metadata' and member in BOOTSTRAP.get(owner, ()):
      return
    if (owner, member, kind) in self.source_members:
      return
    prefix = 'candidates/' + '/'.join(self.job) + '/'
    need(member.startswith(prefix), 'Q1_DIAGNOSTIC_EXACT_FAILED_JOB_ONLY')
    tail = member[len(prefix) :]
    meta = {'V4': {'train/manifest.json', 'train-finalized.json'}, 'V1': {'stage2/model/receipt.json', 'stage2/normalizer/receipt.json'}}
    arrays = {
      'V4': {'train/combined_probability.npy.gz'},
      'V1': {
        'train/move_label.npy.gz',
        'train/prior_delta_tick.npy.gz',
        'stage2/model/coefficients.npy.gz',
        *(f'stage2/normalizer/{f}.npy.gz' for f in NORMALIZER),
      },
    }
    need(tail in (meta if kind == 'metadata' else arrays).get(owner, ()), 'Q1_DIAGNOSTIC_UNAPPROVED_FIELD')

  def enable(self, plan, expected, observed):
    need(not self.enabled and type(expected) is str and expected == observed and re.fullmatch('[0-9a-f]{64}', expected))
    need(plan and all(type(k) is tuple and len(k) == 2 for k in plan))
    self.enabled = True
    self.plan = plan
    try:
      from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e_inputs as e1

      for key, row in plan.items():
        self.authorize(*key, 'array')
        need((row['owner'], row['member']) == key and re.fullmatch('[0-9a-f]{64}', row['raw_sha256']))
        need(type(row['compressed']) is bool and type(row['shape']) is list and len(row['shape']) == 1)
        cap = e1.caps(tuple(row['shape']), row['dtype'])[0 if row['compressed'] else 1]
        need(type(row['cap']) is int and row['cap'] == cap)
    except Exception:
      self.enabled, self.plan = False, {}
      raise

  def require_dev(self):
    raise ValueError('Q1_DIAGNOSTIC_DEV_FORBIDDEN')


def provider_type(modules):
  inp = modules['empirical_hurdle_v4_e2_inputs']
  e1 = modules['empirical_hurdle_v4_e_inputs']

  class Provider(inp.Provider):
    def exact_index(self, index):
      need((self.bound_jobs[index]['candidate_id'], self.bound_jobs[index]['fold']) == self.reader.phase.job, 'Q1_DIAGNOSTIC_EXACT_INDEX')

    def prepare(self, index):
      self.exact_index(index)
      r, expected = self.reader, self.v4_auth['source_manifests']
      manifest = r.metadata('CAUSAL', 'repeat-1/manifest.json', receipt_sha=expected['causal'])
      auth = r.metadata('CAUSAL', 'authorization.json')
      derived_index = r.metadata('DERIVED', 'repeat-1/derived-index.json', receipt_sha=expected['derived_index'])
      result = r.metadata('DERIVED', 'repeat-1/results.json', receipt_sha=expected['derived_result'])
      admission = r.metadata('DERIVED', 'repeat-1/admission.json', receipt_sha=result['admission_sha256'])
      need(admission['manifest_sha256'] == manifest['receipt_sha256'])
      indexed = {s['content_sha256']: s['receipt_sha256'] for s in derived_index['segments']}
      identities = [s for values in auth['segments'].values() for s in values]
      need(len(derived_index['segments']) == len(indexed) == len(identities) == len(set(identities)) == 154 and set(identities) == set(indexed))
      need(
        set(auth['segments']) == set(self.source_policy['route_ids']) and not set(identities).intersection(self.source_policy['excluded_qlog_content_sha256'])
      )
      route = self.references[index]['train_route']
      need(route == r.phase.route)
      r.phase.bind_segments(auth['segments'][route])
      self.source_plan, plan, total = [], {}, 0

      def add(owner, member, desc, n, dtype, compressed):
        need(type(n) is int and 0 < n <= e1.MAX_SOURCE_ROWS)
        need(desc['dtype'] == dtype and desc['shape'] == [n] and desc['order'] == 'C', 'Q1_DIAGNOSTIC_DESCRIPTOR_SCHEMA')
        need(e1.b0._digest(desc['file_sha256']) and e1.b0._digest(desc['array_sha256']))
        need(r.maps[owner].get(member) == desc['file_sha256'], 'Q1_DIAGNOSTIC_MEMBER_HASH')
        cap = e1.caps((n,), dtype)[0 if compressed else 1]
        key = owner, member
        need(key not in plan, 'Q1_DIAGNOSTIC_DUPLICATE_MEMBER')
        plan[key] = {'owner': owner, 'member': member, 'raw_sha256': desc['file_sha256'], 'cap': cap, 'dtype': dtype, 'shape': [n], 'compressed': compressed}

      for identity in sorted(auth['segments'][route]):
        need(e1.b0._digest(identity))
        source_prefix = f'repeat-1/routes/{route}/segments/{identity}'
        derived_prefix = f'repeat-1/segments/{identity}'
        for owner, member in (('CAUSAL', source_prefix + '/receipt.json'), ('DERIVED', derived_prefix + '/receipt.json')):
          r.phase.register(owner, member, 'metadata')
        source = r.metadata('CAUSAL', source_prefix + '/receipt.json')
        derived = r.metadata('DERIVED', derived_prefix + '/receipt.json', receipt_sha=indexed[identity])
        need(
          source['route_id'] == route
          and source['segment_sha256'] == identity
          and derived['source_receipt_sha256'] == source['receipt_sha256']
          and derived['policy_sha256'] == self.source_policy['receipt_sha256']
        )
        n = source['arrays']['state.speed_mps']['shape'][0]
        need(type(n) is int and 0 < n <= e1.MAX_SOURCE_ROWS)
        total += n
        need(total <= e1.MAX_SOURCE_ROWS)
        fields = []
        for owner, prefix, row, names in (('CAUSAL', source_prefix + '/arrays', source, CAUSAL), ('DERIVED', derived_prefix, derived, DERIVED)):
          for name in names:
            member = prefix + '/' + name + '.npy'
            r.phase.register(owner, member, 'array')
            dtype = '<f8' if owner == 'CAUSAL' else '|b1' if name in ('model_eligible', 'rail') else '<i8'
            add(owner, member, row['arrays'][name], n, dtype, False)
            fields.append((owner, member, row['arrays'][name], n, dtype, name))
        self.source_plan.append((route, identity, fields))
      candidate, fold = r.phase.job
      prefix = 'candidates/' + candidate + '/' + fold
      fields = self.bound_jobs[index]['fields'][:3]
      need([f['role'] for f in fields] == ['TRAIN'] * 3)
      expected_n = self.references[index]['train_count']
      need(type(expected_n) is int and 0 < expected_n <= diagnostic.MAX_ROWS)
      need([f['dtype'] for f in fields] == ['<f8', '|b1', '<i8'] and all(f['n'] == expected_n for f in fields))
      for record, tail in zip(fields, ('train/combined_probability.npy.gz', 'train/move_label.npy.gz', 'train/prior_delta_tick.npy.gz'), strict=True):
        owner = 'V4' if record['owner'] == 'V4' else 'V1'
        member = str(PurePosixPath(record['path']).relative_to(r.roots[owner]))
        need(member == prefix + '/' + tail and record['anchor_sha256'] == self.references[index]['train_anchor_sha256'])
        add(owner, member, record['descriptor'], record['n'], record['dtype'], True)
      norm = r.metadata('V1', prefix + '/stage2/normalizer/receipt.json', receipt_sha=self.references[index]['stage2']['normalizer_receipt_sha256'])
      model = r.metadata('V1', prefix + '/stage2/model/receipt.json', receipt_sha=self.references[index]['stage2']['model_receipt_sha256'])
      need(set(norm['arrays']) == set(NORMALIZER) and set(model['arrays']) == {'coefficients'})
      _, length = e1.evaluation.frozen.m.parameters(candidate)
      dimension = 2 * length + 3
      need(norm['candidate_id'] == model['candidate_id'] == candidate and norm['fold'] == model['fold'] == fold)
      need(norm['stage'] == 'STAGE2' and model['normalizer_sha256'] == norm['receipt_sha256'])
      effective_n = norm['arrays']['effective']['shape'][0]
      need(type(effective_n) is int and 0 < effective_n <= dimension)
      need(model['arrays']['coefficients']['array_sha256'] == self.references[index]['stage2']['coefficient_sha256'])
      for name in NORMALIZER:
        desc = norm['arrays'][name]
        need(desc['shape'] == [effective_n if name == 'effective' else dimension])
        dtype = '|b1' if name == 'constant' else '<i8' if name == 'effective' else '<f8'
        add('V1', prefix + '/stage2/normalizer/' + name + '.npy.gz', desc, desc['shape'][0], dtype, True)
      desc = model['arrays']['coefficients']
      need(desc['shape'] == [effective_n])
      add('V1', prefix + '/stage2/model/coefficients.npy.gz', desc, desc['shape'][0], '<f8', True)
      return plan

    def admit_train_sources(self):
      need(self.segments is None and self.reader.phase.enabled)
      segments = []
      for route, identity, fields in self.source_plan:
        arrays = {name: self.reader.array(owner, member, desc, shape=(n,), dtype=dtype, compressed=False) for owner, member, desc, n, dtype, name in fields}
        need(np.all((arrays['angle_tick'] >= -32768) & (arrays['angle_tick'] <= 32767)))
        need(np.all((arrays['streak_all'] > 0) == arrays['model_eligible']))
        segments.append(
          {
            'route_id': route,
            'segment_sha256': identity,
            'tick': arrays['angle_tick'],
            'streak': arrays['streak_all'],
            'command': arrays['command.normalized'],
            'speed': arrays['state.speed_mps'],
            'rail': arrays['rail'],
            'eligible': arrays['model_eligible'],
            'run': arrays['s2_ri_causal_run_id'],
            'within': arrays['within_s2_ri_causal_run_index'],
          }
        )
      self.segments = tuple(segments)

    def train(self, index):
      self.exact_index(index)
      return super().train(index)

    def train_blocks(self, index):
      self.exact_index(index)
      return super().train_blocks(index)

    def stage2(self, index):
      self.exact_index(index)
      return super().stage2(index)

  return Provider


def authenticate_reference(ref, binding, abort, verified, gate, p, lock, lock_raw):
  v2.validate_binding(binding, p, lock, lock_raw)
  need(ref['schema'] == 'V4_E2_V2_Q1_EXACT_FAILED_REFERENCE_V1' and ref['role'] == 'TRAIN')
  need(binding['head'] == FAILED_HEAD and binding['gate_receipt_sha256'] == gate['receipt_sha256'])
  need(abort['binding_receipt_sha256'] == binding['receipt_sha256'] and abort['protocol_raw_sha256'] == v2.PROTOCOL_SHA)
  need(abort['status'] == 'E2_D0_TRAIN_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED' and abort['stage'] == 'Q1' and abort['qualified_TRAIN_jobs'] == 2)
  need(verified['abort_receipt_sha256'] == abort['receipt_sha256'] and verified['binding_receipt_sha256'] == binding['receipt_sha256'])
  need(ref['failed_binding_receipt_sha256'] == binding['receipt_sha256'] and ref['failed_abort_receipt_sha256'] == abort['receipt_sha256'])
  need(ref['job'] == abort['failed_job'] == abort['last_qualification_attempt']['job'] == abort['last_qualification_attempt']['identity']['job'])
  need(
    ref['identity'] == abort['last_qualification_attempt']['identity']
    and abort['last_qualification_attempt']['kind'] == 'Q1'
    and abort['last_qualification_attempt']['status'] == 'BYTE_EXACT_MISMATCH'
  )
  pairs = [(j['candidate_id'], j['fold']) for j in p['jobs']]
  need(tuple(ref['job']) in pairs and pairs.index(tuple(ref['job'])) == ref['job_index_zero_based'] == abort['qualified_TRAIN_jobs'])
  need(ref['protocol_raw_sha256'] == v2.PROTOCOL_SHA and ref['protocol_receipt_sha256'] == p['receipt_sha256'])
  need(abort['schema'] == 'V4_E2_V2_ABORT_ENVELOPE_V1' and abort['source_writes'] == abort['forbidden_attempts'] == 0)
  proof = abort['last_qualification_attempt']
  need(proof['dtype'] == '<f8' and proof['nonempty'] is True and type(proof['numerical_calls']) is int and proof['numerical_calls'] == 1)
  need(proof['Q2'] == 'NOT_EXECUTED_DIAGNOSTIC')
  reference = control.public('empirical-hurdle-fit-cv-results-v1.json')['jobs'][ref['job_index_zero_based']]
  expected = {
    'job': ref['job'],
    'anchor_sha256': reference['train_anchor_sha256'],
    'stage2_receipts': {k: reference['stage2'][k] for k in ('normalizer_receipt_sha256', 'model_receipt_sha256', 'coefficient_sha256')},
    'source_map_sha256': control.sha(control.canonical(p['source_sha256'])),
  }
  need(ref['identity'] == expected and ref['expected_train_count'] == reference['train_count'], 'Q1_DIAGNOSTIC_PUBLIC_REFERENCE_CONFLICT')


def load_sources():
  p_raw = (control.PUBLIC / PROTOCOL).read_bytes()
  p = control.checked(p_raw)
  need(p['version'] == 'V4_E2_V2_Q1_DIAGNOSTIC_PROTOCOL_V1' and p['baseline_head'] == BASELINE)
  need(p['failed_execution_head'] == FAILED_HEAD and p['V2_protocol_raw_sha256'] == v2.PROTOCOL_SHA and p['V2_qualification_raw_sha256'] == v2.AMENDMENT_SHA)
  buffers = {}
  for name, digest in {**p['source_sha256'], **p['diagnostic_source_sha256']}.items():
    buffers[name] = (control.SOURCE / name).read_bytes()
    need(control.sha(buffers[name]) == digest, 'Q1_DIAGNOSTIC_SOURCE_DRIFT')
  old, _, lock, lock_raw, modules = v2.frozen_sources()
  import openpilot.tools.cyber_autotune as package

  for name in ('empirical_hurdle_v4_e2_numerical_diagnostic', 'empirical_hurdle_v4_e2_v2_q1_diagnostic'):
    module = types.ModuleType(package.__name__ + '.' + name)
    module.__file__, module.__package__ = str(control.SOURCE / (name + '.py')), package.__name__
    sys.modules[module.__name__] = module
    setattr(package, name, module)
    exec(compile(buffers[name + '.py'], module.__file__, 'exec'), module.__dict__)
    modules[name] = module
  return p, p_raw, old, lock, lock_raw, modules


def resource_plan(resources):
  n, dimension = 336941, 93
  matrix_workspace = 10 * n * dimension * 8
  vector_workspace = 64 * n
  # Old V2 source/cache base overbounds this one-job adapter. Ten matrices
  # include feature temporaries, xa/za/xc/zc, byte comparisons and BLAS workspace.
  total = 1410679894 + matrix_workspace + vector_workspace + 2 * 1024**3
  need(resources['analytical_live_bound_bytes'] == total < resources['address_space_bytes'])
  need(resources['address_space_bytes'] == 8 * 1024**3 and resources['runtime_reserve_bytes'] == 2 * 1024**3)
  need(resources['input_open_limit'] == 1600 and resources['input_bytes_limit'] == 8 * 1024**3)
  need(resources['cpu_seconds'] == 900 and resources['wall_seconds'] == 1800)
  need(resources['result_bytes_per_file'] == 8 * 1024**2 and resources['output_total_bytes'] == 32 * 1024**2)
  need(resources['reserve_bytes'] == 2 * 1024**3)
  return total


def verify_current_gate(gate, head, protocol_digest):
  need(gate['head'] == head and gate['mission'] == MISSION and gate['protocol_raw_sha256'] == protocol_digest)
  need(gate['ci']['head_sha'] == head and gate['ci']['status'] == 'completed' and gate['ci']['conclusion'] == 'success')
  need(type(gate['diagnostic_runs']) is int and gate['diagnostic_runs'] == 1)
  need(
    all(
      gate[k] is False
      for k in ('DEV_authorized', 'D2_selection_authorized', 'E2_resume_authorized', 'HOLDOUT_authorized', 'vehicle_authorized', 'V5_authorized')
    )
  )


def preflight(work):
  head = control.git('rev-parse', 'HEAD')
  need(
    control.git('branch', '--show-current') == 'feature/cyber-autotune'
    and head == control.git('rev-parse', 'origin/feature/cyber-autotune')
    and not control.git('status', '--porcelain')
  )
  need(control.git('merge-base', BASELINE, head) == BASELINE)
  p, raw, old, lock, lock_raw, modules = load_sources()
  gate = control.checked(control.private(work / 'execution-gate.json'))
  reviews = {n: control.checked(control.private(work / n)) for n in ('science-review.json', 'authority-review.json')}
  sources = {**p['source_sha256'], **p['diagnostic_source_sha256']}
  control.verify_reviews(gate, reviews, control.sha(raw), sources)
  verify_current_gate(gate, head, control.sha(raw))
  resource_plan(p['resources'])
  source_policy = modules['empirical_s2_ri_policy'].policy()
  need(source_policy['receipt_sha256'] == old['source_policy_receipt_sha256'], 'Q1_DIAGNOSTIC_SOURCE_POLICY_CONFLICT')
  ref_raw = control.private(work / 'input-binding.json')
  ref = control.checked(ref_raw)
  need(control.sha(ref_raw) == gate['input_binding_raw_sha256'] and gate['job'] == ref['job'])
  prior_work = Path(ref['prior_work'])
  folder = prior_work / 'repeat-1'
  braw, araw = control.private(folder / 'execution-binding.json'), control.private(folder / 'execution-envelope.json')
  binding, abort = control.checked(braw), control.checked(araw)
  verified = control.checked(control.private(folder / 'verify-only-resume.json'))
  old_gate = control.checked(control.private(prior_work / 'execution-gate.json'))
  need(control.sha(braw) == ref['failed_binding_raw_sha256'] and control.sha(araw) == ref['failed_abort_raw_sha256'] == verified['abort_raw_sha256'])
  authenticate_reference(ref, binding, abort, verified, old_gate, old, lock, lock_raw)
  modules['empirical_hurdle_v4_e_bootstrap'].warm_dependencies()
  need(sys.version.split()[0] == old['environment']['python'] and np.__version__ == old['environment']['numpy'])
  need(all(os.environ.get(k) == '1' for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')))
  need(control.sha(control.canonical(np.show_config(mode='dicts'))) == old['environment']['blas_build_identity_sha256'])
  need(ctypes.CDLL('libm.so.6').fegetround() == 0)
  values = control.controls(Path(ref['historical_control_root']), old, modules)
  refs, roots, request, auth, jobs, environment, mounted, _, _ = values
  need(roots == ref['roots'] == binding['roots'])
  index = ref['job_index_zero_based']
  job = ref['job']
  need([jobs[index]['candidate_id'], jobs[index]['fold']] == job and jobs[index]['fields'][0]['anchor_sha256'] == ref['identity']['anchor_sha256'])
  for source in (*roots.values(), str(prior_work), ref['historical_control_root']):
    need(work != Path(source) and not work.is_relative_to(Path(source)) and not Path(source).is_relative_to(work))
  fd = control.directory(work)
  try:
    size = os.fstatvfs(fd)
    need(size.f_bavail * size.f_frsize >= p['resources']['reserve_bytes'] + p['resources']['output_total_bytes'])
    need(os.fstat(fd).st_dev != mounted[0])
  finally:
    os.close(fd)
  need(int(Path('/proc/self/statm').read_text().split()[0]) * os.sysconf('SC_PAGE_SIZE') <= p['resources']['runtime_reserve_bytes'])
  return p, raw, ref, gate, modules, roots, request, auth, jobs, environment, mounted, source_policy


def run(work):
  p, protocol_raw, ref, gate, modules, roots, request, auth, jobs, environment, mounted, source_policy = preflight(work)
  limits = p['resources']
  for which, cap in (
    (resource.RLIMIT_AS, limits['address_space_bytes']),
    (resource.RLIMIT_CPU, limits['cpu_seconds']),
    (resource.RLIMIT_FSIZE, limits['result_bytes_per_file']),
    (resource.RLIMIT_CORE, 0),
  ):
    resource.setrlimit(which, (cap, cap))
  signal.signal(signal.SIGALRM, lambda *_a: (_ for _ in ()).throw(ValueError('Q1_DIAGNOSTIC_RESOURCE_BOUND')))
  signal.alarm(limits['wall_seconds'])
  inp = modules['empirical_hurdle_v4_e2_inputs']
  core = modules['empirical_hurdle_v4_e2_v2_q1_diagnostic']
  math = modules['empirical_hurdle_fit_cv_math']
  reference = control.public('empirical-hurdle-fit-cv-results-v1.json')['jobs'][ref['job_index_zero_based']]
  phase = Phase(ref['job'], reference['train_route'])

  class Reader(inp.Reader):
    def raw(self, owner, member, kind, expected_raw, cap):
      need(len(self.events) < limits['input_open_limit'] and sum(e['bytes_read'] for e in self.events) + cap <= limits['input_bytes_limit'])
      if kind == 'array':
        phase.authorize(owner, member, kind)
        planned = phase.plan[owner, member]
        need(expected_raw == planned['raw_sha256'] and cap == planned['cap'], 'Q1_DIAGNOSTIC_ARRAY_PLAN_CONFLICT')
      return super().raw(owner, member, kind, expected_raw, cap)

  reader = Reader(roots, '/mnt/e', mounted, phase)
  audit = modules['empirical_hurdle_v4_e_bootstrap'].RuntimeFirewall()
  sys.addaudithook(audit)
  counters = {}
  start = time.monotonic()
  binding = None

  def write(name, value):
    audit.writing_output = True
    try:
      return control.persist(work, name, value, limits['result_bytes_per_file'])
    finally:
      audit.writing_output = False

  def forbidden(*_a, **_k):
    audit.attempts += 1
    raise ValueError('Q1_DIAGNOSTIC_FORBIDDEN_OPERATION')

  original_project = math.project

  def project(value):
    counters['projection_calls'] = counters.get('projection_calls', 0) + 1
    counters['projection_rows'] = counters.get('projection_rows', 0) + len(value)
    return original_project(value)

  try:
    with ExitStack() as stack:
      modules['empirical_hurdle_v4_e_bootstrap'].trap_deserialization(stack, forbidden)
      for module, names in (
        (modules['empirical_hurdle_v4_e2_decision'], ('select_context', 'select_job', 'potentials')),
        (modules['empirical_hurdle_v4_e2_evaluation'], ('evaluate_job',)),
        (modules['empirical_hurdle_v4_e2_v2_execution'] if 'empirical_hurdle_v4_e2_v2_execution' in modules else v2, ('run', 'train')),
        (modules['empirical_hurdle_v4_execution'], ('train', 'select', 'run', 'synthetic_run')),
        (core, ('canonical_synthetic', 'synthetic_controls')),
        (core.prior, ('diagnose', 'synthetic', 'parity_control')),
        (math, ('fit_stage1', 'fit_stage2', 'newton', 'normalizer', 'integrated')),
        (math.source, ('fit', 'normalizer')),
      ):
        for name in names:
          if hasattr(module, name):
            stack.enter_context(patch.object(module, name, forbidden))
      stack.enter_context(patch.object(math, 'project', project))
      provider = provider_type(modules)(
        reader,
        jobs,
        v4_manifest=request['manifests']['V4_REPEAT_1'],
        v1_manifest=request['manifests']['V1_REFERENCE'],
        v4_authorization=auth,
        v1_authorization_sha=request['authorization']['V1_REFERENCE'],
        references=control.public('empirical-hurdle-fit-cv-results-v1.json')['jobs'],
        job_catalog=control.public('empirical-hurdle-stage1-v4-job-manifest.json')['jobs'],
        source_policy=source_policy,
      )
      index = ref['job_index_zero_based']
      plan = provider.prepare(index)
      binding = control.sealed(
        {
          'schema': 'V4_E2_V2_Q1_FRESH_DIAGNOSTIC_BINDING_V1',
          'mission': MISSION,
          'head': gate['head'],
          'protocol_raw_sha256': control.sha(protocol_raw),
          'current_gate_receipt_sha256': gate['receipt_sha256'],
          'failed_reference_receipt_sha256': ref['receipt_sha256'],
          'failed_abort_receipt_sha256': ref['failed_abort_receipt_sha256'],
          'job': ref['job'],
          'role': 'TRAIN',
          'ordered_anchor_sha256': ref['identity']['anchor_sha256'],
          'model_identity': ref['identity']['stage2_receipts'],
          'roots': roots,
          'environment': environment,
          'exact_array_allowlist': list(plan.values()),
          'metadata_events_before_numeric': reader.events.copy(),
          'source_sha256': {**p['source_sha256'], **p['diagnostic_source_sha256']},
          'resources': limits,
          'DEV_authorized': False,
          'D2_selection_authorized': False,
          'E2_resume_authorized': False,
        }
      )
      digest = write('execution-binding.json', binding)
      readback = control.private(work / 'execution-binding.json', limits['result_bytes_per_file'])
      need(control.checked(readback) == binding)
      phase.enable(plan, digest, control.sha(readback))
      provider.admit_train_sources()
      scores, labels, prior = provider.train(index)
      blocks, anchor, n = provider.train_blocks(index)
      need(anchor == ref['identity']['anchor_sha256'] and n == ref['expected_train_count'] == len(scores))
      stage2 = provider.stage2(index)
      counters['frozen_Stage2_model_loads'] = 1
      counters['D0_TRAIN_reconstruction_attempts'] = 1
      result, _ = core.diagnose_training(blocks, ref['job'][0], stage2, scores, labels, prior, ref['identity'], counters=counters)
      need(not audit.attempts)
      status = core.outcome(result)
      payload = control.sealed(
        {
          'schema': 'V4_E2_V2_Q1_PRIVATE_DIAGNOSTIC_RESULT_V1',
          'status': status,
          'binding_receipt_sha256': binding['receipt_sha256'],
          'failed_abort_receipt_sha256': ref['failed_abort_receipt_sha256'],
          'diagnostic': result,
          'input_events': reader.events,
          'input_reads': reader.summary(),
          'control_events': control.CONTROL_EVENTS,
          'operation_counters': counters,
          'forbidden_operation_counters': dict.fromkeys(FORBIDDEN, 0),
          'source_writes': 0,
          'forbidden_attempts': audit.attempts,
          'wall_seconds': time.monotonic() - start,
          'cpu_seconds': resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime,
          'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'D2_performance': 'PERFORMANCE_NOT_EVALUATED',
        }
      )
      digest = write('canonical-result.json', payload)
      stored = control.private(work / 'canonical-result.json', limits['result_bytes_per_file'])
      need(control.sha(stored) == digest and control.checked(stored) == payload)
      print(json.dumps({'status': status, 'diagnostic_jobs': 1, 'DEV_reads': 0, 'D2_decisions': 0, 'source_writes': 0}), flush=True)
      return status
  except Exception as exc:
    status = (
      'E2_V2_Q1_INPUT_OR_TRANSFORM_CONFLICT'
      if str(exc) in ('E2_TRAIN_RECORDED_ORDER_CONFLICT', 'E2_TRAIN_ORDERED_ANCHOR_CONFLICT')
      else 'E2_V2_Q1_DIAGNOSTIC_UNRESOLVED'
    )
    write(
      'execution-envelope.json',
      control.sealed(
        {
          'schema': 'V4_E2_V2_Q1_DIAGNOSTIC_ABORT_V1',
          'status': status,
          'reason': str(exc) if re.fullmatch('[A-Z0-9_]+', str(exc)) else 'Q1_DIAGNOSTIC_PRECONDITION_OR_NUMERIC_FAILURE',
          'binding_receipt_sha256': None if binding is None else binding['receipt_sha256'],
          'input_events': reader.events,
          'input_reads': reader.summary(),
          'operation_counters': counters,
          'forbidden_attempts': audit.attempts,
          'source_writes': 0,
        }
      ),
    )
    print(json.dumps({'status': status, 'source_writes': 0}), flush=True)
    return status
  finally:
    audit.active = False
    signal.alarm(0)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--work', required=True)
  args = parser.parse_args()
  work = Path(args.work)
  need(work.is_absolute() and '..' not in work.parts)
  status = run(work)
  if status not in ('E2_V2_Q1_ROOT_CAUSE_IDENTIFIED', 'E2_V2_Q1_BATCH_LAYOUT_NUMERICAL_DIFFERENCE_CONFIRMED'):
    raise SystemExit(1)


if __name__ == '__main__':
  try:
    main()
  except Exception as exc:
    print(json.dumps({'status': 'E2_Q1_DIAGNOSTIC_INPUT_BINDING_INSUFFICIENT', 'reason': type(exc).__name__}), flush=True)
    raise SystemExit(1) from None
