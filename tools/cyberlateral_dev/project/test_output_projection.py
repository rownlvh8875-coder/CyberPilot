"""Literal quotient, schema-simulation bits and no-clamp/source contracts."""
import math
import subprocess
import sys
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from test_oracle import feature
from test_source_contract import REFERENCE
from v1_helpers import package_feature


class OutputProjectionTests(unittest.TestCase):
    def parts(self):
        return package_feature("cyberlateral_dev.output_projection"), feature("output_oracle")

    def test_ratio_and_both_float32_fields_literal_bits(self):
        model, oracle = self.parts()
        result = model.project_output(1, 3)
        self.assertEqual(result.normalized_expression_hex, "0x1.5555555555555p-2")
        self.assertEqual((result.torque_float32.bits_hex, result.torque_float32.value_hex),
                         ("3eaaaaab", "0x1.5555560000000p-2"))
        self.assertEqual((result.torque_output_can_float32.bits_hex, result.torque_output_can_float32.value_hex),
                         ("3f800000", "0x1.0000000000000p+0"))
        self.assertEqual(result.status, "SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE")
        self.assertEqual(asdict(result), oracle.project_reference(1, 3))

    def test_no_clamp_negative_values_zero_and_endpoints(self):
        model, oracle = self.parts()
        for command, scale, normalized, f32 in [(95, 5, 19.0, "41980000"), (-95, 5, -19.0, "c1980000"),
                                                (0, 5, 0.0, "00000000"), (2048, 1, 2048.0, "45000000"),
                                                (-2048, 1, -2048.0, "c5000000")]:
            with self.subTest(command=command, scale=scale):
                result = model.project_output(command, scale)
                self.assertEqual((result.normalized_expression, result.torque_float32.bits_hex), (normalized, f32))
                self.assertEqual(asdict(result), oracle.project_reference(command, scale))

    def test_float32_halfway_neighbors_and_sign(self):
        model, oracle = self.parts()
        low_tie = float.fromhex("0x1.0000010000000p+0")
        high_tie = float.fromhex("0x1.0000030000000p+0")
        for value, want in [(low_tie, "3f800000"), (math.nextafter(low_tie, math.inf), "3f800001"),
                             (high_tie, "3f800002"), (-high_tie, "bf800002"), (-0.0, "80000000")]:
            with self.subTest(value=value):
                result = model.simulate_float32(value)
                self.assertEqual(result.bits_hex, want)
                self.assertEqual(asdict(result), oracle.float32_reference(value))

    def test_float32_underflow_and_subnormal_normal_crossover(self):
        model, oracle = self.parts()
        half = float.fromhex("0x1.0000000000000p-150")
        for value, bits in [(half, "00000000"), (-half, "80000000"),
                            (math.nextafter(half, math.inf), "00000001"),
                            (float.fromhex("0x1.0000000000000p-149"), "00000001"),
                            (float.fromhex("0x1.fffffc0000000p-127"), "007fffff"),
                            (float.fromhex("0x1.fffffe0000000p-127"), "00800000"),
                            (float.fromhex("0x1.0000000000000p-126"), "00800000")]:
            with self.subTest(value=value):
                actual = model.simulate_float32(value)
                self.assertEqual(actual.bits_hex, bits)
                self.assertEqual(asdict(actual), oracle.float32_reference(value))

    def test_strict_inputs_no_scale_or_range_fallback(self):
        model, _ = self.parts()
        for command, scale in [(True, 5), (1.0, 5), (2049, 5), (1, 0), (1, True), (1, 5.0), (1, 2049), (1, None)]:
            with self.subTest(command=command, scale=scale), self.assertRaises(model.OutputError):
                model.project_output(command, scale)
        for value in [math.nan, math.inf, True, 1, 2049.0]:
            with self.subTest(value=value), self.assertRaises(model.OutputError):
                model.simulate_float32(value)

    def test_output_reference_fresh_import_no_package_or_model(self):
        self.parts()
        code = """
import sys
from output_oracle import project_reference
assert project_reference(1,3)['torque_float32']['bits_hex']=='3eaaaaab'
assert not [n for n in sys.modules if n.split('.')[0] in {'cyberlateral_dev','numpy','state_model','oracle','normalized_pipeline'}]
"""
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=Path(__file__).resolve().parent,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_source_assignments_and_both_schema_fields(self):
        module = feature("output_contract")
        result = module.derive_output_contract((REFERENCE / "carcontroller.py").read_bytes(),
                                               (REFERENCE / "lateral.py").read_bytes(), (REFERENCE / "car.capnp").read_bytes())
        self.assertEqual([x["start_line"] for x in result["output_assignments"]], [121, 122])
        self.assertEqual(result["schema_fields"]["torque"]["type"], "Float32")
        self.assertEqual(result["schema_fields"]["torque"]["ordinal"], 2)
        self.assertEqual(result["schema_fields"]["torqueOutputCan"]["type"], "Float32")
        self.assertEqual(result["schema_fields"]["torqueOutputCan"]["ordinal"], 8)
        self.assertEqual(result["actual_capnp_wire"], "NOT_ESTABLISHED")

    def test_all_source_identities_before_any_ast_or_schema_execution(self):
        module = feature("output_contract")
        c, h, s = [(REFERENCE / name).read_bytes() for name in ["carcontroller.py", "lateral.py", "car.capnp"]]
        for inputs in [(b"bad", h, s), (c, b"bad", s), (c, h, s + b"\n")]:
            with (self.subTest(sizes=tuple(map(len, inputs))),
                  patch("output_contract.ast.parse", side_effect=AssertionError("AST_MUST_NOT_RUN")),
                  self.assertRaises(module.ContractIdentityError)):
                module.derive_output_contract(*inputs)


if __name__ == "__main__":
    unittest.main()
