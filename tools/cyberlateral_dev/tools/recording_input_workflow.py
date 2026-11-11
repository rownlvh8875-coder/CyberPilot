"""Explicitly diagnose and save a SHA-pinned synthetic input to a NEW folder."""

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
        self.exit(2, 'REJECTED: RECORDING_WORKFLOW_USAGE_NO_MODEL_EXECUTION\n')


def main(argv=None) -> int:
    previous_bytecode, previous_paths = sys.dont_write_bytecode, list(sys.path)
    known_errors = ()
    try:
        sys.dont_write_bytecode = True
        parser = _Parser(description=__doc__, allow_abbrev=False)
        parser.add_argument('--run', action='append_const', const=True, required=True)
        for name in ('--input-file', '--expected-sha256', '--output-root'):
            parser.add_argument(name, action='append', required=True)
        args = parser.parse_args(argv)
        if len(args.run) != 1 or any(len(values) != 1 or not values[0] for values in (args.input_file, args.expected_sha256, args.output_root)):
            parser.error('exactly one nonempty value required')
        digest = args.expected_sha256[0]
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            parser.error('exact lowercase SHA256 required')
        sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
        from integration_tools.core_sequence_archive_workflow import ArchiveWorkflowError
        from integration_tools.offline_recording_input_codec import RecordingInputCodecError
        from integration_tools.offline_recording_preflight import RecordingPreflightError
        from integration_tools.recording_input_run import RecordingInputRunError
        from integration_tools.recording_input_workflow import RecordingInputWorkflowError, publish_recording_input
        from integration_tools.scenario_output import canonical

        known_errors = (ArchiveWorkflowError, RecordingInputRunError, RecordingInputWorkflowError, RecordingInputCodecError, RecordingPreflightError)
        receipt = publish_recording_input(Path(args.input_file[0]), digest, Path(args.output_root[0]))
        code = {'MATCH': 0, 'DIFFERENT': 1}[receipt['diagnostic_status']]
        raw = canonical(receipt)
        _write_all(sys.stdout.fileno(), raw)
        return code
    except Exception as error:
        code = error.code if isinstance(error, known_errors) else 'RECORDING_WORKFLOW_FAILED_DIRECTORY_MAY_EXIST_WORK_MAY_BE_NONZERO'
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
