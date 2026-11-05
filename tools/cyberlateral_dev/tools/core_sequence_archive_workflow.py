"""Save verified ZIP comparison JSON, Korean summary and checksum to a NEW folder."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    try:
        directory = tempfile.TemporaryDirectory(prefix='cyberlateral-core16-cache-')
    except OSError:
        print('REJECTED: ARCHIVE_WORKFLOW_CACHE_IO_NO_OUTPUT', file=sys.stderr)
        return 2
    previous = sys.pycache_prefix
    known_errors = None
    try:
        with directory as cache:
            try:
                sys.pycache_prefix = cache
                sys.path.insert(0, str(ROOT))
                from integration_tools.core_sequence_archive_compare import ArchiveCompareError
                from integration_tools.core_sequence_archive_report import ArchiveReportError
                from integration_tools.core_sequence_archive_workflow import ArchiveWorkflowError, publish_archive_report
                from integration_tools.scenario_output import canonical

                known_errors = (ArchiveCompareError, ArchiveReportError, ArchiveWorkflowError)
                parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
                parser.add_argument('--left-archive', type=Path, required=True)
                parser.add_argument('--left-sha256', required=True)
                parser.add_argument('--right-archive', type=Path, required=True)
                parser.add_argument('--right-sha256', required=True)
                parser.add_argument('--output-root', type=Path, required=True)
                args = parser.parse_args(argv)
                receipt = publish_archive_report(args.left_archive, args.left_sha256, args.right_archive, args.right_sha256, args.output_root)
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
        code = (error.code if known_errors is not None and isinstance(error, known_errors)
                else 'ARCHIVE_WORKFLOW_FAILED_DIRECTORY_MAY_EXIST_NO_MODEL_EXECUTION')
        print('REJECTED: ' + code, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
