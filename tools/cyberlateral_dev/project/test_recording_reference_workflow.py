"""Catch repeated reference work, misleading summaries and false publication success."""

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

import test_recording_diagnostics_reference as fixtures
from v1_helpers import ROOT


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


class ReferenceWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/recording_reference_workflow.py').is_file(), 'Missing CORE70 workflow API')
        self.script = ROOT / 'tools/recording_reference_workflow.py'
        self.assertTrue(self.script.is_file(), 'Missing CORE70 workflow CLI')
        self.case = fixtures.RecordingReferenceTests('test_literal_three_row_reference_matches_with_zero_new_model_steps')
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.fixture, self.root = self.case.fixture, self.case.root
        self.output = self.root / 'published audit'
        self.m: Any = importlib.import_module('integration_tools.recording_reference_workflow')
        self.publisher: Any = importlib.import_module('integration_tools.core_sequence_archive_workflow')
        spec = importlib.util.spec_from_file_location('core70_cli_test', self.script)
        assert spec is not None and spec.loader is not None
        self.cli: Any = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.cli)

    def publish(self, output=None):
        return self.m.publish_recording_reference(self.fixture.file, self.fixture.digest(),
            self.case.saved, self.case.case.digest(), self.output if output is None else output)

    def args(self, output=None):
        return self.case.args() + ['--output-root', str(self.output if output is None else output)]

    def command(self, args=None):
        return subprocess.run([sys.executable, '-I', '-B', str(self.script), *(self.args() if args is None else args)],
                              cwd=self.root, capture_output=True)

    def invoke(self, args=None):
        err, target = StringIO(), self.root / 'receipt.stdout'
        with target.open('wb') as out, patch('sys.stdout', out), patch('sys.stderr', err):
            code = self.cli.main(self.args() if args is None else args)
        return code, target.read_bytes(), err.getvalue()

    def saved(self, receipt, output=None):
        target = self.output if output is None else output
        self.assertEqual({p.name for p in target.iterdir()}, {'REFERENCE_AUDIT.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt'})
        raw = (target / 'REFERENCE_AUDIT.json').read_bytes()
        value = json.loads(raw)
        self.assertEqual(raw, canonical(value))
        md = (target / 'SUMMARY_KO.md').read_bytes()
        self.assertLessEqual(len(md), 65536)
        want = ''.join(hashlib.sha256((target / name).read_bytes()).hexdigest() + '  ' + name + '\n'
                       for name in ('REFERENCE_AUDIT.json', 'SUMMARY_KO.md')).encode()
        self.assertEqual((target / 'SHA256SUMS.txt').read_bytes(), want)
        self.assertEqual(receipt['files'], {n: {'sha256': hashlib.sha256((target / n).read_bytes()).hexdigest(),
            'byte_size': (target / n).stat().st_size} for n in ('REFERENCE_AUDIT.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt')})
        self.assertEqual((receipt['contract_id'], receipt['status']),
                         ('CORE70_REFERENCE_AUDIT_WORKFLOW_V1', 'REFERENCE_AUDIT_PUBLISHED'))
        for k in ('audit_status', 'audit_exit_code', 'saved_diagnostic_status', 'reference_diagnostic_status',
                  'input_sha256', 'input_bytes', 'diagnostics_sha256', 'diagnostics_bytes', 'recorded_model_steps',
                  'new_synthetic_model_steps', 'new_reference_steps', 'reference_helper_counts',
                  'shared_admission_preflight', 'gates', *self.case.m.FLAGS):
            self.assertEqual(receipt[k], value[k])
        return value, md.decode()

    # Break: invoking the checker twice or publishing a reduced JSON instead of its full result.
    def test_full_literal_record_is_saved_after_one_real_checker_and_publish(self):
        with patch.object(self.m, 'check_recording_reference', wraps=self.m.check_recording_reference) as check, \
                patch.object(self.m, '_publish', wraps=self.m._publish) as publish:
            receipt, counts = self.fixture.base.counted(self.publish)
        value, md = self.saved(receipt)
        self.case.assert_receipt(value)
        self.assertEqual((check.call_count, publish.call_count, counts), (1, 1, {'step': 0, 'simulate': 0}))
        self.assertEqual(receipt['reference_helper_counts'], {'compile_calls': 1, 'selected_definitions_compiled': 2,
            'limiter_direct': 0, 'limiter_traced': 3, 'fault_explicit': 3, 'fault_default': 0, 'traced_clip_calls': 6})
        self.assertIn('참조 대조: 일치', md)
        self.assertIn('과거 기록 모델 step: 3', md)
        self.assertIn('새 모델 step: 0', md)
        self.assertIn('새 참조 step: 3', md)

    def test_saved_different_audit_match_is_not_presented_as_all_success(self):
        self.case.case.different_input()
        self.case.record = self.case.case.record
        receipt = self.publish()
        value, md = self.saved(receipt)
        self.assertEqual((value['audit_exit_code'], value['saved_diagnostic_status'], value['reference_diagnostic_status']),
                         (0, 'DIFFERENT', 'DIFFERENT'))
        self.assertIn('참조 대조: 일치', md)
        self.assertIn('저장 진단: DIFFERENT', md)
        self.assertIn('참조 진단: DIFFERENT', md)
        self.assertIn('참조 진단 차이 전이: [0]', md)
        self.assertEqual(value['reference_projection']['rows'][1]['computed_next_state']['previous_applied'], 5)

    def test_coherent_forgery_is_saved_as_audit_difference_with_exact_states(self):
        self.case.record['rows'][-1]['computed_next_state']['previous_applied'] = 202
        self.case.record['rows'][-1]['declared_saved_state']['saved_limited_state'] = 202
        self.case.persist()
        value, md = self.saved(self.publish())
        self.assertEqual((value['audit_status'], value['audit_exit_code'], value['differing_transition_indices']),
                         ('REFERENCE_DIFFERENT', 1, [2]))
        self.assertIn('참조 대조: 차이 있음', md)
        self.assertIn('202', md)
        self.assertIn('computed_next_state', md)
        self.assertIn('declared_saved_state', md)
        self.assertIn('전체 1 / 표시 1 / 생략 0', md)

    def test_missing_and_extra_saved_rows_are_explicit(self):
        original = copy.deepcopy(self.case.record)
        for extra in (False, True):
            self.case.record = copy.deepcopy(original)
            if extra:
                row = self.case.record['rows'][-1]
                added = copy.deepcopy(row)
                added.update(transition_index=3, model_index=8)
                added['declared_entry_state'] = copy.deepcopy(row['computed_next_state'])
                added['computed_next_state']['index'] = 9
                added['computed_next_state']['angle_counter'] = 8
                added['declared_saved_state']['saved_angle_counter'] = 8
                self.case.record['rows'].append(added)
            else:
                self.case.record['rows'].pop()
            count = len(self.case.record['rows'])
            self.case.record.update(frame_count=count + 1, checked_transition_count=count, new_synthetic_model_steps=count)
            self.case.persist()
            value, md = self.saved(self.publish(self.root / str(extra)), self.root / str(extra))
            self.assertEqual(value['differing_transition_indices'], [3] if extra else [2])
            self.assertIn('행 없음', md)
            self.assertIn('frame_count', md)

    def test_more_than_twenty_differences_keep_complete_json_and_exact_omission(self):
        frame = self.fixture.recording.records[0]
        frames = tuple(replace(frame, request=replace(frame.request, sequence=7 + i, sample_time_ns=i,
            requested_binary32=bytes.fromhex('00000000')), limited_state_at_entry=0, saved_limited_state=0,
            angle_counter_at_entry=0, saved_angle_counter=0) for i in range(128))
        contexts = tuple(replace(self.fixture.contexts[0], model_index=3969 + i, previous_integer_request=0,
                                current_driver=0.0, current_angle_deg=0.0) for i in range(127))
        self.fixture.save(self.fixture.codec.encode_recording_input(self.fixture.base.recorder.FinishedSyntheticRecordingV1(frames), contexts))
        self.case.record.update(input_sha256=self.fixture.digest(), input_bytes=len(self.fixture.raw), frame_count=128,
            checked_transition_count=127, new_synthetic_model_steps=127, rows=[])
        for i in range(127):
            self.case.record['rows'].append({'transition_index': i, 'model_index': 3969 + i, 'status': 'MATCH',
                'declared_entry_state': {'index': 3969 + i, 'previous_requested': 1 if i == 0 else 0,
                                         'previous_applied': 0, 'angle_counter': 0},
                'computed_next_state': {'index': 3970 + i, 'previous_requested': 0, 'previous_applied': 0, 'angle_counter': 0},
                'declared_saved_state': {'saved_limited_state': 0, 'saved_angle_counter': 0}, 'differences': []})
            # Each observed entry differs yet retains CORE66 declared saved-state links.
            self.case.record['rows'][-1]['declared_entry_state']['previous_applied'] = 1
            self.case.record['rows'][-1]['declared_saved_state']['saved_limited_state'] = 1
            self.case.record['rows'][-1]['computed_next_state']['previous_applied'] = 1
        self.case.persist()
        value, md = self.saved(self.publish())
        self.assertEqual(value['differing_transition_indices'], list(range(127)))
        self.assertEqual(len(value['reference_projection']['rows']), 127)
        self.assertIn('전체 127 / 표시 20 / 생략 107', md)
        self.assertIn('| 19 |', md)
        self.assertNotIn('| 20 |', md)
        self.assertIn('REFERENCE_AUDIT.json', md)

    def test_both_digest_syntaxes_reject_before_paths(self):
        for first, second in [('A' * 64, '0' * 64), ('0' * 64, None)]:
            with patch.object(self.m, '_output', side_effect=AssertionError('path')), self.assertRaisesRegex(ValueError, 'RECORDING_REFERENCE_EXPECTED_SHA256'):
                self.m.publish_recording_reference(Path('/missing'), first, Path('/missing'), second, self.output)

    def test_existing_output_is_preserved_before_checker(self):
        self.output.mkdir()
        (self.output / 'sentinel').write_bytes(b'keep')
        with patch.object(self.m, 'check_recording_reference', side_effect=AssertionError('reference')), self.assertRaises(ValueError):
            self.publish()
        self.assertEqual((self.output / 'sentinel').read_bytes(), b'keep')

    def test_illegal_output_parent_symlink_and_checkout_reject_before_checker(self):
        link = self.root / 'link'
        link.symlink_to(self.root, target_is_directory=True)
        for out in (self.root / 'absent/new', link / 'new', ROOT / 'out-core70-forbidden'):
            with patch.object(self.m, 'check_recording_reference', side_effect=AssertionError('reference')), self.assertRaises(ValueError):
                self.publish(out)
            self.assertFalse(out.exists())

    def test_nested_output_rejects_before_work_and_preserves_source_package_layout(self):
        alias = self.root / 'alias parent'
        alias.mkdir()
        before = {p.name: p.read_bytes() for p in self.case.saved.iterdir()}
        source_alias = alias / '..' / self.case.saved.name
        variants = [(self.case.saved, self.case.saved / 'audit0'),
                    (source_alias, self.case.saved / 'audit1'),
                    (self.case.saved, source_alias / 'audit2')]
        for source, target in variants:
            with patch.object(self.m, 'check_recording_reference', wraps=self.m.check_recording_reference) as check:
                with self.assertRaisesRegex(ValueError, 'REFERENCE_WORKFLOW_OUTPUT_OVERLAPS_DIAGNOSTICS'):
                    self.m.publish_recording_reference(self.fixture.file, self.fixture.digest(), source,
                        self.case.case.digest(), target)
            self.assertEqual(check.call_count, 0)
            self.assertFalse(target.exists())
            self.assertEqual({p.name: p.read_bytes() for p in self.case.saved.iterdir()}, before)

    def test_invalid_late_input_is_rejected_before_worker_and_output(self):
        value = json.loads(self.fixture.raw)
        value['contexts'][-1]['current_driver_hex'] = '0x1.8000000000001p+0'
        raw = canonical(value)
        self.assertNotEqual(raw, self.fixture.raw)
        self.fixture.save(raw)
        self.case.record.update(input_sha256=self.fixture.digest(), input_bytes=len(raw))
        self.case.persist()
        with patch.object(self.case.m, '_launch', side_effect=AssertionError('worker')), self.assertRaises(ValueError):
            self.publish()
        self.assertFalse(self.output.exists())

    def test_original_files_unchanged_and_single_capture_each(self):
        paths = [self.fixture.file, self.case.saved / 'DIAGNOSTICS.json', self.case.saved / 'SHA256SUMS.txt']
        before = [(p.read_bytes(), p.stat().st_mode) for p in paths]
        with patch.object(self.case.m, '_capture', wraps=self.case.m._capture) as capture, \
                patch.object(self.case.m, 'inspect_recording_diagnostics', wraps=self.case.m.inspect_recording_diagnostics) as saved:
            self.publish()
        self.assertEqual((capture.call_count, saved.call_count), (1, 1))
        self.assertEqual([(p.read_bytes(), p.stat().st_mode) for p in paths], before)

    def test_summary_failure_is_after_one_worker_before_directory_creation(self):
        with patch.object(self.m, '_summary', side_effect=ValueError('private')), \
                patch.object(self.case.m, '_launch', wraps=self.case.m._launch) as launch, self.assertRaisesRegex(ValueError, 'REFERENCE_WORKFLOW_PREPARATION_FAILED'):
            self.publish()
        self.assertEqual(launch.call_count, 1)
        self.assertFalse(self.output.exists())

    def test_markdown_size_guard_precedes_publication(self):
        for payload in (b'', b'x' * 65537):
            with patch.object(self.m, '_summary', return_value=payload), self.assertRaisesRegex(ValueError, 'REFERENCE_WORKFLOW_PREPARATION_FAILED'):
                self.publish()
            self.assertFalse(self.output.exists())

    def test_json_and_receipt_serialization_fail_before_directory_creation(self):
        original = self.m.canonical
        for contract in ('CORE69_DECLARED_DIAGNOSTICS_REFERENCE_AUDIT_V1', 'CORE70_REFERENCE_AUDIT_WORKFLOW_V1'):
            def broken(value, contract=contract):
                if isinstance(value, dict) and value.get('contract_id') == contract:
                    raise ValueError('private serialization')
                return original(value)
            with patch.object(self.m, 'canonical', side_effect=broken), self.assertRaisesRegex(ValueError, 'REFERENCE_WORKFLOW_PREPARATION_FAILED'):
                self.publish()
            self.assertFalse(self.output.exists())

    def test_json_and_receipt_size_guards_precede_publication(self):
        original = self.m.canonical
        for contract, limit in [('CORE69_DECLARED_DIAGNOSTICS_REFERENCE_AUDIT_V1', 2097152), ('CORE70_REFERENCE_AUDIT_WORKFLOW_V1', 16384)]:
            def oversized(value, contract=contract, limit=limit):
                if isinstance(value, dict) and value.get('contract_id') == contract:
                    return b'x' * (limit + 1)
                return original(value)
            with patch.object(self.m, 'canonical', side_effect=oversized), self.assertRaisesRegex(ValueError, 'REFERENCE_WORKFLOW_PREPARATION_FAILED'):
                self.publish()
            self.assertFalse(self.output.exists())

    def test_write_failure_preserves_partial_files_and_never_retries_checker(self):
        original = self.publisher._write
        def broken(fd, name, raw):
            if name == 'SUMMARY_KO.md':
                raise OSError('private write')
            return original(fd, name, raw)
        with patch.object(self.publisher, '_write', side_effect=broken), \
                patch.object(self.m, 'check_recording_reference', wraps=self.m.check_recording_reference) as check, self.assertRaises(ValueError):
            self.publish()
        self.assertEqual(check.call_count, 1)
        self.assertEqual({p.name for p in self.output.iterdir()}, {'REFERENCE_AUDIT.json'})

    def test_readback_failure_keeps_complete_files_without_success(self):
        with patch.object(self.publisher, '_readback', side_effect=OSError('private readback')), self.assertRaises(ValueError):
            self.publish()
        self.assertEqual(len(list(self.output.iterdir())), 3)

    def test_gate_and_scope_disclosures_do_not_grant_actual_authority(self):
        receipt = self.publish()
        value, md = self.saved(receipt)
        self.assertTrue(value['shared_admission_preflight'])
        self.assertTrue(all(receipt[k] is False for k in self.case.m.FLAGS))
        self.assertEqual(receipt['gates'], self.fixture.expected()['gates'])
        for text in ('공유', '첫 anchor', 'prehistory', 'R_BUDGET=UNRESOLVED', 'Static Gate=FAIL', '실제 r/T2/scale=null'):
            self.assertIn(text, md)

    def test_cli_unique_opt_in_flags_reject_before_project_imports(self):
        original, args = builtins.__import__, self.args()
        def importing(name, *a, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')):
                raise AssertionError('project import')
            return original(name, *a, **kw)
        variants = [[], args[1:], args + ['--run'], args + ['--r', '0'], args + ['--dt', '0.01'], args + ['--input', 'x']]
        for i in range(1, len(args), 2):
            variants.extend((args[:i] + args[i + 2:], args + args[i:i + 2], args[:i + 1] + [''] + args[i + 2:]))
        variants.append(args[:-3] + ['A' * 64] + args[-2:])
        for argv in variants:
            with patch('builtins.__import__', side_effect=importing), patch('os.open', side_effect=AssertionError('open')), \
                    patch('sys.stderr', StringIO()) as err, self.assertRaises(SystemExit) as found:
                self.cli.main(argv)
            self.assertEqual((found.exception.code, err.getvalue()), (2, 'REJECTED: REFERENCE_WORKFLOW_USAGE_NO_EXECUTION\n'))

    def test_cli_help_does_not_import_project_or_mutate_globals(self):
        paths, flag, original = list(sys.path), sys.dont_write_bytecode, builtins.__import__
        def importing(name, *a, **kw):
            if name.startswith('integration_tools'):
                raise AssertionError('project import')
            return original(name, *a, **kw)
        with patch('builtins.__import__', side_effect=importing), patch('sys.stdout', StringIO()) as out, self.assertRaises(SystemExit) as found:
            self.cli.main(['--help'])
        self.assertEqual(found.exception.code, 0)
        self.assertIn('--output-root', out.getvalue())
        self.assertEqual((sys.path, sys.dont_write_bytecode), (paths, flag))

    def test_fresh_cli_success_and_difference_exits_preserve_files(self):
        first = self.command()
        self.assertEqual((first.returncode, first.stderr), (0, b''))
        self.saved(json.loads(first.stdout))
        self.case.record['rows'][-1]['computed_next_state']['previous_applied'] = 202
        self.case.record['rows'][-1]['declared_saved_state']['saved_limited_state'] = 202
        self.case.persist()
        other = self.root / 'different'
        second = self.command(self.args(other))
        self.assertEqual((second.returncode, second.stderr), (1, b''))
        self.assertEqual(self.saved(json.loads(second.stdout), other)[0]['audit_status'], 'REFERENCE_DIFFERENT')

    def test_positive_short_stdout_write_is_completed_without_rerun(self):
        original = os.write
        def short(fd, raw):
            return original(fd, raw[:min(13, len(raw))]) if fd == sys.stdout.fileno() else original(fd, raw)
        with patch('os.write', side_effect=short), patch.object(self.case.m, '_launch', wraps=self.case.m._launch) as launch:
            code, raw, error = self.invoke()
        self.assertEqual((code, error, launch.call_count), (0, '', 1))
        self.saved(json.loads(raw))

    def test_broken_stdout_keeps_published_files_and_zero_retry(self):
        original, paths = os.write, list(sys.path)
        def broken(fd, raw):
            if fd == sys.stdout.fileno():
                raise BrokenPipeError('private output')
            return original(fd, raw)
        with patch('os.write', side_effect=broken), patch.object(self.case.m, '_launch', wraps=self.case.m._launch) as launch:
            code, raw, error = self.invoke()
        self.assertEqual((code, raw, launch.call_count), (2, b'', 1))
        self.assertNotIn('private output', error)
        self.assertEqual(len(list(self.output.iterdir())), 3)
        self.assertEqual(sys.path, paths)

    def test_stdout_prefix_failure_is_not_a_success_receipt(self):
        original, written = os.write, []
        def prefix(fd, raw):
            if fd != sys.stdout.fileno():
                return original(fd, raw)
            if not written:
                written.append(True)
                return original(fd, raw[:7])
            return 0
        with patch('os.write', side_effect=prefix), patch.object(self.case.m, '_launch', wraps=self.case.m._launch) as launch:
            code, raw, error = self.invoke()
        self.assertEqual((code, len(raw), launch.call_count), (2, 7, 1))
        self.assertIn('WORK_MAY_BE_NONZERO', error)

    def test_second_output_destination_has_identical_three_files_and_receipt(self):
        first, second = self.output, self.root / 'repeat'
        one, two = self.command(self.args(first)), self.command(self.args(second))
        self.assertEqual((one.returncode, two.returncode, one.stderr, two.stderr), (0, 0, b'', b''))
        self.assertEqual(one.stdout, two.stdout)
        for name in ('REFERENCE_AUDIT.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt'):
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())


if __name__ == '__main__':
    unittest.main()
