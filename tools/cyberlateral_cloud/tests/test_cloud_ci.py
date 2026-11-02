"""Verifier behavior: real files/CLI and independent expected ledger/manifest values."""

import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))


class CloudVerifierTests(unittest.TestCase):
    def module(self):
        self.assertTrue((TOOLS / 'ci_verify.py').is_file(), 'shared cloud verifier missing')
        return importlib.import_module('ci_verify')

    def logs(self, root):
        values = {'sdk-version.log': b'{"python":"3.12.13","version":"2.4.0","prefix":"/sdk"}\n',
                  'unittest.log': b'cases\n\nRan 73 tests in 1.125s\n\nOK\n',
                  'ruff.log': b'All checks passed!\n', 'ty.log': b'All checks passed!\n', 'codespell.log': b''}
        for name, raw in values.items():
            (root / name).write_bytes(raw)

    def test_ledger_accepts_complete_dynamic_count_without_hardcoded_new_total(self):
        c = self.module()
        self.assertEqual(c.validate_ledger('Ran 70 tests in 1.234s\n\nOK\n'), 70)
        self.assertEqual(c.validate_ledger('details\nRan 87 tests in 6.000s\n\nOK\n'), 87)

    def test_ledger_rejects_small_truncated_failed_skipped_and_duplicate_runs(self):
        c = self.module()
        invalid = ['Ran 69 tests in 1.0s\nOK\n', 'Ran 0 tests in 1.0s\nOK\n',
                   'Ran 70 tests in 1..0s\nOK\n',
                   'Ran 70 tests in 1.0s\n', 'Ran 70 tests in 1.0s\nFAILED (failures=1)\n',
                   'Ran 70 tests in 1.0s\nOK (skipped=1)\n',
                   'Ran 70 tests in 1.0s\nOK\nRan 71 tests in 1.0s\nOK\n',
                   'FAILED\nRan 70 tests in 1.0s\nOK\n']
        for text in invalid:
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, 'CI_TEST_LEDGER'):
                c.validate_ledger(text)

    def test_compile_owned_does_not_execute_and_hashes_only_python(self):
        c = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'nested').mkdir()
            (root / 'one.py').write_bytes(b'raise AssertionError("must not execute")\n')
            (root / 'nested/two.py').write_bytes(b'value = 2\n')
            (root / 'README.md').write_bytes(b'not python')
            result = c.compile_owned(root)
            self.assertEqual(set(result), {'one.py', 'nested/two.py'})
            self.assertEqual(result['nested/two.py'], hashlib.sha256(b'value = 2\n').hexdigest())
            self.assertFalse((root / '__pycache__').exists())

    def test_compile_rejects_syntax_errors_and_symlink_sources(self):
        c = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            invalid = root / 'bad.py'
            invalid.write_bytes(b'def broken(:\n')
            with self.assertRaisesRegex(ValueError, 'COMPILE'):
                c.compile_owned(root)
            invalid.unlink()
            (root / 'outside.txt').write_bytes(b'pass\n')
            (root / 'link.py').symlink_to(root / 'outside.txt')
            with self.assertRaisesRegex(ValueError, 'SOURCE_SYMLINK'):
                c.compile_owned(root)

    def test_success_summary_and_closed_manifest_match_actual_log_bytes(self):
        c = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.logs(root)
            result = c.seal_results(root, {'example.py': 'a' * 64})
            self.assertEqual(result['status'], 'CYBERLATERAL_CLOUD_VERIFICATION_PASS')
            self.assertEqual((result['tests'], result['own_compiles']), (73, 1))
            self.assertEqual(result['gates']['R_BUDGET'], 'UNRESOLVED')
            self.assertEqual(result['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
            self.assertIsNone(result['gates']['actual_r'])
            self.assertEqual(json.loads((root / 'SUMMARY.json').read_bytes()), result)
            manifest = dict(line.split('  ', 1)[::-1] for line in (root / 'SHA256SUMS.txt').read_text().splitlines())
            self.assertEqual(set(manifest), {'unittest.log', 'sdk-version.log', 'ruff.log', 'ty.log', 'codespell.log', 'SUMMARY.json'})
            for name, value in manifest.items():
                self.assertEqual(value, hashlib.sha256((root / name).read_bytes()).hexdigest())

    def test_failed_logs_or_extra_files_never_get_success_summary(self):
        c = self.module()
        for name, value in [('unittest.log', b'Ran 70 tests in 1.0s\nFAILED\n'),
                            ('ruff.log', b'error'), ('ty.log', b'error'),
                            ('codespell.log', b'spelling error'), ('private.log', b'extra')]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.logs(root)
                (root / name).write_bytes(value)
                with self.assertRaises(ValueError):
                    c.seal_results(root, {'example.py': 'a' * 64})
                self.assertFalse((root / 'SUMMARY.json').exists())
                self.assertFalse((root / 'SHA256SUMS.txt').exists())

    def test_cli_existing_output_is_untouched(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'keep').write_bytes(b'preserved')
            result = subprocess.run([sys.executable, '-B', TOOLS / 'ci_verify.py', '--hf-python', '/bin/false',
                                     '--output', root], capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['code'], 'OUTPUT_EXISTS')
            self.assertEqual([p.name for p in root.iterdir()], ['keep'])

    def test_cli_missing_sdk_preserves_failure_without_suite_or_summary(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / 'new'
            result = subprocess.run([sys.executable, '-B', TOOLS / 'ci_verify.py', '--hf-python', root / 'missing',
                                     '--output', output], capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['code'], 'HF_INTERPRETER_REQUIRED')
            self.assertEqual(json.loads((output / 'FAILURE.json').read_bytes())['stage'], 'PREFLIGHT')
            self.assertEqual([p.name for p in output.iterdir()], ['FAILURE.json'])


if __name__ == '__main__':
    unittest.main()
