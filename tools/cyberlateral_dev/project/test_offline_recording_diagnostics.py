"""Explicit execution must preserve full preflight, declared feed and work claims."""

import importlib
import os
import subprocess
import sys
import unittest
from dataclasses import asdict, replace
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


class RecordedDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/offline_recording_diagnostics.py').is_file(), 'Missing CORE49 explicit recording diagnostics')
        self.model = package_feature()
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.offline_recording_diagnostics')
        self.preflight = importlib.import_module('integration_tools.offline_recording_preflight')
        self.sequence = importlib.import_module('integration_tools.synthetic_sequence_check')
        self.recorder = importlib.import_module('integration_tools.offline_call_recorder')
        self.codec = importlib.import_module('integration_tools.offline_recording_codec')
        self.request = importlib.import_module('integration_tools.request_snapshot')
        self.limiter = importlib.import_module('integration_tools.limiter_snapshot')
        self.inputs = importlib.import_module('integration_tools.synthetic_model_input')
        self.recording, self.contexts = self.fixture()

    def fixture(self):
        context = self.request.SyntheticRequestContextV1(1, 'COUNTERFACTUAL_REQUEST_SNAPSHOT_ONLY',
            'CORE3_COUNTERFACTUAL_REQUEST_SOURCE_V1', 'fixture-capture', 'fixture-controller', 'fixture-config',
            'DECLARED_LIVE_MONOTONIC_NS', 'DECLARED_TORQUE_CONTROL', 'REQUESTED_NORMALIZED_BEFORE_INTEGER_LIMITER', 0, 0)
        settings = self.limiter.SyntheticConsumedSettingsV1(16, 16, 2, 5, 7, 1, 3)
        rows = ((7, -9, 'be800000', 7, -2, 3, 4), (8, -8, '3f000000', -2, 2, 4, 5),
                (9, 123, 'bf000000', 2, -2, 5, 6), (10, 1 << 60, '3e800000', -2, 2, 6, 7))
        frames = []
        for seq, time, word, entry, saved, counter, next_counter in rows:
            request = self.request.SyntheticRequestSnapshotV1(context, seq, time, bytes.fromhex(word), True, False, False)
            frames.append(self.limiter.SyntheticLimiterSnapshotV1(request, settings, 'DECLARED_LIMITED_STATE_POST_INACTIVE_GATE',
                'DECLARED_COUNTERFACTUAL_CONSUMED_SETTINGS', entry, saved, counter, next_counter, True))
        contexts = tuple(self.inputs.SyntheticModelContextV1('COUNTERFACTUAL_MODEL_INPUT_ONLY', index, previous, 1.5, 85.0)
                         for index, previous in ((5, -4), (6, 8), (7, -8)))
        return self.recorder.FinishedSyntheticRecordingV1(tuple(frames)), contexts

    def counted(self, call):
        codes = {self.model.step.__code__: 'step', self.model.simulate.__code__: 'simulate'}
        counts = {'step': 0, 'simulate': 0}

        def profile(frame, event, _arg):
            if event == 'call' and frame.f_code in codes:
                counts[codes[frame.f_code]] += 1

        previous = sys.getprofile()
        try:
            sys.setprofile(profile)
            result = call()
        finally:
            sys.setprofile(previous)
        return result, counts

    def reject(self, recording, contexts, code):
        def call():
            with self.assertRaises(self.preflight.RecordingPreflightError) as caught:
                self.m.check_recorded_synthetic_sequence(recording, contexts)
            self.assertEqual((caught.exception.code, str(caught.exception)), (code, code))
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def changed(self, frames):
        return self.recorder.FinishedSyntheticRecordingV1(tuple(frames))

    def test_literal_three_transitions_match_using_existing_result_type(self):
        result, counts = self.counted(lambda: self.m.check_recorded_synthetic_sequence(self.recording, self.contexts))
        self.assertIs(type(result), self.sequence.SyntheticSequenceCheckV1)
        self.assertEqual((result.status, result.checked_transition_count, result.synthetic_model_steps), ('MATCH', 3, 3))
        self.assertEqual(tuple(row.computed_next_state for row in result.checks),
                         (self.model.LateralState(6, 8, 2, 5), self.model.LateralState(7, -8, -2, 6), self.model.LateralState(8, 4, 2, 7)))
        self.assertEqual(result.differing_transition_indices, ())
        self.assertIs(result.frames, self.recording.records)
        self.assertIs(result.contexts, self.contexts)
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_minimal_recording_executes_one_nonvacuous_step(self):
        result, counts = self.counted(lambda: self.m.check_recorded_synthetic_sequence(
            self.changed(self.recording.records[:2]), self.contexts[:1]))
        self.assertEqual((result.status, result.checked_transition_count, result.synthetic_model_steps), ('MATCH', 1, 1))
        self.assertEqual(counts, {'step': 1, 'simulate': 0})

    def test_maximum_recording_executes_all_127_explicit_transitions(self):
        first = self.recording.records[0]
        frames = tuple(replace(first, request=replace(first.request, sequence=1000 + i, sample_time_ns=-(1 << 63) + i,
            requested_binary32=bytes.fromhex('80000000')), limited_state_at_entry=0, saved_limited_state=0,
            angle_counter_at_entry=0, saved_angle_counter=0) for i in range(128))
        contexts = tuple(replace(self.contexts[0], model_index=3969 + i, previous_integer_request=0,
            current_driver=0.0, current_angle_deg=0.0) for i in range(127))
        result, counts = self.counted(lambda: self.m.check_recorded_synthetic_sequence(self.changed(frames), contexts))
        self.assertEqual((result.status, result.checked_transition_count, result.synthetic_model_steps), ('MATCH', 127, 127))
        self.assertEqual((result.checks[-1].context.model_index, result.checks[-1].computed_next_state.index), (4095, 4096))
        self.assertEqual(counts, {'step': 127, 'simulate': 0})

    def test_early_difference_keeps_declared_state_and_all_later_diagnostics(self):
        fs = self.recording.records
        recording = self.changed((fs[0], replace(fs[1], saved_limited_state=10),
            replace(fs[2], limited_state_at_entry=10, saved_limited_state=5),
            replace(fs[3], limited_state_at_entry=5, saved_limited_state=4)))
        before = self.codec.encode_recording(recording)
        result, counts = self.counted(lambda: self.m.check_recorded_synthetic_sequence(recording, self.contexts))
        self.assertEqual((result.status, result.differing_transition_indices), ('DIFFERENT', (0,)))
        self.assertEqual(tuple(row.status for row in result.checks), ('DIFFERENT', 'MATCH', 'MATCH'))
        self.assertEqual(tuple(row.computed_next_state.previous_applied for row in result.checks), (2, 5, 4))
        self.assertEqual(result.checks[1].prepared.model_state.previous_applied, 10)
        self.assertEqual(self.codec.encode_recording(recording), before)
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_late_counter_difference_is_not_hidden_by_matching_prefix(self):
        fs = self.recording.records
        recording = self.changed((*fs[:3], replace(fs[3], saved_angle_counter=8)))
        result = self.m.check_recorded_synthetic_sequence(recording, self.contexts)
        self.assertEqual((result.status, result.differing_transition_indices), ('DIFFERENT', (2,)))
        self.assertEqual((result.checks[2].differences[0].declared, result.checks[2].differences[0].computed), (8, 7))

    def test_all_differences_remain_in_transition_order(self):
        fs = self.recording.records
        recording = self.changed((fs[0], replace(fs[1], saved_angle_counter=10),
            replace(fs[2], angle_counter_at_entry=10, saved_angle_counter=20),
            replace(fs[3], angle_counter_at_entry=20, saved_angle_counter=30)))
        result = self.m.check_recorded_synthetic_sequence(recording, self.contexts)
        self.assertEqual((result.status, result.differing_transition_indices), ('DIFFERENT', (0, 1, 2)))
        self.assertEqual(tuple(row.computed_next_state.angle_counter for row in result.checks), (5, 11, 21))

    def test_recording_metadata_is_checked_even_when_all_pairs_are_compatible(self):
        object.__setattr__(self.recording, 'model_input_allowed', True)
        self.reject(self.recording, self.contexts, 'RECORDING_PREFLIGHT_RECORDING:RECORDER_METADATA')

    def test_foreign_and_hostile_recording_reject_before_attribute_access(self):
        class Foreign:
            def __getattribute__(self, _name):
                raise AssertionError('READ_FOREIGN')

        class Child(self.recorder.FinishedSyntheticRecordingV1):
            def __getattribute__(self, _name):
                raise AssertionError('READ_CHILD')

        for recording in (None, {}, b'{}', Foreign(), object.__new__(Child)):
            self.reject(recording, self.contexts, 'RECORDING_PREFLIGHT_RECORDING:RECORDER_RECORDING_TYPE')

    def test_receipt_is_not_an_execution_capability_or_alternate_input(self):
        receipt = self.preflight.preflight_recording_input(self.recording, self.contexts)
        self.assertFalse(receipt.model_input_allowed)
        self.reject(receipt, self.contexts, 'RECORDING_PREFLIGHT_RECORDING:RECORDER_RECORDING_TYPE')

    def test_late_invalid_context_does_not_execute_valid_prefix(self):
        contexts = (*self.contexts[:2], replace(self.contexts[2], current_driver=1))
        self.reject(self.recording, contexts, 'RECORDING_PREFLIGHT_INPUT:2:MODEL_DRIVER')

    def test_late_invalid_index_does_not_execute_valid_prefix(self):
        contexts = (*self.contexts[:2], replace(self.contexts[2], model_index=4096))
        self.reject(self.recording, contexts, 'RECORDING_PREFLIGHT_INPUT:2:MODEL_INDEX')

    def test_model_order_is_checked_before_any_step(self):
        contexts = (*self.contexts[:2], replace(self.contexts[2], model_index=8))
        self.reject(self.recording, contexts, 'RECORDING_PREFLIGHT_MODEL_ORDER:2')

    def test_late_field_validation_precedes_earlier_order_problem(self):
        contexts = (self.contexts[0], replace(self.contexts[1], model_index=9), replace(self.contexts[2], current_driver=1))
        self.reject(self.recording, contexts, 'RECORDING_PREFLIGHT_INPUT:2:MODEL_DRIVER')

    def test_invalid_context_container_is_not_iterated(self):
        class Child(tuple):
            def __iter__(self):
                raise AssertionError('ITERATED_CHILD')

            def __len__(self):
                raise AssertionError('READ_CHILD_LENGTH')

        for contexts in (None, list(self.contexts), iter(self.contexts), Child(self.contexts)):
            self.reject(self.recording, contexts, 'RECORDING_PREFLIGHT_CONTEXT_CONTAINER')

    def test_context_count_does_not_allow_partial_prefix(self):
        for contexts in ((), self.contexts[:1], (*self.contexts, self.contexts[0])):
            self.reject(self.recording, contexts, 'RECORDING_PREFLIGHT_CONTEXT_COUNT')

    def test_successful_prior_preflight_does_not_cache_modified_context_authority(self):
        receipt = self.preflight.preflight_recording_input(self.recording, self.contexts)
        object.__setattr__(self.contexts[-1], 'current_driver', 1)
        self.assertFalse(receipt.model_input_allowed)
        self.reject(self.recording, self.contexts, 'RECORDING_PREFLIGHT_INPUT:2:MODEL_DRIVER')

    def test_actual_scope_and_override_are_rejected_without_steps(self):
        contexts = (*self.contexts[:2], replace(self.contexts[2], scope='ACTUAL_VEHICLE'))
        self.reject(self.recording, contexts, 'RECORDING_PREFLIGHT_INPUT:2:MODEL_SCOPE')
        fs = self.recording.records
        recording = self.changed((*fs[:3], replace(fs[3], request=replace(fs[3].request, request_override=True))))
        self.reject(recording, self.contexts, 'RECORDING_PREFLIGHT_INPUT:2:MODEL_OVERRIDE')

    def test_explicit_execution_does_not_promote_original_or_result_permissions(self):
        before = asdict(self.recording)
        result = self.m.check_recorded_synthetic_sequence(self.recording, self.contexts)
        self.assertEqual(asdict(self.recording), before)
        for name in ('source_identity_reauthenticated', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
            self.assertIs(getattr(result, name), False)
            self.assertIs(getattr(self.recording, name), False)
        self.assertIs(self.recording.model_input_allowed, False)
        self.assertIs(result.first_frame_transition_checked, False)
        self.assertIs(result.prehistory_checked, False)

    def test_raw_zero_subnormal_and_int64_times_survive_live_and_replay(self):
        first = self.recording.records[0]
        for clock in ('DECLARED_LIVE_MONOTONIC_NS', 'DECLARED_REPLAY_RECORDED_CAN_NS'):
            for words in (('80000000', '00000001'), ('00000000', '80000001')):
                with self.subTest(clock=clock, words=words):
                    context = replace(first.request.context, clock_domain=clock)
                    frames = tuple(replace(first, request=replace(first.request, context=context, sequence=500 + i,
                        sample_time_ns=(-(1 << 63), (1 << 63) - 1)[i], requested_binary32=bytes.fromhex(word)),
                        limited_state_at_entry=0, saved_limited_state=0, angle_counter_at_entry=0, saved_angle_counter=0)
                        for i, word in enumerate(words))
                    recording = self.changed(frames)
                    contexts = (replace(self.contexts[0], model_index=4095, previous_integer_request=0,
                                        current_driver=-0.0, current_angle_deg=-0.0),)
                    before = self.codec.encode_recording(recording)
                    result = self.m.check_recorded_synthetic_sequence(recording, contexts)
                    self.assertEqual(result.status, 'MATCH')
                    self.assertEqual(tuple(f.request.requested_binary32.hex() for f in result.frames), words)
                    self.assertEqual(tuple(f.request.sample_time_ns for f in result.frames), (-(1 << 63), (1 << 63) - 1))
                    self.assertEqual(self.codec.encode_recording(recording), before)
                    self.assertEqual(result.contexts[0].current_driver.hex(), '-0x0.0p+0')

    def test_later_model_failure_returns_no_partial_success_and_preserves_input(self):
        original = self.model.step
        attempts = 0
        before = self.codec.encode_recording(self.recording)

        def fail_late(sample, state):
            nonlocal attempts
            attempts += 1
            if attempts == 3:
                raise ValueError('RAW_FAILURE_DETAIL')
            return original(sample, state)

        with patch.object(self.model, 'step', side_effect=fail_late):
            with self.assertRaises(self.sequence.SequenceCheckError) as caught:
                self.m.check_recorded_synthetic_sequence(self.recording, self.contexts)
        self.assertEqual(attempts, 3)
        self.assertEqual(caught.exception.code, 'SEQUENCE_TRANSITION:2:TRANSITION_MODEL_FAILURE')
        self.assertNotIn('RAW_FAILURE_DETAIL', str(caught.exception))
        self.assertEqual(self.codec.encode_recording(self.recording), before)

    def test_unexpected_dependency_exception_propagates_without_false_success(self):
        error = RuntimeError('DEPENDENCY_SENTINEL')
        with patch.object(self.model, 'step', side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                self.m.check_recorded_synthetic_sequence(self.recording, self.contexts)
        self.assertIs(caught.exception, error)

    def test_no_default_context_policy_or_permission_arguments(self):
        def call():
            with self.assertRaises(TypeError):
                self.m.check_recorded_synthetic_sequence(self.recording)
            for name in ('rate_budget_per_s', 'dt', 'T2', 'actual_scale', 'model_input_allowed'):
                with self.assertRaises(TypeError):
                    self.m.check_recorded_synthetic_sequence(self.recording, self.contexts, **{name: 0})
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_cold_import_executes_no_model_steps(self):
        code = '''import sys
import cyberlateral_dev as model
calls=[]
codes={model.step.__code__,model.simulate.__code__}
sys.setprofile(lambda frame,event,arg: calls.append(event) if event=='call' and frame.f_code in codes else None)
import integration_tools.offline_recording_diagnostics
sys.setprofile(None)
assert not calls
print('CORE49_IMPORT_NO_STEPS')
'''
        env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'))
        output = subprocess.check_output([sys.executable, '-B', '-c', code], cwd=ROOT, env=env, text=True)
        self.assertEqual(output.strip(), 'CORE49_IMPORT_NO_STEPS')


if __name__ == '__main__':
    unittest.main()
