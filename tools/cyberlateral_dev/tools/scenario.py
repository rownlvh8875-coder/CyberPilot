"""Run a user-declared SYNTHETIC_ONLY JSON file; never a vehicle/log reader."""

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--input', type=Path, required=True, help='V1 declared synthetic JSON regular file')
    parser.add_argument('--output', type=Path, required=True, help='NEW directory in an existing parent; no overwrite')
    args = parser.parse_args(argv)
    # -B prevents new caches, but not stale-cache reads. Use an empty private prefix too.
    with tempfile.TemporaryDirectory(prefix='cyberlateral-r31-cache-') as cache:
        previous = sys.pycache_prefix
        sys.pycache_prefix = cache
        sys.path.insert(0, str(ROOT))
        try:
            from integration_tools.scenario_input import ScenarioError
            from integration_tools.scenario_run import run_scenario

            try:
                result = run_scenario(args.input, args.output)
            except (ScenarioError, OSError) as error:
                print(f'REJECTED: {error}', file=sys.stderr)
                return 2
            print(f'{result["status"]}: {result["model_steps"]} model steps')
            return 0
        finally:
            sys.pycache_prefix = previous


if __name__ == '__main__':
    raise SystemExit(main())
