"""Saved-record path errors are bounded before reads, not later defect masking."""

import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scenario_report_fixture import write_bundle
from v1_helpers import ROOT


class ScenarioReportPathTests(unittest.TestCase):
    def modules(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return (importlib.import_module('integration_tools.scenario_report_data'),
                importlib.import_module('integration_tools.scenario_report_run'))

    def rejection(self, call, code):
        reader, _ = self.modules()
        try:
            call()
        except reader.ReportError as error:
            self.assertEqual(error.code, code)
            return error
        except Exception as error:
            self.fail(f'Unbounded path failure: {type(error).__name__}')
        self.fail('Invalid report path accepted')

    def isolated_cli(self, arguments):
        blocked = {'cyberlateral_dev', 'numpy', 'capnp', 'openpilot', 'opendbc', 'cereal',
                   'integration_tools.scenario_engine', 'integration_tools.scenario_reference_run'}
        code = ('import importlib.util,sys\n'
                'sys.path.insert(0,' + repr(str(ROOT)) + ')\n'
                'blocked=' + repr(blocked) + '\n'
                'class Barrier:\n'
                ' def find_spec(self, fullname, path=None, target=None):\n'
                '  if fullname in blocked or fullname.split(".")[0] in blocked: raise AssertionError("MODEL_IMPORT:"+fullname)\n'
                'sys.meta_path.insert(0,Barrier())\n'
                'spec=importlib.util.spec_from_file_location("actual_cli",' + repr(str(ROOT / 'tools/scenario_report.py')) + ')\n'
                'cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)\n'
                'status=cli.main(' + repr(arguments) + ')\n'
                'assert not any(n in blocked or n.split(".")[0] in blocked for n in sys.modules)\n'
                'raise SystemExit(status)\n')
        return subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, timeout=20, check=False)

    def test_reader_invalid_paths_reject_before_snapshot_or_decode(self):
        reader, _ = self.modules()
        for text, cause in [('invalid\0source', ValueError), ('invalid\ud800source', UnicodeEncodeError)]:
            with (self.subTest(kind=cause.__name__),
                  patch.object(reader.os, 'fdopen', side_effect=AssertionError('SNAPSHOT')),
                  patch.object(reader, 'decode_report', side_effect=AssertionError('DECODE'))):
                error = self.rejection(lambda text=text: reader.read_report(Path(text)), 'REPORT_INPUT_FILE')
                self.assertIsInstance(error.__cause__, cause)

    def test_reader_open_errors_and_classified_original_cause(self):
        reader, _ = self.modules()
        for original in [ValueError('private-open'), PermissionError('private-permission')]:
            with patch.object(reader.os, 'open', side_effect=original):
                error = self.rejection(lambda: reader.read_report(Path('unused')), 'REPORT_INPUT_FILE')
                self.assertIs(error.__cause__, original)
        original_cause = ValueError('independent-original-cause')
        classified = reader.ReportError('REPORT_SIZE')
        classified.__cause__ = original_cause
        with patch.object(reader.os, 'open', side_effect=classified), self.assertRaises(reader.ReportError) as caught:
            reader.read_report(Path('unused'))
        self.assertIs(caught.exception, classified)
        self.assertEqual(caught.exception.code, 'REPORT_SIZE')
        self.assertIs(caught.exception.__cause__, original_cause)

    def test_member_open_value_error_closes_real_directory_descriptor(self):
        reader, _ = self.modules()
        actual_open = os.open
        descriptors = []
        original = ValueError('member-open')

        def fail_member(path, flags, **kwargs):
            if 'dir_fd' in kwargs:
                raise original
            descriptor = actual_open(path, flags, **kwargs)
            descriptors.append(descriptor)
            return descriptor

        with tempfile.TemporaryDirectory() as tmp:
            source = write_bundle(Path(tmp) / 'source')
            before = {p.name: p.read_bytes() for p in source.iterdir()}
            with patch.object(reader.os, 'open', side_effect=fail_member):
                error = self.rejection(lambda: reader.read_report(source), 'REPORT_INPUT_FILE')
            self.assertIs(error.__cause__, original)
            self.assertEqual(len(descriptors), 1)
            with self.assertRaises(OSError):
                os.fstat(descriptors[0])
            self.assertEqual(before, {p.name: p.read_bytes() for p in source.iterdir()})

    def test_existing_reader_content_classifications_are_not_collapsed(self):
        reader, _ = self.modules()
        for mode, code in [('extra', 'REPORT_FILES'), ('large', 'REPORT_SIZE'), ('directory', 'REPORT_INPUT_FILE')]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                source = write_bundle(Path(tmp) / 'source')
                if mode == 'extra':
                    (source / 'extra').write_bytes(b'extra')
                elif mode == 'large':
                    (source / 'INPUT.json').write_bytes(b'x' * (reader.CAPS['INPUT.json'] + 1))
                else:
                    (source / 'INPUT.json').unlink()
                    (source / 'INPUT.json').mkdir()
                self.rejection(lambda source=source: reader.read_report(source), code)

    def test_reader_programmer_interrupt_and_later_decode_errors_propagate(self):
        reader, _ = self.modules()
        for original in [TypeError('programmer'), KeyboardInterrupt(), SystemExit(7)]:
            with patch.object(reader.os, 'open', side_effect=original), self.assertRaises(type(original)) as caught:
                reader.read_report(Path('unused'))
            self.assertIs(caught.exception, original)
        with tempfile.TemporaryDirectory() as tmp:
            source = write_bundle(Path(tmp) / 'source')
            for original in [ValueError('decode-defect'), reader.ReportError('REPORT_SCHEMA')]:
                with patch.object(reader, 'decode_report', side_effect=original), self.assertRaises(type(original)) as caught:
                    reader.read_report(source)
                self.assertIs(caught.exception, original)

    def test_generic_reader_keeps_unicode_and_surrogateescape_paths(self):
        reader, _ = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = reader.read_report(write_bundle(root / 'normal'))
            for name in ['저장된-입력', 'linux-\udcff']:
                with self.subTest(name=repr(name)):
                    source = write_bundle(root / name)
                    before = {p.name: p.read_bytes() for p in source.iterdir()}
                    self.assertEqual(reader.read_report(source), reference)
                    self.assertEqual(before, {p.name: p.read_bytes() for p in source.iterdir()})

    def test_frontend_invalid_outputs_reject_before_read_or_render(self):
        _, runner = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for text in ['invalid\0output', 'invalid\ud800output', 'linux-\udcff']:
                with (self.subTest(path=repr(text)),
                      patch.object(runner, 'read_report', side_effect=AssertionError('INPUT_READ')),
                      patch.object(runner, '_render_html', side_effect=AssertionError('RENDER'))):
                    error = self.rejection(lambda text=text: runner.run_report(root / 'missing', root / text), 'REPORT_OUTPUT_PATH')
                    self.assertIsInstance(error.__cause__, ValueError)
            self.assertEqual(list(root.iterdir()), [])

    def test_frontend_invalid_inputs_reject_before_read_or_render(self):
        _, runner = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for text in ['invalid\0input', 'invalid\ud800input', 'linux-\udcff']:
                with (self.subTest(path=repr(text)),
                      patch.object(runner, 'read_report', side_effect=AssertionError('INPUT_READ')),
                      patch.object(runner, '_render_html', side_effect=AssertionError('RENDER'))):
                    error = self.rejection(lambda text=text: runner.run_report(root / text, root / 'out'), 'REPORT_INPUT_FILE')
                    self.assertIsInstance(error.__cause__, ValueError)
            self.assertEqual(list(root.iterdir()), [])

    def test_existing_frontend_guard_priority_and_saved_classified_cause(self):
        reader, runner = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'source')
            existing = root / 'linux-\udcff'
            existing.write_bytes(b'keep')
            link = root / 'broken'
            link.symlink_to('missing')
            for output, code in [(existing, 'REPORT_OUTPUT_EXISTS'), (link, 'REPORT_OUTPUT_EXISTS'),
                                 (root / 'missing/out', 'REPORT_OUTPUT_PARENT'), (source / 'nested', 'REPORT_OUTPUT_LOCATION')]:
                with patch.object(runner, 'read_report', side_effect=AssertionError('INPUT_READ')):
                    input_path = source if output == source / 'nested' else root / 'invalid\0input'
                    self.rejection(lambda input_path=input_path, output=output: runner.run_report(input_path, output), code)
            self.assertEqual(existing.read_bytes(), b'keep')
            self.assertEqual(link.readlink(), Path('missing'))
            original_cause = OSError('saved-original')
            for method in ['exists', 'resolve']:
                classified = reader.ReportError('REPORT_OUTPUT_PARENT')
                classified.__cause__ = original_cause
                with patch.object(Path, method, side_effect=classified), self.assertRaises(reader.ReportError) as caught:
                    runner.run_report(source, root / 'out')
                self.assertIs(caught.exception, classified)
                self.assertEqual(caught.exception.code, 'REPORT_OUTPUT_PARENT')
                self.assertIs(caught.exception.__cause__, original_cause)

    def test_frontend_metadata_and_resolution_faults_are_position_scoped(self):
        _, runner = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root, source, output = Path(tmp), Path(tmp) / 'source', Path(tmp) / 'out'
            for method, target, code in [('exists', output, 'REPORT_OUTPUT_PATH'), ('is_symlink', output, 'REPORT_OUTPUT_PATH'),
                                         ('is_dir', root, 'REPORT_OUTPUT_PATH'), ('resolve', source, 'REPORT_INPUT_FILE'),
                                         ('resolve', output, 'REPORT_OUTPUT_PATH')]:
                actual = getattr(Path, method)
                failures = [PermissionError('private-path'), ValueError('private-value')]
                if method == 'resolve':
                    failures.append(RuntimeError('symlink-resolution'))
                for original in failures:
                    def fail(path, *args, target=target, actual=actual, original=original, **kwargs):
                        if path == target:
                            raise original
                        return actual(path, *args, **kwargs)

                    with (self.subTest(method=method, target=target.name, kind=type(original).__name__),
                          patch.object(Path, method, autospec=True, side_effect=fail),
                          patch.object(runner, 'read_report', side_effect=AssertionError('INPUT_READ'))):
                        error = self.rejection(lambda source=source, output=output: runner.run_report(source, output), code)
                        self.assertIs(error.__cause__, original)
            self.assertEqual(list(root.iterdir()), [])

    def test_frontend_unrelated_and_later_errors_are_not_reclassified(self):
        reader, runner = self.modules()
        for original in [TypeError('programmer'), KeyboardInterrupt(), SystemExit(7)]:
            with patch.object(Path, 'exists', side_effect=original), self.assertRaises(type(original)) as caught:
                runner.run_report(Path('unused'), Path('unused-out'))
            self.assertIs(caught.exception, original)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'source')
            for stage in ['read_report', '_render_html']:
                for original in [ValueError('later-defect'), reader.ReportError('REPORT_SCHEMA')]:
                    with patch.object(runner, stage, side_effect=original), self.assertRaises(type(original)) as caught:
                        runner.run_report(source, root / 'out')
                    self.assertIs(caught.exception, original)
                    self.assertFalse((root / 'out').exists())

    def test_actual_cli_invalid_paths_are_bounded_and_model_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / 'source')
            surrogate = write_bundle(root / 'linux-\udcff')
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            cases = [(source, root / text, 'REPORT_OUTPUT_PATH') for text in ['invalid\0out', 'invalid\ud800out', 'out-\udcff']]
            cases += [(root / text, root / 'out', 'REPORT_INPUT_FILE') for text in ['invalid\0in', 'invalid\ud800in', surrogate.name]]
            for input_path, output, code in cases:
                with self.subTest(input=repr(str(input_path)), output=repr(str(output))):
                    # NUL cannot travel in OS argv: actual CLI.main receives it inside a fresh child.
                    process = self.isolated_cli(['--input', str(input_path), '--output', str(output)])
                    self.assertEqual(process.returncode, 2, process.stderr.decode(errors='replace'))
                    self.assertEqual(process.stdout, b'')
                    self.assertEqual(process.stderr, ('REJECTED: ' + code + '\n').encode())
                    self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()})
                    self.assertEqual({p.name for p in root.iterdir()}, {source.name, surrogate.name})

    @unittest.skipIf(os.geteuid() == 0, 'Actual mode000 requires an unprivileged actor')
    def test_actual_mode000_frontend_api_and_os_argv_cli(self):
        reader, runner = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            denied = root / 'denied'
            denied.mkdir()
            denied.chmod(0)
            try:
                for source, output, code in [(root / 'missing', denied / 'out', 'REPORT_OUTPUT_PATH'),
                                             (denied / 'input', root / 'out', 'REPORT_INPUT_FILE')]:
                    # Non-strict Path.resolve may defer input EACCES to the bounded reader.
                    module, stage = (runner, 'read_report') if code == 'REPORT_OUTPUT_PATH' else (reader, 'decode_report')
                    with self.subTest(interface='API', code=code), patch.object(module, stage, side_effect=AssertionError('LATE_WORK')):
                        error = self.rejection(lambda source=source, output=output: runner.run_report(source, output), code)
                        self.assertIsInstance(error.__cause__, PermissionError)
                    with self.subTest(interface='CLI', code=code):
                        process = subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/scenario_report.py',
                                                  '--input', source, '--output', output], capture_output=True, timeout=20, check=False)
                        self.assertEqual(process.returncode, 2)
                        self.assertEqual(process.stdout, b'')
                        self.assertEqual(process.stderr, ('REJECTED: ' + code + '\n').encode())
            finally:
                denied.chmod(0o700)
            self.assertEqual({p.name for p in root.iterdir()}, {'denied'})
            self.assertEqual(list(denied.iterdir()), [])

    def test_unicode_cli_preserves_saved_values_portable_view_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, output = write_bundle(root / '입력'), root / '출력'
            before = {p.name: p.read_bytes() for p in source.iterdir()}
            process = self.isolated_cli(['--input', str(source), '--output', str(output)])
            self.assertEqual(process.returncode, 0, process.stderr.decode(errors='replace'))
            self.assertEqual(process.stderr, b'')
            view = json.loads((output / 'VIEW.json').read_bytes())
            self.assertEqual([row['final_command'] for row in view['rows']], [2, -2, 0, 2])
            self.assertEqual(view['renderer_model_executions'], 0)
            receipt = json.loads((output / 'RECEIPT.json').read_bytes())
            self.assertEqual(receipt['forbidden_modules_loaded'], [])
            self.assertEqual(receipt['input_directory'], str(source))
            self.assertEqual(receipt['output_directory'], str(output))
            manifest = dict(line.split('  ', 1)[::-1] for line in (output / 'SHA256SUMS.txt').read_text().splitlines())
            self.assertEqual(manifest, {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                        for p in output.iterdir() if p.name != 'SHA256SUMS.txt'})
            self.assertEqual(before, {p.name: p.read_bytes() for p in source.iterdir()})
