"""Literal negative-angle/driver results, float-kind traces and closed input gate."""

import importlib
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


def sample(p, index):
    return p.LateralInput(index, 1.0 if index < 6 or index == 19 else -1.0,
                          -8.5 if index < 6 else 8.5 if index < 18 else 16.0 if index == 18 else -16.0,
                          -84.5 if index == 14 else -85.0, index != 16,
                          p.Limits(16, 2, 5, 7, 1, 3), 'SYNTHETIC_ONLY')


class DriverConsumptionTests(unittest.TestCase):
    def modules(self):
        self.assertTrue((ROOT / 'integration_tools/driver_consumption.py').is_file(), 'Missing fixed driver consumer')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return package_feature(), importlib.import_module('integration_tools.driver_consumption'), importlib.import_module('integration_tools.driver_reference')

    def test_complete20_step_literal_outputs_and_state_carry_one_call_per_step(self):
        p, consumer, _ = self.modules()
        state = p.LateralState(0, None, 0, 0)
        commands = [2, 4, 6, 8, 10, 12, 7, 2, -2, -4, -6, -8, -10, -12, -12, -12, 0, -2, 0, 0]
        counters = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 0, 1, 0, 1, 2, 3]
        with patch.object(p, 'step', wraps=p.step) as step, patch.object(p, 'simulate', side_effect=AssertionError('no simulate')), \
                patch.object(p, 'initial_state', side_effect=AssertionError('no initialize')):
            for index, (command, counter) in enumerate(zip(commands, counters, strict=True)):
                output = consumer.consume_driver_step(index, sample(p, index), state)
                self.assertEqual((output.projection.integer_command, output.next_state.angle_counter), (command, counter))
                self.assertEqual(output.trace.downstream.limiter_previous, state.previous_applied)
                self.assertEqual(step.call_count, index + 1)
                state = output.next_state
        self.assertEqual(state, p.LateralState(20, 16, 0, 3))

    def test_fractional_limits_and_nearest_even_are_not_clamped_or_integerized(self):
        p, consumer, _ = self.modules()
        for index, state, bound, final in [(5, p.LateralState(5, 16, 10, 5), '0x1.7000000000000p+3', 12),
                                           (13, p.LateralState(13, -16, -10, 13), '-0x1.7000000000000p+3', -12)]:
            output = consumer.consume_driver_step(index, sample(p, index), state)
            driver = output.trace.downstream.driver_clip
            scalar_bound = driver.upper if index == 5 else driver.lower
            self.assertEqual((scalar_bound.kind, scalar_bound.value), ('python.float', bound))
            self.assertEqual((driver.result.kind, driver.result.value), ('numpy.float64', bound))
            self.assertEqual((output.trace.downstream.rate_clip.result.kind, output.trace.downstream.rate_clip.result.value), ('numpy.float64', bound))
            self.assertEqual(output.projection.integer_command, final)

    def test_negative85_inclusive_below_boundary_and_nonzero_inactive_reset(self):
        p, consumer, _ = self.modules()
        state = p.LateralState(14, -16, -12, 14)
        for index, expected in [(14, (0, -12)), (15, (1, -12)), (16, (0, 0)), (17, (1, -2))]:
            output = consumer.consume_driver_step(index, sample(p, index), state)
            self.assertEqual((output.next_state.angle_counter, output.next_state.previous_applied), expected)
            self.assertEqual(output.trace.downstream.fault_condition, index != 14)
            if index == 16:
                self.assertEqual(state.angle_counter, 1)
                self.assertEqual(output.trace.downstream.limited_command, -12)
            state = output.next_state

    def test_driver_zero_clamp_branches_return_integer_kind_traces(self):
        p, consumer, _ = self.modules()
        for index, state, bounds in [(18, p.LateralState(18, -16, -2, 1), (0, 16)), (19, p.LateralState(19, -16, 0, 2), (-16, 0))]:
            output = consumer.consume_driver_step(index, sample(p, index), state)
            clip = output.trace.downstream.driver_clip
            self.assertEqual((clip.lower.value, clip.upper.value), bounds)
            self.assertEqual((clip.result.kind, clip.result.value), ('numpy.int64', 0))
            self.assertEqual(output.trace.downstream.rate_clip.result.kind, 'numpy.int64')

    def test_changed_driver_sign_state_settings_or_type_rejects_before_step(self):
        p, consumer, _ = self.modules()
        source = sample(p, 0)
        with patch.object(p, 'step', side_effect=AssertionError('must not step')):
            for changed in [replace(source, driver=8.5), replace(source, angle_deg=85.0), replace(source, request=-1.0),
                            replace(source, limits=replace(source.limits, STEER_MAX=409)), replace(source, provenance='ACTUAL')]:
                with self.assertRaisesRegex(ValueError, 'DRIVER_INPUT_MISMATCH'):
                    consumer.consume_driver_step(0, changed, p.LateralState(0, None, 0, 0))
            with self.assertRaisesRegex(ValueError, 'DRIVER_INPUT_MISMATCH'):
                consumer.consume_driver_step(17, sample(p, 17), p.LateralState(17, -16, -12, 1))
            for index in [True, -1, 20, '0']:
                with self.assertRaisesRegex(ValueError, 'DRIVER_INDEX'):
                    consumer.consume_driver_step(index, object(), object())
            with self.assertRaisesRegex(ValueError, 'CONSUMPTION_INPUT_TYPE'):
                consumer.consume_driver_step(0, object(), p.LateralState(0, None, 0, 0))

    def test_same_command_with_wrong_float_trace_kind_is_rejected(self):
        p, consumer, _ = self.modules()
        state = p.LateralState(0, None, 0, 0)
        output = consumer.consume_driver_step(0, sample(p, 0), state)
        trace = output.trace.downstream
        wrong = replace(trace, rate_clip=replace(trace.rate_clip, result=replace(trace.rate_clip.result, kind='numpy.int64', value=2)))
        changed = replace(output, trace=replace(output.trace, downstream=wrong))
        with patch.object(p, 'step', return_value=changed), self.assertRaisesRegex(ValueError, 'DRIVER_OUTPUT_MISMATCH'):
            consumer.consume_driver_step(0, sample(p, 0), state)

    def test_literal_assembly_hash_and_fresh_copy_do_not_execute_model(self):
        p, _, reference = self.modules()
        with patch.object(p, 'step', side_effect=AssertionError('reference model execution')):
            expected = reference.expected_output(5)
            self.assertEqual(expected['projection']['integer_command'], 12)
            self.assertEqual(expected['trace']['downstream']['rate_clip']['result'], {'kind': 'numpy.float64', 'value': '0x1.7000000000000p+3'})
            expected['next_state']['previous_applied'] = 99
            self.assertEqual(reference.expected_output(5)['next_state']['previous_applied'], 12)
            with tempfile.TemporaryDirectory() as scratch:
                path = Path(scratch) / 'wrong.json'
                path.write_bytes(b'{}')
                with patch.object(reference, 'REFERENCE_PATH', path), self.assertRaisesRegex(ValueError, 'DRIVER_REFERENCE_IDENTITY'):
                    reference.expected_input(0)

    def test_version_guard_and_no_retry_after_model_error(self):
        p, consumer, _ = self.modules()
        state = p.LateralState(0, None, 0, 0)
        with patch.object(p, '__version__', 'wrong'), patch.object(p, 'step', side_effect=AssertionError('must not step')):
            with self.assertRaisesRegex(ValueError, 'CONSUMPTION_PACKAGE_VERSION'):
                consumer.consume_driver_step(0, sample(p, 0), state)
        with patch.object(p, 'step', side_effect=RuntimeError('failed-model')) as step:
            with self.assertRaisesRegex(RuntimeError, 'failed-model'):
                consumer.consume_driver_step(0, sample(p, 0), state)
            self.assertEqual(step.call_count, 1)


if __name__ == '__main__':
    unittest.main()
