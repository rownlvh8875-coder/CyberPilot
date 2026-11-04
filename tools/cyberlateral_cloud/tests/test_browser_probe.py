"""Independent observed metrics and real loopback boundary, no browser dependency."""

import importlib
import json
import sys
import unittest
from contextlib import closing
from copy import deepcopy
from http.client import HTTPConnection
from pathlib import Path
from urllib.parse import urlsplit

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))


class BrowserProbeTests(unittest.TestCase):
    def module(self):
        self.assertTrue((TOOLS / 'browser_probe.py').is_file(), 'reusable browser probe missing')
        return importlib.import_module('browser_probe')

    def metrics(self):
        return {'viewport': 390, 'document_width': 390, 'pan': 0, 'dpr': 1,
                'footer_font': 16, 'footer_visible': True,
                'footer_text': 'SCHEMA_SIMULATION_NOT_CAPNP_OR_CAN_WIRE F70UH/F70V/F71 NOT_ALLOWED',
                'chart_count': 2, 'min_chart_font': 14, 'csp': True, 'active_assets': 0,
                'table_position': 20, 'single_ticks': ['5', '5'], 'single_circles': 5}

    def test_valid_observations_pass_without_a_browser_import(self):
        p = self.module()
        self.assertEqual(p.assess_case('resumed', 390, self.metrics()), [])
        desktop = self.metrics() | {'viewport': 1440, 'document_width': 1440, 'table_position': 0}
        self.assertEqual(p.assess_case('sign', 1440, desktop), [])

    def test_old_one_pixel_overflow_is_a_failure_without_tolerance(self):
        p = self.module()
        self.assertIn('PAGE_OVERFLOW', p.assess_case('sign', 390, self.metrics() | {'document_width': 391, 'pan': 1}))

    def test_layout_failures_cannot_hide_behind_a_fitting_document(self):
        p = self.module()
        cases = [('pan', 1, 'PAGE_OVERFLOW'), ('viewport', 360, 'PAGE_OVERFLOW'),
                 ('dpr', 2, 'DPR'), ('footer_font', 12, 'FOOTER'),
                 ('footer_visible', False, 'FOOTER'), ('footer_text', 'not qualified', 'FOOTER'),
                 ('chart_count', 1, 'CHARTS'), ('min_chart_font', 13.9, 'CHART_FONT'),
                 ('csp', False, 'CSP'), ('active_assets', 1, 'ACTIVE_ASSETS'),
                 ('table_position', 0, 'TABLE_SCROLL'), ('single_ticks', ['4', '5'], 'RESUMED_POINT'),
                 ('single_circles', 4, 'RESUMED_POINT')]
        for key, value, expected in cases:
            with self.subTest(key=key):
                self.assertIn(expected, p.assess_case('resumed', 390, self.metrics() | {key: value}))

    def test_incomplete_nonfinite_or_mistyped_observations_never_pass(self):
        p = self.module()
        for key, value in [('pan', float('nan')), ('min_chart_font', float('inf')),
                           ('document_width', '390'), ('chart_count', True)]:
            with self.subTest(key=key):
                self.assertTrue(p.assess_case('sign', 390, self.metrics() | {key: value}))
        self.assertTrue(p.assess_case('sign', 390, {}))

    def test_metric_classification_does_not_mutate_observations(self):
        p = self.module()
        metrics = self.metrics()
        before = deepcopy(metrics)
        p.assess_case('resumed', 390, metrics)
        self.assertEqual(metrics, before)

    def test_preview_serves_only_exact_owned_paths_and_copies_payloads(self):
        p = self.module()
        payloads = {'/sign/index.html': b'<p>safe</p>', '/sign/VIEW.json': b'{}\n'}
        with p.preview(payloads) as base:
            payloads['/sign/index.html'] = b'changed after ownership'
            address = urlsplit(base)
            with closing(HTTPConnection(address.hostname, address.port, timeout=5)) as client:
                client.request('GET', '/sign/index.html')
                response = client.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read(), b'<p>safe</p>')
                self.assertIn("default-src 'none'", response.getheader('Content-Security-Policy') or '')
                for name in ['/sign/RECEIPT.json', '/../secret', '/sign/%56IEW.json',
                             '/sign/VIEW.json?extra=1', '/resumed/index.html', '/']:
                    client.request('GET', name)
                    response = client.getresponse()
                    self.assertEqual(response.status, 404, name)
                    response.read()
                client.request('GET', '/sign/VIEW.json')
                response = client.getresponse()
                self.assertEqual(json.loads(response.read()), {})

    def test_preview_rejects_unscoped_payload_names(self):
        p = self.module()
        for name in ['/sign/RECEIPT.json', '/sign/../secret', '/third/index.html']:
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'PREVIEW_SCOPE'):
                with p.preview({name: b'secret'}):
                    self.fail('unsafe payload served')


if __name__ == '__main__':
    unittest.main()
