"""F65 trusted Git bootstrap then Controller-free guarded test/evaluation paths."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import unittest

from tools.cyberpilot.f64.isolation import Guard, active, inspect_project, inspect_text

with Guard():
  from tools.cyberpilot import synthetic_source_separation_f65 as core

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_SHA = '4901195aee68de00dd9b4d978f774875405923b8b2bfe0c65dd57b87743ab737'
MANIFEST = 'artifacts/f65/pre_holdout_source_manifest.json'
_PROOFS = {}
sys.modules.setdefault('tools.cyberpilot.run_f65_source_separation_v1', sys.modules[__name__])


def contract_check():
  core.need(hashlib.sha256((ROOT/'artifacts/f65/preregistered_contract.json').read_bytes()).hexdigest() == CONTRACT_SHA,
            'F65_CONTRACT_PIN')


def validate_manifest_inventory(manifest, required):
  core.need(type(manifest) is dict and type(manifest.get('files')) is list and bool(required), 'F65_SOURCE_PIN')
  seen = set()
  for item in manifest['files']:
    core.need(type(item) is dict and set(item) == {'path', 'bytes', 'sha256'}, 'F65_SOURCE_PIN')
    rel = item['path']
    core.need(type(rel) is str and not rel.startswith('/') and '\\' not in rel and
              '..' not in Path(rel).parts and rel not in seen and
              type(item['bytes']) is int and item['bytes'] >= 0 and
              type(item['sha256']) is str and re.fullmatch('[0-9a-f]{64}', item['sha256']) is not None,
              'F65_SOURCE_PIN')
    seen.add(rel)
  core.need(seen == set(required), 'F65_SOURCE_PIN')
  return True


def validate_bundle_inventory(entries, required):
  core.need(type(entries) is list, 'F65_BUNDLE_MISMATCH')
  result = {}
  for item in entries:
    core.need(type(item) is dict and set(item) == {'path', 'bytes', 'sha256'}, 'F65_BUNDLE_MISMATCH')
    name = item['path']
    core.need(type(name) is str and re.fullmatch('[A-Za-z0-9_]+[.]json', name) is not None and
              name not in result and type(item['bytes']) is int and item['bytes'] >= 0 and
              type(item['sha256']) is str and re.fullmatch('[0-9a-f]{64}', item['sha256']) is not None,
              'F65_BUNDLE_MISMATCH')
    result[name] = item
  core.need(set(result) == set(required), 'F65_BUNDLE_MISMATCH')
  return result


def verify_precommit(commit):
  core.need(type(commit) is str and re.fullmatch('[0-9a-f]{40}', commit) is not None, 'F65_SOURCE_PIN')
  if active():
    core.need(commit in _PROOFS, 'F65_SOURCE_PIN')
    return _PROOFS[commit]
  def git(*args):
    p = subprocess.run(['/usr/bin/git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
                        '-c', 'core.hooksPath=/dev/null', '-C', str(ROOT), *args], capture_output=True, check=False)
    core.need(p.returncode == 0, 'F65_SOURCE_PIN')
    return p.stdout
  core.need(git('rev-parse', commit+'^{commit}').decode().strip() == commit, 'F65_SOURCE_PIN')
  core.need(not git('status', '--porcelain=v1', '--untracked-files=all').strip(), 'F65_SOURCE_PIN')
  git('merge-base', '--is-ancestor', commit, 'HEAD')
  frozen = git('show', commit+':'+MANIFEST)
  core.need((ROOT/MANIFEST).read_bytes() == frozen, 'F65_SOURCE_PIN')
  baseline = '04ae0f6644c7e94b8ed601c46fc45ccff03d0476'
  git('merge-base', '--is-ancestor', baseline, commit)
  added = git('diff', '--name-status', baseline, commit).decode().splitlines()
  exact_new = {'tools/cyberpilot/synthetic_source_separation_f65.py', 'tools/cyberpilot/run_f65_source_separation_v1.py',
               'tools/cyberpilot/tests/test_synthetic_source_separation_f65.py',
               '.github/workflows/cyberpilot-f65-source-separation.yaml',
               'docs/cyberpilot/changes/f65-source-separation-contract.md',
               'docs/cyberpilot/changes/f65-source-separation.md'}
  paths = []
  for line in added:
    kind, rel = line.split('\t')
    core.need(kind == 'A' and (rel in exact_new or rel.startswith('artifacts/f65/')), 'F65_SOURCE_PIN')
    paths.append(rel)
  core.need(exact_new <= set(paths), 'F65_SOURCE_PIN')
  prior = git('diff', '--name-only', '588d6b21c21089065a7d9165d6e7a438e8aa6297', baseline).decode().splitlines()
  required = set(paths + prior + ['tools/cyberpilot/cli_security_f51.py', 'tools/cyberpilot/__init__.py',
                                 'AGENTS.md', '.editorconfig', 'pyproject.toml', 'uv.lock']) - {MANIFEST}
  validate_manifest_inventory(json.loads(frozen), required)
  seen = set()
  for item in json.loads(frozen)['files']:
    rel = item['path']
    core.need(type(rel) is str and not rel.startswith('/') and '..' not in Path(rel).parts and
              '\\' not in rel and rel not in seen, 'F65_SOURCE_PIN')
    seen.add(rel)
    p = ROOT/rel
    core.need(p.is_file() and not p.is_symlink() and p.stat().st_size == item['bytes'] and
              hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256'] and
              hashlib.sha256(git('show', commit+':'+rel)).hexdigest() == item['sha256'], 'F65_SOURCE_PIN')
  proof = {'pre_holdout_commit': commit, 'source_manifest_sha256': hashlib.sha256(frozen).hexdigest(),
           'frozen_files': len(seen), 'source_bound': True}
  _PROOFS[commit] = proof
  return proof


def derive_seeds(commit):
  core.need(type(commit) is str and re.fullmatch('[0-9a-f]{40}', commit) is not None, 'F65_SOURCE_PIN')
  d = hashlib.sha256(('F65_HOLDOUT_V1:'+commit).encode('ascii')).digest()
  return [int.from_bytes(d[:8], 'big'), int.from_bytes(d[8:16], 'big')]


def static_gate():
  record = inspect_project(ROOT)
  core.need(not record['controller_dependencies'] and not record['unapproved_imports'] and
            not record['unsafe_dynamic_calls'], 'F65_ISOLATION')
  for rel in ('tools/cyberpilot/synthetic_source_separation_f65.py', 'tools/cyberpilot/run_f65_source_separation_v1.py'):
    core.need(inspect_text((ROOT/rel).read_text())['allowed'], 'F65_ISOLATION')
  return {'frozen_f64_graph': record, 'new_modules_checked': 2, 'controller_dependencies': []}


def exposed_f64():
  values = []
  for folder in ('public', 'holdout'):
    base = ROOT/'artifacts/f64'/folder
    for item in json.loads((base/'fixture_manifest.json').read_bytes()):
      if item['expected_error'] is None:
        data = (base/item['path']).read_bytes()
        core.need(hashlib.sha256(data).hexdigest() == item['sha256'], 'F65_SOURCE_PIN')
        values.append({'legacy_file': folder+'/'+item['path'], 'signal_sha256': core.signal_hash(data)})
  return values


def exposed_development():
  contract_check()
  contract = json.loads((ROOT/'artifacts/f65/preregistered_contract.json').read_bytes())
  result = []
  for seed in (int(v) for v in contract['development_exposed_seeds']):
    for split in ('PUBLIC', 'EVALUATION'):
      for record, _ in records([seed], split):
        result.append({'exposed_spec': record['spec'], 'signal_sha256': record['signal_sha256']})
  return result


def records(seeds, split):
  result = []
  for index, seed in enumerate(seeds):
    for family in core.FAMILIES:
      spec = {'family': family, 'seed': seed, 'split': split, 'count': 17}
      data = core.generate(spec)
      result.append(({'path': split.lower()+'__'+family+'_'+str(index)+'.json', 'spec': spec,
                      'sha256': hashlib.sha256(data).hexdigest(), 'signal_sha256': core.signal_hash(data)}, data))
  return result


def evaluate(split, seeds, proof=None):
  if split == 'EVALUATION':
    core.need(type(proof) is dict and _PROOFS.get(proof.get('pre_holdout_commit')) is proof, 'F65_SOURCE_PIN')
  core.need(split in ('PUBLIC', 'EVALUATION') and len(seeds) == 2, 'F65_SPEC')
  contract_check()
  from tools.cyberpilot.f64 import metrics, oracle
  with Guard() as guard:
    data_records = records(seeds, split)
    current = [r['signal_sha256'] for r, _ in data_records]
    public = records([0, 1], 'PUBLIC')
    legacy = exposed_f64()
    development = exposed_development()
    exposed = {r['signal_sha256'] for r, _ in public} | {r['signal_sha256'] for r in legacy} | {r['signal_sha256'] for r in development}
    overlap = len(set(current) & exposed) if split == 'EVALUATION' else 0
    metric_records, files = [], {}
    for record, data in data_records:
      actual, expected = metrics.compute(data), oracle.compute(data)
      core.need(actual == expected, 'F65_ORACLE_MISMATCH')
      metric_records.append({'path': record['path'], 'production': actual, 'oracle': expected})
      files[record['path']] = data
    core.need(len(current) == len(set(current)) == 14, 'F65_DUPLICATE_SOURCE')
    core.need(not any(guard.counts.values()), 'F65_ISOLATION')
    result = {'status': core.STATUS if split == 'EVALUATION' else 'F65_PUBLIC_CHECKS_PASS',
              'verified_cases': 14, 'source_overlap': overlap, 'metric_mismatches': 0, 'controller_calls': 0,
              'candidate_output': None, 'r_budget': 'R_BUDGET_UNRESOLVED', 'runtime': 'NO_GO',
              'SOURCE_SCHEMA_UNQUALIFIED': 6000, 'NO_ADMISSIBLE_NEXT_CANDIDATE': True,
              'selected_candidate': None, 'selected_policy': None, 'Vehicle_authority': 'NONE',
              'split': split, 'seeds': seeds, 'source_proof': proof, 'contract_sha256': CONTRACT_SHA,
              'records': metric_records, 'guard_counts': guard.counts,
              'legacy_exposed_fixture_count': len(legacy), 'development_exposed_fixture_count': len(development),
              'actual_signal_fingerprint': True}
    if split == 'EVALUATION':
      core.final_gate(result)
    files['final_result.json'] = core.canonical(result)
  return {'summary': result, 'manifest': [r for r, _ in data_records], 'files': files}


def safe_read(directory, name):
  core.need(type(name) is str and re.fullmatch('[A-Za-z0-9_]+[.]json', name) is not None, 'F65_BUNDLE_PATH')
  flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
  directory = Path(directory).absolute()
  core.need('..' not in directory.parts, 'F65_BUNDLE_PATH')
  descriptor = os.open('/', flags)
  try:
    for part in directory.parts[1:]:
      next_fd = os.open(part, flags, dir_fd=descriptor)
      os.close(descriptor)
      descriptor = next_fd
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=descriptor)
    with os.fdopen(fd, 'rb') as f:
      info = os.fstat(f.fileno())
      core.need(stat.S_ISREG(info.st_mode) and info.st_size <= 1000000, 'F65_BUNDLE_PATH')
      return f.read(1000001)
  except OSError:
    raise core.GateError('F65_BUNDLE_PATH') from None
  finally:
    os.close(descriptor)


def verify_bundle(directory):
  contract_check()
  result = json.loads(safe_read(directory, 'final_result.json'))
  core.final_gate(result)
  core.need(result['split'] == 'EVALUATION', 'F65_GATE_STATUS')
  proof = _PROOFS.get(result.get('source_proof', {}).get('pre_holdout_commit'))
  if proof is None:
    raise core.GateError('F65_SOURCE_PIN')
  core.need(result['source_proof'] == proof, 'F65_SOURCE_PIN')
  core.need(result.get('seeds') == derive_seeds(proof['pre_holdout_commit']), 'F65_SOURCE_PIN')
  manifest = json.loads(safe_read(directory, 'fixture_manifest.json'))
  inventory = json.loads(safe_read(directory, 'SHA256_MANIFEST.json'))
  required = {v['path'] for v, _ in records(result['seeds'], 'EVALUATION')} | {
    'final_result.json', 'fixture_manifest.json', 'metric_oracle_results.json'}
  expected_inventory = validate_bundle_inventory(inventory, required)
  for name, item in expected_inventory.items():
    data = safe_read(directory, name)
    core.need(len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'], 'F65_BUNDLE_MISMATCH')
  expected = evaluate('EVALUATION', result['seeds'], proof)
  core.need(manifest == expected['manifest'] and result == expected['summary'], 'F65_BUNDLE_MISMATCH')
  core.need(safe_read(directory, 'metric_oracle_results.json') == core.canonical(result), 'F65_BUNDLE_MISMATCH')
  for item in manifest:
    data = safe_read(directory, item['path'])
    core.verify_record(item, data)
    core.need(data == expected['files'][item['path']], 'F65_BUNDLE_MISMATCH')
  return True


def run_tests():
  from tools.cyberpilot.f64.runner import Ledger
  expected = (ROOT/'artifacts/f65/test_ids.txt').read_text().splitlines()
  suite = unittest.defaultTestLoader.loadTestsFromName('tools.cyberpilot.tests.test_synthetic_source_separation_f65')
  ledger = Ledger()
  with Guard() as guard:
    suite.run(ledger)
  core.need(ledger.started == ledger.finished == expected and len(expected) == len(set(expected)) and
            ledger.records == [{'id': x, 'status': 'PASS'} for x in expected] and
            not ledger.failures and not ledger.errors and not ledger.skipped and
            not ledger.expectedFailures and not ledger.unexpectedSuccesses, 'F65_TEST_FAILURE')
  return {'test_count': len(expected), 'records': ledger.records, 'guard_counts': guard.counts, 'controller_calls': 0}


class Parser(argparse.ArgumentParser):
  def error(self, message):
    raise core.GateError('F65_SPEC')


def main():
  parser = Parser(allow_abbrev=False)
  parser.add_argument('--tests', action='store_true')
  parser.add_argument('--public', action='store_true')
  parser.add_argument('--pre-holdout')
  parser.add_argument('--verify-bundle', type=Path)
  parser.add_argument('--output', type=Path)
  args = parser.parse_args()
  proof = None
  if args.pre_holdout:
    proof = verify_precommit(args.pre_holdout)
  elif args.verify_bundle:
    # Failed statuses are rejected before any derivation or source claim.
    with Guard():
      doc = json.loads(safe_read(args.verify_bundle, 'final_result.json'))
      core.final_gate(doc)
    proof = verify_precommit(doc.get('source_proof', {}).get('pre_holdout_commit'))
  with Guard():
    static_gate()
    contract_check()
    if args.tests:
      print(core.canonical(run_tests()).decode().rstrip())
    elif args.verify_bundle:
      verify_bundle(args.verify_bundle)
      print(core.STATUS)
    else:
      core.need(args.output is not None and args.public != bool(args.pre_holdout), 'F65_SPEC')
      if args.pre_holdout:
        core.need(proof is not None, 'F65_SOURCE_PIN')
      seeds = [0, 1] if args.public else derive_seeds(args.pre_holdout)
      value = evaluate('PUBLIC' if args.public else 'EVALUATION', seeds, proof)
      from tools.cyberpilot.f64.runner import write_bundle
      write_bundle(args.output, value)
      print(core.canonical({'status': value['summary']['status'], 'cases': 14,
                            'summary_sha256': hashlib.sha256(core.canonical(value['summary'])).hexdigest()}).decode().rstrip())


if __name__ == '__main__':
  try:
    main()
  except Exception:
    print('F65_GATE_REJECTED', file=sys.stderr)
    raise SystemExit(1) from None
