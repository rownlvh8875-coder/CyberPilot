"""Fixed synthetic state trajectories only. No actual-data or runtime mode."""
import argparse
import sys
from dataclasses import asdict
from pathlib import Path

from flow_types import State
from run_checks import canonical, digest, runtime_identity
from scenarios import catalog
from source_contract import CONTROLLER_BYTES, HELPER_BYTES, derive_contract
from source_reference import SourceReference
from state_model import initial_state, step

STATUS = "F70UGZ_R3_SYNTHETIC_LATERAL_STATE_MODEL_PASS"


def _sample_record(sample) -> dict:
    record = asdict(sample)
    record["driver"] = float(sample.driver).hex()
    record["angle_deg"] = float(sample.angle_deg).hex()
    return record


def build_results(controller: bytes, helper: bytes) -> dict[str, bytes]:
    contract = derive_contract(controller, helper)
    runtime = runtime_identity()
    reference = SourceReference(controller, helper)
    scenarios = catalog()
    fixture_data = [{"id": item.id, "samples": [_sample_record(s) for s in item.samples]} for item in scenarios]
    results, total = [], 0
    for scenario in scenarios:
        model_state = initial_state()
        source_state = State(0, None, contract["initializers"]["self.apply_torque_last"]["value"],
                             contract["initializers"]["self.angle_limit_counter"]["value"])
        records = []
        for sample in scenario.samples:
            actual = step(model_state, sample)
            expected = reference.step(source_state, sample)
            if actual != expected:
                raise RuntimeError(f"EXACT_STATE_PARITY_FAILED:{scenario.id}:{sample.index}")
            records.append({"sample": _sample_record(sample), "model_state_before": asdict(model_state),
                            "source_state_before": asdict(source_state), "model": asdict(actual),
                            "source_reference": asdict(expected), "parity": "PASS"})
            model_state, source_state = actual.next_state, expected.next_state
            total += 1
        results.append({"id": scenario.id, "steps": records})
    forbidden = sorted(name for name in sys.modules if name.split(".")[0] in {"selfdrive", "opendbc", "openpilot", "cereal"}
                       or name.startswith("synthetic_rate_constraint_feasibility"))
    if forbidden:
        raise RuntimeError("PROHIBITED_MODULE_LOADED")
    code_hashes = {p.name: digest(p.read_bytes()) for p in sorted(Path(__file__).resolve().parent.glob("*.py"))}
    identity = {"contract_id": contract["contract_id"], "controller_source": contract["controller_source"],
                "helper_source": contract["helper_source"], "code_hashes": code_hashes,
                "catalog_sha256": digest(canonical(fixture_data)), "runtime": runtime,
                "independence": "pure model uses unchanged R2 rational math; source reference uses only original helpers and independently written wiring",
                "index_semantics": "synthetic invocation index, not actual frame/time/dt"}
    summary = {"status": STATUS, "scenarios": len(scenarios), "transition_steps": total, "pure_model_calls": total,
               "helper_execution_counts": reference.counts, "forbidden_modules_loaded": forbidden,
               "whole_original_module_imports": 0, "controller_executable_code_compilations": 0,
               "controller_execution": 0, "runtime_execution": 0, "CAN": 0, "F61_execution": 0,
               "calculator_input_execution": 0, "r_calculations": 0, "candidate_performance_evaluation": 0,
               "actual_production_inputs": 0, "actual_activation": "NOT_ALLOWED",
               "actual_r": None, "actual_T2": None, "actual_vehicle_scale": None,
               "R_BUDGET": "UNRESOLVED", "STATIC_EVIDENCE_GATE": "FAIL", "SOURCE_SCHEMA_UNQUALIFIED": 6000,
               "Candidate": "NO_GO", "Runtime": "NO_GO", "D2": "PERFORMANCE_NOT_EVALUATED", "F19": "LEGACY_UNRESOLVED",
               "NATIVE_EXACT_REPLAY": "NOT_PROVEN", "F70UH": "NOT_ALLOWED", "F70V": "NOT_ALLOWED", "F71": "NOT_ALLOWED",
               "caller_line70_request_conversion": "NOT_RUN", "claim": "bounded synthetic selected-source state model, not full Controller/runtime/vehicle equivalence"}
    return {"summary.json": canonical(summary), "source_contract.json": canonical(contract),
            "execution_identity.json": canonical(identity), "catalog.json": canonical(fixture_data),
            "sequence_results.json": canonical(results)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controller", type=Path, required=True, help="Exact controller source, read as data only")
    parser.add_argument("--helper", type=Path, required=True, help="Exact helper source; only2 selected definitions execute")
    parser.add_argument("--output", type=Path, required=True, help="New destination, never overwritten")
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
