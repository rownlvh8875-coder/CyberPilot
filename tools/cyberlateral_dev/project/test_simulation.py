"""Catch batch resets, state leakage, hidden policy and fixed-catalog drift."""
import hashlib
import json
import unittest
from dataclasses import FrozenInstanceError, asdict, astuple
from types import SimpleNamespace

from consumer_reference import expected_simulation
from normalized_reference import NormalizedReference
from quantized_fixtures import normalized_scenarios
from test_source_contract import REFERENCE
from v1_helpers import package_feature


class SimulationTests(unittest.TestCase):
    def package(self):
        p = package_feature()
        self.assertTrue(hasattr(p, 'simulate'), 'Missing planned pure batch API')
        return p

    def samples(self, p, values=(0.1, 0.3, -0.1, -0.3), start=0):
        return tuple(p.LateralInput(i + start, q, 0.0, 0.0, True, p.Limits(5, 5, 5, 0, 1, 1), 'SYNTHETIC_ONLY')
                     for i, q in enumerate(values))

    def reference(self):
        return NormalizedReference((REFERENCE / 'carcontroller.py').read_bytes(), (REFERENCE / 'lateral.py').read_bytes())

    def test_decimal_ties_and_split_resume_same_outputs(self):
        p = self.package()
        samples, state = self.samples(p), p.initial_state()
        result = p.simulate(samples, state)
        self.assertEqual([x.projection.integer_command for x in result.outputs], [0, 2, 0, -2])
        first = p.simulate(samples[:2], state)
        second = p.simulate(samples[2:], first.next_state)
        self.assertEqual(result.outputs, first.outputs + second.outputs)
        self.assertEqual(result.next_state, second.next_state)

    def test_nonzero_initial_history_uses_same_scale_without_clamp(self):
        p = self.package()
        result = p.simulate(self.samples(p, (0.0,), 1), p.LateralState(1, 100, 100, 0))
        self.assertEqual(result.outputs[0].projection.normalized_expression, 19.0)
        self.assertEqual(result.next_state.previous_applied, 95)

    def test_purity_immutable_result_and_no_partial_return_on_bad_later_sample(self):
        p = self.package()
        samples, state = self.samples(p), p.initial_state()
        before = asdict(state), tuple(asdict(s) for s in samples)
        result = p.simulate(samples, state)
        self.assertEqual(result, p.simulate(samples, state))
        self.assertEqual(before, (asdict(state), tuple(asdict(s) for s in samples)))
        with self.assertRaises(FrozenInstanceError):
            result.next_state = state
        bad = samples[:1] + self.samples(p, (0.0,), 3)
        with self.assertRaises(ValueError):
            p.simulate(bad, state)
        self.assertEqual(asdict(state), before[0])

    def test_strict_bounded_tuple_and_no_iteration_of_generator(self):
        p = self.package()
        def dangerous():
            raise AssertionError('ITERATOR_MUST_NOT_BE_CONSUMED')
            yield
        for value in [None, [], (), self.samples(p) * 1025, dangerous()]:
            with self.subTest(type=type(value)), self.assertRaises(ValueError):
                p.simulate(value, p.initial_state())

    def test_state_exhaustion_rejected_not_reset(self):
        p = self.package()
        result = p.simulate(self.samples(p, (0.0,), 4095), p.LateralState(4095, 0, 0, 0))
        self.assertEqual(result.next_state.index, 4096)
        with self.assertRaises(ValueError):
            p.simulate(self.samples(p, (0.0,), 4096), result.next_state)

    def test_invalid_scope_state_and_missing_scale_rejected(self):
        p = self.package()
        good = self.samples(p)[0]
        for sample in [None, p.LateralInput(0, 0.0, 0.0, 0.0, True, None, 'SYNTHETIC_ONLY'),
                       p.LateralInput(0, 0.0, 0.0, 0.0, True, good.limits, 'PRODUCTION')]:
            with self.assertRaises(ValueError):
                p.simulate((sample,), p.initial_state())
        with self.assertRaises(ValueError):
            p.simulate((good,), None)

    def test_all_224_inherited_scenarios_independent_batch_parity(self):
        p, reference = self.package(), self.reference()
        for scenario in normalized_scenarios():
            samples = tuple(p.LateralInput(s.index, s.request, s.driver, s.angle_deg, s.lat_active,
                                           p.Limits(*astuple(s.limits)), s.provenance) for s in scenario.samples)
            expected = expected_simulation(SimpleNamespace(initial_state=p.initial_state(), samples=samples), reference)
            self.assertEqual(asdict(p.simulate(samples, p.initial_state())), expected, scenario.id)

    def test_catalog_seven_112_literals_and_independent_output_records(self):
        p, reference = self.package(), self.reference()
        scenarios = package_feature('cyberlateral_dev.synthetic_catalog').fixed_catalog()
        self.assertEqual((len(scenarios), sum(len(s.samples) for s in scenarios)), (7, 112))
        actual = {s.id: p.simulate(s.samples, s.initial_state) for s in scenarios}
        for scenario in scenarios:
            self.assertEqual(asdict(actual[scenario.id]), expected_simulation(scenario, reference))
        self.assertEqual([o.projection.integer_command for o in actual['ramp'].outputs], [2, 4, 6])
        self.assertEqual([o.projection.integer_command for o in actual['inactive'].outputs], [2, 0, 0, 2])
        self.assertEqual([i for i, o in enumerate(actual['fault-cycle'].outputs) if not o.steer_request], [89, 90])
        self.assertTrue(all(o.projection.integer_command != 0 for o in actual['fault-cycle'].outputs))
        self.assertEqual(actual['signed-zero'].outputs[0].projection.normalized_expression_hex, '0x0.0p+0')

    def test_canonical_catalog_report_identity_and_gates(self):
        self.package()
        m = package_feature('cyberlateral_dev.reporting')
        one, two = m.catalog_report(), m.catalog_report()
        self.assertEqual(one, two)
        raw = m.canonical_report(one)
        self.assertEqual(raw, (json.dumps(one, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode())
        self.assertEqual(one['total_steps'], 112)
        self.assertEqual(one['package_version'], '0.3.0')
        fixture = [{'id':s['id'], 'initial_state':s['initial_state'], 'samples':s['samples']} for s in one['scenarios']]
        self.assertEqual(one['fixture_catalog_sha256'], hashlib.sha256(m.canonical_report(fixture)).hexdigest())
        for key in ['actual_r', 'actual_T2', 'actual_vehicle_scale']:
            self.assertIsNone(one['gates'][key])
        self.assertEqual(one['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
        self.assertEqual(one['gates']['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(one['gates']['Runtime'], 'NO_GO')
        self.assertEqual(one['original_helper_calls'], 0)
        self.assertNotIn('duration_seconds', one)
        with self.assertRaises(ValueError):
            m.canonical_report({'value':float('nan')})


if __name__ == '__main__':
    unittest.main()
