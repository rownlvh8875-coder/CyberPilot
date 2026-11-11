"""Catch lost transaction boundaries, inferred roles and usable failed prefixes."""
import importlib
import sys
import unittest
from dataclasses import FrozenInstanceError, replace
from typing import Any

from v1_helpers import ROOT

sys.path.insert(0, str(ROOT))

from integration_tools.limiter_snapshot import SyntheticConsumedSettingsV1, SyntheticLimiterSnapshotV1
from integration_tools.request_snapshot import SyntheticRequestContextV1, SyntheticRequestSnapshotV1


def frames():
    context = SyntheticRequestContextV1(1, 'COUNTERFACTUAL_REQUEST_SNAPSHOT_ONLY',
        'CORE3_COUNTERFACTUAL_REQUEST_SOURCE_V1', 'fixture-capture', 'fixture-controller', 'fixture-config',
        'DECLARED_LIVE_MONOTONIC_NS', 'DECLARED_TORQUE_CONTROL', 'REQUESTED_NORMALIZED_BEFORE_INTEGER_LIMITER', 0, 0)
    first = SyntheticRequestSnapshotV1(context, 7, -9, bytes.fromhex('80000000'), True, False, True)
    second = SyntheticRequestSnapshotV1(context, 8, -8, bytes.fromhex('00000001'), False, False, False)
    settings = SyntheticConsumedSettingsV1(16, 16, 2, 5, 7, 1, 3)
    return (SyntheticLimiterSnapshotV1(first, settings, 'DECLARED_LIMITED_STATE_POST_INACTIVE_GATE',
        'DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS', 12, -2, 3, 4, True),
        SyntheticLimiterSnapshotV1(second, settings, 'DECLARED_LIMITED_STATE_POST_INACTIVE_GATE',
        'DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS', -2, 4, 4, 5, True))


class RecorderTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/offline_call_recorder.py').is_file(), 'Missing CORE41 recorder')
        self.m: Any = importlib.import_module('integration_tools.offline_call_recorder')
        self.first, self.second = frames()

    def reject(self, operation, code):
        with self.assertRaises(self.m.RecorderError) as caught:
            operation()
        self.assertEqual((caught.exception.code, str(caught.exception)), (code, code))

    def complete_two(self, capacity=2):
        recorder = self.m.SyntheticCallRecorderV1(capacity)
        for frame in (self.first, self.second):
            recorder.begin(frame.request)
            recorder.complete(frame)
        return recorder

    def test_complete_transactions_preserve_distinct_raw_request_and_state_roles(self):
        result = self.complete_two().finish()
        self.assertEqual(tuple(x.request.requested_binary32.hex() for x in result.records), ('80000000', '00000001'))
        self.assertEqual(tuple((x.limited_state_at_entry, x.saved_limited_state) for x in result.records), ((12, -2), (-2, 4)))
        self.assertEqual(tuple((x.request.sequence, x.request.sample_time_ns) for x in result.records), ((7, -9), (8, -8)))
        self.assertFalse(result.records[1].request.request_active)
        self.assertTrue(result.records[1].inactive_gate_active)
        self.assertFalse(hasattr(result, 'dt'))

    def test_finished_result_is_frozen_and_cannot_grant_permissions(self):
        result = self.complete_two().finish()
        with self.assertRaises(FrozenInstanceError):
            result.records = ()
        for name in ('source_identity_reauthenticated', 'model_input_allowed', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
            self.assertIs(getattr(result, name), False)
            with self.assertRaises(TypeError):
                self.m.FinishedSyntheticRecordingV1(result.records, **{name: True})

    def test_capacity_has_no_bool_float_subclass_or_unbounded_fallback(self):
        class Child(int):
            pass
        for value in (None, True, 2.0, Child(2), 1, 129):
            self.reject(lambda v=value: self.m.SyntheticCallRecorderV1(v), 'RECORDER_CAPACITY')

    def test_first_request_is_validated_before_any_history_exists(self):
        for request, suffix in ((replace(self.first.request, requested_binary32=b'bad'), 'REQUEST_WORD'),
            (replace(self.first.request, context=replace(self.first.request.context, scope='ACTUAL_PRODUCTION')), 'REQUEST_SCOPE'),
            (replace(self.first.request, sample_time_ns=True), 'REQUEST_TIME')):
            recorder = self.m.SyntheticCallRecorderV1(2)
            self.reject(lambda: recorder.begin(request), 'RECORDER_REQUEST:' + suffix)
            self.reject(recorder.finish, 'RECORDER_FAILED')

    def test_external_objects_and_subclasses_reject_without_attribute_reads(self):
        class External:
            def __getattribute__(self, _name):
                raise AssertionError('EXTERNAL_READ')
        class Child(SyntheticRequestSnapshotV1):
            pass
        child = Child(self.first.request.context, 7, -9, b'\x00' * 4, True, False, False)
        for wrong in (External(), child, None):
            recorder = self.m.SyntheticCallRecorderV1(2)
            self.reject(lambda: recorder.begin(wrong), 'RECORDER_REQUEST_TYPE')
        recorder = self.m.SyntheticCallRecorderV1(2)
        recorder.begin(self.first.request)
        self.reject(lambda: recorder.complete(External()), 'RECORDER_FRAME_TYPE')

    def test_double_begin_is_terminal_and_never_overwrites_pending_request(self):
        recorder = self.m.SyntheticCallRecorderV1(2)
        recorder.begin(self.first.request)
        self.reject(lambda: recorder.begin(self.second.request), 'RECORDER_PENDING')
        self.reject(lambda: recorder.complete(self.first), 'RECORDER_FAILED')

    def test_completion_without_begin_is_terminal(self):
        recorder = self.m.SyntheticCallRecorderV1(2)
        self.reject(lambda: recorder.complete(self.first), 'RECORDER_NOT_PENDING')
        self.reject(lambda: recorder.begin(self.first.request), 'RECORDER_FAILED')

    def test_mismatched_completion_does_not_publish_or_resume_prefix(self):
        recorder = self.m.SyntheticCallRecorderV1(2)
        recorder.begin(self.first.request)
        self.reject(lambda: recorder.complete(replace(self.first, request=replace(self.first.request, request_override=True))), 'RECORDER_REQUEST_CHANGED')
        self.reject(recorder.finish, 'RECORDER_FAILED')

    def test_first_completion_validates_settings_and_saved_state(self):
        for frame, suffix in ((replace(self.first, saved_limited_state=True), 'LIMITER_STATE_DOMAIN'),
            (replace(self.first, settings=replace(self.first.settings, limiter_scale=17)), 'LIMITER_SCALE_MISMATCH'),
            (replace(self.first, settings_origin='ACTUAL_CONSUMED'), 'LIMITER_DECLARATION')):
            recorder = self.m.SyntheticCallRecorderV1(2)
            recorder.begin(frame.request)
            self.reject(lambda: recorder.complete(frame), 'RECORDER_LIMITER:' + suffix)
            self.reject(recorder.finish, 'RECORDER_FAILED')

    def test_context_sequence_time_and_reset_discontinuity_reject_at_begin(self):
        for request, suffix in ((replace(self.second.request, sequence=9), 'REQUEST_PAIR_SEQUENCE'),
            (replace(self.second.request, sample_time_ns=-9), 'REQUEST_PAIR_TIME'),
            (replace(self.second.request, reset_since_previous=True), 'REQUEST_PAIR_RESET'),
            (replace(self.second.request, context=replace(self.second.request.context, loss_generation=1)), 'REQUEST_PAIR_CONTEXT'),
            (replace(self.second.request, context=replace(self.second.request.context, clock_domain='DECLARED_REPLAY_RECORDED_CAN_NS')), 'REQUEST_PAIR_CONTEXT')):
            recorder = self.m.SyntheticCallRecorderV1(2)
            recorder.begin(self.first.request)
            recorder.complete(self.first)
            self.reject(lambda: recorder.begin(request), 'RECORDER_REQUEST:' + suffix)
            self.reject(recorder.finish, 'RECORDER_FAILED')

    def test_changed_settings_state_or_counter_do_not_finish_as_a_valid_prefix(self):
        for frame, suffix in ((replace(self.second, limited_state_at_entry=3), 'LIMITER_PAIR_STATE_LINK'),
            (replace(self.second, angle_counter_at_entry=3), 'LIMITER_PAIR_COUNTER_LINK'),
            (replace(self.second, settings=replace(self.second.settings, delta_up=3)), 'LIMITER_PAIR_SETTINGS')):
            recorder = self.m.SyntheticCallRecorderV1(2)
            recorder.begin(self.first.request)
            recorder.complete(self.first)
            recorder.begin(frame.request)
            self.reject(lambda: recorder.complete(frame), 'RECORDER_LIMITER:' + suffix)
            self.reject(recorder.finish, 'RECORDER_FAILED')

    def test_pending_finish_is_not_a_successful_prefix(self):
        recorder = self.complete_two(3)
        recorder.begin(replace(self.second.request, sequence=9, sample_time_ns=-7))
        self.reject(recorder.finish, 'RECORDER_INCOMPLETE')
        self.reject(recorder.finish, 'RECORDER_FAILED')

    def test_empty_and_single_record_finish_reject_without_seeding(self):
        recorder = self.m.SyntheticCallRecorderV1(2)
        self.reject(recorder.finish, 'RECORDER_TOO_SHORT')
        recorder = self.m.SyntheticCallRecorderV1(2)
        recorder.begin(self.first.request)
        recorder.complete(self.first)
        self.reject(recorder.finish, 'RECORDER_TOO_SHORT')

    def test_abort_is_terminal_for_open_and_pending_recordings(self):
        for pending in (False, True):
            recorder = self.m.SyntheticCallRecorderV1(2)
            if pending:
                recorder.begin(self.first.request)
            recorder.abort()
            self.reject(recorder.finish, 'RECORDER_ABORTED')
            self.reject(lambda: recorder.begin(self.first.request), 'RECORDER_ABORTED')

    def test_capacity_overflow_does_not_evict_or_export_a_prefix(self):
        recorder = self.complete_two()
        self.reject(lambda: recorder.begin(replace(self.second.request, sequence=9, sample_time_ns=-7)), 'RECORDER_OVERFLOW')
        self.reject(recorder.finish, 'RECORDER_FAILED')

    def test_successful_finish_closes_all_mutations(self):
        recorder = self.complete_two()
        result = recorder.finish()
        for operation in (recorder.finish, recorder.abort, lambda: recorder.begin(self.first.request), lambda: recorder.complete(self.first)):
            self.reject(operation, 'RECORDER_CLOSED')
        self.assertEqual(len(result.records), 2)

    def test_direct_finished_constructor_revalidates_first_record_and_links(self):
        for wrong in ([], (), (self.first,), (replace(self.first, saved_limited_state=True), self.second),
                      (self.first, replace(self.second, limited_state_at_entry=0))):
            with self.assertRaises(self.m.RecorderError):
                self.m.FinishedSyntheticRecordingV1(wrong)

    def test_maximum_bounded_recording_accepts_128_calls_without_time_arithmetic(self):
        recorder = self.m.SyntheticCallRecorderV1(128)
        for index in range(128):
            request = replace(self.first.request, sequence=index, sample_time_ns=index + 1, reset_since_previous=False)
            frame = replace(self.first, request=request, limited_state_at_entry=0, saved_limited_state=0,
                            angle_counter_at_entry=0, saved_angle_counter=0)
            recorder.begin(request)
            recorder.complete(frame)
        self.assertEqual(len(recorder.finish().records), 128)

    def test_uint64_end_and_signed_int64_times_are_preserved_without_wrap(self):
        first = replace(self.first, request=replace(self.first.request, sequence=(1 << 64) - 2, sample_time_ns=-(1 << 63)))
        second = replace(self.second, request=replace(self.second.request, sequence=(1 << 64) - 1, sample_time_ns=(1 << 63) - 1))
        recorder = self.m.SyntheticCallRecorderV1(2)
        for frame in (first, second):
            recorder.begin(frame.request)
            recorder.complete(frame)
        result = recorder.finish()
        self.assertEqual(result.records[1].request.sequence, 18446744073709551615)
        self.assertEqual(result.records[0].request.sample_time_ns, -9223372036854775808)
