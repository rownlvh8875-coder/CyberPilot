"""Recorded observations are not arithmetic replay or input-origin approval."""

import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from scenario_report_fixture import edit_json, layout_bundle, write_bundle
from v1_helpers import ROOT


class TraceSummaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.scratch.cleanup)
        cls.root = Path(cls.scratch.name)
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        cls.reader = importlib.import_module('integration_tools.scenario_report_data')
        cls.sign = write_bundle(cls.root / 'sign')
        cls.resumed = write_bundle(cls.root / 'resumed', 'resumed')
        cls.flat = layout_bundle(cls.root / 'flat', count=4096, negative_zero=True)
        for source in [cls.sign, cls.resumed, cls.flat]:
            cls.reader.read_report(source)

    def module(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_trace_summary.py').is_file(), 'Missing R70 trace summary')
        return importlib.import_module('integration_tools.scenario_trace_summary')

    def rewrite(self, root, change):
        """Coherently resealed test records, never newly executed model outputs."""
        record = json.loads((root / 'RESULTS.json').read_bytes())
        spec = self.reader._spec(json.loads((root / 'INPUT.json').read_bytes()))
        receipt = json.loads((root / 'RECEIPT.json').read_bytes())
        change(record)
        record['final_state'] = deepcopy(record['rows'][-1]['model_output']['next_state'])
        formatter = importlib.import_module('integration_tools.scenario_output')
        data = {key: record[key] for key in ['model_steps', 'rows', 'final_state']}
        for name, raw in formatter.render_outputs(spec, data, record['identity'], receipt).items():
            (root / name).write_bytes(raw)
        self.reader.read_report(root)

    def test_sign_literals_distinguish_clip_numeric_and_kind_changes(self):
        summary = self.module().summarize_saved_trace(self.sign)
        self.assertEqual(summary['recorded_model_steps'], 4)
        self.assertEqual(summary['stage_events'], {
            'driver_clip_numeric_changed': {'count': 0, 'first_sample_index': None},
            'driver_clip_representation_changed': {'count': 4, 'first_sample_index': 0},
            'rate_clip_numeric_changed': {'count': 4, 'first_sample_index': 0},
            'rate_clip_representation_changed': {'count': 4, 'first_sample_index': 0},
            'rate_to_limited_numeric_changed': {'count': 0, 'first_sample_index': None},
            'fault_condition_true': {'count': 0, 'first_sample_index': None},
            'angle_counter_reset': {'count': 0, 'first_sample_index': None}})
        self.assertEqual(summary['recorded_summary'], {'steps': 4, 'inactive_calls': 1, 'limiter_adjusted': 4,
                                                     'inactive_gate_changed': 1, 'fault_request_suppressed': 0})
        self.assertEqual(len(summary['source_hashes']), 6)
        self.assertFalse(summary['source_identity_reauthenticated'])
        self.assertEqual((summary['summary_model_executions'], summary['summary_reference_executions']), (0, 0))

    def test_resumed_first_sample_index_is_not_offset_or_zeroed_suppression(self):
        summary = self.module().summarize_saved_trace(self.resumed)
        self.assertEqual(summary['stage_events']['fault_condition_true'], {'count': 1, 'first_sample_index': 5})
        self.assertEqual(summary['stage_events']['driver_clip_numeric_changed']['count'], 0)
        self.assertEqual(summary['stage_events']['driver_clip_representation_changed']['count'], 1)
        self.assertEqual(summary['stage_events']['rate_clip_numeric_changed'], {'count': 1, 'first_sample_index': 5})
        self.assertEqual(summary['recorded_summary']['fault_request_suppressed'], 1)
        self.assertEqual(self.reader.read_report(self.resumed)['view']['rows'][0]['final_command'], -2)

    def test_int64_difference_must_not_be_rounded_through_binary64(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            source = write_bundle(Path(scratch) / 'source')

            def change(record):
                down = record['rows'][0]['model_output']['trace']['downstream']
                down['driver_clip']['result'] = {'kind': 'numpy.int64', 'value': 9007199254740993}
                down['rate_clip']['x'] = deepcopy(down['driver_clip']['result'])
                down['rate_clip']['result'] = {'kind': 'numpy.float64', 'value': '0x1.0000000000000p+53'}

            self.rewrite(source, change)
            summary = m.summarize_saved_trace(source)
            self.assertEqual(summary['stage_events']['rate_clip_numeric_changed']['count'], 4)
            self.assertEqual(summary['stage_events']['rate_to_limited_numeric_changed']['count'], 1)
            self.assertEqual(summary['validation_claim'], 'CHECKSUM_AND_CROSS_RECORD_CONSISTENCY_NOT_MODEL_OR_ORIGIN_VALIDATION')

    def test_signed_zero_is_numeric_equal_but_representation_different(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            source = write_bundle(Path(scratch) / 'source')

            def change(record):
                down = record['rows'][0]['model_output']['trace']['downstream']
                down['driver_clip']['result'] = {'kind': 'numpy.float64', 'value': '-0x0.0p+0'}
                down['rate_clip']['x'] = deepcopy(down['driver_clip']['result'])
                down['rate_clip']['result'] = {'kind': 'numpy.float64', 'value': '0x0.0p+0'}

            self.rewrite(source, change)
            summary = m.summarize_saved_trace(source)
            self.assertEqual(summary['stage_events']['rate_clip_numeric_changed'], {'count': 3, 'first_sample_index': 1})
            self.assertEqual(summary['stage_events']['rate_clip_representation_changed'], {'count': 4, 'first_sample_index': 0})

    def test_coherent_recorded_counter_reset_is_observation_not_recalculation(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            source = write_bundle(Path(scratch) / 'source', 'resumed')

            def change(record):
                output = record['rows'][0]['model_output']
                output['next_state']['angle_counter'] = 0
                output['trace']['downstream']['next_state']['angle_counter'] = 0

            self.rewrite(source, change)
            summary = m.summarize_saved_trace(source)
            self.assertEqual(summary['stage_events']['angle_counter_reset'], {'count': 1, 'first_sample_index': 5})
            self.assertFalse(summary['source_identity_reauthenticated'])
            self.assertEqual(summary['summary_model_executions'], 0)

    def test_late_state_false_gates_and_foreign_scalar_reject(self):
        m = self.module()
        changes = [lambda r: r['rows'][-1]['prepared']['state'].update(previous_applied=99),
                   lambda r: r['gates'].update(STATIC_EVIDENCE_GATE='PASS'),
                   lambda r: r['rows'][-1]['model_output']['trace']['downstream']['rate_clip']['result'].update(kind='foreign')]
        for change in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as scratch:
                source = write_bundle(Path(scratch) / 'source')
                edit_json(source, 'RESULTS.json', change)
                with self.assertRaises(self.reader.ReportError):
                    m.summarize_saved_trace(source)

    def test_closed_files_checksums_and_size_bounds_cannot_be_bypassed(self):
        m = self.module()
        for mode in ['missing', 'extra', 'corrupt', 'oversized']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as scratch:
                source = write_bundle(Path(scratch) / 'source')
                if mode == 'missing':
                    (source / 'TRACE.csv').unlink()
                elif mode == 'extra':
                    (source / 'extra').write_bytes(b'not a known record')
                elif mode == 'corrupt':
                    (source / 'TRACE.csv').write_bytes(b'bad\n')
                else:
                    (source / 'RESULTS.json').write_bytes(b' ' * (16777216 + 1))
                with self.assertRaises(self.reader.ReportError):
                    m.summarize_saved_trace(source)

    def test_root_ancestor_and_member_symlinks_reject(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source = write_bundle(root / 'source')
            (root / 'root-link').symlink_to(source)
            (root / 'parent-link').symlink_to(root)
            for target in [root / 'root-link', root / 'parent-link/source']:
                with self.assertRaises(self.reader.ReportError) as error:
                    m.summarize_saved_trace(target)
                self.assertEqual(error.exception.code, 'TRACE_SUMMARY_INPUT_FILE')
            (source / 'TRACE.csv').unlink()
            (source / 'TRACE.csv').symlink_to('/dev/null')
            with self.assertRaises(self.reader.ReportError):
                m.summarize_saved_trace(source)

    def test_fifo_member_rejects_without_blocking(self):
        self.module()
        with tempfile.TemporaryDirectory() as scratch:
            source = write_bundle(Path(scratch) / 'source')
            (source / 'TRACE.csv').unlink()
            os.mkfifo(source / 'TRACE.csv')
            code = (f'import sys;from pathlib import Path;sys.path.insert(0,{str(ROOT)!r});'
                    'from integration_tools.scenario_trace_summary import summarize_saved_trace;'
                    'from integration_tools.scenario_report_data import ReportError\n'
                    f'try: summarize_saved_trace(Path({str(source)!r}))\n'
                    'except ReportError as e: print(e.code)\n')
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, timeout=3, check=False)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b'REPORT_INPUT_FILE\n', b''))

    def test_maximum_recorded_rows_and_detached_return_preserve_input(self):
        m = self.module()
        before = {p.name: p.read_bytes() for p in self.flat.iterdir()}
        summary = m.summarize_saved_trace(self.flat)
        self.assertEqual(summary['recorded_model_steps'], 4096)
        self.assertEqual(summary['stage_events']['driver_clip_representation_changed'], {'count': 4096, 'first_sample_index': 0})
        summary['gates']['STATIC_EVIDENCE_GATE'] = 'PASS'
        summary['stage_events']['driver_clip_numeric_changed']['count'] = 999
        again = m.summarize_saved_trace(self.sign)
        self.assertEqual(again['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
        self.assertEqual(again['stage_events']['driver_clip_numeric_changed']['count'], 0)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.flat.iterdir()})

    def test_metadata_is_inert_and_reader_imports_no_model_or_native_modules(self):
        self.module()
        with tempfile.TemporaryDirectory() as scratch:
            source = write_bundle(Path(scratch) / 'source')
            edit_json(source, 'RESULTS.json', lambda r: r['identity']['observed_dev_source_hashes'].update(
                {'integration_tools/historical_only.py': '1' * 64}))
            code = (f'import sys;from pathlib import Path;sys.path.insert(0,{str(ROOT)!r});'
                    'from integration_tools.scenario_trace_summary import summarize_saved_trace;'
                    f'r=summarize_saved_trace(Path({str(source)!r}));'
                    'assert not any(n.split(".")[0] in {"cyberlateral_dev","capnp","numpy","openpilot","opendbc","cereal"} for n in sys.modules);'
                    'print(r["summary_model_executions"],r["summary_reference_executions"])')
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, timeout=10, check=False)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b'0 0\n', b''))

    def test_unsupported_runtime_rejects_before_missing_input_access(self):
        m = self.module()
        with patch('platform.python_version', return_value='0.0'):
            with self.assertRaises(self.reader.ReportError) as error:
                m.summarize_saved_trace(self.root / 'absent')
        self.assertEqual(error.exception.code, 'TRACE_SUMMARY_RUNTIME')
