"""Catch format bypass,prefix execution,state repair and lost bundled diagnostics."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

import test_offline_recording_input_codec as codec_cases
from v1_helpers import ROOT


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class BundledInputDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        case = codec_cases.RecordingInputCodecTests('test_encoder_matches_independent_literal_wire_without_steps')
        case.setUp()
        self.base = case.fixture
        self.model, self.recording, self.contexts = case.model, case.recording, case.contexts
        self.codec: Any = case.m
        self.m: Any = self.base.m
        self.payload: dict[str, Any] = case.payload
        self.raw = canonical(self.payload)
        self.assertTrue(callable(getattr(self.m, 'check_serialized_recording_input', None)), 'Missing CORE58 complete input diagnostics')

    def counted(self, call):
        return self.base.counted(call)

    def reject(self, raw, code='RECORDING_INPUT_SERIALIZATION', semantic=False):
        kind = self.base.preflight.RecordingPreflightError if semantic else self.codec.RecordingInputCodecError

        def call():
            with self.assertRaises(kind) as caught:
                self.m.check_serialized_recording_input(raw)
            self.assertEqual((caught.exception.code, str(caught.exception)), (code, code))
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_complete_bytes_produce_literal_three_transition_result(self):
        result, counts = self.counted(lambda: self.m.check_serialized_recording_input(self.raw))
        self.assertIs(type(result), self.base.sequence.SyntheticSequenceCheckV1)
        self.assertEqual((result.status, result.checked_transition_count, result.synthetic_model_steps), ('MATCH', 3, 3))
        self.assertEqual(tuple(check.computed_next_state for check in result.checks),
            (self.model.LateralState(6, 8, 2, 5), self.model.LateralState(7, -8, -2, 6), self.model.LateralState(8, 4, 2, 7)))
        self.assertEqual(result.differing_transition_indices, ())
        self.assertEqual(result.frames, self.recording.records)
        self.assertEqual(tuple(asdict(c) for c in result.contexts), tuple(asdict(c) for c in self.contexts))
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_early_difference_keeps_all_checks_and_declared_state_feed(self):
        fs = self.recording.records
        recording = self.base.recorder.FinishedSyntheticRecordingV1((fs[0], replace(fs[1], saved_limited_state=10),
            replace(fs[2], limited_state_at_entry=10, saved_limited_state=5),
            replace(fs[3], limited_state_at_entry=5, saved_limited_state=4)))
        raw = self.codec.encode_recording_input(recording, self.contexts)
        result, counts = self.counted(lambda: self.m.check_serialized_recording_input(raw))
        self.assertEqual((result.status, result.differing_transition_indices), ('DIFFERENT', (0,)))
        self.assertEqual(tuple(check.computed_next_state.previous_applied for check in result.checks), (2, 5, 4))
        self.assertEqual(result.checks[1].prepared.model_state.previous_applied, 10)
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_foreign_raw_types_never_get_coerced_or_inspected(self):
        class Foreign:
            def __getattribute__(self, _name):
                raise AssertionError('FOREIGN_RAW_READ')

        class Child(bytes):
            def __len__(self):
                raise AssertionError('CHILD_LENGTH')

        for raw in (None, self.raw.decode(), bytearray(self.raw), memoryview(self.raw), {}, Foreign(), Child(self.raw)):
            self.reject(raw)

    def test_malformed_or_out_of_bound_bytes_execute_no_model_prefix(self):
        for raw in (b'', b' ' * 1048577, b'\xff', b'{', b'[]', b'null', b'{"x":NaN}', b'[' * 1100):
            self.reject(raw)

    def test_noncanonical_or_duplicate_outer_fields_are_not_repaired(self):
        for raw in (self.raw.rstrip(), b' ' + self.raw, json.dumps(self.payload, indent=2).encode(),
                self.raw.replace(b'"schema_version":1', b'"schema_version":1,"schema_version":1'),
                self.raw.replace(b'"model_index":5', b'"model_index":5,"model_index":5')):
            self.reject(raw)

    def test_outer_scope_and_permission_changes_never_grant_authority(self):
        for key, value in (('schema_version', True), ('model_input_allowed', 0), ('scope', 'ACTUAL_PRODUCTION'),
                ('contract_id', 'OTHER'), ('model_input_allowed', True), ('source_identity_reauthenticated', True),
                ('f61_input_allowed', True), ('v4_payload_allowed', True), ('actual_activation_allowed', True)):
            self.reject(canonical(dict(self.payload, **{key: value})))

    def test_inner_permission_gate_or_late_link_corruption_rejects_wholly(self):
        for mode in ('permission', 'gate', 'link', 'time'):
            inner = json.loads(self.payload['recording_json'])
            if mode == 'permission':
                inner['actual_activation_allowed'] = True
            elif mode == 'gate':
                inner['gates']['STATIC_EVIDENCE_GATE'] = 'PASS'
            elif mode == 'link':
                inner['records'][-1]['limited_state_at_entry'] = 7
            else:
                inner['records'][-1]['request']['sample_time_ns'] = '-8'
            self.reject(canonical(dict(self.payload, recording_json=canonical(inner).decode())))

    def test_late_context_wire_shape_and_noncanonical_hex_reject_before_work(self):
        for mode in ('missing', 'extra', 'number', 'noncanonical', 'nonfinite'):
            payload = json.loads(self.raw)
            context = payload['contexts'][-1]
            if mode == 'missing':
                del context['current_driver_hex']
            elif mode == 'extra':
                context['dt'] = 0
            else:
                context['current_driver_hex'] = {'number': 1.5, 'noncanonical': '0x1.8p+0', 'nonfinite': 'nan'}[mode]
            self.reject(canonical(payload))

    def test_late_numeric_semantic_codes_survive_without_prefix_steps(self):
        for field, value, suffix in (('current_driver_hex', '0x1.0040000000000p+10', 'MODEL_DRIVER'),
                ('current_driver_hex', '0x1.999999999999ap-4', 'MODEL_DRIVER'),
                ('current_angle_deg_hex', '0x1.6a00000000000p+7', 'MODEL_ANGLE')):
            payload = json.loads(self.raw)
            payload['contexts'][-1][field] = value
            self.reject(canonical(payload), 'RECORDING_PREFLIGHT_INPUT:2:' + suffix, semantic=True)

    def test_context_count_and_model_order_never_get_inferred(self):
        self.reject(canonical(dict(self.payload, contexts=self.payload['contexts'][:1])), 'RECORDING_PREFLIGHT_CONTEXT_COUNT', semantic=True)
        payload = json.loads(self.raw)
        payload['contexts'][-1]['model_index'] = 9
        self.reject(canonical(payload), 'RECORDING_PREFLIGHT_MODEL_ORDER:2', semantic=True)

    def test_previous_request_cannot_be_replaced_by_previous_applied_state(self):
        payload = json.loads(self.raw)
        payload['contexts'][-1]['previous_integer_request'] = 2
        self.reject(canonical(payload), 'RECORDING_PREFLIGHT_INPUT:2:MODEL_PREVIOUS_REQUEST_MISMATCH', semantic=True)

    def test_signed_zero_subnormal_words_clocks_and_int64_endpoints_stay_exact(self):
        base = self.recording.records[0]
        for clock in ('DECLARED_LIVE_MONOTONIC_NS', 'DECLARED_REPLAY_RECORDED_CAN_NS'):
            for words in (('80000000', '00000001'), ('80000001', '00000000')):
                frames = tuple(replace(base, request=replace(base.request, context=replace(base.request.context,
                    clock_domain=clock), sequence=7 + i, sample_time_ns=(-(1 << 63), (1 << 63) - 1)[i],
                    requested_binary32=bytes.fromhex(word)), limited_state_at_entry=0, saved_limited_state=0,
                    angle_counter_at_entry=0, saved_angle_counter=0) for i, word in enumerate(words))
                contexts = (replace(self.contexts[0], model_index=4095, previous_integer_request=0,
                    current_driver=-0.0, current_angle_deg=-0.0),)
                raw = self.codec.encode_recording_input(self.base.recorder.FinishedSyntheticRecordingV1(frames), contexts)
                result, counts = self.counted(lambda raw=raw: self.m.check_serialized_recording_input(raw))
                self.assertEqual(result.status, 'MATCH')
                self.assertEqual(tuple(f.request.requested_binary32.hex() for f in result.frames), words)
                self.assertEqual(tuple(f.request.sample_time_ns for f in result.frames), (-(1 << 63), (1 << 63) - 1))
                self.assertEqual(tuple(f.request.context.clock_domain for f in result.frames), (clock, clock))
                self.assertEqual(result.contexts[0].current_driver.hex(), '-0x0.0p+0')
                self.assertEqual(result.contexts[0].current_angle_deg.hex(), '-0x0.0p+0')
                self.assertEqual(result.checks[0].computed_next_state.index, 4096)
                self.assertEqual(counts, {'step': 1, 'simulate': 0})

    def test_maximum_recording_runs_exactly_127_transitions_to_last_index(self):
        base = self.recording.records[0]
        frames = tuple(replace(base, request=replace(base.request, sequence=7 + i, sample_time_ns=i,
            requested_binary32=bytes.fromhex('00000000')), limited_state_at_entry=0, saved_limited_state=0,
            angle_counter_at_entry=0, saved_angle_counter=0) for i in range(128))
        contexts = tuple(replace(self.contexts[0], model_index=3969 + i, previous_integer_request=0,
            current_driver=0.0, current_angle_deg=0.0) for i in range(127))
        raw = self.codec.encode_recording_input(self.base.recorder.FinishedSyntheticRecordingV1(frames), contexts)
        result, counts = self.counted(lambda: self.m.check_serialized_recording_input(raw))
        self.assertEqual((result.status, result.checked_transition_count, result.synthetic_model_steps), ('MATCH', 127, 127))
        self.assertEqual((result.checks[0].computed_next_state.index, result.checks[-1].computed_next_state.index), (3970, 4096))
        self.assertEqual(counts, {'step': 127, 'simulate': 0})

    def test_existing_result_contract_and_false_authority_remain_unchanged(self):
        result = self.m.check_serialized_recording_input(self.raw)
        self.assertEqual(result.contract_id, 'CORE7_COUNTERFACTUAL_DECLARED_SEQUENCE_V1')
        for name in ('first_frame_transition_checked', 'prehistory_checked', 'source_identity_reauthenticated',
                     'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
            self.assertIs(getattr(result, name), False)
        self.assertIs(json.loads(self.raw)['model_input_allowed'], False)

    def test_success_is_deterministic_and_does_not_mutate_saved_input(self):
        before = self.raw, canonical(self.payload)
        first = self.m.check_serialized_recording_input(self.raw)
        second = self.m.check_serialized_recording_input(self.raw)
        self.assertEqual(asdict(first), asdict(second))
        self.assertEqual((self.raw, canonical(self.payload)), before)

    def test_changed_bytes_after_success_are_revalidated_without_cache(self):
        self.assertEqual(self.m.check_serialized_recording_input(self.raw).status, 'MATCH')
        payload = json.loads(self.raw)
        payload['contexts'][-1]['model_index'] = 0
        self.reject(canonical(payload), 'RECORDING_PREFLIGHT_INPUT:2:MODEL_INDEX', semantic=True)

    def test_bare_recording_bytes_objects_and_receipts_are_not_complete_inputs(self):
        receipt = self.codec.decode_recording_input(self.raw)
        for raw in (self.base.raw, self.recording, receipt):
            self.reject(raw)

    def test_unexpected_decoder_error_propagates_without_steps_or_success(self):
        error = RuntimeError('DECODER_DEPENDENCY_SENTINEL')

        def call():
            with patch.object(self.m, 'decode_recording_input', side_effect=error):
                with self.assertRaises(RuntimeError) as caught:
                    self.m.check_serialized_recording_input(self.raw)
            self.assertIs(caught.exception, error)
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_late_value_error_keeps_existing_masked_code_and_prior_work(self):
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
                with self.assertRaises(self.base.sequence.SequenceCheckError) as caught:
                    self.m.check_serialized_recording_input(self.raw)
            self.assertEqual(caught.exception.code, 'SEQUENCE_TRANSITION:2:TRANSITION_MODEL_FAILURE')
            self.assertNotIn('RAW_SENTINEL', str(caught.exception))
        _, counts = self.counted(call)
        self.assertEqual((attempts, counts), (3, {'step': 2, 'simulate': 0}))

    def test_late_unexpected_model_error_keeps_identity_and_nonzero_prior_work(self):
        original = self.model.step
        error = RuntimeError('MODEL_DEPENDENCY_SENTINEL')
        attempts = 0

        def fail_late(sample, state):
            nonlocal attempts
            attempts += 1
            if attempts == 3:
                raise error
            return original(sample, state)

        def call():
            with patch.object(self.model, 'step', side_effect=fail_late):
                with self.assertRaises(RuntimeError) as caught:
                    self.m.check_serialized_recording_input(self.raw)
            self.assertIs(caught.exception, error)
        _, counts = self.counted(call)
        self.assertEqual((attempts, counts), (3, {'step': 2, 'simulate': 0}))

    def test_codec_only_stays_zero_step_while_explicit_diagnostic_runs_three(self):
        receipt, counts = self.counted(lambda: self.codec.decode_recording_input(self.raw))
        self.assertEqual(receipt.status, 'INPUTS_COMPATIBLE')
        self.assertEqual(counts, {'step': 0, 'simulate': 0})
        result, counts = self.counted(lambda: self.m.check_serialized_recording_input(self.raw))
        self.assertEqual(result.status, 'MATCH')
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_no_context_override_policy_arguments_or_missing_raw_default(self):
        def call():
            with self.assertRaises(TypeError):
                self.m.check_serialized_recording_input()
            with self.assertRaises(TypeError):
                self.m.check_serialized_recording_input(self.raw, self.contexts)
            for name in ('contexts', 'rate_budget_per_s', 'dt', 'T2', 'actual_scale', 'model_input_allowed'):
                with self.assertRaises(TypeError):
                    self.m.check_serialized_recording_input(self.raw, **{name: 0})
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_existing_object_and_recording_plus_context_apis_keep_their_results(self):
        bundled = self.m.check_serialized_recording_input(self.raw)
        for call in (lambda: self.m.check_recorded_synthetic_sequence(self.recording, self.contexts),
                     lambda: self.m.check_serialized_synthetic_recording(self.base.raw, self.contexts)):
            result, counts = self.counted(call)
            self.assertEqual((result.status, result.checked_transition_count), ('MATCH', 3))
            self.assertEqual(asdict(result), asdict(bundled))
            self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_cold_import_executes_no_model_or_oracle_and_creates_no_files(self):
        code = '''import sys
import cyberlateral_dev as model
import cyberlateral_dev._r4.oracle as oracle
calls=[]
codes={model.step.__code__,model.simulate.__code__,oracle.oracle_limiter.__code__,oracle.oracle_fault.__code__}
sys.setprofile(lambda f,e,a: calls.append(f.f_code.co_name) if e=='call' and f.f_code in codes else None)
import integration_tools.offline_recording_diagnostics as diagnostics
sys.setprofile(None)
assert callable(diagnostics.check_serialized_recording_input)
assert not calls
assert not any(x.startswith(('openpilot','cereal','opendbc','synthetic_rate_constraint')) for x in sys.modules)
print('CORE58_IMPORT_NO_STEPS')
'''
        env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(ROOT), str(ROOT / 'src'))))
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-B', '-c', code], cwd=directory, env=env,
                capture_output=True, text=True, check=False)
            self.assertEqual((result.returncode, result.stdout.strip(), result.stderr), (0, 'CORE58_IMPORT_NO_STEPS', ''))
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
