"""SHA-guarded AST/data extraction; NEVER execute or compile Controller code."""
import ast
import hashlib

CONTROLLER_SHA = "967d3f69076e19624bc18bdc897d141811c7aa80f727a497f176f670a6b4b59e"
CONTROLLER_BYTES = 11291
HELPER_SHA = "94cf2dde92b43590b1d1e5b2a37b3d295e5f2cf9700ca43e3846bcb1c3ef36b6"
HELPER_BYTES = 9367


class ContractIdentityError(ValueError):
    """Unverified bytes cannot establish this source-order authority."""


def _identity(raw, size, expected):
    if type(raw) is not bytes or len(raw) != size or hashlib.sha256(raw).hexdigest() != expected:
        raise ContractIdentityError("EXACT_SOURCE_IDENTITY_REQUIRED")


def _record(node: ast.stmt, text: str) -> dict:
    return {"start_line": node.lineno, "end_line": node.end_lineno,
            "exact_source_segment": ast.get_source_segment(text, node), "ast": ast.dump(node, include_attributes=False)}


def derive_contract(controller: bytes, helper: bytes) -> dict:
    _identity(controller, CONTROLLER_BYTES, CONTROLLER_SHA)
    _identity(helper, HELPER_BYTES, HELPER_SHA)
    text = controller.decode("utf-8")
    tree = ast.parse(text)  # AST only: no executable code object is produced.
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "CarController")
    methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
    nodes = {n.lineno: n for n in methods["update"].body}
    ordered = [("limiter", nodes[71]), ("fault", nodes[74]),
               ("inactive_gate", nodes[78]), ("previous_applied_update", nodes[81])]
    thresholds = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in {"MAX_ANGLE", "MAX_ANGLE_FRAMES", "MAX_ANGLE_CONSECUTIVE_FRAMES"}:
                if not isinstance(node.value, ast.Constant) or type(node.value.value) is not int:
                    raise ContractIdentityError("LITERAL_THRESHOLD_REQUIRED")
                thresholds[name] = dict(_record(node, text), value=node.value.value)
    initializers = {}
    for node in methods["__init__"].body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = ast.unparse(node.targets[0])
            if target in {"self.apply_torque_last", "self.angle_limit_counter"}:
                if not isinstance(node.value, ast.Constant):
                    raise ContractIdentityError("LITERAL_INITIAL_STATE_REQUIRED")
                initializers[target] = dict(_record(node, text), value=node.value.value)
    records = [dict(_record(node, text), role=role) for role, node in ordered]
    return {"schema_version": 1, "contract_id": "F70UGZ_R3_SELECTED_LATERAL_FLOW_V1",
            "controller_source": {"filename": "opendbc_repo/opendbc/car/hyundai/carcontroller.py", "sha256": CONTROLLER_SHA, "bytes": CONTROLLER_BYTES},
            "helper_source": {"filename": "opendbc_repo/opendbc/car/lateral.py", "sha256": HELPER_SHA, "bytes": HELPER_BYTES},
            "order": [role for role, _ in ordered], "ordered_records": records,
            "thresholds": thresholds, "initializers": initializers,
            "previous_applied_binding": "self.apply_torque_last <- final post-inactive apply_torque",
            "previous_requested_binding": "MODEL_BOOKKEEPING_ONLY",
            "integer_request_stage": "ALREADY_CONVERTED; caller line70 NOT_EXECUTED",
            "model_index_semantics": "INVOCATION_BOOKKEEPING_NOT_FRAME_OR_TIME",
            "elapsed_time_used_by_selected_nodes": any(isinstance(n, ast.Name) and n.id == "now_nanos" for _, node in ordered for n in ast.walk(node)),
            "controller_executable_code_compilations": 0, "controller_execution": 0,
            "claim": "selected source-order development model only, not whole Controller/runtime/CAN equivalence"}
