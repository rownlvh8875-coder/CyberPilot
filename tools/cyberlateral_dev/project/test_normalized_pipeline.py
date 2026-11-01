"""Input conversion joins old state model without conflating units or history."""
import subprocess
import sys
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

from domain import Limits
from flow_types import State
from state_model import initial_state
from test_oracle import feature
from test_source_contract import REFERENCE


class NormalizedPipelineTests(unittest.TestCase):
    def parts(self):
        return feature("quantization_types"), feature("normalized_pipeline")

    def sample(self, index, q=1.0, active=True, angle=0.0, limits=None):
        t, _ = self.parts()
        return t.NormalizedSample(index, q, 0.0, angle, active,
                                  limits if limits is not None else Limits(16, 2, 5, 7, 1, 3), "SYNTHETIC_ONLY")

    def test_same_scale_snapshot_controls_quantizer_and_limiter(self):
        _, model = self.parts()
        for cap, want in [(5, 2), (16, 5)]:
            result = model.step_normalized(initial_state(), self.sample(0, q=0.3, limits=Limits(cap, 5, 5, 0, 1, 1)))
            self.assertEqual(result.quantization.scale, cap)
            self.assertEqual(result.quantization.integer_command, want)
            self.assertEqual(result.downstream.driver_clip.upper.value, cap)
            self.assertEqual(result.downstream.final_command, want)

    def test_integer_history_not_normalized_request(self):
        _, model = self.parts()
        state, results = initial_state(), []
        for i, q in enumerate([0.3, 0.3, -0.3]):
            result = model.step_normalized(state, self.sample(i, q=q, limits=Limits(5, 1, 3, 7, 1, 3)))
            results.append(result)
            state = result.downstream.next_state
        self.assertEqual([r.quantization.integer_command for r in results], [2, 2, -2])
        self.assertEqual([r.downstream.final_command for r in results], [1, 2, -1])
        self.assertEqual([r.downstream.next_state.previous_requested for r in results], [2, 2, -2])

    def test_inactive_and_reactivation_preserve_post_gate_history(self):
        _, model = self.parts()
        state, results = initial_state(), []
        for i, active in enumerate([True, False, False, True]):
            result = model.step_normalized(state, self.sample(i, active=active, angle=90.0))
            results.append(result.downstream)
            state = result.downstream.next_state
        self.assertEqual([r.final_command for r in results], [2, 0, 0, 2])
        self.assertEqual([r.limited_command for r in results], [2, 4, 2, 2])
        self.assertEqual([r.limiter_previous for r in results], [0, 2, 0, 0])

    def test_fault_request_suppression_still_holds_active_torque(self):
        _, model = self.parts()
        state = State(90, 16, 16, 90)
        result = model.step_normalized(state, self.sample(90, angle=90.0))
        self.assertEqual((result.downstream.next_state.angle_counter, result.downstream.steer_request,
                          result.downstream.final_command), (0, False, 16))

    def test_purity_and_scope_limits_no_real_scale_fallback(self):
        _, model = self.parts()
        q = feature("request_quantizer")
        state, sample = initial_state(), self.sample(0, q=-0.0)
        before = (asdict(state), asdict(sample))
        self.assertEqual(model.step_normalized(state, sample), model.step_normalized(state, sample))
        self.assertEqual(before, (asdict(state), asdict(sample)))
        for invalid in [replace(sample, provenance="PRODUCTION"), replace(sample, limits=object()),
                        replace(sample, limits=Limits(4096, 2, 5, 7, 1, 3)), replace(sample, request=True)]:
            with self.subTest(sample=invalid), self.assertRaises(q.QuantizationError):
                model.step_normalized(state, invalid)

    def test_extended_contract_has_line70_without_original_execution(self):
        module = feature("quantization_contract")
        c, h = (REFERENCE / "carcontroller.py").read_bytes(), (REFERENCE / "lateral.py").read_bytes()
        contract = module.derive_quantization_contract(c, h)
        self.assertEqual(contract["quantization_record"]["start_line"], 70)
        self.assertEqual(contract["quantization_record"]["expression"], "int(round(actuators.torque * self.params.STEER_MAX))")
        self.assertEqual(contract["operation_order"], ["binary64_product", "round_to_integer_ties_even", "int"])
        self.assertEqual(contract["original_caller_execution"], 0)
        self.assertEqual(contract["actual_actuator_dtype"], "NOT_ESTABLISHED")

    def test_bad_source_before_reference_helper_construction(self):
        module = feature("normalized_reference")
        contract = feature("source_contract")
        with (patch("normalized_reference.SourceReference", side_effect=AssertionError("HELPER_MUST_NOT_COMPILE")),
              self.assertRaises(contract.ContractIdentityError)):
            module.NormalizedReference(b"bad", (REFERENCE / "lateral.py").read_bytes())

    def test_all_fixed_vectors_and_separate_state_chains(self):
        _, model = self.parts()
        q = feature("request_quantizer")
        oracle = feature("quantization_oracle")
        fixtures = feature("quantized_fixtures")
        vectors = fixtures.quantization_vectors()
        self.assertGreater(len(vectors), 300)
        self.assertTrue(any(value.hex() == (0.1).hex() and scale == 5 for _, value, scale in vectors))
        for case_id, value, scale in vectors:
            with self.subTest(vector=case_id):
                self.assertEqual(q.quantize(value, scale), oracle.quantize_reference(value, scale))
        ref = feature("normalized_reference").NormalizedReference((REFERENCE / "carcontroller.py").read_bytes(),
                                                                 (REFERENCE / "lateral.py").read_bytes())
        total = 0
        for scenario in fixtures.normalized_scenarios():
            model_state, source_state = initial_state(), State(0, None, 0, 0)
            for sample in scenario.samples:
                with self.subTest(scenario=scenario.id, index=sample.index):
                    actual = model.step_normalized(model_state, sample)
                    expected = ref.step(source_state, sample)
                    self.assertEqual(actual, expected)
                    model_state, source_state = actual.downstream.next_state, expected.downstream.next_state
                    total += 1
        self.assertGreater(total, 2500)
        self.assertEqual(ref.counts["limiter_traced"], total)
        self.assertEqual(ref.counts["fault_explicit"], total)

    def test_fresh_import_dependency_boundaries(self):
        self.parts()
        feature("normalized_reference")
        codes = ["""
import sys
from normalized_pipeline import step_normalized
from quantization_types import NormalizedSample
from state_model import initial_state
from domain import Limits
assert step_normalized(initial_state(),NormalizedSample(0,0.3,0.0,0.0,True,Limits(5,5,5,0,1,1),'SYNTHETIC_ONLY')).downstream.final_command==2
assert not {'numpy','kernel','normalized_reference'} & set(sys.modules)
""", """
import sys
from pathlib import Path
from normalized_reference import NormalizedReference
from quantization_types import NormalizedSample
from flow_types import State
from domain import Limits
p=Path(sys.argv[1]);r=NormalizedReference((p/'carcontroller.py').read_bytes(),(p/'lateral.py').read_bytes())
assert r.step(State(0,None,0,0),NormalizedSample(0,0.3,0.0,0.0,True,Limits(5,5,5,0,1,1),'SYNTHETIC_ONLY')).downstream.final_command==2
assert not {'request_quantizer','normalized_pipeline','state_model','oracle'} & set(sys.modules)
assert not [n for n in sys.modules if n.split('.')[0] in {'opendbc','selfdrive','openpilot','cereal'} or n.startswith('synthetic_rate_constraint_feasibility')]
"""]
        for code in codes:
            result = subprocess.run([sys.executable, "-B", "-c", code, str(REFERENCE)], cwd=Path(__file__).resolve().parent,
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
