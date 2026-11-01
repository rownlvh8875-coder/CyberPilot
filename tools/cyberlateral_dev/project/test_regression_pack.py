"""R35 hand-derived literals over unchanged parsing, model and rejection paths."""

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT, package_feature

PACK = ROOT / 'examples/r35'
EXPECTED = ROOT / 'reference/r35_regression_expected_v1.json'


def reference(test):
    test.assertTrue(EXPECTED.is_file(), 'Missing preregistered R35 literal reference')
    return json.loads(EXPECTED.read_bytes())


def row_projection(result):
    rows = []
    for row in result['rows']:
        state, output = row['prepared']['state'], row['model_output']
        rows.append([row['prepared']['sample']['index'], state['previous_requested'],
                     state['previous_applied'], state['angle_counter'],
                     output['trace']['quantization']['integer_command'],
                     output['trace']['downstream']['limited_command'],
                     output['projection']['integer_command'], output['steer_request'],
                     output['next_state']['angle_counter']])
    return rows


def assert_typed(test, actual, expected):
    # Unlike Python equality, JSON distinguishes bool/int and int/float.
    test.assertEqual(json.dumps(actual, sort_keys=True, allow_nan=False),
                     json.dumps(expected, sort_keys=True, allow_nan=False))


def assert_case(test, filename, result):
    want = reference(test)['cases'][filename]
    assert_typed(test, row_projection(result), want['rows'])
    assert_typed(test, result['final_state'], want['final_state'])
    test.assertEqual(result['model_steps'], len(want['rows']))
    outputs = [row['model_output'] for row in result['rows']]
    if 'rate_bounds' in want:
        actual = [[out['trace']['downstream']['rate_clip'][side]['value'] for side in ['lower', 'upper']] for out in outputs]
        assert_typed(test, actual, want['rate_bounds'])
    if 'driver_bounds' in want:
        actual = []
        for out in outputs:
            clip = out['trace']['downstream']['driver_clip']
            actual.append([clip['lower']['kind'], clip['lower']['value'], clip['upper']['kind'], clip['upper']['value']])
        assert_typed(test, actual, want['driver_bounds'])
        assert_typed(test, [out['trace']['downstream']['driver_clip']['result']['kind'] for out in outputs], want['driver_result_kinds'])
    if 'quantization_hex' in want:
        actual = [[out['trace']['quantization'][key] for key in ['request_hex', 'product_hex']] for out in outputs]
        assert_typed(test, actual, want['quantization_hex'])


class RegressionPackTests(unittest.TestCase):
    def evaluate(self, filename):
        reference(self)
        self.assertTrue((PACK / filename).is_file(), 'Missing R35 fixture: ' + filename)
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        package_feature()
        source = importlib.import_module('integration_tools.scenario_input')
        engine = importlib.import_module('integration_tools.scenario_engine')
        result = engine.evaluate_scenario(source.read_scenario(PACK / filename))
        assert_case(self, filename, result)
        return result

    def test_positive_crossing_uses_previous_applied_and_asymmetric_down(self):
        self.evaluate('positive_crossing_v1.json')

    def test_negative_crossing_keeps_nonpositive_branch_and_up_bound(self):
        self.evaluate('negative_crossing_v1.json')

    def test_inactive_clears_applied_and_counter_but_retains_request(self):
        self.evaluate('inactive_resume_v1.json')

    def test_counter89_90_91_negative_threshold_and_below85_reset(self):
        result = self.evaluate('angle_counter_v1.json')
        last = result['rows'][-1]
        assert_typed(self, [last['prepared']['state']['angle_counter'],
                           last['model_output']['next_state']['angle_counter'],
                           last['model_output']['trace']['downstream']['fault_condition']], [1, 0, False])

    def test_fractional_driver_bounds_and_positive_negative_nearest_even(self):
        self.evaluate('fractional_driver_v1.json')

    def test_quantization_ties_binary64_decimal_and_signed_zero(self):
        self.evaluate('quantization_ties_v1.json')

    def reject_before_model(self, filename):
        want = reference(self)['cases'][filename]
        self.assertTrue((PACK / filename).is_file(), 'Missing R35 rejection fixture')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        run = importlib.import_module('integration_tools.scenario_run')
        source = importlib.import_module('integration_tools.scenario_input')
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'must-not-exist'
            with patch.object(run, 'load_model', side_effect=AssertionError('MODEL_LOADED_FOR_REJECTED_INPUT')):
                with self.assertRaises(source.ScenarioError) as caught:
                    run.run_scenario(PACK / filename, output)
            self.assertEqual(caught.exception.code, want['rejection_code'])
            self.assertFalse(output.exists())

    def test_late_integer_request_rejected_before_any_prefix_model_work(self):
        self.reject_before_model('invalid_late_request_v1.json')

    def test_nonadjacent_index_rejected_before_any_prefix_model_work(self):
        self.reject_before_model('invalid_order_v1.json')

    def test_extra_rate_policy_rejected_without_zero_fallback(self):
        self.reject_before_model('invalid_policy_v1.json')
