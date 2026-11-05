"""Inspect the exact saved CORE17 run layout without executing a model."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    try:
        directory = tempfile.TemporaryDirectory(prefix='cyberlateral-core18-cache-')
    except OSError:
        print('REJECTED: RUN_INSPECT_CACHE_IO_NO_MODEL_EXECUTION', file=sys.stderr)
        return 2
    previous = sys.pycache_prefix
    known_error = None
    try:
        with directory as cache:
            try:
                sys.pycache_prefix = cache
                sys.path.insert(0, str(ROOT))
                from integration_tools.core_sequence_run_inspect import RunInspectError, inspect_archived_run
                from integration_tools.scenario_output import canonical

                known_error = RunInspectError
                parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
                parser.add_argument('--input-root', type=Path, required=True)
                parser.add_argument('--baseline-sha256', required=True)
                parser.add_argument('--current-sha256', required=True)
                args = parser.parse_args(argv)
                raw = canonical(inspect_archived_run(args.input_root, args.baseline_sha256, args.current_sha256))
            finally:
                sys.pycache_prefix = previous
        pending = memoryview(raw)
        while pending:
            written = os.write(sys.stdout.fileno(), pending)
            if written <= 0:
                raise OSError('stdout made no progress')
            pending = pending[written:]
        return 0
    except Exception as error:
        code = error.code if known_error is not None and isinstance(error, known_error) else 'RUN_INSPECT_FAILED_NO_MODEL_EXECUTION'
        print('REJECTED: ' + code, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
