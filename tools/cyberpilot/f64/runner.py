"""Public synthetic evaluation only. No Controller/log/Plant execution."""
import argparse
import hashlib
import io
import json
import os
import stat
from pathlib import Path
import re
import sys
import unittest

from tools.cyberpilot.f64 import isolation

isolation.require_active()
GUARDED_IMPORT_VERIFIED = True
from tools.cyberpilot.f64 import metrics, oracle, source

ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = 'artifacts/f64/preregistered_contract.json'
CONTRACT_SHA = '54f3832533034711e52f3e87cb91912e15ef19bceb2a9fe0364e13ca0f733811'
F60_PATH = 'tools/cyberpilot/synthetic_command_rate_attribution_v1.py'
F60_SHA = '9ff1a333dcc45d14577246651f88b28d5935a6dce954b308bb90b1d3f4ccf018'


def verify_f60_pin(root):
  source.need(hashlib.sha256((Path(root)/F60_PATH).read_bytes()).hexdigest() == F60_SHA, 'F64_SOURCE_PIN')
  return True


def verify_contract():
  data = (ROOT/CONTRACT_PATH).read_bytes()
  source.need(hashlib.sha256(data).hexdigest() == CONTRACT_SHA, 'F64_CONTRACT_PIN')
  return json.loads(data)


def derive_seeds(commit):
  source.need(type(commit) is str and re.fullmatch('[0-9a-f]{40}', commit) is not None, 'F64_SOURCE_PIN')
  data = hashlib.sha256(('F64_HOLDOUT_V1:'+commit).encode('ascii')).digest()
  return [int.from_bytes(data[:8], 'big'), int.from_bytes(data[8:16], 'big')]


def require_equal(actual, expected):
  source.need(actual == expected, 'F64_ORACLE_MISMATCH')


def case_records(seeds):
  result = []
  for seed_index, seed in enumerate(seeds):
    for family in source.FAMILIES:
      spec = {'family': family, 'seed': seed, 'count': 17, 'start_ns': 0}
      result.append({'id': family+'_'+str(seed_index), 'data': source.generate(spec), 'spec': spec, 'expected_error': None})
  base = json.loads(source.generate({'family': 'constant', 'seed': 0, 'count': 17, 'start_ns': 0}))
  changes = [
    ('missing_field', 'F64_SCHEMA_KEYS'), ('unexpected_field', 'F64_SCHEMA_KEYS'), ('wrong_type', 'F64_VALUE_TYPE'),
    ('length_mismatch', 'F64_LENGTH'), ('out_of_range', 'F64_VALUE_RANGE'), ('duplicate_time', 'F64_TIME_DUPLICATE'),
    ('reversed_time', 'F64_TIME_ORDER'), ('time_gap', 'F64_TIME_GAP')]
  for name, error in changes:
    x = json.loads(json.dumps(base))
    if name == 'missing_field':
      del x['unit']
    elif name == 'unexpected_field':
      x['unknown'] = 0
    elif name == 'wrong_type':
      x['numerators'][0] = True
    elif name == 'length_mismatch':
      x['numerators'].pop()
    elif name == 'out_of_range':
      x['numerators'][0] = x['denominator']+1
    elif name == 'duplicate_time':
      x['times_ns'][1] = 0
    elif name == 'reversed_time':
      x['times_ns'][2] = 1
    else:
      x['times_ns'][1] = 10000001
    result.append({'id': 'invalid_'+name, 'data': source.canonical(x), 'spec': None, 'expected_error': error})
  return result


def evaluate_cases(seeds, split, source_proof=None):
  if split == 'HOLDOUT':
    from tools.cyberpilot.f64.entry import proof_is_bound
    source.need(proof_is_bound(source_proof), 'F64_SOURCE_PIN')
  verify_contract()
  verify_f60_pin(ROOT)
  records, manifest, files = [], [], {}
  with isolation.Guard() as guard:
    for case in case_records(seeds):
      data = case['data']
      name = split.lower()+'__'+case['id']+'.json'
      files[name] = data
      entry = {'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
               'source_specification': case['spec'], 'expected_error': case['expected_error']}
      manifest.append(entry)
      if case['expected_error'] is None:
        actual, expected = metrics.compute(data), oracle.compute(data)
        require_equal(actual, expected)
        compatibility = metrics.check_f60(data)
        records.append({'id': case['id'], 'status': 'PASS', 'production': actual, 'oracle': expected,
                        'f60_numeric_compatibility': compatibility})
      else:
        try:
          source.decode_source(data)
        except source.ContractError as exc:
          require_equal(str(exc), case['expected_error'])
        else:
          raise source.ContractError('F64_ORACLE_MISMATCH')
        records.append({'id': case['id'], 'status': 'PASS_EXPECTED_REJECTION', 'error': case['expected_error']})
    require_equal(guard.counts, dict.fromkeys(guard.counts, 0))
  summary = {'identity': 'F64_SYNTHETIC_CONTRACT_RUN_V1', 'split': split, 'contract_sha256': CONTRACT_SHA,
             'seeds': seeds, 'records': records, 'case_count': len(records), 'valid_cases': 14, 'invalid_cases': 8,
             'all_contract_checks_pass': True, 'controller_calls': 0, 'isolation_counts': guard.counts,
             'candidate_output': None, 'runtime_authority': 'NONE', 'r_budget': 'R_BUDGET_UNRESOLVED',
             'SOURCE_SCHEMA_UNQUALIFIED': 6000, 'performance_qualified': False, 'source_proof': source_proof,
             'controller_call_evidence': 'REVIEWED_GRAPH_AND_NO_CONTROLLER_MODULE_LOADED_UNDER_SENTINEL'}
  return {'summary': summary, 'manifest': manifest, 'files': files}


def write_bundle(output, value):
  output = Path(output)
  source.need(output.is_absolute() and '..' not in output.parts and output.name not in ('', '.', '..'), 'F64_SPEC')
  flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
  parent = os.open('/', flags)
  child = None
  try:
    for part in output.parent.parts[1:]:
      new = os.open(part, flags, dir_fd=parent)
      os.close(parent)
      parent = new
    info = os.fstat(parent)
    source.need(info.st_uid == os.geteuid() and info.st_mode & 0o022 == 0, 'F64_SPEC')
    try:
      os.mkdir(output.name, 0o700, dir_fd=parent)
    except FileExistsError:
      raise source.ContractError('F64_EXISTING_OUTPUT') from None
    child = os.open(output.name, flags, dir_fd=parent)
    child_info = os.fstat(child)
    source.need(stat.S_IMODE(child_info.st_mode) == 0o700 and child_info.st_uid == os.geteuid(), 'F64_SPEC')
    all_files = {**value['files'], 'fixture_manifest.json': source.canonical(value['manifest']),
                 'metric_oracle_results.json': source.canonical(value['summary'])}
    inventory = [{'path': n, 'bytes': len(d), 'sha256': hashlib.sha256(d).hexdigest()} for n, d in sorted(all_files.items())]
    all_files['SHA256_MANIFEST.json'] = source.canonical(inventory)
    for name, data in sorted(all_files.items()):
      source.need(re.fullmatch('[A-Za-z0-9_]+[.]json', name) is not None, 'F64_SPEC')
      fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=child)
      with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
    check = os.open(output.name, flags, dir_fd=parent)
    try:
      actual = os.fstat(check)
      source.need((actual.st_dev, actual.st_ino) == (child_info.st_dev, child_info.st_ino), 'F64_SPEC')
    finally:
      os.close(check)
  finally:
    if child is not None:
      os.close(child)
    os.close(parent)


class Ledger(unittest.TestResult):
  def __init__(self):
    super().__init__()
    self.started, self.finished, self.records = [], [], []

  def startTest(self, test):
    self.started.append(test.id())
    super().startTest(test)

  def stopTest(self, test):
    self.finished.append(test.id())
    super().stopTest(test)

  def addSuccess(self, test):
    super().addSuccess(test)
    self.records.append({'id': test.id(), 'status': 'PASS'})

  def addFailure(self, test, err):
    super().addFailure(test, err)
    self.records.append({'id': test.id(), 'status': 'FAIL'})

  def addError(self, test, err):
    super().addError(test, err)
    self.records.append({'id': test.id(), 'status': 'ERROR'})


def run_tests():
  sink = io.StringIO()
  # unittest internals may retain synthetic traceback details in memory, never CLI output.
  with isolation.Guard() as guard:
    suite = unittest.defaultTestLoader.loadTestsFromName('tools.cyberpilot.tests.test_synthetic_contract_oracle_f64')
    result = Ledger()
    from contextlib import redirect_stdout, redirect_stderr
    with redirect_stdout(sink), redirect_stderr(sink):
      suite.run(result)
    expected = (ROOT/'artifacts/f64/public_test_ids.txt').read_text().splitlines()
    source.need(result.started == result.finished == expected and
                len(expected) == len(set(expected)) > 0 and
                result.records == [{'id': i, 'status': 'PASS'} for i in expected] and
                not result.failures and not result.errors and not result.skipped and
                not result.expectedFailures and not result.unexpectedSuccesses, 'F64_ORACLE_MISMATCH')
  return {'tests': len(result.records), 'records': result.records, 'guard_counts': guard.counts,
          'controller_calls': 0, 'output_capture_empty': sink.getvalue() == ''}


class PrivateParser(argparse.ArgumentParser):
  def error(self, message):
    raise source.ContractError('F64_SPEC')


def main(argv=None, source_proof: dict | None = None):
  parser = PrivateParser(allow_abbrev=False)
  parser.add_argument('--public', action='store_true')
  parser.add_argument('--pre-holdout')
  parser.add_argument('--output', type=Path)
  parser.add_argument('--tests', action='store_true')
  args = parser.parse_args(argv)
  verify_contract()
  verify_f60_pin(ROOT)
  static = isolation.inspect_project(ROOT)
  source.need(not static['controller_dependencies'] and not static['unapproved_imports'] and
              not static['unsafe_dynamic_calls'], 'F64_ISOLATION_IMPORT')
  if args.tests:
    print(source.canonical(run_tests()).decode().rstrip())
    return
  source.need(args.output is not None and (args.public != bool(args.pre_holdout)), 'F64_SPEC')
  if args.pre_holdout:
    from tools.cyberpilot.f64.entry import proof_is_bound
    source.need(type(source_proof) is dict and proof_is_bound(source_proof) and
                source_proof['pre_holdout_commit'] == args.pre_holdout, 'F64_SOURCE_PIN')
  seeds = [0, 1] if args.public else derive_seeds(args.pre_holdout)
  value = evaluate_cases(seeds, 'PUBLIC' if args.public else 'HOLDOUT', source_proof)
  write_bundle(args.output, value)
  print(source.canonical({'cases': value['summary']['case_count'], 'status': 'CONTRACT_CHECKS_PASS_R_UNRESOLVED',
                          'summary_sha256': hashlib.sha256(source.canonical(value['summary'])).hexdigest()}).decode().rstrip())


if __name__ == '__main__':
  try:
    main()
  except Exception:
    print('F64_EXECUTION_BLOCKED', file=sys.stderr)
    raise SystemExit(1) from None
