"""Allowlisted aggregate publication; no private numerical arrays are loaded."""

import argparse
from pathlib import Path
from openpilot.tools.cyber_autotune import empirical_hurdle_v3_temporal as audit
from openpilot.tools.cyber_autotune import empirical_hurdle_v2_publication as privacy

io, p = audit.io, audit.p


def public_population(row):
  audit.validate_population(row)
  return {
    **{k: row[k] for k in ('route_id', 'anchor_sha256', 'source_receipt_sha256', 'probability_sha256')},
    'scores': {
      name: {k: score[k] for k in (audit.RANK_FIELDS if score['auc'] is not None else audit.EMPTY_RANK_FIELDS)} for name, score in row['scores'].items()
    },
  }


def publish_temporal(output):
  repeated = audit.verify(output)
  manifest = audit.resume(output / 'repeat-1')
  summary = io.read_json(output / 'repeat-1/summary.json', manifest['summary_sha256'])
  jobs = [io.read_json(output / f'repeat-1/jobs/{c}/{f}.json') for c, f in io.JOBS]
  body = {
    'temporal-evidence-policy': {'policy': audit.policy()},
    'transition-statistics': {'routes': {k: {'transitions': r['transitions'], 'anchor_sha256': r['anchor_sha256']} for k, r in summary['routes'].items()}},
    'run-length-statistics': {
      'routes': {
        k: {
          **{state: {field: r['runs'][state][field] for field in audit.RUN_FIELDS} for state in ('STATIC', 'MOVE')},
          **{field: r['runs'][field] for field in ('fragment_count', 'interpretation')},
        }
        for k, r in summary['routes'].items()
      }
    },
    'onset-continuation-ranking': {
      'jobs': [
        {
          'candidate_id': j['candidate_id'],
          'fold': j['fold'],
          **{pop: public_population(j[pop]) for pop in ('train', 'development')},
        }
        for j in jobs
      ]
    },
    'temporal-design-trigger': {
      'persistence_state': summary['persistence_state'],
      'onset_state': 'ONSET_RANK_SIGNAL_PRESENT' if summary['ranking_states']['onset'] else 'ONSET_RANK_SIGNAL_NOT_UNIVERSAL',
      'continuation_state': 'CONTINUATION_RANK_SIGNAL_PRESENT' if summary['ranking_states']['continuation'] else 'CONTINUATION_RANK_SIGNAL_NOT_UNIVERSAL',
      'interpretation': 'DESCRIPTIVE_OBSERVED_TRUTH_NOT_PROJECTED_GATE_PERFORMANCE_NOT_NEW_FEATURE_INFORMATION',
      'repeatability': repeated,
      'opened_member_count': summary['opened_member_count'],
      'source_immutability_scope': summary['source_immutability_scope'],
      'source_members_unchanged_sha256': summary['source_members_unchanged_sha256'],
    },
  }
  result = {}
  for name, fields in body.items():
    value = p.seal(
      {
        'schema': 'HURDLE_STAGE1_V3_TEMPORAL_PUBLIC',
        'baseline': audit.BASELINE,
        'private_manifest_sha256': manifest['receipt_sha256'],
        'v1_manifest_sha256': io.SOURCE_SHA,
        'v2_manifest_sha256': audit.v.V2_SHA,
        'v3_performance': 'NOT_RUN',
        'execution_calls': audit.v.ZERO,
        'holdout': 'CLOSED',
        'opening_count': 0,
        'vehicle_authority': 'NONE',
        **fields,
      }
    )
    privacy.privacy(value)
    path = p.PUBLIC / ('empirical-hurdle-stage1-v3-' + name + '.json')
    io.write_json(path, value)
    result[path.name] = value['receipt_sha256']
  return result


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output', type=Path, required=True)
  publish_temporal(parser.parse_args().output)
