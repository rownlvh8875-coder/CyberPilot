"""Additive, receipt-bound audit of existing descriptive candidate trajectories."""

import argparse
import bisect
from collections import Counter, defaultdict
import json
from pathlib import Path

from openpilot.tools.cyber_autotune import resolution_candidate_audit as a
from openpilot.tools.cyber_autotune import resolution_candidate_repeat as r
from openpilot.tools.cyber_autotune import declared_meter_snapshot as snapshot
from openpilot.tools.cyber_autotune import declared_meter_diagnostic as meter_math
from openpilot.tools.cyber_autotune import curvature_yaw_candidate_history as history
from openpilot.tools.cyber_autotune import native_protocol
from openpilot.tools.cyber_autotune import camera_calibration_evidence, curvature_yaw_attribution
from openpilot.tools.cyber_autotune.native_protocol import canonical, digest

PUBLIC = meter_math.ROOT
METER_SHA = '50982b711bd4348fd6fd2e9a0d70d46a8e2d2e464448b596f81c3dd2cdc59e41'
METER_INDEX_SHA = '16741fe606e3613723cf4662667988f8c84a4fec9e5ca309bdc8f805c3777c7b'
# Full receipt constant is intentionally independent of a Git HEAD changing at commit.
READINESS_SHA = 'b78a4b080c00f823a1a7ce012bf6f2cc31476bba7565c290873edcf5c7ad72dc'
ROLES = ('UPSTREAM_BASELINE', 'CYBER_CURRENT', 'CYBER_CANDIDATE_V1', 'CYBER_CANDIDATE_V2')
NAMES = ('BASELINE', 'CURRENT', 'V1', 'V2')
SOURCE_SHA = digest(Path(__file__).read_bytes())
HELPERS = {
  Path(x.__file__).name: digest(Path(x.__file__).read_bytes())
  for x in (a, r, snapshot, meter_math, history, native_protocol, camera_calibration_evidence, curvature_yaw_attribution)
}


def guard():
  if digest(Path(__file__).read_bytes()) != SOURCE_SHA:
    raise ValueError('AUDIT_SOURCE_DRIFT')
  for x in (a, r, snapshot, meter_math, history, native_protocol, camera_calibration_evidence, curvature_yaw_attribution):
    if digest(Path(x.__file__).read_bytes()) != HELPERS[Path(x.__file__).name]:
      raise ValueError('AUDIT_HELPER_DRIFT')


def meter():
  guard()
  index = json.loads((PUBLIC / snapshot.INDEX).read_bytes())
  r.checked(index, METER_INDEX_SHA)
  result = snapshot.load(PUBLIC)
  if result['receipt_sha256'] != METER_SHA:
    raise ValueError('EXACT_9A6AE36_METER_RECEIPT_REQUIRED')
  return result


def previous_readiness():
  return r.checked(json.loads((PUBLIC / 'declared-hypothesis-meter-readiness-v1.json').read_bytes()), READINESS_SHA)


def ledger():
  original = r.pinned('candidate-history-ledger.json')
  history.validate_history(original['history'])
  entries = {row['entry']['candidate']: row['entry'] for row in original['history']}
  if set(entries) != set(NAMES) or entries['V2']['status'] != 'REJECTED' or entries['CURRENT']['alias_of'] != 'BASELINE':
    raise ValueError('HISTORICAL_CANDIDATE_VERDICT_DRIFT')
  return entries


def envelopes():
  report = meter()
  result = {}
  for row in report['all_declared_envelopes']:
    if row['group'] != 'center':
      continue
    distance = row['distance_m']
    support = [x for x in report['fixed_distance'] if x['group'] == 'center' and x['distance_query_m'] == distance]
    coverage = all(x['valid_samples'] > 0 and x['unavailable_samples'] == 0 for x in support) and len(support) == 78
    result[distance] = {
      **row,
      'reference_coverage_available': coverage,
      'fixed_query_residual_samples': 2240,
      'coverage_semantics': 'FIXED_QUERY_RESIDUAL_EQUIVALENT_NOT_EMPIRICAL_DISTANCE_GT',
    }
  return result


def case_rows(report, envelope):
  manifest = report['manifest']
  arms = report['arms']
  if [arm['arm'] for arm in arms] != list(ROLES) or arms[0]['samples'] != arms[1]['samples']:
    raise ValueError('EXACT_CURRENT_ALIAS_REQUIRED')
  rows = []
  for distance in a.DISTANCES_M:
    points = [a.at_distance(arm['samples'], distance, a.BASIS) for arm in arms]
    for i in (1, 2, 3):
      row = {
        'scenario': manifest['scenario'],
        'role': manifest['role'],
        'config': manifest['config'],
        'perturbation': manifest['perturbation'],
        'candidate': NAMES[i],
        'distance_m': distance,
        'source_scenario_sha256': r.case_id(manifest),
        'repeatable': report['exact_repeatability'],
      }
      relevant = [points[j] for j in (0, 1, i)]
      failure = next((p['status'] for p in relevant if p['status'] != 'AVAILABLE'), None)
      if not report['exact_repeatability']:
        row['classification'] = 'REPEATABILITY_FAILED'
      elif failure:
        row['classification'] = failure
      else:
        p, q = points[0], points[i]
        ref = envelope.get(distance)
        usable = ref if ref and ref.get('reference_coverage_available', True) else None
        row.update(a.compare(p['pose_y_m'], q['pose_y_m'], points[1]['pose_y_m'], usable, True))
        row.update(
          phase=p['phase'],
          candidate_phase=q['phase'],
          phase_transition_bracket=p['phase_transition_bracket'] or q['phase_transition_bracket'],
          speed_mps=p['speed_mps'],
          speed_bucket=a.speed_bucket(p['speed_mps']),
          curvature_sign=a.sign(p['desired_curvature_1pm']),
          curvature_magnitude=a.curvature_bucket(p['desired_curvature_1pm']),
          baseline_time_s=p['time_s'],
          candidate_time_s=q['time_s'],
        )
        if 'effect_sign' in row:
          row['curve_normalized_effect_sign'] = row['effect_sign'] * row['curvature_sign']
      rows.append(row)
  return rows


def summarize(rows):
  rows = sorted(rows, key=canonical)
  by = defaultdict(list)
  for row in rows:
    by[(row['candidate'], row['distance_m'])].append(row)
  distances = []
  for (name, distance), group in sorted(by.items()):
    valid = [r for r in group if 'absolute_effect_m' in r]
    distances.append(
      {
        'candidate': name,
        'distance_m': distance,
        'cases': len(group),
        'available': len(valid),
        'unavailable': len(group) - len(valid),
        'classification_counts': dict(sorted(Counter(x['classification'] for x in group).items())),
        'absolute_effect_m': a.stats(x['absolute_effect_m'] for x in valid),
        'signed_effect_m': a.stats(x['candidate_minus_baseline_m'] for x in valid),
        'effect_to_max_envelope_ratio': a.stats(x['effect_to_max_envelope_ratio'] for x in valid),
      }
    )
  strata = {}
  for field in ('speed_bucket', 'curvature_sign', 'curvature_magnitude', 'phase', 'scenario', 'role'):
    groups = defaultdict(Counter)
    for row in rows:
      groups[str(row.get(field, 'UNAVAILABLE'))][row['classification']] += 1
    strata[field] = {k: dict(sorted(v.items())) for k, v in sorted(groups.items())}
  directions = {}
  for name in ('CURRENT', 'V1', 'V2'):
    selected = [x for x in rows if x['candidate'] == name and 'effect_sign' in x]
    nonstraight = [x for x in selected if x['curvature_sign'] != 0]
    directions[name] = {
      'raw_sign_counts': dict(sorted(Counter(str(x['effect_sign']) for x in selected).items())),
      'curve_normalized_sign_counts': dict(sorted(Counter(str(x['curve_normalized_effect_sign']) for x in nonstraight).items())),
      'status': a.direction_status([x['curve_normalized_effect_sign'] for x in nonstraight]),
      'not_improvement_measure': True,
    }
  return {
    'classification_counts': dict(sorted(Counter(x['classification'] for x in rows).items())),
    'distance_summary': distances,
    'strata': strata,
    'direction_consistency': directions,
  }


def phase_effects(report):
  """Whole-run phase context at baseline observed x, beyond 30m not classified."""
  groups = defaultdict(list)
  base = report['arms'][0]['samples']
  for i in (2, 3):
    trace = report['arms'][i]['samples']
    xs = [p['pose_x_m'] for p in trace]
    if not trace or a.at_distance(trace, xs[0], a.BASIS)['status'] != 'AVAILABLE':
      continue
    for p in base:
      hi = bisect.bisect_left(xs, p['pose_x_m'])
      observed = trace[max(0, hi - 1) : min(len(trace), hi + 1)]
      q = a.at_distance(observed, p['pose_x_m'], a.BASIS)
      if q['status'] == 'AVAILABLE':
        groups[(NAMES[i], p['phase'])].append((p, q))
  return [
    {
      'candidate': name,
      'phase': phase,
      'query_basis': 'BASELINE_OBSERVED_X_SAMPLES_NO_EXTRAPOLATION',
      'absolute_effect_m': a.stats(abs(q['pose_y_m'] - p['pose_y_m']) for p, q in values),
      'query_distance_m': a.stats(p['pose_x_m'] for p, q in values),
      'within_declared_5_30m_count': sum(5 <= p['pose_x_m'] <= 30 for p, q in values),
      'outside_declared_distance_count': sum(not 5 <= p['pose_x_m'] <= 30 for p, q in values),
      'classification': None,
      'reason': 'PHASE_CONTEXT_ONLY_NO_ENVELOPE_EXTRAPOLATION',
    }
    for (name, phase), values in sorted(groups.items())
  ]


def readiness(audit_sha):
  prev = previous_readiness()
  return a.seal(
    {
      'schema': 'MEASUREMENT_RESOLUTION_CANDIDATE_READINESS_V1',
      'status': 'CANDIDATE_EFFECT_AUDIT_COMPLETE',
      'audit_sha256': audit_sha,
      'previous_meter_readiness_sha256': prev['receipt_sha256'],
      'blockers': prev['blockers'],
      'reference_status': 'INDEPENDENT_REFERENCE_UNAVAILABLE',
      'physical_calibration_status': 'INDEPENDENT_CALIBRATION_VALIDATION_PENDING',
      'candidate_verdicts': {k: v['status'] for k, v in ledger().items()},
      'next_plan': {
        'measurement': 'REDUCE_MEASUREMENT_UNCERTAINTY_OR_REDESIGN_LARGER_JUSTIFIED_EFFECT',
        'existing_family': 'FAMILY_REDESIGN_REMAINS_NO_NEW_SEARCH',
        'vehicle_activation': 'PROHIBITED',
      },
    }
  )


def supporting_state(rows):
  valid = [x for x in rows if 'absolute_effect_m' in x]
  if not valid:
    return 'UNCOMPARABLE'
  if all(x['classification'] == 'EFFECT_BELOW_DECLARED_ENVELOPE' for x in valid):
    return 'EFFECT_BELOW_CURRENT_DIAGNOSTIC_RESOLUTION' if len(valid) == len(rows) else 'EFFECT_BELOW_CURRENT_DIAGNOSTIC_RESOLUTION_WHERE_AVAILABLE'
  if any(x['classification'] == 'EFFECT_EXCEEDS_DECLARED_ENVELOPE' for x in valid):
    signs = [x['curve_normalized_effect_sign'] for x in valid if x.get('curvature_sign', 0)]
    if a.direction_status(signs) == 'DIRECTIONALLY_INCONSISTENT_TRADEOFF':
      return 'EFFECT_RESOLVABLE_BUT_DIRECTIONALLY_MIXED'
  return 'EFFECT_PARTIALLY_RESOLVABLE'


def validate_public(value):
  # Frozen complete receipts, rather than a root-key whitelist, reject arbitrary
  # nested coordinates, path injection and resealed numeric/semantic edits.
  from openpilot.tools.cyber_autotune.resolution_candidate_publication import RECEIPTS

  expected = RECEIPTS.get(value.get('schema'))
  if expected is None:
    raise ValueError('STRICT_AUDIT_PUBLICATION_SCHEMA')
  r.checked(value, expected)
  if any(value[k] is not False for k in a.FIREWALL):
    raise ValueError('NONQUALIFYING_AUDIT_REQUIRED')
  if value['total_physical_bound_m'] is not None or value['sealed_reference'] != 'NOT_GENERATED':
    raise ValueError('NONQUALIFYING_AUDIT_REQUIRED')
  return value


def validate_plan(plan):
  r.checked(plan, 'cf6878e16c47125e01906c713da3e9aca8f7a57254f0dd084478bf938d008dec')
  if plan['executor_source_sha256'] != r.HISTORICAL_EXECUTOR_SHA or plan['archives_file_sha256'] != r.ARCHIVES:
    raise ValueError('EXACT_RECOVERY_EXECUTOR_REQUIRED')
  if plan['basis'] != a.BASIS or plan['distances_m'] != list(a.DISTANCES_M):
    raise ValueError('EXACT_PREFROZEN_BASIS_REQUIRED')


def immutable_public(path, data):
  path = Path(path)
  if path.is_symlink() or any(p.is_symlink() for p in path.parents):
    raise ValueError('NO_PUBLICATION_SYMLINK')
  r.immutable(path, data)


def build(recovered, plan):
  guard()
  validate_plan(plan)
  cases = {r.case_id(c): c for c in r.archived_cases()}
  if len(plan['cases']) != 70 or {x['case_id'] for x in plan['cases']} != set(cases):
    raise ValueError('ALL_FROZEN_CASES_REQUIRED')
  planned = {x['case_id']: x for x in plan['cases']}
  rows = []
  phases = []
  proofs = []
  env = envelopes()
  for case_id, old in sorted(cases.items()):
    p = Path(recovered) / (case_id + '.json')
    saved = json.loads(p.read_bytes())
    r.checked(saved, saved['receipt_sha256'])
    if saved['case_id'] != case_id or saved['plan_sha256'] != plan['receipt_sha256'] or saved['exact_repeatability'] is not True:
      raise ValueError('RECOVERY_RECEIPT_BINDING_REQUIRED')
    report = saved['relocated_report']
    if report['manifest_sha256'] != planned[case_id]['relocated_manifest_sha256']:
      raise ValueError('FROZEN_RECOVERED_MANIFEST_REQUIRED')
    normalized = r.normalize_report(report, old)
    if saved['historical_result_sha256'] != [x['repetition_result_sha256'][0] for x in normalized['arms']]:
      raise ValueError('ORIGINAL_RESULT_SHA_REQUIRED')
    rows.extend(case_rows(report, env))
    if old['role'] == 'EVALUATION':
      phases.append(
        {
          'scenario': old['scenario'],
          'role': old['role'],
          'config': old['config'],
          'perturbation': old['perturbation'],
          'effects': phase_effects(report),
          'historical_summary_sha256': old['summary_sha256'],
          'historical_tracking_smoothness_groups': old['groups'],
          'historical_tracking_smoothness_arm_order': list(ROLES),
        }
      )
    proofs.append(
      {
        'case_id': case_id,
        'scenario': old['scenario'],
        'role': old['role'],
        'config': old['config'],
        'perturbation': old['perturbation'],
        'source_head': planned[case_id]['source_head'],
        'original_manifest_sha256': old['manifest_sha256'],
        'identities': old['identities'],
        'recovery_receipt_sha256': saved['receipt_sha256'],
        'historical_summary_sha256': old['summary_sha256'],
        'result_sha256': saved['historical_result_sha256'],
      }
    )
  guard()
  nominal = [x for x in rows if x['role'] == 'EVALUATION']
  met = meter()
  audit = a.seal(
    {
      'schema': 'MEASUREMENT_RESOLUTION_AWARE_CANDIDATE_AUDIT_V1',
      'status': 'CANDIDATE_EFFECT_AUDIT_COMPLETE',
      'source_identity': {'audit_source_sha256': SOURCE_SHA, 'helpers': HELPERS},
      'meter_sha256': METER_SHA,
      'meter_index_sha256': METER_INDEX_SHA,
      'execution_policy_sha256': plan['receipt_sha256'],
      'executed_recovery_source_sha256': plan['executor_source_sha256'],
      'published_recovery_reader_sha256': r.SOURCE_SHA,
      'recovery_publication_redaction': 'LOCAL_CHECKOUT_PATH_REPLACED_BY_RUNTIME_ROOT_NO_NUMERIC_OR_IDENTITY_EDITS',
      'recovery_set_sha256': digest(canonical(proofs)),
      'ledger': ledger(),
      'coverage': met['coverage'],
      'envelopes': list(env.values()),
      'rows': nominal,
      'nominal_summary': summarize(nominal),
      'family_context': [
        {
          'role': role,
          'config': json.loads(config),
          'fourth_arm_semantics': 'ARCHIVED_FAMILY_MEMBER_DIAGNOSTIC_ONLY' if role == 'DEVELOPMENT' else 'SELECTED_V2_HISTORICAL_STRESS_ONLY',
          **summarize([x for x in rows if x['role'] == role and canonical(x['config']).decode() == config]),
        }
        for role, config in sorted({(x['role'], canonical(x['config']).decode()) for x in rows if x['role'] != 'EVALUATION'})
      ],
      'phase_context': [p for p in phases if p['role'] == 'EVALUATION'],
      'open_terms': met['policy']['open_terms'],
      'effect_semantics': 'DESCRIPTIVE_PLANT_COUNTERFACTUAL_EFFECT',
      'basis': a.BASIS,
      'relocation_provenance': 'ROOT_METADATA_ONLY_NORMALIZED_COPY_EXACT_ORIGINAL_SUMMARY_AND_RESULT_NO_EXECUTION',
      'historical_case_count': 70,
      'recovered_case_count': 70,
      'exact_repeatability': True,
      'existing_v2_violations': 37,
      'historical_v2_violation_context': r.pinned('candidate-v2-violation-ledger.json'),
      'public_private_comparability': 'SYNTHETIC_PLANT_SCALE_VS_ASSISTED_FIXED_QUERY_DIAGNOSTIC_NOT_SHARED_PHYSICAL_TRUTH',
    }
  )
  summary = a.seal(
    {
      'schema': 'MEASUREMENT_RESOLUTION_CANDIDATE_SUMMARY_V1',
      'audit_sha256': audit['receipt_sha256'],
      **summarize(nominal),
      'coverage': met['coverage'],
      'supporting_states': {n: supporting_state([x for x in nominal if x['candidate'] == n]) for n in ('V1', 'V2')},
    }
  )
  recovery = a.seal(
    {
      'schema': 'MEASUREMENT_RESOLUTION_CANDIDATE_RECOVERY_INDEX_V1',
      'audit_sha256': audit['receipt_sha256'],
      'execution_policy_sha256': plan['receipt_sha256'],
      'executed_recovery_source_sha256': plan['executor_source_sha256'],
      'published_recovery_reader_sha256': r.SOURCE_SHA,
      'recovery_publication_redaction': 'LOCAL_CHECKOUT_PATH_REPLACED_BY_RUNTIME_ROOT_NO_NUMERIC_OR_IDENTITY_EDITS',
      'recovery_set_sha256': audit['recovery_set_sha256'],
      'cases': proofs,
      'root_relocation': 'METADATA_ONLY_EXACT_ORIGINAL_FULL_REPORT_AND_RESULT_SHA',
      'native_runs': 560,
      'new_search': False,
    }
  )
  return audit, summary, readiness(audit['receipt_sha256']), recovery


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--recovered', required=True)
  parser.add_argument('--plan', required=True)
  parser.add_argument('--output', required=True)
  args = parser.parse_args()
  values = build(args.recovered, json.loads(Path(args.plan).read_bytes()))
  for suffix, value in zip(('audit', 'summary', 'readiness', 'recovery-index'), values, strict=True):
    validate_public(value)
    immutable_public(Path(args.output) / f'measurement-resolution-candidate-{suffix}-v1.json', canonical(value))
    print(suffix, value['receipt_sha256'])
