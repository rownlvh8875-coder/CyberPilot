"""Catch counter loss, wrong fault gating and reset ordering on fixed public chains."""

import itertools
import unittest

from v1_helpers import package_feature

# Manually declared finite progressions,not model/quantizer/oracle output.
POSITIVE_RAMP = (2, 4, 6, 8, 10, 12, 14) + (16,) * 81
NEGATIVE_RAMP = (-2, -4, -6, -8, -10, -12, -14) + (-16,) * 81
COUNTERS = tuple(range(1, 89)) + (89, 90, 0, 1, 0, 1, 0, 1, 2, 0, 1, 2)
FLAGS = (True,) * 88 + (True, False, False, True, False, True, True, True, True, False, True, True)
CONDITIONS = (True,) * 94 + (False,) + (True,) * 5
# request,driver,angle,active,UP,DOWN for calls88..99.
POSITIVE_TAIL = (
    (1.0, 0.0, 85.0, True, 2, 5), (1.0, 0.0, 85.0, True, 2, 5),
    (1.0, 0.0, 85.0, True, 2, 5), (1.0, 0.0, 85.0, True, 2, 5),
    (1.0, 0.0, 85.0, False, 2, 5), (1.0, 0.0, -85.0, True, 2, 5),
    (1.0, 0.0, -84.99609375, True, 2, 5), (1.0, 0.0, 85.0, True, 2, 5),
    (1.0, -12.5, 85.0, True, 2, 5), (1.0, 0.0, 85.0, False, 2, 5),
    (1.0, 0.0, 85.0, True, 0, 0), (-1.0, 0.0, 85.0, True, 2, 5),
)
NEGATIVE_TAIL = (
    (-1.0, 0.0, -85.0, True, 2, 5), (-1.0, 0.0, -85.0, True, 2, 5),
    (-1.0, 0.0, -85.0, True, 2, 5), (-1.0, 0.0, -85.0, True, 2, 5),
    (-1.0, 0.0, -85.0, False, 2, 5), (-1.0, 0.0, 85.0, True, 2, 5),
    (-1.0, 0.0, 84.99609375, True, 2, 5), (-1.0, 0.0, -85.0, True, 2, 5),
    (-1.0, 12.5, -85.0, True, 2, 5), (-1.0, 0.0, -85.0, False, 2, 5),
    (-1.0, 0.0, -85.0, True, 0, 0), (1.0, 0.0, -85.0, True, 2, 5),
)
POSITIVE_LIMITED = POSITIVE_RAMP + (16, 16, 16, 16, 16, 2, 4, 6, 1, 3, 0, -2)
POSITIVE_FINAL = POSITIVE_RAMP + (16, 16, 16, 16, 0, 2, 4, 6, 1, 0, 0, -2)
NEGATIVE_LIMITED = NEGATIVE_RAMP + (-16, -16, -16, -16, -16, -2, -4, -6, -1, -3, 0, 2)
NEGATIVE_FINAL = NEGATIVE_RAMP + (-16, -16, -16, -16, 0, -2, -4, -6, -1, 0, 0, 2)
SINGLE_CUTS = (1, 7, 8, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99)
CRITICAL_CUTS = (7, 88, 89, 90, 91, 92, 93, 94, 96, 97, 98, 99)


def fixed_cases():
    return {
        'positive': {'inputs': ((1.0, 0.0, 85.0, True, 2, 5),) * 88 + POSITIVE_TAIL,
                     'limited': POSITIVE_LIMITED, 'final': POSITIVE_FINAL, 'commands': (16,) * 99 + (-16,)},
        'negative': {'inputs': ((-1.0, 0.0, -85.0, True, 2, 5),) * 88 + NEGATIVE_TAIL,
                     'limited': NEGATIVE_LIMITED, 'final': NEGATIVE_FINAL, 'commands': (-16,) * 99 + (16,)},
    }


class FaultLifecycleTests(unittest.TestCase):
    def integer(self, actual, expected, context=None):
        self.assertIs(type(actual), int, msg=context)
        self.assertEqual(actual, expected, msg=context)

    def samples(self, p, case):
        self.assertTrue(all(len(case[k]) == 100 for k in ('inputs', 'limited', 'final', 'commands')))
        self.assertEqual((len(COUNTERS), len(FLAGS), len(CONDITIONS)), (100, 100, 100))
        return tuple(p.LateralInput(i, request, driver, angle, active,
                     p.Limits(16, up, down, 7, 1, 3), 'SYNTHETIC_ONLY')
                     for i, (request, driver, angle, active, up, down) in enumerate(case['inputs']))

    def prefix_state(self, state, case, end):
        location = f'sample_index={end - 1} prefix_end={end}'
        self.integer(state.index, end, f'{location} field=state.index')
        self.integer(state.previous_requested, case['commands'][end - 1], f'{location} field=state.previous_requested')
        self.integer(state.previous_applied, case['final'][end - 1], f'{location} field=state.previous_applied')
        self.integer(state.angle_counter, COUNTERS[end - 1], f'{location} field=state.angle_counter')

    def selected_expectations(self, outputs, case):
        self.assertEqual(len(outputs), 100, msg='field=outputs.length')
        previous = (0,) + case['final'][:-1]
        for i, output in enumerate(outputs):
            trace = output.trace.downstream
            location = f'sample_index={i}'
            self.integer(output.trace.quantization.integer_command, case['commands'][i], f'{location} field=trace.quantization.integer_command')
            self.integer(trace.limiter_previous, previous[i], f'{location} field=trace.limiter_previous')
            self.integer(trace.limited_command, case['limited'][i], f'{location} field=trace.limited_command')
            self.integer(trace.final_command, case['final'][i], f'{location} field=trace.final_command')
            self.integer(output.projection.integer_command, case['final'][i], f'{location} field=projection.integer_command')
            self.assertIs(trace.fault_condition, CONDITIONS[i], msg=f'{location} field=trace.fault_condition')
            self.assertIs(trace.steer_request, FLAGS[i], msg=f'{location} field=trace.steer_request')
            self.assertIs(output.steer_request, FLAGS[i], msg=f'{location} field=steer_request')
            self.prefix_state(output.next_state, case, i + 1)

    def test_critical_batch_splits_preserve_canonical_fault_counter_lifecycle(self):
        p = package_feature()
        schedules = tuple((cut,) for cut in SINGLE_CUTS) + (CRITICAL_CUTS, tuple(range(1, 100)))
        self.assertEqual(len(set(schedules)), 18)
        for name, case in fixed_cases().items():
            samples = self.samples(p, case)
            baseline = p.simulate(samples, p.initial_state())
            with self.subTest(chain=name, baseline=True):
                self.selected_expectations(baseline.outputs, case)
                self.prefix_state(baseline.next_state, case, 100)
            for cuts in schedules:
                chunks = tuple(samples[a:b] for a, b in itertools.pairwise((0, *cuts, 100)))
                state, outputs, prefixes = p.initial_state(), [], []
                for chunk in chunks:
                    result = p.simulate(chunk, state)
                    outputs.extend(result.outputs)
                    state = result.next_state
                    prefixes.append((chunk[-1].index + 1, state))
                with self.subTest(chain=name, cuts=cuts):
                    self.assertTrue(all(type(chunk) is tuple and chunk for chunk in chunks))
                    self.assertEqual(tuple(s for chunk in chunks for s in chunk), samples)
                    self.assertEqual(tuple(outputs), baseline.outputs)
                    self.assertEqual(state, baseline.next_state)
                    self.selected_expectations(outputs, case)
                    for end, prefix in prefixes:
                        self.prefix_state(prefix, case, end)

    def test_interleaved_fault_lifecycles_keep_signed_histories_and_counters(self):
        p = package_feature(); cases = fixed_cases()
        samples = {name: self.samples(p, case) for name, case in cases.items()}
        baselines = {name: p.simulate(values, p.initial_state()) for name, values in samples.items()}
        states = {name: p.initial_state() for name in cases}
        outputs = {name: [] for name in cases}; prefixes = {name: [] for name in cases}
        for i in range(100):
            for name in cases:
                result = p.simulate((samples[name][i],), states[name])
                outputs[name].extend(result.outputs)
                states[name] = result.next_state  # Actual returned state,not expected history.
                prefixes[name].append(result.next_state)
        for name, case in cases.items():
            with self.subTest(chain=name):
                self.selected_expectations(baselines[name].outputs, case)
                self.assertEqual(tuple(outputs[name]), baselines[name].outputs)
                self.assertEqual(states[name], baselines[name].next_state)
                self.selected_expectations(outputs[name], case)
                for end, state in enumerate(prefixes[name], start=1):
                    self.prefix_state(state, case, end)
