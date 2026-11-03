"""Compare complete saved R43 campaigns without new model/reference execution."""

import argparse
import sys
import tempfile
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--baseline', type=Path, required=True, help='Complete saved R43 V1 baseline')
    parser.add_argument('--candidate', type=Path, required=True, help='Complete saved R43 V1 comparison input, not vehicle candidate evaluation')
    parser.add_argument('--output', type=Path, required=True, help='NEW external directory, no overwrite')
    args = parser.parse_args(argv)
    result_code = None
    try:
        with tempfile.TemporaryDirectory(prefix='cyberlateral-r44-cache-') as cache:
            previous = sys.pycache_prefix
            sys.pycache_prefix = cache
            sys.path.insert(0, str(ROOT))
            try:
                from integration_tools.scenario_campaign_compare_input import CampaignCompareError
                from integration_tools.scenario_campaign_compare_run import exit_code, run_campaign_comparison

                try:
                    record = run_campaign_comparison(args.baseline, args.candidate, args.output)
                except (CampaignCompareError, OSError) as error:
                    code = error.code if isinstance(error, CampaignCompareError) else 'CAMPAIGN_COMPARE_IO'
                    print(f'REJECTED: {code}', file=sys.stderr)
                    result_code = 2
                else:
                    print(f'{record["status"]}: regression={record["regression_status"]}; {record["difference_count"]} differences;'
                          '0 new model/reference executions')
                    result_code = exit_code(record)
            finally:
                sys.pycache_prefix = previous
    except OSError:
        if result_code is None:
            print('REJECTED: CAMPAIGN_COMPARE_IO', file=sys.stderr)
            return 2
        warnings.warn('CAMPAIGN_COMPARE_CACHE_CLEANUP_FAILED_AFTER_RESULT', RuntimeWarning, stacklevel=2)
    return result_code


if __name__ == '__main__':
    raise SystemExit(main())
