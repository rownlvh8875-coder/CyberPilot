"""Literal state transitions catch wrong history, gates, counter order and purity."""
import math
import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path
from unittest.mock import patch

from domain import Limits
from test_oracle import feature


class StateModelTests(unittest.TestCase):
    def parts(self):
        return feature("flow_types"), feature("state_model")

    def sample(self, index, requested=20, active=True, angle=0.0, driver=0.0, limits=None):
        t, _ = self.parts()
        return t.Sample(index, requested, driver, angle, active,
                        limits if limits is not None else Limits(16, 2, 5, 7, 1, 3), "SYNTHETIC_ONLY")

    def test_ramp_and_explicit_history_fields(self):
        _, model = self.parts()
        state = model.initial_state()
        outputs = []
        for i in range(3):
            result = model.step(state, self.sample(i))
            outputs.append(result.final_command)
            self.assertEqual(result.limiter_previous, state.previous_applied)
            self.assertEqual(result.next_state.previous_requested, 20)
            self.assertEqual(result.next_state.previous_applied, result.final_command)
            state = result.next_state
        self.assertEqual(outputs, [2, 4, 6])

    def test_sign_reversal(self):
        _, model = self.parts()
        state = model.initial_state()
        outputs = []
        for i, requested in enumerate([-20, -20, 20, 20]):
            result = model.step(state, self.sample(i, requested=requested))
            outputs.append(result.final_command)
            state = result.next_state
        self.assertEqual(outputs, [-2, -4, 1, 3])

    def test_inactive_limiter_still_runs_but_next_history_is_zero(self):
        _, model = self.parts()
        state = model.initial_state()
        results = []
        for i, active in enumerate([True, False, False, True]):
            result = model.step(state, self.sample(i, active=active, angle=90.0))
            results.append(result)
            state = result.next_state
        self.assertEqual([r.final_command for r in results], [2, 0, 0, 2])
        self.assertEqual([r.limited_command for r in results], [2, 4, 2, 2])
        self.assertEqual([r.limiter_previous for r in results], [0, 2, 0, 0])
        self.assertEqual([r.next_state.angle_counter for r in results], [1, 0, 0, 1])
        self.assertEqual([r.steer_request for r in results], [True, False, False, True])

    def test_fault_request_false_does_not_zero_active_torque(self):
        _, model = self.parts()
        state, results = model.initial_state(), []
        for i in range(94):
            result = model.step(state, self.sample(i, angle=90.0))
            results.append(result)
            state = result.next_state
        self.assertEqual([(r.next_state.angle_counter, r.steer_request) for r in results[88:92]],
                         [(89, True), (90, False), (0, False), (1, True)])
        self.assertEqual([r.final_command for r in results[88:92]], [16, 16, 16, 16])

    def test_dropped_fault_condition_recovers_request_and_resets_counter(self):
        t, model = self.parts()
        state = t.State(90, 20, 16, 90)
        result = model.step(state, self.sample(90, angle=0.0))
        self.assertEqual((result.next_state.angle_counter, result.steer_request, result.final_command), (0, True, 16))

    def test_angle_threshold_both_signs_is_inclusive(self):
        _, model = self.parts()
        for angle, want in [(85.0, True), (-85.0, True), (84.99609375, False),
                            (-84.99609375, False), (0.0, False), (-0.0, False)]:
            with self.subTest(angle=angle):
                result = model.step(model.initial_state(), self.sample(0, angle=angle))
                self.assertEqual(result.fault_condition, want)
                self.assertEqual(result.next_state.angle_counter, int(want))

    def test_returned_stage_types_and_half_even_are_preserved(self):
        t, model = self.parts()
        state = t.State(1, 20, 12, 0)
        result = model.step(state, self.sample(1, driver=-8.5))
        self.assertEqual(result.driver_clip.result, t.Scalar("numpy.float64", "0x1.7000000000000p+3"))
        self.assertEqual(result.rate_clip.result, t.Scalar("numpy.float64", "0x1.7000000000000p+3"))
        self.assertEqual(result.limited_command, 12)

    def test_previous_request_is_not_used_by_limiter(self):
        t, model = self.parts()
        one = model.step(t.State(1, -20, 2, 0), self.sample(1))
        two = model.step(t.State(1, 20, 2, 0), self.sample(1))
        self.assertEqual(one, two)
        self.assertEqual(one.final_command, 4)

    def test_identical_calls_no_mutation_or_state_leakage(self):
        _, model = self.parts()
        state, sample = model.initial_state(), self.sample(0)
        before = (asdict(state), asdict(sample))
        first = model.step(state, sample)
        model.step(model.initial_state(), self.sample(0, requested=-20))
        self.assertEqual(first, model.step(state, sample))
        self.assertEqual(before, (asdict(state), asdict(sample)))
        with self.assertRaises(FrozenInstanceError):
            first.next_state.previous_applied = 999

    def test_sequence_order_invalid_state_and_exhausted_budget_rejected(self):
        t, model = self.parts()
        pairs = [(model.initial_state(), self.sample(1)),
                 (t.State(1, 20, 2, 0), self.sample(0)),
                 (t.State(0, 20, 0, 0), self.sample(0)),
                 (t.State(0, None, 1, 0), self.sample(0)),
                 (t.State(1, None, 2, 0), self.sample(1)),
                 (t.State(1, 20, True, 0), self.sample(1)),
                 (t.State(1, 20, 2, 91), self.sample(1)),
                 (t.State(4096, 20, 2, 0), self.sample(4096))]
        for state, sample in pairs:
            with self.subTest(state=state, sample=sample), self.assertRaises(model.FlowError):
                model.step(state, sample)

    def test_bad_types_scope_and_values_reject_before_math(self):
        t, model = self.parts()
        class SampleSubclass(t.Sample):
            pass
        class FloatSubclass(float):
            pass
        sample = self.sample(0)
        invalid = [replace(sample, index=True), replace(sample, requested=True),
                   replace(sample, lat_active=1), replace(sample, driver=math.nan),
                   replace(sample, driver=0.1), replace(sample, angle_deg=math.inf),
                   replace(sample, angle_deg=180.5), replace(sample, angle_deg=1),
                   replace(sample, angle_deg=FloatSubclass(85.0)),
                   replace(sample, provenance="PRODUCTION"), replace(sample, limits=object()),
                   SampleSubclass(0, 20, 0.0, 0.0, True, sample.limits, "SYNTHETIC_ONLY")]
        with patch("state_model.oracle_limiter", side_effect=AssertionError("MATH_MUST_NOT_RUN")):
            for item in invalid:
                with self.subTest(sample=item), self.assertRaises(model.FlowError):
                    model.step(model.initial_state(), item)

    def test_pure_model_fresh_import_has_no_numpy_kernel_or_controller(self):
        self.parts()
        code = """
import sys
from state_model import initial_state, step
from flow_types import Sample
from domain import Limits
assert step(initial_state(),Sample(0,20,0.0,0.0,True,Limits(16,2,5,7,1,3),'SYNTHETIC_ONLY')).final_command==2
assert not [n for n in sys.modules if n.split('.')[0] in {'numpy','kernel','source_reference','opendbc','selfdrive','openpilot','cereal'}]
"""
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=Path(__file__).resolve().parent,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
