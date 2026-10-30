"""Executable CLI contracts: deterministic results and no writes on rejection."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from domain import LimiterCase, Limits
from oracle import oracle_limiter
from test_kernel import SOURCE

ROOT = Path(__file__).resolve().parent


class RunnerTests(unittest.TestCase):
    def cli(self, source, output):
        self.assertIsNotNone(importlib.util.find_spec("run_checks"), "Missing planned catalog CLI")
        return subprocess.run([sys.executable, "-B", str(ROOT / "run_checks.py"), "--source", str(source), "--output", str(output)],
                              capture_output=True, text=True, check=False)

    def test_cli_two_clean_process_results_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as scratch:
            parent = Path(scratch)
            first, second = parent / "one", parent / "two"
            a, b = self.cli(SOURCE, first), self.cli(SOURCE, second)
            self.assertEqual(a.returncode, 0, a.stderr)
            self.assertEqual(b.returncode, 0, b.stderr)
            one = {p.name: p.read_bytes() for p in first.iterdir()}
            two = {p.name: p.read_bytes() for p in second.iterdir()}
            self.assertEqual(one, two)
            summary = json.loads(one["summary.json"])
            self.assertEqual(summary["status"], "F70UGZ_R2_SYNTHETIC_HELPER_ARITHMETIC_CONFORMANCE_PASS")
            self.assertEqual(summary["limiter_vectors"], 3136)
            self.assertEqual(summary["fault_vectors"], 1392)
            self.assertEqual(summary["source_execution_counts"]["limiter_direct"], 3136)
            self.assertEqual(summary["source_execution_counts"]["limiter_traced"], 3136)
            self.assertEqual(summary["source_execution_counts"]["traced_clip_calls"], 6272)
            self.assertEqual(summary["forbidden_modules_loaded"], [])
            self.assertIsNone(summary["actual_r"])
            for content in one.values():
                obj = json.loads(content)
                self.assertEqual(content, (json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode())

    def test_cli_corrupt_source_rejects_without_output(self):
        with tempfile.TemporaryDirectory() as scratch:
            parent = Path(scratch)
            source, output = parent / "wrong.py", parent / "output"
            # Test fixture only; original pinned file is never written.
            source.write_bytes(b"raise RuntimeError('must not execute')\n")
            result = self.cli(source, output)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("EXACT_SOURCE_BYTES_REQUIRED", result.stderr)
            self.assertFalse(output.exists())

    def test_cli_existing_output_is_preserved_without_execution(self):
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch)
            marker = output / "keep.txt"
            marker.write_bytes(b"preserve")
            # Missing source proves output-exists check precedes source reading.
            result = self.cli(output / "absent.py", output)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("OUTPUT_EXISTS_NO_EXECUTION", result.stderr)
            self.assertEqual(list(output.iterdir()), [marker])
            self.assertEqual(marker.read_bytes(), b"preserve")

    def test_numeric_domain_extremes_remain_exact(self):
        from kernel import Kernel
        kernel = Kernel(SOURCE.read_bytes())
        for driver in [-1024.0, -1023.99609375, 1023.99609375, 1024.0]:
            for previous in [-2048, 0, 2048]:
                case = LimiterCase(2048, previous, driver, Limits(4096, 64, 64, 64, 8, 8), 4096)
                actual = kernel.limiter(case, traced=True)
                self.assertEqual({key: actual[key] for key in ("result", "clips")}, oracle_limiter(case))


if __name__ == "__main__":
    unittest.main()
