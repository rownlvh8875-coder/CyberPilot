"""R27 artifact guard tests: retained inputs, real validator, no native or model."""

import importlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from suite_fixture import rehash, write_stage
from v1_helpers import ROOT


class SuiteValidationTests(unittest.TestCase):
    def modules(self):
        self.assertTrue((ROOT / 'native_qualification/suite_validation.py').is_file(), 'Missing suite validator')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('native_qualification.suite_profiles'), importlib.import_module('native_qualification.suite_validation')

    def test_all_eight_complete_records_with_literal_counts_and_pins(self):
        _, validator = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            rows = []
            for stage_id in ['R19', 'R20', 'R21', 'R22', 'R23', 'R24', 'R25', 'R26']:
                path = Path(scratch) / stage_id
                write_stage(path, stage_id)
                rows.append(validator.validate_stage(path, stage_id))
        self.assertEqual([r['case_count'] for r in rows], [None, 4, 8, 8, 4, 99, 20, 99])
        self.assertEqual([r['model_execution'] for r in rows], [0, 0, 0, 10, 8, 198, 40, 198])
        self.assertEqual(rows[5]['reference_sha256'], 'dfb150fc3f1348be6fae161bdb2d524dc1138c504410c8ef38bf874c27b4d8cd')
        self.assertEqual(rows[-1]['observations_sha256'], '4720baa96bfef759037a80a214d5ce84292fc0b607d06f5ccfd9f5b86d154a62')

    def test_registry_tamper_symlink_and_fresh_load(self):
        profiles, _ = self.modules()
        self.assertEqual([p.stage_id for p in profiles.load_profiles()], ['R19', 'R20', 'R21', 'R22', 'R23', 'R24', 'R25', 'R26'])
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / 'bad'
            path.write_bytes(b'{}')
            with patch.object(profiles, 'REGISTRY_PATH', path), self.assertRaisesRegex(ValueError, 'SUITE_PROFILE_IDENTITY'):
                profiles.load_profiles()
            path.unlink()
            path.symlink_to(profiles.REGISTRY_PATH)
            with patch.object(profiles, 'REGISTRY_PATH', path), self.assertRaisesRegex(ValueError, 'SUITE_PROFILE_IDENTITY'):
                profiles.load_profiles()

    def test_unknown_or_nonbuiltin_stage_rejected(self):
        _, validator = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            for stage in ['R18', 'R27', True, 26, None]:
                with self.assertRaisesRegex(ValueError, 'SUITE_STAGE'):
                    validator.validate_stage(Path(scratch), stage)

    def test_manifest_tamper_duplicate_and_path_escape_do_not_read_outside(self):
        _, validator = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            path = root / 'R19'
            write_stage(path, 'R19')
            manifest = (path / 'SHA256SUMS.txt').read_bytes()
            for raw in [manifest.replace(b'OBSERVATIONS.json', b'../outside'), manifest + manifest, b'0' * 64 + b'  SUMMARY.json\n']:
                (path / 'SHA256SUMS.txt').write_bytes(raw)
                with self.assertRaisesRegex(ValueError, 'SUITE_MANIFEST'):
                    validator.validate_stage(path, 'R19')
            self.assertFalse((root / 'outside').exists())

    def test_missing_extra_and_nonregular_entries_rejected(self):
        _, validator = self.modules()
        for problem in ['missing', 'extra', 'directory']:
            with tempfile.TemporaryDirectory() as scratch:
                path = Path(scratch) / 'R19'
                write_stage(path, 'R19')
                if problem == 'extra':
                    (path / 'EXTRA').write_bytes(b'not allowed')
                else:
                    (path / 'RECEIPT_1.json').unlink()
                    if problem == 'directory':
                        (path / 'RECEIPT_1.json').mkdir()
                with self.assertRaisesRegex(ValueError, 'SUITE_STAGE_FILES'):
                    validator.validate_stage(path, 'R19')

    def test_stage_and_member_symlinks_rejected(self):
        _, validator = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            path = root / 'R19'
            write_stage(path, 'R19')
            link = root / 'link'
            link.symlink_to(path)
            with self.assertRaisesRegex(ValueError, 'SUITE_STAGE_FILES'):
                validator.validate_stage(link, 'R19')
            saved = (path / 'RECEIPT_1.json').read_bytes()
            (root / 'receipt').write_bytes(saved)
            (path / 'RECEIPT_1.json').unlink()
            (path / 'RECEIPT_1.json').symlink_to(root / 'receipt')
            with self.assertRaisesRegex(ValueError, 'SUITE_STAGE_FILES'):
                validator.validate_stage(path, 'R19')

    def test_noncanonical_or_non_dict_records_rejected(self):
        _, validator = self.modules()
        for raw in [b'{}', b'[]\n', b'{"x":1,"x":1}\n', b'{ "scope": "padded" }\n']:
            with tempfile.TemporaryDirectory() as scratch:
                path = Path(scratch) / 'R19'
                write_stage(path, 'R19')
                (path / 'RECEIPT_1.json').write_bytes(raw)
                rehash(path)
                with self.assertRaisesRegex(ValueError, 'SUITE_CANONICAL_RECORD'):
                    validator.validate_stage(path, 'R19')

    def test_changed_observation_or_equal_missing_rows_rejected(self):
        _, validator = self.modules()
        for stage in ['R19', 'R26']:
            with tempfile.TemporaryDirectory() as scratch:
                path = Path(scratch) / stage
                def mutate(record, stage=stage):
                    if stage == 'R26':
                        record['observations']['cases'].pop()
                    else:
                        record['observations']['schema_version'] = True
                write_stage(path, stage, mutate=mutate)
                with self.assertRaisesRegex(ValueError, 'SUITE_OBSERVATION_IDENTITY'):
                    validator.validate_stage(path, stage)

    def test_summary_status_reference_counts_gates_and_extra_fields_rejected(self):
        _, validator = self.modules()
        changes = [('status', 'PASS'), ('model_reference_sha256', '0' * 64), ('model_execution', True),
                   ('model_execution_per_worker', 0), ('worker_processes', True), ('actual_input', 'ALLOWED'),
                   ('STATIC_EVIDENCE_GATE', 'PASS'), ('F61_execution', True), ('r_calculation', 1), ('EXTRA', 0)]
        for key, value in changes:
            with tempfile.TemporaryDirectory() as scratch:
                path = Path(scratch) / 'R26'
                write_stage(path, 'R26', mutate=lambda record, key=key, value=value: record['summary'].update({key: value}))
                with self.assertRaisesRegex(ValueError, 'SUITE_SUMMARY'):
                    validator.validate_stage(path, 'R26')

    def test_source_digest_or_source_key_omission_is_not_accepted(self):
        _, validator = self.modules()
        for problem in ['digest', 'missing', 'escape']:
            with tempfile.TemporaryDirectory() as scratch:
                path = Path(scratch) / 'R19'
                def mutate(record, problem=problem):
                    sources = record['summary']['tool_sources']
                    if problem == 'digest':
                        sources['worker.py'] = '0' * 64
                    elif problem == 'missing':
                        del sources['worker.py']
                    else:
                        sources['../outside'] = '0' * 64
                write_stage(path, 'R19', mutate=mutate)
                with self.assertRaisesRegex(ValueError, 'SUITE_SUMMARY'):
                    validator.validate_stage(path, 'R19')

    def test_numeric_validator_failure_and_oversized_artifact_fail_closed(self):
        _, validator = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            path = root / 'R26'
            write_stage(path, 'R26')
            with patch.object(validator, 'validate_coverage', side_effect=ValueError('NUMERIC_REJECT')), self.assertRaisesRegex(ValueError, 'NUMERIC_REJECT'):
                validator.validate_stage(path, 'R26')
            (path / 'RECEIPT_1.json').write_bytes(b'x' * 2_000_001)
            with self.assertRaisesRegex(ValueError, 'SUITE_STAGE_FILES'):
                validator.validate_stage(path, 'R26')

    def test_import_and_all_validation_do_not_load_or_execute_native_model(self):
        self.modules()
        script = ('import sys; sys.path.insert(0,' + repr(str(ROOT)) + '); '
                  'import native_qualification.suite_validation; '
                  'assert not any(n.split(".")[0] in {"capnp","numpy","cyberlateral_dev","openpilot","opendbc","selfdrive","cereal"} for n in sys.modules)')
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script], capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode())


if __name__ == '__main__':
    unittest.main()
