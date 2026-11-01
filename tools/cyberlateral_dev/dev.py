"""Single command for the standalone synthetic development gate, never vehicles."""

import argparse
import sys
from pathlib import Path

from integration_tools.verify import verify_new_output, verify_project

ROOT = Path(__file__).resolve().parent


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    verify = commands.add_parser('verify', help='Verify imported code/tests/wheel/report in isolation')
    verify.add_argument('--output', type=Path, required=True, help='NEW output directory, no overwrite')
    args = parser.parse_args(argv)
    try:
        verify_new_output(args.output)
        result = verify_project(ROOT, args.output.resolve())
    except (OSError, RuntimeError, ValueError) as error:
        print(f'REJECTED: {error}', file=sys.stderr)
        return 2
    print(result['status'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
