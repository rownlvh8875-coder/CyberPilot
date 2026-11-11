"""Catch overwrite, repeated execution, lost rows and false publication success."""

import builtins
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


class RecordingInputWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/recording_input_workflow.py').is_file(), 'Missing CORE64 save API')
        self.script = ROOT / 'tools/recording_input_workflow.py'
        self.assertTrue(self.script.is_file(), 'Missing CORE64 save CLI')
        self.fixture = fixtures.RecordingInputCliTests('test_api_match_emits_independent_literal_three_row_projection')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.file = self.fixture.root, self.fixture.file
        self.output = self.root / 'saved output'
        self.m: Any = importlib.import_module('integration_tools.recording_input_workflow')
        self.publisher: Any = importlib.import_module('integration_tools.core_sequence_archive_workflow')
        spec = importlib.util.spec_from_file_location('core64_cli_test', self.script)
        assert spec is not None and spec.loader is not None
        self.cli: Any = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.cli)

    def args(self, output=None):
        return [*self.fixture.args(), '--output-root', str(self.output if output is None else output)]

    def publish(self, output=None):
        return self.m.publish_recording_input(self.file, self.fixture.digest(), self.output if output is None else output)

    def counted(self, call):
        return self.fixture.base.counted(call)

    def command(self, args=None):
        return subprocess.run([sys.executable, '-I', '-B', str(self.script), *(self.args() if args is None else args)],
            cwd=self.root, capture_output=True)

    def invoke(self, args=None):
        err = StringIO()
        target = self.root / 'stdout.bin'
        with target.open('wb') as out, patch('sys.stdout', out), patch('sys.stderr', err):
            code = self.cli.main(self.args() if args is None else args)
        return code, target.read_bytes(), err.getvalue()

    def saved(self, receipt, output=None, expected=None):
        target = self.output if output is None else output
        self.assertEqual({p.name for p in target.iterdir()}, {'DIAGNOSTICS.json', 'SHA256SUMS.txt'})
        raw = (target / 'DIAGNOSTICS.json').read_bytes()
        value = json.loads(raw)
        self.assertEqual(raw, canonical(value))
        if expected is not None:
            self.assertEqual(value, expected)
        checksum = (hashlib.sha256(raw).hexdigest() + '  DIAGNOSTICS.json\n').encode()
        self.assertEqual((target / 'SHA256SUMS.txt').read_bytes(), checksum)
        self.assertEqual(receipt['files'], {name: {'sha256': hashlib.sha256((target / name).read_bytes()).hexdigest(),
            'byte_size': len((target / name).read_bytes())} for name in ('DIAGNOSTICS.json', 'SHA256SUMS.txt')})
        self.assertEqual(receipt['contract_id'], 'CORE64_RECORDING_INPUT_WORKFLOW_V1')
        self.assertEqual(receipt['status'], 'RECORDING_DIAGNOSTICS_PUBLISHED')
        self.assertEqual(receipt['diagnostic_status'], value['status'])
        for name in ('input_sha256', 'input_bytes', 'frame_count', 'checked_transition_count', 'new_synthetic_model_steps',
                'differing_transition_indices', 'validation_claim', 'state_feed_rule', 'first_frame_transition_checked',
                'prehistory_checked', 'source_identity_reauthenticated', 'v4_payload_allowed', 'f61_input_allowed',
                'actual_activation_allowed', 'gates'):
            self.assertEqual(receipt[name], value[name])
        self.assertEqual(receipt['gates'], self.fixture.expected()['gates'])
        return value

    # Break: saving a summary rather than all CORE61 rows, or invoking twice.
    def test_match_saves_literal_complete_result_and_three_real_steps(self):
        receipt, counts = self.counted(self.publish)
        self.saved(receipt, expected=self.fixture.expected())
        self.assertEqual((receipt['diagnostic_exit_code'], counts), (0, {'step': 3, 'simulate': 0}))

    def test_difference_is_saved_with_all_later_declared_state_rows(self):
        self.fixture.difference()
        receipt, counts = self.counted(self.publish)
        value = self.saved(receipt)
        self.assertEqual((receipt['diagnostic_status'], receipt['diagnostic_exit_code']), ('DIFFERENT', 1))
        self.assertEqual(value['differing_transition_indices'], [0])
        self.assertEqual([r['computed_next_state']['previous_applied'] for r in value['rows']], [2, 5, 4])
        self.assertEqual(value['rows'][0]['differences'], [{'field': 'saved_limited_state', 'declared': 10, 'computed': 2}])
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_input_bytes_and_mode_preserved_with_private_output_modes(self):
        self.file.chmod(0o444)
        before = self.fixture.snapshot()
        self.publish()
        self.assertEqual(self.fixture.snapshot(), before)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in self.output.iterdir()))

    def test_one_capture_and_one_runner_no_recomputation_for_publication(self):
        original = os.open
        opens = []
        def opening(path, flags, *args, **kw):
            if path == self.file:
                opens.append(path)
            return original(path, flags, *args, **kw)
        with patch('os.open', side_effect=opening):
            receipt, counts = self.counted(self.publish)
        self.assertEqual(opens, [self.file])
        self.assertEqual(counts, {'step': 3, 'simulate': 0})
        self.saved(receipt, expected=self.fixture.expected())

    def test_malformed_sha_rejects_before_input_or_output_path_work(self):
        for sha in (None, True, '', 'A' * 64, 'a' * 63, 'g' * 64):
            with patch.object(Path, 'absolute', side_effect=AssertionError('path')), patch('os.open', side_effect=AssertionError('open')):
                with self.assertRaisesRegex(self.fixture.api.RecordingInputRunError, '^RECORDING_DIAGNOSTICS_INPUT_SHA256$'):
                    self.m.publish_recording_input(self.file, sha, self.output)
        self.assertFalse(self.output.exists())

    def test_wrong_digest_creates_no_output_and_no_steps(self):
        def call():
            with self.assertRaisesRegex(self.fixture.api.RecordingInputRunError, '^RECORDING_DIAGNOSTICS_INPUT_CHECKSUM$'):
                self.m.publish_recording_input(self.file, '0' * 64, self.output)
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})
        self.assertFalse(self.output.exists())

    def test_malformed_complete_input_has_no_output_or_prefix(self):
        self.fixture.save(b'{')
        def call():
            with self.assertRaises(self.fixture.codec.RecordingInputCodecError):
                self.publish()
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})
        self.assertFalse(self.output.exists())

    def test_late_semantic_error_prevents_entire_run_and_publication(self):
        value = json.loads(self.fixture.raw)
        value['contexts'][-1]['current_driver_hex'] = '0x1.999999999999ap-4'
        self.fixture.save(canonical(value))
        def call():
            with self.assertRaises(self.fixture.base.preflight.RecordingPreflightError):
                self.publish()
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})
        self.assertFalse(self.output.exists())

    def test_existing_destination_preserves_sentinel_and_zero_work(self):
        self.output.mkdir()
        (self.output / 'keep').write_bytes(b'untouched')
        def call():
            with self.assertRaisesRegex(self.publisher.ArchiveWorkflowError, '^ARCHIVE_WORKFLOW_OUTPUT_EXISTS$'):
                self.publish()
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 0, 'simulate': 0})
        self.assertEqual((self.output / 'keep').read_bytes(), b'untouched')

    def test_invalid_destinations_reject_before_model_work(self):
        link = self.root / 'link'
        link.symlink_to(self.root, target_is_directory=True)
        for target in (link / 'child', self.root / 'missing' / 'child', ROOT / 'core64-output',
                Path('bad\0name'), Path('bad\ud800'), 'not Path'):
            def call(target=target):
                with self.assertRaises(self.publisher.ArchiveWorkflowError):
                    self.publish(target)
            _, counts = self.counted(call)
            self.assertEqual(counts, {'step': 0, 'simulate': 0})
        self.assertFalse((self.root / 'child').exists())
        self.assertFalse((ROOT / 'core64-output').exists())

    def test_serialization_failure_leaves_no_directory_after_three_steps(self):
        def call():
            with patch.object(self.m, 'canonical', side_effect=ValueError('SECRET')), self.assertRaises(ValueError):
                self.publish()
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 3, 'simulate': 0})
        self.assertFalse(self.output.exists())

    def test_oversized_result_rejects_before_mkdir(self):
        def call():
            with patch.object(self.m, 'canonical', return_value=b'x' * 1048577), \
                    self.assertRaisesRegex(self.m.RecordingInputWorkflowError, 'OUTPUT_SIZE_WORK_MAY_BE_NONZERO'):
                self.publish()
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 3, 'simulate': 0})
        self.assertFalse(self.output.exists())

    def test_unknown_diagnostic_status_cannot_publish_success(self):
        value = self.fixture.expected()
        value['status'] = 'UNKNOWN'
        with patch.object(self.m, 'run_recording_input', return_value=value), self.assertRaises(KeyError):
            self.publish()
        self.assertFalse(self.output.exists())

    def test_receipt_serialization_failure_also_precedes_mkdir(self):
        original = self.m.canonical
        calls = []
        def serializing(value):
            calls.append(value)
            if len(calls) == 2:
                raise ValueError('receipt failure')
            return original(value)
        with patch.object(self.m, 'canonical', side_effect=serializing), self.assertRaises(ValueError):
            self.publish()
        self.assertEqual(len(calls), 2)
        self.assertFalse(self.output.exists())

    def test_short_writes_finish_both_files_without_extra_steps(self):
        original = os.write
        with patch('os.write', side_effect=lambda fd, raw: original(fd, raw[:11])):
            receipt, counts = self.counted(self.publish)
        self.saved(receipt, expected=self.fixture.expected())
        self.assertEqual(counts, {'step': 3, 'simulate': 0})

    def test_nonpositive_file_write_preserves_partial_directory_and_work(self):
        def call():
            with patch('os.write', return_value=0), self.assertRaisesRegex(self.publisher.ArchiveWorkflowError, 'PARTIAL_DIRECTORY_POSSIBLE'):
                self.publish()
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 3, 'simulate': 0})
        self.assertTrue(self.output.is_dir())
        self.assertEqual((self.output / 'DIAGNOSTICS.json').read_bytes(), b'')

    def test_readback_corruption_is_failure_without_cleanup_or_retry(self):
        original = self.publisher._readback
        def corrupt(directory, name, expected):
            if name == 'DIAGNOSTICS.json':
                (self.output / name).write_bytes(b'corrupted')
            return original(directory, name, expected)
        def call():
            with patch.object(self.publisher, '_readback', side_effect=corrupt), \
                    self.assertRaisesRegex(self.publisher.ArchiveWorkflowError, 'CHECK_FAILED_DIRECTORY_MAY_EXIST'):
                self.publish()
        _, counts = self.counted(call)
        self.assertEqual(counts, {'step': 3, 'simulate': 0})
        self.assertEqual((self.output / 'DIAGNOSTICS.json').read_bytes(), b'corrupted')

    def test_distinct_destinations_produce_equal_files_and_receipts(self):
        one = self.publish()
        other = self.root / 'other'
        two = self.publish(other)
        self.assertEqual(two, one)
        self.saved(two, output=other, expected=self.fixture.expected())
        for name in one['files']:
            self.assertEqual((self.output / name).read_bytes(), (other / name).read_bytes())

    def test_cli_match_publishes_and_emits_only_canonical_receipt(self):
        result = self.command()
        self.assertEqual((result.returncode, result.stderr), (0, b''))
        receipt = json.loads(result.stdout)
        self.assertEqual(result.stdout, canonical(receipt))
        self.saved(receipt, expected=self.fixture.expected())

    def test_cli_difference_saves_result_and_exits_one(self):
        self.fixture.difference()
        result = self.command()
        self.assertEqual((result.returncode, result.stderr), (1, b''))
        self.assertEqual(self.saved(json.loads(result.stdout))['status'], 'DIFFERENT')

    def test_cli_input_error_exits_two_without_output_or_steps(self):
        self.fixture.save(b'{')
        (code, out, err), counts = self.counted(self.invoke)
        self.assertEqual((code, out, err), (2, b'', 'REJECTED: RECORDING_INPUT_SERIALIZATION\n'))
        self.assertEqual(counts, {'step': 0, 'simulate': 0})
        self.assertFalse(self.output.exists())

    def test_cli_existing_output_exits_two_preserves_bytes_and_zero_work(self):
        self.output.mkdir()
        (self.output / 'keep').write_bytes(b'keep')
        (code, out, err), counts = self.counted(self.invoke)
        self.assertEqual((code, out, err), (2, b'', 'REJECTED: ARCHIVE_WORKFLOW_OUTPUT_EXISTS\n'))
        self.assertEqual(counts, {'step': 0, 'simulate': 0})
        self.assertEqual((self.output / 'keep').read_bytes(), b'keep')

    def test_cli_strict_invalid_usage_precedes_project_imports_and_paths(self):
        original = builtins.__import__
        def guarded(name, *args, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')):
                raise AssertionError('project import')
            return original(name, *args, **kw)
        args = self.args()
        variants = ([], args[1:], args[:-2], args + ['--run'], args + args[1:3], args + args[3:5], args + args[5:],
            args + ['--r', '0'], ['--r', *args[1:]], args[:-1] + [''], args[:4] + ['A' * 64] + args[5:])
        for argv in variants:
            with patch('builtins.__import__', side_effect=guarded), patch('os.open', side_effect=AssertionError('open')), \
                    patch('sys.stderr', StringIO()) as err, self.assertRaises(SystemExit) as found:
                self.cli.main(argv)
            self.assertEqual((found.exception.code, err.getvalue()),
                (2, 'REJECTED: RECORDING_WORKFLOW_USAGE_NO_MODEL_EXECUTION\n'))
        self.assertFalse(self.output.exists())

    def test_cli_help_does_not_import_project_and_restores_globals(self):
        original, before = builtins.__import__, list(sys.path)
        def guarded(name, *args, **kw):
            if name.startswith(('integration_tools', 'cyberlateral_dev')):
                raise AssertionError('project import')
            return original(name, *args, **kw)
        with patch.object(sys, 'dont_write_bytecode', False), patch('builtins.__import__', side_effect=guarded), \
                patch('sys.stdout', StringIO()) as out, self.assertRaises(SystemExit) as found:
            self.cli.main(['--help'])
        self.assertEqual(found.exception.code, 0)
        self.assertIn('--output-root', out.getvalue())
        self.assertEqual(sys.path, before)
        self.assertFalse(self.output.exists())

    def test_cli_short_stdout_writes_deliver_complete_receipt(self):
        original = os.write
        with patch.object(self.cli.os, 'write', side_effect=lambda fd, raw: original(fd, raw[:7])):
            code, out, err = self.invoke()
        self.assertEqual((code, err), (0, ''))
        self.saved(json.loads(out), expected=self.fixture.expected())

    def test_cli_broken_stdout_retains_saved_files_and_never_reexecutes(self):
        original = os.write
        def writing(fd, raw):
            if os.fstat(fd).st_ino == (self.root / 'stdout.bin').stat().st_ino:
                raise BrokenPipeError('SECRET')
            return original(fd, raw)
        with patch('os.write', side_effect=writing):
            (code, out, err), counts = self.counted(self.invoke)
        self.assertEqual((code, out, err), (2, b'', 'REJECTED: RECORDING_WORKFLOW_FAILED_DIRECTORY_MAY_EXIST_WORK_MAY_BE_NONZERO\n'))
        self.assertEqual(counts, {'step': 3, 'simulate': 0})
        self.assertEqual(json.loads((self.output / 'DIAGNOSTICS.json').read_bytes()), self.fixture.expected())

    def test_cli_nonpositive_stdout_never_becomes_success_or_deletes_files(self):
        original = os.write
        for zero in (0, -1):
            target = self.root / ('zero-' + str(zero))
            def writing(fd, raw, zero=zero):
                if os.fstat(fd).st_ino == (self.root / 'stdout.bin').stat().st_ino:
                    return zero
                return original(fd, raw)
            with patch('os.write', side_effect=writing):
                (code, out, err), counts = self.counted(lambda target=target: self.invoke(self.args(target)))
            self.assertEqual((code, out), (2, b''))
            self.assertIn('DIRECTORY_MAY_EXIST_WORK_MAY_BE_NONZERO', err)
            self.assertEqual(counts, {'step': 3, 'simulate': 0})
            self.assertEqual(json.loads((target / 'DIAGNOSTICS.json').read_bytes()), self.fixture.expected())

    def test_cli_partial_stdout_failure_preserves_prefix_without_retry(self):
        original = os.write
        writes = []
        def writing(fd, raw):
            if os.fstat(fd).st_ino == (self.root / 'stdout.bin').stat().st_ino:
                writes.append(bytes(raw))
                if len(writes) == 1:
                    return original(fd, raw[:11])
                raise OSError('SECRET')
            return original(fd, raw)
        with patch('os.write', side_effect=writing):
            (code, out, err), counts = self.counted(self.invoke)
        self.assertEqual((code, out), (2, writes[0][:11]))
        self.assertEqual(len(writes), 2)
        self.assertIn('DIRECTORY_MAY_EXIST_WORK_MAY_BE_NONZERO', err)
        self.assertNotIn('SECRET', err)
        self.assertEqual(counts, {'step': 3, 'simulate': 0})
        self.assertTrue((self.output / 'SHA256SUMS.txt').is_file())

    def test_cli_late_serialization_failure_does_not_leak_values_or_claim_zero(self):
        with patch.object(self.m, 'canonical', side_effect=ValueError('SECRET')):
            (code, out, err), counts = self.counted(self.invoke)
        self.assertEqual((code, out, err), (2, b'', 'REJECTED: RECORDING_WORKFLOW_FAILED_DIRECTORY_MAY_EXIST_WORK_MAY_BE_NONZERO\n'))
        self.assertEqual(counts, {'step': 3, 'simulate': 0})
        self.assertFalse(self.output.exists())

    def test_cli_restores_paths_and_bytecode_on_success_and_input_failure(self):
        before = list(sys.path)
        with patch.object(sys, 'dont_write_bytecode', False):
            self.assertEqual(self.invoke()[0], 0)
            self.assertFalse(sys.dont_write_bytecode)
            self.assertEqual(sys.path, before)
        self.fixture.save(b'{')
        with patch.object(sys, 'dont_write_bytecode', False):
            self.assertEqual(self.invoke(self.args(self.root / 'failed'))[0], 2)
            self.assertFalse(sys.dont_write_bytecode)
            self.assertEqual(sys.path, before)

    def test_cli_separate_processes_have_equal_receipts_and_saved_bytes(self):
        one = self.command()
        other = self.root / 'other'
        two = self.command(self.args(other))
        self.assertEqual((one.returncode, two.returncode, one.stderr, two.stderr), (0, 0, b'', b''))
        self.assertEqual(one.stdout, two.stdout)
        for name in ('DIAGNOSTICS.json', 'SHA256SUMS.txt'):
            self.assertEqual((self.output / name).read_bytes(), (other / name).read_bytes())

    def test_cli_cold_main_writes_no_bytecode_or_temporary_files(self):
        script = '''import sys
sys.dont_write_bytecode=True
import importlib.util,importlib._bootstrap_external as external
source,cache,*args=sys.argv[1:]
spec=importlib.util.spec_from_file_location('cold_core64',source)
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
writes=[]
external.SourceFileLoader.set_data=lambda self,path,data,**kw:writes.append(path)
before=list(sys.path);sys.pycache_prefix=cache;sys.dont_write_bytecode=False
code=cli.main(args)
assert not writes,writes
assert sys.path==before and sys.dont_write_bytecode is False and sys.pycache_prefix==cache
sys.dont_write_bytecode=True
raise SystemExit(code)
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(self.script), str(self.fixture.folder), *self.args()],
            cwd=self.root, capture_output=True)
        self.assertEqual((result.returncode, result.stderr), (0, b''))
        self.assertEqual({p.name for p in self.fixture.folder.iterdir()}, {self.file.name})
        self.assertEqual({p.name for p in self.root.iterdir()}, {'input', 'saved output'})

    def test_cli_forbidden_imports_absent_with_three_real_public_steps(self):
        script = '''import importlib.abc,runpy,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  forbidden=('openpilot','opendbc','numpy','integration_tools.fixed_model_reference','integration_tools.sequence_reference')
  if any(fullname==n or fullname.startswith(n+'.') for n in forbidden) or fullname.startswith(('integration_tools.f61_','synthetic_rate_constraint_feasibility')):raise AssertionError('FORBIDDEN:'+fullname)
counts={'step':0,'simulate':0}
calls={('cyberlateral_dev.api','step'):'step',('cyberlateral_dev.simulation','simulate'):'simulate'}
def profile(frame,event,arg):
 if event=='call':
  key=calls.get((frame.f_globals.get('__name__',''),frame.f_code.co_name))
  if key is not None:counts[key]+=1
sys.meta_path.insert(0,Block());sys.setprofile(profile);sys.argv=sys.argv[1:]
try:runpy.run_path(sys.argv[0],run_name='__main__')
except SystemExit as end:
 assert end.code==0 and counts=={'step':3,'simulate':0},(end.code,counts)
 raise
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(self.script), *self.args()], cwd=self.root, capture_output=True)
        self.assertEqual((result.returncode, result.stderr), (0, b''))
        self.saved(json.loads(result.stdout), expected=self.fixture.expected())


if __name__ == '__main__':
    unittest.main()
