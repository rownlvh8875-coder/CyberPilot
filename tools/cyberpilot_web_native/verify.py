"""Complete host-native telemetry gate; never build or run a vehicle stack."""

import argparse
import hashlib
import json
import os
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.cyberpilot_web_native.native_check import validate_build  # noqa: E402
from tools.cyberpilot_web_native.prepare import check_output_path  # noqa: E402
from tools.cyberpilot_web_native.supervise import run_command  # noqa: E402


def sources():
  chosen = []
  for directory in ('openpilot/system/cyberpilot_web', 'tools/cyberpilot_web_native'):
    chosen.extend(path for path in (ROOT / directory).rglob('*') if path.is_file() and
                  not any(part.startswith('.') or part == '__pycache__' for part in path.relative_to(ROOT / directory).parts))
  chosen.extend(ROOT / name for name in ('openpilot/__init__.py', 'openpilot/cereal/__init__.py', 'openpilot/cereal/log.capnp',
                                        'openpilot/cereal/deprecated.capnp', 'openpilot/cereal/custom.capnp', 'openpilot/cereal/services.py',
                                        'openpilot/cereal/messaging/__init__.py', 'openpilot/common/utils.py'))
  return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(chosen)}


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--prepared', type=Path, required=True)
  parser.add_argument('--output', type=Path, required=True)
  args = parser.parse_args()
  if 'OPENPILOT_PREFIX' in os.environ or 'CEREAL_FAKE' in os.environ:
    raise ValueError('existing_native_environment_refused')
  receipt = validate_build(args.prepared)
  output = check_output_path(ROOT, args.output)
  output.mkdir()
  before = sources()
  env = {**os.environ, 'PYTHONPATH': os.pathsep.join(str(p) for p in (ROOT, args.prepared / 'msgq', args.prepared / 'opendbc')),
         'PYTHONDONTWRITEBYTECODE': '1'}
  results = {}

  def command(name, argv, environment=env):
    code = run_command(argv, ROOT, environment, output / (name + '.log'))
    results[name] = {'exit': code}
    if code:
      raise RuntimeError(name + ' failed; inspect ' + str(output / (name + '.log')))

  target = 'tools/cyberpilot_web_native'
  command('ruff', [sys.executable, '-m', 'ruff', 'check', '--config', target + '/pyproject.toml', target])
  command('ty', [sys.executable, '-m', 'ty', 'check', '--project', target, target])
  command('codespell', [sys.executable, '-m', 'codespell_lib', target, 'docs/CYBERPILOT_WEB_NATIVE_KO.md', '--skip', '*.lock,.venv', '-L', 'assertin'])
  command('native-tests', [sys.executable, '-B', target + '/test_worker.py', '--output', str(output / 'NATIVE_TEST_RESULTS.json')])
  native = json.loads((output / 'NATIVE_TEST_RESULTS.json').read_text())
  if native['status'] != 'PASS' or native['skipped']:
    raise RuntimeError('native coverage incomplete')
  command('native-web', [sys.executable, '-B', target + '/native_check.py', '--prepared', str(args.prepared), '--output', str(output / 'native-web')])
  command('basic-web', [sys.executable, '-B', 'tools/cyberpilot_web/verify.py', '--output', str(output / 'basic-web')])
  for index, path in enumerate(sorted((ROOT / target).rglob('*.py'))):
    if '.venv' not in path.parts:
      py_compile.compile(str(path), cfile=str(output / 'compile' / f'{index}.pyc'), doraise=True)
  after = sources()
  if before != after:
    raise RuntimeError('checked_source_bytes_changed')
  validate_build(args.prepared)
  (output / 'SOURCE_SHA256.json').write_text(json.dumps(before, sort_keys=True, indent=2) + '\n')
  (output / 'BUILD_RECEIPT.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
  browser = json.loads((output / 'native-web/NATIVE_WEB_RESULTS.json').read_text())
  basic = json.loads((output / 'basic-web/RESULTS.json').read_text())
  results.update(status='PASS', scope='LINUX_X86_64_SYNTHETIC_NATIVE_TELEMETRY', native_tests=native['tests_run'],
                 actual_native_collector_cases=len(native['native_cases_executed']), basic_web_tests=basic['tests']['run'],
                 native_browser_cases=len(browser['cases']), native_browser_checks=sum(len(c['checks']) for c in browser['cases']),
                 basic_browser_checks=7, checked_source_files=len(before), source_bytes_unchanged=True,
                 actual_device_qualification=False, actual_vehicle_inputs=0, controller_execution=0, f61_execution=0,
                 actual_rate_calculation=0, r_budget='UNRESOLVED', static_evidence_gate='FAIL')
  (output / 'RESULTS.json').write_text(json.dumps(results, indent=2) + '\n')
  manifest = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}
  (output / 'MANIFEST.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
  print(json.dumps(results, indent=2))


if __name__ == '__main__':
  main()
