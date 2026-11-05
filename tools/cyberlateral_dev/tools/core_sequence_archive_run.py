"""Explicitly run the fixed synthetic suite, export ZIP and save baseline comparison."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    try:
        directory = tempfile.TemporaryDirectory(prefix='cyberlateral-core17-cache-')
    except OSError:
        print('REJECTED: ARCHIVE_RUN_CACHE_IO_NO_MODEL_EXECUTION', file=sys.stderr)
        return 2
    previous = sys.pycache_prefix
    known_error = None
    try:
        with directory as cache:
            try:
                sys.pycache_prefix = cache
                sys.path.insert(0, str(ROOT))
                from integration_tools.core_sequence_archive_run import ArchiveRunError, run_archived_suite
                from integration_tools.scenario_output import canonical

                known_error = ArchiveRunError
                parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
                parser.add_argument('command', choices=['run'])
                parser.add_argument('--baseline-archive', type=Path, required=True)
                parser.add_argument('--baseline-sha256', required=True)
                parser.add_argument('--output-root', type=Path, required=True)
                args = parser.parse_args(argv)
                receipt = run_archived_suite(args.baseline_archive, args.baseline_sha256, args.output_root)
                raw = canonical(receipt)
                result_code = receipt['comparison_exit_code']
            finally:
                sys.pycache_prefix = previous
        pending = memoryview(raw)
        while pending:
            written = os.write(sys.stdout.fileno(), pending)
            if written <= 0:
                raise OSError('stdout made no progress')
            pending = pending[written:]
        return result_code
    except Exception as error:
        code = (error.code if known_error is not None and isinstance(error, known_error)
                else 'ARCHIVE_RUN_FAILED_WORK_MAY_BE_NONZERO_OUTPUT_MAY_EXIST')
        print('REJECTED: ' + code, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
