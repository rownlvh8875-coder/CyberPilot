"""Explicitly recompute supplied synthetic input and audit SHA-pinned saved diagnostics."""

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
        self.exit(2, 'REJECTED: DIAGNOSTICS_AUDIT_USAGE_NO_MODEL_EXECUTION\n')


def main(argv=None) -> int:
    previous_bytecode, previous_paths = sys.dont_write_bytecode, list(sys.path)
    known_errors = ()
    try:
        sys.dont_write_bytecode = True
        parser = _Parser(description=__doc__, allow_abbrev=False)
        parser.add_argument('--run', action='append_const', const=True, required=True)
        for name in ('--input-file', '--expected-input-sha256', '--diagnostics-root', '--expected-diagnostics-sha256'):
            parser.add_argument(name, action='append', required=True)
        args = parser.parse_args(argv)
        if any(len(values) != 1 or not values[0] for values in vars(args).values()):
            parser.error('exactly one nonempty value required')
        input_sha, diagnostics_sha = args.expected_input_sha256[0], args.expected_diagnostics_sha256[0]
        if any(len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest) for digest in (input_sha, diagnostics_sha)):
            parser.error('exact lowercase SHA256 required')
        sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
        from integration_tools.offline_recording_input_codec import RecordingInputCodecError
        from integration_tools.offline_recording_preflight import RecordingPreflightError
        from integration_tools.recording_diagnostics_audit import DiagnosticsAuditError, audit_recording_diagnostics
        from integration_tools.recording_diagnostics_saved import SavedDiagnosticsError
        from integration_tools.recording_input_run import RecordingInputRunError
        from integration_tools.scenario_output import canonical

        known_errors = (DiagnosticsAuditError, SavedDiagnosticsError, RecordingInputRunError,
                        RecordingInputCodecError, RecordingPreflightError)
        result = audit_recording_diagnostics(Path(args.input_file[0]), input_sha, Path(args.diagnostics_root[0]), diagnostics_sha)
        raw = canonical(result)
        if not 0 < len(raw) <= 2097152:
            raise ValueError('output byte limit')
        _write_all(sys.stdout.fileno(), raw)
        return result['audit_exit_code']
    except Exception as error:
        code = error.code if isinstance(error, known_errors) else 'DIAGNOSTICS_AUDIT_FAILED_WORK_MAY_BE_NONZERO'
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
