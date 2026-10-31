"""Fixed R28 real-native tests; explicit opt-in parent launches isolated worker."""

import argparse
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--schema', type=Path, required=True)
    parser.add_argument('--package-wheel', type=Path, required=True)
    args = parser.parse_args()
    # Cold-import even the loader/verifiers. -B alone still reads old caches.
    with tempfile.TemporaryDirectory(prefix='r28-worker-cold-') as cold:
        sys.pycache_prefix = cold
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from native_qualification.adapter_runtime import qualified_adapter
        from native_qualification.worker import canonical
        with qualified_adapter(args.wheel, args.schema, args.package_wheel) as session:
            import cyberlateral_dev as p
            from native_qualification.adapter_checks import run_checks
            # Tripwires on already-verified public functions: these prohibit
            # accidental model calls, not replace any conversion dependency.
            with (patch.object(p, 'step', side_effect=AssertionError('R28_MODEL_EXECUTION_PROHIBITED')),
                  patch.object(p, 'simulate', side_effect=AssertionError('R28_MODEL_EXECUTION_PROHIBITED')),
                  patch.object(p, 'initial_state', side_effect=AssertionError('R28_MODEL_EXECUTION_PROHIBITED'))):
                checks = run_checks(session.adapter)
            from integration_tools.native_adapter import AdapterError, SyntheticSpec
            from integration_tools.owned_message_boundary import PreviousSnapshot, SettingsSnapshot, Stamp
            stamp = Stamp('CLOSED', 0, 'CLOSED')
            spec = SyntheticSpec(stamp, SettingsSnapshot(stamp, 16, 2, 5, 7, 1, 3),
                                 PreviousSnapshot(stamp, None, 0, 0, 0, 0, None, 'ENTRY_BEFORE_CURRENT_LIMITER'),
                                 0.25, 1.5, -7.25, True)
            handle = session.adapter.construct(spec)
        closed_checks = 0
        for method, value in [(session.adapter.prepare, handle), (session.adapter.inspect, handle), (session.adapter.construct, spec)]:
            try:
                method(value)
            except AdapterError as error:
                if error.code != 'ADAPTER_CONTEXT_CLOSED':
                    raise
                closed_checks += 1
            else:
                raise AssertionError('CLOSED_CONTEXT_ACCEPTED')
        observations = {'status': 'F70UGZ_R28_CONTROLLED_SYNTHETIC_NATIVE_ADAPTER_PASS', 'checks': checks,
                        'closed_context_checks': closed_checks, 'scope': 'INTERNAL_SYNTHETIC_MESSAGES_ONLY',
                        'actual_custody': 'NOT_QUALIFIED', 'generic_external_reader': 'NOT_IMPLEMENTED',
                        'actual_input': 'NOT_ALLOWED', 'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL',
                        'model_execution': 0, 'F61_execution': 0, 'r_calculation': 0, 'dt_calculation': 0}
        sys.stdout.buffer.write(canonical({'observations': observations, 'receipt': session.receipt}))


if __name__ == '__main__':
    main()
