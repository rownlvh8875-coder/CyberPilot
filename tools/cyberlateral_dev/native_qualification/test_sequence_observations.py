"""Independent literal checks on recorded R23 native/model continuity."""

import json
import unittest
from pathlib import Path


class SequenceObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(Path('OBSERVATIONS.json').read_bytes())

    def test_four_ordered_steps_and_scoped_counts(self):
        self.assertEqual([r['index'] for r in self.data['cases']], [0, 1, 2, 3])
        self.assertEqual([r['model_steps'] for r in self.data['cases']], [1, 1, 1, 1])
        self.assertEqual(self.data['model_execution'], 4)

    def test_literal_commands_and_next_states(self):
        rows = self.data['cases']
        self.assertEqual([r['model_output']['projection']['integer_command'] for r in rows], [2, -2, 0, 2])
        self.assertEqual([r['model_output']['next_state'] for r in rows], [
            {'index': 1, 'previous_requested': 5, 'previous_applied': 2, 'angle_counter': 0},
            {'index': 2, 'previous_requested': -4, 'previous_applied': -2, 'angle_counter': 0},
            {'index': 3, 'previous_requested': 4, 'previous_applied': 0, 'angle_counter': 0},
            {'index': 4, 'previous_requested': 4, 'previous_applied': 2, 'angle_counter': 0}])

    def test_actual_model_output_state_is_carried_between_fixed_native_frames(self):
        rows = self.data['cases']
        self.assertEqual(rows[0]['state_binding'], 'EXPLICIT_FIXED_INITIAL_DATA')
        for previous, current in zip(rows[:-1], rows[1:], strict=True):
            self.assertEqual(previous['model_output']['next_state'], current['prepared']['state'])
            self.assertEqual(current['state_binding'], 'PREVIOUS_VERIFIED_MODEL_OUTPUT_NOT_ACTUAL_HISTORY')
        self.assertTrue(all(r['oracle_parity'] and r['model_expected_match'] for r in rows))

    def test_inactive_final_not_limited_or_requested_is_next_previous(self):
        inactive = self.data['cases'][2]['model_output']['trace']['downstream']
        self.assertEqual((inactive['limited_command'], inactive['final_command']), (2, 0))
        self.assertEqual(self.data['cases'][3]['prepared']['state']['previous_applied'], 0)
        self.assertEqual(self.data['cases'][3]['prepared']['state']['previous_requested'], 4)

    def test_invocation_bounds_and_negative_projection_literals(self):
        rows = self.data['cases']
        bounds = [(r['model_output']['trace']['downstream']['rate_clip']['lower']['value'],
                   r['model_output']['trace']['downstream']['rate_clip']['upper']['value']) for r in rows]
        self.assertEqual(bounds, [(-2, 2), (-2, 4), (-4, 2), (-2, 2)])
        projection = rows[1]['model_output']['projection']
        self.assertEqual(projection['torque_float32']['bits_hex'], 'be000000')
        self.assertEqual(projection['torque_output_can_float32']['bits_hex'], 'c0000000')
        self.assertEqual(projection['status'], 'SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE')

    def test_native_float32_request_and_reference_identity(self):
        self.assertEqual(self.data['cases'][0]['prepared']['sample']['request_hex'], '0x1.3333340000000p-2')
        self.assertEqual(self.data['model_reference_sha256'], '221b04aae7a149409f5f91aa516e7f9fcefe090958e785d91bc6fd4153161e97')

    def test_vehicle_f61_and_policy_gates_remain_closed(self):
        self.assertEqual(self.data['F61_execution'], 0)
        self.assertEqual(self.data['actual_activation'], 'NOT_ALLOWED')
        self.assertEqual(self.data['actual_call_custody'], 'NOT_QUALIFIED')
        self.assertEqual(self.data['forbidden_modules_loaded'], [])
        self.assertEqual(self.data['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(self.data['STATIC_EVIDENCE_GATE'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
