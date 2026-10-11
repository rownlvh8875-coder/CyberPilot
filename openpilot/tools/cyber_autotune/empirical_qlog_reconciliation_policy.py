"""Additive authorization for the two historical exclusions, never route discovery."""
from pathlib import Path

from openpilot.tools.cyber_autotune import empirical_plant_policy as p
from openpilot.tools.cyber_autotune import empirical_causal_dataset_policy as base
from openpilot.tools.cyber_autotune import empirical_causal_dataset_publication as historical


def resolve_exclusions(routes, history):
  if len(routes) != 2 or len({r['route_id'] for r in routes}) != 2:
    raise ValueError('EXACT_TWO_HISTORICAL_ROUTES_REQUIRED')
  result = []
  for route in routes:
    rid = route['route_id']
    expected = [x for x in history[rid] if x['kind'] == 'qlog.zst']
    excluded = route['excluded_sources']
    def signature(x):
      return (x['source_sha256'], x['ordinal'], x['kind'])
    if (sorted(map(signature, expected)) != sorted(map(signature, excluded))
        or len({x['source_sha256'] for x in excluded}) != len(excluded)):
      raise ValueError('EXACT_HISTORICAL_QLOG_EXCLUSIONS_REQUIRED')
    result.extend((route, x) for x in sorted(expected, key=lambda x: x['ordinal']))
  if len(result) != 2 or len({s['source_sha256'] for _, s in result}) != 2:
    raise ValueError('EXACT_TWO_DISTINCT_QLOGS_REQUIRED')
  return result


def code_identity():
  names = ('empirical_qlog_source_audit', 'empirical_qlog_reconciliation_policy', 'empirical_qlog_reconciliation',
           'empirical_qlog_publication')
  root = Path(__file__).parent
  return {n: p.sha((root/(n+'.py')).read_bytes()) for n in names}


def policy():
  inputs = historical.load()
  return p.seal({'schema': 'EMPIRICAL_QLOG_RECONCILIATION_POLICY_V1', 'generation': 'QLOG_HISTORICAL_RECONCILIATION_V1',
    'historical_inputs': {n: x['receipt_sha256'] for n, x in inputs.items()},
    'executor_sources': code_identity(), 'reused_executor_sources': base.code_identity(),
    'numeric_scope': 'EXACT_TWO_HISTORICALLY_EXCLUDED_QLOGS_ONLY',
    'role': base.ROLE, 'dt_ns': 10000000, 'max_age_ns': 20000000,
    'signal_whitelist': base.WHITELIST, 'unavailable_fields': base.UNAVAILABLE,
    'grid': 'LATEST_PAST_NO_FILL_NO_INTERPOLATION_ALL_ROWS_SEGMENT_LOCAL',
    'origin': 'OLD_GLOBAL_INDICES_UNCHANGED_SEPARATE_RECONCILED_GLOBAL_INDEX_OVERLAY',
    'merge': 'VIRTUAL_READ_ONLY_154_RLOG_REFERENCE_PLUS_TWO_NEW_QLOG_RECEIPTS',
    'cadence': 'QLOG_DOWNSAMPLED_NOT_100HZ_EQUIVALENT_NO_AGE_RELAXATION',
    'model_fitting': 'NOT_RUN', 'model_selection': 'NOT_RUN', 'candidate_execution': 'NOT_RUN',
    'holdout': 'HOLDOUT_OPENING_CLOSED', 'opening_count': 0, 'reservation': 'NONE',
    'qualification_allowed': False, 'production_authority': False, 'vehicle_activation_allowed': False,
    'ta_execution': False, 'sg_execution': False, 'composition_authorized': False,
    'privacy': 'AGGREGATES_HASHES_ONLY_NO_PATH_CLOCK_ROW_SIGNAL_OR_PRIVATE_ARRAY',
    'calibration_blockers': p.BLOCKERS})


def require_segment(auth, rid, digest, kind):
  expected = {(s['route_id'], s['source_sha256'], s['kind']) for s in auth['segments']}
  if len(expected) != 2 or kind != 'qlog.zst' or (rid, digest, kind) not in expected:
    raise ValueError('EXACT_TWO_QLOG_DECODER_GATE')
