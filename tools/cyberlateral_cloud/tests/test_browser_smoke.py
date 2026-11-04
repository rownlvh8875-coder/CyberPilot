"""Reusable command boundary tests; actual layout runs are separate and explicit."""

import hashlib
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
COMPONENT = TOOLS.parent / 'cyberlateral_dev'
sys.path.insert(0, str(TOOLS))


class BrowserSmokeTests(unittest.TestCase):
    def module(self):
        self.assertTrue((TOOLS / 'browser_smoke.py').is_file(), 'reusable browser command missing')
        return importlib.import_module('browser_smoke')

    def command(self, *args):
        return subprocess.run([sys.executable, '-B', TOOLS / 'browser_smoke.py', *map(str, args)],
                              capture_output=True, timeout=20)

    def test_help_needs_neither_browser_nor_playwright(self):
        result = self.command('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'--app-python', result.stdout)

    def test_missing_browser_is_bounded_rejection_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'new'
            result = self.command('--component', COMPONENT, '--app-python', sys.executable,
                                  '--browser', Path(tmp) / 'missing', '--output', output)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b'BROWSER_EXECUTABLE_REQUIRED', result.stderr)
            self.assertNotIn(b'Traceback', result.stderr)
            self.assertFalse(output.exists())

    def test_missing_component_and_app_are_not_browser_successes(self):
        b = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for component, app, code in [(root / 'missing', Path(sys.executable), 'COMPONENT'),
                                         (COMPONENT, root / 'missing', 'APP_INTERPRETER')]:
                with self.subTest(code=code), self.assertRaisesRegex(ValueError, code):
                    b.validate_paths(component, app, Path(sys.executable), root / 'new')
            self.assertFalse((root / 'new').exists())

    def test_existing_output_is_not_overwritten_or_given_failure_files(self):
        b = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / 'existing'
            output.mkdir()
            (output / 'marker').write_bytes(b'keep')
            with self.assertRaisesRegex((ValueError, FileExistsError), 'OUTPUT_EXISTS'):
                b.validate_paths(COMPONENT, Path(sys.executable), Path(sys.executable), output)
            self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, {'marker': b'keep'})

    def test_symlink_and_component_output_are_rejected_before_writes(self):
        b = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            link = root / 'link'
            link.symlink_to(root / 'missing')
            alias = root / 'parent'
            alias.symlink_to(root, target_is_directory=True)
            for output in [link, alias / 'new', COMPONENT / 'r60-must-not-create']:
                with self.subTest(output=output), self.assertRaises((ValueError, FileExistsError)):
                    b.validate_paths(COMPONENT, Path(sys.executable), Path(sys.executable), output)
            self.assertFalse((COMPONENT / 'r60-must-not-create').exists())

    def test_source_hashes_detect_fixture_edits_without_importing_them(self):
        b = self.module()
        before = b.source_snapshot(COMPONENT)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in before:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(COMPONENT / name, path)
            self.assertEqual(b.source_snapshot(root), before)
            changed = root / 'project/fixtures/r31_report/sign/INPUT.json'
            changed.write_bytes(b'not imported\n')
            self.assertNotEqual(b.source_snapshot(root), before)

    def test_symlinked_fixture_source_is_not_treated_as_owned(self):
        b = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in b.source_snapshot(COMPONENT):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(COMPONENT / name, path)
            path = root / 'project/scenario_report_fixture.py'
            path.unlink()
            path.symlink_to(COMPONENT / 'project/scenario_report_fixture.py')
            with self.assertRaisesRegex(ValueError, 'COMPONENT_SOURCE'):
                b.source_snapshot(root)

    def test_render_uses_preserved_results_and_no_model_imports(self):
        b = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            reports = b.prepare_reports(COMPONENT, Path(sys.executable), output)
            for profile, finals in [('sign', [2, -2, 0, 2]), ('resumed', [-2])]:
                for name in ['INPUT.json', 'RESULTS.json', 'TRACE.csv', 'SUMMARY_KO.md']:
                    self.assertEqual((output / 'fixture-inputs' / profile / name).read_bytes(),
                                     (COMPONENT / 'project/fixtures/r31_report' / profile / name).read_bytes())
                receipt = json.loads((reports / profile / 'RECEIPT.json').read_bytes())
                self.assertEqual(receipt['forbidden_modules_loaded'], [])
                self.assertEqual(receipt['renderer_model_executions'], 0)
                view = json.loads((reports / profile / 'VIEW.json').read_bytes())
                self.assertEqual([row['final_command'] for row in view['rows']], finals)

    def test_completed_result_manifest_closes_over_actual_files(self):
        b = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'capture.png').write_bytes(b'not an actual browser capture')
            b.publish_result(root, importlib.import_module('browser_result_fixture').result_fixture())
            manifest = dict(line.split('  ', 1)[::-1] for line in (root / 'SHA256SUMS.txt').read_text().splitlines())
            self.assertEqual(set(manifest), {'capture.png', 'RESULT.json', 'SUMMARY_KO.md'})
            for name, digest in manifest.items():
                self.assertEqual(digest, hashlib.sha256((root / name).read_bytes()).hexdigest())

    def test_manifest_publication_error_cannot_leave_a_success_result(self):
        b = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'SHA256SUMS.txt').mkdir()
            with self.assertRaises(OSError):
                b.publish_result(root, importlib.import_module('browser_result_fixture').result_fixture())
            self.assertFalse((root / 'RESULT.json').exists())

    def test_summary_write_failure_cannot_create_checksum_or_result(self):
        b = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'SUMMARY_KO.md').mkdir()
            with self.assertRaises(OSError):
                b.publish_result(root, importlib.import_module('browser_result_fixture').result_fixture())
            self.assertFalse((root / 'RESULT.json').exists())
            self.assertFalse((root / 'SHA256SUMS.txt').exists())
            self.assertEqual(list((root / 'SUMMARY_KO.md').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
