"""Post-evaluation explanation, never candidate selection or qualification."""
import json
from pathlib import Path
import statistics

from openpilot.tools.cyber_autotune import curvature_yaw_v2_search as search
from openpilot.tools.cyber_autotune.native_protocol import canonical,digest,_unique_pairs,_invalid_constant

POLICY_SHA='1daffb92010e4bdf58b9fd0d12d8c6fba415b6ab9a1300695329610a41fe7c98'
CELL=('speed_bucket','curvature_magnitude','curvature_sign','phase')
SERIES=('requested_torque','applied_normalized_torque','command_derivative_per_s','torque_derivative_per_s',
        'curvature_residual_1pm','native_aligned_residual_1pm','steering_angle_deg','steering_angle_residual_deg','pose_y_m')


def load_policy(raw=None):
  raw=Path(__file__).with_name('candidate_v2_rejection_policy.json').read_bytes() if raw is None else raw
  if type(raw) is not bytes or digest(raw)!=POLICY_SHA:
    raise ValueError('REJECTION_DIAGNOSTIC_POLICY_DRIFT')
  return json.loads(raw,object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant)


def _family(metric):
  if 'derivative' in metric:
    return 'TORQUE_DERIVATIVE'
  if metric=='saturation_occupancy':
    return 'SATURATION'
  if metric in ('reversals','zero_crossings'):
    return 'SIGN_EVENTS'
  return 'TRACKING'


def _context(samples,indexes):
  rows=[samples[i] for i in indexes]
  return {**{k:{'min':min(r[k] for r in rows),'max':max(r[k] for r in rows),
                'mean':statistics.fmean(r[k] for r in rows)} for k in SERIES},
          'saturation_steps':[r['step_index'] for r in rows if r['saturated']],
          'inactive_steps':[r['step_index'] for r in rows if not r['active']],
          'pressed_steps':[r['step_index'] for r in rows if r['steering_pressed']]}


def divergence(samples,reference,indexes=None):
  """Exact differences, not thresholded onset or proof of a unique cause."""
  indexes=list(range(len(samples))) if indexes is None else indexes
  result={}
  for key in SERIES:
    different=[i for i in indexes if samples[i][key]!=reference[i][key]]
    first=different[0] if different else None
    peak=max(indexes,key=lambda i:abs(samples[i][key]-reference[i][key]))
    result[key]={'first_step':first,'first_time_s':None if first is None else samples[first]['time_s'],
                 'first_delta':None if first is None else samples[first][key]-reference[first][key],
                 'peak_step':peak,'peak_delta':samples[peak][key]-reference[peak][key]}
  return result


def case_ledger(report):
  search.validate_report(report)
  check=search.compare_summary(search.summarize(report))
  arms=report['arms']
  rows=[]
  for failure in check['failures']:
    indexes=[i for i,s in enumerate(arms[0]['samples']) if all(s[k]==failure[k] for k in CELL)]
    groups=[next(g for g in a['groups'] if all(g[k]==failure[k] for k in CELL)) for a in arms]
    values={role:g[failure['metric']] for role,g in zip(search.ROLES,groups,strict=True)}
    samples=arms[0]['samples']
    key={k:failure[k] for k in ('scenario',*CELL,'metric')}
    row={**key,'violation_id':digest(canonical(key)),
         'metric_family':_family(failure['metric']),'values':values,
         'delta_vs_baseline':failure['value']-values[search.ROLES[0]],
         'delta_vs_v1':failure['value']-values[search.ROLES[2]],
         'threshold':failure['reference'],'rule':'V2 <= BASELINE' if failure['speed_bucket']=='HIGH' else 'V2 <= V1',
         'comparison':'exact IEEE; lower is better; zero tolerance; no weighted compensation',
         'violation_magnitude':failure['delta'],'step_indexes':indexes,
         'time_range_s':[samples[indexes[0]]['time_s'],samples[indexes[-1]]['time_s']],
         'speed_range_mps':[min(samples[i]['speed_mps'] for i in indexes),max(samples[i]['speed_mps'] for i in indexes)],
         'curvature_range_1pm':[min(samples[i]['desired_curvature_1pm'] for i in indexes),
                                max(samples[i]['desired_curvature_1pm'] for i in indexes)],
         'dynamics':{a['arm']:{**_context(a['samples'],indexes),
                     'zero_crossing_steps':[n for n in a['diagnostics']['zero_crossing_steps'] if n in indexes],
                     'reversal_steps':[n for n in a['diagnostics']['reversal_steps'] if n in indexes],
                     'cell_zero_crossings':g['zero_crossings'],'cell_reversals':g['reversals']}
                     for a,g in zip(arms,groups,strict=True)},
         'divergence_vs_baseline':divergence(arms[3]['samples'],samples,indexes),
         'divergence_vs_v1':divergence(arms[3]['samples'],arms[2]['samples'],indexes)}
    rows.append(row)
  return rows


def cluster(rows):
  groups={}
  for row in rows:
    name='/'.join([row['scenario'],row['speed_bucket'],row['phase'],row['metric_family']])
    groups.setdefault(name,[]).append(row['violation_id'])
  return [{'cluster':key,'violation_ids':groups[key],'count':len(groups[key])} for key in sorted(groups)]


def build_ledger(reports,selection,evaluation_freeze):
  verdict=search.classify(reports,selection=selection,expected_selection_sha256=selection['receipt_sha256'],
                         expected_evaluation_sha256=digest(canonical(evaluation_freeze['manifest_sha256'])))
  if evaluation_freeze['selection_sha256']!=selection['receipt_sha256']:
    raise ValueError('REJECTION_SELECTION_CONTEXT_DRIFT')
  rows=[r for report in reports for r in case_ledger(report)]
  if verdict['status']!='REJECTED' or len(rows)!=load_policy()['expected_violation_count']:
    raise ValueError('INCOMPLETE_37_REJECTION_LEDGER')
  result={'version':1,'scope':load_policy()['scope'],'diagnostic_policy_sha256':POLICY_SHA,
          'original_policy_sha256':search.POLICY_SHA,'original_status':'REJECTED','violation_count':len(rows),
          'source_report_receipts':[r['receipt_sha256'] for r in reports],
          'evaluation_manifest_list_sha256':verdict['evaluation_manifest_list_sha256'],
          'selection_sha256':selection['receipt_sha256'],'original_failure_list_sha256':digest(canonical(verdict['failures'])),
          'violations':rows,'clusters':cluster(rows),
          'divergence':{r['manifest']['scenario']:{'vs_baseline':divergence(r['arms'][3]['samples'],r['arms'][0]['samples']),
                                                 'vs_v1':divergence(r['arms'][3]['samples'],r['arms'][2]['samples'])}
                        for r in reports if r['manifest']['scenario'] in load_policy()['scenarios']},
          'real_performance_status':'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE',
          'vehicle_status':load_policy()['vehicle_status'],'performance_qualified':False}
  result['receipt_sha256']=digest(canonical(result))
  return result


def freeze_ablations():
  policy=load_policy()
  cases=[search.build_case(name,axis['config'],role='STRESS') for axis in policy['ablations'] for name in policy['scenarios']]
  freeze={'scope':policy['scope'],'diagnostic_policy_sha256':POLICY_SHA,'native_runs':policy['native_runs'],
          'source_sha256':digest(Path(__file__).read_bytes()),
          'manifest_sha256':[digest(canonical(c['manifest'])) for c in cases]}
  freeze['receipt_sha256']=digest(canonical(freeze))
  return cases,freeze


def decide_family(reports,freeze):
  policy=load_policy()
  if (len(reports)!=8 or freeze['diagnostic_policy_sha256']!=POLICY_SHA
      or freeze['source_sha256']!=digest(Path(__file__).read_bytes())
      or freeze['receipt_sha256']!=digest(canonical({k:v for k,v in freeze.items() if k!='receipt_sha256'}))
      or [r['manifest_sha256'] for r in reports]!=freeze['manifest_sha256']):
    raise ValueError('INCOMPLETE_OR_UNFROZEN_ABLATION_MATRIX')
  shared=('native_source','support_files','environment','plant_config','initial_state','frames','phase_labels','car_params_sha256')
  for offset in (0,1):
    reference=reports[offset]['manifest']
    for report in reports[offset::2]:
      if any(canonical(report['manifest'][k])!=canonical(reference[k]) for k in shared):
        raise ValueError('ABLATION_COMMON_SOURCE_INPUT_OR_PLANT_DRIFT')
  results=[]
  for i,axis in enumerate(policy['ablations']):
    pair=reports[2*i:2*i+2]
    if any(r['manifest']['scenario']!=name or r['manifest']['config']!=axis['config']
           or r['manifest']['role']!='STRESS' or r['manifest']['perturbation']!={}
           for r,name in zip(pair,policy['scenarios'],strict=True)):
      raise ValueError('ABLATION_CONTAMINATION')
    summaries=[search.summarize(r) for r in pair]
    failures=[f for s in summaries for f in search.compare_summary(s)['failures']]
    results.append({'name':axis['name'],'config':axis['config'],'report_receipts':[r['receipt_sha256'] for r in pair],
                    'hard_pass':True,'failure_count':len(failures),'failures':failures,
                    'identities':[r['manifest']['identities'][3] for r in pair]})
  verdict='FAMILY_REDESIGN' if all(r['failure_count'] for r in results) else 'FAMILY_RESTRICT'
  result={'version':1,'diagnostic_policy_sha256':POLICY_SHA,'matrix_freeze_sha256':freeze['receipt_sha256'],
          'verdict':verdict,'ablation_results':results,
          'v2_status':'REJECTED','v3_created':False,'selection_permitted':False,
          'reason':'all four component ablations violate original cellwise rules' if verdict=='FAMILY_REDESIGN'
                   else 'a diagnostic lead only; separate prospective experiment required',
          'evidence_tier':'EXPOSED_SYNTHETIC_POST_EVALUATION_DIAGNOSTIC',
          'real_performance_status':'BLOCKED: INDEPENDENT_REFERENCE_UNAVAILABLE','vehicle_status':policy['vehicle_status']}
  result['receipt_sha256']=digest(canonical(result))
  return result



def validate_observation_freeze(observed,freeze):
  if (observed['producer_source_sha256']!=freeze['diagnostic_producer_source_sha256']
      or observed['supervisor_source_sha256']!=freeze['diagnostic_supervisor_source_sha256']):
    raise ValueError('PASSIVE_OBSERVATION_NOT_FROM_FROZEN_SOURCE')


def run_investigation(source_dir,output_dir):
  """Fresh bounded ablations; old final evaluation is never used to reselect."""
  from openpilot.tools.cyber_autotune.curvature_yaw_diagnostics import run_diagnostics,WORKER
  source_dir,output_dir=Path(source_dir),Path(output_dir)
  def read(name):
    raw=(source_dir/name).read_bytes()
    if len(raw)>32*1024*1024:
      raise ValueError('OVERSIZED_HISTORICAL_INPUT')
    return json.loads(raw,object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant)
  original=read('evaluation.json')['reports']
  ledger=build_ledger(original,read('selection.json'),read('evaluation-freeze.json'))
  cases,freeze=freeze_ablations()
  freeze.update(original_ledger_sha256=ledger['receipt_sha256'],
                diagnostic_producer_source_sha256=digest(WORKER.read_bytes()),
                diagnostic_supervisor_source_sha256=digest(WORKER.with_name('curvature_yaw_diagnostics.py').read_bytes()))
  freeze['receipt_sha256']=digest(canonical({k:v for k,v in freeze.items() if k!='receipt_sha256'}))
  output_dir.mkdir(parents=True,exist_ok=False)
  def write(name,value):
    (output_dir/name).write_bytes(canonical(value)+b'\n')
  write('matrix-freeze.json',freeze)
  write('violation-ledger.json',ledger)
  reports=[]
  observations=[]
  for i,case in enumerate(cases):
    report=search.run_case(case,expected_manifest_sha256=freeze['manifest_sha256'][i],timeout_s=30.)
    reports.append(report)
    write(f'case-{i}.json',report)
    print('case',i,case['scenario'],'failures',len(case_ledger(report)),flush=True)
    if i<2:
      historic=next(r for r in original if r['manifest']['scenario']==case['scenario'])
      if [a['samples'] for a in report['arms']]!=[a['samples'] for a in historic['arms']]:
        raise ValueError('HISTORIC_DYNAMICS_NOT_REPRODUCED')
      for arm,request in zip(report['arms'],case['requests'],strict=True):
        observed=run_diagnostics(request,arm['native_result'])
        validate_observation_freeze(observed,freeze)
        observations.append({'scenario':case['scenario'],'arm':arm['arm'],'identity':arm['identity'],'diagnostic':observed})
        write('pid-'+case['scenario']+'-'+arm['arm']+'.json',observations[-1])
        print('passive',case['scenario'],arm['arm'],'EXACT',flush=True)
  if (freeze['diagnostic_producer_source_sha256']!=digest(WORKER.read_bytes())
      or freeze['diagnostic_supervisor_source_sha256']!=digest(WORKER.with_name('curvature_yaw_diagnostics.py').read_bytes())):
    raise ValueError('DIAGNOSTIC_SOURCE_CHANGED_AFTER_FREEZE')
  decision=decide_family(reports,freeze)
  write('family-decision.json',decision)
  summary={'matrix_freeze':freeze,'decision':decision,'original_ledger_sha256':ledger['receipt_sha256'],
           'case_summaries':[search.summarize(r) for r in reports],
           'passive_receipts':[{'scenario':o['scenario'],'arm':o['arm'],'identity':o['identity'],
                                'producer_source_sha256':o['diagnostic']['producer_source_sha256'],
                                'supervisor_source_sha256':o['diagnostic']['supervisor_source_sha256'],
                                'receipt_sha256':o['diagnostic']['receipt_sha256'],
                                'repetition_sha256':o['diagnostic']['repetition_sha256']} for o in observations]}
  summary['receipt_sha256']=digest(canonical(summary))
  write('investigation-summary.json',summary)
  return summary


if __name__=='__main__':
  import argparse
  parser=argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--source-dir',required=True)
  parser.add_argument('--output-dir',required=True)
  args=parser.parse_args()
  run_investigation(args.source_dir,args.output_dir)
