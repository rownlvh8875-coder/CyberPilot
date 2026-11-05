"""Closed synthetic literals. Importing the catalog loads no model or source data."""

CASE_IDS = ('sign-cycle', 'declared-difference', 'late-invalid')


def build_case(case_id: str):
    if type(case_id) is not str or case_id not in CASE_IDS:
        raise ValueError('DEMO_CASE')
    from dataclasses import replace

    from .limiter_snapshot import SyntheticConsumedSettingsV1, SyntheticLimiterSnapshotV1
    from .request_snapshot import SyntheticRequestContextV1, SyntheticRequestSnapshotV1
    from .synthetic_model_input import SyntheticModelContextV1

    context = SyntheticRequestContextV1(1, 'COUNTERFACTUAL_REQUEST_SNAPSHOT_ONLY',
        'CORE3_COUNTERFACTUAL_REQUEST_SOURCE_V1', 'demo-capture', 'demo-controller', 'demo-config',
        'DECLARED_LIVE_MONOTONIC_NS', 'DECLARED_TORQUE_CONTROL', 'REQUESTED_NORMALIZED_BEFORE_INTEGER_LIMITER', 0, 0)
    settings = SyntheticConsumedSettingsV1(16, 16, 2, 5, 7, 1, 3)
    frames = []
    for seq, word, entry, saved, counter, after in [
        (0, 'be800000', 7, -2, 3, 4), (1, '3f000000', -2, 2, 4, 5),
        (2, 'bf000000', 2, -2, 5, 6), (3, '3e800000', -2, 2, 6, 7),
    ]:
        request = SyntheticRequestSnapshotV1(context, seq, 1_000_000_000 + seq * 10_000_000,
                                              bytes.fromhex(word), True, False, False)
        frames.append(SyntheticLimiterSnapshotV1(request, settings, 'DECLARED_LIMITED_STATE_POST_INACTIVE_GATE',
            'DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS', entry, saved, counter, after, True))
    contexts = tuple(SyntheticModelContextV1('COUNTERFACTUAL_MODEL_INPUT_ONLY', index, previous, 1.5, 85.0)
                     for index, previous in [(5, -4), (6, 8), (7, -8)])
    if case_id == 'declared-difference':
        frames[1] = replace(frames[1], saved_limited_state=10)
        frames[2] = replace(frames[2], limited_state_at_entry=10, saved_limited_state=5)
        frames[3] = replace(frames[3], limited_state_at_entry=5, saved_limited_state=4)
    elif case_id == 'late-invalid':
        contexts = (*contexts[:2], replace(contexts[2], current_driver=0.1))
    return tuple(frames), contexts
