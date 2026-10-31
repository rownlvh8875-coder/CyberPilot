"""Verify saved R31 files and write an offline HTML view; never run the model."""

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--input', type=Path, required=True, help='Existing exact R31 six-file output directory')
    parser.add_argument('--output', type=Path, required=True, help='NEW directory outside input tree; existing parent, no overwrite')
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix='cyberlateral-r32-cache-') as cache:
        previous = sys.pycache_prefix
        sys.pycache_prefix = cache
        sys.path.insert(0, str(ROOT))
        try:
            from integration_tools.scenario_report_run import ReportError, run_report

            try:
                result = run_report(args.input, args.output)
            except (ReportError, OSError) as error:
                print(f'REJECTED: {error}', file=sys.stderr)
                return 2
            print(f'{result["status"]}: {result["recorded_steps"]} recorded steps, 0 new model calls')
            return 0
        finally:
            sys.pycache_prefix = previous


if __name__ == '__main__':
    raise SystemExit(main())
