"""The approved partial signal projection must never become a vehicle input API."""

import importlib
import json
import struct
import subprocess
import sys
import unittest
from copy import deepcopy
from fractions import Fraction

from v1_helpers import ROOT


def payload():
    """Literal counterfactual pair, not a capture or an authenticated source record."""
    sample = {
        'value': -0.25,
        'dtype': 'IEEE754_BINARY32',
        'unit': 'normalized_command',
        'stage_id': 'REQUESTED_NORMALIZED',
        'source_commit': '6ca11a4aea8223ebfebb1140bd8094ef1b3c5b90',
        'control_mode': 'TORQUE_CONTROL',
        'clock_domain': 'LIVE_MONOTONIC_NS',
        'epoch_id': 'fixture-epoch',
        'sequence': 0,
        'active': True,
        'override': False,
        'time_source': 'CAR_CONTROLS_UPDATE_NOW_NANOS_ARGUMENT',
        'provenance': 'PUBLIC_SYNTHETIC_SOURCE_FIXTURE',
    }
    return {
        'schema_version': 4,
        'contract_id': 'F70UGHR_REQUEST_TO_REQUEST_EXACT_SUBSET_V4',
        'mode': 'SYNTHETIC_REFERENCE_ONLY',
        'source_identity': {
            'production_repository': 'ajouatom/openpilot',
            'production_commit': sample['source_commit'],
            'controller_path': 'opendbc_repo/opendbc/car/hyundai/carcontroller.py',
            'controller_symbol': 'CarController.update::CC.actuators.torque',
            'f61_source_sha256': 'f343b0edd5578348c570692f05d655dee8e2b1555492a1d99b218d3f81fab035',
        },
        'current_production_value': {**sample, 'sequence': 1, 'value': 0.5},
        'previous_production_state': sample,
        'current_sample_time_ns': 1_001_953_125,
        'previous_sample_time_ns': 1_000_000_000,
        'static_context_reference': {
            'kind': 'PUBLIC_SYNTHETIC_SOURCE_FIXTURE',
            'fixture_id': 'unit-counterfactual',
            'vehicle_context': None,
            'actual_vehicle_gate': 'FAIL',
        },
        'reset_between_samples': False,
    }


class F61SignalAdapterTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/f61_signal_adapter_v4.py').is_file(), 'Missing DEV F61 signal adapter')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.f61_signal_adapter_v4')

    def check(self, value, code=None):
        before = deepcopy(value)
        result = self.module().adapt(value)
        independent = importlib.import_module('f61_signal_oracle').oracle(value)
        # JSON comparison preserves signed zero; numeric dict equality alone does not.
        self.assertEqual(json.dumps(result, sort_keys=True, allow_nan=False), json.dumps(independent, sort_keys=True, allow_nan=False))
        self.assertEqual(value, before)
        self.assertIs(result['accepted'], code is None)
        self.assertEqual(result['rejection_code'], code)
        self.assertFalse(result['calculator_invocation_allowed'])
        if code is not None:
            for key in ('f61_input', 'conversion_trace', 'source_binding', 'state_binding', 'time_binding', 'precision_binding'):
                self.assertIsNone(result[key])
        return result

    def test_literal_request_pair_projection_and_exact_dt(self):
        result = self.check(payload())
        self.assertEqual(
            result['f61_input'],
            {
                'projection_kind': 'PARTIAL_ADAPTER_SIGNAL_PROJECTION_NOT_CONSTRUCTOR_ARGS',
                'current_native': 0.5,
                'previous_native_if_required': -0.25,
                'previous_time': 0.0,
                'current_time': 0.001953125,
                'dt': 0.001953125,
            },
        )
        self.assertEqual(Fraction(result['f61_input']['dt']), Fraction(1, 512))
        self.assertEqual(result['conversion_trace']['seconds_hex'], '0x1.0000000000000p-9')
        self.assertEqual(result['state_binding']['previous_role'], 'PREVIOUS_REQUEST_NOT_APPLIED_COMMAND')

    def test_actual_mode_and_claimed_gate_pass_never_authorize(self):
        for gate, code in [('FAIL', 'STATIC_EVIDENCE_GATE_FAIL'), ('PASS', 'ACTUAL_PRODUCTION_PROHIBITED')]:
            value = payload()
            value['mode'] = 'ACTUAL_PRODUCTION'
            value['static_context_reference']['actual_vehicle_gate'] = gate
            with self.subTest(gate=gate):
                self.check(value, code)

    def test_vehicle_context_rejected_before_missing_fields_and_rate(self):
        value = payload()
        value['static_context_reference']['vehicle_context'] = {'declared_vehicle': True}
        value['rate_budget_per_s'] = 0
        value.pop('previous_production_state')
        self.check(value, 'STATIC_EVIDENCE_GATE_FAIL')

    def test_rate_budget_is_never_a_conversion_input_or_fallback(self):
        for rate in (None, 0, 1.0, float('nan'), 'UNRESOLVED'):
            value = payload()
            value['rate_budget_per_s'] = rate
            with self.subTest(rate=repr(rate)):
                self.check(value, 'RATE_BUDGET_NOT_AN_ADAPTER_INPUT')

    def test_missing_samples_and_times_have_no_inferred_defaults(self):
        for key, code in [
            ('current_production_value', 'MISSING_CURRENT_SAMPLE'),
            ('previous_production_state', 'MISSING_PREVIOUS_SAMPLE'),
            ('current_sample_time_ns', 'MISSING_SAMPLE_TIME'),
            ('previous_sample_time_ns', 'MISSING_SAMPLE_TIME'),
        ]:
            for absent in (True, False):
                value = payload()
                if absent:
                    value.pop(key)
                else:
                    value[key] = None
                with self.subTest(key=key, absent=absent):
                    self.check(value, code)

    def test_previous_applied_or_returned_stage_is_not_previous_request(self):
        for stage in ('APPLY_TORQUE_LAST', 'RETURNED_ACTUATOR', 'CAN_PACKED_TORQUE'):
            value = payload()
            value['previous_production_state']['stage_id'] = stage
            with self.subTest(stage=stage):
                self.check(value, 'UNSUPPORTED_STAGE')

    def test_source_identity_pins_and_matching_commit_required(self):
        for key in payload()['source_identity']:
            value = payload()
            value['source_identity'][key] = 'unapproved'
            with self.subTest(key=key):
                self.check(value, 'UNSUPPORTED_SOURCE')
        value = payload()
        value['current_production_value']['source_commit'] = '1dac44b22426711bdec4aa6ed79f0c8d55be1241'
        self.check(value, 'CONTEXT_MISMATCH')

    def test_second_pinned_commit_supported_only_as_complete_pair(self):
        value = payload()
        commit = '1dac44b22426711bdec4aa6ed79f0c8d55be1241'
        value['source_identity']['production_commit'] = commit
        for key in ('current_production_value', 'previous_production_state'):
            value[key]['source_commit'] = commit
        self.assertEqual(self.check(value)['source_binding']['commit'], commit)

    def test_clock_domains_explicit_and_never_mixed(self):
        value = payload()
        value['current_production_value']['clock_domain'] = 'REPLAY_RECORDED_CAN_NS'
        self.check(value, 'CONTEXT_MISMATCH')
        value['previous_production_state']['clock_domain'] = 'REPLAY_RECORDED_CAN_NS'
        self.assertEqual(self.check(value)['time_binding']['clock_domain'], 'REPLAY_RECORDED_CAN_NS')
        value['current_production_value']['clock_domain'] = 'WALL_CLOCK'
        self.check(value, 'UNSUPPORTED_CLOCK_DOMAIN')

    def test_epoch_mismatch_rejected(self):
        value = payload()
        value['previous_production_state']['epoch_id'] = 'other-epoch'
        self.check(value, 'CONTEXT_MISMATCH')

    def test_caroutput_and_nominal_frame_time_rejected(self):
        for source in ('CAROUTPUT_MESSAGE_TIME', 'FRAME_TIMES_DT_CTRL'):
            value = payload()
            value['current_production_value']['time_source'] = source
            with self.subTest(source=source):
                self.check(value, 'UNSUPPORTED_SAMPLE_TIME_SOURCE')

    def test_torque_mode_and_synthetic_provenance_required(self):
        for key, wrong, code in [
            ('control_mode', 'ANGLE_CONTROL', 'UNSUPPORTED_CONTROL_MODE'),
            ('provenance', 'ACTUAL_PRODUCTION', 'SYNTHETIC_FIXTURE_REQUIRED'),
        ]:
            value = payload()
            value['current_production_value'][key] = wrong
            with self.subTest(key=key):
                self.check(value, code)

    def test_sequence_is_adjacent_uint64_not_boolean_or_wraparound(self):
        for before, now in [(0, 2), (0, True), (-1, 0), ((1 << 64) - 1, 0), ((1 << 64) - 1, 1 << 64)]:
            value = payload()
            value['previous_production_state']['sequence'] = before
            value['current_production_value']['sequence'] = now
            with self.subTest(before=before, now=now):
                self.check(value, 'INVALID_SEQUENCE')
        value = payload()
        value['previous_production_state']['sequence'] = (1 << 64) - 2
        value['current_production_value']['sequence'] = (1 << 64) - 1
        self.check(value)

    def test_native_type_finite_range_and_exact_binary32(self):
        class FloatChild(float):
            pass

        for invalid in (
            True,
            1,
            FloatChild(0.5),
            '0.5',
            [0.5],
            float('nan'),
            float('inf'),
            -float('inf'),
            0.1,
            1.0000001192092896,
            -1.0000001192092896,
            2.0**-150,
        ):
            for key in ('current_production_value', 'previous_production_state'):
                value = payload()
                value[key]['value'] = invalid
                with self.subTest(key=key, invalid=repr(invalid)):
                    self.check(value, 'INVALID_NATIVE_VALUE')

    def test_native_endpoints_subnormal_and_exact_float32_point_one(self):
        for exact in (-1.0, 1.0, 0.0, -0.0, float.fromhex('0x1p-149'), 0.10000000149011612):
            assert type(exact) is float
            value = payload()
            value['current_production_value']['value'] = exact
            result = self.check(value)
            self.assertEqual(result['conversion_trace']['current_native_hex'], float.hex(exact))
            self.assertEqual(struct.pack('>d', result['f61_input']['current_native']), struct.pack('>d', exact))

    def test_nonpositive_time_not_replaced_with_nominal_period(self):
        for now in (1_000_000_000, 999_999_999):
            value = payload()
            value['current_sample_time_ns'] = now
            with self.subTest(now=now):
                self.check(value, 'TIME_ORDER')

    def test_inexact_or_overflowing_time_rejected_without_tolerance(self):
        for delta in (1, 10_000_000, ((1 << 53) + 1) * 1_000_000_000, 10**400):
            value = payload()
            value['current_sample_time_ns'] = value['previous_sample_time_ns'] + delta
            with self.subTest(delta_bits=delta.bit_length()):
                self.check(value, 'TIME_NOT_EXACTLY_REPRESENTABLE')

    def test_huge_signed_python_epoch_preserved_not_claimed_int64(self):
        for before in (10**5000, -(10**5000)):
            value = payload()
            value.update(previous_sample_time_ns=before, current_sample_time_ns=before + 1_953_125)
            result = self.check(value)
            self.assertEqual(int(result['conversion_trace']['epoch_ns_hex'], 16), before)
            self.assertEqual(result['f61_input']['dt'].hex(), '0x1.0000000000000p-9')
            self.assertFalse(result['time_binding']['global_F61_time_coordinate'])
            self.assertFalse(result['time_binding']['actual_acquisition_or_ECU_time_verified'])

    def test_flags_are_preserved_without_feasibility_or_command_selection(self):
        value = payload()
        value['current_production_value'].update(active=False, override=True)
        value['reset_between_samples'] = True
        result = self.check(value)
        self.assertFalse(result['state_binding']['current_active'])
        self.assertTrue(result['state_binding']['current_override'])
        self.assertTrue(result['state_binding']['reset_between_samples'])
        self.assertNotIn('status', result)
        self.assertNotIn('is_nonempty', result)
        self.assertNotIn('native', result['f61_input'])
        self.assertNotIn('rate_budget_per_s', result['f61_input'])

    def test_closed_schema_and_exact_structural_types(self):
        class DictChild(dict):
            pass

        for invalid in (None, [], True, DictChild(payload())):
            self.check(invalid, 'SCHEMA_INVALID')
        for field in (None, 'source_identity', 'current_production_value', 'previous_production_state', 'static_context_reference'):
            value = payload()
            (value if field is None else value[field])['unexpected'] = True
            with self.subTest(field=field):
                self.check(value, 'SCHEMA_INVALID')
        for key, wrong in [('schema_version', True), ('current_sample_time_ns', True), ('reset_between_samples', 0)]:
            value = payload()
            value[key] = wrong
            with self.subTest(key=key):
                self.check(value, 'SCHEMA_INVALID')
        value = payload()
        value.pop('reset_between_samples')
        self.check(value, 'SCHEMA_INVALID')

    def test_scale_sign_rounding_clipping_remain_identity_without_vehicle_scale(self):
        result = self.check(payload())
        trace = result['conversion_trace']
        self.assertEqual((trace['scale'], trace['offset'], trace['rounding'], trace['clipping']), (1, 0, 'NONE', 'NONE'))
        self.assertEqual(trace['previous_native_hex'], '-0x1.0000000000000p-2')
        self.assertNotIn('STEER_MAX', trace)

    def test_repeated_results_are_detached_and_input_unchanged(self):
        value = payload()
        before = deepcopy(value)
        first = self.check(value)
        encoded = json.dumps(first, sort_keys=True, allow_nan=False)
        first['f61_input']['current_native'] = -1.0
        second = self.check(value)
        self.assertEqual(json.dumps(second, sort_keys=True, allow_nan=False), encoded)
        self.assertEqual(value, before)

    def test_oracle_and_adapter_imports_do_not_load_model_or_calculator(self):
        self.module()
        for module in ('f61_signal_oracle', 'integration_tools.f61_signal_adapter_v4'):
            code = (
                f'import sys;sys.path[:0]={[str(ROOT), str(ROOT / "project")]!r};'
                'before=set(sys.modules);'
                f'import importlib;importlib.import_module({module!r});'
                'import json;print(json.dumps(sorted(set(sys.modules)-before)))'
            )
            run = subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            names = {name.split('.')[0] for name in json.loads(run.stdout)}
            forbidden = {
                'cyberlateral_dev',
                'numpy',
                'capnp',
                'cereal',
                'openpilot',
                'opendbc',
                'selfdrive',
                'synthetic_rate_constraint_feasibility_v1',
                'synthetic_rate_constraint_feasibility_reconstructed_v2',
            }
            self.assertFalse(names & forbidden)
            if module == 'f61_signal_oracle':
                self.assertNotIn('fractions', names)
                self.assertNotIn('integration_tools.f61_signal_adapter_v4', json.loads(run.stdout))
