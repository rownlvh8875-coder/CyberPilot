"""Original line70 is syntax/data authority; builtin types are model assumptions."""
import ast

from source_contract import derive_contract


def derive_quantization_contract(controller: bytes, helper: bytes) -> dict:
    base = derive_contract(controller, helper)  # Both identities checked before AST.
    text = controller.decode("utf-8")
    tree = ast.parse(text)
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and n.lineno == 70)
    return {"schema_version": 1, "contract_id": "F70UGZ_R4_SYNTHETIC_QUANTIZATION_V1",
            "base_integer_state_contract": base,
            "quantization_record": {"start_line": node.lineno, "end_line": node.end_lineno,
                                    "source_sha256": base["controller_source"]["sha256"],
                                    "symbol": "CarController.update:new_torque",
                                    "exact_source_segment": ast.get_source_segment(text, node),
                                    "ast": ast.dump(node, include_attributes=False), "expression": ast.unparse(node.value)},
            "operation_order": ["binary64_product", "round_to_integer_ties_even", "int"],
            "operation_order_scope": "DECLARED_SYNTHETIC_BUILTIN_FLOAT_AND_INT_TYPES_ONLY",
            "source_authority": "expression syntax/order and params.STEER_MAX relation, NOT actual operand/accessor dtype",
            "synthetic_q": {"type": "exact builtins.float", "finite": True, "range": [-1, 1], "format": "binary64"},
            "synthetic_scale": {"type": "exact builtins.int", "range": [1, 2048],
                                "binding": "same immutable sample.limits.STEER_MAX consumed by downstream limiter", "fallback": "NONE"},
            "clamp": "NONE; out-of-domain synthetic inputs reject",
            "actual_actuator_dtype": "NOT_ESTABLISHED", "actual_vehicle_scale": None,
            "wire_Float32_ABI": "NOT_ESTABLISHED", "mutable_production_params_snapshot": "NOT_PROVEN",
            "original_caller_execution": 0, "original_controller_executable_compilation": 0,
            "new_quantizer_execution": "ALLOWED_SYNTHETIC_ONLY", "F61_API_change": "NONE"}
