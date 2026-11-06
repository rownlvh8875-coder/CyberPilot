"""Print a saved suite's Korean input preflight summary without replay."""

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
        self.exit(2, 'REJECTED: PREFLIGHT_REPORT_USAGE_NO_MODEL_EXECUTION\n')


def main(argv=None) -> int:
    previous_bytecode = sys.dont_write_bytecode
    previous_paths = list(sys.path)
    known_errors = ()
    try:
        sys.dont_write_bytecode = True
        parser = _Parser(description=__doc__, allow_abbrev=False)
        parser.add_argument('--archive', required=True, action='append')
        parser.add_argument('--sha256', required=True, action='append')
        args = parser.parse_args(argv)
        if len(args.archive) != 1 or not args.archive[0] or len(args.sha256) != 1 or not args.sha256[0]:
            parser.error('exactly one nonempty archive and SHA required')
        archive = Path(args.archive[0])
        sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
        from integration_tools.core_sequence_archive_preflight import ArchivePreflightError
        from integration_tools.core_sequence_preflight_report import PreflightReportError, report_preflight_archive

        known_errors = (ArchivePreflightError, PreflightReportError)
        receipt, markdown = report_preflight_archive(archive, args.sha256[0])
        code = {'INPUTS_COMPATIBLE': 0, 'INPUTS_REJECTED': 1}[receipt['preflight_status']]
        _write_all(sys.stdout.fileno(), markdown)
        return code
    except Exception as error:
        code = error.code if isinstance(error, known_errors) else 'PREFLIGHT_REPORT_FAILED_NO_MODEL_EXECUTION'
        try:
            _message('REJECTED: ' + code + '\n', sys.stderr)
        except Exception:
            # Diagnostic delivery cannot replace operational2 with a flush failure.
            pass
        return 2
    finally:
        sys.path[:] = previous_paths
        sys.dont_write_bytecode = previous_bytecode


if __name__ == '__main__':
    raise SystemExit(main())
