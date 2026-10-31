"""Independent hand-literal checks on exported R29 chain data only."""

import json
import unittest
from pathlib import Path


class AdapterSequenceObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(Path('OBSERVATIONS.json').read_bytes())

    def test_both_complete_profiles_and_exact103_calls(self):
        self.assertEqual([p['profile_id'] for p in self.data['profiles']], ['SIGN_CHANGE_4', 'NEGATIVE_CYCLE_99'])
        self.assertEqual([len(p['cases']) for p in self.data['profiles']], [4, 99])
        self.assertEqual((self.data['model_execution'], self.data['observed_model_calls']), (103, 103))
        for profile in self.data['profiles']:
            self.assertEqual([r['index'] for r in profile['cases']], list(range(len(profile['cases']))))
            self.assertEqual([r['model_steps'] for r in profile['cases']], [1] * len(profile['cases']))

    def test_every_carried_state_equals_previous_verified_output(self):
        for profile in self.data['profiles']:
            self.assertEqual(profile['cases'][0]['prepared']['state'], {'index': 0, 'previous_requested': None, 'previous_applied': 0, 'angle_counter': 0})
            for previous, current in zip(profile['cases'][:-1], profile['cases'][1:], strict=True):
                self.assertEqual(current['prepared']['state'], previous['model_output']['next_state'])
                self.assertEqual(current['state_binding'], 'PREVIOUS_VERIFIED_MODEL_OUTPUT_NOT_ACTUAL_HISTORY')

    def test_sign_change_and_inactive_final_not_limiter_output(self):
        rows = self.data['profiles'][0]['cases']
        self.assertEqual([r['model_output']['next_state']['previous_requested'] for r in rows], [5, -4, 4, 4])
        self.assertEqual([r['model_output']['next_state']['previous_applied'] for r in rows], [2, -2, 0, 2])
        self.assertEqual(rows[2]['model_output']['trace']['downstream']['limited_command'], 2)
        self.assertEqual(rows[3]['prepared']['state']['previous_applied'], 0)

    def test_fault_boundary_reset_and_reactivation_literals(self):
        rows = self.data['profiles'][1]['cases']
        self.assertEqual([rows[i]['model_output']['next_state']['angle_counter'] for i in [88, 89, 90, 91]], [89, 90, 0, 1])
        self.assertEqual([rows[i]['model_output']['steer_request'] for i in [88, 89, 90, 91]], [True, False, False, True])
        self.assertEqual(rows[92]['model_output']['next_state']['angle_counter'], 0)
        self.assertEqual(rows[94]['model_output']['next_state'], {'index': 95, 'previous_requested': -16, 'previous_applied': 0, 'angle_counter': 0})
        self.assertEqual(rows[95]['prepared']['state']['previous_applied'], 0)

    def test_projection_is_not_CAN_wire_and_gates_stay_closed(self):
        for profile in self.data['profiles']:
            for row in profile['cases']:
                self.assertEqual(row['model_output']['projection']['status'], 'SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE')
        self.assertEqual((self.data['actual_call_custody'], self.data['actual_activation'], self.data['time_semantics']),
                         ('NOT_QUALIFIED', 'NOT_ALLOWED', 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME'))
        self.assertEqual((self.data['R_BUDGET'], self.data['STATIC_EVIDENCE_GATE']), ('UNRESOLVED', 'FAIL'))
        self.assertEqual([self.data[name] for name in ['F61_execution', 'Controller_execution', 'Runtime_execution', 'CAN',
                                                     'calculator_input_execution', 'actual_inputs', 'r_calculation', 'dt_calculation']], [0] * 8)
