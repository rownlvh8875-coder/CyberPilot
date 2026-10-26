"""Public-only S2-RI policy builder, exact validator and immutable publisher."""
import argparse
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_s2_ri_fitting_contracts as c

PUBLIC = p.PUBLIC
BASELINE = "68fdcdc1334f682f9300b2f6bf3230074f79922c"
PINS = {
  'empirical-s2-ri-angle-grid-v1.json': {
    'file_sha256': '23d3595fb73c058f1c965c1d110d828fbe25aa9b1c95f3b64e1e5a04791d1e09',
    'receipt_sha256': '83ab72d1dc11521547cb5d9588b7350a836a7e3256342b51bb4d0dcd4eef5fff',
  },
  'empirical-s2-ri-causal-identity-v1.json': {
    'file_sha256': '01c31a851c1612c4c3e5c70f2e14a6fdad694fed0fb2031a724ae2942508982b',
    'receipt_sha256': '42b8dc61b9fd8673a810a93edeee575c7f7333576ea0908cc09b4602aea30cc5',
  },
  'empirical-s2-ri-design-policy-v1.json': {
    'file_sha256': '02395f01d11a8b9a7779914ba7064f05a5c7609458c64699f07dc5e9a6bab522',
    'receipt_sha256': '2a32ee18b757b7fa6dde62360b226bef42d7a203d6f15f509b94d5b18910c454',
  },
  'empirical-s2-ri-future-metric-contract-v1.json': {
    'file_sha256': '1b402dfca196630905649ab327195dc5e1761daeeb993a3c86373ff6a80b896e',
    'receipt_sha256': '9a92fe4d1b2dfaaab00059f69ec78f5d04145e705e20094ef21131cee49874d2',
  },
  'empirical-s2-ri-history-reset-v1.json': {
    'file_sha256': '86a5405fb184304b6861f0a85ed38814acde0d24a1d22cb122df955435e5008d',
    'receipt_sha256': 'b3387dc0d9ab0372cfbc6ed2e9bcc337250a4faa92c7c8fa7ab50451b34a1294',
  },
  'empirical-s2-ri-readiness-v1.json': {
    'file_sha256': '3b6922f67bb096ccba8516e6ead5b4b326b757180582d124e2e6e2aa9c7535c6',
    'receipt_sha256': 'df79966d0f2daedba0a6e798a91b277ee2325ee9e5e303069e3b4287e695d9b4',
  },
  'empirical-s2-ri-regression-validation-v1.json': {
    'file_sha256': '650401647bbd7a7ecb8a7188dc208b7125849f5af5c5862b0bf31a68e9b9efca',
    'receipt_sha256': 'cf8cba4e55c4a8f3268d2e19c1228187c4419ed70513ad765ebd253f8de5082e',
  },
  'empirical-s2-ri-route-cv-contract-v1.json': {
    'file_sha256': 'd3f935674a760754222bf5195312b48dfd90fb1e94ebb26747232c4910a22a09',
    'receipt_sha256': '4fbcfbaf6c76e70b5fbad43e57624c4ec0917abb1aebcdf96a79d525f99cf31c',
  },
  'empirical-s2-ri-row-admission-v1.json': {
    'file_sha256': 'c3de2b51bfd80e6b7122db15277071e5cb6afbed7ebc8773cb70a97513ae1448',
    'receipt_sha256': '43e0eb373a31757ba44159bc674b2f5fb483a8e999142cf5c28898ee5f4908fc',
  },
  'empirical-s2-ri-signal-contract-v1.json': {
    'file_sha256': '7362932d9fd0a61905ac99fa2a5674bf11cd82ce716263e7d30a7e9f79dc3f3d',
    'receipt_sha256': 'e7b422205eba6ee4d1a5839ff8621e91363c2336cab4f302b477479ae32562fa',
  },
  'empirical-s2-ri-structural-diagnostics-v1.json': {
    'file_sha256': '65df72e30a020a9593638d2ff1370af090f287a5d173745b182d93cb3f863622',
    'receipt_sha256': '3f24defe8e6a3049b279c3b4a80386f97326a393da460a70e05ed7bd3308e807',
  },
  'empirical-s2-ri-support-v1.json': {
    'file_sha256': '1569a72bae5dece07a7572fc6e5c20d5dfa6900b38e91e07cd3f525d15a1276f',
    'receipt_sha256': 'e0b8f3719c9907d7b1b647ce2313c11eda4ed24d686c1cb92ee88236501c7392',
  },
  'empirical-s2-ri-target-contract-v1.json': {
    'file_sha256': '225dade0c492beefe5c544d8a9a6e2af83ca2d032490e20a4ba869172efec1c7',
    'receipt_sha256': 'f871a00be28d345c219e213cd81befc84ee071f153938feb670b2eefac212154',
  },
  'empirical-s2-ri-validation-v1.json': {
    'file_sha256': '5707ce441cf320459c5f92b19eb3279e3b37b7b18bb8a01a1742f5d01d62f5c5',
    'receipt_sha256': '8f2d8be144c28bdb9c9192fca3e8e60b64a95b6937f2e501b0c620aa5df0a191',
  },
}


def safe(path):
  path = Path(path).absolute()
  if '..' in path.parts or any(x.is_symlink() for x in (path, *path.parents)):
    raise ValueError('NO_TRAVERSAL_OR_SYMLINK_POLICY_PATH')
  return path


def load_inputs():
  """Read only fixed public JSON filenames. No private store argument or loader."""
  root = safe(PUBLIC)
  values = {}
  for name, pin in PINS.items():
    raw = safe(root/name).read_bytes()
    if p.sha(raw) != pin['file_sha256']:
      raise ValueError('EXACT_HISTORICAL_FILE_SHA_REQUIRED')
    value = p.verify(json.loads(raw))
    if value['receipt_sha256'] != pin['receipt_sha256']:
      raise ValueError('EXACT_HISTORICAL_RECEIPT_SHA_REQUIRED')
    values[name] = value
  ready = values['empirical-s2-ri-readiness-v1.json']
  if (ready['status'] != 'S2_RI_MODEL_DESIGN_READY_FOR_SEPARATE_FITTING_POLICY'
      or ready['steering_rate_dependency'] != 'NONE' or ready['qlog_model_support'] != 0):
    raise ValueError('S2_RI_FAMILY_READINESS_REQUIRED')
  return values


def filename(label):
  return 'empirical-s2-ri-'+label+'-v1.json'


def build():
  inputs = load_inputs()
  contracts = c.definitions(inputs)
  candidates = c.candidate_set(contracts, inputs)
  source = {n: p.sha(Path(__file__).with_name(n).read_bytes()) for n in (
    'empirical_s2_ri_fitting_policy.py', 'empirical_s2_ri_fitting_contracts.py')}
  states = ['S2_RI_FITTING_POLICY_FROZEN', 'S2_RI_FINITE_CANDIDATE_SET_FROZEN',
    'S2_RI_SELECTION_RULE_FROZEN', 'S2_RI_ROLLOUT_SEMANTICS_FROZEN',
    'MODEL_FITTING_NOT_RUN', 'CV_SCORING_NOT_RUN', 'MODEL_SELECTION_NOT_RUN', 'FINAL_POOLED_REFIT_NOT_AUTHORIZED']
  pol = c.sealed('EMPIRICAL_S2_RI_FITTING_POLICY_V1', generation='S2_RI_FITTING_POLICY_V1',
    baseline=BASELINE, family='S2_RI_V1', status=states[0], states=states,
    historical_inputs=PINS, source_sha256=source, contracts={k:v['receipt_sha256'] for k,v in contracts.items()},
    candidate_set_sha256=candidates['receipt_sha256'], primary_scope=c.PRIMARY, non_rail_scope='DIAGNOSTIC_ONLY',
    route_cv_sha256=inputs[filename('route-cv-contract')]['receipt_sha256'],
    folds=inputs[filename('route-cv-contract')]['folds'],
    future_execution='S2_RI_RETROSPECTIVE_FIT_AND_CV_V1_REQUIRES_SEPARATE_EXPLICIT_AUTHORIZATION',
    execution_authorized=False, private_numeric_access=False,
    execution_order='LEXICAL_CANDIDATE_ID_THEN_FOLD_A_THEN_FOLD_B',
    coefficient_sets_per_candidate=2, expected_fold_jobs=32,
    failure='RECEIPT_EVERY_FAILURE_NO_CANDIDATE_SKIP_NO_GATE_RELAXATION',
    final_pooled_refit='FINAL_POOLED_REFIT_NOT_AUTHORIZED', handoff='SELECTED_CONFIGURATION_AND_TWO_FOLD_LINEAGES_ONLY',
    holdout='HOLDOUT_OPENING_CLOSED', opening_count=0, reservation='NONE',
    independent_validation_allowed=False, privacy='DECLARATIVE_POLICY_AND_PUBLIC_AGGREGATE_PINS_ONLY')
  old = inputs[filename('readiness')]
  preserved = {k: old[k] for k in ('dataset', 'S1', 'S2', 'S3', 'historical_track', 'historical_grid_verdict',
    'stage_b', 'ta', 'sg', 'composition', 'future_holdout', 'calibration_blockers', 'sealed_reference', 'vehicle', 'closed_loop_bias')}
  readiness = c.sealed('EMPIRICAL_S2_RI_FITTING_POLICY_READINESS_V1',
    status='S2_RI_FITTING_POLICY_FROZEN', states=states, policy_sha256=pol['receipt_sha256'],
    design_status=old['status'], candidate_count=16, primary_scope=c.PRIMARY,
    fitting_method='DETERMINISTIC_FLOAT64_OLS', normalization='TRAIN_ROUTE_ONLY',
    route_cv='FROZEN_TWO_FOLD_ROUTE_DISJOINT', comparator='HOLD_LAST_ANGLE', recursive_state='PROJECTED_SOURCE_GRID',
    steering_rate_dependency='NONE', qlog_model_support=0, model_fitting='NOT_RUN', cv_scoring='NOT_RUN',
    model_selection='NOT_RUN', prediction='NOT_RUN', residual='NOT_RUN', rollout='NOT_RUN', normalizer_fitting='NOT_RUN',
    private_arrays_opened=0, actual_metric_values='NOT_COMPUTED', selected_candidate=None,
    final_pooled_refit='NOT_AUTHORIZED', holdout='HOLDOUT_OPENING_CLOSED', opening_count=0, reservation='NONE',
    search='SEARCH_NOT_AUTHORIZED', future_execution_authorized=False, **preserved)
  rows = {filename(k): v for k,v in contracts.items()}
  rows.update({filename('candidate-set'): candidates, filename('fitting-policy'): pol,
               filename('fitting-policy-readiness'): readiness})
  validation = c.sealed('EMPIRICAL_S2_RI_FITTING_POLICY_VALIDATION_V1',
    status='POLICY_SCHEMA_AND_HISTORICAL_BINDINGS_VALIDATED',
    policy_sha256=pol['receipt_sha256'], artifact_receipt_set_sha256=p.sha(p.canonical({k:v['receipt_sha256'] for k,v in rows.items()})),
    historical_inputs_exact=True, fixed_candidate_count=16, fold_job_definitions=32,
    policy_only=True, private_arrays_opened=0, coefficients_generated=0, predictions_generated=0,
    metric_values_computed=0, candidates_selected=0, rollout_executions=0,
    historical_private_preservation='NOT_ACCESSED_NO_WRITES_NO_BYTE_SCAN_CLAIM',
    runtime_and_regression_tests='SEPARATE_REGRESSION_VALIDATION_RECEIPT',
    authority_firewall='NO_EXECUTION_APIS_IMPORTED_OR_EXPOSED')
  rows[filename('fitting-policy-validation')] = validation
  return rows


def validate(bundle):
  """Closed schema: resealing unauthorized changes never authorizes new freedom."""
  expected = build()
  if type(bundle) is not dict or set(bundle) != set(expected):
    raise ValueError('EXACT_COMPLETE_FITTING_POLICY_BUNDLE_REQUIRED')
  for name, value in bundle.items():
    p.verify(value)
    if p.canonical(value) != p.canonical(expected[name]):
      raise ValueError('FITTING_POLICY_CONTRACT_DRIFT')
  return bundle


def publish(output):
  root = safe(output)
  bundle = validate(build())
  # Preflight all destinations before writing; exact existing bytes are resume only.
  encoded = {n: json.dumps(v, sort_keys=True, indent=2, allow_nan=False).encode()+b'\n' for n,v in bundle.items()}
  for name, raw in encoded.items():
    for target in (root/name, root/(name+'.atomic')):
      path = safe(target)
      if path.exists() and (not path.is_file() or path.read_bytes() != raw):
        raise ValueError('IMMUTABLE_POLICY_PUBLICATION_CONFLICT')
  for name in sorted(bundle, key=lambda n: (n == filename('fitting-policy-validation'), n)):
    p.persist(safe(root/name), bundle[name])
  if any(safe(root/name).read_bytes() != raw for name, raw in encoded.items()):
    raise ValueError('EXACT_POLICY_PUBLICATION_BYTES_REQUIRED')
  return bundle


def main():
  parser = argparse.ArgumentParser(description='Freeze public-only S2-RI fitting contracts; never execute a model.')
  parser.add_argument('--output', type=Path, required=True)
  args = parser.parse_args()
  bundle = publish(args.output)
  print(json.dumps({'artifacts': len(bundle), 'policy_sha256': bundle[filename('fitting-policy')]['receipt_sha256'],
                    'status': 'S2_RI_FITTING_POLICY_FROZEN', 'private_arrays_opened': 0}))


if __name__ == '__main__':
  main()
