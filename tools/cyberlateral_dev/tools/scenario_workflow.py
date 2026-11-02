"""Validate/run/report/reference declared synthetic JSON, with optional saved regression."""

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--input', type=Path, action='append', required=True, help='Explicit readable synthetic JSON; repeat1..32 in order')
    parser.add_argument('--output', type=Path, required=True, help='NEW folder outside component/inputs; existing parent required')
    parser.add_argument('--baseline', type=Path, help='Optional complete saved R33 batch; never a portable subset')
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix='cyberlateral-r40-cache-') as cache:
        previous = sys.pycache_prefix
        sys.pycache_prefix = cache
        sys.path.insert(0, str(ROOT))
        try:
            from integration_tools.scenario_batch_input import BatchError
            from integration_tools.scenario_batch_reference_run import BatchReferenceError
            from integration_tools.scenario_compare_input import CompareError
            from integration_tools.scenario_output import canonical
            from integration_tools.scenario_reference_run import ReferenceCheckError
            from integration_tools.scenario_report_data import ReportError
            from integration_tools.scenario_workflow_run import WorkflowError, exit_code, run_workflow

            try:
                record = run_workflow(args.input, args.output, args.baseline)
            except (WorkflowError, BatchError, BatchReferenceError, CompareError, ReferenceCheckError, ReportError, OSError) as error:
                code = 'WORKFLOW_IO' if isinstance(error, OSError) else error.code
                print('REJECTED: ' + code, file=sys.stderr)
                return 2
            print(canonical({key: record[key] for key in ['status', 'input_count', 'completed', 'rejected',
                'model_steps', 'reference_steps', 'reference_status', 'regression_status']}).decode(), end='')
            return exit_code(record)
        finally:
            sys.pycache_prefix = previous


if __name__ == '__main__':
    raise SystemExit(main())
