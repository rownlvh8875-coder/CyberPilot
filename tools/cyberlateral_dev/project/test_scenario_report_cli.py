"""Static saved-record view: real DOM/output effects and no model imports."""

import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

from scenario_report_fixture import edit_json, layout_bundle, write_bundle
from v1_helpers import ROOT


class DOM(HTMLParser):
    def __init__(self, raw):
        super().__init__()
        self.tags = []
        self.feed(raw.decode())

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class ScenarioReportCLITests(unittest.TestCase):
    def modules(self):
        self.assertTrue((ROOT / 'tools/scenario_report.py').is_file(), 'Missing R32 CLI')
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_report_data'), importlib.import_module('integration_tools.scenario_report_run')

    def cli(self, *args):
        return subprocess.run([sys.executable, '-I', '-B', ROOT / 'tools/scenario_report.py', *map(str, args)],
                              capture_output=True, timeout=20, check=False)

    def test_actual_cli_two_graphs_complete_table_manifest_and_source_unchanged(self):
        self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source = write_bundle(root / 'source')
            before = {p.name: p.read_bytes() for p in source.iterdir()}
            result = self.cli('--input', source, '--output', root / 'out')
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(before, {p.name: p.read_bytes() for p in source.iterdir()})
            self.assertEqual({p.name for p in (root / 'out').iterdir()}, {'index.html', 'VIEW.json', 'RECEIPT.json', 'SHA256SUMS.txt'})
            html = (root / 'out/index.html').read_bytes()
            dom = DOM(html)
            self.assertEqual(sum(t == 'svg' for t, _ in dom.tags), 2)
            self.assertEqual(sum(t == 'tr' and a.get('data-row') == 'true' for t, a in dom.tags), 4)
            self.assertEqual(sum(t == 'polyline' for t, _ in dom.tags), 5)
            self.assertFalse(any(t in {'script', 'iframe', 'img', 'link'} for t, _ in dom.tags))
            self.assertTrue(any(t == 'meta' and a.get('http-equiv') == 'Content-Security-Policy' for t, a in dom.tags))
            self.assertNotIn(str(source).encode(), html)
            self.assertNotIn(b'/declared-fixture/', html)
            view = json.loads((root / 'out/VIEW.json').read_bytes())
            self.assertEqual([r['final_command'] for r in view['rows']], [2, -2, 0, 2])
            self.assertEqual(view['renderer_model_executions'], 0)
            receipt = json.loads((root / 'out/RECEIPT.json').read_bytes())
            self.assertEqual(receipt['forbidden_modules_loaded'], [])
            lines = (root / 'out/SHA256SUMS.txt').read_text().splitlines()
            self.assertEqual(len(lines), 3)
            for line in lines:
                digest, name = line.split('  ')
                self.assertEqual(hashlib.sha256((root / 'out' / name).read_bytes()).hexdigest(), digest)

    def test_same_saved_bundle_moved_repeat_portable_same_receipt_different(self):
        _, run = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            for name in ['one', 'two']:
                source = write_bundle(root / ('source-' + name))
                run.run_report(source, root / name)
            for name in ['index.html', 'VIEW.json']:
                self.assertEqual((root / 'one' / name).read_bytes(), (root / 'two' / name).read_bytes())
            self.assertNotEqual((root / 'one/RECEIPT.json').read_bytes(), (root / 'two/RECEIPT.json').read_bytes())

    def test_single_resumed_flat_signed_zero_and4096_rows(self):
        m, run = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            resumed = write_bundle(root / 'resumed', 'resumed')
            run.run_report(resumed, root / 'resumed-out')
            dom = DOM((root / 'resumed-out/index.html').read_bytes())
            self.assertEqual(sum(t == 'circle' and a.get('cx') == '375.000' for t, a in dom.tags), 5)
            view = json.loads((root / 'resumed-out/VIEW.json').read_bytes())
            self.assertEqual((view['rows'][0]['angle_counter_after'], view['rows'][0]['final_command']), (90, -2))
            flat = layout_bundle(root / 'flat', count=4096, negative_zero=True)
            run.run_report(flat, root / 'flat-out')
            view = m.read_report(flat)['view']
            self.assertEqual(len(view['rows']), 4096)
            self.assertEqual(view['rows'][-1]['index'], 4095)
            html = (root / 'flat-out/index.html').read_bytes()
            self.assertIn(b'-0x0.0p+0', html)
            dom = DOM(html)
            self.assertEqual(sum(t == 'tr' and a.get('data-row') == 'true' for t, a in dom.tags), 4096)
            for tag, attrs in dom.tags:
                if tag == 'polyline':
                    self.assertEqual(len(attrs['points'].split()), 4096)
                    self.assertNotIn('nan', attrs['points'].lower())
                    self.assertNotIn('inf', attrs['points'].lower())

    def test_internal_renderer_escapes_text_and_has_no_external_urls(self):
        m, _ = self.modules()
        renderer = importlib.import_module('integration_tools.scenario_report_html')
        with tempfile.TemporaryDirectory() as scratch:
            view = deepcopy(m.read_report(write_bundle(Path(scratch) / 'source'))['view'])
            view['scenario_id'] = '<script>alert("x")</script>'
            raw = renderer._render_html(view)
            self.assertIn(b'&lt;script&gt;', raw)
            self.assertFalse(any(t == 'script' for t, _ in DOM(raw).tags))
            self.assertFalse(any(a.get(k, '').startswith(('http:', 'https:', '//')) for _, a in DOM(raw).tags for k in ['href', 'src']))

    def test_output_eligibility_before_input_read_and_nested_source_rejection(self):
        m, run = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source = write_bundle(root / 'source')
            (root / 'existing').write_bytes(b'keep')
            (root / 'link').symlink_to(root / 'missing')
            for path, code in [(root / 'existing', 'REPORT_OUTPUT_EXISTS'), (root / 'link', 'REPORT_OUTPUT_EXISTS'),
                               (root / 'missing/out', 'REPORT_OUTPUT_PARENT'), (source / 'new-report', 'REPORT_OUTPUT_LOCATION')]:
                with patch.object(run, 'read_report', side_effect=AssertionError('MUST_NOT_READ')), self.assertRaises(m.ReportError) as error:
                    run.run_report(source, path)
                self.assertEqual(error.exception.code, code)
            self.assertEqual((root / 'existing').read_bytes(), b'keep')
            self.assertEqual(len(list(source.iterdir())), 6)

    def test_late_invalid_data_never_publishes_output(self):
        m, run = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source = write_bundle(root / 'source')
            edit_json(source, 'RESULTS.json', lambda x: x['rows'][-1]['prepared']['state'].update(previous_applied=99))
            with self.assertRaises(m.ReportError):
                run.run_report(source, root / 'out')
            self.assertFalse((root / 'out').exists())

    def test_write_fault_has_no_index_and_existing_partial_cannot_retry(self):
        m, run = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source = write_bundle(root / 'source')
            original = run._write_exclusive

            def fail(path, raw):
                if path.name == 'RECEIPT.json':
                    raise OSError('declared test fault')
                return original(path, raw)

            with patch.object(run, '_write_exclusive', side_effect=fail), self.assertRaises(m.ReportError):
                run.run_report(source, root / 'out')
            self.assertFalse((root / 'out/index.html').exists())
            self.assertTrue((root / 'out/VIEW.json').is_file())
            with self.assertRaises(m.ReportError) as error:
                run.run_report(source, root / 'out')
            self.assertEqual(error.exception.code, 'REPORT_OUTPUT_EXISTS')

    def test_late_collision_preserves_existing(self):
        m, run = self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            out = Path(scratch) / 'out'
            out.mkdir()
            (out / 'keep').write_bytes(b'keep')
            with self.assertRaises(m.ReportError):
                run._publish(out, {})
            self.assertEqual((out / 'keep').read_bytes(), b'keep')

    def test_help_unknown_flags_missing_input_and_runtime_guard(self):
        m, run = self.modules()
        self.assertEqual(self.cli('--help').returncode, 0)
        self.assertEqual(self.cli('--rate-budget', '0').returncode, 2)
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            result = self.cli('--input', root / 'none', '--output', root / 'out')
            self.assertEqual(result.returncode, 2)
            self.assertFalse((root / 'out').exists())
            source = write_bundle(root / 'source')
            with patch.object(run.platform, 'python_version', return_value='3.12.14'), self.assertRaises(m.ReportError) as error:
                run.run_report(source, root / 'out')
            self.assertEqual(error.exception.code, 'REPORT_RUNTIME')

    def test_cli_import_tripwire_blocks_any_model_or_native_attempt(self):
        self.modules()
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source = write_bundle(root / 'source')
            code = ('import sys,importlib.abc,runpy\n'
                    'class Reject(importlib.abc.MetaPathFinder):\n'
                    ' def find_spec(self,fullname,path=None,target=None):\n'
                    '  if fullname.split(".")[0] in {"cyberlateral_dev","capnp","numpy","openpilot","opendbc","cereal"}: raise AssertionError("FORBIDDEN_IMPORT:"+fullname)\n'
                    'sys.meta_path.insert(0,Reject())\n'
                    'sys.argv=[' + repr(str(ROOT / 'tools/scenario_report.py')) + ',"--input",' + repr(str(source)) + ',"--output",' + repr(str(root / 'out')) + ']\n'
                    'runpy.run_path(sys.argv[0],run_name="__main__")\n')
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, timeout=20, check=False)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertTrue((root / 'out/index.html').is_file())
