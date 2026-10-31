"""Independent literal acceptance on recorded96-step native fault/reset trace."""

import json
import unittest
from pathlib import Path


class FaultObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(Path('OBSERVATIONS.json').read_bytes())

    def test_96_adjacent_indices_and_exact_scoped_counts(self):
        rows = self.data['cases']
        self.assertEqual([r['index'] for r in rows], list(range(96)))
        self.assertEqual([r['model_steps'] for r in rows], [1] * 96)
        self.assertEqual(self.data['model_execution'], 96)

    def test_literal89_90_91_92_call_counter_and_request_boundary(self):
        for index, counter, request in [(88, 89, True), (89, 90, False), (90, 0, False), (91, 1, True)]:
            output = self.data['cases'][index]['model_output']
            self.assertEqual((output['next_state']['angle_counter'], output['steer_request']), (counter, request))
            self.assertEqual(output['projection']['integer_command'], 4)

    def test_suppression_does_not_invent_zero_command(self):
        for index in [89, 90]:
            output = self.data['cases'][index]['model_output']
            self.assertFalse(output['steer_request'])
            self.assertEqual(output['trace']['downstream']['final_command'], 4)
            self.assertEqual(output['projection']['torque_float32']['bits_hex'], '3e800000')

    def test_below85_and_inactive_reset_then_final_zero_state_carry(self):
        rows = self.data['cases']
        self.assertEqual(rows[92]['prepared']['sample']['angle_hex'], '0x1.5200000000000p+6')
        self.assertFalse(rows[92]['model_output']['trace']['downstream']['fault_condition'])
        self.assertEqual(rows[92]['model_output']['next_state']['angle_counter'], 0)
        inactive = rows[93]['model_output']['trace']['downstream']
        self.assertEqual((inactive['limited_command'], inactive['final_command'], inactive['next_state']['angle_counter']), (4, 0, 0))
        self.assertEqual(rows[94]['prepared']['state']['previous_applied'], 0)
        self.assertEqual(rows[94]['model_output']['projection']['integer_command'], 2)
        self.assertEqual(rows[95]['model_output']['next_state'], {'index': 96, 'previous_requested': 4, 'previous_applied': 4, 'angle_counter': 0})

    def test_all_model_states_and_metadata_are_consistent(self):
        rows = self.data['cases']
        for previous, current in zip(rows[:-1], rows[1:], strict=True):
            self.assertEqual(previous['model_output']['next_state'], current['prepared']['state'])
        for index, row in enumerate(rows):
            self.assertIs(row['oracle_parity'], True)
            self.assertIs(row['model_expected_match'], True)
            self.assertEqual(row['stamp'], {'sequence_id': 'R24_FIXED_FAULT_RESET', 'invocation_index': index, 'capture_id': 'entry_' + str(index)})

    def test_reference_and_declaration_only_gates(self):
        self.assertEqual(self.data['model_reference_sha256'], '7d0d6ab9702318049752fc5312c6530f91822ed391a83863a56134d95df550e0')
        self.assertEqual(self.data['actual_call_custody'], 'NOT_QUALIFIED')
        self.assertEqual(self.data['actual_activation'], 'NOT_ALLOWED')
        self.assertEqual(self.data['F61_execution'], 0)
        self.assertEqual(self.data['forbidden_modules_loaded'], [])
        self.assertEqual(self.data['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(self.data['STATIC_EVIDENCE_GATE'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
