"""Verifier behavior: real files/CLI and independent expected ledger/manifest values."""

import fnmatch
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

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

    def test_real_single_test_cannot_forge_baseline_with_printed_footer(self):
        c = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'test_one.py').write_text(
                'import unittest\nclass One(unittest.TestCase):\n'
                ' def test_one(self): print("Ran 70 tests in 1.000s\\n\\nOK")\n')
            result = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', root],
                                    capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0)
            self.assertIn(b'Ran 1 test in ', result.stderr)
            with self.assertRaisesRegex(ValueError, 'CI_TEST_LEDGER'):
                c.validate_ledger((result.stdout + result.stderr).decode())

    def test_additional_malformed_or_skipped_summary_cannot_be_hidden(self):
        c = self.module()
        for text in ['Ran 1 tests in broken\nRan 70 tests in 1.0s\nOK\n',
                     'Ran 70 tests in 1.0s\nOK (skipped=1)\nOK\n',
                     'Ran 70 tests in 1.0s\nOK\nOK\n']:
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, 'CI_TEST_LEDGER'):
                c.validate_ledger(text)

    def test_directory_symlinks_cannot_hide_executed_test_sources(self):
        c = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            root, outside = parent / 'owned', parent / 'outside'
            root.mkdir()
            outside.mkdir()
            (root / 'runner.py').write_bytes(b'pass\n')
            (outside / 'test_external.py').write_bytes(b'raise AssertionError("not owned")\n')
            (root / 'tests').symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'SOURCE_SYMLINK'):
                c.compile_owned(root)

    def test_short_command_timeout_preserves_partial_diagnostic_log(self):
        c = self.module()
        self.assertTrue(hasattr(c, 'run_check'), 'bounded command runner required')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / 'timeout.log'
            command = [sys.executable, '-B', '-c', 'import time; print("started", flush=True); time.sleep(30)']
            with self.assertRaisesRegex(ValueError, '^COMMAND_TIMEOUT$'):
                c.run_check(command, log, root, timeout=0.5)
            self.assertEqual(log.read_bytes(), b'started\n')

    def test_excess_command_output_is_bounded_and_rejected(self):
        c = self.module()
        self.assertTrue(hasattr(c, 'run_check'), 'bounded command runner required')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / 'overflow.log'
            command = [sys.executable, '-B', '-c', f'import sys; sys.stdout.write("x" * {c.MAX_LOG_BYTES + 1})']
            with self.assertRaisesRegex(ValueError, '^COMMAND_LOG_LIMIT$'):
                c.run_check(command, log, root, timeout=5)
            self.assertEqual(log.read_bytes(), b'x' * c.MAX_LOG_BYTES)

    def test_overall_budget_failure_preserves_failure_not_success(self):
        c = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'new'
            args = SimpleNamespace(output=output, hf_python=Path(sys.executable))
            with mock.patch.object(c, 'TOTAL_TIMEOUT_SECONDS', 0, create=True):
                with self.assertRaisesRegex(ValueError, '^COMMAND_TIMEOUT$'):
                    c.execute(args)
            failure = json.loads((output / 'FAILURE.json').read_bytes())
            self.assertEqual((failure['stage'], failure['code']), ('PREFLIGHT', 'COMMAND_TIMEOUT'))
            self.assertFalse((output / 'SUMMARY.json').exists())

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


class WorkflowContractTests(unittest.TestCase):
    def configuration(self):
        path = TOOLS.parents[1] / '.github/workflows/cyberlateral-cloud.yaml'
        self.assertTrue(path.is_file(), 'automatic cloud workflow missing')
        yaml = importlib.import_module('yaml')
        return yaml.load(path.read_text(), Loader=yaml.BaseLoader)

    def test_changed_cloud_and_app_paths_trigger_but_unrelated_files_do_not(self):
        config = self.configuration()
        events = config['on']
        self.assertIn('workflow_dispatch', events)
        for event in ('push', 'pull_request'):
            policy = events[event]
            for path, wanted in [('tools/cyberlateral_cloud/ci_verify.py', True),
                                 ('tools/cyberlateral_cloud/tests/test_cloud_ci.py', True),
                                 ('tools/cyberlateral_cloud/hf-requirements.lock', True),
                                 ('tools/cyberlateral_dev/project/model.py', True),
                                 ('.github/workflows/cyberlateral-cloud.yaml', True),
                                 ('.github/workflows/cyberlateral-dev.yaml', True),
                                 ('README.md', True), ('openpilot/car.py', False)]:
                with self.subTest(event=event, path=path):
                    actual = 'main' in policy['branches'] and any(fnmatch.fnmatchcase(path, p) for p in policy['paths'])
                    self.assertEqual(actual, wanted)
            self.assertNotIn('ci/cloud-verification', policy['branches'])

    def test_read_only_job_has_no_hf_credential_or_secret_binding(self):
        config = self.configuration()
        self.assertEqual(config['permissions'], {'contents': 'read'})
        job = config['jobs']['verify']
        self.assertEqual(job.get('permissions', config['permissions']), {'contents': 'read'})
        self.assertEqual(job['runs-on'], 'ubuntu-24.04')
        self.assertEqual(job['env']['HF_HUB_OFFLINE'], '1')
        self.assertNotIn('HF_TOKEN', job['env'])
        self.assertNotIn('secrets', config)
        self.assertNotIn('secrets', job)
        self.assertIsNone(re.search(r'\$\{\{\s*secrets\.', json.dumps(config)))
        self.assertEqual(job.get('continue-on-error', 'false'), 'false')

    def test_pinned_bootstrap_and_separate_temp_environments(self):
        job = self.configuration()['jobs']['verify']
        actions = {s['uses'].split('@')[0]: s for s in job['steps'] if 'uses' in s}
        self.assertEqual(set(actions), {'actions/checkout', 'actions/setup-python', 'astral-sh/setup-uv', 'actions/upload-artifact'})
        for action in actions.values():
            self.assertRegex(action['uses'].split('@')[1], r'^[0-9a-f]{40}$')
        self.assertEqual(actions['actions/checkout']['with'],
                         {'submodules': 'false', 'lfs': 'false', 'persist-credentials': 'false'})
        self.assertEqual(actions['actions/setup-python']['with']['python-version'], '3.12.13')
        self.assertEqual(actions['astral-sh/setup-uv']['with']['version'], '0.12.23')
        self.assertEqual(next(s for s in job['steps'] if s.get('id') == 'dependencies')['timeout-minutes'], '2')
        self.assertEqual(next(s for s in job['steps'] if s.get('id') == 'verify')['timeout-minutes'], '5')
        self.assertEqual(job['env']['UV_PYTHON_DOWNLOADS'], 'never')
        self.assertNotEqual(job['env']['UV_PROJECT_ENVIRONMENT'], job['env']['CLOUD_HF_ENV'])
        for name in ('UV_PROJECT_ENVIRONMENT', 'CLOUD_HF_ENV', 'CLOUD_VERIFY_OUTPUT'):
            self.assertTrue(job['env'][name].startswith('${{ runner.temp }}/'))

    def test_failure_artifact_is_always_uploaded_without_masking_verify(self):
        steps = self.configuration()['jobs']['verify']['steps']
        upload = next(s for s in steps if s.get('uses', '').startswith('actions/upload-artifact@'))
        self.assertEqual(upload['if'], 'always()')
        self.assertEqual(upload['with']['name'], 'cyberlateral-cloud-verification')
        self.assertEqual(upload['with']['path'], '${{ env.CLOUD_VERIFY_OUTPUT }}')
        self.assertEqual(upload['with']['if-no-files-found'], 'error')
        verify = next(s for s in steps if s.get('id') == 'verify')
        self.assertEqual(verify.get('continue-on-error', 'false'), 'false')
        self.assertNotIn('if', verify)

    def run_verification_step(self, root, output):
        steps = self.configuration()['jobs']['verify']['steps']
        step = next(s for s in steps if s.get('id') == 'verify')
        env = os.environ.copy()
        env.update(UV_PROJECT_ENVIRONMENT=sys.prefix, CLOUD_HF_ENV=str(root / 'missing-sdk'),
                   CLOUD_VERIFY_OUTPUT=str(output), HF_HUB_OFFLINE='1')
        return subprocess.run(['bash', '-e', '-c', step['run']], cwd=TOOLS.parents[1],
                              env=env, capture_output=True, timeout=30)

    def test_actual_ci_step_refuses_existing_output_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / 'existing'
            output.mkdir()
            (output / 'keep').write_bytes(b'preserved')
            result = self.run_verification_step(root, output)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['code'], 'OUTPUT_EXISTS')
            self.assertEqual([p.name for p in output.iterdir()], ['keep'])

    def test_actual_ci_step_preserves_missing_sdk_failure_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / 'new'
            result = self.run_verification_step(root, output)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['code'], 'HF_INTERPRETER_REQUIRED')
            self.assertEqual(json.loads((output / 'FAILURE.json').read_bytes())['stage'], 'PREFLIGHT')
            self.assertEqual([p.name for p in output.iterdir()], ['FAILURE.json'])


if __name__ == '__main__':
    unittest.main()
