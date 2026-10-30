"""Catch missing end-to-end outputs, source guards and unsafe CLI work."""
import contextlib
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


class ModuleRunnerTests(unittest.TestCase):
    def cli(self, output, extra=()):
        feature("run_module_v1")
        return subprocess.run([sys.executable, "-B", str(ROOT / "run_module_v1.py"), "--controller",
                               str(REFERENCE / "carcontroller.py"), "--helper", str(REFERENCE / "lateral.py"),
                               "--schema", str(REFERENCE / "car.capnp"), "--output", str(output), *extra],
                              capture_output=True, text=True, check=False)

    def test_two_process_results_literals_canonical_json_and_gates(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            a, b = root / "one", root / "two"
            for output in (a, b):
                result = self.cli(output)
                self.assertEqual(result.returncode, 0, result.stderr)
            files = {p.name: p.read_bytes() for p in a.iterdir()}
            self.assertEqual(files, {p.name: p.read_bytes() for p in b.iterdir()})
            summary = json.loads(files["summary.json"])
            self.assertEqual(summary["status"], "F70UGZ_R5_CYBERLATERAL_DEV_V1_OUTPUT_PACKAGE_PASS")
            self.assertEqual((summary["output_vectors"], summary["codec_vectors"]), (150, 19))
            self.assertEqual((summary["normalized_scenarios"], summary["transition_steps"]), (224, 2802))
            self.assertEqual(summary["helper_execution_counts"]["limiter_traced"], 2802)
            self.assertEqual(summary["helper_execution_counts"]["fault_explicit"], 2802)
            self.assertEqual(summary["package_original_helper_calls"], 0)
            for key in ("F61_execution", "controller_execution", "Runtime_execution", "CAN", "r_calculations",
                        "actual_production_inputs", "actual_serializer_execution"):
                self.assertEqual(summary[key], 0, key)
            self.assertEqual(summary["Runtime"], "NO_GO")
            self.assertEqual(summary["STATIC_EVIDENCE_GATE"], "FAIL")
            self.assertEqual(summary["R_BUDGET"], "UNRESOLVED")
            self.assertIsNone(summary["actual_vehicle_scale"])
            vectors = {r["id"]: r["model"] for r in json.loads(files["output_results.json"])}
            self.assertEqual(vectors["OUT:1:3"]["torque_float32"]["bits_hex"], "3eaaaaab")
            self.assertEqual(vectors["OUT:95:5"]["normalized_expression"], 19.0)
            self.assertEqual(vectors["OUT:0:1"]["normalized_expression_hex"], "0x0.0p+0")
            trajectories = {r["id"]: r for r in json.loads(files["api_results.json"])}
            ties = trajectories["N-decimal-ties"]["steps"]
            self.assertEqual([r["model"]["projection"]["integer_command"] for r in ties], [0, 2, 0, -2])
            for raw in files.values():
                self.assertEqual(raw, (json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False,
                                                   separators=(",", ":"), allow_nan=False) + "\n").encode())

    def test_all_three_identities_reject_before_reference_construction(self):
        module = feature("run_module_v1")
        from source_contract import ContractIdentityError
        good = [(REFERENCE / name).read_bytes() for name in ("carcontroller.py", "lateral.py", "car.capnp")]
        for index in range(3):
            bad = list(good)
            bad[index] = b"untrusted"
            with (patch.object(module, "NormalizedReference", side_effect=AssertionError("HELPER_MUST_NOT_LOAD")),
                  self.assertRaises(ContractIdentityError)):
                module.build_results(*bad)

    def test_existing_entries_reject_before_source_reads_or_calculation(self):
        module = feature("run_module_v1")
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            entries = (root / "file", root / "dir", root / "dead")
            entries[0].write_bytes(b"KEEP")
            entries[1].mkdir()
            entries[2].symlink_to(root / "missing", target_is_directory=True)
            for output in entries:
                argv = ["run_module_v1", "--controller", "missing", "--helper", "missing", "--schema", "missing",
                        "--output", str(output)]
                error = io.StringIO()
                with (patch.object(sys, "argv", argv), contextlib.redirect_stderr(error),
                      patch.object(module, "build_results", side_effect=AssertionError("NUMERIC_WORK_REACHED"))):
                    self.assertEqual(module.main(), 2)
                self.assertIn("OUTPUT_EXISTS_NO_HELPER_EXECUTION", error.getvalue())
            self.assertEqual(entries[0].read_bytes(), b"KEEP")
            self.assertTrue(entries[2].is_symlink())

    def test_missing_schema_does_not_create_output(self):
        feature("run_module_v1")
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / "out"
            result = self.cli(output, extra=("--schema", str(Path(scratch) / "absent.capnp")))
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())

    def test_no_production_arbitrary_dataset_or_install_mode(self):
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / "out"
            result = self.cli(output, extra=("--production", "--data", "actual_log", "--install"))
            self.assertEqual(result.returncode, 2)
            self.assertIn("unrecognized arguments", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
