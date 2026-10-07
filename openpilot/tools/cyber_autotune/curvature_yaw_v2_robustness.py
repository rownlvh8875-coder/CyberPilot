"""Frozen one-at-a-time synthetic sensitivity; never calibrated vehicle uncertainty."""
import json
from pathlib import Path

from openpilot.tools.cyber_autotune.curvature_yaw_v2_search import (
  POLICY_SHA, load_policy, build_case, execute_case, compare_summary, admitted_summary,
  _classify_admitted, validate_selection, classify,
)
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest, _hex, _keys, _unique_pairs, _invalid_constant


def matrix():
  policy=load_policy()['robustness']
  cases=[{'scenario':policy['scenario'],'perturbation':{}}]
  for axis,spec in sorted(policy['axes'].items()):
    name='reengage_high' if axis in ('pressed_shift_steps','reengage_shift_steps') else policy['scenario']
    cases.extend({'scenario':name,'perturbation':{axis:value}} for value in spec['choices'])
  if len(cases)!=policy['case_count']:
    raise ValueError('ROBUSTNESS_POLICY_COUNT_DRIFT')
  return cases


def freeze_matrix(config,*,selection_sha256=None):
  cases=[build_case(c['scenario'],config,role='STRESS',perturbation=c['perturbation'],
                    selection_sha256=selection_sha256) for c in matrix()]
  return cases,[digest(canonical(c['manifest'])) for c in cases]


def _aggregate_admitted(summaries,selection_sha256,scope):
  if not _hex(selection_sha256,64) or not summaries or any(s['role']!='STRESS' for s in summaries):
    raise ValueError('INVALID_STRESS_SCOPE_OR_SELECTION')
  hard=[s for s in summaries if s['hard_pass'] is not True]
  good=[s for s in summaries if s['hard_pass'] is True]
  checks=[compare_summary(s) for s in good]
  failures=[dict(f,perturbation=s['perturbation'],case_receipt_sha256=s['receipt_sha256'])
            for s,c in zip(good,checks,strict=True) for f in c['failures']]
  regressions={}
  for failure in failures:
    key=failure['speed_bucket']+':'+failure['metric']
    regressions[key]=regressions.get(key,0)+1
  all_deltas=[]
  for summary in good:
    for b,v1,v2 in zip(summary['groups'][0],summary['groups'][2],summary['groups'][3],strict=True):
      cell={k:v2[k] for k in ('speed_bucket','curvature_magnitude','curvature_sign','phase','count')}
      for metric in load_policy()['metrics']:
        all_deltas.append({'scenario':summary['scenario'],'perturbation':summary['perturbation'],
                           'case_receipt_sha256':summary['receipt_sha256'],**cell,'metric':metric,
                           'value':v2[metric],'baseline':b[metric],'v1':v1[metric],
                           'delta_vs_baseline':v2[metric]-b[metric],'delta_vs_v1':v2[metric]-v1[metric]})
  # Separate metrics/units: never rank unrelated dimensions by one maximum.
  worst={key:{metric:max((r for r in all_deltas if r['metric']==metric),key=lambda r:r[key],default=None)
              for metric in load_policy()['metrics']} for key in ('value','baseline','v1','delta_vs_baseline','delta_vs_v1')}
  verdict=_classify_admitted(summaries)
  result={'version':1,'policy_sha256':POLICY_SHA,'selection_sha256':selection_sha256,'scope':scope,
          'producer_source_sha256':digest(Path(__file__).read_bytes()),'case_count':len(summaries),
          'hard_pass_count':len(good),'hard_failure_count':len(hard),
          'no_worse_screen_pass_count':sum(not c['failures'] for c in checks),'hard_failures':hard,
          'regression_buckets':regressions,'failures':failures,'worst_by_metric':worst,
          'case_receipts':[s['receipt_sha256'] for s in summaries],'status':verdict['status'],
          'performance_qualified':False,'real_performance_status':'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE',
          'vehicle_status':load_policy()['vehicle_status'],'reference_status':'NO INDEPENDENT LANE TRUTH'}
  result['receipt_sha256']=digest(canonical(result))
  return result


def aggregate_case(report):
  # Explicit diagnostic partial case; cannot claim complete robustness coverage.
  summary=admitted_summary(report)
  sha=summary['selection_sha256'] or digest(canonical({'scope':'UNSELECTED_STRESS_DIAGNOSTIC'}))
  return _aggregate_admitted([summary],sha,'PARTIAL_CASE_DIAGNOSTIC_NOT_FROZEN_MATRIX')


def bind_evaluation(selection,reports,freeze):
  """Admit final evaluation before stress; stress cannot reselect or erase rejection."""
  _keys(freeze,('selection_sha256','manifest_sha256'))
  sha=selection['receipt_sha256']
  if freeze['selection_sha256']!=sha:
    raise ValueError('STRESS_EVALUATION_SELECTION_FREEZE_DRIFT')
  verdict=classify(reports,selection=selection,expected_selection_sha256=sha,
                   expected_evaluation_sha256=digest(canonical(freeze['manifest_sha256'])))
  context={'selection_sha256':sha,'evaluation_verdict':verdict,
           'evaluation_input_sha256':digest(canonical(reports)),
           'evaluation_freeze_sha256':digest(canonical(freeze))}
  context['receipt_sha256']=digest(canonical(context))
  return context


def bind_final_status(diagnostic,context):
  # Preserve both statuses. A favorable stress subset never promotes a rejected selection.
  result=json.loads(canonical(diagnostic))
  result.pop('receipt_sha256')
  result['stress_screen_status']=result['status']
  result['selected_candidate_status']=context['evaluation_verdict']['status']
  result['evaluation_context']=context
  if result['selected_candidate_status']=='REJECTED' or result['hard_failure_count']:
    result['status']='REJECTED'
  result['receipt_sha256']=digest(canonical(result))
  return result


def aggregate(reports,*,selection,expected_selection_sha256,expected_matrix_sha256,evaluation_reports,evaluation_freeze):
  context=bind_evaluation(selection,evaluation_reports,evaluation_freeze)
  validate_selection(selection,expected_selection_sha256)
  summaries=[admitted_summary(r) for r in reports]
  if ([{'scenario':s['scenario'],'perturbation':s['perturbation']} for s in summaries]!=matrix()
      or any(s['role']!='STRESS' or s['config']!=selection['selected_config']
             or s['selection_sha256']!=expected_selection_sha256 for s in summaries)
      or digest(canonical([s['manifest_sha256'] for s in summaries]))!=expected_matrix_sha256):
    raise ValueError('INCOMPLETE_OR_UNSELECTED_FROZEN_STRESS_MATRIX')
  result=_aggregate_admitted(summaries,expected_selection_sha256,'SYNTHETIC_ROBUSTNESS_STRESS_NOT_VEHICLE_UNCERTAINTY')
  result['matrix_manifest_list_sha256']=expected_matrix_sha256
  return bind_final_status(result,context)


def run_robustness(selection,output_directory,*,evaluation_reports,evaluation_freeze):
  sha=selection['receipt_sha256']
  validate_selection(selection,sha)
  if selection['selected_config'] is None:
    raise ValueError('NO_DEVELOPMENT_SELECTED_CONFIG')
  selection=json.loads(canonical(selection))
  evaluation_reports=json.loads(canonical(evaluation_reports))
  evaluation_freeze=json.loads(canonical(evaluation_freeze))
  context=bind_evaluation(selection,evaluation_reports,evaluation_freeze)
  out=Path(output_directory)
  out.mkdir(parents=True,exist_ok=True)
  if any(out.iterdir()):
    raise ValueError('FRESH_STRESS_DIRECTORY_REQUIRED')
  source_sha=digest(Path(__file__).read_bytes())
  cases,hashes=freeze_matrix(selection['selected_config'],selection_sha256=sha)
  freeze={'policy_sha256':POLICY_SHA,'selection_sha256':sha,'producer_source_sha256':source_sha,
          'evaluation_context':context,'manifests_sha256':hashes,'matrix_sha256':digest(canonical(hashes))}
  frozen=canonical(freeze)
  (out/'matrix-freeze.json').write_bytes(frozen+b'\n')
  reports,summaries=[],[]
  for case,manifest_sha in zip(cases,hashes,strict=True):
    if (out/'matrix-freeze.json').read_bytes()!=frozen+b'\n' or digest(Path(__file__).read_bytes())!=source_sha:
      raise ValueError('STRESS_MATRIX_OR_PRODUCER_FREEZE_DRIFT')
    report,summary=execute_case(case,manifest_sha)
    (out/(manifest_sha+'.json')).write_bytes(canonical(report)+b'\n')
    reports.append(report)
    summaries.append(summary)
    print('STRESS_COMPLETED',case['scenario'],case['perturbation'],summary['hard_pass'],flush=True)
  if digest(Path(__file__).read_bytes())!=source_sha:
    raise ValueError('STRESS_PRODUCER_DRIFT_DURING_EXECUTION')
  result={'aggregate':aggregate(reports,selection=selection,expected_selection_sha256=sha,
                                expected_matrix_sha256=freeze['matrix_sha256'],
                                evaluation_reports=evaluation_reports,evaluation_freeze=evaluation_freeze),'cases':summaries}
  result['receipt_sha256']=digest(canonical(result))
  (out/'robustness-summary.json').write_bytes(canonical(result)+b'\n')
  return result


if __name__=='__main__':
  import argparse
  parser=argparse.ArgumentParser(description='Synthetic stress only; no qualification.')
  parser.add_argument('--selection',type=Path,required=True)
  parser.add_argument('--evaluation',type=Path,required=True)
  parser.add_argument('--evaluation-freeze',type=Path,required=True)
  parser.add_argument('--output-directory',type=Path,required=True)
  args=parser.parse_args()
  def read(path):
    return json.loads(path.read_bytes(),object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant)
  run_robustness(read(args.selection),args.output_directory,
                 evaluation_reports=read(args.evaluation)['reports'],evaluation_freeze=read(args.evaluation_freeze))
