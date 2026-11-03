"""Visible recorded verdicts and inert exact values, without model work."""

import copy
import unittest
from html.parser import HTMLParser

from scenario_campaign_report_fixture import real_comparison


class Page(HTMLParser):
    def __init__(self, raw):
        super().__init__()
        self.text, self.tags, self.links = [], [], []
        self.feed(raw.decode())

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.links.extend(value for name, value in attrs if name in {'href', 'src'})

    def handle_data(self, data):
        self.text.append(data)


class CampaignReportHtmlTests(unittest.TestCase):
    def view(self, kind):
        from integration_tools.scenario_campaign_report_data import read_comparison
        return read_comparison(real_comparison(kind))['view']

    def page(self, view):
        from integration_tools.scenario_campaign_report_html import _render_html
        return Page(_render_html(view))

    def test_source_error_and_difference_never_promoted(self):
        for kind, verdict in [('error', 'ERROR'), ('source_different', 'DIFFERENT')]:
            with self.subTest(kind=kind):
                text = ' '.join(self.page(self.view(kind)).text)
                self.assertIn('전체 판정: ' + verdict, text)
                self.assertIn('저장 기록 회귀: MATCH', text)
                self.assertIn('정상으로 승격하지 않습니다', text)
                self.assertIn('원본 판정', text)

    def test_exact_difference_and_invocation_not_seconds(self):
        text = ' '.join(self.page(self.view('difference')).text)
        for token in ['seed-001', 'case-001', 'limited_command', 'int', '-7', '2', '존재',
                      '호출 순서', '초나 100Hz가 아닙니다', 'R_BUDGET=UNRESOLVED']:
            self.assertIn(token, text)

    def test_hostile_text_is_inert_and_missing_distinct_from_null(self):
        view = copy.deepcopy(self.view('difference'))
        detail = view['comparison']['differences'][0]
        detail.update(before='<script>alert(1)</script><img src="https://evil.invalid">', after=None, after_present=False)
        page = self.page(view)
        self.assertIn('<script>alert(1)</script>', ' '.join(page.text))
        self.assertNotIn('script', page.tags)
        self.assertNotIn('img', page.tags)
        self.assertIn('없음 (missing)', ' '.join(page.text))
        detail.update(after_present=True)
        self.assertIn('null', ' '.join(self.page(view).text))

    def test_fixed_local_links_no_private_paths_or_active_assets(self):
        from integration_tools.scenario_campaign_report_html import _render_html
        view = self.view('match')
        html = _render_html(view)
        page = Page(html)
        self.assertIn('VIEW.json', page.links)
        self.assertIn('SHA256SUMS.txt', page.links)
        self.assertTrue(all(link in {'VIEW.json', 'SHA256SUMS.txt'} or link.startswith('#') for link in page.links))
        self.assertFalse({'script', 'iframe', 'object', 'embed', 'img', 'form'} & set(page.tags))
        self.assertNotIn('/workspace/', html.decode())
        self.assertIn(b"default-src 'none'", html)

    def test_truncated_and_added_reports_preserve_details(self):
        truncated = ' '.join(self.page(self.view('truncated')).text)
        self.assertIn('512', truncated)
        self.assertIn('보존 256', truncated)
        self.assertIn('미보존 256', truncated)
        self.assertIn('미보존 상세는 검증하거나 복원하지 않았습니다', truncated)
        added = ' '.join(self.page(self.view('added')).text)
        self.assertIn('RUN_ADDED', added)
        self.assertIn('seed-002', added)


if __name__ == '__main__':
    unittest.main()
