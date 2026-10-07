"""Publish derived synthetic explanation only; full native proofs stay local."""
import json
from pathlib import Path
from collections import Counter

from openpilot.tools.cyber_autotune import curvature_yaw_rejection as rejection
from openpilot.tools.cyber_autotune import curvature_yaw_v2_search as search
from openpilot.tools.cyber_autotune.curvature_yaw_diagnostics import validate_diagnostics
from openpilot.tools.cyber_autotune.curvature_yaw_candidate_history import append_history,QUALIFICATION
from openpilot.tools.cyber_autotune.native_protocol import canonical,digest,_unique_pairs,_invalid_constant


def read(path):
  with Path(path).open('rb') as stream:
    raw=stream.read(32*1024*1024+1)
  if not 0<len(raw)<=32*1024*1024:
    raise ValueError('BOUNDED_SYNTHETIC_INPUT_REQUIRED')
  return json.loads(raw,object_pairs_hook=_unique_pairs,parse_constant=_invalid_constant)


def request_for_report(report,index):
  m=report['manifest']
  request=search.build_case(m['scenario'],m['config'],role=m['role'],perturbation=m['perturbation'],
                            selection_sha256=m['selection_sha256'])['requests'][index]
  request['native']['source']=m['native_source']
  request['support_files']=m['support_files']
  return request



def validate_evidence_linkage(ledger,matrix,original,reports):
  if (matrix['original_ledger_sha256']!=ledger['receipt_sha256'] or matrix['native_runs']!=64
      or matrix['scope']!=rejection.load_policy()['scope']):
    raise ValueError('MATRIX_ORIGINAL_LEDGER_BINDING_DRIFT')
  for report in reports[:2]:
    historic=next(r for r in original if r['manifest']['scenario']==report['manifest']['scenario'])
    if [a['samples'] for a in report['arms']]!=[a['samples'] for a in historic['arms']]:
      raise ValueError('HISTORIC_DYNAMICS_NOT_REPRODUCED')


def export_results(run_dir,evaluation_dir):
  run_dir,evaluation_dir=Path(run_dir),Path(evaluation_dir)
  original=read(evaluation_dir/'evaluation.json')['reports']
  selection=read(evaluation_dir/'selection.json')
  freeze=read(evaluation_dir/'evaluation-freeze.json')
  ledger=rejection.build_ledger(original,selection,freeze)
  if ledger!=read(run_dir/'violation-ledger.json'):
    raise ValueError('ORIGINAL_LEDGER_DRIFT')
  matrix=read(run_dir/'matrix-freeze.json')
  reports=[read(run_dir/f'case-{i}.json') for i in range(8)]
  validate_evidence_linkage(ledger,matrix,original,reports)
  decision=rejection.decide_family(reports,matrix)
  if decision!=read(run_dir/'family-decision.json'):
    raise ValueError('FAMILY_DECISION_DRIFT')
  observations={}
  for report in reports[:2]:
    name=report['manifest']['scenario']
    observations[name]={}
    for i,arm in enumerate(report['arms']):
      record=read(run_dir/('pid-'+name+'-'+arm['arm']+'.json'))
      if record['scenario']!=name or record['arm']!=arm['arm'] or record['identity']!=arm['identity']:
        raise ValueError('PID_ARM_BINDING_DRIFT')
      diagnostic=record['diagnostic']
      rejection.validate_observation_freeze(diagnostic,matrix)
      validate_diagnostics(request_for_report(report,i),arm['native_result'],diagnostic)
      observations[name][arm['arm']]=diagnostic
  evidence=[]
  for report in reports[:2]:
    name=report['manifest']['scenario']
    arms=observations[name]
    b,v1,v2=[arms[role]['observations'] for role in (search.ROLES[0],search.ROLES[2],search.ROLES[3])]
    unchanged={field:all(x[field]==y[field]==z[field] for x,y,z in zip(b,v1,v2,strict=True))
               for field in ('kp',
      'ki',
      'delay_frames',
      'lookahead_index',
      'history_sha256',
      'raw_jerk',
      'filtered_jerk')}
    points=[41,120,280,304,400] if name=='sharp_mid_left' else [200,201,280,292,300,333,400]
    evidence.append({'scenario':name,'unchanged_observables':unchanged,
      'samples':[{'step_index':n,'time_s':report['arms'][0]['samples'][n]['time_s'],
                  'speed_mps':report['arms'][0]['samples'][n]['speed_mps'],'phase':report['arms'][0]['samples'][n]['phase'],
                  'arm_observations':{role:arms[role]['observations'][n] for role in search.ROLES}} for n in points],
      'pid_clipping_steps':{role:[r['step_index'] for r in arms[role]['observations'] if r['pid_limit_clipped']] for role in search.ROLES},
      'passive_receipts':{role:{k:arms[role][k] for k in ('receipt_sha256',
      'repetition_sha256',
      'producer_source_sha256',
                                                        'supervisor_source_sha256')} for role in search.ROLES}})
  explanations=[
    ('A',
      'latAccelFactor schedule',
      'HIGH',
      'Factor-only has 39 failures; both deltas removed eliminates MID failures.',
     'Factor-only is not sufficient; friction-only still has 17.',
      'Keep factor delta while altering only friction: observed 17 versus 37 failures.'),
    ('B',
      'friction schedule',
      'HIGH',
      'Friction-only reduces failures to 17; onset at frame41 has zero PID error/P/I and different feedforward.',
     'Factor-only also changes failures; nonlinear interaction prevents additive allocation.',
      'Remove friction correction with factor fixed: observed 39 versus 37 failures.'),
    ('C',
      'speed interpolation',
      'HIGH',
      '17.5 m/s lies in the changed 15..20 interpolation interval; sweep first v2-v1 torque difference frame201 at 15.05 m/s.',
     'Piecewise linear schedules and float32 readback are continuous within quantization, not a large breakpoint jump.',
      'Compare identical inputs through frame200: v1/v2 samples exactly equal.'),
    ('D',
      'breakpoint placement',
      'HIGH',
      'Attenuating knot20 changes interpolation before20; v1 preservation holds only through15, not whole MID bucket.',
     'A different global schedule has not been tested; conclusion is restricted to this frozen family.',
      'Check effective parameters at15,17.5,20 m/s.'),
    ('E',
      'candidate transition slew',
      'NOT_APPLICABLE',
      'No slew mechanism is implemented; only a reject-on-rate bound.',
     'No clamping or lag from a slew filter can explain this run.',
      'Inspect candidate prepare_schedule and unchanged physical delay owner.'),
    ('F',
      'controller history interaction',
      'MEDIUM',
      'Same desired history but feedback paths diverge and carry state across speed buckets.',
     'History hashes are exactly equal in all four arms; history configuration is not a changed cause.',
      'Compare all history hashes, raw jerk and filtered jerk: exact equality.'),
    ('G',
      'lookahead interaction',
      'LOW',
      'Fixed lookahead participates in stock feedforward.',
     'Lookahead index and filtered jerk are exactly equal; no direct changed contribution.',
      'Compare lookahead indexes and filtered jerk across all samples.'),
    ('H',
      'prediction-delay mismatch',
      'UNRESOLVED',
      'Stock input history index16 differs from plant physical2-frame delay; this is common descriptive alignment context.',
     'No delay ablation here; mismatch is not identified as differential v2 cause.',
      'A separately prefrozen prediction-delay experiment would be required; not performed.'),
    ('I',
      'physical plant delay interaction',
      'MEDIUM',
      'Applied requested divergence follows the fixed two-frame plant delay; stress delay1/3 showed equal high-speed v2/baseline outputs.',
     'Existing stress uses constant high speed and does not falsify MID/sweep effects.',
      'Matched MID/sweep delay perturbations would be a new explanatory policy; not performed.'),
    ('J',
      'saturation / anti-windup interaction',
      'MEDIUM',
      'PID clipping is observed and factor changes accel-space limits; final same torque can coexist with different feedback and integral.',
     'Zero of37 failures are saturation-occupancy metrics; saturation alone does not explain entry onset.',
      'Compare unclipped PID sum, limits and integral before/after clipping.'),
    ('K',
      'PID integral carry-over',
      'MEDIUM',
      'Sweep frame300 has baseline factor/friction but different PID I and feedback; differences persist after20.',
     'No integral reset ablation performed; P/feedback differences are larger at frame333.',
      'A separately frozen state intervention would be required to isolate I; not performed.'),
    ('L',
      'sign reversal behavior',
      'LOW',
      'Reversal events occur in generic plant responses and are retained in each violation context.',
     'Zero of37 failures are event-count metrics; both failing desired inputs are nonnegative.',
      'Inspect original event counts and signed command differences; no forced sign-reversal explanation.'),
    ('M',
      'desired curvature dynamics',
      'CONTEXT_ONLY',
      'Identical prescribed desired curvature excites entry/apex/exit; sweep changes v squared targets.',
     'Desired input/history are identical between arms; it cannot explain differential output as a path-quality finding.',
      'Same input/different controller experiment is already executed.'),
    ('N',
      'generic plant artifact',
      'UNRESOLVED',
      'Nominal plant has high oscillation/clipping even in baseline; family conclusions are plant-conditional.',
     'Controlled schedule changes reproducibly change response; absence of real calibration does not erase observed diagnostic violations.',
     'Independent calibrated plant/data would be needed for external validity; unavailable.'),
    ('O',
      'unexplained by candidate family',
      'LOW',
      'Factor/friction counterfactuals account for where differing outputs originate.',
     'No unique additive causal percentage or real lane-quality attribution is established.',
      'Use a different offline architecture with a separately frozen experiment; do not expand this grid.')]
  causes=[{'code':c,'cause':cause,'confidence':confidence,'supporting_evidence':support,'contradicting_evidence':contradiction,
           'affected_scenarios':rejection.load_policy()['scenarios'],
           'unaffected_scenarios':['gentle_mid_left (15 m/s: v1=v2)',
      'constant high at25 m/s: v2=baseline'],
           'falsification_test':test} for c,cause,confidence,support,contradiction,test in explanations]
  analysis={'scope':'SYNTHETIC_CONTROLLER_DYNAMICS_EXPLANATION_NO_LANE_QUALITY_JUDGMENT',
    'ledger_sha256':ledger['receipt_sha256'],'family_decision_sha256':decision['receipt_sha256'],
    'source_sha256':digest(Path(__file__).read_bytes()),'metric_counts':dict(Counter(r['metric'] for r in ledger['violations'])),
    'dynamics_evidence':evidence,'root_cause_assessments':causes,
    'capability_boundary':{'differential_classification':'CONTROLLER_TRACKING_PROBLEM_IN_THIS_SYNTHETIC_INPUT',
      'differential_input_changed':False,'lane_path_quality':'UNKNOWN_NO_INDEPENDENT_LANE_TRUTH',
      'model_planner_executed':False,'desired_source':'curvature_yaw_screening._inputs plus frozen derived speed',
      'trajectory_source':'generic plant observer; no independent desired/lane path supplied',
      'next_step':'offline controller/input factorial groundwork; no expanded parameter search'},
    'v3_created':False,'v2_status':'REJECTED',
      'real_performance_status':QUALIFICATION}
  analysis['receipt_sha256']=digest(canonical(analysis))
  # History stores immutable aggregate identities AND retains per-case native identities separately.
  history=[]
  per_case={}
  for _role,name,index,status in [(search.ROLES[0],'BASELINE',0,'REFERENCE'),(search.ROLES[1],'CURRENT',1,'REFERENCE'),
                                 (search.ROLES[2],'V1',2,'TRADEOFF_ONLY'),(search.ROLES[3],'V2',3,'REJECTED')]:
    per_case[name]=[{'scenario':r['manifest']['scenario'],'identity':r['arms'][index]['identity'],
                     'result_sha256':r['arms'][index]['repetition_result_sha256'][0]} for r in original]
    entry={'candidate':name,'status':status,'alias_of':'BASELINE' if name=='CURRENT' else None,
           'source_sha256':digest(canonical([r['arms'][index]['identity']['components']['controller_source_sha256'] for r in original])),
           'config_sha256':digest(canonical([r['manifest']['controller_specs'][index] for r in original])),
           'search_policy_sha256':search.POLICY_SHA if name=='V2' else None,
           'result_sha256':digest(canonical([r['arms'][index]['repetition_result_sha256'][0] for r in original])),
           'scenario_set':[r['manifest']['scenario'] for r in original],
           'rejection_reasons':['37 nominal cell violations; stress PASS cannot overturn'] if name=='V2'
             else ['descriptive v1 adverse high-speed results retained; not a qualified candidate'] if name=='V1' else [],
           'robustness_result':digest((search.ROOT/'docs/cyberpilot/changes/candidate-v2-robustness-results.json').read_bytes())
              if name=='V2' else None,'qualification_status':QUALIFICATION}
    history=append_history(history,entry,expected_parent_sha256=history[-1]['record_sha256'] if history else None)
  history_artifact={'scope':'IMMUTABLE_HISTORY_SNAPSHOT_AGGREGATE_IDENTITIES_NOT_SINGLE_NATIVE_ID',
    'history':history,'tip_sha256':history[-1]['record_sha256'],'per_case_native_identities':per_case,
    'v3_status':'NOT_CREATED_FAMILY_REDESIGN' if decision['verdict']=='FAMILY_REDESIGN' else 'NOT_CREATED_SEPARATE_EXPERIMENT_REQUIRED',
    'original_v1_archive_file_sha256':digest((search.ROOT/'docs/cyberpilot/changes/candidate-v1-attribution-results.json').read_bytes()),
    'original_v2_archive_file_sha256':digest((search.ROOT/'docs/cyberpilot/changes/candidate-v2-delay-domain-search-results.json').read_bytes()),
      'v1_original_history':'candidate-v1-attribution-results.json (immutable, 13-case descriptive tier)',
    'v2_original_history':'candidate-v2-delay-domain-search-results.json; candidate-v2-robustness-results.json',
    'history_rewrite_boundary':'hash-chain consistency only; retain external tip or Git revision to detect complete rewriting',
    'qualification_status':QUALIFICATION}
  history_artifact['receipt_sha256']=digest(canonical(history_artifact))
  return ledger,decision,analysis,history_artifact


if __name__=='__main__':
  import argparse
  parser=argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--run-dir',required=True)
  parser.add_argument('--evaluation-dir',required=True)
  parser.add_argument('--output-dir',required=True)
  args=parser.parse_args()
  values=export_results(args.run_dir,args.evaluation_dir)
  output=Path(args.output_dir)
  output.mkdir(parents=True,exist_ok=False)
  for name,value in zip(('candidate-v2-violation-ledger.json',
      'candidate-family-decision.json',
                        'candidate-v2-dynamics-attribution.json',
      'candidate-history-ledger.json'),values,strict=True):
    (output/name).write_bytes(canonical(value)+b'\n')
