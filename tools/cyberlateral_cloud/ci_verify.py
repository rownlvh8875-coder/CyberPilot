"""Credential-free worktree checks for cloud tooling, never a live HF integration."""

import argparse
import importlib.metadata
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

from artifacts import manifest, new_restore_directory, sha, validate_names
from cloud_restore import VERSIONS
from cloud_run import GATES, run_command, safe_error, write_json

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
LOGS = {'sdk-version.log', 'unittest.log', 'ruff.log', 'ty.log', 'codespell.log'}


def validate_ledger(text: str) -> int:
    counts = re.findall(r'(?m)^Ran (\d+) tests in [0-9]+(?:\.[0-9]+)?s$', text)
    if (len(counts) != 1 or int(counts[0]) < 70 or text.rstrip().splitlines()[-1] != 'OK'
            or re.search(r'(?m)^(FAILED\b|ERROR[: ])', text)):
        raise ValueError('CI_TEST_LEDGER_INVALID')
    return int(counts[0])


def compile_owned(root: Path) -> dict[str, str]:
    compiled = {}
    for path in sorted(root.rglob('*.py')):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('CLOUD_SOURCE_SYMLINK')
        raw = path.read_bytes()
        try:
            compile(raw, str(path), 'exec')
        except SyntaxError:
            raise ValueError('CLOUD_SOURCE_COMPILE_FAILED') from None
        compiled[path.relative_to(root).as_posix()] = sha(raw)
    if not compiled:
        raise ValueError('CLOUD_SOURCE_COMPILE_REQUIRED')
    return compiled


def seal_results(output: Path, compiled: dict[str, str]) -> dict:
    paths = list(output.iterdir())
    if {p.name for p in paths} != LOGS or any(p.is_symlink() or not p.is_file() for p in paths):
        raise ValueError('CI_LOG_CLOSURE')
    tests = validate_ledger((output / 'unittest.log').read_text())
    if (any((output / name).read_text().strip() != 'All checks passed!' for name in ('ruff.log', 'ty.log'))
            or (output / 'codespell.log').read_text().strip()):
        raise ValueError('CI_STATIC_CHECK_INVALID')
    sdk = json.loads((output / 'sdk-version.log').read_bytes())
    if sdk.get('python') != '3.12.13' or sdk.get('version') != '2.4.0':
        raise ValueError('CI_SDK_VERSION_REQUIRED')
    validate_names(compiled)
    if not compiled or any(re.fullmatch('[0-9a-f]{64}', value) is None for value in compiled.values()):
        raise ValueError('CLOUD_SOURCE_COMPILE_REQUIRED')
    result = {'status': 'CYBERLATERAL_CLOUD_VERIFICATION_PASS', 'tests': tests, 'own_compiles': len(compiled),
              'source_sha256': compiled, 'static_checks': {'Ruff': 'PASS', 'Ty': 'PASS', 'Codespell': 'PASS (-L assertin)'},
              'python': '3.12.13', 'hf_sdk': '2.4.0', 'sdk_separate_from_app': True,
              'live_hf_integration': 'NOT_RUN', 'test_transport': 'IN_MEMORY_HF_AND_REAL_LOCAL_SYNTHETIC_WORKFLOWS',
              'synthetic_model_reference_work': 'NONZERO_NOT_AGGREGATED', 'gates': GATES,
              'scope': 'CURRENT_WORKTREE_CLOUD_TESTS_NOT_COMMITTED_ARCHIVE_OR_VEHICLE_QUALIFICATION'}
    write_json(output / 'SUMMARY.json', result)
    files = {p.name: p.read_bytes() for p in output.iterdir()}
    with (output / 'SHA256SUMS.txt').open('xb') as stream:
        stream.write(manifest(files))
    return result


def execute(args) -> dict:
    output = new_restore_directory(args.output)
    if output.resolve().is_relative_to(REPO):
        raise ValueError('EXTERNAL_OUTPUT_REQUIRED')
    output.mkdir(exist_ok=False)
    stage = 'PREFLIGHT'
    try:
        if sys.version_info[:3] != (3, 12, 13):
            raise ValueError('PYTHON_VERSION_REQUIRED')
        if importlib.util.find_spec('huggingface_hub') is not None:
            raise ValueError('SDK_MUST_BE_SEPARATE')
        if {name: importlib.metadata.version(name) for name in VERSIONS} != VERSIONS:
            raise ValueError('DEV_DEPENDENCY_VERSION_REQUIRED')
        sdk_python = args.hf_python.absolute()
        if not sdk_python.is_file() or not os.access(sdk_python, os.X_OK):
            raise ValueError('HF_INTERPRETER_REQUIRED')
        env = os.environ.copy()
        env.update(HF_HUB_OFFLINE='1', PYTHONDONTWRITEBYTECODE='1')
        query = "import importlib.metadata as m,json,sys; print(json.dumps({'python':sys.version.split()[0],'version':m.version('huggingface-hub'),'prefix':sys.prefix},sort_keys=True))"
        raw = run_command([sdk_python, '-I', '-B', '-c', query], output / 'sdk-version.log', REPO, env=env)
        sdk = json.loads(raw)
        if (sdk.get('python') != '3.12.13' or sdk.get('version') != '2.4.0'
                or Path(sdk.get('prefix', '')).resolve() == Path(sys.prefix).resolve()):
            raise ValueError('CI_SDK_VERSION_OR_ISOLATION_REQUIRED')
        before = compile_owned(TOOLS)
        stage = 'UNIT_TESTS'
        run_command([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', TOOLS / 'tests', '-v'],
                    output / 'unittest.log', REPO, env=env)
        validate_ledger((output / 'unittest.log').read_text())
        stage = 'STATIC_CHECKS'
        binaries = Path(sys.executable).parent
        run_command([binaries / 'ruff', 'check', '--isolated', '--select', 'E4,E7,E9,F,I,B,UP', TOOLS],
                    output / 'ruff.log', REPO, env=env)
        run_command([binaries / 'ty', 'check', '--config-file', REPO / 'tools/cyberlateral_dev/ty.toml',
                     '--python', sdk_python, '--extra-search-path', TOOLS, TOOLS], output / 'ty.log', REPO, env=env)
        run_command([binaries / 'codespell', '-L', 'assertin', TOOLS], output / 'codespell.log', REPO, env=env)
        stage = 'COMPILE_AND_SOURCE'
        compiled = compile_owned(TOOLS)
        if compiled != before:
            raise ValueError('CLOUD_SOURCE_CHANGED_DURING_CHECKS')
        stage = 'SEAL'
        return seal_results(output, compiled)
    except Exception as error:
        code = safe_error(error)
        write_json(output / 'FAILURE.json', {'status': 'FAILED', 'stage': stage, 'code': code, 'outputs_preserved': True})
        raise ValueError(code) from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hf-python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = execute(args)
    except Exception as error:
        print(json.dumps({'status': 'FAILED', 'code': safe_error(error)}, sort_keys=True))
        return 2
    print(json.dumps({name: result[name] for name in ('status', 'tests', 'own_compiles', 'live_hf_integration')}, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
