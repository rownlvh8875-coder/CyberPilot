"""Pinned aggregate attribution evidence; private arrays are never dependencies."""

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_source_execution as prior
from openpilot.tools.cyber_autotune import empirical_stage_a_attribution as attribution
from openpilot.tools.cyber_autotune import empirical_v3_publication as old

PINS = {
  'empirical-stage-a-attribution-readiness-v1.json': '2528c42dc66b1d815d47df199ba8b508e487f91404a7943846b34f75e3e6fcfc',
  'empirical-stage-a-causal-separator-audit-v1.json': 'd5e4e0e0bd8995e3585472235a422d267cbd2af7386ea12b644de4d079e962bb',
  'empirical-stage-a-quantization-audit-v1.json': 'c3a440da88742b45aa4f49c4c093b1022a242d6cd57526ca3ce648bfaee850e5',
  'empirical-stage-a-regime-policy-v1.json': '0cb9cfa6c281f3ba034397790a33ea5742f06ccc0304dc6d495b817ccc8456f4',
  'empirical-stage-a-regime-results-v1.json': '13ef725672a3baaf9118442530652f4b4de9e393db74eba03b6c9bb732a25a9a',
  'empirical-stage-a-repeatability-v1.json': '259da0d127399b4ed597ca4ec1d737ffb65492e0ec631d162369d7a49ded43b9',
}


def load():
  old.load()
  rows = {name: attribution.validate_public(prior.read(p.PUBLIC / name)) for name in PINS}
  if any(rows[name]['receipt_sha256'] != digest for name, digest in PINS.items()):
    raise ValueError('ATTRIBUTION_PUBLIC_PIN_DRIFT')
  policy = rows['empirical-stage-a-regime-policy-v1.json']
  result = rows['empirical-stage-a-regime-results-v1.json']
  repeat = rows['empirical-stage-a-repeatability-v1.json']
  if policy != attribution.policy() or result['policy_sha256'] != policy['receipt_sha256']:
    raise ValueError('ATTRIBUTION_PUBLIC_POLICY_CHAIN_DRIFT')
  attribution.validate_repeatability(repeat, result['receipt_sha256'])
  if result['v3_private_before_sha256'] != result['v3_private_after_sha256']:
    raise ValueError('V3_PRIVATE_PRESERVATION_FAILURE')
  return rows
