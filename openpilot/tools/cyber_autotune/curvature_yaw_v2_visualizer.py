"""Validated V2 receipts projected for the shared synthetic-only viewer."""
import copy
import json
from pathlib import Path

from openpilot.tools.cyber_autotune.curvature_yaw_v2_search import validate_report, summarize, compare_summary, classify, classify_case, load_policy
from openpilot.tools.cyber_autotune.curvature_yaw_visualizer import TEMPLATE, SCRIPT
from openpilot.tools.cyber_autotune.curvature_yaw_v2_robustness import aggregate
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest, _keys, _unique_pairs, _invalid_constant

MAX_INPUT_BYTES=32*1024*1024  # bounded synthetic transport, not acceptance threshold


def project(report):
  validate_report(report)
  view=copy.deepcopy(report)
  summary=summarize(report)
  view['arms']=[view['arms'][0],view['arms'][1],view['arms'][3]]
  view['attribution']={'status':classify_case(report)['status'],'comparison':compare_summary(summary),
                       'v1_arm':copy.deepcopy(report['arms'][2]),
                       'scope':'RAW_ALIGNED_SYNTHETIC_DIAGNOSTICS_NO_LANE_TRUTH'}
  # Native proofs were validated above; display projection preserves exact samples/identities.
  for arm in view['arms']+[view['attribution']['v1_arm']]:
    arm.pop('native_result')
  view.pop('receipt_sha256')
  view['projection']={'source_full_report_receipt_sha256':report['receipt_sha256'],'native_proofs_omitted':True,
                      'scope':'DISPLAY_PROJECTION_NOT_AN_INDEPENDENTLY_ADMISSIBLE_RECEIPT'}
  view['display_projection_sha256']=digest(canonical(view))
  return view


def render_html(payload):
  context='selection' in payload
  stress='stress_evidence' in payload
  if stress and not context:
    raise ValueError('STRESS_DISPLAY_REQUIRES_FROZEN_EVALUATION_CONTEXT')
  fields=('reports','selection','evaluation_manifest_list_sha256') if context else ('reports',)
  _keys(payload,fields+('stress_evidence',) if stress else fields)
  reports=payload['reports']
  if type(reports) is not list or not 1<=len(reports)<=len(load_policy()['evaluation']):
    raise ValueError('INVALID_V2_DISPLAY_COUNT')
  names=[r['manifest']['scenario'] for r in reports]
  if len(set(names))!=len(names):
    raise ValueError('DUPLICATE_V2_DISPLAY_SCENARIO')
  verdict=classify(reports,selection=payload['selection'],expected_selection_sha256=payload['selection']['receipt_sha256'],
                   expected_evaluation_sha256=payload['evaluation_manifest_list_sha256']) if context else None
  robustness=None
  if stress:
    evidence=payload['stress_evidence']
    _keys(evidence,('reports','freeze'))
    freeze=evidence['freeze']
    _keys(freeze,('policy_sha256','selection_sha256','producer_source_sha256','evaluation_context',
                  'manifests_sha256','matrix_sha256'))
    selection=payload['selection']
    evaluation_freeze={'selection_sha256':selection['receipt_sha256'],
                       'manifest_sha256':[r['manifest_sha256'] for r in reports]}
    robustness=aggregate(evidence['reports'],selection=selection,
                         expected_selection_sha256=selection['receipt_sha256'],
                         expected_matrix_sha256=freeze['matrix_sha256'],
                         evaluation_reports=reports,evaluation_freeze=evaluation_freeze)
    if (freeze['selection_sha256']!=selection['receipt_sha256']
        or freeze['policy_sha256']!=robustness['policy_sha256']
        or freeze['manifests_sha256']!=[r['manifest_sha256'] for r in evidence['reports']]
        or freeze['evaluation_context']!=robustness['evaluation_context']
        or freeze['producer_source_sha256']!=robustness['producer_source_sha256']):
      raise ValueError('DISPLAY_STRESS_FREEZE_CONTEXT_DRIFT')
  value={'reports':[project(r) for r in reports],'evaluation_verdict':verdict,'robustness':robustness,'artifact':{
    'input_sha256':digest(canonical(payload)),'renderer_sha256':digest(Path(__file__).read_bytes()),
    'template_sha256':digest(TEMPLATE.read_bytes()),'script_sha256':digest(SCRIPT.read_bytes()),
    'scope':'VALIDATED_V2_DISPLAY_PROJECTION_INTERNAL_CONSISTENCY_NOT_AUTHENTICATED_EXECUTION'}}
  data=canonical(value).decode().replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
  data=data.replace('\u2028','\\u2028').replace('\u2029','\\u2029')
  return TEMPLATE.read_text().replace('@@DATA@@',data).replace('@@SCRIPT@@',SCRIPT.read_text())


def load_payload(path):
  with Path(path).open('rb') as stream:
    raw=stream.read(MAX_INPUT_BYTES+1)
  if not 0<len(raw)<=MAX_INPUT_BYTES:
    raise ValueError('INVALID_V2_DISPLAY_INPUT_SIZE')
  payload=json.loads(raw,object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant)
  render_html(payload)  # admission before any output write
  return payload


if __name__=='__main__':
  import argparse
  parser=argparse.ArgumentParser(description='V2 synthetic attribution viewer, no lane/vehicle truth.')
  parser.add_argument('--input',type=Path,required=True)
  parser.add_argument('--output',type=Path,required=True)
  parser.add_argument('--selection',type=Path)
  parser.add_argument('--evaluation-freeze',type=Path)
  parser.add_argument('--stress-directory',type=Path)
  args=parser.parse_args()
  payload=load_payload(args.input)
  if args.selection is not None or args.evaluation_freeze is not None:
    if args.selection is None or args.evaluation_freeze is None:
      parser.error('selection and evaluation freeze must be provided together')
    selection=json.loads(args.selection.read_bytes(),object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant)
    freeze=json.loads(args.evaluation_freeze.read_bytes(),object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant)
    _keys(freeze,('selection_sha256','manifest_sha256'))
    if freeze['selection_sha256']!=selection['receipt_sha256']:
      raise ValueError('DISPLAY_SELECTION_FREEZE_MISMATCH')
    payload.update(selection=selection,evaluation_manifest_list_sha256=digest(canonical(freeze['manifest_sha256'])))
  if args.stress_directory is not None:
    if args.selection is None or args.evaluation_freeze is None:
      parser.error('stress display requires selection and evaluation freeze')
    def read_stress(path):
      with path.open('rb') as stream:
        raw=stream.read(MAX_INPUT_BYTES+1)
      if not 0<len(raw)<=MAX_INPUT_BYTES:
        raise ValueError('INVALID_STRESS_DISPLAY_FILE_SIZE')
      return json.loads(raw,object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant)
    freeze=read_stress(args.stress_directory/'matrix-freeze.json')
    from openpilot.tools.cyber_autotune.native_protocol import _hex
    hashes=freeze['manifests_sha256']
    if type(hashes) is not list or len(hashes)!=load_policy()['robustness']['case_count'] or not all(_hex(h,64) for h in hashes):
      raise ValueError('INVALID_STRESS_DISPLAY_MANIFEST_LIST')
    payload['stress_evidence']={'freeze':freeze,'reports':[read_stress(args.stress_directory/(h+'.json')) for h in hashes]}
  args.output.write_text(render_html(payload))
