"""Run a named closed synthetic sequence; never accept vehicle/log/rate input."""

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    try:
        directory = tempfile.TemporaryDirectory(prefix='cyberlateral-core8-cache-')
    except OSError:
        print('REJECTED: DEMO_CACHE_IO', file=sys.stderr)
        return 2
    with directory as cache:
        previous = sys.pycache_prefix
        sys.pycache_prefix = cache
        sys.path.insert(0, str(ROOT))
        try:
            from integration_tools.core_sequence_cases import CASE_IDS
            from integration_tools.core_sequence_run import DemoError, exit_code, run_sequence_case
            from integration_tools.scenario_output import canonical

            parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
            parser.add_argument('--case', choices=CASE_IDS, required=True, help='Named closed synthetic fixture, no external input')
            parser.add_argument('--output', type=Path, required=True, help='NEW folder outside checkout, existing nonsymlink parent')
            args = parser.parse_args(argv)
            try:
                record = run_sequence_case(args.case, args.output)
            except DemoError as error:
                print('REJECTED: ' + error.code, file=sys.stderr)
                return 2
            except Exception:
                print('REJECTED: DEMO_ERROR_WORK_MAY_BE_NONZERO', file=sys.stderr)
                return 2
            print(canonical({key: record[key] for key in ('case_id', 'status', 'model_steps', 'completed_transition_count')}).decode(), end='')
            return exit_code(record)
        finally:
            sys.pycache_prefix = previous


if __name__ == '__main__':
    raise SystemExit(main())
