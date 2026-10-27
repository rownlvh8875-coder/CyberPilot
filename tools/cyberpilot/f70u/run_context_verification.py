"""Exact-head F70U schema, bounded regression and immutable-baseline CI gates."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tools.cyberpilot.f70u.context_contract import ARTIFACTS, ROOT, load_context_contract, validate_context_contract

BASE = 'deeb6442394468b4759081aa74e6e889f78357da'
BRANCH = 'feature/f70u-static-context-binding-contract'
PREREGISTRATION = '71a1dd9ede5b0670fb5590a28a95763ac4b52c55'
PRIOR_WORKFLOW = '.github/workflows/cyberpilot-f70pr-compatibility-reference.yaml'
PRIOR_WORKFLOW_HASH = '8dcb40c5f0676fc946c4354e538323b65868b1f8fce8fc707266f17db989329d'
WORKFLOW = '.github/workflows/cyberpilot-f70u-static-context-contract.yaml'
NEW_MODULE = 'tools.cyberpilot.tests.test_f70u_static_context_contract'
COMPAT_MODULE = 'tools.cyberpilot.tests.test_f70u_reference_compatibility'
PYTHON_FILES = ['tools/cyberpilot/f70u/context_contract.py', 'tools/cyberpilot/f70u/validate_context_contract.py',
                'tools/cyberpilot/f70u/run_context_verification.py', 'tools/cyberpilot/tests/test_f70u_static_context_contract.py',
                'tools/cyberpilot/tests/test_f70u_reference_compatibility.py']
DOCUMENTS = ['docs/cyberpilot/changes/f70u-' + name + '.md' for name in
             ['static-context-binding-contract', 'reference-interface-map', 'platform-candidates', 'owner-static-context-decision-request-ko']]
ARTIFACT_NAMES = ['F70U_REFERENCE_INTERFACE_MAP.json', 'F70U_PLATFORM_CANDIDATES.json', 'static_context_schema.json',
                  'static_context_input_template.json', 'static_context_contract.json', 'static_context_provenance.json',
                  'owner_static_context_decision_request.json', 'context_validation_result.json', 'F70U_FINAL_RESULT.json',
                  'test_ids.txt', 'compatibility_test_ids.txt']
ALLOWED = set(PYTHON_FILES + DOCUMENTS + ['artifacts/f70u/' + name for name in ARTIFACT_NAMES] + [WORKFLOW])


def sha(raw: bytes) -> str:
  return hashlib.sha256(raw).hexdigest()


def git(*args: str) -> bytes:
  return subprocess.check_output(['git', *args], cwd=ROOT)


def git_tree(ref: str) -> dict[str, bytes]:
  result = {}
  for row in git('ls-tree', '-r', '-z', ref).split(b'\0'):
    if row:
      mode, path = row.split(b'\t', 1)
      result[path.decode()] = mode
  return result


def scope(precommit: bool) -> dict[str, Any]:
  head = git('rev-parse', 'HEAD').decode().strip()
  baseline = git_tree(BASE)
  current = git_tree('HEAD')
  assert all(current.get(path) == entry for path, entry in baseline.items()), 'BASELINE_GIT_OID_CHANGED'
  assert subprocess.run(['git', 'merge-base', '--is-ancestor', BASE, 'HEAD'], cwd=ROOT, check=False).returncode == 0, 'BASE_ANCESTOR'
  assert set(current) - set(baseline) <= ALLOWED, 'UNAPPROVED_PATH'
  assert not git('diff', '--check'), 'WHITESPACE'
  for row in git('diff', '--name-status', BASE).decode().splitlines():
    status, path = row.split('\t')
    assert status == 'A' and path in ALLOWED, 'EXISTING_FILE_MODIFIED'
  if not precommit:
    assert set(current) - set(baseline) == ALLOWED, 'EXACT_ADDITION_SET'
    assert not git('status', '--porcelain=v1', '--untracked-files=all'), 'CLEAN_WORKTREE'
  for path in ALLOWED - ({WORKFLOW} if precommit else set()):
    target = ROOT / path
    assert target.is_file() and not target.is_symlink(), 'REGULAR_ADDITION_ONLY'
  if os.environ.get('GITHUB_ACTIONS') == 'true':
    assert not precommit, 'NO_CLOUD_PRECOMMIT_BYPASS'
    assert os.environ['GITHUB_SHA'] == head, 'EXACT_HEAD'
    assert os.environ['GITHUB_REF'] == 'refs/heads/' + BRANCH, 'EXACT_BRANCH'
    implementation = os.environ['F70U_IMPLEMENTATION_COMMIT']
    assert git('rev-parse', 'HEAD^').decode().strip() == implementation, 'CI_PARENT'
    assert git('rev-parse', implementation + '^').decode().strip() == PREREGISTRATION, 'IMPLEMENTATION_PARENT'
    assert git('rev-parse', PREREGISTRATION + '^').decode().strip() == BASE, 'SPEC_PARENT'
    assert git('rev-list', '--count', BASE + '..HEAD').strip() == b'3', 'THREE_COMMITS'
    assert git('diff-tree', '--no-commit-id', '--name-status', '-r', implementation + '..HEAD').decode().strip() == 'A\t' + WORKFLOW
  return {'head': head, 'baseline': BASE, 'baseline_root_tree': git('rev-parse', BASE + '^{tree}').decode().strip(),
          'protected_baseline_entries': len(baseline), 'modified_existing_paths': 0, 'allowed_additions': sorted(ALLOWED)}


def prior_verifier() -> dict[str, Any]:
  raw = (ROOT / PRIOR_WORKFLOW).read_bytes()
  assert sha(raw) == PRIOR_WORKFLOW_HASH, 'PRIOR_WORKFLOW_IMMUTABLE'
  lines = raw.decode().splitlines()
  support = next(lines[i+1].strip() for i, line in enumerate(lines) if line.strip() == 'F70S_SUPPORT_JSON: >-')
  start = next(i+1 for i, line in enumerate(lines) if line.strip() == "python -B - <<'PY'")
  end = next(i for i in range(start, len(lines)) if lines[i].strip() == 'PY')
  source = '\n'.join(line[10:] for line in lines[start:end]) + '\n'
  namespace: dict[str, Any] = {'__name__': 'f70u_hash_pinned_prior_verifier'}
  exec(compile(source, 'immutable_f70pr_verifier', 'exec'), namespace)
  os.environ['F70S_SUPPORT_JSON'] = support
  return namespace


def run(args: list[str], label: str, out: Path, env: dict[str, str] | None = None) -> bytes:
  done = subprocess.run(args, cwd=ROOT, capture_output=True, timeout=300, env=env, check=False)
  (out / (label + '.stdout')).write_bytes(done.stdout)
  (out / (label + '.stderr')).write_bytes(done.stderr)
  assert done.returncode == 0, label + ': ' + (done.stdout + done.stderr).decode(errors='replace')[-3500:]
  return done.stdout


SUITE_RUNNER = '''import importlib,json,sys,unittest
module=importlib.import_module(sys.argv[1])
suite=unittest.defaultTestLoader.loadTestsFromModule(module)
class LedgerResult(unittest.TestResult):
  def __init__(self):
    super().__init__();self.started=[];self.passed=[]
  def startTest(self,test):
    super().startTest(test);self.started.append(test.id())
  def addSuccess(self,test):
    super().addSuccess(test);self.passed.append(test.id())
result=LedgerResult();suite.run(result)
data={'tests':result.testsRun,'PASS':len(result.passed),'FAIL':len(result.failures),'ERROR':len(result.errors),
      'SKIP':len(result.skipped),'XFAIL':len(result.expectedFailures),'XPASS':len(result.unexpectedSuccesses),
      'started_ids':sorted(result.started),'passed_ids':sorted(result.passed),
      'failures':[{'id':test.id(),'detail':detail} for test,detail in result.failures+result.errors]}
print(json.dumps(data,sort_keys=True,separators=(',',':')))
sys.exit(0 if result.wasSuccessful() and not result.skipped and not result.expectedFailures else 1)
'''


def suite(module: str, count: int, ledger: str, out: Path) -> dict[str, Any]:
  value = json.loads(run([sys.executable, '-B', '-c', SUITE_RUNNER, module], module.rsplit('.', 1)[-1], out))
  expected = (ARTIFACTS / ledger).read_text().splitlines()
  assert len(expected) == len(set(expected)) == count, 'REGISTERED_TEST_COUNT'
  assert value['tests'] == value['PASS'] == count, 'ACTUAL_TEST_COUNT'
  assert value['started_ids'] == value['passed_ids'] == sorted(expected), 'EXACT_TEST_ID_SET'
  assert all(value[key] == 0 for key in ['FAIL', 'ERROR', 'SKIP', 'XFAIL', 'XPASS']), 'TEST_STATUS'
  return value


def reproduction(out: Path) -> dict[str, Any]:
  outputs = []
  for index in [1, 2]:
    with tempfile.TemporaryDirectory(prefix='f70u-fresh-', dir=out) as temp:
      directory = Path(temp)
      environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0',
                         XDG_CACHE_HOME=str(directory / 'cache'), TMPDIR=str(directory / 'tmp'), LC_ALL='C.UTF-8', TZ='UTC')
      (directory / 'cache').mkdir()
      (directory / 'tmp').mkdir()
      generated = directory / 'generated'
      run([sys.executable, '-B', '-m', 'tools.cyberpilot.f70u.validate_context_contract', '--output-dir', str(generated)],
          'generation_' + str(index), out, environment)
      content = {path.name: path.read_bytes() for path in sorted(generated.iterdir())}
      assert len(content) == 7, 'REGENERATION_SET'
      outputs.append(content)
  assert outputs[0] == outputs[1], 'BYTE_IDENTICAL_GENERATION'
  hashes = {name: sha(raw) for name, raw in outputs[0].items()}
  manifest = ''.join(digest + '  ' + name + '\n' for name, digest in sorted(hashes.items())).encode()
  for name in ['context_validation_result.json', 'F70U_FINAL_RESULT.json']:
    assert (ARTIFACTS / name).read_bytes() == outputs[0][name], 'REGISTERED_GENERATED_OUTPUT'
  return {'run_1_manifest_sha256': sha(manifest), 'run_2_manifest_sha256': sha(manifest),
          'byte_identical': True, 'file_hashes': hashes, 'output_count': len(hashes)}


def static_checks(tools: dict[str, str], out: Path) -> None:
  run([tools['ruff'], 'check', '--no-cache', *PYTHON_FILES], 'f70u_ruff', out)
  config = out / 'f70u-strict-ty.toml'
  config.write_text('# No rule exemptions.\n')
  run([tools['ty'], 'check', '--config-file', str(config), '--python', sys.executable, '--python-version', '3.12',
       *PYTHON_FILES], 'f70u_ty', out)
  run([tools['codespell'], *PYTHON_FILES, *DOCUMENTS], 'f70u_codespell', out)
  for path in PYTHON_FILES:
    compile((ROOT / path).read_bytes(), path, 'exec', dont_inherit=True)


def artifact_evidence() -> None:
  schema = json.loads((ARTIFACTS / 'static_context_schema.json').read_text())
  contract = load_context_contract(ARTIFACTS / 'static_context_contract.json')
  result = validate_context_contract(contract)
  assert result.schema_valid and result.instance_status == 'STATIC_CONTEXT_INSTANCE_UNRESOLVED', 'SCHEMA_INSTANCE_SEPARATION'
  assert contract.data['provenance']['sources'] == schema['x-trusted-sources'], 'SOURCE_REGISTRY'
  for source in schema['x-trusted-sources']:
    if 'excerpt' in source:
      assert sha(source['excerpt'].encode()) == source['excerpt_sha256'], 'SOURCE_EXCERPT_SHA'
  catalog = json.loads((ARTIFACTS / 'F70U_PLATFORM_CANDIDATES.json').read_text())
  assert catalog['candidate_count'] == len(catalog['candidates']) == 4, 'PLATFORM_CATALOG'
  assert catalog['selected_candidate'] is None and catalog['admissible_owner_bindings'] == 0, 'NO_VEHICLE_SELECTION'
  assert not any(candidate['selected'] for candidate in catalog['candidates']), 'UNSELECTED_CANDIDATES'
  assert not catalog['owner_description_is_identity_authority'], 'OWNER_SCOPE'


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--precommit', action='store_true')
  parser.add_argument('--output-dir', type=Path, required=True)
  args = parser.parse_args()
  out = args.output_dir
  out.mkdir(parents=True, mode=0o700, exist_ok=False)
  os.chdir(ROOT)
  identity = scope(args.precommit)
  artifact_evidence()
  prior = prior_verifier()
  prior['verify_sources']()
  tools = prior['restore_tools'](out)
  new_tests = suite(NEW_MODULE, 56, 'test_ids.txt', out)
  compatibility = suite(COMPAT_MODULE, 2, 'compatibility_test_ids.txt', out)
  legacy = prior['validate'](out)
  prior['quality'](tools, out)
  static_checks(tools, out)
  repeat = reproduction(out)
  cloud = os.environ.get('GITHUB_ACTIONS') == 'true'
  status = 'F70U_STATIC_CONTEXT_SCHEMA_PUBLISHED_CI_PASS_INSTANCE_UNRESOLVED' if cloud else 'F70U_STATIC_CONTEXT_SCHEMA_LOCAL_PASS_INSTANCE_UNRESOLVED'
  record = {'status': status, 'CONTEXT_SCHEMA_STATUS': 'VALID', 'STATIC_CONTEXT_INSTANCE': 'UNRESOLVED',
            'git': identity, 'new_tests': new_tests, 'compatibility_tests': compatibility, 'reference_PASS': 61,
            'legacy': legacy, 'existing_PASS': 83, 'total_PASS': 202, 'reproduction': repeat,
            'Ruff': 'PASS', 'Ty': 'PASS', 'Codespell': 'PASS', 'Compile': 'PASS',
            'R_BUDGET_UNRESOLVED': True, 'SOURCE_SCHEMA_UNQUALIFIED': 6000, 'candidate_NO_GO': True,
            'RUNTIME_NO_GO': True, 'F71_authorized': False, 'next_allowed_step': 'F70U-A'}
  (out / 'F70U_TERMINAL_RESULT.json').write_text(json.dumps(record, sort_keys=True, indent=2) + '\n')
  print('F70U_TERMINAL_GATE ' + json.dumps(record, sort_keys=True))


if __name__ == '__main__':
  main()
