"""Whole fixed pipeline CLI, exact outputs, source custody and no-work rejection."""
import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_oracle import feature
from test_source_contract import REFERENCE

ROOT = Path(__file__).resolve().parent


class QuantizedRunnerTests(unittest.TestCase):
    def cli(self, output, controller=None, extra=()):
        feature("run_quantized")
        return subprocess.run([sys.executable, "-B", str(ROOT / "run_quantized.py"), "--controller",
                               str(controller if controller is not None else REFERENCE / "carcontroller.py"),
                               "--helper", str(REFERENCE / "lateral.py"), "--output", str(output), *extra],
                              capture_output=True, text=True, check=False)

    def test_two_process_bytes_literal_semantics_and_gates(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            a, b = root / "one", root / "two"
            first, second = self.cli(a), self.cli(b)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            one = {p.name: p.read_bytes() for p in a.iterdir()}
            two = {p.name: p.read_bytes() for p in b.iterdir()}
            self.assertEqual(one, two)
            summary = json.loads(one["summary.json"])
            self.assertEqual(summary["status"], "F70UGZ_R4_SYNTHETIC_QUANTIZED_LATERAL_PIPELINE_PASS")
            self.assertGreater(summary["quantization_vectors"], 300)
            self.assertEqual((summary["normalized_scenarios"], summary["transition_steps"]), (224, 2802))
            self.assertEqual(summary["helper_execution_counts"]["limiter_traced"], 2802)
            self.assertEqual(summary["helper_execution_counts"]["fault_explicit"], 2802)
            self.assertEqual(summary["helper_execution_counts"]["traced_clip_calls"], 5604)
            self.assertEqual(summary["original_caller_execution"], 0)
            self.assertEqual(summary["F61_execution"], 0)
            self.assertEqual(summary["forbidden_modules_loaded"], [])
            self.assertIsNone(summary["actual_vehicle_scale"])
            self.assertEqual(summary["STATIC_EVIDENCE_GATE"], "FAIL")
            trajectories = {x["id"]: x for x in json.loads(one["normalized_results.json"])}
            literals = trajectories["N-decimal-ties"]["steps"]
            self.assertEqual([x["model"]["quantization"]["integer_command"] for x in literals], [0, 2, 0, -2])
            self.assertEqual([x["model"]["downstream"]["final_command"] for x in trajectories["N-inactive"]["steps"]], [2, 0, 0, 2])
            identity = json.loads(one["execution_identity.json"])
            self.assertEqual(identity["code_hashes"]["request_quantizer.py"], hashlib.sha256((ROOT / "request_quantizer.py").read_bytes()).hexdigest())
            for raw in one.values():
                self.assertEqual(raw, (json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False,
                                                   separators=(",", ":"), allow_nan=False) + "\n").encode())

    def test_bad_source_before_helper_creation_and_no_output(self):
        module = feature("run_quantized")
        contract = feature("source_contract")
        with (patch("run_quantized.NormalizedReference", side_effect=AssertionError("HELPER_MUST_NOT_COMPILE")),
              self.assertRaises(contract.ContractIdentityError)):
            module.build_results(b"bad", (REFERENCE / "lateral.py").read_bytes())
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source = root / "bad.py"
            source.write_bytes(b"raise RuntimeError('never run')")
            result = self.cli(root / "output", controller=source)
            self.assertEqual(result.returncode, 2)
            self.assertIn("EXACT_SOURCE_IDENTITY_REQUIRED", result.stderr)
            self.assertFalse((root / "output").exists())

    def test_dangling_output_entry_rejects_before_reads_and_numeric_work(self):
        module = feature("run_quantized")
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            output = root / "dead"
            output.symlink_to(root / "missing", target_is_directory=True)
            argv = ["run_quantized", "--controller", str(root / "missing.py"), "--helper", str(root / "missing2.py"), "--output", str(output)]
            stderr = io.StringIO()
            with (patch.object(sys, "argv", argv), contextlib.redirect_stderr(stderr),
                  patch.object(module, "build_results", side_effect=AssertionError("NUMERIC_WORK_REACHED"))):
                self.assertEqual(module.main(), 2)
            self.assertIn("OUTPUT_EXISTS_NO_HELPER_EXECUTION", stderr.getvalue())
            self.assertTrue(output.is_symlink())

    def test_no_arbitrary_dataset_or_production_mode(self):
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / "output"
            result = self.cli(output, extra=("--production", "--data", "not_a_dataset"))
            self.assertEqual(result.returncode, 2)
            self.assertIn("unrecognized arguments", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
