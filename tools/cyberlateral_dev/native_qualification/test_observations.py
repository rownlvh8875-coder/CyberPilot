"""Opt-in only: actual native assumptions at our controlled message boundary."""

import json
import unittest
from pathlib import Path


class NativeObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(Path('OBSERVATIONS.json').read_bytes())

    def test_binary32_point_three_is_observed_not_binary64_identity(self):
        row = next(r for r in self.data['float32'] if r['id'] == 'point_three')
        self.assertEqual(row['assigned']['hex'], '0x1.3333333333333p-2')
        self.assertEqual(row['builder']['hex'], '0x1.3333340000000p-2')
        self.assertEqual(row['reader'], row['builder'])
        self.assertEqual(row['builder']['type'], 'builtins.float')

    def test_signed_zero_survives_owned_serialization(self):
        row = next(r for r in self.data['float32'] if r['id'] == 'negative_zero')
        self.assertEqual(row['reader']['hex'], '-0x0.0p+0')

    def test_default_wire_is_not_field_supply_proof(self):
        row = self.data['defaults']
        self.assertEqual(row['omitted']['torque']['hex'], '0x0.0p+0')
        self.assertIs(row['omitted']['latActive'], False)
        self.assertEqual(row['omitted']['wire_sha256'], row['explicit']['wire_sha256'])
        self.assertNotEqual(row['omitted']['written_fields'], row['explicit']['written_fields'])
        self.assertEqual(row['presence_authority'], 'CONTROLLED_CONSTRUCTION_LEDGER_REQUIRED')

    def test_generic_native_class_does_not_identify_schema(self):
        row = self.data['types']
        self.assertEqual(row['cc_builder_type'], row['cs_builder_type'])
        self.assertNotEqual(row['cc_schema_id'], row['cs_schema_id'])
        self.assertEqual(row['cc_schema_id'], row['cc_reader_schema_id'])
        self.assertEqual(row['cs_schema_id'], row['cs_reader_schema_id'])

    def test_nonfinite_and_overflow_are_observations_not_json_numbers(self):
        rows = {r['id']: r for r in self.data['float32']}
        self.assertEqual(rows['nan']['reader']['hex'], 'nan')
        self.assertEqual(rows['positive_infinity']['reader']['hex'], 'inf')
        self.assertEqual(rows['negative_infinity']['reader']['hex'], '-inf')
        self.assertIn('overflow', rows)
        # The assignment may reject or overflow to infinity; neither is model acceptance.
        overflow = rows['overflow']
        self.assertTrue('exception' in overflow or overflow['reader']['hex'] == 'inf')

    def test_no_reader_activation_or_custody_claim(self):
        self.assertEqual(self.data['qualification']['Q05'], 'NOT_QUALIFIED')
        self.assertEqual(self.data['qualification']['Q06'], 'NOT_IMPLEMENTED_READER_BLOCKED')
        self.assertEqual(self.data['lifetime']['after_context_access'], 'NOT_PROBED_UNSAFE')
        self.assertEqual(self.data['native_reader_activation'], 'NOT_ALLOWED')
        self.assertEqual(self.data['forbidden_modules_loaded'], [])


if __name__ == '__main__':
    unittest.main()
