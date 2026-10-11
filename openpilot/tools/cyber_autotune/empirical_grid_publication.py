"""Pinned aggregate source-grid results; CI never needs private data."""
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_execution as read
from openpilot.tools.cyber_autotune import empirical_causal_publication as causal
from openpilot.tools.cyber_autotune import empirical_grid_emission as e
from openpilot.tools.cyber_autotune import empirical_grid_analysis as g

POLICY='empirical-source-grid-emission-policy-v1.json'
RESULT='empirical-source-grid-emission-results-v1.json'
READY='empirical-source-grid-emission-readiness-v1.json'
REPEAT='empirical-source-grid-emission-repeatability-v1.json'
CONTRACT='empirical-stage-a-v4-observation-architecture-contract-v1.json'
PINS={
  POLICY:'77d99c602047b7bda5a47e8ac6d5c869884d049bac9dcc397b05fdde98876339',
  RESULT:'e87c48274d072231fd72c3615b096b25af46dee1db6544a6907118619ac847da',
  READY:'13da4be741d49a6303e8512c99f27be5728101c711cda21dac35549f453a0efe',
  REPEAT:'6bbd81fd304de1744649b5337ff150445ee02c31dff2257adaeed53f0f3029fb',
}


def validate_chain(rows):
  pol,result,ready,repeat=(rows[n] for n in (POLICY,RESULT,READY,REPEAT))
  for x in rows.values():
    p.verify(x)
    e.validate_public(x)
  if any(pol.get(k)!=v for k,v in e.static_policy().items()):
    raise ValueError('GRID_SOURCE_POLICY_CODE_DRIFT')
  if result['policy_sha256']!=pol['receipt_sha256'] or ready['result_sha256']!=result['receipt_sha256']:
    raise ValueError('GRID_PUBLIC_CHAIN_DRIFT')
  e.old.validate_repeatability(repeat,result['receipt_sha256'])
  if ready!=e.readiness(result['decision'],pol['receipt_sha256'],result['receipt_sha256'],repeat['receipt_sha256']):
    raise ValueError('GRID_PUBLIC_READINESS_DRIFT')
  if any(repeat.get(k) is not True for k in ('raw_decoder_forced_exception','raw_path_forced_exception','whole_process_succeeded')):
    raise ValueError('GRID_RAW_FIREWALL_REQUIRED')
  if result['input_trees_before_sha256']!=result['input_trees_after_sha256'] or result['input_trees_before_sha256']!=pol['input_tree_sha256']:
    raise ValueError('GRID_PRIVATE_INPUT_MUTATION')
  if result['decision']!=g.adjudicate(result['scopes']):
    raise ValueError('GRID_ADJUDICATION_DRIFT')
  for row in result['scopes']:
    matches=[x for x in pol['selected'] if x['fold']==row['fold'] and x['speed_bin']==row['speed_bin']]
    if len(matches)!=1:
      raise ValueError('GRID_SCOPE_IDENTITY_DRIFT')
    expected=matches[0]
    if row['route_id']!=expected['development_route'] or row['count']!=expected['evaluation']['coverage']['one_step']['valid']:
      raise ValueError('GRID_ROUTE_SUPPORT_DRIFT')
    if not row['exact_same_support'] or row['gate']!=g.gate(row):
      raise ValueError('GRID_SUPPORT_GATE_DRIFT')
    if row['selected_array_sha256']!=expected['array_sha256']['one_step']:
      raise ValueError('GRID_SELECTED_ARRAY_DRIFT')
    origin=[x for x in pol['origin_bindings'] if x['fold']==row['fold'] and x['speed_bin']==row['speed_bin']]
    if len(origin)!=1 or origin[0]['origin_manifest_sha256']!=row['origin_manifest_sha256'] or origin[0]['count']!=row['count']:
      raise ValueError('GRID_ORIGIN_BINDING_DRIFT')
    if row['emission']['state']!=g.comparison(row['arms']['SOURCE_GRID_ARX'],row['arms']['CONTINUOUS_ARX'])['state']:
      raise ValueError('GRID_CONTINUOUS_COMPARISON_DRIFT')
    for arm,key in (('CONTINUOUS_ARX','model'),('HOLD_LAST_OUTPUT','HOLD_LAST_OUTPUT')):
      if any(row['arms'][arm][k]!=v for k,v in expected['evaluation']['one_step'][key].items()):
        raise ValueError('GRID_HISTORICAL_METRIC_MUTATION')
  for b in g.BINS:
    if result['equal_route_by_speed'][b]!=g.aggregate([x for x in result['scopes'] if x['speed_bin']==b]):
      raise ValueError('GRID_EQUAL_ROUTE_AGGREGATION_DRIFT')
  if (CONTRACT in rows)!=(result['decision']['strict_pass_scopes']==6):
    raise ValueError('GRID_CONTRACT_BEFORE_SIX_PASS')
  if CONTRACT in rows and rows[CONTRACT]!=g.architecture(result['decision'],pol['receipt_sha256']):
    raise ValueError('GRID_V4_CONTRACT_DRIFT')
  return rows


def load():
  causal.load()
  rows={name:e.validate_public(read.read(p.PUBLIC/name)) for name in PINS}
  if any(rows[name]['receipt_sha256']!=digest for name,digest in PINS.items()):
    raise ValueError('GRID_PUBLIC_PIN_DRIFT')
  return validate_chain(rows)
