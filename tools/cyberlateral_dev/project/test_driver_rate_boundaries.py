"""Hand-derived public API stages; no target output used to build expectations."""

import unittest

from v1_helpers import package_feature

# name,request,previous,driver,(driver lower,upper,result),(rate lower,upper,result),final.
# Every stage expectation below is a literal;1.ffap+3 is4093/256,not a model output.
DRIVER_ROWS = (
    ('positive-cap-before', 1.0, 15, -6.99609375, (('python.int', -16), ('python.int', 16), ('numpy.int64', 16)), (10, 17, ('numpy.int64', 16)), 16),
    ('positive-cap-at', 1.0, 15, -7.0, (('python.int', -16), ('python.int', 16), ('numpy.int64', 16)), (10, 17, ('numpy.int64', 16)), 16),
    ('positive-cap-after', 1.0, 15, -7.00390625, (('python.int', -16), ('python.float', '0x1.ffa0000000000p+3'), ('numpy.float64', '0x1.ffa0000000000p+3')), (10, 17, ('numpy.float64', '0x1.ffa0000000000p+3')), 16),
    ('negative-cap-before', -1.0, -15, 6.99609375, (('python.int', -16), ('python.int', 16), ('numpy.int64', -16)), (-17, -10, ('numpy.int64', -16)), -16),
    ('negative-cap-at', -1.0, -15, 7.0, (('python.int', -16), ('python.int', 16), ('numpy.int64', -16)), (-17, -10, ('numpy.int64', -16)), -16),
    ('negative-cap-after', -1.0, -15, 7.00390625, (('python.float', '-0x1.ffa0000000000p+3'), ('python.int', 16), ('numpy.float64', '-0x1.ffa0000000000p+3')), (-17, -10, ('numpy.float64', '-0x1.ffa0000000000p+3')), -16),
    ('positive-near-zero', 1.0, 0, -12.25, (('python.int', -16), ('python.float', '0x1.0000000000000p-2'), ('numpy.float64', '0x1.0000000000000p-2')), (-2, 2, ('numpy.float64', '0x1.0000000000000p-2')), 0),
    ('positive-clamped-zero', 1.0, 0, -12.5, (('python.int', -16), ('python.int', 0), ('numpy.int64', 0)), (-2, 2, ('numpy.int64', 0)), 0),
    ('negative-near-zero', -1.0, 0, 12.25, (('python.float', '-0x1.0000000000000p-2'), ('python.int', 16), ('numpy.float64', '-0x1.0000000000000p-2')), (-2, 2, ('numpy.float64', '-0x1.0000000000000p-2')), 0),
    ('negative-clamped-zero', -1.0, 0, 12.5, (('python.int', 0), ('python.int', 16), ('numpy.int64', 0)), (-2, 2, ('numpy.int64', 0)), 0),
)
# name,request,previous,rate lower,rate upper,selected final.
RATE_ROWS = (
    ('negative6-down', -1.0, -6, -8, -1, -8), ('negative6-up', 1.0, -6, -8, -1, -1),
    ('negative4-down', -1.0, -4, -6, 1, -6), ('negative4-up', 1.0, -4, -6, 1, 1),
    ('negative1-down', -1.0, -1, -3, 2, -3), ('negative1-up', 1.0, -1, -3, 2, 2),
    ('zero-down', -1.0, 0, -2, 2, -2), ('zero-up', 1.0, 0, -2, 2, 2),
    ('positive1-down', -1.0, 1, -2, 3, -2), ('positive1-up', 1.0, 1, -2, 3, 3),
    ('positive4-down', -1.0, 4, -1, 6, -1), ('positive4-up', 1.0, 4, -1, 6, 6),
    ('positive6-down', -1.0, 6, 1, 8, 1), ('positive6-up', 1.0, 6, 1, 8, 8),
)
ORDER_ROWS = (
    ('positive-history-rate-lifts-zero', 1.0, 6, -12.5, (('python.int', -16), ('python.int', 0), ('numpy.int64', 0)), (1, 8, ('numpy.int64', 1)), 1),
    ('negative-history-rate-lifts-zero', -1.0, -6, 12.5, (('python.int', 0), ('python.int', 16), ('numpy.int64', 0)), (-8, -1, ('numpy.int64', -1)), -1),
)
HOLD_ROWS = (
    ('positive-zero-steps-hold-history', 1.0, 6, -12.5, (('python.int', -16), ('python.int', 0), ('numpy.int64', 0)), (6, 6, ('numpy.int64', 6)), 6),
    ('negative-zero-steps-hold-history', -1.0, -6, 12.5, (('python.int', 0), ('python.int', 16), ('numpy.int64', 0)), (-6, -6, ('numpy.int64', -6)), -6),
)


class DriverRateBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.p = package_feature()

    def scalar(self, actual, expected):
        self.assertEqual(actual.kind, expected[0])
        self.assertIs(type(actual.value), type(expected[1]))
        self.assertEqual(actual.value, expected[1])

    def check_case(self, request, previous, driver, driver_stage, rate_stage, final, *, up=2, down=5):
        sample = self.p.LateralInput(1, request, driver, 0.0, True, self.p.Limits(16, up, down, 7, 1, 3), 'SYNTHETIC_ONLY')
        result = self.p.step(sample, self.p.LateralState(1, 0, previous, 0))
        output = result.trace.downstream
        requested = {1.0: 16, -1.0: -16}[request]  # Literal mapping,not quantizer/oracle reuse.
        for field, want in zip(('lower', 'upper', 'result'), driver_stage, strict=True):
            self.scalar(getattr(output.driver_clip, field), want)
        self.scalar(output.driver_clip.x, ('python.int', requested))
        self.scalar(output.rate_clip.x, driver_stage[2])
        self.scalar(output.rate_clip.lower, ('python.int', rate_stage[0]))
        self.scalar(output.rate_clip.upper, ('python.int', rate_stage[1]))
        self.scalar(output.rate_clip.result, rate_stage[2])
        for actual, want in ((result.trace.quantization.integer_command, requested), (output.limiter_previous, previous),
            (output.limited_command, final), (output.final_command, final), (result.projection.integer_command, final),
            (result.next_state.index, 2), (result.next_state.previous_requested, requested),
            (result.next_state.previous_applied, final), (result.next_state.angle_counter, 0)):
            self.assertIs(type(actual), int); self.assertEqual(actual, want)
        self.assertIs(output.fault_condition, False)
        self.assertIs(result.steer_request, True)

    def test_driver_endpoint_and_adjacent_fractional_tags_both_signs(self):
        for name, *row in DRIVER_ROWS:
            with self.subTest(case=name): self.check_case(*row)

    def test_asymmetric_rate_endpoints_across_negative_zero_positive_history(self):
        for name, request, previous, lower, upper, final in RATE_ROWS:
            requested = {1.0: 16, -1.0: -16}[request]
            with self.subTest(case=name):
                self.check_case(request, previous, 0.0,
                    (('python.int', -16), ('python.int', 16), ('numpy.int64', requested)),
                    (lower, upper, ('numpy.int64', final)), final)

    def test_rate_after_driver_clip_can_leave_new_driver_interval(self):
        for name, *row in ORDER_ROWS:
            with self.subTest(case=name): self.check_case(*row)

    def test_zero_invocation_steps_hold_nonzero_history_not_driver_zero(self):
        for name, *row in HOLD_ROWS:
            with self.subTest(case=name): self.check_case(*row, up=0, down=0)
