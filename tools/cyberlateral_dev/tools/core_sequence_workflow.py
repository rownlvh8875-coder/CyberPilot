"""Explicit saved-only check or closed synthetic run; JSON stdout receipt only."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    try:
        directory = tempfile.TemporaryDirectory(prefix='cyberlateral-core11-cache-')
    except OSError:
        print('REJECTED: WORKFLOW_CACHE_IO_NO_MODEL_EXECUTION', file=sys.stderr)
        return 2
    previous = sys.pycache_prefix
    mode = 'check'
    workflow_error_type = None
    try:
        with directory as cache:
            try:
                sys.pycache_prefix = cache
                sys.path.insert(0, str(ROOT))
                from integration_tools.core_sequence_cases import CASE_IDS
                from integration_tools.core_sequence_workflow import WorkflowError, check_saved_sequence, exit_code, run_closed_sequence
                from integration_tools.scenario_output import canonical

                workflow_error_type = WorkflowError
                parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
                commands = parser.add_subparsers(dest='command', required=True)
                check = commands.add_parser('check', help='Read existing packages only, no new model execution', allow_abbrev=False)
                check.add_argument('--input', type=Path, required=True)
                check.add_argument('--baseline', type=Path)
                run = commands.add_parser('run', help='Explicitly execute one named closed synthetic fixture', allow_abbrev=False)
                run.add_argument('--case', choices=CASE_IDS, required=True)
                run.add_argument('--output', type=Path, required=True, help='NEW CORE8 package folder outside checkout')
                run.add_argument('--baseline', type=Path)
                args = parser.parse_args(argv)
                mode = args.command
                if args.command == 'check':
                    report = check_saved_sequence(args.input, args.baseline)
                else:
                    report = run_closed_sequence(args.case, args.output, args.baseline)
                result_code = exit_code(report)
                raw = canonical(report)
            finally:
                sys.pycache_prefix = previous
        # Cache teardown is part of the operation and must finish before receipt IO.
        pending = memoryview(raw)
        while pending:
            written = os.write(sys.stdout.fileno(), pending)
            if written <= 0:
                raise OSError('stdout made no progress')
            pending = pending[written:]
        return result_code
    except Exception as error:
        if workflow_error_type is not None and isinstance(error, workflow_error_type):
            code = error.code
        else:
            code = ('WORKFLOW_CHECK_FAILED_NO_MODEL_EXECUTION' if mode == 'check'
                    else 'WORKFLOW_RUN_FAILED_WORK_MAY_BE_NONZERO')
        print('REJECTED: ' + code, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
