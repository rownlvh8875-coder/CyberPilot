"""Closed CORE27 execution/export, exact roles and honest failure custody."""

import hashlib
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT, package_feature

NAMES = ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt')
def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(v): return (json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CoreRolloutRunTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_rollout_run.py').is_file(), 'Missing CORE28 closed rollout runner')
        self.model = package_feature()
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.core_rollout_run')
        self.publisher: Any = importlib.import_module('integration_tools.core_sequence_archive_workflow')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name); self.output = self.root / 'output'

    def run_case(self, case='sign-cycle', output=None): return self.m.run_rollout_case(case, self.output if output is None else output)
    def records(self): return json.loads((self.output / NAMES[0]).read_bytes()), json.loads((self.output / NAMES[1]).read_bytes())
    def snapshot(self): return {p.relative_to(self.root).as_posix(): (p.read_bytes() if p.is_file() else None, p.stat().st_mode) for p in self.root.rglob('*')}
    def profiled(self, call):
        calls = {'model': 0, 'factory': 0, 'rollout': 0, 'publish': 0, 'readbacks': 0}; old = sys.getprofile(); code = self.model.step.__code__
        def profile(frame, event, arg):
            if event != 'call': return
            if frame.f_code is code: calls['model'] += 1
            mapping = {('integration_tools.core_sequence_cases', 'build_case'): 'factory',
                ('integration_tools.synthetic_sequence_rollout', 'rollout_synthetic_sequence'): 'rollout',
                ('integration_tools.core_sequence_archive_workflow', '_publish'): 'publish',
                ('integration_tools.core_sequence_archive_workflow', '_readback'): 'readbacks'}
            key = frame.f_globals.get('__name__'), frame.f_code.co_name
            if key in mapping: calls[mapping[key]] += 1
        try: sys.setprofile(profile); value = call()
        finally: sys.setprofile(old)
        return value, calls
    def package(self, receipt):
        self.assertEqual({p.name for p in self.output.iterdir()}, set(NAMES))
        for n in NAMES[:2]: self.assertEqual((self.output / n).read_bytes(), canonical(json.loads((self.output / n).read_bytes())))
        self.assertEqual((self.output / NAMES[2]).read_bytes(), ''.join(sha((self.output / n).read_bytes()) + '  ' + n + '\n' for n in NAMES[:2]).encode())
        self.assertEqual(receipt['files'], {n: {'sha256': sha((self.output / n).read_bytes()), 'byte_size': (self.output / n).stat().st_size} for n in NAMES})

    def test_matching_case_runs_three_steps_and_publishes_three_exact_files(self):
        r, c = self.profiled(self.run_case); self.package(r); source, result = self.records()
        self.assertEqual(c, {'model': 3, 'factory': 1, 'rollout': 1, 'publish': 1, 'readbacks': 3})
        self.assertEqual((r['status'], r['result_status'], r['result_exit_code'], r['model_steps']), ('COMPUTED_ROLLOUT_RUN_PUBLISHED', 'MATCH', 0, 3))
        self.assertEqual((result['frame_count'], result['declared_transition_count'], result['completed_transition_count']), (4, 3, 3))
        self.assertEqual(source['contract_id'], 'CORE28_CLOSED_COMPUTED_ROLLOUT_INPUT_V1')
        self.assertEqual(result['contract_id'], 'CORE28_CLOSED_COMPUTED_ROLLOUT_RESULT_V1')
        self.assertEqual(r['contract_id'], 'CORE28_CLOSED_COMPUTED_ROLLOUT_RUN_V1')

    def test_declared_difference_preserves_computed_chain_and_all_difference_roles(self):
        r = self.run_case('declared-difference'); self.package(r); source, result = self.records()
        self.assertEqual((r['result_status'], r['result_exit_code'], r['model_steps']), ('DIFFERENT', 1, 3))
        self.assertEqual([row['computed_next_state']['previous_applied'] for row in result['rows']], [2, -2, 2])
        self.assertEqual([row['declared_entry_state']['previous_applied'] for row in result['rows']], [-2, 10, 5])
        self.assertEqual([row['entry_state']['previous_applied'] for row in result['rows']], [-2, 2, -2])
        self.assertEqual(result['entry_differing_transition_indices'], [1, 2]); self.assertEqual(result['output_differing_transition_indices'], [0, 1, 2])
        self.assertEqual(result['rows'][1]['entry_differences'], [{'field': 'entry_previous_applied', 'declared': 10, 'computed': 2}])
        self.assertEqual(result['rows'][1]['output_differences'], [{'field': 'saved_limited_state', 'declared': 5, 'computed': -2}])
        self.assertEqual(source['frames'][1]['saved_limited_state'], 10)

    def test_late_invalid_publishes_truthful_rejection_with_zero_model_calls(self):
        r, c = self.profiled(lambda: self.run_case('late-invalid')); self.package(r); source, result = self.records()
        self.assertEqual(c, {'model': 0, 'factory': 1, 'rollout': 1, 'publish': 1, 'readbacks': 3})
        self.assertEqual((r['result_status'], r['result_exit_code'], r['model_steps'], r['computed_state_fed']), ('REJECTED', 2, 0, False))
        self.assertEqual(result['rejection_code'], 'ROLLOUT_INPUT:2:MODEL_DRIVER'); self.assertEqual(result['rows'], [])
        self.assertIsNone(result['initial_declared_state']); self.assertIsNone(result['final_computed_state'])
        self.assertFalse(result['sequence_completed']); self.assertEqual(result['completed_transition_count'], 0)
        self.assertEqual(source['contexts'][2]['current_driver_hex'], '0x1.999999999999ap-4')

    def test_input_precision_is_lossless_hex_and_not_raw_json_float(self):
        self.run_case(); source, result = self.records()
        self.assertEqual(source['frames'][0]['request']['requested_binary32_be_hex'], 'be800000')
        self.assertEqual(source['frames'][1]['request']['requested_binary32_be_hex'], '3f000000')
        self.assertEqual(source['contexts'][0]['current_driver_hex'], '0x1.8000000000000p+0')
        self.assertEqual(source['contexts'][0]['current_angle_deg_hex'], '0x1.5400000000000p+6')
        self.assertNotIn('requested_binary32', source['frames'][0]['request']); self.assertNotIn('current_driver', source['contexts'][0])
        pending = [source, result]
        while pending:
            value = pending.pop(); self.assertIsNot(type(value), float)
            if type(value) is dict: pending.extend(value.values())
            elif type(value) is list: pending.extend(value)

    def test_initial_final_state_and_ordinal_roles_are_explicit(self):
        self.run_case(); _, r = self.records()
        self.assertEqual(r['initial_declared_state'], {'index': 5, 'previous_requested': -4, 'previous_applied': -2, 'angle_counter': 4})
        self.assertEqual(r['final_computed_state'], {'index': 8, 'previous_requested': 4, 'previous_applied': 2, 'angle_counter': 7})
        self.assertEqual([row['transition_index'] for row in r['rows']], [0, 1, 2]); self.assertEqual([row['model_index'] for row in r['rows']], [5, 6, 7])
        self.assertNotIn('trace', r['rows'][0]); self.assertNotIn('projection', r['rows'][0])

    def test_path_independent_files_and_receipts(self):
        r = self.run_case(); other = self.root / 'other'; second = self.run_case(output=other)
        self.assertEqual(canonical(r), canonical(second))
        for n in NAMES: self.assertEqual((self.output / n).read_bytes(), (other / n).read_bytes())

    def test_private_modes_and_checksum_self_exclusion(self):
        self.package(self.run_case()); self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in self.output.iterdir()))
        self.assertEqual(len((self.output / NAMES[2]).read_text().splitlines()), 2)

    def test_invalid_case_precedes_all_output_and_factory_work(self):
        class Child(str): pass
        with patch.object(self.m, '_output', side_effect=AssertionError('output')), patch.object(self.m, 'build_case', side_effect=AssertionError('factory')):
            for case in (None, True, 1, '', '../input', 'unknown', Child('sign-cycle')):
                with self.subTest(case=repr(case)), self.assertRaises(self.m.RolloutRunError) as found: self.m.run_rollout_case(case, None)
                self.assertEqual(found.exception.code, 'ROLLOUT_RUN_CASE')

    def test_existing_folder_rejects_before_model_and_preserves_sentinel(self):
        self.output.mkdir(); (self.output / 'sentinel').write_bytes(b'keep'); before = self.snapshot()
        with patch.object(self.m, 'build_case', side_effect=AssertionError('factory')), self.assertRaises(self.m.ArchiveWorkflowError) as found: self.run_case()
        self.assertEqual(found.exception.code, 'ARCHIVE_WORKFLOW_OUTPUT_EXISTS'); self.assertEqual(self.snapshot(), before)

    def test_unsafe_outputs_reject_before_factory(self):
        link = self.root / 'link'; link.symlink_to(self.root, target_is_directory=True)
        with patch.object(self.m, 'build_case', side_effect=AssertionError('factory')):
            for path in (None, 'not Path', Path('bad\0name'), Path('bad\ud800'), self.root / 'missing' / 'out', link / 'out', ROOT / 'not-created'):
                with self.subTest(path=repr(path)), self.assertRaises(self.m.ArchiveWorkflowError): self.m.run_rollout_case('sign-cycle', path)

    def test_input_encoding_failure_precedes_rollout_and_mkdir(self):
        with patch.object(self.m, 'canonical', side_effect=ValueError('PRIVATE')), patch.object(self.m, 'rollout_synthetic_sequence', side_effect=AssertionError('model')), self.assertRaises(self.m.RolloutRunError) as found: self.run_case()
        self.assertEqual(found.exception.code, 'ROLLOUT_RUN_INPUT_ENCODING'); self.assertFalse(self.output.exists())

    def test_execution_error_is_not_saved_as_zero_model_rejection(self):
        with patch.object(self.m, 'rollout_synthetic_sequence', side_effect=self.m.SequenceRolloutError('ROLLOUT_MODEL_FAILURE:1:WORK_MAY_BE_NONZERO')), self.assertRaises(self.m.RolloutRunError) as found: self.run_case()
        self.assertEqual(found.exception.code, 'ROLLOUT_RUN_EXECUTION_FAILED_WORK_MAY_BE_NONZERO'); self.assertFalse(self.output.exists())

    def test_real_late_model_failure_has_prefix_work_and_no_output(self):
        original = self.model.step; calls = []
        def stepping(sample, state):
            calls.append(1)
            if len(calls) == 2: raise ValueError('PRIVATE')
            return original(sample, state)
        with patch.object(self.model, 'step', side_effect=stepping), self.assertRaises(self.m.RolloutRunError) as found: self.run_case()
        self.assertEqual(len(calls), 2); self.assertIn('WORK_MAY_BE_NONZERO', found.exception.code); self.assertFalse(self.output.exists())

    def test_result_encoding_failure_after_three_steps_does_not_publish(self):
        original = self.m.canonical
        def encode(v):
            if v['contract_id'] == 'CORE28_CLOSED_COMPUTED_ROLLOUT_RESULT_V1': raise ValueError('PRIVATE')
            return original(v)
        seen = []
        def stepping(sample, state): seen.append(1); return original_step(sample, state)
        original_step = self.model.step
        with patch.object(self.m, 'canonical', side_effect=encode), patch.object(self.model, 'step', side_effect=stepping), self.assertRaises(self.m.RolloutRunError) as found: self.run_case()
        self.assertEqual(found.exception.code, 'ROLLOUT_RUN_RESULT_FAILED_WORK_MAY_BE_NONZERO'); self.assertEqual(len(seen), 3); self.assertFalse(self.output.exists())

    def test_unknown_status_rejects_before_publication(self):
        original = self.m.rollout_synthetic_sequence
        def rolling(*a):
            r = original(*a); object.__setattr__(r, 'status', 'UNKNOWN'); return r
        with patch.object(self.m, 'rollout_synthetic_sequence', side_effect=rolling), self.assertRaises(KeyError): self.run_case()
        self.assertFalse(self.output.exists())

    def test_short_writes_complete_exact_package(self):
        original = os.write
        with patch('os.write', side_effect=lambda fd, raw: original(fd, raw[:7])): r = self.run_case()
        self.package(r)

    def test_zero_write_progress_preserves_partial_file_and_reports_work(self):
        with patch('os.write', return_value=0), self.assertRaises(self.m.RolloutRunError) as found: self.run_case()
        self.assertIn('PUBLICATION_FAILED_PARTIAL_DIRECTORY_POSSIBLE', found.exception.code); self.assertIn('WORK_MAY_BE_NONZERO', found.exception.code)
        self.assertEqual((self.output / NAMES[0]).read_bytes(), b'')

    def test_later_write_failure_preserves_completed_input(self):
        original = self.publisher._write
        def writing(directory, name, raw):
            if name == NAMES[1]: raise OSError('PRIVATE')
            return original(directory, name, raw)
        with patch.object(self.publisher, '_write', side_effect=writing), self.assertRaises(self.m.RolloutRunError) as found: self.run_case()
        self.assertIn('ROLLOUT_RUN_PUBLICATION:', found.exception.code); self.assertEqual({p.name for p in self.output.iterdir()}, {NAMES[0]})
        self.assertEqual(json.loads((self.output / NAMES[0]).read_bytes())['case_id'], 'sign-cycle')

    def test_readback_corruption_is_failure_and_never_cleanup(self):
        original = self.publisher._readback
        def reading(directory, name, expected):
            (self.output / name).write_bytes(b'changed'); return original(directory, name, expected)
        with patch.object(self.publisher, '_readback', side_effect=reading), self.assertRaises(self.m.RolloutRunError) as found: self.run_case()
        self.assertIn('PUBLICATION_CHECK_FAILED_DIRECTORY_MAY_EXIST', found.exception.code); self.assertEqual({p.name for p in self.output.iterdir()}, set(NAMES))
        self.assertEqual((self.output / NAMES[0]).read_bytes(), b'changed')

    def test_output_creation_race_preserves_foreign_sentinel(self):
        original = self.m._publish
        def publishing(target, files):
            target.mkdir(); (target / 'sentinel').write_bytes(b'keep'); return original(target, files)
        with patch.object(self.m, '_publish', side_effect=publishing), self.assertRaises(self.m.RolloutRunError): self.run_case()
        self.assertEqual({p.name: p.read_bytes() for p in self.output.iterdir()}, {'sentinel': b'keep'})

    def test_root_replacement_after_readback_rejects_but_retains_both_roots(self):
        original = self.publisher._readback
        def reading(directory, name, expected):
            original(directory, name, expected)
            if name == NAMES[-1]: self.output.rename(self.root / 'held'); self.output.mkdir(); (self.output / 'sentinel').write_bytes(b'keep')
        with patch.object(self.publisher, '_readback', side_effect=reading), self.assertRaises(self.m.RolloutRunError): self.run_case()
        self.assertEqual({p.name for p in (self.root / 'held').iterdir()}, set(NAMES)); self.assertEqual((self.output / 'sentinel').read_bytes(), b'keep')

    def test_existing_completed_output_rerun_executes_zero_models(self):
        self.run_case(); before = self.snapshot()
        with patch.object(self.m, 'rollout_synthetic_sequence', side_effect=AssertionError('model')), self.assertRaises(self.m.ArchiveWorkflowError): self.run_case()
        self.assertEqual(self.snapshot(), before)

    def test_unexpected_failure_propagates_not_a_rejected_package(self):
        with patch.object(self.m, 'rollout_synthetic_sequence', side_effect=AssertionError('PRIVATE')), self.assertRaises(AssertionError): self.run_case()
        self.assertFalse(self.output.exists())

    def test_authority_flags_and_static_rate_gates_stay_closed(self):
        r = self.run_case(); _, saved = self.records()
        self.assertTrue(r['execution_requested']); self.assertTrue(saved['computed_state_fed'])
        for record in (r, saved):
            for key in ('source_identity_reauthenticated', 'prehistory_checked', 'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'): self.assertIs(record[key], False)
            self.assertEqual(record['gates']['R_BUDGET'], 'UNRESOLVED'); self.assertEqual(record['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
            for key in ('actual_r', 'T2', 'vehicle_scale'): self.assertIsNone(record['gates'][key])
        self.assertFalse(saved['anchor_transition_checked'])

    def test_only_existing_computed_model_not_core7_reference_or_f61_executes(self):
        old = sys.getprofile()
        def profile(frame, event, arg):
            if event == 'call':
                module = frame.f_globals.get('__name__', ''); name = frame.f_code.co_name
                if name in ('check_synthetic_sequence', 'run_sequence_case') or module.startswith(('integration_tools.f61_', 'openpilot', 'opendbc')): raise AssertionError('unexpected work')
        try: sys.setprofile(profile); r = self.run_case()
        finally: sys.setprofile(old)
        self.assertEqual(r['model_steps'], 3)
