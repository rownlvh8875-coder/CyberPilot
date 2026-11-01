"""Static source/schema contract, no executable Controller or Cap'n Proto load."""
import ast
import hashlib
import re

from quantization_contract import derive_quantization_contract
from source_contract import (
    CONTROLLER_BYTES,
    CONTROLLER_SHA,
    HELPER_BYTES,
    HELPER_SHA,
    ContractIdentityError,
)

SCHEMA_SHA = "098a19d69e8d233ac653503b53761a94824f31812757a11a7ded1589fe1e0788"
SCHEMA_BYTES = 21300


def derive_output_contract(controller: bytes, helper: bytes, schema: bytes) -> dict:
    for raw, size, expected in [(controller, CONTROLLER_BYTES, CONTROLLER_SHA), (helper, HELPER_BYTES, HELPER_SHA),
                                 (schema, SCHEMA_BYTES, SCHEMA_SHA)]:
        if type(raw) is not bytes or len(raw) != size or hashlib.sha256(raw).hexdigest() != expected:
            raise ContractIdentityError("EXACT_OUTPUT_SOURCE_SCHEMA_IDENTITY_REQUIRED")
    base = derive_quantization_contract(controller, helper)
    text = controller.decode("utf-8")
    nodes = {n.lineno: n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.Assign) and n.lineno in (121, 122)}
    assignments = [{"start_line": node.lineno, "end_line": node.end_lineno, "symbol": ast.unparse(node.targets[0]),
                    "source_sha256": CONTROLLER_SHA, "exact_source_segment": ast.get_source_segment(text, node),
                    "expression": ast.unparse(node.value), "ast": ast.dump(node, include_attributes=False)}
                   for _, node in sorted(nodes.items())]
    fields, depth, inside = {}, 0, False
    for no, line in enumerate(schema.decode("utf-8").splitlines(), 1):
        if "struct Actuators {" in line:
            inside = True
        if inside:
            depth += line.count("{") - line.count("}")
            match = re.match(r"\s*(torque|torqueOutputCan)\s*@(\d+)\s*:\s*(\w+);", line)
            if match:
                name, ordinal, field_type = match.groups()
                fields[name] = {"type": field_type, "ordinal": int(ordinal), "line": no,
                                "exact_source_line": line, "symbol": "CarControl.Actuators." + name, "source_sha256": SCHEMA_SHA}
            if depth == 0:
                break
    return {"schema_version": 1, "contract_id": "F70UGZ_R5_OUTPUT_SCHEMA_SIMULATION_V1", "input_contract": base,
            "schema_source": {"filename": "opendbc_repo/opendbc/car/car.capnp", "bytes": SCHEMA_BYTES, "sha256": SCHEMA_SHA},
            "output_assignments": assignments, "schema_fields": fields,
            "normalized_model_expression": "builtin integer command / same explicit synthetic Limits.STEER_MAX",
            "clamp": "NONE; schema comment is not a runtime range validator", "actual_capnp_wire": "NOT_ESTABLISHED",
            "actual_serializer_execution": 0, "original_controller_execution": 0,
            "projection": "IEEE754 binary32 RNE numeric word simulation, NOT Cap'n Proto/CAN packet bytes"}
