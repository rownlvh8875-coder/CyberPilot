"""Exact-ID local verifier for the synthetic-only reference, not GitHub CI."""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import re
import stat
import sys
import sysconfig
import tempfile
import unittest
from pathlib import Path

SOURCE_FILES = ['f70_synthetic_exact_reference.py', 'f70_synthetic_exact_audit.py',
                'test_f70_synthetic_exact_reference.py', 'run_f70_synthetic_exact_reference.py']
PRE_FILES = ['F70S_OWNER_SCOPE_AMENDMENT_RECORD.json', 'F70S_SYNTHETIC_EXACT_CONTRACT.json',
             'F70S_PUBLIC_CASES.json', 'F70S_EXPECTED_PUBLIC_RESULTS.json',
             'F70S_EXPECTED_TEST_IDS.txt', 'F70S_DESIGN_AND_IMPLEMENTATION_PLAN_KO.md']
PIN_FILES = SOURCE_FILES + PRE_FILES + ['F70S_PREIMPLEMENTATION_SEAL.json']
_GUARD = None
_LAST_RECORDS = []

class GateError(ValueError):
  """Fixed diagnostic only."""

def require(ok, code):
  if not ok:
    raise GateError(code)

def digest(raw):
  return hashlib.sha256(raw).hexdigest()

def strict_json(raw):
  def unique(pairs):
    result = {}
    for key, value in pairs:
      require(key not in result, 'F70S_JSON')
      result[key] = value
    return result
  try:
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(GateError('F70S_JSON')))
  except (UnicodeError, json.JSONDecodeError) as error:
    raise GateError('F70S_JSON') from error

def verify_pins(root, pins):
  require(type(pins) is dict and set(pins) == {'identity', 'files', 'preimplementation_seal_sha256'}, 'F70S_PINS')
  require(pins['identity'] == 'F70S_SOURCE_PINS_V1' and type(pins['files']) is list, 'F70S_PINS')
  require(not root.is_symlink() and root.is_dir(), 'F70S_PINS')
  entries = pins['files']
  require(all(type(e) is dict and set(e) == {'name', 'sha256', 'bytes'} and type(e['name']) is str for e in entries), 'F70S_PINS')
  names = [e['name'] for e in entries]
  require(len(names) == len(set(names)) == len(PIN_FILES) and set(names) == set(PIN_FILES), 'F70S_PINS')
  for entry in entries:
    require(type(entry['sha256']) is str and re.fullmatch('[0-9a-f]{64}', entry['sha256']) is not None and
            type(entry['bytes']) is int and entry['bytes'] >= 0, 'F70S_PINS')
    path = root / entry['name']
    require(path.is_file() and not path.is_symlink() and path.resolve().parent == root.resolve(), 'F70S_PINS')
    raw = path.read_bytes()
    require(len(raw) == entry['bytes'] and digest(raw) == entry['sha256'], 'F70S_PINS')
  raw = (root / 'F70S_PREIMPLEMENTATION_SEAL.json').read_bytes()
  require(digest(raw) == pins['preimplementation_seal_sha256'], 'F70S_PINS')
  seal = strict_json(raw)
  require(type(seal) is dict and type(seal.get('files')) is list, 'F70S_PINS')
  refs = seal['files']
  require(len(refs) == len(PRE_FILES) and {e['name'] for e in refs} == set(PRE_FILES), 'F70S_PINS')
  for entry in refs:
    data = (root / entry['name']).read_bytes()
    require(digest(data) == entry['sha256'] and len(data) == entry['bytes'], 'F70S_PINS')

def validate_discovery(actual, expected):
  require(bool(expected) and bool(actual) and len(actual) == len(set(actual)) and
          len(expected) == len(set(expected)) and len(actual) == len(expected) and set(actual) == set(expected), 'F70S_DISCOVERY')

def validate_outcome(expected, started, completed, successes, bad_statuses):
  validate_discovery(started, expected)
  validate_discovery(completed, expected)
  validate_discovery(successes, expected)
  require(not bad_statuses, 'F70S_TEST_OUTCOME')

def validate_private_directory(path):
  require(path.is_dir() and not path.is_symlink(), 'F70S_OUTPUT_SECURITY')
  st = path.stat()
  require(st.st_uid == os.getuid() and stat.S_IMODE(st.st_mode) == 0o700, 'F70S_OUTPUT_SECURITY')

class IOFence:
  def __init__(self, root, test_temp):
    self.root = root.resolve()
    self.test_temp = Path(test_temp).resolve()
    self.allowed_files = {self.root / name for name in PIN_FILES + ['F70S_SOURCE_PINS.json']}
    self.standard = Path(sysconfig.get_path('stdlib')).resolve()
    self.last_denied_read_class = None
    self.counts = {'denied_read_requests': 0, 'denied_external_requests': 0, 'denied_import_requests': 0,
                   'successful_private_payload_reads': 0, 'controller_calls': 0, 'runtime_calls': 0}

  def assert_read_allowed(self, path):
    p = Path(path).resolve()
    if p in self.allowed_files or self.test_temp == p or self.test_temp in p.parents or self.standard in p.parents:
      return
    self.last_denied_read_class = (
      'own_cached_bytecode' if self.root in p.parents and '__pycache__' in p.parts
      else 'own_unregistered_file' if self.root in p.parents else 'outside_registered_roots'
    )
    self.counts['denied_read_requests'] += 1
    raise GateError('F70S_FORBIDDEN_IO')

  def assert_external_allowed(self, action):
    self.counts['denied_external_requests'] += 1
    raise GateError('F70S_FORBIDDEN_EXTERNAL')

  def assert_import_allowed(self, name):
    top = name.split('.')[0]
    if top in {'openpilot', 'opendbc', 'cereal', 'panda'} or (top not in sys.stdlib_module_names and top not in
       {'f70_synthetic_exact_reference', 'f70_synthetic_exact_audit', 'test_f70_synthetic_exact_reference', 'run_f70_synthetic_exact_reference'}):
      self.counts['denied_import_requests'] += 1
      raise GateError('F70S_FORBIDDEN_IMPORT')

  def audit(self, event, args):
    if event == 'open':
      name = args[0]
      if type(name) is int:
        require(name in (0, 1, 2), 'F70S_FORBIDDEN_IO')
        return
      self.assert_read_allowed(name)
      mode = args[1]
      flags = args[2]
      writing = (
        (isinstance(mode, str) and any(c in mode for c in 'wax+')) or
        (type(flags) is int and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))
      )
      if writing:
        path = Path(name).resolve()
        require(self.test_temp == path or self.test_temp in path.parents, 'F70S_FORBIDDEN_IO')
    elif event == 'import':
      self.assert_import_allowed(args[0])
    elif event in {'subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn', 'ctypes.dlopen'} or event.startswith('socket.'):
      self.assert_external_allowed(event)

def get_guard():
  require(_GUARD is not None, 'F70S_GUARD_MISSING')
  return _GUARD

class ActualResult(unittest.TestResult):
  def __init__(self):
    super().__init__()
    self.started_ids = []
    self.completed_ids = []
    self.success_ids = []
    self.bad_statuses = []
    self.records = []

  def startTest(self, test):
    super().startTest(test)
    self.started_ids.append(test.id())

  def stopTest(self, test):
    self.completed_ids.append(test.id())
    super().stopTest(test)

  def addSuccess(self, test):
    self.success_ids.append(test.id())
    self.records.append({'id': test.id(), 'status': 'PASS'})

  def bad(self, test, status):
    self.bad_statuses.append(status)
    self.records.append({'id': test.id(), 'status': status})

  def addFailure(self, test, err):
    self.bad(test, 'FAIL')

  def addError(self, test, err):
    self.bad(test, 'ERROR')

  def addSkip(self, test, reason):
    self.bad(test, 'SKIP')

  def addExpectedFailure(self, test, err):
    self.bad(test, 'XFAIL')

  def addUnexpectedSuccess(self, test):
    self.bad(test, 'XPASS')

class PinnedSourceLoader(importlib.machinery.SourceFileLoader):
  def __init__(self, name, path, expected_sha256):
    super().__init__(name, str(path))
    self.expected_sha256 = expected_sha256

  def get_code(self, fullname):
    require(fullname == self.name, 'F70S_PINS')
    raw = Path(self.path).read_bytes()
    require(digest(raw) == self.expected_sha256, 'F70S_PINS')
    return self.source_to_code(raw, self.path)

def load_pinned_source(root, name, pins):
  require(name+'.py' in SOURCE_FILES, 'F70S_PINS')
  path = root / (name+'.py')
  require(path.is_file() and not path.is_symlink(), 'F70S_PINS')
  expected = next(e for e in pins['files'] if e['name'] == name+'.py')
  loader = PinnedSourceLoader(name, path, expected['sha256'])
  spec = importlib.util.spec_from_loader(name, loader)
  if spec is None:
    raise GateError('F70S_PINS')
  module = importlib.util.module_from_spec(spec)
  sys.modules[name] = module
  loader.exec_module(module)
  return module


def flattened(suite):
  result = []
  for item in suite:
    result.extend(flattened(item) if isinstance(item, unittest.TestSuite) else [item])
  return result

def canonical(value):
  return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()

def main():
  global _GUARD, _LAST_RECORDS
  root = Path(__file__).resolve().parent
  pins = strict_json((root / 'F70S_SOURCE_PINS.json').read_bytes())
  verify_pins(root, pins)
  contract = strict_json((root / 'F70S_SYNTHETIC_EXACT_CONTRACT.json').read_bytes())
  require(contract['contract_id'] == 'F70_SYNTHETIC_EXACT_INTERVAL_V1' and contract['scope'] == 'VEHICLE_AGNOSTIC_SOFTWARE_ONLY', 'F70S_CONTRACT')
  with tempfile.TemporaryDirectory(prefix='f70s-private-') as temp:
    validate_private_directory(Path(temp))
    _GUARD = IOFence(root, temp)
    sys.addaudithook(_GUARD.audit)
    sys.path.insert(0, str(root))
    primary = load_pinned_source(root, 'f70_synthetic_exact_reference', pins)
    audit = load_pinned_source(root, 'f70_synthetic_exact_audit', pins)
    tests = load_pinned_source(root, 'test_f70_synthetic_exact_reference', pins)
    suite = unittest.defaultTestLoader.loadTestsFromModule(tests)
    expected = (root / 'F70S_EXPECTED_TEST_IDS.txt').read_text().splitlines()
    discovered = [test.id() for test in flattened(suite)]
    validate_discovery(discovered, expected)
    actual = ActualResult()
    suite.run(actual)
    _LAST_RECORDS = actual.records
    validate_outcome(expected, actual.started_ids, actual.completed_ids, actual.success_ids, actual.bad_statuses)
    corpus = strict_json((root / 'F70S_PUBLIC_CASES.json').read_bytes())
    golden = strict_json((root / 'F70S_EXPECTED_PUBLIC_RESULTS.json').read_bytes())
    require(corpus['case_count'] == len(corpus['cases']) == len(golden['expected']), 'F70S_CASES')
    require(len({x['context_id'] for x in corpus['cases']}) == len(corpus['cases']), 'F70S_CASES')
    case_results = []
    for request, want in zip(corpus['cases'], golden['expected'], strict=True):
      require(request['context_id'] == want['context_id'], 'F70S_CASES')
      first = primary.canonical_summary(request)
      second = audit.canonical_summary(request)
      require(first == second, 'F70S_INDEPENDENT_MISMATCH')
      result = strict_json(first)
      require(all(result[k] == v for k, v in want.items() if k != 'context_id'), 'F70S_GOLDEN')
      case_results.append({'case_id': request['context_id'], 'result': result, 'canonical_sha256': digest(first)})
    summary = {'identity': 'F70S_LOCAL_SYNTHETIC_VERIFICATION_V1', 'contract_sha256': digest((root / 'F70S_SYNTHETIC_EXACT_CONTRACT.json').read_bytes()),
               'test_ids': sorted(discovered), 'started_ids': sorted(actual.started_ids), 'completed_ids': sorted(actual.completed_ids),
               'test_count': len(expected), 'PASS': len(actual.success_ids), 'FAIL': 0, 'ERROR': 0, 'SKIP': 0, 'XFAIL': 0, 'XPASS': 0,
               'records': sorted(actual.records, key=lambda x: x['id']), 'cases': case_results, 'guard_counts': _GUARD.counts,
               'runtime_authority': 'NONE', 'candidate_output': None, 'project_r_budget_resolved': False,
               'vehicle_performance_evaluated': False, 'F71_authorized': False}
    data = canonical(summary)
  sys.stdout.buffer.write(data)

def sanitized_exception_hook(_kind, _value, _trace):
  sys.stdout.write(json.dumps({'status': 'FAIL_CLOSED', 'code': 'F70S_UNEXPECTED_FAILURE'}, sort_keys=True)+'\n')

if __name__ == '__main__':
  sys.excepthook = sanitized_exception_hook
  sys.modules.setdefault('run_f70_synthetic_exact_reference', sys.modules[__name__])
  try:
    main()
  except GateError as error:
    sys.stdout.write(json.dumps(
      {'status': 'FAIL_CLOSED', 'code': str(error), 'records': _LAST_RECORDS,
       'denial_class': _GUARD.last_denied_read_class if _GUARD is not None else None},
      sort_keys=True,
    )+'\n')
    raise SystemExit(1) from None
