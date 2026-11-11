"""Catch input loss,permissive wire parsing and accidental diagnostic execution."""
import importlib
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

import test_serialized_recording_diagnostics as source_fixture
from v1_helpers import ROOT


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class RecordingInputCodecTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/offline_recording_input_codec.py').is_file(), 'Missing CORE55 recording input codec')
        case = source_fixture.SerializedRecordingDiagnosticsTests('test_canonical_bytes_produce_literal_full_sequence_result')
        case.setUp()
        self.fixture = case
        self.model, self.recording, self.contexts = case.model, case.recording, case.contexts
        self.m: Any = importlib.import_module('integration_tools.offline_recording_input_codec')
        self.payload: dict[str, Any] = {'schema_version': 1, 'contract_id': 'CORE55_COUNTERFACTUAL_RECORDING_INPUT_V1',
            'scope': 'COUNTERFACTUAL_RECORDING_INPUT_ONLY', 'recording_json': case.raw.decode(),
            'contexts': [{'scope': 'COUNTERFACTUAL_MODEL_INPUT_ONLY', 'model_index': index,
                'previous_integer_request': previous, 'current_driver_hex': '0x1.8000000000000p+0',
                'current_angle_deg_hex': '0x1.5400000000000p+6'} for index, previous in ((5, -4), (6, 8), (7, -8))],
            'source_identity_reauthenticated': False, 'model_input_allowed': False, 'v4_payload_allowed': False,
            'f61_input_allowed': False, 'actual_activation_allowed': False}

    def counted(self, call):
        return self.fixture.counted(call)

    def reject(self, raw, code='RECORDING_INPUT_SERIALIZATION', semantic=False):
        error_type = self.fixture.preflight.RecordingPreflightError if semantic else self.m.RecordingInputCodecError

        def call():
            with self.assertRaises(error_type) as caught:
                self.m.decode_recording_input(raw)
            self.assertEqual((caught.exception.code, str(caught.exception)), (code, code))
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_encoder_matches_independent_literal_wire_without_steps(self):
        raw, counts = self.counted(lambda: self.m.encode_recording_input(self.recording, self.contexts))
        self.assertIs(type(raw), bytes)
        self.assertEqual(raw, canonical(self.payload))
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_decoder_restores_owned_receipt_without_steps_or_authority(self):
        receipt, counts = self.counted(lambda: self.m.decode_recording_input(canonical(self.payload)))
        self.assertIs(type(receipt), self.fixture.preflight.SyntheticRecordingInputPreflightV1)
        self.assertEqual((receipt.status, receipt.record_count, receipt.validated_transition_count), ('INPUTS_COMPATIBLE', 4, 3))
        self.assertEqual(receipt.recording.records, self.recording.records)
        self.assertEqual(tuple(asdict(c) for c in receipt.contexts), tuple(asdict(c) for c in self.contexts))
        for name in ('model_input_allowed', 'source_identity_reauthenticated', 'v4_payload_allowed',
                     'f61_input_allowed', 'actual_activation_allowed', 'first_frame_transition_checked', 'prehistory_checked'):
            self.assertIs(getattr(receipt, name), False)
        self.assertEqual((receipt.new_synthetic_model_steps, receipt.new_reference_steps), (0, 0))
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_deterministic_roundtrip_preserves_input_objects(self):
        before = (self.fixture.codec.encode_recording(self.recording), tuple(asdict(c) for c in self.contexts))
        first = self.m.encode_recording_input(self.recording, self.contexts)
        receipt = self.m.decode_recording_input(first)
        self.assertEqual(self.m.encode_recording_input(receipt.recording, receipt.contexts), first)
        self.assertEqual(self.m.encode_recording_input(self.recording, self.contexts), first)
        self.assertEqual((self.fixture.codec.encode_recording(self.recording), tuple(asdict(c) for c in self.contexts)), before)

    def test_only_separate_explicit_diagnostics_run_three_literal_transitions(self):
        receipt, counts = self.counted(lambda: self.m.decode_recording_input(canonical(self.payload)))
        self.assertEqual(counts, {'step': 0, 'simulate': 0})
        result, counts = self.counted(lambda: self.fixture.m.check_recorded_synthetic_sequence(receipt.recording, receipt.contexts))
        self.assertEqual((result.status, result.synthetic_model_steps), ('MATCH', 3))
        self.assertEqual(tuple(row.computed_next_state for row in result.checks),
            (self.model.LateralState(6, 8, 2, 5), self.model.LateralState(7, -8, -2, 6), self.model.LateralState(8, 4, 2, 7)))
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_raw_words_signed_auxiliary_zero_and_int64_times_remain_exact(self):
        base = self.recording.records[0]
        for clock in ('DECLARED_LIVE_MONOTONIC_NS', 'DECLARED_REPLAY_RECORDED_CAN_NS'):
            frames = tuple(replace(base, request=replace(base.request,
                context=replace(base.request.context, clock_domain=clock), sequence=7 + i,
                sample_time_ns=(-(1 << 63), (1 << 63) - 1)[i], requested_binary32=bytes.fromhex(word)),
                limited_state_at_entry=0, saved_limited_state=0, angle_counter_at_entry=0, saved_angle_counter=0)
                for i, word in enumerate(('80000000', '80000001')))
            contexts = (replace(self.contexts[0], model_index=4095, previous_integer_request=0,
                current_driver=-0.0, current_angle_deg=-0.0),)
            recording = self.fixture.recorder.FinishedSyntheticRecordingV1(frames)
            raw = self.m.encode_recording_input(recording, contexts)
            receipt, counts = self.counted(lambda raw=raw: self.m.decode_recording_input(raw))
            self.assertEqual(tuple(f.request.requested_binary32.hex() for f in receipt.recording.records), ('80000000', '80000001'))
            self.assertEqual(tuple(f.request.sample_time_ns for f in receipt.recording.records), (-(1 << 63), (1 << 63) - 1))
            self.assertEqual(receipt.contexts[0].current_driver.hex(), '-0x0.0p+0')
            self.assertEqual(receipt.contexts[0].current_angle_deg.hex(), '-0x0.0p+0')
            self.assertEqual(receipt.recording.records[0].request.context.clock_domain, clock)
            self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_maximum_128_records_and_127_contexts_are_accepted_without_work(self):
        base = self.recording.records[0]
        frames = tuple(replace(base, request=replace(base.request, sequence=7 + i, sample_time_ns=i,
            requested_binary32=bytes.fromhex('00000000')), limited_state_at_entry=0, saved_limited_state=0,
            angle_counter_at_entry=0, saved_angle_counter=0) for i in range(128))
        contexts = tuple(replace(self.contexts[0], model_index=3969 + i, previous_integer_request=0,
            current_driver=0.0, current_angle_deg=0.0) for i in range(127))
        recording = self.fixture.recorder.FinishedSyntheticRecordingV1(frames)
        raw, counts = self.counted(lambda: self.m.encode_recording_input(recording, contexts))
        self.assertLessEqual(len(raw), 1048576)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})
        receipt, counts = self.counted(lambda: self.m.decode_recording_input(raw))
        self.assertEqual((receipt.record_count, receipt.validated_transition_count, receipt.contexts[-1].model_index), (128, 127, 4095))
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_wrong_raw_types_are_not_coerced_or_accessed(self):
        class Foreign:
            def __getattribute__(self, _name):
                raise AssertionError('FOREIGN_READ')

        class Child(bytes):
            def __len__(self):
                raise AssertionError('CHILD_LENGTH')

        for raw in (None, '', {}, bytearray(b'{}'), memoryview(b'{}'), Foreign(), Child(b'{}')):
            self.reject(raw)

    def test_empty_oversize_invalid_utf8_and_json_reject(self):
        for raw in (b'', b' ' * 1048577, b'\xff', b'{', b'[]', b'null', b'{"x":NaN}', b'[' * 1100):
            self.reject(raw)

    def test_noncanonical_outer_and_duplicate_keys_are_not_repaired(self):
        raw = canonical(self.payload)
        for bad in (raw.rstrip(), b' ' + raw, json.dumps(self.payload, indent=2).encode(),
                    raw.replace(b'"schema_version":1', b'"schema_version":1,"schema_version":1'),
                    raw.replace(b'"model_index":5', b'"model_index":5,"model_index":5')):
            self.reject(bad)

    def test_outer_header_and_permission_types_are_exact(self):
        for key, value in (('schema_version', True), ('schema_version', 1.0), ('contract_id', 'OTHER'),
                ('scope', 'ACTUAL_PRODUCTION'), ('model_input_allowed', True), ('model_input_allowed', 0),
                ('actual_activation_allowed', True), ('source_identity_reauthenticated', True),
                ('v4_payload_allowed', True), ('f61_input_allowed', True)):
            data = dict(self.payload, **{key: value})
            self.reject(canonical(data))

    def test_extra_or_missing_outer_fields_reject(self):
        for key in self.payload:
            data = dict(self.payload)
            del data[key]
            self.reject(canonical(data))
        self.reject(canonical(dict(self.payload, rate_budget_per_s=0)))

    def test_inner_authority_or_link_tampering_rejects_as_serialization(self):
        for mode in ('permission', 'link', 'gate'):
            inner = json.loads(self.payload['recording_json'])
            if mode == 'permission':
                inner['actual_activation_allowed'] = True
            elif mode == 'link':
                inner['records'][-1]['limited_state_at_entry'] = 7
            else:
                inner['gates']['STATIC_EVIDENCE_GATE'] = 'PASS'
            self.reject(canonical(dict(self.payload, recording_json=canonical(inner).decode())))

    def test_inner_must_be_exact_canonical_utf8_text(self):
        for inner in (None, {}, self.payload['recording_json'].rstrip(), json.dumps(json.loads(self.payload['recording_json']), indent=2)):
            self.reject(canonical(dict(self.payload, recording_json=inner)))

    def test_context_shape_and_float_wire_types_are_exact(self):
        for mutation in ('extra', 'missing', 'driver_number', 'context_list'):
            data = json.loads(canonical(self.payload))
            if mutation == 'extra':
                data['contexts'][-1]['dt'] = 0
            elif mutation == 'missing':
                del data['contexts'][-1]['current_driver_hex']
            elif mutation == 'driver_number':
                data['contexts'][-1]['current_driver_hex'] = 1.5
            else:
                data['contexts'][-1] = []
            self.reject(canonical(data))

    def test_noncanonical_nonfinite_or_oversize_float_hex_is_not_normalized(self):
        for value in ('1.5', '0X1.8000000000000P+0', ' 0x1.8000000000000p+0', '0x1.8p+0',
                      'nan', 'inf', '-inf', '0x1.' + '0' * 40 + 'p+0'):
            data = json.loads(canonical(self.payload))
            data['contexts'][-1]['current_driver_hex'] = value
            self.reject(canonical(data))

    def test_late_numeric_semantic_error_preserves_core46_code(self):
        for text in ('0x1.0040000000000p+10', '0x1.999999999999ap-4'):
            data = json.loads(canonical(self.payload))
            data['contexts'][-1]['current_driver_hex'] = text
            self.reject(canonical(data), 'RECORDING_PREFLIGHT_INPUT:2:MODEL_DRIVER', semantic=True)

    def test_model_index_order_is_not_inferred(self):
        data = json.loads(canonical(self.payload))
        data['contexts'][-1]['model_index'] = 9
        self.reject(canonical(data), 'RECORDING_PREFLIGHT_MODEL_ORDER:2', semantic=True)

    def test_context_count_is_not_inferred_or_padded(self):
        self.reject(canonical(dict(self.payload, contexts=self.payload['contexts'][:1])), 'RECORDING_PREFLIGHT_CONTEXT_COUNT', semantic=True)

    def test_previous_integer_request_mismatch_is_not_repaired(self):
        data = json.loads(canonical(self.payload))
        data['contexts'][-1]['previous_integer_request'] = 0
        self.reject(canonical(data), 'RECORDING_PREFLIGHT_INPUT:2:MODEL_PREVIOUS_REQUEST_MISMATCH', semantic=True)

    def test_encoder_rejects_foreign_declarations_without_attribute_access(self):
        class Foreign:
            def __getattribute__(self, _name):
                raise AssertionError('FOREIGN_DECLARATION_READ')
        for recording, contexts, code in ((Foreign(), self.contexts, 'RECORDING_PREFLIGHT_RECORDING:RECORDER_RECORDING_TYPE'),
                (self.recording, Foreign(), 'RECORDING_PREFLIGHT_CONTEXT_CONTAINER'),
                (self.recording, list(self.contexts), 'RECORDING_PREFLIGHT_CONTEXT_CONTAINER')):
            def call(recording=recording, contexts=contexts, code=code):
                with self.assertRaises(self.fixture.preflight.RecordingPreflightError) as caught:
                    self.m.encode_recording_input(recording, contexts)
                self.assertEqual(caught.exception.code, code)
            _, counts = self.counted(call)
            self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_encoder_late_invalid_context_propagates_without_prefix(self):
        contexts = (*self.contexts[:2], replace(self.contexts[-1], current_driver=1))

        def call():
            with self.assertRaises(self.fixture.preflight.RecordingPreflightError) as caught:
                self.m.encode_recording_input(self.recording, contexts)
            self.assertEqual(caught.exception.code, 'RECORDING_PREFLIGHT_INPUT:2:MODEL_DRIVER')
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_receipt_is_not_an_encoder_recording_capability(self):
        receipt = self.m.decode_recording_input(canonical(self.payload))
        with self.assertRaises(self.fixture.preflight.RecordingPreflightError) as caught:
            self.m.encode_recording_input(receipt, self.contexts)
        self.assertEqual(caught.exception.code, 'RECORDING_PREFLIGHT_RECORDING:RECORDER_RECORDING_TYPE')

    def test_repeat_decoding_revalidates_changed_input(self):
        self.assertEqual(self.m.decode_recording_input(canonical(self.payload)).status, 'INPUTS_COMPATIBLE')
        self.payload['contexts'][-1]['model_index'] = 0
        self.reject(canonical(self.payload), 'RECORDING_PREFLIGHT_INPUT:2:MODEL_INDEX', semantic=True)

    def test_noncanonical_outer_precedes_semantic_error(self):
        data = json.loads(canonical(self.payload))
        data['contexts'][-1]['model_index'] = 0
        self.reject(json.dumps(data, indent=2).encode())

    def test_context_wire_count_bounds_are_structural(self):
        for contexts in (None, {}, [], self.payload['contexts'] * 43):
            self.reject(canonical(dict(self.payload, contexts=contexts)))

    def test_no_policy_arguments_or_defaults(self):
        for name in ('rate_budget_per_s', 'dt', 'T2', 'actual_scale'):
            with self.assertRaises(TypeError):
                self.m.encode_recording_input(self.recording, self.contexts, **{name: 0})
        with self.assertRaises(TypeError):
            self.m.encode_recording_input(self.recording)

    def test_unexpected_preflight_dependency_error_propagates(self):
        error = RuntimeError('UNEXPECTED_PREFLIGHT_FAILURE')
        with patch.object(self.m, 'preflight_recording_input', side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                self.m.decode_recording_input(canonical(self.payload))
        self.assertIs(caught.exception, error)

    def test_cold_import_has_no_model_steps_vehicle_imports_or_files(self):
        code = '''import sys
import cyberlateral_dev as model
calls=[]
codes={model.step.__code__,model.simulate.__code__}
sys.setprofile(lambda f,e,a: calls.append(e) if e=='call' and f.f_code in codes else None)
import integration_tools.offline_recording_input_codec
sys.setprofile(None)
assert not calls
assert not any(x.startswith(('openpilot','cereal','opendbc','synthetic_rate_constraint')) for x in sys.modules)
print('CORE55_IMPORT_NO_STEPS')
'''
        env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(ROOT), str(ROOT / 'src'))))
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-B', '-c', code], cwd=directory, env=env, capture_output=True, text=True, check=False)
            self.assertEqual((result.returncode, result.stdout.strip(), result.stderr), (0, 'CORE55_IMPORT_NO_STEPS', ''))
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
