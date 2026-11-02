"""Independent R38 reference checks over a complete saved declared-synthetic batch."""

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--input', type=Path, required=True, help='Complete saved R33 directory, not portable subset or raw JSON')
    parser.add_argument('--output', type=Path, required=True, help='NEW directory outside input/component; existing parent required')
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix='cyberlateral-r39-cache-') as cache:
        previous = sys.pycache_prefix
        sys.pycache_prefix = cache
        sys.path.insert(0, str(ROOT))
        try:
            from integration_tools.scenario_batch_reference_run import BatchReferenceError, check_batch, exit_code
            from integration_tools.scenario_compare_input import CompareError
            from integration_tools.scenario_output import canonical
            from integration_tools.scenario_reference_run import ReferenceCheckError
            from integration_tools.scenario_report_data import ReportError

            try:
                record = check_batch(args.input, args.output)
            except (BatchReferenceError, CompareError, ReferenceCheckError, ReportError, OSError) as error:
                code = 'BATCH_REFERENCE_IO' if isinstance(error, OSError) else error.code
                print('REJECTED: ' + code, file=sys.stderr)
                return 2
            print(canonical({key: record[key] for key in ['status', 'matched_cases', 'different_cases',
                'input_rejections_confirmed', 'input_rejections_unverified', 'rejection_mismatch_cases',
                'error_cases', 'reference_steps', 'numerical_difference_count', 'new_model_executions']}).decode(), end='')
            return exit_code(record)
        finally:
            sys.pycache_prefix = previous


if __name__ == '__main__':
    raise SystemExit(main())
