"""Catch false replay success, double reads, implicit execution and hidden work."""

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

import test_recording_input_cli as fixtures
from v1_helpers import ROOT


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class RecordingDiagnosticsAuditTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/recording_diagnostics_audit.py').is_file(), 'Missing CORE68 audit API')
        self.script = ROOT / 'tools/recording_diagnostics_audit.py'
        self.assertTrue(self.script.is_file(), 'Missing CORE68 explicit audit CLI')
        self.fixture = fixtures.RecordingInputCliTests('test_api_match_emits_independent_literal_three_row_projection')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.saved = self.root / 'saved diagnostics'
        self.saved.mkdir()
        self.record = self.fixture.expected()
        self.persist()
        self.m: Any = importlib.import_module('integration_tools.recording_diagnostics_audit')
        spec = importlib.util.spec_from_file_location('core68_test_cli', self.script)
        assert spec is not None and spec.loader is not None
        self.cli: Any = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.cli)

    def persist(self):
        self.raw = canonical(self.record)
        (self.saved / 'DIAGNOSTICS.json').write_bytes(self.raw)
        (self.saved / 'SHA256SUMS.txt').write_text(hashlib.sha256(self.raw).hexdigest() + '  DIAGNOSTICS.json\n')

    def digest(self):
        return hashlib.sha256(self.raw).hexdigest()

    def audit(self):
        return self.m.audit_recording_diagnostics(self.fixture.file, self.fixture.digest(), self.saved, self.digest())

    def args(self):
        return ['--run', '--input-file', str(self.fixture.file), '--expected-input-sha256', self.fixture.digest(),
                '--diagnostics-root', str(self.saved), '--expected-diagnostics-sha256', self.digest()]

    def command(self, args=None, script=None):
        cmd = [sys.executable, '-I', '-B']
        if script is not None:
            cmd.extend(['-c', script])
        return subprocess.run([*cmd, str(self.script), *(self.args() if args is None else args)], cwd=self.root, capture_output=True)

    def invoke(self, args=None):
        err, target = StringIO(), self.root / 'stdout.bin'
        with target.open('wb') as out, patch('sys.stdout', out), patch('sys.stderr', err):
            code = self.cli.main(self.args() if args is None else args)
        return code, target.read_bytes(), err.getvalue()

    def expected(self, stored=None, recomputed=None, headers=None, indices=None):
        stored = self.record if stored is None else stored
        recomputed = self.fixture.expected() if recomputed is None else recomputed
        different = bool(headers or indices)
        return {'schema_version': 1, 'contract_id': 'CORE68_SYNTHETIC_DIAGNOSTICS_AUDIT_V1',
            'audit_status': 'DIFFERENT' if different else 'REPRODUCED', 'audit_exit_code': int(different),
            'saved_diagnostic_status': stored['status'], 'recomputed_diagnostic_status': recomputed['status'],
            'input_sha256': self.fixture.digest(), 'input_bytes': len(self.fixture.raw),
            'diagnostics_sha256': self.digest(), 'diagnostics_bytes': len(self.raw),
            'recorded_model_steps': stored['new_synthetic_model_steps'],
            'new_synthetic_model_steps': recomputed['new_synthetic_model_steps'], 'new_reference_steps': 0,
            'differing_header_fields': [] if headers is None else headers,
            'differing_transition_indices': [] if indices is None else indices,
            'stored_record': stored, 'recomputed_record': recomputed, 'arithmetic_recomputed': True,
            'supplied_input_bytes_verified': True, 'independent_numerical_oracle': False,
            'numeric_validation_work': 'NONZERO_NOT_AGGREGATED', 'first_frame_transition_checked': False,
            'prehistory_checked': False, 'source_identity_reauthenticated': False, 'v4_payload_allowed': False,
            'f61_input_allowed': False, 'actual_activation_allowed': False, 'gates': stored['gates'],
            'scope': 'SUPPLIED_SYNTHETIC_INPUT_RECOMPUTATION_NOT_ORIGIN_OR_INDEPENDENT_OR_VEHICLE_PROOF'}

    def rejected(self, call=None, code=None):
        def checking():
            with self.assertRaises(ValueError) as found:
                (self.audit if call is None else call)()
            if code is not None:
                self.assertEqual(str(found.exception), code)
        _, counts = self.fixture.base.counted(checking)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def snapshot(self):
        return {str(p.relative_to(self.root)): (p.read_bytes(), p.stat().st_mode)
                for folder in (self.saved, self.fixture.folder) for p in folder.iterdir()}

    def different_input(self):
        self.fixture.difference()
        self.record = self.fixture.expected()
        self.record.update(status='DIFFERENT', differing_transition_indices=[0])
        self.record['rows'][0].update(status='DIFFERENT',
            declared_saved_state={'saved_limited_state': 10, 'saved_angle_counter': 5},
            differences=[{'field': 'saved_limited_state', 'declared': 10, 'computed': 2}])
        self.record['rows'][1]['declared_entry_state']['previous_applied'] = 10
        self.record['rows'][1]['computed_next_state']['previous_applied'] = 5
        self.record['rows'][1]['declared_saved_state']['saved_limited_state'] = 5
        self.record['rows'][2]['declared_entry_state']['previous_applied'] = 5
        self.record['rows'][2]['computed_next_state']['previous_applied'] = 4
        self.record['rows'][2]['declared_saved_state']['saved_limited_state'] = 4
        self.persist()

    # Break: replacing recomputation by stored-only inspection or dropping old/new work separation.
    def test_match_reproduces_literal_record_with_exactly_three_new_steps(self):
        result, counts = self.fixture.base.counted(self.audit)
        self.assertEqual(result, self.expected())
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_true_saved_difference_is_reproduced_and_keeps_declared_state_feed(self):
        self.different_input()
        result, counts = self.fixture.base.counted(self.audit)
        self.assertEqual(result, self.expected(recomputed=copy.deepcopy(self.record)))
        self.assertEqual((result['audit_exit_code'], result['recomputed_diagnostic_status']), (0, 'DIFFERENT'))
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_consistent_forged_final_arithmetic_is_detected_without_repair(self):
        self.record['rows'][-1]['computed_next_state']['previous_applied'] = 202
        self.record['rows'][-1]['declared_saved_state']['saved_limited_state'] = 202
        self.persist()
        result, counts = self.fixture.base.counted(self.audit)
        self.assertEqual(result, self.expected(indices=[2]))
        self.assertEqual(result['stored_record']['rows'][-1]['computed_next_state']['previous_applied'], 202)
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_missing_saved_rows_are_reported_alongside_all_changed_headers(self):
        self.record.update(frame_count=2, checked_transition_count=1, new_synthetic_model_steps=1,
                           rows=self.record['rows'][:1])
        self.persist()
        self.assertEqual(self.audit(), self.expected(
            headers=['checked_transition_count', 'frame_count', 'new_synthetic_model_steps'], indices=[1, 2]))

    def test_forged_summary_and_changed_row_are_both_visible(self):
        self.record.update(status='DIFFERENT', differing_transition_indices=[2])
        self.record['rows'][2].update(status='DIFFERENT',
            differences=[{'field': 'saved_limited_state', 'declared': 2, 'computed': 202}])
        self.record['rows'][2]['computed_next_state']['previous_applied'] = 202
        self.persist()
        self.assertEqual(self.audit(), self.expected(headers=['differing_transition_indices', 'status'], indices=[2]))

    def test_real_core64_publication_reproduces_without_extra_runs(self):
        producer = importlib.import_module('integration_tools.recording_input_workflow')
        target = self.root / 'real publication'
        producer.publish_recording_input(self.fixture.file, self.fixture.digest(), target)
        raw = (target / 'DIAGNOSTICS.json').read_bytes()
        result, counts = self.fixture.base.counted(lambda: self.m.audit_recording_diagnostics(
            self.fixture.file, self.fixture.digest(), target, hashlib.sha256(raw).hexdigest()))
        self.assertEqual(result['audit_status'], 'REPRODUCED')
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_both_sha_syntax_checks_precede_all_path_access(self):
        for bad in (None, True, b'a' * 64, '', 'A' * 64, 'g' * 64, 'a' * 63, 'a' * 64 + '\n'):
            for first in (True, False):
                values = (bad, self.digest()) if first else (self.fixture.digest(), bad)
                with patch('os.open', side_effect=AssertionError('path access')), \
                        patch.object(Path, 'absolute', side_effect=AssertionError('path conversion')):
                    self.rejected(lambda values=values: self.m.audit_recording_diagnostics(
                        self.fixture.file, values[0], self.saved, values[1]), 'DIAGNOSTICS_AUDIT_EXPECTED_SHA256')

    def test_declared_input_digest_mismatch_rejects_before_input_capture(self):
        self.record['input_sha256'] = 'b' * 64
        self.persist()
        with patch.object(self.m, '_capture', side_effect=AssertionError('input read')):
            self.rejected(code='DIAGNOSTICS_AUDIT_INPUT_IDENTITY')

    def test_declared_byte_count_mismatch_rejects_before_any_model_step(self):
        self.record['input_bytes'] += 1
        self.persist()
        self.rejected(code='DIAGNOSTICS_AUDIT_INPUT_IDENTITY')

    def test_actual_input_digest_mismatch_rejects_without_recalculation(self):
        self.fixture.file.write_bytes(self.fixture.raw + b' ')
        self.rejected(code='RECORDING_DIAGNOSTICS_INPUT_CHECKSUM')

    def test_invalid_saved_checksum_does_not_open_input_or_run_model(self):
        (self.saved / 'DIAGNOSTICS.json').write_bytes(self.raw + b' ')
        with patch.object(self.m, '_capture', side_effect=AssertionError('input read')):
            self.rejected(code='SAVED_DIAGNOSTICS_CHECKSUM')

    def test_invalid_saved_authority_or_structure_is_not_a_numeric_difference(self):
        for mutate in (lambda r: r.update(actual_activation_allowed=True), lambda r: r['rows'][0].update(status='OTHER')):
            self.record = self.fixture.expected()
            mutate(self.record)
            self.persist()
            self.rejected()

    def test_bare_or_noncanonical_input_is_not_guessed_or_executed(self):
        for raw in (b'{', self.fixture.base.codec.encode_recording(self.fixture.recording)):
            self.fixture.save(raw)
            self.record.update(input_sha256=self.fixture.digest(), input_bytes=len(raw))
            self.persist()
            self.rejected(code='RECORDING_INPUT_SERIALIZATION')

    def test_late_semantic_failure_rejects_whole_recording_before_first_step(self):
        payload = json.loads(self.fixture.raw)
        payload['contexts'][-1]['current_driver_hex'] = '0x1.999999999999ap-4'
        self.fixture.save(canonical(payload))
        self.record.update(input_sha256=self.fixture.digest(), input_bytes=len(self.fixture.raw))
        self.persist()
        self.rejected(code='RECORDING_PREFLIGHT_INPUT:2:MODEL_DRIVER')

    def test_input_file_bounds_and_nonregular_paths_reject_without_steps(self):
        for content in (b'', b'x' * 1048577):
            self.fixture.file.write_bytes(content)
            self.rejected(code='RECORDING_DIAGNOSTICS_INPUT_SIZE')
        self.fixture.file.unlink()
        os.mkfifo(self.fixture.file)
        self.rejected(code='RECORDING_DIAGNOSTICS_INPUT_FILE')

    def test_input_and_saved_symlinks_are_not_followed(self):
        link = self.root / 'link'
        link.symlink_to(self.fixture.file)
        self.rejected(lambda: self.m.audit_recording_diagnostics(link, self.fixture.digest(), self.saved, self.digest()))
        link.unlink()
        link.symlink_to(self.saved, target_is_directory=True)
        self.rejected(lambda: self.m.audit_recording_diagnostics(self.fixture.file, self.fixture.digest(), link, self.digest()))

    def test_all_four_descriptors_are_closed_before_recomputation_and_never_reopened(self):
        original_open, diagnose = os.open, self.m._diagnose_captured
        opened = []
        def opening(*args, **kwargs):
            fd = original_open(*args, **kwargs)
            opened.append(fd)
            return fd
        def checking(raw):
            self.assertEqual(len(opened), 4)
            self.assertEqual(raw, self.fixture.raw)
            for fd in opened:
                with self.assertRaises(OSError):
                    os.fstat(fd)
            with patch('os.open', side_effect=AssertionError('reopen')):
                return diagnose(raw)
        with patch('os.open', side_effect=opening), patch.object(self.m, '_diagnose_captured', side_effect=checking):
            self.assertEqual(self.audit(), self.expected())

    def test_path_replacement_after_capture_does_not_change_recomputed_input(self):
        capture = self.m._capture
        def capturing(path):
            raw = capture(path)
            path.write_bytes(b'later input')
            (self.saved / 'DIAGNOSTICS.json').write_bytes(b'later diagnostic')
            return raw
        with patch.object(self.m, '_capture', side_effect=capturing):
            self.assertEqual(self.audit(), self.expected())

    def test_readonly_files_and_relative_paths_are_preserved(self):
        for p in (self.fixture.file, *self.saved.iterdir()):
            p.chmod(0o444)
        before = self.snapshot()
        result = self.m.audit_recording_diagnostics(Path(os.path.relpath(self.fixture.file)), self.fixture.digest(),
                                                   Path(os.path.relpath(self.saved)), self.digest())
        self.assertEqual(result, self.expected())
        self.assertEqual(self.snapshot(), before)

    def test_maximum_recording_executes_all_127_transitions(self):
        frame = self.fixture.recording.records[0]
        frames = tuple(replace(frame, request=replace(frame.request, sequence=7 + i, sample_time_ns=i,
            requested_binary32=bytes.fromhex('00000000')), limited_state_at_entry=0, saved_limited_state=0,
            angle_counter_at_entry=0, saved_angle_counter=0) for i in range(128))
        contexts = tuple(replace(self.fixture.contexts[0], model_index=3969 + i, previous_integer_request=0,
            current_driver=0.0, current_angle_deg=0.0) for i in range(127))
        self.fixture.save(self.fixture.codec.encode_recording_input(
            self.fixture.base.recorder.FinishedSyntheticRecordingV1(frames), contexts))
        self.record.update(input_sha256=self.fixture.digest(), input_bytes=len(self.fixture.raw), frame_count=128,
            checked_transition_count=127, new_synthetic_model_steps=127, rows=[])
        for i in range(127):
            self.record['rows'].append({'transition_index': i, 'model_index': 3969 + i, 'status': 'MATCH',
                'declared_entry_state': fixtures.state(3969 + i, 0, 0, 0),
                'computed_next_state': fixtures.state(3970 + i, 0, 0, 0),
                'declared_saved_state': {'saved_limited_state': 0, 'saved_angle_counter': 0}, 'differences': []})
        self.persist()
        result, counts = self.fixture.base.counted(self.audit)
        self.assertEqual((result['audit_status'], result['new_synthetic_model_steps']), ('REPRODUCED', 127))
        self.assertEqual(counts, {'step': 127, 'simulate': 0})

    def test_cli_reproduced_emits_exact_canonical_record_exit_zero(self):
        result = self.command()
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, canonical(self.expected()), b''))

    def test_cli_changed_arithmetic_exits_one_and_retains_both_records(self):
        self.record['rows'][2]['computed_next_state']['previous_applied'] = 202
        self.record['rows'][2]['declared_saved_state']['saved_limited_state'] = 202
        self.persist()
        result = self.command()
        self.assertEqual((result.returncode, result.stdout, result.stderr), (1, canonical(self.expected(indices=[2])), b''))

    def test_cli_saved_difference_reproduced_is_exit_zero(self):
        self.different_input()
        result = self.command()
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, canonical(self.expected(recomputed=copy.deepcopy(self.record))), b''))

    def test_cli_requires_run_and_all_unique_flags_before_project_imports(self):
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.startswith(('integration_tools', 'cyberlateral_dev')):
                raise AssertionError('project import')
            return original(name, *args, **kwargs)
        good = self.args()
        invalid = [[], good[1:], good + ['--run'], good + ['--r', '0'], good + ['--dt', '0.01'],
                   good + ['--input', 'other'], good[:-1] + ['A' * 64]]
        for i in range(1, len(good), 2):
            invalid.extend([good[:i] + good[i + 2:], good + good[i:i + 2], good[:i + 1] + [''] + good[i + 2:]])
        for args in invalid:
            with patch('builtins.__import__', side_effect=guarded), patch('os.open', side_effect=AssertionError('open')), \
                    patch('sys.stderr', StringIO()) as err, self.assertRaises(SystemExit) as found:
                self.cli.main(args)
            self.assertEqual((found.exception.code, err.getvalue()),
                             (2, 'REJECTED: DIAGNOSTICS_AUDIT_USAGE_NO_MODEL_EXECUTION\n'))

    def test_cli_help_does_not_import_project_and_restores_globals(self):
        original, before = builtins.__import__, list(sys.path)
        def guarded(name, *args, **kwargs):
            if name.startswith(('integration_tools', 'cyberlateral_dev')):
                raise AssertionError('project import')
            return original(name, *args, **kwargs)
        with patch.object(sys, 'dont_write_bytecode', False), patch('builtins.__import__', side_effect=guarded), \
                patch('sys.stdout', StringIO()) as out, self.assertRaises(SystemExit) as found:
            try:
                self.cli.main(['--help'])
            finally:
                self.assertEqual(sys.path, before)
                self.assertFalse(sys.dont_write_bytecode)
        self.assertEqual(found.exception.code, 0)
        self.assertIn('--run', out.getvalue())

    def test_cli_input_identity_failure_is_fixed_exit_two_without_steps(self):
        self.record['input_bytes'] += 1
        self.persist()
        result, counts = self.fixture.base.counted(self.invoke)
        self.assertEqual(result, (2, b'', 'REJECTED: DIAGNOSTICS_AUDIT_INPUT_IDENTITY\n'))
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_cli_positive_short_writes_complete_without_reexecuting_model(self):
        write = os.write
        with patch('os.write', side_effect=lambda fd, raw: write(fd, raw[:17])):
            result, counts = self.fixture.base.counted(self.invoke)
        self.assertEqual(result, (0, canonical(self.expected()), ''))
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_cli_broken_or_nonpositive_stdout_fails_with_nonzero_work(self):
        for value in (0, -1, None):
            def writing(_fd, _raw, value=value):
                if value is None:
                    raise BrokenPipeError('SECRET')
                return value
            with patch('os.write', side_effect=writing):
                result, counts = self.fixture.base.counted(self.invoke)
            self.assertEqual(result, (2, b'', 'REJECTED: DIAGNOSTICS_AUDIT_FAILED_WORK_MAY_BE_NONZERO\n'))
            self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_cli_partial_stdout_is_not_retried_or_retracted(self):
        write, writes = os.write, []
        def writing(fd, raw):
            writes.append(bytes(raw))
            if len(writes) == 1:
                return write(fd, raw[:11])
            raise OSError('SECRET')
        with patch('os.write', side_effect=writing):
            (code, out, err), counts = self.fixture.base.counted(self.invoke)
        self.assertEqual((code, out), (2, canonical(self.expected())[:11]))
        self.assertEqual(len(writes), 2)
        self.assertNotIn('SECRET', err)
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_cli_oversize_or_serialization_failure_does_not_publish_success(self):
        # Patch serialization at the CLI boundary after real replay,not its comparison helper.
        for payload in (b'x' * 2097153, None):
            original_import = builtins.__import__
            def importing(name, *args, _original=original_import, _payload=payload, **kwargs):
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
                (code, out, err), counts = self.fixture.base.counted(self.invoke)
            self.assertEqual((code, out, err), (2, b'', 'REJECTED: DIAGNOSTICS_AUDIT_FAILED_WORK_MAY_BE_NONZERO\n'))
            self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_cli_late_execution_error_has_no_success_and_keeps_work_distinction(self):
        step, calls = self.fixture.model.step, []
        def stepping(*args):
            calls.append(1)
            if len(calls) == 2:
                raise ValueError('SECRET')
            return step(*args)
        with patch.object(self.fixture.model, 'step', side_effect=stepping):
            code, out, err = self.invoke()
        self.assertEqual((code, out, err), (2, b'', 'REJECTED: DIAGNOSTICS_AUDIT_FAILED_WORK_MAY_BE_NONZERO\n'))
        self.assertEqual(len(calls), 2)

    def test_cli_restores_globals_and_never_modifies_input_or_saved_files(self):
        before, paths = self.snapshot(), list(sys.path)
        for invalid in (False, True):
            if invalid:
                (self.saved / 'SHA256SUMS.txt').write_bytes(b'bad')
                before = self.snapshot()
            with patch.object(sys, 'dont_write_bytecode', False):
                self.assertEqual(self.invoke()[0], 2 if invalid else 0)
                self.assertEqual(sys.path, paths)
                self.assertFalse(sys.dont_write_bytecode)
            self.assertEqual(self.snapshot(), before)

    def test_fresh_processes_are_identical_without_actual_or_reference_imports(self):
        script = '''import importlib.abc,runpy,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  forbidden=('openpilot','opendbc','integration_tools.fixed_model_reference','integration_tools.sequence_reference')
  if any(fullname==n or fullname.startswith(n+'.') for n in forbidden) or fullname.startswith(('integration_tools.f61_','synthetic_rate_constraint_feasibility')):raise AssertionError('FORBIDDEN:'+fullname)
sys.meta_path.insert(0,Block());sys.argv=sys.argv[1:]
runpy.run_path(sys.argv[0],run_name='__main__')
'''
        before = self.snapshot()
        one, two = self.command(script=script), self.command(script=script)
        self.assertEqual((one.returncode, two.returncode, one.stderr, two.stderr), (0, 0, b'', b''))
        self.assertEqual(one.stdout, two.stdout)
        self.assertEqual(one.stdout, canonical(self.expected()))
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
