"""Independent selected-source states from validated primitive declarations only."""

from dataclasses import asdict
from math import isfinite
from typing import Any, cast

from domain import LimiterCase, Limits, validate_limiter
from flow_types import State
from normalized_reference import NormalizedReference
from quantization_types import NormalizedSample
from v1_helpers import ROOT


def _need(condition):
    if not condition:
        raise ValueError('DECLARED_REFERENCE_WIRE')


def _integer(value, low, high):
    return type(value) is int and low <= value <= high


def _float(value, bound, *, dyadic):
    _need(type(value) is str and 0 < len(value) <= 32)
    result = float.fromhex(value)
    _need(isfinite(result) and abs(result) <= bound and result.hex() == value)
    _need(not dyadic or result.as_integer_ratio()[1] <= 256)
    return result


def _row(row):
    _need(type(row) is dict and set(row) == {'state', 'request_hex', 'driver_hex', 'angle_hex', 'lat_active', 'limits', 'saved'})
    state, saved, limits = row['state'], row['saved'], row['limits']
    _need(type(state) is dict and set(state) == {'index', 'previous_requested', 'previous_applied', 'angle_counter'})
    _need(_integer(state['index'], 1, 4095) and _integer(state['angle_counter'], 0, 90)
          and all(_integer(state[k], -2048, 2048) for k in ('previous_requested', 'previous_applied')))
    _need(type(saved) is dict and set(saved) == {'saved_limited_state', 'saved_angle_counter'}
          and _integer(saved['saved_limited_state'], -2048, 2048) and _integer(saved['saved_angle_counter'], 0, 90))
    _need(type(row['lat_active']) is bool and (row['lat_active'] or saved['saved_limited_state'] == 0))
    _need(type(limits) is list and len(limits) == 6 and _integer(limits[0], 1, 2048)
          and all(type(x) is int for x in limits))
    settings = Limits(*limits)
    request = _float(row['request_hex'], 1, dyadic=False)
    driver = _float(row['driver_hex'], 1024, dyadic=True)
    angle = _float(row['angle_hex'], 180, dyadic=True)
    validate_limiter(LimiterCase(0, state['previous_applied'], driver, settings))
    return State(**state), NormalizedSample(state['index'], request, driver, angle, row['lat_active'], settings, 'SYNTHETIC_ONLY')


def reference_declared_states(payload: object) -> dict:
    """Validate all declarations first;each step gets its own declared entry state."""
    try:
        if type(payload) is not dict:
            raise ValueError('DECLARED_REFERENCE_WIRE')
        data = cast(dict[str, Any], payload)
        _need(set(data) == {'schema_version', 'scope', 'rows'})
        _need(type(data['schema_version']) is int and data['schema_version'] == 1
              and data['scope'] == 'CORE69_DECLARED_REFERENCE_INPUT_V1')
        rows = data['rows']
        _need(type(rows) is list and 1 <= len(rows) <= 127)
        prepared = [_row(row) for row in rows]
        for i in range(1, len(rows)):
            _need(rows[i]['state']['index'] == rows[i - 1]['state']['index'] + 1
                  and rows[i]['limits'] == rows[i - 1]['limits']
                  and rows[i]['state']['previous_applied'] == rows[i - 1]['saved']['saved_limited_state']
                  and rows[i]['state']['angle_counter'] == rows[i - 1]['saved']['saved_angle_counter'])
    except (ValueError, TypeError, KeyError, OverflowError):
        raise ValueError('DECLARED_REFERENCE_WIRE') from None
    reference = NormalizedReference((ROOT / 'reference/carcontroller.py').read_bytes(), (ROOT / 'reference/lateral.py').read_bytes())
    states = [asdict(reference.step(state, sample).downstream.next_state) for state, sample in prepared]
    return {'schema_version': 1, 'contract_id': 'CORE69_DECLARED_REFERENCE_STATES_V1',
            'states': states, 'reference_steps': len(states), 'helper_counts': reference.counts}
