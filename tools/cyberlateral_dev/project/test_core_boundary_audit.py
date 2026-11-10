"""Closed boundary fixtures and full-output reference audit, not vehicle tests."""

import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
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


class BoundaryAuditTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_boundary_audit.py').is_file(), 'Missing CORE31 boundary audit API')
        self.model = package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.core_boundary_audit')
        self.ref: Any = importlib.import_module('integration_tools.boundary_reference')

    def audit(self, case='inactive-resume'): return self.m.audit_boundary_case(case)
    def reject(self, code, case='inactive-resume'):
        with self.assertRaises(self.m.BoundaryAuditError) as found: self.audit(case)
        self.assertEqual((found.exception.code, str(found.exception)), (code, code))
    def mutated(self, change, case='inactive-resume'):
        original = self.model.step
        with patch.object(self.model, 'step', side_effect=lambda sample, state: change(original(sample, state))): return self.audit(case)

    def test_three_boundaries_match_full_reference_with_explicit_model_counts(self):
        for case, steps in zip(CASES, (3, 4, 6), strict=True):
            calls = {'model': 0, 'quantize': 0, 'rollout': 0}; previous = sys.getprofile()
            def profile(frame, event, arg, counts=calls):
                table = {('cyberlateral_dev.api', 'step'): 'model', ('cyberlateral_dev._r4.request_quantizer', 'quantize'): 'quantize',
                         ('integration_tools.synthetic_sequence_rollout', 'rollout_synthetic_sequence'): 'rollout'}
                key = frame.f_globals.get('__name__'), frame.f_code.co_name
                if event == 'call' and key in table: counts[table[key]] += 1
            try: sys.setprofile(profile); r = self.audit(case)
            finally: sys.setprofile(previous)
            self.assertEqual((r['audit_status'], r['audit_exit_code'], r['difference_count']), ('CLOSED_BOUNDARY_REFERENCE_MATCH', 0, 0))
            self.assertEqual((r['observed_rollout_status'], r['synthetic_model_steps']), ('MATCH', steps))
            self.assertEqual(calls, {'model': steps, 'quantize': steps * 2, 'rollout': 1})

    def test_inactive_expected_distinguishes_limited_final_and_resumed_entry(self):
        rows = self.ref.expected_boundary('inactive-resume')['steps']
        self.assertEqual([r['output']['trace']['downstream']['limited_command'] for r in rows], [2, -2, 2])
        self.assertEqual([r['output']['projection']['integer_command'] for r in rows], [0, -2, 2])
        self.assertEqual([r['entry_state']['previous_applied'] for r in rows], [-2, 0, -2])
        self.assertEqual([r['output']['next_state']['angle_counter'] for r in rows], [0, 1, 2])

    def test_fault_false_request_does_not_zero_active_command(self):
        rows = self.ref.expected_boundary('fault-reset')['steps']
        self.assertEqual([r['output']['next_state']['angle_counter'] for r in rows], [89, 90, 0, 1])
        self.assertEqual([r['output']['steer_request'] for r in rows], [True, False, False, True])
        self.assertEqual([r['output']['trace']['downstream']['final_command'] for r in rows], [2, -2, 2, -2])

    def test_rounding_half_ties_and_input_output_zero_signs(self):
        rows = self.ref.expected_boundary('rounding-ties')['steps']
        self.assertEqual([r['output']['trace']['quantization']['integer_command'] for r in rows], [0, 2, 0, -2, 0, 0])
        self.assertEqual(rows[-1]['output']['trace']['quantization']['product_hex'], '-0x0.0p+0')
        self.assertEqual(rows[-1]['output']['projection']['normalized_expression'].hex(), '0x0.0p+0')
        self.assertEqual(rows[-1]['output']['projection']['torque_float32']['bits_hex'], '00000000')

    def test_foreign_case_rejects_before_reference_and_factory(self):
        class Foreign(str): pass
        for case in ('sign-cycle', '', True, None, Foreign('fault-reset')):
            with self.subTest(case=case), patch.object(self.ref, 'load_reference', side_effect=AssertionError('read')), patch.object(self.m, 'build_boundary_case', side_effect=AssertionError('factory')): self.reject('BOUNDARY_AUDIT_CASE', case)

    def test_reference_failure_precedes_factory(self):
        with patch.object(self.ref, 'load_reference', side_effect=ValueError('PRIVATE')), patch.object(self.m, 'build_boundary_case', side_effect=AssertionError('factory')): self.reject('BOUNDARY_AUDIT_REFERENCE')

    def test_catalog_drift_rejects_before_rollout(self):
        original = self.m.build_boundary_case
        def changed(case):
            frames, contexts = original(case); return frames, (replace(contexts[0], current_angle_deg=84.0), *contexts[1:])
        with patch.object(self.m, 'build_boundary_case', side_effect=changed), patch.object(self.m, 'rollout_synthetic_sequence', side_effect=AssertionError('model')): self.reject('BOUNDARY_AUDIT_INPUT_IDENTITY')

    def test_reference_foreign_case_precedes_file_read(self):
        with patch.object(self.ref, 'load_reference', side_effect=AssertionError('read')), self.assertRaises(ValueError) as found: self.ref.expected_boundary('sign-cycle')
        self.assertEqual(str(found.exception), 'BOUNDARY_REFERENCE_CASE')

    def test_reference_hash_checked_before_decode(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'ref.json'; raw = self.ref.REFERENCE_PATH.read_bytes(); p.write_bytes(b'!' + raw[1:])
            with patch.object(self.ref, 'REFERENCE_PATH', p), patch('json.loads', side_effect=AssertionError('parse')), self.assertRaises(ValueError) as found: self.ref.load_reference()
        self.assertEqual(str(found.exception), 'BOUNDARY_REFERENCE_IDENTITY')

    def test_reference_oversize_and_symlink_are_not_followed(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'ref.json'; p.write_bytes(self.ref.REFERENCE_PATH.read_bytes() + b'x')
            with patch.object(self.ref, 'REFERENCE_PATH', p), patch('os.read', side_effect=AssertionError('read')), self.assertRaises(ValueError): self.ref.load_reference()
            p.unlink(); p.symlink_to(self.ref.REFERENCE_PATH)
            with patch.object(self.ref, 'REFERENCE_PATH', p), self.assertRaises(ValueError): self.ref.load_reference()

    def test_reference_assembly_cold_imports_no_target_or_quantizer(self):
        code = r'''
import importlib.abc, sys
sys.path.insert(0, sys.argv[1])
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('cyberlateral_dev', 'integration_tools.synthetic_', 'integration_tools.core_rollout_run', 'integration_tools.core_boundary_cases', 'integration_tools.core_boundary_audit')): raise AssertionError(fullname)
sys.meta_path.insert(0, Block())
from integration_tools.boundary_reference import expected_boundary
assert expected_boundary('fault-reset')['steps'][2]['output']['steer_request'] is False
assert expected_boundary('rounding-ties')['steps'][-1]['output']['trace']['quantization']['product_hex'] == '-0x0.0p+0'
print('BOUNDARY_REFERENCE_MODEL_FREE')
'''
        r = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(ROOT)], capture_output=True)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, b'BOUNDARY_REFERENCE_MODEL_FREE\n', b''))

    def test_expected_records_do_not_share_mutable_truth(self):
        first = self.ref.expected_boundary('fault-reset'); first['steps'][0]['output']['next_state']['angle_counter'] = 0
        self.assertEqual(self.ref.expected_boundary('fault-reset')['steps'][0]['output']['next_state']['angle_counter'], 89)

    def test_pre_gate_instead_of_post_gate_state_feed_is_detected(self):
        def changed(o):
            d = o.trace.downstream
            return replace(o, next_state=replace(o.next_state, previous_applied=d.limited_command)) if d.final_command == 0 and d.limited_command != 0 else o
        r = self.mutated(changed); self.assertEqual(r['audit_exit_code'], 1)
        self.assertIn('/steps/1/entry_state/previous_applied', r['difference_paths'])

    def test_using_fault_request_to_zero_torque_is_detected(self):
        r = self.mutated(lambda o: replace(o, projection=replace(o.projection, integer_command=0)) if not o.steer_request else o, 'fault-reset')
        self.assertEqual(r['difference_paths'], ['/steps/1/output/projection/integer_command', '/steps/2/output/projection/integer_command'])

    def test_wrong_fault_request_toggle_is_detected(self):
        r = self.mutated(lambda o: replace(o, steer_request=True), 'fault-reset')
        self.assertEqual(r['difference_count'], 2); self.assertIn('/steps/2/output/steer_request', r['difference_paths'])

    def test_negative_output_zero_is_not_equal_to_expected_positive_zero(self):
        r = self.mutated(lambda o: replace(o, projection=replace(o.projection, normalized_expression=-0.0)) if o.projection.integer_command == 0 else o, 'rounding-ties')
        self.assertEqual(r['difference_paths'], ['/steps/' + str(i) + '/output/projection/normalized_expression' for i in (0, 2, 4, 5)])

    def test_lost_negative_zero_request_product_is_detected(self):
        def changed(o):
            q = o.trace.quantization
            return replace(o, trace=replace(o.trace, quantization=replace(q, request_hex='0x0.0p+0', product_hex='0x0.0p+0'))) if q.product_hex == '-0x0.0p+0' else o
        r = self.mutated(changed, 'rounding-ties'); self.assertEqual(r['difference_count'], 2)
        self.assertIn('/steps/5/output/trace/quantization/product_hex', r['difference_paths'])

    def test_bool_and_integer_quantization_are_not_conflated(self):
        r = self.mutated(lambda o: replace(o, trace=replace(o.trace, quantization=replace(o.trace.quantization, integer_command=True))), 'rounding-ties')
        self.assertEqual(r['difference_count'], 6)

    def test_clip_only_corruption_is_detected(self):
        def changed(o):
            d = o.trace.downstream
            return replace(o, trace=replace(o.trace, downstream=replace(d, rate_clip=replace(d.rate_clip, lower=replace(d.rate_clip.lower, value=-99)))))
        r = self.mutated(changed, 'fault-reset'); self.assertEqual(r['difference_count'], 4)

    def test_preflight_failure_is_never_expected_rejection(self):
        with patch.object(self.m, 'rollout_synthetic_sequence', side_effect=ValueError('PRIVATE')): self.reject('BOUNDARY_AUDIT_EXECUTION_FAILED_WORK_MAY_BE_NONZERO')

    def test_prefix_model_failure_never_claims_zero_work(self):
        original = self.model.step; calls = 0
        def step(sample, state):
            nonlocal calls
            calls += 1
            if calls == 2: raise ValueError('PRIVATE')
            return original(sample, state)
        with patch.object(self.model, 'step', side_effect=step): self.reject('BOUNDARY_AUDIT_EXECUTION_FAILED_WORK_MAY_BE_NONZERO')
        self.assertEqual(calls, 2)

    def test_malformed_result_is_not_partial_success(self):
        with patch.object(self.m, 'rollout_synthetic_sequence', return_value=None): self.reject('BOUNDARY_AUDIT_RESULT_FAILED_WORK_MAY_BE_NONZERO')

    def test_baseexception_propagates(self):
        with patch.object(self.m, 'rollout_synthetic_sequence', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt): self.audit()

    def test_differences_count_all_and_report_first_256(self):
        original = self.m._observe
        with patch.object(self.m, '_observe', side_effect=lambda result: {**original(result), **{str(i): i for i in range(300)}}): r = self.audit()
        self.assertEqual((r['difference_count'], r['reported_difference_count'], r['differences_truncated']), (300, 256, True))

    def test_canonical_repeat_receipts_match(self):
        from integration_tools.scenario_output import canonical
        left, right = self.audit('rounding-ties'), self.audit('rounding-ties')
        self.assertEqual(canonical(left), canonical(right)); self.assertEqual(json.loads(canonical(left)), left)

    def test_audit_writes_no_output_or_temp_files(self):
        original = os.open
        def opening(path, flags, *a, **kw):
            self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY); return original(path, flags, *a, **kw)
        with patch('os.open', side_effect=opening), patch('os.mkdir', side_effect=AssertionError('mkdir')), patch('tempfile.gettempdir', side_effect=AssertionError('temp')): self.assertEqual(self.audit()['audit_exit_code'], 0)

    def test_receipt_denies_source_vehicle_and_generic_authority(self):
        r = self.audit()
        for name in ('source_identity_reauthenticated', 'prehistory_checked', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'): self.assertIs(r[name], False)
        self.assertEqual((r['gates']['R_BUDGET'], r['gates']['STATIC_EVIDENCE_GATE']), ('UNRESOLVED', 'FAIL'))
        self.assertEqual(r['expected_reference_model_steps'], 0)
        self.assertEqual(r['numeric_preflight_work'], 'NONZERO_NOT_AGGREGATED')

    def test_core30_contract_and_cases_stay_unchanged(self):
        old = importlib.import_module('integration_tools.core_rollout_audit')
        self.audit('fault-reset')
        for case, status in (('sign-cycle', 'MATCH'), ('declared-difference', 'DIFFERENT'), ('late-invalid', 'REJECTED')):
            r = old.audit_rollout_case(case); self.assertEqual((r['contract_id'], r['observed_rollout_status'], r['audit_exit_code']), ('CORE30_CLOSED_ROLLOUT_REFERENCE_AUDIT_V1', status, 0))
