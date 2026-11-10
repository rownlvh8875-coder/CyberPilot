"""Closed reference audit must detect full-output and chain-only corruptions."""

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

CASES = ('sign-cycle', 'declared-difference', 'late-invalid')


class CoreRolloutAuditTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_rollout_audit.py').is_file(), 'Missing CORE30 full-output reference audit')
        self.model = package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.core_rollout_audit')
        self.ref: Any = importlib.import_module('integration_tools.rollout_reference')

    def audit(self, case='sign-cycle'): return self.m.audit_rollout_case(case)
    def profiled(self, call):
        old = sys.getprofile(); counts = {'model': 0, 'quantize': 0, 'rollout': 0}
        def profile(frame, event, arg):
            key = frame.f_globals.get('__name__'), frame.f_code.co_name
            table = {('cyberlateral_dev.api', 'step'): 'model', ('cyberlateral_dev._r4.request_quantizer', 'quantize'): 'quantize',
                ('integration_tools.synthetic_sequence_rollout', 'rollout_synthetic_sequence'): 'rollout'}
            if event == 'call' and key in table: counts[table[key]] += 1
        try: sys.setprofile(profile); result = call()
        finally: sys.setprofile(old)
        return result, counts
    def reject(self, code, case='sign-cycle'):
        with self.assertRaises(self.m.RolloutAuditError) as found: self.audit(case)
        self.assertEqual((found.exception.code, str(found.exception)), (code, code))
    def mutated_step(self, change):
        original = self.model.step
        with patch.object(self.model, 'step', side_effect=lambda sample, state: change(original(sample, state))): return self.audit()

    def test_all_cases_match_reference_independent_of_rollout_status(self):
        for case, status, code, steps, quantizers in zip(CASES, ('MATCH', 'DIFFERENT', 'REJECTED'), (0, 1, 2), (3, 3, 0), (6, 6, 2), strict=True):
            with self.subTest(case=case):
                r, calls = self.profiled(lambda c=case: self.audit(c))
                self.assertEqual((r['audit_status'], r['audit_exit_code'], r['difference_count']), ('CLOSED_REFERENCE_MATCH', 0, 0))
                self.assertEqual((r['observed_rollout_status'], r['observed_rollout_exit_code'], r['synthetic_model_steps']), (status, code, steps))
                self.assertEqual(calls, {'model': steps, 'quantize': quantizers, 'rollout': 1})

    def test_hand_vectors_contain_exact_full_projection_clip_and_chain_values(self):
        r = self.ref.expected_rollout('sign-cycle'); rows = r['steps']
        self.assertEqual([s['entry_state']['previous_applied'] for s in rows], [-2, 2, -2])
        self.assertEqual([s['output']['next_state']['previous_applied'] for s in rows], [2, -2, 2])
        self.assertEqual([s['output']['trace']['downstream']['rate_clip']['lower']['value'] for s in rows], [-4, -2, -4])
        self.assertEqual([s['output']['projection']['torque_float32']['bits_hex'] for s in rows], ['3e000000', 'be000000', '3e000000'])
        self.assertEqual([s['output']['trace']['quantization']['integer_command'] for s in rows], [8, -8, 4])
        self.assertEqual([s['output']['trace']['downstream']['fault_condition'] for s in rows], [True] * 3)

    def test_declared_differences_do_not_turn_reference_audit_into_failure(self):
        r = self.ref.expected_rollout('declared-difference')
        self.assertEqual((r['entry_differing_transition_indices'], r['output_differing_transition_indices']), ([1, 2], [0, 1, 2]))
        self.assertEqual([s['declared_entry_state']['previous_applied'] for s in r['steps']], [-2, 10, 5])
        self.assertEqual(r['steps'][1]['entry_differences'], [{'field': 'entry_previous_applied', 'declared': 10, 'computed': 2}])
        self.assertEqual(self.audit('declared-difference')['difference_paths'], [])

    def test_expected_late_rejection_retains_exact_code_and_zero_model_not_zero_validation(self):
        r = self.audit('late-invalid')
        self.assertEqual(r['observed_rejection_code'], 'ROLLOUT_INPUT:2:MODEL_DRIVER')
        self.assertEqual(r['synthetic_model_steps'], 0); self.assertEqual(r['numeric_preflight_work'], 'NONZERO_NOT_AGGREGATED')

    def test_foreign_cases_rejected_before_reference_catalog_or_model(self):
        class Foreign(str): pass
        for case in ('', 'other', 0, None, True, Foreign('sign-cycle')):
            with self.subTest(case=case), patch.object(self.ref, 'load_reference', side_effect=AssertionError('reference')), patch.object(self.m, 'build_case', side_effect=AssertionError('catalog')): self.reject('ROLLOUT_AUDIT_CASE', case)

    def test_reference_failure_precedes_catalog_and_model(self):
        with patch.object(self.ref, 'load_reference', side_effect=ValueError('PRIVATE')), patch.object(self.m, 'build_case', side_effect=AssertionError('catalog')): self.reject('ROLLOUT_AUDIT_REFERENCE')

    def test_reference_foreign_case_rejected_before_reference_read(self):
        with patch.object(self.ref, 'load_reference', side_effect=AssertionError('read')), self.assertRaises(ValueError) as found: self.ref.expected_rollout('other')
        self.assertEqual(str(found.exception), 'ROLLOUT_REFERENCE_CASE')

    def test_reference_hash_is_checked_before_json_decode(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'ref.json'; raw = self.ref.REFERENCE_PATH.read_bytes(); p.write_bytes(b'!' + raw[1:])
            with patch.object(self.ref, 'REFERENCE_PATH', p), patch('json.loads', side_effect=AssertionError('parse')), self.assertRaises(ValueError) as found: self.ref.load_reference()
        self.assertEqual(str(found.exception), 'ROLLOUT_REFERENCE_IDENTITY')

    def test_reference_capture_rejects_oversize_and_symlink(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'ref.json'; p.write_bytes(self.ref.REFERENCE_PATH.read_bytes() + b'x')
            with patch.object(self.ref, 'REFERENCE_PATH', p), patch('os.read', side_effect=AssertionError('read')), self.assertRaises(ValueError): self.ref.load_reference()
            p.unlink(); p.symlink_to(self.ref.REFERENCE_PATH)
            with patch.object(self.ref, 'REFERENCE_PATH', p), self.assertRaises(ValueError): self.ref.load_reference()

    def test_reference_assembly_is_cold_model_free(self):
        code = r'''
import importlib.abc, json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('cyberlateral_dev', 'integration_tools.synthetic_', 'integration_tools.core_rollout_run', 'integration_tools.core_rollout_audit')): raise AssertionError(fullname)
sys.meta_path.insert(0, Block())
from integration_tools.rollout_reference import expected_rollout
r = expected_rollout('sign-cycle')
assert r['steps'][1]['output']['projection']['normalized_expression'] == -0.125
assert 'cyberlateral_dev' not in sys.modules
print('MODEL_FREE_REFERENCE_PASS')
'''
        r = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(ROOT)], capture_output=True)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, b'MODEL_FREE_REFERENCE_PASS\n', b''))

    def test_reference_expected_calls_are_detached_not_mutable_shared_truth(self):
        first = self.ref.expected_rollout('sign-cycle'); first['steps'][0]['output']['next_state']['previous_applied'] = 99
        self.assertEqual(self.ref.expected_rollout('sign-cycle')['steps'][0]['output']['next_state']['previous_applied'], 2)

    def test_changed_catalog_blocks_before_rollout(self):
        original = self.m.build_case
        def changed(case):
            frames, contexts = original(case); return frames, (replace(contexts[0], current_angle_deg=84.0), *contexts[1:])
        with patch.object(self.m, 'build_case', side_effect=changed), patch.object(self.m, 'rollout_synthetic_sequence', side_effect=AssertionError('rollout')): self.reject('ROLLOUT_AUDIT_INPUT_IDENTITY')

    def test_projection_only_corruption_is_detected(self):
        r = self.mutated_step(lambda o: replace(o, projection=replace(o.projection, torque_float32=replace(o.projection.torque_float32, bits_hex='00000000'))))
        self.assertEqual((r['audit_status'], r['audit_exit_code'], r['difference_count']), ('CLOSED_REFERENCE_DIFFERENT', 1, 3))
        self.assertEqual(r['difference_paths'][0], '/steps/0/output/projection/torque_float32/bits_hex')

    def test_trace_only_clip_corruption_is_detected(self):
        def change(o):
            d = o.trace.downstream; clip = replace(d.rate_clip, lower=replace(d.rate_clip.lower, value=-99))
            return replace(o, trace=replace(o.trace, downstream=replace(d, rate_clip=clip)))
        r = self.mutated_step(change)
        self.assertEqual(r['difference_count'], 3); self.assertIn('/steps/2/output/trace/downstream/rate_clip/lower/value', r['difference_paths'])

    def test_fault_and_request_flags_are_independently_compared(self):
        def change(o): return replace(o, steer_request=False, trace=replace(o.trace, downstream=replace(o.trace.downstream, fault_condition=False)))
        r = self.mutated_step(change); self.assertEqual(r['difference_count'], 6)
        self.assertIn('/steps/0/output/steer_request', r['difference_paths'])

    def test_wrong_computed_state_feed_is_detected(self):
        r = self.mutated_step(lambda o: replace(o, next_state=replace(o.next_state, previous_applied=3)))
        self.assertEqual(r['audit_exit_code'], 1); self.assertIn('/steps/1/entry_state/previous_applied', r['difference_paths'])

    def test_changed_rollout_authority_metadata_is_detected_without_granting_it(self):
        original = self.m.rollout_synthetic_sequence
        def altered(frames, contexts):
            result = original(frames, contexts); object.__setattr__(result, 'actual_activation_allowed', True); return result
        with patch.object(self.m, 'rollout_synthetic_sequence', side_effect=altered): r = self.audit()
        self.assertEqual(r['difference_paths'], ['/actual_activation_allowed']); self.assertFalse(r['actual_activation_allowed'])

    def test_incorrect_difference_list_is_detected(self):
        original = self.m.rollout_synthetic_sequence
        def altered(frames, contexts):
            result = original(frames, contexts); object.__setattr__(result.steps[0], 'output_differences', ())
            return result
        with patch.object(self.m, 'rollout_synthetic_sequence', side_effect=altered): r = self.audit('declared-difference')
        self.assertIn('/steps/0/output_differences/0', r['difference_paths']); self.assertEqual(r['audit_exit_code'], 1)

    def test_boolean_does_not_equal_integer_in_trace(self):
        def change(o): return replace(o, trace=replace(o.trace, quantization=replace(o.trace.quantization, integer_command=True)))
        r = self.mutated_step(change); self.assertEqual(r['difference_count'], 3)
        self.assertIn('/steps/0/output/trace/quantization/integer_command', r['difference_paths'])

    def test_float_int_type_difference_is_not_tolerance_compared(self):
        r = self.mutated_step(lambda o: replace(o, projection=replace(o.projection, normalized_expression=0)))
        self.assertEqual(r['difference_count'], 3)

    def test_signed_zero_difference_is_exact_and_pointer_keys_are_escaped(self):
        self.assertEqual(list(self.m._paths('', {'a/b~c': 0.0}, {'a/b~c': -0.0})), ['/a~1b~0c'])
        self.assertEqual(list(self.m._paths('', [1, True], [True, 1])), ['/0', '/1'])

    def test_all_differences_counted_but_only_first_256_paths_reported(self):
        original = self.m._observe
        with patch.object(self.m, '_observe', side_effect=lambda result: {**original(result), **{str(i): i for i in range(300)}}): r = self.audit()
        self.assertEqual(r['difference_count'], 300); self.assertEqual(r['reported_difference_count'], 256); self.assertTrue(r['differences_truncated'])
        self.assertEqual(r['difference_paths'], sorted(r['difference_paths']))

    def test_unexpected_preflight_rejection_is_not_reference_success(self):
        with patch.object(self.m, 'rollout_synthetic_sequence', side_effect=self.m.SequenceRolloutError('ROLLOUT_INPUT:0:OTHER')): self.reject('ROLLOUT_AUDIT_EXECUTION_FAILED_WORK_MAY_BE_NONZERO')

    def test_model_failure_after_prefix_is_not_reported_as_zero(self):
        original = self.model.step; calls = 0
        def step(sample, state):
            nonlocal calls
            calls += 1
            if calls == 2: raise ValueError('PRIVATE')
            return original(sample, state)
        with patch.object(self.model, 'step', side_effect=step): self.reject('ROLLOUT_AUDIT_EXECUTION_FAILED_WORK_MAY_BE_NONZERO')
        self.assertEqual(calls, 2)

    def test_malformed_result_cannot_return_partial_match(self):
        with patch.object(self.m, 'rollout_synthetic_sequence', return_value=None): self.reject('ROLLOUT_AUDIT_RESULT_FAILED_WORK_MAY_BE_NONZERO')

    def test_baseexception_not_swallowed_or_converted_to_rejection(self):
        with patch.object(self.m, 'rollout_synthetic_sequence', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt): self.audit()

    def test_repeat_receipts_are_canonical_and_deterministic(self):
        from integration_tools.scenario_output import canonical
        left, right = self.audit(), self.audit(); self.assertEqual(canonical(left), canonical(right)); self.assertEqual(json.loads(canonical(left)), left)

    def test_no_output_temp_or_write_during_audit(self):
        original = os.open
        def opening(path, flags, *a, **kw):
            self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY); return original(path, flags, *a, **kw)
        with patch('os.open', side_effect=opening), patch('os.mkdir', side_effect=AssertionError('mkdir')), patch('tempfile.gettempdir', side_effect=AssertionError('temp')): self.assertEqual(self.audit()['audit_exit_code'], 0)

    def test_audit_match_does_not_grant_generic_or_vehicle_authority(self):
        r = self.audit()
        for field in ('source_identity_reauthenticated', 'prehistory_checked', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'): self.assertIs(r[field], False)
        self.assertEqual((r['gates']['R_BUDGET'], r['gates']['STATIC_EVIDENCE_GATE']), ('UNRESOLVED', 'FAIL'))
        self.assertEqual(r['expected_reference_model_steps'], 0); self.assertIn('CLOSED', r['scope'])
