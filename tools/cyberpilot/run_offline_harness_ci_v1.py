"""Exact-ID, synthetic-only offline CI. No vehicle or private-log authority.

The inherited bootstrap is a tripwire for trusted tests, not a sandbox against
malicious same-UID code. Raw decoder/runtime imports and data paths fail closed.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
import ctypes
import hashlib
import importlib
import importlib.abc
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading
import unittest

IDENTITY = 'CYBERPILOT_OFFLINE_HARNESS_V1'
BASELINE = '60a8a80bf53acb8572c6cc94b1d89c21558fce00'
ROOT = Path(__file__).resolve().parents[2]
MANIFEST = 'docs/cyberpilot/changes/offline-harness-test-ids-v1.txt'
MANIFEST_SHA = '9e863f672179c8c2fa755ac52e1e9da8409e70a9cadfbb9458173785dfd57d37'
EXPECTED_COUNT = 157
PYTHON_VERSION = (3, 12, 13)
SOURCE_PINS = {
  "docs/cyberpilot/changes/rlog-observer-regression-v1.md": "5e0a7fc5e7deda7a77df88d1bbe8af608fd55b98979c5d597ced9a38b11a64d0",
  "openpilot/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "openpilot/selfdrive/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "openpilot/selfdrive/controls/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "openpilot/selfdrive/controls/lib/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "openpilot/selfdrive/controls/lib/cyber_lateral/__init__.py": "67f17a826a48e2e4c9888ffd762dee3a1c016ef6cccffb1a8fc29650f605e1e6",
  "openpilot/selfdrive/controls/lib/cyber_lateral/coordinator.py": "202992806c8f04bfe1d10d190cca8df2380d6ffa547010f7c415a79d1fdbc243",
  "openpilot/selfdrive/controls/lib/cyber_lateral/jerk_observer.py": "7639e0e7fcb56ba5445deee7b97e36bff9282c0efc4e56e6a00054e5d5f5e157",
  "openpilot/selfdrive/controls/lib/cyber_lateral/metrics.py": "e4b02e14c5b250fb4d28e8480b3e821f50351c14e529be92923e1855f4611ba8",
  "openpilot/selfdrive/controls/lib/cyber_lateral/path_observer.py": "1b9665f70ec9cae1a2dde7bed2e3d75d4555f9a98b6d8b560a349d67af389494",
  "openpilot/selfdrive/controls/lib/cyber_lateral/path_tracking.py": "4ee53c7b22b8cca9c5b41b9c4e3462acf15ffcdd39ebcb4583747ea61a9afc5e",
  "openpilot/selfdrive/controls/lib/cyber_lateral/types.py": "97d2e48b795bfde1a7160e654a6bd459861a0a5f7f3ff39aa334aa113f4b647c",
  "openpilot/selfdrive/controls/tests/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "openpilot/selfdrive/controls/tests/test_cyber_lateral.py": "cd1c2a18b119c87ccb6a9f95a32b728955767aa742d370b2601a8d8d4bcffa19",
  "openpilot/selfdrive/controls/tests/test_cyber_lateral_metrics.py": "a2970470a13fc314b5a5f91ae0e14d7e595f4e882def29789d7b3bcb9838bc97",
  "openpilot/selfdrive/controls/tests/test_cyber_lateral_path_tracking.py": "a0441c3c41e002b20ad5805a760dd70d913d0720f8e5ff82d1152680c6e92588",
  "tools/cyberpilot/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "tools/cyberpilot/cli_security_f51.py": "932decf5067d305dae0df25612c79fa0bc5a6c8052f0830a374a415d549f953d",
  "tools/cyberpilot/historical_delay_observer_v1.py": "525a6eb8d3e36e0bb5f584262f003e75aae23dcccfebcf73a739e8006064475b",
  "tools/cyberpilot/recorded_input_binding_v1.py": "d0e3fc5371c9478aa9016288ed5ed6631630b9e63c8d2631f6d2a2777e270ae7",
  "tools/cyberpilot/rlog_observer_regression_v1.py": "8a12a5e6052296c8a588c3840ea4eaa9da8781d265efb59089bd33bace196ef2",
  "tools/cyberpilot/tests/test_cli_security_f51.py": "0d036227d19c6b3d7fac03327b2a1ed89fb618019f2fa2f3ac4baa1d5c3a0a59",
  "tools/cyberpilot/tests/test_historical_delay_observer_v1.py": "f651eb619531617fc1b26d38cd31c834418640e37cc934f54fec79d755ef7079",
  "tools/cyberpilot/tests/test_recorded_input_binding_v1.py": "dd7be80b717e9cb9ee4f0a6b8183588ebc0b374da1ef6c66b1ef768522c21253",
  "tools/cyberpilot/tests/test_rlog_observer_regression_v1.py": "a43f3b3c3a6461e52d159650b52a13124e710d0a9f40a467a43c5da9643c9330"
}
MODULES = tuple('tools.cyberpilot.tests.' + n for n in (
  'test_rlog_observer_regression_v1', 'test_recorded_input_binding_v1',
  'test_historical_delay_observer_v1', 'test_cli_security_f51'))
CANARIES = (b'F51_SYNTHETIC_PRIVATE_CANARY', b'F54_SYNTHETIC_PRIVATE_CANARY')
FORBIDDEN_IMPORTS = ('openpilot.selfdrive.controls.controlsd', 'openpilot.common.params',
                     'openpilot.cereal.messaging', 'cereal.messaging', 'common.params', 'capnp')
PUBLIC_CODES = frozenset(('INVALID_CLI_ARGUMENT', 'MANIFEST_PATH_REJECTED', 'MANIFEST_INVALID',
  'SOURCE_IDENTITY_MISMATCH', 'DISCOVERY_MISMATCH', 'EXECUTION_INCOMPLETE', 'TESTS_NOT_ALL_PASS',
  'PRIVACY_GATE_FAILED', 'RUNTIME_IMPORT_BLOCKED', 'DATA_ACCESS_BLOCKED', 'PROCESS_BLOCKED',
  'GUARD_BOOT_REQUIRED', 'CHILD_GUARD_MISSING', 'OUTPUT_PATH_REJECTED', 'ENVIRONMENT_UNQUALIFIED',
  'RESULT_INVALID', 'UNEXPECTED_GATE_ERROR'))
_GUARD_ACTIVE = False


class GateError(ValueError):
  pass


def need(ok, code):
  if not ok:
    raise GateError(code)


def canonical(value):
  return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(data):
  return hashlib.sha256(data).hexdigest()


def public_error(error):
  if isinstance(error, GateError) and error.args and type(error.args[0]) is str and error.args[0] in PUBLIC_CODES:
    return error.args[0]
  return 'UNEXPECTED_GATE_ERROR'


def parse_manifest(data):
  need(type(data) is bytes and digest(data) == MANIFEST_SHA and b'\r' not in data, 'MANIFEST_INVALID')
  try:
    ids = tuple(data.decode('utf-8').splitlines())
  except UnicodeError as error:
    raise GateError('MANIFEST_INVALID') from error
  need(len(ids) == EXPECTED_COUNT and ids == tuple(sorted(set(ids))) and
       all(re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+', i) for i in ids) and
       data == ('\n'.join(ids) + '\n').encode(), 'MANIFEST_INVALID')
  return ids


def check_ids(expected, actual):
  need(bool(expected) and len(actual) == len(expected) and len(set(actual)) == len(actual)
       and set(expected) == set(actual), 'DISCOVERY_MISMATCH')


def check_manifest_path(path):
  candidate = Path(path)
  need('..' not in candidate.parts and candidate.absolute() == ROOT / MANIFEST, 'MANIFEST_PATH_REJECTED')
  return candidate


def read_source(root, name):
  path = root / name
  need(not Path(name).is_absolute() and '..' not in Path(name).parts, 'SOURCE_IDENTITY_MISMATCH')
  for part in path.relative_to(root).parts:
    root = root / part
    need(not root.is_symlink(), 'SOURCE_IDENTITY_MISMATCH')
  fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
  with os.fdopen(fd, 'rb') as stream:
    need(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'SOURCE_IDENTITY_MISMATCH')
    return stream.read()


def check_source_pins(root=ROOT, pins=SOURCE_PINS):
  for name, expected in pins.items():
    try:
      need(digest(read_source(root, name)) == expected, 'SOURCE_IDENTITY_MISMATCH')
    except OSError as error:
      raise GateError('SOURCE_IDENTITY_MISMATCH') from error


def security():
  check_source_pins()
  sys.path.insert(0, str(ROOT))
  module = importlib.import_module('tools.cyberpilot.cli_security_f51')
  need(Path(module.__file__).resolve() == ROOT / 'tools/cyberpilot/cli_security_f51.py', 'SOURCE_IDENTITY_MISMATCH')
  return module


class ExactResult(unittest.TestResult):
  def __init__(self):
    super().__init__()
    self.started = []
    self.completed = []
    self.rows = []
    self.states = {}

  def startTest(self, test):
    super().startTest(test)
    identity = test.id()
    self.started.append(identity)
    sys.audit('cyberpilot.f54.case_start', identity)
    self.states[identity] = 'UNFINISHED'

  def mark(self, test, state):
    previous = self.states.get(test.id(), 'UNSTARTED')
    self.states[test.id()] = state if previous in ('UNFINISHED', 'UNSTARTED') else 'MULTIPLE_STATUS'

  def addSuccess(self, test):
    super().addSuccess(test)
    # A failed subtest already set FAIL/ERROR; it must not become PASS.
    if self.states.get(test.id()) == 'UNFINISHED':
      self.mark(test, 'PASS')

  def addFailure(self, test, err):
    super().addFailure(test, err)
    self.mark(test, 'FAIL')

  def addError(self, test, err):
    super().addError(test, err)
    self.mark(test, 'ERROR')

  def addSkip(self, test, reason):
    super().addSkip(test, reason)
    self.mark(test, 'SKIP')

  def addExpectedFailure(self, test, err):
    super().addExpectedFailure(test, err)
    self.mark(test, 'XFAIL')

  def addUnexpectedSuccess(self, test):
    super().addUnexpectedSuccess(test)
    self.mark(test, 'XPASS')

  def addSubTest(self, test, subtest, err):
    super().addSubTest(test, subtest, err)
    if err is not None:
      self.states[test.id()] = 'FAIL' if issubclass(err[0], test.failureException) else 'ERROR'

  def stopTest(self, test):
    self.completed.append(test.id())
    self.rows.append({'id': test.id(), 'status': self.states.get(test.id(), 'UNSTARTED')})
    sys.audit('cyberpilot.f54.case_stop', test.id(), self.states.get(test.id(), 'UNSTARTED'))
    super().stopTest(test)


def execute_suite(suite, expected):
  result = ExactResult()
  suite.run(result)
  counts = Counter(x['status'] for x in result.rows)
  return {'started_ids': result.started, 'completed_ids': result.completed, 'records': result.rows,
          'tests_run': result.testsRun, 'counts': {'passed': counts['PASS'], 'failed': counts['FAIL'],
          'errors': counts['ERROR'], 'skipped': counts['SKIP'], 'xfailed': counts['XFAIL'], 'xpassed': counts['XPASS']}}


def validate_execution(data, expected):
  check_ids(expected, data['started_ids'])
  check_ids(expected, data['completed_ids'])
  need(data['started_ids'] == list(expected) == data['completed_ids'] and
       data['tests_run'] == len(expected) and
       data['records'] == [{'id': i, 'status': 'PASS'} for i in expected], 'EXECUTION_INCOMPLETE')
  need(data['counts'] == {'passed': len(expected), 'failed': 0, 'errors': 0, 'skipped': 0, 'xfailed': 0, 'xpassed': 0},
       'TESTS_NOT_ALL_PASS')


def flatten(suite):
  for item in suite:
    if isinstance(item, unittest.TestSuite):
      yield from flatten(item)
    else:
      yield item


def discover(expected):
  extras = [i for i in expected if not i.startswith('tools.cyberpilot.tests.')]
  loader = unittest.TestLoader()
  tests = list(flatten(loader.loadTestsFromNames([*MODULES, *extras])))
  need(not loader.errors, 'DISCOVERY_MISMATCH')
  actual = [test.id() for test in tests]
  check_ids(expected, actual)
  for name, module in tuple(sys.modules.items()):
    file = getattr(module, '__file__', None)
    if name.startswith(('tools.cyberpilot.', 'openpilot.selfdrive.controls.')) and file:
      path = Path(file).resolve()
      need(path.is_relative_to(ROOT) and (path.relative_to(ROOT).as_posix() in SOURCE_PINS or
            path == Path(__file__).resolve()), 'SOURCE_IDENTITY_MISMATCH')
  by_id = {test.id(): test for test in tests}
  return unittest.TestSuite(by_id[i] for i in expected), actual


def _under(path, roots):
  return any(path == root or path.is_relative_to(root) for root in roots)


def install_guard():
  """Inherited through private sitecustomize, including python -B -c children."""
  global _GUARD_ACTIVE
  if _GUARD_ACTIVE:
    return
  own = Path(__file__).resolve()
  need(digest(own.read_bytes()) == os.environ.get('F54_GATE_SHA'), 'GUARD_BOOT_REQUIRED')
  session = Path(os.environ['F54_SESSION'])
  need(not session.is_symlink() and stat.S_IMODE(session.stat().st_mode) == 0o600 and
       session.stat().st_uid == os.geteuid(), 'GUARD_BOOT_REQUIRED')
  config = json.loads(session.read_bytes())
  output = Path(config['output'])
  need(output == session.parent and output == Path(os.environ['RUNNER_TEMP']) / 'offline-harness-v1', 'GUARD_BOOT_REQUIRED')
  ledger = output / 'ledger'
  inherited = {k: os.environ[k] for k in ('F54_SESSION', 'F54_GATE_SHA', 'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'PYTHONNOUSERSITE')}
  state = threading.local()
  event_lock = threading.Lock()
  sequence = 0

  def event_record(kind, **values):
    nonlocal sequence
    state.busy = True
    event_lock.acquire()
    try:
      sequence += 1
      path = ledger / (str(os.getpid()) + '-' + str(sequence) + '.json')
      fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
      with os.fdopen(fd, 'wb') as stream:
        stream.write(canonical({'kind': kind, 'pid': os.getpid(), 'sequence': sequence, 'nonce': config['nonce'], **values}))
    finally:
      event_lock.release()
      state.busy = False

  allowed_read = tuple(p.resolve() for p in (ROOT, output, Path(sys.prefix), Path(sys.base_prefix),
                                            Path('/usr/lib'), Path('/usr/local/lib')))
  original_open = os.open
  original_init = subprocess.Popen.__init__
  original_wait = subprocess.Popen.wait
  python_children = set()
  finished_children = set()

  def python_command(args):
    return isinstance(args, (list, tuple)) and bool(args) and Path(str(args[0])).resolve() == Path(sys.executable).resolve()

  def path_policy(candidate, flags):
    if flags & os.O_DIRECTORY:
      return  # Metadata traversal for F51's independently verified directory FDs.
    raw = Path(os.fsdecode(candidate)).absolute()
    path = raw.resolve()
    writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
    private = any(p.lower() in ('private_e2', 'holdout') for p in (*raw.parts, *path.parts))
    private = private or raw.name in ('rlog', 'rlog.zst') or path.name in ('rlog', 'rlog.zst')
    if path == Path(os.devnull):
      return
    if private or not _under(path, allowed_read) or (writing and not path.is_relative_to(output.resolve())):
      event_record('violation', code='DATA_ACCESS_BLOCKED')
      raise GateError('DATA_ACCESS_BLOCKED')

  def guarded_open(path: str | bytes | os.PathLike[str] | os.PathLike[bytes], flags: int,
                   mode: int = 0o777, *, dir_fd: int | None = None) -> int:
    if getattr(state, 'busy', False):
      return original_open(path, flags, mode, dir_fd=dir_fd)
    candidate = Path(os.fsdecode(path))
    if not candidate.is_absolute() and dir_fd is not None:
      candidate = Path(os.readlink('/proc/self/fd/' + str(dir_fd))) / candidate
    path_policy(candidate, flags)
    state.validated_open = getattr(state, 'validated_open', 0) + 1
    try:
      return original_open(path, flags, mode, dir_fd=dir_fd)
    finally:
      state.validated_open -= 1

  def policy(event, args):
    if getattr(state, 'busy', False):
      return
    code = None
    if event in ('cyberpilot.f54.case_start', 'cyberpilot.f54.case_stop'):
      expected = parse_manifest(read_source(ROOT, MANIFEST))
      if args[0] not in expected:
        event_record('violation', code='EXECUTION_INCOMPLETE')
        raise GateError('EXECUTION_INCOMPLETE')
      if event.endswith('case_start'):
        event_record('test_start', test_id=args[0])
      else:
        need(args[1] in ('PASS', 'FAIL', 'ERROR', 'SKIP', 'XFAIL', 'XPASS', 'UNFINISHED', 'MULTIPLE_STATUS'), 'EXECUTION_INCOMPLETE')
        event_record('test_stop', test_id=args[0], status=args[1])
      return
    if event == 'import':
      name = str(args[0])
      if name.startswith(FORBIDDEN_IMPORTS) or any('carcontroller' in p or p.startswith('latcontrol_') for p in name.split('.')):
        code = 'RUNTIME_IMPORT_BLOCKED'
    elif event in ('socket.connect', 'os.system'):
      code = 'PROCESS_BLOCKED'
    elif event == 'open' and not isinstance(args[0], int):
      if not getattr(state, 'validated_open', 0):
        path_policy(args[0], args[2])
    elif event == 'subprocess.Popen':
      command = args[1]
      git_read = command == ['git', '-C', str(ROOT), 'rev-parse', 'HEAD']
      environment = args[3] if args[3] is not None else os.environ
      startup_safe = (python_command(command) and len(command) >= 3 and command[1] == '-B' and
                      (command[2] == '-c' or (not str(command[2]).startswith('-') and
                       Path(command[2]).resolve().is_relative_to(ROOT))))
      inherited_safe = all(environment.get(k) == value for k, value in inherited.items())
      if not git_read and (not startup_safe or not inherited_safe):
        code = 'PROCESS_BLOCKED'
    if code:
      event_record('violation', code=code)
      raise GateError(code)

  def tracked_init(instance, *args, **kwargs):
    original_init(instance, *args, **kwargs)
    command = kwargs.get('args', args[0] if args else None)
    if python_command(command):
      python_children.add(instance.pid)
      event_record('spawn', child_pid=instance.pid)

  def tracked_wait(instance, *args, **kwargs):
    code = original_wait(instance, *args, **kwargs)
    if instance.pid in python_children and instance.pid not in finished_children:
      finished_children.add(instance.pid)
      event_record('exit', child_pid=instance.pid, exit_code=code)
    return code

  class F54ImportGuard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
      if fullname.startswith(FORBIDDEN_IMPORTS) or any('carcontroller' in p or p.startswith('latcontrol_') for p in fullname.split('.')):
        event_record('violation', code='RUNTIME_IMPORT_BLOCKED')
        raise GateError('RUNTIME_IMPORT_BLOCKED')
      return None

  sys.meta_path.insert(0, F54ImportGuard())
  sys.addaudithook(policy)
  # Register audited OS/process hooks as one explicit instrumentation table.
  hooks = ((os, 'open', guarded_open), (subprocess.Popen, '__init__', tracked_init),
           (subprocess.Popen, 'wait', tracked_wait))
  for owner, attribute, function in hooks:
    setattr(owner, attribute, function)
  os.supports_dir_fd = os.supports_dir_fd | {guarded_open}
  event_record('boot')
  _GUARD_ACTIVE = True


@contextmanager
def capture_output(directory):
  """Private native/Python stdout/stderr capture; never forward raw exceptions."""
  path = 'captured.log'
  directory.verify()
  fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory.fd)
  backups = [(n, os.dup(n)) for n in (1, 2)]
  libc = ctypes.CDLL(None)
  try:
    sys.stdout.flush()
    sys.stderr.flush()
    libc.fflush(None)
    for n, _ in backups:
      os.dup2(fd, n)
    with io.StringIO() as sink:
      from contextlib import redirect_stderr, redirect_stdout
      with redirect_stdout(sink), redirect_stderr(sink):
        yield sink
        libc.fflush(None)
  finally:
    libc.fflush(None)
    for n, saved in backups:
      os.dup2(saved, n)
      os.close(saved)
    os.close(fd)


def check_captured_output(data):
  need(not any(c in data for c in CANARIES), 'PRIVACY_GATE_FAILED')


def resolve_output(value):
  base = os.environ.get('RUNNER_TEMP', '')
  need(bool(base) and Path(base).is_absolute() and '..' not in Path(base).parts, 'OUTPUT_PATH_REJECTED')
  expected = Path(base) / 'offline-harness-v1' / 'summary.json'
  need('..' not in Path(value).parts and Path(value).absolute() == expected, 'OUTPUT_PATH_REJECTED')
  return expected


def check_ledger(folder, expected=None):
  events = []
  for path in (folder / 'ledger').glob('*.json'):
    need(not path.is_symlink(), 'PRIVACY_GATE_FAILED')
    events.append(json.loads(path.read_bytes()))
  session = json.loads((folder / 'session.json').read_bytes())
  nonce = session['nonce']
  need(all(e.get('nonce') == nonce and e.get('kind') in
           ('boot', 'spawn', 'exit', 'violation', 'test_start', 'test_stop') for e in events), 'PRIVACY_GATE_FAILED')
  boots = {e['pid'] for e in events if e['kind'] == 'boot'}
  children = {e['child_pid'] for e in events if e['kind'] == 'spawn'}
  ended = {e['child_pid'] for e in events if e['kind'] == 'exit'}
  need(session.get('executor_pid', os.getpid()) in boots and children <= boots and children == ended, 'CHILD_GUARD_MISSING')
  need(not any(e['kind'] == 'violation' for e in events), 'PRIVACY_GATE_FAILED')
  if expected is not None:
    cases = sorted((e for e in events if e['kind'].startswith('test_')), key=lambda e: e['sequence'])
    need(all(e['pid'] == session.get('executor_pid', os.getpid()) for e in cases), 'EXECUTION_INCOMPLETE')
    need([e['test_id'] for e in cases if e['kind'] == 'test_start'] == list(expected) and
         [e['test_id'] for e in cases if e['kind'] == 'test_stop'] == list(expected) and
         len(cases) == 2 * len(expected) and all(e['status'] == 'PASS' for e in cases if e['kind'] == 'test_stop'), 'EXECUTION_INCOMPLETE')
  return {'policy_violations': 0, 'child_handshakes_verified': True, 'canary_matches': 0, 'execution_ledger_verified': expected is not None}


def verify_summary(summary, expected):
  keys = {'identity', 'baseline_source_commit', 'tested_checkout_sha', 'manifest_sha256', 'source_sha256',
          'runner_sha256', 'collected_ids', 'execution', 'privacy', 'runtime_authority', 'receipt_sha256'}
  need(set(summary) == keys and summary['identity'] == IDENTITY and
       summary['manifest_sha256'] == MANIFEST_SHA and summary['source_sha256'] == SOURCE_PINS and
       summary['runner_sha256'] == digest(Path(__file__).read_bytes()) and
       summary['baseline_source_commit'] == BASELINE and summary['runtime_authority'] == 'NONE', 'RESULT_INVALID')
  need(summary['receipt_sha256'] == digest(canonical({k: v for k, v in summary.items() if k != 'receipt_sha256'})), 'RESULT_INVALID')
  check_ids(expected, summary['collected_ids'])
  validate_execution(summary['execution'], expected)
  need(summary['privacy'] == {'policy_violations': 0, 'child_handshakes_verified': True,
                              'canary_matches': 0, 'execution_ledger_verified': True}, 'PRIVACY_GATE_FAILED')


def guarded_execute(result_path):
  need(os.environ.get('F54_SESSION') and os.environ.get('F54_GATE_SHA') == digest(Path(__file__).read_bytes()), 'GUARD_BOOT_REQUIRED')
  directory = security().SecureDirectory.existing(result_path.parent)
  execution = None
  try:
    expected = parse_manifest(read_source(ROOT, MANIFEST))
    with capture_output(directory) as text:
      check_source_pins()
      suite, actual = discover(expected)
      execution = execute_suite(suite, expected)
      # Test exceptions stay private, but Canary leakage still causes failure.
      captured_python = text.getvalue().encode()
    captured_native = directory.read('captured.log')
    check_captured_output(captured_python + captured_native)
    validate_execution(execution, expected)
    check_source_pins()
    privacy = check_ledger(result_path.parent, expected)
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    summary = {'identity': IDENTITY, 'baseline_source_commit': BASELINE, 'tested_checkout_sha': head,
      'manifest_sha256': MANIFEST_SHA, 'source_sha256': SOURCE_PINS,
      'runner_sha256': digest(Path(__file__).read_bytes()), 'collected_ids': sorted(actual),
      'execution': execution, 'privacy': privacy, 'runtime_authority': 'NONE'}
    summary['receipt_sha256'] = digest(canonical(summary))
    verify_summary(summary, expected)
    directory.write('summary.json', canonical(summary))
    directory.write('summary.sha256', (digest(canonical(summary)) + '\n').encode())
    directory.write('attestation.json', canonical({'checkout_sha': head, 'event': os.environ.get('GITHUB_EVENT_NAME'),
      'github_sha': os.environ.get('GITHUB_SHA'), 'run_id': os.environ.get('GITHUB_RUN_ID'),
      'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'), 'python': sys.version, 'pid': os.getpid()}))
    print('F54_EXACT_157_ID_GATE_PASS')
  except BaseException as error:
    failure = {'identity': IDENTITY, 'reason': public_error(error), 'execution': execution,
               'runtime_authority': 'NONE', 'success': False}
    directory.write('failure.json', canonical(failure))
    if execution is not None:
      for row in execution['records']:
        if row['status'] != 'PASS':
          print('F54_FAILED_TEST ' + json.dumps(row, sort_keys=True))
    raise
  finally:
    directory.close()


def launch(result_path):
  need(sys.version_info[:3] == PYTHON_VERSION and sys.platform == 'linux' and os.geteuid() != 0 and
       importlib.metadata.version('zstandard') == '0.25.0', 'ENVIRONMENT_UNQUALIFIED')
  sec = security()
  folder = sec.SecureDirectory.create(result_path.parent)
  try:
    for name in ('tmp', 'ledger', 'bootstrap', 'home'):
      os.mkdir(name, 0o700, dir_fd=folder.fd)
    nonce = os.urandom(16).hex()
    folder.write('session.json', canonical({'output': str(result_path.parent), 'nonce': nonce, 'executor_pid': os.getpid()}))
    bootstrap = sec.SecureDirectory.existing(result_path.parent / 'bootstrap')
    try:
      bootstrap.write('sitecustomize.py', b'\n'.join((
        b'import os', b'try:',
        b' from tools.cyberpilot.run_offline_harness_ci_v1 import install_guard', b' install_guard()',
        b'except BaseException:', b' os.write(2,b"F54_GUARD_BOOT_FAILURE\\n")', b' os._exit(2)', b'')))
    finally:
      bootstrap.close()
  finally:
    folder.close()
  allowed = ('PATH', 'RUNNER_TEMP', 'CI', 'GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_EVENT_NAME')
  env = {k: os.environ[k] for k in allowed if k in os.environ}
  env.update({'PYTHONPATH': str(result_path.parent / 'bootstrap') + os.pathsep + str(ROOT),
    'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1', 'PYTHONHASHSEED': '0',
    'PYTHONPYCACHEPREFIX': str(result_path.parent / 'no-pycache'),
    'TMPDIR': str(result_path.parent / 'tmp'), 'HOME': str(result_path.parent / 'home'),
    'F54_SESSION': str(result_path.parent / 'session.json'), 'F54_GATE_SHA': digest(Path(__file__).read_bytes())})
  os.chdir(ROOT)
  os.execve(sys.executable, [sys.executable, '-B', str(Path(__file__).resolve()), '--guarded',
                            '--manifest', str(ROOT / MANIFEST), '--result', str(result_path)], env)


class PrivateParser(argparse.ArgumentParser):
  def error(self, message):
    raise GateError('INVALID_CLI_ARGUMENT')


def main(argv=None):
  parser = PrivateParser(prog='cyberpilot-offline-harness-v1')
  parser.add_argument('--manifest', default=str(ROOT / MANIFEST))
  parser.add_argument('--result', required=True)
  parser.add_argument('--verify-result', action='store_true')
  parser.add_argument('--guarded', action='store_true', help=argparse.SUPPRESS)
  try:
    args = parser.parse_args(argv)
    check_manifest_path(args.manifest)
    output = resolve_output(args.result)
    check_source_pins()
    if args.verify_result:
      directory = security().SecureDirectory.existing(output.parent)
      try:
        summary = json.loads(directory.read('summary.json'))
        expected = parse_manifest(read_source(ROOT, MANIFEST))
        verify_summary(summary, expected)
        need(check_ledger(output.parent, expected) == summary['privacy'], 'RESULT_INVALID')
        need(directory.read('summary.sha256').decode() == digest(canonical(summary)) + '\n', 'RESULT_INVALID')
        print('F54_SAVED_EXACT_157_RESULT_VERIFIED')
      finally:
        directory.close()
    elif args.guarded:
      guarded_execute(output)
    else:
      launch(output)
    return 0
  except SystemExit as error:
    return 0 if error.code == 0 else 2
  except BaseException as error:
    print('F54_GATE_BLOCKED:' + public_error(error))
    return 2


if __name__ == '__main__':
  sys.exit(main())
