"""Checksummed recorded data is consistent, not authenticated or re-calculated."""

import importlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scenario_report_fixture import edit_json, rehash, write_bundle
from v1_helpers import ROOT


class ScenarioReportDataTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_report_data.py').is_file(), 'Missing R32 reader')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_report_data')

    def test_preserved_sign_stage_values_and_distinct_state(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            source = write_bundle(Path(scratch) / 'input')
            data = m.read_report(source)
            rows = data['view']['rows']
            self.assertEqual([r['integer_request'] for r in rows], [4, -4, 4, 4])
            self.assertEqual([r['limited_command'] for r in rows], [2, -2, 2, 2])
            self.assertEqual([r['final_command'] for r in rows], [2, -2, 0, 2])
            self.assertEqual((rows[3]['previous_requested'], rows[3]['previous_applied']), (4, 0))
            self.assertEqual(data['view']['summary']['inactive_calls'], 1)
            self.assertEqual(len(data['source_hashes']), 6)
            self.assertEqual(data['view']['validation_claim'], 'CHECKSUM_AND_CROSS_RECORD_CONSISTENCY_NOT_MODEL_OR_ORIGIN_VALIDATION')

    def test_preserved_resumed_counter_and_suppression_not_zero_command(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            source = write_bundle(Path(scratch) / 'input', 'resumed')
            row = m.read_report(source)['view']['rows'][0]
            self.assertEqual((row['index'], row['angle_counter_before'], row['angle_counter_after'], row['final_command']), (5, 89, 90, -2))
            self.assertIs(row['steer_request'], False)
            self.assertIs(row['fault_request_suppressed'], True)

    def test_missing_extra_corrupt_and_unsafe_manifest_reject(self):
        m = self.module()
        for mode in ['missing', 'extra', 'corrupt', 'traversal', 'duplicate']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as scratch:
                source = write_bundle(Path(scratch) / 'input')
                if mode == 'missing':
                    (source / 'SUMMARY_KO.md').unlink()
                elif mode == 'extra':
                    (source / 'extra').write_bytes(b'not opened')
                elif mode == 'corrupt':
                    (source / 'TRACE.csv').write_bytes(b'changed')
                else:
                    raw = (source / 'SHA256SUMS.txt').read_bytes()
                    (source / 'SHA256SUMS.txt').write_bytes(raw.replace(b'INPUT.json', b'../outside') if mode == 'traversal' else raw + raw[:raw.index(b'\n') + 1])
                with self.assertRaises(m.ReportError):
                    m.read_report(source)

    def test_rehashed_csv_summary_and_false_closed_gates_reject(self):
        m = self.module()
        for name in ['TRACE.csv', 'SUMMARY_KO.md', 'RESULTS.json']:
            with tempfile.TemporaryDirectory() as scratch:
                source = write_bundle(Path(scratch) / 'input')
                if name == 'RESULTS.json':
                    edit_json(source, name, lambda x: x['gates'].update(STATIC_EVIDENCE_GATE='PASS'))
                else:
                    (source / name).write_bytes((source / name).read_bytes() + b'changed\n')
                    rehash(source)
                with self.assertRaises(m.ReportError):
                    m.read_report(source)

    def test_rehashed_row_alias_state_final_and_count_mismatch_reject(self):
        m = self.module()
        changes = [lambda x: x['rows'][1]['prepared']['state'].update(previous_applied=1),
                   lambda x: x['final_state'].update(previous_applied=1), lambda x: x.update(model_steps=True),
                   lambda x: x['rows'][0]['model_output']['trace']['downstream'].update(steer_request=False),
                   lambda x: x['rows'][0]['model_output']['trace']['quantization'].update(request_hex='0x0.0p+0')]
        for change in changes:
            with tempfile.TemporaryDirectory() as scratch:
                source = write_bundle(Path(scratch) / 'input')
                edit_json(source, 'RESULTS.json', change)
                with self.assertRaises(m.ReportError):
                    m.read_report(source)

    def test_exact_nested_shapes_types_and_float_words(self):
        m = self.module()
        changes = [lambda x: x.update(extra=0), lambda x: x['rows'][0].update(extra=0),
                   lambda x: x['rows'][0]['model_output']['projection'].update(integer_command=True),
                   lambda x: x['rows'][0]['model_output']['trace']['downstream'].update(fault_condition=1),
                   lambda x: x['rows'][0]['model_output']['projection']['torque_float32'].update(bits_hex='<script>'),
                   lambda x: x['rows'][0]['model_output']['trace']['downstream']['driver_clip']['x'].update(kind='foreign')]
        for change in changes:
            with tempfile.TemporaryDirectory() as scratch:
                source = write_bundle(Path(scratch) / 'input')
                edit_json(source, 'RESULTS.json', change)
                with self.assertRaises(m.ReportError):
                    m.read_report(source)

    def test_recorded_clip_input_aliases_must_agree(self):
        m = self.module()
        for clip in ['driver_clip', 'rate_clip']:
            with tempfile.TemporaryDirectory() as scratch:
                source = write_bundle(Path(scratch) / 'input')
                edit_json(source, 'RESULTS.json', lambda x, clip=clip: x['rows'][0]['model_output']['trace']['downstream'][clip]['x'].update(value=99))
                with self.assertRaises(m.ReportError):
                    m.read_report(source)

    def test_rehashed_rounded_integer_must_equal_recorded_integer_command(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            source = write_bundle(Path(scratch) / 'input')
            edit_json(source, 'RESULTS.json', lambda x: x['rows'][0]['model_output']['trace']['quantization'].update(rounded_integer=999))
            with self.assertRaises(m.ReportError) as error:
                m.read_report(source)
            self.assertEqual(error.exception.code, 'REPORT_CONSISTENCY')

    def test_canonical_json_duplicates_nonfinite_deep_reject_even_rehashed(self):
        m = self.module()
        for mode in ['space', 'duplicate', 'nonfinite', 'deep', 'utf8']:
            with tempfile.TemporaryDirectory() as scratch:
                source = write_bundle(Path(scratch) / 'input')
                raw = (source / 'RESULTS.json').read_bytes()
                bad = {'space': b' ' + raw, 'duplicate': raw.replace(b'"model_steps":4', b'"model_steps":4,"model_steps":4'),
                       'nonfinite': raw.replace(b'"model_steps":4', b'"model_steps":NaN'),
                       'deep': b'[' * 65 + b'0' + b']' * 65, 'utf8': b'\xff'}[mode]
                (source / 'RESULTS.json').write_bytes(bad)
                rehash(source)
                with self.assertRaises(m.ReportError):
                    m.read_report(source)

    def test_bounded_file_sizes_before_parsing(self):
        m = self.module()
        for name, cap in [('INPUT.json', 1048576), ('RESULTS.json', 16777216), ('TRACE.csv', 1048576),
                          ('SUMMARY_KO.md', 16384), ('RECEIPT.json', 524288), ('SHA256SUMS.txt', 4096)]:
            with tempfile.TemporaryDirectory() as scratch:
                source = write_bundle(Path(scratch) / 'input')
                (source / name).write_bytes(b' ' * (cap + 1))
                with self.assertRaises(m.ReportError) as error:
                    m.read_report(source)
                self.assertEqual(error.exception.code, 'REPORT_SIZE')

    def test_directory_member_symlinks_and_fifo_never_followed(self):
        self.module()
        for mode in ['root_link', 'member_link', 'directory', 'fifo']:
            with tempfile.TemporaryDirectory() as scratch:
                root = Path(scratch)
                source = write_bundle(root / 'input')
                if mode == 'root_link':
                    (root / 'link').symlink_to(source)
                    source = root / 'link'
                else:
                    (source / 'TRACE.csv').unlink()
                    if mode == 'member_link':
                        (source / 'TRACE.csv').symlink_to('/dev/null')
                    elif mode == 'directory':
                        (source / 'TRACE.csv').mkdir()
                    else:
                        os.mkfifo(source / 'TRACE.csv')
                code = ('import sys;from pathlib import Path;sys.path.insert(0,' + repr(str(ROOT)) + ');'
                        'from integration_tools.scenario_report_data import read_report,ReportError\n'
                        'try: read_report(Path(' + repr(str(source)) + '))\n'
                        'except ReportError as e: print(e.code)\n')
                result = subprocess.run([sys.executable, '-I', '-B', '-c', code], timeout=3, capture_output=True, check=False)
                self.assertEqual((result.returncode, result.stdout), (0, b'REPORT_INPUT_FILE\n'))

    def test_old_producer_inventory_is_metadata_never_opened(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            source = write_bundle(Path(scratch) / 'input')
            edit_json(source, 'RESULTS.json', lambda x: x['identity']['observed_dev_source_hashes'].update({'integration_tools/historical_only.py': '1' * 64}))
            data = m.read_report(source)
            self.assertIn('integration_tools/historical_only.py', data['view']['producer_identity']['observed_dev_source_hashes'])
            self.assertFalse((ROOT / 'integration_tools/historical_only.py').exists())

    def test_receipt_binding_and_model_identity_mismatch_reject(self):
        m = self.module()
        for name, change in [('RECEIPT.json', lambda x: x.update(input_raw_sha256='f' * 64)),
                             ('RESULTS.json', lambda x: x['identity'].update(model_version='other')),
                             ('INPUT.json', lambda x: x['samples'][0].update(request_hex='0x1p-2'))]:
            with tempfile.TemporaryDirectory() as scratch:
                source = write_bundle(Path(scratch) / 'input')
                edit_json(source, name, change)
                with self.assertRaises(m.ReportError):
                    m.read_report(source)

    def test_inert_reader_no_model_or_native_import(self):
        self.module()
        with tempfile.TemporaryDirectory() as scratch:
            source = write_bundle(Path(scratch) / 'input')
            code = ('import sys;from pathlib import Path;sys.path.insert(0,' + repr(str(ROOT)) + ');'
                    'from integration_tools.scenario_report_data import read_report;read_report(Path(' + repr(str(source)) + '));'
                    'assert not any(n.split(".")[0] in {"cyberlateral_dev","capnp","numpy","openpilot","opendbc","cereal"} for n in sys.modules)')
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
