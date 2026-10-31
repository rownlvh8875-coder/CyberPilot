"""Literal source-derived sequence assertions and fail-before-step regressions."""

import importlib
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


def sample(p, index):
    return p.LateralInput(index, [float.fromhex('0x1.333334p-2'), -0.25, 0.25, 0.25][index], 0.0, 0.0,
                          [True, True, False, True][index], p.Limits(16, 2, 5, 7, 1, 3), 'SYNTHETIC_ONLY')


class SequenceConsumptionTests(unittest.TestCase):
    def modules(self):
        self.assertTrue((ROOT / 'integration_tools/sequence_consumption.py').is_file(), 'Missing closed sequence consumer')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        p = package_feature()
        return p, importlib.import_module('integration_tools.sequence_consumption'), importlib.import_module('integration_tools.sequence_reference')

    def test_four_steps_have_literal_outputs_states_and_no_extra_model_calls(self):
        p, consumer, _ = self.modules()
        state = p.LateralState(0, None, 0, 0)
        with patch.object(p, 'step', wraps=p.step) as step, patch.object(p, 'simulate', side_effect=AssertionError('simulation')), \
                patch.object(p, 'initial_state', side_effect=AssertionError('initialization')):
            for index, command, previous_request in [(0, 2, 5), (1, -2, -4), (2, 0, 4), (3, 2, 4)]:
                output = consumer.consume_fixed_step(index, sample(p, index), state)
                self.assertEqual(output.projection.integer_command, command)
                self.assertEqual(output.next_state, p.LateralState(index + 1, previous_request, command, 0))
                self.assertEqual(step.call_count, index + 1)
                state = output.next_state

    def test_sign_transition_inactive_trace_and_following_state(self):
        p, consumer, _ = self.modules()
        states = [p.LateralState(1, 5, 2, 0), p.LateralState(2, -4, -2, 0), p.LateralState(3, 4, 0, 0)]
        for index, state, bounds, final, limited in [(1, states[0], (-2, 4), -2, -2),
                                                     (2, states[1], (-4, 2), 0, 2), (3, states[2], (-2, 2), 2, 2)]:
            output = consumer.consume_fixed_step(index, sample(p, index), state)
            trace = output.trace.downstream
            self.assertEqual((trace.rate_clip.lower.value, trace.rate_clip.upper.value), bounds)
            self.assertEqual((trace.limited_command, trace.final_command), (limited, final))
            self.assertEqual(trace.limiter_previous, state.previous_applied)
        negative = consumer.consume_fixed_step(1, sample(p, 1), states[0])
        self.assertEqual(negative.projection.torque_float32.bits_hex, 'be000000')
        self.assertEqual(negative.projection.torque_output_can_float32.bits_hex, 'c0000000')

    def test_changed_state_reset_previous_request_and_pre_gate_output_reject_before_step(self):
        p, consumer, _ = self.modules()
        with patch.object(p, 'step', side_effect=AssertionError('must not step')):
            for index, state in [(1, p.LateralState(1, None, 0, 0)), (1, p.LateralState(1, 5, 5, 0)),
                                  (3, p.LateralState(3, 4, 2, 0)), (2, p.LateralState(2, -4, -2, 1))]:
                with self.assertRaisesRegex(ValueError, 'SEQUENCE_INPUT_MISMATCH'):
                    consumer.consume_fixed_step(index, sample(p, index), state)

    def test_changed_sign_zero_settings_provenance_or_active_reject_before_step(self):
        p, consumer, _ = self.modules()
        original = sample(p, 0)
        changes = [replace(original, driver=-0.0), replace(original, angle_deg=-0.0), replace(original, request=0.3),
                   replace(original, lat_active=False), replace(original, provenance='ACTUAL'),
                   replace(original, limits=replace(original.limits, STEER_MAX=409))]
        with patch.object(p, 'step', side_effect=AssertionError('must not step')):
            for changed in changes:
                with self.assertRaisesRegex(ValueError, 'SEQUENCE_INPUT_MISMATCH'):
                    consumer.consume_fixed_step(0, changed, p.LateralState(0, None, 0, 0))

    def test_index_and_exact_record_types_fail_before_callbacks(self):
        p, consumer, _ = self.modules()
        with patch.object(p, 'step', side_effect=AssertionError('must not step')):
            for index in [True, -1, 4, '0', None]:
                with self.assertRaisesRegex(ValueError, 'SEQUENCE_INDEX'):
                    consumer.consume_fixed_step(index, object(), object())
            with self.assertRaisesRegex(ValueError, 'CONSUMPTION_INPUT_TYPE'):
                consumer.consume_fixed_step(0, object(), p.LateralState(0, None, 0, 0))

    def test_full_output_mutation_with_unchanged_final_is_rejected(self):
        p, consumer, _ = self.modules()
        state = p.LateralState(0, None, 0, 0)
        output = consumer.consume_fixed_step(0, sample(p, 0), state)
        changed = replace(output, trace=replace(output.trace, downstream=replace(output.trace.downstream, limiter_previous=1)))
        with patch.object(p, 'step', return_value=changed):
            with self.assertRaisesRegex(ValueError, 'SEQUENCE_OUTPUT_MISMATCH'):
                consumer.consume_fixed_step(0, sample(p, 0), state)

    def test_reference_identity_and_copy_isolation_with_model_disabled(self):
        p, _, reference = self.modules()
        with patch.object(p, 'step', side_effect=AssertionError('reference must not model')):
            expected = reference.expected_output(2)
            self.assertEqual(expected['next_state'], {'index': 3, 'previous_requested': 4, 'previous_applied': 0, 'angle_counter': 0})
            expected['trace']['downstream']['final_command'] = 99
            self.assertEqual(reference.expected_output(2)['trace']['downstream']['final_command'], 0)
            with tempfile.TemporaryDirectory() as scratch:
                wrong = Path(scratch) / 'wrong.json'
                wrong.write_bytes(b'{}')
                with patch.object(reference, 'REFERENCE_PATH', wrong), self.assertRaisesRegex(ValueError, 'SEQUENCE_REFERENCE_IDENTITY'):
                    reference.expected_input(0)

    def test_wrong_version_and_model_exception_do_not_retry(self):
        p, consumer, _ = self.modules()
        state = p.LateralState(0, None, 0, 0)
        with patch.object(p, '__version__', 'other'), patch.object(p, 'step', side_effect=AssertionError('must not step')):
            with self.assertRaisesRegex(ValueError, 'CONSUMPTION_PACKAGE_VERSION'):
                consumer.consume_fixed_step(0, sample(p, 0), state)
        with patch.object(p, 'step', side_effect=RuntimeError('model-failed')) as step:
            with self.assertRaisesRegex(RuntimeError, 'model-failed'):
                consumer.consume_fixed_step(0, sample(p, 0), state)
            self.assertEqual(step.call_count, 1)


if __name__ == '__main__':
    unittest.main()
