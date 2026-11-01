"""Compare complete saved R33 synthetic batches without rerunning the model."""

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--baseline', type=Path, required=True, help='Complete saved R33 baseline bundle')
    parser.add_argument('--candidate', type=Path, required=True, help='Complete saved R33 candidate bundle; not vehicle candidate evaluation')
    parser.add_argument('--output', type=Path, required=True, help='NEW directory outside component/inputs, with existing parent')
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix='cyberlateral-r34-cache-') as cache:
        previous = sys.pycache_prefix
        sys.pycache_prefix = cache
        sys.path.insert(0, str(ROOT))
        try:
            from integration_tools.scenario_compare_input import CompareError
            from integration_tools.scenario_compare_run import run_comparison

            try:
                record = run_comparison(args.baseline, args.candidate, args.output)
            except (CompareError, OSError) as error:
                print(f'REJECTED: {error}', file=sys.stderr)
                return 2
            print(f'{record["status"]}: {record["difference_count"]} differences;0 new model executions')
            return 0 if record['status'] == 'MATCH' else 1
        finally:
            sys.pycache_prefix = previous


if __name__ == '__main__':
    raise SystemExit(main())
