"""Authorized stored-evidence temporal audit, separate from every V3 executor."""

import argparse
from pathlib import Path
from unittest.mock import patch

import numpy as np
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_attribution as v
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_temporal_math as t
from openpilot.tools.cyber_autotune.empirical_hurdle_fit_cv_store import array_digest

io, p = v.io, v.p
BASELINE = '91b3210d3e7d45a9dc7d6253eeec2f4e36d4a57e'
INPUT_SHA = '95a4bb4828137f0280dcebb1e1e39ceed8cdbcfa18fea0d1863e372134e3c2f3'
SUCCESS = 'HURDLE_STAGE1_V3_TEMPORAL_AUDIT_COMPLETE'
IDENTITIES = ('anchor_route_id', 'anchor_segment_sha', 's2_ri_run_id', 'anchor_index', 'within_run_index')
ALLOWED = set(IDENTITIES) | {'actual_delta_tick', 'prior_delta_tick', 'p_move', 'train_probability'}
RANK_FIELDS = (
  'count',
  'positive_count',
  'negative_count',
  'auc_num2',
  'auc_den2',
  'auc',
  'brier',
  'true_move_prevalence',
  'mean_probability',
  'calibration_bias',
  'static_score_mean',
  'move_score_mean',
  'score_mean_gap',
  'support_state',
)
EMPTY_RANK_FIELDS = ('positive_count', 'negative_count', 'auc', 'auc_num2', 'auc_den2', 'support_state')
RUN_FIELDS = ('count', 'boundary_censored_count', 'median', 'p90', 'p95', 'max')
POPULATION_FIELDS = ('route_id', 'anchor_sha256', 'source_receipt_sha256', 'v2_reference_receipt_sha256', 'probability_sha256', 'scores', 'transitions', 'runs')


def exact_keys(value, fields, sealed=False):
  io.require(type(value) is dict and set(value) == set(fields) | (set(p.FIREWALL) | {'receipt_sha256'} if sealed else set()), 'TEMPORAL_SCHEMA_CONFLICT')


def sha_string(value):
  return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def validate_authorization(auth, output):
  exact_keys(
    auth, ('schema', 'baseline', 'scope', 'policy_sha256', 'source_roots', 'output_root', 'executor_sources', 'v1_manifest_sha256', 'v2_manifest_sha256'), True
  )
  io.require(auth['schema'] == 'HURDLE_STAGE1_V3_TEMPORAL_AUTHORIZATION' and auth['baseline'] == BASELINE)
  io.require(auth['scope'] == 'STORED_TEMPORAL_DIAGNOSTICS_ONLY_NO_V3_EXECUTION')
  io.require(auth['v1_manifest_sha256'] == io.SOURCE_SHA and auth['v2_manifest_sha256'] == v.V2_SHA)
  io.require(type(auth['source_roots']) is list and len(auth['source_roots']) == 2 and all(sha_string(x) for x in auth['source_roots']))
  io.require(auth['source_roots'][0] != auth['source_roots'][1])
  io.require(auth['output_root'] == p.sha(str(io.safe(output)).encode()))
  io.require(auth['executor_sources'] == sources() and auth['policy_sha256'] == policy()['receipt_sha256'])
  io.require(io.read_json(output / 'policy.json', auth['policy_sha256']) == policy())


def public_inputs():
  binding = io.read_json(p.PUBLIC / 'empirical-hurdle-stage1-v3-research-inputs.json', INPUT_SHA)
  for name, expected in binding['public_inputs'].items():
    io.require(io.digest(p.PUBLIC / name) == expected['file_sha256'], 'STAGE1_V3_RESEARCH_INPUT_CONFLICT')
    io.read_json(p.PUBLIC / name, expected['receipt_sha256'])
  return binding


def policy():
  return p.seal(
    {
      'schema': 'HURDLE_STAGE1_V3_TEMPORAL_POLICY',
      'baseline': BASELINE,
      'public_binding_sha256': INPUT_SHA,
      'v1_manifest_sha256': io.SOURCE_SHA,
      'v2_manifest_sha256': v.V2_SHA,
      'route_population': 'HRI_D00_L01_ONE_STEP_ONE_POPULATION_PER_ROUTE_NO_CANDIDATE_POOLING',
      'previous_state': 'STORED_PRIOR_DELTA_TICK_ZERO_VS_NONZERO',
      'history_lengths': [1, 2],
      'history_two': 'ADJACENT_STORED_PREDECESSOR_ONLY',
      'continuity': list(IDENTITIES),
      'index_step': 1,
      'runs': 'OBSERVED_ELIGIBLE_FRAGMENTS_REPORT_BOUNDARY_CENSORING',
      'score_population': 'EACH_CANDIDATE_FOLD_TRAIN_AND_DEVELOPMENT_INDEPENDENTLY',
      'auc': 'PYTHON_INT_NUM2_DEN2_EQUAL_SCORE_HALF_CREDIT',
      'trigger_support': 'AT_LEAST_201_EACH_CLASS_ALL_32_DEV_JOBS_NO_EXCLUSION',
      'persistence': 'BOTH_ROUTES_P_MOVE_GIVEN_MOVE_STRICTLY_GREATER_THAN_GIVEN_STATIC_SUPPORT_GE_201',
      'allowed_array_fields': sorted(ALLOWED),
      'private_output': 'D_ONLY_AGGREGATES',
      'no_v3_performance': True,
      'execution_calls': v.ZERO,
    }
  )


def sources():
  return {Path(m.__file__).name: io.digest(Path(m.__file__)) for m in (v, t, io, t.a)} | {Path(__file__).name: io.digest(Path(__file__))}


class StoredReader:
  def __init__(self):
    self.opened = {}

  def load(self, root, receipt, key):
    io.require(key in ALLOWED, 'TEMPORAL_FIELD_NOT_AUTHORIZED')
    member = io.member(root, receipt['arrays'][key]['filename'])
    self.opened[member] = receipt['arrays'][key]['file_sha256']
    return io.load_array(root, receipt, key)

  def verify_unchanged(self):
    io.require(all(io.digest(path) == sha for path, sha in self.opened.items()), 'TEMPORAL_SOURCE_MUTATION')
    return p.sha(p.canonical(sorted(self.opened.values())))


def authorize(v1, v2, output):
  import shutil

  public_inputs()
  for root in (v1, v2):
    io.output_root(output, root)
  io.require(shutil.disk_usage('/mnt/d').free >= 128 * 1024**2, 'TEMPORAL_AGGREGATE_STORAGE_BLOCKED')
  v.metadata(v1, v2)
  auth = p.seal(
    {
      'schema': 'HURDLE_STAGE1_V3_TEMPORAL_AUTHORIZATION',
      'baseline': BASELINE,
      'scope': 'STORED_TEMPORAL_DIAGNOSTICS_ONLY_NO_V3_EXECUTION',
      'policy_sha256': policy()['receipt_sha256'],
      'source_roots': [p.sha(str(io.safe(x)).encode()) for x in (v1, v2)],
      'output_root': p.sha(str(io.safe(output)).encode()),
      'executor_sources': sources(),
      'v1_manifest_sha256': io.SOURCE_SHA,
      'v2_manifest_sha256': v.V2_SHA,
    }
  )
  io.write_json(output / 'policy.json', policy())
  io.write_json(output / 'authorization.json', auth)
  return auth


def analyze_population(v1, v2, old, job, name, reader):
  root, receipt = v.population(v1, old, name)
  _, new = v.population(v2, job, name, True)
  v.reference(new, receipt)
  delta, prior = (reader.load(root, receipt, k) for k in ('actual_delta_tick', 'prior_delta_tick'))
  identities = {k: reader.load(root, receipt, k) for k in IDENTITIES}
  linked = t.continuity(identities)
  transition = t.transitions(delta, prior, linked)
  if name == 'train':
    probability_root = root.parent / 'threshold'
    pr = io.read_json(probability_root / 'receipt.json', old['threshold']['receipt_sha256'])
    manifest = io.read_json(v1 / 'repeat-1/manifest.json', io.SOURCE_SHA)
    path = probability_root / 'receipt.json'
    io.require(io.digest(path) == manifest['files'][path.relative_to(v1 / 'repeat-1').as_posix()])
    binding = pr['arrays']['train_probability']
    member = probability_root / binding['filename']
    io.require(binding['file_sha256'] == manifest['files'][member.relative_to(v1 / 'repeat-1').as_posix()])
    probability = reader.load(probability_root, pr, 'train_probability')
    io.require(array_digest(probability) == new['probability_sha256'] == job['threshold']['probability_sha256'])
  else:
    probability = reader.load(root, receipt, 'p_move')
    io.require(array_digest(probability) == new['arrays']['p_move']['array_sha256'])
  route_ids = np.unique(identities['anchor_route_id'])
  io.require(len(route_ids) == 1)
  route = route_ids[0].decode()
  return {
    'scores': t.scores(probability, delta, prior),
    'transitions': transition,
    'runs': t.runs(delta, linked),
    'route_id': route,
    'anchor_sha256': receipt['anchor_sha256'],
    'source_receipt_sha256': receipt['receipt_sha256'],
    'v2_reference_receipt_sha256': new['receipt_sha256'],
    'probability_sha256': array_digest(probability),
  }


def run(v1, v2, output, replica):
  io.require(replica in ('repeat-1', 'repeat-2'))
  auth = io.read_json(output / 'authorization.json')
  validate_authorization(auth, output)
  io.require(auth['source_roots'] == [p.sha(str(io.safe(x)).encode()) for x in (v1, v2)])
  io.require(auth['output_root'] == p.sha(str(io.safe(output)).encode()))
  root = output / replica
  io.require(not root.exists(), 'TEMPORAL_NO_PARTIAL_REUSE')
  public_inputs()
  with v.firewall():
    manifests = [io.digest(x / 'repeat-1/manifest.json') for x in (v1, v2)]
    _, _, old, jobs = v.metadata(v1, v2)
    reader, results, routes = StoredReader(), [], {}
    for historical, job in zip(old, jobs, strict=True):
      populations = {name: analyze_population(v1, v2, historical, job, name, reader) for name in ('train', 'one-step')}
      if job['candidate_id'] == 'HRI_D00_L01':
        dev = populations['one-step']
        routes[dev['route_id']] = {k: dev[k] for k in ('transitions', 'runs', 'anchor_sha256', 'source_receipt_sha256')}
      row = p.seal(
        {
          'schema': 'HURDLE_STAGE1_V3_TEMPORAL_JOB',
          'candidate_id': job['candidate_id'],
          'fold': job['fold'],
          'train': populations['train'],
          'development': populations['one-step'],
        }
      )
      io.write_json(root / f'jobs/{job["candidate_id"]}/{job["fold"]}.json', row)
      results.append(row)
      print(f'TEMPORAL_JOB_COMPLETE {len(results)}/32', flush=True)
    io.require(len(routes) == 2)
    summary = p.seal(
      {
        'schema': 'HURDLE_STAGE1_V3_TEMPORAL_SUMMARY',
        'routes': routes,
        'persistence_state': 'TEMPORAL_MOVE_PERSISTENCE_PRESENT_BOTH_ROUTES'
        if all(t.persistence(r['transitions']) for r in routes.values())
        else 'TEMPORAL_MOVE_PERSISTENCE_NOT_UNIVERSAL',
        'ranking_states': {k: t.rank_trigger([r['development']['scores'][k] for r in results]) for k in ('onset', 'continuation')},
        'source_members_unchanged_sha256': reader.verify_unchanged(),
        'opened_member_count': len(reader.opened),
        'source_immutability_scope': 'OPENED_MANIFEST_BOUND_MEMBERS_AND_MANIFESTS_ONLY_NO_UNOPENED_GLOBAL_CLAIM',
        'v3_performance': 'NOT_RUN',
        'execution_calls': v.ZERO,
      }
    )
    io.require(manifests == [io.digest(x / 'repeat-1/manifest.json') for x in (v1, v2)])
    io.write_json(root / 'summary.json', summary)
    return io.finish(
      root,
      [f'jobs/{c}/{f}.json' for c, f in io.JOBS] + ['summary.json'],
      {
        'schema': 'HURDLE_STAGE1_V3_TEMPORAL_MANIFEST',
        'status': SUCCESS,
        'job_order': [list(j) for j in io.JOBS],
        'authorization_sha256': auth['receipt_sha256'],
        'summary_sha256': summary['receipt_sha256'],
        'v3_performance': 'NOT_RUN',
      },
    )


def validate_population(row):
  try:
    exact_keys(row, POPULATION_FIELDS)
    for field in ('route_id', 'anchor_sha256', 'source_receipt_sha256', 'v2_reference_receipt_sha256', 'probability_sha256'):
      io.require(len(row[field]) == 64 and all(c in '0123456789abcdef' for c in row[field]))
    tr = row['transitions']
    exact_keys(tr, ('count', 'counts', 'previous_static', 'previous_move', 'history_two'))
    counts = tr['counts']
    io.require(set(counts) == {'SS', 'SM', 'MS', 'MM'})
    io.require(all(type(x) is int and x >= 0 for x in counts.values()) and sum(counts.values()) == tr['count'])
    for name, pos, neg in (('previous_static', 'SM', 'SS'), ('previous_move', 'MM', 'MS')):
      ratio = tr[name]
      exact_keys(ratio, ('numerator', 'denominator', 'ratio'))
      n, d = counts[pos], counts[pos] + counts[neg]
      io.require(ratio == {'numerator': n, 'denominator': d, 'ratio': n / d if d else None})
    expected = {
      'onset': (counts['SM'], counts['SS'] + counts['MS']),
      'continuation': (counts['MM'], counts['SS'] + counts['MS']),
      'previous_static': (counts['SM'], counts['SS']),
      'previous_move': (counts['MM'], counts['MS']),
    }
    io.require(set(row['scores']) == set(expected))
    for key, (positive, negative) in expected.items():
      rank = row['scores'][key]
      exact_keys(rank, RANK_FIELDS if positive and negative else EMPTY_RANK_FIELDS)
      io.require((rank['positive_count'], rank['negative_count']) == (positive, negative))
      if not positive or not negative:
        io.require(rank['auc'] is rank['auc_num2'] is rank['auc_den2'] is None and rank['support_state'] == 'EMPTY_CLASS')
      else:
        numerator, denominator = rank['auc_num2'], rank['auc_den2']
        io.require(type(numerator) is int and type(denominator) is int and 0 <= numerator <= denominator == 2 * positive * negative)
        io.require(rank['auc'] == numerator / denominator)
        io.require(rank['count'] == positive + negative and rank['true_move_prevalence'] == positive / (positive + negative))
        io.require(rank['calibration_bias'] == rank['mean_probability'] - rank['true_move_prevalence'])
        io.require(rank['score_mean_gap'] == rank['move_score_mean'] - rank['static_score_mean'])
        io.require(all(0 <= rank[k] <= 1 for k in ('brier', 'mean_probability', 'static_score_mean', 'move_score_mean')))
        io.require(rank['support_state'] == ('SUPPORTED' if min(positive, negative) >= 201 else 'SMALL_SUPPORT_DESCRIPTIVE_ONLY'))
        io.require(all(np.isfinite(rank[k]) for k in ('static_score_mean', 'move_score_mean', 'score_mean_gap', 'brier', 'mean_probability')))
    exact_keys(row['runs'], ('STATIC', 'MOVE', 'fragment_count', 'interpretation'))
    io.require(row['runs']['interpretation'] == 'ELIGIBLE_OBSERVED_FRAGMENTS_BOUNDARY_CENSORED_NOT_RAW_ROUTE_RUNS')
    io.require(type(row['runs']['fragment_count']) is int and 1 <= row['runs']['fragment_count'] <= tr['count'])
    for state in ('STATIC', 'MOVE'):
      r = row['runs'][state]
      exact_keys(r, RUN_FIELDS)
      io.require(type(r['count']) is int and 0 <= r['boundary_censored_count'] <= r['count'])
      if r['count']:
        io.require(1 <= r['median'] <= r['p90'] <= r['p95'] <= r['max'])
      else:
        io.require(all(r[k] is None for k in ('median', 'p90', 'p95', 'max')))
    h = tr['history_two']
    exact_keys(h, ('support', 'last_two_static', 'any_last_two_move'))
    io.require(h['support'] == tr['count'] - row['runs']['fragment_count'])
    io.require(sum(h[k]['denominator'] for k in ('last_two_static', 'any_last_two_move')) == h['support'] < tr['count'])
    for k in ('last_two_static', 'any_last_two_move'):
      r = h[k]
      exact_keys(r, ('numerator', 'denominator', 'ratio'))
      io.require(0 <= r['numerator'] <= r['denominator'] and r['ratio'] == (r['numerator'] / r['denominator'] if r['denominator'] else None))
  except (KeyError, TypeError, ValueError) as exc:
    raise ValueError('TEMPORAL_INCOMPLETE_AGGREGATE') from exc


def resume(root):
  root = io.safe(root)
  manifest = io.read_json(root / 'manifest.json')
  exact_keys(manifest, ('schema', 'status', 'job_order', 'authorization_sha256', 'summary_sha256', 'v3_performance', 'files'), True)
  io.require(manifest['schema'] == 'HURDLE_STAGE1_V3_TEMPORAL_MANIFEST' and manifest['status'] == SUCCESS)
  io.require(manifest['job_order'] == [list(j) for j in io.JOBS] and manifest['v3_performance'] == 'NOT_RUN')
  auth = io.read_json(root.parent / 'authorization.json', manifest['authorization_sha256'])
  validate_authorization(auth, root.parent)
  io.require(set(manifest['files']) == {f'jobs/{c}/{f}.json' for c, f in io.JOBS} | {'summary.json'})
  io.verify_files(root, manifest['files'])
  rows = []
  for c, f in io.JOBS:
    r = io.read_json(root / f'jobs/{c}/{f}.json')
    exact_keys(r, ('schema', 'candidate_id', 'fold', 'train', 'development'), True)
    io.require((r['candidate_id'], r['fold']) == (c, f))
    io.require(r['schema'] == 'HURDLE_STAGE1_V3_TEMPORAL_JOB')
    for population in ('train', 'development'):
      validate_population(r[population])
    rows.append(r)
  summary = io.read_json(root / 'summary.json', manifest['summary_sha256'])
  exact_keys(
    summary,
    (
      'schema',
      'routes',
      'persistence_state',
      'ranking_states',
      'source_members_unchanged_sha256',
      'opened_member_count',
      'source_immutability_scope',
      'v3_performance',
      'execution_calls',
    ),
    True,
  )
  io.require(summary['opened_member_count'] == len(io.JOBS) * 2 * (len(IDENTITIES) + 3))
  io.require(sha_string(summary['source_members_unchanged_sha256']))
  io.require(summary['source_immutability_scope'] == 'OPENED_MANIFEST_BOUND_MEMBERS_AND_MANIFESTS_ONLY_NO_UNOPENED_GLOBAL_CLAIM')
  io.require(summary['schema'] == 'HURDLE_STAGE1_V3_TEMPORAL_SUMMARY' and summary['v3_performance'] == 'NOT_RUN')
  io.require(summary['execution_calls'] == v.ZERO)
  expected_routes = {
    r['development']['route_id']: {k: r['development'][k] for k in ('transitions', 'runs', 'anchor_sha256', 'source_receipt_sha256')} for r in rows[:2]
  }
  io.require(len(expected_routes) == 2 and summary['routes'] == expected_routes)
  for index, row in enumerate(rows):
    io.require(row['train']['route_id'] != row['development']['route_id'])
    for key in ('route_id', 'anchor_sha256', 'transitions', 'runs'):
      io.require(row['train'][key] == rows[index ^ 1]['development'][key])
  io.require(summary['ranking_states'] == {k: t.rank_trigger([r['development']['scores'][k] for r in rows]) for k in ('onset', 'continuation')})
  persistence = all(t.persistence(r['transitions']) for r in expected_routes.values())
  io.require(summary['persistence_state'] == ('TEMPORAL_MOVE_PERSISTENCE_PRESENT_BOTH_ROUTES' if persistence else 'TEMPORAL_MOVE_PERSISTENCE_NOT_UNIVERSAL'))
  return manifest


def verify(output):
  with (
    patch.object(StoredReader, 'load', io.forbidden),
    patch.object(io, 'load_array', io.forbidden),
    patch.object(t, 'scores', io.forbidden),
    patch.object(t, 'transitions', io.forbidden),
    patch.object(t, 'runs', io.forbidden),
  ):
    first, second = (resume(output / name) for name in ('repeat-1', 'repeat-2'))
  io.require(first == second, 'TEMPORAL_REPEATABILITY_FAILURE')
  receipt = p.seal(
    {
      'schema': 'HURDLE_STAGE1_V3_TEMPORAL_REPEATABILITY',
      'status': 'BYTE_EXACT_PASS',
      'manifest_sha256': first['receipt_sha256'],
      'trapped_resume': 'PASS',
      'v3_performance': 'NOT_RUN',
    }
  )
  io.write_json(output / 'repeatability.json', receipt)
  return receipt


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--v1', type=Path, required=True)
  parser.add_argument('--v2', type=Path, required=True)
  parser.add_argument('--output', type=Path, required=True)
  args = parser.parse_args()
  authorize(args.v1, args.v2, args.output)
  for replica in ('repeat-1', 'repeat-2'):
    run(args.v1, args.v2, args.output, replica)
  print(verify(args.output)['status'])


if __name__ == '__main__':
  main()
