"""Fourteen-file saved capture, exact cross-artifact relations, no execution."""

import hashlib
import importlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

from v1_helpers import ROOT

CASES = ('sign-cycle', 'declared-difference', 'late-invalid')


def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CoreRunInspectTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_sequence_run_inspect.py').is_file(), 'Missing CORE18 saved run inspector')
        self.assertTrue((ROOT / 'tools/core_sequence_run_inspect.py').is_file(), 'Missing CORE18 inspection CLI')
        if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.core_sequence_run_inspect')
        self.suite = importlib.import_module('integration_tools.core_sequence_suite')
        self.bundle = importlib.import_module('integration_tools.core_sequence_bundle')
        self.report = importlib.import_module('integration_tools.core_sequence_archive_report')
        runner = importlib.import_module('integration_tools.core_sequence_archive_run')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        fixture = self.root / 'fixture'; self.suite.run_closed_suite(fixture)
        self.files = {'suite/' + c + '/' + n: (fixture / c / n).read_bytes() for c in CASES for n in ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt')}
        raw = self.bundle.build_suite_archive(self.files); baseline = self.root / 'baseline.zip'; baseline.write_bytes(raw)
        self.folder = self.root / 'run'; r = runner.run_archived_suite(baseline, sha(raw), self.folder)
        self.bsha = sha(raw); self.csha = r['current_export']['archive_sha256']

    def inspect(self, folder=None):
        return self.m.inspect_archived_run(self.folder if folder is None else folder, self.bsha, self.csha)

    def snapshot(self, folder=None):
        return {p.relative_to(folder or self.folder).as_posix(): (p.read_bytes(), p.stat().st_mode)
                for p in (folder or self.folder).rglob('*') if p.is_file()}

    def store_report(self):
        left = (self.folder / 'BASELINE.zip').read_bytes(); right = (self.folder / 'CURRENT.zip').read_bytes()
        _, md = self.report.report_suite_archive_bytes(left, self.bsha, right, self.csha)
        comparison = self.report.report_suite_archive_bytes(left, self.bsha, right, self.csha)[0]
        (self.folder / 'comparison/COMPARISON.json').write_bytes(canonical(comparison))
        (self.folder / 'comparison/SUMMARY_KO.md').write_bytes(md); self.report_checksum()

    def report_checksum(self):
        folder = self.folder / 'comparison'
        (folder / 'SHA256SUMS.txt').write_bytes(''.join(sha((folder / n).read_bytes()) + '  ' + n + '\n'
            for n in ('COMPARISON.json', 'SUMMARY_KO.md')).encode())

    def change_identity(self, files, value):
        copied = dict(files); prefix = 'suite/late-invalid/'
        result = json.loads(copied[prefix + 'RESULTS.json']); result['identity'].update(value)
        copied[prefix + 'RESULTS.json'] = canonical(result)
        copied[prefix + 'SHA256SUMS.txt'] = ''.join(sha(copied[prefix + n]) + '  ' + n + '\n' for n in ('INPUT.json', 'RESULTS.json')).encode()
        return copied

    def install_current(self, files):
        for n, raw in files.items(): (self.folder / n).write_bytes(raw)
        raw = self.bundle.build_suite_archive(files); (self.folder / 'CURRENT.zip').write_bytes(raw); self.csha = sha(raw)
        self.store_report()

    def args(self): return ['--input-root', str(self.folder), '--baseline-sha256', self.bsha, '--current-sha256', self.csha]
    def cli(self, args=None):
        return subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence_run_inspect.py', *(self.args() if args is None else args)], capture_output=True)
    def cli_module(self):
        spec = importlib.util.spec_from_file_location('core18_cli_test', ROOT / 'tools/core_sequence_run_inspect.py')
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

    def test_valid_run_preserves_recorded_steps_without_new_execution_or_writes(self):
        before = self.snapshot(); calls = []; previous = sys.getprofile()
        def profile(frame, event, arg):
            if event == 'call' and frame.f_code.co_name == 'step' and frame.f_code.co_filename.endswith('/src/cyberlateral_dev/api.py'): calls.append(1)
        sys.setprofile(profile)
        try:
            with patch('os.write', side_effect=AssertionError('inspector must not write')): result = self.inspect()
        finally: sys.setprofile(previous)
        self.assertEqual(calls, []); self.assertEqual(before, self.snapshot())
        self.assertEqual(result['inspection_status'], 'SAVED_ARCHIVE_RUN_CONSISTENT')
        self.assertEqual(result['contract_id'], 'CORE18_SAVED_ARCHIVE_RUN_INSPECTION_V1')
        self.assertFalse(result['execution_requested']); self.assertEqual(result['captured_file_count'], 14)
        self.assertEqual(result['recorded_current_model_steps'], 6); self.assertEqual(result['new_synthetic_model_steps'], 0)
        self.assertEqual(result['inspection_model_executions'], 0); self.assertEqual(result['inspection_reference_executions'], 0)
        self.assertFalse(result['source_identity_reauthenticated']); self.assertFalse(result['arithmetic_recomputed'])
        self.assertEqual(result['captured_file_sha256'], {n: sha(v[0]) for n, v in before.items()})
        self.assertEqual(result['gates']['R_BUDGET'], 'UNRESOLVED'); self.assertEqual(result['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')

    def test_valid_stored_difference_is_inspection_success_and_cli_zero(self):
        self.install_current(self.change_identity(self.files, {'marker': None}))
        result = self.inspect(); self.assertEqual(result['comparison_exit_code'], 1)
        self.assertEqual(result['difference_counts'], {'INPUT': 0, 'RESULT': 0, 'IDENTITY': 1})
        command = self.cli(); self.assertEqual(command.returncode, 0, command.stderr)
        self.assertEqual(command.stderr, b''); self.assertEqual(command.stdout, canonical(result))

    def test_each_regular_file_is_captured_once_readonly(self):
        original = os.open; paths = {}; opened = []
        def observe(path, flags, *args, **kwargs):
            self.assertFalse(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
            target = paths[kwargs['dir_fd']] / path if 'dir_fd' in kwargs else Path(path).absolute()
            fd = original(path, flags, *args, **kwargs); paths[fd] = target
            if stat.S_ISREG(os.fstat(fd).st_mode): opened.append(target.relative_to(self.folder).as_posix())
            return fd
        with patch('os.open', side_effect=observe): result = self.inspect()
        self.assertEqual(len(opened), 14); self.assertEqual(set(opened), set(result['captured_file_sha256']))

    def test_both_digest_formats_precede_all_caller_path_inspection(self):
        for left, right, role in (('bad', self.csha, 'LEFT'), (self.bsha, 'bad', 'RIGHT')):
            with patch.object(self.m, '_path', side_effect=AssertionError('path before SHA')), \
                    patch('os.open', side_effect=AssertionError('open before SHA')), self.assertRaises(self.m.RunInspectError) as found:
                self.m.inspect_archived_run(self.folder, left, right)
            self.assertIn(role, found.exception.code)

    def test_wrong_external_digest_rejects_without_partial_result(self):
        with self.assertRaises(self.m.RunInspectError): self.m.inspect_archived_run(self.folder, self.bsha, '0' * 64)

    def test_archive_damage_even_with_updated_external_hash_rejects(self):
        current = self.folder / 'CURRENT.zip'; raw = bytearray(current.read_bytes()); raw[50] ^= 1
        current.write_bytes(raw); self.csha = sha(raw)
        with self.assertRaises(self.m.RunInspectError): self.inspect()

    def test_missing_or_extra_member_at_every_layout_level_rejects(self):
        targets = ('extra', 'suite/extra', 'suite/sign-cycle/extra', 'comparison/extra')
        for i, name in enumerate(targets):
            folder = self.root / ('extra-' + str(i)); shutil.copytree(self.folder, folder); (folder / name).touch()
            with self.subTest(name=name), self.assertRaises(self.m.RunInspectError): self.inspect(folder)
        for i, name in enumerate(('CURRENT.zip', 'suite/late-invalid', 'suite/sign-cycle/INPUT.json', 'comparison/SUMMARY_KO.md')):
            folder = self.root / ('missing-' + str(i)); shutil.copytree(self.folder, folder); (folder / name).rename(self.root / ('removed-' + str(i)))
            with self.subTest(name=name), self.assertRaises(self.m.RunInspectError): self.inspect(folder)

    def test_root_and_descendant_symlinks_reject(self):
        alias = self.root / 'alias'; alias.symlink_to(self.folder, target_is_directory=True)
        with self.assertRaises(self.m.RunInspectError): self.inspect(alias)
        for i, name in enumerate(('CURRENT.zip', 'suite/late-invalid', 'suite/sign-cycle/INPUT.json', 'comparison')):
            folder = self.root / ('symlink-' + str(i)); shutil.copytree(self.folder, folder)
            moved = self.root / ('moved-' + str(i)); (folder / name).rename(moved); (folder / name).symlink_to(moved, target_is_directory=moved.is_dir())
            with self.subTest(name=name), self.assertRaises(self.m.RunInspectError): self.inspect(folder)

    def test_fifo_members_reject_without_blocking(self):
        for i, name in enumerate(('BASELINE.zip', 'suite/sign-cycle/RESULTS.json', 'comparison/COMPARISON.json')):
            folder = self.root / ('fifo-' + str(i)); shutil.copytree(self.folder, folder)
            (folder / name).unlink(); os.mkfifo(folder / name)
            with self.subTest(name=name), self.assertRaises(self.m.RunInspectError): self.inspect(folder)

    def test_file_caps_reject_before_unbounded_read(self):
        for i, (name, length) in enumerate((('CURRENT.zip', 2_000_001), ('suite/sign-cycle/INPUT.json', 65537),
                    ('suite/sign-cycle/RESULTS.json', 524289), ('suite/sign-cycle/SHA256SUMS.txt', 513), ('comparison/COMPARISON.json', 8_000_000))):
            folder = self.root / ('size-' + str(i)); shutil.copytree(self.folder, folder)
            with (folder / name).open('wb') as stream: stream.truncate(length)
            with self.subTest(name=name), self.assertRaises(self.m.RunInspectError): self.inspect(folder)

    def test_invalid_root_paths_reject_with_fixed_errors(self):
        for value in ('not Path', Path('bad\0name'), Path('bad\ud800'), self.root / 'absent'):
            with self.subTest(value=repr(value)), self.assertRaises(self.m.RunInspectError): self.inspect(value)

    def test_case_checksum_damage_rejects(self):
        (self.folder / 'suite/sign-cycle/SHA256SUMS.txt').write_bytes(b'wrong')
        with self.assertRaises(self.m.RunInspectError): self.inspect()

    def test_checksummed_valid_case_copies_diverging_from_current_zip_reject(self):
        changed = self.change_identity(self.files, {'marker': 'valid but not in CURRENT.zip'})
        for n, raw in changed.items(): (self.folder / n).write_bytes(raw)
        with self.assertRaises(self.m.RunInspectError) as found: self.inspect()
        self.assertIn('SUITE_MISMATCH', found.exception.code)

    def test_self_checksummed_altered_comparison_json_rejects(self):
        path = self.folder / 'comparison/COMPARISON.json'; value = json.loads(path.read_bytes()); value['difference_count'] = 900
        path.write_bytes(canonical(value)); self.report_checksum()
        with self.assertRaises(self.m.RunInspectError): self.inspect()

    def test_self_checksummed_altered_markdown_rejects(self):
        path = self.folder / 'comparison/SUMMARY_KO.md'; path.write_bytes(path.read_bytes().replace(b'CORE15', b'WRONG!'))
        self.report_checksum()
        with self.assertRaises(self.m.RunInspectError): self.inspect()

    def test_report_checksum_damage_rejects(self):
        (self.folder / 'comparison/SHA256SUMS.txt').write_bytes(b'wrong')
        with self.assertRaises(self.m.RunInspectError): self.inspect()

    def test_large_valid_json_does_not_inherit_markdown_cap(self):
        self.install_current(self.change_identity(self.files, {f'marker{i:03}': 'x' * 1000 for i in range(100)}))
        self.assertGreater((self.folder / 'comparison/COMPARISON.json').stat().st_size, 65536)
        self.assertEqual(self.inspect()['difference_count'], 100)

    def test_excessive_diagnostics_keep_existing_core14_rejection(self):
        key = '/' * 16384
        left = self.change_identity(self.files, {key: [0] * 300}); right = self.change_identity(self.files, {key: [1] * 300})
        b = self.bundle.build_suite_archive(left); c = self.bundle.build_suite_archive(right)
        (self.folder / 'BASELINE.zip').write_bytes(b); (self.folder / 'CURRENT.zip').write_bytes(c)
        self.bsha, self.csha = sha(b), sha(c)
        with self.assertRaises(self.m.RunInspectError) as found: self.inspect()
        self.assertIn('ARCHIVE_COMPARE_DETAIL_BYTE_LIMIT', found.exception.code)

    def test_stored_report_is_never_parsed_as_external_json(self):
        raw = b'NOT_JSON_OR_RENDERER_INPUT'; (self.folder / 'comparison/COMPARISON.json').write_bytes(raw)
        original = json.loads
        def guarded(value, *args, **kwargs):
            if value == raw or value == raw.decode(): raise AssertionError('external report JSON parsed')
            return original(value, *args, **kwargs)
        with patch('json.loads', side_effect=guarded), self.assertRaises(self.m.RunInspectError): self.inspect()

    def test_consistent_rebuilt_metadata_is_not_origin_or_execution_proof(self):
        self.install_current(self.change_identity(self.files, {'asserted_origin': 'unverified invention'}))
        result = self.inspect()
        self.assertEqual(result['inspection_status'], 'SAVED_ARCHIVE_RUN_CONSISTENT')
        self.assertFalse(result['source_identity_reauthenticated']); self.assertFalse(result['arithmetic_recomputed'])

    def test_capture_describes_saved_bytes_not_later_live_mutation(self):
        original = self.m._capture; target = self.folder / 'suite/sign-cycle/INPUT.json'; before = sha(target.read_bytes())
        def capture(path):
            result = original(path)
            if path.name == 'sign-cycle': target.write_bytes(b'changed after capture')
            return result
        with patch.object(self.m, '_capture', side_effect=capture): result = self.inspect()
        self.assertEqual(result['captured_file_sha256']['suite/sign-cycle/INPUT.json'], before)
        self.assertNotEqual(sha(target.read_bytes()), before)

    def test_repeated_reads_are_deterministic(self): self.assertEqual(canonical(self.inspect()), canonical(self.inspect()))

    def test_cli_valid_inspection_matches_api_and_rejects_execution_options(self):
        command = self.cli(); self.assertEqual(command.returncode, 0, command.stderr); self.assertEqual(command.stdout, canonical(self.inspect()))
        for args in (self.args()[:-2], [*self.args(), '--run'], [*self.args(), '--output-root', '/unused'], [*self.args(), '--format', 'json']):
            result = self.cli(args); self.assertEqual(result.returncode, 2); self.assertEqual(result.stdout, b'')

    def test_cli_import_blocked_for_all_producer_and_reference_paths(self):
        script = '''import importlib.abc,runpy,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  modules=('integration_tools.core_sequence_run','integration_tools.core_sequence_archive_run','integration_tools.scenario_run','cyberlateral_dev','numpy')
  if any(fullname==m or fullname.startswith(m+'.') for m in modules) or fullname.startswith(('integration_tools.synthetic_','integration_tools.f61_')):
   raise AssertionError('forbidden import:'+fullname)
sys.meta_path.insert(0,Block()); sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0],run_name='__main__')
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(ROOT / 'tools/core_sequence_run_inspect.py'), *self.args()], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr); self.assertEqual(result.stdout, canonical(self.inspect()))

    def test_cli_cache_failure_never_accesses_input(self):
        cli = self.cli_module(); err = StringIO()
        with patch.object(cli.tempfile, 'TemporaryDirectory', side_effect=OSError('cache')), patch('sys.stderr', err): self.assertEqual(cli.main(self.args()), 2)
        self.assertIn('CACHE_IO', err.getvalue())

    def test_cli_cleanup_failure_prevents_receipt_and_restores_prefix(self):
        cli = self.cli_module(); original = tempfile.TemporaryDirectory; before = sys.pycache_prefix
        class BadCleanup(original):
            def __exit__(self, exc, value, tb):
                super().__exit__(exc, value, tb); raise OSError('cleanup')
        err, out = StringIO(), StringIO()
        with patch.object(cli.tempfile, 'TemporaryDirectory', BadCleanup), patch('sys.stderr', err), patch('sys.stdout', out): self.assertEqual(cli.main(self.args()), 2)
        self.assertEqual(out.getvalue(), ''); self.assertEqual(sys.pycache_prefix, before); self.assertIn('NO_MODEL_EXECUTION', err.getvalue())

    def test_cli_stdout_failure_keeps_input_unchanged(self):
        cli = self.cli_module(); err = StringIO(); before = self.snapshot()
        with patch('sys.stdout', StringIO()), patch('sys.stderr', err): self.assertEqual(cli.main(self.args()), 2)
        self.assertIn('NO_MODEL_EXECUTION', err.getvalue()); self.assertEqual(before, self.snapshot())
