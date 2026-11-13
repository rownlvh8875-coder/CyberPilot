"""Detect shared model faults, declared-feed drift and false worker success."""

import builtins
import copy
import hashlib
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from dataclasses import replace
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

import test_recording_diagnostics_audit as fixtures
from v1_helpers import ROOT


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class RecordingReferenceTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/recording_diagnostics_reference.py').is_file(), 'Missing CORE69 reference checker')
        self.script = ROOT / 'tools/recording_diagnostics_reference.py'
        self.worker = ROOT / 'tools/recording_diagnostics_reference_worker.py'
        self.assertTrue(self.script.is_file() and self.worker.is_file(), 'Missing CORE69 reference CLIs')
        self.case = fixtures.RecordingDiagnosticsAuditTests('test_match_reproduces_literal_record_with_exactly_three_new_steps')
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.fixture, self.root, self.saved = self.case.fixture, self.case.root, self.case.saved
        self.record = self.case.record
        self.m: Any = importlib.import_module('integration_tools.recording_diagnostics_reference')
        spec = importlib.util.spec_from_file_location('core69_test_cli', self.script)
        assert spec is not None and spec.loader is not None
        self.cli: Any = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.cli)

    def persist(self):
        self.case.record = self.record
        self.case.persist()

    def check(self):
        return self.m.check_recording_reference(self.fixture.file, self.fixture.digest(), self.saved, self.case.digest())

    def payload(self):
        return self.m._payload(self.fixture.codec.decode_recording_input(self.fixture.raw))

    def args(self):
        return self.case.args()

    def invoke(self, args=None):
        target, err = self.root / 'reference.stdout', StringIO()
        with target.open('wb') as stream, patch('sys.stdout', stream), patch('sys.stderr', err):
            code = self.cli.main(self.args() if args is None else args)
        return code, target.read_bytes(), err.getvalue()

    def command(self, args=None):
        return subprocess.run([sys.executable, '-I', '-B', str(self.script), *(self.args() if args is None else args)],
                              cwd=self.root, capture_output=True)

    def assert_receipt(self, result, projection=None, headers=None, indices=None):
        expected = self.fixture.expected() if projection is None else projection
        headers, indices = headers or [], indices or []
        copy_result = dict(result)
        identity = copy_result.pop('reference_identity')
        self.assertEqual(identity['observed_source_hashes']['reference/lateral.py'],
                         '94cf2dde92b43590b1d1e5b2a37b3d295e5f2cf9700ca43e3846bcb1c3ef36b6')
        self.assertTrue(identity['declared_reference_sources'])
        for name, sha in identity['declared_reference_sources'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), sha)
        wanted = {'schema_version': 1, 'contract_id': 'CORE69_DECLARED_DIAGNOSTICS_REFERENCE_AUDIT_V1',
            'audit_status': 'REFERENCE_DIFFERENT' if headers or indices else 'REFERENCE_MATCH',
            'audit_exit_code': int(bool(headers or indices)), 'saved_diagnostic_status': self.record['status'],
            'reference_diagnostic_status': expected['status'], 'input_sha256': self.fixture.digest(),
            'input_bytes': len(self.fixture.raw), 'diagnostics_sha256': self.case.digest(),
            'diagnostics_bytes': len(self.case.raw), 'recorded_model_steps': self.record['new_synthetic_model_steps'],
            'new_synthetic_model_steps': 0, 'new_reference_steps': 3,
            'reference_helper_counts': {'compile_calls': 1, 'selected_definitions_compiled': 2, 'limiter_direct': 0,
                'limiter_traced': 3, 'fault_explicit': 3, 'fault_default': 0, 'traced_clip_calls': 6},
            'reference_runtime': {'python': '3.12.13', 'numpy': '2.5.3'}, 'reference_forbidden_modules_loaded': [],
            'reference_independence': 'EXISTING_SELECTED_SOURCE_AND_INTEGER_BIT_ORACLE_NOT_PUBLIC_MODEL',
            'shared_admission_preflight': True, 'numeric_validation_work': 'NONZERO_NOT_AGGREGATED',
            'differing_header_fields': headers, 'differing_transition_indices': indices,
            'stored_record': self.record, 'reference_projection': expected,
            'first_frame_transition_checked': False, 'prehistory_checked': False,
            'source_identity_reauthenticated': False, 'v4_payload_allowed': False,
            'f61_input_allowed': False, 'actual_activation_allowed': False, 'gates': self.record['gates'],
            'scope': 'BOUNDED_DECLARED_NEXT_STATE_SELECTED_SOURCE_PARITY_NOT_FULL_CONTROLLER_ORIGIN_OR_VEHICLE_PROOF'}
        self.assertEqual(canonical(copy_result), canonical(wanted))

    def reject(self, call=None, code=None):
        def checking():
            with self.assertRaises(ValueError) as found:
                (self.check if call is None else call)()
            if code is not None:
                self.assertEqual(str(found.exception), code)
        _, counts = self.fixture.base.counted(checking)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    # Break: calling the current model instead of the selected-source reference.
    def test_literal_three_row_reference_matches_with_zero_new_model_steps(self):
        result, counts = self.fixture.base.counted(self.check)
        self.assert_receipt(result)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_saved_different_uses_declared_entries_and_can_reference_match(self):
        self.case.different_input()
        self.record = self.case.record
        result, counts = self.fixture.base.counted(self.check)
        self.assert_receipt(result, projection=copy.deepcopy(self.record))
        self.assertEqual(result['reference_projection']['rows'][1]['computed_next_state']['previous_applied'], 5)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_coherent_final_forgery_is_reference_difference(self):
        self.record['rows'][-1]['computed_next_state']['previous_applied'] = 202
        self.record['rows'][-1]['declared_saved_state']['saved_limited_state'] = 202
        self.persist()
        result, counts = self.fixture.base.counted(self.check)
        self.assert_receipt(result, indices=[2])
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_shared_model_arithmetic_fault_reproduces_in_core68_but_not_reference(self):
        step = self.fixture.model.step
        def wrong_step(sample, state):
            result = step(sample, state)
            return replace(result, next_state=replace(result.next_state, previous_applied=202)) if sample.index == 7 else result
        with patch.object(self.fixture.model, 'step', side_effect=wrong_step):
            self.record = self.fixture.run_api()
            self.persist()
            self.assertEqual(self.case.audit()['audit_status'], 'REPRODUCED')
        with patch.object(self.fixture.model, 'step', side_effect=AssertionError('NO_PUBLIC_MODEL')):
            result = self.check()
        self.assert_receipt(result, headers=['differing_transition_indices', 'status'], indices=[2])

    def test_declared_state_is_taken_from_input_not_saved_computed_or_entry(self):
        self.record['rows'][0]['declared_entry_state']['angle_counter'] = 3
        self.persist()
        self.assert_receipt(self.check(), indices=[0])

    def test_negative_driver_sign_is_preserved_in_parent_to_reference_binding(self):
        contexts = (replace(self.fixture.contexts[0], current_driver=-20.0), *self.fixture.contexts[1:])
        self.fixture.save(self.fixture.codec.encode_recording_input(self.fixture.recording, contexts))
        self.record = self.fixture.expected()
        self.persist()
        expected = self.fixture.expected()
        expected.update(status='DIFFERENT', differing_transition_indices=[0])
        expected['rows'][0].update(status='DIFFERENT',
            differences=[{'field': 'saved_limited_state', 'declared': 2, 'computed': 0}])
        expected['rows'][0]['computed_next_state']['previous_applied'] = 0
        result, counts = self.fixture.base.counted(self.check)
        self.assert_receipt(result, projection=expected, headers=['differing_transition_indices', 'status'], indices=[0])
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_both_missing_and_extra_saved_rows_remain_visible(self):
        base = copy.deepcopy(self.record)
        for extra in (False, True):
            self.record = copy.deepcopy(base)
            if extra:
                self.record.update(frame_count=5, checked_transition_count=4, new_synthetic_model_steps=4)
                self.record['rows'].append({'transition_index': 3, 'model_index': 8, 'status': 'MATCH',
                    'declared_entry_state': {'index': 8, 'previous_requested': 4, 'previous_applied': 2, 'angle_counter': 7},
                    'computed_next_state': {'index': 9, 'previous_requested': 4, 'previous_applied': 2, 'angle_counter': 8},
                    'declared_saved_state': {'saved_limited_state': 2, 'saved_angle_counter': 8}, 'differences': []})
            else:
                self.record.update(frame_count=2, checked_transition_count=1, new_synthetic_model_steps=1, rows=self.record['rows'][:1])
            self.persist()
            self.assert_receipt(self.check(), headers=['checked_transition_count', 'frame_count', 'new_synthetic_model_steps'],
                                indices=[3] if extra else [1, 2])

    def test_both_sha_syntax_checks_precede_path_access(self):
        for value in (None, True, b'a' * 64, '', 'A' * 64, 'a' * 63, 'g' * 64, 'a' * 64 + '\n'):
            for first in (True, False):
                sha1, sha2 = (value, self.case.digest()) if first else (self.fixture.digest(), value)
                with patch('os.open', side_effect=AssertionError('open')), patch.object(Path, 'absolute', side_effect=AssertionError('path')):
                    self.reject(lambda sha1=sha1, sha2=sha2: self.m.check_recording_reference(
                        self.fixture.file, sha1, self.saved, sha2), 'RECORDING_REFERENCE_EXPECTED_SHA256')

    def test_declared_input_identity_and_byte_count_reject_before_worker(self):
        for name, value in (('input_sha256', 'b' * 64), ('input_bytes', len(self.fixture.raw) + 1)):
            self.record = self.fixture.expected()
            self.record[name] = value
            self.persist()
            with patch.object(self.m, '_launch', side_effect=AssertionError('worker')):
                self.reject(code='RECORDING_REFERENCE_INPUT_IDENTITY')

    def test_saved_corruption_is_error_not_empty_reference_match(self):
        (self.saved / 'DIAGNOSTICS.json').write_bytes(b'{')
        with patch.object(self.m, '_launch', side_effect=AssertionError('worker')):
            self.reject(code='SAVED_DIAGNOSTICS_CHECKSUM')

    def test_actual_input_hash_mismatch_rejects_before_worker(self):
        self.fixture.file.write_bytes(self.fixture.raw + b' ')
        with patch.object(self.m, '_launch', side_effect=AssertionError('worker')):
            self.reject(code='RECORDING_DIAGNOSTICS_INPUT_CHECKSUM')

    def test_late_invalid_context_has_zero_reference_and_model_prefix(self):
        payload = json.loads(self.fixture.raw)
        payload['contexts'][-1]['current_driver_hex'] = '0x1.999999999999ap-4'
        self.fixture.save(canonical(payload))
        self.record.update(input_sha256=self.fixture.digest(), input_bytes=len(self.fixture.raw))
        self.persist()
        with patch.object(self.m, '_launch', side_effect=AssertionError('worker')):
            self.reject(code='RECORDING_PREFLIGHT_INPUT:2:MODEL_DRIVER')

    def test_reference_source_identity_failure_prevents_worker(self):
        with patch.object(self.m, 'ROOT', self.root / 'absent source'), patch.object(self.m, '_launch', side_effect=AssertionError('worker')):
            self.reject(code='RECORDING_REFERENCE_SOURCE_IDENTITY')

    def test_reference_source_change_after_worker_never_returns_success(self):
        before = self.m._source_identity()
        after = copy.deepcopy(before)
        after['declared_reference_sources']['tools/recording_diagnostics_reference_worker.py'] = 'a' * 64
        with patch.object(self.m, '_source_identity', side_effect=[before, after]):
            self.reject(code='RECORDING_REFERENCE_SOURCE_CHANGED_WORK_MAY_BE_NONZERO')

    def test_worker_timeout_and_failure_never_fallback_to_public_model(self):
        for error in (OSError('SECRET'), subprocess.TimeoutExpired(['PRIVATE'], 60)):
            with patch.object(self.m.subprocess, 'run', side_effect=error):
                self.reject(code='RECORDING_REFERENCE_EXECUTION_FAILED_WORK_MAY_BE_NONZERO')

    def test_worker_stderr_or_bad_json_is_not_forwarded_or_accepted(self):
        for process in (subprocess.CompletedProcess([], 2, b'', b'SECRET'),
                        subprocess.CompletedProcess([], 0, b'{}\n', b'SECRET'),
                        subprocess.CompletedProcess([], 0, b'{', b''),
                        subprocess.CompletedProcess([], 0, b'x' * 1048577, b'')):
            with patch.object(self.m.subprocess, 'run', return_value=process):
                self.reject()

    def test_worker_protocol_rejects_boolean_counts_states_runtime_and_empty_success(self):
        real = self.m._launch(canonical(self.payload()))
        changes = [lambda r: r.update(schema_version=True), lambda r: r.update(extra=1),
            lambda r: r.update(contract_id='OTHER'), lambda r: r.update(reference_steps=False),
            lambda r: r.update(states=[]), lambda r: r['states'][0].update(previous_applied=False),
            lambda r: r['states'][0].update(index=99), lambda r: r['states'][0].update(extra=1),
            lambda r: r['helper_counts'].update(compile_calls=True), lambda r: r['helper_counts'].update(fault_explicit=0),
            lambda r: r.update(numpy_version='OTHER'), lambda r: r.update(python='OTHER'),
            lambda r: r.update(forbidden_modules_loaded=['cyberlateral_dev'])]
        for change in changes:
            result = copy.deepcopy(real)
            change(result)
            with patch.object(self.m, '_launch', return_value=result):
                self.reject(code='RECORDING_REFERENCE_RESULT_FAILED_WORK_MAY_BE_NONZERO')

    def test_runtime_guard_rejects_before_worker(self):
        with patch.object(self.m.platform, 'python_version', return_value='3.12.12'), \
                patch.object(self.m, '_launch', side_effect=AssertionError('worker')):
            self.reject(code='RECORDING_REFERENCE_RUNTIME')

    def test_one_closed_capture_per_artifact_and_no_input_reopen(self):
        original, launch = os.open, self.m._launch
        opened = []
        def opening(*args, **kwargs):
            fd = original(*args, **kwargs)
            opened.append(fd)
            return fd
        def launching(raw):
            self.assertEqual(len(opened), 4)
            for fd in opened:
                with self.assertRaises(OSError):
                    os.fstat(fd)
            return launch(raw)
        with patch('os.open', side_effect=opening), patch.object(self.m, '_launch', side_effect=launching):
            self.assert_receipt(self.check())

    def test_replaced_captured_paths_do_not_change_reference_input(self):
        capture = self.m._capture
        def capturing(path):
            raw = capture(path)
            path.write_bytes(b'later input')
            (self.saved / 'DIAGNOSTICS.json').write_bytes(b'later diagnostics')
            return raw
        with patch.object(self.m, '_capture', side_effect=capturing):
            self.assert_receipt(self.check())

    def test_private_worker_has_no_public_model_imports_and_returns_literal_states(self):
        p = subprocess.run([sys.executable, '-I', '-B', str(self.worker)], input=canonical(self.payload()),
                           cwd=self.root, capture_output=True)
        self.assertEqual((p.returncode, p.stderr), (0, b''))
        result = json.loads(p.stdout)
        self.assertEqual(result['states'], [row['computed_next_state'] for row in self.fixture.expected()['rows']])
        self.assertEqual(result['forbidden_modules_loaded'], [])
        self.assertEqual(result['helper_counts']['traced_clip_calls'], 6)

    def test_private_wire_is_fully_validated_before_helper_initialization(self):
        ref = importlib.import_module('project.recording_diagnostics_reference')
        payload = self.payload()
        payload['rows'][-1]['driver_hex'] = '0x1.999999999999ap-4'
        with patch.object(ref, 'NormalizedReference', side_effect=AssertionError('compile')):
            with self.assertRaisesRegex(ValueError, '^DECLARED_REFERENCE_WIRE$'):
                ref.reference_declared_states(payload)

    def test_worker_rejects_preloaded_public_model_before_reference_imports(self):
        wrapper = '''import runpy,sys,types
sys.modules['cyberlateral_dev']=types.ModuleType('cyberlateral_dev')
source=sys.argv[1];sys.argv=[source]
try:runpy.run_path(source,run_name='__main__')
except SystemExit as error:
 assert error.code==2
 assert 'kernel' not in sys.modules
 raise
'''
        p = subprocess.run([sys.executable, '-I', '-B', '-c', wrapper, str(self.worker)],
                           input=canonical(self.payload()), cwd=self.root, capture_output=True)
        self.assertEqual((p.returncode, p.stdout, p.stderr), (2, b'', b'RECORDING_REFERENCE_WORKER_FAILED\n'))

    def test_rounding_signed_zero_inactive_and_fault_boundaries_use_existing_oracle(self):
        payload = self.payload()
        first = copy.deepcopy(payload['rows'][0])
        examples = [
            ('0x1.0000000000000p-5', False, 0, 0, 0, 0),
            ('0x1.8000000000000p-4', True, 0, 0, 2, 1),
            ('-0x0.0p+0', True, -2, 0, 0, 1),
            ('-0x1.0000000000000p-1', True, 2, 89, -2, 90),
        ]
        for request, active, previous, counter, applied, next_counter in examples:
            row = copy.deepcopy(first)
            row.update(request_hex=request, lat_active=active,
                       saved={'saved_limited_state': applied, 'saved_angle_counter': next_counter})
            row['state'].update(previous_applied=previous, angle_counter=counter)
            wire = {'schema_version': 1, 'scope': 'CORE69_DECLARED_REFERENCE_INPUT_V1', 'rows': [row]}
            result = self.m._launch(canonical(wire))
            state = result['states'][0]
            self.assertEqual((state['previous_applied'], state['angle_counter']), (applied, next_counter))

    def test_maximum_127_reference_steps_do_not_execute_model(self):
        frame = self.fixture.recording.records[0]
        frames = tuple(replace(frame, request=replace(frame.request, sequence=7 + i, sample_time_ns=i,
            requested_binary32=bytes.fromhex('00000000')), limited_state_at_entry=0, saved_limited_state=0,
            angle_counter_at_entry=0, saved_angle_counter=0) for i in range(128))
        contexts = tuple(replace(self.fixture.contexts[0], model_index=3969 + i, previous_integer_request=0,
            current_driver=0.0, current_angle_deg=0.0) for i in range(127))
        self.fixture.save(self.fixture.codec.encode_recording_input(self.fixture.base.recorder.FinishedSyntheticRecordingV1(frames), contexts))
        self.record.update(input_sha256=self.fixture.digest(), input_bytes=len(self.fixture.raw), frame_count=128,
                           checked_transition_count=127, new_synthetic_model_steps=127, rows=[])
        for i in range(127):
            self.record['rows'].append({'transition_index': i, 'model_index': 3969 + i, 'status': 'MATCH',
                'declared_entry_state': {'index': 3969 + i, 'previous_requested': 0, 'previous_applied': 0, 'angle_counter': 0},
                'computed_next_state': {'index': 3970 + i, 'previous_requested': 0, 'previous_applied': 0, 'angle_counter': 0},
                'declared_saved_state': {'saved_limited_state': 0, 'saved_angle_counter': 0}, 'differences': []})
        self.persist()
        result, counts = self.fixture.base.counted(self.check)
        self.assertEqual((result['audit_status'], result['new_reference_steps']), ('REFERENCE_MATCH', 127))
        self.assertEqual(result['reference_helper_counts']['traced_clip_calls'], 254)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_cli_valid_and_forged_results_have_distinct_exits(self):
        result = self.command()
        self.assertEqual((result.returncode, result.stderr), (0, b''))
        self.assert_receipt(json.loads(result.stdout))
        self.record['rows'][-1]['computed_next_state']['previous_applied'] = 202
        self.record['rows'][-1]['declared_saved_state']['saved_limited_state'] = 202
        self.persist()
        result = self.command()
        self.assertEqual((result.returncode, result.stderr), (1, b''))
        self.assert_receipt(json.loads(result.stdout), indices=[2])

    def test_cli_requires_opt_in_and_unique_pins_before_project_imports(self):
        original, args = builtins.__import__, self.args()
        def importing(name, *a, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')):
                raise AssertionError('project import')
            return original(name, *a, **kw)
        invalid = [[], args[1:], args + ['--run'], args + ['--r', '0'], args + ['--dt', '0.01'],
                   args[:-1] + ['A' * 64], args + ['--input', 'x']]
        for i in range(1, len(args), 2):
            invalid.extend([args[:i] + args[i + 2:], args + args[i:i + 2], args[:i + 1] + [''] + args[i + 2:]])
        for argv in invalid:
            with patch('builtins.__import__', side_effect=importing), patch('os.open', side_effect=AssertionError('open')), \
                    patch('sys.stderr', StringIO()) as err, self.assertRaises(SystemExit) as found:
                self.cli.main(argv)
            self.assertEqual((found.exception.code, err.getvalue()), (2, 'REJECTED: RECORDING_REFERENCE_USAGE_NO_EXECUTION\n'))

    def test_cli_help_restores_globals_without_model_or_worker(self):
        paths = list(sys.path)
        with patch.object(sys, 'dont_write_bytecode', False), patch('sys.stdout', StringIO()) as out, \
                patch.object(self.m, '_launch', side_effect=AssertionError('worker')), self.assertRaises(SystemExit) as found:
            try:
                self.cli.main(['--help'])
            finally:
                self.assertEqual(sys.path, paths)
                self.assertFalse(sys.dont_write_bytecode)
        self.assertEqual(found.exception.code, 0)
        self.assertIn('--run', out.getvalue())

    def test_cli_positive_short_writes_complete_and_keep_zero_model_steps(self):
        write = os.write
        with patch('os.write', side_effect=lambda fd, raw: write(fd, raw[:13] if fd == sys.stdout.fileno() else raw)):
            (code, raw, err), counts = self.fixture.base.counted(self.invoke)
        self.assertEqual((code, err), (0, ''))
        self.assert_receipt(json.loads(raw))
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_cli_broken_stdout_reports_possibly_nonzero_reference_work(self):
        write = os.write
        for value in (0, -1, None):
            def writing(fd, raw, value=value):
                if fd != sys.stdout.fileno():
                    return write(fd, raw)
                if value is None:
                    raise BrokenPipeError('SECRET')
                return value
            with patch('os.write', side_effect=writing):
                result, counts = self.fixture.base.counted(self.invoke)
            self.assertEqual(result, (2, b'', 'REJECTED: RECORDING_REFERENCE_FAILED_WORK_MAY_BE_NONZERO\n'))
            self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_cli_partial_stdout_does_not_restart_reference(self):
        write, writes, launch, executions = os.write, [], self.m._launch, []
        def launching(raw):
            result = launch(raw)
            executions.append(result['reference_steps'])
            return result
        def writing(fd, raw):
            if fd != sys.stdout.fileno():
                return write(fd, raw)
            writes.append(bytes(raw))
            if len(writes) == 1:
                return write(fd, raw[:11])
            raise OSError('SECRET')
        with patch('os.write', side_effect=writing), patch.object(self.m, '_launch', side_effect=launching):
            code, out, err = self.invoke()
        self.assertEqual((code, out), (2, writes[0][:11]))
        self.assertEqual(len(writes), 2)
        self.assertNotIn('SECRET', err)
        self.assertEqual(executions, [3])

    def test_cli_output_size_or_serialization_failure_keeps_zero_model_execution(self):
        for payload in (b'x' * 2097153, None):
            original = builtins.__import__
            def importing(name, *args, _original=original, _payload=payload, **kwargs):
                module = _original(name, *args, **kwargs)
                if name == 'integration_tools.scenario_output':
                    class Boundary:
                        @staticmethod
                        def canonical(_value, expected=_payload):
                            if expected is None:
                                raise ValueError('SECRET')
                            return expected
                    return Boundary
                return module
            with patch('builtins.__import__', side_effect=importing):
                result, counts = self.fixture.base.counted(self.invoke)
            self.assertEqual(result, (2, b'', 'REJECTED: RECORDING_REFERENCE_FAILED_WORK_MAY_BE_NONZERO\n'))
            self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_cli_identity_error_restores_globals_and_preserves_originals(self):
        self.record['input_bytes'] += 1
        self.persist()
        before, paths = self.case.snapshot(), list(sys.path)
        with patch.object(sys, 'dont_write_bytecode', False):
            self.assertEqual(self.invoke(), (2, b'', 'REJECTED: RECORDING_REFERENCE_INPUT_IDENTITY\n'))
            self.assertEqual(sys.path, paths)
            self.assertFalse(sys.dont_write_bytecode)
        self.assertEqual(self.case.snapshot(), before)

    def test_two_fresh_commands_are_byte_identical_and_do_not_modify_inputs(self):
        before = self.case.snapshot()
        one, two = self.command(), self.command()
        self.assertEqual((one.returncode, two.returncode, one.stderr, two.stderr), (0, 0, b'', b''))
        self.assertEqual(one.stdout, two.stdout)
        self.assert_receipt(json.loads(one.stdout))
        self.assertEqual(self.case.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
