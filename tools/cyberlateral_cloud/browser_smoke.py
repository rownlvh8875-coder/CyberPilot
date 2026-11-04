"""Opt-in R32 fixture browser check, not numerical or vehicle qualification."""

import argparse
import json
import os
import sys
from pathlib import Path

from artifacts import manifest, new_restore_directory, sha
from browser_probe import PROFILES, browser_library, run_browser
from browser_summary import render_summary

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
SOURCE_NAMES = ('project/scenario_report_fixture.py', 'integration_tools/__init__.py',
                'integration_tools/scenario_report_data.py', 'integration_tools/scenario_report_html.py',
                'integration_tools/scenario_report_run.py', 'integration_tools/scenario_input.py',
                'integration_tools/scenario_output.py', 'tools/scenario_report.py')
PORTABLE_NAMES = ('INPUT.json', 'RESULTS.json', 'TRACE.csv', 'SUMMARY_KO.md')
FIXTURE_CODE = '''import json,sys
from pathlib import Path
component,output=map(Path,sys.argv[1:3])
sys.path[:0]=[str(component/'project'),str(component)]
from scenario_report_fixture import write_bundle
for profile in ['sign','resumed']:write_bundle(output/profile,profile)
forbidden={'cyberlateral_dev','numpy','capnp','openpilot','opendbc','cereal','synthetic_rate_constraint_feasibility_v1'}
if {name.split('.')[0] for name in sys.modules}&forbidden:raise ValueError('FIXTURE_MODEL_IMPORT')
print(json.dumps({'profiles':2,'model_imports':0,'runtime_attestation':False},sort_keys=True))
'''


def source_snapshot(component) -> dict:
    names = list(SOURCE_NAMES) + ['project/fixtures/r31_report/' + p + '/' + n for p in PROFILES for n in PORTABLE_NAMES]
    result = {}
    try:
        for name in names:
            path = component / name
            if (not path.is_file() or any(p.is_symlink() for p in (path, *path.parents))
                    or path.stat().st_size > 8 * 1024 * 1024):
                raise ValueError('COMPONENT_SOURCE_REQUIRED')
            result[name] = sha(path.read_bytes())
    except OSError:
        raise ValueError('COMPONENT_SOURCE_REQUIRED') from None
    return result


def validate_paths(component, app_python, browser, output) -> dict:
    output = new_restore_directory(output)
    if output.resolve().is_relative_to(component.resolve()) or output.resolve().is_relative_to(REPO):
        raise ValueError('EXTERNAL_OUTPUT_REQUIRED')
    source = source_snapshot(component)
    for path, code in [(app_python, 'APP_INTERPRETER_REQUIRED'), (browser, 'BROWSER_EXECUTABLE_REQUIRED')]:
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError(code)
    return source


def tree_hashes(root) -> dict:
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('EVIDENCE_SYMLINK')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = sha(path.read_bytes())
    return result


def child(command, output, name):
    # Reuse the existing bounded process-group/log runner, not unbounded capture.
    from ci_verify import run_check

    try:
        return run_check(command, output / name, output, timeout=120,
                         env=os.environ | {'PYTHONDONTWRITEBYTECODE': '1'})
    except (OSError, ValueError):
        raise ValueError('FIXTURE_OR_RENDER_FAILED') from None


def prepare_reports(component, app_python, output):
    fixture_root, reports = output / 'fixture-inputs', output / 'reports'
    fixture_root.mkdir()
    reports.mkdir()
    receipt = json.loads(child([app_python, '-I', '-B', '-c', FIXTURE_CODE, component, fixture_root],
                               output, 'fixture-preparation.log'))
    if receipt != {'profiles': 2, 'model_imports': 0, 'runtime_attestation': False}:
        raise ValueError('FIXTURE_PREPARATION_IDENTITY')
    for profile in PROFILES:
        for name in PORTABLE_NAMES:
            if (fixture_root / profile / name).read_bytes() != (component / 'project/fixtures/r31_report' / profile / name).read_bytes():
                raise ValueError('FIXTURE_PORTABLE_IDENTITY')
        child([app_python, '-I', '-B', component / 'tools/scenario_report.py',
               '--input', fixture_root / profile, '--output', reports / profile], output, profile + '-render.log')
        receipt = json.loads((reports / profile / 'RECEIPT.json').read_bytes())
        if receipt['renderer_model_executions'] != 0 or receipt['forbidden_modules_loaded']:
            raise ValueError('RENDERER_MODEL_IMPORT')
        for name, expected in receipt['renderer_source_hashes'].items():
            if name not in SOURCE_NAMES or sha((component / name).read_bytes()) != expected:
                raise ValueError('RENDERER_SOURCE_IDENTITY')
    return reports


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def write_json(path, value):
    with path.open('xb') as stream:
        stream.write(json_bytes(value))


def publish_result(output, result):
    owned = tree_hashes(output)
    files = {name: (output / name).read_bytes() for name in owned}
    files['RESULT.json'] = json_bytes(result)
    files['SUMMARY_KO.md'] = render_summary(result, owned)
    with (output / 'SUMMARY_KO.md').open('xb') as stream:
        stream.write(files['SUMMARY_KO.md'])
    with (output / 'SHA256SUMS.txt').open('xb') as stream:
        stream.write(manifest(files))
    # RESULT is the completion marker: checksum publication must finish first.
    with (output / 'RESULT.json').open('xb') as stream:
        stream.write(files['RESULT.json'])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ['component', 'app-python', 'browser', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(argv)
    created = False
    stage = 'PREFLIGHT'
    try:
        before = validate_paths(args.component, args.app_python, args.browser, args.output)
        browser_library()
        output, component = args.output.absolute(), args.component.absolute()
        output.mkdir(exist_ok=False)
        created = True
        stage = 'RENDER'
        reports = prepare_reports(component, args.app_python.absolute(), output)
        inputs_before, reports_before = tree_hashes(output / 'fixture-inputs'), tree_hashes(reports)
        stage = 'BROWSER'
        result = run_browser(reports, output / 'captures', args.browser.absolute())
        stage = 'SOURCE_AND_INPUT_INTEGRITY'
        if (source_snapshot(component) != before or inputs_before != tree_hashes(output / 'fixture-inputs')
                or reports_before != tree_hashes(reports)):
            raise ValueError('SOURCE_OR_INPUT_CHANGED')
        result.update(status='R60_BROWSER_SMOKE_FAIL' if result['failures'] else 'R60_BROWSER_SMOKE_PASS',
                      schema_version=1, source_sha256=before, source_selected_files_unchanged=True,
                      input_sha256=inputs_before, report_sha256=reports_before,
                      captures=tree_hashes(output / 'captures'), fixture_runtime_attestation=False,
                      model_F61_r_dt_native_vehicle_executions=0,
                      scope='FIXED_SAVED_SYNTHETIC_LAYOUT_NOT_NUMERICAL_ORIGIN_ALL_BROWSERS_OR_VEHICLE_PROOF')
        stage = 'PUBLICATION'
        publish_result(output, result)
        print(json.dumps({'status': result['status'], 'cases': len(result['cases']), 'failures': result['failures']}, sort_keys=True))
        return 1 if result['failures'] else 0
    except Exception as error:
        code = str(error) if type(error) is ValueError and str(error).replace('_', '').isupper() else 'BROWSER_SMOKE_FAILED'
        if created:
            write_json(args.output.absolute() / 'FAILURE.json', {'status': 'FAILED', 'stage': stage, 'code': code,
                                                               'partial_output_preserved': True})
        print('REJECTED: ' + code, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
