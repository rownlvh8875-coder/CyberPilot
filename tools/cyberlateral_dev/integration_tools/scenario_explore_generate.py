"""Finite, deterministic declared-synthetic R31 generation; no model work."""

import hashlib
import math

from .scenario_input import parse_scenario
from .scenario_output import canonical

GENERATOR_ID = 'R42_DETERMINISTIC_BOUNDARY_GENERATOR_V1'


class ExplorationError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _parameters(seed: int, cases: int, steps: int) -> None:
    if (any(type(v) is not int for v in [seed, cases, steps]) or not 0 <= seed < 2**32
            or not 1 <= cases <= 16 or not 16 <= steps <= 256):
        raise ExplorationError('EXPLORATION_PARAMETERS')


def _pick(values: tuple, seed: int, case: int, offset: int, channel: str):
    key = f'{GENERATOR_ID}:{seed}:{case}:{offset}:{channel}'.encode('ascii')
    index = int.from_bytes(hashlib.sha256(key).digest()[:8], 'big') % len(values)
    return values[index]


def _case(seed: int, number: int, steps: int) -> bytes:
    scale = (16, 8, 32, 5)[number % 4]
    limits = {'STEER_MAX': scale, 'STEER_DELTA_UP': 0 if number % 4 == 2 else 2, 'STEER_DELTA_DOWN': 5,
              'STEER_DRIVER_ALLOWANCE': 0, 'STEER_DRIVER_FACTOR': 1, 'STEER_DRIVER_MULTIPLIER': 1}
    state = {'index': 0, 'previous_requested': None, 'previous_applied': 0, 'angle_counter': 0} if number == 0 else {
        'index': 5, 'previous_requested': 4, 'previous_applied': -3, 'angle_counter': 88 + (number - 1) % 3}
    half = 0.5 / scale
    requests = (1.0, -1.0, half, 1.5 / scale, math.nextafter(half, 0.0), math.nextafter(half, 1.0),
                -half, -1.5 / scale, -0.0, 0.0, 1.0, -1.0, 1.0, -1.0, 0.5, -0.5)
    drivers = (0.0, 0.0, 20.5, -20.5, 0.0, 0.0, -20.5, 20.5, 0.0, 0.0,
               _pick((0.25, -0.25, 20.5, -20.5), seed, number, 10, 'driver'),
               _pick((0.25, -0.25, 20.5, -20.5), seed, number, 11, 'driver'), 20.5, -20.5, 0.25, -0.25)
    angles = (90.0, 90.0, 90.0, 84.99609375, 85.0, -85.0, -90.0, 0.0, 90.0, -90.0,
              85.00390625, -85.00390625, 0.0, 90.0, -90.0, 0.0)
    samples = []
    for offset in range(steps):
        if offset < 16:
            request, driver, angle, active = requests[offset], drivers[offset], angles[offset], offset not in {8, 12}
        else:
            request = _pick(requests, seed, number, offset, 'request')
            driver = _pick((0.0, 0.25, -0.25, 20.5, -20.5, 1024.0, -1024.0), seed, number, offset, 'driver')
            angle = _pick(angles + (180.0, -180.0), seed, number, offset, 'angle')
            active = _pick((True, True, True, False), seed, number, offset, 'active')
        samples.append({'index': state['index'] + offset, 'request': request, 'driver': driver,
                        'angle_deg': angle, 'lat_active': active})
    raw = canonical({'schema_version': 1, 'scope': 'SYNTHETIC_ONLY', 'scenario_id': f'R42_{seed}_{number + 1}',
                     'limits': limits, 'initial_state': state, 'samples': samples})
    parse_scenario(raw)
    return raw


def generate_cases(seed: int, cases: int, steps: int) -> dict[str, bytes]:
    _parameters(seed, cases, steps)
    return {f'case-{number + 1:03d}.json': _case(seed, number, steps) for number in range(cases)}


def generation_record(seed: int, cases: int, steps: int, payloads: dict[str, bytes]) -> dict:
    _parameters(seed, cases, steps)
    if (type(payloads) is not dict or any(type(k) is not str or type(v) is not bytes for k, v in payloads.items())
            or payloads != generate_cases(seed, cases, steps)):
        raise ExplorationError('EXPLORATION_GENERATION_MISMATCH')
    rows = []
    for name, raw in payloads.items():
        spec = parse_scenario(raw)
        samples = spec.samples
        counts = {'positive_requests': sum(s.request > 0 for s in samples),
                  'negative_requests': sum(s.request < 0 for s in samples),
                  'zero_requests': sum(s.request == 0 for s in samples),
                  'negative_zero_requests': sum(s.request == 0 and math.copysign(1.0, s.request) < 0 for s in samples),
                  'request_sign_transitions': sum(a.request * b.request < 0 for a, b in zip(samples, samples[1:], strict=False)),
                  'fractional_drivers': sum(not s.driver.is_integer() for s in samples),
                  'inactive_samples': sum(not s.lat_active for s in samples),
                  'high_angle_samples': sum(abs(s.angle_deg) >= 85.0 for s in samples),
                  'resumed_cases': int(spec.initial_state.index != 0)}
        rows.append({'file': name, 'input_sha256': spec.raw_sha256, 'scenario_id': spec.scenario_id,
                     'profile': 'SYNTHETIC_SCALE_' + str(spec.limits.STEER_MAX), 'sample_count': len(samples),
                     'initial_state_kind': 'DECLARED_RESUMED_SYNTHETIC' if spec.initial_state.index else 'DECLARED_CANONICAL_SYNTHETIC',
                     'input_feature_counts': counts})
    totals = {key: sum(row['input_feature_counts'][key] for row in rows) for key in rows[0]['input_feature_counts']}
    return {'schema_version': 1, 'generator_id': GENERATOR_ID, 'parameters': {'seed': seed, 'cases': cases, 'steps': steps},
            'selection_algorithm': 'SHA256_FIRST8_BIG_ENDIAN_MOD_CATALOG_SIZE',
            'selection_key': '<generator_id>:<seed>:<zero_based_case>:<offset>:<channel>',
            'generated_samples': cases * steps, 'input_feature_counts': totals, 'cases': rows,
            'coverage_claim': 'INPUT_FEATURE_COUNTS_NOT_EXHAUSTIVE_BRANCH_COVERAGE',
            'state_scope': 'DECLARED_SYNTHETIC_INITIAL_STATE_NOT_OBSERVED_PREHISTORY',
            'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME',
            'normalization_authority': 'SYNTHETIC_STRESS_PARAMETERS_NOT_VEHICLE_SCALE_OR_RATE_POLICY'}
