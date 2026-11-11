"""Catch precision loss, JSON tampering and authority promotion in recordings."""
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from typing import Any

from test_offline_call_recorder import ROOT, frames


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


class RecordingCodecTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/offline_recording_codec.py').is_file(), 'Missing CORE41 codec')
        self.m: Any = importlib.import_module('integration_tools.offline_recording_codec')
        self.r: Any = importlib.import_module('integration_tools.offline_call_recorder')
        self.record = self.r.FinishedSyntheticRecordingV1(frames())

    def reject(self, raw):
        with self.assertRaises(self.r.RecorderError) as caught:
            self.m.decode_recording(raw)
        self.assertEqual((caught.exception.code, str(caught.exception)), ('RECORDER_SERIALIZATION', 'RECORDER_SERIALIZATION'))

    def test_literal_words_and_ns_tokens_survive_canonical_roundtrip(self):
        raw = self.m.encode_recording(self.record)
        obj = json.loads(raw)
        self.assertEqual(obj['records'][0]['request']['requested_binary32_hex'], '80000000')
        self.assertEqual(obj['records'][1]['request']['requested_binary32_hex'], '00000001')
        self.assertEqual(obj['records'][0]['request']['sample_time_ns'], '-9')
        self.assertEqual(obj['records'][1]['request']['sequence'], '8')
        self.assertEqual(obj['records'][0]['saved_limited_state'], -2)
        self.assertEqual(obj['gates']['R_BUDGET'], 'UNRESOLVED')
        self.assertIsNone(obj['gates']['T2'])
        self.assertEqual(raw, canonical(obj))
        decoded = self.m.decode_recording(raw)
        self.assertEqual(decoded.records, frames())
        self.assertEqual(self.m.encode_recording(decoded), raw)

    def test_large_integer_tokens_never_pass_through_json_number_or_float(self):
        first, second = frames()
        context = replace(first.request.context, reset_generation=(1 << 64) - 1, loss_generation=(1 << 64) - 1)
        first = replace(first, request=replace(first.request, context=context, sequence=(1 << 64) - 2, sample_time_ns=-(1 << 63)))
        second = replace(second, request=replace(second.request, context=context, sequence=(1 << 64) - 1, sample_time_ns=(1 << 63) - 1))
        raw = self.m.encode_recording(self.r.FinishedSyntheticRecordingV1((first, second)))
        obj = json.loads(raw)
        self.assertEqual(obj['records'][1]['request']['sequence'], '18446744073709551615')
        self.assertEqual(obj['records'][0]['request']['sample_time_ns'], '-9223372036854775808')
        self.assertEqual(obj['records'][0]['request']['context']['loss_generation'], '18446744073709551615')
        self.assertEqual(self.m.decode_recording(raw).records, (first, second))

    def test_wrong_types_empty_oversize_invalid_utf8_or_json_reject(self):
        for wrong in (None, '', bytearray(b'{}'), b'', b' ' * 262145, b'\xff', b'[]', b'{', b'NaN', b'{"x":NaN}', b'[' * 1100):
            self.reject(wrong)

    def test_duplicate_keys_pretty_json_and_noncanonical_tokens_reject(self):
        raw = self.m.encode_recording(self.record)
        self.reject(raw.replace(b'"schema_version":1', b'"schema_version":1,"schema_version":1', 1))
        self.reject(json.dumps(json.loads(raw), indent=2).encode())
        for text in ('+7', '07', '7.0', '7e0', '9' * 100):
            obj = json.loads(raw)
            obj['records'][0]['request']['sequence'] = text
            self.reject(canonical(obj))

    def test_extra_missing_fields_and_actual_scope_are_not_synthetic_authority(self):
        raw = self.m.encode_recording(self.record)
        for scope in ('ACTUAL_PRODUCTION', None):
            obj = json.loads(raw)
            obj['scope'] = scope
            self.reject(canonical(obj))
        for location in ('top', 'frame', 'request', 'context', 'settings'):
            obj = json.loads(raw)
            target = {'top': obj, 'frame': obj['records'][0], 'request': obj['records'][0]['request'],
                      'context': obj['records'][0]['request']['context'], 'settings': obj['records'][0]['settings']}[location]
            target['rate_budget_per_s'] = 0
            self.reject(canonical(obj))
        obj = json.loads(raw)
        del obj['records'][0]['request']['request_override']
        self.reject(canonical(obj))

    def test_permission_and_gate_changes_reject_even_with_other_valid_fields(self):
        raw = self.m.encode_recording(self.record)
        for name in ('source_identity_reauthenticated', 'model_input_allowed', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
            obj = json.loads(raw)
            obj[name] = True
            self.reject(canonical(obj))
        obj = json.loads(raw)
        obj['gates']['STATIC_EVIDENCE_GATE'] = 'PASS'
        self.reject(canonical(obj))

    def test_invalid_raw_word_or_numeric_field_cannot_be_normalized_on_read(self):
        raw = self.m.encode_recording(self.record)
        for word in ('8000000A', '7fc00000', '3f800001', '00', 0):
            obj = json.loads(raw)
            obj['records'][0]['request']['requested_binary32_hex'] = word
            self.reject(canonical(obj))
        obj = json.loads(raw)
        obj['records'][0]['request']['sample_time_ns'] = -9
        self.reject(canonical(obj))
        obj = json.loads(raw)
        obj['records'][0]['settings']['delta_up'] = 2.0
        self.reject(canonical(obj))

    def test_encoder_rejects_nonrecord_objects_without_attributes_or_calculations(self):
        class External:
            def __getattribute__(self, _name):
                raise AssertionError('EXTERNAL_READ')
        with self.assertRaises(self.r.RecorderError):
            self.m.encode_recording(External())

    def test_fresh_imports_do_not_load_model_vehicle_or_calculator_modules_or_write_files(self):
        code = (f'import sys,json;sys.path.insert(0,{str(ROOT)!r});'
                'import integration_tools.offline_call_recorder,integration_tools.offline_recording_codec;'
                'print(json.dumps([x for x in sys.modules if x.startswith(("cyberlateral_dev","openpilot","cereal","opendbc","synthetic_rate_constraint"))]))')
        with tempfile.TemporaryDirectory() as name:
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code], cwd=name, capture_output=True, text=True, check=False)
            self.assertEqual((result.returncode, result.stdout.strip(), result.stderr), (0, '[]', ''))
            self.assertEqual(list(Path(name).iterdir()), [])
