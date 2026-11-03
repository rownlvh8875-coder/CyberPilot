"""Only cache construction OS errors become bounded producer CLI rejections."""

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from v1_helpers import ROOT

REAL_TEMP = tempfile.TemporaryDirectory
CASES = [('scenario_batch.py', 'cyberlateral-r33-cache-', 'BATCH_IO', ['--input', 'missing.json']),
         ('scenario_workflow.py', 'cyberlateral-r40-cache-', 'WORKFLOW_IO', ['--input', 'missing.json']),
         ('scenario_explore.py', 'cyberlateral-r42-cache-', 'EXPLORATION_IO', ['--seed', '42', '--cases', '1', '--steps', '16']),
         ('scenario_campaign.py', 'cyberlateral-r43-cache-', 'CAMPAIGN_IO', ['--seed', '42', '--cases', '1', '--steps', '16'])]


def cli(name):
    spec = importlib.util.spec_from_file_location('_cache_probe_' + name[:-3], ROOT / 'tools' / name)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProducerCliCacheTests(unittest.TestCase):
    def invoke(self, module, arguments, output):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = module.main([*arguments, '--output', str(output)])
        return result, stdout.getvalue(), stderr.getvalue()

    def test_constructor_os_failures_keep_exact_codes_prefixes_and_process_state(self):
        for name, prefix, code, arguments in CASES:
            module = cli(name)
            for original in [PermissionError('private-denied-location'), FileNotFoundError('private-missing'), OSError('private-io')]:
                with self.subTest(tool=name, kind=type(original).__name__), REAL_TEMP() as tmp:
                    root = Path(tmp)
                    cache_before, paths_before, modules_before = sys.pycache_prefix, sys.path.copy(), set(sys.modules)
                    with patch.object(tempfile, 'TemporaryDirectory', side_effect=original) as factory:
                        try:
                            result = self.invoke(module, arguments, root / 'out')
                        except OSError:
                            self.fail('Cache constructor OS error must not escape the CLI')
                    self.assertEqual(result, (2, '', 'REJECTED: ' + code + '\n'))
                    factory.assert_called_once_with(prefix=prefix)
                    self.assertEqual(sys.pycache_prefix, cache_before)
                    self.assertEqual(sys.path, paths_before)
                    self.assertFalse(any(n.startswith('integration_tools.') for n in set(sys.modules) - modules_before))
                    self.assertEqual(list(root.iterdir()), [])

    @unittest.skipIf(os.geteuid() == 0, 'Actual mode000 requires an unprivileged actor')
    def test_actual_mode000_fresh_children_are_bounded_before_integration_imports(self):
        with REAL_TEMP() as tmp:
            root = Path(tmp)
            denied = root / 'denied'
            denied.mkdir()
            denied.chmod(0)
            try:
                for name, _, code, arguments in CASES:
                    program = ('import importlib.util,sys,tempfile\nfrom unittest.mock import patch\n'
                               'spec=importlib.util.spec_from_file_location("actual_cli",' + repr(str(ROOT / 'tools' / name)) + ')\n'
                               'cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)\n'
                               'before=sys.pycache_prefix;paths=list(sys.path)\n'
                               'with patch.object(tempfile,"gettempdir",return_value=' + repr(str(denied)) + '):\n'
                               ' status=cli.main(sys.argv[1:])\n'
                               'assert before==sys.pycache_prefix and paths==sys.path\n'
                               'assert not any(n.startswith("integration_tools.") or n in {"numpy","cyberlateral_dev","capnp","openpilot","cereal","opendbc"} for n in sys.modules)\n'
                               'raise SystemExit(status)\n')
                    with self.subTest(tool=name):
                        result = subprocess.run([sys.executable, '-I', '-B', '-c', program, *arguments,
                                                 '--output', str(root / 'out')], capture_output=True, timeout=20, check=False)
                        self.assertEqual((result.returncode, result.stdout, result.stderr),
                                         (2, b'', ('REJECTED: ' + code + '\n').encode()))
            finally:
                denied.chmod(0o700)
            self.assertEqual(list(denied.iterdir()), [])
            self.assertEqual(list(root.iterdir()), [denied])

    def test_non_os_constructor_defects_and_interrupts_keep_original_objects(self):
        for name, _, _, arguments in CASES:
            module = cli(name)
            for original in [ValueError('defect'), TypeError('defect'), RuntimeError('defect'), KeyboardInterrupt(), SystemExit(7)]:
                with self.subTest(tool=name, kind=type(original).__name__), REAL_TEMP() as tmp:
                    cache_before, paths_before = sys.pycache_prefix, sys.path.copy()
                    with patch.object(tempfile, 'TemporaryDirectory', side_effect=original), self.assertRaises(type(original)) as caught:
                        self.invoke(module, arguments, Path(tmp) / 'out')
                    self.assertIs(caught.exception, original)
                    self.assertEqual((sys.pycache_prefix, sys.path), (cache_before, paths_before))
                    self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_argparse_errors_still_precede_any_cache_construction(self):
        for name, _, _, _ in CASES:
            with self.subTest(tool=name):
                module = cli(name)
                cache_before, paths_before = sys.pycache_prefix, sys.path.copy()
                with (patch.object(tempfile, 'TemporaryDirectory', side_effect=AssertionError('CACHE')) as factory,
                      contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught):
                    module.main([])
                self.assertEqual(caught.exception.code, 2)
                factory.assert_not_called()
                self.assertEqual((sys.pycache_prefix, sys.path), (cache_before, paths_before))

    def test_manager_entry_os_error_is_not_mislabeled_as_constructor_failure(self):
        for name, _, _, arguments in CASES:
            original = PermissionError('enter-defect')

            @contextlib.contextmanager
            def enter_error(original=original):
                raise original
                yield  # pragma: no cover - make the deliberately failing entry a manager

            with self.subTest(tool=name), REAL_TEMP() as tmp:
                cache_before, paths_before = sys.pycache_prefix, sys.path.copy()
                with patch.object(tempfile, 'TemporaryDirectory', return_value=enter_error()), self.assertRaises(OSError) as caught:
                    self.invoke(cli(name), arguments, Path(tmp) / 'out')
                self.assertIs(caught.exception, original)
                self.assertEqual((sys.pycache_prefix, sys.path), (cache_before, paths_before))
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_late_manager_exit_error_keeps_existing_propagation_and_cache_restore(self):
        for name, prefix, _, arguments in CASES:
            original = OSError('existing-late-cleanup')

            @contextlib.contextmanager
            def exit_error(*args, original=original, **kwargs):
                with REAL_TEMP(*args, **kwargs) as scratch:
                    yield scratch
                raise original

            def factory(*args, expected_prefix=prefix, **kwargs):
                return exit_error(*args, **kwargs) if kwargs.get('prefix') == expected_prefix else REAL_TEMP(*args, **kwargs)

            with self.subTest(tool=name), REAL_TEMP() as tmp:
                root = Path(tmp)
                cache_before, paths_before = sys.pycache_prefix, sys.path.copy()
                try:
                    with patch.object(tempfile, 'TemporaryDirectory', side_effect=factory), self.assertRaises(OSError) as caught:
                        self.invoke(cli(name), arguments, root / 'bad\0out')
                    self.assertIs(caught.exception, original)
                    self.assertEqual(sys.pycache_prefix, cache_before)
                    self.assertEqual(list(root.iterdir()), [])
                finally:
                    sys.path[:] = paths_before

    def test_later_primary_diagnostic_os_error_is_not_constructor_io(self):
        for name, _, _, arguments in CASES:
            original = OSError('existing-primary-sink-error')
            module = cli(name)

            def fail_print(*args, original=original, **kwargs):
                raise original

            with self.subTest(tool=name), REAL_TEMP() as tmp:
                cache_before, paths_before = sys.pycache_prefix, sys.path.copy()
                try:
                    with patch.dict(module.main.__globals__, {'print': fail_print}):
                        with self.assertRaises(OSError) as caught:
                            self.invoke(module, arguments, Path(tmp) / 'bad\0out')
                    self.assertIs(caught.exception, original)
                    self.assertEqual(sys.pycache_prefix, cache_before)
                    self.assertEqual(list(Path(tmp).iterdir()), [])
                finally:
                    sys.path[:] = paths_before

    def test_constructor_rejection_does_not_hide_its_broken_stderr_sink(self):
        class BrokenSink(io.StringIO):
            def write(self, text):
                raise sink_error

        for name, _, _, arguments in CASES:
            factory_error, sink_error = PermissionError('factory'), OSError('diagnostic-sink')
            with self.subTest(tool=name), REAL_TEMP() as tmp:
                module = cli(name)
                with (patch.object(tempfile, 'TemporaryDirectory', side_effect=factory_error),
                      contextlib.redirect_stderr(BrokenSink()), self.assertRaises(OSError) as caught):
                    module.main([*arguments, '--output', str(Path(tmp) / 'out')])
                self.assertIs(caught.exception, sink_error)
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_cache_creation_still_precedes_domain_generation_parameter_validation(self):
        for name, prefix, code, arguments in CASES[2:]:
            arguments = [*arguments[:-1], '1']  # Parsed int, but below the generator's source minimum16.
            with self.subTest(tool=name), REAL_TEMP() as tmp:
                with patch.object(tempfile, 'TemporaryDirectory', side_effect=PermissionError('cache')) as factory:
                    try:
                        result = self.invoke(cli(name), arguments, Path(tmp) / 'out')
                    except OSError:
                        self.fail('Cache construction precedes domain parameter validation')
                self.assertEqual(result, (2, '', 'REJECTED: ' + code + '\n'))
                factory.assert_called_once_with(prefix=prefix)
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_real_cache_still_reaches_original_path_rejection_and_restores_prefix(self):
        for name, prefix, code, arguments in CASES:
            expected = 'BATCH_IO' if name == 'scenario_workflow.py' else code
            with self.subTest(tool=name), REAL_TEMP() as tmp:
                root = Path(tmp)
                cache_before, paths_before = sys.pycache_prefix, sys.path.copy()
                try:
                    with patch.object(tempfile, 'TemporaryDirectory', wraps=REAL_TEMP) as factory:
                        result = self.invoke(cli(name), arguments, root / 'bad\0out')
                    self.assertEqual(result, (2, '', 'REJECTED: ' + expected + '\n'))
                    self.assertIn(call(prefix=prefix), factory.call_args_list)
                    self.assertEqual(sys.pycache_prefix, cache_before)
                    self.assertEqual(list(root.iterdir()), [])
                finally:
                    sys.path[:] = paths_before
