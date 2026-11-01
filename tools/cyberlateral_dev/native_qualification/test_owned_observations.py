"""Literal independent assertions on the closed R20 native demonstration output."""

import json
import unittest
from pathlib import Path


class OwnedObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(Path('OBSERVATIONS.json').read_bytes())

    def test_four_closed_frames_with_structural_only_claims(self):
        self.assertEqual([r['id'] for r in self.data['cases']], ['explicit_zero', 'rounded_point_three', 'negative_zero', 'resumed_declaration'])
        for row in self.data['cases']:
            self.assertEqual(row['custody_claim'], 'STRUCTURAL_SYNTHETIC_DECLARATION_ONLY')
            self.assertEqual(row['precision_claim'], 'OPAQUE_OWNED_WIRE_BYTES_NO_DECODE')
            self.assertEqual(row['time_semantics'], 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME')

    def test_exact_native_rounding_and_signed_zero(self):
        rows = {r['id']: r for r in self.data['cases']}
        self.assertEqual(rows['rounded_point_three']['owned_before']['torque']['hex'], '0x1.3333340000000p-2')
        self.assertEqual(rows['negative_zero']['owned_before']['torque']['hex'], '-0x0.0p+0')
        self.assertEqual(rows['explicit_zero']['owned_before']['torque']['hex'], '0x0.0p+0')
        self.assertIs(rows['explicit_zero']['owned_before']['latActive'], False)

    def test_mutating_both_builders_cannot_change_owned_snapshot(self):
        for row in self.data['cases']:
            self.assertEqual(row['owned_before'], row['owned_after'])
            self.assertNotEqual(row['builder_after'], row['owned_before'])
            self.assertTrue(row['payload_hashes_unchanged'])
            self.assertEqual(row['builder_after']['torque']['hex'], '-0x1.0000000000000p+0')
            self.assertEqual(row['builder_after']['steeringTorque']['hex'], '-0x1.0000000000000p+2')

    def test_default_wire_equality_does_not_fill_missing_ledger(self):
        row = self.data['default_ambiguity']
        self.assertTrue(row['wire_equal'])
        self.assertEqual(row['omitted_wire_sha256'], row['explicit_wire_sha256'])
        self.assertEqual(row['missing_ledger_rejection'], 'OWNED_FIELD_LEDGER')

    def test_cross_frame_schema_state_payload_and_ledger_rejections(self):
        self.assertEqual(self.data['rejections'], {
            'missing_ledger': 'OWNED_FIELD_LEDGER', 'wrong_schema': 'OWNED_SCHEMA', 'crossed_settings': 'OWNED_STAMP',
            'crossed_previous': 'OWNED_STAMP', 'mutated_payload': 'OWNED_PAYLOAD', 'mutable_payload': 'OWNED_PAYLOAD',
            'wrong_previous_index': 'OWNED_PREVIOUS', 'source_model_state_mismatch': 'OWNED_PREVIOUS', 'wrong_stage': 'OWNED_PREVIOUS',
        })
        prior = self.data['cases'][3]['previous']
        self.assertEqual((prior['previous_applied'], prior['previous_requested'], prior['angle_counter']), (3, 5, 1))
        self.assertEqual(prior['origin'], 'EXPLICIT_SYNTHETIC_DECLARATION_NOT_REPLAY_VALIDATED')

    def test_no_native_reader_model_or_actual_activation(self):
        self.assertEqual(self.data['native_reader'], 'NOT_IMPLEMENTED')
        self.assertEqual(self.data['actual_call_custody'], 'NOT_QUALIFIED')
        self.assertEqual(self.data['model_execution'], 0)
        self.assertEqual(self.data['forbidden_modules_loaded'], [])
        self.assertEqual(self.data['repository_import_cache_policy'], 'PRIVATE_EMPTY_PREFIX_NO_WRITES')


if __name__ == '__main__':
    unittest.main()
