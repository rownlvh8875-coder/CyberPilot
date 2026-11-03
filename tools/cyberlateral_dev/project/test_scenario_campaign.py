"""R43 must preserve real R42 verdicts, independent seeds and complete evidence."""

import contextlib
import hashlib
import importlib
import io
import json
import runpy
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scenario_compare_fixture import refresh
from scenario_report_fixture import edit_json
from v1_helpers import ROOT


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def rehash(root):
    files = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*')
             if p.is_file() and p != root / 'SHA256SUMS.txt'}
    (root / 'SHA256SUMS.txt').write_bytes(''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n'
                                               for name, raw in sorted(files.items())).encode())


def rehash_all(root):
    # A closed manifest includes its same-directory portable manifest. Update
    # that subset first even when the filesystem enumerates SHA256SUMS first.
    for sums in sorted(root.rglob('*SHA256SUMS.txt'),
                       key=lambda p: (len(p.parts), p.name == 'PORTABLE_SHA256SUMS.txt'), reverse=True):
        if sums.name == 'PORTABLE_SHA256SUMS.txt':
            names = [line.split('  ')[1] for line in sums.read_text().splitlines()]
        else:
            names = [p.relative_to(sums.parent).as_posix() for p in sums.parent.rglob('*') if p.is_file() and p != sums]
        sums.write_bytes(''.join(hashlib.sha256((sums.parent / name).read_bytes()).hexdigest() + '  ' + name + '\n'
                                 for name in sorted(names)).encode())


class CampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        cls.exploration = importlib.import_module('integration_tools.scenario_explore_run')
        cls.scratch = tempfile.TemporaryDirectory(prefix='r43-real-fixtures-')
        cls.addClassCleanup(cls.scratch.cleanup)
        cls.fixtures = Path(cls.scratch.name)
        # Complete real saved results, reused ONLY beneath expensive completed-worker boundaries.
        for seed in [42, 43]:
            cls.exploration.run_exploration(seed, 1, 16, cls.fixtures / str(seed))

    def module(self):
        self.assertTrue((ROOT / 'integration_tools/scenario_campaign_run.py').is_file(), 'Missing campaign runner')
        return importlib.import_module('integration_tools.scenario_campaign_run')

    def check_manifest(self, root):
        files = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        expected = ''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n'
                           for name, raw in sorted(files.items()) if name != 'SHA256SUMS.txt').encode()
        self.assertEqual(files['SHA256SUMS.txt'], expected)
        for path in root.rglob('SHA256SUMS.txt'):
            for line in path.read_text().splitlines():
                digest, name = line.split('  ')
                self.assertEqual(hashlib.sha256((path.parent / name).read_bytes()).hexdigest(), digest)

    def saved_child(self, seed, cases, steps, target):
        self.assertEqual((cases, steps), (1, 16))
        shutil.copytree(self.fixtures / str(seed), target)
        return json.loads((target / 'EXPLORATION.json').read_bytes())

    def test_real_two_seed_match_preserves_order_counts_state_and_gates(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            result = m.run_campaign([43, 42], 1, 16, output)
            self.assertEqual((result['status'], result['model_steps'], result['reference_steps'], result['difference_count'],
                              m.exit_code(result)), ('MATCH', 32, 32, 0, 0))
            self.assertEqual(result['status_counts'], {'MATCH': 2, 'DIFFERENT': 0, 'ERROR': 0})
            self.assertEqual([row['seed'] for row in result['runs']], [43, 42])
            self.assertEqual(result['findings'], [])
            self.assertEqual(result['parameters'], {'seeds': [43, 42], 'cases': 1, 'steps': 16})
            self.assertEqual(result['time_semantics'], 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME')
            self.assertEqual(result['state_scope'], 'INDEPENDENT_PER_SEED_AND_CASE_NO_CROSS_RUN_STATE')
            self.assertEqual((result['gates']['R_BUDGET'], result['gates']['STATIC_EVIDENCE_GATE']), ('UNRESOLVED', 'FAIL'))
            self.assertTrue(all(result['gates'][name] is None for name in ['actual_r', 'T2', 'vehicle_scale']))
            for number, seed in enumerate([43, 42], 1):
                child = output / f'runs/seed-{number:03d}'
                generated = json.loads((child / 'generated/case-001.json').read_bytes())
                self.assertEqual(generated['scenario_id'], f'R42_{seed}_1')
                self.assertEqual(generated['initial_state'], {'index': 0, 'previous_requested': None,
                                                             'previous_applied': 0, 'angle_counter': 0})
                self.assertEqual(result['runs'][number - 1]['record_sha256'],
                                 hashlib.sha256((child / 'EXPLORATION.json').read_bytes()).hexdigest())
            self.assertEqual((output / 'CAMPAIGN.json').read_bytes(), canonical(result))
            self.assertNotIn(tmp, (output / 'CAMPAIGN.json').read_text())
            self.check_manifest(output)

    def test_duplicate_bool_subclass_and_out_of_bounds_parameters_do_no_work(self):
        m = self.module()
        class Integer(int):
            pass
        class Seeds(list):
            pass
        bad = [([], 1, 16), ((42,), 1, 16), (Seeds([42]), 1, 16), ([42, 42], 1, 16),
               ([True], 1, 16), ([Integer(42)], 1, 16), ([-1], 1, 16), ([2**32], 1, 16),
               ([0, 1, 2, 3, 4], 1, 16), ([42], 0, 16), ([42], 17, 16), ([42], True, 16),
               ([42], 1, 15), ([42], 1, 257), ([42], 1, 16.0)]
        with tempfile.TemporaryDirectory() as tmp, patch.object(m.exploration, 'run_exploration',
                                                               side_effect=AssertionError('must not execute')):
            output = Path(tmp) / 'out'
            for args in bad:
                with self.subTest(args=args), self.assertRaisesRegex(m.CampaignError, 'CAMPAIGN_PARAMETERS'):
                    m.run_campaign(*args, output)
                self.assertFalse(output.exists())

    def test_four_distinct_uint32_boundary_seeds_are_supported(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            result = m.run_campaign([0, 42, 43, 2**32 - 1], 1, 16, Path(tmp) / 'out')
            self.assertEqual((result['status'], len(result['runs']), result['model_steps']), ('MATCH', 4, 64))

    def test_existing_dangling_missing_parent_and_component_outputs_reject(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp, patch.object(m.exploration, 'run_exploration',
                                                               side_effect=AssertionError('must not execute')):
            root = Path(tmp)
            (root / 'exists').mkdir()
            (root / 'exists/keep').write_bytes(b'keep')
            (root / 'link').symlink_to(root / 'missing')
            for output in [root / 'exists', root / 'link', root / 'missing/out', ROOT / 'new-r43-output']:
                with self.subTest(output=output), self.assertRaises(m.CampaignError):
                    m.run_campaign([42], 1, 16, output)
            self.assertEqual((root / 'exists/keep').read_bytes(), b'keep')

    def wrong_projection(self, source, output):
        edit_json(source / 'case-001/data', 'RESULTS.json',
                  lambda r: r['rows'][0]['model_output']['projection']['torque_float32'].update(bits_hex='00000000'))
        refresh(source)
        return self.real_check(source, output)

    def test_actual_numerical_difference_preserves_whole_reproducer(self):
        m = self.module()
        self.real_check = m.exploration.workflow.reference.check_batch
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            with patch.object(m.exploration.workflow.reference, 'check_batch', side_effect=self.wrong_projection):
                result = m.run_campaign([42], 1, 16, output)
            self.assertEqual((result['status'], result['difference_count'], m.exit_code(result)), ('DIFFERENT', 1, 1))
            finding = result['findings'][0]
            raw = (output / finding['reproducer']).read_bytes()
            self.assertEqual(raw, (output / 'runs/seed-001/generated/case-001.json').read_bytes())
            self.assertEqual(len(json.loads(raw)['samples']), 16)
            self.assertEqual(finding['first_difference']['field'], 'rows[0].model_output.projection.torque_float32.bits_hex')
            self.check_manifest(output)

    def test_completed_reference_error_outranks_difference_independent_of_order(self):
        m = self.module()
        real_run = m.exploration.run_exploration
        self.real_check = m.exploration.workflow.reference.check_batch

        def run(seed, cases, steps, target):
            if seed == 42:
                worker = m.exploration.workflow.reference.reference
                with patch.object(worker, '_launch', side_effect=worker.ReferenceCheckError('REFERENCE_WORKER_FAILED')):
                    return real_run(seed, cases, steps, target)
            with patch.object(m.exploration.workflow.reference, 'check_batch', side_effect=self.wrong_projection):
                return real_run(seed, cases, steps, target)

        for seeds, statuses in [([42, 43], ['ERROR', 'DIFFERENT']), ([43, 42], ['DIFFERENT', 'ERROR'])]:
            with self.subTest(seeds=seeds), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / 'out'
                with patch.object(m.exploration, 'run_exploration', side_effect=run):
                    result = m.run_campaign(seeds, 1, 16, output)
                self.assertEqual((result['status'], m.exit_code(result)), ('ERROR', 2))
                self.assertEqual(result['status_counts'], {'MATCH': 0, 'DIFFERENT': 1, 'ERROR': 1})
                self.assertEqual((result['model_steps'], result['reference_steps'], result['difference_count']), (32, 16, 1))
                self.assertEqual([row['status'] for row in result['runs']], statuses)
                self.assertEqual([row['seed'] for row in result['runs']], seeds)
                self.assertEqual([f['seed'] for f in result['findings']], seeds)
                self.assertIn('FAILED_WORK_MAY_BE_NONZERO', result['reference_steps_accounting'])
                self.check_manifest(output)

    def test_fatal_second_worker_preserves_first_but_no_campaign_marker(self):
        m = self.module()
        real = m.exploration.run_exploration

        def run(seed, cases, steps, target):
            if seed == 42:
                return real(seed, cases, steps, target)
            batch = m.exploration.workflow.batch
            with patch.object(batch, '_worker', side_effect=batch.BatchError('BATCH_WORKER_FAILED')):
                return real(seed, cases, steps, target)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            with patch.object(m.exploration, 'run_exploration', side_effect=run):
                with self.assertRaisesRegex(m.CampaignError, 'CAMPAIGN_STAGE_FAILED'):
                    m.run_campaign([42, 43], 1, 16, output)
            self.assertTrue((output / 'runs/seed-001/EXPLORATION.json').is_file())
            self.assertTrue((output / 'runs/seed-002/generated/case-001.json').is_file())
            self.assertFalse((output / 'CAMPAIGN.json').exists())

    def test_rehashed_malformed_counts_identity_gates_and_parameters_reject(self):
        m = self.module()
        changes = [lambda r: r.update(model_steps=True), lambda r: r.update(reference_steps=-1),
                   lambda r: r.update(model_steps=17), lambda r: r.update(status='PASS'),
                   lambda r: r['parameters'].update(seed=43), lambda r: r['gates'].update(actual_r=0),
                   lambda r: r.update(observed_source_identity={}), lambda r: r.update(findings=[{}])]
        for change in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / 'out'

                def child(seed, cases, steps, target, change=change):
                    record = self.saved_child(seed, cases, steps, target)
                    change(record)
                    (target / 'EXPLORATION.json').write_bytes(canonical(record))
                    rehash(target)
                    return record

                with patch.object(m.exploration, 'run_exploration', side_effect=child):
                    with self.assertRaisesRegex(m.CampaignError, 'CAMPAIGN_STAGE_RECORD'):
                        m.run_campaign([42], 1, 16, output)
                self.assertFalse((output / 'CAMPAIGN.json').exists())

    def test_missing_extra_or_linked_child_evidence_cannot_be_rehashed_into_success(self):
        m = self.module()
        for change in ['extra', 'missing', 'linked']:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / 'out'

                def child(seed, cases, steps, target, change=change):
                    record = self.saved_child(seed, cases, steps, target)
                    if change == 'extra':
                        (target / 'extra').write_bytes(b'not part of R42')
                        rehash(target)
                    elif change == 'missing':
                        (target / 'generated/case-001.json').unlink()
                        rehash(target)
                    else:
                        original = target / 'generated'
                        original.rename(target / 'original')
                        original.symlink_to(target / 'original', target_is_directory=True)
                    return record

                with patch.object(m.exploration, 'run_exploration', side_effect=child):
                    with self.assertRaises(m.CampaignError):
                        m.run_campaign([42], 1, 16, output)
                self.assertFalse((output / 'CAMPAIGN.json').exists())

    def test_noncanonical_duplicate_and_nonobject_saved_records_reject(self):
        m = self.module()
        for raw in [b'[]\n', b'null\n', b'{"status":"MATCH","status":"ERROR"}\n', b'{"value":NaN}\n']:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / 'out'

                def child(seed, cases, steps, target, raw=raw):
                    record = self.saved_child(seed, cases, steps, target)
                    (target / 'EXPLORATION.json').write_bytes(raw)
                    rehash(target)
                    return record

                with patch.object(m.exploration, 'run_exploration', side_effect=child):
                    with self.assertRaisesRegex(m.CampaignError, 'CAMPAIGN_STAGE_RECORD'):
                        m.run_campaign([42], 1, 16, output)
                self.assertFalse((output / 'CAMPAIGN.json').exists())

    def test_nonfinite_in_memory_child_result_is_a_bounded_stage_error(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'

            def child(seed, cases, steps, target):
                record = self.saved_child(seed, cases, steps, target)
                record['model_steps'] = float('nan')
                return record

            with patch.object(m.exploration, 'run_exploration', side_effect=child):
                try:
                    m.run_campaign([42], 1, 16, output)
                except m.CampaignError as error:
                    self.assertEqual(error.code, 'CAMPAIGN_STAGE_RECORD')
                except Exception as error:
                    self.fail('Malformed in-memory child escaped as ' + type(error).__name__)
                else:
                    self.fail('Nonfinite child was accepted')
            self.assertFalse((output / 'CAMPAIGN.json').exists())

    def test_rehashed_lower_reports_batch_counts_and_reference_bindings_are_not_match(self):
        m = self.module()
        mutations = [
            ('workflow/reference/case-001/REFERENCE_CHECK.json', lambda r: r.update(status='DIFFERENT', difference_count=1)),
            ('workflow/batch/BATCH.json', lambda r: r.update(total_model_steps=True)),
            ('workflow/reference/BATCH_REFERENCE_CHECK.json', lambda r: r.update(input_root_manifest_sha256='0' * 64)),
            ('workflow/reference/BATCH_REFERENCE_CHECK.json', lambda r: r.update(input_portable_manifest_sha256='0' * 64)),
            ('workflow/reference/BATCH_REFERENCE_CHECK.json', lambda r: r.update(reference_identity={})),
            ('workflow/reference/case-001/REFERENCE_CHECK.json', lambda r: r.update(input_source_hashes={})),
            ('workflow/reference/case-001/REFERENCE_CHECK.json', lambda r: r.update(reference_identity={})),
            ('workflow/WORKFLOW.json', lambda r: r.update(observed_dev_source_hashes={})),
        ]
        for member, mutate in mutations:
            with self.subTest(member=member, mutate=mutate), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / 'out'

                def child(seed, cases, steps, target, member=member, mutate=mutate):
                    record = self.saved_child(seed, cases, steps, target)
                    path = target / member
                    altered = json.loads(path.read_bytes())
                    mutate(altered)
                    path.write_bytes(canonical(altered))
                    rehash_all(target)
                    return record

                with patch.object(m.exploration, 'run_exploration', side_effect=child):
                    with self.assertRaisesRegex(m.CampaignError, 'CAMPAIGN_STAGE_RECORD'):
                        m.run_campaign([42], 1, 16, output)
                self.assertFalse((output / 'CAMPAIGN.json').exists())

    def test_initial_and_late_inherited_source_failures_are_bounded_cli_rejections(self):
        m = self.module()
        frontend = runpy.run_path(str(ROOT / 'tools/scenario_campaign.py'))['main']
        identity = m._source_identity()
        original_read = Path.read_bytes

        def unavailable(path):
            if path == ROOT / 'IMPORTED_ARTIFACT.json':
                raise OSError('controlled missing source observation')
            return original_read(path)

        for late in [False, True]:
            with self.subTest(late=late), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / 'out'
                stdout, stderr = io.StringIO(), io.StringIO()
                failure = m.exploration.workflow.reference.reference.ReferenceCheckError('REFERENCE_SOURCE_IDENTITY')
                control = (patch.object(m, '_source_identity', side_effect=[identity, failure]) if late
                           else patch.object(Path, 'read_bytes', new=unavailable))
                with control, contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    try:
                        code = frontend(['--seed', '42', '--cases', '1', '--steps', '16', '--output', str(output)])
                    except Exception as error:
                        self.fail('Source failure escaped CLI as ' + type(error).__name__)
                self.assertEqual((code, stdout.getvalue(), stderr.getvalue()),
                                 (2, '', 'REJECTED: CAMPAIGN_SOURCE_IDENTITY\n'))
                self.assertFalse((output / 'CAMPAIGN.json').exists())
                self.assertEqual((output / 'runs/seed-001/EXPLORATION.json').exists(), late)

    def test_portable_rehash_is_independent_of_filesystem_order(self):
        m = self.module()
        original_scan = Path.rglob

        def closed_before_portable(path, pattern):
            values = list(original_scan(path, pattern))
            if pattern == '*SHA256SUMS.txt':
                values.sort(key=lambda p: (-len(p.parts), p.name == 'PORTABLE_SHA256SUMS.txt'))
            return iter(values)

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'child'
            self.saved_child(42, 1, 16, target)
            path = target / 'workflow/batch/BATCH.json'
            value = json.loads(path.read_bytes())
            value['total_model_steps'] = True
            path.write_bytes(canonical(value))
            with patch.object(Path, 'rglob', new=closed_before_portable):
                rehash_all(target)
            try:
                m.verify_manifests(target, m.capture_tree(target))
            except m.CampaignError:
                self.fail('Negative-control checksum fixture depends on filesystem enumeration order')

    def test_late_source_or_earlier_child_mutation_prevents_publication(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            identity = m._source_identity()
            with patch.object(m, '_source_identity', side_effect=[identity, {'changed': '0' * 64}]):
                with self.assertRaisesRegex(m.CampaignError, 'CAMPAIGN_SOURCE_CHANGED'):
                    m.run_campaign([42], 1, 16, root / 'source')
            real = m.exploration.run_exploration

            def child(seed, cases, steps, target):
                record = real(seed, cases, steps, target)
                if seed == 43:
                    first = target.parent / 'seed-001'
                    (first / 'generated/case-001.json').write_bytes(b'changed late')
                    rehash(first)
                return record

            with patch.object(m.exploration, 'run_exploration', side_effect=child):
                with self.assertRaisesRegex(m.CampaignError, 'CAMPAIGN_CHILD_CHANGED'):
                    m.run_campaign([42, 43], 1, 16, root / 'child')
            self.assertFalse((root / 'source/CAMPAIGN.json').exists())
            self.assertFalse((root / 'child/CAMPAIGN.json').exists())

    def test_repeat_portable_records_match_but_private_manifest_is_not_claimed_equal(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as tmp:
            first, second = [Path(tmp) / name for name in ['one', 'two']]
            one = m.run_campaign([42, 43], 1, 16, first)
            two = m.run_campaign([42, 43], 1, 16, second)
            self.assertEqual(one, two)
            for name in ['CAMPAIGN.json', 'SUMMARY_KO.md', 'runs/seed-001/EXPLORATION.json',
                         'runs/seed-002/GENERATION.json', 'runs/seed-001/generated/case-001.json']:
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
            self.assertNotEqual((first / 'SHA256SUMS.txt').read_bytes(), (second / 'SHA256SUMS.txt').read_bytes())


if __name__ == '__main__':
    unittest.main()
