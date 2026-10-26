"""One fresh TRAIN-only diagnostic, separately authorized; not an E2 resume.

No filesystem discovery. Existing controls supply exact private references.
New exact-byte reviews/CI/grant bind this caller and its diagnostic protocol.
The old E2 controller is reused only for read-only control authentication.
"""
import argparse
from contextlib import ExitStack
import ctypes
import json
import os
from pathlib import Path
import resource
import signal
import sys
from unittest.mock import patch

import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_execution as control
from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_numerical_diagnostic as diagnostic

MISSION = 'STAGE1_V4_E2_STAGE2_NUMERICAL_EQUIVALENCE_ROOT_CAUSE'
BASELINE = '7adba76d5b1400f35fbd03c420e5f331cf0c7272'
PROTOCOL = 'empirical-hurdle-stage1-v4-e2-numerical-diagnostic-protocol.json'
JOB = ('HRI_D00_L01', 'FOLD_B')
INDEX = 1
need = control.need


class Phase:
  """Metadata bootstraps plus one exact job; source members bind named route."""
  def __init__(self):
    self.job, self.train_sha256 = JOB, None
    self.source_members = set()
    self.loading_source = False

  def authorize(self, owner, member, kind):
    if (owner in ('V4', 'V1') and member == 'manifest.json') or (owner == 'V1_TOP' and member in ('authorization.json', 'input-pins.json')):
      return
    if (owner, member, kind) in self.source_members:
      return
    bootstrap = {'CAUSAL': ('authorization.json', 'repeat-1/manifest.json'),
                 'DERIVED': ('repeat-1/derived-index.json', 'repeat-1/results.json', 'repeat-1/admission.json')}
    if kind == 'metadata' and member in bootstrap.get(owner, ()):
      return
    prefix = 'candidates/' + '/'.join(JOB) + '/'
    need(member.startswith(prefix), 'DIAGNOSTIC_EXACT_JOB_ONLY')
    tail = member[len(prefix):]
    allowed = {'V4': {'train/manifest.json', 'train-finalized.json', 'train/combined_probability.npy.gz'},
               'V1': {'train/move_label.npy.gz', 'train/prior_delta_tick.npy.gz',
                      'stage2/model/receipt.json', 'stage2/model/coefficients.npy.gz', 'stage2/normalizer/receipt.json',
                      *(f'stage2/normalizer/{f}.npy.gz' for f in ('mean', 'std', 'constant', 'effective', 'constant_reference'))}}
    need(tail in allowed.get(owner, ()), 'DIAGNOSTIC_UNAPPROVED_FIELD')

  def require_dev(self):
    raise ValueError('DIAGNOSTIC_NO_DEV')


def provider_type(modules):
  inp = modules['empirical_hurdle_v4_e2_inputs']
  e1 = modules['empirical_hurdle_v4_e_inputs']

  class Provider(inp.Provider):
    def admit_train_sources(self):
      need(self.segments is None)
      r, expected = self.reader, self.v4_auth['source_manifests']
      manifest = r.metadata('CAUSAL', 'repeat-1/manifest.json', receipt_sha=expected['causal'])
      auth = r.metadata('CAUSAL', 'authorization.json')
      index = r.metadata('DERIVED', 'repeat-1/derived-index.json', receipt_sha=expected['derived_index'])
      result = r.metadata('DERIVED', 'repeat-1/results.json', receipt_sha=expected['derived_result'])
      admission = r.metadata('DERIVED', 'repeat-1/admission.json', receipt_sha=result['admission_sha256'])
      need(admission['manifest_sha256'] == manifest['receipt_sha256'])
      indexed = {s['content_sha256']: s['receipt_sha256'] for s in index['segments']}
      all_ids = [s for values in auth['segments'].values() for s in values]
      need(len(index['segments']) == len(indexed) == len(all_ids) == len(set(all_ids)) == 154 and set(all_ids) == set(indexed))
      need(set(auth['segments']) == set(self.source_policy['route_ids']))
      need(not set(all_ids).intersection(self.source_policy['excluded_qlog_content_sha256']))
      route = self.references[INDEX]['train_route']
      need(route in auth['segments'])
      segments, total = [], 0
      for identity in sorted(auth['segments'][route]):
        need(e1.b0._digest(route) and e1.b0._digest(identity))
        source_prefix = f'repeat-1/routes/{route}/segments/{identity}'
        derived_prefix = f'repeat-1/segments/{identity}'
        r.phase.source_members.update({('CAUSAL', source_prefix + '/receipt.json', 'metadata'),
                                       ('DERIVED', derived_prefix + '/receipt.json', 'metadata')})
        source = r.metadata('CAUSAL', source_prefix + '/receipt.json')
        derived = r.metadata('DERIVED', derived_prefix + '/receipt.json', receipt_sha=indexed[identity])
        need(source['route_id'] == route and source['segment_sha256'] == identity)
        need(derived['source_receipt_sha256'] == source['receipt_sha256'] and derived['policy_sha256'] == self.source_policy['receipt_sha256'])
        n = source['arrays']['state.speed_mps']['shape'][0]
        need(type(n) is int and 0 < n <= e1.MAX_SOURCE_ROWS)
        total += n
        need(total <= e1.MAX_SOURCE_ROWS)
        arrays = {}
        for owner, prefix, row, fields in (('CAUSAL', source_prefix + '/arrays', source, e1.CAUSAL_FIELDS),
                                          ('DERIVED', derived_prefix, derived, e1.DERIVED_FIELDS)):
          for field in fields:
            member = prefix + '/' + field + '.npy'
            r.phase.source_members.add((owner, member, 'array'))
            dtype = '<f8' if owner == 'CAUSAL' else '|b1' if field in ('model_eligible', 'rail') else '<i8'
            arrays[field] = r.array(owner, member, row['arrays'][field], shape=(n,), dtype=dtype, compressed=False)
        need(np.all((arrays['angle_tick'] >= -32768) & (arrays['angle_tick'] <= 32767)))
        need(np.all((arrays['streak_all'] > 0) == arrays['model_eligible']))
        segments.append({'route_id': route, 'segment_sha256': identity, 'tick': arrays['angle_tick'], 'streak': arrays['streak_all'],
                         'command': arrays['command.normalized'], 'speed': arrays['state.speed_mps'], 'rail': arrays['rail'],
                         'eligible': arrays['model_eligible'], 'run': arrays['s2_ri_causal_run_id'], 'within': arrays['within_s2_ri_causal_run_index']})
      self.segments = tuple(segments)

  return Provider


def verify_gate(gate, reviews, protocol_raw, protocol, head):
  need(gate['mission'] == MISSION and gate['head'] == head and gate['protocol_raw_sha256'] == control.sha(protocol_raw))
  need(gate['ci']['head_sha'] == head and gate['ci']['status'] == 'completed' and gate['ci']['conclusion'] == 'success')
  need(len({r['reviewer'] for r in reviews.values()}) == 2)
  for name, role in (('science-review.json', 'SCIENTIFIC_NUMERICAL_CAUSAL'), ('authority-review.json', 'AUTHORITY_PRIVACY_SOURCE_INTEGRITY')):
    r = reviews[name]
    need(r['role'] == role and r['approval'] == 'APPROVED' and r['protocol_raw_sha256'] == control.sha(protocol_raw))
    need(r['source_sha256'] == protocol['diagnostic_source_sha256'] and r['receipt_sha256'] == gate['review_receipts'][name])
  need(gate['job'] == list(JOB) and gate['diagnostic_runs'] == 1 and gate['DEV_authorized'] is False and gate['D2_selection_authorized'] is False)


def verify_public_pins(old):
  for name, pin in old['public_inputs'].items():
    raw = (control.PUBLIC / name).read_bytes()
    need(control.sha(raw) == pin['raw_sha256'] and control.checked(raw)['receipt_sha256'] == pin['receipt_sha256'], 'DIAGNOSTIC_PUBLIC_INPUT_DRIFT')


def run(work, prior_work):
  head = control.git('rev-parse', 'HEAD')
  need(control.git('branch', '--show-current') == 'feature/cyber-autotune')
  need(head == control.git('rev-parse', 'origin/feature/cyber-autotune') and not control.git('status', '--porcelain'))
  need(control.git('merge-base', BASELINE, head) == BASELINE)
  protocol_raw = (control.PUBLIC / PROTOCOL).read_bytes()
  protocol = control.checked(protocol_raw)
  need(protocol['version'] == 'V4_E2_NUMERICAL_DIAGNOSTIC_PROTOCOL_V1' and protocol['job'] == list(JOB))
  for name, pin in protocol['diagnostic_source_sha256'].items():
    need(control.sha((control.SOURCE / name).read_bytes()) == pin, 'DIAGNOSTIC_SOURCE_DRIFT')
  old_raw = (control.PUBLIC / control.PROTOCOL_NAME).read_bytes()
  need(control.sha(old_raw) == protocol['frozen_E2_protocol_raw_sha256'])
  old = control.checked(old_raw)
  verify_public_pins(old)
  modules = control.load_exact(old)
  need(modules['empirical_s2_ri_policy'].policy()['receipt_sha256'] == old['source_policy_receipt_sha256'])
  diagnostic.frozen = modules['empirical_hurdle_fit_cv_math']
  modules['empirical_hurdle_v4_e_bootstrap'].warm_dependencies()
  need(sys.version.split()[0] == '3.12.13' and np.__version__ == '2.5.3')
  need(all(os.environ.get(k) == '1' for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')))
  need(control.sha(control.canonical(np.show_config(mode='dicts'))) == old['environment']['blas_build_identity_sha256'])
  need(ctypes.CDLL('libm.so.6').fegetround() == 0)
  # This authenticates historical controls only; it grants no new scientific access.
  values = control.controls(prior_work, old, modules)
  refs, roots, request, auth, jobs, environment, mounted, _, _ = values
  need((jobs[INDEX]['candidate_id'], jobs[INDEX]['fold']) == JOB)
  gate = control.checked(control.private(work / 'execution-gate.json'))
  reviews = {name: control.checked(control.private(work / name)) for name in ('science-review.json', 'authority-review.json')}
  verify_gate(gate, reviews, protocol_raw, protocol, head)
  need(gate['prior_control_references_raw_sha256'] == control.sha(control.private(prior_work / 'control-references.json')))
  need(gate['private_output_root'] == str(work) and gate['prior_work'] == str(prior_work))
  for value in roots.values():
    need(not work.is_relative_to(Path(value)) and not Path(value).is_relative_to(work))
  fd = control.directory(work)
  try:
    info = os.fstatvfs(fd)
    need(info.f_bavail * info.f_frsize >= protocol['resources']['reserve_bytes'] + protocol['resources']['output_bytes'])
    need(os.fstat(fd).st_dev != mounted[0])
  finally:
    os.close(fd)
  binding = control.sealed({'schema': 'V4_E2_NUMERICAL_DIAGNOSTIC_BINDING_V1', 'mission': MISSION, 'head': head,
                            'job': list(JOB), 'protocol_raw_sha256': control.sha(protocol_raw), 'gate_sha256': gate['receipt_sha256'],
                            'roots': roots, 'prior_lineage': refs['prior_lineage'], 'environment': environment})
  control.persist(work, 'execution-binding.json', binding, protocol['resources']['output_bytes'])
  # Exclusive binding creation is the one-shot latch; no retry/resume entry point.
  limit = protocol['resources']
  for which, cap in ((resource.RLIMIT_AS, limit['address_space_bytes']), (resource.RLIMIT_CPU, limit['cpu_seconds']),
                     (resource.RLIMIT_FSIZE, limit['output_bytes']), (resource.RLIMIT_CORE, 0)):
    resource.setrlimit(which, (cap, cap))
  signal.signal(signal.SIGALRM, lambda *_args: (_ for _ in ()).throw(ValueError('DIAGNOSTIC_RESOURCE_BOUND')))
  signal.alarm(limit['wall_seconds'])
  phase = Phase()
  base_reader = modules['empirical_hurdle_v4_e2_inputs'].Reader
  class Reader(base_reader):
    def raw(self, owner, member, kind, expected_raw, cap):
      need(len(self.events) < limit['input_open_limit']
           and sum(e['bytes_read'] for e in self.events) + cap <= limit['input_bytes_limit'], 'DIAGNOSTIC_READ_BOUND')
      return super().raw(owner, member, kind, expected_raw, cap)
  reader = Reader(roots, '/mnt/e', mounted, phase)
  audit = modules['empirical_hurdle_v4_e_bootstrap'].RuntimeFirewall()
  sys.addaudithook(audit)
  counters, result = {}, None
  def forbidden(*_args, **_kwargs):
    audit.attempts += 1
    raise ValueError('DIAGNOSTIC_FORBIDDEN_SCIENTIFIC_OPERATION')
  try:
    with ExitStack() as stack:
      modules['empirical_hurdle_v4_e_bootstrap'].trap_deserialization(stack, forbidden)
      for module, names in ((modules['empirical_hurdle_v4_e2_decision'], ('select_context', 'select_job', 'potentials')),
                            (modules['empirical_hurdle_v4_e_evaluation'], ('evaluate_job',)),
                            (modules['empirical_hurdle_v4_execution'], ('train', 'select', 'run', 'synthetic_run')),
                            (diagnostic.frozen, ('fit_stage1', 'fit_stage2', 'newton', 'normalizer', 'integrated')),
                            (diagnostic.frozen.source, ('fit', 'normalizer'))):
        for name in names:
          if hasattr(module, name):
            stack.enter_context(patch.object(module, name, forbidden))
      provider = provider_type(modules)(reader, jobs, v4_manifest=request['manifests']['V4_REPEAT_1'],
          v1_manifest=request['manifests']['V1_REFERENCE'], v4_authorization=auth,
          v1_authorization_sha=request['authorization']['V1_REFERENCE'],
          references=control.public('empirical-hurdle-fit-cv-results-v1.json')['jobs'],
          job_catalog=control.public('empirical-hurdle-stage1-v4-job-manifest.json')['jobs'],
          source_policy=modules['empirical_s2_ri_policy'].policy())
      provider.admit_train_sources()
      p, y, prior = provider.train(INDEX)
      modules['empirical_hurdle_v4_e2_decision'].validate(p, y, prior)
      d0 = diagnostic.frozen.threshold(p, y, role='TRAIN')
      counters['D0_TRAIN_reconstruction_calls'] = 1
      blocks, anchor, n = provider.train_blocks(INDEX)
      need(n == len(p) == jobs[INDEX]['fields'][0]['n'])
      stage2 = provider.stage2(INDEX)
      design = [diagnostic.frozen.features(segment, ix, JOB[0]) for segment, ix in blocks]
      c = np.concatenate([segment['tick'][ix].astype(np.int64) for segment, ix in blocks])
      t = np.concatenate([segment['tick'][ix + 1].astype(np.int64) for segment, ix in blocks])
      x = np.concatenate(design)
      need(np.array_equal(x[:, -3], prior) and np.array_equal(t != c, y), 'DIAGNOSTIC_RECORDED_ORDER_CONFLICT')
      result = diagnostic.diagnose(design, p > d0['value'], stage2, current=c)
      counters.update({'diagnostic_jobs': 1, 'frozen_stage2_model_loads': 1, **result['calls']})
      need(not audit.attempts)
      status = diagnostic_status(result)
      payload = control.sealed({'schema': 'V4_E2_NUMERICAL_PRIVATE_RESULT_V1', 'status': status,
          'binding_receipt_sha256': binding['receipt_sha256'], 'anchor_sha256': anchor, 'count': n,
          'diagnostic': result, 'input_events': reader.events, 'input_reads': reader.summary(),
          'control_events': control.CONTROL_EVENTS, 'operation_counters': counters, 'source_writes': 0,
          'forbidden_attempts': audit.attempts, 'D2_decisions': 0, 'DEV_reads': 0})
      audit.writing_output = True
      control.persist(work, 'canonical-result.json', payload, limit['output_bytes'])
      audit.writing_output = False
      # No private statistics or paths are printed. Publication is reviewed separately.
      print(json.dumps({'status': status, 'diagnostic_jobs': 1, 'D2_decisions': 0, 'DEV_reads': 0, 'source_writes': 0}), flush=True)
  except Exception as exc:
    audit.writing_output = True
    status, reason = abort_status(exc)
    control.persist(work, 'execution-envelope.json', abort_payload(binding, reader, counters, audit.attempts, exc), limit['output_bytes'])
    print(json.dumps({'status': status, 'reason': reason, 'exception_type': type(exc).__name__}), flush=True)
    raise SystemExit(1) from None
  finally:
    audit.active = False
    signal.alarm(0)


def abort_payload(binding, reader, counters, attempts, exc):
  status, reason = abort_status(exc)
  return control.sealed({'schema': 'V4_E2_NUMERICAL_DIAGNOSTIC_ABORT_V1',
      'status': status, 'reason': reason, 'exception_type': type(exc).__name__,
      'head': binding['head'], 'protocol_raw_sha256': binding['protocol_raw_sha256'],
      'binding_receipt_sha256': binding['receipt_sha256'],
      'input_events': reader.events, 'input_reads': reader.summary(),
      'control_events': control.CONTROL_EVENTS, 'operation_counters': counters,
      'forbidden_attempts': attempts, 'source_writes': 0})


def diagnostic_status(result):
  if not result['transformed_rows_byte_equal']:
    return 'E2_NUMERICAL_INPUT_CONFLICT'
  if result['target_failure_reproduced']:
    return 'E2_NUMERICAL_ROOT_CAUSE_IDENTIFIED'
  return 'E2_NUMERICAL_ROOT_CAUSE_UNRESOLVED'


def abort_status(exc):
  # Only allowlisted, path-free reason codes leave the process. No exception text.
  text = str(exc)
  if isinstance(exc, MemoryError) or text == 'DIAGNOSTIC_RESOURCE_BOUND':
    return 'E2_NUMERICAL_ROOT_CAUSE_UNRESOLVED', 'DIAGNOSTIC_RESOURCE_FAILURE'
  if text in ('DIAGNOSTIC_RECORDED_ORDER_CONFLICT', 'E_MANIFEST_MEMBER_HASH_CONFLICT', 'E_ARRAY_RAW_HASH_CONFLICT',
              'E2_TRAIN_ORDERED_ANCHOR_CONFLICT', 'E2_TRAIN_SEGMENT_BOUNDARY_CONFLICT'):
    return 'E2_NUMERICAL_INPUT_CONFLICT', text
  if text.startswith(('CANDIDATE_FOLD_NUMERICAL_FAILURE', 'HURDLE_NUMERICAL_FAILURE')):
    return 'E2_NUMERICAL_ROOT_CAUSE_UNRESOLVED', 'DIAGNOSTIC_NUMERICAL_FAILURE'
  return 'E2_DIAGNOSTIC_PRIVATE_ACCESS_BLOCKED', 'DIAGNOSTIC_PRECONDITION_OR_AUTHORITY_FAILURE'


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--work', required=True)
  parser.add_argument('--prior-work', required=True)
  args = parser.parse_args()
  work, prior = Path(args.work), Path(args.prior_work)
  need(work.is_absolute() and prior.is_absolute() and '..' not in work.parts and '..' not in prior.parts and work != prior)
  try:
    run(work, prior)
  except Exception as exc:
    status, reason = abort_status(exc)
    print(json.dumps({'status': status, 'reason': reason, 'exception_type': type(exc).__name__}), flush=True)
    raise SystemExit(1) from None


if __name__ == '__main__':
  main()
