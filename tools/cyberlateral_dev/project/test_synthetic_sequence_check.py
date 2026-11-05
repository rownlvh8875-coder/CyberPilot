"""Whole-input preflight and declared-entry diagnostics must not become rollout."""

import importlib
import json
import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError, asdict, replace
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


class SyntheticSequenceCheckTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/synthetic_sequence_check.py').is_file(), 'Missing CORE7 declared sequence checker')
        package_feature()
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.synthetic_sequence_check')

    def fixture(self):
        r = importlib.import_module('integration_tools.request_snapshot')
        limiter = importlib.import_module('integration_tools.limiter_snapshot')
        inputs = importlib.import_module('integration_tools.synthetic_model_input')
        context = r.SyntheticRequestContextV1(1, 'COUNTERFACTUAL_REQUEST_SNAPSHOT_ONLY',
            'CORE3_COUNTERFACTUAL_REQUEST_SOURCE_V1', 'capture-A', 'controller-A', 'config-A',
            'DECLARED_LIVE_MONOTONIC_NS', 'DECLARED_TORQUE_CONTROL', 'REQUESTED_NORMALIZED_BEFORE_INTEGER_LIMITER', 0, 0)
        settings = limiter.SyntheticConsumedSettingsV1(16, 16, 2, 5, 7, 1, 3)
        frames = []
        for seq, word, entry, saved, counter, next_counter in [
            (0, 'be800000', 7, -2, 3, 4), (1, '3f000000', -2, 2, 4, 5),
            (2, 'bf000000', 2, -2, 5, 6), (3, '3e800000', -2, 2, 6, 7),
        ]:
            request = r.SyntheticRequestSnapshotV1(context, seq, 1_000_000_000 + seq * 10_000_000,
                                                  bytes.fromhex(word), True, False, False)
            frames.append(limiter.SyntheticLimiterSnapshotV1(request, settings, 'DECLARED_LIMITED_STATE_POST_INACTIVE_GATE',
                'DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS', entry, saved, counter, next_counter, True))
        contexts = tuple(inputs.SyntheticModelContextV1('COUNTERFACTUAL_MODEL_INPUT_ONLY', index, previous, 1.5, 85.0)
                         for index, previous in [(5, -4), (6, 8), (7, -8)])
        return tuple(frames), contexts

    def no_steps(self, call):
        code = package_feature().step.__code__
        count = 0

        def profile(frame, event, _arg):
            nonlocal count
            if event == 'call' and frame.f_code is code:
                count += 1

        old = sys.getprofile()
        try:
            sys.setprofile(profile)
            call()
        finally:
            sys.setprofile(old)
            self.assertEqual(count, 0)

    def reject(self, m, code, frames, contexts):
        with self.assertRaises(m.SequenceCheckError) as raised:
            self.no_steps(lambda: m.check_synthetic_sequence(frames, contexts))
        self.assertEqual((raised.exception.code, str(raised.exception)), (code, code))

    def test_three_literal_transitions_match_and_preserve_context_roles(self):
        m = self.module()
        frames, contexts = self.fixture()
        result = m.check_synthetic_sequence(frames, contexts)
        model = package_feature()
        self.assertEqual((result.status, result.checked_transition_count, result.synthetic_model_steps), ('MATCH', 3, 3))
        self.assertEqual(tuple(row.computed_next_state for row in result.checks),
                         (model.LateralState(6, 8, 2, 5), model.LateralState(7, -8, -2, 6), model.LateralState(8, 4, 2, 7)))
        self.assertEqual(result.differing_transition_indices, ())
        self.assertIs(result.frames, frames)
        self.assertIs(result.contexts, contexts)
        self.assertEqual(result.checks[0].current.request.sequence, 1)
        self.assertEqual(result.checks[0].context.model_index, 5)

    def test_minimal_two_frames_are_one_nonvacuous_transition(self):
        m = self.module()
        frames, contexts = self.fixture()
        result = m.check_synthetic_sequence(frames[:2], contexts[:1])
        self.assertEqual((result.status, result.checked_transition_count, result.synthetic_model_steps), ('MATCH', 1, 1))

    def test_early_difference_keeps_declared_entry_and_does_not_skip_later_steps(self):
        m = self.module()
        frames, contexts = self.fixture()
        changed = (frames[0], replace(frames[1], saved_limited_state=10),
                   replace(frames[2], limited_state_at_entry=10, saved_limited_state=5),
                   replace(frames[3], limited_state_at_entry=5, saved_limited_state=4))
        result = m.check_synthetic_sequence(changed, contexts)
        self.assertEqual((result.status, result.differing_transition_indices), ('DIFFERENT', (0,)))
        self.assertEqual(tuple(row.status for row in result.checks), ('DIFFERENT', 'MATCH', 'MATCH'))
        self.assertEqual(tuple(row.computed_next_state.previous_applied for row in result.checks), (2, 5, 4))
        self.assertEqual(result.checks[1].prepared.model_state.previous_applied, 10)
        self.assertEqual((result.frames[1].saved_limited_state, result.synthetic_model_steps), (10, 3))

    def test_late_counter_difference_cannot_be_masked_by_matching_prefix(self):
        m = self.module()
        frames, contexts = self.fixture()
        result = m.check_synthetic_sequence((*frames[:3], replace(frames[3], saved_angle_counter=8)), contexts)
        self.assertEqual((result.status, result.differing_transition_indices), ('DIFFERENT', (2,)))
        self.assertEqual(tuple(row.status for row in result.checks), ('MATCH', 'MATCH', 'DIFFERENT'))
        self.assertEqual((result.checks[2].differences[0].declared, result.checks[2].differences[0].computed), (8, 7))

    def test_all_differences_are_reported_in_transition_order(self):
        m = self.module()
        frames, contexts = self.fixture()
        changed = (frames[0], replace(frames[1], saved_angle_counter=10),
                   replace(frames[2], angle_counter_at_entry=10, saved_angle_counter=20),
                   replace(frames[3], angle_counter_at_entry=20, saved_angle_counter=30))
        result = m.check_synthetic_sequence(changed, contexts)
        self.assertEqual((result.status, result.differing_transition_indices), ('DIFFERENT', (0, 1, 2)))
        self.assertEqual(tuple(row.computed_next_state.angle_counter for row in result.checks), (5, 11, 21))

    def test_empty_single_or_oversize_frames_and_context_misalignment_reject(self):
        m = self.module()
        frames, contexts = self.fixture()
        for fs, cs in [((), ()), (frames[:1], ()), (frames, contexts[:2]), (frames, (*contexts, contexts[0])),
                       ((frames[0],) * 4097, (contexts[0],) * 4096)]:
            self.reject(m, 'SEQUENCE_COUNT', fs, cs)

    def test_exact_tuple_containers_reject_foreign_iteration_and_subclasses(self):
        m = self.module()
        frames, contexts = self.fixture()

        class Foreign:
            def __iter__(self):
                raise AssertionError('ITERATED_SOURCE')

            def __len__(self):
                raise AssertionError('READ_SOURCE')

        class Child(tuple):
            pass

        for bad in (None, {}, list(frames), Foreign(), Child(frames)):
            self.reject(m, 'SEQUENCE_CONTAINER', bad, contexts)
        for bad in (None, {}, list(contexts), Foreign(), Child(contexts)):
            self.reject(m, 'SEQUENCE_CONTAINER', frames, bad)

    def test_foreign_frame_and_context_members_are_rejected_without_getters(self):
        m = self.module()
        frames, contexts = self.fixture()

        class Foreign:
            def __getattribute__(self, _name):
                raise AssertionError('SOURCE_READ')

        self.reject(m, 'SEQUENCE_INPUT:2:MODEL_LIMITER:LIMITER_SNAPSHOT_TYPE', (*frames[:3], Foreign()), contexts)
        self.reject(m, 'SEQUENCE_INPUT:2:MODEL_CONTEXT_TYPE', frames, (*contexts[:2], Foreign()))

    def test_late_bad_auxiliary_input_rejects_before_any_step(self):
        m = self.module()
        frames, contexts = self.fixture()
        self.reject(m, 'SEQUENCE_INPUT:2:MODEL_DRIVER', frames, (*contexts[:2], replace(contexts[2], current_driver=0.1)))

    def test_all_preflight_precedes_model_order_diagnostics(self):
        m = self.module()
        frames, contexts = self.fixture()
        bad = (contexts[0], replace(contexts[1], model_index=8), replace(contexts[2], current_angle_deg=0.1))
        self.reject(m, 'SEQUENCE_INPUT:2:MODEL_ANGLE', frames, bad)

    def test_model_index_gap_repeat_or_reverse_is_not_derived_from_capture_sequence(self):
        m = self.module()
        frames, contexts = self.fixture()
        for index in (5, 4, 7):
            self.reject(m, 'SEQUENCE_MODEL_ORDER:1', frames, (contexts[0], replace(contexts[1], model_index=index), contexts[2]))
        changed = tuple(replace(c, model_index=c.model_index + 100) for c in contexts)
        result = m.check_synthetic_sequence(frames, changed)
        self.assertEqual(tuple(row.computed_next_state.index for row in result.checks), (106, 107, 108))

    def test_late_invalid_model_index_is_input_failure_not_partial_success(self):
        m = self.module()
        frames, contexts = self.fixture()
        changed = tuple(replace(c, model_index=4094 + i) for i, c in enumerate(contexts))
        self.reject(m, 'SEQUENCE_INPUT:2:MODEL_INDEX', frames, changed)

    def test_late_broken_link_and_settings_drift_have_transition_ordinals(self):
        m = self.module()
        frames, contexts = self.fixture()
        for last, code in [(replace(frames[3], limited_state_at_entry=10), 'LIMITER_PAIR_STATE_LINK'),
                           (replace(frames[3], angle_counter_at_entry=10), 'LIMITER_PAIR_COUNTER_LINK'),
                           (replace(frames[3], settings=replace(frames[3].settings, delta_down=6)), 'LIMITER_PAIR_SETTINGS')]:
            self.reject(m, 'SEQUENCE_INPUT:2:MODEL_LIMITER:' + code, (*frames[:3], last), contexts)

    def test_reset_epoch_and_time_order_are_not_bridged(self):
        m = self.module()
        frames, contexts = self.fixture()
        last = frames[3]
        for request, code in [(replace(last.request, reset_since_previous=True), 'REQUEST_PAIR_RESET'),
                              (replace(last.request, sample_time_ns=frames[2].request.sample_time_ns), 'REQUEST_PAIR_TIME'),
                              (replace(last.request, context=replace(last.request.context, capture_epoch_id='new-epoch')), 'REQUEST_PAIR_CONTEXT')]:
            self.reject(m, 'SEQUENCE_INPUT:2:MODEL_LIMITER:LIMITER_REQUEST:' + code,
                        (*frames[:3], replace(last, request=request)), contexts)

    def test_late_previous_integer_active_or_override_does_not_execute_prefix(self):
        m = self.module()
        frames, contexts = self.fixture()
        self.reject(m, 'SEQUENCE_INPUT:2:MODEL_PREVIOUS_REQUEST_MISMATCH', frames,
                    (*contexts[:2], replace(contexts[2], previous_integer_request=2)))
        for request, code in [(replace(frames[3].request, request_active=False), 'MODEL_ACTIVE_READS'),
                              (replace(frames[3].request, request_override=True), 'MODEL_OVERRIDE')]:
            self.reject(m, 'SEQUENCE_INPUT:2:' + code, (*frames[:3], replace(frames[3], request=request)), contexts)

    def test_maximum_bounded_sequence_is_not_truncated(self):
        m = self.module()
        frames, contexts = self.fixture()
        anchor = frames[0]
        fs = tuple(replace(anchor, request=replace(anchor.request, sequence=i, sample_time_ns=1_000_000_000 + i,
                       requested_binary32=bytes.fromhex('00000000')), limited_state_at_entry=0, saved_limited_state=0,
                       angle_counter_at_entry=0, saved_angle_counter=0) for i in range(4096))
        cs = tuple(replace(contexts[0], model_index=i, previous_integer_request=0, current_driver=0.0,
                           current_angle_deg=0.0) for i in range(1, 4096))
        result = m.check_synthetic_sequence(fs, cs)
        self.assertEqual((result.status, result.checked_transition_count, result.synthetic_model_steps), ('MATCH', 4095, 4095))
        self.assertEqual(result.checks[-1].computed_next_state.index, 4096)

    def test_valid_sequence_runs_exactly_one_step_per_transition(self):
        m = self.module()
        frames, contexts = self.fixture()
        calls = 0
        code = package_feature().step.__code__

        def profile(frame, event, _arg):
            nonlocal calls
            if event == 'call' and frame.f_code is code:
                calls += 1

        old = sys.getprofile()
        try:
            sys.setprofile(profile)
            a = m.check_synthetic_sequence(frames, contexts)
            self.assertEqual(calls, 3)
            m.SyntheticSequenceCheckV1(frames, contexts)
            self.assertEqual(calls, 6)
            replace(a, frames=(*frames[:3], replace(frames[3], saved_angle_counter=8)))
            self.assertEqual(calls, 9)
        finally:
            sys.setprofile(old)

    def test_direct_construction_and_replace_cannot_bypass_full_preflight(self):
        m = self.module()
        frames, contexts = self.fixture()
        result = m.SyntheticSequenceCheckV1(frames, contexts)
        with self.assertRaisesRegex(m.SequenceCheckError, '^SEQUENCE_INPUT:2:MODEL_CONTEXT_TYPE$'):
            self.no_steps(lambda: replace(result, contexts=(*contexts[:2], None)))

    def test_result_subclasses_and_derived_field_injection_cannot_claim_success(self):
        m = self.module()
        frames, contexts = self.fixture()

        class Child(m.SyntheticSequenceCheckV1):
            pass

        with self.assertRaisesRegex(m.SequenceCheckError, '^SEQUENCE_TYPE$'):
            self.no_steps(lambda: Child(frames, contexts))
        result = m.check_synthetic_sequence(frames, contexts)
        for key in ('checks', 'status', 'differing_transition_indices', 'synthetic_model_steps', 'actual_activation_allowed'):
            with self.assertRaises(TypeError):
                m.SyntheticSequenceCheckV1(frames, contexts, **{key: None})
            with self.assertRaises(ValueError):
                replace(result, **{key: None})

    def test_late_model_failure_has_ordinal_and_never_returns_partial_sequence(self):
        m = self.module()
        frames, contexts = self.fixture()
        model = package_feature()
        original = model.step
        attempted = []

        def fail_second(sample, state):
            attempted.append(sample.index)
            if sample.index == 6:
                raise ValueError('not forwarded')
            return original(sample, state)

        with patch.object(model, 'step', side_effect=fail_second):
            with self.assertRaisesRegex(m.SequenceCheckError, '^SEQUENCE_TRANSITION:1:TRANSITION_MODEL_FAILURE$'):
                m.check_synthetic_sequence(frames, contexts)
        self.assertEqual(attempted, [5, 6])

    def test_unexpected_model_exception_is_not_silently_aggregate_different(self):
        m = self.module()
        frames, contexts = self.fixture()
        with patch.object(package_feature(), 'step', side_effect=RuntimeError('unexpected')):
            with self.assertRaisesRegex(RuntimeError, '^unexpected$'):
                m.check_synthetic_sequence(frames, contexts)

    def test_anchor_can_be_resumed_but_match_is_not_anchor_or_prehistory_proof(self):
        m = self.module()
        frames, contexts = self.fixture()
        result = m.check_synthetic_sequence((replace(frames[0], limited_state_at_entry=2000), *frames[1:]), contexts)
        self.assertEqual(result.status, 'MATCH')
        for key in ('first_frame_transition_checked', 'prehistory_checked', 'source_identity_reauthenticated',
                    'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
            self.assertIs(getattr(result, key), False)

    def test_no_mutation_frozen_deterministic_result_and_no_policy_defaults(self):
        m = self.module()
        frames, contexts = self.fixture()
        before = tuple(asdict(f) for f in frames), tuple(asdict(c) for c in contexts)
        a = m.check_synthetic_sequence(frames, contexts)
        b = m.check_synthetic_sequence(frames, contexts)
        self.assertEqual(a, b)
        self.assertEqual((tuple(asdict(f) for f in frames), tuple(asdict(c) for c in contexts)), before)
        with self.assertRaises(FrozenInstanceError):
            a.status = 'MATCH'
        with self.assertRaises(TypeError):
            m.check_synthetic_sequence(frames, contexts, rate_budget_per_s=0)
        self.assertFalse(hasattr(a, 'dt'))

    def test_fresh_process_does_not_load_original_runtime_numpy_or_f61(self):
        self.module()
        script = '''
import json, sys
from test_synthetic_sequence_check import SyntheticSequenceCheckTests
t = SyntheticSequenceCheckTests()
m = t.module()
m.check_synthetic_sequence(*t.fixture())
bad = [n for n in sys.modules if n == 'numpy' or n.startswith(('openpilot', 'selfdrive', 'opendbc', 'synthetic_rate_constraint_feasibility'))]
assert bad == [], bad
print(json.dumps({'forbidden_modules': bad}))
'''
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT / 'project', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout), {'forbidden_modules': []})
