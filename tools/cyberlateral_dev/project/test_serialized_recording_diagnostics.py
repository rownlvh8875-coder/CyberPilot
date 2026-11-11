"""Catch permissive decoding, prefix execution and lost declared diagnostics."""

import importlib
import json
import os
import subprocess
import sys
import unittest
from dataclasses import asdict, replace
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class SerializedRecordingDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.model = package_feature()
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.offline_recording_diagnostics')
        self.assertTrue(callable(getattr(self.m, 'check_serialized_synthetic_recording', None)), 'Missing CORE52 canonical bytes diagnostics')
        self.recorder = importlib.import_module('integration_tools.offline_call_recorder')
        self.codec = importlib.import_module('integration_tools.offline_recording_codec')
        self.preflight = importlib.import_module('integration_tools.offline_recording_preflight')
        self.sequence = importlib.import_module('integration_tools.synthetic_sequence_check')
        self.request = importlib.import_module('integration_tools.request_snapshot')
        self.limiter = importlib.import_module('integration_tools.limiter_snapshot')
        self.inputs = importlib.import_module('integration_tools.synthetic_model_input')
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
        self.recording = self.recorder.FinishedSyntheticRecordingV1(tuple(frames))
        self.contexts = tuple(self.inputs.SyntheticModelContextV1('COUNTERFACTUAL_MODEL_INPUT_ONLY', index, previous, 1.5, 85.0)
                              for index, previous in ((5, -4), (6, 8), (7, -8)))
        self.raw = self.codec.encode_recording(self.recording)

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

    def reject(self, raw, contexts, error_type, code):
        def call():
            with self.assertRaises(error_type) as caught:
                self.m.check_serialized_synthetic_recording(raw, contexts)
            self.assertEqual((caught.exception.code, str(caught.exception)), (code, code))
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_canonical_bytes_produce_literal_full_sequence_result(self):
        result, counts = self.counted(lambda: self.m.check_serialized_synthetic_recording(self.raw, self.contexts))
        self.assertIs(type(result), self.sequence.SyntheticSequenceCheckV1)
        self.assertEqual((result.status, result.checked_transition_count, result.synthetic_model_steps), ('MATCH', 3, 3))
        self.assertEqual(tuple(row.computed_next_state for row in result.checks),
                         (self.model.LateralState(6, 8, 2, 5), self.model.LateralState(7, -8, -2, 6), self.model.LateralState(8, 4, 2, 7)))
        self.assertEqual(result.differing_transition_indices, ())
        self.assertEqual(result.frames, self.recording.records)
        self.assertIs(result.contexts, self.contexts)
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_early_difference_preserves_declared_feed_and_later_results(self):
        fs = self.recording.records
        recording = self.recorder.FinishedSyntheticRecordingV1((fs[0], replace(fs[1], saved_limited_state=10),
            replace(fs[2], limited_state_at_entry=10, saved_limited_state=5),
            replace(fs[3], limited_state_at_entry=5, saved_limited_state=4)))
        result, counts = self.counted(lambda: self.m.check_serialized_synthetic_recording(self.codec.encode_recording(recording), self.contexts))
        self.assertEqual((result.status, result.differing_transition_indices), ('DIFFERENT', (0,)))
        self.assertEqual(tuple(row.computed_next_state.previous_applied for row in result.checks), (2, 5, 4))
        self.assertEqual(result.checks[1].prepared.model_state.previous_applied, 10)
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_wrong_raw_types_are_not_coerced_or_inspected(self):
        class Foreign:
            def __getattribute__(self, _name):
                raise AssertionError('FOREIGN_RAW_READ')

        class Child(bytes):
            def __len__(self):
                raise AssertionError('CHILD_RAW_LENGTH')

        for raw in (None, self.raw.decode(), bytearray(self.raw), memoryview(self.raw), self.recording, Foreign(), Child(self.raw)):
            self.reject(raw, self.contexts, self.recorder.RecorderError, 'RECORDER_SERIALIZATION')

    def test_empty_oversize_and_malformed_bytes_do_not_run_model(self):
        for raw in (b'', b' ' * 262145, b'\xff', b'{', b'[]', b'{"x":NaN}', b'[' * 1100):
            self.reject(raw, self.contexts, self.recorder.RecorderError, 'RECORDER_SERIALIZATION')

    def test_noncanonical_json_and_duplicate_fields_are_not_repaired(self):
        for raw in (self.raw.rstrip(), json.dumps(json.loads(self.raw), indent=2).encode(),
                    self.raw.replace(b'"schema_version":1', b'"schema_version":1,"schema_version":1', 1)):
            self.reject(raw, self.contexts, self.recorder.RecorderError, 'RECORDER_SERIALIZATION')

    def test_permission_scope_and_static_gate_tampering_reject(self):
        for key, value in (('model_input_allowed', True), ('actual_activation_allowed', True), ('scope', 'ACTUAL_PRODUCTION')):
            data = json.loads(self.raw)
            data[key] = value
            self.reject(canonical(data), self.contexts, self.recorder.RecorderError, 'RECORDER_SERIALIZATION')
        data = json.loads(self.raw)
        data['gates']['STATIC_EVIDENCE_GATE'] = 'PASS'
        self.reject(canonical(data), self.contexts, self.recorder.RecorderError, 'RECORDER_SERIALIZATION')

    def test_late_record_link_corruption_rejects_before_prefix_execution(self):
        data = json.loads(self.raw)
        data['records'][-1]['limited_state_at_entry'] = 7
        self.reject(canonical(data), self.contexts, self.recorder.RecorderError, 'RECORDER_SERIALIZATION')

    def test_bad_bytes_take_precedence_without_reading_hostile_context(self):
        class Foreign:
            def __getattribute__(self, _name):
                raise AssertionError('FOREIGN_CONTEXT_READ')
        self.reject(b'{}', Foreign(), self.recorder.RecorderError, 'RECORDER_SERIALIZATION')

    def test_contexts_are_explicit_exact_tuple_not_inferred_or_coerced(self):
        for contexts, code in ((None, 'RECORDING_PREFLIGHT_CONTEXT_CONTAINER'),
                               (list(self.contexts), 'RECORDING_PREFLIGHT_CONTEXT_CONTAINER'),
                               ((), 'RECORDING_PREFLIGHT_CONTEXT_COUNT')):
            self.reject(self.raw, contexts, self.preflight.RecordingPreflightError, code)

    def test_late_invalid_context_rejects_whole_input_before_model(self):
        contexts = (*self.contexts[:2], replace(self.contexts[2], current_driver=1))
        self.reject(self.raw, contexts, self.preflight.RecordingPreflightError, 'RECORDING_PREFLIGHT_INPUT:2:MODEL_DRIVER')

    def test_context_model_index_is_not_derived_from_record_sequence_or_time(self):
        contexts = (*self.contexts[:2], replace(self.contexts[2], model_index=9))
        self.reject(self.raw, contexts, self.preflight.RecordingPreflightError, 'RECORDING_PREFLIGHT_MODEL_ORDER:2')

    def test_repeat_call_revalidates_context_after_prior_success(self):
        self.assertEqual(self.m.check_serialized_synthetic_recording(self.raw, self.contexts).status, 'MATCH')
        object.__setattr__(self.contexts[-1], 'current_driver', 1)
        self.reject(self.raw, self.contexts, self.preflight.RecordingPreflightError, 'RECORDING_PREFLIGHT_INPUT:2:MODEL_DRIVER')

    def test_signed_zero_subnormals_and_int64_endpoints_remain_exact(self):
        for clock in ('DECLARED_LIVE_MONOTONIC_NS', 'DECLARED_REPLAY_APPLY_NS'):
            for words in (('80000000', '00000001'), ('80000001', '00000000')):
                base = self.recording.records[0]
                request_context = replace(base.request.context, clock_domain=clock)
                frames = tuple(replace(base, request=replace(base.request, context=request_context, sequence=7 + i,
                    sample_time_ns=(-(1 << 63), (1 << 63) - 1)[i], requested_binary32=bytes.fromhex(word)),
                    limited_state_at_entry=0, saved_limited_state=0, angle_counter_at_entry=0, saved_angle_counter=0)
                    for i, word in enumerate(words))
                contexts = (replace(self.contexts[0], model_index=4095, previous_integer_request=0,
                                    current_driver=-0.0, current_angle_deg=-0.0),)
                raw = self.codec.encode_recording(self.recorder.FinishedSyntheticRecordingV1(frames))
                result, counts = self.counted(lambda: self.m.check_serialized_synthetic_recording(raw, contexts))
                self.assertEqual(result.status, 'MATCH')
                self.assertEqual(tuple(f.request.requested_binary32.hex() for f in result.frames), words)
                self.assertEqual(tuple(f.request.sample_time_ns for f in result.frames), (-(1 << 63), (1 << 63) - 1))
                self.assertEqual(tuple(f.request.context.clock_domain for f in result.frames), (clock, clock))
                self.assertEqual(result.contexts[0].current_driver.hex(), '-0x0.0p+0')
                self.assertEqual(result.checks[0].computed_next_state.index, 4096)
                self.assertEqual(counts, {'step': 1, 'simulate': 0})

    def test_result_keeps_false_authority_and_existing_contract(self):
        result = self.m.check_serialized_synthetic_recording(self.raw, self.contexts)
        self.assertEqual(result.contract_id, 'CORE7_COUNTERFACTUAL_DECLARED_SEQUENCE_V1')
        for name in ('first_frame_transition_checked', 'prehistory_checked', 'source_identity_reauthenticated',
                     'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
            self.assertIs(getattr(result, name), False)
        self.assertFalse(json.loads(self.raw)['model_input_allowed'])

    def test_success_does_not_mutate_bytes_or_contexts_and_is_deterministic(self):
        before = (self.raw, tuple(asdict(c) for c in self.contexts))
        first = self.m.check_serialized_synthetic_recording(self.raw, self.contexts)
        second = self.m.check_serialized_synthetic_recording(self.raw, self.contexts)
        self.assertEqual(asdict(first), asdict(second))
        self.assertEqual((self.raw, tuple(asdict(c) for c in self.contexts)), before)

    def test_late_model_error_keeps_existing_code_and_nonzero_prior_work(self):
        original = self.model.step
        attempts = 0

        def fail_late(sample, state):
            nonlocal attempts
            attempts += 1
            if attempts == 3:
                raise ValueError('RAW_SENTINEL')
            return original(sample, state)

        def call():
            with patch.object(self.model, 'step', side_effect=fail_late):
                with self.assertRaises(self.sequence.SequenceCheckError) as caught:
                    self.m.check_serialized_synthetic_recording(self.raw, self.contexts)
            self.assertEqual(caught.exception.code, 'SEQUENCE_TRANSITION:2:TRANSITION_MODEL_FAILURE')
            self.assertNotIn('RAW_SENTINEL', str(caught.exception))
        _, counts = self.counted(call)
        self.assertEqual((attempts, counts), (3, {'step': 2, 'simulate': 0}))

    def test_unexpected_model_error_propagates_without_success_result(self):
        error = RuntimeError('DEPENDENCY_SENTINEL')
        with patch.object(self.model, 'step', side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                self.m.check_serialized_synthetic_recording(self.raw, self.contexts)
        self.assertIs(caught.exception, error)

    def test_no_context_default_or_policy_arguments(self):
        def call():
            with self.assertRaises(TypeError):
                self.m.check_serialized_synthetic_recording(self.raw)
            for name in ('rate_budget_per_s', 'dt', 'T2', 'actual_scale', 'model_input_allowed'):
                with self.assertRaises(TypeError):
                    self.m.check_serialized_synthetic_recording(self.raw, self.contexts, **{name: 0})
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_cold_import_does_not_execute_model_or_import_vehicle_or_f61(self):
        code = '''import sys
import cyberlateral_dev as model
calls=[]
codes={model.step.__code__,model.simulate.__code__}
sys.setprofile(lambda frame,event,arg: calls.append(event) if event=='call' and frame.f_code in codes else None)
from integration_tools.offline_recording_diagnostics import check_serialized_synthetic_recording
sys.setprofile(None)
assert callable(check_serialized_synthetic_recording) and not calls
assert not any(x.startswith(('openpilot','cereal','opendbc','synthetic_rate_constraint')) for x in sys.modules)
print('CORE52_IMPORT_NO_STEPS')
'''
        env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'))
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
        self.assertEqual((result.returncode, result.stdout.strip(), result.stderr), (0, 'CORE52_IMPORT_NO_STEPS', ''))


if __name__ == '__main__':
    unittest.main()
