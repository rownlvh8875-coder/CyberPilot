"""Closed runner preflight and data-only forged-export rejection."""

import copy
import importlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from v1_helpers import ROOT


class AdapterSequenceRunnerTests(unittest.TestCase):
    def modules(self):
        self.assertTrue((ROOT / 'native_qualification/adapter_sequence_run.py').is_file(), 'Missing R29 runner')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return (importlib.import_module('native_qualification.adapter_sequence_run'),
                importlib.import_module('native_qualification.adapter_sequence_validation'))

    def fixture(self):
        from integration_tools import negative_cycle_reference as negative
        from integration_tools import sequence_reference as sign
        profiles = []
        for name, count, reference in [('SIGN_CHANGE_4', 4, sign), ('NEGATIVE_CYCLE_99', 99, negative)]:
            rows: list[dict] = []
            for index in range(count):
                rows.append({'index': index, 'stamp': {'sequence_id': 'R29_' + name, 'invocation_index': index, 'capture_id': 'entry_' + str(index)},
                             'prepared': reference.expected_input(index), 'model_output': reference.expected_output(index),
                             'model_steps': 1, 'oracle_parity': True, 'cc_sha256': '0' * 64, 'cs_sha256': '0' * 64,
                             'read_claim': 'INTERNALLY_CONSTRUCTED_OWNED_SYNTHETIC_BYTES_READ_WITHIN_CONTEXT',
                             'state_binding': 'EXPLICIT_FIXED_INITIAL_DATA' if index == 0 else 'PREVIOUS_VERIFIED_MODEL_OUTPUT_NOT_ACTUAL_HISTORY'})
            profiles.append({'profile_id': name, 'reference_sha256': reference.REFERENCE_SHA256, 'model_execution': count,
                             'initial_state': {'index': 0, 'previous_requested': None, 'previous_applied': 0, 'angle_counter': 0},
                             'final_state': rows[-1]['model_output']['next_state'], 'cases': rows})
        return {'schema_version': 1, 'status': 'F70UGZ_R29_FIXED_SYNTHETIC_ADAPTER_MODEL_SEQUENCE_PASS',
                'scope': 'TWO_REGISTERED_SYNTHETIC_NATIVE_ADAPTER_MODEL_SEQUENCES_ONLY', 'profiles': profiles,
                'package_version': '0.3.0', 'model_execution': 103, 'observed_model_calls': 103,
                'F61_execution': 0, 'Controller_execution': 0, 'Runtime_execution': 0, 'CAN': 0,
                'calculator_input_execution': 0, 'actual_inputs': 0, 'r_calculation': 0, 'dt_calculation': 0,
                'actual_call_custody': 'NOT_QUALIFIED', 'actual_activation': 'NOT_ALLOWED', 'generic_external_reader': 'NOT_IMPLEMENTED',
                'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL', 'time_semantics': 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME'}

    def test_existing_output_is_preserved(self):
        m, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            output = root / 'exists'
            output.write_bytes(b'preserve')
            with self.assertRaisesRegex(FileExistsError, 'OUTPUT_EXISTS'):
                m.qualify(root / 'p', root / 'w', root / 'pub', output, enabled=True)
            self.assertEqual(output.read_bytes(), b'preserve')

    def test_opt_in_and_missing_parent_block_before_work(self):
        m, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            for enabled, code in [(False, 'CHAIN_OPT_IN_REQUIRED'), (1, 'CHAIN_EXPLICIT_BOOL')]:
                with self.assertRaisesRegex(ValueError, code):
                    m.qualify(root / 'p', root / 'w', root / 'pub', root / 'out', enabled=enabled)
            with self.assertRaisesRegex(ValueError, 'CHAIN_PARENT_REQUIRED'):
                m.qualify(root / 'p', root / 'w', root / 'pub', root / 'missing/out', enabled=True)

    def test_wrong_artifact_blocks_without_output(self):
        m, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            wrong = root / 'wrong.whl'
            wrong.write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError, 'PUBLIC_WHEEL_IDENTITY'):
                m.qualify(root / 'p', wrong, wrong, root / 'out', enabled=True)
            self.assertFalse((root / 'out').exists())

    def test_parent_import_does_not_load_native_or_model(self):
        self.modules()
        script = ('import sys;sys.path.insert(0,' + repr(str(ROOT)) + ');import native_qualification.adapter_sequence_run;'
                  'assert not any(n.split(".")[0] in {"capnp","cyberlateral_dev","numpy","openpilot","opendbc","cereal"} for n in sys.modules)')
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_complete_literal_fixture_validates_without_model_work(self):
        _, validation = self.modules()
        self.assertEqual(validation.validate_observations(self.fixture()), 103)

    def test_forged_input_output_and_state_are_rejected(self):
        _, validation = self.modules()
        original = self.fixture()
        for field in ['input', 'output', 'state', 'stamp']:
            data = copy.deepcopy(original)
            row = data['profiles'][0]['cases'][1]
            if field == 'input':
                row['prepared']['sample']['request_hex'] = '0x0.0p+0'
            elif field == 'output':
                row['model_output']['projection']['integer_command'] = 9
            elif field == 'state':
                row['prepared']['state']['previous_applied'] = 5
            else:
                row['stamp']['capture_id'] = 'OTHER'
            with self.assertRaises(ValueError):
                validation.validate_observations(data)

    def test_missing_rows_wrong_counts_and_promoted_gates_reject(self):
        _, validation = self.modules()
        original = self.fixture()
        for field in ['rows', 'model_count', 'bool_count', 'steps', 'gate', 'order', 'reference']:
            data = copy.deepcopy(original)
            if field == 'rows':
                data['profiles'][1]['cases'].pop()
            elif field == 'model_count':
                data['observed_model_calls'] = 102
            elif field == 'bool_count':
                data['profiles'][0]['cases'][0]['model_steps'] = True
            elif field == 'steps':
                data['profiles'][0]['cases'][0]['model_steps'] = 0
            elif field == 'gate':
                data['actual_activation'] = 'ALLOWED'
            elif field == 'order':
                data['profiles'].reverse()
            else:
                data['profiles'][0]['reference_sha256'] = '0' * 64
            with self.assertRaises(ValueError):
                validation.validate_observations(data)

    def test_malformed_shape_has_explicit_rejection(self):
        _, validation = self.modules()
        for data in [None, [], {}, {'profiles': None}]:
            with self.assertRaises(ValueError):
                validation.validate_observations(data)
