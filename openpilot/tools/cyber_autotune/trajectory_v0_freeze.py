"""External pins for the pre-algorithm policy commit 2bec29c54; resealing is not authorization."""
import json

from openpilot.tools.cyber_autotune import trajectory_v0_policy as p
from openpilot.tools.cyber_autotune import candidate_architecture as a

PINS = {'config': 'fff05b2a400f589dc9889cd63802b15b76651d5b6191c6d83abe7d722dd23b2d',
 'matrix': 'bc0d00fa77f123aed03747a7562398b9b1e92519a2bef883a1c557e01379de9f',
 'metrics': '2af46ff521830760cbf9639eb1f96006f109b202de6c46c2fcf6f970f60cc739',
 'policy': '37174f03e13ba4d208829581f5972858ed11bfb67c89984c3da9a1b1054a484c',
 'scenarios': '71e8acc2d5efdcf4dfb00885768726fde4b48f4137bf8ac4cf2fde20393ad45d',
 'selection': 'e99cee05d2899c3341eb9076ed62923b220e3832e0719f5433df8d146efb8aec'}


def load():
  rows = {}
  for key, name in p.FILES.items():
    path = p.PUBLIC / name
    if path.is_symlink() or any(v.is_symlink() for v in path.parents):
      raise ValueError('NO_POLICY_SYMLINK')
    row = json.loads(path.read_bytes())
    if row.get('receipt_sha256') != PINS[key]:
      raise ValueError('EXACT_PRE_ALGORITHM_FREEZE_REQUIRED')
    if a.hash_object({k: v for k, v in row.items() if k != 'receipt_sha256'}) != PINS[key]:
      raise ValueError('POLICY_DRIFT')
    rows[key] = row
  p.validate(rows)
  return rows
