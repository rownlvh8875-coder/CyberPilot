"""Compare two explicit saved ZIPs and full digests without extraction or replay."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    try:
        directory = tempfile.TemporaryDirectory(prefix='cyberlateral-core14-cache-')
    except OSError:
        print('REJECTED: ARCHIVE_COMPARE_CACHE_IO_NO_MODEL_EXECUTION', file=sys.stderr)
        return 2
    previous = sys.pycache_prefix
    compare_error_type = None
    try:
        with directory as cache:
            try:
                sys.pycache_prefix = cache
                sys.path.insert(0, str(ROOT))
                from integration_tools.core_sequence_archive_compare import ArchiveCompareError, compare_suite_archives, exit_code
                from integration_tools.scenario_output import canonical

                compare_error_type = ArchiveCompareError
                parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
                parser.add_argument('--left-archive', type=Path, required=True)
                parser.add_argument('--left-sha256', required=True)
                parser.add_argument('--right-archive', type=Path, required=True)
                parser.add_argument('--right-sha256', required=True)
                args = parser.parse_args(argv)
                report = compare_suite_archives(args.left_archive, args.left_sha256, args.right_archive, args.right_sha256)
                result_code = exit_code(report)
                raw = canonical(report)
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
        code = (error.code if compare_error_type is not None and isinstance(error, compare_error_type)
                else 'ARCHIVE_COMPARE_FAILED_NO_MODEL_EXECUTION')
        print('REJECTED: ' + code, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
