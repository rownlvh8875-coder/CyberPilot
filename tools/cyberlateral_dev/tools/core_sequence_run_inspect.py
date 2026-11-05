"""Inspect the exact saved CORE17 run layout without executing a model."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_PARENT = Path('/tmp')


def main(argv=None) -> int:
    previous = sys.pycache_prefix
    previous_bytecode = sys.dont_write_bytecode
    known_error = None
    try:
        parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
        parser.add_argument('--input-root', type=Path, required=True)
        parser.add_argument('--baseline-sha256', required=True)
        parser.add_argument('--current-sha256', required=True)
        args = parser.parse_args(argv)

        # Bootstrap must not write a source cache before the private cache exists.
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(ROOT))
        from integration_tools.core_sequence_archive_compare import ArchiveCompareError, _preflight
        from integration_tools.core_sequence_run_inspect import RunInspectError, inspect_archived_run
        from integration_tools.core_sequence_suite import SuiteError, _path
        from integration_tools.scenario_output import canonical

        known_error = RunInspectError
        try:
            _preflight(args.baseline_sha256, args.current_sha256)
            input_root = _path(args.input_root, 'RUN_INSPECT_PATH')
        except (ArchiveCompareError, SuiteError) as error:
            raise RunInspectError('RUN_INSPECT:' + error.code) from error
        if not input_root.is_dir():
            raise RunInspectError('RUN_INSPECT_INPUT')
        try:
            parent = _path(CACHE_PARENT, 'RUN_INSPECT_CACHE_IO_NO_MODEL_EXECUTION').resolve()
            if not parent.is_dir():
                raise OSError('cache parent is not a directory')
        except (SuiteError, OSError, ValueError, RuntimeError) as error:
            raise RunInspectError('RUN_INSPECT_CACHE_IO_NO_MODEL_EXECUTION') from error
        if parent.is_relative_to(input_root.resolve()):
            raise RunInspectError('RUN_INSPECT_CACHE_INPUT_OVERLAP_NO_MODEL_EXECUTION')
        try:
            # Explicit dir bypasses gettempdir's potentially input-mutating probe.
            directory = tempfile.TemporaryDirectory(prefix='cyberlateral-core18-cache-', dir=parent)
        except OSError as error:
            raise RunInspectError('RUN_INSPECT_CACHE_IO_NO_MODEL_EXECUTION') from error
        with directory as cache:
            try:
                sys.pycache_prefix = cache
                sys.dont_write_bytecode = previous_bytecode
                raw = canonical(inspect_archived_run(args.input_root, args.baseline_sha256, args.current_sha256))
            finally:
                sys.dont_write_bytecode = True
                sys.pycache_prefix = previous
        sys.dont_write_bytecode = previous_bytecode
        pending = memoryview(raw)
        while pending:
            written = os.write(sys.stdout.fileno(), pending)
            if written <= 0:
                raise OSError('stdout made no progress')
            pending = pending[written:]
        return 0
    except Exception as error:
        code = error.code if known_error is not None and isinstance(error, known_error) else 'RUN_INSPECT_FAILED_NO_MODEL_EXECUTION'
        print('REJECTED: ' + code, file=sys.stderr)
        return 2
    finally:
        sys.pycache_prefix = previous
        sys.dont_write_bytecode = previous_bytecode


if __name__ == '__main__':
    raise SystemExit(main())
