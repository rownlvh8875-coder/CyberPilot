"""Explicit read-only private-HF restoration of the standalone synthetic DEV scope."""

import argparse
import io
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from artifacts import export_source, new_restore_directory, sha, verify_archive
from cloud_run import GATES, canonical, run_command, safe_error, write_json
from workflow_checks import check_workflows, portable_files

TOOLS = Path(__file__).resolve().parent
VERSIONS = {'numpy': '2.5.3', 'ruff': '0.16.7', 'ty': '0.0.80', 'codespell': '2.4.3', 'PyYAML': '6.0.3'}


def archive_payloads(archive: Path, digest: str) -> dict[str, bytes]:
    verify_archive(archive, digest)
    raw = archive.read_bytes()
    if sha(raw) != digest:
        raise ValueError('ARCHIVE_HASH')
    with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
        return {name: bundle.read(name) for name in bundle.namelist()}


def recover_source(repo: Path, commit: str, archive: Path, digest: str, destination: Path) -> dict:
    destination = new_restore_directory(destination)
    if destination.resolve().is_relative_to(repo.resolve()):
        raise ValueError('EXTERNAL_OUTPUT_REQUIRED')
    payloads = archive_payloads(archive, digest)
    with tempfile.TemporaryDirectory(prefix='cyberpilot-git-source-proof-') as temporary:
        reference = Path(temporary) / 'source'
        expected = export_source(repo, commit, reference)
        identity = json.loads(payloads['SOURCE_IDENTITY.json'])
        if canonical(identity) != canonical(expected):
            raise ValueError('SOURCE_IDENTITY_MISMATCH')
        members = {name.removeprefix('SOURCE/') for name in payloads if name.startswith('SOURCE/')}
        if members != set(expected['files']):
            raise ValueError('SOURCE_MEMBER_SET')
        for name in expected['files']:
            if payloads['SOURCE/' + name] != (reference / name).read_bytes():
                raise ValueError('SOURCE_GIT_MISMATCH')
    destination.mkdir(exist_ok=False)
    for name, record in expected['files'].items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(payloads['SOURCE/' + name])
        path.chmod(int(record['git_mode'], 8) & 0o777)
    return {'status': 'EXACT_GIT_MATCHED_SOURCE_RECOVERED', 'source_commit': commit,
            'source_tree': expected['tree'], 'source_files': len(expected['files']),
            'identity': expected, 'downloaded_driver_executions': 0,
            'scope': 'COMMITTED_COMPONENT_AND_ROOT_CI_CONTEXT_NOT_FULL_REPOSITORY_OR_VEHICLE_INSTALLATION'}


def validate_runtime(record: dict, venv: Path) -> None:
    if (record.get('python') != '3.12.13' or record.get('versions') != VERSIONS
            or record.get('hf_sdk_in_app') is not False
            or Path(record.get('prefix', '')).resolve() != venv.resolve()
            or not Path(record.get('numpy_origin', '')).resolve().is_relative_to(venv.resolve())):
        raise ValueError('RESTORED_RUNTIME_MISMATCH')


def verify_restored_workflows(component: Path, workflows: Path, archive: Path, digest: str) -> dict:
    result = check_workflows(component, workflows)
    portable = portable_files(workflows / 'one')
    payloads = archive_payloads(archive, digest)
    archived = {name.removeprefix('R41/'): raw for name, raw in payloads.items() if name.startswith('R41/')}
    if set(archived) != set(portable):
        raise ValueError('HF_R41_MEMBER_SET')
    if archived != portable:
        raise ValueError('HF_PORTABLE_MISMATCH')
    return {**result, 'status': 'HF_RESTORED_R41_EXACT_PASS', 'matches_pinned_hf_portable': True,
            'portable_sha256': {name: sha(raw) for name, raw in sorted(portable.items())}}


def execute(args) -> dict:
    for value, length in [(args.commit, 40), (args.archive_sha, 64), (args.revision, 40)]:
        if re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is None:
            raise ValueError('FULL_ARCHIVE_SOURCE_AND_REVISION_REQUIRED')
    output = new_restore_directory(args.output)
    repo = args.repo_root.resolve()
    if output.resolve().is_relative_to(repo):
        raise ValueError('EXTERNAL_OUTPUT_REQUIRED')
    sdk_python = args.hf_python.absolute()
    if not sdk_python.is_file() or not os.access(sdk_python, os.X_OK):
        raise ValueError('HF_INTERPRETER_REQUIRED')
    output.mkdir(exist_ok=False)
    stage = 'FETCH'
    try:
        env = os.environ.copy()
        env.update(PYTHONDONTWRITEBYTECODE='1', HF_HUB_DISABLE_PROGRESS_BARS='1',
                   UV_CACHE_DIR=str(output / 'uv-cache'), UV_PYTHON_DOWNLOADS='never',
                   UV_LINK_MODE='copy', UV_PROJECT_ENVIRONMENT=str(output / 'dev-venv'))
        raw = run_command([sdk_python, '-B', TOOLS / 'hf_archive.py', 'fetch', '--repo-id', args.hf_repo,
                           '--source-commit', args.commit, '--revision', args.revision,
                           '--archive-sha', args.archive_sha, '--output', output / 'fetched'],
                          output / 'fetch-private.log', output, env=env)
        fetched = json.loads(raw)
        expected_fetch = {'status': 'PRIVATE_FETCH_EXACT', 'repo_id': args.hf_repo, 'private': True,
                          'commit_sha': args.revision, 'archive_sha256': args.archive_sha,
                          'prefix': f'runs/{args.commit}/{args.archive_sha}/', 'verified_files': 2, 'remote_writes': 0}
        if (any(key not in fetched or canonical(fetched[key]) != canonical(value) for key, value in expected_fetch.items())):
            raise ValueError('STORAGE_RECEIPT_INVALID')
        stage = 'SOURCE_IDENTITY'
        archive = output / 'fetched/EVIDENCE.zip'
        recovered = recover_source(repo, args.commit, archive, args.archive_sha, output / 'source')
        write_json(output / 'SOURCE_RECOVERY.json', recovered)
        component = output / 'source/tools/cyberlateral_dev'
        stage = 'ENVIRONMENT'
        uv = shutil.which('uv')
        if uv is None:
            raise ValueError('UV_REQUIRED')
        version = run_command([uv, '--version'], output / 'uv-version.log', output, env=env)
        if version.decode().split()[:2] != ['uv', '0.12.23']:
            raise ValueError('UV_VERSION_REQUIRED')
        run_command([uv, 'venv', '--python', '3.12.13', output / 'dev-venv'], output / 'venv.log', output, env=env)
        run_command([uv, 'sync', '--locked', '--project', component], output / 'dependencies.log', output, env=env)
        python = output / 'dev-venv/bin/python'
        code = """import importlib.metadata as m, importlib.util as u, json, sys, numpy
print(json.dumps({'python':sys.version.split()[0], 'prefix':sys.prefix, 'numpy_origin':numpy.__file__,
 'versions':{n:m.version(n) for n in ['numpy','ruff','ty','codespell','PyYAML']},
 'hf_sdk_in_app':u.find_spec('huggingface_hub') is not None},sort_keys=True))"""
        runtime = json.loads(run_command([python, '-I', '-B', '-c', code], output / 'runtime.log', output, env=env))
        validate_runtime(runtime, output / 'dev-venv')
        run_command([python, '-I', '-B', component / 'tools/scenario.py', '--help'], output / 'cli-help.log', output, env=env)
        stage = 'SYNTHETIC_WORKFLOWS'
        workflows = output / 'workflows'
        workflows.mkdir()
        fixed = json.loads((component / 'reference/r41_regression_expected_v1.json').read_bytes())
        if fixed['order'] != ['combined_boundaries_v1.json', 'repeated_inactive_crossing_v1.json', 'long_fault_cycles_v1.json']:
            raise ValueError('R41_FIXED_PACK_CONTRACT')
        for alias in ('one', 'two', 'baseline'):
            inputs = [item for name in fixed['order'] for item in ('--input', component / 'examples/r41' / name)]
            if alias == 'baseline':
                inputs += ['--baseline', workflows / 'one/batch']
            run_command([python, '-I', '-B', component / 'tools/scenario_workflow.py', *inputs,
                         '--output', workflows / alias], output / (alias + '.log'), output, env=env)
        stage = 'SAVED_ACCEPTANCE'
        raw = run_command([python, '-B', TOOLS / 'cloud_restore.py', 'check-saved', '--component', component,
                           '--workflows', workflows, '--archive', archive, '--archive-sha', args.archive_sha],
                          output / 'saved-acceptance.log', output, env=env)
        acceptance = json.loads(raw)
        if acceptance.get('status') != 'HF_RESTORED_R41_EXACT_PASS':
            raise ValueError('SAVED_ACCEPTANCE_REQUIRED')
        for name, record in recovered['identity']['files'].items():
            path = output / 'source' / name
            if path.is_symlink() or len(path.read_bytes()) != record['byte_size'] or sha(path.read_bytes()) != record['sha256']:
                raise ValueError('RESTORED_SOURCE_CHANGED')
        result = {'status': 'PRIVATE_HF_DEV_RESTORE_SYNTHETIC_PASS', 'source_commit': args.commit,
                  'source_tree': recovered['source_tree'], 'source_files': recovered['source_files'],
                  'fetch': fetched, 'runtime': runtime, 'R41': acceptance, 'gates': GATES,
                  'full_700_test_rerun': False, 'physical_machine_independence': False,
                  'scope': recovered['scope'], 'remote_writes': 0,
                  'F61_Controller_vehicle_Runtime_CAN_actual_r_dt': 0, 'vehicle_installation': 0,
                  'downloaded_driver_executions': 0, 'source_bytes_unchanged': True}
        write_json(output / 'DEV_START.json', {'source_commit': args.commit, 'source_root': str(output / 'source'),
                                              'component': str(component), 'python': str(python), 'gates': GATES,
                                              'scope': recovered['scope'], 'requires': 'RESTORE_RESULT.json status PASS'})
        write_json(output / 'RESTORE_RESULT.json', result)
        return result
    except Exception as error:
        failure = {'status': 'FAILED', 'stage': stage, 'code': safe_error(error), 'outputs_preserved': True}
        write_json(output / 'FAILURE.json', failure)
        raise ValueError(failure['code']) from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    run = commands.add_parser('run')
    run.add_argument('--repo-root', type=Path, required=True)
    run.add_argument('--commit', required=True)
    run.add_argument('--archive-sha', required=True)
    run.add_argument('--revision', required=True)
    run.add_argument('--hf-repo', default='jjuinho/cyberpilot-evidence')
    run.add_argument('--hf-python', type=Path, required=True)
    run.add_argument('--output', type=Path, required=True)
    check = commands.add_parser('check-saved')
    check.add_argument('--component', type=Path, required=True)
    check.add_argument('--workflows', type=Path, required=True)
    check.add_argument('--archive', type=Path, required=True)
    check.add_argument('--archive-sha', required=True)
    args = parser.parse_args(argv)
    try:
        result = (execute(args) if args.action == 'run' else
                  verify_restored_workflows(args.component, args.workflows, args.archive, args.archive_sha))
    except Exception as error:
        print(json.dumps({'status': 'FAILED', 'code': safe_error(error)}, sort_keys=True))
        return 2
    if args.action == 'run':
        result = {key: result[key] for key in ('status', 'source_commit', 'source_files', 'remote_writes')}
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
