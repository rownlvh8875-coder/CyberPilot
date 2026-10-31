"""Hand-derived bit/product/rounding expectations, not target-generated answers."""
import math
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from test_oracle import feature


class QuantizationTests(unittest.TestCase):
    def parts(self):
        return feature("quantization_types"), feature("request_quantizer"), feature("quantization_oracle")

    def test_signed_halfway_nearest_even_literals(self):
        _, model, reference = self.parts()
        for q, scale, want in [(0.5, 1, 0), (0.5, 3, 2), (0.5, 5, 2),
                               (-0.5, 1, 0), (-0.5, 3, -2), (-0.5, 5, -2),
                               (1.0, 2048, 2048), (-1.0, 2048, -2048)]:
            with self.subTest(q=q, scale=scale):
                actual = model.quantize(q, scale)
                self.assertEqual(actual.integer_command, want)
                self.assertEqual(actual.rounded_integer, want)
                self.assertIs(type(actual.integer_command), int)
                self.assertEqual(actual, reference.quantize_reference(q, scale))

    def test_decimal_product_rounding_precedes_integer_rounding(self):
        _, model, reference = self.parts()
        for q, product, want in [(0.1, "0x1.0000000000000p-1", 0),
                                  (0.3, "0x1.8000000000000p+0", 2),
                                  (-0.1, "-0x1.0000000000000p-1", 0),
                                  (-0.3, "-0x1.8000000000000p+0", -2)]:
            with self.subTest(q=q):
                actual = model.quantize(q, 5)
                self.assertEqual((actual.product_hex, actual.integer_command), (product, want))
                self.assertEqual(actual, reference.quantize_reference(q, 5))

    def test_product_significand_carry_into_next_exponent(self):
        _, model, reference = self.parts()
        for sign in [1, -1]:
            q = sign * float.fromhex("0x1.5555555555555p-1")
            want = ("-" if sign < 0 else "") + "0x1.0000000000000p+1"
            actual = model.quantize(q, 3)
            self.assertEqual((actual.product_hex, actual.integer_command), (want, sign * 2))
            self.assertEqual(actual, reference.quantize_reference(q, 3))

    def test_zero_sign_kept_in_product_not_integer(self):
        _, model, reference = self.parts()
        for q, want in [(0.0, "0x0.0p+0"), (-0.0, "-0x0.0p+0")]:
            actual = model.quantize(q, 2048)
            self.assertEqual((actual.request_hex, actual.product_hex, actual.integer_command), (want, want, 0))
            self.assertEqual(actual, reference.quantize_reference(q, 2048))

    def test_subnormal_and_normal_boundary_literals(self):
        _, model, reference = self.parts()
        for q_hex, scale, product in [
            ("0x0.0000000000001p-1022", 2, "0x0.0000000000002p-1022"),
            ("-0x0.0000000000001p-1022", 2048, "-0x0.0000000000800p-1022"),
            ("0x0.fffffffffffffp-1022", 2, "0x1.ffffffffffffep-1022"),
            ("0x1.0000000000000p-1022", 2048, "0x1.0000000000000p-1011"),
        ]:
            with self.subTest(q=q_hex, scale=scale):
                q = float.fromhex(q_hex)
                actual = model.quantize(q, scale)
                self.assertEqual((actual.product_hex, actual.integer_command), (product, 0))
                self.assertEqual(actual, reference.quantize_reference(q, scale))

    def test_halfway_neighbors_both_signs(self):
        _, model, reference = self.parts()
        for q, want in [(math.nextafter(0.5, 0.0), 0), (0.5, 0), (math.nextafter(0.5, 1.0), 1),
                         (math.nextafter(-0.5, -1.0), -1), (-0.5, 0), (math.nextafter(-0.5, 0.0), 0)]:
            with self.subTest(q=q):
                self.assertEqual(model.quantize(q, 1).integer_command, want)
                self.assertEqual(model.quantize(q, 1), reference.quantize_reference(q, 1))

    def test_invalid_q_rejected_without_coercion_or_clamp(self):
        _, model, _ = self.parts()
        class FloatSubclass(float):
            pass
        for q in [math.nan, math.inf, -math.inf, math.nextafter(1.0, math.inf), -1.0000000000000002,
                  1, True, "0.1", None, FloatSubclass(0.1)]:
            with self.subTest(q=q), self.assertRaises(model.QuantizationError):
                model.quantize(q, 5)

    def test_scale_required_strict_integer_without_fallback(self):
        _, model, _ = self.parts()
        class IntSubclass(int):
            pass
        for scale in [None, 0, -1, True, 5.0, 2049, "5", IntSubclass(5)]:
            with self.subTest(scale=scale), self.assertRaises(model.QuantizationError):
                model.quantize(0.1, scale)

    def test_bit_oracle_does_not_call_builtin_round(self):
        _, _, reference = self.parts()
        with patch("builtins.round", side_effect=AssertionError("BUILTIN_ROUND_FORBIDDEN")):
            result = reference.quantize_reference(0.3, 5)
        self.assertEqual((result.product_hex, result.integer_command), ("0x1.8000000000000p+0", 2))

    def test_oracle_fresh_import_independent_of_quantizer_and_models(self):
        self.parts()
        code = """
import sys
from quantization_oracle import quantize_reference
assert quantize_reference(0.1,5).integer_command==0
assert not {'request_quantizer','normalized_pipeline','state_model','oracle','kernel','numpy'} & set(sys.modules)
"""
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=Path(__file__).resolve().parent,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
