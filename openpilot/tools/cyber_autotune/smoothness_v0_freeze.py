"""Externally pinned pre-algorithm SG contracts; no result-driven mutation."""
import json
from openpilot.tools.cyber_autotune import candidate_architecture as a
from openpilot.tools.cyber_autotune.smoothness_v0_policy import PUBLIC

PINS = {'config': ('smoothness-v0-config-v1.json', 'dc95e2de32daf49780509eb48425d3586b3f21a4d7ce6576fa1e8031693c8a5e'),
 'matrix': ('candidate-experiment-matrix-sg-v1.json', 'f1425daadedeca3af8a56bccad883f3fee9422213b806a2e8d1dda02e1ec5199'),
 'metrics': ('smoothness-metric-execution-policy-v1.json', '547a85da3b30491c2668660e145142773d178d9a6217dfaf65f854f75e0665eb'),
 'policy': ('smoothness-family-selection-policy-v1.json', '994bed3c53308cfd83132e4ae32294e2d87ff5f2587e870d6c9d5bf466383ae1'),
 'scenarios': ('smoothness-development-scenarios-v1.json', '24114637c730e6bde73501fb46df88043ee547e8bf2599c9f340156842f5eb3e'),
 'selection': ('smoothness-family-selection-v1.json', '16eef8e12af3bb4e84761597b5168fbf22846acebf865d0ae3ceb238eaeed4b8')}


def load():
  result = {}
  for key, (name, sha) in PINS.items():
    path = PUBLIC/name
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
      raise ValueError("SG_POLICY_SYMLINK")
    row = json.loads(path.read_bytes())
    if row.get("receipt_sha256") != sha or a.hash_object({k:v for k,v in row.items() if k != "receipt_sha256"}) != sha:
      raise ValueError("SG_POLICY_DRIFT")
    result[key] = row
  return result
