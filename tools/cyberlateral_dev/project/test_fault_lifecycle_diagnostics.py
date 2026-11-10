"""Failure diagnostics identify a bad synthetic record without changing the model."""

import unittest
from dataclasses import replace

import test_fault_lifecycle as lifecycle
from v1_helpers import package_feature


class FaultLifecycleDiagnosticTests(unittest.TestCase):
    def result(self):
        p = package_feature()
        helper = lifecycle.FaultLifecycleTests()
        case = lifecycle.fixed_cases()['positive']
        result = p.simulate(helper.samples(p, case), p.initial_state())
        return helper, case, result

    def test_selected_failure_names_sample_and_field(self):
        helper, case, result = self.result()
        outputs = list(result.outputs)
        bad_trace = replace(outputs[89].trace.downstream, fault_condition=False)
        outputs[89] = replace(outputs[89], trace=replace(outputs[89].trace, downstream=bad_trace))
        with self.assertRaisesRegex(AssertionError, r'sample_index=89 field=trace\.fault_condition'):
            helper.selected_expectations(tuple(outputs), case)

    def test_prefix_failure_names_sample_endpoint_and_field(self):
        helper, case, result = self.result()
        bad_state = replace(result.next_state, angle_counter=3)
        with self.assertRaisesRegex(AssertionError, r'sample_index=99 prefix_end=100 field=state\.angle_counter'):
            helper.prefix_state(bad_state, case, 100)
