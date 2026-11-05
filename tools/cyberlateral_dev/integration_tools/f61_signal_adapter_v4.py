"""Pure synthetic signal projection. Never build/invoke actual F61 requests."""

import math
import struct
import sys
from fractions import Fraction
from typing import Any, cast

from . import f61_signal_contract_v4 as c


def _reject(code):
    return {
        'accepted': False,
        'rejection_code': code,
        'f61_input': None,
        'conversion_trace': None,
        'source_binding': None,
        'state_binding': None,
        'time_binding': None,
        'precision_binding': None,
        'calculator_invocation_allowed': False,
    }


def _closed(value, keys):
    return type(value) is dict and all(type(k) is str for k in value) and set(value) == set(keys)


def adapt(payload: object) -> dict:
    if type(payload) is not dict or any(type(k) is not str for k in payload):
        return _reject('SCHEMA_INVALID')
    payload = cast(dict[str, Any], payload)
    context = payload.get('static_context_reference')
    actual = type(payload.get('mode')) is str and payload['mode'] == 'ACTUAL_PRODUCTION'
    vehicle = type(context) is dict and context.get('vehicle_context') is not None
    if actual or vehicle:
        gate_pass = type(context) is dict and type(context.get('actual_vehicle_gate')) is str and context['actual_vehicle_gate'] == 'PASS'
        return _reject('ACTUAL_PRODUCTION_PROHIBITED' if gate_pass else 'STATIC_EVIDENCE_GATE_FAIL')
    if 'rate_budget_per_s' in payload:
        return _reject('RATE_BUDGET_NOT_AN_ADAPTER_INPUT')
    for name, code in [('current_production_value', 'MISSING_CURRENT_SAMPLE'), ('previous_production_state', 'MISSING_PREVIOUS_SAMPLE')]:
        if payload.get(name) is None:
            return _reject(code)
    if payload.get('current_sample_time_ns') is None or payload.get('previous_sample_time_ns') is None:
        return _reject('MISSING_SAMPLE_TIME')
    if not _closed(payload, c.TOP_KEYS):
        return _reject('SCHEMA_INVALID')
    current, previous, source = payload['current_production_value'], payload['previous_production_state'], payload['source_identity']
    if (
        not _closed(current, c.SNAPSHOT_KEYS)
        or not _closed(previous, c.SNAPSHOT_KEYS)
        or not _closed(source, c.SOURCE_KEYS)
        or not _closed(context, c.CONTEXT_KEYS)
    ):
        return _reject('SCHEMA_INVALID')
    context = cast(dict[str, Any], context)
    if (
        type(payload['schema_version']) is not int
        or payload['schema_version'] != 4
        or type(payload['contract_id']) is not str
        or payload['contract_id'] != c.CONTRACT_ID
    ):
        return _reject('SCHEMA_INVALID')
    if type(payload['mode']) is not str or type(payload['reset_between_samples']) is not bool:
        return _reject('SCHEMA_INVALID')
    if any(type(payload[key]) is not int for key in ('current_sample_time_ns', 'previous_sample_time_ns')):
        return _reject('SCHEMA_INVALID')
    strings = set(c.SNAPSHOT_KEYS) - {'value', 'sequence', 'active', 'override'}
    for sample in (current, previous):
        if (
            any(type(sample[key]) is not str or not sample[key] for key in strings)
            or type(sample['active']) is not bool
            or type(sample['override']) is not bool
        ):
            return _reject('SCHEMA_INVALID')
    if any(type(source[key]) is not str or not source[key] for key in c.SOURCE_KEYS):
        return _reject('SCHEMA_INVALID')
    if any(type(context[key]) is not str or not context[key] for key in ('kind', 'fixture_id', 'actual_vehicle_gate')):
        return _reject('SCHEMA_INVALID')
    if payload['mode'] != 'SYNTHETIC_REFERENCE_ONLY' or context['kind'] != c.FIXTURE or context['actual_vehicle_gate'] != 'FAIL':
        return _reject('SYNTHETIC_FIXTURE_REQUIRED')
    expected = {
        'production_repository': 'ajouatom/openpilot',
        'controller_path': c.CONTROLLER_PATH,
        'controller_symbol': c.CONTROLLER_SYMBOL,
        'f61_source_sha256': c.F61_SHA,
    }
    if (
        any(source[key] != value for key, value in expected.items())
        or source['production_commit'] not in c.COMMITS
        or any(s['source_commit'] not in c.COMMITS for s in (current, previous))
    ):
        return _reject('UNSUPPORTED_SOURCE')
    if any(s['stage_id'] != c.STAGE for s in (current, previous)):
        return _reject('UNSUPPORTED_STAGE')
    if any(s['control_mode'] != 'TORQUE_CONTROL' for s in (current, previous)):
        return _reject('UNSUPPORTED_CONTROL_MODE')
    if any(s['time_source'] != c.TIME_SOURCE for s in (current, previous)):
        return _reject('UNSUPPORTED_SAMPLE_TIME_SOURCE')
    if any(s['clock_domain'] not in c.DOMAINS for s in (current, previous)):
        return _reject('UNSUPPORTED_CLOCK_DOMAIN')
    if any(s['provenance'] != c.FIXTURE for s in (current, previous)):
        return _reject('SYNTHETIC_FIXTURE_REQUIRED')
    if (
        any(current[key] != previous[key] for key in ('source_commit', 'epoch_id', 'clock_domain', 'stage_id', 'control_mode'))
        or current['source_commit'] != source['production_commit']
    ):
        return _reject('CONTEXT_MISMATCH')
    if (
        any(type(s['sequence']) is not int or not 0 <= s['sequence'] < (1 << 64) for s in (current, previous))
        or current['sequence'] != previous['sequence'] + 1
    ):
        return _reject('INVALID_SEQUENCE')
    for sample in (current, previous):
        value = sample['value']
        if (
            sample['dtype'] != 'IEEE754_BINARY32'
            or sample['unit'] != 'normalized_command'
            or type(value) is not float
            or not math.isfinite(value)
            or not -1 <= value <= 1
        ):
            return _reject('INVALID_NATIVE_VALUE')
        if struct.unpack('>f', struct.pack('>f', value))[0] != value:
            return _reject('INVALID_NATIVE_VALUE')
    now, before = payload['current_sample_time_ns'], payload['previous_sample_time_ns']
    if now <= before:
        return _reject('TIME_ORDER')
    if (sys.float_info.radix, sys.float_info.mant_dig, sys.float_info.max_exp) != (2, 53, 1024):
        return _reject('UNSUPPORTED_NUMERIC_PLATFORM')
    interval = Fraction(now - before, 1_000_000_000)
    try:
        seconds = float(interval)
    except OverflowError:
        return _reject('TIME_NOT_EXACTLY_REPRESENTABLE')
    if not math.isfinite(seconds) or seconds <= 0 or Fraction(seconds) != interval:
        return _reject('TIME_NOT_EXACTLY_REPRESENTABLE')
    return {
        'accepted': True,
        'rejection_code': None,
        'calculator_invocation_allowed': False,
        'f61_input': {
            'projection_kind': c.PROJECTION_KIND,
            'current_native': current['value'],
            'previous_native_if_required': previous['value'],
            'previous_time': 0.0,
            'current_time': seconds,
            'dt': seconds,
        },
        'conversion_trace': {
            'contract_id': c.CONTRACT_ID,
            'current_native_hex': current['value'].hex(),
            'previous_native_hex': previous['value'].hex(),
            'current_sample_time_ns_hex': hex(now),
            'previous_sample_time_ns_hex': hex(before),
            'epoch_ns_hex': hex(before),
            'delta_ns_hex': hex(now - before),
            'seconds_hex': seconds.hex(),
            'scale': 1,
            'offset': 0,
            'rounding': 'NONE',
            'clipping': 'NONE',
        },
        'source_binding': {
            'repository': source['production_repository'],
            'commit': source['production_commit'],
            'stage': c.STAGE,
            'F61_source_sha256': c.F61_SHA,
            'authority': 'USER_APPROVED_SYNTHETIC_DESIGN',
        },
        'state_binding': {
            'previous_role': 'PREVIOUS_REQUEST_NOT_APPLIED_COMMAND',
            'previous_sequence': previous['sequence'],
            'current_sequence': current['sequence'],
            'previous_active': previous['active'],
            'current_active': current['active'],
            'previous_override': previous['override'],
            'current_override': current['override'],
            'reset_between_samples': payload['reset_between_samples'],
        },
        'time_binding': {
            'clock_domain': current['clock_domain'],
            'epoch_id': current['epoch_id'],
            'source': c.TIME_SOURCE,
            'global_F61_time_coordinate': False,
            'actual_acquisition_or_ECU_time_verified': False,
        },
        'precision_binding': {
            'native': 'EXACT_BINARY32_TO_BINARY64_EMBEDDING',
            'native_rounding': 'NONE',
            'clipping': 'NONE',
            'time': 'EXACT_SUBSET_PAIR_LOCAL_SECONDS',
        },
    }
