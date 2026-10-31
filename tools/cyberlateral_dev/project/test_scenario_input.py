"""Strict user-declared synthetic preflight; parser must never load a model."""

import hashlib
import importlib
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from scenario_fixture import document, encode
from v1_helpers import ROOT


class ScenarioInputTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_input.py').is_file(), 'Missing R31 parser')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_input')

    def reject(self, m, data, code):
        with self.assertRaises(m.ScenarioError) as error:
            m.parse_scenario(encode(data))
        self.assertEqual(error.exception.code, code)

    def test_literal_snapshot_and_raw_identity(self):
        m = self.module()
        raw = encode(document())
        spec = m.parse_scenario(raw)
        self.assertEqual((spec.scenario_id, spec.limits.STEER_MAX, spec.initial_state.index, spec.samples[0].request), ('R31_test', 16, 0, 0.25))
        self.assertEqual(spec.raw_sha256, hashlib.sha256(raw).hexdigest())
        self.assertIs(type(spec.samples), tuple)

    def test_binary64_point_three_and_signed_zero_not_float32_coerced(self):
        m = self.module()
        data = document()
        data['samples'][0].update(request=0.3, driver=-0.0, angle_deg=-0.0)
        sample = m.parse_scenario(encode(data)).samples[0]
        self.assertEqual(sample.request.hex(), '0x1.3333333333333p-2')
        self.assertEqual((sample.driver.hex(), sample.angle_deg.hex()), ('-0x0.0p+0', '-0x0.0p+0'))

    def test_exact_float_tokens_not_integer_or_bool_coercion(self):
        m = self.module()
        for field in ['request', 'driver', 'angle_deg']:
            for value in [0, True, '0.0', None]:
                data = document()
                data['samples'][0][field] = value
                self.reject(m, data, 'SCENARIO_DOMAIN')

    def test_scope_version_identifier_and_unknown_fields(self):
        m = self.module()
        for key, value, code in [('scope', 'ACTUAL', 'SCENARIO_SCOPE'), ('schema_version', True, 'SCENARIO_SCHEMA'),
                                 ('scenario_id', '../outside', 'SCENARIO_ID'), ('scenario_id', '=FORMULA()', 'SCENARIO_ID')]:
            data = document()
            data[key] = value
            self.reject(m, data, code)
        for key in ['rate_budget_per_s', 'dt', 'timestamp_ns', 'vehicle', 'source_path']:
            data = document()
            data[key] = 0
            self.reject(m, data, 'SCENARIO_KEYS')

    def test_missing_or_unknown_nested_fields_never_default(self):
        m = self.module()
        for target in ['limits', 'initial_state', 'sample']:
            data = document()
            nested = data['samples'][0] if target == 'sample' else data[target]
            nested.pop(next(iter(nested)))
            self.reject(m, data, 'SCENARIO_KEYS')
            data = document()
            nested = data['samples'][0] if target == 'sample' else data[target]
            nested['fallback'] = 0
            self.reject(m, data, 'SCENARIO_KEYS')

    def test_duplicate_keys_nonfinite_invalid_utf8_bom_and_trailing_json(self):
        m = self.module()
        raw = encode(document())
        bad = [raw.replace(b'"driver":0.0', b'"driver":0.0,"driver":1.0'),
               raw.replace(b'0.25', b'NaN'), raw.replace(b'0.25', b'Infinity'), raw.replace(b'0.25', b'1e999'),
               b'\xff', b'\xef\xbb\xbf' + raw, raw + b'{}', b'{']
        for value in bad:
            with self.assertRaises(m.ScenarioError) as error:
                m.parse_scenario(value)
            self.assertEqual(error.exception.code, 'SCENARIO_JSON')

    def test_bounded_numeric_tokens_deep_json_and_file_size(self):
        m = self.module()
        raw = encode(document())
        bad = [raw.replace(b'0.25', b'0.' + b'1' * 129),
               raw.replace(b'"STEER_MAX":16', b'"STEER_MAX":' + b'1' * 33),
               b'[' * 1100 + b'0' + b']' * 1100]
        for value in bad:
            with self.assertRaises(m.ScenarioError) as error:
                m.parse_scenario(value)
            self.assertEqual(error.exception.code, 'SCENARIO_JSON')
        with self.assertRaises(m.ScenarioError) as error:
            m.parse_scenario(b' ' * (1048576 + 1))
        self.assertEqual(error.exception.code, 'SCENARIO_SIZE')

    def test_floating_ranges_dyadic_domain_and_bool_active(self):
        m = self.module()
        for field, value in [('request', 1.01), ('driver', 1025.0), ('driver', 0.1), ('angle_deg', 180.5), ('angle_deg', 0.1), ('lat_active', 1)]:
            data = document()
            data['samples'][0][field] = value
            self.reject(m, data, 'SCENARIO_DOMAIN')
        data = document()
        data['samples'][0].update(request=-1.0, driver=-1024.0, angle_deg=180.0, lat_active=False)
        m.parse_scenario(encode(data))

    def test_explicit_limits_and_initial_state_rules(self):
        m = self.module()
        for name, value in [('STEER_MAX', 0), ('STEER_MAX', 2049), ('STEER_DELTA_UP', True), ('STEER_DELTA_DOWN', 65), ('STEER_DRIVER_FACTOR', 9)]:
            data = document()
            data['limits'][name] = value
            self.reject(m, data, 'SCENARIO_DOMAIN')
        for name, value in [('previous_requested', 0), ('previous_applied', 1), ('angle_counter', 1), ('index', True)]:
            data = document()
            data['initial_state'][name] = value
            self.reject(m, data, 'SCENARIO_STATE')

    def test_resumed_state_is_explicit_not_repaired(self):
        m = self.module()
        data = document()
        data['initial_state'].update(index=5, previous_requested=2, previous_applied=-3, angle_counter=89)
        data['samples'][0]['index'] = 5
        spec = m.parse_scenario(encode(data))
        self.assertEqual((spec.initial_state.previous_requested, spec.initial_state.previous_applied), (2, -3))
        data['initial_state']['previous_requested'] = None
        self.reject(m, data, 'SCENARIO_STATE')

    def test_all_indices_and_final_sample_preflight(self):
        m = self.module()
        for index in [True, 1, -1, 4096]:
            data = document()
            data['samples'][0]['index'] = index
            self.reject(m, data, 'SCENARIO_ORDER')
        data = document(3)
        data['samples'][-1]['driver'] = 0.1
        self.reject(m, data, 'SCENARIO_DOMAIN')

    def test_one_to4096_samples_and_end_index_bounds(self):
        m = self.module()
        self.assertEqual(len(m.parse_scenario(encode(document(4096))).samples), 4096)
        self.reject(m, document(0), 'SCENARIO_COUNT')
        self.reject(m, document(4097), 'SCENARIO_COUNT')
        data = document(2)
        data['initial_state'].update(index=4095, previous_requested=0)
        data['samples'][0]['index'], data['samples'][1]['index'] = 4095, 4096
        self.reject(m, data, 'SCENARIO_ORDER')

    def test_frozen_records_and_forged_spec_revalidation(self):
        m = self.module()
        spec = m.parse_scenario(encode(document()))
        with self.assertRaises(FrozenInstanceError):
            spec.scenario_id = 'OTHER'
        bad = replace(spec, samples=(replace(spec.samples[0], request=2.0),))
        with self.assertRaises(m.ScenarioError) as error:
            m.validate_spec(bad)
        self.assertEqual(error.exception.code, 'SCENARIO_DOMAIN')

    def test_regular_file_snapshot_and_symlink_directory_device_refusal(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            path = root / 'input.json'
            raw = encode(document())
            path.write_bytes(raw)
            spec = m.read_scenario(path)
            path.write_bytes(b'changed')
            self.assertEqual(spec.raw_sha256, hashlib.sha256(raw).hexdigest())
            (root / 'link').symlink_to(path)
            for invalid in [root, root / 'link', root / 'missing', Path('/dev/null')]:
                with self.assertRaises(m.ScenarioError) as error:
                    m.read_scenario(invalid)
                self.assertEqual(error.exception.code, 'SCENARIO_INPUT_FILE')

    def test_fifo_is_rejected_without_blocking(self):
        self.module()
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / 'fifo'
            os.mkfifo(path)
            code = ('import sys;from pathlib import Path;sys.path.insert(0,' + repr(str(ROOT)) + ');'
                    'from integration_tools.scenario_input import read_scenario,ScenarioError\n'
                    'try: read_scenario(Path(' + repr(str(path)) + '))\n'
                    'except ScenarioError as e: print(e.code)\n')
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, timeout=3, check=False)
            self.assertEqual((result.returncode, result.stdout), (0, b'SCENARIO_INPUT_FILE\n'))

    def test_parser_import_has_no_model_or_native_side_effect(self):
        self.module()
        code = ('import sys;sys.path.insert(0,' + repr(str(ROOT)) + ');import integration_tools.scenario_input;'
                'assert not any(n.split(".")[0] in {"cyberlateral_dev","capnp","numpy","openpilot","opendbc","cereal"} for n in sys.modules)')
        result = subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
