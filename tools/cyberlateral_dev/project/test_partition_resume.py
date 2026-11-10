"""Catch batch-boundary history loss and output loss on fixed CORE35 chains."""

import itertools
import unittest

import test_driver_state_chain as chain35
from v1_helpers import package_feature


class PartitionResumeTests(unittest.TestCase):
    def integer(self, actual, expected):
        self.assertIs(type(actual), int)
        self.assertEqual(actual, expected)

    def scalar(self, actual, kind, value):
        self.assertIs(type(actual.kind), str)
        self.assertEqual(actual.kind, kind)
        self.integer(actual.value, value)

    def samples(self, p, rows):
        self.assertEqual(len(rows), 9)
        return tuple(p.LateralInput(i, row[0], row[1], 0.0, row[2],
                     p.Limits(16, row[3], row[4], 7, 1, 3), 'SYNTHETIC_ONLY')
                     for i, row in enumerate(rows))

    def prefix_state(self, state, rows, end):
        self.integer(state.index, end)
        self.integer(state.previous_requested, {1.0: 16, -1.0: -16}[rows[end - 1][0]])
        self.integer(state.previous_applied, rows[end - 1][13])
        self.integer(state.angle_counter, 0)

    def literal_outputs(self, outputs, rows):
        self.assertEqual(len(outputs), 9)
        for index, (output, row) in enumerate(zip(outputs, rows, strict=True)):
            trace = output.trace.downstream
            requested = {1.0: 16, -1.0: -16}[row[0]]  # Old literals,not model output.
            self.integer(output.trace.quantization.integer_command, requested)
            self.integer(trace.limiter_previous, row[6])
            self.scalar(trace.driver_clip.x, 'python.int', requested)
            self.scalar(trace.driver_clip.lower, 'python.int', row[7])
            self.scalar(trace.driver_clip.upper, 'python.int', row[8])
            self.scalar(trace.driver_clip.result, 'numpy.int64', row[9])
            self.scalar(trace.rate_clip.x, 'numpy.int64', row[9])
            self.scalar(trace.rate_clip.lower, 'python.int', row[10])
            self.scalar(trace.rate_clip.upper, 'python.int', row[11])
            self.scalar(trace.rate_clip.result, 'numpy.int64', row[12])
            self.integer(trace.limited_command, row[12])
            self.integer(trace.final_command, row[13])
            self.integer(output.projection.integer_command, row[13])
            self.prefix_state(output.next_state, rows, index + 1)
            self.assertIs(trace.fault_condition, False)
            self.assertIs(trace.steer_request, row[14])
            self.assertIs(output.steer_request, row[14])

    def test_all_contiguous_partitions_preserve_outputs_and_prefix_states(self):
        p = package_feature()
        expected_cuts = {cuts for count in range(9)
                         for cuts in itertools.combinations(range(1, 9), count)}
        self.assertEqual(len(expected_cuts), 256)
        for name, rows in (('positive', chain35.POSITIVE_ROWS), ('negative', chain35.NEGATIVE_ROWS)):
            samples = self.samples(p, rows)
            baseline = p.simulate(samples, p.initial_state())
            with self.subTest(chain=name, baseline=True):
                self.literal_outputs(baseline.outputs, rows)
                self.prefix_state(baseline.next_state, rows, 9)
            seen = set()
            for mask in range(256):
                cuts = tuple(i + 1 for i in range(8) if mask & (1 << i))
                seen.add(cuts)
                boundaries = (0, *cuts, 9)
                chunks = tuple(samples[a:b] for a, b in itertools.pairwise(boundaries))
                outputs, prefixes, state = [], [], p.initial_state()
                for chunk in chunks:
                    result = p.simulate(chunk, state)
                    outputs.extend(result.outputs)
                    state = result.next_state  # Actual returned object,never an expected seed.
                    prefixes.append((chunk[-1].index + 1, state))
                with self.subTest(chain=name, cut_mask=mask):
                    self.assertTrue(all(type(chunk) is tuple and chunk for chunk in chunks))
                    self.assertEqual(tuple(s for chunk in chunks for s in chunk), samples)
                    self.assertEqual(tuple(outputs), baseline.outputs)
                    self.assertEqual(state, baseline.next_state)
                    self.literal_outputs(outputs, rows)
                    for end, prefix in prefixes:
                        self.prefix_state(prefix, rows, end)
            self.assertEqual(seen, expected_cuts)

    def test_interleaved_singleton_batches_keep_independent_histories(self):
        p = package_feature()
        rows_by_name = {'positive': chain35.POSITIVE_ROWS, 'negative': chain35.NEGATIVE_ROWS}
        samples = {name: self.samples(p, rows) for name, rows in rows_by_name.items()}
        baselines = {name: p.simulate(values, p.initial_state()) for name, values in samples.items()}
        states = {name: p.initial_state() for name in samples}
        outputs = {name: [] for name in samples}
        prefixes = {name: [] for name in samples}
        for index in range(9):
            for name in samples:
                result = p.simulate((samples[name][index],), states[name])
                outputs[name].extend(result.outputs)
                states[name] = result.next_state
                prefixes[name].append(result.next_state)
        for name, rows in rows_by_name.items():
            with self.subTest(chain=name):
                self.literal_outputs(baselines[name].outputs, rows)
                self.assertEqual(tuple(outputs[name]), baselines[name].outputs)
                self.assertEqual(states[name], baselines[name].next_state)
                self.literal_outputs(outputs[name], rows)
                for end, prefix in enumerate(prefixes[name], start=1):
                    self.prefix_state(prefix, rows, end)
