"""Emitted HTML/geometry contracts, not a browser visual qualification."""

import importlib
import sys
import tempfile
import unittest
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from scenario_report_fixture import write_bundle
from v1_helpers import ROOT


@dataclass
class Element:
    tag: str
    attrs: dict
    ancestors: tuple[str, ...]
    text: str = ''


class ChartDOM(HTMLParser):
    def __init__(self, raw):
        super().__init__()
        self.nodes: list[Element] = []
        self.stack: list[Element] = []
        self.feed(raw.decode())

    def handle_starttag(self, tag, attrs):
        node = Element(tag, dict(attrs), tuple(n.tag for n in self.stack))
        self.nodes.append(node)
        if tag not in {'meta', 'br', 'hr', 'link', 'img', 'input'}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        for node in self.stack:
            node.text += data

    def by_class(self, name):
        return [n for n in self.nodes if name in n.attrs.get('class', '').split()]


class ScenarioReportChartTests(unittest.TestCase):
    def renderer(self):
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        return importlib.import_module('integration_tools.scenario_report_html')

    def saved_html(self, profile):
        renderer = self.renderer()
        reader = importlib.import_module('integration_tools.scenario_report_data')
        with tempfile.TemporaryDirectory() as scratch:
            view = reader.read_report(write_bundle(Path(scratch) / 'saved', profile))['view']
        return renderer._render_html(view)

    def test_axis_values_and_caption_are_outside_shrinking_svg(self):
        # Break caught: reintroducing text into a scaled SVG shrinks mobile labels.
        for profile, expected in [('sign', ['0.25-0.25', '4-4']), ('resumed', ['0-0.25', '2-4'])]:
            with self.subTest(profile=profile):
                dom = ChartDOM(self.saved_html(profile))
                self.assertFalse(any(n.tag == 'text' and 'svg' in n.ancestors for n in dom.nodes))
                self.assertEqual([n.text for n in dom.by_class('y-ticks')], expected)
                self.assertEqual([n.text for n in dom.by_class('axis-caption')], ['모델 호출 index · NOT seconds'] * 2)
                for node in dom.by_class('y-ticks') + dom.by_class('x-ticks') + dom.by_class('axis-caption'):
                    self.assertNotIn('svg', node.ancestors)

    def test_resumed_single_index_is_centered_once_and_points_retained(self):
        # Break caught: duplicate endpoint labels imply a time span for one sample.
        dom = ChartDOM(self.saved_html('resumed'))
        ticks = dom.by_class('x-ticks')
        self.assertEqual([n.text for n in ticks], ['5', '5'])
        self.assertTrue(all('single' in n.attrs.get('class', '').split() for n in ticks))
        circles = [n for n in dom.nodes if n.tag == 'circle']
        self.assertEqual([n.attrs['cx'] for n in circles], ['375.000'] * 5)
        self.assertEqual([n.attrs['cy'] for n in circles], ['200.000', '200.000', '30.000', '143.333', '143.333'])

    def test_signed_small_tick_and_terminal_index_are_complete_html_labels(self):
        # Break caught: lost signs/scientific text or a clipped last SVG index.
        rows = [{'index': 0, 'request_hex': '-0x1.02e84fa5a8c84p-13'}, {'index': 4095, 'request_hex': '0x0.0p+0'}]
        dom = ChartDOM(self.renderer()._chart(rows, True).encode())
        self.assertEqual([n.text for n in dom.by_class('y-ticks')], ['0-0.000123457'])
        self.assertEqual([n.text for n in dom.by_class('x-ticks')], ['04095'])
        self.assertFalse(any(n.tag == 'text' for n in dom.nodes))
        series = [n for n in dom.nodes if n.tag == 'polyline']
        self.assertEqual(series[0].attrs['points'], '50.000,200.000 700.000,30.000')

    def test_series_geometry_and_complete_legend_entries_preserved(self):
        # Break caught: plotting a different stage or splitting a legend label.
        dom = ChartDOM(self.saved_html('sign'))
        plots = {n.attrs['data-series']: n.attrs['points'] for n in dom.nodes if n.tag == 'polyline'}
        self.assertEqual(plots, {
            'request_hex': '50.000,30.000 266.667,200.000 483.333,30.000 700.000,30.000',
            'integer_request': '50.000,30.000 266.667,200.000 483.333,30.000 700.000,30.000',
            'previous_applied': '50.000,115.000 266.667,72.500 483.333,157.500 700.000,115.000',
            'limited_command': '50.000,72.500 266.667,157.500 483.333,72.500 700.000,72.500',
            'final_command': '50.000,72.500 266.667,157.500 483.333,115.000 700.000,72.500',
        })
        self.assertEqual([n.text for n in dom.by_class('legend-entry')],
                         ['request_hex', 'integer_request', 'previous_applied', 'limited_command', 'final_command'])
        self.assertEqual(sum(n.tag == 'svg' for n in dom.nodes), 2)
        self.assertFalse(any(n.tag in {'script', 'iframe', 'img', 'link'} for n in dom.nodes))
