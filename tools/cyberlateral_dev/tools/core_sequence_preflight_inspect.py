"""Inspect saved preflight JSON/summary/checksum against an original ZIP."""

import argparse
import os
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[1]


def _write_all(fd: int, raw: bytes) -> None:
    pending = memoryview(raw)
    while pending:
        written = os.write(fd, pending)
        if written <= 0:
            raise OSError('output made no progress')
        pending = pending[written:]


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
        self.exit(2, 'REJECTED: PREFLIGHT_INSPECT_USAGE_NO_MODEL_EXECUTION\n')


def main(argv=None) -> int:
    previous_bytecode = sys.dont_write_bytecode
    previous_paths = list(sys.path)
    known_errors = ()
    try:
        sys.dont_write_bytecode = True
        parser = _Parser(description=__doc__, allow_abbrev=False)
        for name in ('--input-root', '--archive', '--sha256'):
            parser.add_argument(name, required=True, action='append')
        args = parser.parse_args(argv)
        if any(len(values) != 1 or not values[0] for values in (args.input_root, args.archive, args.sha256)):
            parser.error('exactly one nonempty value for each option required')
        root, archive = Path(args.input_root[0]), Path(args.archive[0])
        sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
        from integration_tools.core_sequence_archive_preflight import ArchivePreflightError
        from integration_tools.core_sequence_preflight_inspect import PreflightInspectError, inspect_preflight_report
        from integration_tools.core_sequence_preflight_report import PreflightReportError
        from integration_tools.scenario_output import canonical

        known_errors = (ArchivePreflightError, PreflightReportError, PreflightInspectError)
        receipt = inspect_preflight_report(root, archive, args.sha256[0])
        _write_all(sys.stdout.fileno(), canonical(receipt))
        return 0
    except Exception as error:
        code = error.code if isinstance(error, known_errors) else 'PREFLIGHT_INSPECT_FAILED_NO_MODEL_EXECUTION'
        try:
            _message('REJECTED: ' + code + '\n', sys.stderr)
        except Exception:
            pass
        return 2
    finally:
        sys.path[:] = previous_paths
        sys.dont_write_bytecode = previous_bytecode


if __name__ == '__main__':
    raise SystemExit(main())
