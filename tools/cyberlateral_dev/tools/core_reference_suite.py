"""Run all six fixed synthetic reference audits explicitly with --run."""

import argparse
import os
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[1]


def _write_all(fd: int, raw: bytes) -> None:
    pending = memoryview(raw)
    while pending:
        count = os.write(fd, pending)
        if count <= 0:
            raise OSError('output made no progress')
        pending = pending[count:]


def _message(text: str, stream) -> None:
    try:
        fd = stream.fileno()
    except (AttributeError, OSError, ValueError):
        if stream.write(text) != len(text):
            raise OSError('message was not delivered') from None
    else:
        _write_all(fd, text.encode('utf-8'))


class _Parser(argparse.ArgumentParser):
    def _print_message(self, message, file=None) -> None:
        if message:
            _message(message, sys.stderr if file is None else file)

    def error(self, message: str) -> NoReturn:
        self.exit(2, 'REJECTED: REFERENCE_SUITE_USAGE_NO_MODEL_EXECUTION\n')


def main(argv=None) -> int:
    previous_flag, previous_paths = sys.dont_write_bytecode, list(sys.path)
    known_errors = ()
    try:
        sys.dont_write_bytecode = True
        parser = _Parser(description=__doc__, allow_abbrev=False)
        parser.add_argument('--run', required=True, action='count', default=0)
        args = parser.parse_args(argv)
        if args.run != 1:
            parser.error('exactly one run required')
        sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
        from integration_tools.core_reference_suite import ReferenceSuiteError, run_reference_suite
        from integration_tools.scenario_output import canonical

        known_errors = (ReferenceSuiteError,)
        receipt = run_reference_suite()
        code = {'CLOSED_REFERENCE_SUITE_MATCH': 0, 'CLOSED_REFERENCE_SUITE_DIFFERENT': 1}[receipt['suite_status']]
        _write_all(sys.stdout.fileno(), canonical(receipt))
        return code
    except Exception as error:
        code = error.code if isinstance(error, known_errors) else 'REFERENCE_SUITE_FAILED_WORK_MAY_BE_NONZERO'
        try:
            _message('REJECTED: ' + code + '\n', sys.stderr)
        except Exception:
            pass
        return 2
    finally:
        sys.path[:] = previous_paths
        sys.dont_write_bytecode = previous_flag


if __name__ == '__main__':
    raise SystemExit(main())
