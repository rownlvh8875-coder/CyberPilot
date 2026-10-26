"""Aggregate-only recovery evidence pins; no private-store dependency in CI."""

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_execution as read
from openpilot.tools.cyber_autotune import empirical_stage_a_publication as old
from openpilot.tools.cyber_autotune import empirical_causal_policy as policy
from openpilot.tools.cyber_autotune import empirical_causal_recovery as recovery
from openpilot.tools.cyber_autotune import empirical_causal_analysis as analysis

PINS = {
  'empirical-stage-a-causal-recovery-policy-v1.json': '1f1f286f42371935d24081302a2214ec2389df0e1a92fe2b1d089a8ec6ac2ad8',
  'empirical-stage-a-row-origin-map-v1.json': '7fe19c79588d55a0c8d9516d317b4f9da027ebfadea7684fd0fd7e552bc3bf31',
  'empirical-stage-a-causal-context-availability-v1.json': '1c55a03e7ede993b267b2dcbb4cee423d544579ee3d8bd7b9522694bb042ae2a',
  'empirical-stage-a-causal-condition-results-v1.json': 'a5ad3f0cb7f9eb8657fe9b47390b328e543b0e9856526d9e2779f277ca762d06',
  'empirical-stage-a-causal-separator-readiness-v1.json': 'df25155e27eaf5bceb3e2bcdc4daabe8740ac6cfac12aef4e6ae8e69eac4914e',
  'empirical-causal-context-schema-v1.json': 'e615e560ac4c95a748349c6236a7240f7e84a364608367fec9cff00e67145388',
  'empirical-stage-a-causal-repeatability-v1.json': 'efe93ed4415644bf40bb0089dc18dc0aafd928c6831b1c7ee49517211d54ddc5',
}


def validate_chain(rows):
  pol = rows['empirical-stage-a-causal-recovery-policy-v1.json']
  result = rows['empirical-stage-a-causal-condition-results-v1.json']
  readiness = rows['empirical-stage-a-causal-separator-readiness-v1.json']
  repeat = rows['empirical-stage-a-causal-repeatability-v1.json']
  if any(pol.get(k) != val for k, val in policy.static_policy().items()):
    raise ValueError('PUBLIC_RECOVERY_SOURCE_POLICY_CODE_DRIFT')
  if result['policy_sha256'] != pol['receipt_sha256'] or readiness['result_sha256'] != result['receipt_sha256']:
    raise ValueError('PUBLIC_RECOVERY_POLICY_RESULT_CHAIN_DRIFT')
  recovery.old.validate_repeatability(repeat, result['receipt_sha256'])
  if readiness['repeatability_sha256'] != repeat['receipt_sha256']:
    raise ValueError('PUBLIC_RECOVERY_REPEATABILITY_CHAIN_DRIFT')
  if result['input_trees_before_sha256'] != result['input_trees_after_sha256'] or result['input_trees_before_sha256'] != pol['input_tree_sha256']:
    raise ValueError('PUBLIC_PRIVATE_CACHE_PRESERVATION_FAILURE')
  records = result['route_fold_speed_results']
  if result['decision'] != analysis.adjudicate(records):
    raise ValueError('PUBLIC_STRICT_SEPARATOR_ADJUDICATION_DRIFT')
  for row, expected in zip(records, pol['selected'], strict=True):
    if any(row[k] != expected[v] for k, v in (('route_id', 'development_route'), ('fold', 'fold'), ('speed_bin', 'speed_bin'))):
      raise ValueError('PUBLIC_ROUTE_FOLD_ORDER_DRIFT')
    if row['count'] != expected['evaluation']['coverage']['one_step']['valid'] or not row['target_design_prediction_previous_order_exact']:
      raise ValueError('PUBLIC_EXACT_ORIGIN_SUPPORT_DRIFT')
    for name, value in row['conditions'].items():
      if name not in analysis.CONDITIONS:
        raise ValueError('PUBLIC_UNKNOWN_CONDITION')
      coverage = value['coverage']
      if coverage != {'valid': row['count'], 'total': row['count'], 'unavailable': 0}:
        raise ValueError('PUBLIC_CONDITION_SUPPORT_DRIFT')
      if value['gate'] != analysis.scope_gate(value['branches']['TRUE'], value['branches']['FALSE']):
        raise ValueError('PUBLIC_BRANCH_GATE_DRIFT')
  if set(result['selector_diagnostics']) != set(result['decision']['strict_pass_conditions']):
    raise ValueError('PUBLIC_SELECTOR_BEFORE_STRICT_ADMISSION')
  if readiness['holdout_opening'] != 'HOLDOUT_OPENING_CLOSED' or readiness['stage_b'] != 'STAGE_B_SIGNAL_ADMISSION_BLOCKED':
    raise ValueError('PUBLIC_UNAUTHORIZED_STATE_PROMOTION')
  return rows


def load():
  old.load()
  if len(PINS) < 7:
    raise ValueError('RECOVERY_PUBLICATION_PINS_REQUIRED')
  rows = {name: recovery.validate_public(read.read(p.PUBLIC / name)) for name in PINS}
  if any(rows[name]['receipt_sha256'] != digest for name, digest in PINS.items()):
    raise ValueError('CAUSAL_RECOVERY_PUBLIC_PIN_DRIFT')
  return validate_chain(rows)
