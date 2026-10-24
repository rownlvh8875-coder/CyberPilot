"""Cache-only origin proof and causal audit. No raw-event, fitting or rollout API."""
import argparse
import os
from pathlib import Path
import numpy as np
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_plant_model as m
from openpilot.tools.cyber_autotune import empirical_source_execution as read
from openpilot.tools.cyber_autotune import empirical_v3_policy as v
from openpilot.tools.cyber_autotune import empirical_v3_cache as cache
from openpilot.tools.cyber_autotune import empirical_stage_a_attribution as old
from openpilot.tools.cyber_autotune import empirical_causal_policy as policy
from openpilot.tools.cyber_autotune import empirical_causal_analysis as analysis
from openpilot.tools.cyber_autotune.empirical_v3_models import save_array

HISTORY = 45
PRIOR = (1, 2, 5, 6)
CONTEXT_COLUMNS = ('u1', 'u2', 'u5', 'u6', 'y1', 'y2', 'prior_speed', 'normalized_u1', 'normalized_u2')
ORIGIN_COLUMNS = ('aligned_row', 'run_id', 'within_run', 'design_row', 'run_start', 'distance_from_run_start_samples',
                  *tuple(f'{kind}_minus_{lag}' for lag in PRIOR for kind in ('state_time', 'command_time', 'control_time', 'grid_time')))
ALIGNED_FIELDS = ('actuator_valid', 'speed_bin', 'command_raw', 'angle_deg', 'speed_mps', 'grid_time_ns',
                  'state_time_ns', 'command_time_ns', 'control_time_ns', 'reasons')


def exact(a, b):
  return a.dtype == b.dtype and a.shape == b.shape and a.tobytes(order='C') == b.tobytes(order='C')


def reconstruct(rows, speed, history=HISTORY):
  if history != 45 or m.HISTORY != 45 or speed not in v.BINS:
    raise ValueError('EXACT_HISTORY45_AND_SPEED_POLICY_REQUIRED')
  # Whitelist projection deliberately discards cached yaw/gyro without analysis.
  rows = [{k: row[k] for k in ALIGNED_FIELDS} for row in rows]
  runs, current = [], []
  for i, row in enumerate(rows):
    if row['actuator_valid'] and row['speed_bin'] == speed:
      current.append(i)
    elif current:
      runs.append(current)
      current = []
  if current:
    runs.append(current)
  x, target, context, origin = [], [], [], []
  for run_id, indices in enumerate(runs):
    for first, second in zip(indices, indices[1:], strict=False):
      before, after = rows[first], rows[second]
      if after['grid_time_ns'] - before['grid_time_ns'] != 10_000_000 or after['state_time_ns'] <= before['state_time_ns']:
        raise ValueError('RUN_CLOCK_OR_GRID_REGRESSION')
    for j in range(44, len(indices)):
      k = indices[j]
      past = [rows[indices[j-lag]] for lag in PRIOR]
      now = rows[k]
      clocks = []
      for row in past:
        state, command, control, grid = [row[k] for k in ('state_time_ns','command_time_ns','control_time_ns','grid_time_ns')]
        if any(type(t) is not int for t in (state, command, control, grid)):
          raise ValueError('EXACT_INTEGER_RECEIPT_CLOCK_REQUIRED')
        if not (0 <= grid-state <= 20_000_000 and 0 <= state-command <= 20_000_000
                and 0 <= state-control <= 20_000_000 and state < now['state_time_ns']):
          raise ValueError('CAUSAL_PRIOR_TIMESTAMP_ORDER_REQUIRED')
        if set(row['reasons']) - {'YAW_UNAVAILABLE'}:
          raise ValueError('VALID_RUN_CONTEXT_CONFLICT')
        clocks.extend((state, command, control, grid))
      a, b, delayed, delayed_previous = past
      raw = [a['command_raw'], b['command_raw'], delayed['command_raw'], delayed_previous['command_raw']]
      if not analysis.command_equivalence(raw):
        raise ValueError('RAW_NORMALIZED_CONDITION_CONFLICT')
      y1, y2 = a['angle_deg'], b['angle_deg']
      values = [*raw, y1, y2, a['speed_mps'], float(np.float32(raw[0]/409)), float(np.float32(raw[1]/409))]
      if not np.isfinite(values).all() or not np.isfinite(now['angle_deg']):
        raise ValueError('FINITE_RECOVERED_VALUES_REQUIRED')
      x.append((y1, raw[2], 1.))
      target.append(now['angle_deg'])
      context.append(values)
      origin.append((k, run_id, j, len(target)-1, indices[0], j, *clocks))
  return (np.asarray(x, dtype=np.float64).reshape(-1,3), np.asarray(target, dtype=np.float64),
          np.asarray(context, dtype=np.float64).reshape(-1,len(CONTEXT_COLUMNS)),
          np.asarray(origin, dtype=np.int64).reshape(-1,len(ORIGIN_COLUMNS)))


def prove(design, target, frozen_design, one, coefficients):
  old.validate_pair(frozen_design, one)
  if (not exact(design, frozen_design) or not exact(target, one[:,0])
      or not exact(design[:,0], one[:,3])
      or not exact(design @ np.asarray(coefficients, dtype=np.float64), one[:,1])):
    raise ValueError('CAUSAL_CONTEXT_ORIGIN_MAPPING_BLOCKED')


def load_routes(paths, pol):
  public = v.inputs()
  split = read.read(paths['v2'] / 'split.json')
  auth = read.read(paths['v2'] / 'authorization.json')
  if split != public['empirical-plant-v2-train-dev-split-v1.json'] or auth != public['empirical-plant-v2-numeric-authorization-v1.json']:
    raise ValueError('PINNED_V2_SPLIT_AUTHORIZATION_DRIFT')
  integrity = read.read(paths['v3'] / 'cache-integrity.json')
  if integrity['receipt_sha256'] != pol['v3_cache_integrity_sha256']:
    raise ValueError('V3_SOURCE_HASH_ATTESTATION_DRIFT')
  result = read.read(paths['v2'] / 'train-dev-results.json')
  manifest = read.read(paths['v2'] / 'manifest.json')
  if manifest['receipt_sha256'] != integrity['v2_manifest_sha256']:
    raise ValueError('V2_LINEAGE_MANIFEST_DRIFT')
  routes = {}
  for route in pol['routes']:
    rid = route['route_id']
    bound = next(x for x in integrity['routes'] if x['route_id'] == rid)
    receipt = read.read(paths['v2'] / 'routes' / (rid+'.json'))
    cache.validate_parent(result, public, receipt)
    if receipt['receipt_sha256'] != bound['route_receipt_sha256'] or receipt['split_sha256'] != split['receipt_sha256'] or receipt['role'] != 'TRAIN':
      raise ValueError('V2_ROUTE_IDENTITY_DRIFT')
    expected = auth['sources'][rid]
    segments = manifest['routes'][rid]
    if sorted(expected) != sorted(x['source_sha256'] for x in segments) or sorted(expected) != sorted(x['source_sha256'] for x in bound['segments']):
      raise ValueError('EXACT_SEGMENT_LINEAGE_REQUIRED')
    if bound['bridge']['status'] != 'ROUTE_COMMAND_BRIDGE_CONFIRMED' or bound['bridge']['steer_max'] != 409:
      raise ValueError('SOURCE_COMMAND_BRIDGE_CONFLICT')
    part = {b: [[], [], [], []] for b in v.BINS}
    segment_hashes = []
    for ordinal, segment in enumerate(segments):
      digest = segment['source_sha256']
      seal = next(x for x in bound['segments'] if x['source_sha256'] == digest)
      opening = read.read(paths['v2'] / 'openings' / rid / (digest+'.json'))
      row = read.read(paths['v2'] / 'segments' / rid / (digest+'.json'))
      cache.validate_segment(row, opening, route, digest, split['receipt_sha256'], auth['receipt_sha256'])
      if row['receipt_sha256'] != seal['cache_sha256'] or opening['receipt_sha256'] != seal['opening_sha256']:
        raise ValueError('V2_IMMUTABLE_SEGMENT_RECEIPT_DRIFT')
      segment_hashes.append(row['receipt_sha256'])
      for b in v.BINS:
        x, y, context, origin = reconstruct(row['aligned']['rows'], b)
        # Segment ordinal indexes only the private ordered receipt list.
        origin = np.column_stack([np.full(len(origin),ordinal,dtype=np.int64),origin])
        for out, value in zip(part[b], (x,y,context,origin), strict=True):
          out.append(value)
    routes[rid] = {'segments': segment_hashes, 'bins': {}}
    for b, arrays in part.items():
      combined = [np.concatenate(x, axis=0) for x in arrays]
      if len(combined[1]) != bound['coverage']['bins'][b]['common_design_rows']:
        raise ValueError('EXACT_V3_ADMITTED_COMMON_SUPPORT_REQUIRED')
      routes[rid]['bins'][b] = combined
    print('recovered cache route', rid[:8], len(segments), 'segments', flush=True)
  return routes


def run(inputs, output):
  paths, output, pol = policy.require_frozen(inputs, output)
  if any(os.environ.get(k) != '1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS')):
    raise ValueError('SINGLE_THREAD_ENVIRONMENT_REQUIRED')
  routes = load_routes(paths, pol)
  records = []
  for expected in pol['selected']:
    rid, b, fold = expected['development_route'], expected['speed_bin'], expected['fold']
    folder = paths['v3'] / 'folds' / 'STAGE_A' / b / 'ARX1-5' / fold
    receipt = read.read(folder / 'receipt.json')
    if (receipt['receipt_sha256'] != expected['private_result_sha256'] or receipt['config'] != pol['config']
        or any(receipt[k] != expected[k] for k in ('development_route','train_route','fold'))):
      raise ValueError('EXACT_FROZEN_SELECTED_FOLD_REQUIRED')
    design = old.load_array(folder/'design.npy', expected['array_sha256']['design'])
    one = old.load_array(folder/'one_step.npy', expected['array_sha256']['one_step'])
    x,y,context,origin = routes[rid]['bins'][b]
    prove(x,y,design,one,receipt['model']['coefficients'])
    conditions = analysis.conditions(context[:,:6], one[:,1])
    folder = output / 'recovered' / b / fold
    hashes = {'context': save_array(folder/'context.npy',context),
              'origin': save_array(folder/'origin.npy',origin),
              'conditions': save_array(folder/'conditions.npy',np.column_stack(list(conditions.values())))}
    # Private manifest provides route and segment/timestamp ordering identities.
    manifest = p.seal({'schema':'EMPIRICAL_CAUSAL_PRIVATE_ORIGIN_V1','route_id':rid,'fold':fold,'speed_bin':b,
      'segments': routes[rid]['segments'], 'origin_columns':['segment_ordinal',*ORIGIN_COLUMNS],
      'context_columns':list(CONTEXT_COLUMNS),'array_sha256':hashes,'policy_sha256':pol['receipt_sha256']})
    p.persist(folder/'receipt.json',manifest)
    records.append({'route_id':rid,'fold':fold,'speed_bin':b,'count':len(one),
      'mapping_status':'EXACT_FLOAT64_BYTES_MATCH','target_design_prediction_previous_order_exact':True,
      'origin_manifest_sha256':manifest['receipt_sha256'],'private_array_sha256':hashes,
      'raw_normalized_condition_equivalent':analysis.command_equivalence(context[:,:4].ravel()),
      'conditions':analysis.audit(one,context[:,:6])})
  decision = analysis.adjudicate(records)
  selectors = {}
  for name in decision['strict_pass_conditions']:
    selectors[name] = []
    for expected in pol['selected']:
      b,fold,rid = expected['speed_bin'],expected['fold'],expected['development_route']
      one = old.load_array(paths['v3']/'folds'/'STAGE_A'/b/'ARX1-5'/fold/'one_step.npy',expected['array_sha256']['one_step'])
      context = routes[rid]['bins'][b][2]
      selectors[name].append({'route_id':rid,'fold':fold,'speed_bin':b,
        'metrics':analysis.selector(one,analysis.conditions(context[:,:6],one[:,1])[name],True),
        'coverage':{'valid':len(one),'total':len(one),'unavailable':0}})
  after = {name: cache.tree_identity(path) for name,path in paths.items()}
  if after != pol['input_tree_sha256']:
    raise ValueError('INPUT_STORE_MUTATION')
  result = p.seal({'schema':'EMPIRICAL_STAGE_A_CAUSAL_CONDITION_RESULTS_V1','policy_sha256':pol['receipt_sha256'],
    'route_fold_speed_results':records,'decision':decision,'selector_diagnostics':selectors,
    'equal_route_by_speed':{b:{name:{branch:analysis.aggregate([x for x in records if x['speed_bin']==b],name,branch)
       for branch in ('TRUE','FALSE')} for name in analysis.CONDITIONS} for b in v.BINS},
    'input_trees_before_sha256':pol['input_tree_sha256'],'input_trees_after_sha256':after,
    'raw_payload_opened':False,'refit':'NOT_RUN','rollout':'NOT_RUN','stage_b':'NOT_RUN'})
  p.persist(output/'results.json',result)
  return result


def context_schema():
  return p.seal({'schema':'EMPIRICAL_CAUSAL_CONTEXT_SCHEMA_V1','scope':'FUTURE_GENERATIONS_ONLY',
    'publication':'PRIVATE_ROWS_NEVER_PUBLISHED','required_private_fields':[
      'opaque_route_id','segment_receipt_sha256','aligned_row_index','run_id','within_run_index','design_row_index',
      'model_required_command_history','past_measured_angle_history','normalized_command','speed_context',
      'mask_reasons','state_command_control_timestamp_ordering','rail_context','intervention_boundary',
      'source_profile_policy_identity'],
    'optional_private_fields':{'steeringRateDeg':'ONLY_AFTER_EXPLICIT_FUTURE_READER_AUTHORIZATION'},
    'historical_steering_rate':'UNAVAILABLE_NOT_PRESERVED','historical_regeneration_allowed':False,
    'future_target_gate_allowed':False,'raw_publication_allowed':False})


def validate_public(row):
  old.validate_public(row)
  forbidden = {'origin_rows','aligned_row_index','run_index','within_run_index','design_row_index',
               'state_time_ns','command_time_ns','control_time_ns','context_values','coefficients',
               'predictions','targets','commands','residuals','private_path'}
  def check(value):
    if isinstance(value,dict):
      if set(value) & forbidden:
        raise ValueError('PRIVATE_RECOVERED_ROW_PUBLICATION_PROHIBITED')
      for x in value.values():
        check(x)
    elif isinstance(value,list):
      for x in value:
        check(x)
  check(row)
  return row


def outputs(output):
  pol = read.read(output/'policy.json')
  result = read.read(output/'results.json')
  if any(pol.get(k) != val for k,val in policy.static_policy().items()) or result['policy_sha256'] != pol['receipt_sha256']:
    raise ValueError('RECOVERY_PUBLIC_POLICY_RESULT_CHAIN_DRIFT')
  repeat = read.read(output/'repeatability.json')
  old.validate_repeatability(repeat,result['receipt_sha256'])
  rows = result['route_fold_speed_results']
  common = {'policy_sha256':pol['receipt_sha256'],'result_sha256':result['receipt_sha256']}
  mapping = p.seal({'schema':'EMPIRICAL_STAGE_A_ROW_ORIGIN_MAP_V1',**common,
    'status':'CAUSAL_CONTEXT_RECOVERED','scopes':[{k:x[k] for k in ('route_id','fold','speed_bin','count','mapping_status',
        'target_design_prediction_previous_order_exact','origin_manifest_sha256','private_array_sha256')} for x in rows],
    'raw_origin_indices_published':False,'raw_timestamps_published':False})
  availability = p.seal({'schema':'EMPIRICAL_STAGE_A_CAUSAL_CONTEXT_AVAILABILITY_V1',**common,
    'prior_commands':'RECOVERED','prior_angles':'RECOVERED','prior_speed':'RECOVERED',
    'raw_normalized_changed':'EXACT_ALIAS_NOT_TWO_INDEPENDENT_CONDITIONS',
    'raw_normalized_equivalence':all(x['raw_normalized_condition_equivalent'] for x in rows),
    'source_steering_rate':'UNAVAILABLE_NOT_PRESERVED',
    'mask_context':'RECOVERED_FROM_REASONS_IN_VALID_RUNS_ONLY',
    'intervention_context':'NO_OVERRIDE_ACTIVE_IN_SELECTED_RUNS_BOUNDARIES_IDENTIFIED_NO_EVENT_TRANSIENT_SUPPORT',
    'safety_limited':None,'curvature_limited':None,'acquisition_clock':'UNVERIFIED_PUBLISH_TIME_ONLY'})
  historical = v3_readiness()
  readiness = p.seal({'schema':'EMPIRICAL_STAGE_A_CAUSAL_SEPARATOR_READINESS_V1',**common,**result['decision'],
    'repeatability_sha256':repeat['receipt_sha256'],'future_holdout':'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED',
    'package_status':'CLOSED_MISSING_ADMISSIBLE_MODEL','holdout_opening':'HOLDOUT_OPENING_CLOSED',
    'stage_b':'STAGE_B_SIGNAL_ADMISSION_BLOCKED','stage_c':'NOT_RUN','ta_sg_execution':'NOT_RUN',
    'fitting':'NOT_RUN','model_selection':'NOT_RUN','threshold_search':'NOT_RUN','combination_search':'NOT_RUN',
    'historical':historical['historical'],'calibration_blockers':p.BLOCKERS,
    'sealed_reference':'NOT_GENERATED','vehicle':historical['vehicle'],
    'source_freshness':'CACHED_PRIOR_SOURCE_HASH_ATTESTATION_NO_RAW_FILE_REHASH'})
  artifacts = {
    'empirical-stage-a-causal-recovery-policy-v1.json':pol,
    'empirical-stage-a-row-origin-map-v1.json':mapping,
    'empirical-stage-a-causal-context-availability-v1.json':availability,
    'empirical-stage-a-causal-condition-results-v1.json':result,
    'empirical-stage-a-causal-separator-readiness-v1.json':readiness,
    'empirical-causal-context-schema-v1.json':context_schema(),
    'empirical-stage-a-causal-repeatability-v1.json':repeat}
  if result['decision']['strict_pass_conditions']:
    artifacts['empirical-stage-a-v4-architecture-contract-v1.json'] = p.seal({
      'schema':'EMPIRICAL_STAGE_A_V4_ARCHITECTURE_CONTRACT_V1',
      'conditions':result['decision']['strict_pass_conditions'],'condition_policy_sha256':pol['condition_policy']['receipt_sha256'],
      'allowed_inputs':pol['condition_policy']['causal_fields'],'causal_timing':pol['clock'],
      'source_quantization_sha256':pol['source_quantization_sha256'],'arx_branch_sha256':pol['selected_structure_sha256'],
      'hold_last_branch':'EXACT_PREVIOUS_MEASUREMENT','state_owner':'FUTURE_LATENT_MODEL_AND_SELECTOR_EXPLICIT_SINGLE_OWNER',
      'reset':'FUTURE_POLICY_MUST_DEFINE_NEW_INSTANCE_AT_ROUTE_SEGMENT_RUN_MASK_BOUNDARY',
      'future_rollout':'SEPARATE_AUTHORIZATION_AND_FROZEN_STATE_MEASUREMENT_EMISSION_TRANSITION_POLICY_REQUIRED',
      'actual_algorithm_implemented':False,'fitting':False,'execution_allowed':False,'search_allowed':False,
      'holdout_opening_allowed':False,'future_holdout':'FUTURE_UNTOUCHED_HOLDOUT_REQUIRED'})
  for x in artifacts.values():
    validate_public(x)
  return artifacts


def v3_readiness():
  from openpilot.tools.cyber_autotune import empirical_v3_publication
  return empirical_v3_publication.load()['empirical-plant-v3-readiness-v1.json']


def main():
  cli=argparse.ArgumentParser(description=__doc__)
  cli.add_argument('mode',choices=('freeze','run','publish'))
  cli.add_argument('--v2-store',type=Path,required=True)
  cli.add_argument('--v3-store',type=Path,required=True)
  cli.add_argument('--attribution-store',type=Path,required=True)
  cli.add_argument('--store',type=Path,required=True)
  args=cli.parse_args()
  inputs={'v2':args.v2_store,'v3':args.v3_store,'attribution':args.attribution_store}
  if args.mode=='freeze':
    pol=policy.freeze(inputs,args.store)
    print('recovery policy frozen',pol['receipt_sha256'])
  elif args.mode=='run':
    first=run(inputs,args.store)
    second=run(inputs,args.store)
    if first!=second:
      raise ValueError('RECOVERY_EXACT_REPEATABILITY_FAILURE')
    p.persist(args.store/'repeatability.json',p.seal({'schema':'EMPIRICAL_CAUSAL_RECOVERY_REPEATABILITY_V1',
      'runs':2,'exact_repeatability':True,'result_sha256':first['receipt_sha256'],
      'compared':['ROW_ORIGINS','CONTEXT_BYTES','CONDITION_BYTES','COUNTS','METRICS','VERDICT','RECEIPT_SHA','ALL_INPUT_STORE_TREES']}))
    print(first['decision'])
  else:
    policy.require_frozen(inputs,args.store)
    for name,row in outputs(args.store).items():
      p.persist(p.PUBLIC/name,row)
    print('aggregate recovery publication complete')


if __name__=='__main__':
  main()
