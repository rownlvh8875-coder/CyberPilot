"""Export/verify saved-suite custody without extraction, replay or policy values."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    try:
        directory = tempfile.TemporaryDirectory(prefix='cyberlateral-core13-cache-')
    except OSError:
        print('REJECTED: PORTABLE_CACHE_IO_NO_MODEL_EXECUTION', file=sys.stderr)
        return 2
    previous = sys.pycache_prefix
    portable_error_type = None
    try:
        with directory as cache:
            try:
                sys.pycache_prefix = cache
                sys.path.insert(0, str(ROOT))
                from integration_tools.core_sequence_portable import PortableError, export_saved_suite, verify_suite_archive
                from integration_tools.scenario_output import canonical

                portable_error_type = PortableError
                parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
                commands = parser.add_subparsers(dest='command', required=True)
                export = commands.add_parser('export', help='Preserve existing saved-suite bytes in a NEW ZIP', allow_abbrev=False)
                export.add_argument('--input-root', type=Path, required=True)
                export.add_argument('--output', type=Path, required=True)
                verify = commands.add_parser('verify', help='Read a ZIP with explicit full external SHA256, never extract', allow_abbrev=False)
                verify.add_argument('--archive', type=Path, required=True)
                verify.add_argument('--sha256', required=True)
                args = parser.parse_args(argv)
                report = (export_saved_suite(args.input_root, args.output) if args.command == 'export'
                          else verify_suite_archive(args.archive, args.sha256))
                raw = canonical(report)
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
        code = (error.code if portable_error_type is not None and isinstance(error, portable_error_type)
                else 'PORTABLE_OPERATION_FAILED_NO_MODEL_EXECUTION')
        print('REJECTED: ' + code, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
