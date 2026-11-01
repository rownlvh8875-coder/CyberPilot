"""Explicit fixed R19–R26 native suite, separate from the default pure gate."""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from native_qualification.run import qualify
from native_qualification.suite_profiles import ROOT, STAGE_IDS, load_profiles
from native_qualification.suite_report import build_summary, render_report
from native_qualification.suite_validation import FILES, validate_stage
from native_qualification.worker import canonical, sha, verify_experiment, verify_inputs

REPORTS = ('SUITE_RECEIPT.json', 'SUITE_REPORT_KO.md', 'SUITE_SUMMARY.json')


def _preflight(python: Path, wheel: Path, package_wheel: Path) -> None:
    verify_experiment(False, True, package_wheel)
    verify_inputs(wheel, ROOT / 'reference/car.capnp')
    if not python.is_file() or not os.access(python, os.X_OK):
        raise ValueError('SUITE_PYTHON_PATH')


def _artifact_names() -> list[str]:
    return sorted([stage + '/' + name for stage in STAGE_IDS for name in (*FILES, 'SHA256SUMS.txt')] + list(REPORTS))


def _publish(staging: Path, output: Path) -> None:
    output.mkdir(exist_ok=False)
    for stage in STAGE_IDS:
        (output / stage).mkdir(exist_ok=False)
    names = [name for name in _artifact_names() if name != 'SUITE_SUMMARY.json'] + ['SHA256SUMS.txt', 'SUITE_SUMMARY.json']
    for name in names:
        os.link(staging / name, output / name)


def run_suite(python: Path, wheel: Path, package_wheel: Path, output: Path, *, enabled: bool = False) -> dict:
    if output.exists() or output.is_symlink():
        raise FileExistsError('OUTPUT_EXISTS')
    if type(enabled) is not bool:
        raise ValueError('SUITE_EXPLICIT_BOOL')
    if not enabled:
        raise ValueError('SUITE_OPT_IN_REQUIRED')
    if not output.parent.is_dir():
        raise ValueError('SUITE_PARENT_REQUIRED')
    profiles = load_profiles()
    _preflight(python, wheel, package_wheel)
    with tempfile.TemporaryDirectory(prefix='.r27-staging-', dir=output.parent) as scratch:
        staging = Path(scratch)
        rows = []
        for profile in profiles:
            options: dict[str, Any] = {} if profile.mode is None else {profile.mode: True}
            if profile.stage_id not in ('R19', 'R20'):
                options['package_wheel'] = package_wheel
            returned = qualify(python, wheel, staging / profile.stage_id, **options)
            row = validate_stage(staging / profile.stage_id, profile.stage_id)
            if sha(canonical(returned)) != row['summary_sha256']:
                raise ValueError('SUITE_RETURN_MISMATCH')
            rows.append(row)
        final_rows = [validate_stage(staging / profile.stage_id, profile.stage_id) for profile in profiles]
        if canonical(rows) != canonical(final_rows):
            raise ValueError('SUITE_STAGE_CHANGED')
        summary = build_summary(final_rows)
        (staging / 'SUITE_SUMMARY.json').write_bytes(canonical(summary))
        (staging / 'SUITE_REPORT_KO.md').write_text(render_report(summary))
        receipt = {'scope': 'BOUNDED_PROCESS_AND_FILE_RECEIPTS_NOT_OS_AUTHENTICATION',
                   'python': str(python.absolute()), 'wheel': str(wheel.absolute()), 'public_wheel': str(package_wheel.absolute()),
                   'stages': {stage: {name: sha((staging / stage / name).read_bytes()) for name in
                                      ['RECEIPT_1.json', 'RECEIPT_2.json', 'SHA256SUMS.txt']} for stage in STAGE_IDS}}
        (staging / 'SUITE_RECEIPT.json').write_bytes(canonical(receipt))
        if {p.name for p in staging.iterdir()} != {*STAGE_IDS, *REPORTS}:
            raise ValueError('SUITE_STAGING_FILES')
        names = _artifact_names()
        (staging / 'SHA256SUMS.txt').write_text(''.join(sha((staging / name).read_bytes()) + '  ' + name + '\n' for name in names))
        _publish(staging, output)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixed-native-suite', action='store_true', help='Explicitly execute only all eight fixed synthetic R19–R26 profiles')
    parser.add_argument('--python', type=Path, required=True, help='Separate pinned native venv interpreter')
    parser.add_argument('--wheel', type=Path, required=True, help='Exact pinned native wheel; never installed here')
    parser.add_argument('--package-wheel', type=Path, required=True, help='Exact sealed public0.3.0 wheel')
    parser.add_argument('--output', type=Path, required=True, help='New directory under an existing parent; never overwritten')
    args = parser.parse_args()
    try:
        summary = run_suite(args.python, args.wheel, args.package_wheel, args.output, enabled=args.fixed_native_suite)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print('REJECTED:' + str(error), file=sys.stderr)
        return 2
    print(summary['status'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
