"""Real batch workers, file isolation, literal regressions and exclusive output."""

import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from scenario_fixture import document, encode
from v1_helpers import ROOT


class Links(HTMLParser):
    def __init__(self, raw):
        super().__init__()
        self.tags = []
        self.feed(raw.decode())

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class BatchCLITests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'tools/scenario_batch.py').is_file(), 'Missing batch CLI')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_batch_run')

    def cli(self, *args):
        return subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/scenario_batch.py', *map(str, args)],
                              capture_output=True, timeout=40, check=False)

    def record(self, output):
        return json.loads((output / 'BATCH.json').read_bytes())

    def test_two_examples_literals_state_isolation_and_renderer_zero(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            result = self.cli('--input', ROOT / 'examples/synthetic_sign_cycle_v1.json',
                              '--input', ROOT / 'examples/synthetic_resumed_v1.json', '--output', output)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            record = self.record(output)
            self.assertEqual((record['completed'], record['rejected'], record['total_model_steps']), (2, 0, 5))
            self.assertEqual(record['renderer_model_executions'], 0)
            self.assertEqual(record['gates']['STATIC_EVIDENCE_GATE'], 'FAIL')
            self.assertEqual(record['gates']['R_BUDGET'], 'UNRESOLVED')
            for key in ['actual_r', 'T2', 'vehicle_scale']:
                self.assertIsNone(record['gates'][key])
            first, second = [json.loads((output / r['report'] / 'VIEW.json').read_bytes()) for r in record['cases']]
            self.assertEqual([r['integer_request'] for r in first['rows']], [4, -4, 4, 4])
            self.assertEqual([r['final_command'] for r in first['rows']], [2, -2, 0, 2])
            row = second['rows'][0]
            self.assertEqual([row[k] for k in ['index', 'previous_requested', 'previous_applied', 'angle_counter_before',
                                              'integer_request', 'final_command', 'angle_counter_after', 'steer_request']],
                             [5, 2, 2, 89, -4, -2, 90, False])
            for item in record['cases']:
                receipt = json.loads((output / item['report'] / 'RECEIPT.json').read_bytes())
                self.assertEqual(receipt['forbidden_modules_loaded'], [])
                self.assertEqual(receipt['renderer_model_executions'], 0)

    def test_driver_inactive_resume_and_duplicate_ids_do_not_share_state(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = document(4)
            data['samples'][0]['driver'] = -1024.0
            data['samples'][1]['lat_active'] = False
            (root / 'one.json').write_bytes(encode(data))
            (root / 'two.json').write_bytes(encode(document()))
            record = m.run_batch([root / 'one.json', root / 'two.json'], root / 'out')
            self.assertEqual([r['scenario_id'] for r in record['cases']], ['R31_test', 'R31_test'])
            views = [json.loads((root / 'out' / r['report'] / 'VIEW.json').read_bytes()) for r in record['cases']]
            self.assertEqual([r['final_command'] for r in views[0]['rows']], [0, 0, 2, 4])
            self.assertEqual(views[1]['rows'][0]['final_command'], 2)
            self.assertEqual(views[1]['rows'][0]['previous_applied'], 0)

    def test_mixed_rejections_preserve_order_and_valid_file_executes(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'bad.json').write_bytes(b'{')
            result = self.cli('--input', root / 'bad.json', '--input', ROOT / 'examples/synthetic_resumed_v1.json',
                              '--input', root / 'absent.json', '--output', root / 'out')
            self.assertEqual(result.returncode, 1, result.stderr.decode())
            record = self.record(root / 'out')
            self.assertEqual([r['status'] for r in record['cases']], ['REJECTED', 'COMPLETE', 'REJECTED'])
            self.assertEqual([r['rejection_code'] for r in record['cases']], ['SCENARIO_JSON', None, 'SCENARIO_INPUT_FILE'])
            self.assertEqual((record['total_model_steps'], record['rejected']), (1, 2))
            self.assertEqual((root / 'out/inputs/case-001.json').read_bytes(), b'{')
            self.assertFalse((root / 'out/case-001').exists())
            self.assertIsNone(record['cases'][2]['input_sha256'])

    def test_all_invalid_creates_complete_error_index_without_workers(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(m, '_worker', side_effect=AssertionError('WORKER_EXECUTED')):
                result = m.run_batch([root / 'missing.json'], root / 'out')
            self.assertEqual((result['completed'], result['rejected'], result['total_model_steps']), (0, 1, 0))
            self.assertIn(b'REJECTED', (root / 'out/index.html').read_bytes())
            self.assertEqual(self.cli('--input', root / 'missing.json', '--output', root / 'out2').returncode, 1)

    def test_snapshot_consumed_even_when_original_changes_before_worker(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'input.json'
            raw = encode(document())
            source.write_bytes(raw)
            worker = m._worker

            def mutate_then_run(*args):
                source.write_bytes(b'changed after preflight')
                return worker(*args)

            with patch.object(m, '_worker', side_effect=mutate_then_run):
                result = m.run_batch([source], root / 'out')
            self.assertEqual(result['total_model_steps'], 1)
            self.assertEqual((root / 'out/inputs/case-001.json').read_bytes(), raw)
            self.assertEqual(result['cases'][0]['input_sha256'], hashlib.sha256(raw).hexdigest())

    def test_repeat_portable_manifest_and_all_nested_hashes(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ['one', 'two']:
                m.run_batch([ROOT / 'examples/synthetic_resumed_v1.json'], root / name)
                output = root / name
                for manifest in output.rglob('SHA256SUMS.txt'):
                    for line in manifest.read_text().splitlines():
                        digest, relative = line.split('  ')
                        self.assertEqual(hashlib.sha256((manifest.parent / relative).read_bytes()).hexdigest(), digest)
                for line in (output / 'PORTABLE_SHA256SUMS.txt').read_text().splitlines():
                    digest, relative = line.split('  ')
                    self.assertEqual(hashlib.sha256((output / relative).read_bytes()).hexdigest(), digest)
                    self.assertNotIn('RECEIPT', relative)
                    self.assertNotIn('SHA256SUMS', relative)
                    self.assertFalse(relative.endswith('.log'))
            self.assertEqual((root / 'one/PORTABLE_SHA256SUMS.txt').read_bytes(), (root / 'two/PORTABLE_SHA256SUMS.txt').read_bytes())
            self.assertNotEqual((root / 'one/RECEIPT.json').read_bytes(), (root / 'two/RECEIPT.json').read_bytes())

    def test_hostile_filename_escaped_only_generated_links_and_no_active_content(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / '<script>alert(1)</script>.json'.replace('/', '_')
            source.write_bytes(b'{')
            m.run_batch([source], root / 'out')
            raw = (root / 'out/index.html').read_bytes()
            dom = Links(raw)
            self.assertIn(b'&lt;script&gt;', raw)
            self.assertFalse(any(tag in {'script', 'iframe', 'img', 'link'} for tag, _ in dom.tags))
            self.assertTrue(any(tag == 'meta' and a.get('name') == 'viewport' for tag, a in dom.tags))
            self.assertTrue(any(tag == 'meta' and a.get('http-equiv') == 'Content-Security-Policy' for tag, a in dom.tags))
            links = [a['href'] for tag, a in dom.tags if tag == 'a']
            self.assertTrue(links)
            for href in links:
                self.assertNotIn(':', href)
                self.assertNotIn('..', href)
                self.assertTrue((root / 'out' / href).is_file())
            self.assertNotIn(str(root).encode(), raw)

    def test_worker_failure_retains_partial_without_completion_and_retry_rejects(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = m._worker

            def fail_report(tool, *args):
                if tool == 'scenario_report.py':
                    raise m.BatchError('BATCH_WORKER_FAILED')
                return original(tool, *args)

            with patch.object(m, '_worker', side_effect=fail_report), self.assertRaises(m.BatchError):
                m.run_batch([ROOT / 'examples/synthetic_resumed_v1.json'], root / 'out')
            self.assertTrue((root / 'out/case-001/data/RESULTS.json').is_file())
            self.assertFalse((root / 'out/BATCH.json').exists())
            with self.assertRaises(m.BatchError) as caught:
                m.run_batch([root / 'missing.json'], root / 'out')
            self.assertEqual(caught.exception.code, 'BATCH_OUTPUT_EXISTS')

    def test_publication_failure_does_not_write_completion_marker(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = m._write_exclusive

            def fail_marker(path, raw):
                if path.name == 'BATCH.json':
                    raise OSError('synthetic write fault')
                original(path, raw)

            with patch.object(m, '_write_exclusive', side_effect=fail_marker), self.assertRaises(m.BatchError) as caught:
                m.run_batch([root / 'absent.json'], root / 'out')
            self.assertEqual(caught.exception.code, 'BATCH_PUBLICATION_FAILED')
            self.assertTrue((root / 'out/index.html').is_file())
            self.assertFalse((root / 'out/BATCH.json').exists())

    def test_existing_output_and_missing_parent_start_no_worker(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'out').mkdir()
            (root / 'out/keep').write_bytes(b'keep')
            with patch.object(m, '_worker', side_effect=AssertionError('WORKER_EXECUTED')):
                for output in [root / 'out', root / 'missing/out']:
                    with self.assertRaises(m.BatchError):
                        m.run_batch([root / 'missing.json'], output)
            self.assertEqual((root / 'out/keep').read_bytes(), b'keep')

    def test_worker_timeout_is_failure_not_input_rejection(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(m.subprocess, 'run', side_effect=subprocess.TimeoutExpired('synthetic-worker', 120)), self.assertRaises(m.BatchError) as caught:
                m.run_batch([ROOT / 'examples/synthetic_resumed_v1.json'], root / 'out')
            self.assertEqual(caught.exception.code, 'BATCH_WORKER_TIMEOUT')
            self.assertFalse((root / 'out/BATCH.json').exists())

    def test_cli_help_unknown_fallback_and_duplicate_input_fail(self):
        self.module()
        self.assertEqual(self.cli('--help').returncode, 0)
        self.assertEqual(self.cli('--rate-budget', '0').returncode, 2)
        self.assertEqual(self.cli('--inp', 'x').returncode, 2)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.cli('--input', root / 'x.json', '--input', root / 'x.json', '--output', root / 'out')
            self.assertEqual(result.returncode, 2)
            self.assertIn(b'BATCH_DUPLICATE_INPUT', result.stderr)
            self.assertFalse((root / 'out').exists())

    def test_undecodable_input_ancestor_and_output_path_reject_before_publication(self):
        self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = root / 'non_utf8_\udcff'
            bad.mkdir()
            for source, output in [(bad / 'absent.json', root / 'out'), (root / 'absent.json', bad / 'out')]:
                with self.subTest(output=repr(output)):
                    result = self.cli('--input', source, '--output', output)
                    self.assertEqual(result.returncode, 2, result.stderr.decode(errors='replace'))
                    self.assertIn(b'BATCH_PATH_ENCODING', result.stderr)
                    self.assertNotIn(b'Traceback', result.stderr)
                    self.assertFalse(output.exists())
