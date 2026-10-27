"""Validate or deterministically regenerate the registered F70U static contract."""
import argparse
import json
from pathlib import Path

from tools.cyberpilot.f70u.context_contract import ARTIFACTS, generate_contract_bundle, load_context_contract, validate_context_contract


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--contract', type=Path, default=ARTIFACTS / 'static_context_contract.json')
  parser.add_argument('--output-dir', type=Path)
  args = parser.parse_args()
  try:
    contract = load_context_contract(args.contract)
    result = validate_context_contract(contract)
    if result.schema_valid and args.output_dir is not None:
      generate_contract_bundle(contract, args.output_dir)
    print(json.dumps(result.as_dict(), ensure_ascii=False, sort_keys=True, separators=(',', ':')))
    return 0 if result.schema_valid else 1
  except (ValueError, OSError):
    print('{"errors":["F70U_CONTRACT_INPUT_INVALID"],"schema_valid":false}')
    return 1


if __name__ == '__main__':
  raise SystemExit(main())
