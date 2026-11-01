"""Owned batch validation catches rehashed contradictions and unsafe filesystem input."""

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scenario_compare_fixture import edit_batch, manifest, refresh, write_batch
from scenario_report_fixture import canonical
from v1_helpers import ROOT


class CompareInputTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_compare_input.py').is_file(), 'Missing R34 saved-batch reader')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_compare_input')

    def test_complete_mixed_and_rejected_owned_records(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            for number, profiles in enumerate([('sign', 'resumed'), ('bad', 'resumed'), ('bad', 'missing')]):
                source = write_batch(Path(tmp) / str(number), profiles)
                result = m.read_batch(source)
                self.assertEqual(result['record']['input_count'], 2)
                self.assertEqual(len(result['cases']), 2)
                if profiles[0] == 'sign':
                    self.assertEqual([r['model_output']['projection']['integer_command'] for r in result['cases'][0]['result']['rows']], [2, -2, 0, 2])
                self.assertEqual(len(result['portable_manifest_sha256']), 64)

    def test_owned_decoder_preserves_existing_reader_behavior_and_checksums(self):
        self.module()
        from scenario_report_fixture import write_bundle

        from integration_tools.scenario_report_data import ReportError, decode_report, read_report

        with tempfile.TemporaryDirectory() as tmp:
            path = write_bundle(Path(tmp) / 'data')
            owned = {p.name: p.read_bytes() for p in path.iterdir()}
            self.assertEqual(decode_report(owned), read_report(path))
            owned['RESULTS.json'] += b' '
            with self.assertRaises(ReportError):
                decode_report(owned)

    def test_root_nested_and_portable_checksums_all_required(self):
        m = self.module()
        for mode in ['root', 'nested', 'portable', 'subset', 'extra']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                source = write_batch(Path(tmp) / 'batch')
                target = {'root': 'index.html', 'nested': 'case-001/data/TRACE.csv', 'portable': 'PORTABLE_SHA256SUMS.txt',
                          'subset': 'RECEIPT.json', 'extra': 'unexpected.txt'}[mode]
                if mode == 'subset':
                    (source / target).unlink()
                else:
                    (source / target).write_bytes(b'changed')
                if mode in ('nested', 'portable', 'subset', 'extra'):
                    edit_batch(source, lambda x: None)
                with self.assertRaises(m.CompareError):
                    m.read_batch(source)

    def test_rehashed_shape_count_order_gate_and_path_contradictions_reject(self):
        m = self.module()
        changes = [lambda x: x.update(total_model_steps=6), lambda x: x.update(completed=True),
                   lambda x: x['cases'][0].update(case_id='case-002'), lambda x: x['cases'][0].update(data='../outside'),
                   lambda x: x['cases'][0].update(input_sha256='0' * 64), lambda x: x['gates'].update(STATIC_EVIDENCE_GATE='PASS'),
                   lambda x: x['cases'][0].update(extra=0), lambda x: x.update(input_count=33)]
        for change in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                source = write_batch(Path(tmp) / 'batch')
                edit_batch(source, change)
                with self.assertRaises(m.CompareError):
                    m.read_batch(source)

    def test_raw_snapshot_must_match_typed_input_not_only_claimed_hash(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            source = write_batch(Path(tmp) / 'batch')
            raw = json.loads((source / 'inputs/case-001.json').read_bytes())
            raw['samples'][0]['request'] = 0.5
            (source / 'inputs/case-001.json').write_bytes(canonical(raw))
            refresh(source)
            with self.assertRaises(m.CompareError):
                m.read_batch(source)

    def test_rehashed_saved_report_view_disagreement_rejects(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            source = write_batch(Path(tmp) / 'batch')
            report = source / 'case-001/report'
            value = json.loads((report / 'VIEW.json').read_bytes())
            value['rows'][0]['final_command'] = 9
            (report / 'VIEW.json').write_bytes(canonical(value))
            (report / 'SHA256SUMS.txt').write_bytes(manifest({p.name: p.read_bytes() for p in report.iterdir() if p.name != 'SHA256SUMS.txt'}))
            edit_batch(source, lambda x: None)
            with self.assertRaises(m.CompareError):
                m.read_batch(source)

    def test_root_member_directory_symlinks_and_fifo_reject_without_following(self):
        m = self.module()
        for mode in ['root', 'member', 'directory', 'fifo']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = write_batch(root / 'batch')
                if mode == 'root':
                    (root / 'link').symlink_to(source)
                    source = root / 'link'
                elif mode == 'directory':
                    (source / 'linked-dir').symlink_to(root)
                else:
                    path = source / 'case-001/producer.log'
                    path.unlink()
                    if mode == 'member':
                        path.symlink_to('/dev/zero')
                    else:
                        os.mkfifo(path)
                with self.assertRaises(m.CompareError):
                    m.read_batch(source)

    def test_resource_limits_reject_before_unbounded_read(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            source = write_batch(Path(tmp) / 'batch')
            for name, value in [('MAX_FILE_BYTES', 128), ('MAX_TOTAL_BYTES', 1024), ('MAX_MEMBERS', 4)]:
                with self.subTest(name=name), patch.object(m, name, value), self.assertRaises(m.CompareError) as error:
                    m.read_batch(source)
                self.assertEqual(error.exception.code, 'COMPARE_SIZE')

    def test_noncanonical_duplicate_and_deep_json_reject(self):
        m = self.module()
        for raw in [b' {}\n', b'{"schema_version":1,"schema_version":1}\n', b'[' * 65 + b'0' + b']' * 65]:
            with tempfile.TemporaryDirectory() as tmp:
                source = write_batch(Path(tmp) / 'batch')
                (source / 'BATCH.json').write_bytes(raw)
                edit_manifest = {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob('*')
                                 if p.is_file() and p != source / 'SHA256SUMS.txt'}
                (source / 'SHA256SUMS.txt').write_bytes(manifest(edit_manifest))
                with self.assertRaises(m.CompareError):
                    m.read_batch(source)

    def test_batch_producer_metadata_is_hashed_never_followed(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            source = write_batch(Path(tmp) / 'batch', ('bad',))
            first = m.read_batch(source)
            receipt = json.loads((source / 'RECEIPT.json').read_bytes())
            receipt['observed_source_hashes']['integration_tools/historical_only.py'] = '1' * 64
            (source / 'RECEIPT.json').write_bytes(canonical(receipt))
            edit_batch(source, lambda x: None)
            second = m.read_batch(source)
            self.assertIn('batch_producer_identity_sha256', first, 'Missing batch producer metadata identity')
            self.assertNotEqual(first['batch_producer_identity_sha256'], second['batch_producer_identity_sha256'])
            self.assertFalse((ROOT / 'integration_tools/historical_only.py').exists())
