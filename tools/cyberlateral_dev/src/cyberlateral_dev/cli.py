"""Closed synthetic catalog CLI; never accepts logs, source roots or live input."""
import argparse
import sys
from pathlib import Path

from .reporting import canonical_report, catalog_report
from .trace_report import build_report_bundle

STATUS = 'F70UGZ_R6_SYNTHETIC_OFFLINE_SIMULATION_PASS'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='NEW output directory; default canonical JSON to stdout')
    parser.add_argument('--report', action='store_true', help='Write self-contained HTML/CSV/JSON fixed-catalog report; requires --output')
    args = parser.parse_args(argv)
    if args.report and args.output is None:
        parser.error('--report requires --output NEW_DIR')
    try:
        if args.output is not None and (args.output.exists() or args.output.is_symlink()):
            raise FileExistsError('OUTPUT_EXISTS_NO_SIMULATION')
        files = build_report_bundle() if args.report else {'simulation.json': canonical_report(catalog_report())}
        if args.output is None:
            sys.stdout.write(files['simulation.json'].decode('utf-8'))
        else:
            args.output.mkdir(parents=True, exist_ok=False)
            for name, raw in sorted(files.items()):
                with (args.output / name).open('xb') as output:
                    output.write(raw)
            print('F70UGZ_R7_OFFLINE_TRACE_REPORT_WRITTEN' if args.report else STATUS)
    except (ValueError, RuntimeError, TypeError, OSError) as error:
        print(f'REJECTED: {error}', file=sys.stderr)
        return 2
    return 0
