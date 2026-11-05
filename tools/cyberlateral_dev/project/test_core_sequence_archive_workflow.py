"""Saved-only publication: exact artifacts, bounded readback and honest failures."""

import hashlib
import importlib
import importlib.util
import json
import os
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
NAMES = {'COMPARISON.json', 'SUMMARY_KO.md', 'SHA256SUMS.txt'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


class CoreArchiveWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'integration_tools/core_sequence_archive_workflow.py').is_file(), 'Missing CORE16 saved archive workflow')
        self.assertTrue((ROOT / 'tools/core_sequence_archive_workflow.py').is_file(), 'Missing CORE16 workflow CLI')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        self.m: Any = importlib.import_module('integration_tools.core_sequence_archive_workflow')
        self.report = importlib.import_module('integration_tools.core_sequence_archive_report')
        self.bundle = importlib.import_module('integration_tools.core_sequence_bundle')
        self.compare = importlib.import_module('integration_tools.core_sequence_archive_compare')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        producer = importlib.import_module('integration_tools.core_sequence_run')
        self.source = {}
        for case in CASES:
            folder = self.root / case; producer.run_sequence_case(case, folder)
            for name in ('INPUT.json', 'RESULTS.json', 'SHA256SUMS.txt'):
                self.source['suite/' + case + '/' + name] = (folder / name).read_bytes()
        self.raw = self.bundle.build_suite_archive(self.source)
        self.left = self.root / 'left.zip'; self.left.write_bytes(self.raw)
        self.right = self.root / 'right.zip'; self.right.write_bytes(self.raw)
        self.output = self.root / 'output'

    def publish(self, output=None):
        return self.m.publish_archive_report(self.left, sha(self.raw), self.right, sha(self.right.read_bytes()), self.output if output is None else output)

    def changed(self, count=1, width=1):
        files = dict(self.source); prefix = 'suite/late-invalid/'
        record = json.loads(files[prefix + 'RESULTS.json'])
        record['identity'].update({f'marker{i:03}': 'x' * width for i in range(count)})
        files[prefix + 'RESULTS.json'] = canonical(record)
        files[prefix + 'SHA256SUMS.txt'] = ''.join(sha(files[prefix + n]) + '  ' + n + '\n' for n in ('INPUT.json', 'RESULTS.json')).encode()
        self.right.write_bytes(self.bundle.build_suite_archive(files))

    def args(self, output=None):
        return ['--left-archive', str(self.left), '--left-sha256', sha(self.raw), '--right-archive', str(self.right),
                '--right-sha256', sha(self.right.read_bytes()), '--output-root', str(self.output if output is None else output)]

    def cli(self, args=None):
        return subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/core_sequence_archive_workflow.py', *(self.args() if args is None else args)], capture_output=True)

    def cli_module(self):
        spec = importlib.util.spec_from_file_location('core16_cli_test', ROOT / 'tools/core_sequence_archive_workflow.py')
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def assert_package(self, receipt):
        self.assertEqual({p.name for p in self.output.iterdir()}, NAMES)
        compared, markdown = self.report.report_suite_archives(self.left, sha(self.raw), self.right, sha(self.right.read_bytes()))
        self.assertEqual((self.output / 'COMPARISON.json').read_bytes(), canonical(compared))
        self.assertEqual((self.output / 'SUMMARY_KO.md').read_bytes(), markdown)
        expected = ''.join(sha((self.output / name).read_bytes()) + '  ' + name + '\n' for name in ('COMPARISON.json', 'SUMMARY_KO.md')).encode()
        self.assertEqual((self.output / 'SHA256SUMS.txt').read_bytes(), expected)
        self.assertEqual(receipt['files'], {n: {'sha256': sha((self.output / n).read_bytes()), 'byte_size': (self.output / n).stat().st_size} for n in NAMES})
        self.assertEqual(receipt['contract_id'], 'CORE16_ARCHIVE_WORKFLOW_V1')
        self.assertEqual(receipt['status'], 'ARCHIVE_REPORT_PUBLISHED')
        self.assertEqual(receipt['gates']['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(receipt['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
        self.assertFalse(receipt['source_identity_reauthenticated'])
        self.assertFalse(receipt['arithmetic_recomputed'])
        self.assertEqual(receipt['new_synthetic_model_steps'], 0)
        self.assertEqual(receipt['comparison_reference_executions'], 0)

    # Break: wrapping/changing CORE14 JSON or treating stored REJECTED as CLI failure.
    def test_identical_package_preserves_original_artifacts_and_saved_outcomes(self):
        r = self.publish(); self.assert_package(r)
        self.assertEqual(r['comparison_exit_code'], 0)
        saved = json.loads((self.output / 'COMPARISON.json').read_bytes())
        self.assertEqual(saved['left']['suite']['saved_status_counts'], {'MATCH': 1, 'DIFFERENT': 1, 'REJECTED': 1})
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in self.output.iterdir()))

    def test_different_is_published_success_with_comparison_exit_one(self):
        self.changed(); r = self.publish(); self.assert_package(r)
        self.assertEqual(r['comparison_exit_code'], 1)
        self.assertEqual(r['comparison_status'], 'SAVED_SUITE_ARCHIVES_DIFFERENT')

    def test_two_destinations_produce_identical_files_and_receipts(self):
        r = self.publish(); other = self.root / 'other'
        self.assertEqual(self.publish(other), r)
        for n in NAMES: self.assertEqual((self.output / n).read_bytes(), (other / n).read_bytes())

    def test_source_roles_captured_once_and_inputs_unchanged(self):
        original = os.open; opens = []
        before = [(p.read_bytes(), p.stat().st_mode) for p in (self.left, self.right)]
        def observed(path, flags, *args, **kwargs):
            if path in (self.left, self.right): opens.append(path)
            return original(path, flags, *args, **kwargs)
        with patch('os.open', side_effect=observed): self.publish()
        self.assertEqual(opens, [self.left, self.right])
        self.assertEqual(before, [(p.read_bytes(), p.stat().st_mode) for p in (self.left, self.right)])

    def test_bad_second_digest_precedes_all_caller_path_access(self):
        with patch('os.open', side_effect=AssertionError('path access before digest rejection')):
            with self.assertRaises(self.compare.ArchiveCompareError) as found:
                self.m.publish_archive_report(self.left, sha(self.raw), self.right, 'abbreviated', self.output)
        self.assertIn('RIGHT:', found.exception.code); self.assertFalse(self.output.exists())

    def test_bad_source_hash_leaves_output_absent(self):
        with self.assertRaises(self.compare.ArchiveCompareError):
            self.m.publish_archive_report(self.left, '0' * 64, self.right, sha(self.raw), self.output)
        self.assertFalse(self.output.exists())

    def test_malformed_zip_leaves_output_absent(self):
        self.right.write_bytes(b'not a ZIP')
        with self.assertRaises(self.compare.ArchiveCompareError): self.publish()
        self.assertFalse(self.output.exists())

    def test_existing_output_is_preserved_without_capture(self):
        self.output.mkdir(); (self.output / 'sentinel').write_bytes(b'keep')
        with patch('os.open', side_effect=AssertionError('must not capture')):
            with self.assertRaises(self.m.ArchiveWorkflowError): self.publish()
        self.assertEqual((self.output / 'sentinel').read_bytes(), b'keep')

    def test_output_path_guards_do_not_create_directories(self):
        link = self.root / 'link'; link.symlink_to(self.root, target_is_directory=True)
        paths = [self.root / 'missing' / 'child', link / 'new', ROOT / 'core16-output', Path('bad\0name'), Path('bad\ud800'), 'not Path']
        for path in paths:
            with self.subTest(path=repr(path)), self.assertRaises(self.m.ArchiveWorkflowError): self.publish(path)
        self.assertFalse((self.root / 'new').exists()); self.assertFalse((ROOT / 'core16-output').exists())

    def test_dangling_output_symlink_rejected(self):
        self.output.symlink_to(self.root / 'missing')
        with self.assertRaises(self.m.ArchiveWorkflowError): self.publish()
        self.assertTrue(self.output.is_symlink())

    def test_large_valid_comparison_not_limited_to_markdown_size(self):
        self.changed(100, 1000); r = self.publish(); self.assert_package(r)
        self.assertGreater((self.output / 'COMPARISON.json').stat().st_size, 65536)
        self.assertLessEqual((self.output / 'SUMMARY_KO.md').stat().st_size, 65536)

    def test_short_writes_finish_all_bytes(self):
        original = os.write
        with patch('os.write', side_effect=lambda fd, raw: original(fd, raw[:17])): r = self.publish()
        self.assert_package(r)

    def test_no_write_progress_preserves_partial_directory_and_rejects(self):
        with patch('os.write', return_value=0), self.assertRaises(self.m.ArchiveWorkflowError) as found: self.publish()
        self.assertIn('PARTIAL_DIRECTORY_POSSIBLE', found.exception.code)
        self.assertTrue(self.output.is_dir()); self.assertTrue((self.output / 'COMPARISON.json').exists())

    def test_later_write_error_preserves_already_written_file(self):
        original = os.write
        def fail(fd, raw):
            if os.readlink('/proc/self/fd/' + str(fd)).endswith('SUMMARY_KO.md'): raise OSError('disk full')
            return original(fd, raw)
        with patch('os.write', side_effect=fail), self.assertRaises(self.m.ArchiveWorkflowError): self.publish()
        self.assertTrue(json.loads((self.output / 'COMPARISON.json').read_bytes())['archive_bytes_identical'])

    def test_exclusive_creation_race_never_overwrites(self):
        original = os.mkdir
        def race(path, *args, **kwargs):
            if path == self.output:
                original(path, *args, **kwargs); (path / 'sentinel').write_bytes(b'race')
            return original(path, *args, **kwargs)
        with patch('os.mkdir', side_effect=race), self.assertRaises(self.m.ArchiveWorkflowError): self.publish()
        self.assertEqual(list(self.output.iterdir()), [self.output / 'sentinel'])

    def test_readback_mismatch_does_not_return_success(self):
        original = os.read
        def corrupt(fd, size):
            raw = original(fd, size)
            if os.readlink('/proc/self/fd/' + str(fd)).endswith('COMPARISON.json') and raw: return b'X' + raw[1:]
            return raw
        with patch('os.read', side_effect=corrupt), self.assertRaises(self.m.ArchiveWorkflowError) as found: self.publish()
        self.assertIn('DIRECTORY_MAY_EXIST', found.exception.code); self.assertTrue(self.output.is_dir())

    def test_extra_file_during_publication_rejected(self):
        original = os.write
        def extra(fd, raw):
            written = original(fd, raw)
            (self.output / 'extra').touch(exist_ok=True)
            return written
        with patch('os.write', side_effect=extra), self.assertRaises(self.m.ArchiveWorkflowError): self.publish()
        self.assertTrue((self.output / 'extra').exists())

    def test_readback_fifo_rejected_without_blocking(self):
        original = os.open
        def fifo(path, flags, *args, **kwargs):
            if path == 'COMPARISON.json' and not flags & os.O_WRONLY:
                os.unlink(path, dir_fd=kwargs['dir_fd'])
                os.mkfifo(path, dir_fd=kwargs['dir_fd'])
            return original(path, flags, *args, **kwargs)
        with patch('os.open', side_effect=fifo), self.assertRaises(self.m.ArchiveWorkflowError): self.publish()

    def test_replaced_output_root_rejected(self):
        original = os.listdir; replaced = False
        def change(fd):
            nonlocal replaced
            if not replaced:
                self.output.rename(self.root / 'moved'); self.output.mkdir(); replaced = True
            return original(fd)
        with patch('os.listdir', side_effect=change), self.assertRaises(self.m.ArchiveWorkflowError): self.publish()
        self.assertEqual({p.name for p in (self.root / 'moved').iterdir()}, NAMES)

    def test_cli_receipt_stdout_and_comparison_exit_codes(self):
        for changed in (False, True):
            if changed: self.changed()
            output = self.root / ('cli-' + str(changed)); command = self.cli(self.args(output))
            self.assertEqual(command.returncode, int(changed), command.stderr)
            self.assertEqual(command.stderr, b'')
            receipt = json.loads(command.stdout); self.assertEqual(command.stdout, canonical(receipt))
            self.assertEqual(receipt['comparison_exit_code'], int(changed))
            self.assertEqual(receipt, self.publish(self.root / ('api-' + str(changed))))

    def test_cli_bad_arguments_and_input_never_create_output(self):
        args = self.args()
        for bad in (args[:-2], [*args, '--run'], [*args, '--format', 'json'], ['--left-arch', str(self.left), *args[2:]]):
            result = self.cli(bad); self.assertEqual(result.returncode, 2); self.assertEqual(result.stdout, b'')
        self.right.write_bytes(b'broken'); result = self.cli()
        self.assertEqual(result.returncode, 2); self.assertEqual(result.stdout, b''); self.assertFalse(self.output.exists())

    def test_cache_creation_failure_has_no_output(self):
        cli = self.cli_module(); err = StringIO()
        with patch.object(cli.tempfile, 'TemporaryDirectory', side_effect=OSError('cache')), patch('sys.stderr', err):
            self.assertEqual(cli.main(self.args()), 2)
        self.assertIn('CACHE_IO', err.getvalue()); self.assertFalse(self.output.exists())

    def test_cleanup_failure_after_publication_is_honest_and_restores_cache(self):
        cli = self.cli_module(); original = tempfile.TemporaryDirectory; before = sys.pycache_prefix
        class BadCleanup(original):
            def __exit__(self, exc, value, tb):
                super().__exit__(exc, value, tb); raise OSError('cleanup failed')
        err = StringIO(); out = StringIO()
        with patch.object(cli.tempfile, 'TemporaryDirectory', BadCleanup), patch('sys.stderr', err), patch('sys.stdout', out):
            self.assertEqual(cli.main(self.args()), 2)
        self.assertEqual(out.getvalue(), ''); self.assertIn('DIRECTORY_MAY_EXIST', err.getvalue())
        self.assertEqual(sys.pycache_prefix, before); self.assertEqual({p.name for p in self.output.iterdir()}, NAMES)

    def test_stdout_failure_after_publication_keeps_valid_package(self):
        cli = self.cli_module(); err = StringIO()
        with patch('sys.stdout', StringIO()), patch('sys.stderr', err): self.assertEqual(cli.main(self.args()), 2)
        self.assertIn('DIRECTORY_MAY_EXIST', err.getvalue()); self.assertEqual({p.name for p in self.output.iterdir()}, NAMES)

    def test_cli_does_not_import_producer_or_reference(self):
        script = '''import importlib.abc,runpy,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.startswith(('integration_tools.core_sequence_run','integration_tools.scenario_run','integration_tools.synthetic_', 'cyberlateral_dev', 'numpy')):
   raise AssertionError('forbidden import: '+fullname)
sys.meta_path.insert(0,Block())
sys.argv=sys.argv[1:]
runpy.run_path(sys.argv[0],run_name='__main__')
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(ROOT / 'tools/core_sequence_archive_workflow.py'), *self.args()], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr); self.assertEqual(json.loads(result.stdout)['new_synthetic_model_steps'], 0)
