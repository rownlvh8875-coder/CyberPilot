"""R27 orchestration/report/publication tests; external qualification I/O doubled."""

import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from suite_fixture import write_stage
from v1_helpers import ROOT

IDS = ['R19', 'R20', 'R21', 'R22', 'R23', 'R24', 'R25', 'R26']
MODES = [None, 'owned_boundary', 'semantic_bridge', 'model_consumption', 'model_sequence', 'fault_boundaries', 'driver_boundaries', 'negative_cycle']


class SuiteRunnerTests(unittest.TestCase):
    def modules(self):
        self.assertTrue((ROOT / 'native_qualification/suite.py').is_file(), 'Missing explicit suite runner')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('native_qualification.suite'), importlib.import_module('native_qualification.suite_report')

    def invoke(self, suite, output, *, effect=None, python=Path('/test/python')):
        def qualify(given_python, wheel, path, **kwargs):
            stage = path.name
            index = IDS.index(stage)
            mode = MODES[index]
            expected: dict[str, Any] = {} if mode is None else {mode: True}
            if index >= 2:
                expected['package_wheel'] = Path('/test/public.whl')
            if given_python != python or wheel != Path('/test/native.whl') or kwargs != expected:
                raise AssertionError('WRONG_FIXED_MODE_OR_INPUT_IDENTITY')
            if effect is not None:
                return effect(stage, path)
            return write_stage(path, stage)
        with patch.object(suite, '_preflight'), patch.object(suite, 'qualify', side_effect=qualify):
            return suite.run_suite(python, Path('/test/native.whl'), Path('/test/public.whl'), output, enabled=True)

    def rows(self):
        from native_qualification.suite_validation import validate_stage
        with tempfile.TemporaryDirectory() as scratch:
            rows = []
            for stage in IDS:
                path = Path(scratch) / stage
                write_stage(path, stage)
                rows.append(validate_stage(path, stage))
            return rows

    def test_explicit_opt_in_types_parent_and_existing_outputs_block_before_work(self):
        suite, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch, patch.object(suite, 'qualify', side_effect=AssertionError('no qualification')):
            root = Path(scratch)
            for enabled, code in [(False, 'SUITE_OPT_IN_REQUIRED'), (1, 'SUITE_EXPLICIT_BOOL')]:
                with self.assertRaisesRegex(ValueError, code):
                    suite.run_suite(root / 'python', root / 'wheel', root / 'public', root / 'output', enabled=enabled)
            with self.assertRaisesRegex(ValueError, 'SUITE_PARENT_REQUIRED'):
                suite.run_suite(root / 'python', root / 'wheel', root / 'public', root / 'missing/output', enabled=True)
            for kind in ['file', 'directory', 'dangling']:
                output = root / kind
                if kind == 'file':
                    output.write_bytes(b'preserve')
                elif kind == 'directory':
                    output.mkdir()
                else:
                    output.symlink_to(root / 'absent')
                with self.assertRaisesRegex(FileExistsError, 'OUTPUT_EXISTS'):
                    suite.run_suite(root / 'python', root / 'wheel', root / 'public', output, enabled=True)
            self.assertEqual((root / 'file').read_bytes(), b'preserve')
            self.assertFalse((root / 'output').exists())

    def test_real_preflight_rejects_wrong_wheels_or_missing_interpreter(self):
        suite, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch, patch.object(suite, 'qualify', side_effect=AssertionError('no worker')):
            root = Path(scratch)
            wrong = root / 'wrong.whl'
            wrong.write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError, 'PUBLIC_WHEEL_IDENTITY'):
                suite.run_suite(root / 'python', wrong, wrong, root / 'output', enabled=True)
            with patch.object(suite, 'verify_experiment'), self.assertRaisesRegex(ValueError, 'WHEEL_IDENTITY'):
                suite.run_suite(root / 'python', wrong, wrong, root / 'output', enabled=True)
            with patch.object(suite, 'verify_experiment'), patch.object(suite, 'verify_inputs'), self.assertRaisesRegex(ValueError, 'SUITE_PYTHON_PATH'):
                suite.run_suite(root / 'python', wrong, wrong, root / 'output', enabled=True)
            self.assertFalse((root / 'output').exists())

    def test_complete_eight_modes_publish_exact_scoped_counts_and43_hashes(self):
        suite, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / 'output'
            result = self.invoke(suite, output)
            self.assertEqual(result['status'], 'F70UGZ_R27_FIXED_NATIVE_SUITE_PASS')
            self.assertEqual((result['stage_count'], result['worker_processes'], result['model_execution']), (8, 16, 454))
            self.assertEqual([row['stage_id'] for row in result['stages']], IDS)
            self.assertEqual([row['model_execution'] for row in result['stages']], [0, 0, 0, 10, 8, 198, 40, 198])
            self.assertEqual(json.loads((output / 'SUITE_SUMMARY.json').read_bytes()), result)
            lines = (output / 'SHA256SUMS.txt').read_text().splitlines()
            self.assertEqual(len(lines), 43)
            for line in lines:
                expected, name = line.split('  ', 1)
                self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), expected)

    def test_stage_failure_aborts_without_final_or_later_execution(self):
        suite, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / 'output'
            seen = []
            def effect(stage, path):
                seen.append(stage)
                if stage == 'R23':
                    raise ValueError('STAGE_FAILED')
                return write_stage(path, stage)
            with self.assertRaisesRegex(ValueError, 'STAGE_FAILED'):
                self.invoke(suite, output, effect=effect)
            self.assertEqual(seen, ['R19', 'R20', 'R21', 'R22', 'R23'])
            self.assertFalse(output.exists())

    def test_forged_child_artifact_does_not_publish(self):
        suite, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / 'output'
            def effect(stage, path):
                return write_stage(path, stage, mutate=lambda record: record['summary'].update(actual_input='ALLOWED'))
            with self.assertRaisesRegex(ValueError, 'SUITE_SUMMARY'):
                self.invoke(suite, output, effect=effect)
            self.assertFalse(output.exists())
        for problem, code in [('late_corruption', 'SUITE_MANIFEST'), ('extra_root', 'SUITE_STAGING_FILES')]:
            with tempfile.TemporaryDirectory() as scratch:
                output = Path(scratch) / 'output'
                def late(stage, path, problem=problem):
                    result = write_stage(path, stage)
                    if stage == 'R26':
                        if problem == 'late_corruption':
                            (path.parent / 'R19/SUMMARY.json').write_bytes(b'{}\n')
                        else:
                            (path.parent / 'EXTRA').write_bytes(b'not registered')
                    return result
                with self.assertRaisesRegex(ValueError, code):
                    self.invoke(suite, output, effect=late)
                self.assertFalse(output.exists())

    def test_returned_summary_must_match_validated_artifact(self):
        suite, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / 'output'
            def effect(stage, path):
                result = write_stage(path, stage)
                result['model_execution'] = 999
                return result
            with self.assertRaisesRegex(ValueError, 'SUITE_RETURN_MISMATCH'):
                self.invoke(suite, output, effect=effect)
            self.assertFalse(output.exists())

    def test_report_rejects_missing_duplicate_reordered_or_false_count_rows(self):
        _, report = self.modules()
        rows = self.rows()
        for changed in [rows[:-1], [rows[0], *rows[:-1]], list(reversed(rows)), [dict(rows[0], model_execution=True), *rows[1:]]]:
            with self.assertRaisesRegex(ValueError, 'SUITE_COVERAGE'):
                report.build_summary(changed)

    def test_portable_summary_and_report_ignore_environment_receipt_differences(self):
        suite, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            self.invoke(suite, root / 'first', python=Path('/first/python'))
            self.invoke(suite, root / 'second', python=Path('/second/python'))
            for name in ['SUITE_SUMMARY.json', 'SUITE_REPORT_KO.md']:
                self.assertEqual((root / 'first' / name).read_bytes(), (root / 'second' / name).read_bytes())
            self.assertNotEqual((root / 'first/SUITE_RECEIPT.json').read_bytes(), (root / 'second/SUITE_RECEIPT.json').read_bytes())
        script = ('import sys;sys.path.insert(0,' + repr(str(ROOT)) + ');import native_qualification.suite;'
                  'assert not any(n.split(".")[0] in {"capnp","numpy","cyberlateral_dev","openpilot","opendbc","cereal"} for n in sys.modules)')
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_cli_help_opt_in_and_unknown_input_flags_never_create_output(self):
        self.modules()
        command = [sys.executable, '-I', '-B', str(ROOT / 'native_qualification/suite.py')]
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / 'output'
            help_result = subprocess.run([*command, '--help'], capture_output=True, check=False)
            self.assertEqual(help_result.returncode, 0)
            self.assertIn(b'--fixed-native-suite', help_result.stdout)
            args = ['--python', '/missing/python', '--wheel', '/missing/native', '--package-wheel', '/missing/public', '--output', str(output)]
            for extra in [[], ['--fixed-native-suite', '--stage', 'R22'], ['--fixed-native-suite', '--r', '0'], ['--fixed-native-suite', '--data', 'actual']]:
                result = subprocess.run([*command, *args, *extra], capture_output=True, check=False)
                self.assertEqual(result.returncode, 2, result.stderr.decode())
                self.assertFalse(output.exists())

    def test_report_keeps_unsupported_capabilities_and_real_gates_closed(self):
        _, report = self.modules()
        result = report.build_summary(self.rows())
        self.assertEqual(result['capabilities']['generic_native_reader'], 'NOT_IMPLEMENTED')
        self.assertEqual(result['capabilities']['actual_call_custody'], 'NOT_QUALIFIED')
        self.assertEqual(result['gates']['R_BUDGET'], 'UNRESOLVED')
        self.assertEqual(result['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
        self.assertEqual(result['gates']['actual_activation'], 'NOT_ALLOWED')
        self.assertEqual(result['default_pure_gate'], 'UNCHANGED_NOT_RUN_BY_THIS_COMMAND')
        self.assertEqual(result['gates']['F61_execution'], 0)
        rendered = report.render_report(result)
        self.assertIn('R19', rendered)
        self.assertIn('R26', rendered)
        self.assertIn('UNRESOLVED', rendered)
        self.assertIn('NOT_IMPLEMENTED', rendered)

    def test_late_output_claim_is_preserved_without_overwrite(self):
        suite, _ = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            output = Path(scratch) / 'output'
            def effect(stage, path):
                if stage == 'R26':
                    output.mkdir()
                    (output / 'USER_DATA').write_bytes(b'preserve')
                return write_stage(path, stage)
            with self.assertRaises(FileExistsError):
                self.invoke(suite, output, effect=effect)
            self.assertEqual((output / 'USER_DATA').read_bytes(), b'preserve')
            self.assertFalse((output / 'SUITE_SUMMARY.json').exists())

    def test_publication_error_leaves_no_success_and_summary_is_last_link(self):
        suite, _ = self.modules()
        original = os.link
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            def fail(source, target):
                if Path(target).name == 'SUITE_REPORT_KO.md':
                    raise OSError('LINK_FAILED')
                return original(source, target)
            with patch.object(suite.os, 'link', side_effect=fail), self.assertRaisesRegex(OSError, 'LINK_FAILED'):
                self.invoke(suite, root / 'failed')
            self.assertTrue((root / 'failed').is_dir())
            self.assertFalse((root / 'failed/SUITE_SUMMARY.json').exists())
            order = []
            def track(source, target):
                order.append(Path(target).name)
                return original(source, target)
            with patch.object(suite.os, 'link', side_effect=track):
                self.invoke(suite, root / 'passed')
            self.assertEqual(order[-1], 'SUITE_SUMMARY.json')


if __name__ == '__main__':
    unittest.main()
