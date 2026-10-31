"""Source-to-table mapping, snapshot identity and zero-compute audit behavior."""

import builtins
import contextlib
import csv
import hashlib
import importlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from v1_helpers import ROOT, package_feature

EXPECTED_COLUMNS = (
    'scenario_id offset invocation_index sequence_id seed_origin source_request source_request_hex lat_active driver driver_hex '
    'angle_deg angle_deg_hex STEER_MAX STEER_DELTA_UP STEER_DELTA_DOWN STEER_DRIVER_ALLOWANCE STEER_DRIVER_FACTOR '
    'STEER_DRIVER_MULTIPLIER previous_requested previous_applied angle_counter quantized_integer driver_clip_result rate_clip_result '
    'limited_command final_command normalized_expression normalized_expression_hex steer_request next_index next_previous_requested '
    'next_previous_applied next_angle_counter source_result_sha256 custody_claim precision_claim time_semantics'
).split()


class HandoffAuditTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT / 'integration_tools/handoff_audit.py').is_file(), 'Missing planned read-only handoff audit')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.handoff_audit')

    def sources(self, root):
        m = self.module()
        package_feature()
        record = importlib.import_module('integration_tools.handoff_lifecycle').run_lifecycle()
        record['execution_environment'] = {'isolated': True, 'installed_package': True, 'numpy_available': False, 'forbidden_modules_loaded': []}
        paths = [root / 'lifecycle_one', root / 'lifecycle_two']
        self.write_sources(m, paths, record)
        return record, paths

    def write_sources(self, m, paths, record):
        raw = m.canonical(record)
        for path in paths:
            path.mkdir(exist_ok=True)
            (path / 'RESULTS.json').write_bytes(raw)
            (path / 'SHA256SUMS.txt').write_text(hashlib.sha256(raw).hexdigest() + '  RESULTS.json\n')

    def manifest(self, path):
        files = [name for name in ['AUDIT.json', 'EXECUTION.json', 'SUMMARY_KO.md', 'audit.csv'] if (path / name).is_file()]
        (path / 'SHA256SUMS.txt').write_text(''.join(hashlib.sha256((path / name).read_bytes()).hexdigest() + '  ' + name + '\n' for name in files))

    def test_complete_source_to_table_mapping(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source, paths = self.sources(root)
            target = root / 'report'
            m.write_audit(*paths, target)
            audit = json.loads((target / 'AUDIT.json').read_bytes())
            table = list(csv.DictReader(io.StringIO((target / 'audit.csv').read_text())))
            self.assertEqual(audit['columns'], EXPECTED_COLUMNS)
            self.assertEqual((audit['scenario_count'], audit['row_count'], len(table)), (7, 112, 112))
            self.assertEqual(audit['input_lifecycle_sha256'], hashlib.sha256((paths[0] / 'RESULTS.json').read_bytes()).hexdigest())
            expected = []
            for row in source['baseline']['scenarios']:
                for offset, item in enumerate(row['prepared']):
                    sample, state, output = item['sample'], item['state'], row['result']['outputs'][offset]
                    downstream, quant = output['trace']['downstream'], output['trace']['quantization']
                    expected.append({
                        'scenario_id': row['id'], 'offset': offset, 'invocation_index': sample['index'], 'sequence_id': item['sequence_id'],
                        'seed_origin': row['seed_origin'], 'source_request': sample['request'], 'source_request_hex': sample['request'].hex(),
                        'lat_active': sample['lat_active'], 'driver': sample['driver'], 'driver_hex': sample['driver'].hex(),
                        'angle_deg': sample['angle_deg'], 'angle_deg_hex': sample['angle_deg'].hex(),
                        'STEER_MAX': sample['limits']['STEER_MAX'], 'STEER_DELTA_UP': sample['limits']['STEER_DELTA_UP'],
                        'STEER_DELTA_DOWN': sample['limits']['STEER_DELTA_DOWN'], 'STEER_DRIVER_ALLOWANCE': sample['limits']['STEER_DRIVER_ALLOWANCE'],
                        'STEER_DRIVER_FACTOR': sample['limits']['STEER_DRIVER_FACTOR'], 'STEER_DRIVER_MULTIPLIER': sample['limits']['STEER_DRIVER_MULTIPLIER'],
                        'previous_requested': state['previous_requested'], 'previous_applied': state['previous_applied'], 'angle_counter': state['angle_counter'],
                        'quantized_integer': quant['integer_command'], 'driver_clip_result': downstream['driver_clip']['result']['value'],
                        'rate_clip_result': downstream['rate_clip']['result']['value'], 'limited_command': downstream['limited_command'],
                        'final_command': downstream['final_command'], 'normalized_expression': output['projection']['normalized_expression'],
                        'normalized_expression_hex': output['projection']['normalized_expression_hex'], 'steer_request': output['steer_request'],
                        'next_index': output['next_state']['index'], 'next_previous_requested': output['next_state']['previous_requested'],
                        'next_previous_applied': output['next_state']['previous_applied'], 'next_angle_counter': output['next_state']['angle_counter'],
                        'source_result_sha256': row['result_sha256'], 'custody_claim': item['custody_claim'],
                        'precision_claim': item['precision_claim'], 'time_semantics': item['time_semantics'],
                    })
            self.assertEqual(m.canonical(audit['rows']), m.canonical(expected))
            for actual, want in zip(table, expected, strict=True):
                self.assertEqual(actual, {k: v if isinstance(v, str) else json.dumps(v, allow_nan=False) for k, v in want.items()})
            ramp = next(r for r in audit['rows'] if r['scenario_id'] == 'ramp' and r['offset'] == 0)
            self.assertEqual([ramp[k] for k in ['previous_requested', 'previous_applied', 'angle_counter', 'quantized_integer', 'driver_clip_result',
                                              'rate_clip_result', 'limited_command', 'final_command', 'normalized_expression', 'next_index',
                                              'next_previous_requested', 'next_previous_applied', 'next_angle_counter']],
                             [None, 0, 0, 16, 16, 2, 2, 2, 0.125, 1, 16, 2, 0])
            self.assertEqual(audit['gates'], source['gates'])

    def test_signed_zero_and_declared_seed_labels(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            _, paths = self.sources(root)
            m.write_audit(*paths, root / 'report')
            rows = list(csv.DictReader(io.StringIO((root / 'report/audit.csv').read_text())))
            zero = next(r for r in rows if r['scenario_id'] == 'signed-zero' and r['offset'] == '0')
            self.assertEqual((zero['source_request'], zero['source_request_hex'], zero['previous_requested']), ('-0.0', '-0x0.0p+0', 'null'))
            history = next(r for r in rows if r['scenario_id'] == 'history-scale')
            self.assertEqual((history['invocation_index'], history['normalized_expression']), ('1', '19.0'))
            self.assertEqual(history['seed_origin'], 'REGISTERED_SYNTHETIC_SEED_NOT_OBSERVED_PREHISTORY')
            self.assertEqual(history['custody_claim'], 'SYNTHETIC_DECLARATION_ONLY')
            self.assertEqual(history['time_semantics'], 'INVOCATION_ORDER_ONLY_NOT_ELAPSED_TIME')

    def test_no_model_or_extractor_work(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            _, paths = self.sources(root)
            p = package_feature()
            b = importlib.import_module('integration_tools.message_boundary')
            original = builtins.__import__

            def forbid(name, *args, **kwargs):
                if name.split('.')[0] in {'cyberlateral_dev', 'openpilot', 'opendbc', 'cereal', 'capnp', 'numpy'}:
                    raise AssertionError('NO_MODEL_OR_NATIVE_IMPORT')
                return original(name, *args, **kwargs)

            with patch.object(builtins, '__import__', side_effect=forbid), patch.object(p, 'step', side_effect=AssertionError('NO_STEP')), \
                    patch.object(p, 'simulate', side_effect=AssertionError('NO_SIMULATE')), patch.object(b, 'extract_synthetic_message', side_effect=AssertionError('NO_EXTRACT')):
                m.write_audit(*paths, root / 'report')
            audit = json.loads((root / 'report/AUDIT.json').read_bytes())
            self.assertEqual(audit['report_execution_counts'], {'model_steps': 0, 'extractor_calls': 0, 'F61': 0, 'r_calculations': 0, 'dt_calculations': 0})
            self.assertEqual(audit['source_execution_counts'], {'model_steps': 9010, 'extractor_calls': 9010})

    def test_reject_poisoned_input_before_output(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source, paths = self.sources(root)
            for index, change in enumerate([
                lambda r: r['gates'].update(STATIC_EVIDENCE_GATE='PASS'),
                lambda r: r['split_runs'][0]['cuts'].pop(),
                lambda r: r['execution_environment'].update(isolated=False),
                lambda r: r['baseline']['scenarios'][0]['prepared'][0]['state'].update(previous_applied=99),
            ]):
                bad = deepcopy(source)
                change(bad)
                self.write_sources(m, paths, bad)
                target = root / str(index)
                with self.assertRaises(ValueError):
                    m.write_audit(*paths, target)
                self.assertFalse(target.exists())
            self.write_sources(m, paths, source)
            (paths[0] / 'SHA256SUMS.txt').write_bytes(b'BAD\n')
            with self.assertRaises(ValueError):
                m.write_audit(*paths, root / 'bad_manifest')
            self.assertFalse((root / 'bad_manifest').exists())

    def test_existing_output_and_failed_publication(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            _, paths = self.sources(root)
            targets = [root / 'file', root / 'directory', root / 'dangling']
            targets[0].write_bytes(b'KEEP')
            targets[1].mkdir()
            targets[2].symlink_to(root / 'absent', target_is_directory=True)
            with patch.object(m, 'read_lifecycle_pair', side_effect=AssertionError('NO_INPUT_READ')):
                for target in targets:
                    with self.assertRaises(FileExistsError):
                        m.write_audit(*paths, target)
                for flag in ['--data', '--native', '--r', '--dt', '--source-root']:
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                        m.main(['--first', str(paths[0]), '--second', str(paths[1]), '--output', str(root / 'new'), flag, 'UNSUPPORTED'])
            original = Path.open

            def fail_manifest(path, *args, **kwargs):
                if path.name == 'SHA256SUMS.txt' and args and args[0] == 'xb':
                    raise OSError('SYNTHETIC_MANIFEST_FAILURE')
                return original(path, *args, **kwargs)

            with patch.object(Path, 'open', fail_manifest), self.assertRaises(OSError):
                m.write_audit(*paths, root / 'failed')
            self.assertFalse((root / 'failed/AUDIT.json').exists())
            self.assertEqual(targets[0].read_bytes(), b'KEEP')

    def test_report_pair_rejects_tampering(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            _, paths = self.sources(root)
            reports = [root / 'one', root / 'two']
            for target in reports:
                m.write_audit(*paths, target)
                (target / 'EXECUTION.json').write_bytes(m.canonical({'isolated': True, 'forbidden_modules_loaded': []}))
                self.manifest(target)
            self.assertEqual(m.audit_pair_summary(*reports, *paths)['row_count'], 112)
            original = {p.name: p.read_bytes() for p in reports[0].iterdir()}
            for mutation in ['row', 'columns', 'csv', 'summary', 'execution', 'gate', 'seed', 'manifest', 'missing', 'extra', 'noncanonical']:
                for target in reports:
                    for name, raw in original.items():
                        (target / name).write_bytes(raw)
                    (target / 'extra').unlink(missing_ok=True)
                    audit = json.loads(original['AUDIT.json'])
                    if mutation == 'row':
                        audit['rows'][4]['previous_requested'] = 1
                    elif mutation == 'columns':
                        audit['columns'].reverse()
                    elif mutation == 'gate':
                        audit['gates']['STATIC_EVIDENCE_GATE'] = 'PASS'
                    elif mutation == 'seed':
                        audit['rows'][-1]['seed_origin'] = 'OBSERVED_PREHISTORY'
                    if mutation in {'row', 'columns', 'gate', 'seed'}:
                        (target / 'AUDIT.json').write_bytes(m.canonical(audit))
                    elif mutation == 'csv':
                        (target / 'audit.csv').write_bytes(original['audit.csv'].replace(b',16,16,2,2,2,', b',16,16,3,2,2,', 1))
                    elif mutation == 'summary':
                        (target / 'SUMMARY_KO.md').write_bytes(original['SUMMARY_KO.md'] + b'PROMOTED\n')
                    elif mutation == 'execution':
                        (target / 'EXECUTION.json').write_bytes(m.canonical({'isolated': True, 'forbidden_modules_loaded': ['cyberlateral_dev']}))
                    elif mutation == 'missing':
                        (target / 'AUDIT.json').unlink()
                    elif mutation == 'extra':
                        (target / 'extra').write_bytes(b'EXTRA')
                    elif mutation == 'noncanonical':
                        (target / 'AUDIT.json').write_bytes(json.dumps(audit, indent=2).encode())
                    self.manifest(target)
                    if mutation == 'manifest':
                        (target / 'SHA256SUMS.txt').write_bytes(b'BAD\n')
                with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'AUDIT_'):
                    m.audit_pair_summary(*reports, *paths)

    def test_validated_snapshot_not_reread(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            _, paths = self.sources(root)
            reader = m.read_lifecycle_pair
            expected_sha = hashlib.sha256((paths[0] / 'RESULTS.json').read_bytes()).hexdigest()

            def changed_after_read(first, second):
                snapshot = reader(first, second)
                for target in [first, second]:
                    (target / 'RESULTS.json').write_bytes(b'{}\n')
                return snapshot

            with patch.object(m, 'read_lifecycle_pair', side_effect=changed_after_read):
                m.write_audit(*paths, root / 'report')
            audit = json.loads((root / 'report/AUDIT.json').read_bytes())
            self.assertEqual((audit['input_lifecycle_sha256'], audit['row_count']), (expected_sha, 112))

    def test_isolated_installed_report_pair(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            output = root / 'artifacts'
            output.mkdir()
            _, paths = self.sources(output)
            v = importlib.import_module('integration_tools.verify')
            self.assertTrue(callable(getattr(v, 'verify_installed_audit', None)), 'Missing installed audit gate')
            backend = importlib.import_module('build_backend')
            name = backend.build_wheel(str(root / 'dist'))
            subprocess.run([sys.executable, '-B', '-m', 'venv', '--without-pip', str(root / 'env')], check=True, capture_output=True)
            py = root / 'env/bin/python'
            subprocess.run(['uv', 'pip', 'install', '--offline', '--no-deps', '--link-mode=copy', '--python', str(py), str(root / 'dist' / name)], check=True, capture_output=True)
            summary = v.verify_installed_audit(ROOT, py, output, root)
            self.assertEqual((summary['row_count'], summary['model_steps']), (112, 0))
            self.assertEqual(json.loads((output / 'audit_one/EXECUTION.json').read_bytes()), {'isolated': True, 'forbidden_modules_loaded': []})
            (output / 'audit_two/audit.csv').write_bytes(b'BAD\n')
            with self.assertRaisesRegex(ValueError, 'AUDIT_'):
                m.audit_pair_summary(output / 'audit_one', output / 'audit_two', *paths)


if __name__ == '__main__':
    unittest.main()
