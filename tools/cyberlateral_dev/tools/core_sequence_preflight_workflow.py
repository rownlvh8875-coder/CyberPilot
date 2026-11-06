"""Save input preflight JSON, Korean summary and checksum to a NEW folder."""

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
        self.exit(2, 'REJECTED: PREFLIGHT_WORKFLOW_USAGE_NO_MODEL_EXECUTION\n')


def main(argv=None) -> int:
    previous_bytecode = sys.dont_write_bytecode
    previous_paths = list(sys.path)
    known_errors = ()
    try:
        sys.dont_write_bytecode = True
        parser = _Parser(description=__doc__, allow_abbrev=False)
        for name in ('--archive', '--sha256', '--output-root'):
            parser.add_argument(name, required=True, action='append')
        args = parser.parse_args(argv)
        if any(len(values) != 1 or not values[0] for values in (args.archive, args.sha256, args.output_root)):
            parser.error('exactly one nonempty value for each option required')
        archive, output = Path(args.archive[0]), Path(args.output_root[0])
        sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
        from integration_tools.core_sequence_archive_preflight import ArchivePreflightError
        from integration_tools.core_sequence_archive_workflow import ArchiveWorkflowError
        from integration_tools.core_sequence_preflight_report import PreflightReportError
        from integration_tools.core_sequence_preflight_workflow import publish_preflight_report
        from integration_tools.scenario_output import canonical

        known_errors = (ArchivePreflightError, PreflightReportError, ArchiveWorkflowError)
        receipt = publish_preflight_report(archive, args.sha256[0], output)
        code = {'INPUTS_COMPATIBLE': 0, 'INPUTS_REJECTED': 1}[receipt['preflight_status']]
        _write_all(sys.stdout.fileno(), canonical(receipt))
        return code
    except Exception as error:
        code = error.code if isinstance(error, known_errors) else 'PREFLIGHT_WORKFLOW_FAILED_DIRECTORY_MAY_EXIST_NO_MODEL_EXECUTION'
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
