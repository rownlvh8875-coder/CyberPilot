"""Stored record relations only: no model, numeric decoding or origin proof."""

import re

from .core_sequence_cases import CASE_IDS
from .scenario_output import GATES, canonical

CONTRACT = 'CORE8_CLOSED_SYNTHETIC_SEQUENCE_DEMO_V1'
SCOPE = 'CLOSED_DECLARED_SYNTHETIC_FIXTURE_ONLY'
CLAIM = 'ADJACENT_DECLARED_CURRENT_TRANSITIONS_ONLY_NOT_COMPUTED_ROLLOUT'
FRAME_KEYS = set(('request settings state_stage settings_origin limited_state_at_entry saved_limited_state '
                  'angle_counter_at_entry saved_angle_counter inactive_gate_active').split())
REQUEST_KEYS = set(('context sequence sample_time_ns requested_binary32_be_hex request_active request_override reset_since_previous').split())
CONTEXT_KEYS = set(('schema_version scope source_profile capture_epoch_id controller_instance_id configuration_epoch_id '
                    'clock_domain control_mode request_stage reset_generation loss_generation').split())
SETTINGS_KEYS = set('request_scale limiter_scale delta_up delta_down driver_allowance driver_factor driver_multiplier'.split())
AUX_KEYS = set('scope model_index previous_integer_request current_driver_hex current_angle_deg_hex'.split())
STATE_KEYS = set('index previous_requested previous_applied angle_counter'.split())
ROW_KEYS = set('transition_index status model_index entry_state computed_next_state declared_saved_state differences'.split())
SAVED_KEYS = {'saved_limited_state', 'saved_angle_counter'}
RESULT_KEYS = set(('schema_version contract_id scope case_id status rejection_code sequence_completed frame_count declared_transition_count '
                   'completed_transition_count model_steps differing_transition_indices rows identity gates validation_claim '
                   'anchor_transition_checked prehistory_checked source_authenticated').split())


class InspectError(ValueError):
    """Fixed diagnostic without raw input forwarding."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _need(condition: bool, code: str = 'INSPECT_RECORD') -> None:
    if not condition:
        raise InspectError(code)


def _mapping(value, keys, code='INSPECT_RECORD') -> dict:
    _need(type(value) is dict and set(value) == keys, code)
    return value


def _integer(value, low, high) -> bool:
    return type(value) is int and low <= value <= high


def _equal(left, right) -> bool:
    # JSON equality preserves the difference between false and integer zero.
    return canonical(left) == canonical(right)


def _matches(value, pattern) -> bool:
    return type(value) is str and re.fullmatch(pattern, value) is not None


def _request(value) -> dict:
    r = _mapping(value, REQUEST_KEYS)
    c = _mapping(r['context'], CONTEXT_KEYS)
    _need(type(c['schema_version']) is int and c['schema_version'] == 1)
    for key, literal in [('scope', 'COUNTERFACTUAL_REQUEST_SNAPSHOT_ONLY'),
        ('source_profile', 'CORE3_COUNTERFACTUAL_REQUEST_SOURCE_V1'), ('control_mode', 'DECLARED_TORQUE_CONTROL'),
        ('request_stage', 'REQUESTED_NORMALIZED_BEFORE_INTEGER_LIMITER')]:
        _need(c[key] == literal)
    _need(c['clock_domain'] in ('DECLARED_LIVE_MONOTONIC_NS', 'DECLARED_REPLAY_RECORDED_CAN_NS'))
    _need(all(_matches(c[key], r'[A-Za-z0-9_-]{1,64}') for key in ('capture_epoch_id', 'controller_instance_id', 'configuration_epoch_id')))
    _need(all(_integer(c[key], 0, (1 << 64) - 1) for key in ('reset_generation', 'loss_generation')))
    _need(_integer(r['sequence'], 0, (1 << 64) - 1) and _integer(r['sample_time_ns'], -(1 << 63), (1 << 63) - 1))
    _need(_matches(r['requested_binary32_be_hex'], r'[0-9a-f]{8}'))
    _need(all(type(r[key]) is bool for key in ('request_active', 'request_override', 'reset_since_previous')))
    return r


def _frames(value) -> list:
    _need(type(value) is list and len(value) == 4)
    for i, frame in enumerate(value):
        f = _mapping(frame, FRAME_KEYS)
        r = _request(f['request'])
        s = _mapping(f['settings'], SETTINGS_KEYS)
        _need(all(_integer(s[key], 1, 2048) for key in ('request_scale', 'limiter_scale')))
        _need(s['request_scale'] == s['limiter_scale'])
        _need(all(_integer(s[key], 0, 64) for key in ('delta_up', 'delta_down', 'driver_allowance')))
        _need(all(_integer(s[key], 0, 8) for key in ('driver_factor', 'driver_multiplier')))
        _need(f['state_stage'] == 'DECLARED_LIMITED_STATE_POST_INACTIVE_GATE'
              and f['settings_origin'] == 'DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS')
        _need(all(_integer(f[key], -2048, 2048) for key in ('limited_state_at_entry', 'saved_limited_state')))
        _need(all(_integer(f[key], 0, 90) for key in ('angle_counter_at_entry', 'saved_angle_counter')))
        _need(type(f['inactive_gate_active']) is bool and (f['inactive_gate_active'] or f['saved_limited_state'] == 0))
        if i:
            previous = value[i - 1]
            p = previous['request']
            _need(_equal(r['context'], p['context']) and _equal(s, previous['settings']))
            _need(r['sequence'] == p['sequence'] + 1 and r['sample_time_ns'] > p['sample_time_ns'])
            _need(not r['reset_since_previous'])
            _need(f['limited_state_at_entry'] == previous['saved_limited_state']
                  and f['angle_counter_at_entry'] == previous['saved_angle_counter'])
    return value


def _contexts(value) -> list:
    _need(type(value) is list and len(value) == 3)
    for i, item in enumerate(value):
        c = _mapping(item, AUX_KEYS)
        _need(c['scope'] == 'COUNTERFACTUAL_MODEL_INPUT_ONLY' and _integer(c['model_index'], 1, 4095))
        _need(_integer(c['previous_integer_request'], -2048, 2048))
        # Text grammar only, deliberately not float.fromhex or dyadic validation.
        _need(all(_matches(c[key], r'-?0x(?:0\.0|[01]\.[0-9a-f]{13})p[+-][0-9]{1,4}')
                  for key in ('current_driver_hex', 'current_angle_deg_hex')))
        if i:
            _need(c['model_index'] == value[i - 1]['model_index'] + 1)
    return value


def _state(value) -> dict:
    s = _mapping(value, STATE_KEYS, 'INSPECT_ROWS')
    _need(_integer(s['index'], 1, 4096) and _integer(s['angle_counter'], 0, 90), 'INSPECT_ROWS')
    _need(all(_integer(s[key], -2048, 2048) for key in ('previous_requested', 'previous_applied')), 'INSPECT_ROWS')
    return s


def _rows(result, frames, contexts) -> list:
    rows = result['rows']
    _need(type(rows) is list and len(rows) == 3, 'INSPECT_ROWS')
    projected, differing = [], []
    for i, item in enumerate(rows):
        row = _mapping(item, ROW_KEYS, 'INSPECT_ROWS')
        frame, context = frames[i + 1], contexts[i]
        _need(_integer(row['transition_index'], 0, 2) and row['transition_index'] == i, 'INSPECT_ROWS')
        _need(_integer(row['model_index'], 1, 4095) and row['model_index'] == context['model_index'], 'INSPECT_ROWS')
        entry, computed = _state(row['entry_state']), _state(row['computed_next_state'])
        _need(entry['index'] == row['model_index'] and computed['index'] == entry['index'] + 1, 'INSPECT_ROWS')
        _need(entry['previous_requested'] == context['previous_integer_request']
              and entry['previous_applied'] == frame['limited_state_at_entry']
              and entry['angle_counter'] == frame['angle_counter_at_entry'], 'INSPECT_ROWS')
        saved = _mapping(row['declared_saved_state'], SAVED_KEYS, 'INSPECT_ROWS')
        _need(_equal(saved, {key: frame[key] for key in SAVED_KEYS}), 'INSPECT_ROWS')
        differences = [{'field': field, 'declared': saved[field], 'computed': computed[key]}
                       for field, key in [('saved_limited_state', 'previous_applied'), ('saved_angle_counter', 'angle_counter')]
                       if saved[field] != computed[key]]
        status = 'DIFFERENT' if differences else 'MATCH'
        _need(_equal(row['differences'], differences) and row['status'] == status, 'INSPECT_ROWS')
        if differences:
            differing.append(i)
        if i:
            _need(rows[i - 1]['computed_next_state']['previous_requested'] == entry['previous_requested'], 'INSPECT_ROWS')
        projected.append({'transition_index': i, 'status': status, 'model_index': row['model_index'],
            'saved_limited_state': saved['saved_limited_state'], 'computed_limited_state': computed['previous_applied'],
            'saved_angle_counter': saved['saved_angle_counter'], 'computed_angle_counter': computed['angle_counter'],
            'differences': differences})
    _need(_equal(result['differing_transition_indices'], differing)
          and result['status'] == ('DIFFERENT' if differing else 'MATCH'), 'INSPECT_ROWS')
    return projected


def _preflight_code(value) -> bool:
    if type(value) is not str or len(value) > 128:
        return False
    if value in ('SEQUENCE_TYPE', 'SEQUENCE_CONTAINER', 'SEQUENCE_COUNT', 'SEQUENCE_MODEL_ORDER:1', 'SEQUENCE_MODEL_ORDER:2'):
        return True
    match = re.fullmatch(r'SEQUENCE_INPUT:[0-2]:(MODEL_[A-Z_:]+)', value)
    if match is None:
        return False
    code = match[1]
    if code in {'MODEL_INPUT_TYPE', 'MODEL_CONTEXT_TYPE', 'MODEL_SCOPE', 'MODEL_INDEX', 'MODEL_PREVIOUS_REQUEST',
                'MODEL_DRIVER', 'MODEL_ANGLE', 'MODEL_OVERRIDE', 'MODEL_ACTIVE_READS', 'MODEL_VERSION', 'MODEL_PREVIOUS_REQUEST_MISMATCH'}:
        return True
    limiter = {'DECLARATION', 'SETTINGS_TYPE', 'SETTINGS_DOMAIN', 'SCALE_MISMATCH', 'STATE_DOMAIN', 'COUNTER_DOMAIN',
               'GATE_FLAG', 'INACTIVE_STATE', 'SNAPSHOT_TYPE', 'PAIR_SETTINGS', 'PAIR_STATE_LINK', 'PAIR_COUNTER_LINK'}
    request = {'CONTEXT_TYPE', 'SCOPE', 'SOURCE_PROFILE', 'CONTEXT_MODE', 'CONTEXT_ID', 'GENERATION', 'SEQUENCE',
               'TIME', 'WORD', 'FLAGS', 'SNAPSHOT_TYPE', 'PAIR_CONTEXT', 'PAIR_SEQUENCE', 'PAIR_TIME', 'PAIR_RESET'}
    return code in {'MODEL_LIMITER:LIMITER_' + s for s in limiter} | {'MODEL_LIMITER:LIMITER_REQUEST:REQUEST_' + s for s in request}


def validate_records(input_record: object, result_record: object) -> dict:
    """Check stored links/comparisons, never whether the recorded arithmetic is true."""
    source = _mapping(input_record, {'schema_version', 'contract_id', 'scope', 'case_id', 'frames', 'contexts'})
    result = _mapping(result_record, RESULT_KEYS)
    for record in (source, result):
        _need(type(record['schema_version']) is int and record['schema_version'] == 1)
        _need(record['contract_id'] == CONTRACT and record['scope'] == SCOPE)
        _need(type(record['case_id']) is str and record['case_id'] in CASE_IDS)
    _need(source['case_id'] == result['case_id'])
    frames, contexts = _frames(source['frames']), _contexts(source['contexts'])
    _need(_integer(result['frame_count'], 4, 4) and _integer(result['declared_transition_count'], 3, 3))
    _need(_equal(result['gates'], GATES) and result['validation_claim'] == CLAIM)
    _need(all(result[key] is False for key in ('anchor_transition_checked', 'prehistory_checked', 'source_authenticated')))
    identity = result['identity']
    _need(type(identity) is dict and identity.get('model_version') == '0.3.0'
          and _matches(identity.get('demo_cli_sha256'), r'[0-9a-f]{64}'))
    status = result['status']
    _need(type(status) is str and status in ('MATCH', 'DIFFERENT', 'REJECTED'))
    if status == 'REJECTED':
        _need(result['sequence_completed'] is False and _integer(result['model_steps'], 0, 0)
              and _integer(result['completed_transition_count'], 0, 0) and _equal(result['rows'], [])
              and _equal(result['differing_transition_indices'], []) and _preflight_code(result['rejection_code']))
        rows = []
    else:
        _need(result['sequence_completed'] is True and _integer(result['model_steps'], 3, 3)
              and _integer(result['completed_transition_count'], 3, 3) and result['rejection_code'] is None)
        rows = _rows(result, frames, contexts)
    return {'schema_version': 1, 'contract_id': 'CORE9_SAVED_SEQUENCE_INSPECTION_V1',
        'inspection_status': 'SAVED_RECORDS_CONSISTENT', 'case_id': result['case_id'], 'saved_status': status,
        'saved_rejection_code': result['rejection_code'], 'recorded_model_steps': result['model_steps'],
        'recorded_transition_count': result['completed_transition_count'],
        'differing_transition_indices': result['differing_transition_indices'], 'rows': rows, 'gates': dict(GATES),
        'inspection_model_executions': 0, 'inspection_reference_executions': 0, 'source_identity_reauthenticated': False,
        'anchor_transition_checked': False, 'prehistory_checked': False,
        'integrity_scope': 'CAPTURED_BYTES_CHECKSUMS_AND_RECORD_RELATIONS_NOT_ARITHMETIC_OR_ORIGIN_PROOF'}
