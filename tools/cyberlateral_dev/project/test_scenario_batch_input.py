"""Batch preflight owns bytes, rejects paths/resources before any worker work."""

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scenario_fixture import document, encode
from v1_helpers import ROOT


class BatchInputTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_batch_input.py').is_file(), 'Missing batch preflight')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_batch_input')

    def test_owned_bytes_and_duplicate_ids_remain_separate(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = encode(document())
            paths = [root / n for n in ['b.json', 'a.json']]
            for p in paths:
                p.write_bytes(raw)
            items = m.prepare_batch(paths, root / 'out')
            paths[0].write_bytes(b'changed')
            self.assertEqual([i.label for i in items], ['b.json', 'a.json'])
            self.assertEqual([i.raw for i in items], [raw, raw])
            self.assertEqual([i.spec.scenario_id for i in items], ['R31_test', 'R31_test'])
            self.assertFalse((root / 'out').exists())

    def test_output_rejections_happen_before_any_input_read(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'keep').write_bytes(b'keep')
            (root / 'link').symlink_to(root / 'absent')
            cases = [(root / 'keep', 'BATCH_OUTPUT_EXISTS'), (root / 'link', 'BATCH_OUTPUT_EXISTS'),
                     (root / 'missing/out', 'BATCH_OUTPUT_PARENT'), (ROOT / 'new-batch-out', 'BATCH_OUTPUT_LOCATION'),
                     (root / 'out', 'BATCH_OUTPUT_LOCATION')]
            with patch.object(m, '_read', side_effect=AssertionError('INPUT_READ')):
                for output, code in cases:
                    with self.subTest(code=code), self.assertRaises(m.BatchError) as caught:
                        m.prepare_batch([root / 'out/input.json'], output)
                    self.assertEqual(caught.exception.code, code)
            self.assertEqual((root / 'keep').read_bytes(), b'keep')

    def test_counts_and_duplicate_paths_reject_without_reads(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(m, '_read', side_effect=AssertionError('INPUT_READ')):
                for paths, code in [([], 'BATCH_INPUT_COUNT'), ([root / f'{i}.json' for i in range(33)], 'BATCH_INPUT_COUNT'),
                                    ([root / 'a.json', root / './a.json'], 'BATCH_DUPLICATE_INPUT')]:
                    with self.subTest(code=code), self.assertRaises(m.BatchError) as caught:
                        m.prepare_batch(paths, root / 'out')
                    self.assertEqual(caught.exception.code, code)

    def test_invalid_files_recorded_individually_with_no_model_import(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'bad.json').write_bytes(b'{')
            (root / 'valid.json').write_bytes(encode(document()))
            (root / 'dir.json').mkdir()
            (root / 'link.json').symlink_to(root / 'valid.json')
            os.mkfifo(root / 'fifo.json')
            names = ['bad.json', 'missing.json', 'dir.json', 'link.json', 'fifo.json', 'valid.json']
            with patch('builtins.__import__', wraps=__import__) as imports:
                items = m.prepare_batch([root / n for n in names], root / 'out')
            self.assertEqual([i.rejection_code for i in items], ['SCENARIO_JSON'] + ['SCENARIO_INPUT_FILE'] * 4 + [None])
            self.assertEqual(items[0].raw, b'{')
            self.assertIsNone(items[1].digest)
            self.assertFalse(any(c.args[0].startswith(('cyberlateral_dev', 'openpilot', 'opendbc')) for c in imports.call_args_list))

    def test_oversize_has_no_full_digest_or_snapshot(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'large.json').write_bytes(b' ' * (1048576 + 1))
            item = m.prepare_batch([root / 'large.json'], root / 'out')[0]
            self.assertEqual(item.rejection_code, 'SCENARIO_SIZE')
            self.assertIsNone(item.raw)
            self.assertIsNone(item.digest)

    def test_unknown_rate_and_late_invalid_sample_reject_whole_file(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            values = [document(), document(2)]
            values[0]['rate_budget_per_s'] = 0.0
            values[1]['samples'][-1]['request'] = 2.0
            paths = []
            for i, value in enumerate(values):
                path = root / f'{i}.json'
                path.write_bytes(encode(value))
                paths.append(path)
            self.assertEqual([i.rejection_code for i in m.prepare_batch(paths, root / 'out')], ['SCENARIO_KEYS', 'SCENARIO_DOMAIN'])

    def test_aggregate_steps_cap_and_exact_boundary(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = []
            for i in range(3):
                path = root / f'{i}.json'
                path.write_bytes(encode(document(4096 if i < 2 else 1)))
                paths.append(path)
            self.assertEqual(sum(len(i.spec.samples) for i in m.prepare_batch(paths[:2], root / 'out')), 8192)
            with self.assertRaises(m.BatchError) as caught:
                m.prepare_batch(paths, root / 'out')
            self.assertEqual(caught.exception.code, 'BATCH_SAMPLE_COUNT')
            self.assertFalse((root / 'out').exists())

    def test_32_rejected_files_are_not_silently_dropped(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = m.prepare_batch([root / f'{i}.json' for i in range(32)], root / 'out')
            self.assertEqual(len(items), 32)
            self.assertTrue(all(i.rejection_code == 'SCENARIO_INPUT_FILE' for i in items))
