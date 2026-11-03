"""Run explicitly named synthetic JSON files independently, then link reports."""

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--input', type=Path, action='append', required=True, help='R31 synthetic JSON; repeat1..32 times, in order')
    parser.add_argument('--output', type=Path, required=True, help='NEW directory outside the component, in an existing parent')
    args = parser.parse_args(argv)
    try:
        cache_directory = tempfile.TemporaryDirectory(prefix='cyberlateral-r33-cache-')
    except OSError:
        print('REJECTED: BATCH_IO', file=sys.stderr)
        return 2
    with cache_directory as cache:
        previous = sys.pycache_prefix
        sys.pycache_prefix = cache
        sys.path.insert(0, str(ROOT))
        try:
            from integration_tools.scenario_batch_input import BatchError
            from integration_tools.scenario_batch_run import run_batch

            try:
                record = run_batch(args.input, args.output)
            except (BatchError, OSError) as error:
                print(f'REJECTED: {error}', file=sys.stderr)
                return 2
            print(f'{record["status"]}: {record["completed"]} completed, {record["rejected"]} rejected; '
                  f'{record["total_model_steps"]} synthetic model steps')
            return 1 if record['rejected'] else 0
        finally:
            sys.pycache_prefix = previous


if __name__ == '__main__':
    raise SystemExit(main())
