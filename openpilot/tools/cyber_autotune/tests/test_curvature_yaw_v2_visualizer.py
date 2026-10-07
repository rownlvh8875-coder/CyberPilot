"""V2 display projection must preserve source receipts, adverse results and truth boundary."""
import copy
import shutil
import subprocess
import unittest
from unittest.mock import patch
import tempfile
from pathlib import Path

from openpilot.tools.cyber_autotune.curvature_yaw_v2_search import build_case, configurations, run_case
from openpilot.tools.cyber_autotune.curvature_yaw_v2_visualizer import render_html, project, load_payload
from openpilot.tools.cyber_autotune.curvature_yaw_visualizer import SCRIPT
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest


class TestV2Visualizer(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    case=build_case('gentle_high_right',configurations()[0],role='EVALUATION',selection_sha256='a'*64)
    cls.report=run_case(case,expected_manifest_sha256=digest(canonical(case['manifest'])))

  def test_projection_preserves_exact_raw_values_and_identity(self):
    view=project(self.report)
    for i,j in ((0,0),(1,1),(2,3)):
      self.assertEqual(view['arms'][i]['samples'],self.report['arms'][j]['samples'])
      self.assertEqual(view['arms'][i]['identity'],self.report['arms'][j]['identity'])
      self.assertNotIn('native_result',view['arms'][i])
    self.assertNotIn('receipt_sha256',view)
    self.assertEqual(view['projection']['source_full_report_receipt_sha256'],self.report['receipt_sha256'])
    self.assertTrue(view['projection']['native_proofs_omitted'])
    self.assertEqual(view['display_projection_sha256'],digest(canonical({k:v for k,v in view.items() if k!='display_projection_sha256'})))
    self.assertEqual(view['attribution']['v1_arm']['samples'],self.report['arms'][2]['samples'])

  def test_html_warning_delta_speed_and_frozen_candidate_policy(self):
    html=render_html({'reports':[self.report]})
    self.assertEqual(html,render_html({'reports':[self.report]}))
    for label in ('NO INDEPENDENT LANE TRUTH','SYNTHETIC / NOT VEHICLE TRUTH','CURRENT = BASELINE',
                  'requested-delta','applied-delta','residual-delta','derivative-delta','speed',
                  'Frozen v2 attribution','Frozen synthetic stress matrix','Frozen 23-case','HIGH','saturation','candidate_identity_sha256','policy_sha256'):
      self.assertIn(label,html)
    for forbidden in ('fetch(', 'XMLHttpRequest', 'WebSocket(', '<script src=', '<link href=', '<iframe'):
      self.assertNotIn(forbidden,html)

  def test_wrong_scope_tamper_duplicate_and_empty_rejected(self):
    with self.assertRaises(ValueError):
      render_html({'reports':[]})
    with self.assertRaises(ValueError):
      render_html({'reports':[self.report,self.report]})
    r=copy.deepcopy(self.report)
    r['performance_qualified']=True
    with self.assertRaises(ValueError):
      render_html({'reports':[r]})

  def test_stress_display_requires_full_final_context_and_evidence(self):
    with self.assertRaises(ValueError):
      render_html({'reports':[self.report],'stress_evidence':{'aggregate':{'hard_pass_count':23}}})

  def test_summary_only_stress_refused_after_evaluation_context_admission(self):
    # Isolate the display evidence boundary; final EVAL admission is tested by search tests/real CLI.
    payload={'reports':[self.report],'selection':{'receipt_sha256':'a'*64},
             'evaluation_manifest_list_sha256':'b'*64,'stress_evidence':{'aggregate':{'case_count':23}}}
    with patch('openpilot.tools.cyber_autotune.curvature_yaw_v2_visualizer.classify',return_value={'status':'REJECTED'}):
      with self.assertRaises(ValueError):
        render_html(payload)

  def test_display_freeze_tamper_refused_after_full_aggregate_admission(self):
    freeze={'policy_sha256':'c'*64,'selection_sha256':'b'*64,'producer_source_sha256':'d'*64,
            'evaluation_context':{},'manifests_sha256':[],'matrix_sha256':'e'*64}
    payload={'reports':[self.report],'selection':{'receipt_sha256':'a'*64},
             'evaluation_manifest_list_sha256':'f'*64,'stress_evidence':{'reports':[],'freeze':freeze}}
    aggregate={'policy_sha256':'c'*64,'producer_source_sha256':'d'*64,'evaluation_context':{}}
    # Mock only expensive upstream admissions, testing the distinct display freeze-binding guard.
    with patch('openpilot.tools.cyber_autotune.curvature_yaw_v2_visualizer.classify',return_value={'status':'REJECTED'}),patch(
      'openpilot.tools.cyber_autotune.curvature_yaw_v2_visualizer.aggregate',return_value=aggregate):
      with self.assertRaisesRegex(ValueError,'DISPLAY_STRESS_FREEZE_CONTEXT_DRIFT'):
        render_html(payload)

  def test_partial_display_cannot_claim_final_evaluation_context(self):
    with self.assertRaises(ValueError):
      render_html({'reports':[self.report],'selection':{'receipt_sha256':'a'*64},
                   'evaluation_manifest_list_sha256':'b'*64})

  def test_strict_json_transport_rejects_duplicate_nonfinite_and_size(self):
    with tempfile.TemporaryDirectory() as directory:
      path=Path(directory)/'input.json'
      for raw in (b'{"reports":[],"reports":[]}',b'{"reports":NaN}',b'x'*(32*1024*1024+1)):
        path.write_bytes(raw)
        with self.assertRaises(ValueError):
          load_payload(path)

  def test_javascript_v2_deltas_are_raw_aligned_and_controls_work(self):
    node=shutil.which('node')
    if not node:
      self.skipTest('Node unavailable')
    bundle={'artifact':{},'reports':[project(self.report)]}
    harness=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const bundle=JSON.parse(fs.readFileSync(0,'utf8')),items=new Map();
function element(id){
  if(!items.has(id))items.set(id,{value:'0',checked:true,textContent:'',innerHTML:'',children:[],listeners:{},
    appendChild(x){this.children.push(x);},addEventListener(e,f){this.listeners[e]=f;}});
  return items.get(id);
}
element('screening-data').textContent=JSON.stringify(bundle);
const document={getElementById:element,createElement(){return{value:'',textContent:''};}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,JSON,Math});
assert(element('scenario').children[0].textContent.includes('HIGH'));
assert(element('torque').innerHTML.includes('candidate-requested_torque'));
assert(element('requested-delta').innerHTML.includes('candidate-minus-baseline-requested_torque'));
assert(element('applied-delta').innerHTML.includes('candidate-minus-baseline-applied_normalized_torque'));
assert(element('residual-delta').innerHTML.includes('candidate-minus-baseline-curvature_residual_1pm'));
assert(element('derivative-delta').innerHTML.includes('candidate-minus-baseline-command_derivative_per_s'));
assert(element('speed').innerHTML.includes('speed_mps'));
assert(element('angle').innerHTML.includes('desired-steering-angle'));
assert.equal(element('physical-delay').textContent,'20 ms');
assert(element('attribution').textContent.includes('V1'));
assert(element('robustness').textContent.includes('not supplied'));
element('cursor').value='120';element('cursor').listeners.input();
assert(element('cursor-readout').textContent.includes('HIGH'));
assert(element('cursor-readout').textContent.includes('apex'));
element('candidate').checked=false;element('candidate').listeners.change();
assert(!element('torque').innerHTML.includes('candidate-requested_torque'));
assert(!element('requested-delta').innerHTML.includes('data-series'));
assert(!element('delta').innerHTML.includes('data-series'));
assert(element('projection-warning').textContent.includes('cannot independently satisfy full report admission'));
for(const id of ['requested-delta','applied-delta','residual-delta','derivative-delta','speed'])
  assert(!/NaN|Infinity/.test(element(id).innerHTML));
console.log('V2 raw aligned deltas and controls PASS');
"""
    result=subprocess.run([node,'-e',harness,str(SCRIPT)],input=canonical(bundle),capture_output=True,timeout=10)
    self.assertEqual(result.returncode,0,result.stderr.decode())

if __name__=='__main__':
  unittest.main()
