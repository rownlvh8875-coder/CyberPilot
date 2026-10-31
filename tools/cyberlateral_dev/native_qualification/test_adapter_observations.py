"""Independent data-only assertions on exported R28 observations."""

import json
import os
import unittest
from pathlib import Path


class AdapterObservationsTests(unittest.TestCase):
    def data(self):
        return json.loads(Path(os.environ['R28_OBSERVATIONS']).read_bytes())

    def test_hand_derived_literal_records(self):
        self.assertEqual(self.data()['checks']['records'], [
            {'id': 'literal', 'request_hex': '0x1.0000000000000p-2', 'state': [0, None, 0, 0]},
            {'id': 'negative_zero', 'hex': '-0x0.0p+0'},
            {'id': 'promoted_point_three', 'hex': '0x1.3333340000000p-2'},
            {'id': 'resumed', 'state': [1, 5, 3, 1]},
            {'id': 'subnormal', 'hex': '0x1.0000000000000p-149'},
        ])

    def test_native_and_close_checks_pass(self):
        row = self.data()
        self.assertEqual((row['checks']['tests_run'], row['checks']['failures'], row['checks']['errors'], row['closed_context_checks']), (15, 0, 0, 3))

    def test_actual_authority_not_promoted(self):
        row = self.data()
        self.assertEqual((row['scope'], row['actual_custody'], row['generic_external_reader'], row['actual_input']),
                         ('INTERNAL_SYNTHETIC_MESSAGES_ONLY', 'NOT_QUALIFIED', 'NOT_IMPLEMENTED', 'NOT_ALLOWED'))
        self.assertEqual((row['R_BUDGET'], row['STATIC_EVIDENCE_GATE']), ('UNRESOLVED', 'FAIL'))
        self.assertEqual([row[name] for name in ['model_execution', 'F61_execution', 'r_calculation', 'dt_calculation']], [0, 0, 0, 0])
