"""Independent literal checks of the recorded fixed20-step native driver trace."""

import json
import unittest
from pathlib import Path


class DriverObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(Path('OBSERVATIONS.json').read_bytes())

    def test_exact20_adjacent_steps_and_scoped_counts(self):
        rows = self.data['cases']
        self.assertEqual([r['index'] for r in rows], list(range(20)))
        self.assertEqual([r['model_steps'] for r in rows], [1] * 20)
        self.assertEqual(self.data['model_execution'], 20)
        for before, after in zip(rows[:-1], rows[1:], strict=True):
            self.assertEqual(before['model_output']['next_state'], after['prepared']['state'])

    def test_literal_commands_and_final_state(self):
        rows = self.data['cases']
        self.assertEqual([r['model_output']['projection']['integer_command'] for r in rows],
                         [2, 4, 6, 8, 10, 12, 7, 2, -2, -4, -6, -8, -10, -12, -12, -12, 0, -2, 0, 0])
        self.assertEqual(rows[-1]['model_output']['next_state'],
                         {'index': 20, 'previous_requested': 16, 'previous_applied': 0, 'angle_counter': 3})

    def test_fractional_bounds_preserve_float_kinds_and_hex_results(self):
        rows = self.data['cases']
        for index, bound, value in [(0, 'upper', '0x1.7000000000000p+3'), (5, 'upper', '0x1.7000000000000p+3'),
                                     (13, 'lower', '-0x1.7000000000000p+3'), (16, 'lower', '-0x1.7000000000000p+3')]:
            trace = rows[index]['model_output']['trace']['downstream']
            self.assertEqual(trace['driver_clip'][bound], {'kind': 'python.float', 'value': value})
            for stage in ['driver_clip', 'rate_clip']:
                self.assertEqual(trace[stage]['result']['kind'], 'numpy.float64')
        self.assertEqual(rows[0]['model_output']['trace']['downstream']['rate_clip']['result']['value'], '0x1.0000000000000p+1')

    def test_nearest_even_fractional_bounds_are_not_post_round_clamped(self):
        for index, fraction, integer in [(5, '0x1.7000000000000p+3', 12), (13, '-0x1.7000000000000p+3', -12)]:
            trace = self.data['cases'][index]['model_output']['trace']['downstream']
            self.assertEqual(trace['rate_clip']['result'], {'kind': 'numpy.float64', 'value': fraction})
            self.assertEqual((trace['limited_command'], trace['final_command']), (integer, integer))

    def test_negative_boundary_below_boundary_and_nonzero_inactive_reset(self):
        rows = self.data['cases']
        self.assertEqual([r['model_output']['next_state']['angle_counter'] for r in rows],
                         [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 0, 1, 0, 1, 2, 3])
        self.assertEqual(rows[14]['prepared']['sample']['angle_hex'], '-0x1.5200000000000p+6')
        self.assertFalse(rows[14]['model_output']['trace']['downstream']['fault_condition'])
        self.assertTrue(rows[15]['model_output']['trace']['downstream']['fault_condition'])
        self.assertEqual(rows[16]['prepared']['state']['angle_counter'], 1)
        self.assertFalse(rows[16]['prepared']['sample']['lat_active'])
        trace = rows[16]['model_output']['trace']['downstream']
        self.assertEqual((trace['limited_command'], trace['final_command'], trace['next_state']['angle_counter']), (-12, 0, 0))
        self.assertEqual(rows[17]['prepared']['state']['previous_applied'], 0)
        self.assertEqual(rows[17]['model_output']['projection']['integer_command'], -2)

    def test_zero_clamp_branches_use_integer_bounds_and_results(self):
        for index, lower, upper in [(18, 0, 16), (19, -16, 0)]:
            trace = self.data['cases'][index]['model_output']['trace']['downstream']
            self.assertEqual(trace['driver_clip']['lower'], {'kind': 'python.int', 'value': lower})
            self.assertEqual(trace['driver_clip']['upper'], {'kind': 'python.int', 'value': upper})
            for stage in ['driver_clip', 'rate_clip']:
                self.assertEqual(trace[stage]['result'], {'kind': 'numpy.int64', 'value': 0})

    def test_reference_stamps_oracle_and_closed_gates(self):
        self.assertEqual(self.data['model_reference_sha256'], '21de9d95fa3e45dd03fe5ac8da0505a4ea94d233dc81d21ba65d741573ef1fa7')
        for index, row in enumerate(self.data['cases']):
            self.assertIs(row['oracle_parity'], True)
            self.assertIs(row['model_expected_match'], True)
            self.assertEqual(row['stamp'], {'sequence_id': 'R25_FIXED_DRIVER_CONTEXT', 'invocation_index': index, 'capture_id': 'entry_' + str(index)})
        self.assertEqual(self.data['actual_call_custody'], 'NOT_QUALIFIED')
        self.assertEqual(self.data['actual_activation'], 'NOT_ALLOWED')
        self.assertEqual(self.data['F61_execution'], 0)
        self.assertEqual(self.data['forbidden_modules_loaded'], [])
        self.assertEqual(self.data['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(self.data['STATIC_EVIDENCE_GATE'], 'FAIL')
        self.assertEqual(self.data['time_semantics'], 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME')


if __name__ == '__main__':
    unittest.main()
