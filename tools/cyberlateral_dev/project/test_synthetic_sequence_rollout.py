"""Computed next-state feed must differ from independent declared diagnostics."""

import importlib
import os
import sys
import unittest
from dataclasses import FrozenInstanceError, asdict, replace
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


class SyntheticSequenceRolloutTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/synthetic_sequence_rollout.py').is_file(), 'Missing CORE27 computed rollout')
        self.model = package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.m = importlib.import_module('integration_tools.synthetic_sequence_rollout')
        self.cases = importlib.import_module('integration_tools.core_sequence_cases')
        self.frames, self.contexts = self.cases.build_case('sign-cycle')

    def run_case(self, frames=None, contexts=None):
        return self.m.rollout_synthetic_sequence(self.frames if frames is None else frames, self.contexts if contexts is None else contexts)

    def states(self, result): return tuple((r.output.next_state.index, r.output.next_state.previous_requested, r.output.next_state.previous_applied, r.output.next_state.angle_counter) for r in result.steps)

    def profiled(self, call):
        code = self.model.step.__code__; calls = []; old = sys.getprofile()
        def profile(frame, event, arg):
            if event == 'call' and frame.f_code is code: calls.append((frame.f_locals['sample'], frame.f_locals['state']))
        try:
            sys.setprofile(profile); result = call()
        finally: sys.setprofile(old)
        return result, calls

    def reject(self, code, frames, contexts):
        calls = []; target = self.model.step.__code__; old = sys.getprofile()
        def profile(frame, event, arg):
            if event == 'call' and frame.f_code is target: calls.append(1)
        try:
            sys.setprofile(profile)
            with self.assertRaises(self.m.SequenceRolloutError) as found: self.m.rollout_synthetic_sequence(frames, contexts)
        finally: sys.setprofile(old)
        self.assertEqual((found.exception.code, str(found.exception)), (code, code)); self.assertEqual(calls, [])

    def test_literal_matching_chain_uses_three_public_steps(self):
        r, calls = self.profiled(self.run_case)
        self.assertEqual((r.status, r.checked_transition_count, r.synthetic_model_steps), ('MATCH', 3, 3))
        self.assertEqual(self.states(r), ((6, 8, 2, 5), (7, -8, -2, 6), (8, 4, 2, 7)))
        self.assertEqual(len(calls), 3); self.assertEqual(r.differing_transition_indices, ())
        self.assertEqual(r.initial_declared_state, self.model.LateralState(5, -4, -2, 4))
        self.assertIs(r.final_computed_state, r.steps[-1].output.next_state)

    def test_subsequent_entry_is_identical_computed_next_state_not_declared_state(self):
        r, calls = self.profiled(self.run_case)
        self.assertIs(r.steps[0].entry_state, r.steps[0].prepared.model_state)
        for index in (1, 2):
            self.assertIs(r.steps[index].entry_state, r.steps[index - 1].output.next_state)
            self.assertIs(calls[index][1], r.steps[index - 1].output.next_state)
            self.assertIsNot(r.steps[index].entry_state, r.steps[index].prepared.model_state)

    def test_early_difference_never_reseeds_from_declared_ten_or_five(self):
        frames, contexts = self.cases.build_case('declared-difference'); before = asdict(frames[1])
        r = self.run_case(frames, contexts)
        self.assertEqual(self.states(r), ((6, 8, 2, 5), (7, -8, -2, 6), (8, 4, 2, 7)))
        self.assertEqual((r.status, r.differing_transition_indices, r.entry_differing_transition_indices, r.output_differing_transition_indices), ('DIFFERENT', (0, 1, 2), (1, 2), (0, 1, 2)))
        self.assertEqual(tuple(row.prepared.model_state.previous_applied for row in r.steps), (-2, 10, 5))
        self.assertEqual(tuple(row.entry_state.previous_applied for row in r.steps), (-2, 2, -2))
        self.assertEqual(asdict(frames[1]), before)

    def test_entry_and_output_differences_have_separate_literal_roles(self):
        r = self.run_case(*self.cases.build_case('declared-difference'))
        self.assertEqual(tuple((d.field, d.declared, d.computed) for d in r.steps[0].output_differences), (('saved_limited_state', 10, 2),))
        self.assertEqual(tuple((d.field, d.declared, d.computed) for d in r.steps[1].entry_differences), (('entry_previous_applied', 10, 2),))
        self.assertEqual(tuple((d.field, d.declared, d.computed) for d in r.steps[1].output_differences), (('saved_limited_state', 5, -2),))
        self.assertEqual(tuple((d.field, d.declared, d.computed) for d in r.steps[2].output_differences), (('saved_limited_state', 4, 2),))

    def test_existing_core7_still_uses_declared_entry_diagnostics(self):
        old = importlib.import_module('integration_tools.synthetic_sequence_check')
        frames, contexts = self.cases.build_case('declared-difference'); result = old.check_synthetic_sequence(frames, contexts)
        self.assertEqual(tuple(r.computed_next_state.previous_applied for r in result.checks), (2, 5, 4))
        self.assertEqual(result.differing_transition_indices, (0,)); self.assertFalse(result.first_frame_transition_checked)
        self.assertEqual(tuple(r.output.next_state.previous_applied for r in self.run_case(frames, contexts).steps), (2, -2, 2))

    def test_difference_can_be_followed_by_matching_computed_chain_without_repair(self):
        frames = (self.frames[0], replace(self.frames[1], saved_limited_state=10), replace(self.frames[2], limited_state_at_entry=10), self.frames[3])
        r = self.run_case(frames)
        self.assertEqual(tuple(row.status for row in r.steps), ('DIFFERENT', 'DIFFERENT', 'MATCH'))
        self.assertEqual(r.entry_differing_transition_indices, (1,)); self.assertEqual(r.output_differing_transition_indices, (0,))

    def test_counter_divergence_is_not_fed_to_later_model_calls(self):
        frames = (self.frames[0], replace(self.frames[1], saved_angle_counter=10),
            replace(self.frames[2], angle_counter_at_entry=10, saved_angle_counter=20), replace(self.frames[3], angle_counter_at_entry=20, saved_angle_counter=30))
        r = self.run_case(frames)
        self.assertEqual(tuple(row.output.next_state.angle_counter for row in r.steps), (5, 6, 7))
        self.assertEqual(tuple(row.entry_state.angle_counter for row in r.steps), (4, 5, 6))
        self.assertEqual(tuple((d.field, d.declared, d.computed) for d in r.steps[1].entry_differences), (('entry_angle_counter', 10, 5),))

    def test_all_difference_fields_are_complete_and_stably_ordered(self):
        frames = (self.frames[0], replace(self.frames[1], saved_limited_state=10, saved_angle_counter=10),
            replace(self.frames[2], limited_state_at_entry=10, angle_counter_at_entry=10, saved_limited_state=5, saved_angle_counter=20),
            replace(self.frames[3], limited_state_at_entry=5, angle_counter_at_entry=20, saved_limited_state=4, saved_angle_counter=30))
        r = self.run_case(frames)
        self.assertEqual(tuple(d.field for d in r.steps[1].entry_differences), ('entry_previous_applied', 'entry_angle_counter'))
        self.assertEqual(tuple(d.field for d in r.steps[1].output_differences), ('saved_limited_state', 'saved_angle_counter'))
        self.assertEqual(r.differing_transition_indices, (0, 1, 2))

    def test_inactive_output_and_counter_are_fed_into_resumed_step(self):
        frames = (self.frames[0], self.frames[1], replace(self.frames[2], request=replace(self.frames[2].request, request_active=False), inactive_gate_active=False, saved_limited_state=0, saved_angle_counter=0),
            replace(self.frames[3], limited_state_at_entry=0, angle_counter_at_entry=0, saved_angle_counter=1))
        r = self.run_case(frames)
        self.assertEqual(self.states(r), ((6, 8, 2, 5), (7, -8, 0, 0), (8, 4, 2, 1)))
        self.assertEqual(r.status, 'MATCH'); self.assertEqual(tuple(row.output.steer_request for row in r.steps), (True, False, True))

    def test_fault_counter_boundary_uses_computed_eighty_nine_ninety_zero(self):
        frames = (replace(self.frames[0], saved_angle_counter=88), replace(self.frames[1], angle_counter_at_entry=88, saved_angle_counter=89),
            replace(self.frames[2], angle_counter_at_entry=89, saved_angle_counter=90), replace(self.frames[3], angle_counter_at_entry=90, saved_angle_counter=0))
        r = self.run_case(frames)
        self.assertEqual(tuple(row.output.next_state.angle_counter for row in r.steps), (89, 90, 0))
        self.assertEqual(tuple(row.output.steer_request for row in r.steps), (True, False, False)); self.assertEqual(r.status, 'MATCH')

    def test_minimum_is_one_nonvacuous_step_and_anchor_is_unproven(self):
        r, calls = self.profiled(lambda: self.run_case(self.frames[:2], self.contexts[:1]))
        self.assertEqual((r.synthetic_model_steps, r.checked_transition_count, len(calls)), (1, 1, 1))
        self.assertFalse(r.first_frame_transition_checked); self.assertFalse(r.prehistory_checked)

    def test_maximum_frames_and_last_model_index_are_supported(self):
        seed = self.frames[0]; frames = tuple(replace(seed, request=replace(seed.request, sequence=i, sample_time_ns=1_000_000_000 + i * 10_000_000, requested_binary32=bytes(4)),
            limited_state_at_entry=0, saved_limited_state=0, angle_counter_at_entry=0, saved_angle_counter=0) for i in range(4096))
        contexts = tuple(replace(self.contexts[0], model_index=i + 1, previous_integer_request=0, current_driver=0.0, current_angle_deg=0.0) for i in range(4095))
        r = self.run_case(frames, contexts)
        self.assertEqual((r.status, r.synthetic_model_steps, r.final_computed_state.index), ('MATCH', 4095, 4096))

    def test_bad_containers_do_not_invoke_foreign_iteration(self):
        class Foreign:
            def __iter__(self): raise AssertionError('iterated')
            def __len__(self): raise AssertionError('length')
        class Child(tuple): pass
        for value in (None, [], {}, Foreign(), Child(self.frames)):
            self.reject('ROLLOUT_CONTAINER', value, self.contexts)
            self.reject('ROLLOUT_CONTAINER', self.frames, value)

    def test_empty_single_oversize_or_misaligned_inputs_reject(self):
        for frames, contexts in (((), ()), (self.frames[:1], ()), (self.frames, self.contexts[:2]),
            (self.frames, (*self.contexts, self.contexts[0])), ((self.frames[0],) * 4097, (self.contexts[0],) * 4096)):
            self.reject('ROLLOUT_COUNT', frames, contexts)

    def test_foreign_frame_and_context_members_do_not_invoke_getters(self):
        class Foreign:
            def __getattribute__(self, name): raise AssertionError('getter')
        self.reject('ROLLOUT_INPUT:2:MODEL_LIMITER:LIMITER_SNAPSHOT_TYPE', (*self.frames[:3], Foreign()), self.contexts)
        self.reject('ROLLOUT_INPUT:2:MODEL_CONTEXT_TYPE', self.frames, (*self.contexts[:2], Foreign()))

    def test_late_invalid_case_rejects_before_any_public_step(self):
        self.reject('ROLLOUT_INPUT:2:MODEL_DRIVER', *self.cases.build_case('late-invalid'))

    def test_full_input_preflight_precedes_model_order_check(self):
        contexts = (self.contexts[0], replace(self.contexts[1], model_index=9), replace(self.contexts[2], current_angle_deg=0.1))
        self.reject('ROLLOUT_INPUT:2:MODEL_ANGLE', self.frames, contexts)

    def test_model_order_gap_repeat_and_reverse_are_not_repaired(self):
        for index in (5, 4, 7): self.reject('ROLLOUT_MODEL_ORDER:1', self.frames, (self.contexts[0], replace(self.contexts[1], model_index=index), self.contexts[2]))

    def test_model_index_not_derived_from_capture_sequence_or_time(self):
        contexts = tuple(replace(c, model_index=c.model_index + 100) for c in self.contexts); r = self.run_case(contexts=contexts)
        self.assertEqual(tuple(row.output.next_state.index for row in r.steps), (106, 107, 108))
        self.assertEqual(tuple(f.request.sequence for f in r.frames), (0, 1, 2, 3))

    def test_late_settings_state_counter_links_reject_without_steps(self):
        for frame, suffix in ((replace(self.frames[-1], limited_state_at_entry=5), 'LIMITER_PAIR_STATE_LINK'),
            (replace(self.frames[-1], angle_counter_at_entry=8), 'LIMITER_PAIR_COUNTER_LINK'),
            (replace(self.frames[-1], settings=replace(self.frames[-1].settings, delta_down=6)), 'LIMITER_PAIR_SETTINGS')):
            self.reject('ROLLOUT_INPUT:2:MODEL_LIMITER:' + suffix, (*self.frames[:3], frame), self.contexts)

    def test_late_reset_time_and_epoch_are_not_bridged(self):
        request = self.frames[-1].request
        for changed, suffix in ((replace(request, reset_since_previous=True), 'REQUEST_PAIR_RESET'),
            (replace(request, sample_time_ns=self.frames[-2].request.sample_time_ns), 'REQUEST_PAIR_TIME'),
            (replace(request, context=replace(request.context, capture_epoch_id='new')), 'REQUEST_PAIR_CONTEXT')):
            self.reject('ROLLOUT_INPUT:2:MODEL_LIMITER:LIMITER_REQUEST:' + suffix, (*self.frames[:3], replace(self.frames[-1], request=changed)), self.contexts)

    def test_late_previous_request_override_and_active_mismatch_reject(self):
        self.reject('ROLLOUT_INPUT:2:MODEL_PREVIOUS_REQUEST_MISMATCH', self.frames, (*self.contexts[:2], replace(self.contexts[2], previous_integer_request=0)))
        self.reject('ROLLOUT_INPUT:2:MODEL_OVERRIDE', (*self.frames[:3], replace(self.frames[-1], request=replace(self.frames[-1].request, request_override=True))), self.contexts)
        self.reject('ROLLOUT_INPUT:2:MODEL_ACTIVE_READS', (*self.frames[:3], replace(self.frames[-1], request=replace(self.frames[-1].request, request_active=False))), self.contexts)

    def test_model_failure_after_prefix_reports_work_uncertainty_and_stops(self):
        original = self.model.step; calls = []
        def stepping(sample, state):
            calls.append(state)
            if len(calls) == 2: raise ValueError('PRIVATE')
            return original(sample, state)
        with patch.object(self.model, 'step', side_effect=stepping), self.assertRaises(self.m.SequenceRolloutError) as found: self.run_case()
        self.assertEqual(found.exception.code, 'ROLLOUT_MODEL_FAILURE:1:WORK_MAY_BE_NONZERO'); self.assertEqual(len(calls), 2)

    def test_malformed_model_output_or_next_state_never_returns_result(self):
        prep = importlib.import_module('integration_tools.synthetic_model_input').prepare_model_input(self.frames[0], self.frames[1], self.contexts[0])
        valid = self.model.step(prep.model_input, prep.model_state)
        invalid = (None, object(), replace(valid, next_state=object()), replace(valid, next_state=replace(valid.next_state, index=7)),
            replace(valid, next_state=replace(valid.next_state, previous_requested=True)),
            replace(valid, next_state=replace(valid.next_state, previous_applied=2049)), replace(valid, next_state=replace(valid.next_state, angle_counter=91)))
        for output in invalid:
            with self.subTest(output=type(output)), patch.object(self.model, 'step', return_value=output), self.assertRaises(self.m.SequenceRolloutError) as found: self.run_case()
            self.assertEqual(found.exception.code, 'ROLLOUT_MODEL_RESULT:0:TRANSITION_MODEL_RESULT:WORK_MAY_BE_NONZERO')

    def test_unexpected_model_exception_propagates_without_retry(self):
        calls = []
        def stepping(*args): calls.append(1); raise AssertionError('unexpected')
        with patch.object(self.model, 'step', side_effect=stepping), self.assertRaisesRegex(AssertionError, 'unexpected'): self.run_case()
        self.assertEqual(calls, [1])

    def test_inputs_and_contexts_are_preserved_without_repair(self):
        frames, contexts = self.cases.build_case('declared-difference'); before = tuple(asdict(f) for f in frames), tuple(asdict(c) for c in contexts)
        r = self.run_case(frames, contexts); self.assertIs(r.frames, frames); self.assertIs(r.contexts, contexts)
        self.assertEqual(before, (tuple(asdict(f) for f in frames), tuple(asdict(c) for c in contexts)))
        for index, row in enumerate(r.steps): self.assertIs(row.prepared.current, frames[index + 1]); self.assertIs(row.prepared.context, contexts[index])

    def test_previous_requested_entry_difference_is_reported_not_hidden(self):
        original = self.model.step; calls = []
        def stepping(sample, state):
            output = original(sample, state); calls.append(1)
            return replace(output, next_state=replace(output.next_state, previous_requested=7)) if len(calls) == 1 else output
        with patch.object(self.model, 'step', side_effect=stepping): r = self.run_case()
        self.assertEqual(tuple((d.field, d.declared, d.computed) for d in r.steps[1].entry_differences), (('entry_previous_requested', 8, 7),))
        self.assertEqual(r.entry_differing_transition_indices, (1,)); self.assertEqual(r.status, 'DIFFERENT')

    def test_direct_constructor_and_replace_repeat_the_full_computation(self):
        r, calls = self.profiled(lambda: self.m.SyntheticSequenceRolloutV1(self.frames, self.contexts))
        other, again = self.profiled(lambda: replace(r)); self.assertEqual(asdict(r), asdict(other))
        self.assertEqual((len(calls), len(again)), (3, 3))

    def test_derived_fields_cannot_be_injected_and_records_are_frozen(self):
        constructor: Any = self.m.SyntheticSequenceRolloutV1
        with self.assertRaises(TypeError): constructor(self.frames, self.contexts, status='MATCH')
        r = self.run_case()
        for obj, field, value in ((r, 'status', 'OTHER'), (r.steps[0], 'status', 'OTHER')):
            with self.assertRaises(FrozenInstanceError): setattr(obj, field, value)
        d = self.run_case(*self.cases.build_case('declared-difference')).steps[0].output_differences[0]
        with self.assertRaises(FrozenInstanceError): d.computed = 10

    def test_result_subclass_rejects_before_steps(self):
        class Child(self.m.SyntheticSequenceRolloutV1): pass
        with patch.object(self.model, 'step', side_effect=AssertionError('step')), self.assertRaises(self.m.SequenceRolloutError) as found: Child(self.frames, self.contexts)
        self.assertEqual(found.exception.code, 'ROLLOUT_TYPE')

    def test_claims_and_flags_never_promote_seed_to_source_or_vehicle_authority(self):
        r = self.run_case()
        self.assertEqual((r.contract_id, r.state_feed_rule), ('CORE27_COUNTERFACTUAL_COMPUTED_STATE_ROLLOUT_V1', 'FIRST_DECLARED_ENTRY_THEN_COMPUTED_NEXT_STATE_NO_RESEED'))
        self.assertTrue(r.computed_state_fed)
        for name in ('first_frame_transition_checked', 'prehistory_checked', 'source_identity_reauthenticated', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'): self.assertIs(getattr(r, name), False)

    def test_no_io_controller_runtime_f61_or_rate_policy_work(self):
        old = sys.getprofile()
        def profile(frame, event, arg):
            module = frame.f_globals.get('__name__', '')
            if event == 'call' and module.startswith(('integration_tools.f61_', 'openpilot', 'opendbc')): raise AssertionError('external work')
        try:
            sys.setprofile(profile)
            with patch('builtins.open', side_effect=AssertionError('open')), patch('os.open', side_effect=AssertionError('open')), \
                    patch.object(os, 'write', side_effect=AssertionError('write')), patch.object(os, 'mkdir', side_effect=AssertionError('mkdir')): r = self.run_case()
        finally: sys.setprofile(old)
        self.assertEqual(r.synthetic_model_steps, 3)
