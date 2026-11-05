"""Inspect saved CORE8 records without running a model or qualifying real inputs."""

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    try:
        directory = tempfile.TemporaryDirectory(prefix='cyberlateral-core9-cache-')
    except OSError:
        print('REJECTED: INSPECT_OPERATION_FAILED', file=sys.stderr)
        return 2
    with directory as cache:
        previous = sys.pycache_prefix
        sys.pycache_prefix = cache
        sys.path.insert(0, str(ROOT))
        try:
            from integration_tools.core_sequence_saved import InspectError, format_saved_sequence

            parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
            parser.add_argument('--input', type=Path, required=True, help='Existing saved three-file CORE8 folder')
            parser.add_argument('--format', choices=('json', 'markdown'), default='json')
            args = parser.parse_args(argv)
            try:
                raw = format_saved_sequence(args.input, args.format)
            except InspectError as error:
                print('REJECTED: ' + error.code, file=sys.stderr)
                return 2
            except Exception:
                print('REJECTED: INSPECT_OPERATION_FAILED', file=sys.stderr)
                return 2
            sys.stdout.buffer.write(raw)
            return 0
        finally:
            sys.pycache_prefix = previous


if __name__ == '__main__':
    raise SystemExit(main())
