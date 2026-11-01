"""Actual read-only CLI behavior, exact exit codes and exclusive publication."""

import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scenario_compare_fixture import refresh, write_batch
from v1_helpers import ROOT


class CompareCLITests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'tools/scenario_compare.py').is_file(), 'Missing R34 comparison CLI')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_compare_run')

    def cli(self, *args):
        return subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/scenario_compare.py', *map(str, args)],
                              capture_output=True, timeout=15, check=False)

    def test_cli_match_preserves_inputs_full_output_hashes_and_private_receipt(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = write_batch(root / 'baseline')
            after = write_batch(root / 'candidate')
            originals = {str(p): p.read_bytes() for directory in [before, after] for p in directory.rglob('*') if p.is_file()}
            result = self.cli('--baseline', before, '--candidate', after, '--output', root / 'out')
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(originals, {str(p): p.read_bytes() for directory in [before, after] for p in directory.rglob('*') if p.is_file()})
            self.assertEqual({p.name for p in (root / 'out').iterdir()}, {'COMPARE.json', 'SUMMARY_KO.md', 'RECEIPT.json', 'SHA256SUMS.txt'})
            record = json.loads((root / 'out/COMPARE.json').read_bytes())
            self.assertEqual((record['status'], record['compared_sample_count'], record['new_model_executions']), ('MATCH', 5, 0))
            receipt = json.loads((root / 'out/RECEIPT.json').read_bytes())
            self.assertEqual(receipt['forbidden_modules_loaded'], [])
            self.assertIn(str(before), json.dumps(receipt))
            self.assertNotIn(str(root).encode(), (root / 'out/COMPARE.json').read_bytes())
            self.assertNotIn(str(root).encode(), (root / 'out/SUMMARY_KO.md').read_bytes())
            for line in (root / 'out/SHA256SUMS.txt').read_text().splitlines():
                digest, name = line.split('  ')
                self.assertEqual(hashlib.sha256((root / 'out' / name).read_bytes()).hexdigest(), digest)

    def test_completed_difference_exit1_exact_field_without_new_model_work(self):
        self.module()
        from integration_tools.scenario_output import render_outputs
        from integration_tools.scenario_report_data import _spec

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before, after = write_batch(root / 'before'), write_batch(root / 'after')
            data = after / 'case-001/data'
            source, record, receipt = [json.loads((data / n).read_bytes()) for n in ['INPUT.json', 'RESULTS.json', 'RECEIPT.json']]
            record['rows'][1]['model_output']['trace']['downstream']['limited_command'] = -3
            saved = {k: record[k] for k in ['model_steps', 'rows', 'final_state']}
            for name, raw in render_outputs(_spec(source), saved, record['identity'], receipt).items():
                (data / name).write_bytes(raw)
            refresh(after)
            result = self.cli('--baseline', before, '--candidate', after, '--output', root / 'out')
            self.assertEqual(result.returncode, 1, result.stderr.decode())
            record = json.loads((root / 'out/COMPARE.json').read_bytes())
            self.assertEqual(record['first_difference']['sample_index'], 1)
            self.assertEqual(record['first_difference']['field'], 'rows[1].model_output.trace.downstream.limited_command')
            self.assertEqual((record['first_difference']['before'], record['first_difference']['after']), (-2, -3))
            self.assertEqual(record['new_model_executions'], 0)

    def test_same_saved_input_moved_produces_identical_portable_comparison(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ['one', 'two']:
                m.run_comparison(write_batch(root / ('a-' + name)), write_batch(root / ('b-' + name)), root / name)
            for name in ['COMPARE.json', 'SUMMARY_KO.md']:
                self.assertEqual((root / 'one' / name).read_bytes(), (root / 'two' / name).read_bytes())
            self.assertNotEqual((root / 'one/RECEIPT.json').read_bytes(), (root / 'two/RECEIPT.json').read_bytes())

    def test_invalid_bundle_exit2_before_any_output_publication(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'source')
            (source / 'case-002/data/TRACE.csv').write_bytes(b'corrupt')
            result = self.cli('--baseline', source, '--candidate', source, '--output', root / 'out')
            self.assertEqual(result.returncode, 2)
            self.assertIn(b'COMPARE_CHECKSUM', result.stderr)
            self.assertFalse((root / 'out').exists())

    def test_missing_raw_input_never_returns_verified_match(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'source', ('missing',))
            result = self.cli('--baseline', source, '--candidate', source, '--output', root / 'out')
            self.assertEqual(result.returncode, 1)
            record = json.loads((root / 'out/COMPARE.json').read_bytes())
            self.assertEqual(record['cases'][0]['classification'], 'UNVERIFIABLE_INPUT')

    def test_output_guards_precede_input_read_and_preserve_existing_bytes(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'source')
            (root / 'keep').write_bytes(b'keep')
            (root / 'dangling').symlink_to(root / 'absent')
            for destination, code in [(root / 'keep', 'COMPARE_OUTPUT_EXISTS'), (root / 'dangling', 'COMPARE_OUTPUT_EXISTS'),
                                      (root / 'absent/out', 'COMPARE_OUTPUT_PARENT'), (source / 'out', 'COMPARE_OUTPUT_LOCATION'),
                                      (ROOT / 'r34-forbidden-output', 'COMPARE_OUTPUT_LOCATION')]:
                with self.subTest(code=code), patch.object(m, 'read_batch', side_effect=AssertionError('INPUT_READ')), self.assertRaises(m.CompareError) as caught:
                    m.run_comparison(source, source, destination)
                self.assertEqual(caught.exception.code, code)
            self.assertEqual((root / 'keep').read_bytes(), b'keep')

    def test_non_utf8_paths_and_symlink_loop_reject_without_traceback(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'source')
            (root / 'loop').symlink_to('loop')
            for before, output, code in [(root / 'loop', root / 'out', b'COMPARE_INPUT_FILE'),
                                         (source, root / 'bad_\udcff', b'COMPARE_PATH_ENCODING')]:
                result = self.cli('--baseline', before, '--candidate', source, '--output', output)
                self.assertEqual(result.returncode, 2)
                self.assertIn(code, result.stderr)
                self.assertNotIn(b'Traceback', result.stderr)
                self.assertFalse(output.exists())

    def test_partial_publication_has_no_completed_marker_and_cannot_be_reused(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'source')
            original = m._write_exclusive

            def fail_completion(path, raw):
                if path.name == 'COMPARE.json':
                    raise OSError('synthetic write fault')
                original(path, raw)

            with patch.object(m, '_write_exclusive', side_effect=fail_completion), self.assertRaises(m.CompareError) as caught:
                m.run_comparison(source, source, root / 'out')
            self.assertEqual(caught.exception.code, 'COMPARE_PUBLICATION_FAILED')
            self.assertFalse((root / 'out/COMPARE.json').exists())
            self.assertTrue((root / 'out/SUMMARY_KO.md').exists())
            with self.assertRaises(m.CompareError) as caught:
                m.run_comparison(source, source, root / 'out')
            self.assertEqual(caught.exception.code, 'COMPARE_OUTPUT_EXISTS')

    def test_help_unknown_abbreviations_and_policy_fallback_rejected(self):
        self.module()
        self.assertEqual(self.cli('--help').returncode, 0)
        for args in [('--bas', 'x'), ('--rate-budget', '0'), ('--tolerance', '0.01'), ('--update-baseline',)]:
            self.assertEqual(self.cli(*args).returncode, 2)

    def test_fresh_cli_succeeds_with_model_native_imports_blocked(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / 'source')
            code = ('import importlib.abc,runpy,sys\n'
                    'class Block(importlib.abc.MetaPathFinder):\n'
                    ' def find_spec(self,fullname,path=None,target=None):\n'
                    '  if fullname.split(".")[0] in {"cyberlateral_dev","numpy","capnp","openpilot","opendbc","cereal"}:\n'
                    '   raise AssertionError("FORBIDDEN_MODEL_OR_NATIVE_IMPORT")\n'
                    'sys.meta_path.insert(0,Block())\n'
                    'sys.argv=' + repr(['scenario_compare.py', '--baseline', str(source), '--candidate', str(source), '--output', str(root / 'out')]) + '\n'
                    'runpy.run_path(' + repr(str(ROOT / 'tools/scenario_compare.py')) + ',run_name="__main__")\n')
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, timeout=15, check=False)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertTrue((root / 'out/COMPARE.json').is_file())
