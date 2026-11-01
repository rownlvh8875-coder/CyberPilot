"""Bounded V1 declared-synthetic JSON preflight. No model imports or work."""

import hashlib
import json
import math
import os
import re
import stat
from dataclasses import dataclass, fields
from pathlib import Path

MAX_BYTES = 1048576
ROOT_KEYS = {'schema_version', 'scope', 'scenario_id', 'limits', 'initial_state', 'samples'}


class ScenarioError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class LimitsSpec:
    STEER_MAX: int
    STEER_DELTA_UP: int
    STEER_DELTA_DOWN: int
    STEER_DRIVER_ALLOWANCE: int
    STEER_DRIVER_FACTOR: int
    STEER_DRIVER_MULTIPLIER: int


@dataclass(frozen=True, slots=True)
class StateSpec:
    index: int
    previous_requested: int | None
    previous_applied: int
    angle_counter: int


@dataclass(frozen=True, slots=True)
class SampleSpec:
    index: int
    request: float
    driver: float
    angle_deg: float
    lat_active: bool


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    scenario_id: str
    limits: LimitsSpec
    initial_state: StateSpec
    samples: tuple[SampleSpec, ...]
    raw_sha256: str


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ScenarioError(code)


def _integer(value, low: int, high: int, code: str) -> None:
    _require(type(value) is int and low <= value <= high, code)


def _floating(value, bound: float, dyadic: bool = False) -> None:
    _require(type(value) is float and math.isfinite(value) and -bound <= value <= bound, 'SCENARIO_DOMAIN')
    if dyadic:
        _require(value.as_integer_ratio()[1] <= 256, 'SCENARIO_DOMAIN')


def _keys(value, names: set[str]) -> None:
    _require(type(value) is dict and value.keys() == names, 'SCENARIO_KEYS')


def validate_spec(spec: ScenarioSpec) -> None:
    """Revalidate even caller-created records, without running model arithmetic."""
    _require(type(spec) is ScenarioSpec, 'SCENARIO_SCHEMA')
    _require(type(spec.scenario_id) is str and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', spec.scenario_id) is not None, 'SCENARIO_ID')
    _require(type(spec.raw_sha256) is str and re.fullmatch(r'[0-9a-f]{64}', spec.raw_sha256) is not None, 'SCENARIO_SCHEMA')
    _require(type(spec.limits) is LimitsSpec, 'SCENARIO_DOMAIN')
    for field in fields(LimitsSpec):
        low, high = (1, 2048) if field.name == 'STEER_MAX' else (0, 8 if field.name in {'STEER_DRIVER_FACTOR', 'STEER_DRIVER_MULTIPLIER'} else 64)
        _integer(getattr(spec.limits, field.name), low, high, 'SCENARIO_DOMAIN')
    state = spec.initial_state
    _require(type(state) is StateSpec, 'SCENARIO_STATE')
    _integer(state.index, 0, 4095, 'SCENARIO_STATE')
    _integer(state.previous_applied, -2048, 2048, 'SCENARIO_STATE')
    _integer(state.angle_counter, 0, 90, 'SCENARIO_STATE')
    if state.index == 0:
        _require(state.previous_requested is None and state.previous_applied == 0 and state.angle_counter == 0, 'SCENARIO_STATE')
    else:
        _integer(state.previous_requested, -2048, 2048, 'SCENARIO_STATE')
    _require(type(spec.samples) is tuple and 1 <= len(spec.samples) <= 4096, 'SCENARIO_COUNT')
    for offset, sample in enumerate(spec.samples):
        _require(type(sample) is SampleSpec, 'SCENARIO_DOMAIN')
        _integer(sample.index, 0, 4095, 'SCENARIO_ORDER')
        _require(sample.index == state.index + offset, 'SCENARIO_ORDER')
        _floating(sample.request, 1.0)
        _floating(sample.driver, 1024.0, True)
        _floating(sample.angle_deg, 180.0, True)
        _require(type(sample.lat_active) is bool, 'SCENARIO_DOMAIN')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'SCENARIO_JSON')
        result[key] = value
    return result


def _float_token(token: str) -> float:
    _require(len(token) <= 128, 'SCENARIO_JSON')
    value = float(token)
    _require(math.isfinite(value), 'SCENARIO_JSON')
    return value


def _int_token(token: str) -> int:
    _require(len(token) <= 32, 'SCENARIO_JSON')
    return int(token)


def _constant(_token):
    raise ScenarioError('SCENARIO_JSON')


def _depth_bound(raw: bytes) -> None:
    # Resource cap independent of an embedding caller's sys.setrecursionlimit.
    depth, quoted, escaped = 0, False, False
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            _require(depth <= 64, 'SCENARIO_JSON')
        elif byte in (93, 125):
            depth -= 1


def parse_scenario(raw: bytes) -> ScenarioSpec:
    _require(type(raw) is bytes, 'SCENARIO_JSON')
    _require(len(raw) <= MAX_BYTES, 'SCENARIO_SIZE')
    _depth_bound(raw)
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs, parse_float=_float_token,
                           parse_int=_int_token, parse_constant=_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ScenarioError('SCENARIO_JSON') from error
    _keys(value, ROOT_KEYS)
    _require(type(value['schema_version']) is int and value['schema_version'] == 1, 'SCENARIO_SCHEMA')
    _require(type(value['scope']) is str and value['scope'] == 'SYNTHETIC_ONLY', 'SCENARIO_SCOPE')
    for key, cls in [('limits', LimitsSpec), ('initial_state', StateSpec)]:
        _keys(value[key], {field.name for field in fields(cls)})
    _require(type(value['samples']) is list and 1 <= len(value['samples']) <= 4096, 'SCENARIO_COUNT')
    for sample in value['samples']:
        _keys(sample, {field.name for field in fields(SampleSpec)})
    spec = ScenarioSpec(value['scenario_id'], LimitsSpec(**value['limits']), StateSpec(**value['initial_state']),
                        tuple(SampleSpec(**sample) for sample in value['samples']), hashlib.sha256(raw).hexdigest())
    validate_spec(spec)
    return spec


def read_scenario(path: Path) -> ScenarioSpec:
    """Own one bounded byte snapshot; final symlinks and nonregular files reject."""
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        with os.fdopen(os.open(path, flags), 'rb') as stream:
            _require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'SCENARIO_INPUT_FILE')
            raw = stream.read(MAX_BYTES + 1)
    except (OSError, AttributeError) as error:
        raise ScenarioError('SCENARIO_INPUT_FILE') from error
    return parse_scenario(raw)
