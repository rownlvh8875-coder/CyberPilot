"""R22 closed input gates and preregistered whole-output checks, not vehicle IO."""

import importlib
import sys
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


class ModelConsumptionTests(unittest.TestCase):
    def modules(self):
        self.assertTrue((ROOT / 'integration_tools/model_consumption.py').is_file(), 'Missing closed model consumer')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        p = package_feature()
        return (importlib.import_module('integration_tools.model_consumption'),
                importlib.import_module('integration_tools.fixed_model_reference'), p)

    def inputs(self, p, case='rounded_request'):
        values = {
            'zero': (0, 0.0, 0.0, 0.0, False, (0, None, 0, 0)),
            'rounded_request': (0, 0.30000001192092896, 1.5, -7.25, True, (0, None, 0, 0)),
            'signed_zero': (0, -0.0, -0.0, -0.0, False, (0, None, 0, 0)),
            'resumed': (1, 0.25, 2.0, 8.0, True, (1, 5, 3, 1)),
            'smallest_subnormal': (0, float.fromhex('0x1p-149'), 0.0, 0.0, True, (0, None, 0, 0)),
        }
        index, request, driver, angle, active, state = values[case]
        return p.LateralInput(index, request, driver, angle, active, p.Limits(16, 2, 5, 7, 1, 3), 'SYNTHETIC_ONLY'), p.LateralState(*state)

    def test_five_literal_results_match_with_exactly_five_real_steps(self):
        m, _, p = self.modules()
        expected = [('zero', 0, False, (1, 0, 0, 0)), ('rounded_request', 2, True, (1, 5, 2, 0)),
                    ('signed_zero', 0, False, (1, 0, 0, 0)), ('resumed', 4, True, (2, 4, 4, 0)),
                    ('smallest_subnormal', 0, True, (1, 0, 0, 0))]
        with patch.object(p, 'step', wraps=p.step) as step:
            for case, command, request, state in expected:
                result = m.consume_closed_case(case, *self.inputs(p, case))
                self.assertEqual(result.projection.integer_command, command)
                self.assertIs(result.steer_request, request)
                self.assertEqual(result.next_state, p.LateralState(*state))
            self.assertEqual(step.call_count, 5)

    def test_literal_trace_precision_rate_and_schema_words(self):
        m, _, p = self.modules()
        result = m.consume_closed_case('rounded_request', *self.inputs(p))
        self.assertEqual(result.trace.quantization.product_hex, '0x1.3333340000000p+2')
        self.assertEqual(result.trace.quantization.integer_command, 5)
        self.assertEqual((result.trace.downstream.rate_clip.lower.value, result.trace.downstream.rate_clip.upper.value), (-2, 2))
        self.assertEqual(result.projection.normalized_expression_hex, '0x1.0000000000000p-3')
        self.assertEqual((result.projection.torque_float32.bits_hex, result.projection.torque_output_can_float32.bits_hex), ('3e000000', '40000000'))
        self.assertEqual(result.projection.status, 'SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE')

    def test_signed_zero_preserved_in_quantization_not_in_integer_output(self):
        m, _, p = self.modules()
        result = m.consume_closed_case('signed_zero', *self.inputs(p, 'signed_zero'))
        self.assertEqual(result.trace.quantization.request_hex, '-0x0.0p+0')
        self.assertEqual(result.trace.quantization.product_hex, '-0x0.0p+0')
        self.assertEqual(result.projection.normalized_expression_hex, '0x0.0p+0')

    def test_unknown_or_non_builtin_case_rejects_before_step(self):
        m, _, p = self.modules()
        class Strange(str):
            def __hash__(self):
                raise AssertionError('Do not hash untrusted subclasses')
        with patch.object(p, 'step', side_effect=AssertionError('No step before gate')):
            for name in ['unknown', 'driver_precision_reject', None, Strange('zero')]:
                with self.assertRaisesRegex(ValueError, 'CONSUMPTION_CASE'):
                    m.consume_closed_case(name, *self.inputs(p))

    def test_same_case_id_changed_request_driver_angle_active_or_limits_rejects(self):
        m, _, p = self.modules()
        sample, state = self.inputs(p)
        values = [replace(sample, request=0.3), replace(sample, driver=0.0), replace(sample, angle_deg=0.0),
                  replace(sample, lat_active=False), replace(sample, limits=replace(sample.limits, STEER_MAX=17)),
                  replace(sample, provenance='ACTUAL'), replace(sample, index=1)]
        with patch.object(p, 'step', side_effect=AssertionError('No model work for mismatched input')):
            for changed in values:
                with self.assertRaisesRegex(ValueError, 'CONSUMPTION_INPUT_MISMATCH'):
                    m.consume_closed_case('rounded_request', changed, state)

    def test_negative_zero_and_prior_history_mismatch_reject_before_step(self):
        m, _, p = self.modules()
        sample, state = self.inputs(p, 'signed_zero')
        with patch.object(p, 'step', side_effect=AssertionError('No mismatched step')):
            with self.assertRaisesRegex(ValueError, 'CONSUMPTION_INPUT_MISMATCH'):
                m.consume_closed_case('signed_zero', replace(sample, request=0.0), state)
            sample, state = self.inputs(p, 'resumed')
            with self.assertRaisesRegex(ValueError, 'CONSUMPTION_INPUT_MISMATCH'):
                m.consume_closed_case('resumed', sample, p.LateralState(1, 4, 3, 1))

    def test_wrong_records_or_primitive_types_reject_without_callbacks(self):
        m, _, p = self.modules()
        sample, state = self.inputs(p)
        class Hostile:
            def __getattribute__(self, name):
                raise AssertionError('No hostile properties')
        with patch.object(p, 'step', side_effect=AssertionError('No malformed step')):
            for s, prior in [(Hostile(), state), (sample, Hostile()), (replace(sample, limits=Hostile()), state),
                             (replace(sample, request=1), state), (replace(sample, lat_active=1), state)]:
                with self.assertRaisesRegex(ValueError, 'CONSUMPTION_INPUT_TYPE'):
                    m.consume_closed_case('rounded_request', s, prior)

    def test_no_simulation_initialization_or_input_mutation(self):
        m, _, p = self.modules()
        sample, state = self.inputs(p, 'resumed')
        before = asdict(sample), asdict(state)
        with (patch.object(p, 'simulate', side_effect=AssertionError('No chain')),
              patch.object(p, 'initial_state', side_effect=AssertionError('No fallback'))):
            m.consume_closed_case('resumed', sample, state)
        self.assertEqual((asdict(sample), asdict(state)), before)

    def test_reference_expected_assembly_is_independent_with_model_disabled(self):
        _, reference, p = self.modules()
        with patch.object(p, 'step', side_effect=AssertionError('Do not derive expected from model')):
            expected = reference.expected_output('resumed')
            self.assertEqual(expected['projection']['integer_command'], 4)
            self.assertEqual(expected['trace']['downstream']['rate_clip']['upper']['value'], 5)
            self.assertEqual(expected['next_state'], {'index': 2, 'previous_requested': 4, 'previous_applied': 4, 'angle_counter': 0})

    def test_reference_identity_and_copy_isolation(self):
        _, reference, _ = self.modules()
        first = reference.load_reference()
        first['limits'][0] = 999
        self.assertEqual(reference.load_reference()['limits'], [16, 2, 5, 7, 1, 3])
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / 'bad.json'
            path.write_bytes(b'{}')
            with patch.object(reference, 'REFERENCE_PATH', path), self.assertRaisesRegex(ValueError, 'MODEL_REFERENCE_IDENTITY'):
                reference.load_reference()

    def test_complete_output_mutations_reject_with_unchanged_final_command(self):
        m, _, p = self.modules()
        result = m.consume_closed_case('rounded_request', *self.inputs(p))
        mutations = [replace(result, steer_request=False), replace(result, next_state=p.LateralState(1, 4, 2, 0)),
                     replace(result, projection=replace(result.projection, torque_float32=replace(result.projection.torque_float32, bits_hex='00000000'))),
                     replace(result, trace=replace(result.trace, quantization=replace(result.trace.quantization, product_hex='0x0.0p+0'))),
                     replace(result, trace=replace(result.trace, downstream=replace(result.trace.downstream, fault_condition=True)))]
        for changed in mutations:
            self.assertEqual(changed.projection.integer_command, 2)
            with self.assertRaisesRegex(ValueError, 'CONSUMPTION_OUTPUT_MISMATCH'):
                m.verify_output('rounded_request', changed)

    def test_model_bad_return_is_not_exposed_as_success(self):
        m, _, p = self.modules()
        with patch.object(p, 'step', return_value=None) as step:
            with self.assertRaisesRegex(ValueError, 'CONSUMPTION_OUTPUT_TYPE'):
                m.consume_closed_case('rounded_request', *self.inputs(p))
            self.assertEqual(step.call_count, 1)

    def test_package_version_mismatch_rejects_before_step(self):
        m, _, p = self.modules()
        with patch.object(p, '__version__', '0.4.0'), patch.object(p, 'step', side_effect=AssertionError('No wrong package')):
            with self.assertRaisesRegex(ValueError, 'CONSUMPTION_PACKAGE_VERSION'):
                m.consume_closed_case('rounded_request', *self.inputs(p))


if __name__ == '__main__':
    unittest.main()
