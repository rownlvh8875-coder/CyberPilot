"""R41 catches interacting arithmetic branches and state loss across long runs."""

import importlib
import json
import sys
import unittest

from test_regression_pack import assert_typed, row_projection
from v1_helpers import ROOT, package_feature

PACK = ROOT / 'examples/r41'
EXPECTED = ROOT / 'reference/r41_regression_expected_v1.json'


def expected_contract(test):
    test.assertTrue(EXPECTED.is_file(), 'Missing preregistered R41 independent expectations')
    return json.loads(EXPECTED.read_bytes())


def selected_rows(want):
    """Expand only independently hand-derived literal cycles, never model logic."""
    if 'rows' in want:
        return want['rows']
    return [[want['first_index'] + cycle * 8 + row[0], *row[1:]]
            for cycle in range(want['repetitions']) for row in want['cycle_rows']]


def assert_saved_case(test, filename, result):
    want = expected_contract(test)['cases'][filename]
    rows = row_projection(result)
    if 'fault_period' in want:
        # Independent closed-form fixture expectation: two complete91-call cycles,
        # not a call into the model, its helpers, or the selected-source worker.
        expected_rows = [[i, None if i == 0 else 4, 0 if i == 0 else 2 if i == 1 else 4,
                          i % 91, 4, 2 if i == 0 else 4, 2 if i == 0 else 4,
                          i not in [89, 90, 180, 181], (i + 1) % 91] for i in range(184)]
        assert_typed(test, rows, expected_rows)
    else:
        assert_typed(test, rows, selected_rows(want))
    assert_typed(test, result['final_state'], want['final_state'])
    test.assertEqual(result['model_steps'], want['sample_count'])


class BoundaryRegressionPackTests(unittest.TestCase):
    def evaluate(self, filename):
        expected_contract(self)
        self.assertTrue((PACK / filename).is_file(), 'Missing R41 fixture: ' + filename)
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        package_feature()
        source = importlib.import_module('integration_tools.scenario_input')
        engine = importlib.import_module('integration_tools.scenario_engine')
        result = engine.evaluate_scenario(source.read_scenario(PACK / filename))
        assert_saved_case(self, filename, result)
        return result

    def test_combined_fractional_sign_fault_and_inactive_rows(self):
        self.evaluate('combined_boundaries_v1.json')

    def test_combined_driver_rounding_and_rate_order_keep_fractional_bounds(self):
        result = self.evaluate('combined_boundaries_v1.json')
        outputs = [r['model_output'] for r in result['rows']]
        upper = outputs[0]['trace']['downstream']['driver_clip']['upper']
        assert_typed(self, upper, {'kind': 'python.float', 'value': '0x1.4000000000000p+1'})
        # -3.5 rounds to-4, but +3.5 is rate-limited to1 by the previous applied-4.
        assert_typed(self, [outputs[i]['trace']['downstream']['limited_command'] for i in [0, 3, 4]], [2, -4, 1])
        kinds = [outputs[i]['trace']['downstream']['driver_clip']['result']['kind'] for i in [9, 10]]
        self.assertEqual(kinds, ['numpy.float64', 'numpy.int64'])

    def test_combined_signed_zero_and_half_even_ties_survive_history(self):
        outputs = [r['model_output'] for r in self.evaluate('combined_boundaries_v1.json')['rows']]
        zero = outputs[7]['trace']['quantization']
        self.assertEqual([zero['request_hex'], zero['product_hex']], ['-0x0.0p+0', '-0x0.0p+0'])
        assert_typed(self, [outputs[i]['trace']['quantization']['integer_command'] for i in [1, 7, 8, 11]], [2, 0, -2, 0])

    def test_combined_fault_suppression_does_not_apply_inactive_zeroing(self):
        outputs = [r['model_output'] for r in self.evaluate('combined_boundaries_v1.json')['rows']]
        assert_typed(self, [[outputs[i]['steer_request'], outputs[i]['projection']['integer_command']] for i in [1, 2, 5]],
                     [[False, 2], [False, -2], [False, 0]])

    def test_repeated_crossing_keeps_applied_history_through_all16_cycles(self):
        self.evaluate('repeated_inactive_crossing_v1.json')

    def test_repeated_inactive_clears_counter_and_applied_not_previous_request(self):
        rows = row_projection(self.evaluate('repeated_inactive_crossing_v1.json'))
        for start in range(0, 128, 8):
            assert_typed(self, [rows[start + 3][5:], rows[start + 4][1:4], rows[start + 5][5:]],
                         [[3, 0, False, 0], [16, 0, 0], [-4, 0, False, 0]])

    def test_long_high_angle_crosses_two_fault_cycles_without_torque_zeroing(self):
        self.evaluate('long_fault_cycles_v1.json')

    def test_long_fault_counter_resets_at_both91_call_boundaries(self):
        rows = row_projection(self.evaluate('long_fault_cycles_v1.json'))
        for i in [90, 181]:
            assert_typed(self, rows[i][3:], [90, 4, 4, 4, False, 0])
            assert_typed(self, rows[i + 1][3:], [0, 4, 4, 4, True, 1])
