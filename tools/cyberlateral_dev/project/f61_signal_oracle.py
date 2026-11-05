"""Independent integer/IEEE oracle; no Fraction or reference validator/import."""

import math
import struct
import sys
from typing import Any, cast

from integration_tools import f61_signal_contract_v4 as c


def _error(reason):
    result = dict.fromkeys(('f61_input', 'conversion_trace', 'source_binding', 'state_binding', 'time_binding', 'precision_binding'))
    result.update(accepted=False, rejection_code=reason, calculator_invocation_allowed=False)
    return result


def _shape(value, required):
    if type(value) is not dict:
        return False
    if any(type(key) is not str for key in value):
        return False
    return len(value) == len(required) and all(key in value for key in required)


def _binary_parts(numerator):
    shift = (numerator & -numerator).bit_length() - 1
    return numerator >> shift, shift


def _is_binary32(value):
    if type(value) is not float:
        return False
    bits = int.from_bytes(struct.pack('>d', value), 'big')
    exponent = (bits >> 52) & 0x7FF
    fraction = bits & ((1 << 52) - 1)
    if exponent == 0x7FF or value < -1 or value > 1:
        return False
    if exponent == 0 and fraction == 0:
        return True
    mantissa = fraction | ((1 << 52) if exponent else 0)
    power = exponent - 1023 - 52 if exponent else -1074
    odd, shift = _binary_parts(mantissa)
    power += shift
    return odd.bit_length() <= 24 and power >= -149 and power + odd.bit_length() - 1 <= 127


def _seconds(delta):
    divisor = math.gcd(delta, 1_000_000_000)
    numerator, denominator = delta // divisor, 1_000_000_000 // divisor
    if denominator & (denominator - 1):
        return None
    odd, shift = _binary_parts(numerator)
    power = shift - (denominator.bit_length() - 1)
    length = odd.bit_length()
    top = power + length - 1
    if length > 53 or power < -1074 or top > 1023:
        return None
    if top >= -1022:
        mantissa = odd << (53 - length)
        bits = ((top + 1023) << 52) | (mantissa - (1 << 52))
    else:
        bits = odd << (power + 1074)
    return struct.unpack('>d', bits.to_bytes(8, 'big'))[0]


def oracle(payload: object) -> dict:
    if type(payload) is not dict or not all(type(key) is str for key in payload):
        return _error('SCHEMA_INVALID')
    payload = cast(dict[str, Any], payload)
    ctx = payload.get('static_context_reference')
    has_vehicle = type(ctx) is dict and ctx.get('vehicle_context') is not None
    actual_mode = type(payload.get('mode')) is str and payload['mode'] == 'ACTUAL_PRODUCTION'
    if has_vehicle or actual_mode:
        passed = type(ctx) is dict and type(ctx.get('actual_vehicle_gate')) is str and ctx['actual_vehicle_gate'] == 'PASS'
        return _error('ACTUAL_PRODUCTION_PROHIBITED' if passed else 'STATIC_EVIDENCE_GATE_FAIL')
    if 'rate_budget_per_s' in payload:
        return _error('RATE_BUDGET_NOT_AN_ADAPTER_INPUT')
    if payload.get('current_production_value') is None:
        return _error('MISSING_CURRENT_SAMPLE')
    if payload.get('previous_production_state') is None:
        return _error('MISSING_PREVIOUS_SAMPLE')
    if payload.get('previous_sample_time_ns') is None or payload.get('current_sample_time_ns') is None:
        return _error('MISSING_SAMPLE_TIME')
    if not _shape(payload, c.TOP_KEYS):
        return _error('SCHEMA_INVALID')
    now = payload['current_production_value']
    old = payload['previous_production_state']
    identity = payload['source_identity']
    for record, keys in ((now, c.SNAPSHOT_KEYS), (old, c.SNAPSHOT_KEYS), (identity, c.SOURCE_KEYS), (ctx, c.CONTEXT_KEYS)):
        if not _shape(record, keys):
            return _error('SCHEMA_INVALID')
    ctx = cast(dict[str, Any], ctx)
    if type(payload['schema_version']) is not int or payload['schema_version'] != 4:
        return _error('SCHEMA_INVALID')
    if type(payload['contract_id']) is not str or payload['contract_id'] != c.CONTRACT_ID:
        return _error('SCHEMA_INVALID')
    if type(payload['mode']) is not str or type(payload['reset_between_samples']) is not bool:
        return _error('SCHEMA_INVALID')
    if type(payload['current_sample_time_ns']) is not int or type(payload['previous_sample_time_ns']) is not int:
        return _error('SCHEMA_INVALID')
    for record in (now, old):
        for key in c.SNAPSHOT_KEYS:
            if key not in ('value', 'sequence', 'active', 'override') and (type(record[key]) is not str or len(record[key]) == 0):
                return _error('SCHEMA_INVALID')
        if type(record['active']) is not bool or type(record['override']) is not bool:
            return _error('SCHEMA_INVALID')
    for key in c.SOURCE_KEYS:
        if type(identity[key]) is not str or len(identity[key]) == 0:
            return _error('SCHEMA_INVALID')
    for key in ('kind', 'fixture_id', 'actual_vehicle_gate'):
        if type(ctx[key]) is not str or not ctx[key]:
            return _error('SCHEMA_INVALID')
    if (payload['mode'], ctx['kind'], ctx['actual_vehicle_gate']) != ('SYNTHETIC_REFERENCE_ONLY', c.FIXTURE, 'FAIL'):
        return _error('SYNTHETIC_FIXTURE_REQUIRED')
    for key, expected in [
        ('production_repository', 'ajouatom/openpilot'),
        ('controller_path', c.CONTROLLER_PATH),
        ('controller_symbol', c.CONTROLLER_SYMBOL),
        ('f61_source_sha256', c.F61_SHA),
    ]:
        if identity[key] != expected:
            return _error('UNSUPPORTED_SOURCE')
    if any(value not in c.COMMITS for value in (identity['production_commit'], now['source_commit'], old['source_commit'])):
        return _error('UNSUPPORTED_SOURCE')
    for key, allowed, rejection in [
        ('stage_id', (c.STAGE,), 'UNSUPPORTED_STAGE'),
        ('control_mode', ('TORQUE_CONTROL',), 'UNSUPPORTED_CONTROL_MODE'),
        ('time_source', (c.TIME_SOURCE,), 'UNSUPPORTED_SAMPLE_TIME_SOURCE'),
        ('clock_domain', c.DOMAINS, 'UNSUPPORTED_CLOCK_DOMAIN'),
        ('provenance', (c.FIXTURE,), 'SYNTHETIC_FIXTURE_REQUIRED'),
    ]:
        if now[key] not in allowed or old[key] not in allowed:
            return _error(rejection)
    if now['source_commit'] != identity['production_commit'] or any(
        now[key] != old[key] for key in ('source_commit', 'epoch_id', 'clock_domain', 'stage_id', 'control_mode')
    ):
        return _error('CONTEXT_MISMATCH')
    for record in (old, now):
        sequence = record['sequence']
        if type(sequence) is not int or sequence < 0 or sequence > 0xFFFFFFFFFFFFFFFF:
            return _error('INVALID_SEQUENCE')
    if now['sequence'] - old['sequence'] != 1:
        return _error('INVALID_SEQUENCE')
    for record in (now, old):
        if record['dtype'] != 'IEEE754_BINARY32' or record['unit'] != 'normalized_command' or not _is_binary32(record['value']):
            return _error('INVALID_NATIVE_VALUE')
    t1, t0 = payload['current_sample_time_ns'], payload['previous_sample_time_ns']
    delta = t1 - t0
    if delta <= 0:
        return _error('TIME_ORDER')
    if sys.float_info.radix != 2 or sys.float_info.mant_dig != 53 or sys.float_info.max_exp != 1024:
        return _error('UNSUPPORTED_NUMERIC_PLATFORM')
    seconds = _seconds(delta)
    if seconds is None:
        return _error('TIME_NOT_EXACTLY_REPRESENTABLE')
    projection = {
        'projection_kind': c.PROJECTION_KIND,
        'current_native': now['value'],
        'previous_native_if_required': old['value'],
        'previous_time': 0.0,
        'current_time': seconds,
        'dt': seconds,
    }
    trace = {
        'contract_id': c.CONTRACT_ID,
        'current_native_hex': float.hex(now['value']),
        'previous_native_hex': float.hex(old['value']),
        'current_sample_time_ns_hex': hex(t1),
        'previous_sample_time_ns_hex': hex(t0),
        'epoch_ns_hex': hex(t0),
        'delta_ns_hex': hex(delta),
        'seconds_hex': float.hex(seconds),
        'scale': 1,
        'offset': 0,
        'rounding': 'NONE',
        'clipping': 'NONE',
    }
    source = {
        'repository': identity['production_repository'],
        'commit': identity['production_commit'],
        'stage': c.STAGE,
        'F61_source_sha256': c.F61_SHA,
        'authority': 'USER_APPROVED_SYNTHETIC_DESIGN',
    }
    state = {
        'previous_role': 'PREVIOUS_REQUEST_NOT_APPLIED_COMMAND',
        'previous_sequence': old['sequence'],
        'current_sequence': now['sequence'],
        'previous_active': old['active'],
        'current_active': now['active'],
        'previous_override': old['override'],
        'current_override': now['override'],
        'reset_between_samples': payload['reset_between_samples'],
    }
    timing = {
        'clock_domain': now['clock_domain'],
        'epoch_id': now['epoch_id'],
        'source': c.TIME_SOURCE,
        'global_F61_time_coordinate': False,
        'actual_acquisition_or_ECU_time_verified': False,
    }
    precision = {'native': 'EXACT_BINARY32_TO_BINARY64_EMBEDDING', 'native_rounding': 'NONE', 'clipping': 'NONE', 'time': 'EXACT_SUBSET_PAIR_LOCAL_SECONDS'}
    return {
        'accepted': True,
        'rejection_code': None,
        'f61_input': projection,
        'conversion_trace': trace,
        'source_binding': source,
        'state_binding': state,
        'time_binding': timing,
        'precision_binding': precision,
        'calculator_invocation_allowed': False,
    }
