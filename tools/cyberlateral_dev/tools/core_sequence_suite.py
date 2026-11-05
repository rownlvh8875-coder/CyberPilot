"""Check or explicitly run the fixed three-case suite; JSON stdout summary only."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    try:
        directory = tempfile.TemporaryDirectory(prefix='cyberlateral-core12-cache-')
    except OSError:
        print('REJECTED: SUITE_CACHE_IO_NO_MODEL_EXECUTION', file=sys.stderr)
        return 2
    previous = sys.pycache_prefix
    mode = 'check'
    suite_error_type = None
    try:
        with directory as cache:
            try:
                sys.pycache_prefix = cache
                sys.path.insert(0, str(ROOT))
                from integration_tools.core_sequence_suite import SuiteError, check_closed_suite, exit_code, run_closed_suite
                from integration_tools.scenario_output import canonical

                suite_error_type = SuiteError
                parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
                commands = parser.add_subparsers(dest='command', required=True)
                check = commands.add_parser('check', help='Inspect exactly three saved case folders, no model execution', allow_abbrev=False)
                check.add_argument('--input-root', type=Path, required=True)
                check.add_argument('--baseline-root', type=Path)
                run = commands.add_parser('run', help='Explicitly execute all three closed synthetic cases', allow_abbrev=False)
                run.add_argument('--output-root', type=Path, required=True, help='NEW suite root outside checkout')
                run.add_argument('--baseline-root', type=Path)
                args = parser.parse_args(argv)
                mode = args.command
                report = (check_closed_suite(args.input_root, args.baseline_root) if mode == 'check'
                          else run_closed_suite(args.output_root, args.baseline_root))
                result_code = exit_code(report)
                raw = canonical(report)
            finally:
                sys.pycache_prefix = previous
        pending = memoryview(raw)
        while pending:
            written = os.write(sys.stdout.fileno(), pending)
            if written <= 0:
                raise OSError('stdout made no progress')
            pending = pending[written:]
        return result_code
    except Exception as error:
        if suite_error_type is not None and isinstance(error, suite_error_type):
            code = error.code
        else:
            code = ('SUITE_CHECK_FAILED_NO_MODEL_EXECUTION' if mode == 'check'
                    else 'SUITE_RUN_FAILED_WORK_MAY_BE_NONZERO')
        print('REJECTED: ' + code, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
