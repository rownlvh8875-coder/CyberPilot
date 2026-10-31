"""Independent data-only checks against one recorded complete fixed R27 suite."""

import hashlib
import json
import unittest
from pathlib import Path


class SuiteObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(Path('SUITE_SUMMARY.json').read_bytes())

    def test_complete_eight_modes_and_exact_scoped16_workers454_calls(self):
        self.assertEqual(self.data['status'], 'F70UGZ_R27_FIXED_NATIVE_SUITE_PASS')
        self.assertEqual([r['stage_id'] for r in self.data['stages']], ['R19', 'R20', 'R21', 'R22', 'R23', 'R24', 'R25', 'R26'])
        self.assertEqual((self.data['stage_count'], self.data['worker_processes'], self.data['model_execution']), (8, 16, 454))
        self.assertEqual([r['model_execution'] for r in self.data['stages']], [0, 0, 0, 10, 8, 198, 40, 198])
        self.assertEqual(self.data['model_execution_scope'], 'THIS_FIXED_SUITE_WORKERS_NOT_UNIT_TEST_OR_STAGE_TOTAL')

    def test_all_eight_complete_historical_observation_identities_and_child_summaries(self):
        expected = ['b7eaadea476113bcd5e56b6526382dc468773f9ec69327f4a6c6fc31cff2fe74',
                    'd88aabec4c37ceaca52f2516ae0a7c7c3d2efbad2680afa365a1c809b06448af',
                    'afbc84215769d23a8939828a28cc4c5507485bb8177a3e64e52fadad2c753ae2',
                    'c802a6ecad9f0cae59b8d82598d9b6a58a171d7e8a826406b21e3c157d02c4a7',
                    '662a138f71ef6c065eebb6061ba71ab2e6c728250c57bef8a932e32e0c260441',
                    'b13ff35e6fda538af2a437309384109d5e87adf8cc6c3f5a6edba44c4626287d',
                    '2283bed92bafaacda57486fe109be213d5a1479a820cfc63074539f3d7ba3150',
                    '4720baa96bfef759037a80a214d5ce84292fc0b607d06f5ccfd9f5b86d154a62']
        for row, digest in zip(self.data['stages'], expected, strict=True):
            directory = Path(row['stage_id'])
            self.assertEqual(hashlib.sha256((directory / 'OBSERVATIONS.json').read_bytes()).hexdigest(), digest)
            self.assertEqual(row['observations_sha256'], digest)
            self.assertEqual(hashlib.sha256((directory / 'SUMMARY.json').read_bytes()).hexdigest(), row['summary_sha256'])

    def test_numerical_references_match_constructor_contracts_including_r24_v2(self):
        expected = [None, None, None, '55e07d229fadd5cbe96130670b3a16812ef0ef9ebf20a389408cd5ca9cf0fff1',
                    '221b04aae7a149409f5f91aa516e7f9fcefe090958e785d91bc6fd4153161e97',
                    'dfb150fc3f1348be6fae161bdb2d524dc1138c504410c8ef38bf874c27b4d8cd',
                    '21de9d95fa3e45dd03fe5ac8da0505a4ea94d233dc81d21ba65d741573ef1fa7',
                    'f3b60afc2e3ba8b100ee9dbcb2a125f9c27c797c3d6b4af7b882cc7c069390f8']
        self.assertEqual([r['reference_sha256'] for r in self.data['stages']], expected)
        for row in self.data['stages'][3:]:
            directory = Path(row['stage_id'])
            observed = json.loads((directory / 'OBSERVATIONS.json').read_bytes())
            summary = json.loads((directory / 'SUMMARY.json').read_bytes())
            self.assertEqual(observed['model_reference_sha256'], row['reference_sha256'])
            self.assertEqual(summary['model_reference_sha256'], row['reference_sha256'])

    def test_all_real_gates_and_unimplemented_capabilities_stay_closed(self):
        self.assertEqual(self.data['capabilities']['generic_native_reader'], 'NOT_IMPLEMENTED')
        self.assertEqual(self.data['capabilities']['actual_call_custody'], 'NOT_QUALIFIED')
        gates = self.data['gates']
        for name in ['F61_execution', 'calculator_input_execution', 'Controller_execution', 'Runtime_execution', 'CAN', 'actual_inputs', 'r_calculation', 'dt_calculation']:
            self.assertIs(type(gates[name]), int)
            self.assertEqual(gates[name], 0)
        self.assertEqual(gates['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(gates['STATIC_EVIDENCE_GATE'], 'FAIL')
        self.assertEqual(gates['actual_activation'], 'NOT_ALLOWED')
        self.assertEqual(gates['native_GitHub_CI'], 'NOT_RUN')
        self.assertEqual(self.data['default_pure_gate'], 'UNCHANGED_NOT_RUN_BY_THIS_COMMAND')

    def test_root43_hashes_and_each_four_file_child_manifest(self):
        roots = Path('SHA256SUMS.txt').read_text().splitlines()
        self.assertEqual(len(roots), 43)
        self.assertEqual(len(set(roots)), 43)
        for line in roots:
            digest, name = line.split('  ', 1)
            self.assertEqual(hashlib.sha256(Path(name).read_bytes()).hexdigest(), digest)
        for row in self.data['stages']:
            directory = Path(row['stage_id'])
            lines = (directory / 'SHA256SUMS.txt').read_text().splitlines()
            self.assertEqual(len(lines), 4)
            for line in lines:
                digest, name = line.split('  ', 1)
                self.assertEqual(hashlib.sha256((directory / name).read_bytes()).hexdigest(), digest)

    def test_receipt_is_separate_and_does_not_pollute_portable_summary_or_report(self):
        raw = Path('SUITE_SUMMARY.json').read_bytes()
        report = Path('SUITE_REPORT_KO.md').read_text()
        receipt = json.loads(Path('SUITE_RECEIPT.json').read_bytes())
        self.assertEqual(receipt['scope'], 'BOUNDED_PROCESS_AND_FILE_RECEIPTS_NOT_OS_AUTHENTICATION')
        for key in ['python', 'wheel', 'public_wheel']:
            self.assertNotIn(receipt[key].encode(), raw)
            self.assertNotIn(receipt[key], report)
        for row in self.data['stages']:
            for name, digest in receipt['stages'][row['stage_id']].items():
                self.assertEqual(hashlib.sha256((Path(row['stage_id']) / name).read_bytes()).hexdigest(), digest)

    def test_registry_and_reporter_source_identity_are_bound(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(self.data['registry_sha256'], 'b51d265b8dbd01b7efb1d1bb35529a3fc080201e59bf4936842097a41168ce18')
        self.assertEqual(set(self.data['tool_sources']), {'native_qualification/suite.py', 'native_qualification/suite_profiles.py',
                                                       'native_qualification/suite_validation.py', 'native_qualification/suite_report.py'})
        for name, digest in self.data['tool_sources'].items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest)


if __name__ == '__main__':
    unittest.main()
