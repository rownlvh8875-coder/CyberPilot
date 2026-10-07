import shutil
import subprocess
import unittest
from openpilot.tools.cyber_autotune import curvature_yaw_rejection_visualizer as viewer
from openpilot.tools.cyber_autotune import curvature_yaw_rejection as rejection
from openpilot.tools.cyber_autotune.curvature_yaw_v2_search import build_case,run_case
from openpilot.tools.cyber_autotune.native_protocol import canonical,digest


class TestRejectionVisualizer(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    case=build_case('sharp_mid_left',{'factor_high_fraction':0.,'friction_high_fraction':0.},role='STRESS')
    cls.report=run_case(case,expected_manifest_sha256=digest(canonical(case['manifest'])))

  def bundle(self):
    rows=rejection.case_ledger(self.report)
    return {'reports':[viewer.case_view(self.report)],'artifact':{},'evaluation_verdict':{'status':'REJECTED'},
            'rejection':{'ledger':{'violations':rows,'clusters':rejection.cluster(rows),'violation_count':len(rows),
                                  'divergence':{'sharp_mid_left':{'vs_v1':rejection.divergence(
                                    self.report['arms'][3]['samples'],self.report['arms'][2]['samples'])}}},
                         'family_decision':{'verdict':'FAMILY_REDESIGN'}}}

  def test_case_projection_keeps_all_four_raw_arms_and_schedule(self):
    view=viewer.case_view(self.report)
    self.assertEqual(view['attribution']['v1_arm']['samples'],self.report['arms'][2]['samples'])
    for arm in self.report['arms']:
      self.assertEqual(view['schedules'][arm['arm']],arm['native_result']['effective_parameters'])
    self.assertEqual(len(view['case_violations']),21)
    self.assertEqual(view['display_projection_sha256'],digest(canonical({k:v for k,v in view.items() if k!='display_projection_sha256'})))

  def test_final_viewer_rejects_partial_or_missing_selection(self):
    for payload in ({'reports':[]},{'reports':[self.report]}):
      with self.assertRaises(ValueError):
        viewer.render_html(payload)

  def test_html_truth_warnings_remote_assets_and_json_injection(self):
    bundle=self.bundle()
    bundle['artifact']['untrusted']='</script><script src="https://invalid.example/asset"></script>'
    html=viewer._html(bundle)
    for label in ('NO INDEPENDENT LANE TRUTH','SYNTHETIC / NOT VEHICLE TRUTH','violation-cluster','violation-rows',
                  'factor-schedule','friction-schedule','pid_i','applied-derivative','v1-overlay'):
      self.assertIn(label,html)
    for forbidden in ('<script src=','fetch(','XMLHttpRequest','WebSocket('):
      self.assertNotIn(forbidden,html)

  def javascript_check(self,bundle):
    node=shutil.which('node')
    if not node:
      self.skipTest('Node unavailable')
    html=viewer._html(bundle)
    script=html.split('<script>',1)[1].split('</script>',1)[0]
    harness=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const data=JSON.parse(fs.readFileSync(0,'utf8')),items=new Map();
function element(id){
  if(!items.has(id)){const obj={value:'0',checked:true,textContent:'',children:[],listeners:{},dataset:{},
    appendChild(x){this.children.push(x);},addEventListener(e,f){(this.listeners[e]??=[]).push(f);}};
    Object.defineProperty(obj,'innerHTML',{get(){return this.html??'';},set(v){this.html=v;if(v==='')this.children=[];}});
    items.set(id,obj);}
  return items.get(id);
}
function create(){return{value:'',textContent:'',children:[],listeners:{},dataset:{},
  appendChild(x){this.children.push(x);},addEventListener(e,f){(this.listeners[e]??=[]).push(f);}};}
element('screening-data').textContent=JSON.stringify(data.bundle);
const document={getElementById:element,createElement:create};
vm.runInNewContext(data.script,{document,JSON,Math,String});
assert.equal(element('violation-rows').children.length,21);
assert(element('torque').innerHTML.includes('v1-requested_torque'));
assert(element('curvature').innerHTML.includes('v1-curvature_1pm'));
assert(element('factor-schedule').innerHTML.includes('candidate-factor-schedule'));
assert(element('rejection-readout').textContent.includes('step 41'));
element('violation-rows').children[0].children[0].children[0].listeners.click[0]();
assert.notEqual(element('cursor').value,'0');
assert(element('rejection-readout').textContent.includes('Selected violation'));
element('violation-cluster').value=data.bundle.rejection.ledger.clusters[0].cluster;
element('violation-cluster').listeners.change[0]();
assert.equal(element('violation-rows').children.length,data.bundle.rejection.ledger.clusters[0].count);
element('v1-overlay').checked=false;element('v1-overlay').listeners.change[0]();
assert(!element('torque').innerHTML.includes('v1-requested_torque'));
for(const id of ['curvature','torque','command-derivative','applied-derivative','factor-schedule'])
  assert(!/NaN|Infinity/.test(element(id).innerHTML));
console.log('rejection overlay, cluster, click navigation PASS');
"""
    result=subprocess.run([node,'-e',harness],input=canonical({'bundle':bundle,'script':script}),
                          capture_output=True,timeout=10)
    self.assertEqual(result.returncode,0,result.stderr.decode())

  def test_javascript_overlay_cluster_and_click_navigation(self):
    self.javascript_check(self.bundle())

  def test_divergence_does_not_depend_on_failing_scenario_ledger(self):
    bundle=self.bundle()
    bundle['rejection']['ledger']['divergence']={}
    self.javascript_check(bundle)
