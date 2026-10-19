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


def need(condition, code='Q1_METADATA_BINDING_CONFLICT'):
  control.need(condition, code)


BASELINE = '5032e7197ed84fc58e236152f4a3ba30b1a3f7e3'
MISSION = 'STAGE1_V4_E2_V2_Q1_READER_SCHEMA_REPAIR_AND_FRESH_DIAGNOSTIC'
PROTOCOL = 'empirical-hurdle-stage1-v4-e2-v2-q1-diagnostic-protocol-v2.json'
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
  'MIXED_TRAIN_CARRIER_OPENINGS',
  'NOMINAL_COEFFICIENTS_ARRAY_OPENINGS',
  'SINGULAR_VALUES_ARRAY_OPENINGS',
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
      need(self.enabled and (owner, member) in self.plan, 'Q1_NUMERIC_ALLOWLIST_NOT_ENABLED')
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


WRITER_SHA = 'a952eb4986f47e0335bf355ee74868755f14b592d05070008a0b117979d4e635'
DESCRIPTOR_KEYS = frozenset(
  ('dtype', 'shape', 'order', 'array_sha256', 'file_sha256', 'npy_sha256', 'storage_format', 'filename', 'lossless_roundtrip_verified')
)


def validate_model_metadata(norm, model, reference, members, prefix):
  """Authenticate Writer declarations; never open nominal/singular payloads.

  The Stage2 TRAIN anchor/count are the original MOVE-only fitting subset,
  linked by the frozen V1 Stage2 reference, not the full TRAIN score anchor.
  """
  code = 'Q1_MODEL_DESCRIPTOR_FORMAT_CONFLICT'
  need(type(norm) is dict and type(model) is dict, code)
  for receipt in (norm, model):
    need(
      receipt.get('receipt_sha256') == control.sha(control.canonical({k: v for k, v in receipt.items() if k != 'receipt_sha256'})),
      'Q1_MODEL_SOURCE_HASH_CONFLICT',
    )
  need(type(norm.get('arrays')) is dict and type(model.get('arrays')) is dict, code)
  keys = set(model['arrays'])
  need(
    set(norm['arrays']) == set(NORMALIZER) and {'coefficients', 'nominal_coefficients'} <= keys <= {'coefficients', 'nominal_coefficients', 'singular_values'},
    'Q1_MODEL_DESCRIPTOR_SET_CONFLICT',
  )
  ref = reference['stage2']
  need(norm['receipt_sha256'] == ref['normalizer_receipt_sha256'] and model['receipt_sha256'] == ref['model_receipt_sha256'], 'Q1_MODEL_SOURCE_HASH_CONFLICT')
  need(norm['schema'] == 'EMPIRICAL_HURDLE_TRAIN_NORMALIZER_V1' and model['schema'] == 'EMPIRICAL_HURDLE_FOLD_STAGE_MODEL_V1', code)
  need(norm['stage'] == model['stage'] == 'STAGE2' and model['normalizer_sha256'] == norm['receipt_sha256'], 'Q1_MODEL_NORMALIZER_IDENTITY_CONFLICT')
  candidate, fold = prefix.split('/')[1:3]
  need(norm['candidate_id'] == model['candidate_id'] == candidate and norm['fold'] == model['fold'] == fold, 'Q1_METADATA_BINDING_CONFLICT')
  need(
    norm['train_anchor_sha256'] == model['train_anchor_sha256'] == ref['train_anchor_sha256'] and norm['count'] == model['train_count'] == ref['count'],
    'Q1_METADATA_BINDING_CONFLICT',
  )
  need(norm['train_route'] == reference['train_route'] and norm['authorization_sha256'] == model['authorization_sha256'], 'Q1_METADATA_BINDING_CONFLICT')
  from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_store as store
  from openpilot.tools.cyber_autotune import empirical_hurdle_fit_cv_math as math

  need(model['policy_sha256'] == store.PINS['fitting-policy'], 'Q1_MODEL_SOURCE_HASH_CONFLICT')
  dimension = 2 * math.parameters(candidate)[1] + 3
  effective = model['effective_columns']
  need(type(effective) is int and 0 < effective <= dimension and model['nominal_columns'] == dimension, code)
  need(type(model['train_count']) is int and model['train_count'] >= effective and model['rank'] == effective, code)
  need(type(model['constant_columns']) is int and model['constant_columns'] == dimension - effective, code)
  for name in ('rank', 'effective_columns', 'nominal_columns', 'constant_columns'):
    need(model[name] == ref[name], 'Q1_MODEL_NORMALIZER_IDENTITY_CONFLICT')
  need(bool(re.fullmatch('[0-9a-f]{64}', model['effective_x_sha256'])), code)
  need(model['interpretation'] == 'EMPIRICAL_PREDICTIVE_PARAMETERS', code)
  for role, receipt in (('normalizer', norm), ('model', model)):
    for name, desc in receipt['arrays'].items():
      need(type(desc) is dict and set(desc) == DESCRIPTOR_KEYS, code)
      n = effective if name in ('coefficients', 'singular_values', 'effective') else dimension
      dtype = '|b1' if name == 'constant' else '<i8' if name == 'effective' else '<f8'
      need(desc['dtype'] == dtype and desc['shape'] == [n] and all(type(v) is int for v in desc['shape']) and desc['order'] == 'C', code)
      need(desc['storage_format'] == 'NPY_GZIP_V1' and desc['filename'] == name + '.npy.gz' and desc['lossless_roundtrip_verified'] is True, code)
      need(all(type(desc[k]) is str and re.fullmatch('[0-9a-f]{64}', desc[k]) for k in ('file_sha256', 'array_sha256', 'npy_sha256')), code)
      member = prefix + '/stage2/' + role + '/' + name + '.npy.gz'
      need(members.get(member) == desc['file_sha256'], 'Q1_MODEL_SOURCE_HASH_CONFLICT')
  need(model['arrays']['coefficients']['array_sha256'] == ref['coefficient_sha256'], 'Q1_MODEL_SOURCE_HASH_CONFLICT')


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
      validate_model_metadata(norm, model, self.references[index], r.maps['V1'], prefix)
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
  need(p['writer_source_sha256'] == WRITER_SHA and p['source_sha256']['empirical_hurdle_fit_cv_execution.py'] == WRITER_SHA, 'Q1_MODEL_SOURCE_HASH_CONFLICT')
  need(p['version'] == 'V4_E2_V2_Q1_DIAGNOSTIC_PROTOCOL_V2' and p['baseline_head'] == BASELINE)
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
  need(gate['output_root'] and gate['head'] == head and gate['mission'] == MISSION and gate['protocol_raw_sha256'] == protocol_digest)
  need(gate['ci']['head_sha'] == head and gate['ci']['status'] == 'completed' and gate['ci']['conclusion'] == 'success')
  need(type(gate['diagnostic_runs']) is int and gate['diagnostic_runs'] == 1)
  need(
    all(
      gate[k] is False
      for k in ('DEV_authorized', 'D2_selection_authorized', 'E2_resume_authorized', 'HOLDOUT_authorized', 'vehicle_authorized', 'V5_authorized')
    )
  )


def preflight(work, ledger=None):
  head = control.git('rev-parse', 'HEAD')
  need(
    control.git('branch', '--show-current') == 'feature/cyber-autotune'
    and head == control.git('rev-parse', 'origin/feature/cyber-autotune')
    and not control.git('status', '--porcelain')
  )
  need(control.git('merge-base', BASELINE, head) == BASELINE)
  p, raw, old, lock, lock_raw, modules = load_sources()
  gate = control.checked(control.private(work / 'execution-gate.json'))
  if ledger is not None:
    ledger.identity['current_grant_receipt_sha256'] = gate['receipt_sha256']
  reviews = {n: control.checked(control.private(work / n)) for n in ('science-review.json', 'authority-review.json')}
  sources = {**p['source_sha256'], **p['diagnostic_source_sha256']}
  control.verify_reviews(gate, reviews, control.sha(raw), sources)
  verify_current_gate(gate, head, control.sha(raw))
  need(gate['output_root'] == str(work), 'Q1_METADATA_BINDING_CONFLICT')
  resource_plan(p['resources'])
  source_policy = modules['empirical_s2_ri_policy'].policy()
  need(source_policy['receipt_sha256'] == old['source_policy_receipt_sha256'], 'Q1_DIAGNOSTIC_SOURCE_POLICY_CONFLICT')
  ref_raw = control.private(work / 'input-binding.json')
  ref = control.checked(ref_raw)
  if ledger is not None:
    ledger.identity['failed_reference_receipt_sha256'] = ref['receipt_sha256']
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
  need(set(gate['output_disjoint_inputs']) == {*roots.values(), str(prior_work), ref['historical_control_root']}, 'Q1_OUTPUT_SCOPE_CONFLICT')
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


class Telemetry:
  """Entry-to-finally ledger; prior attempts are never backfilled."""

  def __init__(self):
    self.started = time.monotonic()
    self.cpu = resource.getrusage(resource.RUSAGE_SELF)
    self.control_start = len(control.CONTROL_EVENTS)
    self.control_attempts = 0
    self.stage = 'ENTRY'
    self.reader = self.phase = self.audit = None
    self.binding = None
    self.counters = {'frozen_Stage2_model_loads': 0, 'D0_TRAIN_reconstruction_attempts': 0}
    self.outputs = []
    self.ac_started = False
    self.identity = {
      'mission': MISSION,
      'head': 'NOT_RECORDED',
      'protocol_raw_sha256': 'NOT_RECORDED',
      'current_grant_receipt_sha256': 'NOT_RECORDED',
      'failed_reference_receipt_sha256': 'NOT_RECORDED',
      'source_sha256': 'NOT_RECORDED',
    }

  def snapshot(self):
    usage = resource.getrusage(resource.RUSAGE_SELF)
    events = [] if self.reader is None else self.reader.events
    controls = control.CONTROL_EVENTS[self.control_start :]
    return {
      'stage': self.stage,
      'identity': self.identity,
      'binding_receipt_sha256': 'NOT_RECORDED' if self.binding is None else self.binding['receipt_sha256'],
      'input_events': events.copy(),
      'input_reads': {
        kind: {'files': sum(e['file_openings'] for e in events if e['kind'] == kind), 'bytes': sum(e['bytes_read'] for e in events if e['kind'] == kind)}
        for kind in ('metadata', 'array')
      },
      'control_events': controls.copy(),
      'control_reads': {'files': len(controls), 'bytes': sum(e['bytes'] for e in controls), 'scope': 'SUCCESSFULLY_COMPLETED_READS'},
      'control_read_attempts': self.control_attempts,
      'failed_control_read_bytes': 0 if self.control_attempts == len(controls) else 'NOT_RECORDED',
      'failed_control_file_openings': 0 if self.control_attempts == len(controls) else 'NOT_RECORDED',
      'control_totals_complete': self.control_attempts == len(controls),
      'operation_counters': self.counters.copy(),
      'wall_seconds': time.monotonic() - self.started,
      'process_cpu_user_seconds': usage.ru_utime - self.cpu.ru_utime,
      'process_cpu_system_seconds': usage.ru_stime - self.cpu.ru_stime,
      'process_peak_rss': {'value': usage.ru_maxrss, 'unit': 'KiB', 'scope': 'LINUX_PROCESS_LIFETIME_HIGH_WATER'},
      'durable_array_allowlist_enabled': self.phase is not None and self.phase.enabled,
      'actual_A_C_started': self.ac_started,
      'output_file_records_before_telemetry': self.outputs.copy(),
      'source_writes': 0,
      'forbidden_operation_counters': dict.fromkeys(FORBIDDEN, 0),
      'forbidden_attempts': 0 if self.audit is None else self.audit.attempts,
      'measurement_scope': 'THIS_FRESH_PROCESS_ONLY;NO_RETROACTIVE_PRIOR_COUNTERS',
    }


def predicate(error, stage):
  if isinstance(error, MemoryError):
    return 'Q1_DIAGNOSTIC_RESOURCE_BOUND'
  reason = str(error)
  if re.fullmatch('Q1_[A-Z0-9_]+', reason):
    return reason
  if stage == 'NUMERIC_INPUT':
    return 'Q1_NUMERIC_INPUT_READ_FAILURE'
  if stage == 'A_C_DIAGNOSTIC':
    return 'Q1_DIAGNOSTIC_NUMERICAL_EXECUTION_INCOMPLETE'
  return 'Q1_METADATA_BINDING_CONFLICT'


def persist(work, name, value, telemetry):
  """Exclusive fsync output with aggregate cap; no unrestricted source writes."""
  need(name in ('attempt.json', 'execution-binding.json', 'canonical-result.json', 'execution-envelope.json', 'telemetry.json'), 'Q1_OUTPUT_SCOPE_CONFLICT')
  raw = control.canonical(value)
  need(len(raw) <= 8 * 1024**2 and sum(v['bytes'] for v in telemetry.outputs) + len(raw) <= 32 * 1024**2, 'Q1_DIAGNOSTIC_RESOURCE_BOUND')
  audit = telemetry.audit
  if audit is not None:
    audit.writing_output = True
  try:
    parent = control.directory(work)
    try:
      fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent)
      output = {'name': name, 'bytes': 0, 'complete': False}
      telemetry.outputs.append(output)
      try:
        view = memoryview(raw)
        while view:
          count = os.write(fd, view)
          need(count > 0, 'Q1_OUTPUT_WRITE_FAILURE')
          output['bytes'] += count
          view = view[count:]
        os.fsync(fd)
        need((os.fstat(fd).st_mode & 0o777) == 0o600, 'Q1_OUTPUT_PERMISSION_CONFLICT')
      finally:
        os.close(fd)
      directory_fd = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC, dir_fd=parent)
      try:
        os.fsync(directory_fd)
      finally:
        os.close(directory_fd)
    finally:
      os.close(parent)
    output['complete'] = True
    return control.sha(raw)
  finally:
    if audit is not None:
      audit.writing_output = False


def authorize_output(work, protocol_raw, protocol, ledger):
  """Current exact approval before the first exclusive output write."""
  import pwd

  home = Path(pwd.getpwuid(os.getuid()).pw_dir)
  need(work.parent == home and work.name == 'v4-e2-v2-q1-reader-repair-diagnostic-v2', 'Q1_OUTPUT_SCOPE_CONFLICT')
  gate = control.checked(control.private(work / 'execution-gate.json'))
  ledger.identity['current_grant_receipt_sha256'] = gate['receipt_sha256']
  verify_current_gate(gate, ledger.identity['head'], control.sha(protocol_raw))
  need(gate['output_root'] == str(work), 'Q1_OUTPUT_SCOPE_CONFLICT')
  reviews = {n: control.checked(control.private(work / n)) for n in ('science-review.json', 'authority-review.json')}
  control.verify_reviews(gate, reviews, control.sha(protocol_raw), {**protocol['source_sha256'], **protocol['diagnostic_source_sha256']})
  need(type(gate['output_disjoint_inputs']) is list and len(gate['output_disjoint_inputs']) >= 5, 'Q1_OUTPUT_SCOPE_CONFLICT')
  for source in gate['output_disjoint_inputs']:
    source = Path(source)
    need(
      source.is_absolute() and '..' not in source.parts and work != source and not work.is_relative_to(source) and not source.is_relative_to(work),
      'Q1_OUTPUT_SCOPE_CONFLICT',
    )
  fd = control.directory(work)
  try:
    size = os.fstatvfs(fd)
    need(size.f_bavail * size.f_frsize >= protocol['resources']['reserve_bytes'] + protocol['resources']['output_total_bytes'], 'Q1_DIAGNOSTIC_RESOURCE_BOUND')
  finally:
    os.close(fd)


def input_budget(ledger, cap):
  controls = control.CONTROL_EVENTS[ledger.control_start :]
  events = [] if ledger.reader is None else ledger.reader.events
  openings = len(controls) + sum(e['file_openings'] for e in events)
  size = sum(e['bytes'] for e in controls) + sum(e['bytes_read'] for e in events)
  need(openings < 1600 and type(cap) is int and 0 < cap and size + cap <= 8 * 1024**3, 'Q1_DIAGNOSTIC_RESOURCE_BOUND')


def run(work):
  ledger = Telemetry()
  status, reason = 'E2_Q1_DIAGNOSTIC_INPUT_BINDING_INSUFFICIENT', 'NOT_RECORDED'
  owns_attempt = False
  private_original = control.private

  def counted_private(path, cap=16 * 1024**2):
    input_budget(ledger, cap)
    ledger.control_attempts += 1
    return private_original(path, cap)

  control.private = counted_private
  try:
    # One-shot latch precedes every private control and original metadata read.
    need(work.name == 'v4-e2-v2-q1-reader-repair-diagnostic-v2', 'Q1_OUTPUT_SCOPE_CONFLICT')
    p_raw = (control.PUBLIC / PROTOCOL).read_bytes()
    public_protocol = control.checked(p_raw)
    resource_plan(public_protocol['resources'])
    limits = public_protocol['resources']
    for which, cap in (
      (resource.RLIMIT_AS, limits['address_space_bytes']),
      (resource.RLIMIT_CPU, limits['cpu_seconds']),
      (resource.RLIMIT_FSIZE, limits['result_bytes_per_file']),
      (resource.RLIMIT_CORE, 0),
    ):
      resource.setrlimit(which, (cap, cap))
    signal.signal(signal.SIGALRM, lambda *_a: (_ for _ in ()).throw(ValueError('Q1_DIAGNOSTIC_RESOURCE_BOUND')))
    signal.alarm(limits['wall_seconds'])
    ledger.identity.update(
      head=control.git('rev-parse', 'HEAD'),
      protocol_raw_sha256=control.sha(p_raw),
      source_sha256={**public_protocol['source_sha256'], **public_protocol['diagnostic_source_sha256']},
    )
    authorize_output(work, p_raw, public_protocol, ledger)
    persist(work, 'attempt.json', control.sealed({'schema': 'V4_Q1_READER_REPAIR_ATTEMPT_V2', **ledger.identity}), ledger)
    owns_attempt = True
    ledger.stage = 'PREFLIGHT'
    p, protocol_raw, ref, gate, modules, roots, request, auth, jobs, environment, mounted, source_policy = preflight(work, ledger)
    ledger.identity.update(current_grant_receipt_sha256=gate['receipt_sha256'], failed_reference_receipt_sha256=ref['receipt_sha256'])
    limits = p['resources']
    for which, cap in (
      (resource.RLIMIT_AS, limits['address_space_bytes']),
      (resource.RLIMIT_CPU, limits['cpu_seconds']),
      (resource.RLIMIT_FSIZE, limits['result_bytes_per_file']),
      (resource.RLIMIT_CORE, 0),
    ):
      resource.setrlimit(which, (cap, cap))
    signal.signal(signal.SIGALRM, lambda *_a: (_ for _ in ()).throw(ValueError('Q1_DIAGNOSTIC_RESOURCE_BOUND')))
    signal.alarm(max(1, limits['wall_seconds'] - int(time.monotonic() - ledger.started)))
    inp, core = modules['empirical_hurdle_v4_e2_inputs'], modules['empirical_hurdle_v4_e2_v2_q1_diagnostic']
    math = modules['empirical_hurdle_fit_cv_math']
    reference = control.public('empirical-hurdle-fit-cv-results-v1.json')['jobs'][ref['job_index_zero_based']]
    phase = ledger.phase = Phase(ref['job'], reference['train_route'])

    class Reader(inp.Reader):
      def raw(self, owner, member, kind, expected_raw, cap):
        input_budget(ledger, cap)
        if kind == 'array':
          phase.authorize(owner, member, kind)
          planned = phase.plan[owner, member]
          need(expected_raw == planned['raw_sha256'] and cap == planned['cap'], 'Q1_METADATA_BINDING_CONFLICT')
        return super().raw(owner, member, kind, expected_raw, cap)

    reader = ledger.reader = Reader(roots, '/mnt/e', mounted, phase)
    audit = ledger.audit = modules['empirical_hurdle_v4_e_bootstrap'].RuntimeFirewall()
    sys.addaudithook(audit)
    counters = ledger.counters

    def forbidden(*_a, **_k):
      audit.attempts += 1
      raise ValueError('Q1_DIAGNOSTIC_FORBIDDEN_OPERATION')

    original_predict = math.predict_delta

    def predict(x, model):
      ledger.ac_started = True
      counters['Stage2_actual_predict_calls'] = counters.get('Stage2_actual_predict_calls', 0) + 1
      return original_predict(x, model)

    original_project = math.project

    def project(value):
      counters['projection_calls'] = counters.get('projection_calls', 0) + 1
      counters['projection_rows'] = counters.get('projection_rows', 0) + len(value)
      return original_project(value)

    with ExitStack() as stack:
      modules['empirical_hurdle_v4_e_bootstrap'].trap_deserialization(stack, forbidden)
      for module, names in (
        (modules['empirical_hurdle_v4_e2_decision'], ('select_context', 'select_job', 'potentials')),
        (modules['empirical_hurdle_v4_e2_evaluation'], ('evaluate_job',)),
        (v2, ('run', 'train')),
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
      stack.enter_context(patch.object(math, 'predict_delta', predict))
      ledger.stage = 'METADATA_PLANNING'
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
      binding = ledger.binding = control.sealed(
        {
          'schema': 'V4_E2_V2_Q1_FRESH_DIAGNOSTIC_BINDING_V2',
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
          'source_sha256': ledger.identity['source_sha256'],
          'resources': limits,
          'DEV_authorized': False,
          'D2_selection_authorized': False,
          'E2_resume_authorized': False,
        }
      )
      ledger.stage = 'ARRAY_ALLOWLIST_READBACK'
      digest = persist(work, 'execution-binding.json', binding, ledger)
      readback = control.private(work / 'execution-binding.json', limits['result_bytes_per_file'])
      need(control.checked(readback) == binding, 'Q1_METADATA_BINDING_CONFLICT')
      phase.enable(plan, digest, control.sha(readback))
      ledger.stage = 'NUMERIC_INPUT'
      provider.admit_train_sources()
      scores, labels, prior = provider.train(index)
      blocks, anchor, n = provider.train_blocks(index)
      need(anchor == ref['identity']['anchor_sha256'] and n == ref['expected_train_count'] == len(scores), 'Q1_METADATA_BINDING_CONFLICT')
      counters['frozen_Stage2_model_load_attempts'] = 1
      stage2 = provider.stage2(index)
      counters['frozen_Stage2_model_loads'] = 1
      ledger.stage = 'A_C_DIAGNOSTIC'
      counters['D0_TRAIN_reconstruction_attempts'] = 1
      result, _ = core.diagnose_training(blocks, ref['job'][0], stage2, scores, labels, prior, ref['identity'], counters=counters)
      need(not audit.attempts, 'Q1_DIAGNOSTIC_FORBIDDEN_OPERATION')
      status = core.outcome(result)
      reason = 'Q1_DIAGNOSTIC_NUMERICAL_REPRODUCTION_CONFLICT' if status == 'E2_V2_Q1_DIAGNOSTIC_REPRODUCTION_CONFLICT' else 'NONE'
      ledger.stage = 'RESULT_SEAL'
      payload = control.sealed(
        {
          'schema': 'V4_E2_V2_Q1_PRIVATE_DIAGNOSTIC_RESULT_V2',
          'status': status,
          'binding_receipt_sha256': binding['receipt_sha256'],
          'diagnostic': result,
          'telemetry': ledger.snapshot(),
          'D2_performance': 'PERFORMANCE_NOT_EVALUATED',
        }
      )
      digest = persist(work, 'canonical-result.json', payload, ledger)
      stored = control.private(work / 'canonical-result.json', limits['result_bytes_per_file'])
      need(control.sha(stored) == digest and control.checked(stored) == payload, 'Q1_OUTPUT_READBACK_CONFLICT')
      ledger.stage = 'COMPLETE'
  except Exception as exc:
    owns_attempt = owns_attempt or any(v['name'] == 'attempt.json' for v in ledger.outputs)
    reason = predicate(exc, ledger.stage)
    status = 'E2_V2_Q1_READER_REPAIR_BLOCKED' if ledger.stage == 'METADATA_PLANNING' else 'E2_Q1_DIAGNOSTIC_INPUT_BINDING_INSUFFICIENT'
    if reason == 'Q1_DIAGNOSTIC_RESOURCE_BOUND':
      status = 'E2_Q1_DIAGNOSTIC_RESOURCE_PREFLIGHT_BLOCKED'
    elif ledger.stage == 'A_C_DIAGNOSTIC':
      status = (
        'E2_V2_Q1_INPUT_OR_TRANSFORM_CONFLICT'
        if str(exc) in ('E2_TRAIN_RECORDED_ORDER_CONFLICT', 'E2_TRAIN_ORDERED_ANCHOR_CONFLICT')
        else 'E2_V2_Q1_DIAGNOSTIC_UNRESOLVED'
      )
    if owns_attempt:
      persist(
        work,
        'execution-envelope.json',
        control.sealed({'schema': 'V4_Q1_READER_REPAIR_ABORT_V2', 'status': status, 'predicate': reason, 'telemetry': ledger.snapshot()}),
        ledger,
      )
  finally:
    if owns_attempt:
      # Final record includes control readbacks and its own output size/count.
      value = {'schema': 'V4_Q1_READER_REPAIR_TELEMETRY_V2', 'status': status, 'predicate': reason, **ledger.snapshot()}
      final_size = 0
      for _ in range(16):
        value['output_files_total'] = len(ledger.outputs) + 1
        value['output_bytes_total'] = sum(v['bytes'] for v in ledger.outputs) + final_size
        sealed = control.sealed(value)
        size = len(control.canonical(sealed))
        if size == final_size:
          break
        final_size = size
      need(len(control.canonical(control.sealed(value))) == value['output_bytes_total'] - sum(v['bytes'] for v in ledger.outputs), 'Q1_OUTPUT_SIZE_CONFLICT')
      persist(work, 'telemetry.json', sealed, ledger)
    if ledger.audit is not None:
      ledger.audit.active = False
    signal.alarm(0)
    control.private = private_original
  print(json.dumps({'status': status, 'source_writes': 0, 'D2_performance': 'PERFORMANCE_NOT_EVALUATED'}), flush=True)
  return status


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
