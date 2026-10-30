"""Catch incomplete exports, unsafe HTML, clamped charts and nondeterministic bundles."""
import copy
import csv
import hashlib
import io
import json
import math
import unittest
from html.parser import HTMLParser

from v1_helpers import package_feature

EXPECTED_COLUMNS = ['scenario_id','invocation_index','request_hex','scale','integer_requested','previous_applied',
                    'limited_command','final_command','normalized_expression_hex','torque_f32_bits','torque_output_can_f32_bits',
                    'lat_active','steer_request','fault_condition','angle_counter','limiter_adjusted','inactive_gate_changed',
                    'fault_request_suppressed','delta_from_previous_command']


class Page(HTMLParser):
    def __init__(self, raw):
        super().__init__(); self.tags=[]; self.text=[]; self.feed(raw)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag,dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


class TraceRenderTests(unittest.TestCase):
    def bundle(self):
        return package_feature('cyberlateral_dev.trace_report').build_report_bundle()

    def test_bundle_manifest_canonical_json_and_determinism(self):
        files=self.bundle()
        self.assertEqual(set(files),{'simulation.json','analysis.json','trace.csv','index.html','REPORT_SHA256SUMS.txt'})
        self.assertEqual(files,self.bundle())
        covered=[]
        for line in files['REPORT_SHA256SUMS.txt'].decode().splitlines():
            checksum,name=line.split('  ',1);covered.append(name)
            self.assertEqual(hashlib.sha256(files[name]).hexdigest(),checksum)
        self.assertEqual(covered,sorted(set(files)-{'REPORT_SHA256SUMS.txt'}))
        for name in ['simulation.json','analysis.json']:
            raw=files[name]
            self.assertEqual(raw,(json.dumps(json.loads(raw),sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode())
        self.assertEqual(json.loads(files['analysis.json'])['source_report_sha256'],hashlib.sha256(files['simulation.json']).hexdigest())

    def test_csv_19_columns_112_rows_exact_no_display_rounding(self):
        files=self.bundle();rows=list(csv.DictReader(io.StringIO(files['trace.csv'].decode())))
        self.assertEqual((list(rows[0]),len(rows)),(EXPECTED_COLUMNS,112))
        self.assertEqual(rows[0]['request_hex'],'0x1.999999999999ap-4')
        history=next(r for r in rows if r['scenario_id']=='history-scale')
        self.assertEqual((history['previous_applied'],history['final_command'],history['normalized_expression_hex']),('100','95',19.0.hex()))
        fault=[r for r in rows if r['fault_request_suppressed']=='true']
        self.assertEqual([(r['invocation_index'],r['final_command']) for r in fault],[('89','16'),('90','16')])
        self.assertNotIn(b'\r\n',files['trace.csv'])

    def test_html_complete_semantic_structure_and_no_active_external_content(self):
        files=self.bundle();p=Page(files['index.html'].decode())
        self.assertEqual(sum(tag=='svg' for tag,_ in p.tags),14)
        self.assertEqual(sum(tag=='section' and attrs.get('class')=='scenario' for tag,attrs in p.tags),7)
        self.assertEqual(sum(tag=='tr' and 'data-row' in attrs for tag,attrs in p.tags),112)
        for tag,attrs in p.tags:
            self.assertNotIn(tag,{'script','iframe','object','embed','img','link','form'})
            self.assertFalse(any(key.startswith('on') for key in attrs))
            for key in ['href','src','action']:
                if key in attrs:self.assertIn(attrs[key],{'analysis.json','simulation.json','trace.csv'})
        text=' '.join(p.text)
        self.assertIn('실차 사용 금지',text)
        self.assertIn('모델 호출 순서',text)
        self.assertIn('R_BUDGET',text)
        self.assertIn('UNRESOLVED',text)
        self.assertTrue(any(tag=='meta' and attrs.get('http-equiv')=='Content-Security-Policy' and "default-src 'none'" in attrs.get('content','') for tag,attrs in p.tags))

    def test_html_single_flat_series_and_history_range_not_clamped(self):
        files=self.bundle();p=Page(files['index.html'].decode())
        charts=[a for t,a in p.tags if t=='svg']
        normalized_history=next(a for a in charts if a.get('data-chart')=='history-scale:normalized')
        self.assertGreaterEqual(float(normalized_history['data-ymax']),19.0)
        integer_history=next(a for a in charts if a.get('data-chart')=='history-scale:command')
        self.assertGreaterEqual(float(integer_history['data-ymax']),100.0)
        self.assertTrue(any(t=='circle' for t,_ in p.tags))
        for tag,attrs in p.tags:
            if tag=='polyline':
                for point in attrs['points'].split():
                    x,y=map(float,point.split(','))
                    self.assertTrue(math.isfinite(x) and math.isfinite(y))
                    self.assertTrue(0<=x<=720 and 0<=y<=240)

    def test_html_escapes_data_text_and_attribute_values_without_mutation(self):
        module=package_feature('cyberlateral_dev.report_html')
        files=self.bundle();analysis=json.loads(files['analysis.json'])
        analysis['scenarios'][0]['id']='<script src="https://bad.invalid/x">&evil</script>'
        before=copy.deepcopy(analysis)
        raw=module.render_html(analysis).decode();p=Page(raw)
        self.assertEqual(analysis,before)
        self.assertFalse(any(tag=='script' for tag,_ in p.tags))
        self.assertIn(analysis['scenarios'][0]['id'],''.join(p.text))

    def test_html_escapes_hostile_summary_text_even_for_internal_renderer_misuse(self):
        module=package_feature('cyberlateral_dev.report_html')
        analysis=json.loads(self.bundle()['analysis.json'])
        payload='<img src="https://bad.invalid/x" onerror="alert(1)">'
        analysis['summary']['steps']=payload
        analysis['scenarios'][0]['summary']['steps']=payload
        p=Page(module.render_html(analysis).decode())
        self.assertFalse(any(tag=='img' for tag,_ in p.tags))
        self.assertIn(payload,''.join(p.text))


if __name__=='__main__':unittest.main()
