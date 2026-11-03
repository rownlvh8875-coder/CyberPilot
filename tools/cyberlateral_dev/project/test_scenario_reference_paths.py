"""Reference preflight bounds path failures, not later arithmetic/reader defects."""

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

from scenario_compare_fixture import write_batch
from scenario_report_fixture import write_bundle
from v1_helpers import ROOT


class ScenarioReferencePathTests(unittest.TestCase):
    def modules(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return (importlib.import_module('integration_tools.scenario_reference_run'),
                importlib.import_module('integration_tools.scenario_batch_reference_run'))

    def frontends(self):
        single, batch = self.modules()
        return [('single', single, single.check_saved, single.ReferenceCheckError, '_files', 'REFERENCE_IO'),
                ('batch', batch, batch.check_batch, batch.BatchReferenceError, '_owned_files', 'BATCH_REFERENCE_IO')]

    def rejection(self, call, kind, code):
        try:
            call()
        except kind as error:
            self.assertEqual(error.code, code)
            return error
        except Exception as error:
            self.fail(f'Unbounded or wrong preflight exception: {type(error).__name__}')
        self.fail('Invalid reference path accepted')

    def isolated_cli(self, alias, arguments):
        tool = 'scenario_reference_check.py' if alias == 'single' else 'scenario_batch_reference_check.py'
        code = ('import importlib.util,sys\n'
                'from unittest.mock import patch\n'
                'sys.path.insert(0,' + repr(str(ROOT)) + ')\n'
                'blocked={"cyberlateral_dev","numpy","capnp","openpilot","opendbc","cereal","integration_tools.verify"}\n'
                'class Barrier:\n'
                ' def find_spec(self,fullname,path=None,target=None):\n'
                '  if fullname in blocked or fullname.split(".")[0] in blocked: raise AssertionError("MODEL_IMPORT:"+fullname)\n'
                'sys.meta_path.insert(0,Barrier())\n'
                'from integration_tools import scenario_reference_run as single,scenario_batch_reference_run as batch\n'
                'spec=importlib.util.spec_from_file_location("actual_cli",' + repr(str(ROOT / 'tools' / tool)) + ')\n'
                'cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)\n'
                'with patch.object(single,"_files",side_effect=AssertionError("INPUT_READ")),patch.object(batch,"_owned_files",side_effect=AssertionError("BATCH_READ")),patch.object(single,"_launch",side_effect=AssertionError("WORKER")):\n'
                ' status=cli.main(' + repr(arguments) + ')\n'
                'assert not any(n in blocked or n.split(".")[0] in blocked for n in sys.modules)\n'
                'raise SystemExit(status)\n')
        return subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, timeout=20, check=False)

    def test_single_invalid_paths_are_bounded_before_acquisition_or_worker(self):
        single, _ = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for input_path, output in [(root / 'bad\0input', root / 'out'), (root / 'none', root / 'bad\0out'),
                                       (root / 'bad\ud800input', root / 'out'), (root / 'none', root / 'bad\ud800out')]:
                with (self.subTest(input=repr(str(input_path)), output=repr(str(output))),
                      patch.object(single, '_files', side_effect=AssertionError('INPUT_READ')),
                      patch.object(single, '_launch', side_effect=AssertionError('WORKER'))):
                    error = self.rejection(lambda input_path=input_path, output=output: single.check_saved(input_path, output),
                                           single.ReferenceCheckError, 'REFERENCE_IO')
                    self.assertIsInstance(error.__cause__, ValueError)
            self.assertEqual(list(root.iterdir()), [])

    def test_batch_nul_paths_are_bounded_before_acquisition_or_worker(self):
        single, batch = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for input_path, output in [(root / 'bad\0input', root / 'out'), (root / 'none', root / 'bad\0out')]:
                with (self.subTest(input=repr(str(input_path)), output=repr(str(output))),
                      patch.object(batch, '_owned_files', side_effect=AssertionError('INPUT_READ')),
                      patch.object(single, '_launch', side_effect=AssertionError('WORKER'))):
                    error = self.rejection(lambda input_path=input_path, output=output: batch.check_batch(input_path, output),
                                           batch.BatchReferenceError, 'BATCH_REFERENCE_IO')
                    self.assertIsInstance(error.__cause__, ValueError)
            self.assertEqual(list(root.iterdir()), [])

    def test_output_guard_priority_and_existing_input_location_codes(self):
        for alias, module, check, kind, reader, _ in self.frontends():
            prefix = 'REFERENCE_' if alias == 'single' else 'BATCH_REFERENCE_'
            with self.subTest(frontend=alias), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                existing, source, link = root / 'existing', root / 'source', root / 'broken'
                existing.write_bytes(b'keep')
                source.mkdir()
                link.symlink_to('missing')
                cases = [(root / 'bad\0input', existing, 'OUTPUT_EXISTS'), (root / 'bad\0input', link, 'OUTPUT_EXISTS'),
                         (root / 'bad\0input', root / 'missing/out', 'OUTPUT_PARENT'),
                         (root / 'bad\0input', ROOT / 'new-r54-output', 'OUTPUT_LOCATION'),
                         (source, source / 'nested', 'OUTPUT_LOCATION')]
                for input_path, output, suffix in cases:
                    with self.subTest(code=prefix + suffix), patch.object(module, reader, side_effect=AssertionError('INPUT_READ')):
                        self.rejection(lambda input_path=input_path, output=output, check=check: check(input_path, output), kind, prefix + suffix)
                self.assertEqual(existing.read_bytes(), b'keep')
                self.assertEqual(link.readlink(), Path('missing'))
                self.assertEqual(list(source.iterdir()), [])

    def test_existing_loop_runtime_and_batch_encoding_codes_keep_priority(self):
        single, batch = self.modules()
        report = importlib.import_module('integration_tools.scenario_report_data')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            loop = root / 'loop'
            loop.symlink_to('loop')
            with patch.object(single, '_files', side_effect=AssertionError('INPUT_READ')):
                error = self.rejection(lambda: single.check_saved(loop, root / 'out'), report.ReportError, 'REPORT_INPUT_FILE')
                self.assertIsInstance(error.__cause__, RuntimeError)
            with patch.object(batch, '_owned_files', side_effect=AssertionError('INPUT_READ')):
                error = self.rejection(lambda: batch.check_batch(loop, root / 'out'), batch.BatchReferenceError,
                                       'BATCH_REFERENCE_INPUT_FILE')
                self.assertIsInstance(error.__cause__, RuntimeError)
            for _, module, check, kind, reader, _ in self.frontends():
                with patch.object(module.platform, 'python_version', return_value='3.12.14'), patch.object(module, reader, side_effect=AssertionError('INPUT_READ')):
                    prefix = 'REFERENCE_' if module is single else 'BATCH_REFERENCE_'
                    self.rejection(lambda check=check: check(root / 'source', root / 'out'), kind, prefix + 'RUNTIME')
            for text in ['bad\ud800', 'linux-\udcff']:
                for source, output in [(root / text, root / 'out'), (root / 'source', root / text)]:
                    with patch.object(batch, '_owned_files', side_effect=AssertionError('INPUT_READ')):
                        error = self.rejection(lambda source=source, output=output: batch.check_batch(source, output),
                                               batch.BatchReferenceError, 'BATCH_REFERENCE_PATH_ENCODING')
                        self.assertIsInstance(error.__cause__, UnicodeEncodeError)

    def test_classified_objects_and_independently_saved_causes_are_preserved(self):
        single, _ = self.modules()
        report = importlib.import_module('integration_tools.scenario_report_data')
        for alias, module, check, kind, reader, _ in self.frontends():
            kinds = [kind, report.ReportError] if module is single else [kind]
            for error_kind in kinds:
                original_cause = OSError('original-cause')
                classified = error_kind('SAVED_CLASSIFIED_CODE')
                classified.__cause__ = original_cause
                with (self.subTest(frontend=alias, kind=error_kind.__name__),
                      patch.object(Path, 'exists', side_effect=classified),
                      patch.object(module, reader, side_effect=AssertionError('INPUT_READ')),
                      self.assertRaises(error_kind) as caught):
                    check(Path('unused'), Path('unused-output'))
                self.assertIs(caught.exception, classified)
                self.assertEqual(caught.exception.code, 'SAVED_CLASSIFIED_CODE')
                self.assertIs(caught.exception.__cause__, original_cause)

    def test_unclassified_metadata_failures_are_chained_to_existing_io_code(self):
        for alias, module, check, kind, reader, code in self.frontends():
            with self.subTest(frontend=alias), tempfile.TemporaryDirectory() as tmp:
                root, output = Path(tmp), Path(tmp) / 'out'
                for method, target in [('exists', output), ('is_symlink', output), ('is_dir', root)]:
                    actual = getattr(Path, method)
                    for original in [PermissionError('private-metadata'), ValueError('private-value')]:
                        def fail(path, *args, target=target, actual=actual, original=original, **kwargs):
                            if path == target:
                                raise original
                            return actual(path, *args, **kwargs)

                        with (self.subTest(method=method, kind=type(original).__name__),
                              patch.object(Path, method, autospec=True, side_effect=fail),
                              patch.object(module, reader, side_effect=AssertionError('INPUT_READ'))):
                            error = self.rejection(lambda check=check, root=root, output=output: check(root / 'missing', output), kind, code)
                            self.assertIs(error.__cause__, original)
                self.assertEqual(list(root.iterdir()), [])

    def test_resolution_preserves_existing_codes_or_chains_unclassified_values(self):
        single, _ = self.modules()
        report = importlib.import_module('integration_tools.scenario_report_data')
        for alias, module, check, kind, reader, code in self.frontends():
            with self.subTest(frontend=alias), tempfile.TemporaryDirectory() as tmp:
                source, output = Path(tmp) / 'source', Path(tmp) / 'out'
                actual = Path.resolve
                for target in [source, output]:
                    for original in [PermissionError('private-path'), RuntimeError('resolution-loop'), ValueError('private-value')]:
                        def fail(path, *args, target=target, original=original, actual=actual, **kwargs):
                            if path == target:
                                raise original
                            return actual(path, *args, **kwargs)

                        expected_kind, expected_code = kind, code
                        if not isinstance(original, ValueError):
                            prefix = 'REFERENCE_' if module is single else 'BATCH_REFERENCE_'
                            expected_code = prefix + 'OUTPUT_LOCATION'
                            if target == source:
                                expected_kind = report.ReportError if module is single else kind
                                expected_code = 'REPORT_INPUT_FILE' if module is single else 'BATCH_REFERENCE_INPUT_FILE'
                        with (self.subTest(target=target.name, kind=type(original).__name__),
                              patch.object(Path, 'resolve', autospec=True, side_effect=fail),
                              patch.object(module, reader, side_effect=AssertionError('INPUT_READ'))):
                            error = self.rejection(lambda check=check, source=source, output=output: check(source, output), expected_kind, expected_code)
                            self.assertIs(error.__cause__, original)

    def test_programmer_errors_interrupts_and_later_reader_identity_faults_propagate(self):
        for alias, module, check, _, reader, _ in self.frontends():
            for original in [TypeError('programmer'), RuntimeError('metadata-defect'), KeyboardInterrupt(), SystemExit(7)]:
                with patch.object(Path, 'exists', side_effect=original), self.assertRaises(type(original)) as caught:
                    check(Path('unused'), Path('unused-out'))
                self.assertIs(caught.exception, original)
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = write_bundle(root / 'source') if alias == 'single' else write_batch(root / 'source')
                before = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()}
                stages = [reader, '_identity', '_launch'] if alias == 'single' else [reader, '_source_identity']
                for stage in stages:
                    original = ValueError('later-' + stage)
                    with patch.object(module, stage, side_effect=original), self.assertRaises(ValueError) as caught:
                        check(source, root / 'out')
                    self.assertIs(caught.exception, original)
                    self.assertFalse((root / 'out').exists())
                    self.assertEqual(before, {str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()})

    def test_fresh_actual_cli_nul_paths_are_bounded_and_worker_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for alias, _, _, _, _, code in self.frontends():
                for source, output in [(root / 'bad\0input', root / 'out'), (root / 'none', root / 'bad\0output')]:
                    with self.subTest(frontend=alias, input=repr(str(source)), output=repr(str(output))):
                        # The OS cannot carry NUL argv; actual CLI.main receives it inside the child.
                        result = self.isolated_cli(alias, ['--input', str(source), '--output', str(output)])
                        self.assertEqual(result.returncode, 2, result.stderr.decode(errors='replace'))
                        self.assertEqual(result.stdout, b'')
                        self.assertEqual(result.stderr, ('REJECTED: ' + code + '\n').encode())
                        self.assertEqual(list(root.iterdir()), [])

    @unittest.skipIf(os.geteuid() == 0, 'Real mode000 requires unprivileged actor')
    def test_actual_permission_output_api_and_os_argv_cli_are_bounded(self):
        for alias, module, check, kind, reader, code in self.frontends():
            with self.subTest(frontend=alias), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                denied = root / 'denied'
                denied.mkdir()
                denied.chmod(0)
                try:
                    with patch.object(module, reader, side_effect=AssertionError('INPUT_READ')):
                        error = self.rejection(lambda check=check, root=root, denied=denied: check(root / 'missing', denied / 'out'), kind, code)
                        self.assertIsInstance(error.__cause__, PermissionError)
                    tool = 'scenario_reference_check.py' if alias == 'single' else 'scenario_batch_reference_check.py'
                    result = subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools' / tool,
                                             '--input', root / 'missing', '--output', denied / 'out'],
                                            capture_output=True, timeout=20, check=False)
                    self.assertEqual((result.returncode, result.stdout, result.stderr), (2, b'', ('REJECTED: ' + code + '\n').encode()))
                finally:
                    denied.chmod(0o700)
                self.assertEqual(list(denied.iterdir()), [])
                self.assertEqual({p.name for p in root.iterdir()}, {'denied'})

    def test_single_surrogateescape_paths_and_unicode_keep_path_free_results(self):
        single, _ = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_bundle(root / '입력-\udcff')
            before = {p.name: p.read_bytes() for p in source.iterdir()}
            outputs = [root / '출력', root / 'output-\udcff']
            records = [single.check_saved(source, output) for output in outputs]
            self.assertEqual(records[0], records[1])
            self.assertEqual(records[0]['status'], 'MATCH')
            self.assertEqual(records[0]['reference_steps'], 4)
            self.assertEqual(records[0]['new_model_executions'], 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in source.iterdir()})
            for name in ['REFERENCE_CHECK.json', 'SHA256SUMS.txt']:
                self.assertEqual((outputs[0] / name).read_bytes(), (outputs[1] / name).read_bytes())

    def test_batch_unicode_valid_context_preserves_closed_gates_and_manifest(self):
        _, batch = self.modules()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = write_batch(root / '입력')
            before = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()}
            output = root / '출력'
            result = batch.check_batch(source, output)
            self.assertEqual(result['status'], 'MATCH')
            self.assertEqual(result['reference_steps'], 5)
            self.assertEqual(result['new_model_executions'], 0)
            self.assertEqual(result['gates']['R_BUDGET'], 'UNRESOLVED')
            self.assertEqual(result['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
            self.assertTrue(all(result['gates'][name] is None for name in ['actual_r', 'T2', 'vehicle_scale']))
            self.assertEqual(json.loads((output / 'BATCH_REFERENCE_CHECK.json').read_bytes()), result)
            for manifest in output.rglob('SHA256SUMS.txt'):
                for line in manifest.read_text().splitlines():
                    digest, name = line.split('  ', 1)
                    self.assertEqual(hashlib.sha256((manifest.parent / name).read_bytes()).hexdigest(), digest)
            root_members = {line.split('  ', 1)[1] for line in (output / 'SHA256SUMS.txt').read_text().splitlines()}
            self.assertEqual(root_members, {p.relative_to(output).as_posix() for p in output.rglob('*')
                                            if p.is_file() and p != output / 'SHA256SUMS.txt'})
            self.assertEqual(before, {str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()})
