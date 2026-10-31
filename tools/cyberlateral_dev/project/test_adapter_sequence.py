"""R29 closed gate: invalid preparation cannot cause a model step."""

import importlib
import sys
import unittest
from dataclasses import replace
from unittest.mock import patch

from v1_helpers import ROOT, package_feature


class AdapterSequenceTests(unittest.TestCase):
    def modules(self):
        self.assertTrue((ROOT / 'integration_tools/adapter_sequence.py').is_file(), 'Missing R29 sequence')
        p = package_feature()
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.adapter_sequence'), p

    def prepared(self, p, index=0):
        from integration_tools.native_adapter import PreparedNativeInput
        from integration_tools.owned_message_boundary import Stamp
        from integration_tools.semantic_types import PreparedSemanticInput
        from integration_tools.sequence_reference import expected_input
        fixture = expected_input(index)
        sample, state = fixture['sample'], fixture['state']
        prepared = PreparedSemanticInput(
            'F70UGZ_R21_SYNTHETIC_SEMANTIC_BRIDGE_V1', Stamp('R29_SIGN_CHANGE_4', index, 'entry_' + str(index)),
            p.LateralInput(index, float.fromhex(sample['request_hex']), 0.0, 0.0, sample['lat_active'], p.Limits(16, 2, 5, 7, 1, 3), 'SYNTHETIC_ONLY'),
            p.LateralState(**state), 'DECLARED_READBACK_BINDING_NOT_AUTHENTICATED_NATIVE_CUSTODY',
            'EXACT_SUPPLIED_FLOAT32_PROMOTED_TO_PYTHON_FLOAT', 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME')
        return PreparedNativeInput(prepared, 'INTERNALLY_CONSTRUCTED_OWNED_SYNTHETIC_BYTES_READ_WITHIN_CONTEXT')

    def test_exact_first_step_matches_literal_not_current_request_alias(self):
        m, p = self.modules()
        output = m.consume_prepared('SIGN_CHANGE_4', 0, self.prepared(p))
        self.assertEqual(output.next_state, p.LateralState(1, 5, 2, 0))
        self.assertEqual(output.projection.integer_command, 2)

    def test_only_registered_profiles_and_exact_indices(self):
        m, p = self.modules()
        self.assertEqual([m.profile_count(name) for name in ['SIGN_CHANGE_4', 'NEGATIVE_CYCLE_99']], [4, 99])
        with patch.object(p, 'step', side_effect=AssertionError('No invalid step')):
            for profile in ['UNKNOWN', '', None, True]:
                with self.assertRaisesRegex(m.SequenceError, 'CHAIN_PROFILE'):
                    m.consume_prepared(profile, 0, self.prepared(p))
            for index in [-1, 4, True, 0.0]:
                with self.assertRaisesRegex(m.SequenceError, 'CHAIN_INDEX'):
                    m.consume_prepared('SIGN_CHANGE_4', index, self.prepared(p))

    def test_wrong_type_and_metadata_reject_before_step(self):
        m, p = self.modules()
        record = self.prepared(p)
        with patch.object(p, 'step', side_effect=AssertionError('No invalid step')):
            for changed in [None, record.prepared, replace(record, read_claim='ACTUAL'),
                            replace(record, prepared=replace(record.prepared, custody_claim='AUTHENTICATED')),
                            replace(record, prepared=replace(record.prepared, precision_claim='ROUNDED')),
                            replace(record, prepared=replace(record.prepared, time_semantics='ACTUAL_SECONDS'))]:
                with self.assertRaisesRegex(m.SequenceError, 'CHAIN_PREPARATION'):
                    m.consume_prepared('SIGN_CHANGE_4', 0, changed)

    def test_wrong_stamp_rejects_before_step(self):
        m, p = self.modules()
        record = self.prepared(p)
        with patch.object(p, 'step', side_effect=AssertionError('No invalid step')):
            for stamp in [replace(record.prepared.stamp, sequence_id='OTHER'), replace(record.prepared.stamp, invocation_index=True),
                          replace(record.prepared.stamp, capture_id='entry_1')]:
                with self.assertRaisesRegex(m.SequenceError, 'CHAIN_STAMP'):
                    m.consume_prepared('SIGN_CHANGE_4', 0, replace(record, prepared=replace(record.prepared, stamp=stamp)))

    def test_incorrect_previous_state_rejects_before_step(self):
        m, p = self.modules()
        from integration_tools.model_consumption import ConsumptionError
        record = self.prepared(p, 1)
        with patch.object(p, 'step', side_effect=AssertionError('No invalid step')):
            for state in [replace(record.prepared.state, previous_requested=2), replace(record.prepared.state, previous_applied=5),
                          replace(record.prepared.state, angle_counter=1), replace(record.prepared.state, index=0)]:
                with self.assertRaisesRegex(ConsumptionError, 'SEQUENCE_INPUT_MISMATCH'):
                    m.consume_prepared('SIGN_CHANGE_4', 1, replace(record, prepared=replace(record.prepared, state=state)))

    def test_changed_request_or_settings_rejects_before_step(self):
        m, p = self.modules()
        from integration_tools.model_consumption import ConsumptionError
        record = self.prepared(p)
        with patch.object(p, 'step', side_effect=AssertionError('No invalid step')):
            for sample in [replace(record.prepared.sample, request=0.3), replace(record.prepared.sample, driver=1.5),
                           replace(record.prepared.sample, limits=p.Limits(32, 2, 5, 7, 1, 3))]:
                with self.assertRaisesRegex(ConsumptionError, 'SEQUENCE_INPUT_MISMATCH'):
                    m.consume_prepared('SIGN_CHANGE_4', 0, replace(record, prepared=replace(record.prepared, sample=sample)))

    def test_corrupt_model_output_fails_closed_without_retry(self):
        m, p = self.modules()
        from integration_tools.model_consumption import ConsumptionError
        original = p.step
        calls = []
        def corrupt(sample, state):
            calls.append(sample.index)
            output = original(sample, state)
            return replace(output, next_state=replace(output.next_state, previous_applied=7))
        with patch.object(p, 'step', side_effect=corrupt), self.assertRaisesRegex(ConsumptionError, 'SEQUENCE_OUTPUT_MISMATCH'):
            m.consume_prepared('SIGN_CHANGE_4', 0, self.prepared(p))
        self.assertEqual(calls, [0])

    def test_unowned_adapter_rejects_before_native_or_model_work(self):
        m, p = self.modules()
        with patch.object(p, 'step', side_effect=AssertionError('No invalid step')):
            with self.assertRaisesRegex(m.SequenceError, 'CHAIN_ADAPTER_TYPE'):
                m.run_registered_sequence(None, 'SIGN_CHANGE_4')
