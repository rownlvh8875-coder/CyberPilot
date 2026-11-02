"""Generate deterministic synthetic boundary inputs and run existing independent checks."""

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--seed', type=int, required=True, help='Explicit builtin uint32 seed, not a runtime policy')
    parser.add_argument('--cases', type=int, required=True, help='1..16 independent synthetic cases')
    parser.add_argument('--steps', type=int, required=True, help='16..256 samples per case; invocation order only')
    parser.add_argument('--output', type=Path, required=True, help='NEW folder outside component; parent must exist')
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix='cyberlateral-r42-cache-') as cache:
        previous = sys.pycache_prefix
        sys.pycache_prefix = cache
        sys.path.insert(0, str(ROOT))
        try:
            from integration_tools.scenario_explore_run import exit_code, run_exploration
            from integration_tools.scenario_output import canonical

            try:
                record = run_exploration(args.seed, args.cases, args.steps, args.output)
            except (ValueError, OSError) as error:
                code = 'EXPLORATION_IO' if isinstance(error, OSError) else getattr(error, 'code', 'EXPLORATION_STAGE_ERROR')
                print('REJECTED: ' + code, file=sys.stderr)
                return 2
            print(canonical({key: record[key] for key in ['status', 'parameters', 'model_steps', 'reference_steps', 'difference_count']}).decode(), end='')
            return exit_code(record)
        finally:
            sys.pycache_prefix = previous


if __name__ == '__main__':
    raise SystemExit(main())
