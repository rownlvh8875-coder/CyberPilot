"""Closed boundary fixtures and full-output reference audit, not vehicle tests."""

import importlib
import sys
import unittest
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT, package_feature

CASES = ('inactive-resume', 'fault-reset', 'rounding-ties')


class BoundaryCaseTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_boundary_cases.py').is_file(), 'Missing CORE31 boundary factory')
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        package_feature()
        self.m: Any = importlib.import_module('integration_tools.core_boundary_cases')

    def test_inactive_resume_preserves_distinct_gate_and_state_roles(self):
        frames, contexts = self.m.build_boundary_case('inactive-resume')
        self.assertEqual([f.inactive_gate_active for f in frames], [True, False, True, True])
        self.assertEqual([f.request.request_active for f in frames], [True, False, True, True])
        self.assertEqual([f.saved_limited_state for f in frames], [-2, 0, -2, 2])
        self.assertEqual([f.saved_angle_counter for f in frames], [4, 0, 1, 2])
        self.assertEqual([c.previous_integer_request for c in contexts], [-4, 8, -8])

    def test_fault_counter_crosses_threshold_reset_and_recovery(self):
        frames, contexts = self.m.build_boundary_case('fault-reset')
        self.assertEqual([f.saved_angle_counter for f in frames], [88, 89, 90, 0, 1])
        self.assertEqual([f.saved_limited_state for f in frames], [-2, 2, -2, 2, -2])
        self.assertEqual([c.model_index for c in contexts], [5, 6, 7, 8]); self.assertTrue(all(c.current_angle_deg == 85.0 for c in contexts))

    def test_rounding_words_keep_both_zero_signs_and_explicit_previous_requests(self):
        frames, contexts = self.m.build_boundary_case('rounding-ties')
        self.assertEqual([f.request.requested_binary32.hex() for f in frames], ['00000000', '3d000000', '3dc00000', 'bd000000', 'bdc00000', '00000000', '80000000'])
        self.assertEqual([c.previous_integer_request for c in contexts], [0, 0, 2, 0, -2, 0])
        self.assertEqual([f.saved_limited_state for f in frames], [0, 0, 2, 0, -2, 0, 0])
        self.assertTrue(all(type(c.current_angle_deg) is float and c.current_angle_deg == 0.0 for c in contexts))

    def test_foreign_case_precedes_original_catalog_access(self):
        class Foreign(str): pass
        original = importlib.import_module('integration_tools.core_sequence_cases')
        for case in ('', 'sign-cycle', None, 1, True, Foreign('fault-reset')):
            with self.subTest(case=case), patch.object(original, 'build_case', side_effect=AssertionError('catalog')), self.assertRaises(ValueError) as found: self.m.build_boundary_case(case)
            self.assertEqual(str(found.exception), 'BOUNDARY_CASE')

    def test_factory_invokes_no_model_or_quantizer(self):
        calls = []; previous = sys.getprofile()
        def profile(frame, event, arg):
            if event == 'call' and frame.f_code.co_name in ('quantize', 'step', 'rollout_synthetic_sequence', 'prepare_model_input'): calls.append(frame.f_code.co_name)
        try:
            sys.setprofile(profile)
            for case in CASES: self.m.build_boundary_case(case)
        finally: sys.setprofile(previous)
        self.assertEqual(calls, [])

    def test_declared_pairs_link_without_shared_mutable_case_objects(self):
        for case in CASES:
            frames, contexts = self.m.build_boundary_case(case); other, _ = self.m.build_boundary_case(case)
            self.assertIs(type(frames), tuple); self.assertIs(type(contexts), tuple); self.assertEqual(frames, other); self.assertIsNot(frames[0], other[0])
            for before, after in zip(frames, frames[1:], strict=False):
                self.assertEqual((before.saved_limited_state, before.saved_angle_counter), (after.limited_state_at_entry, after.angle_counter_at_entry))
                self.assertEqual(after.request.sequence, before.request.sequence + 1)
                self.assertGreater(after.request.sample_time_ns, before.request.sample_time_ns)

    def test_input_record_uses_new_contract_and_lossless_representation(self):
        frames, contexts = self.m.build_boundary_case('rounding-ties')
        record = self.m.input_record('rounding-ties', frames, contexts)
        self.assertEqual(record['contract_id'], 'CORE31_CLOSED_BOUNDARY_INPUT_V1')
        self.assertEqual(record['frames'][-1]['request']['requested_binary32_be_hex'], '80000000')
        self.assertNotIn('requested_binary32', record['frames'][-1]['request'])

    def test_original_catalog_is_not_mutated_by_new_cases(self):
        original = importlib.import_module('integration_tools.core_sequence_cases')
        frames, contexts = original.build_case('sign-cycle')
        for case in CASES: self.m.build_boundary_case(case)
        self.assertEqual(original.build_case('sign-cycle'), (frames, contexts))
        self.assertEqual(original.CASE_IDS, ('sign-cycle', 'declared-difference', 'late-invalid'))
