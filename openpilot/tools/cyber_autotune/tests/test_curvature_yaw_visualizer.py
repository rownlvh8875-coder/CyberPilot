"""Standalone offline rendering: consistency admission, no fabricated lane geometry."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from openpilot.tools.cyber_autotune.curvature_yaw_screening import build_screening_case, run_screening_case
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


class TestCurvatureYawVisualizer(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    case = build_screening_case('gentle_low_left')
    cls.payload = {'reports':[run_screening_case(case,expected_manifest_sha256=digest(canonical(case['manifest'])),timeout_s=10.)]}

  def test_warning_traces_and_receipt_are_visible_and_repeatable(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_visualizer import render_html
    html = render_html(self.payload)
    self.assertEqual(html,render_html(self.payload))
    for label in ('NO INDEPENDENT LANE TRUTH','SYNTHETIC / NOT VEHICLE TRUTH',
                  'NOT_READY','REAL_VEHICLE_UNVERIFIED','VEHICLE_ACTIVATION_BLOCKED',
                  'Desired / actual curvature','Requested / applied delayed torque',
                  'Steering angle','Baseline / current / candidate trajectory',
                  'CURRENT = BASELINE','Command zero crossings','Reversal events',
                  'scenario','cursor','saturation','Curve phase'):
      self.assertIn(label,html)
    self.assertIn(self.payload['reports'][0]['receipt_sha256'],html)
    self.assertIn('Content-Security-Policy',html)
    for forbidden in ('fetch(', 'XMLHttpRequest','WebSocket(', '<script src=', '<link href=', '<iframe', '<img'):
      self.assertNotIn(forbidden,html)

  def test_bad_scope_receipt_empty_duplicate_and_catalog_binding_rejected(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_visualizer import render_html
    for payload in ({'reports':[]},{'reports':self.payload['reports']*2},
                    dict(self.payload,catalog_sha256='a'*64)):
      with self.assertRaises(ValueError):
        render_html(payload)
    for field in ('reference_status','receipt_sha256','performance_qualified'):
      payload = copy.deepcopy(self.payload)
      payload['reports'][0][field] = True
      with self.subTest(field=field),self.assertRaises(ValueError):
        render_html(payload)

  def test_data_is_script_safe_even_for_checksum_consistent_hostile_metadata(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_visualizer import render_html
    payload = copy.deepcopy(self.payload)
    report = payload['reports'][0]
    injection = '</script><script>alert("metadata")</script>'
    report['manifest']['environment']['python'] = injection
    report['manifest_sha256'] = digest(canonical(report['manifest']))
    report['receipt_sha256'] = digest(canonical({k:v for k,v in report.items() if k!='receipt_sha256'}))
    html = render_html(payload)
    self.assertNotIn(injection,html)
    self.assertIn('\\u003c/script',html)

  def test_input_file_duplicate_keys_and_nonfinite_values_rejected(self):
    from openpilot.tools.cyber_autotune.curvature_yaw_visualizer import load_payload
    with tempfile.TemporaryDirectory() as root:
      path = Path(root)/'synthetic.json'
      path.write_bytes(canonical(self.payload))
      self.assertEqual(load_payload(path),self.payload)
      for raw in ('{"reports":[],"reports":[]}','{"reports":[NaN]}'):
        path.write_text(raw)
        with self.assertRaises(ValueError):
          load_payload(path)

  def test_renderer_binds_input_and_actual_renderer_sources(self):
    from openpilot.tools.cyber_autotune import curvature_yaw_visualizer as renderer
    html = renderer.render_html(self.payload)
    for value in (digest(canonical(self.payload)),digest(Path(renderer.__file__).read_bytes()),
                  digest(renderer.TEMPLATE.read_bytes()),digest(renderer.SCRIPT.read_bytes())):
      self.assertIn(value,html)

  def test_cli_writes_only_validated_synthetic_artifact(self):
    import subprocess
    import sys
    with tempfile.TemporaryDirectory() as root:
      source,target = Path(root)/'screening.json',Path(root)/'viewer.html'
      source.write_bytes(canonical(self.payload))
      outcome = subprocess.run([sys.executable,'-m','openpilot.tools.cyber_autotune.curvature_yaw_visualizer',
                                '--input',str(source),'--output',str(target)],capture_output=True,timeout=10)
      self.assertEqual(outcome.returncode,0,outcome.stderr)
      self.assertIn('NO INDEPENDENT LANE TRUTH',target.read_text())
      source.write_text(json.dumps({'reports':[]}))
      target.unlink()
      outcome = subprocess.run([sys.executable,'-m','openpilot.tools.cyber_autotune.curvature_yaw_visualizer',
                                '--input',str(source),'--output',str(target)],capture_output=True,timeout=10)
      self.assertNotEqual(outcome.returncode,0)
      self.assertFalse(target.exists())

  def test_javascript_controls_and_svg_series_with_dom_double(self):
    # This checks component logic in Node, not browser layout or CSP enforcement.
    import shutil
    import subprocess
    node = shutil.which('node')
    if not node:
      self.skipTest('Node unavailable; pure JavaScript control test only')
    from openpilot.tools.cyber_autotune.curvature_yaw_visualizer import SCRIPT
    second = build_screening_case('reengage_high')
    report = run_screening_case(second,expected_manifest_sha256=digest(canonical(second['manifest'])),timeout_s=10.)
    bundle = {'artifact':{},'reports':self.payload['reports']+[report]}
    harness = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const bundle=JSON.parse(fs.readFileSync(0,'utf8'));
const items=new Map();
function element(id){
  if(!items.has(id)) items.set(id,{value:id==='scenario'?'0':'0', checked:true,
    textContent:'',innerHTML:'',children:[],listeners:{},
    appendChild(x){this.children.push(x);},
    addEventListener(event,callback){this.listeners[event]=callback;}});
  return items.get(id);
}
element('screening-data').textContent=JSON.stringify(bundle);
const document={getElementById:element,createElement(){return {value:'',textContent:''};}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,JSON,Math});
assert.equal(element('scenario').children.length,2);
assert.equal(element('clock').textContent,'0.00 s');
assert(element('torque').innerHTML.includes('data-series="baseline-requested_torque"'));
assert(element('curvature').innerHTML.includes('data-series="desired"'));
assert(element('trajectory').innerHTML.includes('data-series="candidate-pose_y_m"'));
element('cursor').value='120';element('cursor').listeners.input();
assert.equal(element('clock').textContent,'1.20 s');
assert(element('cursor-readout').textContent.includes('Curve phase: apex'));
element('baseline').checked=false;element('baseline').listeners.change();
assert(!element('torque').innerHTML.includes('data-series="baseline-requested_torque"'));
assert(element('torque').innerHTML.includes('data-series="candidate-requested_torque"'));
element('scenario').value='1';element('scenario').listeners.change();
assert.equal(element('cursor').value,'0');
element('cursor').value='200';element('cursor').listeners.input();
assert(element('cursor-readout').textContent.includes('Curve phase: inactive'));
assert(element('cursor-readout').textContent.includes('active: false'));
assert(element('identity').textContent.includes(bundle.reports[1].receipt_sha256));
for(const id of ['trajectory','torque','curvature','angle','delta']){
  assert(!/NaN|Infinity/.test(element(id).innerHTML));
}
console.log('DOM-double controls / SVG series PASS; browser rendering NOT_RUN');
"""
    outcome = subprocess.run([node,'-e',harness,str(SCRIPT)],input=canonical(bundle),capture_output=True,timeout=10)
    self.assertEqual(outcome.returncode,0,outcome.stderr.decode())
    self.assertIn('PASS',outcome.stdout.decode())


if __name__ == '__main__':
  unittest.main()
