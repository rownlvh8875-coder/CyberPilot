#!/usr/bin/env python3
"""Full CI V2 final gate. JSON evidence is accepted only from the exact job/run.

The workflow binds the bundle SHA to the producing job output and downloads its
specific artifact ID from this run. No binaries are transferred to this gate.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import sys

from tools.cyberpilot import full_ci_test_manifest as m

SCHEMA = 'CYBERPILOT_FULL_CI_V2_COMPLETE_COVERAGE_GATE'
REQUIRED_STAGES = ('checkout', 'setup', 'publication_before', 'source_lfs', 'build', 'ruff', 'test_dependency',
                   'native_build', 'native_verify', 'autotune_controls', 'attribution', 'syntax', 'lateral', 'json',
                   'publication_after', 'source_after', 'clean')


def artifact_binding(needs):
  try:
    m.need(set(needs) == {'validate'}, 'CI_PRODUCER_JOB_MISSING')
    outputs = needs['validate']['outputs']
    artifact_id, digest = outputs['artifact_id'], outputs['evidence_sha256']
    m.need(type(artifact_id) is str and re.fullmatch('[1-9][0-9]*', artifact_id) is not None,
           'CI_EXACT_ARTIFACT_ID_REQUIRED')
    m.need(type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest) is not None,
           'CI_EXACT_ARTIFACT_SHA_REQUIRED')
    return {'artifact_id': artifact_id, 'evidence_sha256': digest}
  except (KeyError, TypeError, ValueError) as error:
    raise m.CIIntegrityError('CI_ARTIFACT_BINDING_REJECTED: ' + str(error)) from error


def verify_regression(manifest, result, head):
  m.validate_manifest(manifest)
  m.check_seal(result)
  m.need(manifest['head'] == result['head'] == head and result['schema'] == 'CYBERPILOT_FULL_TEST_RESULT_V2'
         and result['manifest_receipt_sha256'] == manifest['receipt_sha256'] and result['exit_code'] == 0,
         'CI_REGRESSION_BINDING_CONFLICT')
  ids = [r['id'] for r in result['records']]
  m.need(ids == sorted(set(ids)) and ids == manifest['test_ids'], 'CI_REGRESSION_ID_CONFLICT')
  counts = Counter(r['status'] for r in result['records'])
  m.need(counts == result['counts'] == {'passed': manifest['count']}, 'CI_NONPASS_RESULT')
  m.need(all(type(r['seconds']) in (int, float) and r['seconds'] >= 0 for r in result['records']), 'CI_INVALID_DURATION')


def verify_bundle(bundle, head, run_id, needs):
  try:
    m.check_seal(bundle)
    m.need(re.fullmatch('[0-9a-f]{40}', head) is not None and str(run_id).isdigit(), 'CI_EXPECTED_BINDING_INVALID')
    m.need(bundle['schema'] == SCHEMA and bundle['head'] == head and bundle['run_id'] == str(run_id), 'CI_HEAD_RUN_CONFLICT')
    m.need(set(needs) == {'validate'} and needs['validate']['result'] == 'success', 'CI_REQUIRED_JOB_NOT_SUCCESS')
    stages = bundle['stages']
    m.need(set(stages) == set(REQUIRED_STAGES) and all(stages[k]['outcome'] == stages[k]['conclusion'] == 'success'
           for k in REQUIRED_STAGES), 'CI_REQUIRED_STAGE_NOT_SUCCESS')
    native = bundle['native']
    m.need(native['verified'] is True and native['source_sha256'] == m.NATIVE_SOURCE_SHA
           and native['wrapper_sha256'] == m.NATIVE_WRAPPER_SHA and native['compiler_version'] == '13.3.0'
           and native['ABI'] == m.NATIVE_ABI and native['flags'] == list(m.NATIVE_FLAGS)
           and native['private_execution_authorized'] is False and native['runtime_integration_authorized'] is False
           and all(re.fullmatch('[0-9a-f]{64}', native[k]) is not None for k in ('receipt_sha256', 'binary_sha256')),
           'CI_NATIVE_WITNESS_CONFLICT')
    source = bundle['source_integrity']
    m.need(source['frozen_source_pins'] == 231 and source['pointer_count'] == 252 and source['conflicts'] == [], 'CI_SOURCE_CONFLICT')
    verify_regression(bundle['manifest'], bundle['regression'], head)
    return {'status': 'CI_BUNDLE_INTERNAL_CONSISTENCY_VERIFIED', 'head': head, 'run_id': str(run_id),
            'test_count': bundle['manifest']['count'], 'missing_ids': 0, 'duplicate_ids': 0,
            'unapproved_skips': 0, 'collection_errors': 0, 'baseline_ids_sha256': bundle['manifest']['baseline_ids_sha256'],
            'final_ids_sha256': bundle['manifest']['sorted_ids_sha256']}
  except (KeyError, TypeError, ValueError) as error:
    raise m.CIIntegrityError('CI_COMPLETE_COVERAGE_REJECTED: ' + str(error)) from error


def capture(output, evidence):
  output = Path(output)
  steps = json.loads(os.environ['CI_V2_STEPS_JSON'])
  stages = {k: {'outcome': steps.get(k, {}).get('outcome', 'missing'),
                'conclusion': steps.get(k, {}).get('conclusion', 'missing')} for k in REQUIRED_STAGES}
  payload = {'schema': SCHEMA, 'head': os.environ['GITHUB_SHA'], 'run_id': os.environ['GITHUB_RUN_ID'], 'stages': stages}
  for key, file in [('manifest', 'regression/manifest.json'), ('regression', 'regression/regression.json'),
                    ('native', 'native-verified.json'), ('source_integrity', 'source-after.json')]:
    try:
      payload[key] = m.read_json(output / file)
    except (OSError, ValueError):
      payload[key] = {'evidence_missing_or_invalid': True}
  digest = m.write_json(evidence, m.seal(payload))
  with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
    stream.write('evidence_sha256=' + digest + '\n')
  print(json.dumps({'evidence_sha256': digest, 'stages': stages}, indent=2))


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('mode', choices=('capture', 'verify', 'preflight'))
  parser.add_argument('--directory', type=Path)
  parser.add_argument('--evidence', type=Path)
  args = parser.parse_args()
  if args.mode == 'preflight':
    print(json.dumps(artifact_binding(json.loads(os.environ['CI_V2_NEEDS_JSON']))))
    return
  m.need(args.directory is not None and args.evidence is not None, 'CI_EVIDENCE_LOCATION_REQUIRED')
  if args.mode == 'capture':
    capture(args.directory, args.evidence)
  else:
    binding = artifact_binding(json.loads(os.environ['CI_V2_NEEDS_JSON']))
    expected = os.environ['CI_V2_EXPECTED_EVIDENCE_SHA256']
    m.need(expected == binding['evidence_sha256'], 'CI_PRODUCER_SHA_CONFLICT')
    m.need(re.fullmatch('[0-9a-f]{64}', expected) is not None, 'CI_ARTIFACT_EXPECTED_SHA_REQUIRED')
    # Directory traversal and regular-file checks are performed by read_json.
    bundle = m.read_json(args.evidence, expected_digest=expected)
    result = verify_bundle(bundle, os.environ['GITHUB_SHA'], os.environ['GITHUB_RUN_ID'], json.loads(os.environ['CI_V2_NEEDS_JSON']))
    m.need(bundle['manifest']['baseline_count'] == m.BASELINE_COUNT
           and bundle['manifest']['baseline_ids_sha256'] == m.BASELINE_IDS_SHA
           and bundle['source_integrity']['lfs_materialized_verified'] == 251, 'CI_BASELINE_OR_LFS_COVERAGE_CONFLICT')
    baseline = (m.ROOT / m.BASELINE_IDS_FILE).read_text().splitlines()
    m.need(len(baseline) == m.BASELINE_COUNT and m.ids_hash(baseline) == m.BASELINE_IDS_SHA
           and set(baseline) <= set(bundle['manifest']['test_ids']), 'CI_ACTUAL_BASELINE_IDS_MISSING')
    source = m.source_integrity(verify_lfs=False)
    m.need(source['ci_v2_lock_receipt_sha256'] == bundle['source_integrity']['ci_v2_lock_receipt_sha256'], 'CI_SOURCE_BUNDLE_CONFLICT')
    result['status'] = 'FULL_CI_V2_COMPLETE_COVERAGE_VERIFIED'
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
  try:
    main()
  except (m.CIIntegrityError, KeyError, OSError, ValueError) as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1) from error
