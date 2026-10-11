"""Aggregate-only paired campaign pins. Never opens full local frames or raw logs."""

import json

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import cyber_h1_pairing as q
from openpilot.tools.cyber_autotune import cyber_h1_paired_visual_adapter as adapter
from openpilot.tools.cyber_autotune import cyber_h1_comparison_server as server

PINS = {
  'cyber-h1-paired-campaign-policy-v1.json': '419c5bb1193ab5fac474383ced8ab776d3344b37bdac98492a20d7746ead13cb',
  'cyber-h1-paired-campaign-manifest-v1.json': '26e435619b374ae9f0e4a30d5b6aa067146b752e8087ef5fdb749ed00c656cc4',
  'cyber-h1-paired-trace-repeatability-v1.json': '8eeb2efecd7e3108ae78dcfb54741a14688510601bd70172a9c09c6b21e577c6',
  'cyber-h1-paired-frame-schema-v1.json': 'a5113752c0318500570ef3183141fee3a8abd11fe71ac14a494cbe8211683038',
  'cyber-h1-comparison-catalog-v1.json': '90c5a923ee471ee05bff21b50af640fb05ff018f62f32dab039b6cf5b4bcbfe1',
  'cyber-h1-comparison-server-contract-v1.json': '16ca11db47de46f94617e7db4941b0834daba6600d63bf43d8846e347bbd4815',
  'cyber-h1-comparison-browser-validation-v1.json': '21d38e4a64f062db06f95c2ab243b778d1466369cd16d6c3b12804622d57d52a',
  'cyber-h1-comparison-readiness-v1.json': 'b513a1d98b898647342b532c760d16d3081786b0e2ac8a93bc7c8b120616a1b3',
}


def read(name):
  path = p.PUBLIC / name
  if any(part.is_symlink() for part in (path, *path.parents)):
    raise ValueError('PAIR_PUBLICATION_SYMLINK')
  row = q.verify(json.loads(path.read_bytes()))
  if row['receipt_sha256'] != PINS.get(name):
    raise ValueError('PAIR_FIXED_PUBLICATION_PIN_DRIFT')
  return row


def validate_server_contract():
  row = read('cyber-h1-comparison-server-contract-v1.json')
  if row != server.contract():
    raise ValueError('PAIR_FIXED_SERVER_SOURCE_DRIFT')
  return row


def validate_catalog(cat):
  if cat != read('cyber-h1-comparison-catalog-v1.json'):
    raise ValueError('PAIR_FIXED_OUTPUT_DIGEST_SET_DRIFT')
  return cat


def validate(rows):
  if set(rows) != set(PINS) or len(rows) != 8:
    raise ValueError('PAIR_EXACT_EIGHT_PUBLIC_ARTIFACTS')
  for name, row in rows.items():
    q.verify(row)
    if row['receipt_sha256'] != PINS[name]:
      raise ValueError('PAIR_PUBLICATION_PIN_DRIFT')
  if (
    rows['cyber-h1-paired-campaign-policy-v1.json'] != q.policy()
    or rows['cyber-h1-paired-frame-schema-v1.json'] != adapter.schema()
    or rows['cyber-h1-comparison-server-contract-v1.json'] != server.contract()
  ):
    raise ValueError('PAIR_PUBLIC_SOURCE_CONTRACT_DRIFT')
  manifest = rows['cyber-h1-paired-campaign-manifest-v1.json']
  cat = rows['cyber-h1-comparison-catalog-v1.json']
  repeat = rows['cyber-h1-paired-trace-repeatability-v1.json']
  browser = rows['cyber-h1-comparison-browser-validation-v1.json']
  ready = rows['cyber-h1-comparison-readiness-v1.json']
  from openpilot.tools.cyber_autotune.cyber_h1_comparison_catalog import catalog

  entries = manifest['runs']
  if (
    len(entries) != 22
    or catalog(entries) != cat
    or repeat['h1_packages'] != 88
    or repeat['paired_framesets'] != 44
    or repeat['status'] != 'EXACT_PASS'
    or repeat['observer_noninterference'] != 'EXACT_HISTORICAL_FULL_RESULT_BYTES'
    or browser['status'] != 'ACTUAL_BROWSER_VALIDATED'
    or browser['campaign_count'] != 2
    or browser['scenarios_per_campaign'] != 11
    or any(browser[k] != 0 for k in ('javascript_errors', 'console_warnings', 'network_errors', 'external_network_requests'))
    or browser['server_contract_sha256'] != server.contract()['receipt_sha256']
    or browser['catalog_sha256'] != cat['receipt_sha256']
    or ready['holdout_opening'] != 'CLOSED'
    or ready['opening_count'] != 0
    or ready['calibration_blockers'] != p.BLOCKERS
    or ready['manifest_sha256'] != manifest['receipt_sha256']
    or ready['repeatability_sha256'] != repeat['receipt_sha256']
    or ready['browser_sha256'] != browser['receipt_sha256']
  ):
    raise ValueError('PAIR_PUBLIC_EVIDENCE_LINK_DRIFT')
  return rows


def load():
  from openpilot.tools.cyber_autotune.cyber_h1_visual_publication import load as old

  old()
  return validate({name: read(name) for name in PINS})
