"""Compare two saved CORE8 packages; never execute model, vehicle or F61 code."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    try:
        directory = tempfile.TemporaryDirectory(prefix='cyberlateral-core10-cache-')
    except OSError:
        print('REJECTED: COMPARE_OPERATION_FAILED', file=sys.stderr)
        return 2
    with directory as cache:
        previous = sys.pycache_prefix
        sys.pycache_prefix = cache
        sys.path.insert(0, str(ROOT))
        try:
            from integration_tools.core_sequence_compare import CompareError, compare_saved_sequences, render_comparison

            parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
            parser.add_argument('--left', type=Path, required=True, help='Left saved three-file CORE8 folder')
            parser.add_argument('--right', type=Path, required=True, help='Right saved three-file CORE8 folder')
            parser.add_argument('--format', choices=('json', 'markdown'), default='json')
            args = parser.parse_args(argv)
            try:
                result = compare_saved_sequences(args.left, args.right)
                raw = render_comparison(result, args.format)
                pending = memoryview(raw)
                while pending:
                    written = os.write(sys.stdout.fileno(), pending)
                    if written <= 0:
                        raise OSError('stdout made no progress')
                    pending = pending[written:]
            except CompareError as error:
                print('REJECTED: ' + error.code, file=sys.stderr)
                return 2
            except Exception:
                print('REJECTED: COMPARE_OPERATION_FAILED', file=sys.stderr)
                return 2
            return 0 if result['comparison_status'] == 'SAVED_PACKAGES_IDENTICAL' else 1
        finally:
            sys.pycache_prefix = previous


if __name__ == '__main__':
    raise SystemExit(main())
