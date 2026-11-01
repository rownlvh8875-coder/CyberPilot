"""Independent boundary literals and fail-before-step faults; no arbitrary inputs."""

import importlib
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


def sample(p, index):
    return p.LateralInput(index, 0.25, 0.0, 84.5 if index in (92, 95) else 85.0,
                          index not in (93, 97), p.Limits(16, 2, 5, 7, 1, 3), 'SYNTHETIC_ONLY')


class FaultConsumptionTests(unittest.TestCase):
    def modules(self):
        self.assertTrue((ROOT / 'integration_tools/fault_consumption.py').is_file(), 'Missing fixed fault consumer')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return package_feature(), importlib.import_module('integration_tools.fault_consumption'), importlib.import_module('integration_tools.fault_reference')

    def test_nonzero_counter_is_reset_by_carried_inactive_call(self):
        p, consumer, reference = self.modules()
        self.assertEqual(len(reference.load_reference()['steps']), 99, 'Missing preregistered99-step extension')
        state = p.LateralState(96, 4, 4, 0)
        active = consumer.consume_fault_step(96, sample(p, 96), state)
        self.assertEqual(active.next_state, p.LateralState(97, 4, 4, 1))
        inactive = consumer.consume_fault_step(97, sample(p, 97), active.next_state)
        self.assertEqual(inactive.next_state, p.LateralState(98, 4, 0, 0))
        self.assertFalse(inactive.steer_request)
        reactivated = consumer.consume_fault_step(98, sample(p, 98), inactive.next_state)
        self.assertEqual(reactivated.next_state, p.LateralState(99, 4, 2, 1))
        self.assertTrue(reactivated.steer_request)

    def test_continuous_99_steps_hit_literal_boundaries_without_extra_initialization(self):
        p, consumer, _ = self.modules()
        state = p.LateralState(0, None, 0, 0)
        boundaries = {0: (1, True, 2), 1: (2, True, 4), 88: (89, True, 4), 89: (90, False, 4),
                      90: (0, False, 4), 91: (1, True, 4), 92: (0, True, 4), 93: (0, False, 0),
                      94: (1, True, 2), 95: (0, True, 4), 96: (1, True, 4), 97: (0, False, 0), 98: (1, True, 2)}
        with patch.object(p, 'step', wraps=p.step) as step, patch.object(p, 'simulate', side_effect=AssertionError('no simulation')), \
                patch.object(p, 'initial_state', side_effect=AssertionError('no initialization')):
            for index in range(99):
                output = consumer.consume_fault_step(index, sample(p, index), state)
                if index in boundaries:
                    self.assertEqual((output.next_state.angle_counter, output.steer_request, output.projection.integer_command), boundaries[index])
                self.assertEqual(output.trace.downstream.limiter_previous, state.previous_applied)
                self.assertEqual(step.call_count, index + 1)
                state = output.next_state
        self.assertEqual(state, p.LateralState(99, 4, 2, 1))

    def test_suppressed_request_does_not_invent_command_zeroing(self):
        p, consumer, _ = self.modules()
        for index, counter, next_counter, request in [(89, 89, 90, False), (90, 90, 0, False), (91, 0, 1, True)]:
            output = consumer.consume_fault_step(index, sample(p, index), p.LateralState(index, 4, 4, counter))
            self.assertEqual((output.steer_request, output.projection.integer_command, output.next_state.angle_counter), (request, 4, next_counter))
            self.assertTrue(output.trace.downstream.fault_condition)

    def test_below_threshold_and_inactive_reset_then_prior_final_zero_reactivation(self):
        p, consumer, _ = self.modules()
        for index, state, condition, limited, final, counter in [
                (92, p.LateralState(92, 4, 4, 1), False, 4, 4, 0),
                (93, p.LateralState(93, 4, 4, 0), True, 4, 0, 0),
                (94, p.LateralState(94, 4, 0, 0), True, 2, 2, 1),
                (95, p.LateralState(95, 4, 2, 1), False, 4, 4, 0)]:
            output = consumer.consume_fault_step(index, sample(p, index), state)
            trace = output.trace.downstream
            self.assertEqual((trace.fault_condition, trace.limited_command, trace.final_command), (condition, limited, final))
            self.assertEqual(output.next_state.angle_counter, counter)
        reactivated = consumer.consume_fault_step(94, sample(p, 94), p.LateralState(94, 4, 0, 0))
        self.assertEqual((reactivated.trace.downstream.rate_clip.lower.value, reactivated.trace.downstream.rate_clip.upper.value), (-2, 2))

    def test_wrong_counter_prior_state_and_index_reject_before_step(self):
        p, consumer, _ = self.modules()
        with patch.object(p, 'step', side_effect=AssertionError('must not step')):
            for index, state in [(89, p.LateralState(89, 4, 4, 88)), (90, p.LateralState(90, 4, 4, 89)),
                                  (91, p.LateralState(91, 4, 4, 90)), (94, p.LateralState(94, 4, 4, 0))]:
                with self.assertRaisesRegex(ValueError, 'FAULT_INPUT_MISMATCH'):
                    consumer.consume_fault_step(index, sample(p, index), state)
            for index in [True, -1, 99, '0']:
                with self.assertRaisesRegex(ValueError, 'FAULT_INDEX'):
                    consumer.consume_fault_step(index, object(), object())

    def test_changed_angle_settings_zero_sign_and_type_reject_before_step(self):
        p, consumer, _ = self.modules()
        original, state = sample(p, 0), p.LateralState(0, None, 0, 0)
        with patch.object(p, 'step', side_effect=AssertionError('must not step')):
            for changed in [replace(original, angle_deg=84.5), replace(original, driver=-0.0), replace(original, lat_active=False),
                            replace(original, provenance='ACTUAL'), replace(original, limits=replace(original.limits, STEER_MAX=409))]:
                with self.assertRaisesRegex(ValueError, 'FAULT_INPUT_MISMATCH'):
                    consumer.consume_fault_step(0, changed, state)
            with self.assertRaisesRegex(ValueError, 'CONSUMPTION_INPUT_TYPE'):
                consumer.consume_fault_step(0, object(), state)

    def test_reference_hash_copy_isolation_and_no_model_derived_expectations(self):
        p, _, reference = self.modules()
        with patch.object(p, 'step', side_effect=AssertionError('reference must not run model')):
            expected = reference.expected_output(90)
            self.assertEqual(expected['next_state'], {'index': 91, 'previous_requested': 4, 'previous_applied': 4, 'angle_counter': 0})
            self.assertFalse(expected['steer_request'])
            expected['next_state']['angle_counter'] = 99
            self.assertEqual(reference.expected_output(90)['next_state']['angle_counter'], 0)
            with tempfile.TemporaryDirectory() as scratch:
                wrong = Path(scratch) / 'wrong.json'
                wrong.write_bytes(b'{}')
                with patch.object(reference, 'REFERENCE_PATH', wrong), self.assertRaisesRegex(ValueError, 'FAULT_REFERENCE_IDENTITY'):
                    reference.expected_input(0)

    def test_full_flag_or_counter_mutation_with_same_command_rejects(self):
        p, consumer, _ = self.modules()
        state = p.LateralState(89, 4, 4, 89)
        output = consumer.consume_fault_step(89, sample(p, 89), state)
        for changed in [replace(output, steer_request=True), replace(output, next_state=replace(output.next_state, angle_counter=89)),
                        replace(output, trace=replace(output.trace, downstream=replace(output.trace.downstream, fault_condition=False)))]:
            with patch.object(p, 'step', return_value=changed), self.assertRaisesRegex(ValueError, 'FAULT_OUTPUT_MISMATCH'):
                consumer.consume_fault_step(89, sample(p, 89), state)

    def test_version_and_failed_model_have_no_fallback_or_retry(self):
        p, consumer, _ = self.modules()
        state = p.LateralState(0, None, 0, 0)
        with patch.object(p, '__version__', 'wrong'), patch.object(p, 'step', side_effect=AssertionError('must not step')):
            with self.assertRaisesRegex(ValueError, 'CONSUMPTION_PACKAGE_VERSION'):
                consumer.consume_fault_step(0, sample(p, 0), state)
        with patch.object(p, 'step', side_effect=RuntimeError('failed-model')) as step:
            with self.assertRaisesRegex(RuntimeError, 'failed-model'):
                consumer.consume_fault_step(0, sample(p, 0), state)
            self.assertEqual(step.call_count, 1)


if __name__ == '__main__':
    unittest.main()
