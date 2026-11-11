"""Catch unpinned reads, rehashed row corruption, replay and false inspect exits."""

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
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

import test_recording_input_cli as fixtures
from v1_helpers import ROOT


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class SavedRecordingDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/recording_diagnostics_saved.py').is_file(), 'Missing CORE66 saved reader')
        self.script = ROOT / 'tools/recording_diagnostics_inspect.py'
        self.assertTrue(self.script.is_file(), 'Missing CORE66 inspect CLI')
        self.fixture = fixtures.RecordingInputCliTests('test_api_match_emits_independent_literal_three_row_projection')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.saved = self.root / 'saved result'
        self.saved.mkdir()
        self.value = self.fixture.expected()
        self.persist()
        self.m: Any = importlib.import_module('integration_tools.recording_diagnostics_saved')
        spec = importlib.util.spec_from_file_location('core66_test_cli', self.script)
        assert spec is not None and spec.loader is not None
        self.cli: Any = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.cli)

    def persist(self, value=None, raw=None, manifest=None):
        self.raw = canonical(self.value if value is None else value) if raw is None else raw
        (self.saved / 'DIAGNOSTICS.json').write_bytes(self.raw)
        checksum = (hashlib.sha256(self.raw).hexdigest() + '  DIAGNOSTICS.json\n').encode()
        (self.saved / 'SHA256SUMS.txt').write_bytes(checksum if manifest is None else manifest)

    def digest(self):
        return hashlib.sha256(self.raw).hexdigest()

    def inspect(self):
        return self.m.inspect_recording_diagnostics(self.saved, self.digest())

    def args(self):
        return ['--input-root', str(self.saved), '--expected-sha256', self.digest()]

    def expected(self, record=None):
        value = self.value if record is None else record
        return {'schema_version': 1, 'contract_id': 'CORE66_SAVED_RECORDING_DIAGNOSTICS_INSPECTION_V1',
            'inspection_status': 'SAVED_DIAGNOSTICS_CONSISTENT', 'inspection_exit_code': 0,
            'saved_status': value['status'], 'saved_diagnostic_exit_code': 0 if value['status'] == 'MATCH' else 1,
            'diagnostics_sha256': self.digest(), 'diagnostics_bytes': len(self.raw),
            'recorded_model_steps': value['new_synthetic_model_steps'], 'new_synthetic_model_steps': 0,
            'new_reference_steps': 0, 'numeric_validation_work': 'NONZERO_NOT_AGGREGATED', 'stored_record': value,
            'arithmetic_recomputed': False, 'original_input_verified': False, 'source_identity_reauthenticated': False,
            'first_frame_transition_checked': False, 'prehistory_checked': False, 'v4_payload_allowed': False,
            'f61_input_allowed': False, 'actual_activation_allowed': False, 'gates': self.value['gates'],
            'scope': 'CHECKED_CAPTURED_SAVED_RELATIONS_NOT_NUMERICAL_OR_ORIGIN_PROOF'}

    def different(self):
        value = copy.deepcopy(self.value)
        value['status'] = 'DIFFERENT'
        value['differing_transition_indices'] = [0]
        value['rows'][0].update(status='DIFFERENT', declared_saved_state={'saved_limited_state': 10, 'saved_angle_counter': 5},
            differences=[{'field': 'saved_limited_state', 'declared': 10, 'computed': 2}])
        value['rows'][1]['declared_entry_state']['previous_applied'] = 10
        for i, applied in ((1, 5), (2, 4)):
            value['rows'][i]['computed_next_state']['previous_applied'] = applied
            value['rows'][i]['declared_saved_state']['saved_limited_state'] = applied
        value['rows'][2]['declared_entry_state']['previous_applied'] = 5
        return value

    def rejected(self, call=None, code=None):
        def check():
            with self.assertRaises(self.m.SavedDiagnosticsError) as found:
                (self.inspect if call is None else call)()
            if code is not None:
                self.assertEqual((found.exception.code, str(found.exception)), (code, code))
        _, counts = self.fixture.base.counted(check)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def invalid(self, change, code=None):
        value = copy.deepcopy(self.value)
        change(value)
        self.persist(value)
        self.rejected(code=code)

    def command(self, args=None, script=None):
        command = [sys.executable, '-I', '-B']
        if script is not None:
            command.extend(['-c', script])
        command.extend([str(self.script), *(self.args() if args is None else args)])
        return subprocess.run(command, cwd=self.root, capture_output=True)

    def invoke(self, args=None):
        err = StringIO()
        path = self.root / 'stdout.bin'
        with path.open('wb') as out, patch('sys.stdout', out), patch('sys.stderr', err):
            code = self.cli.main(self.args() if args is None else args)
        return code, path.read_bytes(), err.getvalue()

    def snapshot(self):
        return {p.name: (p.read_bytes(), p.stat().st_mode) for p in self.saved.iterdir()}

    # Break: treating historical work as new work or dropping/rewriting original rows.
    def test_match_literal_receipt_preserves_all_rows_with_zero_new_steps(self):
        result, counts = self.fixture.base.counted(self.inspect)
        self.assertEqual(result, self.expected())
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_different_preserves_declared_feed_and_historical_work(self):
        value = self.different()
        self.persist(value)
        result, counts = self.fixture.base.counted(self.inspect)
        self.assertEqual(result, self.expected(value))
        self.assertEqual((result['inspection_exit_code'], result['saved_diagnostic_exit_code']), (0, 1))
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_real_core64_publication_is_compatible_without_second_execution(self):
        producer = importlib.import_module('integration_tools.recording_input_workflow')
        target = self.root / 'real output'
        producer.publish_recording_input(self.fixture.file, self.fixture.digest(), target)
        raw = (target / 'DIAGNOSTICS.json').read_bytes()
        result, counts = self.fixture.base.counted(lambda: self.m.inspect_recording_diagnostics(target, hashlib.sha256(raw).hexdigest()))
        self.assertEqual(result['stored_record'], self.value)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_readonly_relative_input_bytes_modes_and_layout_unchanged(self):
        for path in self.saved.iterdir():
            path.chmod(0o444)
        self.saved.chmod(0o555)
        self.addCleanup(lambda: self.saved.chmod(0o700))
        before = self.snapshot()
        relative = Path(os.path.relpath(self.saved, Path.cwd()))
        self.assertEqual(self.m.inspect_recording_diagnostics(relative, self.digest()), self.expected())
        self.assertEqual(self.snapshot(), before)

    def test_one_capture_per_file_all_descriptors_closed_before_parse(self):
        original, parse = os.open, self.m._parse
        opened = []
        def opening(path, flags, *args, **kw):
            fd = original(path, flags, *args, **kw)
            opened.append((path, fd))
            return fd
        def parsing(raw):
            self.assertEqual(len(opened), 3)
            for _, fd in opened:
                with self.assertRaises(OSError):
                    os.fstat(fd)
            return parse(raw)
        with patch('os.open', side_effect=opening), patch.object(self.m, '_parse', side_effect=parsing):
            self.assertEqual(self.inspect(), self.expected())
        self.assertEqual([name for name, _ in opened[1:]], ['DIAGNOSTICS.json', 'SHA256SUMS.txt'])

    def test_capture_uses_only_readonly_nofollow_nonblocking_close_on_exec(self):
        original = os.open
        def opening(path, flags, *args, **kw):
            self.assertEqual(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC), 0)
            self.assertEqual(flags & (os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC), os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
            return original(path, flags, *args, **kw)
        with patch('os.open', side_effect=opening):
            self.assertEqual(self.inspect(), self.expected())

    def test_replacement_after_capture_does_not_reopen_or_change_parsed_bytes(self):
        parse = self.m._parse
        original = self.raw
        def parsing(raw):
            self.assertEqual(raw, original)
            (self.saved / 'DIAGNOSTICS.json').write_bytes(b'changed later')
            return parse(raw)
        with patch.object(self.m, '_parse', side_effect=parsing):
            self.assertEqual(self.inspect(), self.expected())
        self.assertEqual((self.saved / 'DIAGNOSTICS.json').read_bytes(), b'changed later')

    def test_malformed_external_sha_precedes_all_caller_path_work(self):
        for digest in (None, True, '', b'a' * 64, 'A' * 64, 'g' * 64, 'a' * 63, 'a' * 64 + '\n'):
            with patch.object(Path, 'absolute', side_effect=AssertionError('path')), patch('os.open', side_effect=AssertionError('open')):
                self.rejected(lambda digest=digest: self.m.inspect_recording_diagnostics(self.saved, digest), 'SAVED_DIAGNOSTICS_EXPECTED_SHA256')

    def test_wrong_external_sha_rejects_even_with_matching_internal_manifest(self):
        self.rejected(lambda: self.m.inspect_recording_diagnostics(self.saved, '0' * 64), 'SAVED_DIAGNOSTICS_CHECKSUM')

    def test_stale_manifest_rejected_even_with_correct_external_sha(self):
        (self.saved / 'SHA256SUMS.txt').write_bytes(b'0' * 64 + b'  DIAGNOSTICS.json\n')
        self.rejected(code='SAVED_DIAGNOSTICS_CHECKSUM')

    def test_manifest_is_exact_not_permissive_checksum_text(self):
        good = (self.saved / 'SHA256SUMS.txt').read_bytes()
        for raw in (good.rstrip(), good.upper(), good + good, good.replace(b'  ', b' '), good.replace(b'DIAGNOSTICS', b'OTHER')):
            self.persist(manifest=raw)
            self.rejected(code='SAVED_DIAGNOSTICS_CHECKSUM')

    def test_missing_or_extra_members_are_not_silently_ignored(self):
        extra = self.saved / 'EXTRA'
        extra.write_bytes(b'not accepted')
        self.rejected(code='SAVED_DIAGNOSTICS_INPUT')
        extra.unlink()
        (self.saved / 'SHA256SUMS.txt').unlink()
        self.rejected(code='SAVED_DIAGNOSTICS_INPUT')

    def test_symlink_and_fifo_members_are_rejected_without_blocking(self):
        target = self.saved / 'DIAGNOSTICS.json'
        target.unlink()
        target.symlink_to(self.fixture.file)
        self.rejected(code='SAVED_DIAGNOSTICS_INPUT')
        target.unlink()
        os.mkfifo(target)
        self.rejected(code='SAVED_DIAGNOSTICS_INPUT')

    def test_invalid_root_and_ancestor_symlink_are_fixed_rejections(self):
        link = self.root / 'link'
        link.symlink_to(self.root, target_is_directory=True)
        for value in (link / self.saved.name, self.fixture.file, self.root / 'missing', Path('bad\0path'), Path('bad\ud800'), 'not Path'):
            self.rejected(lambda value=value: self.m.inspect_recording_diagnostics(value, self.digest()), 'SAVED_DIAGNOSTICS_INPUT')

    def test_empty_and_oversize_files_reject_before_success(self):
        for raw, manifest in ((b'', None), (b'x' * 1048577, None), (self.raw, b'x' * 513), (self.raw, b'')):
            self.persist(raw=raw, manifest=manifest)
            self.rejected()

    def test_short_reads_are_completed_without_truncating_json(self):
        original = os.read
        with patch('os.read', side_effect=lambda fd, count: original(fd, min(count, 11))):
            self.assertEqual(self.inspect(), self.expected())

    def test_actual_read_cap_holds_even_with_misleading_fstat_size(self):
        self.persist(raw=b'x' * 1048577)
        original = os.fstat
        def statting(fd):
            values = list(original(fd))
            values[6] = 0
            return os.stat_result(values)
        with patch('os.fstat', side_effect=statting):
            self.rejected(code='SAVED_DIAGNOSTICS_INPUT')

    def test_read_failure_closes_every_open_descriptor(self):
        original = os.open
        opened = []
        def opening(*args, **kw):
            fd = original(*args, **kw)
            opened.append(fd)
            return fd
        with patch('os.open', side_effect=opening), patch('os.read', side_effect=OSError('SECRET')):
            self.rejected(code='SAVED_DIAGNOSTICS_INPUT')
        self.assertEqual(len(opened), 2)
        for fd in opened:
            with self.assertRaises(OSError):
                os.fstat(fd)

    def test_root_identity_change_before_capture_exit_is_rejected(self):
        original_read, original_stat = self.m._read_file, Path.stat
        reads = []
        def reading(*args):
            raw = original_read(*args)
            reads.append(args[1])
            return raw
        def statting(path, *args, **kw):
            info = original_stat(path, *args, **kw)
            if path == self.saved and len(reads) == 2 and kw.get('follow_symlinks') is False:
                values = list(info)
                values[1] += 1
                return os.stat_result(values)
            return info
        with patch.object(self.m, '_read_file', side_effect=reading), patch.object(Path, 'stat', statting):
            self.rejected(code='SAVED_DIAGNOSTICS_INPUT')

    def test_json_rejects_duplicates_floats_nonfinite_depth_and_noncanonical_bytes(self):
        for raw in (self.raw.rstrip(), b' ' + self.raw, b'\xff', b'{', b'{"x":1,"x":1}\n',
                b'{"x":1.0}\n', b'{"x":NaN}\n', b'{"x":' + b'1' * 33 + b'}\n', b'[' * 70 + b'0' + b']' * 70 + b'\n'):
            self.persist(raw=raw)
            self.rejected(code='SAVED_DIAGNOSTICS_JSON')

    def test_header_exact_keys_literals_and_declared_input_identity(self):
        changes = (lambda d: d.pop('scope'), lambda d: d.update(extra=1), lambda d: d.update(schema_version=True),
            lambda d: d.update(contract_id='OTHER'), lambda d: d.update(scope='ACTUAL'),
            lambda d: d.update(validation_claim='SOURCE_PROVEN'), lambda d: d.update(state_feed_rule='COMPUTED_ROLLOUT'),
            lambda d: d.update(input_sha256='A' * 64), lambda d: d.update(input_bytes=False), lambda d: d.update(input_bytes=1048577))
        for change in changes:
            self.invalid(change, 'SAVED_DIAGNOSTICS_RECORD')

    def test_authority_flags_and_gates_require_exact_types_and_blocked_values(self):
        for key in ('first_frame_transition_checked', 'prehistory_checked', 'source_identity_reauthenticated',
                'v4_payload_allowed', 'f61_input_allowed', 'actual_activation_allowed'):
            for value in (0, True, None):
                self.invalid(lambda d, key=key, value=value: d.update({key: value}), 'SAVED_DIAGNOSTICS_RECORD')
        for key, value in (('F61_calculator_executions', False), ('actual_r', 0), ('T2', 0), ('vehicle_scale', 409),
                ('STATIC_EVIDENCE_GATE', 'PASS'), ('extra', 0)):
            self.invalid(lambda d, key=key, value=value: d['gates'].update({key: value}), 'SAVED_DIAGNOSTICS_RECORD')

    def test_frame_and_work_counts_reject_missing_rows_boolean_or_wrong_totals(self):
        for key, value in (('frame_count', 1), ('frame_count', 129), ('frame_count', True),
                ('checked_transition_count', 2), ('new_synthetic_model_steps', 0), ('new_synthetic_model_steps', True)):
            self.invalid(lambda d, key=key, value=value: d.update({key: value}), 'SAVED_DIAGNOSTICS_RECORD')
        self.invalid(lambda d: d.update(rows=d['rows'][:-1]), 'SAVED_DIAGNOSTICS_ROWS')

    def test_row_shape_and_transition_ordinals_cannot_be_rehashed_away(self):
        for change in (lambda d: d['rows'][0].update(extra=1), lambda d: d['rows'][0].pop('status'),
                lambda d: d['rows'][0].update(transition_index=False), lambda d: d['rows'][1].update(transition_index=0),
                lambda d: d['rows'][1].update(model_index=True)):
            self.invalid(change, 'SAVED_DIAGNOSTICS_ROWS')

    def test_state_domains_and_index_increment_are_exact(self):
        for name, key, value in (('declared_entry_state', 'previous_requested', -2049),
                ('declared_entry_state', 'previous_applied', True), ('computed_next_state', 'previous_applied', 2049),
                ('computed_next_state', 'angle_counter', 91), ('computed_next_state', 'angle_counter', -1),
                ('computed_next_state', 'index', 5), ('declared_entry_state', 'index', 4)):
            self.invalid(lambda d, name=name, key=key, value=value: d['rows'][0][name].update({key: value}), 'SAVED_DIAGNOSTICS_ROWS')
        self.invalid(lambda d: d['rows'][0]['declared_saved_state'].update(saved_limited_state=False), 'SAVED_DIAGNOSTICS_ROWS')

    def test_model_index_gaps_reject_even_when_each_row_local_indices_match(self):
        def changed(value):
            for row, index in zip(value['rows'][1:], (7, 8)):
                row['model_index'] = row['declared_entry_state']['index'] = index
                row['computed_next_state']['index'] = index + 1
        self.invalid(changed, 'SAVED_DIAGNOSTICS_ROWS')

    def test_computed_rollout_cannot_replace_declared_saved_state_link(self):
        value = self.different()
        value['rows'][1]['declared_entry_state']['previous_applied'] = 2
        self.persist(value)
        self.rejected(code='SAVED_DIAGNOSTICS_ROWS')
        self.invalid(lambda d: d['rows'][1]['declared_entry_state'].update(angle_counter=4), 'SAVED_DIAGNOSTICS_ROWS')

    def test_adjacent_requested_state_is_not_previous_applied_state(self):
        self.invalid(lambda d: d['rows'][1]['declared_entry_state'].update(previous_requested=2), 'SAVED_DIAGNOSTICS_ROWS')

    def test_difference_list_exact_fields_order_values_and_types(self):
        value = self.different()
        for change in (lambda d: d['rows'][0].update(differences=[]),
                lambda d: d['rows'][0]['differences'][0].update(extra=1),
                lambda d: d['rows'][0]['differences'][0].update(field='previous_applied'),
                lambda d: d['rows'][0]['differences'][0].update(computed=False),
                lambda d: d['rows'][0].update(status='MATCH')):
            changed = copy.deepcopy(value)
            change(changed)
            self.persist(changed)
            self.rejected(code='SAVED_DIAGNOSTICS_ROWS')
        value['rows'][0]['declared_saved_state']['saved_angle_counter'] = 8
        value['rows'][1]['declared_entry_state']['angle_counter'] = 8
        value['rows'][0]['differences'].append({'field': 'saved_angle_counter', 'declared': 8, 'computed': 5})
        self.persist(value)
        self.assertEqual(self.inspect()['stored_record'], value)
        value['rows'][0]['differences'].reverse()
        self.persist(value)
        self.rejected(code='SAVED_DIAGNOSTICS_ROWS')

    def test_total_status_and_differing_indices_are_derived_from_saved_rows(self):
        for indices in ([], [False], [0, 0], [1]):
            value = self.different()
            value['differing_transition_indices'] = indices
            self.persist(value)
            self.rejected(code='SAVED_DIAGNOSTICS_ROWS')
        self.invalid(lambda d: d.update(status='DIFFERENT'), 'SAVED_DIAGNOSTICS_ROWS')

    def test_consistently_forged_arithmetic_can_pass_without_origin_or_math_claim(self):
        value = copy.deepcopy(self.value)
        value['input_sha256'] = 'b' * 64
        value['rows'][-1]['computed_next_state']['previous_applied'] = 202
        value['rows'][-1]['declared_saved_state']['saved_limited_state'] = 202
        self.persist(value)
        result, counts = self.fixture.base.counted(self.inspect)
        self.assertEqual(result, self.expected(value))
        self.assertFalse(result['arithmetic_recomputed'])
        self.assertFalse(result['original_input_verified'])
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_maximum_127_rows_and_state_upper_bound_need_no_replay(self):
        value = copy.deepcopy(self.value)
        value.update(frame_count=128, checked_transition_count=127, new_synthetic_model_steps=127, rows=[])
        for i in range(127):
            value['rows'].append({'transition_index': i, 'model_index': i + 1, 'status': 'MATCH',
                'declared_entry_state': fixtures.state(i + 1, 0, 0, 0),
                'computed_next_state': fixtures.state(i + 2, 0, 0, 0),
                'declared_saved_state': {'saved_limited_state': 0, 'saved_angle_counter': 0}, 'differences': []})
        self.persist(value)
        result, counts = self.fixture.base.counted(self.inspect)
        self.assertEqual((result['recorded_model_steps'], len(result['stored_record']['rows'])), (127, 127))
        self.assertEqual(counts, {'step': 0, 'simulate': 0})
        value.update(frame_count=2, checked_transition_count=1, new_synthetic_model_steps=1, rows=[value['rows'][0]])
        value['rows'][0].update(model_index=4095, declared_entry_state=fixtures.state(4095, -2048, -2048, 90),
            computed_next_state=fixtures.state(4096, 2048, 2048, 90),
            declared_saved_state={'saved_limited_state': 2048, 'saved_angle_counter': 90})
        self.persist(value)
        self.assertEqual(self.inspect()['stored_record'], value)

    def test_cli_valid_match_emits_exact_canonical_receipt_exit_zero(self):
        result = self.command()
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, canonical(self.expected()), b''))

    def test_cli_valid_difference_is_inspection_success_not_new_diagnosis(self):
        value = self.different()
        self.persist(value)
        (code, out, err), counts = self.fixture.base.counted(self.invoke)
        self.assertEqual((code, out, err), (0, canonical(self.expected(value)), ''))
        self.assertEqual(counts, {'step': 0, 'simulate': 0})

    def test_cli_corrupt_input_exits_two_without_success_or_writes(self):
        self.persist(raw=b'{')
        before = self.snapshot()
        self.assertEqual(self.invoke(), (2, b'', 'REJECTED: SAVED_DIAGNOSTICS_JSON\n'))
        self.assertEqual(self.snapshot(), before)

    def test_cli_usage_and_sha_syntax_precede_project_imports_and_paths(self):
        original = builtins.__import__
        def guarded(name, *args, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')):
                raise AssertionError('project import')
            return original(name, *args, **kw)
        args = self.args()
        for argv in ([], args[:-2], args + args[:2], args + args[2:], args + ['--run'], args + ['--r', '0'],
                ['--input-r', *args[1:]], args[:-1] + ['A' * 64], ['--input-root', '', *args[2:]]):
            with patch('builtins.__import__', side_effect=guarded), patch('os.open', side_effect=AssertionError('open')), \
                    patch('sys.stderr', StringIO()) as err, self.assertRaises(SystemExit) as found:
                self.cli.main(argv)
            self.assertEqual((found.exception.code, err.getvalue()),
                (2, 'REJECTED: SAVED_DIAGNOSTICS_INSPECT_USAGE_NO_MODEL_EXECUTION\n'))

    def test_cli_help_suppresses_project_imports_and_restores_globals(self):
        original, before = builtins.__import__, list(sys.path)
        def guarded(name, *args, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')):
                raise AssertionError('project import')
            return original(name, *args, **kw)
        with patch.object(sys, 'dont_write_bytecode', False), patch('builtins.__import__', side_effect=guarded), \
                patch('sys.stdout', StringIO()) as out, self.assertRaises(SystemExit) as found:
            try:
                self.cli.main(['--help'])
            finally:
                self.assertFalse(sys.dont_write_bytecode)
                self.assertEqual(sys.path, before)
        self.assertEqual(found.exception.code, 0)
        self.assertIn('--expected-sha256', out.getvalue())

    def test_cli_cold_main_has_no_bytecode_or_temp_side_effects(self):
        script = '''import sys
sys.dont_write_bytecode=True
import importlib.util,importlib._bootstrap_external as external
source,*args=sys.argv[1:]
spec=importlib.util.spec_from_file_location('cold_core66',source)
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
writes=[]
external.SourceFileLoader.set_data=lambda self,path,data,**kw:writes.append(path)
before=list(sys.path);sys.pycache_prefix=args[1];sys.dont_write_bytecode=False
code=cli.main(args)
assert not writes,writes
assert sys.path==before and sys.dont_write_bytecode is False and sys.pycache_prefix==args[1]
sys.dont_write_bytecode=True
raise SystemExit(code)
'''
        before = self.snapshot()
        result = self.command(script=script)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, canonical(self.expected()), b''))
        self.assertEqual(self.snapshot(), before)

    def test_cli_short_stdout_writes_complete_the_receipt(self):
        original = os.write
        with patch('os.write', side_effect=lambda fd, raw: original(fd, raw[:13])):
            self.assertEqual(self.invoke(), (0, canonical(self.expected()), ''))

    def test_cli_broken_and_nonpositive_stdout_are_failures_with_zero_new_steps(self):
        for value in (0, -1, None):
            def writing(_fd, _raw, value=value):
                if value is None:
                    raise BrokenPipeError('SECRET')
                return value
            before = self.snapshot()
            with patch('os.write', side_effect=writing):
                (code, out, err), counts = self.fixture.base.counted(self.invoke)
            self.assertEqual((code, out, err), (2, b'', 'REJECTED: SAVED_DIAGNOSTICS_INSPECT_FAILED_NO_MODEL_EXECUTION\n'))
            self.assertEqual(counts, {'step': 0, 'simulate': 0})
            self.assertEqual(self.snapshot(), before)

    def test_cli_partial_stdout_is_not_retried_or_retracted(self):
        original = os.write
        writes = []
        def writing(fd, raw):
            writes.append(bytes(raw))
            if len(writes) == 1:
                return original(fd, raw[:11])
            raise OSError('SECRET')
        with patch('os.write', side_effect=writing):
            code, out, err = self.invoke()
        self.assertEqual((code, out), (2, canonical(self.expected())[:11]))
        self.assertEqual(len(writes), 2)
        self.assertNotIn('SECRET', err)

    def test_cli_output_budget_and_serialization_failures_precede_stdout(self):
        for result in (b'x' * 2097153, None):
            with patch('integration_tools.scenario_output.canonical', side_effect=ValueError('SECRET') if result is None else None,
                    return_value=result):
                code, out, err = self.invoke()
            self.assertEqual((code, out, err), (2, b'', 'REJECTED: SAVED_DIAGNOSTICS_INSPECT_FAILED_NO_MODEL_EXECUTION\n'))

    def test_cli_restores_paths_and_bytecode_on_valid_and_invalid_inputs(self):
        before = list(sys.path)
        for invalid in (False, True):
            if invalid:
                self.persist(raw=b'{')
            with patch.object(sys, 'dont_write_bytecode', False):
                self.assertEqual(self.invoke()[0], 2 if invalid else 0)
                self.assertFalse(sys.dont_write_bytecode)
                self.assertEqual(sys.path, before)

    def test_fresh_processes_block_execution_imports_and_are_byte_identical(self):
        script = '''import importlib.abc,runpy,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  forbidden=('cyberlateral_dev','openpilot','opendbc','numpy','integration_tools.recording_input_run','integration_tools.recording_input_workflow','integration_tools.offline_recording_diagnostics','integration_tools.fixed_model_reference','integration_tools.sequence_reference')
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
