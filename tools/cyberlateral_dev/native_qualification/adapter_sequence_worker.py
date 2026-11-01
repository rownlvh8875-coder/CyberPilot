"""Fixed R29 synthetic native→model chains in an isolated qualified worker."""

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
    with tempfile.TemporaryDirectory(prefix='r29-worker-cold-') as cold:
        sys.pycache_prefix = cold
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from native_qualification.adapter_runtime import qualified_adapter
        from native_qualification.adapter_sequence_validation import validate_observations
        from native_qualification.worker import canonical
        with qualified_adapter(args.wheel, args.schema, args.package_wheel) as session:
            import cyberlateral_dev as p
            from integration_tools.adapter_sequence import run_registered_sequence
            original = p.step
            calls = 0
            def counted(*args, **kwargs):
                nonlocal calls
                calls += 1
                return original(*args, **kwargs)
            with patch.object(p, 'step', side_effect=counted):
                profiles = [run_registered_sequence(session.adapter, name) for name in ['SIGN_CHANGE_4', 'NEGATIVE_CYCLE_99']]
            observations = {
                'schema_version': 1, 'status': 'F70UGZ_R29_FIXED_SYNTHETIC_ADAPTER_MODEL_SEQUENCE_PASS',
                'scope': 'TWO_REGISTERED_SYNTHETIC_NATIVE_ADAPTER_MODEL_SEQUENCES_ONLY', 'profiles': profiles,
                'package_version': p.__version__, 'model_execution': sum(row['model_execution'] for row in profiles),
                'observed_model_calls': calls, 'F61_execution': 0, 'Controller_execution': 0, 'Runtime_execution': 0, 'CAN': 0,
                'calculator_input_execution': 0, 'actual_inputs': 0, 'r_calculation': 0, 'dt_calculation': 0,
                'actual_call_custody': 'NOT_QUALIFIED', 'actual_activation': 'NOT_ALLOWED', 'generic_external_reader': 'NOT_IMPLEMENTED',
                'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL', 'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME'}
            validate_observations(observations)
        sys.stdout.buffer.write(canonical({'observations': observations, 'receipt': session.receipt}))


if __name__ == '__main__':
    main()
