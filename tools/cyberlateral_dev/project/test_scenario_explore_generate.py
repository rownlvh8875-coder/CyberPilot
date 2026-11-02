"""R42 generation must be reproducible, bounded and explicitly synthetic."""

import importlib
import json
import math
import subprocess
import sys
import unittest

from v1_helpers import ROOT


class ExplorationGeneratorTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_explore_generate.py').is_file(), 'Missing R42 deterministic generator')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_explore_generate')

    def test_repeated_generation_has_stable_names_bytes_and_explicit_scope(self):
        m = self.module()
        first = m.generate_cases(42, 2, 32)
        self.assertEqual(list(first), ['case-001.json', 'case-002.json'])
        self.assertEqual(first, m.generate_cases(42, 2, 32))
        for raw in first.values():
            data = json.loads(raw)
            self.assertEqual((data['schema_version'], data['scope']), (1, 'SYNTHETIC_ONLY'))
            self.assertEqual(raw, (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode())

    def test_seed_changes_actual_samples_not_only_names(self):
        m = self.module()
        first, second = [json.loads(m.generate_cases(seed, 1, 64)['case-001.json']) for seed in [42, 43]]
        self.assertNotEqual(first['samples'], second['samples'])
        self.assertEqual(first['initial_state'], second['initial_state'])

    def test_strict_parameter_types_and_bounds_fail_before_generation(self):
        m = self.module()

        class IntChild(int):
            pass

        for args in [(True, 1, 16), (IntChild(42), 1, 16), (42.0, 1, 16), ('42', 1, 16),
                     (-1, 1, 16), (2**32, 1, 16), (42, False, 16), (42, 0, 16), (42, 17, 16),
                     (42, 1.0, 16), (42, 1, True), (42, 1, 15), (42, 1, 257), (42, 1, 16.0)]:
            with self.subTest(args=args), self.assertRaisesRegex(m.ExplorationError, 'EXPLORATION_PARAMETERS'):
                m.generate_cases(*args)

    def test_maximum_parameters_produce_only_parseable_bounded_inputs(self):
        m = self.module()
        from integration_tools.scenario_input import parse_scenario

        cases = m.generate_cases(2**32 - 1, 16, 256)
        self.assertEqual(len(cases), 16)
        specs = [parse_scenario(raw) for raw in cases.values()]
        self.assertEqual(sum(len(s.samples) for s in specs), 4096)
        self.assertEqual([s.samples[-1].index for s in specs], [255] + [260] * 15)
        self.assertTrue(all(json.loads(raw)['scope'] == 'SYNTHETIC_ONLY' for raw in cases.values()))

    def test_fixed_prefix_preserves_rounding_neighbors_and_signed_zero(self):
        m = self.module()
        data = json.loads(m.generate_cases(42, 1, 16)['case-001.json'])
        requests = [row['request'] for row in data['samples']]
        self.assertEqual(requests[:4], [1.0, -1.0, 0.03125, 0.09375])
        self.assertEqual(requests[4].hex(), '0x1.fffffffffffffp-6')
        self.assertEqual(requests[5].hex(), '0x1.0000000000001p-5')
        self.assertEqual(requests[8].hex(), '-0x0.0p+0')
        self.assertEqual(requests[9].hex(), '0x0.0p+0')
        self.assertTrue(all(type(r) is float and math.isfinite(r) for r in requests))
        self.assertEqual(data['samples'][3]['angle_deg'], 84.99609375)
        self.assertFalse(data['samples'][8]['lat_active'])
        self.assertTrue(data['samples'][9]['lat_active'])

    def test_resumed_states_do_not_conflate_previous_requested_and_applied(self):
        m = self.module()
        data = [json.loads(raw) for raw in m.generate_cases(0, 4, 16).values()]
        self.assertEqual(data[0]['initial_state'], {'index': 0, 'previous_requested': None, 'previous_applied': 0, 'angle_counter': 0})
        for value, counter in zip(data[1:], [88, 89, 90], strict=True):
            self.assertEqual(value['initial_state'], {'index': 5, 'previous_requested': 4, 'previous_applied': -3, 'angle_counter': counter})
            self.assertEqual(value['samples'][0]['index'], 5)
        self.assertEqual([r['limits']['STEER_MAX'] for r in data], [16, 8, 32, 5])
        self.assertEqual(data[2]['limits']['STEER_DELTA_UP'], 0)

    def test_feature_counts_describe_actual_prefix_not_exhaustive_coverage(self):
        m = self.module()
        raw = m.generate_cases(42, 1, 16)
        record = m.generation_record(42, 1, 16, raw)
        self.assertEqual(record['input_feature_counts'], {
            'positive_requests': 8, 'negative_requests': 6, 'zero_requests': 2, 'negative_zero_requests': 1,
            'request_sign_transitions': 8, 'fractional_drivers': 10, 'inactive_samples': 2,
            'high_angle_samples': 12, 'resumed_cases': 0,
        })
        self.assertEqual(record['coverage_claim'], 'INPUT_FEATURE_COUNTS_NOT_EXHAUSTIVE_BRANCH_COVERAGE')
        self.assertEqual(record['generated_samples'], 16)

    def test_generation_metadata_rejects_wrong_bytes_or_wrong_parameters(self):
        m = self.module()
        raw = m.generate_cases(42, 1, 16)
        for payloads in [{}, {**raw, 'extra.json': b'{}'}, {'case-001.json': b'{}'}]:
            with self.subTest(payloads=payloads), self.assertRaisesRegex(m.ExplorationError, 'EXPLORATION_GENERATION_MISMATCH'):
                m.generation_record(42, 1, 16, payloads)
        with self.assertRaisesRegex(m.ExplorationError, 'EXPLORATION_GENERATION_MISMATCH'):
            m.generation_record(43, 1, 16, raw)

    def test_pure_generator_and_metadata_cannot_import_model_or_numpy(self):
        self.module()
        code = ('import sys\n'
                'class Barrier:\n'
                ' def find_spec(self,fullname,path=None,target=None):\n'
                '  if fullname.split(".")[0] in {"cyberlateral_dev","numpy","capnp","openpilot","opendbc","cereal"}: '
                'raise AssertionError("GENERATOR_IMPORT:"+fullname)\n'
                'sys.meta_path.insert(0,Barrier())\n'
                f'sys.path.insert(0,{str(ROOT)!r})\n'
                'from integration_tools.scenario_explore_generate import generate_cases,generation_record\n'
                'r=generation_record(42,1,16,generate_cases(42,1,16))\n'
                'assert r["generated_samples"]==16\n')
        result = subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, check=False, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode())


if __name__ == '__main__':
    unittest.main()
