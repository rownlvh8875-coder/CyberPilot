"""Render complete saved R44 comparisons, without new model/reference work."""

import argparse
import sys
import tempfile
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--input', type=Path, required=True, help='Complete saved R44 V1 comparison directory')
    parser.add_argument('--output', type=Path, required=True, help='NEW external output directory')
    args = parser.parse_args(argv)
    result_code = None
    try:
        with tempfile.TemporaryDirectory(prefix='cyberlateral-r46-cache-') as cache:
            previous = sys.pycache_prefix
            sys.pycache_prefix = cache
            sys.path.insert(0, str(ROOT))
            try:
                from integration_tools.scenario_campaign_report_run import run_report
                from integration_tools.scenario_campaign_report_schema import CampaignReportError

                try:
                    result = run_report(args.input, args.output)
                except (CampaignReportError, OSError) as error:
                    code = error.code if isinstance(error, CampaignReportError) else 'CAMPAIGN_REPORT_IO'
                    print(f'REJECTED: {code}', file=sys.stderr)
                    result_code = 2
                else:
                    print(f'REPORT_COMPLETE: overall={result["recorded_status"]}; regression={result["recorded_regression_status"]}; '
                          '0 new model/reference executions')
                    result_code = 0
            finally:
                sys.pycache_prefix = previous
    except OSError:
        if result_code is None:
            print('REJECTED: CAMPAIGN_REPORT_IO', file=sys.stderr)
            return 2
        warnings.warn('CAMPAIGN_REPORT_CACHE_CLEANUP_FAILED_AFTER_RESULT', RuntimeWarning, stacklevel=2)
    return result_code


if __name__ == '__main__':
    raise SystemExit(main())
