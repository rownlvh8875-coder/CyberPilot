"""Exact historical synthetic re-execution, with explicit request-root relocation.

Never runs a search or creates configurations. Copies are never execution inputs
after original-root normalization; only relocated, filesystem-verified requests
are executed. Historical JSON is read-only.
"""

import argparse
import copy
import json
import os
from pathlib import Path
import tempfile

from openpilot.tools.cyber_autotune import curvature_yaw_v2_search as s
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / 'docs/cyberpilot/changes'
# Runtime checkout identity is local, never a published personal absolute path.
# Original execution bytes are retained locally and pinned separately; this
# publication-safe reader is not represented as those original executor bytes.
ORIGINAL_ROOT = str(ROOT)
HISTORICAL_EXECUTOR_SHA = '2e7e05ec92e12726cc3c006752c00b437e9ac23ef7fb62a35caca3ff370b5af0'
SOURCE_SHA = digest(Path(__file__).read_bytes())
# Exact file-byte identities from 9a6ae36a6; generated once before execution.
ARCHIVES = {
  'candidate-history-ledger.json': '39f7327e54f12d4c93cf32e540f12a376d3649a96c033580518775627e41d0c1',
  'candidate-v2-delay-domain-search-results.json': 'e68abb4f54cdc403c97465c4f9c144cec992357d7db0aadd35da4dfbc613a6b4',
  'candidate-v2-robustness-results.json': 'b1d3222f5c28753284eef86038caae5406a2662da594063296cc86f3f7b083c4',
  'candidate-family-decision.json': 'e3ed14ef9756399e8c8b7a6657f5e80b403734cdb514e6d9d8b6dbf1533fb919',
  'candidate-v2-violation-ledger.json': '6b92a002b3abaa1fcb9500c7464fa5b2cbf862a1dcea19e1f86f58d343c6fa71',
  'candidate-v1-attribution-results.json': '07309dd5371097a667d1cfa66c46da03041142ee5d20d83c87786dcc295be124',
  'candidate-v2-development-receipts-1.json': '5c6ea0033dc778e73fdfd66d7f45f1841da01ed96fc84d8da2340f12671a5a75',
  'candidate-v2-development-receipts-2.json': '9781c37d548d6f0917d98578fe12029dd4288b9d0e954be5c86d73543098f5db',
  'candidate-v2-development-receipts-3.json': '4e2104061361dcf3d8b2f583aec05238400168e8a38d16cd7d37a937910565f2',
  'candidate-v2-stress-receipts-1.json': '687b52f0cf8ceec153c72f123fc0db8fb20a447f6fbf5801705c2620911ba36b',
  'candidate-v2-stress-receipts-2.json': '984eee8d292574e2e57c765900590c00d182b3d8ec8d3eb659b449df075f4133',
  'candidate-v2-stress-receipts-3.json': '77c22cfd3c5afac3bb0f1568e69b958904b7d34d622f9f90838d325c2f1c6391',
}


def checked(value, expected):
  if value.get('receipt_sha256') != expected or digest(canonical({k: v for k, v in value.items() if k != 'receipt_sha256'})) != expected:
    raise ValueError('EXACT_RECEIPT_REQUIRED')
  return value


def pinned(name):
  data = (PUBLIC / name).read_bytes()
  if name not in ARCHIVES or digest(data) != ARCHIVES[name]:
    raise ValueError('HISTORICAL_ARCHIVE_DRIFT')
  return json.loads(data)


def archived_cases():
  cases = list(pinned('candidate-v2-delay-domain-search-results.json')['evaluation'])
  for i in (1, 2, 3):
    for entry in pinned(f'candidate-v2-development-receipts-{i}.json')['candidate_entries']:
      cases.extend(entry['cases'])
    cases.extend(pinned(f'candidate-v2-stress-receipts-{i}.json')['cases'])
  if len(cases) != 70 or len({case_id(c) for c in cases}) != 70:
    raise ValueError('EXACT_SEVENTY_ARCHIVED_CASES_REQUIRED')
  for c in cases:
    if digest(canonical({k: v for k, v in c.items() if k != 'summary_sha256'})) != c['summary_sha256']:
      raise ValueError('HISTORICAL_CASE_SUMMARY_DRIFT')
  return cases


def case_id(c):
  return digest(canonical({k: c[k] for k in ('scenario', 'role', 'config', 'perturbation', 'selection_sha256')}))


def original_request(request):
  result = copy.deepcopy(request)
  result['native']['source']['root'] = ORIGINAL_ROOT
  return result


def verify_reconstruction(case, old):
  manifest = copy.deepcopy(case['manifest'])
  for i, request in enumerate(case['requests']):
    actual = manifest['identities'][i]
    expected = old['identities'][i]
    if any(actual[k] != expected[k] for k in actual if k != 'request_sha256'):
      raise ValueError('EXACT_HISTORICAL_NATIVE_IDENTITY_REQUIRED')
    if digest(s.encode_request(original_request(request))) != expected['request_sha256']:
      raise ValueError('ONLY_DECLARED_ROOT_RELOCATION_ALLOWED')
  manifest['native_source']['root'] = ORIGINAL_ROOT
  manifest['identities'] = copy.deepcopy(old['identities'])
  if digest(canonical(manifest)) != old['manifest_sha256']:
    raise ValueError('HISTORICAL_MANIFEST_NOT_RECONSTRUCTED')


def normalize_report(report, old):
  """Comparison copy only: exactly undo declared path metadata, no numeric edits."""
  s.validate_report(report)
  result = copy.deepcopy(report)
  result['manifest']['native_source']['root'] = ORIGINAL_ROOT
  result['manifest']['identities'] = copy.deepcopy(old['identities'])
  result['manifest_sha256'] = digest(canonical(result['manifest']))
  for i, arm in enumerate(result['arms']):
    arm['identity'] = copy.deepcopy(old['identities'][i])
    arm['native_result']['request_sha256'] = old['identities'][i]['request_sha256']
    arm['repetition_result_sha256'] = [digest(canonical(arm['native_result']))] * 2
  result['receipt_sha256'] = digest(canonical({k: v for k, v in result.items() if k != 'receipt_sha256'}))
  # Pure persisted validation only. Never execute normalized original-root requests.
  s.validate_report(result)
  if s.summarize(result) != old:
    raise ValueError('HISTORICAL_NUMERIC_OUTPUT_OR_RESULT_DRIFT')
  return result


def immutable(path, data):
  path = Path(path)
  path.parent.mkdir(parents=True, exist_ok=True)
  if path.exists():
    if path.read_bytes() != data:
      raise ValueError('IMMUTABLE_RECOVERY_CONFLICT')
    return
  handle, name = tempfile.mkstemp(dir=path.parent, prefix='.pending-')
  try:
    with os.fdopen(handle, 'wb') as stream:
      stream.write(data)
      stream.flush()
      os.fsync(stream.fileno())
    try:
      os.link(name, path)
    except FileExistsError:
      if path.read_bytes() != data:
        raise ValueError('IMMUTABLE_RECOVERY_CONFLICT') from None
    fd = os.open(path.parent, os.O_RDONLY)
    try:
      os.fsync(fd)
    finally:
      os.close(fd)
  finally:
    Path(name).unlink(missing_ok=True)


def execute(plan_path, output, public):
  global PUBLIC, ORIGINAL_ROOT
  PUBLIC = Path(public)
  ORIGINAL_ROOT = str(PUBLIC.parents[2])
  plan = json.loads(Path(plan_path).read_bytes())
  checked(plan, plan['receipt_sha256'])
  if plan['executor_source_sha256'] != digest(Path(__file__).read_bytes()) or plan['executor_source_sha256'] != SOURCE_SHA:
    raise ValueError('EXECUTOR_SOURCE_DRIFT')
  cases = {case_id(c): c for c in archived_cases()}
  selected = [r for r in plan['cases'] if r['source_head'] == s.build_request('identity')['source']['head']]
  if not selected:
    raise ValueError('NO_FROZEN_CASES_FOR_THIS_CHECKOUT')
  ready = []
  for row in selected:
    old = cases[row['case_id']]
    case = s.build_case(old['scenario'], old['config'], role=old['role'], perturbation=old['perturbation'], selection_sha256=old['selection_sha256'])
    verify_reconstruction(case, old)
    if digest(canonical(case['manifest'])) != row['relocated_manifest_sha256']:
      raise ValueError('PREFROZEN_RELOCATED_MANIFEST_REQUIRED')
    ready.append((row, case, old))
  # Every request in this checkout passes identity checks before first worker.
  for row, case, old in ready:
    p = Path(output) / (row['case_id'] + '.json')
    if p.exists():
      saved = json.loads(p.read_bytes())
      checked(saved, saved['receipt_sha256'])
      if saved['plan_sha256'] != plan['receipt_sha256']:
        raise ValueError('STALE_RECOVERY_PLAN')
      report = saved['relocated_report']
      verify_reconstruction(case, old)
      normalize_report(report, old)
    else:
      report = s.run_case(case, expected_manifest_sha256=row['relocated_manifest_sha256'])
      normalized = normalize_report(report, old)
      saved = {
        'schema': 'EXACT_HISTORICAL_CANDIDATE_RECOVERY_V1',
        'plan_sha256': plan['receipt_sha256'],
        'case_id': row['case_id'],
        'relocated_report': report,
        'historical_result_sha256': [a['repetition_result_sha256'][0] for a in normalized['arms']],
        'historical_summary_sha256': old['summary_sha256'],
        'relocation_only_metadata': True,
        'exact_repeatability': True,
      }
      saved['receipt_sha256'] = digest(canonical(saved))
      immutable(p, canonical(saved))
    print('RECOVERED', old['role'], old['scenario'], row['case_id'][:12], flush=True)


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--plan', required=True)
  parser.add_argument('--output', required=True)
  parser.add_argument('--public', required=True)
  args = parser.parse_args()
  execute(args.plan, args.output, args.public)
