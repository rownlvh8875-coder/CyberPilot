"""Executable synthetic sequence delivery, deterministic and fail-closed."""
import hashlib
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


class SequenceRunnerTests(unittest.TestCase):
    def cli(self, controller, helper, output):
        feature("run_sequences")
        return subprocess.run([sys.executable, "-B", str(ROOT / "run_sequences.py"), "--controller", str(controller),
                               "--helper", str(helper), "--output", str(output)], capture_output=True, text=True, check=False)

    def test_two_process_outputs_identical_and_real_transitions(self):
        with tempfile.TemporaryDirectory() as scratch:
            parent = Path(scratch)
            first, second = parent / "one", parent / "two"
            a = self.cli(REFERENCE / "carcontroller.py", REFERENCE / "lateral.py", first)
            b = self.cli(REFERENCE / "carcontroller.py", REFERENCE / "lateral.py", second)
            self.assertEqual(a.returncode, 0, a.stderr)
            self.assertEqual(b.returncode, 0, b.stderr)
            one = {p.name: p.read_bytes() for p in first.iterdir()}
            two = {p.name: p.read_bytes() for p in second.iterdir()}
            self.assertEqual(one, two)
            summary = json.loads(one["summary.json"])
            self.assertEqual(summary["status"], "F70UGZ_R3_SYNTHETIC_LATERAL_STATE_MODEL_PASS")
            self.assertEqual((summary["scenarios"], summary["transition_steps"]), (227, 2913))
            self.assertEqual(summary["helper_execution_counts"]["limiter_traced"], 2913)
            self.assertEqual(summary["helper_execution_counts"]["fault_explicit"], 2913)
            self.assertEqual(summary["helper_execution_counts"]["traced_clip_calls"], 5826)
            self.assertEqual(summary["controller_execution"], 0)
            self.assertEqual(summary["forbidden_modules_loaded"], [])
            self.assertIsNone(summary["actual_r"])
            self.assertEqual(summary["STATIC_EVIDENCE_GATE"], "FAIL")
            data = {s["id"]: s for s in json.loads(one["sequence_results.json"])}
            self.assertEqual([s["model"]["final_command"] for s in data["H-inactive"]["steps"]], [2, 0, 0, 2])
            fault = data["H-fault-cycle"]["steps"][89]["model"]
            self.assertFalse(fault["steer_request"])
            self.assertEqual((fault["final_command"], fault["next_state"]["angle_counter"]), (16, 90))
            identity = json.loads(one["execution_identity.json"])
            self.assertEqual(identity["code_hashes"]["state_model.py"], hashlib.sha256((ROOT / "state_model.py").read_bytes()).hexdigest())
            for raw in one.values():
                self.assertEqual(raw, (json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False,
                                                   separators=(",", ":"), allow_nan=False) + "\n").encode())

    def test_bad_identity_rejected_before_reference_initialization(self):
        module = feature("run_sequences")
        contract = feature("source_contract")
        with (patch("run_sequences.SourceReference", side_effect=AssertionError("HELPER_MUST_NOT_COMPILE")),
              self.assertRaises(contract.ContractIdentityError)):
            module.build_results(b"bad controller", (REFERENCE / "lateral.py").read_bytes())

    def test_existing_output_rejected_before_source_reads(self):
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch)
            marker = output / "keep.txt"
            marker.write_bytes(b"preserve")
            result = self.cli(output / "missing.py", output / "missing2.py", output)
            self.assertEqual(result.returncode, 2)
            self.assertIn("OUTPUT_EXISTS_NO_HELPER_EXECUTION", result.stderr)
            self.assertEqual(marker.read_bytes(), b"preserve")
            self.assertEqual(list(output.iterdir()), [marker])

    def test_corrupted_source_no_output_and_no_arbitrary_data_mode(self):
        with tempfile.TemporaryDirectory() as scratch:
            parent = Path(scratch)
            wrong = parent / "wrong.py"
            wrong.write_bytes(b"raise RuntimeError('never execute')")
            output = parent / "output"
            result = self.cli(wrong, REFERENCE / "lateral.py", output)
            self.assertEqual(result.returncode, 2)
            self.assertIn("EXACT_SOURCE_IDENTITY_REQUIRED", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
