"""Read-only saved R31 trace stage observations; no model or rate calculation."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, 'REJECTED: TRACE_SUMMARY_USAGE\n')


def _write_stdout(payload: bytes) -> None:
    try:
        sys.stdout.buffer.write(payload)
        sys.stdout.buffer.flush()
    except OSError:
        # Failed buffered output must not be retried at CPython shutdown (exit120).
        try:
            with open(os.devnull, 'wb') as sink:
                os.dup2(sink.fileno(), sys.stdout.fileno())
        except (OSError, ValueError, AttributeError):
            # Custom/non-descriptor sinks may not support neutralizing; keep the IO result.
            pass
        raise


def main(argv=None):
    parser = _Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--input', type=Path, required=True, help='Complete saved R31 six-file directory')
    parser.add_argument('--format', choices=['json', 'markdown'], default='json', help='stdout format (default: json)')
    args = parser.parse_args(argv)
    result_code = None
    try:
        with tempfile.TemporaryDirectory(prefix='cyberlateral-r70-cache-') as cache:
            previous = sys.pycache_prefix
            sys.pycache_prefix = cache
            sys.path.insert(0, str(ROOT))
            try:
                from integration_tools.result_diagnostics import _warn_after_result
                from integration_tools.scenario_report_data import ReportError
                from integration_tools.scenario_trace_summary import format_saved_trace

                try:
                    payload = format_saved_trace(args.input, args.format)
                    _write_stdout(payload)
                except (ReportError, OSError) as error:
                    code = error.code if isinstance(error, ReportError) else 'TRACE_SUMMARY_IO'
                    print(f'REJECTED: {code}', file=sys.stderr)
                    result_code = 2
                else:
                    result_code = 0
            finally:
                sys.pycache_prefix = previous
    except OSError:
        if result_code is None:
            print('REJECTED: TRACE_SUMMARY_IO', file=sys.stderr)
            return 2
        _warn_after_result('TRACE_SUMMARY_CACHE_CLEANUP_FAILED_AFTER_RESULT')
    return result_code


if __name__ == '__main__':
    raise SystemExit(main())
