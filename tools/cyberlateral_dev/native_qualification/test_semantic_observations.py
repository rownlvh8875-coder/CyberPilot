"""Independent literal expectations on the closed actual-native R21 output."""

import json
import unittest
from pathlib import Path


class SemanticObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(Path('OBSERVATIONS.json').read_bytes())

    def rows(self):
        return {row['id']: row for row in self.data['cases']}

    def test_eight_cases_five_accepted_three_rejected(self):
        rows = self.rows()
        self.assertEqual(set(rows), {'zero', 'rounded_request', 'signed_zero', 'resumed', 'driver_precision_reject',
                                     'angle_precision_reject', 'request_range_reject', 'smallest_subnormal'})
        self.assertEqual(sum(row['accepted'] for row in rows.values()), 5)

    def test_literal_scalar_and_six_limit_mapping(self):
        result = self.rows()['rounded_request']['prepared']
        self.assertEqual(result['sample'], {'index': 0, 'request_hex': '0x1.3333340000000p-2', 'driver_hex': '0x1.8000000000000p+0',
                                          'angle_hex': '-0x1.d000000000000p+2', 'lat_active': True,
                                          'limits': [16, 2, 5, 7, 1, 3], 'provenance': 'SYNTHETIC_ONLY'})

    def test_signed_zero_and_smallest_subnormal_preserved(self):
        zero = self.rows()['signed_zero']['prepared']['sample']
        self.assertEqual([zero[n] for n in ['request_hex', 'driver_hex', 'angle_hex']], ['-0x0.0p+0'] * 3)
        self.assertEqual(self.rows()['smallest_subnormal']['prepared']['sample']['request_hex'], '0x1.0000000000000p-149')

    def test_resumed_source_state_is_explicit_not_inferred(self):
        self.assertEqual(self.rows()['resumed']['prepared']['state'], {'index': 1, 'previous_requested': 5, 'previous_applied': 3, 'angle_counter': 1})

    def test_native_domain_rejections_and_exact_oracle_agreement(self):
        for name in ['driver_precision_reject', 'angle_precision_reject', 'request_range_reject']:
            row = self.rows()[name]
            self.assertFalse(row['accepted'])
            self.assertEqual((row['rejection_code'], row['oracle_rejection_code']), ('SEMANTIC_DOMAIN', 'SEMANTIC_DOMAIN'))
        self.assertTrue(all(row['oracle_parity'] for row in self.data['cases']))

    def test_no_model_f61_actual_input_or_custody_promotion(self):
        self.assertEqual(self.data['model_execution'], 0)
        self.assertEqual(self.data['F61_execution'], 0)
        self.assertEqual(self.data['actual_activation'], 'NOT_ALLOWED')
        self.assertEqual(self.data['actual_call_custody'], 'NOT_QUALIFIED')
        self.assertEqual(self.data['forbidden_modules_loaded'], [])


if __name__ == '__main__':
    unittest.main()
