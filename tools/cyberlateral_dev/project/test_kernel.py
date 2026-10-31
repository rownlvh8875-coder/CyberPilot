"""Real extracted function-body conformance; no whole-module import."""
import importlib
import math
import subprocess
import sys
import unittest
from pathlib import Path
from typing import cast

from domain import DomainError, FaultCase, LimiterCase, Limits
from oracle import oracle_fault, oracle_limiter
from test_oracle import feature

SOURCE = Path(__file__).resolve().parents[1] / "reference/lateral.py"


class KernelTests(unittest.TestCase):
    def kernel(self):
        return feature("kernel").Kernel(SOURCE.read_bytes())

    def test_corrupted_bytes_reject_before_execution(self):
        k = feature("kernel")
        for raw in [b"", SOURCE.read_bytes()[:-1], SOURCE.read_bytes() + b"\nraise RuntimeError('NOT_ALLOWED')\n",
                    SOURCE.read_bytes().replace(b"np.clip", b"zz.clip", 1)]:
            with self.subTest(size=len(raw)), self.assertRaises(k.SourceIdentityError):
                k.Kernel(raw)

    def test_literal_sequential_not_intersection_and_rounding(self):
        kernel = self.kernel()
        limits = Limits(16, 2, 5, 7, 1, 3)
        for case, want in [(LimiterCase(16, 10, -64.0, limits), 5),
                           (LimiterCase(-16, -10, 64.0, limits), -5),
                           (LimiterCase(20, 12, -8.5, limits), 12)]:
            with self.subTest(case=case):
                traced = kernel.limiter(case, traced=True)
                self.assertEqual(traced["result"], want)
                self.assertEqual({key: traced[key] for key in ("result", "clips")}, oracle_limiter(case))
                self.assertEqual(kernel.limiter(case, traced=False)["result"], want)

    def test_limits_reads_default_override_and_direction_order(self):
        kernel = self.kernel()
        limits = Limits(16, 2, 5, 7, 1, 3)
        calibration = ["STEER_DRIVER_ALLOWANCE", "STEER_DRIVER_FACTOR", "STEER_DRIVER_MULTIPLIER"] * 2
        for previous, expected_rate in [(1, ["STEER_DELTA_DOWN", "STEER_DELTA_UP", "STEER_DELTA_UP"]),
                                        (0, ["STEER_DELTA_UP", "STEER_DELTA_DOWN", "STEER_DELTA_UP"]),
                                        (-1, ["STEER_DELTA_UP", "STEER_DELTA_DOWN", "STEER_DELTA_UP"])]:
            for override in [None, 9]:
                with self.subTest(previous=previous, override=override):
                    result = kernel.limiter(LimiterCase(20, previous, 0.0, limits, override), traced=True)
                    expected = (["STEER_MAX"] if override is None else []) + calibration + expected_rate
                    self.assertEqual(result["reads"], expected)

    def test_invalid_domain_never_calls_original(self):
        kernel = self.kernel()
        before = dict(kernel.counts)
        limits = Limits(16, 2, 5, 7, 1, 3)
        for case in [LimiterCase(True, 0, 0.0, limits), LimiterCase(0, 0, math.nan, limits),
                     LimiterCase(0, 0, 0.1, limits), LimiterCase(0, 0, 0.0, cast(Limits, object()))]:
            with self.assertRaises(DomainError):
                kernel.limiter(case, traced=True)
        with self.assertRaises(DomainError):
            kernel.fault(FaultCase(True, True, 0, 2, 0))
        self.assertEqual(kernel.counts, before)

    def test_synthetic_grid_exact_output_and_intermediate_parity(self):
        kernel = self.kernel()
        catalog = feature("vectors").limiter_cases()
        self.assertEqual(len(catalog), 3136)
        for case_id, case in catalog:
            with self.subTest(case=case_id):
                expected = oracle_limiter(case)
                actual = kernel.limiter(case, traced=True)
                self.assertEqual({key: actual[key] for key in ("result", "clips")}, expected)
                self.assertEqual(kernel.limiter(case, traced=False)["result"], expected["result"])

    def test_fault_grid_and_default_parameter(self):
        kernel = self.kernel()
        catalog = feature("vectors").fault_cases()
        self.assertGreater(len(catalog), 1000)
        for case_id, case in catalog:
            with self.subTest(case=case_id):
                self.assertEqual(kernel.fault(case), oracle_fault(case))
                if case.mismatch == 1:
                    self.assertEqual(kernel.fault(case, use_default=True), oracle_fault(case))
        with self.assertRaises(DomainError):
            kernel.fault(FaultCase(True, True, 0, 2, 2), use_default=True)

    def test_sequential_output_used_as_explicit_previous(self):
        kernel = self.kernel()
        limits = Limits(16, 2, 5, 7, 1, 3)
        previous = 3
        outputs = []
        for requested in [-20, -20, 20, 20]:
            result = kernel.limiter(LimiterCase(requested, previous, 0.0, limits), traced=True)
            outputs.append(result["result"])
            previous = result["result"]
        self.assertEqual(outputs, [-2, -4, 1, 3])
        counter, requests = 0, []
        for _ in range(5):
            counter, request = kernel.fault(FaultCase(True, True, counter, 2, 2))
            requests.append((counter, request))
        self.assertEqual(requests, [(1, True), (2, True), (3, False), (0, False), (1, True)])

    def test_fresh_process_no_prohibited_modules_imported(self):
        feature("kernel")
        code = """
from pathlib import Path
import sys
from kernel import Kernel
from domain import Limits, LimiterCase, FaultCase
k = Kernel(Path(sys.argv[1]).read_bytes())
assert k.limiter(LimiterCase(100,0,0.0,Limits(16,2,5,7,1,3)),traced=True)['result']==2
assert k.fault(FaultCase(True,True,2,2))==(0,False)
bad=[x for x in sys.modules if x.split('.')[0] in ('opendbc','selfdrive','cereal','openpilot','synthetic_rate_constraint_feasibility_v1')]
assert not bad, bad
print('ISOLATED_OK')
"""
        result = subprocess.run([sys.executable, "-B", "-c", code, str(SOURCE)], cwd=Path(__file__).resolve().parent,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "ISOLATED_OK\n")

    def test_oracle_fresh_import_does_not_load_numpy_or_kernel(self):
        result = subprocess.run([sys.executable, "-B", "-c", "import sys, oracle; assert 'numpy' not in sys.modules; assert 'kernel' not in sys.modules"],
                                cwd=Path(__file__).resolve().parent, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_numpy_scalar_characterization_separate_from_helper_domain(self):
        feature("kernel")
        np = importlib.import_module("numpy")
        for args, want_hex in [((0.0, -0.0, 1.0), "0x0.0p+0"),
                               ((-0.0, 0.0, 1.0), "-0x0.0p+0"),
                               ((2.0, 4.0, 1.0), "0x1.0000000000000p+0")]:
            with self.subTest(args=args):
                self.assertEqual(float(np.clip(*args)).hex(), want_hex)
        # Narrow dependency characterization, NOT broader helper acceptance.
        for value, want in [(math.nextafter(0.5, 0.0), 0), (0.5, 0),
                            (math.nextafter(0.5, 1.0), 1), (-0.5, 0), (1.5, 2)]:
            self.assertEqual(int(round(float(value))), want)  # noqa: RUF046 — exact source conversion sequence.


if __name__ == "__main__":
    unittest.main()
