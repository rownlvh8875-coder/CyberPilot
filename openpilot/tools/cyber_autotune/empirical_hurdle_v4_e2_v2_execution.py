"""Fresh additive E2 V2 caller. Never calls/patches the V1 runner or potentials.

Old controls authenticate historical identity only. A new explicit V2 grant,
exact-byte reviews and successful pre-execution CI are required before controls
or original numeric input are opened. No discovery or resumed scientific run.
"""
import argparse
from contextlib import ExitStack
import ctypes
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time
import types
from unittest.mock import patch
import zlib

from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_execution as legacy

need, sha, canonical, sealed, checked = legacy.need, legacy.sha, legacy.canonical, legacy.sealed, legacy.checked
ROOT, SOURCE, PUBLIC = legacy.ROOT, legacy.SOURCE, legacy.PUBLIC
BASELINE = '63f74c22d2c30978bf51dc7c00fca3eb423e45c1'
MISSION = 'STAGE1_V4_E2_V2_ADDITIVE_RUNNER_AND_FRESH_EXECUTION'
PROTOCOL = 'empirical-hurdle-stage1-v4-e2-execution-protocol-v2.json'
LOCK = 'empirical-hurdle-stage1-v4-e2-v2-implementation-lock.json'
PROTOCOL_SHA = '7a4e02966d921759430a4b6c3c9ca1f343f400a293e4f79f1a9a73fb8aaeeb2f'
AMENDMENT_SHA = '7a51775da2ec0edd18c21abf73d78123f940cff3c8e125ddac0cd43857427ccf'
FORBIDDEN = ('stage1_refit', 'stage2_refit', 'normalizer_refit', 'calibration_fit', 'new_policy_arm', 'additional_policy_search',
             'posthoc_threshold_tuning', 'guard_relaxation', 'candidate_grid_change', 'extra_tolerance', 'rebatching_retry',
             'original_source_writes', 'raw_log_openings', 'qlog_openings', 'holdout_discovery', 'holdout_openings',
             'controller_changes', 'vehicle_activation', 'pooled_refit', 'composition', 'V5_execution')


def public_locks():
  raw = (PUBLIC / PROTOCOL).read_bytes()
  need(sha(raw) == PROTOCOL_SHA, 'E2_V2_PROTOCOL_DRIFT')
  p = checked(raw)
  need(p['version'] == 'V4_E2_D0_D1_D2_PROTOCOL_V2' and p['baseline_head'] == '93bc9db25565bcd8b6bd988550c4488ad1c42500')
  amendment = (PUBLIC / p['qualification_amendment']['file']).read_bytes()
  need(sha(amendment) == AMENDMENT_SHA == p['qualification_amendment']['raw_sha256'])
  need(checked(amendment)['receipt_sha256'] == p['qualification_amendment']['receipt_sha256'])
  lock_raw = (PUBLIC / LOCK).read_bytes()
  lock = checked(lock_raw)
  need(lock['protocol_raw_sha256'] == PROTOCOL_SHA and lock['baseline_head'] == BASELINE)
  for name, pin in p['public_inputs'].items():
    value = (PUBLIC / name).read_bytes()
    need(sha(value) == pin['raw_sha256'] and checked(value)['receipt_sha256'] == pin['receipt_sha256'], 'E2_PUBLIC_INPUT_DRIFT')
  buffers = {name: (SOURCE / name).read_bytes() for name in lock['additive_source_sha256']}
  for name, digest in lock['additive_source_sha256'].items():
    need(sha(buffers[name]) == digest, 'E2_V2_ADDITIVE_SOURCE_DRIFT')
  for name, digest in p['source_sha256'].items():
    need(sha((SOURCE / name).read_bytes()) == digest, 'E2_SOURCE_DRIFT')
  return p, raw, lock, lock_raw, buffers


def frozen_sources():
  p, raw, lock, lock_raw, buffers = public_locks()
  modules = legacy.load_exact(p)
  import openpilot.tools.cyber_autotune as package
  name = 'empirical_hurdle_v4_e2_v2_qualification'
  module = types.ModuleType(package.__name__ + '.' + name)
  module.__file__, module.__package__ = str(SOURCE / (name + '.py')), package.__name__
  sys.modules[module.__name__] = module
  setattr(package, name, module)
  exec(compile(buffers[name + '.py'], module.__file__, 'exec'), module.__dict__)
  modules[name] = module
  return p, raw, lock, lock_raw, modules



def verify_reviews(gate, reviews, protocol_sha, sources, lock_sha):
  legacy.verify_reviews(gate, reviews, protocol_sha, sources)
  need(all(r.get('implementation_lock_raw_sha256') == lock_sha for r in reviews.values()), 'E2_V2_REVIEW_LOCK_BINDING')


def validate_binding(binding, protocol, lock, lock_raw):
  need(binding['schema'] == 'V4_E2_V2_FRESH_BINDING_V1' and binding['baseline_head'] == BASELINE
       and binding['protocol_raw_sha256'] == PROTOCOL_SHA and binding['protocol_receipt_sha256'] == protocol['receipt_sha256']
       and binding['implementation_lock_raw_sha256'] == sha(lock_raw)
       and binding['source_sha256'] == {**protocol['source_sha256'], **lock['additive_source_sha256']}
       and binding['current_explicit_human_grant'] == MISSION
       and all(binding.get(k) is False for k in ('F_AUTHORIZED', 'policy_adoption_authorized', 'V5_AUTHORIZED'))
       and re.fullmatch('[0-9a-f]{40}', binding['head']), 'E2_V2_STORED_BINDING_CONFLICT')


def validate_proof(proof, kind, job, expected_identity):
  need(set(proof) == {'kind', 'job', 'identity', 'dtype', 'Q2', 'status', 'nonempty', 'numerical_calls'}, 'E2_V2_PROOF_SCHEMA')
  need(proof['kind'] == kind and proof['job'] == list(job) and proof['identity'] == expected_identity
       and proof['dtype'] == '<f8' and proof['Q2'] == 'NOT_EXECUTED_DIAGNOSTIC', 'E2_V2_PROOF_BINDING')
  need(type(proof['nonempty']) is bool and type(proof['numerical_calls']) is int, 'E2_V2_PROOF_TYPES')
  need((proof['status'], proof['nonempty'], proof['numerical_calls']) in (
    ('BYTE_EXACT_PASS', True, 1), ('VERIFIED_EMPTY_GATE_ORIGINAL_INTEGRATED_NOOP', False, 0)), 'E2_V2_PROOF_SEMANTICS')


def resource_plan(protocol):
  r, review = protocol['resources'], protocol['resource_review']
  need((r['TRAIN_DEV_row_upper_bound'], r['features_max'], r['chunk_rows'], r['threads'], r['jobs_parallel']) == (336941, 93, 512, 1, 1))
  need(r['address_space_bytes'] == 8 * 1024**3 and r['cpu_seconds_per_repeat'] == 21600 and r['wall_seconds_per_repeat'] == 43200)
  n, p = r['TRAIN_DEV_row_upper_bound'], r['features_max']
  matrix = 8 * n * p * 8
  comparison = 32 * n
  receipt = 64 * 4096
  total = 1410679894 + matrix + comparison + receipt + 2 * 1024**3
  need(total == r['peak_live_buffer_bound_bytes'] == 5574680630 and total < r['address_space_bytes'], 'E2_RESOURCE_PREFLIGHT_BLOCKED')
  need(review['qualification_matrix_workspace_bytes'] == matrix and review['comparison_vector_workspace_bytes'] == comparison)
  return {'analytical_live_bound_bytes': total, 'matrix_bytes': matrix, 'comparison_bytes': comparison,
          'proof_bytes': receipt, 'native_runtime_reserve_bytes': 2 * 1024**3,
          'input_rereads_for_Q1_Q3': 0, 'Q1_calls_max': 32, 'Q3_calls_max': 32, 'Q2_calls': 0}

def preflight(work):
  head = legacy.git('rev-parse', 'HEAD')
  need(legacy.git('branch', '--show-current') == 'feature/cyber-autotune' and head == legacy.git('rev-parse', 'origin/feature/cyber-autotune'))
  need(not legacy.git('status', '--porcelain'), 'E2_CLEAN_FROZEN_SNAPSHOT_REQUIRED')
  import subprocess
  subprocess.run(['git', 'merge-base', '--is-ancestor', BASELINE, head], check=True, cwd=ROOT)
  p, raw, lock, lock_raw, modules = frozen_sources()
  plan = resource_plan(p)
  gate = checked(legacy.private(work / 'execution-gate.json'))
  need(gate['head'] == head and gate['mission'] == MISSION and gate['protocol_raw_sha256'] == sha(raw)
       and gate['implementation_lock_raw_sha256'] == sha(lock_raw), 'E2_V2_CURRENT_GRANT_BINDING')
  need(gate['ci']['head_sha'] == head and gate['ci']['status'] == 'completed' and gate['ci']['conclusion'] == 'success')
  combined = {**p['source_sha256'], **lock['additive_source_sha256']}
  reviews = {name: checked(legacy.private(work / name)) for name in ('science-review.json', 'authority-review.json')}
  verify_reviews(gate, reviews, sha(raw), combined, sha(lock_raw))
  # No old grant can satisfy the new gate above. Historical receipts are read only afterwards.
  historical = Path(gate['historical_control_root'])
  old_gate = checked(legacy.private(historical / 'execution-gate.json'))
  old_binding = checked(legacy.private(historical / 'repeat-1/execution-binding.json'))
  old_abort = checked(legacy.private(historical / 'repeat-1/execution-envelope.json'))
  old_refs_raw = legacy.private(historical / 'control-references.json')
  need(old_gate['control_references_raw_sha256'] == sha(old_refs_raw)
       and old_binding['gate_receipt_sha256'] == old_gate['receipt_sha256']
       and old_binding['head'] == old_gate['head']
       and old_binding['protocol_raw_sha256'] == p['V1_lineage']['raw_sha256']
       and old_abort['status'] == p['V1_lineage']['historical_failure'], 'E2_V2_HISTORICAL_IDENTITY_CONFLICT')
  import numpy as np
  modules['empirical_hurdle_v4_e_bootstrap'].warm_dependencies()
  need(sys.version.split()[0] == p['environment']['python'] and np.__version__ == p['environment']['numpy'])
  need(all(os.environ.get(k) == '1' for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')))
  need(sha(canonical(np.show_config(mode='dicts'))) == p['environment']['blas_build_identity_sha256'])
  need(zlib.ZLIB_RUNTIME_VERSION == p['environment']['zlib_runtime_version'] and ctypes.CDLL('libm.so.6').fegetround() == 0)
  refs, roots, request, auth, jobs, environment, mounted, E1_binding, E1_envelope = legacy.controls(historical, p, modules)
  q = modules['empirical_hurdle_v4_e2_v2_qualification']
  need(tuple((j['candidate_id'], j['fold']) for j in jobs) == q.JOBS)
  for value in roots.values():
    need(not work.is_relative_to(Path(value)) and not Path(value).is_relative_to(work), 'E2_SOURCE_OUTPUT_OVERLAP')
  need(work != historical and not work.is_relative_to(historical) and not historical.is_relative_to(work), 'E2_V2_FRESH_OUTPUT_REQUIRED')
  fd = legacy.directory(work)
  try:
    size = os.fstatvfs(fd)
    need(size.f_bavail * size.f_frsize >= p['resources']['reserve_bytes'] + p['resources']['output_total_bytes'], 'E2_RESOURCE_PREFLIGHT_BLOCKED')
    need(os.fstat(fd).st_dev != mounted[0], 'E2_OUTPUT_DEVICE_CONFLICT')
  finally:
    os.close(fd)
  # Interpreter/native baseline must fit the frozen2GiB reserve before any numeric input.
  memory = int(Path('/proc/self/statm').read_text().split()[0]) * os.sysconf('SC_PAGE_SIZE')
  need(memory <= p['resource_review']['runtime_reserve_bytes'], 'E2_RESOURCE_PREFLIGHT_BLOCKED')
  binding = sealed({'schema': 'V4_E2_V2_FRESH_BINDING_V1', 'head': head, 'baseline_head': BASELINE,
    'protocol_raw_sha256': sha(raw), 'protocol_receipt_sha256': p['receipt_sha256'],
    'implementation_lock_raw_sha256': sha(lock_raw), 'source_sha256': combined,
    'current_explicit_human_grant': MISSION, 'gate_receipt_sha256': gate['receipt_sha256'],
    'historical_control_raw_sha256': sha(old_refs_raw), 'historical_V1_abort_receipt_sha256': old_abort['receipt_sha256'],
    'roots': roots, 'root_identities': auth['root_identities'], 'prior_lineage': refs['prior_lineage'],
    'E1_canonical_raw_sha256': E1_envelope['canonical_raw_sha256'], 'E1_head': E1_binding['head'],
    'environment': environment, 'preflight_virtual_bytes': memory, 'resource_contract': p['resources'],
    'resource_liveness': plan, 'input_scope': p['input_scope'], 'F_AUTHORIZED': False, 'policy_adoption_authorized': False, 'V5_AUTHORIZED': False})
  return p, raw, modules, binding, roots, request, auth, jobs, mounted, refs


def failure_status(exc):
  if str(exc) == 'E2_D2_TRAIN_SELECTED_PATH_NUMERICAL_EQUIVALENCE_NOT_PROVEN_FAIL_CLOSED':
    return str(exc)
  return legacy.failure_status(exc)


def train(provider, phase, dec, q, oldev, olddec, jobs, counters, limit, source_map_sha):
  """All32 B/C/D, then all64 E, then all32 F. No output or DEV here."""
  caches, d0s, d1s, records = [], [], [], []
  phase.begin()
  for index, job in enumerate(jobs):
    candidate, fold = job['candidate_id'], job['fold']
    phase.job = candidate, fold
    p, y, prior = provider.train(index)
    d0s.append(dec.reconstruct_D0(p, y, role='TRAIN', counters=counters))
    caches.append({'p': p, 'y': y, 'prior': prior})
    phase.complete('D0', phase.job)
  phase.advance('POTENTIALS')
  for index, job in enumerate(jobs):
    candidate, fold = job['candidate_id'], job['fold']
    phase.job = candidate, fold
    blocks, anchor, n = provider.train_blocks(index)
    stage2 = provider.stage2(index)
    dec.count(counters, 'frozen_Stage2_model_loading_jobs')
    values = caches[index]
    need(n == len(values['p']))
    caches[index] = q.potentials(blocks, candidate, stage2, values['p'], values['y'], values['prior'], d0s[index]['value'], counters)
    phase.complete('POTENTIALS', phase.job)
    need(sum(a.nbytes for c in caches for a in c.values()) <= limit['TRAIN_cache_bytes'], 'E2_RESOURCE_PREFLIGHT_BLOCKED')
  del values, p, y, prior
  phase.advance('Q1')
  def identity(index, anchor):
    receipts = provider.references[index]['stage2']
    model_keys = ('normalizer_receipt_sha256', 'model_receipt_sha256', 'coefficient_sha256')
    return {'job': list(q.JOBS[index]), 'anchor_sha256': anchor,
            'stage2_receipts': {k: receipts[k] for k in model_keys}, 'source_map_sha256': source_map_sha}
  for index, job in enumerate(jobs):
    phase.job = q.JOBS[index]
    blocks, anchor, _ = provider.train_blocks(index)
    proof = q.qualification('Q1', blocks, job['candidate_id'], provider.stage2_cache[index], caches[index], caches[index]['D0_gate'],
                            identity(index, anchor), counters)
    phase.record_qualification(phase.job, proof)
    dec.count(counters, 'TRAIN_numerical_qualification_jobs')
  phase.advance('SELECTION')
  for index, job in enumerate(jobs):
    phase.job = q.JOBS[index]
    cache = caches[index]
    anchor = job['fields'][0]['anchor_sha256']
    d1s.append(olddec.select_job(cache['p'], cache['y'], cache['prior'], candidate=phase.job[0], fold=phase.job[1], anchor=anchor, role='TRAIN'))
    dec.count(counters, 'D1_context_decision_reproduction_calls')
    dec.count(counters, 'D1_context_decision_reproduction_calls')
    row = dec.select_job(cache, d0s[index]['value'], candidate=phase.job[0], fold=phase.job[1], anchor=anchor, counters=counters)
    row['new_D0_gate'] = 'NEW_E2_V2_RECONSTRUCTED_D0_TRAIN_REFERENCE'
    row['score_diagnostics'] = oldev.score_diagnostics(cache['p'], cache['y'], cache['prior'])
    records.append(row)
  del cache
  phase.finish_selection(records)
  for index, job in enumerate(jobs):
    phase.job = q.JOBS[index]
    cache = caches[index]
    blocks, anchor, _ = provider.train_blocks(index)
    proof = q.qualification('Q3', blocks, job['candidate_id'], provider.stage2_cache[index], cache, q.d2_gate(cache, records[index]),
                            identity(index, anchor), counters)
    phase.record_qualification(phase.job, proof)
  return records, d0s, d1s


private, persist, public = legacy.private, legacy.persist, legacy.public


def run(work, replica):
  import numpy as np

  protocol, protocol_raw, modules, binding, roots, request, auth, jobs, mounted, refs = preflight(work)
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
  q = modules['empirical_hurdle_v4_e2_v2_qualification']
  phase = q.Phase()
  reader = inp.Reader(roots, '/mnt/e', mounted, phase)
  audit = modules['empirical_hurdle_v4_e_bootstrap'].RuntimeFirewall()
  sys.addaudithook(audit)
  counters, train_rows, result_jobs = {}, [], []
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
        (dec, ('potentials',)),
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
      stage = 'TRAIN_GLOBAL_BARRIERS'
      train_rows, D0_rows, D1_rows = train(provider, phase, dec, q, oldev, olddec, jobs, counters, limit,
                                         sha(canonical(protocol['source_sha256'])))
      train_seal = sealed(
        {
          'schema': 'V4_E2_V2_ALL64_TRAIN_DECISIONS_V1',
          'protocol_sha256': sha(protocol_raw),
          'qualification_PASS_jobs': 32,
          'Q3_PASS_jobs': 32,
          'qualification_proofs': phase.proofs,
          'Q2': 'NOT_EXECUTED_DIAGNOSTIC',
          'jobs': train_rows,
          'D0_reconstruction': D0_rows,
          'D1_TRAIN_reproduction': D1_rows,
        }
      )
      digest = write('train-decisions.json', train_seal)
      readback = private(destination / 'train-decisions.json', limit['result_bytes_per_file'])
      need(checked(readback) == train_seal)
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
        print(json.dumps({'E2_V2_completed_jobs': index + 1}), flush=True)
      need(not audit.attempts and len(result_jobs) == 32)
      payload = sealed(
        {
          'schema': 'V4_E2_CANONICAL_RESULT_V1',
          'head': binding['head'],
          'execution_version': 'V2',
          'V2_forbidden_operation_counters': dict.fromkeys(FORBIDDEN, 0),
          'protocol_sha256': sha(protocol_raw),
          'prior_lineage': binding['prior_lineage'],
          'E1_canonical_raw_sha256': binding['E1_canonical_raw_sha256'],
          'TRAIN_seal_sha256': digest,
          'jobs': result_jobs,
          'operation_counters': counters,
          'V2_qualification': {'Q1_jobs': len(phase.qualified), 'Q3_jobs': len(phase.Q3_jobs), 'decisions': phase.decisions,
                               'Q2': 'NOT_EXECUTED_DIAGNOSTIC', 'Q2_private_calls': 0},
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
            'schema': 'V4_E2_V2_EXECUTION_ENVELOPE_V1',
            'replica': replica,
            'canonical_raw_sha256': digest,
            'binding_receipt_sha256': binding['receipt_sha256'],
            'input_events': reader.events,
            'control_events': legacy.CONTROL_EVENTS,
            'wall_seconds': time.monotonic() - start,
            'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'cpu_seconds': resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime,
            'forbidden_attempts': audit.attempts,
            'source_writes': 0,
          }
        ),
      )
      print(json.dumps({'status': 'E2_V2_REPEAT_COMPLETE', 'completed_jobs': 32, 'source_writes': 0}), flush=True)
  except Exception as exc:
    code = str(exc) if re.fullmatch('[A-Z0-9_]+', str(exc)) else 'E2_FIXED_INPUT_OR_IMPLEMENTATION_FAILURE'
    status = failure_status(exc)
    write(
      'execution-envelope.json',
      sealed(
        {
          'schema': 'V4_E2_V2_ABORT_ENVELOPE_V1',
          'binding_receipt_sha256': binding['receipt_sha256'],
          'protocol_raw_sha256': sha(protocol_raw),
          'status': status,
          'failure': code,
          'exception_type': type(exc).__name__,
          'stage': phase.stage if stage == 'TRAIN_GLOBAL_BARRIERS' else stage,
          'failed_job': list(phase.job) if stage == 'TRAIN_GLOBAL_BARRIERS' else failed_job,
          'last_qualification_attempt': getattr(phase, 'last_proof', None),
          'V2_forbidden_operation_counters': dict.fromkeys(FORBIDDEN, 0),
          'completed_jobs': len(result_jobs),
          'qualified_TRAIN_jobs': len(phase.qualified),
          'operation_counters': counters,
          'V2_qualification': {'Q1_jobs': len(phase.qualified), 'Q3_jobs': len(phase.Q3_jobs), 'decisions': phase.decisions,
                               'Q2': 'NOT_EXECUTED_DIAGNOSTIC', 'Q2_private_calls': 0},
          'input_events': reader.events,
          'input_reads': reader.summary(),
          'control_events': legacy.CONTROL_EVENTS,
          'forbidden_attempts': audit.attempts,
          'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'cpu_seconds': resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime,
          'source_writes': 0,
        }
      ),
    )
    print(json.dumps({'status': status, 'stage': phase.stage if stage == 'TRAIN_GLOBAL_BARRIERS' else stage,
                      'Q1_qualified_jobs': len(phase.qualified), 'Q3_qualified_jobs': len(phase.Q3_jobs),
                      'D2_decisions': counters.get('D2_context_decision_selection_calls', 0),
                      'completed_jobs': len(result_jobs), 'DEV_access': phase.train_sha256 is not None,
                      'source_writes': 0}), flush=True)
    raise SystemExit(1) from None
  finally:
    audit.active = False
    signal.alarm(0)



def stored(work, replica):
  import importlib
  ev = importlib.import_module('openpilot.tools.cyber_autotune.empirical_hurdle_v4_e2_evaluation')
  protocol, _, lock, lock_raw, _ = public_locks()
  folder = work / replica
  envelope = checked(private(folder / 'execution-envelope.json', protocol['resources']['result_bytes_per_file']))
  need(envelope['schema'] == 'V4_E2_V2_EXECUTION_ENVELOPE_V1' and envelope['replica'] == replica
       and type(envelope['forbidden_attempts']) is int and envelope['forbidden_attempts'] == 0
       and type(envelope['source_writes']) is int and envelope['source_writes'] == 0)
  binding = checked(private(folder / 'execution-binding.json'))
  validate_binding(binding, protocol, lock, lock_raw)
  need(envelope['binding_receipt_sha256'] == binding['receipt_sha256'])
  raw = private(folder / 'canonical-result.json', protocol['resources']['result_bytes_per_file'])
  result = ev.verify_only(raw, envelope['canonical_raw_sha256'], PROTOCOL_SHA, head=binding['head'])
  value = checked(raw)
  need(value['execution_version'] == 'V2' and value['V2_qualification'] == {
    'Q1_jobs': 32, 'Q3_jobs': 32, 'decisions': 64, 'Q2': 'NOT_EXECUTED_DIAGNOSTIC', 'Q2_private_calls': 0})
  need(set(value['V2_forbidden_operation_counters']) == set(FORBIDDEN)
       and all(type(v) is int and v == 0 for v in value['V2_forbidden_operation_counters'].values()))
  train_seal = checked(private(folder / 'train-decisions.json', protocol['resources']['result_bytes_per_file']))
  need(sha(canonical(train_seal)) == value['TRAIN_seal_sha256'] and train_seal['protocol_sha256'] == PROTOCOL_SHA)
  need(train_seal['schema'] == 'V4_E2_V2_ALL64_TRAIN_DECISIONS_V1' and train_seal['Q2'] == 'NOT_EXECUTED_DIAGNOSTIC')
  need(train_seal['jobs'] == [r['TRAIN'] for r in value['jobs']]
       and all(type(train_seal[k]) is int and train_seal[k] == 32 for k in ('qualification_PASS_jobs', 'Q3_PASS_jobs')))
  need(set(train_seal['qualification_proofs']) == {'Q1', 'Q3'})
  references = public('empirical-hurdle-fit-cv-results-v1.json')['jobs']
  need(len(train_seal['D0_reconstruction']) == len(train_seal['D1_TRAIN_reproduction']) == 32)
  for kind in ('Q1', 'Q3'):
    proofs = train_seal['qualification_proofs'][kind]
    need(type(proofs) is list and len(proofs) == 32)
    for index, (proof, job, reference) in enumerate(zip(proofs, protocol['jobs'], references, strict=True)):
      pair = [job['candidate_id'], job['fold']]
      need(pair == [reference['candidate_id'], reference['fold']])
      row = train_seal['jobs'][index]
      need(row['anchor_sha256'] == reference['train_anchor_sha256'] and row['count'] == reference['train_count'])
      expected = {'job': pair, 'anchor_sha256': row['anchor_sha256'],
                  'stage2_receipts': {k: reference['stage2'][k] for k in ('normalizer_receipt_sha256', 'model_receipt_sha256', 'coefficient_sha256')},
                  'source_map_sha256': sha(canonical(protocol['source_sha256']))}
      validate_proof(proof, kind, pair, expected)
  return protocol, folder, raw, result


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('mode', choices=('execute', 'verify-only', 'compare', 'verify-abort'))
  parser.add_argument('--work', required=True)
  parser.add_argument('--repeat', choices=('repeat-1', 'repeat-2'))
  args = parser.parse_args()
  work = Path(args.work)
  need(work.is_absolute() and '..' not in work.parts)
  if args.mode == 'execute':
    need(args.repeat is not None)
    if args.repeat == 'repeat-2':
      # No second scientific attempt follows an aborted/partial first repeat.
      stored(work, 'repeat-1')
    run(work, args.repeat)
  elif args.mode == 'verify-only':
    need(args.repeat is not None)
    protocol, folder, _, result = stored(work, args.repeat)
    persist(folder, 'verify-only-resume.json', sealed(result), protocol['resources']['control_bytes'])
    print(json.dumps(result), flush=True)
  elif args.mode == 'verify-abort':
    need(args.repeat is not None)
    protocol, _, lock, lock_raw, _ = public_locks()
    binding = checked(private(work / args.repeat / 'execution-binding.json'))
    validate_binding(binding, protocol, lock, lock_raw)
    record = checked(private(work / args.repeat / 'execution-envelope.json'))
    need(binding['protocol_raw_sha256'] == PROTOCOL_SHA and record['schema'] == 'V4_E2_V2_ABORT_ENVELOPE_V1'
         and record['binding_receipt_sha256'] == binding['receipt_sha256']
         and record['protocol_raw_sha256'] == PROTOCOL_SHA
         and record['source_writes'] == record['forbidden_attempts'] == 0)
    # This is an abort receipt check, never a complete result or repeatability proof.
    print(json.dumps({'status': 'E2_V2_ABORT_RECEIPT_VERIFIED', 'source_rereads': 0, 'inference_calls': 0,
                      'recompute_calls': 0, 'source_writes': 0}), flush=True)
  else:
    protocol, _, a, _ = stored(work, 'repeat-1')
    _, _, b, _ = stored(work, 'repeat-2')
    need(a == b, 'E2_REPEATABILITY_FAILED')
    from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_publication as publication
    projection = publication.project(checked(a))
    record = sealed({'schema': 'V4_E2_V2_REPEATABILITY_V1', 'status': 'E2_BYTE_EXACT_REPEATABILITY_PASS',
                     'canonical_raw_sha256': sha(a), 'public_projection': projection,
                     'source_rereads': 0, 'inference_calls': 0, 'recompute_calls': 0, 'source_writes': 0})
    persist(work, 'repeatability-receipt.json', record, protocol['resources']['result_bytes_per_file'])
    print(json.dumps({'repeatability': record['status'], 'status': projection['status']}))


if __name__ == '__main__':
  try:
    main()
  except Exception as exc:
    code = str(exc) if re.fullmatch('[A-Z0-9_]+', str(exc)) else 'E2_V2_CONTROL_OR_ENVIRONMENT_FAILURE'
    print(json.dumps({'status': failure_status(exc), 'code': code, 'exception_type': type(exc).__name__}), flush=True)
    raise SystemExit(1) from None
