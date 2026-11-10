"""Three literal boundary fixtures; no model, quantizer or elapsed-time calculation."""

CASE_IDS = ('inactive-resume', 'fault-reset', 'rounding-ties')
# word, active, declared entry/saved applied, declared entry/saved counter
_FRAMES = {
    'inactive-resume': (('be800000', True, 7, -2, 3, 4), ('3f000000', False, -2, 0, 4, 0),
                        ('bf000000', True, 0, -2, 0, 1), ('3e800000', True, -2, 2, 1, 2)),
    'fault-reset': (('be800000', True, 7, -2, 87, 88), ('3f000000', True, -2, 2, 88, 89),
                    ('bf000000', True, 2, -2, 89, 90), ('3e800000', True, -2, 2, 90, 0), ('be800000', True, 2, -2, 0, 1)),
    'rounding-ties': (('00000000', True, 0, 0, 0, 0), ('3d000000', True, 0, 0, 0, 0),
                      ('3dc00000', True, 0, 2, 0, 0), ('bd000000', True, 2, 0, 0, 0),
                      ('bdc00000', True, 0, -2, 0, 0), ('00000000', True, -2, 0, 0, 0), ('80000000', True, 0, 0, 0, 0)),
}
_PREVIOUS_REQUESTS = {'inactive-resume': (-4, 8, -8), 'fault-reset': (-4, 8, -8, 4), 'rounding-ties': (0, 0, 2, 0, -2, 0)}


def build_boundary_case(case_id: object):
    """Fresh typed carriers only; declarations never establish actual capture/history."""
    if type(case_id) is not str or case_id not in CASE_IDS:
        raise ValueError('BOUNDARY_CASE')
    from dataclasses import replace

    from .core_sequence_cases import build_case
    from .synthetic_model_input import SyntheticModelContextV1

    originals, _ = build_case('sign-cycle')
    base = originals[0]
    context = replace(base.request.context, capture_epoch_id='core31-' + case_id)
    frames = []
    for i, (word, active, entry, saved, counter, after) in enumerate(_FRAMES[case_id]):
        request = replace(base.request, context=context, sequence=i, sample_time_ns=1_000_000_000 + i * 10_000_000,
                          requested_binary32=bytes.fromhex(word), request_active=active)
        frames.append(replace(base, request=request, limited_state_at_entry=entry, saved_limited_state=saved,
                              angle_counter_at_entry=counter, saved_angle_counter=after, inactive_gate_active=active))
    contexts = tuple(SyntheticModelContextV1('COUNTERFACTUAL_MODEL_INPUT_ONLY', 5 + i, previous, 1.5,
                                            0.0 if case_id == 'rounding-ties' else 85.0)
                     for i, previous in enumerate(_PREVIOUS_REQUESTS[case_id]))
    return tuple(frames), contexts


def input_record(case_id, frames, contexts) -> dict:
    """Structural serializer reused, explicitly NOT an additional CORE28 accepted case."""
    from .core_rollout_run import _input_record

    return {**_input_record(case_id, frames, contexts), 'contract_id': 'CORE31_CLOSED_BOUNDARY_INPUT_V1'}
