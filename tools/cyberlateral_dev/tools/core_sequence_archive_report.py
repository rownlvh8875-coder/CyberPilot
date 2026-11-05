"""Print a bounded Korean Markdown summary of two verified saved ZIP captures."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    try:
        directory = tempfile.TemporaryDirectory(prefix='cyberlateral-core15-cache-')
    except OSError:
        print('REJECTED: ARCHIVE_REPORT_CACHE_IO_NO_MODEL_EXECUTION', file=sys.stderr)
        return 2
    previous = sys.pycache_prefix
    known_errors = None
    try:
        with directory as cache:
            try:
                sys.pycache_prefix = cache
                sys.path.insert(0, str(ROOT))
                from integration_tools.core_sequence_archive_compare import ArchiveCompareError, exit_code
                from integration_tools.core_sequence_archive_report import ArchiveReportError, report_suite_archives

                known_errors = (ArchiveCompareError, ArchiveReportError)
                parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
                parser.add_argument('--left-archive', type=Path, required=True)
                parser.add_argument('--left-sha256', required=True)
                parser.add_argument('--right-archive', type=Path, required=True)
                parser.add_argument('--right-sha256', required=True)
                args = parser.parse_args(argv)
                comparison, raw = report_suite_archives(args.left_archive, args.left_sha256, args.right_archive, args.right_sha256)
                result_code = exit_code(comparison)
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
        code = error.code if known_errors is not None and isinstance(error, known_errors) else 'ARCHIVE_REPORT_FAILED_NO_MODEL_EXECUTION'
        print('REJECTED: ' + code, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
