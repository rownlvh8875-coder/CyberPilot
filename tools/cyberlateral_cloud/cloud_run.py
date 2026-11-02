"""One explicit committed-source cloud verification and private archive command."""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import uuid
from pathlib import Path, PurePosixPath

from artifacts import (
    SOURCE_PREFIX,
    export_source,
    git,
    new_path,
    seal,
    sha,
    verify_archive,
)
from workflow_checks import portable_files, verify_tree

TOOLS = Path(__file__).resolve().parent
GATES = {'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL', 'actual_r': None, 'actual_T2': None,
         'actual_vehicle_scale': None, 'Candidate': 'NO_GO', 'Runtime': 'NO_GO',
         'F70UH': 'NOT_ALLOWED', 'F70V': 'NOT_ALLOWED', 'F71': 'NOT_ALLOWED',
         'D2': 'PERFORMANCE_NOT_EVALUATED', 'F19': 'LEGACY_UNRESOLVED', 'NATIVE_EXACT_REPLAY': 'NOT_PROVEN',
         'SOURCE_SCHEMA_UNQUALIFIED': 6000, 'actual_activation': 'NOT_ALLOWED'}
ZERO_FIELDS = ['F61_execution', 'r_calculations', 'dt_calculations', 'Controller_execution', 'Runtime_execution',
               'CAN', 'actual_production_inputs', 'calculator_input_execution', 'candidate_performance_evaluation']


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def write_json(path: Path, value) -> None:
    with path.open('xb') as stream:
        stream.write(canonical(value))


def run_command(command, log: Path, cwd: Path, timeout=1800, env=None) -> bytes:
    process = subprocess.Popen([str(x) for x in command], cwd=cwd, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    expired = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        expired = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
    with log.open('xb') as stream:
        stream.write(stdout + stderr)
    if expired:
        raise ValueError('COMMAND_TIMEOUT')
    if process.returncode:
        try:
            failure = json.loads(stdout)
        except (ValueError, UnicodeError):
            failure = {}
        code = failure.get('code') if isinstance(failure, dict) else None
        if isinstance(code, str) and re.fullmatch(r'[A-Z0-9_]{1,80}', code):
            raise ValueError(code)
        raise ValueError('COMMAND_FAILED')
    return stdout


def validate_gate(summary: dict, ledger: str, expected_compiles: int, expected_wheel: str) -> dict:
    matched = re.search(r'(?m)^Ran (\d+) tests in ', ledger)
    tests = summary.get('tests')
    if (type(tests) is not int or tests < 127 or matched is None or int(matched[1]) != tests
            or not ledger.rstrip().endswith('OK') or re.search(r'(?m)^FAILED\b', ledger)):
        raise ValueError('GATE_LEDGER')
    if (summary.get('status') != 'F70UGZ_R18_FIXED_AUDIT_BUNDLE_REFERENCE_PASS'
            or type(summary.get('own_python_compile_count')) is not int
            or summary['own_python_compile_count'] != expected_compiles):
        raise ValueError('GATE_CONTRACT')
    if summary.get('wheel', {}).get('sha256') != expected_wheel or summary['wheel'].get('byte_identical') is not True:
        raise ValueError('GATE_WHEEL')
    gates = summary.get('source_gates', {})
    if (any(k not in gates or gates[k] != v for k, v in GATES.items())
            or any(type(summary.get(k)) is not int or summary[k] != 0 for k in ZERO_FIELDS)):
        raise ValueError('GATE_SAFETY')
    return {'tests': tests, 'own_compiles': expected_compiles, 'wheel_sha256': expected_wheel,
            'static_checks': 'PASS_FROM_SUCCESSFUL_FULL_GATE', 'gates': gates,
            'scope': 'EXISTING_CONFIGURED_COMPONENT_GATE_NOT_FULL_OPENPILOT_OR_VEHICLE_QUALIFICATION'}


def registered_payloads(source: Path, provenance: dict) -> dict[str, bytes]:
    files = {}
    for name, record in provenance['files'].items():
        path = source / name
        if path.is_symlink() or not path.resolve().is_relative_to(source.resolve()):
            raise ValueError('SOURCE_CHANGED_DURING_RUN')
        raw = path.read_bytes()
        if len(raw) != record['byte_size'] or sha(raw) != record['sha256']:
            raise ValueError('SOURCE_CHANGED_DURING_RUN')
        files['SOURCE/' + name] = raw
    return files


def storage(command: str, sdk_python: Path, repo: str, output: Path, extra=()) -> dict:
    env = os.environ.copy()
    env['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
    raw = run_command([sdk_python, '-B', TOOLS / 'hf_archive.py', command, '--repo-id', repo, *extra],
                      output / ('storage-' + command + '-' + uuid.uuid4().hex + '.log'), output, env=env)
    result = json.loads(raw)
    if result.get('status') != ('PRIVATE_STORAGE_READY' if command == 'preflight' else 'PRIVATE_BACKUP_EXACT'):
        raise ValueError('STORAGE_RECEIPT_INVALID')
    return result


def perform_backup(output: Path, sdk_python: Path, repo: str) -> dict:
    local = json.loads((output / 'LOCAL_VERIFIED.json').read_bytes())
    if local.get('status') != 'LOCAL_VERIFIED_BACKUP_PENDING':
        raise ValueError('LOCAL_VERIFICATION_REQUIRED')
    verified = verify_archive(output / 'EVIDENCE.zip', local['archive']['archive_sha256'])
    if verified != local['archive']:
        raise ValueError('LOCAL_ARCHIVE_CHANGED')
    result = storage('backup', sdk_python, repo, output,
                     ['--archive', output / 'EVIDENCE.zip', '--archive-sha', verified['archive_sha256'],
                      '--source-commit', local['source_commit']])
    expected_prefix = f"runs/{local['source_commit']}/{verified['archive_sha256']}/"
    if (result.get('status') != 'PRIVATE_BACKUP_EXACT' or result.get('private') is not True
            or result.get('repo_id') != repo or result.get('archive_sha256') != verified['archive_sha256']
            or result.get('prefix') != expected_prefix or type(result.get('verified_files')) is not int
            or result['verified_files'] != 2 or not isinstance(result.get('commit_sha'), str)
            or not re.fullmatch(r'[0-9a-f]{40}', result['commit_sha'])):
        raise ValueError('STORAGE_RECEIPT_INVALID')
    if verify_archive(output / 'EVIDENCE.zip', verified['archive_sha256']) != verified:
        raise ValueError('LOCAL_ARCHIVE_CHANGED')
    final = {'status': 'CLOUD_VERIFICATION_AND_PRIVATE_BACKUP_PASS', 'source_commit': local['source_commit'],
             'local': local, 'backup': result}
    name = 'FINAL_RESULT.json' if not (output / 'FINAL_RESULT.json').exists() else 'BACKUP_RECHECK-' + uuid.uuid4().hex + '.json'
    write_json(output / name, final)
    return final


def execute(args) -> dict:
    output = args.output.absolute()
    repo = args.repo_root.resolve()
    new_path(output)
    if output.resolve().is_relative_to(repo):
        raise ValueError('EXTERNAL_OUTPUT_REQUIRED')
    if not re.fullmatch(r'[0-9a-f]{40}', args.commit):
        raise ValueError('FULL_COMMIT_REQUIRED')
    if not args.local_only and args.hf_python is None:
        raise ValueError('HF_INTERPRETER_REQUIRED')
    project_python = args.project_python.absolute()
    if not project_python.is_file() or not os.access(project_python, os.X_OK):
        raise ValueError('PROJECT_INTERPRETER_REQUIRED')
    output.mkdir(exist_ok=False)
    stage = 'STORAGE_PREFLIGHT'
    try:
        if not args.local_only:
            storage('preflight', args.hf_python.absolute(), args.hf_repo, output)
        stage = 'EXPORT'
        provenance = export_source(repo, args.commit, output / 'source')
        component = output / 'source' / SOURCE_PREFIX
        env = os.environ.copy()
        env.update(UV_CACHE_DIR=str(output / 'private-cache'), UV_PYTHON_DOWNLOADS='never', UV_LINK_MODE='copy')
        stage = 'GATE'
        print('cloud pipeline: GATE', file=sys.stderr, flush=True)
        run_command([project_python, '-B', component / 'dev.py', 'verify', '--output', output / 'verify'],
                    output / 'gate-private.log', output, env=env)
        compiled = 0
        for name in provenance['files']:
            relative = PurePosixPath(name).relative_to(SOURCE_PREFIX)
            if (relative.suffix == '.py' and relative.parts[0] in {'project', 'src', 'integration_tools', 'tools'}
                    or str(relative) in {'dev.py', 'build_backend.py'}):
                compiled += 1
        imported = json.loads((component / 'IMPORTED_ARTIFACT.json').read_bytes())
        gate = validate_gate(json.loads((output / 'verify/SUMMARY.json').read_bytes()),
                             (output / 'verify/unittest.log').read_text(), compiled, imported['expected_wheel_sha256'])
        stage = 'R41_WORKFLOWS'
        print('cloud pipeline: R41_WORKFLOWS', file=sys.stderr, flush=True)
        workflows = output / 'workflows'
        workflows.mkdir()
        expected = json.loads((component / 'reference/r41_regression_expected_v1.json').read_bytes())
        for alias in ['one', 'two', 'baseline']:
            inputs = [part for name in expected['order'] for part in ['--input', component / 'examples/r41' / name]]
            if alias == 'baseline':
                inputs += ['--baseline', workflows / 'one/batch']
            run_command([project_python, '-I', '-B', component / 'tools/scenario_workflow.py', *inputs,
                         '--output', workflows / alias], output / ('workflow-' + alias + '-private.log'), output, env=env)
        raw = run_command([project_python, '-B', TOOLS / 'workflow_checks.py', '--component', component,
                           '--work-root', workflows], output / 'workflow-acceptance-private.log', output, env=env)
        workflow_acceptance = json.loads(raw)
        verify_tree(output / 'verify')
        stage = 'SEAL'
        print('cloud pipeline: SEAL', file=sys.stderr, flush=True)
        members = registered_payloads(output / 'source', provenance)
        members['SOURCE_IDENTITY.json'] = canonical(provenance)
        driver = {}
        for filename in ['artifacts.py', 'cloud_run.py', 'hf_archive.py', 'workflow_checks.py', 'README_KO.md', 'hf-requirements.lock']:
            payload = (TOOLS / filename).read_bytes()
            members['DRIVER/' + filename] = payload
            driver[filename] = sha(payload)
        driver_commit = git(repo, 'rev-parse', 'HEAD').decode().strip()
        tracked_driver = True
        for filename, digest in driver.items():
            try:
                tracked_driver &= sha(git(repo, 'show', driver_commit + ':tools/cyberlateral_cloud/' + filename)) == digest
            except subprocess.CalledProcessError:
                tracked_driver = False
        members['DRIVER_IDENTITY.json'] = canonical({'files': driver, 'commit': driver_commit if tracked_driver else None})
        portable = portable_files(workflows / 'one')
        members.update({'R41/' + name: raw for name, raw in portable.items()})
        for name in ['COMPARE.json', 'SUMMARY_KO.md']:
            members['R41_BASELINE/' + name] = (workflows / 'baseline/regression' / name).read_bytes()
        acceptance = {'contract_id': 'CYBERPILOT_CLOUD_RUN_V1', 'source_commit': args.commit, 'gate': gate,
                      'R41': workflow_acceptance, 'source_files': len(provenance['files']),
                      'portable_subset_not_complete_baseline': True, 'private_receipts_logs_cache_excluded': True,
                      'unit_gate_work': 'ADDITIONAL_NONZERO_NOT_AGGREGATED', 'vehicle_F61_actual_r_dt': 0,
                      'secret_shape_check': 'LIMITED_PATTERN_CHECK_NOT_ALL_SECRETS_ABSENCE_PROOF'}
        members['ACCEPTANCE.json'] = canonical(acceptance)
        sealed = seal(output / 'EVIDENCE.zip', members)
        with (output / 'EVIDENCE.zip.sha256').open('xb') as stream:
            stream.write((sealed['archive_sha256'] + '  EVIDENCE.zip\n').encode())
        local = {'status': 'LOCAL_VERIFIED_BACKUP_PENDING', 'source_commit': args.commit,
                 'archive': sealed, 'acceptance': acceptance}
        write_json(output / 'LOCAL_VERIFIED.json', local)
        if args.local_only:
            return {'status': 'LOCAL_VERIFIED_NOT_UPLOADED', 'local': local, 'backup': 'NOT_RUN_EXPLICIT_LOCAL_ONLY'}
        stage = 'BACKUP'
        print('cloud pipeline: BACKUP', file=sys.stderr, flush=True)
        return perform_backup(output, args.hf_python.absolute(), args.hf_repo)
    except Exception as error:
        failure = {'status': 'FAILED', 'stage': stage, 'code': safe_error(error),
                   'local_verified': (output / 'LOCAL_VERIFIED.json').is_file(), 'outputs_preserved': True}
        write_json(output / 'FAILURE.json', failure)
        raise ValueError(failure['code']) from None


def safe_error(error) -> str:
    text = str(error)
    return text if isinstance(error, (ValueError, FileExistsError)) and re.fullmatch(r'[A-Z0-9_]{1,80}', text) else 'PIPELINE_ACCEPTANCE_FAILED'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    run = commands.add_parser('run')
    run.add_argument('--repo-root', type=Path, required=True)
    run.add_argument('--commit', required=True)
    run.add_argument('--project-python', type=Path, required=True)
    run.add_argument('--output', type=Path, required=True)
    run.add_argument('--local-only', action='store_true')
    run.add_argument('--hf-python', type=Path)
    run.add_argument('--hf-repo', default='jjuinho/cyberpilot-evidence')
    retry = commands.add_parser('backup')
    retry.add_argument('--run-dir', type=Path, required=True)
    retry.add_argument('--hf-python', type=Path, required=True)
    retry.add_argument('--hf-repo', default='jjuinho/cyberpilot-evidence')
    args = parser.parse_args(argv)
    try:
        if args.action == 'run':
            result = execute(args)
        else:
            if args.run_dir.is_symlink():
                raise ValueError('RUN_DIRECTORY_SYMLINK')
            result = perform_backup(args.run_dir.absolute(), args.hf_python.absolute(), args.hf_repo)
    except Exception as error:
        if args.action == 'backup' and args.run_dir.is_dir() and not args.run_dir.is_symlink():
            write_json(args.run_dir / ('BACKUP_FAILED-' + uuid.uuid4().hex + '.json'),
                       {'status': 'FAILED', 'stage': 'BACKUP', 'code': safe_error(error), 'outputs_preserved': True})
        print(json.dumps({'status': 'FAILED', 'code': safe_error(error)}, sort_keys=True))
        return 2
    # The detailed private acceptance/receipts stay on disk. Terminal output is bounded.
    compact = {'status': result['status'], 'source_commit': result.get('source_commit', args.commit if args.action == 'run' else None)}
    if isinstance(result.get('backup'), dict):
        compact['backup'] = result['backup']
    print(json.dumps(compact, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
