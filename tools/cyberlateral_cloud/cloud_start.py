"""One explicit frozen-profile private recovery; never publish or activate vehicles."""

import argparse
import json
import os
import re
from pathlib import Path

from artifacts import SOURCE_CONTEXT, SOURCE_PREFIX, git, new_restore_directory
from browser_compare import compare_saved_browser
from browser_compare_summary import render_comparison_summary
from cloud_restore import validate_runtime
from cloud_run import GATES, canonical, run_command, safe_error, write_json
from tooling_restore import recover_tooling

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
_PROFILE = {
    'schema_version': 1, 'profile_id': 'R67_MAIN_V1', 'repo_id': 'jjuinho/cyberpilot-evidence',
    'source_commit': 'f562377abefdc5796f54b4f98c0c3ded9a5a4a3e',
    'source_tree': '6b42352b0ee2a2a5259837a4df779d47c7b7c54a',
    'dev': {'sha256': 'adeaf66e4212ffa350c5b851c684153eac0f5953716f9e9449afd22d5c031c22',
            'revision': '5916191894529c579451b21c7f3f18b9f5eee2ed'},
    'tools': {'sha256': 'c7ca0b6fd9ed46cd31d3456b39536b35203799070dfee0e89ed485eb7004723d',
              'revision': '9d41b3cccacc25fa7c4843b1a1a44f23a33ed16e'},
}


def get_profile() -> dict:
    return json.loads(canonical(_PROFILE))


def _need(condition, code):
    if not condition:
        raise ValueError(code)


def _validate_profile(profile):
    code = 'START_PROFILE_INVALID'
    _need(type(profile) is dict and set(profile) == set(_PROFILE), code)
    _need(type(profile.get('schema_version')) is int and profile['schema_version'] == 1, code)
    for name, pattern in [('profile_id', '[A-Z][A-Z0-9_]{0,79}'), ('source_commit', '[0-9a-f]{40}'),
                          ('source_tree', '[0-9a-f]{40}'),
                          ('repo_id', '[A-Za-z0-9][A-Za-z0-9_.-]{0,95}/[A-Za-z0-9][A-Za-z0-9_.-]{0,95}')]:
        value = profile.get(name)
        _need(type(value) is str and re.fullmatch(pattern, value) is not None, code)
    for role in ['dev', 'tools']:
        block = profile[role]
        _need(type(block) is dict and set(block) == {'sha256', 'revision'}, code)
        for field, length in [('sha256', 64), ('revision', 40)]:
            value = block[field]
            _need(type(value) is str and re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is not None, code)


def _matches(record, expected, code):
    _need(type(record) is dict and all(k in record and canonical(record[k]) == canonical(v)
                                     for k, v in expected.items()), code)


def _fetch_receipt(record, profile, role):
    expected = {'status': 'PRIVATE_FETCH_EXACT', 'repo_id': profile['repo_id'], 'private': True,
                'commit_sha': profile[role]['revision'], 'archive_sha256': profile[role]['sha256'],
                'prefix': f'runs/{profile["source_commit"]}/{profile[role]["sha256"]}/',
                'verified_files': 2, 'remote_writes': 0}
    _matches(record, expected, 'START_FETCH_RECEIPT_INVALID')


def _dev_receipt(dev, profile, count, folder):
    _matches(dev, {'status': 'PRIVATE_HF_DEV_RESTORE_SYNTHETIC_PASS', 'source_commit': profile['source_commit'],
             'source_tree': profile['source_tree'], 'source_files': count, 'gates': GATES,
             'full_700_test_rerun': False, 'physical_machine_independence': False,
             'scope': 'COMMITTED_COMPONENT_AND_ROOT_CI_CONTEXT_NOT_FULL_REPOSITORY_OR_VEHICLE_INSTALLATION',
             'remote_writes': 0, 'F61_Controller_vehicle_Runtime_CAN_actual_r_dt': 0,
             'vehicle_installation': 0, 'downloaded_driver_executions': 0, 'source_bytes_unchanged': True},
             'START_DEV_RECEIPT_INVALID')
    _fetch_receipt(dev.get('fetch'), profile, 'dev')
    _need(type(dev.get('runtime')) is dict, 'START_DEV_RECEIPT_INVALID')
    validate_runtime(dev['runtime'], folder / 'dev-venv')
    _matches(dev.get('R41'), {'status': 'HF_RESTORED_R41_EXACT_PASS', 'portable_files': 26,
             'baseline_samples': 324, 'baseline_differences': 0, 'explicit_model_steps': 972,
             'explicit_reference_steps': 972, 'matches_pinned_hf_portable': True}, 'START_DEV_RECEIPT_INVALID')
    _need((folder / 'DEV_START.json').is_file(), 'START_DEV_RECEIPT_INVALID')


def run_profile(repo: Path, sdk: Path, output: Path, profile: dict) -> dict:
    """Testable engine; CLI alone selects the built-in, detached frozen profile."""
    _validate_profile(profile)
    profile = json.loads(canonical(profile))
    repo, sdk = repo.resolve(), sdk.absolute()
    output = new_restore_directory(output)
    _need(not output.resolve().is_relative_to(repo), 'EXTERNAL_OUTPUT_REQUIRED')
    output.mkdir(exist_ok=False)
    stage = 'SDK_PREFLIGHT'
    try:
        _need(sdk.is_file() and os.access(sdk, os.X_OK), 'HF_INTERPRETER_REQUIRED')
        try:
            _need(Path(git(repo, 'rev-parse', '--show-toplevel').decode().strip()).resolve() == repo,
                  'PINNED_GIT_SOURCE_UNAVAILABLE')
            _need(git(repo, 'rev-parse', profile['source_commit'] + '^{tree}').decode().strip() == profile['source_tree'],
                  'PINNED_GIT_SOURCE_UNAVAILABLE')
            count = len(git(repo, 'ls-tree', '-r', '--name-only', profile['source_commit'], '--',
                           SOURCE_PREFIX.rstrip('/'), *SOURCE_CONTEXT).splitlines())
            _need(count > 0, 'PINNED_GIT_SOURCE_UNAVAILABLE')
        except (OSError, ValueError) as error:
            raise ValueError('PINNED_GIT_SOURCE_UNAVAILABLE') from error
        except Exception:
            raise ValueError('PINNED_GIT_SOURCE_UNAVAILABLE') from None
        write_json(output / 'PROFILE.json', profile)
        env = os.environ.copy()
        env.update(PYTHONDONTWRITEBYTECODE='1', HF_HUB_DISABLE_PROGRESS_BARS='1', UV_PYTHON_DOWNLOADS='never')
        stage = 'DEV_RESTORE'
        raw = run_command([sdk, '-B', TOOLS / 'cloud_restore.py', 'run', '--repo-root', repo,
            '--commit', profile['source_commit'], '--archive-sha', profile['dev']['sha256'],
            '--revision', profile['dev']['revision'], '--hf-repo', profile['repo_id'], '--hf-python', sdk,
            '--output', output / 'dev'], output / 'dev-restore-private.log', output, env=env)
        _need(json.loads(raw).get('status') == 'PRIVATE_HF_DEV_RESTORE_SYNTHETIC_PASS', 'START_DEV_RECEIPT_INVALID')
        dev = json.loads((output / 'dev/RESTORE_RESULT.json').read_bytes())
        _dev_receipt(dev, profile, count, output / 'dev')
        stage = 'TOOL_FETCH'
        raw = run_command([sdk, '-B', TOOLS / 'hf_archive.py', 'fetch', '--repo-id', profile['repo_id'],
            '--source-commit', profile['source_commit'], '--archive-sha', profile['tools']['sha256'],
            '--revision', profile['tools']['revision'], '--output', output / 'tool-fetched'],
            output / 'tool-fetch-private.log', output, env=env)
        fetched = json.loads(raw)
        _fetch_receipt(fetched, profile, 'tools')
        write_json(output / 'TOOL_FETCH.json', fetched)
        stage = 'TOOL_SOURCE'
        tools = recover_tooling(repo, profile['source_commit'], output / 'tool-fetched/EVIDENCE.zip',
                                profile['tools']['sha256'], output / 'tooling')
        write_json(output / 'TOOL_RECOVERY.json', tools)
        stage = 'SAVED_COMPARISON'
        saved = output / 'tooling/saved'
        different = compare_saved_browser(saved / 'one', saved / 'two')
        same_fail = compare_saved_browser(saved / 'fail', saved / 'fail')
        _need(different['status'] == 'R66_SAVED_BROWSER_BYTES_DIFFERENT'
              and same_fail['status'] == 'R66_SAVED_BROWSER_EXACT_BYTES_MATCH'
              and all(same_fail[side + '_verification']['recorded_status'] == 'R60_BROWSER_SMOKE_FAIL'
                      for side in ['baseline', 'candidate']), 'START_COMPARISON_INVALID')
        comparisons = {'different': different, 'same_fail': same_fail}
        folder = output / 'comparisons'
        folder.mkdir()
        for name, record in comparisons.items():
            write_json(folder / (name + '.json'), record)
            with (folder / (name + '_KO.md')).open('xb') as stream:
                stream.write(render_comparison_summary(record))
        result = {'status': 'R68_PINNED_CLOUD_START_PASS', 'profile': profile, 'dev_source_files': dev['source_files'],
                  'tool_source_files': tools['source_files'], 'saved_files': tools['saved_files'],
                  'comparisons': comparisons, 'gates': GATES, 'remote_writes': 0,
                  'downloaded_driver_executions': 0, 'recovered_tool_source_executions': 0,
                  'new_passive_comparison_model_executions': 0, 'new_browser_F61_actual_r_dt_vehicle_work': 0,
                  'synthetic_work': {'scope': 'EXPLICIT_RESTORED_R41_NOT_UNIT_AGGREGATE',
                                     'model_steps': dev['R41']['explicit_model_steps'],
                                     'reference_steps': dev['R41']['explicit_reference_steps']},
                  'children': {'dev': 'dev/DEV_START.json', 'tooling': 'TOOL_RECOVERY.json'},
                  'physical_machine_independence': False,
                  'scope': 'OFFLINE_DEV_AND_SAVED_BYTES_NOT_VEHICLE_OR_NEW_SCREEN_VERDICT'}
        stage = 'SEAL'
        summary = ('# 고정 클라우드 개발판 복구 완료\n\n'
                   '복구 완료는 화면 PASS가 아닙니다. 동일한 FAIL의 MATCH도 새 품질 승인이 아닙니다.\n\n'
                   '- [DEV 실행 정보](dev/DEV_START.json)\n'
                   '- [도구 source 복구 기록](TOOL_RECOVERY.json)\n'
                   '- [서로 다른 저장 묶음](comparisons/different_KO.md)\n'
                   '- [동일한 원래 FAIL 묶음](comparisons/same_fail_KO.md)\n\n'
                   'START_RESULT.json이 전체 완료 표시입니다. 자식 DEV 성공만으로 전체 완료가 아닙니다.\n'
                   'R41 합성 모델/참조 작업은 수행했습니다. 새 브라우저/F61/실차 실행은 없습니다.\n'
                   'R_BUDGET UNRESOLVED · Static Gate FAIL · 실제 r/T2/scale=null · 실차 활성화 NOT_ALLOWED.\n')
        with (output / 'START_KO.md').open('xb') as stream:
            stream.write(summary.encode())
        pending = output / 'START_RESULT.pending.json'
        write_json(pending, result)
        os.link(pending, output / 'START_RESULT.json')
        return result
    except Exception as error:
        code = safe_error(error)
        write_json(output / 'FAILURE.json', {'status': 'FAILED', 'stage': stage, 'code': code, 'outputs_preserved': True})
        raise ValueError(code) from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest='action', required=True)
    commands.add_parser('profile', allow_abbrev=False)
    run = commands.add_parser('run', allow_abbrev=False)
    run.add_argument('--repo-root', type=Path, default=REPO)
    run.add_argument('--hf-python', type=Path, required=True)
    run.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = get_profile() if args.action == 'profile' else run_profile(args.repo_root, args.hf_python, args.output, get_profile())
    except Exception as error:
        print(json.dumps({'status': 'FAILED', 'code': safe_error(error)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
