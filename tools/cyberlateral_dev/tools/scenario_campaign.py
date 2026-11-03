"""Run explicitly ordered synthetic R42 seeds, never vehicle data or rate policy."""

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--seed', type=int, action='append', required=True, help='Repeat for 1..4 unique uint32 seeds in explicit order')
    parser.add_argument('--cases', type=int, required=True, help='1..16 independent cases per seed')
    parser.add_argument('--steps', type=int, required=True, help='16..256 invocation-ordered samples per case')
    parser.add_argument('--output', type=Path, required=True, help='NEW external folder with an existing parent')
    args = parser.parse_args(argv)
    try:
        cache_directory = tempfile.TemporaryDirectory(prefix='cyberlateral-r43-cache-')
    except OSError:
        print('REJECTED: CAMPAIGN_IO', file=sys.stderr)
        return 2
    with cache_directory as cache:
        previous = sys.pycache_prefix
        sys.pycache_prefix = cache
        sys.path.insert(0, str(ROOT))
        try:
            from integration_tools.scenario_campaign_run import CampaignError, exit_code, run_campaign
            from integration_tools.scenario_output import canonical

            try:
                record = run_campaign(args.seed, args.cases, args.steps, args.output)
            except (CampaignError, OSError) as error:
                code = 'CAMPAIGN_IO' if isinstance(error, OSError) else error.code
                print('REJECTED: ' + code, file=sys.stderr)
                return 2
            print(canonical({key: record[key] for key in ['status', 'parameters', 'model_steps', 'reference_steps', 'difference_count']}).decode(), end='')
            return exit_code(record)
        finally:
            sys.pycache_prefix = previous


if __name__ == '__main__':
    raise SystemExit(main())
