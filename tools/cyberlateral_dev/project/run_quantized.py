"""Closed synthetic quantization/lateral pipeline CLI, no actual-data mode."""
import argparse
import sys
from dataclasses import asdict
from pathlib import Path

from flow_types import State
from normalized_pipeline import step_normalized
from normalized_reference import NormalizedReference
from quantization_contract import derive_quantization_contract
from quantization_oracle import quantize_reference
from quantized_fixtures import normalized_scenarios, quantization_vectors
from request_quantizer import quantize
from run_checks import canonical, digest, runtime_identity
from source_contract import CONTROLLER_BYTES, HELPER_BYTES
from state_model import initial_state

STATUS = "F70UGZ_R4_SYNTHETIC_QUANTIZED_LATERAL_PIPELINE_PASS"


def _sample_record(sample) -> dict:
    value = asdict(sample)
    for key in ("request", "driver", "angle_deg"):
        value[key] = float(value[key]).hex()
    return value


def build_results(controller: bytes, helper: bytes) -> dict[str, bytes]:
    contract = derive_quantization_contract(controller, helper)
    runtime = runtime_identity()
    vectors = quantization_vectors()
    quantization_results = []
    for case_id, q, scale in vectors:
        actual, expected = quantize(q, scale), quantize_reference(q, scale)
        if actual != expected:
            raise RuntimeError(f"EXACT_QUANTIZATION_PARITY_FAILED:{case_id}")
        quantization_results.append({"id": case_id, "model": asdict(actual), "bit_oracle": asdict(expected), "parity": "PASS"})
    reference = NormalizedReference(controller, helper)
    scenarios = normalized_scenarios()
    fixture_data = {"quantization_vectors": [{"id": case_id, "request_hex": float(q).hex(), "scale": scale} for case_id, q, scale in vectors],
                    "normalized_scenarios": [{"id": item.id, "samples": [_sample_record(s) for s in item.samples]} for item in scenarios]}
    trajectories, total = [], 0
    base = contract["base_integer_state_contract"]
    for scenario in scenarios:
        model_state = initial_state()
        source_state = State(0, None, base["initializers"]["self.apply_torque_last"]["value"],
                             base["initializers"]["self.angle_limit_counter"]["value"])
        records = []
        for sample in scenario.samples:
            actual = step_normalized(model_state, sample)
            expected = reference.step(source_state, sample)
            if actual != expected:
                raise RuntimeError(f"EXACT_NORMALIZED_PIPELINE_PARITY_FAILED:{scenario.id}:{sample.index}")
            records.append({"sample": _sample_record(sample), "model_state_before": asdict(model_state),
                            "reference_state_before": asdict(source_state), "model": asdict(actual),
                            "source_reference": asdict(expected), "parity": "PASS"})
            model_state, source_state = actual.downstream.next_state, expected.downstream.next_state
            total += 1
        trajectories.append({"id": scenario.id, "steps": records})
    forbidden = sorted(name for name in sys.modules if name.split(".")[0] in {"selfdrive", "opendbc", "openpilot", "cereal"}
                       or name.startswith("synthetic_rate_constraint_feasibility"))
    if forbidden:
        raise RuntimeError("PROHIBITED_MODULE_LOADED")
    code = {p.name: digest(p.read_bytes()) for p in sorted(Path(__file__).resolve().parent.glob("*.py"))}
    identity = {"contract_id": contract["contract_id"], "controller_source": base["controller_source"],
                "helper_source": base["helper_source"], "code_hashes": code, "runtime": runtime,
                "catalog_sha256": digest(canonical(fixture_data)),
                "independence": "builtin binary64 quantizer+R3 pure model versus integer-bit oracle+original-helper reference; separate state chains",
                "synthetic_types": "exact builtin binary64 float q[-1,1], explicit int scale1..2048 from same Limits snapshot",
                "actual_accessors_wire_params_dtype": "NOT_ESTABLISHED", "original_caller_source_authority": "AST_AND_BYTES_ONLY"}
    summary = {"status": STATUS, "quantization_vectors": len(vectors), "normalized_scenarios": len(scenarios),
               "transition_steps": total, "new_quantizer_calls": len(vectors) + total, "bit_oracle_calls": len(vectors) + total,
               "helper_execution_counts": reference.counts, "pure_state_model_calls": total,
               "forbidden_modules_loaded": forbidden, "whole_original_module_imports": 0,
               "original_caller_execution": 0, "controller_execution": 0, "controller_executable_code_compilation": 0,
               "Runtime_execution": 0, "CAN": 0, "F61_execution": 0, "calculator_input_execution": 0,
               "r_calculations": 0, "candidate_performance_evaluation": 0, "actual_production_inputs": 0,
               "actual_r": None, "actual_T2": None, "actual_vehicle_scale": None, "R_BUDGET": "UNRESOLVED",
               "STATIC_EVIDENCE_GATE": "FAIL", "SOURCE_SCHEMA_UNQUALIFIED": 6000, "Candidate": "NO_GO", "Runtime": "NO_GO",
               "D2": "PERFORMANCE_NOT_EVALUATED", "F19": "LEGACY_UNRESOLVED", "NATIVE_EXACT_REPLAY": "NOT_PROVEN",
               "actual_activation": "NOT_ALLOWED", "F70UH": "NOT_ALLOWED", "F70V": "NOT_ALLOWED", "F71": "NOT_ALLOWED",
               "output_guard": "exists OR is_symlink before reads/work; no race-free/atomicity claim",
               "claim": "synthetic typed request-to-final-command pipeline only, not actual Controller/runtime/vehicle equivalence"}
    return {"summary.json": canonical(summary), "quantization_contract.json": canonical(contract),
            "execution_identity.json": canonical(identity), "catalog.json": canonical(fixture_data),
            "quantization_results.json": canonical(quantization_results), "normalized_results.json": canonical(trajectories)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controller", type=Path, required=True, help="Exact source read as AST/data only")
    parser.add_argument("--helper", type=Path, required=True, help="Exact source, only2 selected helper definitions execute")
    parser.add_argument("--output", type=Path, required=True, help="New output entry, no overwrite")
    args = parser.parse_args()
    try:
        if args.output.exists() or args.output.is_symlink():
            raise FileExistsError("OUTPUT_EXISTS_NO_HELPER_EXECUTION")
        with args.controller.open("rb") as stream:
            controller = stream.read(CONTROLLER_BYTES + 1)
        with args.helper.open("rb") as stream:
            helper = stream.read(HELPER_BYTES + 1)
        files = build_results(controller, helper)
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
