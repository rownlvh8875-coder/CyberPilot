"""Public package API preserves state/math and deliberately distinguishes outputs."""
import ast
import json
import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError, asdict, astuple
from pathlib import Path

from normalized_reference import NormalizedReference
from output_oracle import project_reference
from quantized_fixtures import normalized_scenarios
from test_source_contract import REFERENCE
from v1_helpers import ROOT, package_feature


class LateralApiTests(unittest.TestCase):
    def package(self):
        p = package_feature()
        self.assertTrue(hasattr(p, "step"), "Missing planned public step API")
        return p

    def sample(self, p, index=0, q=0.3, active=True, angle=0.0, cap=5):
        return p.LateralInput(index, q, 0.0, angle, active, p.Limits(cap, 5, 5, 0, 1, 1), "SYNTHETIC_ONLY")

    def test_single_public_api_literal_outputs(self):
        p = self.package()
        output = p.step(self.sample(p), p.initial_state())
        self.assertEqual(output.projection.integer_command, 2)
        self.assertEqual(output.projection.normalized_expression_hex, "0x1.999999999999ap-2")
        self.assertEqual(output.projection.torque_float32.bits_hex, "3ecccccd")
        self.assertEqual(output.projection.torque_output_can_float32.bits_hex, "40000000")
        self.assertEqual(output.next_state.previous_applied, 2)
        self.assertTrue(output.steer_request)
        self.assertEqual(p.__version__, "0.3.0")

    def test_history_scale_mismatch_does_not_clamp_output(self):
        p = self.package()
        state = p.LateralState(1, 100, 100, 0)
        output = p.step(self.sample(p, index=1, q=0.0), state)
        self.assertEqual((output.projection.integer_command, output.projection.normalized_expression), (95, 19.0))
        self.assertEqual(output.next_state.previous_applied, 95)

    def test_normalization_is_not_inverse_quantization(self):
        p = self.package()
        output = p.step(self.sample(p, q=0.1), p.initial_state())
        self.assertEqual((output.trace.quantization.integer_command, output.projection.normalized_expression), (0, 0.0))
        self.assertNotEqual(output.projection.normalized_expression, 0.1)
        zero = p.step(self.sample(p, q=-0.0), p.initial_state())
        self.assertEqual(zero.trace.quantization.product_hex, "-0x0.0p+0")
        self.assertEqual(zero.projection.normalized_expression_hex, "0x0.0p+0")

    def test_purity_and_invalid_scope(self):
        p = self.package()
        sample, state = self.sample(p), p.initial_state()
        before = asdict(sample), asdict(state)
        result = p.step(sample, state)
        self.assertEqual(result, p.step(sample, state))
        self.assertEqual(before, (asdict(sample), asdict(state)))
        with self.assertRaises(FrozenInstanceError):
            result.projection.integer_command = 9
        wrong = p.LateralInput(0, 0.3, 0.0, 0.0, True, sample.limits, "PRODUCTION")
        with self.assertRaises(ValueError):
            p.step(wrong, state)

    def test_all_legacy_trajectories_against_independent_reference(self):
        p = self.package()
        reference = NormalizedReference((REFERENCE / "carcontroller.py").read_bytes(), (REFERENCE / "lateral.py").read_bytes())
        for scenario in normalized_scenarios():
            private_state = p.initial_state()
            from flow_types import State
            reference_state = State(0, None, 0, 0)
            for sample in scenario.samples:
                with self.subTest(scenario=scenario.id, index=sample.index):
                    public_sample = p.LateralInput(sample.index, sample.request, sample.driver, sample.angle_deg,
                                                   sample.lat_active, p.Limits(*astuple(sample.limits)), sample.provenance)
                    actual = p.step(public_sample, private_state)
                    expected = reference.step(reference_state, sample)
                    record = {"projection": project_reference(expected.downstream.final_command, sample.limits.STEER_MAX),
                              "steer_request": expected.downstream.steer_request,
                              "next_state": asdict(expected.downstream.next_state), "trace": asdict(expected)}
                    self.assertEqual(asdict(actual), record)
                    private_state, reference_state = actual.next_state, expected.downstream.next_state

    def test_import_relocation_only_and_provenance_hashes(self):
        self.package()
        proof = json.loads((ROOT / "src/cyberlateral_dev/provenance/derived_modules.json").read_bytes())
        self.assertEqual(len(proof["modules"]), 7)
        for record in proof["modules"]:
            original = ast.parse((ROOT / "project" / record["filename"]).read_bytes())
            copied = ast.parse((ROOT / "src/cyberlateral_dev/_r4" / record["filename"]).read_bytes())
            for node in ast.walk(copied):
                if isinstance(node, ast.ImportFrom) and node.level == 1:
                    node.level = 0
            self.assertEqual(ast.dump(original, include_attributes=False), ast.dump(copied, include_attributes=False))

    def test_fresh_package_no_generic_names_or_vehicle_dependencies(self):
        self.package()
        code = """
import sys,types
sys.path.insert(0,sys.argv[1])
sys.modules['domain']=types.ModuleType('domain')
sys.modules['oracle']=types.ModuleType('oracle')
import cyberlateral_dev as p
r=p.step(p.LateralInput(0,0.3,0.0,0.0,True,p.Limits(5,5,5,0,1,1),'SYNTHETIC_ONLY'),p.initial_state())
assert r.projection.integer_command==2
assert not [n for n in sys.modules if n.split('.')[0] in {'numpy','opendbc','selfdrive','openpilot','cereal','capnp','kernel','normalized_pipeline'}]
"""
        result = subprocess.run([sys.executable, "-B", "-c", code, str(ROOT / "src")], cwd=Path(__file__).resolve().parent,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
