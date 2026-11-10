"""Canonical public chains with fixed literals and actual returned-state feed."""

import unittest

from v1_helpers import package_feature

# request,driver,active,up,down,previous request,previous applied,
# driver lower,upper,result,rate lower,upper,limited,final,steer request.
POSITIVE_ROWS = (
    (1.0, 0.0, True, 2, 5, None, 0, -16, 16, 16, -2, 2, 2, 2, True),
    (1.0, 0.0, True, 2, 5, 16, 2, -16, 16, 16, -2, 4, 4, 4, True),
    (1.0, 0.0, True, 2, 5, 16, 4, -16, 16, 16, -1, 6, 6, 6, True),
    (1.0, -12.5, True, 0, 0, 16, 6, -16, 0, 0, 6, 6, 6, 6, True),
    (1.0, -12.5, True, 2, 5, 16, 6, -16, 0, 0, 1, 8, 1, 1, True),
    (1.0, 0.0, False, 2, 5, 16, 1, -16, 16, 16, -2, 3, 3, 0, False),
    (1.0, 0.0, True, 0, 0, 16, 0, -16, 16, 16, 0, 0, 0, 0, True),
    (1.0, 0.0, True, 2, 5, 16, 0, -16, 16, 16, -2, 2, 2, 2, True),
    (-1.0, 0.0, True, 2, 5, 16, 2, -16, 16, -16, -2, 4, -2, -2, True),
)
NEGATIVE_ROWS = (
    (-1.0, 0.0, True, 2, 5, None, 0, -16, 16, -16, -2, 2, -2, -2, True),
    (-1.0, 0.0, True, 2, 5, -16, -2, -16, 16, -16, -4, 2, -4, -4, True),
    (-1.0, 0.0, True, 2, 5, -16, -4, -16, 16, -16, -6, 1, -6, -6, True),
    (-1.0, 12.5, True, 0, 0, -16, -6, 0, 16, 0, -6, -6, -6, -6, True),
    (-1.0, 12.5, True, 2, 5, -16, -6, 0, 16, 0, -8, -1, -1, -1, True),
    (-1.0, 0.0, False, 2, 5, -16, -1, -16, 16, -16, -3, 2, -3, 0, False),
    (-1.0, 0.0, True, 0, 0, -16, 0, -16, 16, -16, 0, 0, 0, 0, True),
    (-1.0, 0.0, True, 2, 5, -16, 0, -16, 16, -16, -2, 2, -2, -2, True),
    (1.0, 0.0, True, 2, 5, -16, -2, -16, 16, 16, -4, 2, 2, 2, True),
)


class DriverStateChainTests(unittest.TestCase):
    def integer(self, actual, expected):
        self.assertIs(type(actual), int)
        self.assertEqual(actual, expected)

    def scalar(self, actual, kind, value):
        self.assertIs(type(actual.kind), str)
        self.assertEqual(actual.kind, kind)
        self.integer(actual.value, value)

    def chain(self, rows):
        p = package_feature(); state = p.initial_state()
        for index, row in enumerate(rows):
            request, driver, active, up, down, previous_request, previous_applied, lower, upper, first, rate_lower, rate_upper, limited, final, steer = row
            sample = p.LateralInput(index, request, driver, 0.0, active, p.Limits(16, up, down, 7, 1, 3), 'SYNTHETIC_ONLY')
            result = p.step(sample, state)
            trace = result.trace.downstream
            with self.subTest(index=index):
                self.integer(state.index, index)
                if previous_request is None: self.assertIsNone(state.previous_requested)
                else: self.integer(state.previous_requested, previous_request)
                self.integer(state.previous_applied, previous_applied)
                self.integer(state.angle_counter, 0)
                requested = {1.0: 16, -1.0: -16}[request]  # Literal mapping,not model output.
                self.integer(result.trace.quantization.integer_command, requested)
                self.integer(trace.limiter_previous, previous_applied)
                self.scalar(trace.driver_clip.x, 'python.int', requested)
                self.scalar(trace.driver_clip.lower, 'python.int', lower)
                self.scalar(trace.driver_clip.upper, 'python.int', upper)
                self.scalar(trace.driver_clip.result, 'numpy.int64', first)
                self.scalar(trace.rate_clip.x, 'numpy.int64', first)
                self.scalar(trace.rate_clip.lower, 'python.int', rate_lower)
                self.scalar(trace.rate_clip.upper, 'python.int', rate_upper)
                self.scalar(trace.rate_clip.result, 'numpy.int64', limited)
                self.integer(trace.limited_command, limited)
                self.integer(trace.final_command, final)
                self.integer(result.projection.integer_command, final)
                self.integer(result.next_state.index, index + 1)
                self.integer(result.next_state.previous_requested, requested)
                self.integer(result.next_state.previous_applied, final)
                self.integer(result.next_state.angle_counter, 0)
                self.assertIs(trace.fault_condition, False)
                self.assertIs(trace.steer_request, steer)
                self.assertIs(result.steer_request, steer)
            state = result.next_state  # Never replace actual history with expected rows.

    def test_positive_chain_carries_hold_driver_release_and_inactive_reset(self):
        self.chain(POSITIVE_ROWS)

    def test_negative_chain_carries_hold_driver_release_and_inactive_reset(self):
        self.chain(NEGATIVE_ROWS)
