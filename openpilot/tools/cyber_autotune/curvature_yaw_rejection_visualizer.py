"""37-cell rejection viewer: original admission, exact data, no real lane claim."""
import copy
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import curvature_yaw_v2_visualizer as viewer
from openpilot.tools.cyber_autotune import curvature_yaw_rejection as rejection
from openpilot.tools.cyber_autotune.curvature_yaw_rejection_export import export_results,read
from openpilot.tools.cyber_autotune.native_protocol import canonical,digest

SCRIPT=Path(__file__).with_suffix('.js')
DATA_START='<script id="screening-data" type="application/json">'


def case_view(report):
  view=viewer.project(report)
  view['schedules']={a['arm']:copy.deepcopy(a['native_result']['effective_parameters']) for a in report['arms']}
  view['case_violations']=rejection.case_ledger(report)
  view['display_projection_sha256']=digest(canonical({k:v for k,v in view.items() if k!='display_projection_sha256'}))
  return view


def _html(bundle):
  controls="""<section class="panel"><h2>Frozen V2 rejection · 37 metric/cell violations</h2>
<p id="family-decision"></p><label><input type="checkbox" id="v1-overlay" checked>V1 overlay</label>
<label for="violation-cluster">Violation cluster</label><select id="violation-cluster"></select>
<p id="violation-count"></p><p class="muted">Click a violation to jump to its original first step.
White marker = exact V2/V1 requested divergence. Scalar rows retain their original metric units.
Factor/friction plots show delta vs baseline; absolute values appear at the cursor.</p>
<div style="overflow:auto"><table><thead><tr><th>Scenario / cell / metric</th><th>Baseline</th><th>Current</th>
<th>V1</th><th>V2</th><th>Δ baseline</th><th>Δ V1</th><th>Violation</th><th>Rule</th></tr></thead>
<tbody id="violation-rows"></tbody></table></div><pre id="rejection-readout"></pre></section>"""
  panels=''.join('<div class="panel"><h2>'+title+'</h2><svg id="' +panel_id+
    '" viewBox="0 0 860 250" role="img" aria-label="'+title+'"></svg></div>' for panel_id,title in
    [('factor-schedule','Factor schedule delta'),('friction-schedule','Friction schedule delta'),
     ('command-derivative','Requested torque derivative'),('applied-derivative','Applied delayed torque derivative'),
     ('pid_p','Passive PID P'),('pid_i','Passive PID I'),('pid_f','Passive PID feedforward'),('pid_control','Passive PID control')])
  data=canonical(bundle).decode().replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
  data=data.replace('\u2028','\\u2028').replace('\u2029','\\u2029')
  template=viewer.TEMPLATE.read_text().replace('<div class="grid">',controls+'<div class="grid">'+panels)
  return template.replace('@@DATA@@',data).replace('@@SCRIPT@@',viewer.SCRIPT.read_text()+'\n'+SCRIPT.read_text())


def render_html(payload,*,run_dir=None,evaluation_dir=None):
  # Shared renderer performs full evaluation and optional stress evidence admission.
  if 'selection' not in payload or 'evaluation_manifest_list_sha256' not in payload:
    raise ValueError('FROZEN_EVALUATION_REQUIRED')
  html=viewer.render_html(payload)
  bundle=json.loads(html.split(DATA_START,1)[1].split('</script>',1)[0])
  freeze={'selection_sha256':payload['selection']['receipt_sha256'],
          'manifest_sha256':[r['manifest_sha256'] for r in payload['reports']]}
  ledger=rejection.build_ledger(payload['reports'],payload['selection'],freeze)
  bundle['reports']=[case_view(r) for r in payload['reports']]
  bundle['rejection']={'ledger':ledger,'family_decision':None,'scope':'SYNTHETIC_REJECTION_ATTRIBUTION_NO_LANE_TRUTH'}
  if run_dir is not None:
    if evaluation_dir is None:
      raise ValueError('ORIGINAL_EVALUATION_SOURCE_REQUIRED')
    admitted,decision,_,_=export_results(run_dir,evaluation_dir)
    if admitted!=ledger:
      raise ValueError('VIEWER_ABLATION_ORIGINAL_LEDGER_MISMATCH')
    bundle['rejection']['family_decision']=decision
    for i in (0,1):
      report=read(Path(run_dir)/f'case-{i}.json')
      view=next(v for v in bundle['reports'] if v['manifest']['scenario']==report['manifest']['scenario'])
      view['passive_pid']={}
      for arm in report['arms']:
        record=read(Path(run_dir)/('pid-'+report['manifest']['scenario']+'-'+arm['arm']+'.json'))
        diagnostic=record['diagnostic']
        view['passive_pid'][arm['arm']]={k:diagnostic[k] for k in
            ('observations','receipt_sha256','producer_source_sha256','supervisor_source_sha256','request_sha256')}
        view['passive_pid'][arm['arm']]['source_full_report_receipt_sha256']=report['receipt_sha256']
      view['display_projection_sha256']=digest(canonical({k:v for k,v in view.items() if k!='display_projection_sha256'}))
  bundle['artifact'].update(rejection_renderer_sha256=digest(Path(__file__).read_bytes()),
                            rejection_script_sha256=digest(SCRIPT.read_bytes()),rejection_ledger_sha256=ledger['receipt_sha256'])
  return _html(bundle)


if __name__=='__main__':
  import argparse
  parser=argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--evaluation-dir',required=True)
  parser.add_argument('--run-dir',required=True)
  parser.add_argument('--output',required=True)
  args=parser.parse_args()
  directory=Path(args.evaluation_dir)
  payload=read(directory/'evaluation.json')
  selection=read(directory/'selection.json')
  freeze=read(directory/'evaluation-freeze.json')
  if freeze['selection_sha256']!=selection['receipt_sha256']:
    raise ValueError('VIEWER_SELECTION_FREEZE_DRIFT')
  payload.update(selection=selection,evaluation_manifest_list_sha256=digest(canonical(freeze['manifest_sha256'])))
  Path(args.output).write_text(render_html(payload,run_dir=args.run_dir,evaluation_dir=directory))
