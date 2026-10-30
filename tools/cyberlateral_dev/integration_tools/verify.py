"""Scoped offline verification orchestration; never import vehicle runtime."""

import base64
import csv
import hashlib
import importlib.metadata
import io
import json
import platform
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

WHEEL = 'cyberlateral_dev-0.3.0-py3-none-any.whl'
PINS = {'numpy': '2.5.3', 'ruff': '0.16.7', 'ty': '0.0.80', 'codespell': '2.4.3', 'PyYAML': '6.0.3'}


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_new_output(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError('OUTPUT_EXISTS_NO_VERIFICATION')


def verify_imports(root: Path) -> dict:
    record = json.loads((root / 'IMPORTED_ARTIFACT.json').read_bytes())
    for name, expected in record['imported_files'].items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
            raise ValueError('UNSAFE_IMPORTED_PATH')
        target = root / name
        if target.is_symlink() or root.resolve() not in target.resolve().parents:
            raise ValueError('IMPORTED_PATH_ESCAPES_COMPONENT')
        if sha(target.read_bytes()) != expected:
            raise ValueError(f'IMPORTED_HASH_MISMATCH:{name}')
    return {
        'files': len(record['imported_files']),
        'source_sha256': record['source_sha256'],
        'expected_wheel_sha256': record['expected_wheel_sha256'],
        'scope': 'manifest consistency, not authenticity of an untrusted manifest',
    }


def _run(args, log: Path, cwd: Path):
    result = subprocess.run([str(x) for x in args], cwd=cwd, capture_output=True, check=False)
    with log.open('xb') as stream:
        stream.write(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f'COMMAND_FAILED:{log.name}:exit={result.returncode}')
    return result.stdout


def _wheel_record(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise ValueError('WHEEL_CRC_OR_DUPLICATE')
        files = {name: archive.read(name) for name in names}
    record = next(name for name in names if name.endswith('.dist-info/RECORD'))
    covered = set()
    for name, digest, size in csv.reader(io.StringIO(files[record].decode())):
        if name in covered:
            raise ValueError('WHEEL_RECORD_DUPLICATE')
        covered.add(name)
        if name == record:
            if (digest, size) != ('', ''):
                raise ValueError('WHEEL_RECORD_SELF_ENTRY')
        else:
            expected = base64.urlsafe_b64encode(hashlib.sha256(files[name]).digest()).rstrip(b'=').decode()
            if digest != 'sha256=' + expected or int(size) != len(files[name]):
                raise ValueError('WHEEL_RECORD_HASH_OR_SIZE')
    if covered != set(names):
        raise ValueError('WHEEL_RECORD_COVERAGE')
    return len(covered)


def build_wheels(root: Path, output: Path) -> dict:
    verify_new_output(output)
    output.mkdir(parents=True, exist_ok=False)
    for name in ['one', 'two']:
        _run([sys.executable, '-B', root / 'tools/build_wheel.py', '--output', output / name], output / (name + '.log'), root)
    a, b = [(output / name / WHEEL).read_bytes() for name in ['one', 'two']]
    expected = json.loads((root / 'IMPORTED_ARTIFACT.json').read_bytes())['expected_wheel_sha256']
    if a != b or sha(a) != expected:
        raise ValueError('WHEEL_REPRODUCTION_OR_SEALED_IDENTITY_MISMATCH')
    return {
        'byte_identical': True,
        'sha256': sha(a),
        'bytes': len(a),
        'record_entries': _wheel_record(a),
        'build_count_scope': 'two explicit build processes, not aggregate unit-test activity',
    }


def _compare(a, b):
    one = {p.name: p.read_bytes() for p in a.iterdir()}
    two = {p.name: p.read_bytes() for p in b.iterdir()}
    if one != two:
        raise ValueError('REPRODUCTION_BYTE_MISMATCH')
    return {name: sha(raw) for name, raw in sorted(one.items())}


def harness_pair_summary(first: Path, second: Path) -> dict:
    hashes = _compare(first, second)
    if set(hashes) != {'RESULTS.json', 'SHA256SUMS.txt'}:
        raise ValueError('MISSING_HARNESS_ARTIFACTS')
    raw = (first / 'RESULTS.json').read_bytes()
    record = json.loads(raw)
    if type(record) is not dict or canonical(record) != raw:
        raise ValueError('HARNESS_CONTRACT_NONCANONICAL_RECORD')
    environment = {'isolated': True, 'installed_package': True, 'numpy_available': False, 'forbidden_modules_loaded': []}
    valid = (
        record.get('status') == 'F70UGZ_R9_SYNTHETIC_CALLER_HARNESS_PASS'
        and record.get('package_version') == '0.3.0'
        and (record.get('scenario_count'), record.get('total_steps'), record.get('two_chunk_splits')) == (7, 112, 105)
        and record.get('step_chain_parity') is True and record.get('interleaved_caller_parity') is True
        and type(record.get('rejections')) is list and len(record['rejections']) == 11
        and record.get('execution_environment') == environment
    )
    if not valid:
        raise ValueError('HARNESS_CONTRACT_MISMATCH')
    if (first / 'SHA256SUMS.txt').read_bytes() != (sha(raw) + '  RESULTS.json\n').encode():
        raise ValueError('HARNESS_MANIFEST_MISMATCH')
    return {
        'status': record['status'], 'byte_identical': True, 'scenario_count': record['scenario_count'],
        'total_steps': record['total_steps'], 'two_chunk_splits': record['two_chunk_splits'],
        'rejection_cases': len(record['rejections']), 'file_hashes': hashes,
        'scope': 'fixed installed caller lifecycle/regression; not independent numerical oracle or production activation',
    }


def verify_installed_harness(root: Path, python: Path, output: Path, cwd: Path) -> dict:
    for name in ['harness_one', 'harness_two']:
        _run([python, '-I', '-B', root / 'integration_tools/synthetic_harness.py', '--output', output / name],
             output / (name + '.log'), cwd)
    return harness_pair_summary(output / 'harness_one', output / 'harness_two')


def _runtime():
    if platform.python_implementation() != 'CPython' or platform.python_version() != '3.12.13' or sys.float_info.mant_dig != 53:
        raise ValueError('PINNED_CPYTHON31213_BINARY64_REQUIRED')
    try:
        versions = {name: importlib.metadata.version(name) for name in PINS}
    except importlib.metadata.PackageNotFoundError as error:
        raise ValueError('PINNED_DEV_DEPENDENCIES_MISSING_RUN_UV_LOCKED') from error
    if versions != PINS:
        raise ValueError('PINNED_DEV_DEPENDENCIES_REQUIRED')
    return {'python': platform.python_version(), 'development_dependencies': versions, 'runtime_dependencies': []}


def test_count(text: str) -> int:
    match = re.search(r'(?m)^Ran (\d+) tests in ', text)
    if match is None or int(match[1]) < 127:
        raise ValueError('MISSING_OR_TRUNCATED_INHERITED_SUITE_LEDGER')
    return int(match[1])


def verify_project(root: Path, output: Path) -> dict:
    verify_new_output(output)
    imported, runtime = verify_imports(root), _runtime()
    output.mkdir(parents=True, exist_ok=False)
    python = Path(sys.executable)
    _run([python, '-B', '-m', 'unittest', 'discover', '-s', root / 'project', '-v'], output / 'unittest.log', root)
    tools = python.parent
    own = ['project', 'src', 'build_backend.py', 'dev.py', 'integration_tools', 'tools']
    _run([tools / 'ruff', 'check', *own], output / 'ruff.log', root)
    _run([tools / 'ty', 'check', '--python', python, *own], output / 'ty.log', root)
    _run([tools / 'codespell', 'README.md', 'docs', *own], output / 'codespell.log', root)
    compiled = []
    for directory in ['project', 'src', 'integration_tools', 'tools']:
        for path in sorted((root / directory).rglob('*.py')):
            compile(path.read_bytes(), str(path), 'exec')
            compiled.append(path.relative_to(root).as_posix())
    for name in ['dev.py', 'build_backend.py']:
        compile((root / name).read_bytes(), name, 'exec')
        compiled.append(name)
    wheels = build_wheels(root, output / 'wheels')
    with tempfile.TemporaryDirectory(prefix='cyberlateral-installed-') as scratch:
        temp = Path(scratch)
        _run([python, '-B', '-m', 'venv', '--without-pip', temp / 'env'], output / 'venv.log', root)
        isolated = temp / 'env/bin/python'
        _run(
            ['uv', 'pip', 'install', '--offline', '--no-deps', '--link-mode=copy', '--python', isolated, output / 'wheels/one' / WHEEL],
            output / 'install.log',
            temp,
        )
        for name in ['report_one', 'report_two']:
            _run([isolated, '-I', '-B', '-m', 'cyberlateral_dev', '--report', '--output', output / name], output / (name + '.log'), temp)
        report_hashes = _compare(output / 'report_one', output / 'report_two')
        code = """
import importlib.metadata,importlib.util,json,sys
assert importlib.util.find_spec('numpy') is None
import cyberlateral_dev as p
assert '/site-packages/cyberlateral_dev/' in p.__file__
assert not importlib.metadata.requires('cyberlateral-dev')
assert not [n for n in sys.modules if n.split('.')[0] in {'numpy','kernel','openpilot','selfdrive','opendbc','cereal','capnp'}]
print(json.dumps({'status':'PASS','version':p.__version__,'runtime_dependencies':[],'numpy_available':False,'isolated':bool(sys.flags.isolated)},sort_keys=True))
"""
        _run([isolated, '-I', '-B', '-c', code], output / 'installed.log', temp)
        harness = verify_installed_harness(root, isolated, output, temp)
    for name in ['numeric_one', 'numeric_two']:
        _run(
            [
                python,
                '-B',
                root / 'project/run_module_v1.py',
                '--controller',
                root / 'reference/carcontroller.py',
                '--helper',
                root / 'reference/lateral.py',
                '--schema',
                root / 'reference/car.capnp',
                '--output',
                output / name,
            ],
            output / (name + '.log'),
            root,
        )
    numeric_hashes = _compare(output / 'numeric_one', output / 'numeric_two')
    source = json.loads((output / 'report_one/simulation.json').read_bytes())
    summary = {
        'status': 'F70UGZ_R9_SYNTHETIC_INTEGRATION_HARNESS_PASS',
        'runtime': runtime,
        'imports': imported,
        'tests': test_count((output / 'unittest.log').read_text()),
        'own_python_compile_count': len(compiled),
        'original_Controller_schema_executable_compile': 0,
        'wheel': wheels,
        'report_file_hashes': report_hashes,
        'numeric_file_hashes': numeric_hashes,
        'synthetic_harness': harness,
        'report_and_numeric_pairs_byte_identical': True,
        'source_gates': source['gates'],
        'Controller_execution': 0,
        'Runtime_execution': 0,
        'CAN': 0,
        'F61_execution': 0,
        'calculator_input_execution': 0,
        'r_calculations': 0,
        'dt_calculations': 0,
        'candidate_performance_evaluation': 0,
        'actual_production_inputs': 0,
        'installed_package_original_helper_calls': 0,
        'browser_visual_verification': 'NOT_ESTABLISHED',
        'per_numeric_process_reference_helper_counts': json.loads((output / 'numeric_one/summary.json').read_bytes())['helper_execution_counts'],
        'scope': 'standalone synthetic verification only; not full openpilot tests, deployment, physical safety or authenticating untrusted manifests',
    }
    with (output / 'SUMMARY.json').open('xb') as stream:
        stream.write(canonical(summary))
    entries = [(p.relative_to(output).as_posix(), p.read_bytes()) for p in sorted(output.rglob('*')) if p.is_file()]
    with (output / 'SHA256SUMS.txt').open('xb') as stream:
        stream.write(''.join(sha(raw) + '  ' + name + '\n' for name, raw in entries).encode())
    return summary
