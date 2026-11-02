"""Gate rejection and real R41 portable selection, not source-text assertions."""

import hashlib
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
COMPONENT = TOOLS.parent / 'cyberlateral_dev'
sys.path.insert(0, str(TOOLS))


class GateTests(unittest.TestCase):
    def module(self):
        self.assertTrue((TOOLS / 'cloud_run.py').is_file(), 'pipeline implementation missing')
        return importlib.import_module('cloud_run')

    def summary(self):
        return {'tests': 128, 'own_python_compile_count': 3,
                'status': 'F70UGZ_R18_FIXED_AUDIT_BUNDLE_REFERENCE_PASS',
                'wheel': {'sha256': 'a' * 64, 'byte_identical': True},
                'source_gates': {'R_BUDGET': 'UNRESOLVED', 'STATIC_EVIDENCE_GATE': 'FAIL',
                                 'actual_r': None, 'actual_T2': None, 'actual_vehicle_scale': None,
                                 'Candidate': 'NO_GO', 'Runtime': 'NO_GO', 'F70UH': 'NOT_ALLOWED',
                                 'F70V': 'NOT_ALLOWED', 'F71': 'NOT_ALLOWED', 'D2': 'PERFORMANCE_NOT_EVALUATED',
                                 'F19': 'LEGACY_UNRESOLVED', 'NATIVE_EXACT_REPLAY': 'NOT_PROVEN',
                                 'SOURCE_SCHEMA_UNQUALIFIED': 6000, 'actual_activation': 'NOT_ALLOWED'},
                **{k: 0 for k in ['F61_execution', 'r_calculations', 'dt_calculations', 'Controller_execution',
                                 'Runtime_execution', 'CAN', 'actual_production_inputs', 'calculator_input_execution',
                                 'candidate_performance_evaluation']}}

    def test_matching_actual_gate_ledger_and_closed_gates_are_accepted(self):
        p = self.module()
        result = p.validate_gate(self.summary(), 'Ran 128 tests in 2.0s\n\nOK\n', 3, 'a' * 64)
        self.assertEqual(result['tests'], 128)
        self.assertEqual(result['own_compiles'], 3)
        self.assertIsNone(result['gates']['actual_r'])

    def test_missing_truncated_and_failed_ledgers_are_rejected(self):
        p = self.module()
        for ledger in ['', 'Ran 127 tests in 2s\nOK\n', 'Ran 128 tests in 2s\nFAILED (failures=1)\n']:
            with self.subTest(ledger=ledger), self.assertRaisesRegex(ValueError, 'GATE_LEDGER'):
                p.validate_gate(self.summary(), ledger, 3, 'a' * 64)

    def test_wrong_wheel_compile_count_and_zero_or_bool_tests_are_rejected(self):
        p = self.module()
        for key, value in [('tests', True), ('tests', 0), ('own_python_compile_count', 2)]:
            record = self.summary()
            record[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                p.validate_gate(record, 'Ran 128 tests in 2s\nOK\n', 3, 'a' * 64)
        with self.assertRaisesRegex(ValueError, 'GATE_WHEEL'):
            p.validate_gate(self.summary(), 'Ran 128 tests in 2s\nOK\n', 3, 'b' * 64)

    def test_opened_safety_gate_or_actual_execution_is_rejected(self):
        p = self.module()
        for key, value in [('R_BUDGET', 'RESOLVED'), ('STATIC_EVIDENCE_GATE', 'PASS'), ('actual_r', 0),
                           ('actual_T2', 0.01), ('Runtime', 'GO'), ('F71', 'ALLOWED')]:
            record = self.summary()
            record['source_gates'][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'GATE_SAFETY'):
                p.validate_gate(record, 'Ran 128 tests in 2s\nOK\n', 3, 'a' * 64)
        record = self.summary()
        record['F61_execution'] = 1
        with self.assertRaisesRegex(ValueError, 'GATE_SAFETY'):
            p.validate_gate(record, 'Ran 128 tests in 2s\nOK\n', 3, 'a' * 64)

    def test_other_qualification_gates_are_not_silently_promoted(self):
        p = self.module()
        for key, value in [('D2', 'PERFORMANCE_PASS'), ('F19', 'RESOLVED'), ('NATIVE_EXACT_REPLAY', 'PROVEN'),
                           ('SOURCE_SCHEMA_UNQUALIFIED', 0), ('actual_activation', 'ALLOWED')]:
            record = self.summary()
            record['source_gates'][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'GATE_SAFETY'):
                p.validate_gate(record, 'Ran 128 tests in 2s\nOK\n', 3, 'a' * 64)

    def test_cli_rejects_existing_output_before_any_work_or_overwrite(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'existing'
            target.mkdir()
            (target / 'keep').write_bytes(b'keep')
            run = subprocess.run([sys.executable, '-B', TOOLS / 'cloud_run.py', 'run', '--repo-root', TOOLS.parents[1],
                                  '--commit', 'a' * 40, '--project-python', sys.executable, '--local-only', '--output', target],
                                 capture_output=True, check=False)
            self.assertEqual(run.returncode, 2)
            self.assertIn(b'OUTPUT_EXISTS', run.stdout)
            self.assertEqual({p.name for p in target.iterdir()}, {'keep'})
            self.assertEqual((target / 'keep').read_bytes(), b'keep')

    def test_cli_rejects_output_inside_checkout(self):
        self.module()
        run = subprocess.run([sys.executable, '-B', TOOLS / 'cloud_run.py', 'run', '--repo-root', TOOLS.parents[1],
                              '--commit', 'a' * 40, '--project-python', sys.executable, '--local-only',
                              '--output', TOOLS / 'forbidden-output'], capture_output=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn(b'EXTERNAL_OUTPUT_REQUIRED', run.stdout)
        self.assertFalse((TOOLS / 'forbidden-output').exists())

    def test_failed_gate_preserves_failure_and_source_without_success_receipt(self):
        self.module()
        repo = TOOLS.parents[1]
        commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD']).decode().strip()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'run'
            result = subprocess.run([sys.executable, '-B', TOOLS / 'cloud_run.py', 'run', '--repo-root', repo,
                                     '--commit', commit, '--project-python', '/bin/false', '--local-only',
                                     '--output', output], capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads((output / 'FAILURE.json').read_bytes())['stage'], 'GATE')
            self.assertTrue((output / 'source/tools/cyberlateral_dev/dev.py').is_file())
            self.assertFalse((output / 'FINAL_RESULT.json').exists())
            self.assertFalse((output / 'LOCAL_VERIFIED.json').exists())

    def test_changed_registered_source_is_not_published(self):
        p = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'a.txt'
            source.write_bytes(b'changed')
            provenance = {'files': {'a.txt': {'sha256': '0' * 64, 'byte_size': 7}}}
            with self.assertRaisesRegex(ValueError, 'SOURCE_CHANGED_DURING_RUN'):
                p.registered_payloads(Path(tmp), provenance)

    def test_timeout_stops_command_group_and_records_only_private_log(self):
        p = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / 'late'
            code = 'import time,pathlib; time.sleep(0.7); pathlib.Path(' + repr(str(marker)) + ').write_text("bad")'
            with self.assertRaisesRegex(ValueError, 'COMMAND_TIMEOUT'):
                p.run_command([sys.executable, '-c', code], root / 'private.log', root, timeout=0.1)
            time.sleep(0.8)
            self.assertFalse(marker.exists())

    def local_archive(self, root):
        a = importlib.import_module('artifacts')
        sealed = a.seal(root / 'EVIDENCE.zip', {'SOURCE_IDENTITY.json': b'{"commit":"1111111111111111111111111111111111111111"}'})
        (root / 'LOCAL_VERIFIED.json').write_text(json.dumps({'status': 'LOCAL_VERIFIED_BACKUP_PENDING',
            'source_commit': '1' * 40, 'archive': sealed}))
        receipt = {'status': 'PRIVATE_BACKUP_EXACT', 'private': True, 'repo_id': 'owner/evidence',
                   'archive_sha256': sealed['archive_sha256'], 'commit_sha': '2' * 40, 'verified_files': 2,
                   'prefix': 'runs/' + '1' * 40 + '/' + sealed['archive_sha256'] + '/', 'reused_commit': False}
        return receipt

    def test_backup_retry_preserves_local_results_and_does_not_overwrite_success(self):
        p = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = self.local_archive(root)
            before = (root / 'EVIDENCE.zip').read_bytes()
            # Replace only the external worker call; all host artifact/state logic is real.
            with patch.object(p, 'storage', side_effect=ValueError('STORAGE_UPLOAD_FAILED')):
                with self.assertRaisesRegex(ValueError, 'STORAGE_UPLOAD_FAILED'):
                    p.perform_backup(root, Path(sys.executable), 'owner/evidence')
            self.assertFalse((root / 'FINAL_RESULT.json').exists())
            self.assertEqual((root / 'EVIDENCE.zip').read_bytes(), before)
            with patch.object(p, 'storage', return_value=receipt):
                first = p.perform_backup(root, Path(sys.executable), 'owner/evidence')
                saved = (root / 'FINAL_RESULT.json').read_bytes()
                second = p.perform_backup(root, Path(sys.executable), 'owner/evidence')
            self.assertEqual(first['status'], 'CLOUD_VERIFICATION_AND_PRIVATE_BACKUP_PASS')
            self.assertEqual(second['status'], first['status'])
            self.assertEqual((root / 'FINAL_RESULT.json').read_bytes(), saved)
            self.assertEqual(len(list(root.glob('BACKUP_RECHECK-*.json'))), 1)

    def test_worker_receipt_for_another_archive_or_repo_is_not_success(self):
        p = self.module()
        for key, value in [('repo_id', 'other/evidence'), ('archive_sha256', '0' * 64),
                           ('private', False), ('verified_files', 0), ('commit_sha', 'HEAD')]:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                receipt = self.local_archive(root)
                receipt[key] = value
                with patch.object(p, 'storage', return_value=receipt), self.assertRaisesRegex(ValueError, 'STORAGE_RECEIPT_INVALID'):
                    p.perform_backup(root, Path(sys.executable), 'owner/evidence')
                self.assertFalse((root / 'FINAL_RESULT.json').exists())

    def test_failed_backup_cli_records_stage_without_running_model_or_overwrite(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.local_archive(root)
            record = json.loads((root / 'LOCAL_VERIFIED.json').read_bytes())
            record['archive']['archive_sha256'] = '0' * 64
            (root / 'LOCAL_VERIFIED.json').write_text(json.dumps(record))
            before = (root / 'EVIDENCE.zip').read_bytes()
            result = subprocess.run([sys.executable, '-B', TOOLS / 'cloud_run.py', 'backup', '--run-dir', root,
                                     '--hf-python', '/bin/false', '--hf-repo', 'owner/evidence'], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['code'], 'ARCHIVE_HASH')
            failures = list(root.glob('BACKUP_FAILED-*.json'))
            self.assertEqual(len(failures), 1)
            self.assertEqual(json.loads(failures[0].read_bytes())['stage'], 'BACKUP')
            self.assertEqual((root / 'EVIDENCE.zip').read_bytes(), before)
            self.assertFalse((root / 'FINAL_RESULT.json').exists())


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (TOOLS / 'workflow_checks.py').is_file():
            return
        cls.scratch = tempfile.TemporaryDirectory(prefix='cloud-workflow-unit-')
        cls.addClassCleanup(cls.scratch.cleanup)
        cls.root = Path(cls.scratch.name)
        want = json.loads((COMPONENT / 'reference/r41_regression_expected_v1.json').read_bytes())
        for alias in ['one', 'two', 'baseline']:
            args = [part for name in want['order'] for part in ['--input', COMPONENT / 'examples/r41' / name]]
            if alias == 'baseline':
                args += ['--baseline', cls.root / 'one/batch']
            run = subprocess.run([sys.executable, '-I', '-B', COMPONENT / 'tools/scenario_workflow.py',
                                  *args, '--output', cls.root / alias], capture_output=True, timeout=180)
            if run.returncode:
                raise AssertionError('Real R41 fixture workflow failed')

    def module(self):
        self.assertTrue((TOOLS / 'workflow_checks.py').is_file(), 'workflow checker missing')
        return importlib.import_module('workflow_checks')

    def test_real_r41_rows_views_reference_baseline_and_portable_repetition(self):
        w = self.module()
        result = w.check_workflows(COMPONENT, self.root)
        self.assertEqual(result['explicit_model_steps'], 972)
        self.assertEqual(result['explicit_reference_steps'], 972)
        self.assertEqual(result['portable_files'], 26)
        self.assertEqual(result['baseline_samples'], 324)

    def test_portable_payload_excludes_receipts_and_full_manifest(self):
        w = self.module()
        files = w.portable_files(self.root / 'one')
        self.assertEqual(len(files), 26)
        self.assertIn('WORKFLOW.json', files)
        self.assertIn('batch/BATCH.json', files)
        self.assertFalse(any('RECEIPT' in n or 'SHA256SUMS' in n or '/reference/' in n for n in files))

    def test_extra_or_corrupt_saved_file_is_not_accepted(self):
        w = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            saved = Path(tmp) / 'saved'
            shutil.copytree(self.root / 'one', saved)
            (saved / 'extra.txt').write_bytes(b'extra')
            with self.assertRaisesRegex(ValueError, 'MANIFEST_CLOSURE'):
                w.verify_tree(saved)
            (saved / 'extra.txt').unlink()
            (saved / 'WORKFLOW.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'MANIFEST_HASH'):
                w.verify_tree(saved)

    def test_coherent_private_log_substitution_is_not_a_portable_allowlist(self):
        w = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'workflows'
            shutil.copytree(self.root, root)
            for alias in ['one', 'two']:
                saved = root / alias
                private = saved / 'batch/private.log'
                private.write_bytes((saved / 'batch/case-003/report/index.html').read_bytes())
                portable = saved / 'batch/PORTABLE_SHA256SUMS.txt'
                portable.write_bytes(portable.read_bytes().replace(b'  case-003/report/index.html\n', b'  private.log\n'))
                for base in [saved / 'batch', saved]:
                    files = {p.relative_to(base).as_posix(): p.read_bytes() for p in base.rglob('*')
                             if p.is_file() and p != base / 'SHA256SUMS.txt'}
                    (base / 'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n'
                                                               for name, raw in sorted(files.items())))
            # Full records, literals, references, hashes and repetition still match.
            with self.assertRaisesRegex(ValueError, 'PORTABLE_ALLOWLIST'):
                w.check_workflows(COMPONENT, root)


if __name__ == '__main__':
    unittest.main()
