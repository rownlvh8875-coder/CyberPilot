"""Fixed synthetic catalog CLI; no vehicle, policy or arbitrary-data input mode."""
import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
from kernel import SOURCE_BYTES, SOURCE_SHA, Kernel
from oracle import oracle_fault, oracle_limiter
from vectors import fault_cases, limiter_cases

STATUS = "F70UGZ_R2_SYNTHETIC_HELPER_ARITHMETIC_CONFORMANCE_PASS"


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def runtime_identity() -> dict:
    if platform.python_implementation() != "CPython" or platform.python_version() != "3.12.13" or sys.float_info.mant_dig != 53:
        raise RuntimeError("PINNED_CPYTHON_BINARY64_REQUIRED")
    dist = importlib.metadata.distribution("numpy")
    payload = {}
    for entry in sorted(dist.files or [], key=str):
        name = str(entry)
        if "__pycache__" in name or name.endswith(".pyc") or ".." in Path(name).parts:
            continue
        path = Path(str(dist.locate_file(entry)))
        if path.is_file():
            payload[name] = digest(path.read_bytes())
    if not payload:
        raise RuntimeError("NUMPY_PAYLOAD_IDENTITY_MISSING")
    return {"python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(), "python_build": sys.version,
            "python_executable_sha256": digest(Path(sys.executable).resolve().read_bytes()),
            "platform": platform.platform(), "machine": platform.machine(),
            "binary64_mantissa_bits": sys.float_info.mant_dig, "numpy_version": np.__version__,
            "numpy_int_bytes": np.dtype(int).itemsize, "numpy_float64_bytes": np.dtype(np.float64).itemsize,
            "numpy_payload_hashes": payload, "numpy_payload_manifest_sha256": digest(canonical(payload)),
            "closure_scope": "installed distribution site-package files excluding pycache, bytecode and external console scripts; not full OS/production closure"}


def evaluate(source: bytes) -> dict[str, bytes]:
    runtime = runtime_identity()
    kernel = Kernel(source)
    limiter_results = []
    for case_id, case in limiter_cases():
        expected = oracle_limiter(case)
        traced = kernel.limiter(case, traced=True)
        direct = kernel.limiter(case, traced=False)
        observed = {key: traced[key] for key in ("result", "clips")}
        if observed != expected or direct["result"] != expected["result"] or direct["reads"] != traced["reads"]:
            raise RuntimeError(f"EXACT_LIMITER_PARITY_FAILED:{case_id}")
        inputs = asdict(case)
        inputs["driver"] = float(case.driver).hex()
        limiter_results.append({"id": case_id, "synthetic_inputs": inputs, "oracle": expected,
                                "target_traced": traced, "target_direct_result": direct["result"], "parity": "PASS"})
    fault_results = []
    for case_id, case in fault_cases():
        expected = oracle_fault(case)
        actual = kernel.fault(case)
        default = kernel.fault(case, use_default=True) if case.mismatch == 1 else None
        if actual != expected or (default is not None and default != expected):
            raise RuntimeError(f"EXACT_FAULT_PARITY_FAILED:{case_id}")
        fault_results.append({"id": case_id, "synthetic_inputs": asdict(case), "oracle": expected,
                              "target": actual, "default_parameter_result": default, "parity": "PASS"})
    forbidden = sorted(name for name in sys.modules if name.split(".")[0] in {"selfdrive", "opendbc", "cereal", "openpilot"}
                       or name.startswith("synthetic_rate_constraint_feasibility"))
    if forbidden:
        raise RuntimeError("PROHIBITED_MODULE_LOADED")
    summary = {"status": STATUS, "limiter_vectors": len(limiter_results), "fault_vectors": len(fault_results),
               "source_execution_counts": kernel.counts, "forbidden_modules_loaded": forbidden,
               "whole_original_module_imports": 0, "controller_execution": 0, "runtime_execution": 0,
               "can_calls": 0, "f61_execution": 0, "calculator_input_execution": 0, "r_calculations": 0,
               "candidate_evaluation": 0, "actual_production_inputs": 0,
               "actual_r": None, "actual_T2": None, "actual_vehicle_scale": None,
               "R_BUDGET": "UNRESOLVED", "STATIC_EVIDENCE_GATE": "FAIL", "actual_activation": "NOT_ALLOWED",
               "F70UH": "NOT_ALLOWED", "F70V": "NOT_ALLOWED", "F71": "NOT_ALLOWED",
               "claim_scope": "exact controlled function-body conformance in declared synthetic subset, not module/runtime/vehicle equivalence",
               "ARITH_REQUEST_ROUND": "NOT_RUN_OUTSIDE_SELECTED_HELPER_SCOPE"}
    identity = {"source_filename": "opendbc_repo/opendbc/car/lateral.py", "source_sha256": SOURCE_SHA,
                "source_byte_size": SOURCE_BYTES, "source_unchanged": True,
                "symbols": {"apply_driver_steer_torque_limits": [70, 90], "common_fault_avoidance": [174, 195]},
                "injected_globals": {"np_direct": "numpy2.5.3", "np_traced": "delegate each clip once to numpy2.5.3 and record scalar results",
                                     "builtins": ["int", "float", "bool", "max", "min", "round"]},
                "limits_binding": "immutable builtin-int snapshot wrapped with ordered-read recorder; not mutable production context"}
    return {"summary.json": canonical(summary), "identity.json": canonical(identity), "runtime.json": canonical(runtime),
            "limiter_results.json": canonical(limiter_results), "fault_results.json": canonical(fault_results)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Only exact hash-pinned lateral.py accepted")
    parser.add_argument("--output", type=Path, required=True, help="New output directory, never overwritten")
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise FileExistsError("OUTPUT_EXISTS_NO_EXECUTION")
        files = evaluate(args.source.read_bytes())
        args.output.mkdir(parents=True, exist_ok=False)
        for name, raw in sorted(files.items()):
            with (args.output / name).open("xb") as output:
                output.write(raw)
    except (ValueError, RuntimeError, OSError, TypeError) as error:
        print(f"REJECTED: {error}", file=sys.stderr)
        return 2
    print(STATUS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
