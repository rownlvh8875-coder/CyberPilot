"""Bound E2 controller. No grant is inferred from a mode flag or old E1 approval.

Exact private control references and a fresh human/review/CI gate live outside
Git. Original input reads use the pinned openat2 reader; this is not an OS sandbox.
"""

import argparse
import ast
from contextlib import ExitStack
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import stat
import subprocess
import sys
import time
import types
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / 'docs/cyberpilot/changes'
SOURCE = ROOT / 'openpilot/tools/cyber_autotune'
BASELINE = 'a0e78aa3c231fce77e194f44ab4120b1f5e2a845'
MISSION = 'STAGE1_V4_E2_D0_D1_D2_OFFLINE_EVALUATION'
PROTOCOL_NAME = 'empirical-hurdle-stage1-v4-e2-execution-protocol.json'
CONTROL_EVENTS = []
OUTPUT_NAMES = (
  'execution-binding.json',
  'train-decisions.json',
  'canonical-result.json',
  'execution-envelope.json',
  'verify-only-resume.json',
  'repeatability-receipt.json',
)


def need(condition, code='E2_CONTROL_CONFLICT'):
  if not condition:
    raise ValueError(code)


def sha(raw):
  return hashlib.sha256(raw).hexdigest()


def canonical(value):
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def checked(raw):
  value = json.loads(raw)
  need(value.get('receipt_sha256') == sha(canonical({k: v for k, v in value.items() if k != 'receipt_sha256'})), 'E2_CONTROL_SEAL_CONFLICT')
  return value


def sealed(value):
  return {**value, 'receipt_sha256': sha(canonical(value))}


def directory(path):
  need(path.is_absolute() and '..' not in path.parts)
  fd = os.open('/', os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)
  try:
    for part in path.parts[1:]:
      child = os.open(part, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
      os.close(fd)
      fd = child
    info = os.fstat(fd)
    need(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700, 'E2_PRIVATE_DIRECTORY_PERMISSION')
    return fd
  except Exception:
    os.close(fd)
    raise


def private(path, cap=16 * 1024**2):
  parent = directory(path.parent)
  try:
    fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
  finally:
    os.close(parent)
  try:
    before = os.fstat(fd)
    need(
      stat.S_ISREG(before.st_mode)
      and before.st_nlink == 1
      and before.st_uid == os.getuid()
      and stat.S_IMODE(before.st_mode) == 0o600
      and 0 < before.st_size <= cap,
      'E2_CONTROL_PERMISSION_OR_SIZE',
    )
    blocks, left = [], before.st_size
    while left:
      block = os.read(fd, min(left, 65536))
      need(bool(block), 'E2_CONTROL_CHANGED')
      blocks.append(block)
      left -= len(block)
    after = os.fstat(fd)
    need((before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'E2_CONTROL_CHANGED')
    raw = b''.join(blocks)
    CONTROL_EVENTS.append({'name': path.name, 'bytes': len(raw), 'raw_sha256': sha(raw)})
    return raw
  finally:
    os.close(fd)


def persist(destination, name, value, cap):
  need(name in OUTPUT_NAMES, 'E2_OUTPUT_FILENAME_SCOPE')
  raw = canonical(value)
  need(len(raw) <= cap, 'E2_OUTPUT_SIZE_BOUND')
  parent = directory(destination)
  try:
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent)
    try:
      with os.fdopen(fd, 'wb', closefd=False) as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
      need(stat.S_IMODE(os.fstat(fd).st_mode) == 0o600)
    finally:
      os.close(fd)
    sync = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC, dir_fd=parent)
    try:
      os.fsync(sync)
    finally:
      os.close(sync)
  finally:
    os.close(parent)
  return sha(raw)


def public(name):
  return checked((PUBLIC / name).read_bytes())


def git(*args):
  return subprocess.check_output(['git', *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL, timeout=30).strip()


def load_exact(protocol):
  import openpilot.tools.cyber_autotune as package

  buffers = {}
  for name, digest in protocol['source_sha256'].items():
    raw = (SOURCE / name).read_bytes()
    need(sha(raw) == digest, 'E2_SOURCE_PIN_DRIFT')
    buffers[name] = raw
  order = (
    'empirical_s2_ri_policy',
    'empirical_s2_ri_fit_cv_math',
    'empirical_hurdle_fit_cv_math',
    'empirical_hurdle_v4_fitting_policy',
    'empirical_hurdle_v4_execution',
    'empirical_hurdle_fit_cv_data',
    'empirical_hurdle_fit_cv_gates',
    'empirical_hurdle_v4_b0_metadata',
    'empirical_hurdle_v4_b1_evidence',
    'empirical_hurdle_v4_b1_train_score',
    'empirical_hurdle_v4_c_math',
    'empirical_hurdle_v4_c_diagnostics',
    'empirical_hurdle_v4_e_decision',
    'empirical_hurdle_v4_e_evaluation',
    'empirical_hurdle_v4_e_inputs',
    'empirical_hurdle_v4_e_publication',
    'empirical_hurdle_v4_e_bootstrap',
    'empirical_hurdle_v4_e2_decision',
    'empirical_hurdle_v4_e2_inputs',
    'empirical_hurdle_v4_e2_evaluation',
    'empirical_hurdle_v4_e2_publication',
  )
  modules = {}
  for name in order:
    module = types.ModuleType(package.__name__ + '.' + name)
    module.__file__, module.__package__ = str(SOURCE / (name + '.py')), package.__name__
    sys.modules[module.__name__] = module
    setattr(package, name, module)
    exec(compile(buffers[name + '.py'], module.__file__, 'exec'), module.__dict__)
    modules[name] = module
  return modules


def controls(work, protocol, modules):
  refs_raw = private(work / 'control-references.json')
  refs = checked(refs_raw)
  need(refs['schema'] == 'V4_E2_PRIVATE_CONTROL_REFERENCES_V1' and refs['current_grant'] == MISSION)
  old_protocol = public('empirical-hurdle-stage1-v4-e-execution-protocol-v2.json')
  source = private(Path(refs['e1_caller_path']), 65536)
  need(sha(source) == refs['e1_caller_raw_sha256'] == old_protocol['private_caller_sha256'])
  # Only the already reviewed exact environment function; no old executor main.
  parsed = ast.parse(source)
  environment_fn = next(n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name == 'live_environment')
  namespace = {'need': need, 'sha': sha, 'subprocess': subprocess, 'os': os, 'json': json}
  exec(compile(ast.Module(body=[environment_fn], type_ignores=[]), '<pinned-E1-environment-function>', 'exec'), namespace)
  auth = public('empirical-hurdle-stage1-v4-retrospective-execution-authorization.json')
  environment = namespace['live_environment'](auth)
  b0 = modules['empirical_hurdle_v4_b0_metadata']
  names = refs['references']
  handoff_raw = private(Path(names['HANDOFF']), 65536)
  need(sha(handoff_raw) == names['HANDOFF_SHA'], 'E2_HANDOFF_RAW_IDENTITY')
  handoff = b0._decode(handoff_raw)
  old = {}
  for owner, key in (('B0', 'B0_WORK'), ('B1', 'PRIOR'), ('TRAIN', 'TRAIN')):
    folder = Path(names[key])
    if owner == 'B0':
      old[owner] = {
        k: checked(private(folder / filename)) for k, filename in (('binding', 'execution-binding.json'), ('result', 'metadata-verification-receipt.json'))
      }
    else:
      old[owner] = {
        k: checked(private(folder / filename))
        for k, filename in (('binding', 'execution-binding.json'), ('result', 'verification-result.json'), ('resume', 'verify-only-resume.json'))
      }
  need(old['B0']['result']['status'] == 'B0_VERIFIED_METADATA_ONLY' and old['B0']['binding']['handoff_sha256'] == names['HANDOFF_SHA'])
  need(old['B1']['binding']['handoff_sha256'] == names['HANDOFF_SHA'])
  jobs = modules['empirical_hurdle_v4_c_diagnostics'].inputs(old['B1'], old['TRAIN'])
  c_binding = checked(private(Path(names['C_WORK']) / 'execution-binding.json'))
  need(
    c_binding['previous_binding_sha256'] == old['B1']['binding']['receipt_sha256']
    and c_binding['completion_binding_sha256'] == old['TRAIN']['binding']['receipt_sha256']
  )
  E1_binding_raw = private(Path(names['WORK']) / 'repeat-1/execution-binding.json')
  E1_binding = checked(E1_binding_raw)
  E1_envelope_raw = private(Path(names['WORK']) / 'repeat-1/execution-envelope.json')
  E1_envelope = checked(E1_envelope_raw)
  E1_resume = checked(private(Path(names['WORK']) / 'repeat-1/verify-only-resume.json'))
  need(sha(E1_binding_raw) == refs['source_control_raw_sha256']['E1_binding'] and sha(E1_envelope_raw) == refs['source_control_raw_sha256']['E1_envelope'])
  need(E1_envelope['binding_receipt_sha256'] == E1_binding['receipt_sha256'] and E1_envelope['forbidden_attempts'] == 0)
  need(E1_resume['source_rereads'] == E1_resume['inference_calls'] == E1_resume['recompute_calls'] == 0)
  need(E1_binding['protocol_raw_sha256'] == protocol['E1_protocol_raw_sha256'] and E1_binding['prior_lineage'] == refs['prior_lineage'])
  request = old['B1']['binding']['request']
  roots = E1_binding['roots']
  need(roots == refs['roots'])
  need(roots['V4'] == request['roots']['V4_REPEAT_1'] and roots['V1'] == request['roots']['V1_REFERENCE'])
  need(roots['V1_TOP'] == handoff['roots']['v1_reference']['exact_execution_root'])
  for name, value in (
    ('source', roots['V1_TOP']),
    ('output', handoff['roots']['v4_actual']['exact_execution_root']),
    ('causal', roots['CAUSAL']),
    ('derived', roots['DERIVED']),
  ):
    need(sha(value.encode()) == auth['root_identities'][name], 'E2_ROOT_BINDING_CONFLICT')
  for path in roots.values():
    b0._path(path, absolute=True)
    need(not work.is_relative_to(Path(path)) and not Path(path).is_relative_to(work), 'E2_SOURCE_OUTPUT_OVERLAP')
  fd = b0._mount_fd('/mnt/e')
  try:
    info = os.fstat(fd)
    mounted = info.st_dev, info.st_ino
    need(f'{os.major(info.st_dev)}:{os.minor(info.st_dev)}' == environment['mount']['maj:min'])
  finally:
    os.close(fd)
  fd = directory(work)
  try:
    size = os.fstatvfs(fd)
    need(size.f_bavail * size.f_frsize >= protocol['resources']['reserve_bytes'] + protocol['resources']['output_total_bytes'], 'E2_RESOURCE_PREFLIGHT_BLOCKED')
    need(os.fstat(fd).st_dev != mounted[0], 'E2_OUTPUT_DEVICE_CONFLICT')
  finally:
    os.close(fd)
  return refs, roots, request, auth, jobs, environment, mounted, E1_binding, E1_envelope


def verify_reviews(gate, reviews, protocol_raw_sha256, source_sha256):
  roles = {'science-review.json': 'SCIENTIFIC_NUMERICAL_CAUSAL', 'authority-review.json': 'AUTHORITY_PRIVACY_SOURCE_INTEGRITY'}
  need(set(reviews) == set(roles), 'E2_TWO_INDEPENDENT_REVIEWS_REQUIRED')
  need(len({r['receipt_sha256'] for r in reviews.values()}) == 2 and len({r['reviewer'] for r in reviews.values()}) == 2, 'E2_DUPLICATE_REVIEWER')
  for name, role in roles.items():
    review = reviews[name]
    need(
      review['role'] == role
      and type(review['reviewer']) is str
      and bool(review['reviewer'])
      and review['approval'] == 'APPROVED'
      and review['protocol_raw_sha256'] == protocol_raw_sha256
      and review['receipt_sha256'] == gate['review_receipts'][name]
      and review['source_sha256'] == source_sha256,
      'E2_EXACT_BYTE_REVIEW_REQUIRED',
    )


def preflight(work, execute):
  head = git('rev-parse', 'HEAD')
  need(git('branch', '--show-current') == 'feature/cyber-autotune' and head == git('rev-parse', 'origin/feature/cyber-autotune'))
  need(not git('status', '--porcelain'), 'E2_CLEAN_FROZEN_SNAPSHOT_REQUIRED')
  subprocess.run(['git', 'merge-base', '--is-ancestor', BASELINE, head], check=True, cwd=ROOT)
  raw = (PUBLIC / PROTOCOL_NAME).read_bytes()
  protocol = checked(raw)
  need(protocol['version'] == 'V4_E2_D0_D1_D2_PROTOCOL_V1' and protocol['baseline_head'] == BASELINE)
  for name, pin in protocol['public_inputs'].items():
    b = (PUBLIC / name).read_bytes()
    need(sha(b) == pin['raw_sha256'] and checked(b)['receipt_sha256'] == pin['receipt_sha256'], 'E2_PUBLIC_INPUT_DRIFT')
  modules = load_exact(protocol)
  import numpy as np

  modules['empirical_hurdle_v4_e_bootstrap'].warm_dependencies()
  need(sys.version.split()[0] == '3.12.13' and np.__version__ == '2.5.3')
  need(all(os.environ.get(k) == '1' for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')))
  need(sha(canonical(np.show_config(mode='dicts'))) == protocol['environment']['blas_build_identity_sha256'])
  need(zlib.ZLIB_RUNTIME_VERSION == protocol['environment']['zlib_runtime_version'])
  need(ctypes.CDLL('libm.so.6').fegetround() == 0, 'E2_ROUND_TO_NEAREST_REQUIRED')
  values = controls(work, protocol, modules)
  refs, roots, request, auth, jobs, environment, mounted, E1_binding, E1_envelope = values
  gate = None
  if execute:
    gate = checked(private(work / 'execution-gate.json'))
    need(gate['head'] == head and gate['protocol_raw_sha256'] == sha(raw) and gate['mission'] == MISSION, 'E2_CURRENT_GRANT_BINDING')
    need(gate['control_references_raw_sha256'] == sha(private(work / 'control-references.json')))
    need(gate['ci']['head_sha'] == head and gate['ci']['status'] == 'completed' and gate['ci']['conclusion'] == 'success')
    reviews = {name: checked(private(work / name)) for name in ('science-review.json', 'authority-review.json')}
    verify_reviews(gate, reviews, sha(raw), protocol['source_sha256'])
  binding = sealed(
    {
      'schema': 'V4_E2_EXECUTION_BINDING_V1',
      'head': head,
      'baseline_head': BASELINE,
      'protocol_raw_sha256': sha(raw),
      'protocol_receipt_sha256': protocol['receipt_sha256'],
      'current_explicit_human_grant': MISSION,
      'root_identities': auth['root_identities'],
      'roots': roots,
      'prior_lineage': refs['prior_lineage'],
      'E1_canonical_raw_sha256': E1_envelope['canonical_raw_sha256'],
      'E1_head': E1_binding['head'],
      'environment': environment,
      'gate_receipt_sha256': gate['receipt_sha256'] if gate else None,
      'F_AUTHORIZED': False,
      'policy_adoption_authorized': False,
      'V5_AUTHORIZED': False,
    }
  )
  return protocol, raw, modules, binding, roots, request, auth, jobs, mounted, refs


def failure_status(exc):
  code = str(exc)
  special = ('E2_D0_TRAIN_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED', 'D2_TRAIN_FEASIBILITY_CONTRACT_UNRESOLVED', 'E2_RESOURCE_PREFLIGHT_BLOCKED')
  if code in special:
    return code
  if isinstance(exc, MemoryError):
    return 'E2_RESOURCE_PREFLIGHT_BLOCKED'
  if (
    code.startswith(('CANDIDATE_FOLD_NUMERICAL_FAILURE', 'HURDLE_NUMERICAL_FAILURE'))
    or code in ('E2_NONFINITE_LOSS', 'E2_TRAIN_POTENTIAL_CONFLICT', 'E2_TRAIN_TICK_RANGE')
    or isinstance(exc, FloatingPointError)
  ):
    return 'E2_TRAIN_NUMERICAL_FAILURE_JOB_NONPASS'
  return 'E2_INPUT_INSUFFICIENT' if isinstance(exc, FileNotFoundError) or code == 'B1_MISSING' else 'E2_INPUT_CONFLICT_FAIL_CLOSED'


def run(work, replica):
  import numpy as np

  protocol, protocol_raw, modules, binding, roots, request, auth, jobs, mounted, refs = preflight(work, True)
  inp, dec, ev = (modules['empirical_hurdle_v4_e2_' + n] for n in ('inputs', 'decision', 'evaluation'))
  oldev, olddec = modules['empirical_hurdle_v4_e_evaluation'], modules['empirical_hurdle_v4_e_decision']
  destination = work / replica
  os.mkdir(destination, 0o700)
  limit = protocol['resources']
  persist(destination, 'execution-binding.json', binding, limit['control_bytes'])
  for what, cap in (
    (resource.RLIMIT_AS, limit['address_space_bytes']),
    (resource.RLIMIT_CPU, limit['cpu_seconds_per_repeat']),
    (resource.RLIMIT_FSIZE, limit['result_bytes_per_file']),
    (resource.RLIMIT_CORE, 0),
  ):
    resource.setrlimit(what, (cap, cap))
  signal.signal(signal.SIGALRM, lambda *_args: (_ for _ in ()).throw(ValueError('E2_RESOURCE_PREFLIGHT_BLOCKED')))
  signal.alarm(limit['wall_seconds_per_repeat'])
  phase = inp.Phase()
  reader = inp.Reader(roots, '/mnt/e', mounted, phase)
  audit = modules['empirical_hurdle_v4_e_bootstrap'].RuntimeFirewall()
  sys.addaudithook(audit)
  counters, caches, D0_rows, D1_rows, train_rows, result_jobs = {}, [], [], [], [], []
  start, failed_job, stage = time.monotonic(), None, 'TRAIN_QUALIFICATION'

  def write(name, value):
    audit.writing_output = True
    try:
      return persist(destination, name, value, limit['result_bytes_per_file'])
    finally:
      audit.writing_output = False

  def forbidden(*_args, **_kwargs):
    audit.attempts += 1
    raise ValueError('E2_FORBIDDEN_SCIENTIFIC_OPERATION')

  try:
    with ExitStack() as stack:
      modules['empirical_hurdle_v4_e_bootstrap'].trap_deserialization(stack, forbidden)
      for module, names in (
        (oldev.frozen, ('train', 'select', 'run', 'synthetic_run')),
        (oldev.frozen.m, ('newton', 'normalizer', 'fit_stage1', 'fit_stage2')),
        (oldev.frozen.m.source, ('fit', 'normalizer')),
        (oldev.gates, ('select',)),
        (oldev.data, ('load_route',)),
        (np.linalg, ('solve', 'lstsq', 'pinv')),
      ):
        for name in names:
          if hasattr(module, name):
            stack.enter_context(patch.object(module, name, forbidden))
      source_policy = modules['empirical_s2_ri_policy'].policy()
      need(source_policy['receipt_sha256'] == protocol['source_policy_receipt_sha256'])
      provider = inp.Provider(
        reader,
        jobs,
        v4_manifest=request['manifests']['V4_REPEAT_1'],
        v1_manifest=request['manifests']['V1_REFERENCE'],
        v4_authorization=auth,
        v1_authorization_sha=request['authorization']['V1_REFERENCE'],
        references=public('empirical-hurdle-fit-cv-results-v1.json')['jobs'],
        job_catalog=public('empirical-hurdle-stage1-v4-job-manifest.json')['jobs'],
        source_policy=source_policy,
      )
      provider.admit_train_sources()
      for index, job in enumerate(jobs):
        candidate, fold = job['candidate_id'], job['fold']
        failed_job = {'candidate_id': candidate, 'fold': fold}
        phase.job = candidate, fold
        p, y, prior = provider.train(index)
        D0 = dec.reconstruct_D0(p, y, role='TRAIN', counters=counters)
        blocks, anchor, n = provider.train_blocks(index)
        stage2 = provider.stage2(index)
        dec.count(counters, 'frozen_Stage2_model_loading_jobs')
        _, length = oldev.frozen.m.parameters(candidate)
        cache = dec.potentials(blocks, candidate, stage2, p, y, prior, D0['value'], {'count': n, 'feature_dimension': 2 * length + 3}, counters)
        caches.append(cache)
        need(sum(a.nbytes for c in caches for a in c.values()) <= limit['TRAIN_cache_bytes'], 'E2_RESOURCE_PREFLIGHT_BLOCKED')
        D0_rows.append(D0)
        D1_rows.append(olddec.select_job(p, y, prior, candidate=candidate, fold=fold, anchor=anchor, role='TRAIN'))
        dec.count(counters, 'D1_context_decision_reproduction_calls')
        dec.count(counters, 'D1_context_decision_reproduction_calls')
        phase.qualify(candidate, fold)
        print(json.dumps({'TRAIN_qualified_jobs': index + 1, 'D2_decisions': 0, 'DEV_role_reads': 0}), flush=True)
      phase.require_selection()
      stage = 'D2_TRAIN_SELECTION'
      for index, job in enumerate(jobs):
        candidate, fold = job['candidate_id'], job['fold']
        failed_job = {'candidate_id': candidate, 'fold': fold}
        cache = caches[index]
        record = dec.select_job(cache, D0_rows[index]['value'], candidate=candidate, fold=fold, anchor=job['fields'][0]['anchor_sha256'], counters=counters)
        record['score_diagnostics'] = oldev.score_diagnostics(cache['p'], cache['y'], cache['prior'])
        train_rows.append(record)
        caches[index] = None
      del caches, cache, p, y, prior, blocks
      train = sealed(
        {
          'schema': 'V4_E2_ALL64_TRAIN_DECISIONS_V1',
          'protocol_sha256': sha(protocol_raw),
          'qualification_PASS_jobs': 32,
          'jobs': train_rows,
          'D0_reconstruction': D0_rows,
          'D1_TRAIN_reproduction': D1_rows,
        }
      )
      digest = write('train-decisions.json', train)
      readback = private(destination / 'train-decisions.json', limit['result_bytes_per_file'])
      need(checked(readback) == train)
      phase.unlock(train_rows, digest, sha(readback))
      print('E2_ALL64_TRAIN_DECISIONS_DURABLY_SEALED_DEV_CAPABILITY_ENABLED', flush=True)
      stage = 'DEV_EVALUATION'
      old_raw = private(Path(refs['references']['WORK']) / 'repeat-1/canonical-result.json', limit['result_bytes_per_file'])
      oldev.verify_only(old_raw, binding['E1_canonical_raw_sha256'], protocol['E1_protocol_raw_sha256'], head=binding['E1_head'])
      old = checked(old_raw)
      need(old['prior_lineage'] == binding['prior_lineage'])
      comparison_read = {'files': 1, 'bytes': len(old_raw)}
      del old_raw
      dev = public('empirical-hurdle-stage1-v4-development-results.json')['jobs']
      roll = public('empirical-hurdle-stage1-v4-rollout-results.json')['jobs']
      clauses = public('empirical-hurdle-acceptance-gate-v1.json')['clauses']
      for index, job in enumerate(jobs):
        candidate, fold = job['candidate_id'], job['fold']
        failed_job = {'candidate_id': candidate, 'fold': fold}
        reference = old['jobs'][index]
        need(
          D1_rows[index]['contexts'] == reference['TRAIN']['contexts'] and D1_rows[index]['anchor_sha256'] == reference['TRAIN']['anchor_sha256'],
          'E2_D1_TRAIN_IDENTITY_CONFLICT',
        )
        model, stage2 = provider.models(index)
        dec.count(counters, 'frozen_Stage1_model_loading_jobs')
        segments = provider.route(provider.references[index]['development_route'], candidate)
        decisions = tuple(train_rows[index]['contexts'][k]['decision'] for k in dec.CONTEXTS)
        row = ev.evaluate_job(
          segments, candidate, fold, model, decisions, stage2, provider, {**dev[index], 'rollout': roll[index]['rollout']}, reference, clauses, counters
        )
        row['TRAIN'] = train_rows[index]
        row['TRAIN_to_DEV'] = oldev.score_transfer(train_rows[index]['score_diagnostics'], row['arms']['D2']['score_diagnostics'])
        result_jobs.append(row)
        print(json.dumps({'E2_completed_jobs': index + 1, 'D2_gate_pass': row['arms']['D2']['gate']['pass']}), flush=True)
      need(not audit.attempts and len(result_jobs) == 32)
      payload = sealed(
        {
          'schema': 'V4_E2_CANONICAL_RESULT_V1',
          'head': binding['head'],
          'protocol_sha256': sha(protocol_raw),
          'prior_lineage': binding['prior_lineage'],
          'E1_canonical_raw_sha256': binding['E1_canonical_raw_sha256'],
          'TRAIN_seal_sha256': digest,
          'jobs': result_jobs,
          'operation_counters': counters,
          'input_reads': reader.summary(),
          'comparison_result_reads': comparison_read,
          'forbidden_operation_counters': dict.fromkeys(ev.FORBIDDEN, 0),
          'mixed_carrier_openings': 0,
          'original_D0_threshold_readings': 0,
          'selected_candidate': None,
          'selected_policy': None,
          'holdout': 'CLOSED',
          'vehicle_authority': 'NONE',
          'original_TRAIN_gate': 'NOT_SAVED',
          'original_replica': 'REPLICA_PAYLOAD_EQUALITY_NOT_FULLY_REVERIFIED',
        }
      )
      ev.validate_stored(payload, sha(protocol_raw), head=binding['head'])
      digest = write('canonical-result.json', payload)
      write(
        'execution-envelope.json',
        sealed(
          {
            'schema': 'V4_E2_EXECUTION_ENVELOPE_V1',
            'replica': replica,
            'canonical_raw_sha256': digest,
            'binding_receipt_sha256': binding['receipt_sha256'],
            'input_events': reader.events,
            'control_events': CONTROL_EVENTS,
            'wall_seconds': time.monotonic() - start,
            'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'forbidden_attempts': audit.attempts,
            'source_writes': 0,
          }
        ),
      )
      print(json.dumps({'status': 'E2_REPEAT_COMPLETE', 'completed_jobs': 32, 'input_reads': reader.summary(), 'source_writes': 0}), flush=True)
  except Exception as exc:
    code = str(exc) if re.fullmatch('[A-Z0-9_]+', str(exc)) else 'E2_FIXED_INPUT_OR_IMPLEMENTATION_FAILURE'
    status = failure_status(exc)
    write(
      'execution-envelope.json',
      sealed(
        {
          'schema': 'V4_E2_ABORT_ENVELOPE_V1',
          'status': status,
          'failure': code,
          'exception_type': type(exc).__name__,
          'stage': stage,
          'failed_job': failed_job,
          'completed_jobs': len(result_jobs),
          'qualified_TRAIN_jobs': len(phase.qualified),
          'operation_counters': counters,
          'input_events': reader.events,
          'input_reads': reader.summary(),
          'control_events': CONTROL_EVENTS,
          'forbidden_attempts': audit.attempts,
          'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'source_writes': 0,
        }
      ),
    )
    print(
      json.dumps(
        {
          'status': status,
          'failure': code,
          'qualified_TRAIN_jobs': len(phase.qualified),
          'completed_jobs': len(result_jobs),
          'D2_decisions': counters.get('D2_context_decision_selection_calls', 0),
          'input_reads': reader.summary(),
          'source_writes': 0,
        }
      ),
      flush=True,
    )
    raise SystemExit(1) from None
  finally:
    audit.active = False
    signal.alarm(0)


def stored(work, replica):
  raw_protocol = (PUBLIC / PROTOCOL_NAME).read_bytes()
  protocol = checked(raw_protocol)
  modules = load_exact(protocol)
  ev = modules['empirical_hurdle_v4_e2_evaluation']
  folder = work / replica
  envelope = checked(private(folder / 'execution-envelope.json', protocol['resources']['result_bytes_per_file']))
  need(envelope['schema'] == 'V4_E2_EXECUTION_ENVELOPE_V1' and envelope['replica'] == replica and envelope['forbidden_attempts'] == 0)
  binding = checked(private(folder / 'execution-binding.json'))
  need(envelope['binding_receipt_sha256'] == binding['receipt_sha256'] and binding['protocol_raw_sha256'] == sha(raw_protocol))
  raw = private(folder / 'canonical-result.json', protocol['resources']['result_bytes_per_file'])
  result = ev.verify_only(raw, envelope['canonical_raw_sha256'], sha(raw_protocol), head=binding['head'])
  train = checked(private(folder / 'train-decisions.json', protocol['resources']['result_bytes_per_file']))
  need(sha(canonical(train)) == checked(raw)['TRAIN_seal_sha256'])
  need(train['qualification_PASS_jobs'] == 32 and len(train['jobs']) == 32)
  need(train['jobs'] == [r['TRAIN'] for r in checked(raw)['jobs']], 'E2_DURABLE_TRAIN_CANONICAL_LINK')
  need(train['protocol_sha256'] == sha(raw_protocol))
  return protocol, modules, folder, raw, result


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('mode', choices=('prepare', 'execute', 'verify-only', 'compare'))
  parser.add_argument('--work', required=True)
  parser.add_argument('--repeat', choices=('repeat-1', 'repeat-2'))
  args = parser.parse_args()
  work = Path(args.work)
  need(work.is_absolute() and '..' not in work.parts)
  if args.mode == 'prepare':
    preflight(work, False)
    print('E2_CONTROL_PREFLIGHT_PASS_NO_SCIENTIFIC_INPUT_OPEN')
  elif args.mode == 'execute':
    need(args.repeat is not None)
    run(work, args.repeat)
  elif args.mode == 'verify-only':
    need(args.repeat is not None)
    protocol, _, folder, _, result = stored(work, args.repeat)
    persist(folder, 'verify-only-resume.json', sealed(result), protocol['resources']['control_bytes'])
    print(json.dumps(result), flush=True)
  else:
    protocol, modules, _, first, _ = stored(work, 'repeat-1')
    _, _, _, second, _ = stored(work, 'repeat-2')
    need(first == second, 'E2_REPEATABILITY_FAILED')
    projection = modules['empirical_hurdle_v4_e2_publication'].project(checked(first))
    record = sealed(
      {
        'schema': 'V4_E2_REPEATABILITY_V1',
        'status': 'E2_BYTE_EXACT_REPEATABILITY_PASS',
        'canonical_raw_sha256': sha(first),
        'public_projection': projection,
        'source_rereads': 0,
        'inference_calls': 0,
        'recompute_calls': 0,
        'source_writes': 0,
      }
    )
    persist(work, 'repeatability-receipt.json', record, protocol['resources']['result_bytes_per_file'])
    print(json.dumps({'repeatability': record['status'], 'status': projection['status']}))


if __name__ == '__main__':
  try:
    main()
  except Exception as exc:
    code = str(exc) if re.fullmatch('[A-Z0-9_]+', str(exc)) else 'E2_CONTROL_OR_ENVIRONMENT_FAILURE'
    print(json.dumps({'status': failure_status(exc), 'code': code, 'exception_type': type(exc).__name__}), flush=True)
    raise SystemExit(1) from None
