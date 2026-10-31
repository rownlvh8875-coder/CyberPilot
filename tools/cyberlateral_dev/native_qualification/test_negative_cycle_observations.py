"""Independent literal checks on the recorded fixed99-step negative cycle."""

import json
import unittest
from pathlib import Path


class NegativeCycleObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(Path('OBSERVATIONS.json').read_bytes())

    def test99_ordered_rows_one_step_each_and_exact_state_adjacency(self):
        rows = self.data['cases']
        self.assertEqual([r['index'] for r in rows], list(range(99)))
        self.assertEqual([r['model_steps'] for r in rows], [1] * 99)
        self.assertEqual(self.data['model_execution'], 99)
        for previous, current in zip(rows[:-1], rows[1:], strict=True):
            self.assertEqual(previous['model_output']['next_state'], current['prepared']['state'])

    def test_call89_90_91_92_exact_counter_request_and_nonzero_command(self):
        for index, counter, request in [(88, 89, True), (89, 90, False), (90, 0, False), (91, 1, True)]:
            output = self.data['cases'][index]['model_output']
            self.assertEqual((output['next_state']['angle_counter'], output['steer_request']), (counter, request))
            self.assertEqual(output['projection']['integer_command'], -12)
            self.assertEqual(output['projection']['torque_float32']['bits_hex'], 'bf400000')
            self.assertEqual(output['projection']['torque_output_can_float32']['bits_hex'], 'c1400000')

    def test_negative85_inclusive_and_negative84_point5_reset(self):
        rows = self.data['cases']
        self.assertEqual(rows[91]['prepared']['sample']['angle_hex'], '-0x1.5400000000000p+6')
        self.assertTrue(rows[91]['model_output']['trace']['downstream']['fault_condition'])
        self.assertEqual(rows[92]['prepared']['sample']['angle_hex'], '-0x1.5200000000000p+6')
        self.assertFalse(rows[92]['model_output']['trace']['downstream']['fault_condition'])
        self.assertEqual(rows[92]['model_output']['next_state']['angle_counter'], 0)
        self.assertEqual(rows[93]['model_output']['next_state']['angle_counter'], 1)

    def test_nonzero_inactive_reset_and_reactivation_uses_final_zeros(self):
        rows = self.data['cases']
        self.assertEqual(rows[94]['prepared']['state'], {'index': 94, 'previous_requested': -16, 'previous_applied': -12, 'angle_counter': 1})
        self.assertFalse(rows[94]['prepared']['sample']['lat_active'])
        trace = rows[94]['model_output']['trace']['downstream']
        self.assertEqual((trace['limited_command'], trace['final_command']), (-12, 0))
        self.assertEqual(rows[94]['model_output']['next_state'], {'index': 95, 'previous_requested': -16, 'previous_applied': 0, 'angle_counter': 0})
        self.assertEqual(rows[95]['prepared']['state'], rows[94]['model_output']['next_state'])
        self.assertEqual(rows[95]['model_output']['projection']['integer_command'], -2)

    def test_fractional_bounds_and_float_kind_rounding_are_preserved(self):
        rows = self.data['cases']
        for index in [0, 5, 89, 90, 94, 95]:
            trace = rows[index]['model_output']['trace']['downstream']
            self.assertEqual(trace['driver_clip']['lower'], {'kind': 'python.float', 'value': '-0x1.7000000000000p+3'})
            self.assertEqual(trace['driver_clip']['result'], {'kind': 'numpy.float64', 'value': '-0x1.7000000000000p+3'})
            self.assertEqual(trace['rate_clip']['result']['kind'], 'numpy.float64')
        for index in [5, 89, 90, 94]:
            trace = rows[index]['model_output']['trace']['downstream']
            self.assertEqual(trace['rate_clip']['result']['value'], '-0x1.7000000000000p+3')
            self.assertEqual(trace['limited_command'], -12)
        self.assertEqual(rows[0]['model_output']['trace']['downstream']['rate_clip']['result']['value'], '-0x1.0000000000000p+1')

    def test_complete_command_series_and_final_state(self):
        rows = self.data['cases']
        self.assertEqual([r['model_output']['projection']['integer_command'] for r in rows],
                         [-2, -4, -6, -8, -10, -12] + [-12] * 88 + [0, -2, -4, -6, -8])
        self.assertEqual(rows[-1]['model_output']['next_state'], {'index': 99, 'previous_requested': -16, 'previous_applied': -8, 'angle_counter': 4})

    def test_exact_reference_stamps_oracle_and_prohibited_real_gates(self):
        self.assertEqual(self.data['model_reference_sha256'], 'f3b60afc2e3ba8b100ee9dbcb2a125f9c27c797c3d6b4af7b882cc7c069390f8')
        for index, row in enumerate(self.data['cases']):
            self.assertIs(row['oracle_parity'], True)
            self.assertIs(row['model_expected_match'], True)
            self.assertEqual(row['stamp'], {'sequence_id': 'R26_FIXED_NEGATIVE_CYCLE', 'invocation_index': index, 'capture_id': 'entry_' + str(index)})
        self.assertEqual(self.data['actual_call_custody'], 'NOT_QUALIFIED')
        self.assertEqual(self.data['actual_activation'], 'NOT_ALLOWED')
        self.assertEqual(self.data['F61_execution'], 0)
        self.assertEqual(self.data['forbidden_modules_loaded'], [])
        self.assertEqual(self.data['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(self.data['STATIC_EVIDENCE_GATE'], 'FAIL')
        self.assertEqual(self.data['time_semantics'], 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME')


if __name__ == '__main__':
    unittest.main()
