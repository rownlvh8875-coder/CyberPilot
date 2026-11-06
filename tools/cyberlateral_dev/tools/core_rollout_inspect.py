"""Inspect one pinned CORE28 saved fixture; no model execution or output-folder writes."""

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
        self.exit(2, 'REJECTED: ROLLOUT_INSPECT_USAGE_NO_MODEL_EXECUTION\n')


def main(argv=None) -> int:
    previous_bytecode, previous_paths = sys.dont_write_bytecode, list(sys.path)
    known_errors = ()
    try:
        sys.dont_write_bytecode = True
        parser = _Parser(description=__doc__, allow_abbrev=False)
        parser.add_argument('--case', required=True, action='append', choices=('sign-cycle', 'declared-difference', 'late-invalid'))
        parser.add_argument('--input-root', required=True, action='append')
        args = parser.parse_args(argv)
        if any(len(values) != 1 or not values[0] for values in (args.case, args.input_root)):
            parser.error('exactly one nonempty case and input required')
        root = Path(args.input_root[0])
        sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
        from integration_tools.core_rollout_inspect import RolloutInspectError, inspect_rollout_case
        from integration_tools.scenario_output import canonical

        known_errors = (RolloutInspectError,)
        receipt = inspect_rollout_case(args.case[0], root)
        code = {'PINNED_CORE28_ARTIFACTS_MATCH': 0}[receipt['inspection_status']]
        _write_all(sys.stdout.fileno(), canonical(receipt))
        return code
    except Exception as error:
        code = error.code if isinstance(error, known_errors) else 'ROLLOUT_INSPECT_FAILED_NO_MODEL_EXECUTION'
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
