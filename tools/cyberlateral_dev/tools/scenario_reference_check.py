"""Independent selected-source check of complete saved declared-synthetic R31 data."""

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--input', type=Path, required=True, help='Complete checksummed saved R31 directory, not portable subset')
    parser.add_argument('--output', type=Path, required=True, help='NEW directory outside input/component; existing parent required')
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix='cyberlateral-r38-cache-') as cache:
        previous = sys.pycache_prefix
        sys.pycache_prefix = cache
        sys.path.insert(0, str(ROOT))
        try:
            from integration_tools.scenario_output import canonical
            from integration_tools.scenario_reference_run import ReferenceCheckError, check_saved
            from integration_tools.scenario_report_data import ReportError

            try:
                result = check_saved(args.input, args.output)
            except (ReferenceCheckError, ReportError, OSError) as error:
                code = error.code if isinstance(error, (ReferenceCheckError, ReportError)) else 'REFERENCE_IO'
                print('REJECTED: ' + code, file=sys.stderr)
                return 2
            print(canonical({key: result[key] for key in ['status', 'difference_count', 'reference_steps', 'new_model_executions']}).decode(), end='')
            return 0 if result['status'] == 'MATCH' else 1
        finally:
            sys.pycache_prefix = previous


if __name__ == '__main__':
    raise SystemExit(main())
