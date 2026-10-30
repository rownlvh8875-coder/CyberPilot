"""Literal expectations catch wrong clips, ties, thresholds and harness acceptance."""
import importlib
import importlib.util
import math
import unittest


def feature(name):
    if importlib.util.find_spec(name) is None:
        raise AssertionError(f"Missing planned feature: {name}")
    return importlib.import_module(name)


class OracleTests(unittest.TestCase):
    def models(self):
        d = feature("domain")
        o = feature("oracle")
        return d, o, d.Limits(16, 2, 5, 7, 1, 3)

    def test_driver_then_rate_literals(self):
        d, o, limits = self.models()
        for requested, previous, driver, want in [
            (100, 0, 0.0, 2), (-100, 0, 0.0, -2),
            (100, 10, 0.0, 12), (-100, 10, 0.0, 5),
            (-100, -10, 0.0, -12), (100, -10, 0.0, -5),
            (16, 10, -64.0, 5), (-16, -10, 64.0, -5),
        ]:
            with self.subTest(requested=requested, previous=previous, driver=driver):
                self.assertEqual(o.oracle_limiter(d.LimiterCase(requested, previous, driver, limits))["result"], want)

    def test_round_halfway_even_both_signs(self):
        d, o, limits = self.models()
        for requested, previous, driver, selected, want in [
            (20, 12, -8.5, limits, 12), (-20, -12, 8.5, limits, -12),
            (20, 10, -12.5, d.Limits(16, 2, 5, 7, 1, 1), 10),
            (-20, -10, 12.5, d.Limits(16, 2, 5, 7, 1, 1), -10),
        ]:
            with self.subTest(want=want):
                self.assertEqual(o.oracle_limiter(d.LimiterCase(requested, previous, driver, selected))["result"], want)

    def test_explicit_override_is_not_default_cap(self):
        d, o, limits = self.models()
        self.assertEqual(o.oracle_limiter(d.LimiterCase(20, 12, 0.0, limits))["result"], 14)
        self.assertEqual(o.oracle_limiter(d.LimiterCase(20, 12, 0.0, limits, 9))["result"], 9)

    def test_intermediate_literal_float_bits_and_kind(self):
        d, o, limits = self.models()
        clips = o.oracle_limiter(d.LimiterCase(20, 12, -8.5, limits))["clips"]
        self.assertEqual(clips[0], {
            "x": {"kind": "python.int", "value": 20},
            "lower": {"kind": "python.int", "value": -16},
            "upper": {"kind": "python.float", "value": "0x1.7000000000000p+3"},
            "result": {"kind": "numpy.float64", "value": "0x1.7000000000000p+3"},
        })

    def test_reject_nonfinite_nondyadic_and_wrong_scalar_types(self):
        d, o, limits = self.models()
        for driver in [math.nan, math.inf, -math.inf, 0.1, 1, True, [0.0], 1024.5, 1 / 512]:
            with self.subTest(driver=driver), self.assertRaises(d.DomainError):
                o.oracle_limiter(d.LimiterCase(0, 0, driver, limits))
        for request in [True, 1.0, 2049, -2049]:
            with self.subTest(request=request), self.assertRaises(d.DomainError):
                o.oracle_limiter(d.LimiterCase(request, 0, 0.0, limits))

    def test_reject_invalid_limits_override_and_previous(self):
        d, o, limits = self.models()
        for case in [d.LimiterCase(0, True, 0.0, limits), d.LimiterCase(0, 0, 0.0, limits, 0),
                     d.LimiterCase(0, 0, 0.0, limits, True), d.LimiterCase(0, 0, 0.0, object()),
                     d.LimiterCase(0, 0, 0.0, d.Limits(0, 2, 5, 7, 1, 3)),
                     d.LimiterCase(0, 0, 0.0, d.Limits(16, -1, 5, 7, 1, 3)),
                     d.LimiterCase(0, 0, 0.0, d.Limits(16, 2, 5, 7, 9, 3))]:
            with self.subTest(case=case), self.assertRaises(d.DomainError):
                o.oracle_limiter(case)

    def test_zero_step_limits_hold_previous_not_first_clip(self):
        d, o, _ = self.models()
        limits = d.Limits(16, 0, 0, 0, 1, 1)
        self.assertEqual(o.oracle_limiter(d.LimiterCase(20, 10, -64.0, limits))["result"], 10)

    def test_fault_literals(self):
        d, o, _ = self.models()
        for args, want in [
            ((True, True, 2, 2, 1), (0, False)),
            ((True, True, 1, 2, 2), (2, True)),
            ((True, True, 2, 2, 2), (3, False)),
            ((True, True, 3, 2, 2), (0, False)),
            ((False, True, 5, 2, 2), (0, True)),
            ((True, False, 5, 2, 2), (0, False)),
            ((True, True, 0, 0, 1), (0, False)),
        ]:
            with self.subTest(args=args):
                self.assertEqual(o.oracle_fault(d.FaultCase(*args)), want)

    def test_fault_sequence_reset_does_not_restore_request(self):
        d, o, _ = self.models()
        counter = 0
        observed = []
        for _ in range(5):
            result = o.oracle_fault(d.FaultCase(True, True, counter, 2, 2))
            observed.append(result)
            counter = result[0]
        self.assertEqual(observed, [(1, True), (2, True), (3, False), (0, False), (1, True)])

    def test_fault_rejects_wrong_types_and_ranges(self):
        d, o, _ = self.models()
        for args in [(1, True, 0, 2, 1), (True, 1, 0, 2, 1), (True, True, -1, 2, 1),
                     (True, True, 0, 129, 1), (True, True, 0, 2, 0),
                     (True, True, 0, 2, 9), (True, True, True, 2, 1)]:
            with self.subTest(args=args), self.assertRaises(d.DomainError):
                o.oracle_fault(d.FaultCase(*args))

    def test_oracle_import_has_no_numeric_or_target_dependency(self):
        # Import dependency checks are behavioral in a fresh interpreter (Task3).
        _, o, _ = self.models()
        self.assertEqual(o.oracle_fault(feature("domain").FaultCase(False, True, 0, 2)), (0, True))


if __name__ == "__main__":
    unittest.main()
