"""Independent literal checks on the actual closed native R22 observation file."""

import json
import unittest
from pathlib import Path


class ModelObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(Path('OBSERVATIONS.json').read_bytes())

    def rows(self):
        return {row['id']: row for row in self.data['cases']}

    def test_eight_cases_five_single_steps_and_three_rejections(self):
        rows = self.rows()
        self.assertEqual(len(rows), 8)
        self.assertEqual(sum(r['accepted'] for r in rows.values()), 5)
        self.assertEqual(sum(r['model_steps'] for r in rows.values()), 5)
        self.assertEqual(self.data['model_execution'], 5)
        for row in rows.values():
            self.assertEqual(row['model_steps'], int(row['accepted']))
        for name in ['driver_precision_reject', 'angle_precision_reject', 'request_range_reject']:
            self.assertNotIn('model_output', rows[name])
            self.assertEqual(rows[name]['rejection_code'], 'SEMANTIC_DOMAIN')

    def test_literal_commands_and_request_bits(self):
        for name, command, active in [('zero', 0, False), ('rounded_request', 2, True), ('signed_zero', 0, False),
                                      ('resumed', 4, True), ('smallest_subnormal', 0, True)]:
            output = self.rows()[name]['model_output']
            self.assertEqual(output['projection']['integer_command'], command)
            self.assertEqual(output['steer_request'], active)

    def test_literal_next_states_are_not_chained(self):
        for name in ['zero', 'signed_zero', 'smallest_subnormal']:
            self.assertEqual(self.rows()[name]['model_output']['next_state'],
                             {'index': 1, 'previous_requested': 0, 'previous_applied': 0, 'angle_counter': 0})
        self.assertEqual(self.rows()['rounded_request']['model_output']['next_state'],
                         {'index': 1, 'previous_requested': 5, 'previous_applied': 2, 'angle_counter': 0})
        self.assertEqual(self.rows()['resumed']['model_output']['next_state'],
                         {'index': 2, 'previous_requested': 4, 'previous_applied': 4, 'angle_counter': 0})

    def test_quantization_product_and_signed_zero_literals(self):
        for name, product in [('rounded_request', '0x1.3333340000000p+2'), ('signed_zero', '-0x0.0p+0'),
                               ('smallest_subnormal', '0x1.0000000000000p-145'), ('resumed', '0x1.0000000000000p+2')]:
            self.assertEqual(self.rows()[name]['model_output']['trace']['quantization']['product_hex'], product)

    def test_invocation_rate_bounds_and_schema_simulation_not_wire(self):
        for name, lower, upper in [('rounded_request', -2, 2), ('resumed', -2, 5)]:
            output = self.rows()[name]['model_output']
            clip = output['trace']['downstream']['rate_clip']
            self.assertEqual((clip['lower']['value'], clip['upper']['value']), (lower, upper))
            self.assertEqual(output['projection']['status'], 'SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE')
        self.assertEqual(self.rows()['rounded_request']['model_output']['projection']['torque_float32']['bits_hex'], '3e000000')
        self.assertEqual(self.rows()['resumed']['model_output']['projection']['torque_float32']['bits_hex'], '3e800000')

    def test_pinned_preregistration_and_complete_comparison(self):
        self.assertEqual(self.data['model_reference_sha256'], '55e07d229fadd5cbe96130670b3a16812ef0ef9ebf20a389408cd5ca9cf0fff1')
        for row in self.rows().values():
            self.assertTrue(row['oracle_parity'])
            if row['accepted']:
                self.assertTrue(row['model_expected_match'])

    def test_no_actual_or_f61_work_or_history_promotion(self):
        self.assertEqual(self.data['F61_execution'], 0)
        self.assertEqual(self.data['actual_activation'], 'NOT_ALLOWED')
        self.assertEqual(self.data['actual_call_custody'], 'NOT_QUALIFIED')
        self.assertEqual(self.data['forbidden_modules_loaded'], [])
        self.assertEqual(self.data['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(self.data['STATIC_EVIDENCE_GATE'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
