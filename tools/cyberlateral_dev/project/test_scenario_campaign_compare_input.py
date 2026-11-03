"""R44 must reject malformed saved evidence before any comparison publication."""

import importlib
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scenario_campaign_compare_fixture import copy_campaign, edit, real_campaign, rehash_all, sha
from v1_helpers import ROOT


class CampaignCompareInputTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_campaign_compare_input.py').is_file(), 'Missing R44 reader')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_campaign_compare_input')

    def test_complete_real_two_seed_snapshot_preserves_bytes_and_order(self):
        m = self.module()
        source = real_campaign()
        before = {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*') if p.is_file()}
        result = m.read_campaign(source)
        self.assertEqual(result['record']['parameters'], {'seeds': [42, 43], 'cases': 1, 'steps': 16})
        self.assertEqual(result['record']['status'], 'MATCH')
        self.assertEqual([row['record']['parameters']['seed'] for row in result['runs']], [42, 43])
        self.assertEqual([row['batch']['record']['total_model_steps'] for row in result['runs']], [16, 16])
        self.assertEqual(result['hashes'], before)
        self.assertEqual(before, {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*') if p.is_file()})

    def test_rehashed_root_counts_parameters_status_order_and_paths_reject(self):
        m = self.module()
        changes = [lambda r: r.update(model_steps=True), lambda r: r.update(reference_steps=-1),
                   lambda r: r.update(expected_samples=31), lambda r: r.update(status='PASS'),
                   lambda r: r['parameters'].update(seeds=[42, 42]), lambda r: r['parameters'].update(seeds=[True]),
                   lambda r: r['parameters'].update(seeds=[{}]), lambda r: r['parameters'].update(steps=15),
                   lambda r: r['status_counts'].update(MATCH=1), lambda r: r['runs'].reverse(),
                   lambda r: r['runs'][0].update(exploration='../../never-open'),
                   lambda r: r['runs'][0].update(record_sha256='0' * 64), lambda r: r.update(unexpected=0)]
        for change in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = copy_campaign(Path(tmp) / 'input')
                edit(root, 'CAMPAIGN.json', change)
                with self.assertRaisesRegex(m.CampaignCompareError, 'CAMPAIGN_COMPARE_RECORD'):
                    m.read_campaign(root)

    def test_rehashed_source_gates_identity_findings_and_child_semantics_reject(self):
        m = self.module()
        changes = [('CAMPAIGN.json', lambda r: r['gates'].update(actual_r=0)),
                   ('CAMPAIGN.json', lambda r: r.update(observed_source_identity={})),
                   ('CAMPAIGN.json', lambda r: r['observed_source_identity']['campaign'].clear()),
                   ('CAMPAIGN.json', lambda r: r.update(findings=[{}])),
                   ('runs/seed-001/EXPLORATION.json', lambda r: r.update(time_semantics='SECONDS')),
                   ('runs/seed-001/EXPLORATION.json', lambda r: r.update(reference_helper_counts={})),
                   ('runs/seed-001/workflow/batch/BATCH.json', lambda r: r.update(total_model_steps=True)),
                   ('runs/seed-001/workflow/reference/case-001/REFERENCE_CHECK.json', lambda r: r.update(status='DIFFERENT'))]
        for name, change in changes:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = copy_campaign(Path(tmp) / 'input')
                edit(root, name, change)
                with self.assertRaises(m.CampaignCompareError):
                    m.read_campaign(root)

    def test_hashes_extra_missing_payload_and_portable_only_never_qualify(self):
        m = self.module()
        for kind in ['corrupt', 'extra', 'missing', 'portable']:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = copy_campaign(Path(tmp) / 'input')
                if kind == 'corrupt':
                    (root / 'runs/seed-001/workflow/batch/case-001/data/TRACE.csv').write_bytes(b'corrupt')
                elif kind == 'extra':
                    (root / 'extra.txt').write_bytes(b'extra')
                    rehash_all(root)
                elif kind == 'missing':
                    (root / 'runs/seed-001/generated/case-001.json').unlink()
                    rehash_all(root)
                else:
                    shutil.rmtree(root / 'runs')
                    rehash_all(root)
                with self.assertRaises(m.CampaignCompareError):
                    m.read_campaign(root)

    def test_root_ancestor_file_directory_links_and_fifo_reject(self):
        m = self.module()
        for kind in ['root', 'ancestor', 'file', 'directory', 'fifo']:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                source = copy_campaign(base / 'input')
                target = source
                if kind == 'root':
                    target = base / 'link'
                    target.symlink_to(source, target_is_directory=True)
                elif kind == 'ancestor':
                    (base / 'link').symlink_to(base, target_is_directory=True)
                    target = base / 'link/input'
                elif kind == 'file':
                    path = source / 'CAMPAIGN.json'
                    path.rename(base / 'record')
                    path.symlink_to(base / 'record')
                elif kind == 'directory':
                    (source / 'runs').rename(base / 'runs')
                    (source / 'runs').symlink_to(base / 'runs', target_is_directory=True)
                else:
                    os.mkfifo(source / 'fifo')
                with self.assertRaises(m.CampaignCompareError):
                    m.read_campaign(target)

    def test_file_and_total_count_caps_apply_before_schema_traversal(self):
        m = self.module()
        for name, value in [('MAX_FILES', 2), ('MAX_BYTES', 1024)]:
            with self.subTest(name=name), patch.object(m, name, value):
                with self.assertRaises(m.CampaignCompareError):
                    m.read_campaign(real_campaign())
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_campaign(Path(tmp) / 'input')
            with (root / 'too-big').open('wb') as stream:
                stream.truncate(16 * 1024 * 1024 + 1)
            with self.assertRaises(m.CampaignCompareError):
                m.read_campaign(root)

    def test_noncanonical_duplicate_nonobject_and_oversize_root_records_reject(self):
        m = self.module()
        for raw in [b'[]\n', b'{"status":"MATCH","status":"ERROR"}\n', b'{"x":NaN}\n', b' ' * (1048576 + 1)]:
            with self.subTest(raw=raw[:50]), tempfile.TemporaryDirectory() as tmp:
                root = copy_campaign(Path(tmp) / 'input')
                (root / 'CAMPAIGN.json').write_bytes(raw)
                rehash_all(root)
                with self.assertRaises(m.CampaignCompareError):
                    m.read_campaign(root)

    def test_recorded_identity_change_is_metadata_not_current_source_authentication(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_campaign(Path(tmp) / 'input')
            edit(root, 'CAMPAIGN.json',
                 lambda r: r['observed_source_identity']['campaign'].update({'tools/scenario_campaign.py': '0' * 64}))
            result = m.read_campaign(root)
            self.assertEqual(result['record']['observed_source_identity']['campaign']['tools/scenario_campaign.py'], '0' * 64)

    def test_complete_error_and_different_campaigns_remain_visible(self):
        m = self.module()
        for status in ['ERROR', 'DIFFERENT']:
            with self.subTest(status=status):
                result = m.read_campaign(real_campaign(seeds=(42,), status=status))
                self.assertEqual(result['record']['status'], status)
                self.assertEqual(len(result['record']['findings']), 1)
                self.assertEqual(result['record']['findings'][0]['case_status'], status)

    def test_full_workflow_and_validation_contracts_are_not_ignored(self):
        m = self.module()
        workflow = 'runs/seed-001/workflow/WORKFLOW.json'
        validation = 'runs/seed-001/workflow/VALIDATION.json'
        changes = [(workflow, lambda r: r.update(schema_version=99)),
                   (workflow, lambda r: r.update(contract_id='OTHER_CONTRACT')),
                   (workflow, lambda r: r.update(batch_record='missing/BATCH.json')),
                   (workflow, lambda r: r.update(reference_report='missing/reference.json')),
                   (workflow, lambda r: r.update(validation_report='../../never-open')),
                   (workflow, lambda r: r.update(regression_status='DIFFERENT', regression_report='regression/COMPARE.json')),
                   (workflow, lambda r: r.update(renderer_new_model_executions=1)),
                   (validation, lambda r: r.update(cases=[])),
                   (validation, lambda r: r['cases'][0]['validation'].update(accepted=False)),
                   (validation, lambda r: r['cases'][0]['validation'].update(input_raw_sha256='0' * 64))]
        for name, change in changes:
            with self.subTest(name=name, change=change), tempfile.TemporaryDirectory() as tmp:
                root = copy_campaign(Path(tmp) / 'input')
                edit(root, name, change)
                with self.assertRaises(m.CampaignCompareError):
                    m.read_campaign(root)
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_campaign(Path(tmp) / 'input')
            (root / validation).write_bytes(b'not JSON\n')
            rehash_all(root)
            with self.assertRaises(m.CampaignCompareError):
                m.read_campaign(root)
