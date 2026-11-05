"""Preflight a saved synthetic CORE8 input without executing a model."""

import argparse
import os
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[1]


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.exit(2, 'REJECTED: INPUT_PREFLIGHT_USAGE_NO_MODEL_EXECUTION\n')


def main(argv=None) -> int:
    previous_bytecode = sys.dont_write_bytecode
    previous_paths = list(sys.path)
    known_error = None
    try:
        # Suppress cold argparse/gettext imports as well as project imports.
        sys.dont_write_bytecode = True
        parser = _Parser(description=__doc__, allow_abbrev=False)
        parser.add_argument('--input-root', required=True, action='append')
        args = parser.parse_args(argv)
        if len(args.input_root) != 1 or not args.input_root[0]:
            parser.error('exactly one nonempty input root required')
        input_root = Path(args.input_root[0])
        sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
        from integration_tools.core_sequence_input_preflight import InputPreflightError, preflight_saved_sequence
        from integration_tools.scenario_output import canonical

        known_error = InputPreflightError
        result = preflight_saved_sequence(input_root)
        code = {'INPUTS_COMPATIBLE': 0, 'INPUTS_REJECTED': 1}[result['preflight_status']]
        pending = memoryview(canonical(result))
        while pending:
            written = os.write(sys.stdout.fileno(), pending)
            if written <= 0:
                raise OSError('stdout made no progress')
            pending = pending[written:]
        return code
    except Exception as error:
        code = error.code if known_error is not None and isinstance(error, known_error) else 'INPUT_PREFLIGHT_FAILED_NO_MODEL_EXECUTION'
        print('REJECTED: ' + code, file=sys.stderr)
        return 2
    finally:
        sys.path[:] = previous_paths
        sys.dont_write_bytecode = previous_bytecode


if __name__ == '__main__':
    raise SystemExit(main())
