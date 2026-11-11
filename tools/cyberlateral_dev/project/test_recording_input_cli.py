"""Catch SHA/path bypass, prefix execution, lost diagnostics and false CLI success."""

import builtins
import hashlib
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

import test_offline_recording_input_codec as fixtures
from v1_helpers import ROOT


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def state(index, requested, applied, counter):
    return dict(index=index, previous_requested=requested, previous_applied=applied, angle_counter=counter)


class RecordingInputCliTests(unittest.TestCase):
    def setUp(self):
        self.script = ROOT / 'tools/recording_input_diagnostics.py'
        self.assertTrue((ROOT / 'integration_tools/recording_input_run.py').is_file(), 'Missing CORE61 saved-input runner')
        self.assertTrue(self.script.is_file(), 'Missing CORE61 explicit CLI')
        case = fixtures.RecordingInputCodecTests('test_encoder_matches_independent_literal_wire_without_steps')
        case.setUp()
        self.base, self.codec, self.model = case.fixture, case.m, case.model
        self.recording, self.contexts = case.recording, case.contexts
        self.raw = canonical(case.payload)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / 'input'
        self.folder.mkdir()
        self.file = self.folder / 'complete input.json'
        self.file.write_bytes(self.raw)
        self.api: Any = importlib.import_module('integration_tools.recording_input_run')
        spec = importlib.util.spec_from_file_location('core61_test_cli', self.script)
        assert spec is not None and spec.loader is not None
        self.cli: Any = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.cli)

    def digest(self, raw=None):
        return hashlib.sha256(self.raw if raw is None else raw).hexdigest()

    def args(self):
        return ['--run', '--input-file', str(self.file), '--expected-sha256', self.digest()]

    def run_api(self):
        return self.api.run_recording_input(self.file, self.digest())

    def expected(self):
        rows = []
        for i, entry, computed, saved, counter in (
            (0, state(5, -4, -2, 4), state(6, 8, 2, 5), 2, 5),
            (1, state(6, 8, 2, 5), state(7, -8, -2, 6), -2, 6),
            (2, state(7, -8, -2, 6), state(8, 4, 2, 7), 2, 7),
        ):
            rows.append({'transition_index': i, 'model_index': i + 5, 'status': 'MATCH',
                'declared_entry_state': entry, 'computed_next_state': computed,
                'declared_saved_state': {'saved_limited_state': saved, 'saved_angle_counter': counter}, 'differences': []})
        return {'schema_version': 1, 'contract_id': 'CORE61_COUNTERFACTUAL_RECORDING_DIAGNOSTICS_V1',
            'scope': 'DECLARED_SYNTHETIC_INPUT_DIAGNOSTICS_ONLY', 'input_sha256': self.digest(), 'input_bytes': len(self.raw),
            'status': 'MATCH', 'frame_count': 4, 'checked_transition_count': 3, 'new_synthetic_model_steps': 3,
            'differing_transition_indices': [], 'rows': rows,
            'validation_claim': 'ADJACENT_DECLARED_CURRENT_TRANSITIONS_ONLY_NOT_COMPUTED_ROLLOUT',
            'state_feed_rule': 'DECLARED_ENTRY_EACH_STEP_NO_REPAIR_OR_COMPUTED_ROLLOUT',
            'first_frame_transition_checked': False, 'prehistory_checked': False,
            'source_identity_reauthenticated': False, 'v4_payload_allowed': False,
            'f61_input_allowed': False, 'actual_activation_allowed': False,
            'gates': {'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL', 'actual_r': None, 'T2': None,
                'vehicle_scale': None, 'actual_vehicle_input_authorization': 'NOT_ALLOWED',
                'actual_production_activation': 'NOT_ALLOWED', 'F61_calculator_executions': 0, 'r_calculations': 0,
                'dt_calculations': 0, 'SOURCE_SCHEMA_UNQUALIFIED': 6000, 'Candidate': 'NO_GO', 'Runtime': 'NO_GO',
                'D2': 'PERFORMANCE_NOT_EVALUATED', 'F19': 'LEGACY_UNRESOLVED', 'NATIVE_EXACT_REPLAY': 'NOT_PROVEN',
                'F70UH': 'NOT_ALLOWED', 'F70V': 'NOT_ALLOWED', 'F71': 'NOT_ALLOWED'}}

    def save(self, raw):
        self.raw = raw
        self.file.write_bytes(raw)

    def difference(self):
        fs = self.recording.records
        recording = self.base.recorder.FinishedSyntheticRecordingV1((fs[0], replace(fs[1], saved_limited_state=10),
            replace(fs[2], limited_state_at_entry=10, saved_limited_state=5),
            replace(fs[3], limited_state_at_entry=5, saved_limited_state=4)))
        self.save(self.codec.encode_recording_input(recording, self.contexts))

    def snapshot(self):
        return {p.name: (p.read_bytes(), p.stat().st_mode) for p in self.folder.iterdir()}

    def command(self, args=None):
        return subprocess.run([sys.executable, '-I', '-B', str(self.script), *(self.args() if args is None else args)],
            cwd=self.root, capture_output=True)

    def invoke(self, args=None):
        err = StringIO()
        target = self.root / 'stdout.bin'
        with target.open('wb') as out, patch('sys.stdout', out), patch('sys.stderr', err):
            code = self.cli.main(self.args() if args is None else args)
        return code, target.read_bytes(), err.getvalue()

    def rejected(self, call, kind, code):
        def check():
            with self.assertRaises(kind) as found:
                call()
            self.assertEqual((found.exception.code, str(found.exception)), (code, code))
        _, counts = self.base.counted(check)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_api_match_emits_independent_literal_three_row_projection(self):
        result, counts = self.base.counted(self.run_api)
        self.assertEqual(result, self.expected())
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_api_difference_keeps_declared_entry_and_all_later_rows(self):
        self.difference()
        result, counts = self.base.counted(self.run_api)
        self.assertEqual((result['status'], result['differing_transition_indices']), ('DIFFERENT', [0]))
        self.assertEqual([r['status'] for r in result['rows']], ['DIFFERENT', 'MATCH', 'MATCH'])
        self.assertEqual([r['computed_next_state']['previous_applied'] for r in result['rows']], [2, 5, 4])
        self.assertEqual(result['rows'][1]['declared_entry_state']['previous_applied'], 10)
        self.assertEqual(result['rows'][0]['differences'], [{'field': 'saved_limited_state', 'declared': 10, 'computed': 2}])
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_api_invalid_digest_rejects_before_any_path_access(self):
        for digest in (None, True, b'0' * 64, '', 'a' * 63, 'A' * 64, 'g' * 64, '0' * 64 + '\n'):
            with patch('os.open', side_effect=AssertionError('opened')), patch.object(Path, 'absolute', side_effect=AssertionError('path')):
                self.rejected(lambda digest=digest: self.api.run_recording_input(self.file, digest),
                    self.api.RecordingInputRunError, 'RECORDING_DIAGNOSTICS_INPUT_SHA256')

    def test_api_digest_mismatch_prevents_diagnostic_execution(self):
        self.rejected(lambda: self.api.run_recording_input(self.file, '0' * 64),
            self.api.RecordingInputRunError, 'RECORDING_DIAGNOSTICS_INPUT_CHECKSUM')

    def test_api_single_regular_readonly_capture_closed_before_diagnostic(self):
        real_open, real_check = os.open, self.api.check_serialized_recording_input
        opened = []
        def opening(path, flags, *a, **kw):
            self.assertFalse(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
            self.assertEqual(flags & (os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC), os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
            fd = real_open(path, flags, *a, **kw)
            opened.append(fd)
            return fd
        def checked(raw):
            self.assertEqual(len(opened), 1)
            with self.assertRaises(OSError): os.fstat(opened[0])
            self.assertEqual(raw, self.raw)
            return real_check(raw)
        with patch('os.open', side_effect=opening), patch.object(self.api, 'check_serialized_recording_input', side_effect=checked):
            self.assertEqual(self.run_api(), self.expected())
        self.assertEqual(len(opened), 1)

    def test_api_path_replacement_after_capture_does_not_reopen_or_change_input(self):
        original = self.raw
        check = self.api.check_serialized_recording_input
        def replacing(raw):
            self.file.write_bytes(b'changed after capture')
            self.assertEqual(raw, original)
            return check(raw)
        with patch.object(self.api, 'check_serialized_recording_input', side_effect=replacing):
            result = self.run_api()
        self.assertEqual(result, self.expected())
        self.assertEqual(self.file.read_bytes(), b'changed after capture')

    def test_api_empty_and_oversized_files_reject_without_steps(self):
        for raw in (b'', b' ' * 1048577):
            self.save(raw)
            self.rejected(self.run_api, self.api.RecordingInputRunError, 'RECORDING_DIAGNOSTICS_INPUT_SIZE')

    def test_api_nonregular_symlink_and_symlink_parent_reject_without_blocking(self):
        link = self.folder / 'link'
        link.symlink_to(self.file)
        parent = self.root / 'linked'
        parent.symlink_to(self.folder, target_is_directory=True)
        fifo = self.folder / 'fifo'
        os.mkfifo(fifo)
        for path in (None, str(self.file), self.folder, link, parent / self.file.name, fifo, self.folder / 'missing'):
            self.rejected(lambda path=path: self.api.run_recording_input(path, self.digest()),
                self.api.RecordingInputRunError, 'RECORDING_DIAGNOSTICS_INPUT_FILE')

    def test_api_readonly_relative_space_path_preserves_input(self):
        self.file.chmod(0o444)
        before = self.snapshot()
        relative = Path(os.path.relpath(self.file, Path.cwd()))
        self.assertEqual(self.api.run_recording_input(relative, self.digest()), self.expected())
        self.assertEqual(self.snapshot(), before)

    def test_api_noncanonical_or_malformed_input_does_not_run_prefix(self):
        for raw in (self.raw.rstrip(), b' ' + self.raw, b'\xff', b'{', b'{"x":NaN}'):
            self.save(raw)
            self.rejected(self.run_api, self.codec.RecordingInputCodecError, 'RECORDING_INPUT_SERIALIZATION')

    def test_api_late_semantic_failure_rejects_whole_input_before_steps(self):
        payload = json.loads(self.raw)
        payload['contexts'][-1]['current_driver_hex'] = '0x1.999999999999ap-4'
        self.save(canonical(payload))
        self.rejected(self.run_api, self.base.preflight.RecordingPreflightError, 'RECORDING_PREFLIGHT_INPUT:2:MODEL_DRIVER')

    def test_api_bare_recording_format_is_not_guessed_or_repaired(self):
        self.save(self.base.codec.encode_recording(self.recording))
        self.rejected(self.run_api, self.codec.RecordingInputCodecError, 'RECORDING_INPUT_SERIALIZATION')

    def test_api_all_actual_authority_flags_and_policy_values_remain_blocked(self):
        result = self.run_api()
        for key in ('first_frame_transition_checked', 'prehistory_checked', 'source_identity_reauthenticated',
                'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
            self.assertIs(result[key], False)
        self.assertEqual(result['gates'], self.expected()['gates'])

    def test_api_maximum_complete_input_runs_and_reports_all_127_transitions(self):
        base = self.recording.records[0]
        frames = tuple(replace(base, request=replace(base.request, sequence=7 + i, sample_time_ns=i,
            requested_binary32=bytes.fromhex('00000000')), limited_state_at_entry=0, saved_limited_state=0,
            angle_counter_at_entry=0, saved_angle_counter=0) for i in range(128))
        contexts = tuple(replace(self.contexts[0], model_index=3969 + i, previous_integer_request=0,
            current_driver=0.0, current_angle_deg=0.0) for i in range(127))
        self.save(self.codec.encode_recording_input(self.base.recorder.FinishedSyntheticRecordingV1(frames), contexts))
        result, counts = self.base.counted(self.run_api)
        self.assertEqual((result['status'], result['frame_count'], result['checked_transition_count']), ('MATCH', 128, 127))
        self.assertEqual((len(result['rows']), result['rows'][-1]['computed_next_state']), (127, state(4096, 0, 0, 0)))
        self.assertEqual(counts, {'step': 127, 'simulate': 0})

    def test_api_exact_capture_keeps_binary_words_and_auxiliary_hex_bytes(self):
        payload = json.loads(self.raw)
        payload['contexts'][0]['current_driver_hex'] = '-0x0.0p+0'
        self.save(canonical(payload))
        original = self.raw
        seen = []
        check = self.api.check_serialized_recording_input
        def checked(raw):
            seen.append(raw)
            return check(raw)
        with patch.object(self.api, 'check_serialized_recording_input', side_effect=checked):
            result = self.run_api()
        self.assertEqual(seen, [original])
        self.assertEqual((result['input_sha256'], result['input_bytes']), (self.digest(), len(original)))
        self.assertEqual(self.file.read_bytes(), original)

    def test_api_late_value_error_preserves_existing_error_and_prior_work(self):
        original = self.model.step
        calls = []
        def step(*args):
            calls.append(1)
            if len(calls) == 3: raise ValueError('SECRET_DEPENDENCY')
            return original(*args)
        with patch.object(self.model, 'step', side_effect=step), self.assertRaises(self.base.sequence.SequenceCheckError) as found:
            self.run_api()
        self.assertEqual(found.exception.code, 'SEQUENCE_TRANSITION:2:TRANSITION_MODEL_FAILURE')
        self.assertEqual(len(calls), 3)

    def test_api_unexpected_execution_error_is_not_rewritten_or_retried(self):
        original = self.model.step
        calls, failure = [], RuntimeError('SECRET_DEPENDENCY')
        def step(*args):
            calls.append(1)
            if len(calls) == 3: raise failure
            return original(*args)
        with patch.object(self.model, 'step', side_effect=step), self.assertRaises(RuntimeError) as found:
            self.run_api()
        self.assertIs(found.exception, failure)
        self.assertEqual(len(calls), 3)

    def test_api_read_failure_closes_fd_and_executes_no_model(self):
        real_open, opened = os.open, []
        def opening(*a, **kw):
            fd = real_open(*a, **kw)
            opened.append(fd)
            return fd
        with patch('os.open', side_effect=opening), patch('os.read', side_effect=OSError('SECRET_READ')):
            self.rejected(self.run_api, self.api.RecordingInputRunError, 'RECORDING_DIAGNOSTICS_INPUT_FILE')
        self.assertEqual(len(opened), 1)
        with self.assertRaises(OSError): os.fstat(opened[0])

    def test_api_short_reads_complete_original_bytes_without_truncation(self):
        original = os.read
        with patch('os.read', side_effect=lambda fd, size: original(fd, min(size, 17))):
            self.assertEqual(self.run_api(), self.expected())

    def test_api_misreported_small_stat_cannot_bypass_actual_read_cap(self):
        self.save(b' ' * 1048577)
        original, read, amounts = os.fstat, os.read, []
        def info(fd):
            values = list(original(fd))
            values[6] = 1
            return os.stat_result(values)
        def reading(fd, size):
            raw = read(fd, size)
            amounts.append(len(raw))
            return raw
        with patch('os.fstat', side_effect=info), patch('os.read', side_effect=reading):
            self.rejected(self.run_api, self.api.RecordingInputRunError, 'RECORDING_DIAGNOSTICS_INPUT_SIZE')
        self.assertEqual(sum(amounts), 1048577)

    def test_cli_real_subprocess_emits_literal_canonical_json_and_exit_zero(self):
        result = self.command()
        self.assertEqual((result.returncode, result.stderr), (0, b''))
        self.assertEqual(result.stdout, canonical(self.expected()))

    def test_cli_difference_exit_one_keeps_all_rows_and_literal_difference(self):
        self.difference()
        code, raw, err = self.invoke()
        self.assertEqual((code, err), (1, ''))
        result = json.loads(raw)
        self.assertEqual((result['status'], result['new_synthetic_model_steps'], result['differing_transition_indices']), ('DIFFERENT', 3, [0]))
        self.assertEqual([row['computed_next_state']['previous_applied'] for row in result['rows']], [2, 5, 4])

    def test_cli_invalid_syntax_and_digest_precede_project_import_and_input_access(self):
        importing = builtins.__import__
        def guarded(name, *a, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')): raise AssertionError('PROJECT_IMPORT')
            return importing(name, *a, **kw)
        args = self.args()
        variants = ([], args[1:], args[:-2], args + ['--run'], args + args[1:3], args + args[3:],
            args + ['--rate-budget-per-s', '0'], args + ['--contexts', 'SECRET'], args + ['--output', 'SECRET'],
            ['--r', *args[1:]], ['--run', '--input-file', '', *args[3:]], args[:-1] + ['A' * 64])
        for argv in variants:
            out, err = StringIO(), StringIO()
            with patch('builtins.__import__', side_effect=guarded), patch('os.open', side_effect=AssertionError('INPUT_OPEN')), \
                    patch('sys.stdout', out), patch('sys.stderr', err), self.assertRaises(SystemExit) as found:
                self.cli.main(argv)
            self.assertEqual((found.exception.code, out.getvalue(), err.getvalue()),
                (2, '', 'REJECTED: RECORDING_DIAGNOSTICS_USAGE_NO_MODEL_EXECUTION\n'))

    def test_cli_help_has_no_project_import_or_model_and_restores_globals(self):
        importing, before = builtins.__import__, list(sys.path)
        def guarded(name, *a, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')): raise AssertionError('PROJECT_IMPORT')
            return importing(name, *a, **kw)
        out = StringIO()
        with patch.object(sys, 'dont_write_bytecode', False), patch('builtins.__import__', side_effect=guarded), \
                patch('os.open', side_effect=AssertionError('INPUT_OPEN')), patch('sys.stdout', out), self.assertRaises(SystemExit) as found:
            try: self.cli.main(['--help'])
            finally:
                self.assertFalse(sys.dont_write_bytecode)
                self.assertEqual(sys.path, before)
        self.assertEqual(found.exception.code, 0)
        self.assertIn('--expected-sha256', out.getvalue())

    def test_cli_cold_main_suppresses_bytecode_even_with_prefix_inside_input(self):
        script = '''import sys
sys.dont_write_bytecode=True
import importlib.util,importlib._bootstrap_external as external
source,folder,*args=sys.argv[1:]
spec=importlib.util.spec_from_file_location('cold_core61',source)
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
writes=[]
def store(self,path,data,**kw):writes.append(path)
external.SourceFileLoader.set_data=store
before=list(sys.path);sys.pycache_prefix=folder;sys.dont_write_bytecode=False
code=cli.main(args)
assert not writes,writes
assert sys.path==before and sys.dont_write_bytecode is False and sys.pycache_prefix==folder
sys.dont_write_bytecode=True
raise SystemExit(code)
'''
        before = self.snapshot()
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(self.script), str(self.folder), *self.args()], capture_output=True)
        self.assertEqual((result.returncode, result.stderr, result.stdout), (0, b'', canonical(self.expected())))
        self.assertEqual(self.snapshot(), before)

    def test_cli_readonly_input_and_layout_are_preserved(self):
        self.file.chmod(0o444)
        self.folder.chmod(0o555)
        before = self.snapshot()
        result = self.command()
        self.assertEqual((result.returncode, result.stderr), (0, b''))
        self.assertEqual(self.snapshot(), before)

    def test_cli_unrelated_cwd_and_spaces_do_not_change_literal_result(self):
        before = self.snapshot()
        result = self.command()
        self.assertEqual((result.returncode, result.stdout), (0, canonical(self.expected())))
        self.assertEqual(self.snapshot(), before)

    def test_cli_checksum_failure_is_fixed_exit_two_without_raw_path(self):
        result = self.command(self.args()[:-1] + ['0' * 64])
        self.assertEqual((result.returncode, result.stdout, result.stderr),
            (2, b'', b'REJECTED: RECORDING_DIAGNOSTICS_INPUT_CHECKSUM\n'))

    def test_cli_codec_and_late_preflight_errors_emit_no_success_and_zero_steps(self):
        payload = json.loads(self.raw)
        payload['contexts'][-1]['current_driver_hex'] = '0x1.999999999999ap-4'
        for raw, code in ((b'{', 'RECORDING_INPUT_SERIALIZATION'),
                (canonical(payload), 'RECORDING_PREFLIGHT_INPUT:2:MODEL_DRIVER')):
            self.save(raw)
            result, counts = self.base.counted(self.invoke)
            self.assertEqual(result, (2, b'', 'REJECTED: ' + code + '\n'))
            self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_cli_late_model_failure_does_not_claim_zero_work_or_leak_values(self):
        original, calls = self.model.step, []
        def step(*args):
            calls.append(1)
            if len(calls) == 3: raise ValueError('SECRET_MODEL_VALUE')
            return original(*args)
        with patch.object(self.model, 'step', side_effect=step):
            code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: RECORDING_DIAGNOSTICS_FAILED_WORK_MAY_BE_NONZERO\n'))
        self.assertEqual(len(calls), 3)

    def test_cli_unexpected_execution_error_is_fixed_and_never_retried(self):
        original, calls = self.model.step, []
        def step(*args):
            calls.append(1)
            if len(calls) == 3: raise RuntimeError('SECRET_MODEL_VALUE')
            return original(*args)
        with patch.object(self.model, 'step', side_effect=step):
            code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: RECORDING_DIAGNOSTICS_FAILED_WORK_MAY_BE_NONZERO\n'))
        self.assertEqual(len(calls), 3)

    def test_cli_project_import_failure_is_fixed_and_restores_globals(self):
        importing, paths = builtins.__import__, list(sys.path)
        def guarded(name, *a, **kw):
            if name == 'integration_tools.recording_input_run': raise ImportError('SECRET_IMPORT')
            return importing(name, *a, **kw)
        with patch.object(sys, 'dont_write_bytecode', False), patch('builtins.__import__', side_effect=guarded):
            code, raw, err = self.invoke()
            self.assertEqual(sys.path, paths)
            self.assertFalse(sys.dont_write_bytecode)
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: RECORDING_DIAGNOSTICS_FAILED_WORK_MAY_BE_NONZERO\n'))

    def test_cli_unknown_api_status_never_becomes_success_or_difference(self):
        with patch.object(self.api, 'run_recording_input', return_value=dict(self.expected(), status='UNKNOWN')):
            code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: RECORDING_DIAGNOSTICS_FAILED_WORK_MAY_BE_NONZERO\n'))

    def test_cli_serialization_failure_emits_no_partial_success_record(self):
        output = importlib.import_module('integration_tools.scenario_output')
        with patch.object(output, 'canonical', side_effect=ValueError('SECRET_SERIALIZATION')):
            code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: RECORDING_DIAGNOSTICS_FAILED_WORK_MAY_BE_NONZERO\n'))

    def test_cli_output_size_guard_rejects_before_first_stdout_byte(self):
        output = importlib.import_module('integration_tools.scenario_output')
        with patch.object(output, 'canonical', return_value=b'x' * 1048577):
            code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, b'', 'REJECTED: RECORDING_DIAGNOSTICS_FAILED_WORK_MAY_BE_NONZERO\n'))

    def test_cli_short_stdout_writes_complete_the_literal_receipt(self):
        original = os.write
        with patch('os.write', side_effect=lambda fd, raw: original(fd, raw[:7])):
            code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (0, canonical(self.expected()), ''))

    def test_cli_nonpositive_stdout_write_fails_without_retry(self):
        for amount in (0, -1):
            calls = []
            def writing(fd, raw, amount=amount, calls=calls):
                calls.append(1)
                return amount
            with patch('os.write', side_effect=writing):
                code, raw, err = self.invoke()
            self.assertEqual(calls, [1])
            self.assertEqual((code, raw, err), (2, b'', 'REJECTED: RECORDING_DIAGNOSTICS_FAILED_WORK_MAY_BE_NONZERO\n'))

    def test_cli_partial_stdout_failure_is_exit_two_and_retains_only_prefix(self):
        original, calls = os.write, []
        def writing(fd, raw):
            calls.append(1)
            if len(calls) > 1: raise OSError('SECRET_BROKEN_PIPE')
            return original(fd, raw[:13])
        with patch('os.write', side_effect=writing):
            code, raw, err = self.invoke()
        self.assertEqual((code, raw, err), (2, canonical(self.expected())[:13], 'REJECTED: RECORDING_DIAGNOSTICS_FAILED_WORK_MAY_BE_NONZERO\n'))

    def test_cli_broken_diagnostic_stream_cannot_turn_failure_into_success(self):
        class Broken(StringIO):
            def write(self, text): raise OSError('SECRET_STDERR')
        with patch('sys.stderr', Broken()), patch.object(self.api, 'run_recording_input', side_effect=RuntimeError('SECRET_API')):
            self.assertEqual(self.cli.main(self.args()), 2)

    def test_cli_help_stream_failure_is_fixed_operational_exit_two(self):
        class Broken(StringIO):
            def write(self, text): raise OSError('SECRET_HELP')
        err = StringIO()
        with patch('sys.stdout', Broken()), patch('sys.stderr', err):
            self.assertEqual(self.cli.main(['--help']), 2)
        self.assertEqual(err.getvalue(), 'REJECTED: RECORDING_DIAGNOSTICS_FAILED_WORK_MAY_BE_NONZERO\n')

    def test_cli_never_probes_or_allocates_temporary_cache(self):
        before, prefix = self.snapshot(), sys.pycache_prefix
        with patch.dict(os.environ, {key: str(self.folder) for key in ('TMPDIR', 'TEMP', 'TMP')}), \
                patch.object(tempfile, 'tempdir', str(self.folder)), patch.object(tempfile, 'gettempdir', side_effect=AssertionError('TEMP_PROBE')), \
                patch.object(tempfile, 'TemporaryDirectory', side_effect=AssertionError('TEMP_ALLOCATION')):
            self.assertEqual(self.invoke(), (0, canonical(self.expected()), ''))
            self.assertEqual(tempfile.tempdir, str(self.folder))
        self.assertEqual((self.snapshot(), sys.pycache_prefix), (before, prefix))

    def test_cli_success_and_error_restore_global_paths_and_bytecode_flag(self):
        for failed in (False, True):
            with patch.object(sys, 'dont_write_bytecode', False), patch.object(sys, 'path', [*sys.path, 'caller-marker']):
                before = list(sys.path)
                if failed:
                    with patch.object(self.api, 'run_recording_input', side_effect=RuntimeError('SECRET_API')): code, _, _ = self.invoke()
                else:
                    code, _, _ = self.invoke()
                self.assertEqual(code, 2 if failed else 0)
                self.assertFalse(sys.dont_write_bytecode)
                self.assertEqual(sys.path, before)

    def test_cli_forbidden_dependencies_stay_unimported_and_real_model_runs_three(self):
        script = '''import importlib.abc,runpy,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  forbidden=('openpilot','opendbc','numpy','integration_tools.fixed_model_reference','integration_tools.sequence_reference')
  if any(fullname==n or fullname.startswith(n+'.') for n in forbidden) or fullname.startswith(('integration_tools.f61_','synthetic_rate_constraint_feasibility')):raise AssertionError('FORBIDDEN:'+fullname)
counts={'step':0,'simulate':0}
def profile(frame,event,arg):
 if event=='call' and frame.f_globals.get('__name__','').startswith('cyberlateral_dev') and frame.f_code.co_name in counts:counts[frame.f_code.co_name]+=1
sys.meta_path.insert(0,Block());sys.setprofile(profile);sys.argv=sys.argv[1:]
try:runpy.run_path(sys.argv[0],run_name='__main__')
except SystemExit as end:
 assert end.code==0 and counts=={'step':3,'simulate':0},(end.code,counts)
 raise
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(self.script), *self.args()], capture_output=True, cwd=self.root)
        self.assertEqual((result.returncode, result.stderr, result.stdout), (0, b'', canonical(self.expected())))

    def test_cli_independent_processes_are_deterministic_and_do_not_write_input(self):
        before = self.snapshot()
        one, two = self.command(), self.command()
        self.assertEqual((one.returncode, two.returncode, one.stderr, two.stderr), (0, 0, b'', b''))
        self.assertEqual(one.stdout, two.stdout)
        self.assertEqual(one.stdout, canonical(self.expected()))
        self.assertEqual(self.snapshot(), before)
