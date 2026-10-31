"""Literal custom model mapping; not a generic independent numerical oracle."""

import importlib
import sys
import unittest
from dataclasses import replace
from unittest.mock import patch

from scenario_fixture import document, encode
from v1_helpers import ROOT, package_feature


class ScenarioEngineTests(unittest.TestCase):
    def modules(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_engine.py').is_file(), 'Missing R31 engine')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        p = package_feature()
        return importlib.import_module('integration_tools.scenario_input'), importlib.import_module('integration_tools.scenario_engine'), p

    def test_literal_sign_inactive_cycle_and_distinct_history(self):
        m, e, p = self.modules()
        data = document(4)
        data['samples'][1]['request'] = -0.25
        data['samples'][2]['lat_active'] = False
        with patch.object(p, 'simulate', wraps=p.simulate) as calls:
            result = e.evaluate_scenario(m.parse_scenario(encode(data)))
        self.assertEqual(calls.call_count, 1)
        self.assertEqual(result['model_steps'], 4)
        rows = result['rows']
        self.assertEqual([r['model_output']['trace']['quantization']['integer_command'] for r in rows], [4, -4, 4, 4])
        self.assertEqual([r['model_output']['trace']['downstream']['limited_command'] for r in rows], [2, -2, 2, 2])
        self.assertEqual([r['model_output']['projection']['integer_command'] for r in rows], [2, -2, 0, 2])
        self.assertEqual(rows[3]['prepared']['state'], {'index': 3, 'previous_requested': 4, 'previous_applied': 0, 'angle_counter': 0})
        self.assertEqual(result['final_state'], {'index': 4, 'previous_requested': 4, 'previous_applied': 2, 'angle_counter': 0})

    def test_explicit_resumed_fault_boundary(self):
        m, e, _ = self.modules()
        data = document()
        data['initial_state'].update(index=5, previous_requested=2, previous_applied=2, angle_counter=89)
        data['samples'][0].update(index=5, request=-0.25, driver=8.5, angle_deg=85.0)
        result = e.evaluate_scenario(m.parse_scenario(encode(data)))
        self.assertEqual(result['final_state'], {'index': 6, 'previous_requested': -4, 'previous_applied': -2, 'angle_counter': 90})
        self.assertIs(result['rows'][0]['model_output']['steer_request'], False)

    def test_binary64_and_signed_zero_mapping(self):
        m, e, _ = self.modules()
        data = document()
        data['samples'][0].update(request=0.3, driver=-0.0, angle_deg=-0.0)
        row = e.evaluate_scenario(m.parse_scenario(encode(data)))['rows'][0]
        self.assertEqual(row['prepared']['sample']['request_hex'], '0x1.3333333333333p-2')
        self.assertEqual(row['prepared']['sample']['driver_hex'], '-0x0.0p+0')
        self.assertEqual(row['model_output']['trace']['quantization']['product_hex'], '0x1.3333333333333p+2')

    def test_forged_late_invalid_spec_never_calls_model(self):
        m, e, p = self.modules()
        spec = m.parse_scenario(encode(document(3)))
        bad = replace(spec, samples=spec.samples[:-1] + (replace(spec.samples[-1], driver=0.1),))
        with patch.object(p, 'simulate', side_effect=AssertionError('MODEL_MUST_NOT_RUN')) as calls:
            with self.assertRaises(m.ScenarioError):
                e.evaluate_scenario(bad)
        self.assertEqual(calls.call_count, 0)

    def test_maximum4096_and_explicit_zero_limits(self):
        m, e, _ = self.modules()
        data = document(4096)
        data['limits']['STEER_DELTA_UP'] = 0
        result = e.evaluate_scenario(m.parse_scenario(encode(data)))
        self.assertEqual((result['model_steps'], result['final_state']['index'], result['final_state']['previous_applied']), (4096, 4096, 0))

    def test_wrong_package_and_malformed_simulation_rejected(self):
        m, e, p = self.modules()
        spec = m.parse_scenario(encode(document()))
        with patch.object(p, '__version__', 'other'), self.assertRaises(m.ScenarioError):
            e.evaluate_scenario(spec)
        for invalid in [None, p.SimulationResult((), p.LateralState(0, None, 0, 0))]:
            with patch.object(p, 'simulate', return_value=invalid), self.assertRaises(m.ScenarioError):
                e.evaluate_scenario(spec)
