"""Closed synthetic public-API/output validation; no arbitrary-data or install mode."""
import argparse
import sys
from dataclasses import asdict, astuple
from pathlib import Path

from flow_types import State
from normalized_reference import NormalizedReference
from output_contract import SCHEMA_BYTES, derive_output_contract
from output_fixtures import codec_vectors, output_vectors
from output_oracle import float32_reference, project_reference
from quantized_fixtures import normalized_scenarios
from run_checks import canonical, digest, runtime_identity
from source_contract import CONTROLLER_BYTES, HELPER_BYTES
from v1_helpers import ROOT, package_feature

STATUS = "F70UGZ_R5_CYBERLATERAL_DEV_V1_OUTPUT_PACKAGE_PASS"


def _sample_record(sample):
    record = asdict(sample)
    for key in ("request", "driver", "angle_deg"):
        record[key] = float(record[key]).hex()
    return record


def build_results(controller: bytes, helper: bytes, schema: bytes) -> dict[str, bytes]:
    contract = derive_output_contract(controller, helper, schema)
    runtime = runtime_identity()
    package = package_feature()
    projection = package_feature("cyberlateral_dev.output_projection")
    output_results, codec_results = [], []
    for name, command, scale in output_vectors():
        actual = asdict(projection.project_output(command, scale))
        expected = project_reference(command, scale)
        if actual != expected:
            raise RuntimeError(f"EXACT_OUTPUT_PARITY_FAILED:{name}")
        output_results.append({"id": name, "model": actual, "integer_oracle": expected, "parity": "PASS"})
    for name, value in codec_vectors():
        actual = asdict(projection.simulate_float32(value))
        expected = float32_reference(value)
        if actual != expected:
            raise RuntimeError(f"EXACT_CODEC_PARITY_FAILED:{name}")
        codec_results.append({"id": name, "input_hex": value.hex(), "model": actual, "integer_oracle": expected, "parity": "PASS"})
    reference = NormalizedReference(controller, helper)
    scenarios = normalized_scenarios()
    trajectories, total = [], 0
    for scenario in scenarios:
        public_state, source_state = package.initial_state(), State(0, None, 0, 0)
        records = []
        for sample in scenario.samples:
            public_sample = package.LateralInput(sample.index, sample.request, sample.driver, sample.angle_deg,
                                                sample.lat_active, package.Limits(*astuple(sample.limits)), sample.provenance)
            actual = asdict(package.step(public_sample, public_state))
            expected_trace = reference.step(source_state, sample)
            expected = {"projection": project_reference(expected_trace.downstream.final_command, sample.limits.STEER_MAX),
                        "steer_request": expected_trace.downstream.steer_request,
                        "next_state": asdict(expected_trace.downstream.next_state), "trace": asdict(expected_trace)}
            if actual != expected:
                raise RuntimeError(f"EXACT_PUBLIC_API_PARITY_FAILED:{scenario.id}:{sample.index}")
            records.append({"sample": _sample_record(sample), "model_state_before": asdict(public_state),
                            "reference_state_before": asdict(source_state), "model": actual,
                            "independent_reference": expected, "parity": "PASS"})
            public_state = package.LateralState(**actual["next_state"])
            source_state = expected_trace.downstream.next_state
            total += 1
        trajectories.append({"id": scenario.id, "steps": records})
    forbidden = sorted(name for name in sys.modules if name.split(".")[0] in {"selfdrive", "opendbc", "openpilot", "cereal", "capnp"}
                       or name.startswith("synthetic_rate_constraint_feasibility"))
    if forbidden:
        raise RuntimeError("PROHIBITED_MODULE_LOADED")
    catalog = {"output_vectors": [{"id": name, "command": command, "scale": scale} for name, command, scale in output_vectors()],
               "codec_vectors": [{"id": name, "value_hex": value.hex()} for name, value in codec_vectors()],
               "normalized_scenarios": [{"id": item.id, "samples": [_sample_record(s) for s in item.samples]} for item in scenarios]}
    code_paths = [*sorted((ROOT / "project").glob("*.py")), *sorted((ROOT / "src").rglob("*.py")),
                  ROOT / "src/cyberlateral_dev/provenance/derived_modules.json", ROOT / "build_backend.py", ROOT / "pyproject.toml"]
    identity = {"contract_id": contract["contract_id"], "package": "cyberlateral-dev", "version": package.__version__,
                "runtime": runtime, "code_hashes": {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in code_paths},
                "catalog_sha256": digest(canonical(catalog)),
                "independence": "relocated pure R4 package + builtin quotient/struct projection versus original2 helpers + integer-bit quantization/output oracle; separate state chains",
                "source_authority": "Controller/schema data+AST only, no original caller or serializer execution",
                "installed_wheel_validation": "separate test_wheel.py empty-venv test; source CLI is NOT installation proof"}
    summary = {"status": STATUS, "output_vectors": len(output_results), "codec_vectors": len(codec_results),
               "normalized_scenarios": len(trajectories), "transition_steps": total, "helper_execution_counts": reference.counts,
               "package_original_helper_calls": 0, "forbidden_modules_loaded": forbidden,
               "whole_original_module_imports": 0, "original_caller_execution": 0, "controller_execution": 0,
               "controller_executable_code_compilation": 0, "actual_serializer_execution": 0, "schema_compilation": 0,
               "Runtime_execution": 0, "CAN": 0, "F61_execution": 0, "calculator_input_execution": 0,
               "r_calculations": 0, "candidate_performance_evaluation": 0, "actual_production_inputs": 0,
               "actual_r": None, "actual_T2": None, "actual_vehicle_scale": None, "R_BUDGET": "UNRESOLVED",
               "STATIC_EVIDENCE_GATE": "FAIL", "SOURCE_SCHEMA_UNQUALIFIED": 6000, "Candidate": "NO_GO", "Runtime": "NO_GO",
               "D2": "PERFORMANCE_NOT_EVALUATED", "F19": "LEGACY_UNRESOLVED", "NATIVE_EXACT_REPLAY": "NOT_PROVEN",
               "actual_activation": "NOT_ALLOWED", "F70UH": "NOT_ALLOWED", "F70V": "NOT_ALLOWED", "F71": "NOT_ALLOWED",
               "output_guard": "exists OR is_symlink before reads/work; not race-free/atomic snapshot proof",
               "claim": "synthetic development module/output simulation only; not actual Cap'n Proto/CAN/Controller/vehicle equivalence"}
    return {"summary.json": canonical(summary), "output_contract.json": canonical(contract), "execution_identity.json": canonical(identity),
            "catalog.json": canonical(catalog), "output_results.json": canonical(output_results), "codec_results.json": canonical(codec_results),
            "api_results.json": canonical(trajectories)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controller", type=Path, required=True, help="Exact source, data/AST only")
    parser.add_argument("--helper", type=Path, required=True, help="Exact source, only2 selected helper definitions execute")
    parser.add_argument("--schema", type=Path, required=True, help="Exact schema read as data only, never compiled/loaded")
    parser.add_argument("--output", type=Path, required=True, help="New output entry, no overwrite")
    args = parser.parse_args()
    try:
        if args.output.exists() or args.output.is_symlink():
            raise FileExistsError("OUTPUT_EXISTS_NO_HELPER_EXECUTION")
        values = []
        for source, size in [(args.controller, CONTROLLER_BYTES), (args.helper, HELPER_BYTES), (args.schema, SCHEMA_BYTES)]:
            with source.open("rb") as stream:
                values.append(stream.read(size + 1))
        files = build_results(*values)
        args.output.mkdir(parents=True, exist_ok=False)
        for name, raw in sorted(files.items()):
            with (args.output / name).open("xb") as stream:
                stream.write(raw)
    except (ValueError, RuntimeError, OSError, TypeError) as error:
        print(f"REJECTED: {error}", file=sys.stderr)
        return 2
    print(STATUS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
