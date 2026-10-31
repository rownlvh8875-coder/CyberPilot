"""Identical reduced coverage must not be published as a successful experiment."""

import copy
import importlib
import sys
import unittest

from v1_helpers import ROOT


def observations(mode):
    # Structural mutation fixtures from preregistered literals, NOT a numerical oracle test.
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    rows = []
    if mode == 'R22':
        reference = importlib.import_module('integration_tools.fixed_model_reference')
        for name in ['zero', 'rounded_request', 'signed_zero', 'resumed', 'smallest_subnormal']:
            rows.append({'id': name, 'accepted': True, 'model_steps': 1, 'model_expected_match': True,
                         'prepared': reference.expected_input(name), 'model_output': reference.expected_output(name)})
        for name in ['driver_precision_reject', 'angle_precision_reject', 'request_range_reject']:
            rows.append({'id': name, 'accepted': False, 'model_steps': 0, 'rejection_code': 'SEMANTIC_DOMAIN'})
        count = 5
    else:
        reference = importlib.import_module('integration_tools.sequence_reference')
        for index in range(4):
            rows.append({'index': index, 'accepted': True, 'model_steps': 1, 'model_expected_match': True,
                         'prepared': reference.expected_input(index), 'model_output': reference.expected_output(index)})
        count = 4
    return {'cases': rows, 'model_execution': count, 'F61_execution': 0, 'actual_activation': 'NOT_ALLOWED',
            'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL'}


class NativeCoverageTests(unittest.TestCase):
    def validator(self):
        self.assertTrue((ROOT / 'native_qualification/coverage.py').is_file(), 'Missing observation coverage gate')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('native_qualification.coverage').validate_coverage

    def test_valid_counts_derive_from_exact_coverage_without_model_import(self):
        validate = self.validator()
        before = set(sys.modules)
        self.assertEqual(validate(observations('R22'), 'R22'), 5)
        self.assertEqual(validate(observations('R23'), 'R23'), 4)
        self.assertFalse(any(n.split('.')[0] in {'cyberlateral_dev', 'capnp', 'numpy', 'openpilot'} for n in set(sys.modules) - before))

    def test_missing_duplicate_extra_and_reordered_sequence_rows_reject(self):
        validate = self.validator()
        for mode in ['R22', 'R23']:
            data = observations(mode)
            for rows in [data['cases'][:-1], data['cases'] + [data['cases'][0]], [data['cases'][0]] * len(data['cases'])]:
                with self.assertRaisesRegex(ValueError, 'OBSERVATION_COVERAGE'):
                    validate({**data, 'cases': rows}, mode)
        data = observations('R23')
        with self.assertRaisesRegex(ValueError, 'OBSERVATION_COVERAGE'):
            validate({**data, 'cases': list(reversed(data['cases']))}, 'R23')

    def test_boolean_negative_and_wrong_integer_counts_reject(self):
        validate = self.validator()
        for mode in ['R22', 'R23']:
            for path, value in [('model_execution', True), ('model_execution', 0), ('row_count', True),
                                ('row_count', -1), ('row_count', 0), ('accepted', 1), ('model_expected_match', False)]:
                data = observations(mode)
                if path == 'model_execution':
                    data[path] = value
                else:
                    data['cases'][0]['model_steps' if path == 'row_count' else path] = value
                with self.assertRaisesRegex(ValueError, 'OBSERVATION_COVERAGE'):
                    validate(data, mode)

    def test_rejected_r22_row_must_have_no_output_or_steps_and_exact_code(self):
        validate = self.validator()
        for key, value in [('model_steps', 1), ('model_steps', False), ('model_output', {}),
                            ('accepted', True), ('rejection_code', 'OTHER')]:
            data = observations('R22')
            data['cases'][-1][key] = value
            with self.assertRaisesRegex(ValueError, 'OBSERVATION_COVERAGE'):
                validate(data, 'R22')

    def test_wrong_prepared_state_or_output_and_false_gate_reject(self):
        validate = self.validator()
        for mode in ['R22', 'R23']:
            data = observations(mode)
            changed = copy.deepcopy(data)
            changed['cases'][1]['prepared']['state']['previous_applied'] = 99
            with self.assertRaisesRegex(ValueError, 'OBSERVATION_COVERAGE'):
                validate(changed, mode)
            changed = copy.deepcopy(data)
            changed['cases'][0]['model_output']['trace']['downstream']['limiter_previous'] = 99
            with self.assertRaisesRegex(ValueError, 'OBSERVATION_COVERAGE'):
                validate(changed, mode)
            for key, value in [('F61_execution', True), ('actual_activation', 'ALLOWED'), ('R_BUDGET', 'RESOLVED')]:
                with self.assertRaisesRegex(ValueError, 'OBSERVATION_COVERAGE'):
                    validate({**data, key: value}, mode)

    def test_wrong_shapes_and_unknown_mode_reject(self):
        validate = self.validator()
        for data, mode in [(None, 'R23'), ({}, 'R23'), ({'cases': {}}, 'R22'), ({}, 'OTHER')]:
            with self.assertRaisesRegex(ValueError, 'OBSERVATION_COVERAGE'):
                validate(data, mode)


if __name__ == '__main__':
    unittest.main()
