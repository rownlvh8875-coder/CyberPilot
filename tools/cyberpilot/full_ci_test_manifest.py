#!/usr/bin/env python3
"""Additive full-CI evidence around the unchanged public unittest runner.

No target/filter API: both original directories are always collected and run.
The original runner owns discovery, fixture grouping, capture, and execution.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import stat
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
TARGETS = ('openpilot/tools/cyber_autotune/tests', 'openpilot/selfdrive/controls/tests')
BASELINE_HEAD = '5af7b52d9fd16f43e1def6f9b75e9f7913d14f53'
BASELINE_COUNT = 5927
BASELINE_IDS_SHA = 'e293db84c944594175ed50bba9d98408692ecd63054e17c96656a2bf004c870b'
BASELINE_IDS_FILE = 'docs/cyberpilot/changes/cyberpilot-full-ci-v2-baseline-test-ids.txt'
LEGACY_SHA = '30fbd6d6138fd4b44b9371ce0f803ed500bf662d287463d4a28a0585654d28d4'
NATIVE_SOURCE_SHA = '1af1bfa0ce165b47104980ed917375de5fd1c2385c7c0d8429c6f8b7d0e7115e'
NATIVE_WRAPPER_SHA = 'a89a4473e3d9cacf3a42ca5056a656c42b757dc12f1358a071a7e28545215092'
NATIVE_ABI = 'C11_LINUX_X86_64_DOUBLE_SIZE_T_INT64_V1'
NATIVE_FLAGS = ('-O2', '-std=c11', '-fPIC', '-shared', '-fno-fast-math', '-ffp-contract=off',
                '-fno-associative-math', '-frounding-math', '-fexcess-precision=standard',
                '-fno-tree-vectorize', '-mfpmath=sse', '-msse2', '-Wall', '-Wextra', '-Werror')
WORKERS = 2
MAX_EVIDENCE_BYTES = 16 * 1024**2


class CIIntegrityError(ValueError):
  pass


def need(condition, code):
  if not condition:
    raise CIIntegrityError(code)


def canonical(value):
  return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def seal(value):
  value = {k: v for k, v in value.items() if k != 'receipt_sha256'}
  return {**value, 'receipt_sha256': hashlib.sha256(canonical(value)).hexdigest()}


def check_seal(value):
  need(type(value) is dict and value == seal(value), 'CI_RECEIPT_CONFLICT')


def ids_hash(ids):
  return hashlib.sha256(('\n'.join(ids) + '\n').encode()).hexdigest()


def git(*args):
  return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def make_manifest(head, ids, baseline_ids):
  need(type(head) is str and re.fullmatch('[0-9a-f]{40}', head), 'CI_HEAD_INVALID')
  ids, baseline_ids = list(ids), list(baseline_ids)
  need(ids and all(type(i) is str and re.fullmatch(r'[A-Za-z0-9_.]+', i) for i in ids), 'CI_TEST_ID_INVALID')
  need(len(ids) == len(set(ids)) and len(baseline_ids) == len(set(baseline_ids)), 'CI_DUPLICATE_ID')
  need(set(baseline_ids) <= set(ids), 'CI_BASELINE_ID_MISSING')
  ids = sorted(ids)
  return seal({'schema': 'CYBERPILOT_FULL_TEST_MANIFEST_V2', 'head': head, 'targets': list(TARGETS),
               'workers': WORKERS, 'test_ids': ids, 'count': len(ids), 'sorted_ids_sha256': ids_hash(ids),
               'baseline_count': len(baseline_ids), 'baseline_ids_sha256': ids_hash(sorted(baseline_ids)),
               'collection_errors': [], 'runner': 'tools/test_runner.py', 'filter': None})


def validate_manifest(manifest):
  check_seal(manifest)
  need(manifest['schema'] == 'CYBERPILOT_FULL_TEST_MANIFEST_V2' and manifest['targets'] == list(TARGETS)
       and manifest['workers'] == WORKERS and manifest['collection_errors'] == [] and manifest['filter'] is None,
       'CI_COLLECTION_CONTRACT_CONFLICT')
  ids = manifest['test_ids']
  need(ids == sorted(set(ids)) and len(ids) == manifest['count'] and ids_hash(ids) == manifest['sorted_ids_sha256'],
       'CI_MANIFEST_IDS_CONFLICT')


def parse_log(manifest, text, exit_code):
  validate_manifest(manifest)
  need(exit_code == 0, 'CI_RUNNER_NONZERO_EXIT')
  collected = re.findall(r'^collected (\d+) tests? in [0-9.]+s • (\d+) workers?$', text, re.M)
  need(collected == [(str(manifest['count']), str(WORKERS))], 'CI_COLLECTION_OUTPUT_CONFLICT')
  records = [{'id': i, 'status': {'.': 'passed', 's': 'skipped', 'F': 'failed', 'E': 'error',
                                'x': 'xfailed', 'X': 'xpassed'}[mark], 'seconds': float(seconds)}
             for mark, i, seconds in re.findall(r'^([.sFExX]) (\S+) ([0-9.]+)s$', text, re.M)]
  counts = Counter(x['status'] for x in records)
  actual = [x['id'] for x in records]
  need(len(actual) == len(set(actual)) and set(actual) == set(manifest['test_ids']), 'CI_EXECUTED_ID_CONFLICT')
  need(counts == {'passed': manifest['count']}, 'CI_NONPASS_TEST')
  summaries = re.findall(r'^(\d+) passed in ([0-9.]+)s$', text, re.M)
  need(len(summaries) == 1 and int(summaries[0][0]) == manifest['count']
       and 'COLLECTION ERROR' not in text and re.search(r'^interrupted$', text, re.M) is None, 'CI_PARTIAL_RUN')
  return seal({'schema': 'CYBERPILOT_FULL_TEST_RESULT_V2', 'head': manifest['head'],
               'manifest_receipt_sha256': manifest['receipt_sha256'], 'exit_code': exit_code,
               'records': sorted(records, key=lambda x: x['id']), 'counts': dict(counts),
               'runner_elapsed_seconds': float(summaries[0][1]), 'log_sha256': hashlib.sha256(text.encode()).hexdigest()})


def read_json(path, expected_digest=None):
  from tools.cyberpilot.verify_full_ci_lfs import open_directory
  path = Path(path)
  parent = open_directory(path.parent)
  try:
    fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    with os.fdopen(fd, 'rb') as stream:
      st = os.fstat(stream.fileno())
      need(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and st.st_uid == os.getuid() and st.st_size <= MAX_EVIDENCE_BYTES, 'CI_EVIDENCE_FILE_INVALID')
      raw = stream.read(MAX_EVIDENCE_BYTES + 1)
      need(len(raw) == st.st_size and len(raw) <= MAX_EVIDENCE_BYTES, 'CI_EVIDENCE_CAP')
      after = os.fstat(stream.fileno())
      need((st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
           == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'CI_EVIDENCE_CHANGED')
      if expected_digest is not None:
        need(re.fullmatch('[0-9a-f]{64}', expected_digest) is not None
             and hashlib.sha256(raw).hexdigest() == expected_digest, 'CI_EVIDENCE_SHA_CONFLICT')
    return json.loads(raw)
  finally:
    os.close(parent)


def write_json(path, value):
  path = Path(path)
  path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
  from tools.cyberpilot.verify_full_ci_lfs import open_directory
  parent = open_directory(path.parent)
  try:
    raw = json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n'
    need(len(raw) <= MAX_EVIDENCE_BYTES, 'CI_EVIDENCE_CAP')
    fd = os.open(path.name, os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_WRONLY, 0o600, dir_fd=parent)
    with os.fdopen(fd, 'wb') as stream:
      stream.write(raw)
      stream.flush()
      os.fsync(stream.fileno())
    os.fsync(parent)
  finally:
    os.close(parent)
  return hashlib.sha256(raw).hexdigest()


def verify_native(path, digest):
  need(bool(path) and re.fullmatch('[0-9a-f]{64}', digest or '') is not None, 'CI_NATIVE_RECEIPT_REQUIRED')
  from openpilot.tools.cyber_autotune import empirical_hurdle_v4_e2_canonical_native_candidate as native
  need(hashlib.sha256(native.SOURCE.read_bytes()).hexdigest() == NATIVE_SOURCE_SHA
       and hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest() == NATIVE_WRAPPER_SHA, 'CI_NATIVE_SOURCE_CONFLICT')
  candidate = native.NativeCandidate(path, digest)
  need(candidate.noop() == 0 and tuple(native.FLAGS) == NATIVE_FLAGS, 'CI_NATIVE_ABI_CONFLICT')
  return {'verified': True, 'receipt_sha256': digest, 'source_sha256': NATIVE_SOURCE_SHA,
          'wrapper_sha256': NATIVE_WRAPPER_SHA, **{k: candidate.receipt[k] for k in
          ('binary_sha256', 'compiler_version', 'flags', 'ABI', 'private_execution_authorized', 'runtime_integration_authorized')}}


def pointer_members(text):
  members = {}
  for line in text.splitlines():
    match = re.fullmatch(r'([0-9a-f]{64}) [*-] (.+)', line)
    need(match is not None, 'CI_LFS_INDEX_FORMAT_CONFLICT')
    oid, path = match.groups()
    need(path not in members, 'CI_LFS_INDEX_DUPLICATE_MEMBER')
    members[path] = oid
  return members


def source_integrity(verify_lfs=False):
  from tools.cyberpilot.verify_full_ci_lfs import verify_file
  base = ROOT / 'docs/cyberpilot/changes'
  pins = json.loads((base / 'empirical-hurdle-stage1-v4-e2-canonical-native-bounded-contract-v1.json').read_text())['frozen_source_sha256']
  need(len(pins) == 231 and all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in pins.items()), 'CI_FROZEN_SOURCE_CONFLICT')
  changed_original_tests = git('diff', '--name-only', '--diff-filter=DMRTUXB', BASELINE_HEAD, '--',
                               'tools/test_runner.py', *TARGETS)
  need(not changed_original_tests, 'CI_ORIGINAL_TEST_SOURCE_CHANGED')
  lock_path = base / 'cyberpilot-full-ci-v2-lock.json'
  need(lock_path.is_file(), 'CI_V2_SOURCE_LOCK_REQUIRED')
  lock = json.loads(lock_path.read_text())
  check_seal(lock)
  need(all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in lock['source_sha256'].items()),
       'CI_V2_SOURCE_LOCK_CONFLICT')
  inventory = json.loads((base / 'cyberpilot-full-ci-lfs-recovery-inventory.json').read_text())['all_head_pointers']
  current_members = pointer_members(git('lfs', 'ls-files', '--long'))
  need(len(inventory) == 252 and current_members == {i['path']: i['oid'] for i in inventory}, 'CI_LFS_INVENTORY_CONFLICT')
  for item in inventory:
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:' + item['path']])
    need(hashlib.sha256(raw).hexdigest() == item['pointer_raw_sha256'], 'CI_LFS_POINTER_CONFLICT')
  payloads = [i for i in inventory if i['path'] != 'openpilot/selfdrive/modeld/models/big_driving_tinygrad.pkl']
  if verify_lfs:
    for item in payloads:
      verify_file(ROOT / item['path'], item)
  return {'ci_v2_lock_receipt_sha256': lock['receipt_sha256'], 'frozen_source_pins': len(pins), 'pointer_count': len(inventory), 'conflicts': [],
          'lfs_materialized_verified': len(payloads) if verify_lfs else 'NOT_CHECKED',
          'lfs_materialized_bytes': sum(i['size'] for i in payloads) if verify_lfs else 'NOT_CHECKED',
          'existing_only_exclusion_unchanged': True}


def collect_manifest():
  from tools import test_runner
  started = time.monotonic()
  baseline = (ROOT / BASELINE_IDS_FILE).read_text().splitlines()
  need(len(baseline) == BASELINE_COUNT and baseline == sorted(set(baseline))
       and ids_hash(baseline) == BASELINE_IDS_SHA, 'CI_BASELINE_MANIFEST_CONFLICT')
  tests, errors = test_runner.collect(list(TARGETS), None)
  need(not errors, 'CI_COLLECTION_ERRORS: ' + '\n'.join(errors))
  manifest = make_manifest(git('rev-parse', 'HEAD'), [t.id() for t in tests], baseline)
  groups = test_runner.make_batches(tests, WORKERS)
  return seal({**manifest, 'batch_assignment_sha256': hashlib.sha256(canonical(groups)).hexdigest(),
               'batch_count': len(groups), 'collection_wall_seconds': time.monotonic() - started})


class ProcessObservation:
  """Sample only this subprocess family. RSS/VM sums include shared-page overcount."""
  def __init__(self, pid):
    self.pid, self.done = pid, threading.Event()
    self.peak_rss_kib = self.peak_virtual_kib = self.peak_processes = 0
    self.thread = threading.Thread(target=self.sample, daemon=True)
    self.thread.start()

  def sample(self):
    while not self.done.is_set():
      pending, seen, rss, virtual = [self.pid], set(), 0, 0
      while pending:
        pid = pending.pop()
        if pid in seen:
          continue
        seen.add(pid)
        try:
          root = Path('/proc') / str(pid)
          fields = dict(line.split(':', 1) for line in (root / 'status').read_text().splitlines() if ':' in line)
          rss += int(fields.get('VmRSS', '0 kB').split()[0])
          virtual += int(fields.get('VmSize', '0 kB').split()[0])
          pending.extend(int(x) for x in (root / 'task' / str(pid) / 'children').read_text().split())
        except (FileNotFoundError, ProcessLookupError):
          pass
      self.peak_rss_kib = max(self.peak_rss_kib, rss)
      self.peak_virtual_kib = max(self.peak_virtual_kib, virtual)
      self.peak_processes = max(self.peak_processes, len(seen))
      self.done.wait(0.25)

  def finish(self):
    self.done.set()
    self.thread.join()
    return {'sampled_family_peak_RSS_KiB': self.peak_rss_kib,
            'sampled_family_peak_virtual_KiB': self.peak_virtual_kib,
            'sampled_peak_processes': self.peak_processes, 'sample_interval_seconds': 0.25,
            'shared_pages_double_counted': True, 'transient_allocations_may_be_missed': True}


def run_regression(output):
  output = Path(output)
  output.mkdir(mode=0o700, parents=True, exist_ok=False)
  native = verify_native(os.environ.get('CYBERPILOT_PUBLIC_NATIVE_RECEIPT', ''), os.environ.get('CYBERPILOT_PUBLIC_NATIVE_RECEIPT_SHA256', ''))
  manifest = collect_manifest()
  write_json(output / 'manifest.json', manifest)
  write_json(output / 'native.json', native)
  before = resource.getrusage(resource.RUSAGE_CHILDREN)
  start = time.monotonic()
  command = [sys.executable, '-u', '-B', 'tools/test_runner.py', *TARGETS, '-j', str(WORKERS), '-v']
  with (output / 'regression.log').open('x') as stream:
    child = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    observation = ProcessObservation(child.pid)
    try:
      exit_code = child.wait()
    finally:
      measured = observation.finish()
  after = resource.getrusage(resource.RUSAGE_CHILDREN)
  resources = {**measured, 'wall_seconds': time.monotonic() - start,
               'user_cpu_seconds': after.ru_utime - before.ru_utime, 'system_cpu_seconds': after.ru_stime - before.ru_stime,
               'runner_exit_code': exit_code, 'worker_exit_codes': 'NOT_EXPOSED_BY_UNMODIFIED_RUNNER',
               'host_cpu_count': os.cpu_count(), 'host_memory_bytes': os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')}
  write_json(output / 'resources.json', resources)
  need(git('rev-parse', 'HEAD') == manifest['head'], 'CI_HEAD_CHANGED_DURING_TESTS')
  text = (output / 'regression.log').read_text()
  print(text[-4000:], flush=True)
  result = parse_log(manifest, text, exit_code)
  write_json(output / 'regression.json', result)
  print(json.dumps({'test_count': manifest['count'], 'coverage': 'ALL_IDS_EXACTLY_ONCE_PASSED', 'resources': resources}, indent=2))


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('mode', choices=('sources', 'native', 'collect', 'run'))
  parser.add_argument('--output', type=Path, required=True)
  parser.add_argument('--workers', type=int, choices=(WORKERS,), default=WORKERS)
  args = parser.parse_args()
  os.chdir(ROOT)
  if args.mode == 'sources':
    write_json(args.output, source_integrity(verify_lfs=True))
  elif args.mode == 'native':
    witness = verify_native(os.environ.get('CYBERPILOT_PUBLIC_NATIVE_RECEIPT', ''),
                            os.environ.get('CYBERPILOT_PUBLIC_NATIVE_RECEIPT_SHA256', ''))
    write_json(args.output, witness)
  elif args.mode == 'collect':
    write_json(args.output, collect_manifest())
  else:
    run_regression(args.output)


if __name__ == '__main__':
  try:
    main()
  except (CIIntegrityError, KeyError, OSError, ValueError) as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1) from error
