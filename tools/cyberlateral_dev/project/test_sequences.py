"""Independent state chains compare rational model to original helper bodies."""
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from domain import Limits
from flow_types import Sample, State
from state_model import initial_state, step
from test_oracle import feature
from test_source_contract import REFERENCE


class SequenceTests(unittest.TestCase):
    def reference(self):
        return feature("source_reference").SourceReference((REFERENCE / "carcontroller.py").read_bytes(),
                                                            (REFERENCE / "lateral.py").read_bytes())

    def test_all_synthetic_scenarios_separate_state_chains_exact_parity(self):
        reference = self.reference()
        scenarios = feature("scenarios").catalog()
        self.assertEqual(len(scenarios), 227)
        self.assertEqual([len(s.samples) for s in scenarios[:11]], [3, 4, 4, 94, 93, 93, 6, 6, 6, 8, 4])
        self.assertEqual(sum(len(s.samples) for s in scenarios), 2913)
        self.assertEqual(len({s.id for s in scenarios}), 227)
        for scenario in scenarios:
            model_state, source_state = initial_state(), State(0, None, 0, 0)
            for sample in scenario.samples:
                with self.subTest(scenario=scenario.id, index=sample.index):
                    actual = step(model_state, sample)
                    expected = reference.step(source_state, sample)
                    self.assertEqual(actual, expected)
                    model_state, source_state = actual.next_state, expected.next_state
        self.assertEqual(reference.counts["limiter_traced"], 2913)
        self.assertEqual(reference.counts["fault_explicit"], 2913)
        self.assertEqual(reference.counts["traced_clip_calls"], 5826)

    def test_inactive_source_order_executes_both_helpers_then_resets(self):
        reference = self.reference()
        state, observed = State(0, None, 0, 0), []
        for i, active in enumerate([True, False, False, True]):
            result = reference.step(state, Sample(i, 20, 0.0, 90.0, active, Limits(16, 2, 5, 7, 1, 3), "SYNTHETIC_ONLY"))
            observed.append((result.limited_command, result.final_command, result.next_state.angle_counter))
            state = result.next_state
        self.assertEqual(observed, [(2, 2, 1), (4, 0, 0), (2, 0, 0), (2, 2, 1)])
        self.assertEqual((reference.counts["limiter_traced"], reference.counts["fault_explicit"]), (4, 4))

    def test_identity_failure_precedes_helper_compilation(self):
        module = feature("source_reference")
        contract = feature("source_contract")
        with (patch("source_reference.Kernel", side_effect=AssertionError("HELPER_MUST_NOT_COMPILE")),
              self.assertRaises(contract.ContractIdentityError)):
            module.SourceReference(b"bad controller", (REFERENCE / "lateral.py").read_bytes())

    def test_fresh_reference_import_and_step_no_model_or_oracle(self):
        feature("source_reference")
        code = """
from pathlib import Path
import sys
from source_reference import SourceReference
from flow_types import Sample, State
from domain import Limits
p=Path(sys.argv[1]);r=SourceReference((p/'carcontroller.py').read_bytes(),(p/'lateral.py').read_bytes())
assert r.step(State(0,None,0,0),Sample(0,20,0.0,0.0,True,Limits(16,2,5,7,1,3),'SYNTHETIC_ONLY')).final_command==2
assert 'state_model' not in sys.modules and 'oracle' not in sys.modules
assert not [n for n in sys.modules if n.split('.')[0] in {'opendbc','selfdrive','openpilot','cereal'} or n.startswith('synthetic_rate_constraint_feasibility')]
"""
        result = subprocess.run([sys.executable, "-B", "-c", code, str(REFERENCE)], cwd=Path(__file__).resolve().parent,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
