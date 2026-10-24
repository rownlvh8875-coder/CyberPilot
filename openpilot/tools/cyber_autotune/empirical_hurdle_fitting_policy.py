"""Public-only immutable Hurdle fitting-policy builder. No numerical execution."""

import argparse
import json
from pathlib import Path
from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_hurdle_fitting_contracts as c

BASELINE = 'cce79c2762e4e83f39fa2239f7129253fb5b713b'
SOURCES = ('empirical_hurdle_fitting_policy.py', 'empirical_hurdle_fitting_contracts.py')
PINS = {
  'empirical-hurdle-composition-contract-v1.json': {
    'file_sha256': '9c0f48ffada6ce8e905d85d9d72df21a3997f9ce6dc757bb96d9291218046948',
    'receipt_sha256': '046d0ba328c7a52421aedfff504ed20ad27114785d67054f6e78fd8547eccc67',
  },
  'empirical-hurdle-conditional-delta-target-v1.json': {
    'file_sha256': '5187c5f0fdb19285dca424b24a54cce3747ab7c59057a5bbf933859e71d1fe2d',
    'receipt_sha256': 'a29d77ce85acf114b1f54c5a1a80785fb9a83cea7ecd6b608ff731b4d683030c',
  },
  'empirical-hurdle-design-evidence-v1.json': {
    'file_sha256': 'c7677194276983192ac90f25ad9f4758e426367698ae62a8e5d49cf6f2dda2f5',
    'receipt_sha256': '49abff45affee17049e4864b99731526acd3952b2efacea24c30047c5819d9cc',
  },
  'empirical-hurdle-design-readiness-v1.json': {
    'file_sha256': '955c96a711a2628fbf3ea4dce6a30b5ff6036df5ab84fffc20dfcfb11ac071ec',
    'receipt_sha256': '8d08f9c06583983e237cbdf92dc6028865a3d87a9a289aaba00ea895ede9fd2a',
  },
  'empirical-hurdle-design-validation-v1.json': {
    'file_sha256': 'b6752a1aab3bfba475eda539b2ef1af9fa54199178c676b36018db071167ade0',
    'receipt_sha256': '94da1e54aaaf705fb1be3aa987b71242cf3b50654326788375c70ddd7153575a',
  },
  'empirical-hurdle-diagnostic-contract-v1.json': {
    'file_sha256': 'bb1f4c0766a3a0bbd81f59388f5b0c6810fc19c89a40a0cb0c2fb7bd0dc8e89c',
    'receipt_sha256': '68aeaf13efc8912fa62400d73352c3c3314557123405d529811980ad56d15b17',
  },
  'empirical-hurdle-family-contract-v1.json': {
    'file_sha256': 'cccaba738cb55c2506269976d1cb86510a90ba2d20f41004493d05f1aeab1d41',
    'receipt_sha256': 'c780fa1e75bdb3d13480f4863b6dabb7c7dbfe68797032fce582b7854d45dfe3',
  },
  'empirical-hurdle-feature-contract-v1.json': {
    'file_sha256': '8676c89bcfe629d6bcc60706172ca29f79ee42430e67893c8ee837a7da672488',
    'receipt_sha256': '517288519b2ae0ef9edaa4b2a0c5e5a1b296389e4381ac4af0a2bddfec41be3a',
  },
  'empirical-hurdle-future-fitting-requirements-v1.json': {
    'file_sha256': '7b92cea1d8e87c6eaa875199d80cc724a7e3bf096a83a24b78b469bfe686d869',
    'receipt_sha256': '8cfa83d6e1e613796925f532be5d391016da31d7da87b0009662d4c8d8c99989',
  },
  'empirical-hurdle-move-gate-target-v1.json': {
    'file_sha256': '362d73b231c810f4e1ccd5f376effe0b7887eea77f3d9e5c211403d54dc03bbe',
    'receipt_sha256': '0ca483ef467c7039214956cc3c599256ac23147a89e9dccc13d098abb9dfa23d',
  },
  'empirical-hurdle-normalization-policy-v1.json': {
    'file_sha256': 'f262c6a82a8d3a716a8c5464f8ec179f4b2a0a7af155f2a26446405828c160b1',
    'receipt_sha256': '618772cfcd852113da81b60b5570e33b4eaba8959022bf8eba498392da0033dc',
  },
  'empirical-hurdle-rollout-contract-v1.json': {
    'file_sha256': '772d5febe8894c189c8332836365149467c0c5870bd630d0db1be7372ebc3d04',
    'receipt_sha256': 'ae1b447a4abdc3c5ba4c34adcfa4c650d3ee35b9229d899a8d6ff557ce09bb92',
  },
  'empirical-hurdle-structural-candidates-v1.json': {
    'file_sha256': '5acdb0b5aa4413965ba37dc6dfe27e724a0c8b8b1319869abaee6db10e61fdc6',
    'receipt_sha256': 'b3935fb07073d8f8445f6db263624f93929cb269c780455d00e3c589cdef20b3',
  },
  'empirical-hurdle-training-population-v1.json': {
    'file_sha256': 'e7646168c73759c63cc78de43b57936be062f29c54b2afca3c449431409b8a24',
    'receipt_sha256': '98b9296594b087df720b626389438c76072148c7a4d5709b11bca4df04507a0c',
  },
  'empirical-s2-ri-route-cv-contract-v1.json': {
    'file_sha256': 'd3f935674a760754222bf5195312b48dfd90fb1e94ebb26747232c4910a22a09',
    'receipt_sha256': '4fbcfbaf6c76e70b5fbad43e57624c4ec0917abb1aebcdf96a79d525f99cf31c',
  },
  'empirical-s2-ri-fitting-metric-contract-v1.json': {
    'file_sha256': '3d4121f6a5c1f85d08c0af8dcbbf6a3796738a04b20c5a8e09e91b053744b6bc',
    'receipt_sha256': 'a554c0fa7848890ffc8e756874eddcd12c3a0e91b0a4b39c3eb3c3404db3bd70',
  },
  'empirical-s2-ri-fitting-grid-contract-v1.json': {
    'file_sha256': '7f079c65e5c75ac9521a829874d17a9ded00e36ac0aa627a2ea8a86d0d515c89',
    'receipt_sha256': 'ff2b3c0cfa926b029dda87dbfb8fc80ec1cbb57a58b59bb20430bef0c6c7a9af',
  },
}


def safe(path):
  path = Path(path).absolute()
  if '..' in path.parts or any(x.is_symlink() for x in (path, *path.parents)):
    raise ValueError('HURDLE_FITTING_POLICY_UNSAFE_PATH')
  return path


def filename(label):
  return 'empirical-hurdle-' + label + '-v1.json'


def check_inputs(inputs):
  try:
    if set(inputs) != set(PINS):
      raise ValueError('input set')
    for name, value in inputs.items():
      p.verify(value)
      if value['receipt_sha256'] != PINS[name]['receipt_sha256']:
        raise ValueError('receipt pin')
    ready = inputs[filename('design-readiness')]
    expected = {
      'status': 'HURDLE_FAMILY_DESIGN_READY_FOR_SEPARATE_FITTING_POLICY',
      'family': 'HURDLE_RI_V1',
      'steering_rate_dependency': 'NONE',
      'structural_configurations': 16,
      'move_gate_threshold': 'UNSET',
      'hurdle_acceptance_policy': 'NOT_YET_FROZEN',
      'historical_verdict': 'S2_RI_NO_ADMISSIBLE_CANDIDATE',
    }
    if any(ready.get(k) != v for k, v in expected.items()):
      raise ValueError('readiness')
    return inputs
  except (ValueError, KeyError, TypeError) as exc:
    raise ValueError('HURDLE_FITTING_POLICY_DESIGN_BINDING_CONFLICT') from exc


def load_inputs():
  values = {}
  try:
    for name, pin in PINS.items():
      raw = safe(p.PUBLIC / name).read_bytes()
      if p.sha(raw) != pin['file_sha256']:
        raise ValueError('file pin')
      values[name] = json.loads(raw)
    return check_inputs(values)
  except (ValueError, OSError, TypeError) as exc:
    raise ValueError('HURDLE_FITTING_POLICY_DESIGN_BINDING_CONFLICT') from exc


def build():
  inputs = load_inputs()
  contracts = c.definitions(inputs)
  source = {name: p.sha(Path(__file__).with_name(name).read_bytes()) for name in SOURCES}
  contracts['fitting-policy'] = c.sealed(
    'fitting-policy',
    status=c.READY,
    baseline=BASELINE,
    historical_inputs=PINS,
    source_sha256=source,
    contract_sha256={k: v['receipt_sha256'] for k, v in contracts.items()},
    exact_candidates=16,
    expected_candidate_fold_jobs=32,
    job_order=[[x['candidate_id'], f] for x in contracts['candidate-set']['candidates'] for f in ('FOLD_A', 'FOLD_B')],
    complete_accounting='EVERY_JOB_PASS_PRECONDITION_FAILURE_NUMERICAL_FAILURE_OR_INSUFFICIENT_SUPPORT_NO_SILENT_SKIP',
    early_stop=False,
    actual_execution_authorized=False,
    composition={
      'move_operator': '>',
      'static_operator': '<=',
      'static_delta': 0.0,
      'static_tick': 'CURRENT_PROJECTED_TICK',
      'stage2_on_static': False,
      'move_delta': 'STAGE2_FROZEN_MOVE_NORMALIZER_AND_COEFFICIENTS',
      'projection': 'DIRECT_ROUND_HALF_TO_EVEN_TO_INTEGER_TICK',
      'projection_input': 'BINARY64_CURRENT_TICK_PLUS_CONDITIONAL_DELTA',
      'projected_range': 'SIGNED16_INTEGER_TICK_RANGE_FAIL_WHOLE_FOLD_ON_VIOLATION',
      'force_minimum_movement': False,
      'soft_blending': False,
      'debounce': False,
      'hysteresis': False,
      'clipping': False,
      'epsilon': 0,
    },
    rollout={
      'design_sha256': inputs[filename('rollout-contract')]['receipt_sha256'],
      'state': 'PROJECTED_INTEGER_TICK',
      'stage1': 'EACH_RECURSIVE_STEP',
      'stage2': 'ONLY_PREDICTED_MOVE',
      'future_measured_steering_feedback': False,
      'future_measured_move_label': False,
      'horizons_steps': c.HORIZONS,
      'sample_period_seconds': 0.01,
      'horizon_seconds': [0.25, 0.5, 1.0, 2.0],
      'off_by_one': 'ANCHOR_k_PLUS_H_AFTER_H_TRANSITIONS_PATH_LENGTH_H_PLUS_1',
      'initial_state': 'OBSERVED_TICK_k_AND_DELTA_HISTORY_THROUGH_k_MINUS_1',
      'delta_history_update': 'APPEND_NEW_PROJECTED_TICK_MINUS_PREVIOUS_PROJECTED_TICK',
      'exogenous': ['LOGGED_NORMALIZED_POST_CARCONTROLLER_COMMAND', 'RECORDED_VEGO'],
      'semantics': 'LOGGED_EXOGENOUS_COMMAND_CONDITIONED_ROLLOUT',
      'boundary': 'ENTIRE_HISTORY_AND_HORIZON_SAME_ROUTE_SEGMENT_S2_RI_RUN_ELIGIBLE_STREAK_EXACT_100HZ',
      'required': 'COMMAND_AND_VEGO_AVAILABLE_ENTIRE_WINDOW_NO_PADDING_NO_INTERPOLATION',
      'numeric_failure': 'WHOLE_FOLD_FAILURE_NO_ROW_DROP',
    },
    stage_models='TWO_SEPARATE_NORMALIZERS_COEFFICIENT_RECEIPTS_PLUS_STAGE1_PRIVATE_THRESHOLD_PER_FOLD',
    primary_scope='SCOPE_ALL_ACTIVE_NO_OVERRIDE',
    stage1_feature_sha256=inputs[filename('feature-contract')]['receipt_sha256'],
    stage2_feature_sha256=inputs[filename('feature-contract')]['receipt_sha256'],
    steering_rate_dependency='NONE',
    policy_change_after_performance='FORBIDDEN_REQUIRES_INVALIDATION_AND_SEPARATE_REDESIGN_AUTHORIZATION',
    final_pooled_refit='FINAL_POOLED_REFIT_NOT_AUTHORIZED',
    future_fitting='REQUIRES_SEPARATE_EXPLICIT_EXECUTION_AUTHORIZATION',
    model_parameters='EMPIRICAL_PREDICTIVE_PARAMETERS',
    closed_loop_bias='CLOSED_LOOP_IDENTIFICATION_BIAS_RISK',
    threshold_meaning='MODEL_DECISION_THRESHOLD_NOT_PHYSICAL_EPS_DEADZONE',
  )
  old = inputs[filename('design-readiness')]
  preserved = {
    key: old[key]
    for key in (
      'dataset',
      'S1',
      'S2',
      'S3',
      'historical_track',
      'historical_grid_verdict',
      'stage_b',
      'ta',
      'sg',
      'composition',
      'future_holdout',
      'calibration_blockers',
      'sealed_reference',
      'vehicle',
      'closed_loop_bias',
      'historical_verdict',
      'historical_selection',
      'historical_attribution',
      'no_model_admitted',
      'search',
      'final_pooled_refit',
    )
  }
  contracts['fitting-policy-readiness'] = c.sealed(
    'fitting-policy-readiness',
    status=c.READY,
    states=c.STATES,
    contract_sha256={k: v['receipt_sha256'] for k, v in contracts.items()},
    design_sha256=old['receipt_sha256'],
    source_sha256=source,
    exact_candidates=16,
    expected_jobs=32,
    steering_rate_dependency='NONE',
    move_gate_threshold_policy='TRAIN_ONLY_BALANCED_ACCURACY_FROZEN',
    actual_threshold='NOT_COMPUTED',
    acceptance_policy='FROZEN',
    model_fitting='NOT_RUN',
    move_gate_fitting='NOT_RUN',
    conditional_delta_fitting='NOT_RUN',
    normalizer_fitting='NOT_RUN',
    threshold_selection='NOT_RUN',
    cv_scoring='NOT_RUN',
    prediction='NOT_RUN',
    rollout='NOT_RUN',
    model_selection='NOT_RUN',
    private_arrays_opened=0,
    raw_log_openings=0,
    qlog_openings=0,
    holdout='HOLDOUT_OPENING_CLOSED',
    opening_count=0,
    vehicle_authority=False,
    **preserved,
  )
  contracts['fitting-policy-validation'] = c.sealed(
    'fitting-policy-validation',
    status='PUBLIC_POLICY_AND_SHA_CHAIN_VALIDATED',
    artifact_receipts={k: v['receipt_sha256'] for k, v in contracts.items()},
    source_sha256=source,
    historical_inputs_exact=True,
    private_arrays_opened=0,
    actual_fit_calls=0,
    actual_threshold_selection_calls=0,
    actual_metrics_computed=0,
    actual_prediction_calls=0,
    actual_rollout_calls=0,
    actual_selection_calls=0,
    private_preservation='NOT_ACCESSED_NO_BYTE_SCAN_CLAIM',
    runtime_validation='SEPARATE_FITTING_POLICY_REGRESSION_VALIDATION_RECEIPT',
  )
  return {filename(k): v for k, v in contracts.items()}


def validate(bundle):
  expected = build()
  if type(bundle) is not dict or set(bundle) != set(expected):
    raise ValueError('HURDLE_FITTING_POLICY_CONTRACT_DRIFT')
  for name, value in bundle.items():
    p.verify(value)
    if p.canonical(value) != p.canonical(expected[name]):
      raise ValueError('HURDLE_FITTING_POLICY_CONTRACT_DRIFT')
  return bundle


def publish(output):
  root = safe(output)
  bundle = validate(build())
  encoded = {name: json.dumps(v, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n' for name, v in bundle.items()}
  for name, data in encoded.items():
    for target in (root / name, root / (name + '.atomic')):
      path = safe(target)
      if path.exists() and (not path.is_file() or path.read_bytes() != data):
        raise ValueError('HURDLE_FITTING_POLICY_IMMUTABLE_OUTPUT_CONFLICT')
  for name in sorted(bundle, key=lambda n: (n == filename('fitting-policy-validation'), n)):
    p.persist(safe(root / name), bundle[name])
  if any(safe(root / name).read_bytes() != data for name, data in encoded.items()):
    raise ValueError('HURDLE_FITTING_POLICY_PUBLICATION_BYTES_CONFLICT')
  return bundle


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output', required=True, type=Path)
  args = parser.parse_args()
  bundle = publish(args.output)
  print(json.dumps({'status': c.READY, 'artifacts': len(bundle), 'private_arrays_opened': 0, 'actual_fitting': 'NOT_RUN'}))


if __name__ == '__main__':
  main()
