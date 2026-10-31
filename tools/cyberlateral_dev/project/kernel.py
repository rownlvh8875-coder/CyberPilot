"""Only two exact source definitions execute; whole original module never imports.

This is an execution boundary for known trusted hash-pinned code, not a general
Python security sandbox. The np binding is deliberately controlled and recorded.
"""
import ast
import hashlib
import types
from typing import Any

import numpy as np
from domain import (
    DomainError,
    FaultCase,
    LimiterCase,
    Limits,
    validate_fault,
    validate_limiter,
)

SOURCE_SHA = "94cf2dde92b43590b1d1e5b2a37b3d295e5f2cf9700ca43e3846bcb1c3ef36b6"
SOURCE_BYTES = 9367
SYMBOLS = {"apply_driver_steer_torque_limits": (70, 90), "common_fault_avoidance": (174, 195)}


class SourceIdentityError(ValueError):
    """No AST parsing/compilation allowed for unmatched original source bytes."""


def scalar_record(value) -> dict:
    kind = {int: "python.int", float: "python.float", np.int64: "numpy.int64", np.float64: "numpy.float64"}.get(type(value))
    if kind is None:
        raise TypeError("UNSUPPORTED_TRACE_SCALAR")
    return {"kind": kind, "value": float(value).hex() if "float" in kind else int(value)}


class _ClipProbe:
    def __init__(self):
        self.records = []

    def clip(self, value, lower, upper):
        result = np.clip(value, lower, upper)
        self.records.append({"x": scalar_record(value), "lower": scalar_record(lower),
                             "upper": scalar_record(upper), "result": scalar_record(result)})
        return result


class _LimitsProxy:
    def __init__(self, limits: Limits):
        self._limits = limits
        self.reads = []

    def __getattr__(self, name):
        self.reads.append(name)
        return getattr(self._limits, name)


class Kernel:
    def __init__(self, source: bytes):
        if type(source) is not bytes or len(source) != SOURCE_BYTES or hashlib.sha256(source).hexdigest() != SOURCE_SHA:
            raise SourceIdentityError("EXACT_SOURCE_BYTES_REQUIRED")
        if np.__version__ != "2.5.3" or np.dtype(int).itemsize != 8:
            raise RuntimeError("PINNED_NUMPY_SCALAR_ABI_REQUIRED")
        parsed = ast.parse(source, filename="pinned_lateral.py", mode="exec")
        selected = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name in SYMBOLS]
        if len(selected) != 2 or any((node.lineno, node.end_lineno) != SYMBOLS[node.name] or node.decorator_list for node in selected):
            raise SourceIdentityError("PINNED_SYMBOL_LOCATIONS_REQUIRED")
        self._globals: dict[str, Any] = {"__builtins__": {"int": int, "float": float, "bool": bool,
                                         "max": max, "min": min, "round": round},
                         "__name__": "isolated_selected_helpers", "np": np}
        body: list[ast.stmt] = list(selected)
        compiled = compile(ast.Module(body=body, type_ignores=[]), "pinned_lateral.py", "exec")
        exec(compiled, self._globals)  # noqa: S102 — authorized exact-identity definitions only.
        self._functions: dict[str, types.FunctionType] = {}
        for name in SYMBOLS:
            function = self._globals[name]
            if not isinstance(function, types.FunctionType):
                raise SourceIdentityError("FUNCTION_DEFINITION_REQUIRED")
            self._functions[name] = function
        self._counts = {"compile_calls": 1, "selected_definitions_compiled": 2,
                        "limiter_direct": 0, "limiter_traced": 0, "fault_explicit": 0,
                        "fault_default": 0, "traced_clip_calls": 0}

    @property
    def counts(self) -> dict:
        return dict(self._counts)

    def limiter(self, case: LimiterCase, *, traced: bool) -> dict:
        validate_limiter(case)
        if type(traced) is not bool:
            raise DomainError("EXPLICIT_TRACE_MODE_REQUIRED")
        probe = _ClipProbe() if traced else None
        namespace = dict(self._globals, np=probe if traced else np)
        original = self._functions["apply_driver_steer_torque_limits"]
        function = types.FunctionType(original.__code__, namespace, original.__name__, original.__defaults__)
        context = _LimitsProxy(case.limits)
        self._counts["limiter_traced" if traced else "limiter_direct"] += 1
        result = function(case.requested, case.previous, case.driver, context, case.override)
        if type(result) is not int:
            raise TypeError("BUILTIN_INT_OUTPUT_REQUIRED")
        clips = probe.records if probe is not None else []
        self._counts["traced_clip_calls"] += len(clips)
        return {"result": result, "clips": clips, "reads": context.reads}

    def fault(self, case: FaultCase, *, use_default: bool = False) -> tuple[int, bool]:
        validate_fault(case)
        if type(use_default) is not bool or (use_default and case.mismatch != 1):
            raise DomainError("FAULT_DEFAULT_MUST_EQUAL_ONE")
        function = self._functions["common_fault_avoidance"]
        args = (case.condition, case.request, case.counter, case.maximum)
        self._counts["fault_default" if use_default else "fault_explicit"] += 1
        result = function(*args) if use_default else function(*args, case.mismatch)
        if type(result) is not tuple or len(result) != 2 or type(result[0]) is not int or type(result[1]) is not bool:
            raise TypeError("EXACT_FAULT_OUTPUT_REQUIRED")
        return result
