"""Verify fixed local metadata artifacts and emit deterministic metadata results."""
import argparse
import hashlib
import importlib.util
import json
import stat
from pathlib import Path
from typing import Any, Protocol, cast

ROOT = Path(__file__).resolve().parent


class BoundaryAPI(Protocol):
  MAX_DOCUMENT_BYTES: int
  def load_json(self, raw: bytes) -> dict[str, Any]: ...
  def validate_contract(self, value: object) -> dict[str, Any]: ...
  def validate_record(self, value: object, contract: object) -> dict[str, Any]: ...
  def canonicalize_record(self, value: object) -> bytes: ...
  def hash_record(self, value: object) -> str: ...


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output-dir', type=Path, required=True)
  args = parser.parse_args()
  spec = importlib.util.spec_from_file_location('source_boundary', ROOT / 'source_boundary.py')
  if spec is None or spec.loader is None:
    raise RuntimeError('BOUNDARY_MODULE_UNAVAILABLE')
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  api = cast(BoundaryAPI, module)
  artifact_root = ROOT / 'artifacts'
  if artifact_root.is_symlink():
    raise ValueError('ARTIFACT_DIRECTORY_SYMLINK')

  def read(name: str) -> dict[str, Any]:
    path = artifact_root / name
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
      raise ValueError('ARTIFACT_PATH_TYPE')
    if info.st_size > api.MAX_DOCUMENT_BYTES:
      raise ValueError('ARTIFACT_TOO_LARGE')
    with path.open('rb') as source:
      raw = source.read(api.MAX_DOCUMENT_BYTES + 1)
    return api.load_json(raw)

  contract = api.validate_contract(read('source_boundary_contract.json'))
  static_result = api.validate_record(read('static_metadata_envelope.json'), contract)
  reference_result = api.validate_record(read('synthetic_descriptor_envelope.json'), contract)
  result = {'status': 'F70UB_SOURCE_BOUNDARY_METADATA_LOCAL_PASS',
            'contract_id': contract['contract_id'], 'contract_sha256': api.hash_record(contract),
            'validated_metadata_records': 2, 'calculator_input_created': False,
            'numeric_samples_admitted': False, 'production_samples_admitted': False,
            'context_instance_resolved': False, 'r_budget_resolved': False,
            'F70V_allowed': False, 'F71_allowed': False}
  seal = {'scope': 'EXTERNAL_METADATA_CONTRACT_ONLY',
          'contract_sha256': api.hash_record(contract),
          'static_result_sha256': api.hash_record(static_result),
          'reference_result_sha256': api.hash_record(reference_result),
          'result_sha256': api.hash_record(result),
          'existing_instance_status': 'F70UB_BLOCKED_STATIC_EVIDENCE_INSUFFICIENT'}
  files = {'source_boundary_contract.json': api.canonicalize_record(contract),
           'static_metadata_validation.json': api.canonicalize_record(static_result),
           'synthetic_descriptor_validation.json': api.canonicalize_record(reference_result),
           'boundary_result.json': api.canonicalize_record(result),
           'final_seal.json': api.canonicalize_record(seal)}
  manifest = ''.join(hashlib.sha256(raw).hexdigest() + '  ' + name + '\n' for name, raw in sorted(files.items()))
  files['SHA256SUMS.txt'] = manifest.encode('ascii')
  args.output_dir.mkdir(parents=True, mode=0o700, exist_ok=False)
  for name, raw in sorted(files.items()):
    with (args.output_dir / name).open('xb') as output:
      output.write(raw)
  print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
  main()
