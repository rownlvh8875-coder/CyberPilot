"""Closed99-step negative cycle, hand-derived boundary/state/float expectations."""

import importlib
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


def sample(p, index):
    return p.LateralInput(index, -1.0, 8.5, -84.5 if index == 92 else -85.0,
                          index != 94, p.Limits(16, 2, 5, 7, 1, 3), 'SYNTHETIC_ONLY')


class NegativeCycleConsumptionTests(unittest.TestCase):
    def modules(self):
        self.assertTrue((ROOT / 'integration_tools/negative_cycle_consumption.py').is_file(), 'Missing negative-cycle consumer')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return (package_feature(), importlib.import_module('integration_tools.negative_cycle_consumption'),
                importlib.import_module('integration_tools.negative_cycle_reference'))

    def test_complete99_actual_output_state_carries_one_step_each(self):
        p, consumer, _ = self.modules()
        state = p.LateralState(0, None, 0, 0)
        commands = [-2, -4, -6, -8, -10, -12] + [-12] * 88 + [0, -2, -4, -6, -8]
        counters = list(range(1, 91)) + [0, 1, 0, 1, 0, 1, 2, 3, 4]
        with patch.object(p, 'step', wraps=p.step) as step, patch.object(p, 'simulate', side_effect=AssertionError('no simulate')), \
                patch.object(p, 'initial_state', side_effect=AssertionError('no initialize')):
            for index, (command, counter) in enumerate(zip(commands, counters, strict=True)):
                output = consumer.consume_negative_cycle_step(index, sample(p, index), state)
                self.assertEqual((output.projection.integer_command, output.next_state.angle_counter), (command, counter))
                self.assertEqual(output.trace.downstream.limiter_previous, state.previous_applied)
                self.assertEqual(step.call_count, index + 1)
                state = output.next_state
        self.assertEqual(state, p.LateralState(99, -16, -8, 4))

    def test_call89_90_91_92_suppression_preserves_nonzero_command(self):
        p, consumer, _ = self.modules()
        state = p.LateralState(88, -16, -12, 88)
        for index, counter, request in [(88, 89, True), (89, 90, False), (90, 0, False), (91, 1, True)]:
            output = consumer.consume_negative_cycle_step(index, sample(p, index), state)
            self.assertEqual((output.next_state.angle_counter, output.steer_request), (counter, request))
            self.assertEqual(output.trace.downstream.final_command, -12)
            self.assertEqual(output.projection.torque_float32.bits_hex, 'bf400000')
            state = output.next_state

    def test_negative_boundary_nonzero_inactive_reset_and_actual_final_zero_carry(self):
        p, consumer, _ = self.modules()
        state = p.LateralState(92, -16, -12, 1)
        for index, counter, final in [(92, 0, -12), (93, 1, -12), (94, 0, 0), (95, 1, -2)]:
            output = consumer.consume_negative_cycle_step(index, sample(p, index), state)
            self.assertEqual(output.trace.downstream.fault_condition, index != 92)
            self.assertEqual((output.next_state.angle_counter, output.next_state.previous_applied), (counter, final))
            if index == 94:
                self.assertEqual((state.angle_counter, state.previous_applied), (1, -12))
                self.assertEqual(output.trace.downstream.limited_command, -12)
            if index == 95:
                self.assertEqual((state.angle_counter, state.previous_applied), (0, 0))
            state = output.next_state

    def test_fractional_bound_kind_and_nearest_even_are_not_normalized_or_clamped(self):
        p, consumer, _ = self.modules()
        for index, state, value, final in [(0, p.LateralState(0, None, 0, 0), '-0x1.0000000000000p+1', -2),
                                           (5, p.LateralState(5, -16, -10, 5), '-0x1.7000000000000p+3', -12),
                                           (89, p.LateralState(89, -16, -12, 89), '-0x1.7000000000000p+3', -12)]:
            output = consumer.consume_negative_cycle_step(index, sample(p, index), state)
            trace = output.trace.downstream
            self.assertEqual((trace.driver_clip.lower.kind, trace.driver_clip.lower.value), ('python.float', '-0x1.7000000000000p+3'))
            self.assertEqual((trace.rate_clip.result.kind, trace.rate_clip.result.value), ('numpy.float64', value))
            self.assertEqual(output.projection.integer_command, final)

    def test_wrong_sign_state_settings_types_or_index_rejects_before_step(self):
        p, consumer, _ = self.modules()
        source = sample(p, 0)
        with patch.object(p, 'step', side_effect=AssertionError('must not step')):
            for changed in [replace(source, request=1.0), replace(source, angle_deg=85.0), replace(source, driver=-8.5),
                            replace(source, limits=replace(source.limits, STEER_MAX=409)), replace(source, provenance='ACTUAL')]:
                with self.assertRaisesRegex(ValueError, 'NEGATIVE_CYCLE_INPUT_MISMATCH'):
                    consumer.consume_negative_cycle_step(0, changed, p.LateralState(0, None, 0, 0))
            with self.assertRaisesRegex(ValueError, 'NEGATIVE_CYCLE_INPUT_MISMATCH'):
                consumer.consume_negative_cycle_step(95, sample(p, 95), p.LateralState(95, -16, -12, 1))
            for index in [True, -1, 99, '0']:
                with self.assertRaisesRegex(ValueError, 'NEGATIVE_CYCLE_INDEX'):
                    consumer.consume_negative_cycle_step(index, object(), object())
            with self.assertRaisesRegex(ValueError, 'CONSUMPTION_INPUT_TYPE'):
                consumer.consume_negative_cycle_step(0, object(), p.LateralState(0, None, 0, 0))

    def test_same_final_command_wrong_trace_or_request_is_rejected(self):
        p, consumer, _ = self.modules()
        state = p.LateralState(89, -16, -12, 89)
        output = consumer.consume_negative_cycle_step(89, sample(p, 89), state)
        downstream = output.trace.downstream
        wrong = replace(downstream, rate_clip=replace(downstream.rate_clip, result=replace(downstream.rate_clip.result, kind='numpy.int64', value=-12)))
        for changed in [replace(output, trace=replace(output.trace, downstream=wrong)), replace(output, steer_request=True)]:
            with patch.object(p, 'step', return_value=changed), self.assertRaisesRegex(ValueError, 'NEGATIVE_CYCLE_OUTPUT_MISMATCH'):
                consumer.consume_negative_cycle_step(89, sample(p, 89), state)

    def test_reference_identity_fresh_copy_and_assembly_do_not_run_model(self):
        p, _, reference = self.modules()
        with patch.object(p, 'step', side_effect=AssertionError('no reference computation')):
            expected = reference.expected_output(89)
            self.assertFalse(expected['steer_request'])
            self.assertEqual(expected['projection']['integer_command'], -12)
            expected['next_state']['angle_counter'] = 99
            self.assertEqual(reference.expected_output(89)['next_state']['angle_counter'], 90)
            with tempfile.TemporaryDirectory() as scratch:
                path = Path(scratch) / 'wrong.json'
                path.write_bytes(b'{}')
                with patch.object(reference, 'REFERENCE_PATH', path), self.assertRaisesRegex(ValueError, 'NEGATIVE_CYCLE_REFERENCE_IDENTITY'):
                    reference.expected_input(0)

    def test_version_and_model_failure_do_not_fallback_or_retry(self):
        p, consumer, _ = self.modules()
        state = p.LateralState(0, None, 0, 0)
        with patch.object(p, '__version__', 'wrong'), patch.object(p, 'step', side_effect=AssertionError('must not step')):
            with self.assertRaisesRegex(ValueError, 'CONSUMPTION_PACKAGE_VERSION'):
                consumer.consume_negative_cycle_step(0, sample(p, 0), state)
        with patch.object(p, 'step', side_effect=RuntimeError('model-failure')) as step:
            with self.assertRaisesRegex(RuntimeError, 'model-failure'):
                consumer.consume_negative_cycle_step(0, sample(p, 0), state)
            self.assertEqual(step.call_count, 1)


if __name__ == '__main__':
    unittest.main()
