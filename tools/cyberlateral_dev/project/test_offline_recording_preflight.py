"""Recording preservation must not imply executable input or output arithmetic parity."""

import importlib
import sys
import unittest
from dataclasses import FrozenInstanceError, fields, replace
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


class RecordingPreflightTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/offline_recording_preflight.py').is_file(), 'Missing CORE46 recording preflight')
        self.model = package_feature()
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.offline_recording_preflight')
        self.recorder = importlib.import_module('integration_tools.offline_call_recorder')
        self.inputs = importlib.import_module('integration_tools.synthetic_model_input')
        self.request = importlib.import_module('integration_tools.request_snapshot')
        self.limiter = importlib.import_module('integration_tools.limiter_snapshot')
        self.codec = importlib.import_module('integration_tools.offline_recording_codec')
        self.recording, self.contexts = self.fixture()

    def fixture(self):
        context = self.request.SyntheticRequestContextV1(1, 'COUNTERFACTUAL_REQUEST_SNAPSHOT_ONLY',
            'CORE3_COUNTERFACTUAL_REQUEST_SOURCE_V1', 'fixture-capture', 'fixture-controller', 'fixture-config',
            'DECLARED_LIVE_MONOTONIC_NS', 'DECLARED_TORQUE_CONTROL', 'REQUESTED_NORMALIZED_BEFORE_INTEGER_LIMITER', 0, 0)
        settings = self.limiter.SyntheticConsumedSettingsV1(16, 16, 2, 5, 7, 1, 3)
        frames = []
        for seq, word, entry, saved, counter, next_counter in (
            (7, 'be800000', 7, -2, 3, 4), (8, '3f000000', -2, 2, 4, 5),
            (9, 'bf000000', 2, -2, 5, 6), (10, '3e800000', -2, 2, 6, 7),
        ):
            request = self.request.SyntheticRequestSnapshotV1(context, seq, seq - 16, bytes.fromhex(word), True, False, False)
            frames.append(self.limiter.SyntheticLimiterSnapshotV1(request, settings, 'DECLARED_LIMITED_STATE_POST_INACTIVE_GATE',
                'DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS', entry, saved, counter, next_counter, True))
        contexts = tuple(self.inputs.SyntheticModelContextV1('COUNTERFACTUAL_MODEL_INPUT_ONLY', index, previous, 1.5, 85.0)
                         for index, previous in ((5, -4), (6, 8), (7, -8)))
        return self.recorder.FinishedSyntheticRecordingV1(tuple(frames)), contexts

    def reject(self, recording, contexts, code, direct=False):
        call = self.m.SyntheticRecordingInputPreflightV1 if direct else self.m.preflight_recording_input
        with self.assertRaises(self.m.RecordingPreflightError) as caught:
            call(recording, contexts)
        self.assertEqual((caught.exception.code, str(caught.exception)), (code, code))
        return caught.exception

    def changed_recording(self, *frames):
        return self.recorder.FinishedSyntheticRecordingV1(tuple(frames))

    def maximum(self):
        first = self.recording.records[0]
        records = tuple(replace(first, request=replace(first.request, sequence=1000 + i, sample_time_ns=-(1 << 63) + i,
            requested_binary32=bytes.fromhex('80000000')), limited_state_at_entry=0, saved_limited_state=0,
            angle_counter_at_entry=0, saved_angle_counter=0) for i in range(128))
        contexts = tuple(replace(self.contexts[0], model_index=3969 + i, previous_integer_request=0,
            current_driver=0.0, current_angle_deg=0.0) for i in range(127))
        return self.changed_recording(*records), contexts

    def test_four_frames_preserve_explicit_contexts_and_distinct_request_state_roles(self):
        result = self.m.preflight_recording_input(self.recording, self.contexts)
        self.assertEqual((result.status, result.record_count, result.validated_transition_count), ('INPUTS_COMPATIBLE', 4, 3))
        self.assertIs(result.recording, self.recording)
        self.assertIs(result.contexts, self.contexts)
        self.assertEqual(tuple(c.previous_integer_request for c in result.contexts), (-4, 8, -8))
        self.assertEqual(tuple(f.limited_state_at_entry for f in result.recording.records), (7, -2, 2, -2))
        self.assertEqual(tuple(c.model_index for c in result.contexts), (5, 6, 7))
        self.assertEqual(tuple(f.request.sequence for f in result.recording.records), (7, 8, 9, 10))

    def test_two_frames_are_one_nonvacuous_validation(self):
        result = self.m.preflight_recording_input(self.changed_recording(*self.recording.records[:2]), self.contexts[:1])
        self.assertEqual((result.record_count, result.validated_transition_count), (2, 1))

    def test_maximum_recording_validates_all_127_contexts_and_explicit_upper_index(self):
        recording, contexts = self.maximum()
        result = self.m.preflight_recording_input(recording, contexts)
        self.assertEqual((result.record_count, result.validated_transition_count), (128, 127))
        self.assertEqual((result.contexts[0].model_index, result.contexts[-1].model_index), (3969, 4095))
        self.assertEqual(result.recording.records[-1].request.requested_binary32.hex(), '80000000')

    def test_last_context_of_maximum_is_not_silently_skipped(self):
        recording, contexts = self.maximum()
        self.reject(recording, (*contexts[:-1], replace(contexts[-1], model_index=4096)), 'RECORDING_PREFLIGHT_INPUT:126:MODEL_INDEX')

    def test_contexts_and_policy_values_have_no_defaults_or_constructor_backdoor(self):
        with self.assertRaises(TypeError):
            self.m.preflight_recording_input(self.recording)
        with self.assertRaises(TypeError):
            self.m.SyntheticRecordingInputPreflightV1(self.recording)
        for name in ('dt', 'rate_budget_per_s', 'T2', 'actual_scale', 'model_input_allowed', 'validated_transition_count'):
            with self.assertRaises(TypeError):
                self.m.SyntheticRecordingInputPreflightV1(self.recording, self.contexts, **{name: 0})

    def test_foreign_recording_and_hostile_subclass_reject_before_attribute_reads(self):
        class Foreign:
            def __getattribute__(self, _name):
                raise AssertionError('READ_FOREIGN_RECORDING')

        class Child(self.recorder.FinishedSyntheticRecordingV1):
            def __getattribute__(self, _name):
                raise AssertionError('READ_CHILD_RECORDING')

        child = object.__new__(Child)
        for invalid in (None, {}, b'{}', Foreign(), child):
            self.reject(invalid, self.contexts, 'RECORDING_PREFLIGHT_RECORDING:RECORDER_RECORDING_TYPE')

    def test_context_container_rejects_lists_generators_and_hostile_tuple_subclasses(self):
        class Foreign:
            def __iter__(self):
                raise AssertionError('ITERATED_FOREIGN')

            def __len__(self):
                raise AssertionError('READ_FOREIGN_LENGTH')

        class Child(tuple):
            def __iter__(self):
                raise AssertionError('ITERATED_CHILD')

            def __len__(self):
                raise AssertionError('READ_CHILD_LENGTH')

        for invalid in (None, {}, list(self.contexts), iter(self.contexts), Foreign(), Child(self.contexts)):
            self.reject(self.recording, invalid, 'RECORDING_PREFLIGHT_CONTEXT_CONTAINER')

    def test_missing_extra_or_empty_contexts_reject_before_partial_preparation(self):
        for invalid in ((), self.contexts[:1], self.contexts[:2], (*self.contexts, self.contexts[0])):
            self.reject(self.recording, invalid, 'RECORDING_PREFLIGHT_CONTEXT_COUNT')

    def test_foreign_and_hostile_context_members_reject_before_leaf_reads(self):
        class Foreign:
            def __getattribute__(self, _name):
                raise AssertionError('READ_FOREIGN_CONTEXT')

        class Child(self.inputs.SyntheticModelContextV1):
            def __getattribute__(self, _name):
                raise AssertionError('READ_CHILD_CONTEXT')

        child = Child('COUNTERFACTUAL_MODEL_INPUT_ONLY', 7, -8, 1.5, 85.0)
        for invalid in (None, {}, Foreign(), child):
            self.reject(self.recording, (*self.contexts[:2], invalid), 'RECORDING_PREFLIGHT_INPUT:2:MODEL_CONTEXT_TYPE')

    def test_actual_scope_is_not_promoted_by_valid_synthetic_recording(self):
        self.reject(self.recording, (*self.contexts[:2], replace(self.contexts[2], scope='ACTUAL_VEHICLE')),
                    'RECORDING_PREFLIGHT_INPUT:2:MODEL_SCOPE')

    def test_previous_limited_or_saved_state_cannot_substitute_for_previous_request(self):
        for invalid in (-2, 2, 7):
            self.reject(self.recording, (replace(self.contexts[0], previous_integer_request=invalid), *self.contexts[1:]),
                        'RECORDING_PREFLIGHT_INPUT:0:MODEL_PREVIOUS_REQUEST_MISMATCH')

    def test_core5_primitive_types_and_numeric_domains_are_not_coerced(self):
        for field_name, invalid, suffix in (
            ('model_index', True, 'MODEL_INDEX'), ('model_index', 5.0, 'MODEL_INDEX'),
            ('previous_integer_request', -4.0, 'MODEL_PREVIOUS_REQUEST'), ('previous_integer_request', True, 'MODEL_PREVIOUS_REQUEST'),
            ('current_driver', 1, 'MODEL_DRIVER'), ('current_driver', float('nan'), 'MODEL_DRIVER'),
            ('current_driver', 0.1, 'MODEL_DRIVER'), ('current_angle_deg', 85, 'MODEL_ANGLE'),
            ('current_angle_deg', float('inf'), 'MODEL_ANGLE'), ('current_angle_deg', 180.5, 'MODEL_ANGLE'),
        ):
            with self.subTest(field=field_name, suffix=suffix):
                self.reject(self.recording, (replace(self.contexts[0], **{field_name: invalid}), *self.contexts[1:]),
                            'RECORDING_PREFLIGHT_INPUT:0:' + suffix)

    def test_model_index_gap_rejects_even_when_each_input_is_individually_valid(self):
        self.reject(self.recording, (self.contexts[0], replace(self.contexts[1], model_index=7), replace(self.contexts[2], model_index=8)),
                    'RECORDING_PREFLIGHT_MODEL_ORDER:1')

    def test_late_invalid_input_precedes_earlier_model_order_gap(self):
        contexts = (self.contexts[0], replace(self.contexts[1], model_index=7), replace(self.contexts[2], current_driver=0.1))
        self.reject(self.recording, contexts, 'RECORDING_PREFLIGHT_INPUT:2:MODEL_DRIVER')

    def test_forged_recording_permissions_are_revalidated_before_context_container(self):
        for name in ('model_input_allowed', 'source_identity_reauthenticated', 'f61_input_allowed', 'actual_activation_allowed'):
            recording = self.changed_recording(*self.recording.records)
            object.__setattr__(recording, name, True)
            self.reject(recording, None, 'RECORDING_PREFLIGHT_RECORDING:RECORDER_METADATA')

    def test_changed_record_links_and_request_scope_are_not_trusted_after_construction(self):
        last = self.recording.records[-1]
        for changed, suffix in (
            (replace(last, limited_state_at_entry=3), 'LIMITER_PAIR_STATE_LINK'),
            (replace(last, angle_counter_at_entry=3), 'LIMITER_PAIR_COUNTER_LINK'),
            (replace(last, settings=replace(last.settings, delta_up=3)), 'LIMITER_PAIR_SETTINGS'),
        ):
            recording = self.changed_recording(*self.recording.records)
            object.__setattr__(recording, 'records', (*recording.records[:-1], changed))
            self.reject(recording, self.contexts, 'RECORDING_PREFLIGHT_RECORDING:RECORDER_LIMITER:' + suffix)
        recording = self.changed_recording(*self.recording.records)
        bad_request = replace(last.request, context=replace(last.request.context, scope='ACTUAL_PRODUCTION'))
        object.__setattr__(recording, 'records', (*recording.records[:-1], replace(last, request=bad_request)))
        self.reject(recording, self.contexts, 'RECORDING_PREFLIGHT_RECORDING:RECORDER_REQUEST:REQUEST_SCOPE')

    def test_override_and_different_active_reads_remain_distinct_rejections(self):
        first, *later = self.recording.records
        overridden = self.changed_recording(replace(first, request=replace(first.request, request_override=True)), *later)
        self.reject(overridden, self.contexts, 'RECORDING_PREFLIGHT_INPUT:0:MODEL_OVERRIDE')
        last = self.recording.records[-1]
        mismatch = self.changed_recording(*self.recording.records[:-1], replace(last, request=replace(last.request, request_active=False)))
        self.reject(mismatch, self.contexts, 'RECORDING_PREFLIGHT_INPUT:2:MODEL_ACTIVE_READS')

    def test_inactive_final_call_is_compatible_only_with_matching_read_and_saved_zero(self):
        last = self.recording.records[-1]
        inactive = replace(last, request=replace(last.request, request_active=False), inactive_gate_active=False, saved_limited_state=0)
        recording = self.changed_recording(*self.recording.records[:-1], inactive)
        result = self.m.preflight_recording_input(recording, self.contexts)
        self.assertEqual(result.status, 'INPUTS_COMPATIBLE')
        self.assertFalse(result.recording.records[-1].inactive_gate_active)
        self.assertEqual(result.recording.records[-1].saved_limited_state, 0)
        self.assertFalse(result.actual_activation_allowed)

    def test_raw_zero_subnormal_and_auxiliary_signed_zero_are_preserved(self):
        for word in ('80000000', '00000000', '00000001', '80000001'):
            first = replace(self.recording.records[0], request=replace(self.recording.records[0].request, requested_binary32=bytes.fromhex(word)))
            recording = self.changed_recording(first, *self.recording.records[1:])
            contexts = (replace(self.contexts[0], previous_integer_request=0, current_driver=-0.0, current_angle_deg=-0.0), *self.contexts[1:])
            before = self.codec.encode_recording(recording)
            result = self.m.preflight_recording_input(recording, contexts)
            self.assertEqual(result.recording.records[0].request.requested_binary32.hex(), word)
            self.assertEqual((result.contexts[0].current_driver.hex(), result.contexts[0].current_angle_deg.hex()), ('-0x0.0p+0', '-0x0.0p+0'))
            self.assertEqual(self.codec.encode_recording(recording), before)

    def test_int64_time_extremes_are_order_metadata_not_seconds_or_period(self):
        first, second = self.recording.records[:2]
        recording = self.changed_recording(replace(first, request=replace(first.request, sample_time_ns=-(1 << 63))),
                                           replace(second, request=replace(second.request, sample_time_ns=(1 << 63) - 1)))
        result = self.m.preflight_recording_input(recording, self.contexts[:1])
        self.assertEqual(tuple(f.request.sample_time_ns for f in result.recording.records), (-(1 << 63), (1 << 63) - 1))
        self.assertEqual(result.time_semantics, 'ORDER_ONLY_NO_DELTA_OR_PERIOD')
        for name in ('dt', 'seconds', 'rate_budget_per_s', 'T2', 'vehicle_scale', 'model_input', 'model_state', 'prepared'):
            self.assertFalse(hasattr(result, name))

    def test_live_and_replay_clock_declarations_remain_unqualified(self):
        for clock in ('DECLARED_LIVE_MONOTONIC_NS', 'DECLARED_REPLAY_RECORDED_CAN_NS'):
            recording = self.changed_recording(*(replace(f, request=replace(f.request,
                context=replace(f.request.context, clock_domain=clock))) for f in self.recording.records))
            result = self.m.preflight_recording_input(recording, self.contexts)
            self.assertEqual(result.recording.records[0].request.context.clock_domain, clock)
            self.assertFalse(result.source_identity_reauthenticated)

    def test_compatible_does_not_recompute_or_repair_arithmetically_different_saved_declarations(self):
        first, second, third, fourth = self.recording.records
        recording = self.changed_recording(first, replace(second, saved_limited_state=10),
            replace(third, limited_state_at_entry=10, saved_limited_state=5), replace(fourth, limited_state_at_entry=5, saved_limited_state=4))
        result = self.m.preflight_recording_input(recording, self.contexts)
        self.assertEqual((result.status, result.validated_transition_count), ('INPUTS_COMPATIBLE', 3))
        self.assertEqual(tuple(f.saved_limited_state for f in result.recording.records), (-2, 10, 5, 4))
        self.assertEqual(result.validation_claim, 'DECLARED_INPUT_COMPATIBILITY_NOT_OUTPUT_PARITY_OR_SOURCE_PROOF')
        self.assertFalse(result.first_frame_transition_checked)
        self.assertFalse(result.prehistory_checked)

    def test_direct_constructor_and_replace_revalidate_instead_of_copying_success(self):
        result = self.m.SyntheticRecordingInputPreflightV1(self.recording, self.contexts)
        self.assertEqual(result.validated_transition_count, 3)
        with self.assertRaises(self.m.RecordingPreflightError) as caught:
            replace(result, contexts=(*self.contexts[:2], replace(self.contexts[2], current_driver=0.1)))
        self.assertEqual(caught.exception.code, 'RECORDING_PREFLIGHT_INPUT:2:MODEL_DRIVER')
        self.reject(self.recording, (), 'RECORDING_PREFLIGHT_CONTEXT_COUNT', direct=True)

    def test_result_is_frozen_and_permissions_cannot_be_supplied(self):
        result = self.m.preflight_recording_input(self.recording, self.contexts)
        with self.assertRaises(FrozenInstanceError):
            result.record_count = 0
        for name in ('first_frame_transition_checked', 'prehistory_checked', 'source_identity_reauthenticated',
                     'model_input_allowed', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
            self.assertIs(getattr(result, name), False)
            with self.assertRaises(TypeError):
                self.m.SyntheticRecordingInputPreflightV1(self.recording, self.contexts, **{name: True})
        self.assertEqual((result.new_synthetic_model_steps, result.new_reference_steps, result.numeric_validation_work),
                         (0, 0, 'NONZERO_NOT_AGGREGATED'))

    def test_result_subclass_rejects_before_attribute_reads(self):
        class Child(self.m.SyntheticRecordingInputPreflightV1):
            def __getattribute__(self, _name):
                raise AssertionError('READ_CHILD_RESULT')

        with self.assertRaises(self.m.RecordingPreflightError) as caught:
            Child(self.recording, self.contexts)
        self.assertEqual(caught.exception.code, 'RECORDING_PREFLIGHT_TYPE')

    def test_success_and_late_rejection_execute_no_real_model_entry_point(self):
        codes = (self.model.step.__code__, self.model.simulate.__code__)
        calls = []

        def profile(frame, event, _arg):
            if event == 'call' and frame.f_code in codes:
                calls.append(frame.f_code.co_name)

        old = sys.getprofile()
        try:
            sys.setprofile(profile)
            result = self.m.preflight_recording_input(self.recording, self.contexts)
            self.reject(self.recording, (*self.contexts[:2], replace(self.contexts[2], current_driver=0.1)),
                        'RECORDING_PREFLIGHT_INPUT:2:MODEL_DRIVER')
        finally:
            sys.setprofile(old)
        self.assertEqual((result.status, calls), ('INPUTS_COMPATIBLE', []))

    def test_unexpected_dependency_exception_propagates_without_false_compatibility(self):
        failure = RuntimeError('opaque dependency failure')
        with patch.object(self.m, 'prepare_model_input', side_effect=failure):
            with self.assertRaises(RuntimeError) as caught:
                self.m.preflight_recording_input(self.recording, self.contexts)
        self.assertIs(caught.exception, failure)

    def test_failed_call_does_not_mutate_recording_or_export_a_successful_prefix(self):
        before = self.codec.encode_recording(self.recording)
        error = self.reject(self.recording, (*self.contexts[:2], replace(self.contexts[2], current_angle_deg=0.1)),
                            'RECORDING_PREFLIGHT_INPUT:2:MODEL_ANGLE')
        self.assertFalse(hasattr(error, 'recording'))
        self.assertFalse(hasattr(error, 'validated_transition_count'))
        result = self.m.preflight_recording_input(self.recording, self.contexts)
        self.assertEqual(result.validated_transition_count, 3)
        self.assertEqual(self.codec.encode_recording(self.recording), before)
        self.assertEqual({f.name for f in fields(result) if f.init}, {'recording', 'contexts'})
